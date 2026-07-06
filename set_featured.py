#!/usr/bin/env python3
"""
set_featured.py — Set exactly 4 events as featured for the Stutensee frontend.

Usage:
    python3 set_featured.py <id1> <id2> <id3> <id4> [--force]

Safety checks:
    - Exactly 4 IDs required
    - Each ID must exist in curated_events
    - Each ID must match at least one of the 5 OG Stutensee districts
      (Blankenloch, Friedrichstal, Spöck, Staffort, Büchig) via tags or location
    - Use --force to skip the district check (for manually verified edge cases)
    - Reports which events were previously featured and are being replaced

DB path: /shared/work/stutensee_events.db
"""

import sqlite3
import sys

DB_PATH = "/shared/work/stutensee_events.db"
DISTRICTS = ["Blankenloch", "Friedrichstal", "Spöck", "Staffort", "Büchig"]


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    force = "--force" in sys.argv

    if len(args) != 4:
        print(f"ERROR: Expected exactly 4 event IDs, got {len(args)}")
        print(f"Usage: python3 set_featured.py <id1> <id2> <id3> <id4> [--force]")
        sys.exit(1)

    try:
        ids = [int(a) for a in args]
    except ValueError:
        print("ERROR: All arguments must be numeric event IDs.")
        sys.exit(1)

    if len(set(ids)) != 4:
        print("ERROR: Duplicate IDs detected. All 4 IDs must be distinct.")
        sys.exit(1)

    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    # --- Validate all 4 IDs exist ---
    errors = []
    validated = []
    for eid in ids:
        cur.execute(
            "SELECT id, title, tags, date_start, location FROM curated_events WHERE id = ? AND is_passed = 0 AND tags != 'blocked'",
            (eid,),
        )
        row = cur.fetchone()
        if row is None:
            # Distinguish: not found vs filtered out by is_passed/blocked
            cur.execute("SELECT id FROM curated_events WHERE id = ?", (eid,))
            if cur.fetchone():
                errors.append(f"ID {eid}: exists but is either already passed or blocked — cannot feature")
            else:
                errors.append(f"ID {eid}: not found in database")
            continue

        tags = row[2] or ""
        location = row[4] or ""

        # Word-boundary match against comma-separated tags.
        # Substring matching is dangerous: "Büchig" ⊆ "Dürrenbüchig" (a Bretten district,
        # not Stutensee-Büchig). Split on commas to avoid false positives.
        # Location uses substring matching — locations are free text, not structured.
        tag_tokens = [t.strip() for t in tags.split(",") if t.strip()]
        district_match = [
            d for d in DISTRICTS
            if d in tag_tokens or d in location
        ]

        if not force and not district_match:
            errors.append(
                f"ID {eid} ({row[1][:50]}): neither tags '{tags}' nor location match "
                f"any Stutensee district. Use --force to override."
            )
            continue

        validated.append(
            {
                "id": eid,
                "title": row[1],
                "tags": tags,
                "district": district_match or ["(forced)"],
                "date": row[3],
                "location": location,
            }
        )

    if errors:
        print("VALIDATION FAILED:")
        for e in errors:
            print(f"  ❌ {e}")
        sys.exit(1)

    if force:
        print("⚠️  --force active: district check bypassed for non-matching IDs.\n")

    # --- Show what's about to change ---
    cur.execute("SELECT id, title, tags, date_start FROM curated_events WHERE featured = 1")
    previously_featured = cur.fetchall()

    if previously_featured:
        print("Currently featured (will be cleared):")
        for pf in previously_featured:
            print(f"  🔄 [{pf[0]}] {pf[1][:60]} | tags={pf[2]} | date={pf[3]}")
    else:
        print("Currently featured: (none)")

    print("\nNew featured events:")
    for v in validated:
        print(
            f"  ⭐ [{v['id']}] {v['title'][:60]} | district={v['district']} | date={v['date']}"
        )

    # --- Execute ---
    cur.execute("UPDATE curated_events SET featured = 0 WHERE featured = 1")
    cleared = cur.rowcount
    print(f"\nCleared featured flag from {cleared} event(s).")

    for eid in ids:
        cur.execute("UPDATE curated_events SET featured = 1 WHERE id = ?", (eid,))

    conn.commit()
    print(f"Set featured=1 on {len(ids)} event(s). ✅")

    # --- Verify ---
    cur.execute("SELECT COUNT(*) FROM curated_events WHERE featured = 1")
    final_count = cur.fetchone()[0]
    print(f"Featured count post-update: {final_count}")

    conn.close()


if __name__ == "__main__":
    main()
