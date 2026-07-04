#!/usr/bin/env python3
"""
scraper_graben_neudorf.py — Scraper for Graben-Neudorf event calendar.

TYPO3 with hwveranstaltung extension at
/freizeit-kultur/veranstaltungen/veranstaltungskalender.
Data: title, category, date, time, organizer, location in listing HTML.
All data available on listing pages — no need to visit individual events.
"""

import re
from urllib.parse import urljoin

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


def enrich_event_detail(event, session):
    """Fetch event detail page for full description."""
    url = event.get("event_url", "")
    if not url or url == CALENDAR_URL:
        return event

    try:
        resp = session.get(url, timeout=30, headers={
            "User-Agent": "Mozilla/5.0 (compatible; StutenseeBot/1.0)",
            "Cookie": "ccm_consent=1",
        })
        resp.raise_for_status()
    except requests.exceptions.RequestException as e:
        print(f"  Error fetching detail {url}: {e}", flush=True)
        return event

    soup = BeautifulSoup(resp.text, "html.parser")

    # Try common TYPO3 content containers for description text
    desc_parts = []
    for selector in [".hwcontent", ".hw_text", ".ce-bodytext", ".hwveranstaltung__text",
                      ".article-content", ".content-block", "article", ".tx-hwveranstaltung-pi1"]:
        for block in soup.select(selector):
            text = block.get_text(separator="\n", strip=True)
            if text and len(text) > 20:
                desc_parts.append(text)

    if desc_parts:
        event["description"] = "\n\n".join(desc_parts)
    else:
        # Fallback: grab all text from main/content area, excluding nav/header/footer
        main = soup.find("main") or soup.find(id="content") or soup.find(class_="content")
        if main:
            # Remove known non-content elements
            for tag in main.select("nav, header, footer, .breadcrumb, .hw_record__title"):
                tag.decompose()
            text = main.get_text(separator="\n", strip=True)
            if text and len(text) > 20:
                event["description"] = text

    return event


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

                description = ""

                detail_link = record.select_one('a[href*="veranstaltungskalender/"]')
                event_url = urljoin(BASE_URL, detail_link["href"]) if detail_link and detail_link.get("href") else CALENDAR_URL

                all_events.append({
                    "title": title,
                    "date_start": date_start,
                    "date_end": date_end,
                    "time_raw": time_raw,
                    "location": location,
                    "organizer": organizer,
                    "description": description,
                    "event_url": event_url,
                    "district": "graben-neudorf",
                })
            except Exception as e:
                print(f"  Error parsing event: {e}", flush=True)
                continue

        page += 1

        pagination = soup.select_one("div.pagination.hw_pagination")
        if pagination:
            next_link = pagination.select_one('a[title="Seite weiter"]')
            if not next_link:
                break

    # Enrich events with descriptions from detail pages
    empty_count = sum(1 for e in all_events if not e.get("description"))
    print(f"  Enriching {empty_count} events with detail pages...", flush=True)
    enriched = 0
    for i, event in enumerate(all_events):
        if not event.get("description"):
            all_events[i] = enrich_event_detail(event, session)
            if all_events[i].get("description"):
                enriched += 1
    print(f"    Enriched {enriched}/{empty_count} events with descriptions", flush=True)

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
