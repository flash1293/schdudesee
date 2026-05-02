#!/usr/bin/env python3
"""
scraper_graben_neudorf.py — Scraper for Graben-Neudorf event calendar.

TYPO3 with hwveranstaltung extension at
/freizeit-kultur/veranstaltungen/veranstaltungskalender.
Data: title, category, date, time, organizer, location in listing HTML.
All data available on listing pages — no need to visit individual events.
"""

import re

import requests
from bs4 import BeautifulSoup

BASE_URL = "https://www.graben-neudorf.de"
CALENDAR_URL = f"{BASE_URL}/freizeit-kultur/veranstaltungen/veranstaltungskalender"


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


def parse_date_range(text):
    m = re.search(r"(\d{1,2}\.\d{1,2}\.\d{4})\s*bis\s*(\d{1,2}\.\d{1,2}\.\d{4})", text)
    if m:
        return parse_german_date(m.group(1)), parse_german_date(m.group(2))
    return parse_german_date(text), None


def parse_time(text):
    m = re.search(r"(\d{1,2}:\d{2})", text)
    return m.group(1) if m else ""


def scrape_graben_neudorf():
    session = requests.Session()
    session.headers.update({"User-Agent": "Mozilla/5.0 (compatible; StutenseeBot/1.0)"})

    all_events = []
    page = 1

    while True:
        url = CALENDAR_URL if page == 1 else f"{BASE_URL}/freizeit-kultur/veranstaltungen/veranstaltungskalender/seite-{page}/suche-none"

        html = fetch_url(url, session)
        if not html:
            break

        soup = BeautifulSoup(html, "html.parser")
        records = soup.select(".hwveranstaltung__record")
        if not records:
            break

        print(f"  Graben-Neudorf page {page}: {len(records)} events", flush=True)

        for record in records:
            try:
                title_el = record.select_one(".hw_record__title span")
                if not title_el:
                    continue
                title = title_el.get_text(strip=True)

                cat_el = record.select_one(".hw_record__categories__wrap .hw_tag")
                category = f"[{cat_el.get_text(strip=True)}]" if cat_el else ""

                date_el = record.select_one(".hw_record__date .hw_iconlist__text")
                date_text = date_el.get_text(strip=True) if date_el else ""
                date_start, date_end = parse_date_range(date_text)
                if not date_start:
                    continue

                time_el = record.select_one(".hw_record__time .hw_iconlist__text")
                time_raw = time_el.get_text(strip=True) if time_el else ""

                organizer_el = record.select_one(".hw_record__organizer .hw_iconlist__text")
                organizer = organizer_el.get_text(strip=True) if organizer_el else ""

                location_el = record.select_one(".hw_record__simpleLocation .hw_iconlist__text")
                location = location_el.get_text(strip=True) if location_el else "Graben-Neudorf"

                description = category

                all_events.append({
                    "title": title,
                    "date_start": date_start,
                    "date_end": date_end,
                    "time_raw": time_raw,
                    "location": location,
                    "organizer": organizer,
                    "description": description,
                    "event_url": CALENDAR_URL,
                    "district": "graben-neudorf",
                })
            except Exception as e:
                print(f"  Error parsing event: {e}", flush=True)
                continue

        page += 1

    return {
        "source_url": CALENDAR_URL,
        "events": all_events,
    }


if __name__ == "__main__":
    result = scrape_graben_neudorf()
    print(f"Found {len(result['events'])} events from Graben-Neudorf")
    for e in result["events"]:
        dates = e["date_start"]
        if e["date_end"]:
            dates += f" - {e['date_end']}"
        print(f"  {dates} | {e['title']} | {e['time_raw']}")
