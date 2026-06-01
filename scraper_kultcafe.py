#!/usr/bin/env python3
"""
scraper_kultcafe.py — Scraper for Familienzentrum Friedrichstal "Kult Café"
https://www.familienzentrum-friedrichstal-kult-cafe-stutensee.de/

Sources:
1. Konzerte page — upcoming concert dates
2. Veranstaltungen page — special events
3. Regular recurring Treffs (Skattreff, Kaffee-Kuchen-Spiele, Witwenstammtisch)
4. Reparatur-Treff — specific 2026 dates
"""

import re
import sys
from datetime import datetime, timedelta

import requests
from bs4 import BeautifulSoup

BASE_URL = "https://www.familienzentrum-friedrichstal-kult-cafe-stutensee.de"
KONZERTE_URL = f"{BASE_URL}/programm/kultur/konzerte"
VERANSTALTUNGEN_URL = f"{BASE_URL}/programm/kultur/veranstaltungen"
REPARATUR_URL = f"{BASE_URL}/programm/treffs/reparatur-treff"

LOCATION = "Altes Rathaus Friedrichstal, Rheinstraße Ost 14, 76297 Stutensee-Friedrichstal"
ORGANIZER = "Familienzentrum Friedrichstal - Kult Café"


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


def parse_german_date(text):
    """Parse a German date string like '24.Oktober 26' or '27.Februar' to YYYY-MM-DD.
    Handles formats: DD.Month YY, DD.Month, DD.MM.YYYY, DD.MM.YY"""
    text = text.strip()
    
    # Try DD.MM.YYYY or DD.MM.YY first
    m = re.search(r"(\d{1,2})\.(\d{1,2})\.(\d{2,4})", text)
    if m:
        day, month_num, year = m.group(1), m.group(2), m.group(3)
        if len(year) == 2:
            year = "20" + year
        return f"{year}-{month_num.zfill(2)}-{day.zfill(2)}"
    
    # Try German month name format: DD.Month YY or DD.Month YYYY
    months_de = {
        "januar": 1, "februar": 2, "märz": 3, "april": 4, "mai": 5, "juni": 6,
        "juli": 7, "august": 8, "september": 9, "oktober": 10, "november": 11, "dezember": 12
    }
    
    m = re.search(r"(\d{1,2})\.\s*([a-zA-Zäöüß]+)\s*(?:(\d{2,4}))?", text)
    if m:
        day = m.group(1)
        month_name = m.group(2).lower().strip().rstrip(".")
        year = m.group(3) if m.group(3) else str(datetime.now().year)
        if len(year) == 2:
            year = "20" + year
        month_num = months_de.get(month_name)
        if month_num:
            return f"{year}-{month_num:02d}-{day.zfill(2)}"
    
    # Try DD. Month YYYY (with space after dot)
    m = re.search(r"(\d{1,2})\.\s+([a-zA-Zäöüß]+)\s+(\d{4})", text)
    if m:
        day = m.group(1)
        month_name = m.group(2).lower().strip().rstrip(".")
        year = m.group(3)
        month_num = months_de.get(month_name)
        if month_num:
            return f"{year}-{month_num:02d}-{day.zfill(2)}"
    
    return None


def scrape_konzerte():
    """Scrape the Konzerte page for upcoming concert dates."""
    events = []
    html = fetch_url(KONZERTE_URL)
    if not html:
        return events
    
    soup = BeautifulSoup(html, "html.parser")
    text = soup.get_text(separator="\n")
    
    # The page lists concert dates in the "Termine 2026" section
    # Format: "27.Februar / 27.März / 24.April / 24.Oktober / 06.November / 4.Dezember"
    # All concerts are Fridays at 19:30 (except 24.10. which is Saturday)
    
    # Find the "Termine 2026" section
    termine_match = re.search(r"Termine\s+2026\s*[:\-]?\s*([\d\.\s\/a-zA-Zäöüß,]+)", text)
    if termine_match:
        dates_text = termine_match.group(1)
        # Split by / or ,
        date_parts = re.split(r"\s*[\/,]\s*", dates_text.strip())
        for part in date_parts:
            part = part.strip()
            if not part:
                continue
            date_str = parse_german_date(part)
            if not date_str:
                continue
            
            # Check if this is the 24. Oktober (Saturday exception)
            is_saturday = "24.Oktober" in part or "24. Oktober" in part
            
            day_name = "Samstag" if is_saturday else "Freitag"
            
            events.append({
                "title": "Konzert im Kult Café",
                "date_start": date_str,
                "date_end": None,
                "time_raw": "19:30",
                "location": LOCATION,
                "organizer": ORGANIZER,
                "description": f"Konzert im Kult Café Friedrichstal. {day_name} um 19:30 Uhr im Alten Rathaus. Eintritt frei – Spende erbeten.",
                "event_url": KONZERTE_URL,
                "district": "Friedrichstal",
            })
    
    # Also check for the "Aktuell" section with a specific concert mention
    # "Skupa" Freitag, 24.Oktober 26 19:30 Uhr
    aktuell_match = re.search(r'"([^"]+)"\s*(?:Freitag|Samstag|Sonntag|Donnerstag)\s*[,.]?\s*(\d{1,2}\.\s*[a-zA-Zäöüß]+\s*(?:\d{2,4})?)\s*(\d{1,2}:\d{2})\s*Uhr', text)
    if aktuell_match:
        title = aktuell_match.group(1).strip()
        date_text = aktuell_match.group(2).strip()
        time_str = aktuell_match.group(3).strip()
        
        date_str = parse_german_date(date_text)
        if date_str:
            # Check if this date is already in our list
            already_added = any(e["date_start"] == date_str for e in events)
            if not already_added:
                events.append({
                    "title": title,
                    "date_start": date_str,
                    "date_end": None,
                    "time_raw": time_str,
                    "location": LOCATION,
                    "organizer": ORGANIZER,
                    "description": f"Konzert im Kult Café Friedrichstal. Eintritt frei – Spende erbeten.",
                    "event_url": KONZERTE_URL,
                    "district": "Friedrichstal",
                })
    
    return events


def scrape_veranstaltungen():
    """Scrape special events from the Veranstaltungen page."""
    events = []
    html = fetch_url(VERANSTALTUNGEN_URL)
    if not html:
        return events
    
    soup = BeautifulSoup(html, "html.parser")
    text = soup.get_text(separator="\n")
    
    # Look for events with German date patterns
    # The page currently has "Märchen aus Afghanistan" with no fixed date
    
    return events


def generate_recurring_treffs():
    """Generate recurring regular events from the Treffs sections."""
    events = []
    today = datetime.now()
    current_year = today.year
    
    # === Skattreff: Every Thursday, 15-17 Uhr (not during summer holidays) ===
    # Summer holidays in Baden-Württemberg: typically late July to early September
    # We'll generate for the current year
    for month in range(1, 13):
        # Skip August and September (summer holidays approximation)
        if month in (8, 9):
            continue
        # Find all Thursdays in this month
        first_day = datetime(current_year, month, 1)
        # Day of week: Monday=0, Sunday=6, Thursday=3
        days_in_month = (datetime(current_year, month + 1, 1) - timedelta(days=1)).day if month < 12 else 31
        
        for day in range(1, days_in_month + 1):
            dt = datetime(current_year, month, day)
            if dt.weekday() == 3:  # Thursday
                if dt < today:
                    continue
                events.append({
                    "title": "Skattreff",
                    "date_start": dt.strftime("%Y-%m-%d"),
                    "date_end": None,
                    "time_raw": "15:00 – 17:00",
                    "location": LOCATION,
                    "organizer": ORGANIZER,
                    "description": "Skattreff im Kult Café Friedrichstal. Jeden Donnerstag, 15–17 Uhr (nicht in den Sommerferien). Ohne Anmeldung und kostenfrei.",
                    "event_url": f"{BASE_URL}/programm/treffs/skattreff",
                    "district": "Friedrichstal",
                })
    
    # === Kaffee-Kuchen-Spiele: Every Thursday, 15-17 Uhr (not during school holidays) ===
    for month in range(1, 13):
        if month in (8, 9):  # Skip summer holidays
            continue
        first_day = datetime(current_year, month, 1)
        days_in_month = (datetime(current_year, month + 1, 1) - timedelta(days=1)).day if month < 12 else 31
        
        for day in range(1, days_in_month + 1):
            dt = datetime(current_year, month, day)
            if dt.weekday() == 3:  # Thursday
                if dt < today:
                    continue
                events.append({
                    "title": "Kaffee-Kuchen-Spiele",
                    "date_start": dt.strftime("%Y-%m-%d"),
                    "date_end": None,
                    "time_raw": "15:00 – 17:00",
                    "location": LOCATION,
                    "organizer": ORGANIZER,
                    "description": "Offener Treff für alle Generationen im Kult Café Friedrichstal. Donnerstags 15–17 Uhr. Bei Kaffee und Kuchen plaudern, spielen oder an Aktionen teilnehmen. Während der Schulferien geschlossen.",
                    "event_url": f"{BASE_URL}/programm/treffs/kaffee-kuchen-spiele",
                    "district": "Friedrichstal",
                })
    
    # === Witwenstammtisch: Every 1st and 3rd Tuesday, 16-19 Uhr ===
    for month in range(1, 13):
        first_day = datetime(current_year, month, 1)
        days_in_month = (datetime(current_year, month + 1, 1) - timedelta(days=1)).day if month < 12 else 31
        
        tuesday_count = 0
        for day in range(1, days_in_month + 1):
            dt = datetime(current_year, month, day)
            if dt.weekday() == 1:  # Tuesday
                tuesday_count += 1
                if tuesday_count in (1, 3):  # 1st and 3rd Tuesday
                    if dt >= today:
                        events.append({
                            "title": "Witwenstammtisch",
                            "date_start": dt.strftime("%Y-%m-%d"),
                            "date_end": None,
                            "time_raw": "16:00 – 19:00",
                            "location": "Gastätte des FC Germania (Kult Café Friedrichstal)",
                            "organizer": ORGANIZER,
                            "description": "Witwenstammtisch im Kult Café Friedrichstal. Jeden 1. und 3. Dienstag im Monat, 16–19 Uhr.",
                            "event_url": f"{BASE_URL}/programm/treffs/witwenstammtisch",
                            "district": "Friedrichstal",
                        })
    
    return events


def scrape_reparatur_treff():
    """Scrape the Reparatur-Treff page for specific event dates."""
    events = []
    html = fetch_url(REPARATUR_URL)
    if not html:
        return events
    
    soup = BeautifulSoup(html, "html.parser")
    text = soup.get_text(separator="\n")
    
    # Find "Termine für 2026" section
    termine_match = re.search(r"Termine\s+für\s+2026\s*\n?\s*([\d\.\,\s]+?)(?:Änderungen|\n\n)", text, re.DOTALL)
    if termine_match:
        dates_text = termine_match.group(1)
        # Extract individual dates (deduplicated)
        seen_dates = set()
        dates = re.findall(r"(\d{1,2})\.(\d{1,2})\.", dates_text)
        for day, month in dates:
            date_str = f"2026-{month.zfill(2)}-{day.zfill(2)}"
            if date_str not in seen_dates:
                seen_dates.add(date_str)
                events.append({
                    "title": "Reparatur-Treff",
                    "date_start": date_str,
                    "date_end": None,
                    "time_raw": "10:00 – 12:00",
                    "location": LOCATION,
                    "organizer": ORGANIZER,
                    "description": "Reparatur-Treff im Kult Café Friedrichstal. Ehrenamtliche Fachkräfte helfen bei Reparaturen von Elektrik, elektronischen Geräten, Mechanik, Holz, Textilien und IT. Samstags 10–12 Uhr. Letzte Annahme bis 11:30 Uhr.",
                    "event_url": REPARATUR_URL,
                    "district": "Friedrichstal",
                })
    
    return events


def scrape_kultcafe():
    """Main entry point: scrape all Kult Café event sources."""
    all_events = []
    
    print("  Scraping Kult Café Konzerte...", flush=True)
    konzerte = scrape_konzerte()
    for e in konzerte:
        e["_source_url"] = KONZERTE_URL
    all_events.extend(konzerte)
    print(f"    {len(konzerte)} concert events", flush=True)
    
    print("  Scraping Kult Café Veranstaltungen...", flush=True)
    veranstaltungen = scrape_veranstaltungen()
    for e in veranstaltungen:
        e["_source_url"] = VERANSTALTUNGEN_URL
    all_events.extend(veranstaltungen)
    print(f"    {len(veranstaltungen)} special events", flush=True)
    
    print("  Generating recurring Treffs...", flush=True)
    treffs = generate_recurring_treffs()
    for e in treffs:
        e["_source_url"] = BASE_URL
    all_events.extend(treffs)
    print(f"    {len(treffs)} recurring events", flush=True)
    
    print("  Scraping Reparatur-Treff...", flush=True)
    reparatur = scrape_reparatur_treff()
    for e in reparatur:
        e["_source_url"] = REPARATUR_URL
    all_events.extend(reparatur)
    print(f"    {len(reparatur)} repair events", flush=True)
    
    return {
        "source_url": BASE_URL,
        "events": all_events,
    }


if __name__ == "__main__":
    result = scrape_kultcafe()
    print(f"\nTotal: {len(result['events'])} events from Kult Café Friedrichstal")
    for e in sorted(result["events"], key=lambda x: x.get("date_start", "")):
        print(f"  {e['date_start']} | {e['title']} | {e.get('time_raw', '')} | {e.get('location', LOCATION[:40])}...")
