#!/usr/bin/env python3
"""
scrape_and_merge.py — Scrape all sources, dedup, tag, detect recurring, output JSON.

Output: One JSON file per curated event in events/curated/{date}_{slug}.json
         (nicely formatted, 2-space indent, one file per event)
         
Usage:  python3 scrape_and_merge.py
        python3 scrape_and_merge.py --sources "Bruchsal,Weingarten"
        
Keep run_pipeline.py working for now (old flow still valid).
"""

import json, sys, os, re, html, hashlib
from concurrent.futures import ThreadPoolExecutor, as_completed
from collections import defaultdict
from datetime import datetime, timedelta
from calendar import month_name
import importlib.util

for mod in ["scraper_vhs", "scraper_gewerbeverein", "scraper_blutspende", "scraper_pestalozzi", "scraper_wochenmarkt", "scraper_waldstadt", "scraper_vsv_buechig", "scraper_eggenstein", "scraper_rintheim", "scraper_linkenheim", "scraper_graben_neudorf", "scraper_weingarten", "scraper_bruchsal", "scraper_tsg_blankenloch", "scraper_cvjm_graben_neudorf", "scraper_karlsdorf_neuthard", "scraper_karlsruhe", "scraper_kultcafe", "scraper_bretten"]:
    spec = importlib.util.spec_from_file_location(mod, f"{mod}.py")
    m = importlib.util.module_from_spec(spec)
    sys.modules[mod] = m
    spec.loader.exec_module(m)

scrape_vhs = sys.modules["scraper_vhs"].scrape_vhs
scrape_gewerbeverein = sys.modules["scraper_gewerbeverein"].scrape_gewerbeverein
scrape_blutspende = sys.modules["scraper_blutspende"].scrape_blutspende
scrape_pestalozzi = sys.modules["scraper_pestalozzi"].scrape_pestalozzi
scrape_wochenmarkt = sys.modules["scraper_wochenmarkt"].scrape_wochenmarkt
scrape_waldstadt = sys.modules["scraper_waldstadt"].scrape_waldstadt
scrape_vsv_buechig = sys.modules["scraper_vsv_buechig"].scrape_vsv_buechig
scrape_eggenstein = sys.modules["scraper_eggenstein"].scrape_eggenstein
scrape_rintheim = sys.modules["scraper_rintheim"].scrape_rintheim
scrape_linkenheim = sys.modules["scraper_linkenheim"].scrape_linkenheim
scrape_graben_neudorf = sys.modules["scraper_graben_neudorf"].scrape_graben_neudorf
scrape_weingarten = sys.modules["scraper_weingarten"].scrape_weingarten
scrape_bruchsal = sys.modules["scraper_bruchsal"].scrape_bruchsal
scrape_tsg_blankenloch = sys.modules["scraper_tsg_blankenloch"].scrape_tsg_blankenloch
scrape_cvjm_graben_neudorf = sys.modules["scraper_cvjm_graben_neudorf"].scrape_cvjm_graben_neudorf
scrape_karlsdorf_neuthard = sys.modules["scraper_karlsdorf_neuthard"].scrape_karlsdorf_neuthard
scrape_karlsruhe = sys.modules["scraper_karlsruhe"].scrape_karlsruhe
scrape_kultcafe = sys.modules["scraper_kultcafe"].scrape_kultcafe
scrape_bretten = sys.modules["scraper_bretten"].scrape_bretten
from scraper_clubs import scrape_clubs

OUT_DIR = "events/curated"


def fetch_url(url, timeout=30):
    import urllib.request
    req = urllib.request.Request(url, headers={"User-Agent": "StutenseeEvents/1.0"})
    resp = urllib.request.urlopen(req, timeout=timeout)
    return resp.read().decode("utf-8", errors="replace")


def scrape_official():
    events = []
    base = "https://stutensee.de/Veranstaltungen?item=eventDate&view=find&doPage=1&limit=15&doShowSearch=2&doCropPreviewImages=1&offset={}"
    for page in range(10):
        offset = page * 15
        html_content = fetch_url(base.format(offset))
        blocks = re.findall(
            r'<div class="cVeka_box_eventDate">(.*?)<div style="clear:\s*both;"></div>\s*</div>',
            html_content, re.DOTALL
        )
        for b in blocks:
            title_m = re.search(r'<div class="cVeka_box_title">\s*<a[^>]*href="([^"]*)"[^>]*>([^<]+)</a>', b)
            date_m = re.search(r'<abbr[^>]*>([^<]+)</abbr>,\s*([\d.]+)', b)
            time_m = re.search(r'class="cVeka_box_time">([^<]+)', b)
            loc_m = re.search(r'class="cVeka_box_location">(.*?)(?:<br\s*/?>|</div>)', b, re.DOTALL)
            org_m = re.search(r'class="cVeka_box_organizer">(.*?)(?:<br\s*/?>|</div>)', b, re.DOTALL)
            desc_m = re.search(r'class="cVeka_box_teaser">([^<]+)', b)
            title = title_m.group(2).strip() if title_m else ""
            event_url = title_m.group(1).strip() if title_m else ""
            date_str = date_m.group(2).strip() if date_m else ""
            time_str = re.sub(r'<[^>]+>', '', time_m.group(1)).strip() if time_m else ""
            loc = re.sub(r'<[^>]+>', '', loc_m.group(1)).strip() if loc_m else ""
            org = re.sub(r'<[^>]+>', '', org_m.group(1)).strip() if org_m else ""
            org = re.sub(r'^Veranstalter:\s*', '', org)
            desc = desc_m.group(1).strip() if desc_m else ""
            try:
                parts = date_str.split(".")
                y = "20" + parts[2] if len(parts[2]) == 2 else parts[2]
                iso_date = f"{y}-{parts[1].zfill(2)}-{parts[0].zfill(2)}"
            except:
                iso_date = ""
            events.append({"title": title, "date_start": iso_date, "date_end": None,
                "time_raw": time_str, "location": loc, "organizer": org,
                "description": desc, "event_url": html.unescape(event_url)})
    return {"source_url": "https://stutensee.de/Veranstaltungen", "events": events}


def scrape_kinderkalender():
    events = []
    base = "https://stutenseekinderkalender.de/wp-json/tribe/events/v1/events/?per_page=50&start_date=2025-01-01+00%3A00%3A00&end_date=2029-12-31+23%3A59%3A59&status=publish&page={}"
    page = 1
    while True:
        data = json.loads(fetch_url(base.format(page)))
        for e in data.get("events", []):
            title = html.unescape(e.get("title", ""))
            start = e.get("start_date", "")
            end = e.get("end_date", "")
            v = e.get("venue", {}) or {}
            venue = v.get("venue", "") if isinstance(v, dict) else ""
            va = ", ".join(p for p in [v.get(k, "") for k in ["address", "city", "zip"]] if p) if isinstance(v, dict) else ""
            od = e.get("organizer", []) or []
            orgs = [o.get("organizer", "") for o in (od if isinstance(od, list) else [od]) if isinstance(o, dict)]
            desc = e.get("description", "").strip() or ""
            desc = re.sub(r'<[^>]+>', '', desc)
            desc = html.unescape(desc)
            events.append({"title": title, "date_start": start[:10] if start else "",
                "date_end": end[:10] if end else "", "time_raw": start[11:16] if len(start) > 16 else "",
                "location": f"{venue}, {va}".strip(", "), "organizer": "; ".join(o for o in orgs if o),
                "description": html.unescape(desc), "event_url": e.get("url", "")})
        if not data.get("next_rest_url"):
            break
        page += 1
    return {"source_url": "https://stutenseekinderkalender.de", "events": events}


def parse_meinstutensee_date(start):
    if not start:
        return "", ""
    date_part = start.split("T")[0]
    time_part = ""
    if "T" in start:
        tm = re.search(r'(\d{1,2}:\d{2})', start.split("T")[1])
        if tm:
            time_part = tm.group(1)
    try:
        parts = date_part.split("-")
        y = parts[0]
        m = parts[1].zfill(2) if len(parts) > 1 else "01"
        d = parts[2].zfill(2) if len(parts) > 2 else "01"
        iso_date = f"{y}-{m}-{d}"
        datetime.strptime(iso_date, "%Y-%m-%d")
        return iso_date, time_part
    except:
        return "", ""


def extract_jsonld_value(data, key):
    val = data.get(key, {}) or {}
    if isinstance(val, list):
        if val and isinstance(val[0], dict):
            return val[0].get("name", "")
        return ""
    if isinstance(val, dict):
        return val.get("name", "")
    return ""


def scrape_meinstutensee():
    events = []
    html_content = fetch_url("https://meinstutensee.de/termine/")
    for schema in re.findall(r'<script type="application/ld\+json">(.*?)</script>', html_content, re.DOTALL):
        try:
            data = json.loads(schema)
            if isinstance(data, dict) and data.get("@type") == "Event":
                start = data.get("startDate", "")
                iso_date, time_str = parse_meinstutensee_date(start)
                if not iso_date:
                    continue
                end = data.get("endDate", "")
                end_date = ""
                if end:
                    end_date, _ = parse_meinstutensee_date(end)
                desc = data.get("description", "") or ""
                desc = re.sub(r'<[^>]+>', '', desc).strip()
                events.append({"title": data.get("name", ""), "date_start": iso_date,
                    "date_end": end_date,
                    "time_raw": time_str,
                    "location": extract_jsonld_value(data, "location"),
                    "organizer": extract_jsonld_value(data, "organizer"),
                    "description": html.unescape(desc), "event_url": data.get("url", "")})
        except:
            pass
    return {"source_url": "https://meinstutensee.de/termine/", "events": events}


def scrape_buergerwerkstatt():
    events = []
    html_content = fetch_url("https://buergerwerkstatt-stutensee.de/veranstaltungen/")
    for art in re.findall(r'<article[^>]*class="teaser[^"]*"[^>]*>(.*?)</article>', html_content, re.DOTALL):
        title_m = re.search(r'<h5[^>]*class="entry-header-teaser"[^>]*>([^<]+)</h5>', art)
        link_m = re.search(r'<a[^>]*class="read-more"[^>]*href="([^"]+)"', art)
        desc_m = re.search(r'<div[^>]*class="entry-content-teaser"[^>]*>(.*?)</div>', art, re.DOTALL)
        desc = re.sub(r'<[^>]+>', '', desc_m.group(1)).strip() if desc_m else ""
        dm = re.search(r'(\d{2})\.(\d{2})\.(\d{4})', desc)
        iso = f"{dm.group(3)}-{dm.group(2)}-{dm.group(1)}" if dm else ""
        tm = re.search(r'um\s*(\d{1,2})\s*Uhr', desc)
        ts = f"{tm.group(1).zfill(2)}:00" if tm else ""
        events.append({"title": title_m.group(1).strip() if title_m else "",
            "date_start": iso, "date_end": None, "time_raw": ts,
            "location": "Mehrgenerationenhaus Bürgerwerkstatt Stutensee e.V., Seegrabenweg 5, 76297 Stutensee",
            "organizer": "", "description": desc, "event_url": link_m.group(1).strip() if link_m else ""})
    return {"source_url": "https://buergerwerkstatt-stutensee.de/veranstaltungen/", "events": events}


def scrape_optional(url, name, source_url=None):
    try:
        html_content = fetch_url(url, timeout=8)
        return {"source_url": source_url or url, "events": [{"_raw": True}], "_html": html_content}
    except Exception as e:
        print(f"skip ({e})", flush=True)
        return None


def scrape_buechigerleben():
    from bs4 import BeautifulSoup
    events = []
    try:
        html = fetch_url("https://www.buechigerleben.de/", timeout=10)
    except Exception as e:
        print(f"  Error: {e}", flush=True)
        return {"source_url": "https://www.buechigerleben.de/", "events": []}
    soup = BeautifulSoup(html, "lxml")
    lines = [l.strip() for l in soup.get_text(separator="\n").split("\n") if l.strip()]
    section_start = None
    for i, line in enumerate(lines):
        if "Veranstaltungen" in line and "Projekte" in line:
            section_start = i + 1
            break
    if section_start is None:
        return {"source_url": "https://www.buechigerleben.de/", "events": []}
    i = section_start
    while i < len(lines):
        line = lines[i]
        dm = re.match(r'(\d{2})\.(\d{2})\.(\d{2})$', line)
        if dm:
            d, mth, y = dm.group(1), dm.group(2), "20" + dm.group(3)
            iso = f"{y}-{mth.zfill(2)}-{d.zfill(2)}"
            i += 1
            time_str = ""
            title = ""
            if i < len(lines) and re.match(r'[\d:ab\s-]+Uhr', lines[i]):
                time_str = lines[i].split(",")[0].strip()
                i += 1
            loc = ""
            if i < len(lines) and re.match(r'^[A-Za-z]', lines[i]) and "Mittagstisch" not in lines[i] and "Maifest" not in lines[i] and "Sommerfest" not in lines[i] and "Laternenfest" not in lines[i] and "Adventsfest" not in lines[i] and not re.match(r'\d{2}\.', lines[i]):
                loc = lines[i]
                i += 1
            if i < len(lines):
                title = lines[i]
                i += 1
                if title in ("Maifest", "Sommerfest", "Laternenfest", "Adventsfest"):
                    title += " Büchig"
            desc = ""
            if title.startswith("Mittagstisch") and i < len(lines) and not re.match(r'\d{2}\.', lines[i]) and "Büchig(er)" not in lines[i]:
                desc = lines[i]
                i += 1
                title = f"Mittagstisch \u2013 {desc}"
            if title:
                events.append({"title": title, "date_start": iso, "date_end": None,
                    "time_raw": time_str, "location": loc or "B\u00fcchig",
                    "organizer": "B\u00fcchig(er)leben", "description": "",
                    "event_url": "https://www.buechigerleben.de/"})
        else:
            i += 1
    seen = set()
    deduped = []
    for e in events:
        key = (e["title"], e["date_start"])
        if key not in seen:
            seen.add(key)
            deduped.append(e)
    return {"source_url": "https://www.buechigerleben.de/", "events": deduped}


def parse_german_date(text):
    dm = re.search(r'(\d{1,2})\.\s*([A-Za-z]+)\s*(\d{4})', text)
    if not dm:
        return ""
    months = {m.lower(): i for i, m in enumerate(month_name) if m}
    month_num = months.get(dm.group(2).lower())
    if not month_num:
        return ""
    return f"{dm.group(3)}-{str(month_num).zfill(2)}-{dm.group(1).zfill(2)}"


def is_past(iso_date):
    if not iso_date:
        return False
    try:
        return datetime.strptime(iso_date, "%Y-%m-%d").date() < datetime.now().date()
    except:
        return True


def scrape_flohmarkt():
    events = []
    html_content = fetch_url("https://www.flohmarkt-buechig.de/")
    iso = parse_german_date(html_content)
    if iso and not is_past(iso):
        events.append({"title": "Flohmarkt B\u00fcchig", "date_start": iso, "date_end": None,
            "time_raw": "", "location": "Festhalle Blankenloch", "organizer": "Flohmarkt Kitas B\u00fcchig",
            "description": "", "event_url": "https://www.flohmarkt-buechig.de/"})
    return {"source_url": "https://www.flohmarkt-buechig.de/", "events": events}


BLOCKED_TITLES = [
    "Krabbelk\u00e4fer Stutensee-B\u00fcchig \u2013 gem\u00fctliches Beisammensein mit Fr\u00fchst\u00fcck",
    "Bereitschaftsabend (\u00dcbungsabend)",
    "Chorprobe Gospel Unlimited",
    "Chorprobe Posaunenchor Blankenloch",
    "JRK Gruppenstunde",
    "Paddeltraining f\u00fcr Erwachsene (Sommer)",
    "Treffen f\u00fcr Vorst\u00e4nde und Verantwortliche",
    "Altpapiersammlung",
    "Mittagstisch \u2013 Wir veranstalten abends unseren Sommerbiergarten, deswegen m\u00fcssen wir den Mittagstisch leider absagen.",
]

BLOCKED_PREFIXES = [
    "Altpapiersammlung",
]

MANUAL_ORG_MERGE = {
    "Gesamtelternbeirat": "Gesamtelternbeirat und Eltern der Stutenseer Kindergärten",
}


MANUAL_DUPES = {
    "H\u00e4hnchen Grillfest": ["H\u00e4hnchenfest"],
    "Sommerfest am Baggersee": ["Sommerfest"],
}

MANUAL_EVENTS = [
    {"title": "U16 KVV Pokalfinale", "date_start": "2026-05-13", "date_end": None, "time_raw": "", "location": "Friedrichstal", "organizer": "FC Germania Friedrichstal", "description": "KVV Pokalfinale der U16", "event_url": "https://www.fcfriedrichstal.de/"},
    {"title": "Fahrradtour am 1. Mai 2026", "date_start": "2026-05-01", "date_end": None, "time_raw": "", "location": "Alte Schule Sp\u00f6ck", "organizer": "DLRG Ortsgruppe Sp\u00f6ck", "description": "", "event_url": "https://spoeck.dlrg.de/"},
    {"title": "Chorwochenende", "date_start": "2027-03-19", "date_end": None, "time_raw": "", "location": "", "organizer": "Gospel Unlimited", "description": "", "event_url": "https://www.gospel-unlimited.de"},
    {"title": "Badentreff", "date_start": "2026-06-03", "date_end": "2026-06-06", "time_raw": "", "location": "CVJM Sp\u00f6ck", "organizer": "CVJM Sp\u00f6ck", "description": "", "event_url": "https://www.cvjm-spoeck.de/"},
]

DISTRICTS = {
    "Blankenloch": ["blankenloch", "bl.", "mehrgenerationenhaus", "b\u00fcrgerwerkstatt", "seegrabenweg", "gymnasiumstr", "zukunftshaus"],
    "B\u00fcchig": ["b\u00fcchig", "buechig"],
    "Friedrichstal": ["friedrichstal", "sp\u00f6cker weg", "spoecker weg"],
    "Sp\u00f6ck": ["sp\u00f6ck", "spoeck"],
    "Staffort": ["staffort"],
    "Weingarten": ["weingarten", "weingarten (baden)", "mineralix-arena", "walzbachhalle"],
    "Hagsfeld": ["hagsfeld"],
    "B\u00fcchenau": ["b\u00fcchenau", "buechenau"],
    "Neuthard": ["neuthard", "karlsdorf", "karlsdorf-neuthard", "zehntscheuer"],
    "Waldstadt": ["waldstadt", "bv-waldstadt"],
    "Neureut": ["neureut", "badnerlandhalle", "kunstraum neureut", "neureuter platz", "stadtteilbibliothek neureut"],
    "Eggenstein": ["eggenstein"],
    "Leopoldshafen": ["leopoldshafen"],
    "Rintheim": ["rintheim"],
    "Linkenheim": ["linkenheim", "linkenheim-hochstetten"],
    "Graben-Neudorf": ["graben-neudorf"],
    "Bruchsal": ["bruchsal"],
    "Bretten": ["bretten"],
}

DISTRICT_EXCLUSIONS = {
    "Sp\u00f6ck": ["sp\u00f6cker weg", "spoecker weg"],
    "B\u00fcchenau": ["staffort-b\u00fcchenau", "staffort b\u00fcchenau"],
}

KEYWORDS = {
    "Sport": ["stadtlauf", "triathlon", "tennis", "turnen", "fitness", "yoga", "pilates", "tischtennis", "fu\u00dfball", "fussball", "schwimm", "rad", "bike", "cycling", "sport", "bewegung", "gymnastik", "tanz", "dance", "ballett", "kickbox", "karate", "indiaca", "volleyball", "handball", "basketball", "reiten", "pferd", "wandern", "training", "spechaa", "turnier", "kajak", "kanu", "dressur", "springturnier", "reitturnier", "meisterschaft", "pokalfinale", "segeln", "regatta", "gleitschirm", "sportwoche", "radtour", "wanderung"],
    "Musik": ["konzert", "chor", "gesang", "musik", "band", "jazz", "singen", "lieder", "klang", "musikal", "orchester", "posaunen", "gitarre", "vox", "choir", "swing", "liederabend", "gospel", "rockfestival", "siyou"],
    "Kultur": ["theater", "lesung", "kunst", "ausstellung", "kino", "literatur", "b\u00fchne", "kultur", "museum", "foto", "malen", "zeichnen", "denkmals", "salsa", "vernissage", "modellbahn",
               "garde", "fasching", "karneval", "kost\u00fcm", "tanzgruppe"],
    "Kirche": ["gottesdienst", "kirche", "konfirmation", "firmung", "taufe", "messe", "andacht", "segen", "\u00f6kumen", "patrozinium", "gebet", "evangelisch", "katholisch", "trauer", "abendmahl", "kommunion", "herzensgebet", "maiandacht", "bibelkreis", "bibelgespr\u00e4ch", "bibelstunde", "vesper", "kreuzweg", "volkstrauertag", "allerseelen", "allerheiligen", "glaubenskurs", "religionsunterricht"],
    "Kinder": ["kind", "baby", "eltern-kind", "krabbel", "spiel", "familie", "m\u00e4dchen", "junge", "kindergarten", "schule", "vorlesen", "bilderbuch", "k\u00fcken", "seepferdchen", "abenteuer", "zwerge", "jugend", "teen", "sch\u00fcler", "kinderturnen", "ferien", "caribi", "minis", "bambini", "steckenpferd", "drachen", "lager", "ballontag", "halloween", "gruselnacht", "modellflug", "scoutcamp", "ferienspa\u00df", "nikolaus", "camp", "w\u00f6lfling"],
    "Fest": ["fest", "oktoberfest", "maifest", "weihnachtsmarkt", "kerwe", "party", "sportfest", "maibaum", "fr\u00fchlingsfest", "sommerfest", "jubil\u00e4um", "vatertagsfest", "abschlussfeier", "thanksgiving", "neujahr", "adventzauber", "wintergl\u00fchen", "weihnachtskorso", "heimattage", "steinwiesenfest", "k\u00fcrbisfest", "h\u00e4hnchenfest", "fischerfest", "apfelbl\u00fctenfest", "kinderspielfest", "pfingstfeier"],
    "Markt": ["markt", "flohmarkt", "tr\u00f6del", "weihnachtsmarkt", "verkaufsoffener", "herbstmarkt", "hofflohmarkt", "frauenflohmarkt", "bauernmarkt"],
    "Workshop": ["workshop", "kurs", "seminar", "unterricht", "training"],
    "Bildung": ["bildung", "vortrag", "schule", "vhs", "diskussion", "fortbildung", "lesen",
               "lernen", "infoveranstaltung", "podiumsdiskussion", "ausbildungsplattform", "schulkonferenz"],
    "Natur": ["natur", "wald", "vogel", "vögel", "baum", "pflanze", "umwelt", "klima",
               "hornisse", "mulchen", "exkursion", "wanderung",
               "gartenfest", "gartenarbeit", "gartengestaltung", "gartenbau"],
    "Senioren": ["senior", "50+", "\u00e4lter", "alt werden", "beweglich im alter"],
    "Digital": ["digital", "smartphone", "computer", "handy", "online", "internet"],
    "Handwerk": ["basteln", "werkstatt", "n\u00e4hen", "stricken", "h\u00e4keln", "reparier", "reparatur", "handarbeit", "secondhand", "bastel", "sonnenf\u00e4nger"],
    "Essen": ["kochen", "backen", "grill", "fr\u00fchst\u00fcck", "k\u00fcche", "kuchen", "kaffee", "bowle", "bier", "weinprobe", "h\u00e4hnchen", "flammkuchen", "zwiebelkuchen", "mittagstisch", "dampfnudel"],
    "Treff": ["treff", "caf\u00e9", "stammtisch", "begegnung", "gespr\u00e4ch", "runde", "kreis", "spieleabend", "badentreff", "m\u00e4nnerrunde", "selbsthilfe", "afterwork", "clubhaus", "fr\u00fchschoppen", "netzwerktreffen"],
    "Politik": ["gemeinderat", "b\u00fcrgermeister", "politik", "partei", "ausschuss", "b\u00fcrgermeisterkandidaten", "einwohnerversammlung", "bürgerkönig", "ortschaftsrat", "verwaltungsausschuss", "ob-kandidaten", "ob-wahl", "kandidatenvorstellung"],
    "Verein": ["verein", "e.v.", "mitgliederversammlung", "vorstand", "ehrenamt", "clubabend", "hobbyday", "vorstandsmeeting", "arbeitseinsatz", "stammesklausur", "hobbylager", "baueinsatz", "jahreshauptversammlung", "jahreshauptübung", "hobbytag", "vereinsforum"],
    "Wohlt\u00e4tigkeit": ["spende", "blutspende", "kleidersammlung", "charity", "sozial", "tafel",
                       "hilfe", "sanit\u00e4tsdienst"],
}


def normalize_title(title):
    if not title:
        return ""
    t = title.lower().strip()
    for suffix in [' in blankenloch', ' in b\u00fcchig', ' in friedrichstal', ' in sp\u00f6ck', ' in staffort',
                    ' blankenloch', ' b\u00fcchig', ' friedrichstal', ' sp\u00f6ck', ' staffort']:
        t = t.replace(suffix, '')
    return t


def normalize_location(location):
    if not location:
        return ""
    loc = location.strip()
    idx = loc.find(',')
    if idx > 0:
        return loc[:idx].strip()
    return loc


def normalize_location_dedup(location):
    if not location:
        return ""
    loc = location.strip().lower()
    for district in ["blankenloch", "b\u00fcchig", "buechig", "friedrichstal", "sp\u00f6ck", "spoeck", "staffort", "stutensee"]:
        if district in loc:
            return district
    for district, keywords in DISTRICTS.items():
        for kw in keywords:
            if kw in loc:
                return district
    idx = loc.find(',')
    return loc[:idx].strip() if idx > 0 else loc


TITLE_EXCLUSIVE_TAGS = {
    "krabbelgruppe": "Kinder",
    "fit in der schwangerschaft": "Kinder",
    "v\u00f6gel": "Natur",
}

# Titles that always get specific tags added after truncation (no override, just addition)
TITLE_ALWAYS_TAGS = {
    "tanzen f\u00fcr die kleinsten": ["Kinder"],
    "4-6 jahre": ["Kinder"],
    "3\u20136 jahre": ["Kinder"],
    "seesternchengarde": ["Kinder"],
    # One-off cases for untagged events (Issue #123)
    "remember in concert": ["Musik"],
    "landesmeutenaktion (lama)": ["Natur"],
    "f\u00eate de la musique": ["Musik"],
    "abifeier": ["Fest"],
    "'leben im alter - denken h\u00e4lt fit'": ["Senioren"],
    "aktionstage 60+": ["Senioren"],
    "herbstfahrt 2026": ["Natur"],
    "gemarkungsputzete": ["Natur"],
    "thanksgivin\u2018": ["Fest"],
    "gro\u00dfer pflegetag": ["Senioren"],
    "kampagne er\u00f6ffnung / inthronisation": ["Kultur"],
    "saueressen kirwe": ["Fest"],
    "adventskranzbinden": ["Workshop"],
}

# Known false positive substrings: when found in title/description, remove the tag.
FALSE_POSITIVE_CLEANUP = {
    "Essen": ["bieringer", "bieringer-str"],
    "Fest": ["standfest"],
    "Kirche": ["lutherkirche", "messen"],
    "Natur": ["waldstadt"],
    "Sport": ["jam session", "jam-session", "konrad", "bereiten"],
    "Musik": ["k\u00fckenstube", "eltern-baby-caf\u00e9", "krabbelgruppe", "eltern-kind-kreis",
               "eltern-kind-caf\u00e9", "eltern-kind-gruppe", "babycaf\u00e9", "babytreff",
               "choreografien", "mitgliedern", "mitglieder"],
    "Workshop": ["jugendrotkreuz", "pfadfind"],
}

ORGANIZER_EXCLUSIVE_TAGS = {
    "agendagruppe umwelt": "Natur",
    "fc ": "Sport",
    "jugendzentrum graubau": "Blankenloch",
    "vogelliebhaber graben": "Graben-Neudorf",
    "cvjm": "Kirche",
}


def auto_tag(title, description="", location="", organizer=""):
    title_lower = (title or "").lower()

    content_tags = []
    organizer_tag = None
    for exclusive_kw, forced_tag in TITLE_EXCLUSIVE_TAGS.items():
        if exclusive_kw in title_lower:
            content_tags = [forced_tag]
            break

    if not content_tags:
        org_lower = (organizer or "").lower()
        for exclusive_kw, forced_tag in ORGANIZER_EXCLUSIVE_TAGS.items():
            if exclusive_kw in org_lower:
                organizer_tag = forced_tag
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

    # Re-apply mandatory tags for specific titles after truncation (always runs)
    for title_trigger, extra_tags in TITLE_ALWAYS_TAGS.items():
        if title_trigger in title_lower:
            for t in extra_tags:
                if t not in content_tags:
                    content_tags.append(t)

    if organizer_tag and organizer_tag not in content_tags:
        content_tags.append(organizer_tag)

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


def slugify(title, max_len=60):
    s = title.lower().strip()
    s = s.replace('\u00e4', 'ae').replace('\u00f6', 'oe').replace('\u00fc', 'ue').replace('\u00df', 'ss')
    s = re.sub(r'[^a-z0-9\s-]', '', s)
    s = re.sub(r'[\s-]+', '-', s).strip('-')
    if len(s) > max_len:
        s = s[:max_len].rstrip('-')
    return s or "event"


def build_filename(event):
    date = event.get("date_start", "unknown") or "unknown"
    slug = slugify(event.get("title", "event"))
    return f"{date}_{slug}.json"


def dedup_events(raw_events):
    events = []
    for ev in raw_events:
        if ev.get("title", "") in BLOCKED_TITLES:
            continue
        title = ev.get("title", "")
        if any(title.startswith(p) for p in BLOCKED_PREFIXES):
            continue
        if is_past(ev.get("date_start", "")):
            continue
        if not ev.get("title", "").strip():
            continue
        date = ev.get("date_start", "") or ""
        if date and not re.match(r'\d{4}-\d{2}-\d{2}', date):
            continue
        # Clean titles: strip leading/trailing quotes from scraped data
        title = ev.get("title", "")
        if len(title) > 2 and title.startswith('"') and title.endswith('"'):
            title = title[1:-1].strip()
            ev["title"] = title
        # Guard against empty title after cleanup
        if not ev.get("title", "").strip():
            ev["title"] = f'Untitled ({ev.get("date_start", "unknown")})'
        events.append(ev)

    groups = defaultdict(list)
    for ev in events:
        key = (normalize_title(ev.get("title", "")), ev.get("date_start", "") or "", normalize_location(ev.get("location", "")))
        groups[key].append(ev)

    curated = []
    for key, evs in groups.items():
        best = max(evs, key=lambda e: len(e.get("description", "") or ""))
        merged = dict(best)
        merged["sources"] = sorted(set(
            s for ev in evs for s in (ev.get("_source_url", "").split(",") if ev.get("_source_url") else [])
        ))
        merged["sources"] = sorted(set(
            s.strip() for ev in evs
            for s in (ev.get("_source_url", "") or "").split(",") if s.strip()
        ))
        curated.append(merged)

    curated.sort(key=lambda e: (e.get("date_start", "") or "", e.get("title", "") or ""))

    merged = 0
    date_groups = defaultdict(list)
    for i, ev in enumerate(curated):
        dedup_key = normalize_location_dedup(ev.get("location", ""))
        date_groups.setdefault((ev.get("date_start", "") or "", dedup_key), []).append(i)

    def compact(lst):
        return [e for e in lst if e is not None]

    for candidates in date_groups.values():
        while True:
            match = None
            for i, a_idx in enumerate(candidates):
                if curated[a_idx] is None:
                    continue
                for b_idx in candidates[i+1:]:
                    if curated[b_idx] is None:
                        continue
                    a, b = curated[a_idx], curated[b_idx]
                    at = normalize_title(a.get("title", ""))
                    bt = normalize_title(b.get("title", ""))
                    if at == bt or (len(at) > 6 and len(bt) > 6 and (at in bt or bt in at or at.replace(' ','') in bt.replace(' ','') or bt.replace(' ','') in at.replace(' ',''))):
                        a_org = re.sub(r'[\s\.,;:-]+', '', ((a.get("organizer") or "") or "").lower())
                        b_org = re.sub(r'[\s\.,;:-]+', '', ((b.get("organizer") or "") or "").lower())
                        if a_org == b_org:
                            match = (a_idx, b_idx)
                            break
                if match:
                    break
            if not match:
                break
            a_idx, b_idx = match
            a, b = curated[a_idx], curated[b_idx]
            pick = max([a, b], key=lambda x: len(x.get("description", "") or ""))
            kill = b if pick is a else a
            kill_idx = b_idx if pick is a else a_idx
            merged += 1
            pick["sources"] = sorted(set(pick.get("sources", []) + kill.get("sources", [])))
            curated[kill_idx] = None

    curated = compact(curated)

    cross_date_groups = defaultdict(list)
    for i, ev in enumerate(curated):
        cross_date_groups.setdefault(ev.get("date_start", "") or "", []).append(i)

    for date_key, indices in cross_date_groups.items():
        for i in range(len(indices)):
            a = curated[indices[i]]
            if a is None:
                continue
            for j in range(i+1, len(indices)):
                b = curated[indices[j]]
                if b is None:
                    continue
                at = normalize_title(a.get("title", ""))
                bt = normalize_title(b.get("title", ""))
                if at == bt:
                    continue
                short, long = (at, bt) if len(at) < len(bt) else (bt, at)
                short_ns = short.replace(" ","")
                long_ns = long.replace(" ","")
                long_w = set(long.split())
                match = False
                if len(short_ns) > 6 and len(long_ns) > 6:
                    if (short_ns in long_ns or long_ns in short_ns) and len(short_ns) >= 0.3 * len(long_ns):
                        match = True
                    elif short_ns and all(any(w in word for word in long_w) for w in short_ns.split()):
                        match = True
                if match:
                    a_org = re.sub(r'[\s\.,;:-]+', '', ((a.get("organizer") or "") or "").lower())
                    b_org = re.sub(r'[\s\.,;:-]+', '', ((b.get("organizer") or "") or "").lower())
                    if a_org != b_org:
                        continue
                    pick = max([a, b], key=lambda x: len(x.get("description", "") or ""))
                    kill = b if pick is a else a
                    kill_idx = indices[j] if pick is a else indices[i]
                    merged += 1
                    pick["sources"] = sorted(set(pick.get("sources", []) + kill.get("sources", [])))
                    curated[kill_idx] = None

    curated = compact(curated)

    for canon, variants in MANUAL_DUPES.items():
        cn = normalize_title(canon)
        for i, ev in enumerate(curated):
            if ev is None:
                continue
            if ev.get("title") == canon:
                for j, ev2 in enumerate(curated):
                    if j == i:
                        continue
                    if ev2.get("title") in variants and ev.get("date_start") == ev2.get("date_start"):
                        pick = max([ev, ev2], key=lambda x: len(x.get("description", "") or ""))
                        kill = ev2 if pick is ev else ev
                        kill_idx = j if pick is ev else i
                        merged += 1
                        pick["sources"] = sorted(set(pick.get("sources", []) + kill.get("sources", [])))
                        curated[kill_idx] = None
                        curated[i] = pick if pick is ev else pick
                        break

    curated = compact(curated)

    title_groups = defaultdict(list)
    for i, ev in enumerate(curated):
        title_groups.setdefault((normalize_title(ev.get("title", "")), ev.get("date_start", "") or ""), []).append(i)

    for candidates in title_groups.values():
        if len(candidates) > 1:
            best_idx = max(candidates, key=lambda idx: len(curated[idx].get("description", "") or ""))
            best = curated[best_idx]
            for idx in candidates:
                if idx == best_idx:
                    continue
                merged += 1
                best["sources"] = sorted(set(best.get("sources", []) + curated[idx].get("sources", [])))
                curated[idx] = None

    curated = compact(curated)

    org_groups = defaultdict(list)
    for i, ev in enumerate(curated):
        org = (ev.get("organizer", "") or "").lower().strip()
        org = re.sub(r'\be\.\s*v\.?\b', '', org).strip()
        org = re.sub(r'\beingetragener\s+verein\b', '', org).strip()
        org = re.sub(r'\s+', ' ', org).strip()
        date = ev.get("date_start", "") or ""
        org_groups.setdefault((date, org), []).append(i)

    for candidates in org_groups.values():
        if len(candidates) < 2:
            continue
        best_idx = max(candidates, key=lambda idx: len(curated[idx].get("description", "") or ""))
        best = curated[best_idx]
        best_title_words = set(normalize_title(best.get("title", "")).split())
        for idx in candidates:
            if idx == best_idx:
                continue
            ev = curated[idx]
            ev_words = set(normalize_title(ev.get("title", "")).split())
            common = best_title_words & ev_words
            if len(common) >= 2:
                merged += 1
                best["sources"] = sorted(set(best.get("sources", []) + ev.get("sources", [])))
                curated[idx] = None

    curated = compact(curated)

    if merged:
        print(f"  Post-merge: {merged} duplicates merged (fuzzy)", flush=True)
    # Manual org merge: merge same-date events with matching organizers
    date_org_groups = defaultdict(list)
    for i, ev in enumerate(curated):
        date = ev.get("date_start", "") or ""
        org = (ev.get("organizer", "") or "").lower().strip()
        date_org_groups.setdefault(date, []).append(i)

    for candidates in date_org_groups.values():
        for i_idx in candidates:
            for j_idx in candidates:
                if i_idx >= j_idx or curated[i_idx] is None or curated[j_idx] is None:
                    continue
                a_org = (curated[i_idx].get("organizer", "") or "").lower().strip()
                b_org = (curated[j_idx].get("organizer", "") or "").lower().strip()
                for canonical, variant in MANUAL_ORG_MERGE.items():
                    can_low = canonical.lower().strip()
                    var_low = variant.lower().strip()
                    if (can_low in a_org and can_low in b_org) or (var_low in a_org and var_low in b_org):
                        pick = max([curated[i_idx], curated[j_idx]], key=lambda x: len(x.get("description", "") or ""))
                        kill = curated[j_idx] if pick is curated[i_idx] else curated[i_idx]
                        kill_idx = j_idx if pick is curated[i_idx] else i_idx
                        merged += 1
                        pick["sources"] = sorted(set(pick.get("sources", []) + kill.get("sources", [])))
                        curated[kill_idx] = None
                        break

    curated = compact(curated)

    return curated


def tag_events(curated):
    count = 0
    for ev in curated:
        auto_tags = auto_tag(ev.get("title", ""), ev.get("description", ""), ev.get("location", ""), ev.get("organizer", ""))
        existing_tags = ev.get("tags", [])
        if existing_tags and auto_tags:
            # Merge: keep scraper-set tags, add any auto_tags not already present
            merged = list(existing_tags)
            for t in auto_tags:
                if t not in merged:
                    merged.append(t)
            ev["tags"] = merged
            count += 1
        elif auto_tags:
            ev["tags"] = auto_tags
            count += 1
        # If neither existing_tags nor auto_tags, leave as-is (noop)
    return count


def detect_recurring(curated):
    parse_date = lambda d: datetime.strptime(d, "%Y-%m-%d").date() if d else None

    def gap_type(gap_days):
        if gap_days == 7:
            return "weekly"
        elif gap_days == 14:
            return "biweekly"
        elif 28 <= gap_days <= 31:
            return "monthly"
        return None

    def classify_gaps(gaps):
        if not gaps:
            return None
        n = len(gaps)
        # Count gaps matching each pattern
        weekly = sum(1 for g in gaps if g == 7)
        biweekly = sum(1 for g in gaps if g == 14)
        monthly = sum(1 for g in gaps if 28 <= g <= 31)
        # Majority rule: >50% of gaps match a pattern
        if weekly > n / 2:
            return "weekly"
        if biweekly > n / 2:
            return "biweekly"
        if monthly > n / 2:
            return "monthly"
        # For short sequences (2-3 events), be stricter: all must match
        if n <= 2:
            if all(g == 7 for g in gaps):
                return "weekly"
            if all(g == 14 for g in gaps):
                return "biweekly"
            if all(28 <= g <= 31 for g in gaps):
                return "monthly"
        return None

    for ev in curated:
        ev["recurring_group_id"] = None

    groups = defaultdict(list)
    for i, ev in enumerate(curated):
        d = parse_date(ev.get("date_start"))
        if d is not None:
            groups[ev.get("title", "")].append((i, ev.get("title", ""), d))

    recurring_groups_found = 0
    total_events_linked = 0

    for group_key, events in groups.items():
        if len(events) < 2:
            continue
        events.sort(key=lambda x: x[2])
        gaps = []
        for i in range(1, len(events)):
            gap = (events[i][2] - events[i-1][2]).days
            gaps.append(gap)

        pattern = classify_gaps(gaps)
        if pattern is None:
            continue

        import hashlib
        group_min_id = int(hashlib.md5(group_key.encode()).hexdigest(), 16) % (2**31)
        for idx, _, _ in events:
            curated[idx]["recurring_group_id"] = group_min_id

        recurring_groups_found += 1
        total_events_linked += len(events)

        titles = set(e[1] for e in events)
        display_title = next(iter(titles)) if len(titles) == 1 else group_key
        print(f"  {pattern}: '{display_title[:50]}' \u2014 {len(events)} events, group_id={group_min_id}")

    return recurring_groups_found, total_events_linked


def write_event_json(event, out_dir):
    os.makedirs(out_dir, exist_ok=True)

    sources = event.get("sources", []) or []
    if not sources and event.get("_source_url"):
        sources = [event["_source_url"]]

    tags = event.get("tags", []) or []
    if isinstance(tags, str):
        tags = [t.strip() for t in tags.split(",") if t.strip()]

    ev = {
        "title": event.get("title", ""),
        "date_start": event.get("date_start", ""),
        "date_end": event.get("date_end"),
        "time_raw": event.get("time_raw", ""),
        "location": event.get("location", ""),
        "organizer": event.get("organizer", ""),
        "description": event.get("description", ""),
        "event_url": event.get("event_url", ""),
        "sources": sources,
        "tags": tags,
        "recurring_group_id": event.get("recurring_group_id"),
    }

    filename = build_filename(ev)
    filepath = os.path.join(out_dir, filename)
    new_content = json.dumps(ev, indent=2, ensure_ascii=False) + "\n"

    if os.path.exists(filepath):
        with open(filepath, "r", encoding="utf-8") as f:
            if f.read() == new_content:
                return filename

    with open(filepath, "w", encoding="utf-8") as f:
        f.write(new_content)

    return filename


def main():
    import argparse
    parser = argparse.ArgumentParser(description="Scrape and merge events into JSON")
    parser.add_argument("--sources", help="Comma-separated source names to run (default: all)")
    parser.add_argument("--out", default=OUT_DIR, help=f"Output directory (default: {OUT_DIR})")
    args = parser.parse_args()

    out_dir = args.out
    os.makedirs(out_dir, exist_ok=True)

    print("Scrape and Merge — JSON Pipeline v2", flush=True)
    print(f"Time: {datetime.now().isoformat()}", flush=True)
    if args.sources:
        print(f"Sources: {args.sources}", flush=True)

    sources = [
        ("Official calendar", scrape_official),
        ("Kinderkalender", scrape_kinderkalender),
        ("meinstutensee.de", scrape_meinstutensee),
        ("B\u00fcrgerwerkstatt events", scrape_buergerwerkstatt),
        ("B\u00fcchigerleben", scrape_buechigerleben),
        ("Flohmarkt", scrape_flohmarkt),
        ("VHS Stutensee", scrape_vhs),
        ("Gewerbeverein", scrape_gewerbeverein),
        ("Blutspende", scrape_blutspende),
        ("Pestalozzi Schule", scrape_pestalozzi),
        ("Wochenmarkt", scrape_wochenmarkt),
        ("B\u00fcrgerverein Waldstadt", scrape_waldstadt),
        ("Club websites (39 sites)", scrape_clubs),
        ("VSV B\u00fcchig", scrape_vsv_buechig),
        ("Eggenstein-Leopoldshafen", scrape_eggenstein),
        ("Rintheim", scrape_rintheim),
        ("Linkenheim-Hochstetten", scrape_linkenheim),
        ("Graben-Neudorf", scrape_graben_neudorf),
        ("Weingarten", scrape_weingarten),
        ("Bruchsal", scrape_bruchsal),
        ("TSG Blankenloch", scrape_tsg_blankenloch),
        ("CVJM Graben-Neudorf", scrape_cvjm_graben_neudorf),
        ("Karlsdorf-Neuthard", scrape_karlsdorf_neuthard),
        ("Karlsruhe (Hagsfeld/Neureut/Rintheim/Waldstadt)", scrape_karlsruhe),
        ("Kult Café Friedrichstal", scrape_kultcafe),
        ("Bretten", scrape_bretten),
    ]
    optional_sources = [
        ("Kath. Kirche", "https://www.kath-weistu.de/", "https://www.kath-stutensee-weingarten.de/"),
        ("Bibliothek", "https://bibliotheken.komm.one/stutensee", None),
    ]

    source_filter = [s.strip() for s in args.sources.split(",")] if args.sources else None
    if source_filter:
        filtered = [(n, s) for n, s in sources if n in source_filter]
        not_found = [s for s in source_filter if s not in dict(sources)]
        if not_found:
            print(f"  Warning: sources not found: {', '.join(not_found)}", flush=True)
        sources = filtered

    all_raw = []
    total_new = 0

    def scrape_one(name_scraper):
        name, scraper_func = name_scraper
        try:
            data = scraper_func()
            for ev in data.get("events", []):
                ev["_source_url"] = data.get("source_url", "")
            return name, len(data["events"]), data["events"], None
        except Exception as e:
            return name, 0, [], str(e)

    with ThreadPoolExecutor(max_workers=8) as executor:
        futures = {executor.submit(scrape_one, s): s[0] for s in sources}
        for future in as_completed(futures):
            name = futures[future]
            try:
                name, fetched, evts, err = future.result()
                if err:
                    print(f"  {name}: ERROR: {err}", flush=True)
                else:
                    total_new += len(evts)
                    all_raw.extend(evts)
                    print(f"  {name}: {fetched} fetched, {len(evts)} new", flush=True)
            except Exception as e:
                print(f"  {name}: ERROR: {e}", flush=True)

    for name, url, src_url in optional_sources:
        print(f"  Scraping {name}...", end=" ", flush=True)
        result = scrape_optional(url, name, src_url)
        if result:
            print(f"available", flush=True)
        else:
            print(f"skipped", flush=True)

    print(f"  Injecting manual events...", end=" ", flush=True)
    for ev in MANUAL_EVENTS:
        ev["_source_url"] = "manual_override"
        all_raw.append(ev)
    print(f"{len(MANUAL_EVENTS)} injected", flush=True)

    print(f"  Total raw: {len(all_raw)}", flush=True)

    print(f"  Dedup...", end=" ", flush=True)
    curated = dedup_events(all_raw)
    print(f"{len(curated)} curated", flush=True)

    print(f"  Tagging...", end=" ", flush=True)
    tagged = tag_events(curated)
    print(f"{tagged} tagged", flush=True)

    print(f"  Recurring detection...", end=" ", flush=True)
    num_groups, num_linked = detect_recurring(curated)
    print(f"  done", flush=True)
    if num_groups:
        print(f"Recurring groups found: {num_groups}", flush=True)
        print(f"Total events linked: {num_linked}", flush=True)

    existing = set()
    if os.path.isdir(out_dir):
        existing = set(os.listdir(out_dir))

    written = 0
    for ev in curated:
        filename = write_event_json(ev, out_dir)
        if filename in existing:
            existing.remove(filename)
        written += 1

    for stale in existing:
        os.remove(os.path.join(out_dir, stale))

    print(f"\nSummary: {len(all_raw)} raw → {len(curated)} curated, {tagged} tagged, {num_groups} recurring groups", flush=True)
    print(f"Wrote {written} JSON files to {out_dir}/", flush=True)
    if existing:
        print(f"Removed {len(existing)} stale files", flush=True)
    print("Done.", flush=True)


if __name__ == "__main__":
    main()
