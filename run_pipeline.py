#!/usr/bin/env python3
"""
Weekly Stutensee events pipeline.
Scrapes all sources, loads new events, deduplicates, verifies.
Usage:  python3 run_pipeline.py
"""

import json, sys, os, sqlite3, urllib.request, re, html, hashlib
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


def scrape_meinstutensee():
    events = []
    html_content = fetch_url("https://meinstutensee.de/termine/")
    for schema in re.findall(r'<script type="application/ld\+json">(.*?)</script>', html_content, re.DOTALL):
        try:
            data = json.loads(schema)
            if isinstance(data, dict) and data.get("@type") == "Event":
                start = data.get("startDate", "")
                loc = data.get("location", {}) or {}
                org = data.get("organizer", {}) or {}
                events.append({"title": data.get("name", ""), "date_start": start[:10] if start else "",
                    "date_end": data.get("endDate", "")[:10] if data.get("endDate") else "",
                    "time_raw": start[11:16] if len(start) > 16 else "",
                    "location": loc.get("name", "") if isinstance(loc, dict) else "",
                    "organizer": org.get("name", "") if isinstance(org, dict) else "",
                    "description": "", "event_url": data.get("url", "")})
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


def insert_raw(source_data):
    conn = sqlite3.connect(DB)
    c = conn.cursor()
    count = 0
    for ev in source_data["events"]:
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


def dedup_sql():
    conn = sqlite3.connect(DB)
    c = conn.cursor()
    c.execute("DELETE FROM curated_events")
    c.execute("DELETE FROM raw_to_curated")
    c.execute("""
        INSERT INTO curated_events (title, date_start, date_end, time_raw, location, organizer, description, event_url, sources)
        SELECT title, date_start, date_end, time_raw, location, organizer, description, event_url, GROUP_CONCAT(DISTINCT source_url)
        FROM raw_events WHERE title IS NOT NULL AND title != ''
        GROUP BY LOWER(TRIM(title)), COALESCE(date_start, ''), COALESCE(location, '')
        ORDER BY date_start ASC
    """)
    conn.commit()
    count = c.execute("SELECT COUNT(*) FROM curated_events").fetchone()[0]
    conn.close()
    return count


if __name__ == "__main__":
    print("Stutensee Events Pipeline", flush=True)

    sources = [
        ("Official calendar", scrape_official),
        ("Kinderkalender", scrape_kinderkalender),
        ("meinstutensee.de", scrape_meinstutensee),
        ("Bürgerwerkstatt", scrape_buergerwerkstatt),
    ]
    total_new = 0
    for name, scraper in sources:
        print(f"  Scraping {name}...", end=" ", flush=True)
        data = scraper()
        n = insert_raw(data)
        total_new += n
        print(f"{len(data['events'])} fetched, {n} new", flush=True)

    print(f"  Total new: {total_new}", flush=True)
    print(f"  Dedup...", end=" ", flush=True)
    curated = dedup_sql()
    conn = sqlite3.connect(DB)
    raw = conn.execute("SELECT COUNT(*) FROM raw_events").fetchone()[0]
    conn.close()
    print(f"{curated} curated from {raw} raw", flush=True)
    print(f"Done. Start server: python3 server.py", flush=True)
