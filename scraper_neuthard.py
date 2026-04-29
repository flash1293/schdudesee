"""
scraper_neuthard.py — Scraper for Karlsdorf-Neuthard (Neuthard district) events.

Sources:
1. Official ECICS event calendar at karlsdorf-neuthard.de/eventcalendar
   Paginated HTML with structured event data.

Additional sources noted but not yet scraped:
- TV Neuthard (tv-neuthard.de): WordPress with AI1EC calendar (JS-rendered)
- PDF calendar (karlsdorf-neuthard.de/resources/ecics_647.pdf): 2026 full-year calendar
"""

import re
import sys
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup

BASE_URL = "https://www.karlsdorf-neuthard.de"


def parse_event_date(date_text: str) -> tuple[str | None, str | None]:
    m = re.search(r"(\d{2})\.(\d{2})\.(\d{4})", date_text)
    if m:
        date_start = f"{m.group(3)}-{m.group(2)}-{m.group(1)}"
    else:
        date_start = None
    time_m = re.search(r"\((\d{1,2}:\d{2})\s*(?:&ndash;|–|-)\s*(\d{1,2}:\d{2})\s*Uhr\)", date_text)
    if time_m:
        time_raw = f"{time_m.group(1)} - {time_m.group(2)}"
    else:
        time_m = re.search(r"\((\d{1,2}:\d{2})\s*Uhr\)", date_text)
        time_raw = time_m.group(1) if time_m else None
    return date_start, time_raw


def fetch_page(page: int, session: requests.Session) -> str | None:
    url = f"{BASE_URL}/eventcalendar?calendar=1"
    if page > 1:
        url += f"&page={page}"
    try:
        resp = session.get(url, timeout=30)
        resp.raise_for_status()
        return resp.text
    except Exception as e:
        return None


def parse_events(html: str) -> list[dict]:
    soup = BeautifulSoup(html, "html.parser")
    events = []
    for item in soup.select("div.ec-item-box"):
        try:
            title_el = item.select_one("h2.ec-title")
            if not title_el:
                continue
            title = title_el.get_text(strip=True)

            date_el = item.select_one("p.ec-date")
            date_text = date_el.get_text(strip=True) if date_el else ""
            date_start, time_raw = parse_event_date(date_text)

            organizer = None
            location = None
            for p in item.select("p"):
                text = p.get_text(strip=True)
                if text.startswith("Veranstalter:"):
                    organizer = text.replace("Veranstalter:", "", 1).strip()
                elif text.startswith("Veranstaltungsort:"):
                    loc_name = p.select_one("[itemprop='name']")
                    if loc_name and loc_name.get_text(strip=True):
                        location = loc_name.get_text(strip=True)

            link_el = item.select_one("a[href*='action=view_event&event_id=']")
            event_url = None
            if link_el:
                href = link_el.get("href", "")
                event_url = urljoin(BASE_URL, href)

            events.append({
                "title": title,
                "date_start": date_start,
                "date_end": None,
                "time_raw": time_raw,
                "location": location,
                "organizer": organizer,
                "description": None,
                "event_url": event_url,
            })
        except Exception:
            continue
    return events


BUERGERTSTIFTUNG_API = "https://buergerstiftung-kn.de/wp-json/tribe/events/v1/events"


def scrape_buergerstiftung_kn() -> dict:
    session = requests.Session()
    session.headers.update({
        "User-Agent": "Mozilla/5.0 (compatible; StutenseeBot/1.0)"
    })

    all_events = []
    api_used = False

    try:
        resp = session.get(
            BUERGERTSTIFTUNG_API,
            params={"per_page": 50, "page": 1},
            timeout=30,
        )
        resp.raise_for_status()
        data = resp.json()
        total_pages = data.get("total_pages", 1)

        for page in range(1, total_pages + 1):
            if page > 1:
                resp = session.get(
                    BUERGERTSTIFTUNG_API,
                    params={"per_page": 50, "page": page},
                    timeout=30,
                )
                resp.raise_for_status()
                data = resp.json()

            for event in data.get("events", []):
                try:
                    title = event.get("title", "")
                    start_date = event.get("start_date", "")
                    end_date = event.get("end_date", "")

                    date_start = start_date[:10] if start_date else None
                    date_end = end_date[:10] if end_date else None

                    time_raw = None
                    if start_date and len(start_date) >= 16:
                        start_time = start_date[11:16]
                        if end_date and len(end_date) >= 16:
                            end_time = end_date[11:16]
                            time_raw = f"{start_time} - {end_time}"
                        else:
                            time_raw = start_time

                    venue = event.get("venue") or {}
                    location_parts = []
                    if venue.get("venue"):
                        location_parts.append(venue["venue"])
                    if venue.get("address"):
                        location_parts.append(venue["address"])
                    if venue.get("city"):
                        location_parts.append(venue["city"])
                    location = ", ".join(location_parts) if location_parts else None

                    description_raw = event.get("description", "") or ""
                    if description_raw:
                        desc_soup = BeautifulSoup(description_raw, "html.parser")
                        description = desc_soup.get_text(separator=" ", strip=True)
                    else:
                        description = None

                    all_events.append({
                        "title": title,
                        "date_start": date_start,
                        "date_end": date_end,
                        "time_raw": time_raw,
                        "location": location,
                        "organizer": "Bürgerstiftung Karlsdorf-Neuthard",
                        "description": description,
                        "event_url": event.get("url"),
                    })
                except Exception:
                    continue

        api_used = True

    except Exception:
        pass

    if not api_used:
        try:
            resp = session.get("https://buergerstiftung-kn.de/events/", timeout=30)
            resp.raise_for_status()
            soup = BeautifulSoup(resp.text, "html.parser")

            for event_div in soup.select(".tribe-events-calendar-list__event"):
                try:
                    title_el = event_div.select_one(
                        "h3.tribe-events-calendar-list__event-title a"
                    )
                    if not title_el:
                        continue
                    title = title_el.get_text(strip=True)
                    event_url = title_el.get("href")

                    day_el = event_div.select_one(
                        ".tribe-events-calendar-list__event-date-tag-daynum"
                    )
                    month_el = event_div.select_one(
                        ".tribe-events-calendar-list__event-date-tag-month"
                    )
                    date_str = None
                    if day_el and month_el:
                        day = day_el.get_text(strip=True)
                        month = month_el.get_text(strip=True)
                        date_str = f"{month} {day}"

                    time_el = event_div.select_one(
                        "time.tribe-events-calendar-list__event-datetime"
                    )
                    time_raw = None
                    if time_el:
                        dt = time_el.get("datetime", "")
                        if dt:
                            time_raw = dt
                        else:
                            time_raw = time_el.get_text(strip=True)

                    venue_el = event_div.select_one(
                        "address.tribe-events-calendar-list__event-venue"
                    )
                    location = venue_el.get_text(strip=True) if venue_el else None

                    desc_el = event_div.select_one(
                        ".tribe-events-calendar-list__event-description"
                    )
                    description = desc_el.get_text(strip=True) if desc_el else None

                    all_events.append({
                        "title": title,
                        "date_start": date_str,
                        "date_end": None,
                        "time_raw": time_raw,
                        "location": location,
                        "organizer": "Bürgerstiftung Karlsdorf-Neuthard",
                        "description": description,
                        "event_url": event_url,
                    })
                except Exception:
                    continue

        except Exception:
            pass

    return {
        "source_url": "https://buergerstiftung-kn.de/events/",
        "events": all_events,
    }


def scrape_neuthard() -> dict:
    session = requests.Session()
    session.headers.update({
        "User-Agent": "Mozilla/5.0 (compatible; StutenseeBot/1.0)"
    })

    all_events = []
    for page in range(1, 101):
        html = fetch_page(page, session)
        if not html:
            break
        events = parse_events(html)
        if not events:
            break
        all_events.extend(events)

    buergerstiftung = scrape_buergerstiftung_kn()
    all_events.extend(buergerstiftung["events"])

    return {
        "source_url": BASE_URL + "/",
        "events": all_events,
    }


if __name__ == "__main__":
    result = scrape_neuthard()
    print(f"Found {len(result['events'])} events from Karlsdorf-Neuthard")
    for e in result["events"][:10]:
        print(f"  - {e['title']} | {e['date_start']} | {e['time_raw']} | {e['location']} | {e['organizer']}")
    if len(result["events"]) > 10:
        print(f"  ... and {len(result['events']) - 10} more")
