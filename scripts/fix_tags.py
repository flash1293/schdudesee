import sqlite3
import re

DBPATH = "/Users/joereuter/Clones/schdudesee/stutensee_events.db"

DISTRICTS = {"Blankenloch", "Büchig", "Friedrichstal", "Spöck", "Staffort", "Weingarten"}

TAG_RULES = [
    ("Kirche", [r"gottesdienst", r"kirche", r"konfirmation", r"firmung", r"messfeier",
                r"andacht", r"patrozinium", r"taufe", r"gemeinde", r"ökumen",
                r"trauer", r"gebet"]),
    ("Sport", [r"training", r"turnen", r"lauf", r"triathlon", r"tennis", r"fitness",
               r"yoga", r"pilates", r"volleyball", r"handball", r"basketball",
               r"fussball", r"fußball", r"sport", r"gymnastik", r"tanz", r"reiten",
               r"korallengarde", r"seepferdchengarde"]),
    ("Kinder", [r"kind", r"baby", r"krabbel", r"spielgruppe", r"familie",
                r"kindergarten", r"jugend", r"teen", r"schüler", r"ferien",
                r"vorlesen", r"eltern"]),
    ("Musik", [r"konzert", r"chor", r"musik", r"band", r"singen", r"jazz", r"posaune",
               r"vox"]),
    ("Fest", [r"fest", r"feier", r"maifest", r"oktoberfest", r"weihnachtsmarkt",
              r"kerwe", r"sommerfest", r"maihocke", r"maibaum"]),
    ("Markt", [r"flohmarkt", r"weihnachtsmarkt", r"trödel"]),
    ("Essen", [r"kochen", r"backen", r"grill", r"hähnchen", r"kaffee", r"kuchen",
               r"frühstück", r"mittagstisch", r"abendessen"]),
    ("Treff", [r"treff", r"café", r"cafe", r"stammtisch", r"begegnung", r"runde",
               r"kaffeeklatsch"]),
    ("Workshop", [r"workshop", r"kurs", r"seminar"]),
    ("Bildung", [r"bildung", r"vortrag", r"lesung", r"schule", r"vhs",
                 r"infoveranstaltung", r"podium", r"integrationskurs"]),
    ("Natur", [r"natur", r"garten", r"vogel", r"baum", r"pflanze", r"umwelt",
               r"klima", r"exkursion", r"hornisse"]),
    ("Digital", [r"digital", r"smartphone", r"computer", r"handy", r"online",
                 r"internetcafé", r"internetcafe"]),
    ("Handwerk", [r"basteln", r"werkstatt", r"nähen", r"stricken", r"häkeln",
                  r"reparatur", r"kreativ"]),
    ("Verein", [r"mitgliederversammlung", r"vorstand", r"jahreshauptversammlung",
                r"e\.v\.", r"verein", r"vdk"]),
    ("Kultur", [r"theater", r"kunst", r"ausstellung", r"kino", r"literatur"]),
    ("Politik", [r"wahl", r"bürgermeister", r"gemeinderat", r"politik"]),
    ("Wohltätigkeit", [r"spende", r"blutspende", r"kleidersammlung", r"sozial",
                       r"tafel"]),
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
    conn = sqlite3.connect(DBPATH)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()

    rows = c.execute("SELECT id, title, description, location, organizer, tags FROM curated_events").fetchall()
    changed = 0
    stats = {}
    no_match = 0

    for row in rows:
        eid = row["id"]
        title = row["title"] or ""
        description = row["description"] or ""
        organizer = row["organizer"] or ""

        current_tags_str = row["tags"] or ""
        current_tags = [t.strip() for t in current_tags_str.split(",") if t.strip()]

        district_tags = [t for t in current_tags if t in DISTRICTS]

        combined = f"{title} {description} {organizer}"
        content_tags = get_content_tags(combined)

        content_tags = content_tags[:2]
        content_tags.sort()

        new_tags = content_tags + district_tags
        new_tags_str = ",".join(new_tags)

        old_tags_set = set(current_tags)
        new_tags_set = set(new_tags)
        if old_tags_set != new_tags_set or len(current_tags) != len(new_tags):
            c.execute("UPDATE curated_events SET tags = ? WHERE id = ?", (new_tags_str, eid))
            changed += 1

        for t in content_tags:
            stats[t] = stats.get(t, 0) + 1
        if not content_tags and not district_tags:
            no_match += 1

    conn.commit()
    conn.close()

    print(f"Total events processed: {len(rows)}")
    print(f"Events updated: {changed}")
    print(f"Events with no content tags: {no_match}")
    print("\nTag distribution (content tags only):")
    for tag, count in sorted(stats.items(), key=lambda x: -x[1]):
        print(f"  {tag}: {count}")

if __name__ == "__main__":
    main()
