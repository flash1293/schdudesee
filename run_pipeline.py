#!/usr/bin/env python3
"""
Weekly Stutensee events pipeline.
Scrapes all sources, loads new events, deduplicates, verifies.
Usage:  python3 run_pipeline.py
"""

import json, sys, os, sqlite3, urllib.request, re, html, hashlib
import importlib.util
for mod in ["scraper_vhs", "scraper_gewerbeverein", "scraper_blutspende", "scraper_pestalozzi", "scraper_wochenmarkt"]:
    spec = importlib.util.spec_from_file_location(mod, f"{mod}.py")
    m = importlib.util.module_from_spec(spec)
    sys.modules[mod] = m
    spec.loader.exec_module(m)
scrape_vhs = sys.modules["scraper_vhs"].scrape_vhs
scrape_gewerbeverein = sys.modules["scraper_gewerbeverein"].scrape_gewerbeverein
scrape_blutspende = sys.modules["scraper_blutspende"].scrape_blutspende
scrape_pestalozzi = sys.modules["scraper_pestalozzi"].scrape_pestalozzi
scrape_wochenmarkt = sys.modules["scraper_wochenmarkt"].scrape_wochenmarkt
from datetime import datetime

DB = "stutensee_events.db"

def fetch_url(url, timeout=30):
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
            desc = html.unescape(e.get("description", "").strip() or "")
            desc = re.sub(r'<[^>]+>', '', desc)
            events.append({"title": title, "date_start": start[:10] if start else "",
                "date_end": end[:10] if end else "", "time_raw": start[11:16] if len(start) > 16 else "",
                "location": f"{venue}, {va}".strip(", "), "organizer": "; ".join(o for o in orgs if o),
                "description": html.unescape(desc), "event_url": e.get("url", "")})
        if not data.get("next_rest_url"):
            break
        page += 1
    return {"source_url": "https://stutenseekinderkalender.de", "events": events}


def parse_meinstutensee_date(start):
    """Parse non-padded ISO dates like '2026-5-7T19:00+2:00' or '2026-5-1'."""
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
    """Extract name from a JSON-LD object or list of objects."""
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
    """Safely scrape an optional source with short timeout."""
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
            # Next line might be time
            if i < len(lines) and re.match(r'[\d:ab\s-]+Uhr', lines[i]):
                time_str = lines[i].split(",")[0].strip()  # strip trailing location
                i += 1
            # Next lines might be location
            loc = ""
            if i < len(lines) and re.match(r'^[A-Za-z]', lines[i]) and "Mittagstisch" not in lines[i] and "Maifest" not in lines[i] and "Sommerfest" not in lines[i] and "Laternenfest" not in lines[i] and "Adventsfest" not in lines[i] and not re.match(r'\d{2}\.', lines[i]):
                loc = lines[i]
                i += 1
            # Next line is the event title
            if i < len(lines):
                title = lines[i]
                i += 1
                if title in ("Maifest", "Sommerfest", "Laternenfest", "Adventsfest"):
                    title += " Büchig"
            # Next line might be the food description (for Mittagstisch)
            desc = ""
            if title.startswith("Mittagstisch") and i < len(lines) and not re.match(r'\d{2}\.', lines[i]) and "Büchig(er)" not in lines[i]:
                desc = lines[i]
                i += 1
                title = f"Mittagstisch – {desc}"
            if title:
                events.append({"title": title, "date_start": iso, "date_end": None,
                    "time_raw": time_str, "location": loc or "Büchig",
                    "organizer": "Büchig(er)leben", "description": "",
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
    """Parse '26. January 2026' style dates from German text. Returns ISO date or empty string."""
    dm = re.search(r'(\d{1,2})\.\s*([A-Za-z]+)\s*(\d{4})', text)
    if not dm:
        return ""
    from calendar import month_name
    months = {m.lower(): i for i, m in enumerate(month_name) if m}
    month_num = months.get(dm.group(2).lower())
    if not month_num:
        return ""
    return f"{dm.group(3)}-{str(month_num).zfill(2)}-{dm.group(1).zfill(2)}"


def is_past(iso_date):
    """Check if an ISO date string is in the past."""
    if not iso_date:
        return False
    try:
        return datetime.strptime(iso_date, "%Y-%m-%d").date() < datetime.now().date()
    except:
        return True  # if we can't parse, treat as past to be safe


def scrape_flohmarkt():
    events = []
    html_content = fetch_url("https://www.flohmarkt-buechig.de/")
    iso = parse_german_date(html_content)
    if iso and not is_past(iso):
        events.append({"title": "Flohmarkt Büchig", "date_start": iso, "date_end": None,
            "time_raw": "", "location": "Festhalle Blankenloch", "organizer": "Flohmarkt Kitas Büchig",
            "description": "", "event_url": "https://www.flohmarkt-buechig.de/"})
    return {"source_url": "https://www.flohmarkt-buechig.de/", "events": events}


def cleanup_kath_urls():
    """Add ?vt=1&cb-id=12179900 to kath-weistu.de event URLs (required for rendering)."""
    conn = sqlite3.connect(DB)
    c = conn.cursor()
    total = 0
    for table, id_col in [("raw_events", "rowid"), ("curated_events", "id")]:
        rows = c.execute(f"SELECT {id_col}, event_url FROM {table} WHERE event_url LIKE 'https://www.kath-weistu.de/%' AND event_url NOT LIKE '%vt=1%'").fetchall()
        for eid, url in rows:
            fixed = url + ("&" if "?" in url else "?") + "vt=1&cb-id=12179900"
            c.execute(f"UPDATE {table} SET event_url = ? WHERE {id_col} = ?", (fixed, eid))
            total += 1
    conn.commit()
    conn.close()
    return total


def insert_raw(source_data):
    conn = sqlite3.connect(DB)
    c = conn.cursor()
    count = 0
    for ev in source_data["events"]:
        if ev.get("title", "") in BLOCKED_TITLES:
            continue
        if is_past(ev.get("date_start", "")):
            continue
        h = hashlib.sha256(json.dumps(ev, sort_keys=True).encode()).hexdigest()
        try:
            c.execute("""INSERT OR IGNORE INTO raw_events
                (source_url, title, date_start, date_end, time_raw, location, organizer, description, event_url, raw_html_hash)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (source_data["source_url"], ev.get("title"), ev.get("date_start"), ev.get("date_end"),
                 ev.get("time_raw"), ev.get("location"), ev.get("organizer"),
                 ev.get("description"), ev.get("event_url"), h))
            if c.rowcount > 0: count += 1
        except Exception:
            pass
    conn.commit()
    conn.close()
    return count


def cleanup_past_events():
    """Remove past events from raw_events so they don't appear in curated."""
    conn = sqlite3.connect(DB)
    c = conn.cursor()
    today = datetime.now().date().isoformat()
    deleted = c.execute("DELETE FROM raw_events WHERE date_start IS NOT NULL AND date_start != '' AND date_start < ?", (today,)).rowcount
    conn.commit()
    conn.close()
    print(f"  Removed {deleted} past events from raw_events", flush=True)
    return deleted


def cleanup_malformed_dates():
    """Remove rows with malformed dates (from old buggy parser runs)."""
    conn = sqlite3.connect(DB)
    c = conn.cursor()
    deleted = c.execute("DELETE FROM raw_events WHERE date_start IS NOT NULL AND date_start != '' AND date_start NOT LIKE '____-__-__'").rowcount
    conn.commit()
    conn.close()
    print(f"  Removed {deleted} malformed date rows from raw_events", flush=True)
    return deleted


def dedup_sql():
    conn = sqlite3.connect(DB)
    c = conn.cursor()

    # Snapshot old tags + recurring_group_id before rebuilding
    # Key by (normalized_title, date, location_prefix) to survive id changes
    old = {}
    try:
        for r in c.execute("SELECT id, title, date_start, location, COALESCE(tags,''), recurring_group_id FROM curated_events").fetchall():
            nt = normalize_title(r[1])
            dl = normalize_location(r[3])
            old[(nt, r[2] or "", dl)] = (r[4], r[5])
    except:
        pass

    c.execute("DELETE FROM curated_events")
    c.execute("DELETE FROM raw_to_curated")
    blocked_placeholders = ",".join("?" for _ in BLOCKED_TITLES)
    c.execute(f"""
        INSERT INTO curated_events (title, date_start, date_end, time_raw, location, organizer, description, event_url, sources)
        SELECT title, date_start, date_end, time_raw, location, organizer, description, event_url, GROUP_CONCAT(DISTINCT source_url)
        FROM raw_events WHERE title IS NOT NULL AND title != '' AND title NOT IN ({blocked_placeholders})
            AND (date_start IS NULL OR date_start = '' OR date_start >= date('now'))
        GROUP BY LOWER(TRIM(REPLACE(REPLACE(REPLACE(REPLACE(REPLACE(REPLACE(
            REPLACE(REPLACE(REPLACE(REPLACE(title,
                ' in blankenloch',''),' in büchig',''),' in friedrichstal',''),
                ' in spöck',''),' in staffort',''),
                ' blankenloch',''),' büchig',''),' friedrichstal',''),
                ' spöck',''),' staffort','')
        )), COALESCE(date_start, ''), COALESCE(TRIM(SUBSTR(location, 1, INSTR(location || ',', ',') - 1)), TRIM(location), '')
        ORDER BY date_start ASC
    """, BLOCKED_TITLES)
    conn.commit()

    # Restore old tags + recurring_group_id by matching on normalized key
    restored_tags = 0
    restored_rec = 0
    for r in c.execute("SELECT id, title, date_start, location FROM curated_events").fetchall():
        nt = normalize_title(r[1])
        dl = normalize_location(r[3])
        key = (nt, r[2] or "", dl)
        if key in old:
            tags, rec_id = old[key]
            if tags:
                c.execute("UPDATE curated_events SET tags = ? WHERE id = ?", (tags, r[0]))
                restored_tags += 1
            if rec_id:
                c.execute("UPDATE curated_events SET recurring_group_id = ? WHERE id = ?", (rec_id, r[0]))
                restored_rec += 1

    conn.commit()
    count = c.execute("SELECT COUNT(*) FROM curated_events").fetchone()[0]
    conn.close()
    print(f"  Restored: {restored_tags} tags, {restored_rec} recurring", flush=True)
    return count


def normalize_title(title):
    if not title:
        return ""
    t = title.lower().strip()
    for suffix in [' in blankenloch', ' in büchig', ' in friedrichstal', ' in spöck', ' in staffort',
                    ' blankenloch', ' büchig', ' friedrichstal', ' spöck', ' staffort']:
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


BLOCKED_TITLES = [
    "Krabbelkäfer Stutensee-Büchig – gemütliches Beisammensein mit Frühstück",
]

DISTRICTS = {
    "Blankenloch": ["blankenloch", "bl.", "mehrgenerationenhaus", "bürgerwerkstatt", "seegrabenweg", "gymnasiumstr", "zukunftshaus"],
    "Büchig": ["büchig", "buechig"],
    "Friedrichstal": ["friedrichstal", "spöcker weg", "spoecker weg"],
    "Spöck": ["spöck", "spoeck"],
    "Staffort": ["staffort"],
    "Weingarten": ["weingarten"],
 }

DISTRICT_EXCLUSIONS = {
    "Spöck": ["spöcker weg", "spoecker weg"],
}

KEYWORDS = {
    "Sport": ["lauf", "triathlon", "tennis", "turnen", "fitness", "yoga", "pilates", "tischtennis",
              "fußball", "fussball", "schwimm", "rad", "bike", "cycling", "sport", "bewegung",
              "gymnastik", "tanz", "dance", "ballett", "kickbox", "karate", "indiaca", "volleyball",
              "handball", "basketball", "reit", "pferd", "wandern", "training", "stadtlauf", "spechaa",
              "turnier", "kajak", "kanu", "dressur", "springturnier", "reitturnier"],
    "Musik": ["konzert", "chor", "gesang", "musik", "band", "jazz", "singen", "lieder", "klang",
              "musikal", "orchester", "posaunen", "gitarre", "vox", "choir", "swing", "liederabend",
              "gospel", "rockfestival"],
    "Kultur": ["theater", "lesung", "kunst", "ausstellung", "kino", "literatur", "bühne", "kultur",
               "museum", "foto", "malen", "zeichnen", "denkmals"],
    "Kirche": ["gottesdienst", "kirche", "konfirmation", "firmung", "taufe", "messe",
               "andacht", "segen", "ökumen", "patrozinium", "gebet", "evangelisch", "katholisch",
               "trauer", "abendmahl", "kommunion", "herzensgebet", "maiandacht", "bibelkreis",
               "bibelgespräch", "bibelstunde", "vesper", "kreuzweg", "volkstrauertag",
               "allerseelen", "allerheiligen", "glaubenskurs", "religionsunterricht"],
    "Kinder": ["kind", "baby", "eltern-kind", "krabbel", "spiel", "familie", "mädchen", "junge",
               "kindergarten", "schule", "vorlesen", "bilderbuch", "küken", "seepferdchen",
               "abenteuer", "zwerge", "jugend", "teen", "schüler", "kinderturnen", "ferien",
               "caribi", "minis", "bambini", "steckenpferd", "drachen", "lager", "ballontag",
               "halloween", "gruselnacht"],
    "Fest": ["fest", "oktoberfest", "maifest", "weihnachtsmarkt", "kerwe", "party",
             "sportfest", "maibaum", "frühlingsfest", "sommerfest", "jubiläum", "vatertagsfest",
             "heimattage", "steinwiesenfest", "kürbisfest", "hähnchenfest", "fischerfest",
             "apfelblütenfest", "kinderspielfest", "pfingstfeier"],
    "Markt": ["markt", "flohmarkt", "trödel", "weihnachtsmarkt"],
    "Workshop": ["workshop", "kurs", "seminar", "lernen", "unterricht", "stunde", "training"],
    "Bildung": ["bildung", "vortrag", "schule", "vhs", "diskussion", "fortbildung", "lesen",
                "lernen", "infoveranstaltung", "podiumsdiskussion", "ausbildungsplattform"],
    "Natur": ["natur", "garten", "wald", "vogel", "baum", "pflanze", "umwelt", "klima",
              "hornisse", "mulchen", "exkursion", "wanderung"],
    "Senioren": ["senior", "50+", "älter", "alt werden", "beweglich im alter"],
    "Digital": ["digital", "smartphone", "computer", "handy", "online", "app", "internet"],
    "Handwerk": ["basteln", "werkstatt", "nähen", "stricken", "häkeln", "reparier", "reparatur",
                 "handarbeit", "kreativ", "secondhand", "bastel", "sonnenfänger"],
    "Essen": ["kochen", "backen", "essen", "grill", "frühstück", "küche", "kuchen", "kaffee",
              "bowle", "bier", "wein", "hähnchen", "flammkuchen", "zwiebelkuchen", "mittagstisch",
              "dampfnudel"],
    "Treff": ["treff", "café", "stammtisch", "begegnung", "gespräch", "runde", "kreis",
              "spieleabend", "badentreff", "männerrunde"],
    "Politik": ["wahl", "gemeinderat", "bürgermeister", "politik", "partei", "rat", "ausschuss",
                "bürgermeisterkandidaten", "einwohnerversammlung"],
    "Verein": ["verein", "e.v.", "mitgliederversammlung", "vorstand", "ehrenamt",
               "clubabend", "hobbyday", "vorstandsmeeting", "arbeitseinsatz",
               "stammesklausur", "hobbylager"],
    "Wohltätigkeit": ["spende", "blutspende", "kleidersammlung", "charity", "sozial", "tafel",
                      "hilfe", "sanitätsdienst"],
}

def auto_tag(title, description="", location="", organizer=""):
    # Content tags from title+description only (avoid false positives from organizer "Kirchengemeinde")
    content_text = f"{title} {description}".lower()
    content_tags = []
    for tag, keywords in KEYWORDS.items():
        for kw in keywords:
            if kw in content_text:
                content_tags.append(tag)
                break
    content_tags = content_tags[:2]
    # District tags from full text
    full_text = f"{title} {description} {location} {organizer}".lower()
    district_tags = []
    for district, keywords in DISTRICTS.items():
        for kw in keywords:
            if kw in full_text:
                excluded = False
                for excl in DISTRICT_EXCLUSIONS.get(district, []):
                    if excl in full_text:
                        excluded = True
                        break
                if not excluded and district not in district_tags:
                    district_tags.append(district)
                break
    return content_tags + district_tags


def tag_untagged():
    """Only tag events that have no tags yet (preserves restored/manual tags)."""
    conn = sqlite3.connect(DB)
    c = conn.cursor()
    rows = c.execute("SELECT id, title, COALESCE(description,''), COALESCE(location,''), COALESCE(organizer,''), COALESCE(tags,'') FROM curated_events WHERE tags IS NULL OR tags = ''").fetchall()
    count = 0
    for r in rows:
        tags = auto_tag(r[1], r[2], r[3], r[4])
        if tags:
            c.execute("UPDATE curated_events SET tags = ? WHERE id = ?", (",".join(tags), r[0]))
            count += 1
    conn.commit()
    conn.close()
    return count


if __name__ == "__main__":
    print("Stutensee Events Pipeline", flush=True)
    print(f"Time: {datetime.now().isoformat()}", flush=True)

    sources = [
        ("Official calendar", scrape_official),
        ("Kinderkalender", scrape_kinderkalender),
        ("meinstutensee.de", scrape_meinstutensee),
        ("Bürgerwerkstatt events", scrape_buergerwerkstatt),
        ("Büchigerleben", scrape_buechigerleben),
        ("Flohmarkt", scrape_flohmarkt),
        ("VHS Stutensee", scrape_vhs),
        ("Gewerbeverein", scrape_gewerbeverein),
        ("Blutspende", scrape_blutspende),
        ("Pestalozzi Schule", scrape_pestalozzi),
        ("Wochenmarkt", scrape_wochenmarkt),
    ]
    optional_sources = [
        ("Kath. Kirche", "https://www.kath-weistu.de/", "https://www.kath-stutensee-weingarten.de/"),
        ("Bibliothek", "https://bibliotheken.komm.one/stutensee", None),
    ]

    cleanup_malformed_dates()
    cleanup_past_events()

    total_new = 0
    for name, scraper in sources:
        print(f"  Scraping {name}...", end=" ", flush=True)
        try:
            data = scraper()
            n = insert_raw(data)
            total_new += n
            print(f"{len(data['events'])} fetched, {n} new", flush=True)
        except Exception as e:
            print(f"ERROR: {e}", flush=True)

    for name, url, src_url in optional_sources:
        print(f"  Scraping {name}...", end=" ", flush=True)
        result = scrape_optional(url, name, src_url)
        if result:
            # Optional sources handled by agents, just acknowledge
            print(f"available", flush=True)
        else:
            print(f"skipped", flush=True)

    print(f"  Total new: {total_new}", flush=True)
    print(f"  URL cleanup...", end=" ", flush=True)
    cleaned = cleanup_kath_urls()
    print(f"{cleaned} urls fixed", flush=True)

    print(f"  Dedup...", end=" ", flush=True)
    curated = dedup_sql()
    print(f"{curated} curated", flush=True)

    print(f"  Tagging untagged...", end=" ", flush=True)
    tagged = tag_untagged()
    print(f"{tagged} tagged", flush=True)

    print(f"  Recurring detection...", end=" ", flush=True)
    from detect_recurring import main as detect_recurring
    detect_recurring()
    print(f"  done", flush=True)

    conn = sqlite3.connect(DB)
    raw = conn.execute("SELECT COUNT(*) FROM raw_events").fetchone()[0]
    tagged = conn.execute("SELECT COUNT(*) FROM curated_events WHERE tags != ''").fetchone()[0]
    recurring = conn.execute("SELECT COUNT(*) FROM curated_events WHERE recurring_group_id IS NOT NULL").fetchone()[0]
    conn.close()
    print(f"\nSummary: {raw} raw → {curated} curated, {tagged} tagged, {recurring} recurring", flush=True)
    print(f"Done. Start server: python3 server.py", flush=True)
