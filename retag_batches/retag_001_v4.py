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

def contains_word(text, word):
    """Check if word appears as a whole word or as a compound part in text."""
    return bool(re.search(rf"(?<![a-zäöüß]){re.escape(word)}(?![a-zäöüß])", text, re.IGNORECASE))

def contains_any(text, words):
    """Check if any word from a list appears in text."""
    for w in words:
        if contains_word(text, w):
            return True
    return False

def classify_event(title, description, organizer, location):
    t = f"{title} {description}".lower()
    full = f"{title} {description} {organizer} {location}".lower()
    org = (organizer or "").lower()
    is_church_org = bool(re.search(r"(ev\.|evangelisch|katholisch|kath\.|kirchengemeinde|pfarrei|pfarramt|liebenzeller)", org))

    tags = set()

    # --- Kirche ---
    kirchen_words = ["gottesdienst", "wortgottesdienst", "abendmahl", "abendmahlsfeier",
                     "ökumene", "ökumenisch", "kirchenkaffee", "kirchencafé", "gemeindecafé",
                     "andacht", "segen", "segnung", "gebet", "beten", "rosenkranz",
                     "jungschar", "kindergottesdienst", "kinderkirche", "konfirmanden", "konfi",
                     "taufe", "taufen", "firmung", "trauung", "trauerfeier", "trauercafé",
                     "patrozinium", "krabbelgruppe", "kükenstube", "müttergruppe",
                     "eltern-baby-treff", "eltern-baby-café", "frauenabend",
                     "erstkommunion", "kommunionkinder"]
    if contains_any(t, kirchen_words):
        tags.add("Kirche")
    if is_church_org:
        tags.add("Kirche")

    # --- Sport ---
    sport_words = ["fußball", "fussball", "handball", "basketball", "volleyball",
                   "badminton", "tischtennis", "tennis", "stadtlauf", "kinderlauf",
                   "schülerlauf", "spendenlauf", "lauftreff", "walkingtreff",
                   "sportabzeichen", "sportfest", "sporttag", "sportwoche", "sportgruppe",
                   "turnen", "geräteturnen", "leistungsturnen", "turnrat",
                   "eltern-kind-turnen", "kinderturnen",
                   "skikurs", "skiwochenende", "skilager", "skifahren", "skigebiet",
                   "schwimmkurs", "schwimmen", "kinderschwimmen",
                   "radtour", "radtouren", "radfahren", "wanderung", "wanderungen",
                   "wandertag", "wanderwoche", "wanderpreis",
                   "rundenwettkämpfe", "rundenwettkampf", "wanderpokal",
                   "kajak", "kanu", "paddeln", "kanufahrt",
                   "torwand", "torwandschießen",
                   "turnier", "ordonnanz", "langwaffen",
                   "fechten", "rudern", "reiten", "kegeln", "bouldern", "klettern",
                   "zumba", "aerobic", "yoga", "pilates",
                   "sportlich", "sportverein"]
    if contains_any(t, sport_words):
        tags.add("Sport")

    # --- Musik ---
    musik_words = ["konzert", "abschiedskonzert", "weihnachtskonzert", "frühlingskonzert",
                   "herbstkonzert", "gospelkonzert", "klavierkonzert",
                   "musikabend", "musikverein", "musikkapelle", "musikschule",
                   "chor", "gospelchor", "popchor", "kinderchor", "jugendchor",
                   "singkreis", "gesangverein", "sängerfest", "sängerkreis",
                   "blasmusik", "bläser", "bläserkreis", "posaunenchor",
                   "fanfarenzug", "musikzug", "spielmannszug",
                   "orchester", "schulorchester", "jugendorchester",
                   "gitarre", "blockflöte", "klavier", "schlagzeug",
                   "musikalisch", "musikgarten", "musikalische früherziehung",
                   "trommeln", "trommelkurs", "trommler"]
    # "singen" alone is not enough (too common in children's programs)
    if contains_any(t, musik_words):
        tags.add("Musik")

    # --- Kinder / Jugend ---
    kinder_words = ["kinderflohmarkt", "babyflohmarkt", "kindersachen", "babybasar",
                    "ferienaktion", "ferienprogramm", "ferienspaß", "ferienbetreuung",
                    "ferienfreizeit", "kinderferien", "jugendfreizeit",
                    "kinderfest", "kinderparty", "kindertag", "weltkindertag",
                    "kinderkleider", "kinderschuhe",
                    "kindergeburtstag", "kinderbetreuung",
                    "teen girls", "teen club", "mädchen", "mädels",
                    "bildschirmfrei",
                    "babys in bewegung", "baby in bewegung",
                    "familiensamstag", "familienausflug", "familiennachmittag",
                    "spieleabend", "spiele-treff", "spielenachmittag", "spielefest",
                    "spielgruppe", "kinderspielfest", "kinderspiel",
                    "jugendtraining", "jugendrotkreuz",
                    "selbsthilfegruppe", "modellbahn",
                    "schach für", "schachkurs",
                    "jugend", "teenager"]
    if contains_any(t, kinder_words):
        tags.add("Kinder")
    # Title explicitly mentioning children/youth
    if re.search(r"\b(kinder|kind|kids|jugend|schüler|schülerin)\b", t, re.IGNORECASE):
        # Only if not a church context (church has its own category)
        # But general children's activities should get Kinder
        pass  # handled below

    # --- Handwerk / Basteln ---
    handwerk_words = ["basteln", "bastel", "osterbasteln", "weihnachtsbasteln",
                      "nähen", "nähkurs", "stricken", "stricktreff", "strick",
                      "häkeln", "handarbeit", "handarbeiten",
                      "reparaturtreff", "reparatur-treff", "reparatur",
                      "werkstatt", "werken", "töpfern", "schnitzen", "holzwerken",
                      "kreativwerkstatt", "kreativkurs", "kreativ",
                      "modellbahn"]
    if contains_any(t, handwerk_words):
        tags.add("Handwerk")

    # --- Essen / Kulinarisch ---
    essen_words = ["dampfnudel", "dampfnudeltag", "kässpätzle", "käsespätzle",
                   "schupfnudel", "flädlesuppe", "spaghetti", "pasta", "pizza",
                   "kochkurs", "kochabend", "kochen", "kochworkshop",
                   "backen", "backkurs", "backtag", "brotbacken", "backaktion",
                   "frühstück", "frühstückstreff", "brunch",
                   "kulinarisch", "schlemmen", "genießen", "grillen", "grillfest",
                   "kuchenverkauf", "kuchenbuffet", "kuchenbasar", "waffel", "waffeln",
                   "mittagstisch", "bratwurst", "wurstsalat",
                   "kaffeetreff", "kaffeetrinken", "kaffee treff", "kaffeeklatsch",
                   "bier", "weinprobe", "hähnchen"]
    if contains_any(t, essen_words):
        tags.add("Essen")

    # --- Fest / Feier ---
    fest_words = ["bürgerball", "maskenball", "bunter abend",
                  "jubiläum", "jubiläumsfeier", "jubiläumsfest",
                  "sommerfest", "frühlingsfest", "herbstfest", "weihnachtsfeier",
                  "jahresfeier",
                  "maibaumstellen", "maibaum", "maifest",
                  "party", "partyabend", "karnevalsparty", "faschingsparty",
                  "abschlussfest", "vatertagsfest"]
    if contains_any(t, fest_words):
        tags.add("Fest")

    # --- Markt ---
    markt_words = ["flohmarkt", "trödelmarkt", "trödel", "basar",
                   "wochenmarkt", "bauernmarkt", "kunsthandwerkermarkt",
                   "adventsmarkt", "ostermarkt", "herbstmarkt", "frühlingsmarkt"]
    if contains_any(t, markt_words):
        tags.add("Markt")

    # --- Kultur ---
    kultur_words = ["autorenlesung", "lesung", "buchvorstellung", "buchpremiere",
                    "bilderbuchkino", "bilderbuch-kino", "kamishibai",
                    "märchenstunde", "vorlesestunde", "geschichtenstunde", "vorlesen",
                    "theater", "theaterstück", "theateraufführung", "schattenspiel",
                    "puppentheater", "mitspieltheater", "improtheater",
                    "kino", "filmabend", "filmvorführung",
                    "kunstausstellung", "vernissage", "ausstellung",
                    "kabarett", "comedy", "kleinkunst", "varieté", "zirkus",
                    "krimidinner", "krimiabend",
                    "kulturentreff", "kulturen",
                    "10 jahre.*festival", "festival"]
    if contains_any(t, kultur_words):
        tags.add("Kultur")

    # --- Bildung ---
    bildung_words = ["vortrag", "vortragsreihe", "vortragsabend", "infovortrag",
                     "informationsabend", "infoveranstaltung", "themenabend",
                     "vhs", "volkshochschule", "bildungswerk",
                     "fortbildung", "schulung", "lehrgang", "diskussionsabend",
                     "führung", "stadtführung", "museum",
                     "forum wohnen"]
    if contains_any(t, bildung_words):
        tags.add("Bildung")

    # --- Workshop ---
    workshop_words = ["workshop", "schnupperkurs"]
    if contains_any(t, workshop_words):
        tags.add("Workshop")

    # --- Digital ---
    digital_words = ["edv", "computer", "programmieren", "coding",
                     "roboter", "robotik",
                     "künstliche intelligenz", "chatgpt",
                     "digital treff", "digitaltreff",
                     "smartphone treff", "tablet treff"]
    if contains_any(t, digital_words):
        tags.add("Digital")

    # --- Natur ---
    natur_words = ["putzete", "stadtputzete", "säuberungsaktion",
                   "wald", "waldspaziergang", "waldschule", "waldpädagogik",
                   "naturspaziergang", "naturerlebnis", "naturführung",
                   "kräuter", "kräuterwanderung", "kräuterspaziergang",
                   "vogel", "vögel", "vogelkunde",
                   "insekten", "bienen", "imker",
                   "garten", "gartenarbeit", "gartenaktion", "gartentag"]
    if contains_any(t, natur_words):
        tags.add("Natur")

    # --- Senioren ---
    senioren_words = ["seniorennachmittag", "seniorenkreis", "seniorentreff",
                      "seniorenclub", "seniorenausflug", "seniorenfeier"]
    if contains_any(t, senioren_words):
        tags.add("Senioren")

    # --- Treff (use sparingly) ---
    treff_words = ["stammtisch", "offener treff"]
    if contains_any(t, treff_words):
        tags.add("Treff")

    # --- Politik ---
    politik_words = ["gemeinderat", "gemeinderatssitzung", "ortsbeirat",
                     "bürgerversammlung", "bürgermeister", "ob-kandidat",
                     "wahl", "wahlen"]
    if contains_any(t, politik_words):
        tags.add("Politik")

    # --- Verein (use sparingly - only if about club business, not just organized by a club) ---
    verein_words = ["mitgliederversammlung", "jahreshauptversammlung", "hauptversammlung",
                    "vorstand", "vorstandssitzung", "vorstandschaft", "vorstandswahl",
                    "abteilungsleitung", "abteilungsleiter", "abteilungsversammlung",
                    "turnrat", "vereinsrat",
                    "arbeitseinsatz", "arbeitsdienst", "vereinsarbeit",
                    "ehrenamt", "ehrenamtstreffen", "förderverein",
                    "mitgliedsversammlung", "wachdienst"]
    if contains_any(t, verein_words):
        tags.add("Verein")

    # --- Wohltätigkeit ---
    wohltätigkeit_words = ["blutspende", "blutspendetermin",
                           "spendenaktion", "spendensammlung", "spendenlauf",
                           "karitativ", "caritas", "diakonie", "jugendrotkreuz"]
    if contains_any(t, wohltätigkeit_words):
        tags.add("Wohltätigkeit")

    # ====== TITLE-BASED FALLBACKS ======
    # If no tags found yet, check title for strong signals
    if not tags:
        tl = t[:200]

        # Dance-related: Tanzen für Kleinsten | Garde groups -> Sport
        if re.search(r"\b(tanzen|tanz)", tl):
            tags.add("Sport")
        # Garde groups are dance groups -> Sport
        elif contains_any(tl, ["garde", "seesternchen", "seepferdchen", "korallen"]):
            tags.add("Sport")
        # Kinder- und Jugendtraining -> Sport
        elif contains_any(tl, ["training", "trainiert", "sport", "turnen"]):
            tags.add("Sport")
        # Spiele / Spiel -> Kinder
        elif contains_any(tl, ["spiele", "spiel"]):
            tags.add("Kinder")
        # Schüler / Schule -> Bildung/Kinder
        elif contains_any(tl, ["schüler", "schule", "gymnasium"]):
            tags.add("Kinder")
        # Pfingstlager / Hobbylager -> Kinder
        elif contains_any(tl, ["lager", "pfingstlager", "hobbylager"]):
            tags.add("Kinder")
        # Red Horse Festival -> Kultur
        elif contains_any(tl, ["festival"]):
            tags.add("Kultur")
        # Kanufahrt -> Sport
        elif contains_any(tl, ["kanufahrt", "kanu"]):
            tags.add("Sport")

    # ====== CONTEXTUAL REFINEMENTS ======

    # Remove Essen from flohmarkt/basar events (refreshments ≠ food event)
    if "Essen" in tags and "Markt" in tags:
        if contains_any(t, ["flohmarkt", "basar", "trödel"]):
            tags.discard("Essen")

    # Putzete -> Natur (remove Sonstiges override happens later)
    if contains_word(t, "putzete"):
        tags.add("Natur")

    # "Abschiedskonzert" must be Musik
    if contains_word(t, "abschiedskonzert"):
        tags.add("Musik")

    # Dampfnudeltag -> Essen
    if contains_word(t, "dampfnudel"):
        tags.add("Essen")

    # Babys in Bewegung -> Kinder
    if contains_word(t, "baby in bewegung") or contains_word(t, "babys in bewegung"):
        tags.discard("Sport")
        tags.add("Kinder")

    # Frauenabend in church context -> Kirche
    if contains_word(t, "frauenabend") and is_church_org:
        tags.add("Kirche")

    # Abendmahlsfeier -> Kirche
    if contains_word(t, "abendmahlsfeier"):
        tags.add("Kirche")

    # Patrozinium -> Kirche
    if contains_word(t, "patrozinium"):
        tags.add("Kirche")

    # Rundenwettkämpfe -> Sport
    if contains_word(t, "rundenwettkämpfe") or contains_word(t, "rundenwettkampf"):
        tags.add("Sport")

    # Ski events -> Sport
    if re.search(r"\bski", t):
        tags.add("Sport")

    # Bildschirmfrei -> Kinder
    if contains_word(t, "bildschirmfrei"):
        tags.add("Kinder")

    # Turnier + (waffen|ordonnanz) -> Sport
    if "turnier" in t.lower() and contains_any(t, ["waffen", "waffe", "ordonnanz"]):
        tags.add("Sport")

    # Wachdienst -> Verein
    if contains_word(t, "wachdienst"):
        tags.add("Verein")

    # Jugendrotkreuz -> Wohltätigkeit (and Kinder/jugend)
    if contains_word(t, "jugendrotkreuz"):
        tags.add("Wohltätigkeit")
        tags.add("Kinder")

    # Selbsthilfegruppe -> Treff or Kirche
    if contains_word(t, "selbsthilfegruppe"):
        tags.add("Treff")

    # Modellbahn -> Handwerk
    if contains_word(t, "modellbahn"):
        tags.add("Handwerk")

    # Schach for students -> Kinder
    if re.search(r"\bschach\b", t):
        tags.add("Kinder")

    # "Tanzen für die Kleinsten" -> Sport (dance)
    if re.search(r"\btanzen\b", t):
        tags.add("Sport")

    # Garde groups are dance -> Sport
    if contains_word(t, "garde"):
        tags.add("Sport")

    # Spieleabend / Spiele-Treff -> Kinder
    if contains_any(t, ["spieleabend", "spiele-treff", "spielenachmittag"]):
        tags.add("Kinder")

    # Kinderspielfest -> Kinder
    if contains_word(t, "kinderspielfest"):
        tags.add("Kinder")

    # Pfingstlager -> Kinder
    if contains_word(t, "pfingstlager"):
        tags.add("Kinder")

    # Hobbylager -> Kinder
    if contains_word(t, "hobbylager"):
        tags.add("Kinder")

    # Landesmeutenaktion -> Kinder (scouts)
    if contains_word(t, "landesmeutenaktion"):
        tags.add("Kinder")

    # Internationaler Tag des Strickens -> Handwerk
    if contains_word(t, "strickens") or contains_word(t, "stricken"):
        tags.add("Handwerk")

    # Kanufahrt -> Sport
    if contains_word(t, "kanufahrt"):
        tags.add("Sport")

    # Abschlussfest -> Fest
    if contains_word(t, "abschlussfest"):
        tags.add("Fest")

    # Vatertagsfest -> Fest
    if contains_word(t, "vatertagsfest"):
        tags.add("Fest")

    # Forum Wohnen -> Bildung
    if contains_word(t, "forum wohnen"):
        tags.add("Bildung")
        tags.add("Politik")

    # KulturenTreff -> Kultur
    if contains_word(t, "kulturentreff") or contains_word(t, "kulturen"):
        tags.add("Kultur")

    # Red Horse Festival -> Musik/Kultur
    if contains_word(t, "red horse festival") or contains_word(t, "festival"):
        tags.add("Kultur")
        tags.add("Musik")

    # Dankgottesdienst -> Kirche
    if contains_word(t, "dankgottesdienst"):
        tags.add("Kirche")

    # Erstkommunion -> Kirche
    if contains_word(t, "erstkommunion") or contains_word(t, "kommunion"):
        tags.add("Kirche")

    # Landesmeutenaktion -> scouts/nature
    if contains_word(t, "landesmeuten"):
        tags.add("Natur")

    # Jugendliche/Jugend in title -> Kinder
    if re.search(r"\bjugend", t):
        tags.add("Kinder")

    # ---- Limit to top 2, prefer stronger signals ----
    if not tags:
        tags.add("Sonstiges")

    # Convert to list, deduplicate, preserve order
    result = list(tags)
    return result


results = {}
errors = {}

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

output = {"errors": errors, "results": results}

with open("/Users/joereuter/Clones/schdudesee/retag_batches/results_001.json", "w") as f:
    json.dump(output, f, indent=2, ensure_ascii=False)

total = len(events)
done = len(results)
error_count = len(errors)
print(f"Processed {done}/{total} events. {error_count} errors.")
