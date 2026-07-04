#!/usr/bin/env python3
"""
Build events.db from events/curated/*.json
Output: events/events.db (SQLite, same schema as D1 curated_events table)
"""

import json, os, sqlite3, re, glob, hashlib

EVENTS_DIR = "events/curated"
OUTPUT_DB = "events/events.db"
SCHEMA = """
DROP TABLE IF EXISTS curated_events;
CREATE TABLE curated_events (
    id INTEGER PRIMARY KEY,
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
CREATE INDEX idx_curated_dates ON curated_events(date_start);
CREATE INDEX idx_curated_title ON curated_events(normalized_title);
"""


def event_hash(event):
    """Generate a stable 64-bit integer ID from the event's identity.
    Uses event_url as primary key; falls back to title+date_start.
    The ID is deterministic and survives reordering/additions/deletions."""
    key = event.get("event_url") or f"{event.get('title', '')}|{event.get('date_start', '')}"
    # Use 13 hex chars = 52 bits, safe within JavaScript's Number.MAX_SAFE_INTEGER (2^53)
    h = hashlib.sha256(key.encode("utf-8")).hexdigest()[:13]
    return int(h, 16)


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
        (id, title, normalized_title, date_start, date_end, time_raw, location, organizer,
         description, event_url, sources, tags, recurring_group_id)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)"""

    seen_ids = set()
    for ev in events:
        eid = event_hash(ev)
        # Collision safeguard (vanishingly unlikely with 64-bit IDs)
        if eid in seen_ids:
            new_key = f"{ev.get('event_url', '')}|{ev.get('title', '')}|{len(seen_ids)}"
            eid = int(hashlib.sha256(new_key.encode('utf-8')).hexdigest()[:13], 16)
        seen_ids.add(eid)

        sources_str = ",".join(ev.get("sources", [])) if isinstance(ev.get("sources"), list) else (ev.get("sources") or "")
        tags_str = ",".join(ev.get("tags", [])) if isinstance(ev.get("tags"), list) else (ev.get("tags") or "")
        norm = normalize_title(ev.get("title", ""))

        conn.execute(insert_sql, (
            eid,
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
