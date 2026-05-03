#!/usr/bin/env python3
"""
retag_districts.py — Comprehensive district tag backfill for all curated events.

Re-checks ALL curated events against the DISTRICTS map from run_pipeline.py
and adds any missing district tags. Fixes the known issue where tag_untagged()
skips events that already have tags (from dedup).

Usage:  python3 retag_districts.py [--dry-run]
"""

import sys
import sqlite3
import re

DB = "stutensee_events.db"

# Full districts map — mirrors run_pipeline.py's DISTRICTS dict
DISTRICTS = {
    "Blankenloch": ["blankenloch", "bl.", "mehrgenerationenhaus", "bürgerwerkstatt", "seegrabenweg", "gymnasiumstr", "zukunftshaus"],
    "Büchig": ["büchig", "buechig"],
    "Friedrichstal": ["friedrichstal", "spöcker weg", "spoecker weg"],
    "Spöck": ["spöck", "spoeck"],
    "Staffort": ["staffort"],
    "Weingarten": ["weingarten", "weingarten (baden)", "mineralix-arena", "walzbachhalle"],
    "Hagsfeld": ["hagsfeld"],
    "Büchenau": ["büchenau", "buechenau"],
    "Neuthard": ["neuthard", "karlsdorf", "karlsdorf-neuthard", "zehntscheuer"],
    "Waldstadt": ["waldstadt", "bv-waldstadt"],
    "Eggenstein": ["eggenstein"],
    "Leopoldshafen": ["leopoldshafen"],
    "Rintheim": ["rintheim"],
    "Linkenheim": ["linkenheim", "linkenheim-hochstetten"],
    "Graben-Neudorf": ["graben-neudorf", "neudorf"],
    "Bruchsal": ["bruchsal"],
}


def main():
    dry_run = "--dry-run" in sys.argv

    conn = sqlite3.connect(DB)
    conn.row_factory = sqlite3.Row

    rows = conn.execute("SELECT id, title, location, organizer, description, tags FROM curated_events").fetchall()
    total = len(rows)
    updated = 0
    by_district = {}

    for r in rows:
        eid = r["id"]
        combined = f'{r["location"] or ""} {r["title"] or ""} {r["organizer"] or ""} {r["description"] or ""}'.lower()
        tag_list = [t.strip() for t in (r["tags"] or "").split(",") if t.strip()]
        changed = False

        for district_name, keywords in DISTRICTS.items():
            if district_name in tag_list:
                continue
            for kw in keywords:
                if re.search(re.escape(kw), combined):
                    tag_list.append(district_name)
                    by_district[district_name] = by_district.get(district_name, 0) + 1
                    changed = True
                    break

        if changed:
            new_tags = ",".join(tag_list)
            updated += 1
            if not dry_run:
                conn.execute(
                    "UPDATE curated_events SET tags = ?, updated_at = datetime('now') WHERE id = ?",
                    (new_tags, eid),
                )

    if not dry_run:
        conn.commit()

    conn.close()

    print(f"Total events checked: {total}")
    print(f"Events updated: {updated}")
    print()
    if updated > 0:
        print("By district:")
        for d in sorted(by_district.keys()):
            print(f"  {d}: {by_district[d]}")

    if dry_run:
        print()
        print("DRY RUN — no changes applied. Run without --dry-run to apply.")

    return updated


if __name__ == "__main__":
    count = main()
    print(f"\nDone. {count} events updated.")
