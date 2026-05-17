#!/usr/bin/env python3
"""
scraper_tsg_blankenloch.py — Scraper for TSG Blankenloch event calendar.

TSG Blankenloch is a large sports club in Stutensee-Blankenloch.
Events are listed on the /Veranstaltungen/ page.

Excludes events already covered by other sources (Spechaa-Lauf, Waldlauf, Triathlon).
Deduplicates multi-day events vs. individual Arbeitseinsatz entries.
"""

import re
import requests
from bs4 import BeautifulSoup

BASE_URL = "https://tsg-blankenloch.de"
CALENDAR_URL = f"{BASE_URL}/Veranstaltungen/"

# Events to exclude — already covered by other scrapers
# (title substring match, case-insensitive)
EXCLUDED_TITLES = [
    "Spechaa-Lauf",
    "Spechaa Lauf",
    "Waldlauf",
    "Friedrichstaler Waldlauf",
    "Stutenseer Stadtlauf",
    "Topiblüten-Lauf",
    "Topiblueten-Lauf",
]

# Exclude specific (date, title) combinations
EXCLUDED_EVENTS = {
    ("2026-06-20", "32. Heinz Beierstorf Triathlon"),  # "Aufbau" already covered
    ("2026-06-21", "32. Heinz Beierstorf Triathlon"),  # main event already covered
}


def fetch_url(url, session=None, timeout=30):
    if session is None:
        session = requests.Session()
    try:
        resp = session.get(url, timeout=timeout, headers={
            "User-Agent": "Mozilla/5.0 (compatible; StutenseeBot/1.0)"
        })
        resp.raise_for_status()
        return resp.text
    except Exception as e:
        print(f"  Error fetching {url}: {e}", flush=True)
        return None


def parse_german_date(text):
    text = text.strip()
    m = re.search(r"(\d{1,2})\.(\d{1,2})\.(\d{4})", text)
    if m:
        return f"{m.group(3)}-{int(m.group(2)):02d}-{int(m.group(1)):02d}"
    return None


def is_excluded(title, date_start):
    """Check if an event should be skipped (already covered by other sources)."""
    title_lower = title.lower()
    for excl in EXCLUDED_TITLES:
        if excl.lower() in title_lower:
            print(f"  TSG skip (dup from other source): {date_start} | {title}", flush=True)
            return True
    if (date_start, title) in EXCLUDED_EVENTS:
        print(f"  TSG skip (dup from other source): {date_start} | {title}", flush=True)
        return True
    return False


def assign_tags(title, category, location):
    """Assign appropriate tags based on title, category, and location."""
    tags = []
    title_lower = title.lower()
    
    if category == "Arbeitseinsatz":
        tags.append("Sonstiges")
    elif "weihnachtsmarkt" in title_lower or "weihnacht" in title_lower:
        tags.extend(["Fest", "Markt"])
    elif "halloween" in title_lower:
        tags.append("Fest")
    elif "nikolaus" in title_lower:
        tags.append("Kinder")
    elif "triathlon" in title_lower or "lauf" in title_lower or "cup" in title_lower:
        tags.extend(["Sport", "Laufen"])
    else:
        tags.append("Sport")
    
    # Add district tag
    loc_lower = location.lower()
    if "blankenloch" in loc_lower or not any(d in loc_lower for d in ["spöck", "staffort", "friedrichstal"]):
        tags.append("Blankenloch")
    elif "spöck" in loc_lower:
        tags.append("Spöck")
    elif "staffort" in loc_lower:
        tags.append("Staffort")
    elif "friedrichstal" in loc_lower:
        tags.append("Friedrichstal")
    
    return tags


def scrape_tsg_blankenloch():
    session = requests.Session()
    session.headers.update({"User-Agent": "Mozilla/5.0 (compatible; StutenseeBot/1.0)"})

    all_events = []
    seen_dates = {}  # title -> set of date ranges covered (to catch multi-day vs single-day dups)

    # --- Scrape main Veranstaltungen calendar ---
    html = fetch_url(CALENDAR_URL, session)
    if html:
        soup = BeautifulSoup(html, "html.parser")
        for td in soup.find_all("td", class_="contenttable"):
            row = td.find_parent("tr")
            if not row:
                continue
            cells = row.find_all("td")
            if len(cells) < 2:
                continue

            # Cell 0: dates (start<br/>end)
            date_cell = cells[0]
            date_parts = date_cell.get_text(" ", strip=True).split()
            date_start = parse_german_date(date_parts[0]) if date_parts else None
            date_end = parse_german_date(date_parts[-1]) if len(date_parts) > 1 and parse_german_date(date_parts[-1]) else date_start
            if not date_start:
                continue

            # Cell 1: title <br/> location
            info_cell = cells[1]
            br = info_cell.find("br")
            if br:
                title = info_cell.contents[0].strip() if info_cell.contents else ""
                location = br.next_sibling.strip() if br.next_sibling else ""
                title = re.sub(r'\s+', ' ', title).strip()
                location = re.sub(r'\s+', ' ', location).strip()
            else:
                title = info_cell.get_text(strip=True)
                location = "Blankenloch"

            # Skip excluded events that are already covered by other sources
            if is_excluded(title, date_start):
                continue

            # Cell 3 (optional): category/Abteilung
            category = cells[3].get_text(strip=True) if len(cells) >= 4 else ""

            # Dedup: if we already have an event with same title whose date range
            # covers this one, skip (prevents Arbeitseinsatz entries that are for
            # the same multi-day event)
            if title in seen_dates:
                existing_start, existing_end = seen_dates[title]
                # Skip if this single-day event falls within existing multi-day range
                if existing_start <= date_start <= existing_end and \
                   existing_start <= (date_end or date_start) <= existing_end:
                    print(f"  TSG skip (dup within multi-day range): {date_start} | {title}", flush=True)
                    continue
                # Also skip if previous entry was single-day and this is too
                if date_start == date_end and existing_start == existing_end:
                    print(f"  TSG skip (dup single-day): {date_start} | {title}", flush=True)
                    continue

            seen_dates[title] = (date_start, date_end or date_start)

            district = "blankenloch"
            loc_lower = location.lower()
            if "spöck" in loc_lower:
                district = "spöck"
            elif "staffort" in loc_lower:
                district = "staffort"
            elif "friedrichstal" in loc_lower:
                district = "friedrichstal"

            tags = assign_tags(title, category, location)

            all_events.append({
                "title": title,
                "date_start": date_start,
                "date_end": date_end,
                "time_raw": "",
                "location": location if location and location != " " else "TSG Blankenloch",
                "organizer": "TSG Blankenloch",
                "description": "",
                "event_url": CALENDAR_URL,
                "district": district,
                "tags": tags,
            })
            print(f"  TSG: {date_start}→{date_end or date_start} | {title} | {location}", flush=True)

    print(f"  TSG Blankenloch total: {len(all_events)} events", flush=True)
    return {
        "source_url": CALENDAR_URL,
        "events": all_events,
    }


if __name__ == "__main__":
    result = scrape_tsg_blankenloch()
    print(f"\nFound {len(result['events'])} events from TSG Blankenloch")
    for e in result["events"]:
        print(f"  {e['date_start']}→{e['date_end']} | {e['title']} | {e['location']} | district={e['district']} | tags={e['tags']}")
