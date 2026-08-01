#!/usr/bin/env python3
"""
scraper_karlsdorf_neuthard.py — Scraper for Karlsdorf-Neuthard event calendar.

Events in div.ec-item-box with h2.ec-title + p tags for org/location.
Each box has meta[itemprop=url] with a link to the individual event.
Paginated: /eventcalendar?calendar=1&page=N (max 20 pages).
"""

import re
import requests
from bs4 import BeautifulSoup

BASE_URL = "https://www.karlsdorf-neuthard.de"
CALENDAR_URL = f"{BASE_URL}/eventcalendar"
MAX_PAGES = 20


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


def parse_time(text):
    m = re.search(r"(\d{1,2}:\d{2})", text)
    if m:
        return m.group(1)
    # Also support HH.MM format (e.g., "14.30")
    m = re.search(r"(\d{1,2})\.(\d{2})(?:\s|$|Uhr)", text)
    if m:
        return f"{m.group(1)}:{m.group(2)}"
    return ""


def scrape_karlsdorf_neuthard():
    session = requests.Session()
    session.headers.update({"User-Agent": "Mozilla/5.0 (compatible; StutenseeBot/1.0)"})

    all_events = []
    seen = set()
    page = 1

    while page <= MAX_PAGES:
        url = CALENDAR_URL if page == 1 else f"{CALENDAR_URL}?calendar=1&page={page}"
        html = fetch_url(url, session)
        if not html:
            break

        soup = BeautifulSoup(html, "html.parser")
        boxes = soup.find_all("div", class_="ec-item-box")

        if not boxes:
            break

        print(f"  KN page {page}: {len(boxes)} events", flush=True)

        for box in boxes:
            try:
                header = box.find("div", class_="ec-header")
                if not header:
                    continue
                content = header.find("div", class_="content")
                if not content:
                    continue

                # Title
                title_el = content.find("h2", class_="ec-title")
                title = title_el.get_text(strip=True) if title_el else ""
                if not title:
                    continue

                # Date
                date_el = content.find("p", class_="ec-date")
                date_text = date_el.get_text(strip=True) if date_el else ""
                dates = re.findall(r"(\d{1,2}\.\d{1,2}\.\d{4})", date_text)
                date_start = parse_german_date(dates[0]) if dates else None
                date_end = parse_german_date(dates[-1]) if len(dates) > 1 else date_start
                if not date_start:
                    continue

                time_raw = parse_time(date_text)

                # Specific event URL
                event_url = CALENDAR_URL
                meta_url = box.find("meta", itemprop="url")
                if meta_url and meta_url.get("content"):
                    event_url = meta_url["content"]

                # Organizer and location
                paragraphs = content.find_all("p")
                organizer = ""
                location = "Karlsdorf-Neuthard"
                for p in paragraphs:
                    text = p.get_text(strip=True)
                    if text.startswith("Veranstalter:"):
                        organizer = text.replace("Veranstalter:", "", 1).strip()
                    elif "Veranstaltungsort" in text:
                        loc_text = text.split("Veranstaltungsort")[-1].lstrip(":").strip()
                        if loc_text:
                            location = loc_text

                # Dedup includes location to prevent merging distinct events same date
                key = (date_start, title, location)
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
                    "event_url": event_url,
                })

            except Exception as e:
                print(f"  Error: {e}", flush=True)
                continue

        page += 1

    print(f"  KN town calendar: {len(all_events)} events", flush=True)

    # Also scrape Bürgerstiftung Karlsdorf-Neuthard (WordPress Events Calendar API)
    bs_events = scrape_buergerstiftung_kn()
    seen_keys = set((e["date_start"], e["title"], e.get("location", "")) for e in all_events)
    for e in bs_events:
        key = (e["date_start"], e["title"], e.get("location", ""))
        if key not in seen_keys:
            seen_keys.add(key)
            all_events.append(e)
    print(f"  KN total (incl. Bürgerstiftung): {len(all_events)} events", flush=True)

    return {
        "source_url": CALENDAR_URL,
        "events": all_events,
    }


def scrape_buergerstiftung_kn():
    """Scrape Bürgerstiftung Karlsdorf-Neuthard events via WP REST API."""
    import json
    API_URL = "https://buergerstiftung-kn.de/wp-json/tribe/events/v1/events"
    events = []
    session = requests.Session()
    session.headers.update({"User-Agent": "Mozilla/5.0 (compatible; StutenseeBot/1.0)"})

    try:
        resp = session.get(API_URL, params={"per_page": 50, "page": 1}, timeout=30)
        resp.raise_for_status()
        data = resp.json()
        total_pages = data.get("total_pages", 1)

        for page in range(1, total_pages + 1):
            if page > 1:
                resp = session.get(API_URL, params={"per_page": 50, "page": page}, timeout=30)
                resp.raise_for_status()
                data = resp.json()

            for ev in data.get("events", []):
                try:
                    title = ev.get("title", "")
                    start_date = ev.get("start_date", "")
                    end_date = ev.get("end_date", "")
                    date_start = start_date[:10] if start_date else None
                    date_end = end_date[:10] if end_date else None
                    time_raw = start_date[11:16] if start_date and len(start_date) >= 16 else ""

                    venue = ev.get("venue") or {}
                    location_parts = []
                    if venue.get("venue"):
                        location_parts.append(venue["venue"])
                    if venue.get("address"):
                        location_parts.append(venue["address"])
                    if venue.get("city"):
                        location_parts.append(venue["city"])
                    location = ", ".join(location_parts) if location_parts else "Karlsdorf-Neuthard"

                    desc_raw = ev.get("description", "") or ""
                    description = re.sub(r"<[^>]+>", "", desc_raw).strip() if desc_raw else ""

                    events.append({
                        "title": title,
                        "date_start": date_start,
                        "date_end": date_end,
                        "time_raw": time_raw,
                        "location": location,
                        "organizer": "Bürgerstiftung Karlsdorf-Neuthard",
                        "description": description,
                        "event_url": ev.get("url", ""),
                    })
                except Exception:
                    continue
    except Exception as e:
        print(f"  Bürgerstiftung KN: API error ({e})", flush=True)

    print(f"  Bürgerstiftung KN: {len(events)} events", flush=True)
    return events


if __name__ == "__main__":
    result = scrape_karlsdorf_neuthard()
    print(f"\nFound {len(result['events'])} events")
    for e in result["events"]:
        print(f"  {e['date_start']} | {e['title'][:50]} | {e['location'][:30]}")
