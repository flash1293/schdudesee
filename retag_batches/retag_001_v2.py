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

# --- Strong direct patterns (checked first) ---
STRONG_PATTERNS = [
    # Sport
    (r"\b(sportabzeichen|stadtlauf|kinderlauf|spendenlauf|schülerlauf|lauftreff|walkingtreff|wanderung|wanderungen|wandertag|wanderwoche|bike|biken|radtour|radtouren|torwand|torwandschießen)\b", "Sport"),
    (r"\b(fußball|fussball|handball|basketball|volleyball|badminton|tischtennis|schnupperkurs\s+tennis|skikurs|skiwochenende|skilager)\b", "Sport"),
    (r"\b(turnen|eltern\-kind\-turnen|kinderturnen|turnen\s+für|geräteturnen|leistungsturnen|turnrat)\b", "Sport"),
    (r"\b(schwimmkurs|schwimmen|anfängerschwimmen|kinderschwimmen|wassergewöhnung|toben|bewegungslandschaft|bewegung\s+für)\b", "Kinder"),
    # The "toben" and "bewegungslandschaft" are children's movement play, should be Kinder
    # Actually re-check - let me be more precise
    (r"\b(erlebnisbad|wasserspielplatz)\b", "Kinder"),

    # Kultur
    (r"\b(autorenlesung|lesung|buchvorstellung|bilderbuchkino|bilderbuch\-kino|kamishibai|märchen|märchenstunde|vorlesestunde|vorlesen|geschichtenstunde)\b", "Kultur"),
    (r"\b(theater|theaterstück|theateraufführung|schattenspiel|puppentheater|mitspieltheater|improtheater|krimidinner)\b", "Kultur"),
    (r"\b(kino|filmabend|filmvorführung|dokumentation|dokumentarfilm)\b", "Kultur"),
    (r"\b(kunstausstellung|kunst|künstler|ausstellungseröffnung|vernissage|malerei|zeichnen|aquarell|fotografie|fotokurs)\b", "Kultur"),
    (r"\b(kabarett|comedy|kleinkunst|varieté|zirkus|zirkusprojekt|zirkusworkshop)\b", "Kultur"),

    # Musik
    (r"\b(konzert|klavierkonzert|weihnachtskonzert|frühlingskonzert|herbstkonzert|musikabend|gospelkonzert)\b", "Musik"),
    (r"\b(chor|singen|singkreis|gesang|sänger|sängerin|sing|gospelchor|popchor|kinderchor|jugendchor)\b", "Musik"),
    (r"\b(musikverein|musikkapelle|blasmusik|bläser|bläserkreis|posaunenchor|fanfarenzug|musikzug|spielmannszug|trommler|trommelkurs)\b", "Musik"),
    (r"\b(orchester|schulorchester|jugendorchester)\b", "Musik"),
    (r"\b(musikschule|musikalische\s+früherziehung|musikgarten|instrument|gitarre|gitarrenkurs|gitarrengruppe|blockflöte|flöten|flötengruppe)\b", "Musik"),

    # Kirche
    (r"\b(gottesdienst|wortgottesdienst|abendmahl|ökumenisch|ökumenischer|ökumene)\b", "Kirche"),
    (r"\b(kirchenkaffee|kirchencafé|gemeindecafé|krabbelgruppe|kükenstube|eltern\-kind\-gruppe|mütter)\b", "Kirche"),
    (r"\b(evangelisch|ev\.|katholisch|kath\.)\s+(kirchengemeinde|gemeindehaus|pfarrei|pfarramt|kirche)\b", "Kirche"),
    (r"\b(friedhof|bestattung|trauer|trauerbegleitung|trauercafé)\b", "Kirche"),
    (r"\b(kirche|kirchliche|christlich)\s", "Kirche"),
    (r"\b(andacht|segens|segen|gebet|beten|rosenkranz|meditation)\b", "Kirche"),
    (r"\b(jungschar|kindergottesdienst|kinderkirche|konfi|konfirmanden)\b", "Kirche"),

    # Kinder
    (r"\b(kinderflohmarkt|kindersachen|babyflohmarkt|baby\s+basar|kinderkleider|kinderschuhe|bücherflohmarkt)\b", "Markt"),
    (r"\b(ferienaktion|ferienprogramm|ferienspaß|ferienbetreuung|ferienfreizeit|kinderferien|jugendfreizeit)\b", "Kinder"),
    (r"\b(kinderfest|kinderparty|kindertag|weltkindertag|kinderfasching|kinderkarneval|kinderfastnacht)\b", "Kinder"),
    (r"\b(kinderkino|kinderfilm|kinderkultur|kinderkunst|kindermal|kindertheater|theater\s+für\s+kinder)\b", "Kultur"),
    (r"\b(kreativwerkstatt|kreativkurse\s+für\s+kinder|basteln|bastel|bastelspaß|bastelnachmittag|bastelaktion)\b", "Handwerk"),
    (r"\b(osterbasteln|weihnachtsbasteln|basteln\s+mit)\b", "Handwerk"),
    (r"\b(spiel|spielen|spielgruppe|spielplatz|spieleabend|spielefest|spielenachmittag|spieltag|spielfest)\b", "Kinder"),
    (r"\b(kindergeburtstag|geburtstagsfeier|kinderbetreuung|kinderhüten)\b", "Kinder"),
    (r"\b(waldkindergarten|waldschule|waldpädagogik|walderlebnis)\b", "Natur"),

    # Fest
    (r"\b(bürgerball|ball|ballnacht|maskenball|bunter\s+abend|partyabend|party|karnevalsparty|faschingsparty|weihnachtsfeier|weihnachtsparty|silvester|jahresfeier|sommerfest|frühlingsfest|herbstfest|dorfgemeinschaftsabend|dorfabend)\b", "Fest"),
    (r"\b(jubiläum|jubiläumsfeier|jubiläumsfest)\b", "Fest"),

    # Markt
    (r"\b(wochenmarkt|bauernmarkt|trödelmarkt|trödel\b|kunsthandwerkermarkt|adventsmarkt|ostermarkt|herbstmarkt|frühlingsmarkt|jahrmarkt)\b", "Markt"),

    # Bildung
    (r"\b(vortrag|vortragsreihe|infovortrag|informationsabend|informationsveranstaltung|infoveranstaltung|themenabend)\b", "Bildung"),
    (r"\b(vhs\b|volkshochschule|bildungswerk|akademie|bildungshaus)\b", "Bildung"),

    # Digital
    (r"\b(edv\b|pc\s+|computer|programmieren|coding|codier|roboter|robotic|ki\s|künstliche\s+intelligenz|chatgpt|digital|smartphone\s+treff|digitaltreff|digitales)\b", "Digital"),

    # Essen
    (r"\b(dampfnudel|kässpätzle|käsespätzle|schupfnudel|flädlesuppe|grillfest|grillen|bratwurst|wurstsalat|frühstück|brunch|schlemmen|kulinarisch|kochkurs|kochabend|backen|backkurs|backtag|brotbacken)\b", "Essen"),
    (r"\b(kaffeetrinken|kaffeetreff|kaffee\s+treff|kaffeeklatsch|kuchenbuffet|kuchenbasar)\b", "Essen"),

    # Natur
    (r"\b(waldspaziergang|naturspaziergang|kräuter|kräuterwanderung|kräuterspaziergang|naturerlebnis|naturführung|vogel|vögel|vogelkunde|insekten|bienen|imker)\b", "Natur"),
    (r"\b(gartenarbeit|gartenaktion|gartentag|gartenfest|gartenpflege|kleingarten|schrebergarten)\b", "Natur"),

    # Senioren
    (r"\b(seniorennachmittag|seniorenkreis|seniorentreff|seniorenclub|seniorenausflug|seniorenfeier|seniorenarbeit)\b", "Senioren"),

    # Handwerk
    (r"\b(reparaturtreff|reparatur|näh|nähen|nähkurs|stricken|strick|häkeln|handarbeit|handarbeiten|stricktreff)\b", "Handwerk"),

    # Verein
    (r"\b(mitgliederversammlung|jahreshauptversammlung|hauptversammlung|vorstandssitzung|vorstandschaft|vorstand\+|vorstand\b.*(?:sitzung|wahl)|mitgliedsversammlung)\b", "Verein"),
    (r"\b(abteilungsleitung|abteilungsleiter|abteilungsversammlung|turnrat|vereinsrat)\b", "Verein"),
    (r"\b(arbeitseinsatz|arbeitsdienst|vereinsarbeit|ehrenamt|ehrenamtstreffen|förderverein)\b", "Verein"),

    # Wohltätigkeit
    (r"\b(blutspende|blutspendetermin|spendenlauf|spendenaktion|spendensammlung|karitativ)\b", "Wohltätigkeit"),

    # Treff (using this sparingly now)
    (r"\b(stammtisch|stammtischtreffen)\b", "Treff"),
]

def strong_match(text):
    """Check strong patterns first - these override generic keyword matching"""
    for pattern, tag in STRONG_PATTERNS:
        if re.search(pattern, text, re.IGNORECASE):
            return tag
    return None

# --- Generic keyword patterns for fallback ---
GENERIC_PATTERNS = [
    ("Kirche", r"\b(kirche|kirchengemeinde|gottesdienst|gemeindehaus|evangelisch|katholisch|pfarrei|seelsorge)\b"),
    ("Sport", r"\b(sport|turnen|gymnastik|trainings|trainiert|sportgruppe|sportverein|yoga|pilates|fitness)\b"),
    ("Kinder", r"\b(kinder|kinder|jugendliche|kids|jugend|eltern|familie)\b"),
    ("Musik", r"\b(musik|sing|chor|orchester|konzert|instrument|gitarre|klavier|flöte)\b"),
    ("Fest", r"\b(fest|feier|feiern|party)\b"),
    ("Kultur", r"\b(kultur|lesung|ausstellung|museum|kunst|theater|kino|film)\b"),
    ("Natur", r"\b(natur|wald|garten|pflanze|tier|vogel|kräuter)\b"),
    ("Essen", r"\b(essen|kochen|frühstück|kuchen|brot|grill)\b"),
    ("Bildung", r"\b(bildung|vortrag|kurs|seminar|schulung|fortbildung|vhs)\b"),
    ("Workshop", r"\b(workshop|workshops)\b"),
    ("Handwerk", r"\b(handwerk|basteln|werkstatt|töpfern)\b"),
    ("Digital", r"\b(digital|computer|pc|edv|programmieren|roboter|smartphone)\b"),
    ("Senioren", r"\b(senioren|rentner|ältere)\b"),
    ("Markt", r"\b(markt|flohmarkt|basar|trödel)\b"),
    ("Politik", r"\b(politik|gemeinderat|bürger|wahl)\b"),
    ("Verein", r"\b(verein|vorstand|mitglieder)\b"),
    ("Wohltätigkeit", r"\b(spende|karitativ|sozial|hilfe)\b"),
    ("Treff", r"\b(treff|stammtisch|gesellig)\b"),
]

def classify_event(title, description, organizer, location):
    text = f"{title} {description}".lower()
    full = f"{title} {description} {organizer} {location}".lower()

    # Phase 1: Strong direct patterns
    strong = strong_match(f"{title} {description}")
    if strong:
        return [strong]

    # Phase 2: Keyword scoring
    scores = {}
    for tag, pattern in GENERIC_PATTERNS:
        matches = re.findall(pattern, text)
        if matches:
            scores[tag] = len(matches)

    if not scores:
        return ["Sonstiges"]

    # Find top scoring tags
    sorted_scores = sorted(scores.items(), key=lambda x: -x[1])
    top_score = sorted_scores[0][1]
    
    result = []
    for tag, score in sorted_scores:
        if len(result) >= 2:
            break
        if score == top_score:
            result.append(tag)
    
    # If 2 tied for top, that's fine. If only 1 top, add second if clearly present
    if len(result) == 1:
        for tag, score in sorted_scores[1:]:
            if score >= top_score * 0.7 and len(result) < 2:
                if tag not in result:
                    result.append(tag)
                break

    if not result:
        result = ["Sonstiges"]

    # Special: "Spiel" + "Kinder" -> prefer Kinder if both match
    if "Sport" in result and "Kinder" in scores:
        # Check if sport words are actually about children
        if re.search(r"\b(kinder|kind|jugend|eltern)\b", text):
            pass  # Keep both if relevant
    # Don't have Kinder+Sport unless both are strong
    # Actually, keep both - it's fine

    # Special: if "Kinder" is the top tag and "Kirche" also matches, that's fine
    # but don't over-tag

    return result


results = {}
errors = []

for i, event in enumerate(events):
    try:
        eid = str(event["id"])
        title = event.get("title", "")
        description = event.get("description", "")
        organizer = event.get("organizer", "")
        location = event.get("location", "")

        combined = f"{title} {description} {organizer} {location}"
        district_tags = extract_district_tags(combined)

        existing_tags = event.get("tags", "")
        if existing_tags:
            for tag in existing_tags.split(","):
                tag = tag.strip()
                if tag in DISTRICTS:
                    district_tags.add(tag)

        content_tags = classify_event(title, description, organizer, location)

        # Clean Verein - only if truly about club activities
        if "Verein" in content_tags:
            txt = f"{title} {description}".lower()
            is_really_verein = bool(re.search(r"\b(mitgliederversammlung|jahreshauptversammlung|vorstand|abteilungsleitung|turnrat|arbeitseinsatz|vereinsarbeit|hauptversammlung|mitgliedsversammlung|ehrenamt|förderverein)\b", txt))
            if not is_really_verein:
                content_tags = [t for t in content_tags if t != "Verein"]

        # Clean Treff - only if primary purpose IS social gathering
        if "Treff" in content_tags and len(content_tags) > 1:
            # If there's another meaningful tag, Treff is probably not the primary
            other_tags = [t for t in content_tags if t != "Treff"]
            # Only keep Treff if the other tags are weaker
            content_tags = other_tags

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
