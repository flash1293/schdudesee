#!/usr/bin/env python3
"""
scraper_linkenheim.py — Scraper for Linkenheim-Hochstetten event calendar.

WordPress listing at /leben-und-freizeit/veranstaltungskalender/.
Data: date/time, title, description, category all in listing HTML.
"""

import re
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup

BASE_URL = "https://linkenheim-hochstetten.de"
CALENDAR_URL = f"{BASE_URL}/leben-und-freizeit/veranstaltungskalender/"


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
    m = re.search(r"(\d{1,2})\.(\d{1,2})\.(\d{2,4})", text)
    if m:
        day = int(m.group(1))
        month = int(m.group(2))
        year = m.group(3)
        if len(year) == 2:
            year = f"20{year}"
        return f"{year}-{month:02d}-{day:02d}"
    return None


def parse_time(text):
    m = re.search(r"(\d{1,2}:\d{2})", text)
    return m.group(1) if m else ""


def scrape_linkenheim():
    session = requests.Session()
    session.headers.update({"User-Agent": "Mozilla/5.0 (compatible; StutenseeBot/1.0)"})

    all_events = []
    page = 1

    while True:
        url = CALENDAR_URL if page == 1 else f"{CALENDAR_URL}page/{page}/"
        html = fetch_url(url, session)
        if not html:
            break

        soup = BeautifulSoup(html, "html.parser")
        articles = soup.find_all("article", class_=lambda c: c and "post-entry" in c)

        if not articles:
            break

        print(f"  Linkenheim page {page}: {len(articles)} events", flush=True)

        for article in articles:
            try:
                title_el = article.select_one("h2.post-title a")
                if not title_el:
                    continue
                title = title_el.get_text(strip=True)

                dt_el = article.select_one(".date-time")
                dt_text = dt_el.get_text(strip=True) if dt_el else ""
                date_start = parse_german_date(dt_text)
                if not date_start:
                    continue

                time_raw = parse_time(dt_text)

                desc_el = article.select_one(".entry-content")
                description = desc_el.get_text(strip=True) if desc_el else ""

                event_url = title_el.get("href", "")
                if event_url and not event_url.startswith("http"):
                    event_url = urljoin(BASE_URL, event_url)

                all_events.append({
                    "title": title,
                    "date_start": date_start,
                    "date_end": None,
                    "time_raw": time_raw,
                    "location": "Linkenheim-Hochstetten",
                    "organizer": "",
                    "description": description,
                    "event_url": event_url,
                    "district": "linkenheim",
                })
            except Exception as e:
                print(f"  Error parsing event: {e}", flush=True)
                continue

        next_el = soup.select_one("a.next.page-numbers")
        if not next_el:
            break
        page += 1

    return {
        "source_url": CALENDAR_URL,
        "events": all_events,
    }


if __name__ == "__main__":
    result = scrape_linkenheim()
    print(f"Found {len(result['events'])} events from Linkenheim-Hochstetten")
    for e in result["events"]:
        print(f"  {e['date_start']} | {e['title']} | {e['time_raw']}")
