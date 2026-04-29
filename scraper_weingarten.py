#!/usr/bin/env python3
"""
scraper_weingarten.py — Scraper for Weingarten (Baden) event sources.

Sources:
1. weingarten-baden.de — TYPO3 CMS with hwveranstaltung extension (official calendar)
2. musikverein-weingarten.de — WordPress with Google Calendar Events (Simple Calendar)
3. mineralix-arena.de — Landing page with upcoming wrestling matches
"""

import re
import sys
from datetime import datetime, timezone, timedelta
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup

BASE_URL = "https://www.weingarten-baden.de"
MV_URL = "https://www.musikverein-weingarten.de"
MINERALIX_URL = "https://www.mineralix-arena.de"
CVJM_URL = "https://www.cvjm-weingarten.de"


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
    """Parse DD.MM.YYYY to YYYY-MM-DD."""
    text = text.strip()
    m = re.search(r"(\d{1,2})\.(\d{1,2})\.(\d{4})", text)
    if m:
        return f"{m.group(3)}-{m.group(2).zfill(2)}-{m.group(1).zfill(2)}"
    return None


def parse_timestamp(ts):
    """Convert unix timestamp to YYYY-MM-DD and HH:MM (Europe/Berlin)."""
    dt = datetime.fromtimestamp(int(ts), tz=timezone.utc)
    berlin_offset = timedelta(hours=2) if dt.month >= 3 and dt.month <= 10 else timedelta(hours=1)
    dt_local = dt + berlin_offset
    return dt_local.strftime("%Y-%m-%d"), dt_local.strftime("%H:%M")


def scrape_official_events(session):
    """Scrape events from weingarten-baden.de official calendar."""
    source_url = f"{BASE_URL}/freizeit-tourismus/veranstaltungen"
    events = []
    seen_urls = set()

    for page in range(1, 12):
        if page == 1:
            url = source_url
        else:
            url = f"{BASE_URL}/freizeit-tourismus/veranstaltungen/seite-{page}/suche-none"

        html = fetch_url(url, session)
        if not html:
            break

        soup = BeautifulSoup(html, "html.parser")
        records = soup.find_all("div", class_="hw_fe__record")
        if not records:
            break

        for record in records:
            try:
                title_el = record.select_one(".hw_record__title span")
                if not title_el:
                    continue
                title = title_el.get_text(strip=True)

                date_el = record.select_one(".hw_record__date .hw_iconlist__text")
                date_start = parse_german_date(date_el.get_text(strip=True)) if date_el else None

                time_el = record.select_one(".hw_record__time .hw_iconlist__text")
                time_raw = time_el.get_text(strip=True) if time_el else ""

                organizer_el = record.select_one(".hw_record__organizer .hw_iconlist__text")
                organizer = organizer_el.get_text(strip=True) if organizer_el else ""

                location_el = record.select_one(".hw_record__simpleLocation .hw_iconlist__text")
                location = location_el.get_text(strip=True) if location_el else ""

                more_link = record.select_one(".hw_record__more__show")
                event_url = ""
                if more_link and more_link.get("href"):
                    event_url = urljoin(BASE_URL, more_link["href"])

                if event_url and event_url in seen_urls:
                    continue
                if event_url:
                    seen_urls.add(event_url)

                events.append({
                    "title": title,
                    "date_start": date_start,
                    "date_end": None,
                    "time_raw": time_raw,
                    "location": location,
                    "organizer": organizer,
                    "description": "",
                    "event_url": event_url,
                })
            except Exception as e:
                print(f"  Error parsing event card: {e}", flush=True)
                continue

        pagination = soup.select_one("nav.hw_fe__pagination")
        if pagination:
            current = pagination.select_one("button[disabled]")
            last = pagination.select_one("a[title='Letzte Seite']")
            if not last and current:
                break

    return events


def scrape_musikverein_events(session):
    """Scrape events from musikverein-weingarten.de Google Calendar."""
    url = f"{MV_URL}/erleben/kalender/"
    events = []

    html = fetch_url(url, session)
    if not html:
        return events

    soup = BeautifulSoup(html, "html.parser")
    event_items = soup.select("li.simcal-event")

    for item in event_items:
        try:
            title_el = item.select_one(".simcal-event-title")
            if not title_el:
                continue
            title = title_el.get_text(strip=True)

            data_start = item.get("data-start")
            if not data_start:
                continue

            date_start, time_start = parse_timestamp(data_start)

            time_end = ""
            time_el = item.select_one(".simcal-event-end-time")
            if time_el:
                time_end = time_el.get_text(strip=True)

            date_end = None
            date_end_el = item.select_one(".simcal-event-end-date")
            if date_end_el:
                date_end = date_end_el.get_text(strip=True)
                parsed = parse_german_date(date_end)
                if parsed:
                    date_end = parsed

            time_raw = time_start
            if time_end:
                time_raw = f"{time_start} - {time_end}"

            location_el = item.select_one(".simcal-event-address")
            location = location_el.get_text(strip=True) if location_el else ""

            events.append({
                "title": title,
                "date_start": date_start,
                "date_end": date_end,
                "time_raw": time_raw,
                "location": location,
                "organizer": "Musikverein Weingarten (Baden) e.V.",
                "description": "",
                "event_url": url,
            })
        except Exception as e:
            print(f"  Error parsing Musikverein event: {e}", flush=True)
            continue

    return events


def scrape_mineralix_arena(session):
    """Scrape events from mineralix-arena.de landing page."""
    url = f"{MINERALIX_URL}/"
    events = []

    html = fetch_url(url, session)
    if not html:
        return events

    soup = BeautifulSoup(html, "html.parser")
    header = soup.find("h2", string=re.compile(r"Aktuelle Veranstaltungen"))
    if not header:
        return events

    for p in header.find_all_next("p", limit=10):
        b = p.find("b")
        if not b:
            continue
        text = b.get_text(strip=True)
        m = re.match(r"(\d{1,2}\.\d{1,2}\.\d{4}),\s*(\d{1,2}:\d{2})\s*Uhr", text)
        if not m:
            continue
        date_start = parse_german_date(m.group(1))
        time_raw = m.group(2)

        title_b = b.next_sibling
        title = ""
        if title_b and isinstance(title_b, str):
            title = title_b.strip()
        elif title_b and hasattr(title_b, "string") and title_b.string:
            title = title_b.string.strip()
        if not title:
            title_br = b.find_next("br")
            if title_br and title_br.next_sibling:
                title = title_br.next_sibling.strip()

        events.append({
            "title": title,
            "date_start": date_start,
            "date_end": None,
            "time_raw": time_raw,
            "location": "Mineralix-Arena, Ringstraße 67, 76356 Weingarten",
            "organizer": "SV Germania 04 Weingarten",
            "description": "",
            "event_url": url,
        })

    return events


def scrape_cvjm_weingarten(session):
    """Scrape events from CVJM Weingarten ECICS calendar."""
    source_url = f"{CVJM_URL}/eventcalendar?calendar=1"
    events = []
    seen_links = set()
    page = 1

    while True:
        url = source_url if page == 1 else f"{source_url}&page={page}"
        print(f"  Fetching CVJM page {page}...", flush=True)
        html = fetch_url(url, session)
        if not html:
            break

        soup = BeautifulSoup(html, "html.parser")
        items = soup.select("div.ec-item-box")
        if not items:
            print(f"  No more events found on page {page}", flush=True)
            break

        for item in items:
            try:
                title_el = item.select_one("h3.title")
                if not title_el:
                    continue
                title = title_el.get_text(strip=True)

                date_start = None
                date_end = None
                d1 = item.select_one("span.d1")
                d2 = item.select_one("span.d2")
                if d1:
                    d1_text = d1.get_text(" ", strip=True)
                    date_start = parse_german_date(d1_text)
                if d2:
                    d2_text = d2.get_text(" ", strip=True)
                    date_end = parse_german_date(d2_text)

                time_raw = ""
                d3 = item.select_one("span.d3")
                if d3:
                    time_raw = d3.get_text(" ", strip=True).strip()

                location = ""
                addr = item.select_one("p.address")
                if addr:
                    location = addr.get_text(strip=True)

                link_el = item.select_one("a[title='weitere Infos']")
                event_url = ""
                if link_el and link_el.get("href"):
                    event_url = urljoin(CVJM_URL, link_el["href"])

                if event_url and event_url in seen_links:
                    continue
                if event_url:
                    seen_links.add(event_url)

                events.append({
                    "title": title,
                    "date_start": date_start,
                    "date_end": date_end,
                    "time_raw": time_raw,
                    "location": location,
                    "organizer": "CVJM Weingarten e.V.",
                    "description": "",
                    "event_url": event_url,
                })
            except Exception as e:
                print(f"  Error parsing CVJM event card: {e}", flush=True)
                continue

        next_link = soup.select_one("a.next")
        if not next_link:
            break
        page += 1

    return events


def scrape_weingarten():
    """Main entry point: scrape all Weingarten event sources."""
    session = requests.Session()
    session.headers.update({
        "User-Agent": "Mozilla/5.0 (compatible; StutenseeBot/1.0)"
    })

    all_events = []

    official = scrape_official_events(session)
    for e in official:
        e["district"] = "Weingarten"
        if not e["organizer"]:
            e["organizer"] = "Gemeinde Weingarten (Baden)"
    all_events.extend(official)

    mv = scrape_musikverein_events(session)
    for e in mv:
        e["district"] = "Weingarten"
    all_events.extend(mv)

    cvjm = scrape_cvjm_weingarten(session)
    for e in cvjm:
        e["district"] = "Weingarten"
    all_events.extend(cvjm)

    mineralix = scrape_mineralix_arena(session)
    for e in mineralix:
        e["district"] = "Weingarten"
    all_events.extend(mineralix)

    return {
        "source_url": f"{BASE_URL}/freizeit-tourismus/veranstaltungen",
        "events": all_events,
    }


if __name__ == "__main__":
    result = scrape_weingarten()
    print(f"Found {len(result['events'])} events from Weingarten (Baden)")
    seen_titles = set()
    unique_count = 0
    for e in result["events"]:
        key = (e["title"], e["date_start"])
        if key not in seen_titles:
            seen_titles.add(key)
            unique_count += 1
        print(f"  - {e['date_start']} | {e['title']} | {e.get('time_raw', '')} | {e.get('location', '')} | {e.get('organizer', '')}")
    print(f"  ({unique_count} unique)")
