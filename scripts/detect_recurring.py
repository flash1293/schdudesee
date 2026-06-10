#!/usr/bin/env python3
"""Detect recurring events in curated_events and assign recurring_group_id."""

import hashlib
import sqlite3
from datetime import datetime, timedelta
from collections import defaultdict

DB_PATH = "stutensee_events.db"

GAP_TOLERANCE = 1  # days +/- for gap matching


def parse_date(d):
    if not d:
        return None
    try:
        return datetime.strptime(d, "%Y-%m-%d").date()
    except ValueError:
        return None


def gap_type(gap_days):
    if gap_days == 7:
        return "weekly"
    elif gap_days == 14:
        return "biweekly"
    elif 28 <= gap_days <= 31:
        return "monthly"
    return None


def classify_gaps(gaps):
    if not gaps:
        return None
    if all(g == 7 for g in gaps):
        return "weekly"
    if all(g == 14 for g in gaps):
        return "biweekly"
    if all(28 <= g <= 31 for g in gaps):
        return "monthly"
    return None


def main():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()

    c.execute("SELECT id, title, COALESCE(NULLIF(normalized_title, ''), title) AS group_key, date_start FROM curated_events ORDER BY group_key, date_start")
    rows = c.fetchall()

    groups = defaultdict(list)
    for id_, title, group_key, date_start in rows:
        d = parse_date(date_start)
        if d is not None:
            groups[group_key].append((id_, title, d))

    c.execute("UPDATE curated_events SET recurring_group_id = NULL")
    conn.commit()

    recurring_groups_found = 0
    total_events_linked = 0

    for group_key, events in groups.items():
        if len(events) < 2:
            continue
        events.sort(key=lambda x: x[2])

        gaps = []
        for i in range(1, len(events)):
            gap = (events[i][2] - events[i-1][2]).days
            gaps.append(gap)

        pattern = classify_gaps(gaps)
        if pattern is None:
            continue

        # Use a stable hash of the group key so recurring_group_id
        # doesn't change every pipeline run (auto-increment IDs are unstable
        # after the delete/re-insert cycle in dedup_sql).
        # Take first 8 bytes of SHA256, mask to signed 64-bit range so the
        # value always fits in SQLite's signed INTEGER column.
        group_id = int.from_bytes(hashlib.sha256(group_key.encode()).digest()[:8], "big") & 0x7FFFFFFFFFFFFFFF
        event_ids = [e[0] for e in events]
        placeholders = ",".join("?" for _ in event_ids)
        c.execute(f"UPDATE curated_events SET recurring_group_id = ? WHERE id IN ({placeholders})", (group_id, *event_ids))

        recurring_groups_found += 1
        total_events_linked += len(events)

        print(f"  {pattern}: '{group_key}' — {len(events)} events, group_id={group_id}")

    conn.commit()
    conn.close()

    print(f"\nRecurring groups found: {recurring_groups_found}")
    print(f"Total events linked: {total_events_linked}")


if __name__ == "__main__":
    main()
