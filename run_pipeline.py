#!/usr/bin/env python3
"""
Weekly Stutensee events pipeline.
Scrapes all sources, loads new events, deduplicates, verifies.
Usage:  python3 run_pipeline.py
"""

import json, sys, os, sqlite3, urllib.request, re, html, hashlib
from concurrent.futures import ThreadPoolExecutor, as_completed
from scrape_and_merge import (
    auto_tag,
    TITLE_ALWAYS_TAGS,
    TITLE_EXCLUSIVE_TAGS,
    KEYWORDS,
    FALSE_POSITIVE_CLEANUP,
    ORGANIZER_EXCLUSIVE_TAGS,
    DISTRICTS,
    DISTRICT_EXCLUSIONS,
    BLOCKED_TITLES,
    BLOCKED_PREFIXES,
    MANUAL_DUPES,
    MANUAL_EVENTS,
)
import importlib.util
for mod in ["scraper_vhs", "scraper_gewerbeverein", "scraper_blutspende", "scraper_pestalozzi", "scraper_wochenmarkt", "scraper_waldstadt", "scraper_vsv_buechig", "scraper_eggenstein", "scraper_rintheim", "scraper_linkenheim", "scraper_graben_neudorf", "scraper_weingarten", "scraper_bruchsal"]:
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
from datetime import datetime
from scraper_clubs import scrape_clubs

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
        title = ev.get("title", "")
        if title in BLOCKED_TITLES:
            continue
        if any(title.startswith(p) for p in BLOCKED_PREFIXES):
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
    prefix_conditions = " AND ".join(
        f"title NOT LIKE '{p}%' ESCAPE ''" for p in BLOCKED_PREFIXES
    ) if BLOCKED_PREFIXES else "1=1"
    where_clause = (
        f"title IS NOT NULL AND title != '' "
        f"AND title NOT IN ({blocked_placeholders}) "
        f"AND {prefix_conditions} "
        f"AND (date_start IS NULL OR date_start = '' OR date_start >= date('now'))"
    )
    c.execute(f"""
        INSERT INTO curated_events (title, date_start, date_end, time_raw, location, organizer, description, event_url, sources)
        SELECT title, date_start, date_end, time_raw, location, organizer, description, event_url, GROUP_CONCAT(DISTINCT source_url)
        FROM raw_events WHERE {where_clause}
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

    # Re-populate raw_to_curated mapping after initial dedup INSERT
    # Use Python dict for efficient matching (avoids slow SQL cross-join)
    curated_map = {}
    for row in c.execute("SELECT id, title, date_start, location FROM curated_events").fetchall():
        key = (normalize_title(row[1]), row[2] or "", normalize_location(row[3]))
        curated_map[key] = row[0]

    batch = []
    for row in c.execute("""
        SELECT id, title, date_start, location, source_url
        FROM raw_events
        WHERE title IS NOT NULL AND title != ''
            AND (date_start IS NULL OR date_start = '' OR date_start >= date('now'))
    """).fetchall():
        key = (normalize_title(row[1]), row[2] or "", normalize_location(row[3]))
        cid = curated_map.get(key)
        if cid:
            batch.append((row[0], cid, row[4]))
        if len(batch) >= 500:
            c.executemany("INSERT INTO raw_to_curated (raw_id, curated_id, source) VALUES (?, ?, ?)", batch)
            batch = []
    if batch:
        c.executemany("INSERT INTO raw_to_curated (raw_id, curated_id, source) VALUES (?, ?, ?)", batch)
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

    # Post-dedup: merge remaining cross-source duplicates: same date + district, similar title
    merged = 0
    rows = []
    for r in c.execute("""
        SELECT id, title, date_start, location, description, sources
        FROM curated_events ORDER BY date_start, title
    """).fetchall():
        rows.append(list(r) + [normalize_title(r[1]), normalize_location_dedup(r[3])])
    # Group by date + district
    dd_groups = {}
    for r in rows:
        dd_groups.setdefault((r[2] or "", r[7]), []).append(r)
    for candidates in dd_groups.values():
        while True:
            match = None
            for i, a in enumerate(candidates):
                for b in candidates[i+1:]:
                    at, bt = a[6], b[6]
                    if at == bt or (len(at) > 6 and len(bt) > 6 and (at in bt or bt in at or at.replace(' ','') in bt.replace(' ','') or bt.replace(' ','') in at.replace(' ',''))):
                        match = (a, b)
                        break
                if match:
                    break
            if not match:
                break
            a, b = match
            pick = max([a, b], key=lambda x: len(x[4] or ""))
            kill = b if pick[0] == a[0] else a
            merged += 1
            merged_src = set(pick[5].split(",")) if pick[5] else set()
            for s in (kill[5] or "").split(","):
                if s.strip():
                    merged_src.add(s.strip())
            c.execute("UPDATE raw_to_curated SET curated_id = ? WHERE curated_id = ?", (pick[0], kill[0]))
            c.execute("DELETE FROM curated_events WHERE id = ?", (kill[0],))
            c.execute("UPDATE curated_events SET sources = ? WHERE id = ?",
                      (",".join(sorted(merged_src)), pick[0]))
            candidates.remove(kill)
    # Cross-date fuzzy pass: same date, similar title regardless of district
    date_rows = {}
    for r in rows:
        date_rows.setdefault(r[2] or "", []).append(r)
    for date_key, candidates in date_rows.items():
        for i in range(len(candidates)):
            for j in range(i+1, len(candidates)):
                a, b = candidates[i], candidates[j]
                at, bt = a[6], b[6]
                if at == bt:
                    continue
                short, long = (at, bt) if len(at) < len(bt) else (bt, at)
                short_ns = short.replace(" ","")
                long_ns = long.replace(" ","")
                long_w = set(long.split())
                match = False
                if len(short_ns) > 6 and len(long_ns) > 6:
                    if short_ns in long_ns or long_ns in short_ns:
                        match = True
                    elif short_ns and all(any(w in word for word in long_w) for w in short_ns.split()):
                        match = True
                if match:
                    a, b = candidates[i], candidates[j]
                    pick = max([a, b], key=lambda x: len(x[4] or ""))
                    kill = b if pick[0] == a[0] else a
                    merged += 1
                    merged_src = set(pick[5].split(",")) if pick[5] else set()
                    for s in (kill[5] or "").split(","):
                        if s.strip():
                            merged_src.add(s.strip())
                    c.execute("UPDATE raw_to_curated SET curated_id = ? WHERE curated_id = ?", (pick[0], kill[0]))
                    c.execute("DELETE FROM curated_events WHERE id = ?", (kill[0],))
                    c.execute("UPDATE curated_events SET sources = ? WHERE id = ?",
                              (",".join(sorted(merged_src)), pick[0]))

    # Manual overrides: merge variant titles into canonical
    for canon, variants in MANUAL_DUPES.items():
        cn = normalize_title(canon)
        for r in rows:
            if r[1] == canon:
                for r2 in rows:
                    if r2[0] == r[0]:
                        continue
                    if r2[1] in variants and r[2] == r2[2]:
                        pick = max([r, r2], key=lambda x: len(x[4] or ""))
                        kill = r2 if pick[0] == r[0] else r
                        merged += 1
                        merged_src = set(pick[5].split(",")) if pick[5] else set()
                        for s in (kill[5] or "").split(","):
                            if s.strip():
                                merged_src.add(s.strip())
                        c.execute("UPDATE raw_to_curated SET curated_id = ? WHERE curated_id = ?", (pick[0], kill[0]))
                        c.execute("DELETE FROM curated_events WHERE id = ?", (kill[0],))
                        c.execute("UPDATE curated_events SET sources = ? WHERE id = ?",
                                  (",".join(sorted(merged_src)), pick[0]))

    # Also merge same-title duplicates where one has no location
    title_groups = {}
    for r in rows:
        title_groups.setdefault((r[6], r[2] or ""), []).append(r)
    for candidates in title_groups.values():
        if len(candidates) > 1:
            best = max(candidates, key=lambda x: len(x[4] or ""))
            for kill in candidates:
                if kill[0] == best[0]:
                    continue
                merged += 1
                merged_src = set(best[5].split(",")) if best[5] else set()
                for s in (kill[5] or "").split(","):
                    if s.strip():
                        merged_src.add(s.strip())
                c.execute("UPDATE raw_to_curated SET curated_id = ? WHERE curated_id = ?", (best[0], kill[0]))
                c.execute("DELETE FROM curated_events WHERE id = ?", (kill[0],))
                c.execute("UPDATE curated_events SET sources = ? WHERE id = ?",
                          (",".join(sorted(merged_src)), best[0]))
    if merged:
        conn.commit()
        print(f"  Post-merge: {merged} duplicates merged (fuzzy)", flush=True)

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


def normalize_location_dedup(location):
    """Normalize location for dedup grouping: strip street addresses, keep district."""
    if not location:
        return ""
    loc = location.strip().lower()
    for district in ["blankenloch", "büchig", "buechig", "friedrichstal", "spöck", "spoeck", "staffort", "stutensee"]:
        if district in loc:
            return district
    for district, keywords in DISTRICTS.items():
        for kw in keywords:
            if kw in loc:
                return district
    idx = loc.find(',')
    return loc[:idx].strip() if idx > 0 else loc


def tag_untagged(force=False):
    """Tag events. By default only tags untagged events (preserves restored/manual tags).
    Pass force=True to re-tag ALL events (overwrites existing tags)."""
    conn = sqlite3.connect(DB)
    c = conn.cursor()
    if force:
        rows = c.execute("SELECT id, title, COALESCE(description,''), COALESCE(location,''), COALESCE(organizer,''), COALESCE(tags,'') FROM curated_events").fetchall()
    else:
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
    import argparse
    parser = argparse.ArgumentParser(description="Stutensee Events Pipeline")
    parser.add_argument("--sources", help="Comma-separated source names to run (default: all)")
    parser.add_argument("--force-retag", action="store_true", help="Re-tag ALL curated events, not just untagged ones. Useful after updating tagging logic.")
    args = parser.parse_args()

    print("Stutensee Events Pipeline", flush=True)
    print(f"Time: {datetime.now().isoformat()}", flush=True)
    if args.sources:
        print(f"Sources: {args.sources}", flush=True)

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
        ("Bürgerverein Waldstadt", scrape_waldstadt),
        ("Club websites (39 sites)", scrape_clubs),
        ("VSV Büchig", scrape_vsv_buechig),
        ("Eggenstein-Leopoldshafen", scrape_eggenstein),
        ("Rintheim", scrape_rintheim),
        ("Linkenheim-Hochstetten", scrape_linkenheim),
        ("Graben-Neudorf", scrape_graben_neudorf),
        ("Weingarten", scrape_weingarten),
        ("Bruchsal", scrape_bruchsal),
    ]
    optional_sources = [
        ("Kath. Kirche", "https://www.kath-weistu.de/", "https://www.kath-stutensee-weingarten.de/"),
        ("Bibliothek", "https://bibliotheken.komm.one/stutensee", None),
    ]

    cleanup_malformed_dates()
    cleanup_past_events()

    source_filter = [s.strip() for s in args.sources.split(",")] if args.sources else None
    if source_filter:
        filtered = [(n, s) for n, s in sources if n in source_filter]
        not_found = [s for s in source_filter if s not in dict(sources)]
        if not_found:
            print(f"  Warning: sources not found: {', '.join(not_found)}", flush=True)
        sources = filtered

    total_new = 0

    def scrape_one(name_scraper):
        name, scraper_func = name_scraper
        try:
            data = scraper_func()
            n = insert_raw(data)
            return name, len(data["events"]), n, None
        except Exception as e:
            return name, 0, 0, str(e)

    with ThreadPoolExecutor(max_workers=8) as executor:
        futures = {executor.submit(scrape_one, s): s[0] for s in sources}
        for future in as_completed(futures):
            name = futures[future]
            try:
                name, fetched, new, err = future.result()
                if err:
                    print(f"  {name}: ERROR: {err}", flush=True)
                else:
                    total_new += new
                    print(f"  {name}: {fetched} fetched, {new} new", flush=True)
            except Exception as e:
                print(f"  {name}: ERROR: {e}", flush=True)

    for name, url, src_url in optional_sources:
        print(f"  Scraping {name}...", end=" ", flush=True)
        result = scrape_optional(url, name, src_url)
        if result:
            # Optional sources handled by agents, just acknowledge
            print(f"available", flush=True)
        else:
            print(f"skipped", flush=True)

    print(f"  Injecting manual events...", end=" ", flush=True)
    conn = sqlite3.connect(DB)
    mc = conn.cursor()
    inject_count = 0
    for ev in MANUAL_EVENTS:
        h = hashlib.sha256(json.dumps(ev, sort_keys=True).encode()).hexdigest()
        try:
            mc.execute("""INSERT OR IGNORE INTO raw_events
                (source_url, title, date_start, date_end, time_raw, location, organizer, description, event_url, raw_html_hash)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                ("manual_override", ev["title"], ev["date_start"], ev["date_end"],
                 ev["time_raw"], ev["location"], ev["organizer"], ev["description"], ev["event_url"], h))
            if mc.rowcount > 0:
                inject_count += 1
        except Exception:
            pass
    conn.commit()
    conn.close()
    print(f"{inject_count} injected", flush=True)

    print(f"  Total new: {total_new}", flush=True)
    print(f"  URL cleanup...", end=" ", flush=True)
    cleaned = cleanup_kath_urls()
    print(f"{cleaned} urls fixed", flush=True)

    print(f"  Dedup...", end=" ", flush=True)
    curated = dedup_sql()
    print(f"{curated} curated", flush=True)

    if args.force_retag:
        print(f"  Force re-tagging all events...", end=" ", flush=True)
    else:
        print(f"  Tagging untagged...", end=" ", flush=True)
    tagged = tag_untagged(force=args.force_retag)
    print(f"{tagged} tagged", flush=True)

    print(f"  Recurring detection...", end=" ", flush=True)
    from scripts.detect_recurring import main as detect_recurring
    detect_recurring()
    print(f"  done", flush=True)

    conn = sqlite3.connect(DB)
    raw = conn.execute("SELECT COUNT(*) FROM raw_events").fetchone()[0]
    tagged = conn.execute("SELECT COUNT(*) FROM curated_events WHERE tags != ''").fetchone()[0]
    recurring = conn.execute("SELECT COUNT(*) FROM curated_events WHERE recurring_group_id IS NOT NULL").fetchone()[0]
    conn.close()
    print(f"\nSummary: {raw} raw → {curated} curated, {tagged} tagged, {recurring} recurring", flush=True)
    print(f"Done. Start server: python3 server.py", flush=True)
