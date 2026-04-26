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
    return bool(re.search(rf"(?<![a-zäöüß]){re.escape(word)}(?![a-zäöüß])", text, re.IGNORECASE))

def contains_any(text, words):
    for w in words:
        if contains_word(text, w):
            return True
    return False

def classify_event(title, description, organizer, location):
    t = f"{title} {description}".lower()
    org = (organizer or "").lower()
    loc = (location or "").lower()

    is_church_org = bool(re.search(r"(ev\.?|evangelisch|katholisch|kath\.?|kirchengemeinde|pfarrei|pfarramt|liebenzeller\s+gemeinschaft)", org))
    is_church_loc = bool(re.search(r"(ev\.?\s+gemeindehaus|gemeindehaus)", loc))

    tags = set()

    # ===== Tier 1: Strong, unambiguous signals =====

    # --- Kirche ---
    if is_church_org or is_church_loc:
        tags.add("Kirche")
    if contains_any(t, ["gottesdienst", "wortgottesdienst", "abendmahl", "abendmahlsfeier",
                         "ökumene", "ökumenisch", "kirchenkaffee", "kirchencafé", "gemeindecafé",
                         "andacht", "segen", "segnung", "gebet", "beten", "rosenkranz",
                         "jungschar", "kindergottesdienst", "kinderkirche", "konfirmanden", "konfi",
                         "taufe", "taufen", "firmung", "trauung", "trauerfeier", "trauercafé",
                         "patrozinium", "krabbelgruppe", "kükenstube", "müttergruppe",
                         "eltern-baby-treff", "eltern-baby-café", "eltern-kind-treff",
                         "erstkommunion", "kommunionkinder", "dankgottesdienst",
                         "konfirmationsgottesdienst", "maiandacht",
                         "frauenabend", "selbsthilfegruppe",
                         "themenvormittage für eltern", "frühe hilfen"]):
        tags.add("Kirche")

    # --- Sport ---
    if contains_any(t, ["fußball", "fussball", "handball", "basketball", "volleyball",
                         "badminton", "tischtennis", "tennis",
                         "stadtlauf", "kinderlauf", "schülerlauf", "spendenlauf",
                         "lauftreff", "walkingtreff",
                         "turnen", "geräteturnen", "leistungsturnen", "turnrat",
                         "eltern-kind-turnen", "kinderturnen",
                         "skikurs", "skiwochenende", "skilager", "skifahren", "ski",
                         "schwimmkurs", "schwimmen", "kinderschwimmen",
                         "radtour", "radtouren", "radfahren",
                         "wanderung", "wanderungen", "wandertag", "wanderwoche", "wanderpreis",
                         "rundenwettkämpfe", "rundenwettkampf", "wanderpokal",
                         "kajak", "kanu", "paddeln", "kanufahrt",
                         "torwand", "torwandschießen",
                         "ordonnanz", "langwaffen",
                         "fechten", "rudern", "reiten", "kegeln", "bouldern", "klettern",
                         "zumba", "aerobic", "yoga", "pilates",
                         "sportabzeichen", "sportfest", "sporttag", "sportwoche",
                         "spechaa lauf", "lauf",
                         "reitturnier", "dressur", "springturnier",
                         "fischereitag", "fischerfest",
                         "public viewing", "wm",
                         "badentreff",
                         "schwangerschaftsgymnastik", "gymnastik",
                         "fit in der schwangerschaft",
                         "fitness check", "fitness",
                         "mannschaftsturnier", "ortsturnier", "turnier"]):
        tags.add("Sport")

    # --- Musik ---
    if contains_any(t, ["konzert", "abschiedskonzert", "weihnachtskonzert", "frühlingskonzert",
                         "herbstkonzert", "gospelkonzert", "klavierkonzert",
                         "musikabend", "musikverein", "musikkapelle", "musikschule",
                         "chor", "gospelchor", "popchor", "kinderchor", "jugendchor",
                         "singkreis", "gesangverein", "sängerfest", "sängerkreis",
                         "blasmusik", "bläser", "bläserkreis", "posaunenchor",
                         "fanfarenzug", "musikzug", "spielmannszug",
                         "orchester", "schulorchester", "jugendorchester",
                         "gitarre", "blockflöte", "klavier", "schlagzeug",
                         "musikalisch", "musikgarten", "musikalische früherziehung",
                         "trommeln", "trommelkurs", "trommler",
                         "rhythmuschor", "klangdialog",
                         "festival"]):
        tags.add("Musik")

    # --- Kinder / Jugend ---
    if contains_any(t, ["kinderflohmarkt", "babyflohmarkt", "kindersachen", "babybasar",
                        "ferienaktion", "ferienprogramm", "ferienspaß", "ferienbetreuung",
                        "ferienfreizeit", "kinderferien", "jugendfreizeit",
                        "kinderfest", "kinderparty", "kindertag", "weltkindertag",
                        "kinderkleider", "kinderschuhe",
                        "kindergeburtstag", "kinderbetreuung",
                        "teen girls", "teen club", "mädchen", "mädels", "mädchengruppe",
                        "bildschirmfrei",
                        "babys in bewegung", "baby in bewegung",
                        "familiensamstag", "familienausflug", "familiennachmittag",
                        "spieleabend", "spiele-treff", "spielenachmittag", "spielefest",
                        "spielgruppe", "kinderspielfest", "kinderspiel",
                        "jugendtraining", "jugendrotkreuz",
                        "modellbahn",
                        "schach für", "schachkurs", "schach",
                        "pfingstlager", "hobbylager", "lager",
                        "landesmeuten", "landesmeutenaktion",
                        "kinder", "kinders",
                        "18+ freizeit", "freizeit",
                        "babymassage", "baby massage",
                        "kreativfreitag", "kreativtreff",
                        "farbenfrohe", "sonnenfänger",
                        "tee- und spielstube", "tee und spielstube",
                        "steckenpferd und drachen",
                        "mamamacht's"]):
        tags.add("Kinder")

    # --- Essen ---
    if contains_any(t, ["dampfnudel", "dampfnudeltag", "kässpätzle", "käsespätzle",
                        "schupfnudel", "flädlesuppe", "spaghetti", "pasta", "pizza",
                        "kochkurs", "kochabend", "kochen", "kochworkshop",
                        "backen", "backkurs", "backtag", "brotbacken", "backaktion",
                        "frühstück", "frühstückstreff", "brunch",
                        "kulinarisch", "schlemmen", "genießen",
                        "grillen", "grillfest", "grillabend", "bratwurst", "wurstsalat",
                        "kuchenverkauf", "kuchenbuffet", "kuchenbasar", "waffel", "waffeln",
                        "mittagstisch", "kaffeetreff", "kaffeetrinken", "kaffee treff",
                        "kaffeeklatsch", "bier", "weinprobe", "hähnchen",
                        "abendessen", "essen"]):
        tags.add("Essen")

    # --- Fest ---
    if contains_any(t, ["bürgerball", "maskenball", "bunter abend",
                        "jubiläum", "jubiläumsfeier", "jubiläumsfest",
                        "sommerfest", "frühlingsfest", "herbstfest",
                        "weihnachtsfeier", "jahresfeier",
                        "maibaumstellen", "maibaum", "maifest",
                        "party", "partyabend", "karnevalsparty", "faschingsparty",
                        "abschlussfest", "vatertagsfest", "pfingstfeier",
                        "apfelblütenfest", "steinwiesenfest",
                        "1. mai fest", "maihockete",
                        "fischerfest"]):
        tags.add("Fest")

    # --- Markt ---
    if contains_any(t, ["flohmarkt", "trödelmarkt", "trödel", "basar",
                        "wochenmarkt", "bauernmarkt", "kunsthandwerkermarkt",
                        "adventsmarkt", "ostermarkt", "herbstmarkt", "frühlingsmarkt"]):
        tags.add("Markt")

    # --- Kultur ---
    if contains_any(t, ["autorenlesung", "lesung", "buchvorstellung", "buchpremiere",
                        "bilderbuchkino", "bilderbuch-kino", "kamishibai",
                        "märchenstunde", "vorlesestunde", "geschichtenstunde", "vorlesen",
                        "theater", "theaterstück", "theateraufführung", "schattenspiel",
                        "puppentheater", "mitspieltheater", "improtheater",
                        "erzähltheater",
                        "kino", "filmabend", "filmvorführung",
                        "kunstausstellung", "vernissage", "ausstellung",
                        "kabarett", "comedy", "kleinkunst", "varieté", "zirkus",
                        "krimidinner", "krimiabend",
                        "kulturentreff", "kulturen",
                        "red horse festival"]):
        tags.add("Kultur")

    # --- Handwerk (crafts, making) ---
    if contains_any(t, ["basteln", "bastel", "osterbasteln", "weihnachtsbasteln",
                        "nähen", "nähkurs", "stricken", "stricktreff", "strick",
                        "häkeln", "handarbeit", "handarbeiten",
                        "reparaturtreff", "reparatur-treff", "reparatur",
                        "werkstatt", "werken", "töpfern", "schnitzen", "holzwerken",
                        "modellbahn"]):
        tags.add("Handwerk")

    # --- Bildung ---
    if contains_any(t, ["vortrag", "vortragsreihe", "vortragsabend", "infovortrag",
                        "informationsabend", "infoveranstaltung", "themenabend",
                        "vhs", "volkshochschule", "bildungswerk",
                        "fortbildung", "schulung", "lehrgang", "diskussionsabend",
                        "führung", "stadtführung", "museum",
                        "forum wohnen",
                        "erste-hilfe-kurs",
                        "denkfabrik",
                        "podiumsdiskussion",
                        "geburtsvorbereitungskurs", "vorbereitungskurs"]):
        tags.add("Bildung")

    # --- Workshop ---
    if contains_any(t, ["workshop", "schnupperkurs"]):
        tags.add("Workshop")

    # --- Digital ---
    if contains_any(t, ["edv", "computer", "programmieren", "coding",
                        "roboter", "robotik",
                        "künstliche intelligenz", "chatgpt",
                        "digital treff", "digitaltreff",
                        "smartphone treff", "tablet treff",
                        "digitales info-café", "info-café", "was finde ich wo"]):
        tags.add("Digital")

    # --- Natur ---
    if contains_any(t, ["putzete", "stadtputzete", "säuberungsaktion",
                        "wald", "waldspaziergang", "waldschule", "waldpädagogik",
                        "naturspaziergang", "naturerlebnis", "naturführung",
                        "kräuter", "kräuterwanderung",
                        "vogel", "vögel", "vogelkunde",
                        "insekten", "bienen", "imker",
                        "garten", "gartenarbeit", "gartenaktion", "gartentag",
                        "fischereitag", "angeln",
                        "geflügelimpfung", "geflügel"]):
        tags.add("Natur")

    # --- Senioren ---
    if contains_any(t, ["seniorennachmittag", "seniorenkreis", "seniorentreff",
                        "seniorenclub", "seniorenausflug", "seniorenfeier"]):
        tags.add("Senioren")

    # --- Treff (use sparingly) ---
    if contains_any(t, ["stammtisch", "offener treff", "clubabend", "badentreff"]):
        tags.add("Treff")

    # --- Politik ---
    if contains_any(t, ["gemeinderat", "gemeinderatssitzung", "ortsbeirat",
                        "bürgerversammlung", "bürgermeister", "ob-kandidat", "ob-kandidaten",
                        "bürgermeisterkandidat",
                        "podiumsdiskussion",
                        "wahl", "wahlen", "denkfabrik",
                        "einwohnerversammlung"]):
        tags.add("Politik")

    # --- Verein (sparingly) ---
    if contains_any(t, ["mitgliederversammlung", "jahreshauptversammlung", "hauptversammlung",
                        "vorstand", "vorstandssitzung", "vorstandschaft", "vorstandswahl",
                        "abteilungsleitung", "abteilungsleiter", "abteilungsversammlung",
                        "turnrat", "vereinsrat",
                        "arbeitseinsatz", "arbeitsdienst", "vereinsarbeit",
                        "ehrenamt", "ehrenamtstreffen", "förderverein",
                        "mitgliedsversammlung", "wachdienst",
                        "clubabend"]):
        tags.add("Verein")

    # --- Wohltätigkeit ---
    if contains_any(t, ["blutspende", "blutspendetermin",
                        "spendenaktion", "spendensammlung", "spendenlauf",
                        "karitativ", "caritas", "diakonie", "jugendrotkreuz",
                        "vdk lotsendienst", "lotsendienst",
                        "offene sprechstunde", "psychologische beratungsstelle"]):
        tags.add("Wohltätigkeit")

    # ===== Contextual overrides =====

    # Remove Essen from flohmarkt/basar events
    if "Essen" in tags and contains_any(t, ["flohmarkt", "basar", "trödel"]):
        tags.discard("Essen")

    # Stage Fever Klangdialog -> Musik
    if contains_word(t, "klangdialog") or contains_word(t, "stage fever"):
        tags.add("Musik")

    # Maiandacht -> Kirche
    if contains_word(t, "maiandacht"):
        tags.add("Kirche")

    # Konfirmationsgottesdienst -> Kirche
    if contains_word(t, "konfirmationsgottesdienst"):
        tags.add("Kirche")

    # Pfingstausflug -> Kirche (often church-organized)
    if contains_word(t, "pfingstausflug"):
        tags.add("Kirche")

    # Apfelblütenfest -> Fest
    if contains_word(t, "apfelblütenfest"):
        tags.add("Fest")

    # Steinwiesenfest -> Fest
    if contains_word(t, "steinwiesenfest"):
        tags.add("Fest")

    # Proben (rehearsal) of choir -> Musik
    if contains_word(t, "probe") and contains_word(t, "chor"):
        tags.add("Musik")

    # Offene Sprechstunde -> Wohltätigkeit / Bildung
    if contains_word(t, "offene sprechstunde"):
        tags.add("Wohltätigkeit")

    # Erste-Hilfe-Kurs -> Bildung
    if contains_word(t, "erste-hilfe-kurs"):
        tags.add("Bildung")

    # 1. Mai Denkfabrik -> Bildung/Politik
    if contains_word(t, "denkfabrik"):
        tags.add("Bildung")

    # WM / Public Viewing -> Sport
    if contains_word(t, "public viewing") or contains_word(t, "wm "):
        tags.add("Sport")

    # Sports matches: FC X vs Y, pokalfinale
    if re.search(r'\bfc\b.*\b(vs|gegen)\b', t) or re.search(r'\bvs\b.*\bfc\b', t):
        tags.add("Sport")
    if contains_word(t, "pokalfinale"):
        tags.add("Sport")

    # Elterninfoabend -> Bildung
    if contains_word(t, "elterninfoabend"):
        tags.add("Bildung")

    # Internationaler Tag des Strickens -> Handwerk
    if contains_word(t, "strickens") or contains_word(t, "stricken"):
        tags.add("Handwerk")

    if not tags:
        tags.add("Sonstiges")

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
