#!/usr/bin/env python3
"""
scraper_cvjm_graben_neudorf.py — Scraper for CVJM Graben-Neudorf event calendar.

CVJM is a Christian youth organization with events in Graben-Neudorf.
Events are listed on /eventcalendar in div.ec-item-box elements.
Structure: h3.title = event name, p.address = location, date in box text.
"""

import re
import requests
from bs4 import BeautifulSoup

BASE_URL = "https://www.cvjm-graben-neudorf.de"
CALENDAR_URL = f"{BASE_URL}/eventcalendar"


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


def scrape_cvjm_graben_neudorf():
    session = requests.Session()
    session.headers.update({"User-Agent": "Mozilla/5.0 (compatible; StutenseeBot/1.0)"})

    all_events = []
    seen = set()

    html = fetch_url(CALENDAR_URL, session)
    if not html:
        return {"source_url": CALENDAR_URL, "events": []}

    soup = BeautifulSoup(html, "html.parser")
    boxes = soup.find_all("div", class_="ec-item-box")

    print(f"  CVJM: found {len(boxes)} event boxes", flush=True)

    for box in boxes:
        try:
            # Extract date from box text (e.g., "17.05.2026,10:00 UhrGottesdienst...")
            box_text = box.get_text(strip=True)
            date_start = parse_german_date(box_text)
            if not date_start:
                continue

            # Extract time
            time_m = re.search(r"(\d{1,2}:\d{2})", box_text)
            time_raw = time_m.group(1) if time_m else ""

            # Title from h3.title
            title_el = box.find("h3", class_="title")
            title = title_el.get_text(strip=True) if title_el else ""
            if not title:
                continue

            # Location from p.address
            addr_el = box.find("p", class_="address")
            location = addr_el.get_text(strip=True) if addr_el and addr_el.get_text(strip=True) else "Graben-Neudorf"

            key = (date_start, title)
            if key in seen:
                continue
            seen.add(key)

            all_events.append({
                "title": title,
                "date_start": date_start,
                "date_end": date_start,
                "time_raw": time_raw,
                "location": location,
                "organizer": "CVJM Graben-Neudorf",
                "description": "",
                "event_url": CALENDAR_URL,
                "district": "graben-neudorf",
                "tags": ["Kirche"],
            })
            print(f"  CVJM: {date_start} | {title} | {location} | {time_raw}", flush=True)

        except Exception as e:
            print(f"  CVJM error: {e}", flush=True)
            continue

    print(f"  CVJM total: {len(all_events)} events", flush=True)
    return {
        "source_url": CALENDAR_URL,
        "events": all_events,
    }


if __name__ == "__main__":
    result = scrape_cvjm_graben_neudorf()
    print(f"\nFound {len(result['events'])} events from CVJM Graben-Neudorf")
    for e in result["events"]:
        print(f"  {e['date_start']} | {e['title']} | {e['location']} | {e['time_raw']}")
