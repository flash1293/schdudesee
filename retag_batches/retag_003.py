import json
import re

DISTRICTS = {"Blankenloch", "Büchig", "Friedrichstal", "Spöck", "Staffort", "Weingarten"}

TAG_RULES = [
    ("Kirche", [r"gottesdienst", r"kirche", r"konfirmation", r"firmung", r"messfeier",
                r"andacht", r"patrozinium", r"taufe", r"gemeinde", r"ökumen",
                r"trauer", r"gebet", r"evangelisch", r"katholisch"]),
    ("Sport", [r"training", r"turnen", r"lauf", r"triathlon", r"tennis", r"fitness",
               r"yoga", r"pilates", r"volleyball", r"handball", r"basketball",
               r"fussball", r"fußball", r"sport", r"gymnastik", r"tanz", r"reiten",
               r"korallengarde", r"seepferdchengarde", r"seesternchengarde",
               r"schach", r"pfadfinder", r"wölflinge", r"wander"]),
    ("Kinder", [r"kind", r"baby", r"krabbel", r"spielgruppe", r"familie",
                r"kindergarten", r"jugend", r"jugendliche", r"teen", r"schüler",
                r"schüler", r"ferien", r"vorlesen", r"eltern", r"mutter"]),
    ("Musik", [r"konzert", r"chor", r"musik", r"band", r"singen", r"jazz", r"posaune",
               r"vox", r"flöte", r"gitarre", r"klavier", r"orchester"]),
    ("Fest", [r"fest", r"feier", r"maifest", r"oktoberfest", r"weihnachtsmarkt",
              r"kerwe", r"sommerfest", r"maihocke", r"maibaum", r"jubiläum"]),
    ("Markt", [r"flohmarkt", r"weihnachtsmarkt", r"trödel", r"markt"]),
    ("Essen", [r"kochen", r"backen", r"grill", r"hähnchen", r"kaffee", r"kuchen",
               r"frühstück", r"mittagstisch", r"abendessen", r"essen", r"imbiss",
               r"bratwurst"]),
    ("Treff", [r"treff", r"café", r"cafe", r"stammtisch", r"begegnung", r"runde",
               r"kaffeeklatsch", r"plauder"]),
    ("Workshop", [r"workshop", r"kurs", r"seminar"]),
    ("Bildung", [r"bildung", r"vortrag", r"lesung", r"schule", r"vhs",
                 r"infoveranstaltung", r"podium", r"integrationskurs", r"unterricht",
                 r"lernen"]),
    ("Natur", [r"natur", r"garten", r"vogel", r"baum", r"pflanze", r"umwelt",
               r"klima", r"exkursion", r"hornisse", r"insekt", r"biene"]),
    ("Digital", [r"digital", r"smartphone", r"computer", r"handy", r"online",
                 r"internetcafé", r"internetcafe", r"tablet"]),
    ("Handwerk", [r"basteln", r"werkstatt", r"nähen", r"stricken", r"häkeln",
                  r"reparatur", r"kreativ", r"modellbau"]),
    ("Verein", [r"mitgliederversammlung", r"vorstand", r"jahreshauptversammlung",
                r"e\.v\.", r"verein", r"vdk", r"hauptversammlung"]),
    ("Kultur", [r"theater", r"kunst", r"ausstellung", r"kino", r"literatur",
                r"museum", r"foto"]),
    ("Politik", [r"wahl", r"bürgermeister", r"gemeinderat", r"politik",
                 r"stadtrat"]),
    ("Wohltätigkeit", [r"spende", r"blutspende", r"kleidersammlung", r"sozial",
                       r"tafel", r"hilfe"]),
]

def get_content_tags(text):
    if not text:
        return []
    text_lower = text.lower()
    matched = []
    for tag_name, patterns in TAG_RULES:
        for p in patterns:
            if re.search(p, text_lower):
                matched.append(tag_name)
                break
    return matched

def main():
    with open("/Users/joereuter/Clones/schdudesee/retag_batches/chunk_003.json") as f:
        events = json.load(f)

    print(f"Loaded {len(events)} events")

    results = {}
    errors = []
    tag_counts = {}

    for e in events:
        eid = str(e["id"])
        title = e.get("title") or ""
        description = e.get("description") or ""
        organizer = e.get("organizer") or ""
        tags_str = e.get("tags") or ""

        current_tags = [t.strip() for t in tags_str.split(",") if t.strip()]
        district_tags = [t for t in current_tags if t in DISTRICTS]

        combined = f"{title} {description} {organizer}"
        content_tags = get_content_tags(combined)

        # Limit to max 2 content tags
        # Prioritize more specific tags over generic ones
        GENERIC = {"Verein", "Treff", "Sonstiges"}
        specific = [t for t in content_tags if t not in GENERIC]
        generic = [t for t in content_tags if t in GENERIC]
        ordered = specific + generic
        content_tags = ordered[:2]
        content_tags.sort()

        # If no content tags matched, assign Sonstiges
        if not content_tags:
            content_tags = ["Sonstiges"]

        all_tags = content_tags + district_tags
        results[eid] = ",".join(all_tags)

        for t in content_tags:
            tag_counts[t] = tag_counts.get(t, 0) + 1

    output = {"errors": errors, "results": results}

    with open("/Users/joereuter/Clones/schdudesee/retag_batches/results_003.json", "w") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)

    print(f"\nResults written to results_003.json")
    print(f"Events processed: {len(results)}")
    print(f"Errors: {len(errors)}")
    print(f"\nTag distribution:")
    for tag, count in sorted(tag_counts.items(), key=lambda x: -x[1]):
        print(f"  {tag}: {count}")

if __name__ == "__main__":
    main()
