import json

with open('/tmp/tag_batch_4.json') as f:
    data = json.load(f)

events = data["events"]
results = []

tag_rules = [
    ("Eltern-Baby-Café", ["Kinder", "Treff"]),
    ("Eltern-Kind-Kreis", ["Kinder", "Treff", "Kirche"]),
    ("Jugendrotkreuz", ["Kinder", "Wohltätigkeit", "Verein"]),
    ("Wilde 13", ["Sport", "Kinder", "Verein"]),
    ("Korallengarde", ["Sport", "Kinder", "Verein"]),
    ("Krabbelgruppe Stutensee-Blankenloch", ["Kinder", "Treff"]),
    ("Krabbelgruppe im ev. Gemeindehaus Staffort", ["Kinder", "Treff", "Kirche"]),
    ("Krabbelgruppe in Spöck", ["Kinder", "Treff"]),
    ("Krabbelkäfer", ["Kinder", "Treff", "Essen"]),
    ("Kreativfreitag", ["Kinder", "Handwerk"]),
    ("Kükenstube", ["Kinder", "Kirche"]),
    ("Modellbahn-AG", ["Kinder", "Bildung", "Handwerk", "Verein"]),
    ("Pfadfinder", ["Kinder", "Natur", "Verein"]),
    ("Schach für Schüler", ["Kinder", "Bildung", "Verein"]),
    ("Seepferdchengarde", ["Sport", "Kinder", "Verein"]),
    ("Seesternchengarde", ["Sport", "Kinder", "Verein"]),
    ("Selbsthilfegruppe", ["Treff"]),
    ("Spiele-Treff", ["Treff"]),
    ("Tanzen für die Kleinsten", ["Sport", "Kinder"]),
    ("Tee- und Spielstube", ["Treff", "Wohltätigkeit"]),
    ("Teen Girls", ["Kinder", "Handwerk", "Treff"]),
]

import re

for event in events:
    event_id = event["id"]
    title = event["title"]
    tags = []
    for keyword, tag_list in tag_rules:
        if keyword in title:
            tags = tag_list
            break
    results.append({"id": event_id, "tags": tags})

output = {"batch_id": 4, "events": results}

with open('/tmp/tag_output_4.json', 'w') as f:
    json.dump(output, f, ensure_ascii=False, indent=2)

tagged = len([r for r in results if r["tags"]])
untagged = len([r for r in results if not r["tags"]])
print(f"Total events: {len(results)}")
print(f"Tagged: {tagged}")
print(f"Untagged: {untagged}")

# Verify all titles matched
matched_titles = set()
for event in events:
    title = event["title"]
    for keyword, _ in tag_rules:
        if keyword in title:
            matched_titles.add(title)
            break
all_titles = set(e["title"] for e in events)
unmatched = all_titles - matched_titles
if unmatched:
    print(f"Unmatched titles: {unmatched}")
else:
    print("All titles matched successfully")
