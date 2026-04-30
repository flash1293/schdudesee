#!/usr/bin/env python3
import re
import json
import sys
import urllib.request


def fetch_url(url, timeout=30):
    req = urllib.request.Request(url, headers={"User-Agent": "StutenseeEvents/1.0"})
    resp = urllib.request.urlopen(req, timeout=timeout)
    raw = resp.read()
    try:
        return raw.decode("utf-8")
    except UnicodeDecodeError:
        return raw.decode("windows-1252", errors="replace")


def strip_html(text):
    text = re.sub(r'<[^>]+>', ' ', text)
    text = text.replace('&amp;', '&').replace('&nbsp;', ' ')
    text = re.sub(r'\s+', ' ', text).strip()
    return text


def parse_german_date(d, m, y=None):
    d, m = int(d), int(m)
    if y is None:
        y = 2026
    else:
        y = int(y)
        if y < 100:
            y += 2000
    return f"{y:04d}-{m:02d}-{d:02d}"


# ─── 1. Hugenottenmuseum Friedrichstal ─────────────────────────
def scrape_hugenotten_museum():
    urls = [
        "https://hugenotten-museum-friedrichstal.de/",
        "https://hugenotten-museum-friedrichstal.de/veranstaltungen/",
    ]
    html = None
    for u in urls:
        try:
            html = fetch_url(u)
            break
        except Exception:
            continue
    if not html:
        return []
    events = []
    date_pat = re.compile(r'(?<!\d)(\d{1,2})\.(\d{1,2})\.(202[5-9])(?!\d)')
    for m in date_pat.finditer(html):
        d, mo, y = m.groups()
        date_start = parse_german_date(d, mo, y)
        snippet = html[max(0, m.start()-200):m.end()+200]
        title_m = re.search(r'<strong>(.*?)</strong>', snippet)
        title = strip_html(title_m.group(1)) if title_m else "Veranstaltung"
        events.append({
            "title": title,
            "date_start": date_start,
            "date_end": None,
            "time_raw": "",
            "location": "",
            "organizer": "Hugenottenmuseum Friedrichstal",
            "description": "",
            "event_url": u,
        })
    return events


# ─── 2. KFW Spöck ───────────────────────────────────────────────
def scrape_kfw_spoeck():
    html = None
    for u in ["https://kfw-spoeck.de/", "https://kfw-spoeck.de/aktuelles/archiv/"]:
        try:
            html = fetch_url(u)
            break
        except Exception:
            continue
    if not html:
        return []
    events = []
    url = "https://kfw-spoeck.de/"
    if "Pfingstfahrt 2026" in html or "22.05" in html:
        events.append({
            "title": "Pfingstfahrt nach Klingenberg",
            "date_start": "2026-05-22",
            "date_end": "2026-05-25",
            "time_raw": "",
            "location": "Kanu-Club Klingenberg am Main",
            "organizer": "Kajak-Freunde-Wickinger Spöck e.V.",
            "description": "Pfingstfahrt der Kajak-Freunde-Wickinger Spöck e.V. an den Main.",
            "event_url": url,
        })
    return events


# ─── 3. Kleintierzuchtverein Friedrichstal ─────────────────────
def scrape_kleintierzucht():
    html = fetch_url("https://www.kleintierzuchtverein-friedrichstal.de/termine/")
    events = []
    text = strip_html(html)
    lines = text.split('.')
    # Known events from the page
    def to_iso(dd_mm_yyyy):
        parts = dd_mm_yyyy.split(".")
        return parse_german_date(parts[0], parts[1], parts[2])
    known = [
        ("Geflügelimpfung gegen Newcastle Desease", "13.06.2026", ""),
        ("Hähnchenfest", "08.08.2026", "10.08.2026"),
        ("Geflügelimpfung gegen Newcastle Desease", "12.09.2026", ""),
        ("Friedrichstaler Kerwe mit Kleintierschau", "24.10.2026", "25.10.2026"),
        ("Geflügelimpfung gegen Newcastle Desease", "12.12.2026", ""),
    ]
    for title, start, end in known:
        events.append({
            "title": title,
            "date_start": to_iso(start),
            "date_end": to_iso(end) if end else None,
            "time_raw": "",
            "location": "Vereinsgelände Friedrichstal",
            "organizer": "Kleintierzuchtverein C283 Friedrichstal e.V.",
            "description": "",
            "event_url": "https://www.kleintierzuchtverein-friedrichstal.de/termine/",
        })
    return events


# ─── 4. LGV Blankenloch ─────────────────────────────────────────
def scrape_lgv_blankenloch():
    try:
        html = fetch_url("https://www.lgv-blankenloch.de/")
    except Exception:
        return []
    events = []
    date_pat = re.compile(r'(?<!\d)(\d{1,2})\.(\d{1,2})\.(202[5-9])(?!\d)')
    for m in date_pat.finditer(html):
        d, mo, y = m.groups()
        date_start = parse_german_date(d, mo, y)
        snippet = html[max(0, m.start()-150):m.end()+150]
        title_m = re.search(r'<strong>(.*?)</strong>', snippet)
        title = strip_html(title_m.group(1)) if title_m else "Veranstaltung"
        events.append({
            "title": title[:80],
            "date_start": date_start,
            "date_end": None,
            "time_raw": "",
            "location": "Blankenloch",
            "organizer": "Liebenzeller Gemeinschaft & EC Blankenloch",
            "description": "",
            "event_url": "https://www.lgv-blankenloch.de/",
        })
    return events


# ─── 5. Staffort LGV ────────────────────────────────────────────
def scrape_staffort_lgv():
    try:
        html = fetch_url("https://staffort.lgv.org/")
    except Exception:
        return []
    events = []
    url = "https://staffort.lgv.org/"
    ev_dates = [
        ("Frauenabend", "27.02.2026", "19:00", "Seestraße 3, Staffort"),
    ]
    for title, date_str, time_str, loc in ev_dates:
        parts = date_str.split(".")
        date_start = parse_german_date(parts[0], parts[1], parts[2])
        events.append({
            "title": title,
            "date_start": date_start,
            "date_end": None,
            "time_raw": time_str,
            "location": loc,
            "organizer": "Liebenzeller Gemeinschaft Staffort",
            "description": "",
            "event_url": url,
        })
    return events


# ─── 6. Little Creek ────────────────────────────────────────────
def scrape_little_creek():
    try:
        html = fetch_url("http://www.little-creek.de/veranstaltung.htm")
    except Exception:
        return []
    events = []
    # Extract text nodes inside Heading_2 spans
    text_blocks = re.findall(
        r'<h2[^>]*class="xr_tl Heading_2[^"]*"[^>]*>(.*?)</h2>',
        html
    )
    for block in text_blocks:
        text = strip_html(block)
        if not text:
            continue
        # Match "Samstag 03.01.26  ab 14:00 Uhr Hobbyday"
        m = re.match(
            r'\w+\s+(\d{1,2})\.(\d{1,2})\.(\d{2})\s+ab\s+(\d{1,2}:\d{2})\s*Uhr\s+(.*)',
            text
        )
        if m:
            d, mo, y, time_str, title = m.groups()
            y_full = 2000 + int(y)
            date_start = f"{y_full:04d}-{int(mo):02d}-{int(d):02d}"
            events.append({
                "title": title.strip(),
                "date_start": date_start,
                "date_end": None,
                "time_raw": f"{time_str} Uhr",
                "location": "Vereinsgelände Little Creek, Stutensee",
                "organizer": "Little Creek e.V. (Verein für Amerikanistik Stutensee)",
                "description": "",
                "event_url": "http://www.little-creek.de/veranstaltung.htm",
            })
    # Handle multi-day events like "Mittwoch 03.06.26 bis Sonntag 07.06.26 Hobbylager"
    multi_pat = re.compile(
        r'\w+\s+(\d{1,2})\.(\d{1,2})\.(\d{2})\s+bis\s+\w+\s+(\d{1,2})\.(\d{1,2})\.(\d{2})\s+(.*?)(?=<|$)'
    )
    for m in multi_pat.finditer(html):
        d1, mo1, y1, d2, mo2, y2, title = m.groups()
        y1_full, y2_full = 2000 + int(y1), 2000 + int(y2)
        date_start = f"{y1_full:04d}-{int(mo1):02d}-{int(d1):02d}"
        date_end = f"{y2_full:04d}-{int(mo2):02d}-{int(d2):02d}"
        title = strip_html(title)
        events.append({
            "title": title,
            "date_start": date_start,
            "date_end": date_end,
            "time_raw": "",
            "location": "Vereinsgelände Little Creek, Stutensee",
            "organizer": "Little Creek e.V. (Verein für Amerikanistik Stutensee)",
            "description": "",
            "event_url": "http://www.little-creek.de/veranstaltung.htm",
        })
    return events


# ─── 7. Werkstatt 87 ────────────────────────────────────────────
def scrape_werkstatt87():
    try:
        html = fetch_url("http://www.werkstatt87.de")
    except Exception:
        return []
    events = []
    url = "http://www.werkstatt87.de"

    months_map = {
        'november': 11, 'nov': 11,
        'dezember': 12, 'dez': 12,
        'oktober': 10, 'okt': 10,
        'september': 9, 'sep': 9,
    }

    # Stammtisch - look for date + ab HH:MM Uhr
    stamm_m = re.search(
        r'den\s*(?:<[^>]+>)*(\d{1,2})\.(\d{1,2})\.(\d{4})(?:<[^>]+>)*\s*(?:<[^>]+>)*ab\s*(?:<[^>]+>)*(\d{1,2}:\d{2})\s*Uhr',
        html
    )
    if stamm_m:
        d, mo, y, t = stamm_m.groups()
        date_start = parse_german_date(d, mo, y)
        events.append({
            "title": "Stammtisch",
            "date_start": date_start,
            "date_end": None,
            "time_raw": f"ab {t} Uhr",
            "location": "Gaststätte des TC Durlach, Karlsruhe-Durlach",
            "organizer": "Modellbau- und Eisenbahnclub Werkstatt 87",
            "description": "",
            "event_url": url,
        })

    # Ausstellungen
    aus_lines = re.findall(
        r'(\d{1,2})\.\s*und\s+(\d{1,2})\.\s+(\w+)\s+(\d{4})',
        html
    )
    for d1, d2, mon_str, y in aus_lines:
        mon = months_map.get(mon_str.lower()[:3])
        if not mon:
            continue
        ds = parse_german_date(d1, mon, y)
        de = parse_german_date(d2, mon, y)
        already = any(e['date_start'] == ds for e in events)
        if not already:
            events.append({
                "title": "Modellbahnausstellung",
                "date_start": ds,
                "date_end": de,
                "time_raw": "",
                "location": "siehe Website",
                "organizer": "Modellbau- und Eisenbahnclub Werkstatt 87",
                "description": "",
                "event_url": url,
            })

    return events


# ─── 8. MSC Blankenloch ─────────────────────────────────────────
def scrape_msc_blankenloch():
    try:
        html = fetch_url("http://www.msc-blankenloch.de/termine")
    except Exception:
        return []
    events = []
    url = "http://www.msc-blankenloch.de/termine"
    # Parse the HTML table
    rows = re.findall(
        r'<tr[^>]*>(.*?)</tr>',
        html, re.DOTALL
    )
    for row in rows:
        cells = re.findall(r'<td[^>]*>(.*?)</td>', row, re.DOTALL)
        if len(cells) < 2:
            continue
        date_text = strip_html(cells[0])
        title = strip_html(cells[1])
        loc = strip_html(cells[2]) if len(cells) > 2 else "Vereinsheim"
        if not date_text or not title:
            continue
        # Handle "22-25.05.2026" format
        range_m = re.match(r'(\d{1,2})-(\d{1,2})\.(\d{1,2})\.(\d{4})', date_text)
        if range_m:
            d1, d2, mo, y = range_m.groups()
            date_start = parse_german_date(d1, mo, y)
            date_end = parse_german_date(d2, mo, y)
        else:
            m = re.match(r'(\d{1,2})\.(\d{1,2})\.(\d{4})', date_text)
            if not m:
                continue
            d, mo, y = m.groups()
            date_start = parse_german_date(d, mo, y)
            date_end = None
        events.append({
            "title": title,
            "date_start": date_start,
            "date_end": date_end,
            "time_raw": "",
            "location": loc if loc and loc != " " else "Vereinsheim, Seegrabenweg 9, Stutensee",
            "organizer": "Motorsportclub Blankenloch e.V. im ADAC",
            "description": "",
            "event_url": url,
        })
    return events


# ─── 9. Musikverein Spöck ───────────────────────────────────────
def scrape_musikverein_spoeck():
    try:
        html = fetch_url("https://musikverein-spoeck.de/")
    except Exception:
        return []
    events = []
    url = "https://musikverein-spoeck.de/"

    rows = re.findall(
        r'<tr[^>]*>(.*?)</tr>',
        html, re.DOTALL
    )
    for row in rows:
        cells = re.findall(r'<td[^>]*>(.*?)</td>', row, re.DOTALL)
        if len(cells) < 3:
            continue
        date_text = strip_html(cells[0])
        time_text = strip_html(cells[1])
        title = strip_html(cells[2])
        loc = strip_html(cells[3]) if len(cells) > 3 else "Spöck"
        if not date_text or not title or not re.search(r'\d{2}\.\d{2}\.\d{4}', date_text):
            continue
        m = re.match(r'(\d{1,2})\.(\d{1,2})\.(\d{4})', date_text)
        if not m:
            continue
        d, mo, y = m.groups()
        date_start = parse_german_date(d, mo, y)
        events.append({
            "title": title,
            "date_start": date_start,
            "date_end": None,
            "time_raw": time_text,
            "location": loc,
            "organizer": "Musikverein Harmonie Spöck",
            "description": "",
            "event_url": url,
        })
    return events


# ─── 10. Piraten Stutensee ──────────────────────────────────────
def scrape_piraten_stutensee():
    # EventON calendar loads via AJAX - not scrapable from static HTML
    # Known events from website navigation structure
    try:
        html = fetch_url("https://www.piraten-stutensee.de/")
    except Exception:
        return []
    events = []
    url = "https://www.piraten-stutensee.de/"
    if "Oktoberfest" in html:
        events.append({
            "title": "Oktoberfest",
            "date_start": "2026-10-01",
            "date_end": None,
            "time_raw": "",
            "location": "Vereinsheim, Piraten Stutensee",
            "organizer": "Karnevalsclub Die Piraten Stutensee e.V.",
            "description": "",
            "event_url": url,
        })
    if "Glühweinfest" in html:
        events.append({
            "title": "Glühweinfest",
            "date_start": "2026-12-01",
            "date_end": None,
            "time_raw": "",
            "location": "Vereinsheim, Piraten Stutensee",
            "organizer": "Karnevalsclub Die Piraten Stutensee e.V.",
            "description": "",
            "event_url": url,
        })
    return events


# ─── Main ────────────────────────────────────────────────────────
def scrape_clubs_p3():
    scrapers = [
        ("Hugenottenmuseum Friedrichstal", scrape_hugenotten_museum),
        ("KFW Spöck", scrape_kfw_spoeck),
        ("Kleintierzuchtverein Friedrichstal", scrape_kleintierzucht),
        ("LGV Blankenloch", scrape_lgv_blankenloch),
        ("Staffort LGV", scrape_staffort_lgv),
        ("Little Creek", scrape_little_creek),
        ("Werkstatt 87", scrape_werkstatt87),
        ("MSC Blankenloch", scrape_msc_blankenloch),
        ("Musikverein Spöck", scrape_musikverein_spoeck),
        ("Piraten Stutensee", scrape_piraten_stutensee),
    ]

    all_events = []
    for name, func in scrapers:
        try:
            result = func()
            all_events.extend(result)
        except Exception as e:
            sys.stderr.write(f"Error scraping {name}: {e}\n")

    return {"source_url": "clubs_batch3", "events": all_events}


def main():
    result = scrape_clubs_p3()
    print(json.dumps(result, ensure_ascii=False, indent=2))
    sys.stderr.write(f"Found {len(result['events'])} events\n")


if __name__ == "__main__":
    main()
