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

# Patterns: carefully crafted for German compound words.
# IMPORTANT: no trailing \b to match compounds like "Abschiedskonzert", "Dampfnudeltag".
# Leading \b ensures we don't match mid-word substrings.
# Longer patterns first to avoid partial matches.

CONTENT_RULES = [
    ("Kirche", [
        r"\b(kirchen|kirche|kirchlich)\b",
        r"\b(gottesdienst|wortgottesdienst|abendmahl|abendmahlsfeier|ökumene|ökumenisch|ökumenischer)\b",
        r"\b(evangelisch|ev\.)\s+(kirchengemeinde|gemeindehaus|pfarrei|pfarramt)\b",
        r"\b(katholisch|kath\.)\s+(kirchengemeinde|gemeindehaus|pfarrei|pfarramt)\b",
        r"\b(krabbelgruppe|kükenstube|müttergruppe|eltern\-baby\-treff|eltern\-baby\-café)\b",
        r"\b(kindergarten|kiga)\b",
        r"\b(kirchenkaffee|kirchencafé|gemeindecafé)\b",
        r"\b(andacht|segen|segnung|gebet|beten|rosenkranz|meditation|stille)\b",
        r"\b(jungschar|kindergottesdienst|kinderkirche|konfirmanden|konfi)\b",
        r"\b(liebenzeller\s+gemeinschaft)\b",
        r"\b(taufe|taufen|firmung|firmung|trauung|bestattung|trauerfeier|trauerbegleitung|trauercafé)\b",
        r"\b(patrozinium|patroziniumsfest)\b",
        r"\b(frauenabend)\s+.*(seele|glaube|gott)\b",
    ]),
    ("Kinder", [
        r"\b(kinderflohmarkt|kindersachen|babyflohmarkt|bücherflohmarkt\s+für\s+kinder)\b",
        r"\b(ferienaktion|ferienprogramm|ferienspaß|ferienbetreuung|ferienfreizeit|kinderferien|jugendfreizeit)\b",
        r"\b(kinderfest|kinderparty|kindertag|weltkindertag|kinderfasching|kinderkarneval)\b",
        r"\b(kinderkleider|kinderschuhe|babybasar)\b",
        r"\b(kindergeburtstag|kinderbetreuung|kinderhüten)\b",
        r"\b(teen\s+girls|teen\s+club|mädchen|jungschar)\b",
        r"\b(bildschirmfrei|ohne\s+bildschirm)\s+.*(schüler|kinder|klasse)\b",
        r"\b(babys\s+in\s+bewegung)\b",
        r"\b(familiensamstag|familienausflug|familiennachmittag)\b",
        r"\b(kinder|kind|kids|jugendliche|jugend|eltern)\s+(ab\s+\d|ab\s+klasse|für\s+schüler|für\s+kinder)\b",
    ]),
    ("Sport", [
        r"\b(fußball|fussball|handball|basketball|volleyball|badminton|tischtennis)\b",
        r"\b(stadtlauf|kinderlauf|schülerlauf|spendenlauf|lauftreff|walkingtreff)\b",
        r"\b(sportabzeichen|sportfest|sporttag|sportwoche)\b",
        r"\b(turnen|geräteturnen|leistungsturnen|turnrat|eltern\-kind\-turnen|kinderturnen)\b",
        r"\b(skikurs|skiwochenende|skilager|skifahren|ski)\b",
        r"\b(schwimmkurs|schwimmen|anfängerschwimmen|kinderschwimmen|wassergewöhnung)\b",
        r"\b(radtour|radtouren|radfahren|bike|biken|wanderung|wanderungen|wandertag|wanderwoche)\b",
        r"\b(wanderpreis|wanderpokal)\b",
        r"\b(rundenwettkämpfe|rundenwettkampf)\b",
        r"\b(wachdienst)\b",
        r"\b(sport|sportlich)\s",
        r"\b(fechten|rudern|reiten|kegeln|bouldern|klettern|zumba|aerobic)\b",
        r"\b(kajak|kanu|paddeln)\b",
        r"\b(torwand|torwandschießen)\b",
    ]),
    ("Musik", [
        r"\b(abschiedskonzert|konzert|weihnachtskonzert|frühlingskonzert|herbstkonzert|gospelkonzert|klavierkonzert)\b",
        r"\b(musikabend|musikalisch|musikverein|musikkapelle|musikschule|musikgarten)\b",
        r"\b(chor|gospelchor|popchor|kinderchor|jugendchor|singkreis|gesangverein)\b",
        r"\b(sänger|sängerin|sängerfest|sängerkreis|singen)\b",
        r"\b(blasmusik|bläser|bläserkreis|posaunenchor|fanfarenzug|musikzug|spielmannszug)\b",
        r"\b(orchester|schulorchester|jugendorchester)\b",
        r"\b(gitarre|gitarrenkurs|gitarrengruppe|blockflöte|flöten|flötengruppe|klavier|schlagzeug)\b",
        r"\b(musikalische\s+früherziehung|musikgarten)\b",
        r"\b(trommeln|trommelkurs|trommler|djembé)\b",
    ]),
    ("Fest", [
        r"\b(bürgerball|ball|maskenball|bunter\s+abend)\b",
        r"\b(jubiläum|jubiläumsfeier|jubiläumsfest)\b",
        r"\b(sommerfest|frühlingsfest|herbstfest|weihnachtsfeier|weihnachtsparty|silvesterfeier|jahresfeier)\b",
        r"\b(maibaumstellen|maifest|maibaum)\b",
        r"\b(dorfabend|dorfgemeinschaftsabend|dorfabend)\b",
        r"\b(party|partyabend|karnevalsparty|faschingsparty)\b",
    ]),
    ("Markt", [
        r"\b(flohmarkt|trödelmarkt|trödel)\b",
        r"\b(wochenmarkt|bauernmarkt|kunsthandwerkermarkt)\b",
        r"\b(adventsmarkt|ostermarkt|herbstmarkt|frühlingsmarkt|jahrmarkt)\b",
        r"\b(kinderflohmarkt|babyflohmarkt|bücherflohmarkt)\b",
        r"\b(basar|verkaufsausstellung)\b",
    ]),
    ("Kultur", [
        r"\b(autorenlesung|lesung|buchvorstellung|buchpremiere)\b",
        r"\b(bilderbuchkino|bilderbuch\-kino|kamishibai|märchenstunde|vorlesestunde|geschichtenstunde)\b",
        r"\b(theater|theaterstück|theateraufführung|schattenspiel|puppentheater|mitspieltheater|improtheater)\b",
        r"\b(kino|filmabend|filmvorführung|dokumentation|dokumentarfilm|kurzfilm)\b",
        r"\b(kunstausstellung|ausstellung|vernissage|kunst|künstler|malerei|aquarell|fotografie|fotokurs)\b",
        r"\b(kabarett|comedy|kleinkunst|varieté|zirkus|zirkusprojekt|zirkusworkshop)\b",
        r"\b(krimidinner|krimiabend)\b",
    ]),
    ("Bildung", [
        r"\b(vortrag|vortragsreihe|vortragsabend|infovortrag|informationsabend|infoveranstaltung|themenabend)\b",
        r"\b(vhs|volkshochschule)\b",
        r"\b(bildungswerk|akademie|bildungshaus|bildung)\b",
        r"\b(fortbildung|schulung|lehrgang|referat|diskussionsabend)\b",
        r"\b(führung|führungen|stadtführung|kirchenführung)\b",
        r"\b(ausstellung|museum)\b",
    ]),
    ("Workshop", [
        r"\b(workshop|workshops)\b",
        r"\b(schnupperkurs|schnupperworkshop)\b",
    ]),
    ("Handwerk", [
        r"\b(basteln|bastel|bastelspaß|bastelnachmittag|bastelaktion|osterbasteln|weihnachtsbasteln)\b",
        r"\b(nähen|nähkurs|nähworkshop|stricken|stricktreff|strick|häkeln|handarbeit|handarbeiten)\b",
        r"\b(reparaturtreff|reparatur\-treff|reparatur)\b",
        r"\b(werkstatt|werken|töpfern|töpferkurs|schnitzen|holzwerken)\b",
        r"\b(kreativwerkstatt|kreativkurse)\b",
    ]),
    ("Essen", [
        r"\b(dampfnudel|dampfnudeltag|kässpätzle|käsespätzle|schupfnudel|flädlesuppe)\b",
        r"\b(kochkurs|kochabend|kochen|kochworkshop)\b",
        r"\b(backen|backkurs|backtag|brotbacken|backaktion)\b",
        r"\b(frühstück|frühstückstreff|brunch)\b",
        r"\b(kulinarisch|kulinarik|schlemmen|genießen|geniessen)\b",
        r"\b(kuchenverkauf|kuchenbuffet|kuchenbasar|waffel|waffeln|crêpe|crepe)\b",
        r"\b(mittagstisch|mitagessen|abendessen)\b",
        r"\b(grillen|grillfest|grillabend|bratwurst|wurstsalat)\b",
        r"\b(suppe|eintopf|gulasch|hähnchen\b|spaghetti|pasta|pizza)\b",
        r"\b(kaffeetreff|kaffeetrinken|kaffee\s+treff|kaffeeklatsch)\b",
        r"\b(bier|wein|weinprobe|biergarten|weinfest)\b",
    ]),
    ("Natur", [
        r"\b(wald|waldspaziergang|waldschule|waldpädagogik|walderlebnis)\b",
        r"\b(natur|naturspaziergang|naturerlebnis|naturführung)\b",
        r"\b(kräuter|kräuterwanderung|kräuterspaziergang)\b",
        r"\b(vogel|vögel|vogelkunde|vogelbeobachtung|vogelführung)\b",
        r"\b(insekten|bienen|imker|imkerei|schmetterling)\b",
        r"\b(garten|gartenarbeit|gartenaktion|gartentag|gartenpflege|kleingarten)\b",
        r"\b(umwelt|klima|nachhaltigkeit|naturschutz)\b",
        r"\b(putzete|stadtputzete|säuberungsaktion)\b",
    ]),
    ("Digital", [
        r"\b(edv|pc\s+|computer|programmieren|coding|codier)\b",
        r"\b(roboter|robotik|robotic)\b",
        r"\b(ki\s|künstliche\s+intelligenz|chatgpt|digital\s+treff|digitaltreff)\b",
        r"\b(smartphone\s+treff|tablet\s+treff|handy\s+treff)\b",
    ]),
    ("Senioren", [
        r"\b(seniorennachmittag|seniorenkreis|seniorentreff|seniorenclub)\b",
        r"\b(seniorenausflug|seniorenfeier|seniorenarbeit|seniorenberatung)\b",
    ]),
    ("Treff", [
        r"\b(stammtisch|stammtischtreffen)\b",
        r"\b(offener\s+treff)\b",
    ]),
    ("Politik", [
        r"\b(gemeinderat|gemeinderatssitzung|ortsbeirat|bürgerversammlung|bürgerinfo|bürgerinformations)\b",
        r"\b(bürgermeister|wahl|wahlen|kommunalwahl|landtagswahl|bundestagswahl)\b",
        r"\b(partei|fraktion|ausschuss|sitzung)\s+(.*?)(gemeinde|rat|stadt)\b",
    ]),
    ("Verein", [
        r"\b(mitgliederversammlung|jahreshauptversammlung|hauptversammlung)\b",
        r"\b(vorstand|vorstandssitzung|vorstandschaft|vorstandswahl|vorstand\+)\b",
        r"\b(abteilungsleitung|abteilungsleiter|abteilungsversammlung)\b",
        r"\b(turnrat|vereinsrat|vereinsausschuss)\b",
        r"\b(arbeitseinsatz|arbeitsdienst|vereinsarbeit)\b",
        r"\b(ehrenamt|ehrenamtstreffen|förderverein)\b",
        r"\b(mitgliedsversammlung|mitgliederversammlung)\b",
    ]),
    ("Wohltätigkeit", [
        r"\b(blutspende|blutspendetermin|blutspendeaktion)\b",
        r"\b(spendenaktion|spendensammlung|spendenlauf)\b",
        r"\b(karitativ|caritas|diakonie)\b",
    ]),
]


def score_content(title, description, organizer, location):
    text = f"{title} {description}".lower()
    full = f"{title} {description} {organizer} {location}".lower()

    scores = {}
    for tag, patterns in CONTENT_RULES:
        count = 0
        for pat in patterns:
            count += len(re.findall(pat, text))
        if count > 0:
            scores[tag] = count

    return scores


def classify_event(title, description, organizer, location):
    scores = score_content(title, description, organizer, location)

    if not scores:
        return ["Sonstiges"]

    # Sort by score descending
    sorted_tags = sorted(scores.items(), key=lambda x: -x[1])
    top_score = sorted_tags[0][1]

    # Take top 1-2 tags
    result = []
    for tag, score in sorted_tags:
        if len(result) >= 2:
            break
        if score == top_score:
            result.append(tag)

    # If only 1 top tag, add second if clearly significant
    if len(result) == 1 and len(sorted_tags) > 1:
        second = sorted_tags[1]
        # Only add if second score is at least 50% of top
        if second[1] >= top_score * 0.5:
            if second[0] not in result:
                result.append(second[0])

    # --- Contextual overrides ---

    # If Kirche is a top tag and Kinder is also strong, keep both (church children's groups)
    # But if Musik comes from "singen" in a children's church context, remove Musik
    t = f"{title} {description}".lower()
    org = (organizer or "").lower()
    loc = (location or "").lower()
    full = f"{t} {org} {loc}"

    # Church context: if organizer is a church/gemeinde, prioritize Kirche
    is_church_org = bool(re.search(r"(ev\.|evangelisch|katholisch|kath\.|kirchengemeinde|pfarrei|pfarramt)", org))

    # Remove Musik if it's only from "singen" in a church/children context and Kirche/Kinder are also top
    if "Musik" in result and ("Kirche" in result or "Kinder" in result):
        # Check if the only Musik signal is "singen" (which is generic in children's programs)
        musik_only_singen = bool(re.search(r"\bsingen\b", t)) and not re.search(
            r"\b(konzert|chor|orchester|musikverein|musikkapelle|gitarre|klavier|flöte|bläser|posaune|gesangverein|sänger|sängerin)\b", t
        )
        if musik_only_singen:
            result.remove("Musik")

    # Remove Essen from flohmarkt/basar events (refreshments ≠ food event)
    if "Essen" in result:
        if re.search(r"\b(flohmarkt|basar|trödel)\b", t):
            result.remove("Essen")

    # Remove Essen from Kinderflohmarkt
    if "Essen" in result:
        if re.search(r"\b(kinderflohmarkt|babyflohmarkt|bücherflohmarkt)\b", t):
            result.remove("Essen")

    # Handwerk over Markt for basteln events
    if "Markt" in result and "Handwerk" in scores:
        if re.search(r"\b(basteln|bastel|osterbasteln|handarbeit|kreativ)\b", t):
            result = [t for t in result if t != "Markt"]

    # Putzete -> Natur
    if re.search(r"\b(putzete|stadtputzete|säuberung)\b", t):
        result = [t for t in result if t != "Sonstiges"]
        if "Natur" not in result:
            result.append("Natur")

    # Abschiedskonzert / concert events
    if re.search(r"\b(konzert|abschiedskonzert)\b", t):
        if "Musik" not in result:
            result.append("Musik")

    # Dampfnudeltag -> Essen
    if re.search(r"\b(dampfnudel)\b", t):
        if "Essen" not in result:
            result.append("Essen")

    # Babys in Bewegung -> Kinder (not Sport)
    if re.search(r"\b(babys?\s+in\s+bewegung)\b", t):
        result = [t for t in result if t != "Sport"]
        if "Kinder" not in result:
            result.append("Kinder")

    # Frauenabend with church context -> Kirche
    if re.search(r"\bfrauenabend\b", t) and is_church_org:
        if "Kirche" not in result:
            result.append("Kirche")

    # Abendmahlsfeier -> Kirche
    if re.search(r"\babendmahlsfeier\b", t):
        if "Kirche" not in result:
            result.append("Kirche")
        result = [t for t in result if t != "Sonstiges"]

    # Patrozinium -> Kirche
    if re.search(r"\bpatrozinium\b", t):
        if "Kirche" not in result:
            result.append("Kirche")
        result = [t for t in result if t != "Sonstiges"]

    # Rundenwettkämpfe -> Sport
    if re.search(r"\b(rundenwettkämpfe|rundenwettkampf)\b", t):
        if "Sport" not in result:
            result.append("Sport")
        result = [t for t in result if t != "Sonstiges"]

    # Ski events -> Sport
    if re.search(r"\b(skiwochenende|skikurs|skilager|ski)\b", t):
        if "Sport" not in result:
            result.append("Sport")
        result = [t for t in result if t != "Sonstiges"]

    # Bildschirmfrei für Schüler -> Kinder
    if re.search(r"\b(bildschirmfrei)\b", t):
        if "Kinder" not in result:
            result.append("Kinder")
        result = [t for t in result if t != "Sonstiges"]

    # Turnier + Waffen -> Sport
    if re.search(r"\bturnier\b.*\b(waffen|waffe|ordonnanz)\b", t):
        if "Sport" not in result:
            result.append("Sport")
        result = [t for t in result if t != "Sonstiges"]

    # Wachdienst -> Verein (club duty)
    if re.search(r"\bwachdienst\b", t):
        if "Verein" not in result:
            result.append("Verein")

    # Clean up: remove Sonstiges if we found a real tag
    if len([t for t in result if t != "Sonstiges"]) > 0:
        result = [t for t in result if t != "Sonstiges"]

    # Deduplicate
    result = list(dict.fromkeys(result))

    if not result:
        result = ["Sonstiges"]

    return result


results = {}
errors = []

for i, event in enumerate(events):
    try:
        eid = str(event["id"])
        title = event.get("title") or ""
        description = event.get("description") or ""
        organizer = event.get("organizer") or ""
        location = event.get("location") or ""

        combined = f"{title} {description} {organizer} {location}"
        district_tags = extract_district_tags(combined)

        existing_tags = event.get("tags") or ""
        if existing_tags:
            for tag in existing_tags.split(","):
                tag = tag.strip()
                if tag in DISTRICTS:
                    district_tags.add(tag)

        content_tags = classify_event(title, description, organizer, location)

        all_tags = content_tags + sorted(district_tags)
        results[eid] = ",".join(all_tags)

    except Exception as e:
        import traceback
        errors.append({"id": event.get("id"), "error": str(e), "traceback": traceback.format_exc()})

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
