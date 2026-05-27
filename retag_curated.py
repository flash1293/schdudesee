#!/usr/bin/env python3
"""Re-tag all curated event JSONs using current auto_tag() logic, without re-scraping."""
import json, sys, os, glob, re

# ===== Constants (copy of what's in scrape_and_merge.py / run_pipeline.py) =====

TITLE_EXCLUSIVE_TAGS = {}

ORGANIZER_EXCLUSIVE_TAGS = {
    "agendagruppe umwelt": "Natur",
    "fc ": "Sport",
    "jugendzentrum graubau": "Blankenloch",
}

KEYWORDS = {
    "Sport": ["stadtlauf", "triathlon", "tennis", "turnen", "fitness", "yoga", "pilates", "tischtennis",
              "fu\u00dfball", "fussball", "schwimm", "rad", "bike", "cycling", "sport", "bewegung",
              "gymnastik", "tanz", "dance", "ballett", "kickbox", "karate", "indiaca", "volleyball",
              "handball", "basketball", "reiten", "pferd", "wandern", "training", "spechaa",
              "turnier", "kajak", "kanu", "dressur", "springturnier", "reitturnier", "meisterschaft",
              "pokalfinale", "segeln", "regatta", "gleitschirm", "sportwoche", "radtour", "wanderung",
              "m\u00fcllsammel", "altpapiersammlung", "vogelstimmen", "streuobstwiese", "waldbegehung", "waldbegang"],
    "Musik": ["konzert", "chor", "gesang", "musik", "band", "jazz", "singen", "lieder", "klang",
              "musikal", "orchester", "posaunen", "gitarre", "vox", "choir", "swing", "liederabend",
              "gospel", "rockfestival"],
    "Kultur": ["theater", "lesung", "kunst", "ausstellung", "kino", "literatur", "b\u00fchne", "kultur",
               "museum", "foto", "malen", "zeichnen", "denkmals", "salsa", "vernissage", "modellbahn",
               "garde", "fasching", "karneval", "kost\u00fcm", "tanzgruppe"],
    "Kirche": ["gottesdienst", "kirche", "konfirmation", "firmung", "taufe", "messe",
               "andacht", "segen", "\u00f6kumen", "patrozinium", "gebet", "evangelisch", "katholisch",
               "trauer", "abendmahl", "kommunion", "herzensgebet", "maiandacht", "bibelkreis",
               "bibelgespr\u00e4ch", "bibelstunde", "vesper", "kreuzweg", "volkstrauertag", "allerseelen",
               "allerheiligen", "glaubenskurs", "religionsunterricht"],
    "Kinder": ["kind", "baby", "eltern-kind", "krabbel", "spiel", "familie", "m\u00e4dchen", "junge",
               "kindergarten", "schule", "vorlesen", "bilderbuch", "k\u00fcken", "seepferdchen",
               "abenteuer", "zwerge", "jugend", "teen", "sch\u00fcler", "kinderturnen", "ferien",
               "caribi", "minis", "bambini", "steckenpferd", "drachen", "lager", "ballontag",
               "halloween", "gruselnacht", "modellflug", "scoutcamp", "ferienspa\u00df", "nikolaus",
               "camp", "w\u00f6lfling"],
    "Fest": ["fest", "oktoberfest", "maifest", "weihnachtsmarkt", "kerwe", "party", "sportfest",
             "maibaum", "fr\u00fchlingsfest", "sommerfest", "jubil\u00e4um", "vatertagsfest",
             "abschlussfeier", "thanksgiving", "neujahr", "adventzauber", "wintergl\u00fchen",
             "weihnachtskorso", "heimattage", "steinwiesenfest", "k\u00fcrbisfest", "h\u00e4hnchenfest",
             "fischerfest", "apfelbl\u00fctenfest", "kinderspielfest", "pfingstfeier"],
    "Markt": ["markt", "flohmarkt", "tr\u00f6del", "weihnachtsmarkt", "verkaufsoffener", "herbstmarkt",
              "hofflohmarkt", "frauenflohmarkt", "bauernmarkt"],
    "Workshop": ["workshop", "kurs", "seminar", "unterricht", "training"],
    "Bildung": ["bildung", "vortrag", "schule", "vhs", "diskussion", "fortbildung", "lesen",
                "lernen", "infoveranstaltung", "podiumsdiskussion", "ausbildungsplattform", "schulkonferenz"],
    "Natur": ["natur", "wald", "vogel", "baum", "pflanze", "umwelt", "klima",
              "hornisse", "mulchen", "exkursion", "wanderung",
              "gartenfest", "gartenarbeit", "gartengestaltung", "gartenbau"],
    "Essen": ["essen", "fr\u00fchst\u00fcck", "kuchen", "bratwurst", "bier", "wein", "getr\u00e4nk",
              "imbiss", "grill", "kulinarisch", "mittagstisch", "mittagessen", "steak", "schnitzel",
              "burger", "pommes", "wurst", "currywurst", "suppe", "eintopf", "veggie", "salat",
              "k\u00e4se", "waffel", "crepe", "eis", "sp\u00e4tzle", "maultaschen", "fisch", "fleisch",
              "pasta", "pizza", "paella", "chili", "bowl", "tacos", "burrito", "asiatisch",
              "thail\u00e4ndisch", "indisch", "mediterran", "griechisch", "italienisch", "amerikanisch",
              "kartoffel", "gem\u00fcse", "obst", "beeren", "kraut", "r\u00fcbe", "k\u00fcrbis",
              "marmelade", "honig", "saft", "most", "apfelwein", "biergarten", "weinstand",
              "weinprobe", "weinfest", "bierfest", "fr\u00fchst\u00fccksbuffet", "brunch"],
    "Treff": ["treff", "stammtisch", "runde", "begegnung", "fr\u00fchst\u00fcck", "kochen",
              "backen", "basteln", "handarbeit", "stricken", "h\u00e4keln", "n\u00e4hen",
              "gesellschaft", "spieleabend", "spielenachmittag", "kegeln", "schach", "bridge",
              "skat", "bingo", "quiz", "reisebericht", "diavortrag", "lichtbildervortrag",
              "gespr\u00e4chskreis", "gespr\u00e4chsrunde", "erz\u00e4hlcaf\u00e9",
              "hock", "hocketse", "plauderei", "kl\u00f6n", "klon"],
    "Handwerk": ["handwerk", "t\u00f6pferei", "keramik", "schnitzen", "schreinern", "werken",
                 "diy", "selbermachen", "bastel", "n\u00e4hen", "stricken", "h\u00e4keln", "sticken",
                 "filzen", "weben", "spinnen", "holz", "metall", "schmied", "leder", "papier",
                 "pappe", "karton", "gestalten", "werkzeug", "maschine", "technik", "reparieren",
                 "upcycling", "recycling"],
}

DISTRICTS = {
    "Blankenloch": ["blankenloch", "thomas-mann-gymnasium", "thomas-mann-schule", "tmg"],
    "B\u00fcchig": ["b\u00fcchig"],
    "Friedrichstal": ["friedrichstal"],
    "Sp\u00f6ck": ["sp\u00f6ck"],
    "Stutensee": ["stutensee", "wasserwerk", "graubau"],
}

DISTRICT_EXCLUSIONS = {
    "Stutensee": ["waldstadt"],
}

TITLE_ALWAYS_TAGS = {
    "tanzen f\u00fcr die kleinsten": ["Kinder"],
    "seesternchengarde": ["Kinder"],
}

FALSE_POSITIVE_CLEANUP = {
    "Essen": ["bieringer", "bieringer-str"],
    "Kirche": ["lutherkirche", "messen"],
    "Natur": ["waldstadt"],
    "Sport": ["jam session", "jam-session", "konrad", "bereiten"],
    "Musik": ["k\u00fckenstube", "eltern-baby-caf\u00e9", "krabbelgruppe", "eltern-kind-kreis",
               "eltern-kind-caf\u00e9", "eltern-kind-gruppe", "babycaf\u00e9", "babytreff",
               "choreografien", "mitgliedern", "mitglieder"],
    "Workshop": ["jugendrotkreuz", "pfadfind"],
}

def auto_tag(title, description="", location="", organizer=""):
    title_lower = (title or "").lower()
    content_tags = []
    for exclusive_kw, forced_tag in TITLE_EXCLUSIVE_TAGS.items():
        if exclusive_kw in title_lower:
            content_tags = [forced_tag]
            break

    if not content_tags:
        org_lower = (organizer or "").lower()
        for exclusive_kw, forced_tag in ORGANIZER_EXCLUSIVE_TAGS.items():
            if exclusive_kw in org_lower:
                content_tags = [forced_tag]
                break

    if not content_tags:
        content_text = f"{title} {description}".lower()
        for tag, keywords in KEYWORDS.items():
            for kw in keywords:
                if kw in content_text:
                    content_tags.append(tag)
                    break
        # Remove tags for known false positive substring matches BEFORE truncation
        for tag, fakes in FALSE_POSITIVE_CLEANUP.items():
            if tag in content_tags and any(fp in content_text for fp in fakes):
                content_tags.remove(tag)
        content_tags = content_tags[:2]
        # Re-apply mandatory tags for specific titles after truncation
        for title_trigger, extra_tags in TITLE_ALWAYS_TAGS.items():
            if title_trigger in title_lower:
                for t in extra_tags:
                    if t not in content_tags:
                        content_tags.append(t)

    def match_districts(text):
        results = []
        for district, keywords in DISTRICTS.items():
            for kw in keywords:
                if kw in text:
                    excluded = False
                    for excl in DISTRICT_EXCLUSIONS.get(district, []):
                        if excl in text:
                            excluded = True
                            break
                    if not excluded and district not in results:
                        results.append(district)
                    break
        return results

    loc_text = (location or "").lower()
    content_text_full = f"{title} {description}".lower()
    org_text = (organizer or "").lower()
    location_districts = match_districts(loc_text)
    content_districts = match_districts(content_text_full)
    district_tags = list(location_districts)
    for d in content_districts:
        if d not in district_tags:
            district_tags.append(d)
    if not location_districts:
        org_districts = match_districts(org_text)
        for d in org_districts:
            if d not in district_tags:
                district_tags.append(d)
    return content_tags + district_tags


# ===== Re-tag all curated event JSONs =====
# Replace tags entirely (not merge) since these are pipeline-generated and we want to fix FPs

def retag_all():
    out_dir = "events/curated"
    files = sorted(glob.glob(os.path.join(out_dir, "*.json")))
    print(f"Found {len(files)} curated event JSONs", flush=True)
    
    updated = 0
    unchanged = 0
    for fpath in files:
        with open(fpath, "r") as f:
            ev = json.load(f)
        
        old_tags = list(ev.get("tags", []))
        
        # Re-tag using updated auto_tag logic (replace entirely)
        new_auto_tags = auto_tag(
            ev.get("title", ""),
            ev.get("description", ""),
            ev.get("location", ""),
            ev.get("organizer", "")
        )
        
        ev["tags"] = new_auto_tags
        
        if ev["tags"] != old_tags:
            with open(fpath, "w") as f:
                json.dump(ev, f, ensure_ascii=False, indent=2)
            updated += 1
        else:
            unchanged += 1
    
    print(f"Updated {updated} / {len(files)} files ({unchanged} unchanged)", flush=True)


if __name__ == "__main__":
    retag_all()
