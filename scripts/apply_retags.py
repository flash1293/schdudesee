import json, sqlite3, os, sys

DB = "stutensee_events.db"
RESULTS_DIR = "retag_batches"

all_results = {}
for f in sorted(os.listdir(RESULTS_DIR)):
    if f.startswith("results_") and f.endswith(".json"):
        path = os.path.join(RESULTS_DIR, f)
        data = json.load(open(path))
        all_results.update(data["results"])
        print(f"Loaded {len(data['results'])} results from {f}")

print(f"\nTotal: {len(all_results)} events with new tags")

conn = sqlite3.connect(DB)
c = conn.cursor()

updated = 0
errors = 0
for eid_str, new_tags in all_results.items():
    eid = int(eid_str)
    c.execute("UPDATE curated_events SET tags = ? WHERE id = ?", (new_tags, eid))
    if c.rowcount != 1:
        print(f"Warning: event {eid} not found in DB")
        errors += 1
    updated += c.rowcount

conn.commit()

# Verify
count = c.execute("SELECT COUNT(*) FROM curated_events").fetchone()[0]
tagged = c.execute("SELECT COUNT(*) FROM curated_events WHERE tags != '' AND tags IS NOT NULL").fetchone()[0]
untagged = c.execute("SELECT COUNT(*) FROM curated_events WHERE tags = '' OR tags IS NULL").fetchone()[0]

# Tag distribution
tag_counts = {}
rows = c.execute("SELECT tags FROM curated_events WHERE tags != '' AND tags IS NOT NULL").fetchall()
for (tags_str,) in rows:
    for t in tags_str.split(","):
        t = t.strip()
        if t:
            tag_counts[t] = tag_counts.get(t, 0) + 1

tag_count_dist = {}
for (tags_str,) in rows:
    n = len([t for t in tags_str.split(",") if t.strip()])
    tag_count_dist[n] = tag_count_dist.get(n, 0) + 1

conn.close()

print(f"\nDB: {count} total events, {tagged} tagged, {untagged} untagged")
print(f"\nTag distribution (sorted by frequency):")
for t, n in sorted(tag_counts.items(), key=lambda x: -x[1]):
    print(f"  {t}: {n}")

print(f"\nNumber of tags per event:")
for n in sorted(tag_count_dist):
    print(f"  {n} tag(s): {tag_count_dist[n]} events")

print(f"\nUpdated: {updated}, Errors: {errors}")
