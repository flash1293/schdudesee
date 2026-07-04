#!/usr/bin/env python3
"""
scraper_bretten.py — Scraper for Bretten (Baden) event calendar.
https://www.bretten.de/tourismus-kultur-freizeit/veranstaltungen

CMS: Drupal with Views module.
Events are listed in monthly pages with structured date fields.
"""

import re
import sys
from datetime import datetime, timedelta

import requests
from bs4 import BeautifulSoup

BASE_URL = "https://www.bretten.de"
CALENDAR_PATH = "/tourismus-kultur-freizeit/veranstaltungen"
LOCATION_DEFAULT = "Bretten"

# Category labels based on the filter options on the calendar page
CATEGORIES = {
    1: "Ausstellung",
    3: "Fest",
    4: "Kirche",
    5: "Literatur",
    6: "Musik",
    7: "Vortrag",
    8: "Sport",
    9: "Theater",
    10: "Verein",
    11: "Sonstiges",
    957: "Sonstiges",
    1010: "Kirche",
    1011: "Sonstiges",
    1012: "Markt",
    1013: "Stadtgeschichte",
    1014: "Kinder",
    1015: "Natur",
    1080: "Sonstiges",
}


def fetch_url(url, timeout=30):
    """Fetch a URL and return the text content."""
    try:
        resp = requests.get(url, timeout=timeout, headers={
            "User-Agent": "Mozilla/5.0 (compatible; StutenseeBot/1.0)"
        })
        resp.raise_for_status()
        return resp.text
    except Exception as e:
        print(f"  Error fetching {url}: {e}", flush=True)
        return None


def parse_iso_datetime(content_str):
    """Parse ISO datetime string like '2026-06-01T15:00:00+02:00'."""
    if not content_str:
        return None, None
    # Extract date part
    date_match = re.match(r"(\d{4}-\d{2}-\d{2})", content_str)
    date_start = date_match.group(1) if date_match else None
    
    # Extract time part
    time_match = re.search(r"T(\d{2}:\d{2})", content_str)
    time_str = time_match.group(1) if time_match else ""
    
    return date_start, time_str


def scrape_month(year, month):
    """Scrape events for a specific month."""
    month_str = f"{year}-{month:02d}"
    url = f"{BASE_URL}{CALENDAR_PATH}/monat/{month_str}"
    events = []
    
    html = fetch_url(url)
    if not html:
        return events
    
    soup = BeautifulSoup(html, "html.parser")
    rows = soup.select(".views-row")
    
    for row in rows:
        try:
            # Title and link
            title_el = row.select_one(".views-field-title .field-content a")
            if not title_el:
                continue
            title = title_el.get_text(strip=True)
            event_path = title_el.get("href", "")
            event_url = f"{BASE_URL}{event_path}" if event_path else url
            
            # Category from URL? Not available in list view directly.
            # Will determine from title/context later.
            
            # Date/time
            date_el = row.select_one(".views-field-field-eventdate .field-content")
            if not date_el:
                continue
            
            # Check for single date vs date range
            single = date_el.select_one(".date-display-single")
            start_el = date_el.select_one(".date-display-start")
            end_el = date_el.select_one(".date-display-end")
            
            date_start = None
            date_end = None
            time_raw = ""
            
            if single:
                content = single.get("content", "")
                date_start, time_str = parse_iso_datetime(content)
                time_raw = time_str
            elif start_el:
                content = start_el.get("content", "")
                date_start, time_str = parse_iso_datetime(content)
                time_raw = time_str
                if end_el:
                    end_content = end_el.get("content", "")
                    date_end, _ = parse_iso_datetime(end_content)
            
            if not date_start:
                continue
            
            events.append({
                "title": title,
                "date_start": date_start,
                "date_end": date_end,
                "time_raw": time_raw,
                "location": LOCATION_DEFAULT,
                "organizer": "",
                "description": "",
                "event_url": event_url,
                "_event_id": event_path.split("/")[-1] if event_path else "",
                "district": "Bretten",
            })
        except Exception as e:
            print(f"  Error parsing event row: {e}", flush=True)
            continue
    
    return events


def enrich_event_detail(event):
    """Fetch event detail page for location and organizer info."""
    event_id = event.get("_event_id", "")
    if not event_id:
        return event
    
    url = f"{BASE_URL}/tourismus-kultur-freizeit/veranstaltungen/{event_id}"
    html = fetch_url(url)
    if not html:
        return event
    
    soup = BeautifulSoup(html, "html.parser")
    
    # Find field labels
    labels = soup.find_all(class_="field-label")
    for label in labels:
        label_text = label.get_text(strip=True).lower()
        value_el = label.find_next_sibling()
        if not value_el:
            continue
        value = value_el.get_text(" ", strip=True)
        
        if "veranstaltungsort" in label_text or "ort" in label_text:
            event["location"] = value
        elif "veranstalter" in label_text:
            event["organizer"] = value
    
    # Description from main content (after the header)
    # Try to find the main content area
    main = soup.find("main") or soup.find("article")
    if main:
        # Get all text and extract description (text after the header fields)
        texts = main.get_text(separator="\n", strip=True)
        # Remove known field labels from description
        for field_label in ["Veranstaltungszeitraum", "Veranstaltungsort", "Veranstalter", "weitere Infos"]:
            texts = texts.replace(field_label, "")
        event["description"] = texts.strip()
    
    return event


def scrape_bretten():
    """Main entry point: scrape Bretten event calendar."""
    all_events = []
    today = datetime.now()
    current_year = today.year
    current_month = today.month
    
    # Scrape current month + next 5 months
    for month_offset in range(6):
        year = current_year + (current_month + month_offset - 1) // 12
        month = (current_month + month_offset - 1) % 12 + 1
        
        print(f"  Scraping Bretten {year}-{month:02d}...", flush=True)
        events = scrape_month(year, month)
        print(f"    Found {len(events)} events", flush=True)
        all_events.extend(events)
    
    print(f"  Enriching {len(all_events)} events with detail pages...", flush=True)
    enriched = 0
    for i, event in enumerate(all_events):
        if event.get("_event_id"):
            enriched_event = enrich_event_detail(event)
            all_events[i] = enriched_event
            enriched += 1
    print(f"    Enriched {enriched} events", flush=True)
    
    # Deduplicate by event URL (events spanning multiple months appear in each monthly view)
    seen_urls = set()
    deduped = []
    for e in all_events:
        url = e.get("event_url", "")
        if url and url not in seen_urls:
            seen_urls.add(url)
            deduped.append(e)
        elif not url:
            deduped.append(e)
    all_events = deduped
    print(f"  After dedup: {len(all_events)} unique events", flush=True)

    return {
        "source_url": f"{BASE_URL}{CALENDAR_PATH}",
        "events": all_events,
    }


if __name__ == "__main__":
    result = scrape_bretten()
    print(f"\nTotal: {len(result['events'])} events from Bretten")
    for e in sorted(result["events"], key=lambda x: x.get("date_start", ""))[:20]:
        loc = e.get("location", "") or LOCATION_DEFAULT
        print(f"  {e['date_start']} | {e['title'][:50]:50s} | {e.get('time_raw', ''):10s} | {loc[:30]}")
    if len(result["events"]) > 20:
        print(f"  ... and {len(result['events']) - 20} more")
