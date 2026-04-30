#!/usr/bin/env python3
"""
Scraper for Batch 2 club sites (10 Stutensee clubs).

Events are dynamically loaded in some sites (ekistuwei.de, posaunenchor Google Calendar),
so those return []. Reliable event data sources:
- gvl-spoeck.clubdesk.com: homepage news tile
- ttf-spoeck.de: static HTML
- fcfriedrichstal.de: Jimdo homepage game schedule
- saengerbund-friedrichstal.de: homepage event table
- gospel-unlimited.de: Drupal /termine page
"""
import re
import json
import sys
import urllib.request


def fetch_url(url, timeout=30):
    req = urllib.request.Request(url, headers={"User-Agent": "StutenseeEvents/1.0"})
    resp = urllib.request.urlopen(req, timeout=timeout)
    return resp.read().decode("utf-8", errors="replace")


def to_iso(date_str):
    """Convert DD.MM.YYYY or DD.MM.YY to YYYY-MM-DD."""
    m = re.match(r'(\d{1,2})\.(\d{1,2})\.(\d{2,4})$', date_str.strip())
    if not m:
        return None
    d, mo, y = m.groups()
    if len(y) == 2:
        y = '20' + y
    return f"{y}-{int(mo):02d}-{int(d):02d}"


def strip_html(text):
    text = re.sub(r'<[^>]+>', ' ', text)
    text = text.replace('&amp;', '&').replace('&nbsp;', ' ').replace('&#8211;', '-')
    text = text.replace('&#8217;', "'").replace('&#8222;', '"').replace('&#8220;', '"')
    text = re.sub(r'\s+', ' ', text).strip()
    return text


GERMAN_MONTHS = {
    "Januar": "01", "Februar": "02", "März": "03", "April": "04",
    "Mai": "05", "Juni": "06", "Juli": "07", "August": "08",
    "September": "09", "Oktober": "10", "November": "11", "Dezember": "12",
    "Jan": "01", "Feb": "02", "Mär": "03", "Apr": "04", "Mai": "05",
    "Jun": "06", "Jul": "07", "Aug": "08", "Sep": "09", "Okt": "10",
    "Nov": "11", "Dez": "12",
}


def parse_german_date(day, month_name, year="2026"):
    month = GERMAN_MONTHS.get(month_name)
    if not month:
        return None
    return f"{year}-{month}-{int(day):02d}"


# ─── Site 1: Kirchengemeinde Staffort-Büchenau ──────────────────────────────
# Events loaded dynamically via Edith CMS API. No reliable static HTML extraction.

def scrape_kg_staffort():
    return []


# ─── Site 2: Posaunenchor Blankenloch ──────────────────────────────────────
# Uses embedded Google Calendar iframe. No static event data.

def scrape_posaunenchor_blankenloch():
    return []


# ─── Site 3: Evangelische Kirche Spöck ──────────────────────────────────────
# Events loaded dynamically via Edith CMS API.

def scrape_ek_spoeck():
    return []


# ─── Site 4: GVL Spöck (clubdesk.com) ──────────────────────────────────────

def scrape_gvl_spoeck():
    """Scrape from gvl-spoeck.clubdesk.com homepage."""
    url = "https://gvl-spoeck.clubdesk.com"
    try:
        html = fetch_url(url)
    except Exception:
        return []
    events = []
    seen = set()

    for item_m in re.finditer(
        r'cd-tile-v-main-heading[^>]*>(.*?)</div>.*?cd-tile-v-detail-value[^>]*>(.*?)</div>',
        html, re.DOTALL
    ):
        heading = strip_html(item_m.group(1))
        detail = strip_html(item_m.group(2))
        date_m = re.search(r'am\s+(\d{1,2})\.(\w+)\s*(\d{4})', heading)
        if not date_m:
            date_m = re.search(r'am\s+(\d{1,2})\.(\w+)', heading)
        if not date_m:
            date_m = re.search(r'(\d{1,2})\.(\w+)\s*(\d{4})', heading)
        if not date_m:
            continue
        day = date_m.group(1)
        month_name = date_m.group(2)
        year = date_m.group(3) if date_m.lastindex >= 3 else "2026"
        iso = parse_german_date(day, month_name, year)
        if not iso:
            continue
        if iso not in seen:
            seen.add(iso)
            title = heading.split("am")[0].strip() if "am" in heading else heading
            title = title.rstrip(',;:')
            events.append({
                "title": title if title else "Waldfest",
                "date_start": iso,
                "date_end": None,
                "time_raw": "",
                "location": "Spöck",
                "organizer": "Gesangverein Liederkranz Spöck",
                "description": detail,
                "event_url": url,
            })
    return events


# ─── Site 5: TTF Spöck ──────────────────────────────────────────────────────

def scrape_ttf_spoeck():
    """Scrape from ttf-spoeck.de (single static page)."""
    url = "https://www.ttf-spoeck.de/"
    try:
        html = fetch_url(url)
    except Exception:
        return []
    events = []
    event_section = re.search(
        r'<h2>2er Mannschaftsturnier</h2>(.*?)(?:<h2>|$)',
        html, re.DOTALL
    )
    if event_section:
        text = event_section.group(1)
        date_m = re.search(r'(\d{1,2})\.\s*(\w+)\s*um\s*(\d{1,2})[:.](\d{2})\s*Uhr', text)
        if date_m:
            day, month_name, hour, minute = date_m.groups()
            iso = parse_german_date(day, month_name, "2026")
            if iso:
                loc_m = re.search(r'in der (.*?alle)', text)
                location = strip_html(loc_m.group(1)) if loc_m else "Spechaahalle, Spöck"
                if not location.endswith("Spöck"):
                    location = location + ", Spöck"
                events.append({
                    "title": "2er Mannschaftsturnier",
                    "date_start": iso,
                    "date_end": None,
                    "time_raw": f"{int(hour):02d}:{minute} Uhr",
                    "location": location,
                    "organizer": "TTF Schwarz-Weiß Spöck",
                    "description": strip_html(text)[:300],
                    "event_url": url,
                })
    return events


# ─── Site 6: Friedrichstaler Backhaus ──────────────────────────────────────
# WordPress blog - all event posts found were from 2025, none in 2026.

def scrape_friedrichstaler_backhaus():
    return []


# ─── Site 7: FC Friedrichstal ──────────────────────────────────────────────

def scrape_fcfriedrichstal():
    """Scrape match events from fcfriedrichstal.de homepage."""
    url = "https://www.fcfriedrichstal.de/"
    try:
        html = fetch_url(url)
    except Exception:
        return []
    events = []
    seen = set()

    game_blocks = re.findall(
        r'(?:bfv-Kreisliga[^<]*</strong>|bfv-Kreisklasse[^<]*</strong>).*?'
        r'(?:Sonntag|Samstag|Freitag|Mittwoch|Montag|Donnerstag)'
        r'[.,]?\s*(\d{1,2})\.(\d{1,2})\.(\d{4})'
        r'(?:,\s*(\d{1,2})[:.](\d{2})\s*Uhr)?'
        r'.*?<b>(.*?)</b>',
        html, re.DOTALL
    )

    for block in re.finditer(
        r'(?:bfv-Kreisliga[^<]*</strong>|bfv-Kreisklasse[^<]*</strong>).*?'
        r'(Sonntag|Samstag|Freitag|Mittwoch|Montag|Donnerstag)'
        r'[.,]?\s*(\d{1,2})\.(\d{1,2})\.(\d{4})'
        r'(?:[,]\s*(\d{1,2})[:.](\d{2}))?'
        r'(?:\s*Uhr)?'
        r'.*?<b>(.*?)</b>',
        html, re.DOTALL
    ):
        weekday, day, month, year = block.group(1), block.group(2), block.group(3), block.group(4)
        hour, minute = block.group(5), block.group(6)
        match_name = block.group(7)
        iso = f"{year}-{int(month):02d}-{int(day):02d}"
        title = strip_html(match_name)
        if not title or len(title) < 5 or len(title) > 80:
            continue
        key = (iso, title)
        if key in seen:
            continue
        seen.add(key)
        time_raw = f"{int(hour):02d}:{minute} Uhr" if hour and minute else ""
        events.append({
            "title": title,
            "date_start": iso,
            "date_end": None,
            "time_raw": time_raw,
            "location": "Friedrichstal",
            "organizer": "FC Germania Friedrichstal",
            "description": "",
            "event_url": url,
        })

    return events


# ─── Site 8: Concordia Blankenloch ──────────────────────────────────────────
# Complex WPBakery site. No structured event data found.

def scrape_gv_concordia_blankenloch():
    return []


# ─── Site 9: Sängerbund Friedrichstal ──────────────────────────────────────

def scrape_saengerbund_friedrichstal():
    """Scrape from saengerbund-friedrichstal.de homepage event table."""
    url = "https://saengerbund-friedrichstal.de/"
    try:
        html = fetch_url(url)
    except Exception:
        return []
    events = []
    seen = set()

    for row_m in re.finditer(
        r'<tr class="el-item">(.*?)</tr>',
        html, re.DOTALL
    ):
        row_html = row_m.group(1)
        date_text_m = re.search(r'class="el-title">(.*?)</div>', row_html)
        content_m = re.search(r'class="el-content[^"]*">(.*?)</div>', row_html)
        if not date_text_m or not content_m:
            continue
        date_text = strip_html(date_text_m.group(1))
        content_text = strip_html(content_m.group(1))
        date_m = re.search(r'(\d{1,2})\.\s*(\w+)\.?\s*(\d{4})', date_text)
        if not date_m:
            continue
        day, month_name, year = date_m.groups()
        iso = parse_german_date(day, month_name, year)
        if not iso or iso > "2026-12-31" or iso < "2026-01-01":
            continue
        if iso in seen:
            continue
        seen.add(iso)
        title_match = re.search(r'<strong>(.*?)</strong>', content_m.group(1))
        title = strip_html(title_match.group(1)) if title_match else content_text[:80]
        events.append({
            "title": title,
            "date_start": iso,
            "date_end": None,
            "time_raw": "",
            "location": "Sängerhalle Friedrichstal",
            "organizer": "Gesangverein Sängerbund Friedrichstal",
            "description": content_text[:500],
            "event_url": url,
        })

    blockquote_m = re.search(
        r'Samstag\s+(\d{1,2})\.\s*(\w+)\s*(\d{4})\s*[-–]\s*(\d{1,2})[:.](\d{2})\s*Uhr',
        html
    )
    if blockquote_m:
        day, month_name, year, hour, minute = blockquote_m.groups()
        iso = parse_german_date(day, month_name, year)
        if iso and iso not in seen:
            seen.add(iso)
            events.append({
                "title": "Stage Fever Klangdialog",
                "date_start": iso,
                "date_end": None,
                "time_raw": f"{int(hour):02d}:{int(minute):02d} Uhr",
                "location": "Sängerhalle Friedrichstal",
                "organizer": "Gesangverein Sängerbund Friedrichstal",
                "description": "Chorkonzert mit vier Chören unter Leitung von Aldo Martínez",
                "event_url": url,
            })

    return events


# ─── Site 10: Gospel Unlimited ──────────────────────────────────────────────

def scrape_gospel_unlimited():
    """Scrape from gospel-unlimited.de /termine Drupal page."""
    url = "https://www.gospel-unlimited.de/termine"
    try:
        html = fetch_url(url)
    except Exception:
        return []
    events = []
    seen = set()

    for page_item in re.finditer(
        r'termin-page-item.*?'
        r'datum[^>]*>(.*?)</div>.*?'
        r'zeit[^>]*>(.*?)</div>.*?'
        r'info[^>]*>(.*?)</div>',
        html, re.DOTALL
    ):
        date_text = strip_html(page_item.group(1))
        time_text = strip_html(page_item.group(2))
        info_text = strip_html(page_item.group(3))

        iso = to_iso(date_text)
        if not iso or iso > "2026-12-31" or iso < "2026-01-01":
            continue

        info_parts = [p.strip() for p in info_text.split('\n') if p.strip()]
        title = info_parts[0] if info_parts else "Termin"
        if len(title) > 80:
            continue

        location = ""
        for part in info_parts[1:]:
            if not part.startswith('mehr') and part not in title:
                location = part
                break

        if iso not in seen:
            seen.add(iso)
            title = re.sub(r'\s*mehr\.\.\.$', '', title).strip()
            location = re.sub(r'\s*mehr\.\.\.$', '', location).strip() if location else ""
            events.append({
                "title": title,
                "date_start": iso,
                "date_end": None,
                "time_raw": time_text,
                "location": location if location else "Büchig",
                "organizer": "Gospel Unlimited",
                "description": "",
                "event_url": url,
            })

    return events


# ─── Main ────────────────────────────────────────────────────────────────────

def scrape_clubs_p2():
    """Scrape all batch 2 club sites and return aggregated results."""
    scrapers = [
        ("Kirchengemeinde Staffort-Büchenau", scrape_kg_staffort),
        ("Posaunenchor Blankenloch", scrape_posaunenchor_blankenloch),
        ("Evangelische Kirche Spöck", scrape_ek_spoeck),
        ("GVL Spöck", scrape_gvl_spoeck),
        ("TTF Spöck", scrape_ttf_spoeck),
        ("Friedrichstaler Backhaus", scrape_friedrichstaler_backhaus),
        ("FC Friedrichstal", scrape_fcfriedrichstal),
        ("Concordia Blankenloch", scrape_gv_concordia_blankenloch),
        ("Sängerbund Friedrichstal", scrape_saengerbund_friedrichstal),
        ("Gospel Unlimited", scrape_gospel_unlimited),
    ]

    all_events = []
    for name, scraper_fn in scrapers:
        try:
            result = scraper_fn()
            all_events.extend(result)
            sys.stderr.write(f"  {name}: {len(result)} events\n")
        except Exception as e:
            sys.stderr.write(f"  {name}: ERROR - {e}\n")

    return {"source_url": "clubs_batch2", "events": all_events}


def main():
    result = scrape_clubs_p2()
    print(json.dumps(result, ensure_ascii=False, indent=2))
    sys.stderr.write(f"Total: {len(result['events'])} events from batch 2\n")


if __name__ == '__main__':
    main()
