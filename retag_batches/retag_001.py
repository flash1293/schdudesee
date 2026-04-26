import json
import re

with open("/Users/joereuter/Clones/schdudesee/retag_batches/chunk_001.json", "r") as f:
    events = json.load(f)

DISTRICTS = {"Blankenloch", "Büchig", "Friedrichstal", "Spöck", "Staffort"}
DISTRICT_PATTERNS = {
    "Blankenloch": r"\bblankenloch\b",
    "Büchig": r"\bbüchig\b",
    "Friedrichstal": r"\bfriedrichstal\b",
    "Spöck": r"\bspöck\b(?!er\s+weg)",
    "Staffort": r"\bstaffort\b",
}

def extract_district_tags(text):
    found = set()
    for district, pattern in DISTRICT_PATTERNS.items():
        if re.search(pattern, text, re.IGNORECASE):
            found.add(district)
    return found

def classify_event(title, description, organizer, location):
    t = f"{title} {description} {organizer} {location}".lower()
    te = f"{title} {description}".lower()

    scores = {}

    # Sport - physical activity, sports clubs, exercise
    sport_pat = r"\b(sport|turnen|gymnastik|radfahren|radtour|fußball|fussball|handball|basketball|volleyball|tennis|tischtennis|badminton|schwimmen|tanzen|tanzkurs|yoga|pilates|fitness|wander|joggen|laufen|fechten|rudern|reiten|kegeln|wandern|wanderung|radeln|radtour|walken|aerobic|zumba|bouldern|klettern|sportkurs|sportgruppe|sportverein|sporttag|sportfest|bewegung|sportlich|tanz|tänze|tanzt)\b"
    scores["Sport"] = len(re.findall(sport_pat, te))

    # Musik - music, concerts, singing
    musik_pat = r"\b(musik|konzert|singen|gesang|chor|orchester|band|gitarre|klavier|flöte|floete|schlagzeug|musizieren|musikalisch|lieder|blasmusik|sing|sänger|sängerin|konzerte|musikverein|musikschule|bläser|bläserkreis|posaunenchor|akkordeon|gospel|popchor)\b"
    scores["Musik"] = len(re.findall(musik_pat, te))

    # Kirche - church services, religious events
    kirche_pat = r"\b(kirche|gottesdienst|evangelisch|katholisch|gemeindehaus|kindergarten|kommunion|firmung|taufe|trauung|seelsorge|gebet|andacht|predigt|kirchen|gemeinde|kirchengemeinde|kükenstube|krabbelgruppe|christen|christlich|religion|religiös|ökumenisch|öku)(?:s|n|r|m)?\b"
    scores["Kirche"] = len(re.findall(kirche_pat, te))

    # Kinder - children-specific events
    kinder_pat = r"\b(kinder|kind|jugend|kids|familie|eltern|baby|babys|spiel|spielen|vorlesen|basteln|malen|kindertag|kinderfest|kinderprogramm|jugendliche|ferien|ferienprogramm|kindergarten|krabbelgruppe|spielgruppe|kindersport|kinderturnen|kindertheater|kinderchor|kinderflohmarkt|kinderkleider|spielplatz|jungschar|kindergottesdienst|kinderkirche|teen|teens|schüler)\b"
    scores["Kinder"] = len(re.findall(kinder_pat, te))

    # Fest - festivals, celebrations
    fest_pat = r"\b(fest|feier|jubiläum|jahreshauptversammlung|jahresfeier|weihnachtsfeier|sommerfest|straßenfest|stadtfest|dorfgemeinschaft|maifest|erntedank|faschings|karneval|fastnacht|party|abend|ball|bürgerfest|vereinsfest|grillfest|frühschoppen|zeltfest|kerwe|kirchweih|oktoberfest|weinfest|schützenfest|musikfest|sportfest|kinderfest)\b"
    scores["Fest"] = len(re.findall(fest_pat, te))

    # Markt - markets, flea markets
    markt_pat = r"\b(markt|flohmarkt|wochenmarkt|weihnachtsmarkt|trödel|trödelmarkt|basar|verkauf|verkaufs|kunsthandwerk|handwerkermarkt|bauernmarkt|adventsmarkt)\b"
    scores["Markt"] = len(re.findall(markt_pat, te))

    # Workshop - hands-on learning, making
    workshop_pat = r"\b(workshop|kurs|seminar|schulung|fortbildung|lehrgang|training|unterricht|stricken|häkeln|nähen|kochen|backen|töpfern|schnitzen|werkstatt|selbermachen|selbst|anleitung|lern|vhs|volkshochschule)\b"
    scores["Workshop"] = len(re.findall(workshop_pat, te))

    # Bildung - education, lectures, learning
    bildung_pat = r"\b(bildung|vortrag|vorlesung|lesung|referat|diskussion|vhs|volkshochschule|ausstellung|museum|führung|führungen|schule|schulung|studium|wissen|bildungswerk|akademie|vortragsreihe|infoveranstaltung|informationsabend|unterricht)\b"
    scores["Bildung"] = len(re.findall(bildung_pat, te))

    # Natur - nature, outdoor
    natur_pat = r"\b(natur|garten|wald|wiese|park|see|fluss|radtour|wandern|wanderung|vogel|pflanze|baum|blume|gärtnern|gartenschau|kleingarten|umwelt|klima|nachhaltigkeit|biologisch|öko|naturkunde|naturschutz|ausflug|exkursion|frühling|herbst|jagd|angeln|imker|bienen|schmetterling|wild|pflücken)\b"
    scores["Natur"] = len(re.findall(natur_pat, te))

    # Senioren - senior-specific
    senioren_pat = r"\b(senior|rentner|altersheim|pflegeheim|betreutes|wohnen\s+im\s+alter|alte\s+menschen|ältere|generationen|nachmittag|seniorenkreis|seniorennachmittag)\b"
    scores["Senioren"] = len(re.findall(senioren_pat, te))

    # Digital - tech, computers
    digital_pat = r"\b(digital|computer|laptop|software|app|internet|online|programmieren|coding|roboter|ki|künstliche\s+intelligenz|smartphone|tablet|social\s+media|webseite|homepage|e-mail|email|it\b|edv|pc\b|technik|technologie)\b"
    scores["Digital"] = len(re.findall(digital_pat, te))

    # Handwerk - crafts/trades
    handwerk_pat = r"\b(handwerk|schreiner|tischler|klempner|elektriker|mauer|zimmer|handwerker|basteln|werken|werkeln|selber\s+machen|heimwerken|renovieren|reparieren)\b"
    scores["Handwerk"] = len(re.findall(handwerk_pat, te))

    # Essen - food, cooking
    essen_pat = r"\b(essen|kochen|backen|frühstück|brunch|mittagessen|abendessen|grillen|grill|kulinarisch|küche|lecker|brot|kuchen|torte|bier|wein|wurst|salat|suppe|kochkurs|kochabend|schlemmen|genießen|geniessen|speise|buffet|imbiss|verpflegung)\b"
    scores["Essen"] = len(re.findall(essen_pat, te))

    # Politik - political events
    politik_pat = r"\b(politik|politiker|gemeinderat|stadtrat|bürgermeister|wahl|wahlen|demonstration|kundgebung|parlament|partei|bürger|bürgerschaft|bürgerbeteiligung|kommunal|landtag|bundestag|fraktion|ausschuss|sitzung|bürgerversammlung|bürgerinfo|bürgerinformations|gemeinderatssitzung|ortsbeirat)\b"
    scores["Politik"] = len(re.findall(politik_pat, te))

    # Verein - club/association activities
    verein_pat = r"\b(verein|vereins|mitgliederversammlung|jahreshauptversammlung|vorstand|vereinsheim|clubheim|clubhaus|e\.v\.|vereinsleben|vereinsarbeit|vereinsgründung|ehrenamt|förderverein|mitgliedsversammlung|hauptversammlung)\b"
    scores["Verein"] = len(re.findall(verein_pat, te))

    # Wohltätigkeit - charity
    wohltätigkeit_pat = r"\b(wohltätigkeit|wohltätig|spende|spenden|karitativ|caritas|diakonie|sozial|soziales|sozialverein|hilfe|hilfs|unterstützung|tierheim|tierschutz|obdachlosen|armut|benachteiligt|sozialstation|sozialverband)\b"
    scores["Wohltätigkeit"] = len(re.findall(wohltätigkeit_pat, te))

    # Treff - social gathering (be selective)
    treff_pat = r"\b(treff|treffen|stammtisch|gesellig|beisammensein|zusammenkunft|frühstückstreff|seniorentreff|nachbarschaftstreff|begegnung|café\s+treff|cafer|komm\s+und\s+triff|offener\s+treff)\b"
    scores["Treff"] = len(re.findall(treff_pat, te))

    # Kultur - general culture
    kultur_pat = r"\b(kultur|theater|kino|film|bühne|schauspiel|literatur|märchen|ausstellung|museum|kunst|künstler|kreativ|fotografie|malerei|zeichnen|graffiti|performance|kabarett|comedy|kleinkunst|varieté|zirkus|museum|lesung|vernissage|kunstwerk)\b"
    scores["Kultur"] = len(re.findall(kultur_pat, te))

    return scores

def get_top_tags(scores, min_score=1):
    tags = []
    sorted_tags = sorted(scores.items(), key=lambda x: -x[1])
    for tag, score in sorted_tags:
        if score >= min_score:
            tags.append(tag)
    return tags

results = {}
errors = []

for i, event in enumerate(events):
    try:
        eid = str(event["id"])
        title = event.get("title", "")
        description = event.get("description", "")
        organizer = event.get("organizer", "")
        location = event.get("location", "")

        # Extract district tags from combined text
        combined = f"{title} {description} {organizer} {location}"
        district_tags = extract_district_tags(combined)

        # Also check existing tags for districts
        existing_tags = event.get("tags", "")
        if existing_tags:
            for tag in existing_tags.split(","):
                tag = tag.strip()
                if tag in DISTRICTS:
                    district_tags.add(tag)

        # Classify content
        scores = classify_event(title, description, organizer, location)

        # Get top tags - use a threshold approach
        scored = [(tag, score) for tag, score in scores.items() if score > 0]
        scored.sort(key=lambda x: -x[1])

        content_tags = []
        if scored:
            top_score = scored[0][1]
            # Take all tags with top_score, but at most 2
            for tag, score in scored:
                if score == top_score and len(content_tags) < 2:
                    content_tags.append(tag)
                elif score > 0 and len(content_tags) < 2:
                    content_tags.append(tag)
                    break

            # If no clear winner, just take the top one
            if not content_tags and scored:
                content_tags.append(scored[0][0])

        # Special logic for overused tags
        # "Treff" - only if primary purpose IS social gathering and no stronger tag
        if "Treff" in content_tags:
            stronger_tags = [t for t in content_tags if t != "Treff" and scores.get(t, 0) >= scores.get("Treff", 0)]
            if len(stronger_tags) > 1 or (len(stronger_tags) == 1 and scores["Treff"] <= scores[stronger_tags[0]]):
                content_tags = [t for t in content_tags if t != "Treff"]

        # "Verein" - only if event is about club activities, not just organized by a club
        if "Verein" in content_tags:
            # Check if it's really about a club meeting
            txt = f"{title} {description}".lower()
            is_really_verein = bool(re.search(r"\b(mitgliederversammlung|jahreshauptversammlung|vorstandssitzung|vereinsleben|vereinsarbeit|hauptversammlung|mitgliedsversammlung|ehrenamt|förderverein)\b", txt))
            if not is_really_verein and "Verein" in content_tags:
                # It's likely just organized by a club, not ABOUT the club
                content_tags = [t for t in content_tags if t != "Verein"]

        # Kitchen/backen events: prefer Essen over Workshop if food focus
        if "Workshop" in content_tags and "Essen" in content_tags:
            txt = f"{title} {description}".lower()
            food_focus = re.search(r"\b(kochen|backen|koch|back|frühstück|brunch|grill|essen|lecker|kuchen|brot)\b", txt)
            workshop_focus = re.search(r"\b(workshop|kurs|seminar|workshop)\b", txt)
            if food_focus and not workshop_focus:
                content_tags = ["Essen"]
            elif food_focus and workshop_focus:
                content_tags = ["Essen", "Workshop"]

        # No tags found
        if not content_tags:
            content_tags = ["Sonstiges"]

        # Combine content + district tags
        all_tags = content_tags + sorted(district_tags)
        results[eid] = ",".join(all_tags)

    except Exception as e:
        errors.append({"id": event.get("id"), "error": str(e)})

output = {
    "errors": errors,
    "results": results
}

with open("/Users/joereuter/Clones/schdudesee/retag_batches/results_001.json", "w") as f:
    json.dump(output, f, indent=2, ensure_ascii=False)

total = len(events)
done = len(results)
error_count = len(errors)
print(f"Processed {done}/{total} events. {error_count} errors.")
