#!/usr/bin/env python3
"""
scraper_tsg_blankenloch.py — Scraper for TSG Blankenloch event calendar.

TSG Blankenloch is a large sports club in Stutensee-Blankenloch.
Events are listed on the /Veranstaltungen/ page with dates, title, and location.
Events are in HTML tables with class="contenttable".
"""

import re
import requests
from bs4 import BeautifulSoup

BASE_URL = "https://tsg-blankenloch.de"
CALENDAR_URL = f"{BASE_URL}/Veranstaltungen/"
CUP_URL = f"{BASE_URL}/Veranstaltungen/StutenseeCUP/"


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


def scrape_tsg_blankenloch():
    session = requests.Session()
    session.headers.update({"User-Agent": "Mozilla/5.0 (compatible; StutenseeBot/1.0)"})

    all_events = []
    seen = set()  # dedup by (date, title)

    # --- Scrape main Veranstaltungen calendar ---
    html = fetch_url(CALENDAR_URL, session)
    if html:
        soup = BeautifulSoup(html, "html.parser")
        # Find all rows in contenttable-class tables
        for td in soup.find_all("td", class_="contenttable"):
            row = td.find_parent("tr")
            if not row:
                continue
            cells = row.find_all("td")
            if len(cells) < 2:
                continue

            # Cell 0: dates (may have <br/> separator for start/end)
            date_cell = cells[0]
            date_parts = date_cell.get_text(" ", strip=True).split()
            date_start = parse_german_date(date_parts[0]) if date_parts else None
            date_end = parse_german_date(date_parts[-1]) if len(date_parts) > 1 and parse_german_date(date_parts[-1]) else date_start
            if not date_start:
                continue

            # Cell 1: title <br/> location (separated by <br/> tag)
            info_cell = cells[1]
            br = info_cell.find("br")
            if br:
                title = info_cell.contents[0].strip() if info_cell.contents else ""
                location = br.next_sibling.strip() if br.next_sibling else ""
                # Clean up whitespace
                title = re.sub(r'\s+', ' ', title).strip()
                location = re.sub(r'\s+', ' ', location).strip()
            else:
                title = info_cell.get_text(strip=True)
                location = "Blankenloch"

            # Cell 3 (optional): category/Abteilung
            category = cells[3].get_text(strip=True) if len(cells) >= 4 else ""

            key = (date_start, title)
            if key in seen:
                continue
            seen.add(key)

            # Determine district based on location
            district = "blankenloch"
            loc_lower = location.lower()
            if "spöck" in loc_lower or "spechaa" in loc_lower:
                district = "spöck"
            elif "staffort" in loc_lower:
                district = "staffort"
            elif "friedrichstal" in loc_lower:
                district = "friedrichstal"

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
                "tags": ["Sport"],
            })
            print(f"  TSG: {date_start} | {title} | {location}", flush=True)

    # --- Scrape Stutensee CUP page ---
    html = fetch_url(CUP_URL, session)
    if html:
        soup = BeautifulSoup(html, "html.parser")
        content = soup.find("div", id="content") or soup.find("main") or soup
        text = content.get_text(strip=True)

        # Parse running events from CUP listing
        # Pattern: "X. Lauf DD.MM.YYYY <optional_num.> <title> XX km <organizer>"
        cup_matches = re.findall(
            r'(\d+)\.\s*Lauf\s*(\d{2}\.\d{2}\.\d{4})\s*(?:\d+\.\s*)?(.+?)(?:\d+\s*km)\s*(.+?)(?=\d+\.\s*Lauf|\s*Wir\s|\s*$|$)',
            text
        )
        for cup_num, date_str, event_name, organizer in cup_matches:
            date = f"{date_str[6:10]}-{date_str[3:5]}-{date_str[0:2]}"
            title = event_name.strip()
            org = organizer.strip()
            key = (date, title)
            if key in seen:
                continue
            seen.add(key)
            
            # Determine district
            district = "blankenloch"
            title_lower = title.lower()
            org_lower = org.lower()
            if "spöck" in title_lower or "spöck" in org_lower:
                district = "spöck"
            elif "staffort" in title_lower or "staffort" in org_lower:
                district = "staffort"
            elif "friedrichstal" in title_lower or "friedrichstal" in org_lower:
                district = "friedrichstal"

            all_events.append({
                "title": title,
                "date_start": date,
                "date_end": date,
                "time_raw": "",
                "location": f"{org}" if org else "Blankenloch",
                "organizer": org or "TSG Blankenloch",
                "description": "",
                "event_url": CUP_URL,
                "district": district,
                "tags": ["Sport", "Laufen"],
            })
            print(f"  TSG CUP: {date} | {title} | {org}", flush=True)

    print(f"  TSG Blankenloch total: {len(all_events)} events", flush=True)
    return {
        "source_url": CALENDAR_URL,
        "events": all_events,
    }


if __name__ == "__main__":
    result = scrape_tsg_blankenloch()
    print(f"\nFound {len(result['events'])} events from TSG Blankenloch")
    for e in result["events"]:
        print(f"  {e['date_start']} | {e['title']} | {e['location']} | district={e['district']}")
