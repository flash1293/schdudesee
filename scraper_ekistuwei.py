#!/usr/bin/env python3
"""
scraper_ekistuwei.py — Scrape event calendars from ekistuwei.de
(Evangelischer Kooperationsraum Stutensee-Weingarten).

Covers 4 Stutensee congregations:
  - Friedrichstal  (weekly table layout)
  - Blankenloch    (list layout)
  - Spöck          (list layout)
  - Staffort-Büchenau (list layout)

The site uses Edith CMS with two calendar rendering modes:
  1. v-calfe (table): Friedrichstal — pre-rendered server-side
  2. v-listefe (list): Blankenloch, Spöck, Staffort-Büchenau — pre-rendered server-side
"""

import re
import sys
import urllib.request
from datetime import datetime

BASE = "https://www.ekistuwei.de"

CONGREGATIONS = [
    {
        "name": "Friedrichstal",
        "url": "/gemeinden/kirchengemeinde-friedrichstal-3/terminkalender",
        "district": "Friedrichstal",
        "organizer": "Evangelische Kirchengemeinde Friedrichstal",
        "layout": "table",  # v-calfe
    },
    {
        "name": "Blankenloch",
        "url": "/gemeinden/michaelisgemeinde-blankenloch/kalender",
        "district": "Blankenloch",
        "organizer": "Michaelisgemeinde Blankenloch",
        "layout": "list",  # v-listefe
    },
    {
        "name": "Spöck",
        "url": "/gemeinden/kirchengemeinde-spoeck/termine-spoeck-2",
        "district": "Spöck",
        "organizer": "Evangelische Kirchengemeinde Spöck",
        "layout": "list",
    },
    {
        "name": "Staffort-Büchenau",
        "url": "/gemeinden/kirchengemeinde-staffort-buechenau/termine",
        "district": "Staffort",  # Staffort is the primary Stutensee district; Büchenau is Bruchsal
        "organizer": "Evangelische Kirchengemeinde Staffort-Büchenau",
        "layout": "list",
    },
]

# How many months ahead to scrape
MONTHS_AHEAD = 6


def fetch_url(url, timeout=30):
    req = urllib.request.Request(url, headers={"User-Agent": "StutenseeEvents/1.0"})
    resp = urllib.request.urlopen(req, timeout=timeout)
    return resp.read().decode("utf-8", errors="replace")


def parse_german_date(date_str):
    """Parse 'Do, 16.07.2026' or 'Do. 16.07.2026' → YYYY-MM-DD."""
    m = re.search(r"(\d{1,2})\.(\d{1,2})\.(\d{4})", date_str)
    if m:
        return f"{m.group(3)}-{int(m.group(2)):02d}-{int(m.group(1)):02d}"
    return None


def parse_time_range(time_str):
    """Parse 'Mi. 15.07.2026, 14:00 bis 17:30 Uhr' or '09:00 Uhr' → (time_start, time_end)."""
    time_str = time_str.replace("Uhr", "").strip()
    m = re.search(r"(\d{1,2}:\d{2})\s*(?:bis|-)\s*(\d{1,2}:\d{2})", time_str)
    if m:
        return m.group(1).strip(), m.group(2).strip()
    m = re.search(r"(\d{1,2}:\d{2})", time_str)
    if m:
        return m.group(1).strip(), None
    return None, None


def scrape_table_layout(html, congregation, source_url):
    """
    Parse the weekly table layout (v-calfe) used by Friedrichstal.
    """
    events = []
    # Find all day headers and their events
    # Structure: <th class="dayhead"><div class="v-calfe-datum">Mo, 13.07.2026</div></th>
    # followed by <tr class="daytimeentry"> rows with events

    # Split by dayhead to get each day's section
    day_sections = re.split(
        r'<th[^>]*class="[^"]*dayhead[^"]*"[^>]*>.*?<div[^>]*class="[^"]*v-calfe-datum[^"]*"[^>]*>(.*?)</div>.*?</th>',
        html,
        flags=re.DOTALL,
    )
    # First element is before the first dayhead, rest are pairs of (date_str, content)
    for i in range(1, len(day_sections), 2):
        if i + 1 > len(day_sections):
            break
        date_str = day_sections[i].strip()
        date_start = parse_german_date(date_str)
        if not date_start:
            continue

        content = day_sections[i + 1]

        # Find all v-calfe-item blocks in this day
        items = re.findall(r'<div[^>]*class="[^"]*v-calfe-item[^"]*"[^>]*>(.*?)</div>\s*</div>\s*</div>', content, re.DOTALL)
        if not items:
            # Simpler regex
            items = re.findall(r'<div[^>]*class="[^"]*v-calfe-item[^"]*"[^>]*>(.*?)</div>', content, re.DOTALL)

        # Also find daytimeentry rows to get times per row
        daytime_rows = re.findall(
            r'<tr[^>]*class="[^"]*daytimeentry[^"]*"[^>]*>(.*?)</tr>',
            content,
            re.DOTALL,
        )
        # Map: for each daytimeentry, extract time and associated events
        row_events = []
        for row_html in daytime_rows:
            time_m = re.search(r'<span[^>]*title="([^"]+)"[^>]*>', row_html)
            time_raw = time_m.group(1) if time_m else ""
            # Find v-calfe-item blocks in this row
            row_items = re.findall(
                r'<div[^>]*class="[^"]*v-calfe-item[^"]*"[^>]*>(.*?)</div>\s*</div>\s*</div>',
                row_html,
                re.DOTALL,
            )
            if not row_items:
                row_items = re.findall(
                    r'<div[^>]*class="[^"]*v-calfe-item[^"]*"[^>]*>(.*?)</div>',
                    row_html,
                    re.DOTALL,
                )
            for item_html in row_items:
                row_events.append((time_raw, item_html))

        for time_raw, item_html in row_events:
            # Title
            title_m = re.search(r'<span[^>]*class="[^"]*termin-titel[^"]*"[^>]*>(.*?)</span>', item_html, re.DOTALL)
            title = title_m.group(1).strip() if title_m else None

            # Event URL
            url_m = re.search(r'<a[^>]*href="([^"]*detail/termin/id/\d+[^"]*)"', item_html)
            event_url = url_m.group(1) if url_m else source_url
            if event_url.startswith("/"):
                event_url = BASE + event_url

            # Location
            loc_name_m = re.search(r'<div[^>]*class="[^"]*oertlichkeit-name[^"]*"[^>]*>(.*?)</div>', item_html, re.DOTALL)
            loc_ort_m = re.search(r'<div[^>]*class="[^"]*oertlichkeit-ort[^"]*"[^>]*>(.*?)</div>', item_html, re.DOTALL)
            location_parts = []
            if loc_name_m:
                location_parts.append(loc_name_m.group(1).strip())
            if loc_ort_m:
                location_parts.append(loc_ort_m.group(1).strip())
            location = ", ".join(location_parts) if location_parts else congregation["district"]

            if title:
                events.append({
                    "title": title,
                    "date_start": date_start,
                    "date_end": None,
                    "time_raw": time_raw or "",
                    "location": location,
                    "organizer": congregation["organizer"],
                    "description": "",
                    "event_url": event_url,
                })

    return events


def scrape_list_layout(html, congregation, source_url):
    """
    Parse the list layout (v-listefe) used by Blankenloch, Spöck, Staffort-Büchenau.
    """
    events = []

    # Find all list items
    items = re.findall(
        r'<div[^>]*class="[^"]*v-listefe-item[^"]*"[^>]*>(.*?)</div>\s*</div>\s*</div>\s*</div>',
        html,
        re.DOTALL,
    )

    for item_html in items:
        # Date: <div class="v-listefe-item-datum">Mi. 15.07.2026, 17:00 Uhr</div>
        date_m = re.search(
            r'class="[^"]*v-listefe-item-datum[^"]*"[^>]*>\s*(.*?)\s*</div>',
            item_html,
            re.DOTALL,
        )
        if not date_m:
            continue
        date_text = date_m.group(1).strip()

        # Parse date from text like "Mi. 15.07.2026, 17:00 Uhr" or "Mi. 15.07.2026, 17:00 bis 18:30 Uhr"
        date_start = parse_german_date(date_text)
        if not date_start:
            continue

        time_start, time_end = parse_time_range(date_text)
        time_raw = time_start or ""
        if time_end:
            time_raw += f" - {time_end}"

        # Title: <a title="zum Termin Konfinachtreffen" href="...">
        title_m = re.search(r'<a[^>]*title="zum\s+Termin\s+(.*?)"\s+href="([^"]+)"', item_html)
        if not title_m:
            continue
        title = title_m.group(1).strip()
        event_url = title_m.group(2)
        if event_url.startswith("/"):
            event_url = BASE + event_url

        # Location
        loc_name_m = re.search(
            r'class="[^"]*oertlichkeit-name[^"]*"[^>]*>(.*?)</div>',
            item_html,
            re.DOTALL,
        )
        loc_ort_m = re.search(
            r'class="[^"]*oertlichkeit-ort[^"]*"[^>]*>(.*?)</div>',
            item_html,
            re.DOTALL,
        )
        location_parts = []
        if loc_name_m:
            location_parts.append(loc_name_m.group(1).strip())
        if loc_ort_m:
            location_parts.append(loc_ort_m.group(1).strip())
        location = ", ".join(location_parts) if location_parts else congregation["district"]

        events.append({
            "title": title,
            "date_start": date_start,
            "date_end": None,
            "time_raw": time_raw,
            "location": location,
            "organizer": congregation["organizer"],
            "description": "",
            "event_url": event_url,
        })

    return events


def scrape_congregation(congregation):
    """Scrape a single congregation for the next MONTHS_AHEAD months."""
    all_events = []
    now = datetime.now()

    for offset in range(MONTHS_AHEAD):
        year = now.year + (now.month + offset - 1) // 12
        month = (now.month + offset - 1) % 12 + 1
        month_str = f"{year}-{month:02d}"

        # The month parameter key varies by congregation; try common patterns
        url = f"{BASE}{congregation['url']}?monat_f1092ea5={month_str}"
        try:
            html = fetch_url(url)
        except Exception as e:
            print(f"  {congregation['name']} {month_str}: {e}", flush=True)
            continue

        if congregation["layout"] == "table":
            month_events = scrape_table_layout(html, congregation, url)
        else:
            month_events = scrape_list_layout(html, congregation, url)

        all_events.extend(month_events)
        print(f"  {congregation['name']} {month_str}: {len(month_events)} events", flush=True)

    return all_events


def scrape_ekistuwei():
    """Main entry point — scrape all Stutensee congregations."""
    all_events = []

    for cong in CONGREGATIONS:
        print(f"Scraping {cong['name']}...", flush=True)
        try:
            events = scrape_congregation(cong)
            all_events.extend(events)
            print(f"  Total {cong['name']}: {len(events)} events", flush=True)
        except Exception as e:
            print(f"  Error scraping {cong['name']}: {e}", flush=True)

    return {
        "source_url": f"{BASE}/termine-und-nachrichten",
        "events": all_events,
    }


if __name__ == "__main__":
    result = scrape_ekistuwei()
    print(f"\nTotal: {len(result['events'])} events from ekistuwei.de")
    for e in result["events"]:
        dates = e["date_start"]
        if e.get("date_end"):
            dates += f" - {e['date_end']}"
        print(f"  {dates} | {e['title']} | {e['time_raw']} | {e['location']} | {e['organizer']}")
