#!/usr/bin/env python3
"""Restore curated_events from JSON export (taken before any modifications)."""
import json, sqlite3

DB = "/Users/joereuter/Clones/schdudesee/stutensee_events.db"

with open("/tmp/curated_events_export.json") as f:
    events = json.load(f)

conn = sqlite3.connect(DB)
conn.execute("PRAGMA journal_mode=WAL")
conn.execute("BEGIN")

conn.execute("DELETE FROM raw_to_curated")
conn.execute("DELETE FROM curated_events")

for e in events:
    conn.execute(
        """INSERT INTO curated_events
           (id, title, date_start, date_end, time_raw, location, organizer,
            description, event_url, sources, tags, dedup_round)
           VALUES (?,?,?,?,?,?,?,?,?,?,?,?)""",
        (e["id"], e["title"], e.get("date_start"), e.get("date_end"),
         e.get("time_raw"), e.get("location"), e.get("organizer"),
         e.get("description"), e.get("event_url"), e.get("sources"),
         e.get("tags"), e.get("dedup_round"))
    )

conn.execute("DELETE FROM sqlite_sequence WHERE name='curated_events'")
conn.commit()
conn.close()

count = len(events)
print(f"Restored {count} events (original state)")
