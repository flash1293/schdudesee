#!/usr/bin/env python3
"""
Build events.db from events/curated/*.json
Output: events/events.db (SQLite, same schema as D1 curated_events table)
"""

import json, os, sqlite3, re, glob

EVENTS_DIR = "events/curated"
OUTPUT_DB = "events/events.db"
SCHEMA = """
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
    updated_at TEXT DEFAULT (datetime('now'))
);
CREATE INDEX IF NOT EXISTS idx_curated_dates ON curated_events(date_start);
CREATE INDEX IF NOT EXISTS idx_curated_title ON curated_events(normalized_title);
"""


def normalize_title(title):
    if not title:
        return ""
    t = title.lower().strip()
    for suffix in [' in blankenloch', ' in büchig', ' in friedrichstal', ' in spöck', ' in staffort',
                    ' blankenloch', ' büchig', ' friedrichstal', ' spöck', ' staffort']:
        t = t.replace(suffix, '')
    return t


def main():
    os.makedirs(os.path.dirname(OUTPUT_DB), exist_ok=True)

    pattern = os.path.join(EVENTS_DIR, "*.json")
    files = sorted(glob.glob(pattern))

    if not files:
        print(f"No JSON files found in {EVENTS_DIR}/")
        # Create empty DB for CI to not fail on empty PRs
        conn = sqlite3.connect(OUTPUT_DB)
        conn.executescript(SCHEMA)
        conn.commit()
        conn.close()
        print(f"Created empty {OUTPUT_DB}")
        return

    events = []
    for fp in files:
        with open(fp, "r") as f:
            ev = json.load(f)
        events.append(ev)

    conn = sqlite3.connect(OUTPUT_DB)
    conn.executescript(SCHEMA)

    insert_sql = """INSERT INTO curated_events
        (title, normalized_title, date_start, date_end, time_raw, location, organizer,
         description, event_url, sources, tags, recurring_group_id)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)"""

    for ev in events:
        sources_str = ",".join(ev.get("sources", [])) if isinstance(ev.get("sources"), list) else (ev.get("sources") or "")
        tags_str = ",".join(ev.get("tags", [])) if isinstance(ev.get("tags"), list) else (ev.get("tags") or "")
        norm = normalize_title(ev.get("title", ""))

        conn.execute(insert_sql, (
            ev.get("title", ""),
            norm,
            ev.get("date_start"),
            ev.get("date_end"),
            ev.get("time_raw"),
            ev.get("location"),
            ev.get("organizer"),
            ev.get("description"),
            ev.get("event_url"),
            sources_str,
            tags_str,
            ev.get("recurring_group_id"),
        ))

    conn.commit()
    count = conn.execute("SELECT COUNT(*) FROM curated_events").fetchone()[0]
    conn.close()
    print(f"Built {OUTPUT_DB}: {count} events from {len(files)} JSON files")


if __name__ == "__main__":
    main()
