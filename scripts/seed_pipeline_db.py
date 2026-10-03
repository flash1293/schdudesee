#!/usr/bin/env python3
"""Bootstrap the pipeline database (stutensee_events.db) from the published
event files in events/curated/*.json.

Why this exists
---------------
`run_pipeline.py` keeps its working state in a SQLite database that is *not*
committed (it is a local workspace file). Every run rebuilds `curated_events`
from `raw_events`, so starting from an empty database would silently discard the
whole existing catalogue and publish a much smaller site.

The published JSON files are the durable, versioned source of truth (they are
what the website is built from). This script seeds the pipeline database from
them, so the pipeline can be started on any machine — or after a fresh sandbox —
without losing data.

Usage
-----
    python3 scripts/seed_pipeline_db.py           # seed only if the DB is missing/empty
    python3 scripts/seed_pipeline_db.py --force    # rebuild the DB from scratch
    python3 scripts/seed_pipeline_db.py --db /path/to/stutensee_events.db
"""

import argparse
import glob
import json
import os
import sqlite3
import sys

SCRIPTS_DIR = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.dirname(SCRIPTS_DIR)
DEFAULT_DB = os.path.join(REPO_ROOT, "stutensee_events.db")
EVENTS_DIR = os.path.join(REPO_ROOT, "events", "curated")

# Keep title normalization identical to the pipeline, so tag/featured
# restore-by-key matching works after the first rebuild.
sys.path.insert(0, SCRIPTS_DIR)
from build_db import normalize_title  # noqa: E402

SCHEMA = """
CREATE TABLE IF NOT EXISTS raw_events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    source_url TEXT NOT NULL,
    title TEXT,
    date_start TEXT,
    date_end TEXT,
    time_raw TEXT,
    location TEXT,
    organizer TEXT,
    description TEXT,
    event_url TEXT,
    raw_html_hash TEXT,
    scraped_at TEXT DEFAULT (datetime('now')),
    tags TEXT DEFAULT '',
    UNIQUE(source_url, event_url, date_start, title)
);

CREATE TABLE IF NOT EXISTS curated_events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title TEXT NOT NULL,
    normalized_title TEXT,
    date_start TEXT,
    date_end TEXT,
    time_raw TEXT,
    location TEXT,
    organizer TEXT,
    description TEXT,
    event_url TEXT,
    sources TEXT,
    tags TEXT DEFAULT '',
    recurring_group_id INTEGER DEFAULT NULL,
    dedup_round INTEGER,
    created_at TEXT DEFAULT (datetime('now')),
    updated_at TEXT DEFAULT (datetime('now')),
    featured INTEGER DEFAULT 0,
    is_passed INTEGER DEFAULT 0
);

CREATE TABLE IF NOT EXISTS raw_to_curated (
    raw_id INTEGER NOT NULL,
    curated_id INTEGER NOT NULL,
    dedup_round INTEGER NOT NULL,
    source TEXT DEFAULT '',
    PRIMARY KEY (raw_id, curated_id)
);

CREATE INDEX IF NOT EXISTS idx_curated_dates ON curated_events(date_start);
CREATE INDEX IF NOT EXISTS idx_curated_title ON curated_events(normalized_title);
"""


def as_list(value):
    """Accept a list or a comma-separated string (the JSON files use lists)."""
    if isinstance(value, list):
        return [str(v).strip() for v in value if str(v).strip()]
    if isinstance(value, str):
        return [v.strip() for v in value.split(",") if v.strip()]
    return []


def count_curated(db_path):
    if not os.path.exists(db_path):
        return 0
    try:
        conn = sqlite3.connect(db_path)
        try:
            return conn.execute("SELECT COUNT(*) FROM curated_events").fetchone()[0]
        finally:
            conn.close()
    except Exception:
        return 0


def main():
    parser = argparse.ArgumentParser(description="Seed the pipeline DB from events/curated/*.json")
    parser.add_argument("--db", default=DEFAULT_DB, help=f"Target DB path (default: {DEFAULT_DB})")
    parser.add_argument("--events-dir", default=EVENTS_DIR, help="Directory with event JSON files")
    parser.add_argument("--force", action="store_true", help="Rebuild the DB from scratch")
    args = parser.parse_args()

    files = sorted(glob.glob(os.path.join(args.events_dir, "*.json")))
    if not files:
        print(f"ERROR: no event files found in {args.events_dir}", file=sys.stderr)
        return 1

    existing = count_curated(args.db)
    if existing and not args.force:
        print(f"Pipeline DB already seeded ({existing} curated events) — nothing to do.")
        return 0

    if args.force and os.path.exists(args.db):
        backup = args.db + ".pre_seed_backup"
        os.replace(args.db, backup)
        print(f"Existing DB moved to {os.path.basename(backup)}")

    conn = sqlite3.connect(args.db)
    c = conn.cursor()
    c.executescript(SCHEMA)

    raw_sql = """INSERT OR IGNORE INTO raw_events
        (source_url, title, date_start, date_end, time_raw, location, organizer,
         description, event_url, raw_html_hash, tags)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)"""
    curated_sql = """INSERT INTO curated_events
        (title, normalized_title, date_start, date_end, time_raw, location, organizer,
         description, event_url, sources, tags, recurring_group_id, dedup_round,
         featured, is_passed)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)"""

    seeded = 0
    raw_rows = 0
    for fp in files:
        try:
            with open(fp, encoding="utf-8") as f:
                ev = json.load(f)
        except Exception as e:
            print(f"  Skipping {os.path.basename(fp)}: {e}", file=sys.stderr)
            continue

        title = ev.get("title", "")
        if not title or not ev.get("date_start"):
            continue

        sources = as_list(ev.get("sources"))
        tags = as_list(ev.get("tags"))
        source_url = sources[0] if sources else "seeded_from_json"
        raw_html_hash = "seeded:" + os.path.basename(fp)

        c.execute(raw_sql, (
            source_url, title, ev.get("date_start"), ev.get("date_end"),
            ev.get("time_raw", ""), ev.get("location", ""), ev.get("organizer", ""),
            ev.get("description", ""), ev.get("event_url", ""), raw_html_hash,
            ",".join(tags),
        ))
        if c.rowcount > 0:
            raw_rows += 1
        raw_id = c.lastrowid
        if not raw_id:
            row = c.execute(
                "SELECT id FROM raw_events WHERE source_url = ? AND COALESCE(event_url,'') = ? "
                "AND COALESCE(date_start,'') = ? AND title = ?",
                (source_url, ev.get("event_url", ""), ev.get("date_start", ""), title),
            ).fetchone()
            raw_id = row[0] if row else None

        c.execute(curated_sql, (
            title, normalize_title(title), ev.get("date_start"), ev.get("date_end"),
            ev.get("time_raw", ""), ev.get("location", ""), ev.get("organizer", ""),
            ev.get("description", ""), ev.get("event_url", ""), ", ".join(sources),
            ",".join(tags), ev.get("recurring_group_id"), 1,
            int(ev.get("featured") or 0), int(ev.get("is_passed") or 0),
        ))
        curated_id = c.lastrowid
        if raw_id:
            c.execute(
                "INSERT OR IGNORE INTO raw_to_curated (raw_id, curated_id, dedup_round, source) "
                "VALUES (?, ?, ?, ?)",
                (raw_id, curated_id, 1, source_url),
            )
        seeded += 1

    conn.commit()
    total_raw = c.execute("SELECT COUNT(*) FROM raw_events").fetchone()[0]
    total_cur = c.execute("SELECT COUNT(*) FROM curated_events").fetchone()[0]
    featured = c.execute("SELECT COUNT(*) FROM curated_events WHERE featured = 1").fetchone()[0]
    tagged = c.execute("SELECT COUNT(*) FROM curated_events WHERE tags != ''").fetchone()[0]
    conn.close()

    print(f"Seeded from {len(files)} event files")
    print(f"  raw_events:      {total_raw} ({raw_rows} inserted now)")
    print(f"  curated_events:  {total_cur} ({seeded} inserted now, {tagged} tagged, {featured} featured)")
    print(f"  Database:        {args.db}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
