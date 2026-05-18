#!/usr/bin/env python3
"""
scraper_karlsdorf_neuthard.py — Scraper for Karlsdorf-Neuthard event calendar.

Structurally similar to CVJM site (both using ec-event-calendar).
Events in div.ec-item-box with h2.ec-title + organizer/location in paragraphs.
Paginated: /eventcalendar?calendar=1&page=N
"""

import re
from urllib.parse import urljoin
import requests
from bs4 import BeautifulSoup

BASE_URL = "https://www.karlsdorf-neuthard.de"
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
    m = re.search(r"(\d{1,2})\.(\d{1,2})\.(\d{4})", text)
    if m:
        return f"{m.group(3)}-{int(m.group(2)):02d}-{int(m.group(1)):02d}"
    return None


def parse_german_date_range(text):
    """Parse start and end date from text like '12.09.2026 bis 14.09.2026' or '18.05.2026'"""
    dates = re.findall(r"(\d{1,2}\.\d{1,2}\.\d{4})", text)
    if not dates:
        return None, None
    start = f"{dates[0][6:10]}-{dates[0][3:5]}-{dates[0][0:2]}"
    end = f"{dates[-1][6:10]}-{dates[-1][3:5]}-{dates[-1][0:2]}" if len(dates) > 1 else start
    return start, end


def parse_time(text):
    m = re.search(r"(\d{1,2}:\d{2})", text)
    return m.group(1) if m else ""


def scrape_karlsdorf_neuthard():
    session = requests.Session()
    session.headers.update({"User-Agent": "Mozilla/5.0 (compatible; StutenseeBot/1.0)"})

    all_events = []
    seen = set()
    page = 1

    while True:
        url = CALENDAR_URL if page == 1 else f"{CALENDAR_URL}?calendar=1&page={page}"
        html = fetch_url(url, session)
        if not html:
            break

        soup = BeautifulSoup(html, "html.parser")
        boxes = soup.find_all("div", class_="ec-item-box")

        if not boxes:
            break

        print(f"  Karlsdorf-Neuthard page {page}: {len(boxes)} events", flush=True)

        for box in boxes:
            try:
                header = box.find("div", class_="ec-header")
                if not header:
                    continue
                content = header.find("div", class_="content")
                if not content:
                    continue

                # Title from h2.ec-title
                title_el = content.find("h2", class_="ec-title")
                title = title_el.get_text(strip=True) if title_el else ""
                if not title:
                    continue

                # Date from p.ec-date
                date_el = content.find("p", class_="ec-date")
                date_text = date_el.get_text(strip=True) if date_el else ""
                date_start, date_end = parse_german_date_range(date_text)
                if not date_start:
                    continue

                # Time
                time_raw = parse_time(date_text)

                # Organizer and location from <p> tags
                paragraphs = content.find_all("p")
                organizer = ""
                location = "Karlsdorf-Neuthard"
                for p in paragraphs:
                    text = p.get_text(strip=True)
                    if text.startswith("Veranstalter:"):
                        organizer = text.replace("Veranstalter:", "", 1).strip()
                    elif text.startswith("Veranstaltungsort:") or text.startswith("Veranstaltungsort"):
                        loc_text = text.replace("Veranstaltungsort:", "", 1).replace("Veranstaltungsort", "", 1).strip()
                        if loc_text:
                            location = loc_text

                key = (date_start, title)
                if key in seen:
                    continue
                seen.add(key)

                all_events.append({
                    "title": title,
                    "date_start": date_start,
                    "date_end": date_end,
                    "time_raw": time_raw,
                    "location": location,
                    "organizer": organizer,
                    "description": "",
                    "event_url": url,
                    "district": "karlsdorf-neuthard",
                    "tags": [],
                })
                print(f"  KN: {date_start} | {title} | {location}", flush=True)

            except Exception as e:
                print(f"  Error: {e}", flush=True)
                continue

        # Check for next page (iterate while we find event boxes on the page)
        if len(boxes) > 0:
            page += 1
        else:
            break

    print(f"  Karlsdorf-Neuthard total: {len(all_events)} events", flush=True)
    return {
        "source_url": CALENDAR_URL,
        "events": all_events,
    }


if __name__ == "__main__":
    result = scrape_karlsdorf_neuthard()
    print(f"\nFound {len(result['events'])} events from Karlsdorf-Neuthard")
    for e in result["events"]:
        print(f"  {e['date_start']}→{e['date_end'] or ''} | {e['title'][:50]} | {e['location'][:30]}")
