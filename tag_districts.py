import sqlite3
import re

DB_PATH = "/Users/joereuter/Clones/schdudesee/stutensee_events.db"

DISTRICTS = ["Blankenloch", "Büchig", "Friedrichstal", "Spöck", "Staffort"]

def build_patterns():
    patterns = {}
    for d in DISTRICTS:
        tokens = []
        dl = d.lower()
        tokens.append(re.escape(d))
        tokens.append(re.escape(d) + r"er")
        patterns[d] = re.compile("(" + "|".join(tokens) + ")", re.IGNORECASE)
    return patterns

def find_district(text, patterns):
    if not text:
        return None
    for d, pat in patterns.items():
        if pat.search(text):
            return d
    return None

def run():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()

    cur.execute("SELECT id, title, location, organizer, description, tags FROM curated_events")
    rows = cur.fetchall()
    total = len(rows)

    patterns = build_patterns()
    district_counts = {d: 0 for d in DISTRICTS}
    district_counts["Stutensee"] = 0
    no_match = 0
    updated = 0

    for row in rows:
        eid = row["id"]
        title = row["title"] or ""
        location = row["location"] or ""
        organizer = row["organizer"] or ""
        description = row["description"] or ""
        tags = row["tags"] or ""

        district = None
        location_is_city_level = False

        # Check location for district (highest priority)
        district = find_district(location, patterns)
        if not district and re.search(r'\bStutensee\b', location, re.IGNORECASE):
            location_is_city_level = True

        # Next: check title
        if not district:
            district = find_district(title, patterns)

        # If location was city-level (mentions "Stutensee" but no specific district)
        # and title didn't yield a district either, use "Stutensee" — don't fall
        # through to organizer/description which could match a club's district
        # for a non-district-specific event (e.g. city-wide festival organized
        # by a club from a specific district).
        if not district and location_is_city_level:
            district = "Stutensee"

        # Check organizer
        if not district:
            district = find_district(organizer, patterns)

        # Check description
        if not district:
            district = find_district(description, patterns)

        # Fallback: whole city
        if not district:
            district = "Stutensee"

        # Parse existing tags, add district if not present
        tag_list = [t.strip() for t in tags.split(",") if t.strip()]
        if district not in tag_list:
            tag_list.append(district)
            district_counts[district] = district_counts.get(district, 0) + 1
            new_tags = ",".join(tag_list)
            cur.execute(
                "UPDATE curated_events SET tags = ?, updated_at = datetime('now') WHERE id = ?",
                (new_tags, eid),
            )
            updated += 1
        else:
            # Already had this tag
            pass

    conn.commit()

    print("=== District Tagging Results ===")
    print(f"Total events: {total}")
    print(f"Events updated: {updated}")
    print()
    for d in DISTRICTS:
        print(f"  {d}: {district_counts.get(d, 0)}")
    print(f"  Stutensee (whole city): {district_counts.get('Stutensee', 0)}")
    print()

    # Quick verification
    cur.execute("SELECT id, title, tags FROM curated_events WHERE tags LIKE '%Stutensee%' LIMIT 5")
    print("Sample Stutensee-tagged events:")
    for r in cur.fetchall():
        print(f"  {r['id']}: {r['title'][:50]} -> {r['tags']}")

    conn.close()

if __name__ == "__main__":
    run()
