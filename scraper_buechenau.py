#!/usr/bin/env python3
"""
scraper_buechenau.py — Scraper for Büchenau (Bruchsal) event sources.

Sources:
1. Freie Wähler Büchenau Vereinskalender (PDF, Excel-generated)
2. Musikverein Büchenau Termine (GravCMS, r-events component)
3. Bruchsal.de Büchenau Info
"""

import re
import sys
from datetime import datetime
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup

SOURCE_FW = "https://freie-waehler-buechenau.de/pages/was-wann-wo/kalender.php"
SOURCE_MV = "https://musikverein-buechenau.de/de/termine"
SOURCE_BRUCHSAL = "https://www.bruchsal.de/buechenau"


def fetch_url(url, session=None, timeout=30):
    if session is None:
        session = requests.Session()
    try:
        resp = session.get(url, timeout=timeout, headers={
            "User-Agent": "Mozilla/5.0 (compatible; StutenseeBot/1.0)"
        })
        resp.raise_for_status()
        return resp.content, resp.text
    except Exception:
        return None, None


def parse_german_date(text):
    text = text.strip()
    m = re.search(r"(\d{1,2})\.(\d{1,2})\.(\d{4})", text)
    if m:
        return f"{m.group(3)}-{int(m.group(2)):02d}-{int(m.group(1)):02d}"
    return None


def parse_german_date_range(text):
    m = re.search(r"(\d{1,2})\.(?:\s*&\s*)(\d{1,2})\.(\d{1,2})\.(\d{4})", text)
    if m:
        start = f"{m.group(4)}-{int(m.group(3)):02d}-{int(m.group(1)):02d}"
        end = f"{m.group(4)}-{int(m.group(3)):02d}-{int(m.group(2)):02d}"
        return start, end
    return None, None


def scrape_fw_buechenau(session):
    """Scrape Freie Wähler Büchenau Vereinskalender (PDF)."""
    events = []
    raw, text = fetch_url(SOURCE_FW, session)
    if raw is None:
        print("  FW Büchenau: could not fetch PDF", flush=True)
        return events

    content_type = session.head(SOURCE_FW, timeout=10).headers.get("Content-Type", "")
    if "pdf" not in content_type.lower():
        html = raw.decode("utf-8", errors="replace")
        soup = BeautifulSoup(html, "html.parser")
        for row in soup.select("tr"):
            cells = row.find_all("td")
            if len(cells) >= 2:
                date_text = cells[0].get_text(strip=True)
                title = cells[1].get_text(strip=True)
                date_start = parse_german_date(date_text)
                if title and date_start:
                    events.append({
                        "title": title,
                        "date_start": date_start,
                        "date_end": None,
                        "time_raw": "",
                        "location": "Büchenau",
                        "organizer": "Freie Wähler Büchenau",
                        "description": "",
                        "event_url": SOURCE_FW,
                    })
        return events

    print("  FW Büchenau: PDF format — no PDF parser available, skipping", flush=True)
    return events


def scrape_musikverein(session):
    """Scrape Musikverein Büchenau Termine page."""
    events = []
    raw, html = fetch_url(SOURCE_MV, session)
    if raw is None:
        print("  Musikverein Büchenau: could not fetch page", flush=True)
        return events

    soup = BeautifulSoup(html, "html.parser")
    items = soup.select(".r-events-item")
    if not items:
        items = soup.find_all("div", class_="r-events-item")

    for item in items:
        try:
            title_el = item.select_one(".r-events-title")
            if not title_el:
                continue
            title = title_el.get_text(strip=True)

            date_el = item.select_one(".r-events-date")
            if not date_el:
                continue
            date_text = date_el.get_text(" ", strip=True)

            time_el = date_el.select_one(".r-events-time")
            time_raw = time_el.get_text(strip=True) if time_el else ""

            venue_el = item.select_one(".r-events-venue")
            location = venue_el.get_text(strip=True) if venue_el else "Büchenau"

            date_start, date_end = parse_german_date_range(date_text)
            if not date_start:
                date_start = parse_german_date(date_text)

            if not date_start:
                continue

            events.append({
                "title": title,
                "date_start": date_start,
                "date_end": date_end,
                "time_raw": time_raw,
                "location": location,
                "organizer": "Musikverein 1898 Büchenau e.V.",
                "description": "",
                "event_url": SOURCE_MV,
            })
        except Exception as e:
            continue

    return events


def scrape_bruchsal_buechenau(session):
    """Scrape Bruchsal.de Büchenau page."""
    events = []
    raw, html = fetch_url(SOURCE_BRUCHSAL, session)
    if raw is None:
        print("  Bruchsal Büchenau: site not accessible", flush=True)
        return events

    soup = BeautifulSoup(html, "html.parser")
    for heading in soup.find_all(["h2", "h3"]):
        text = heading.get_text(strip=True).lower()
        if "veranstaltung" in text or "termin" in text or "event" in text:
            parent = heading.find_parent(["div", "section"])
            if parent:
                content = parent.get_text("\n", strip=True)
                lines = [l.strip() for l in content.split("\n") if l.strip()]
                current_title = None
                for line in lines:
                    date_start = parse_german_date(line)
                    if date_start:
                        events.append({
                            "title": current_title or "Veranstaltung",
                            "date_start": date_start,
                            "date_end": None,
                            "time_raw": "",
                            "location": "Büchenau",
                            "organizer": "Stadt Bruchsal",
                            "description": "",
                            "event_url": SOURCE_BRUCHSAL,
                        })
                        current_title = None
                    elif line and not any(kw in line.lower() for kw in ["veranstaltung", "termin", "kontakt", "impressum"]):
                        current_title = line

    return events


def scrape_buechenau():
    session = requests.Session()
    session.headers.update({"User-Agent": "Mozilla/5.0 (compatible; StutenseeBot/1.0)"})

    all_events = []

    # Source 1: Freie Wähler Büchenau
    fw_events = scrape_fw_buechenau(session)
    print(f"  FW Büchenau: {len(fw_events)} events", flush=True)
    all_events.extend(fw_events)

    # Source 2: Musikverein Büchenau
    mv_events = scrape_musikverein(session)
    print(f"  Musikverein Büchenau: {len(mv_events)} events", flush=True)
    all_events.extend(mv_events)

    # Source 3: Bruchsal Büchenau
    br_events = scrape_bruchsal_buechenau(session)
    print(f"  Bruchsal Büchenau: {len(br_events)} events", flush=True)
    all_events.extend(br_events)

    return {
        "source_url": SOURCE_FW,
        "events": all_events,
    }


if __name__ == "__main__":
    result = scrape_buechenau()
    print(f"\nTotal: {len(result['events'])} events from Büchenau")
    for e in result["events"]:
        dates = e["date_start"]
        if e.get("date_end"):
            dates += f" - {e['date_end']}"
        print(f"  {dates} | {e['title']} | {e['time_raw']} | {e['location']}")
