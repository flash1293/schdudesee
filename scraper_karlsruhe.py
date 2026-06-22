#!/usr/bin/env python3
"""
scraper_karlsruhe.py — Scraper for Karlsruhe city events (RSS feed + venue pages).

Parses kalender.karlsruhe.de/db/termine/rss and filters events in the
districts closest to Stutensee:
  - Hagsfeld
  - Neureut
  - Waldstadt
  - Rintheim

Matching strategy:
  1. Check title + RSS description for district/location indicators
  2. For ambiguous matches, fetch detail page and check structured location data + page content
  3. Scrape known venue pages in target districts for events not covered by RSS
  4. Avoid false positives by scoping content checks to relevant sections (not nav/footer)
  5. Canceled/ENTFÄLLT events are filtered out
"""

import re
from defusedxml import ElementTree as ET
from datetime import datetime
import urllib.request
import urllib.error
from urllib.parse import urlparse

RSS_URL = "https://kalender.karlsruhe.de/db/termine/rss"
SOURCE_URL = "https://kalender.karlsruhe.de"

# Known venue pages in target districts — scraped as a secondary source
# for events not covered by the RSS feed.
# Auto-discovered from https://kalender.karlsruhe.de/db/termine/orte
# Format: {venue_id: district_name}
KNOWN_VENUES = {
    # Hagsfeld
    5932:   "Hagsfeld",   # Festplatz Hagsfeld
    551851: "Hagsfeld",   # Gemeindezentrum der Laurentiusgemeinde Hagsfeld
    # Neureut
    533488: "Neureut",    # KunstRaum Neureut e.V.
    239261: "Neureut",    # Neureuter Platz an der Badnerlandhalle (weekly market — skipped)
    139302: "Neureut",    # Stadtbibliothek Karlsruhe - Stadtteilbibliothek Neureut
    # Waldstadt
    7754:   "Waldstadt",  # Waldstadtzentrum (weekly market — skipped)
    139303: "Waldstadt",  # Stadtbibliothek Karlsruhe - Stadtteilbibliothek Waldstadt
}

# District-specific location patterns (broader matching to catch all events)
DISTRICT_PATTERNS = {
    "Hagsfeld": [
        r"\bhagsfeld\b",
    ],
    "Neureut": [
        r"\bneureut\b",
        r"kunstraum\s+neureut",
        r"badnerlandhalle",
        r"neureuter\s*platz",
        r"stadtteilbibliothek\s+neureut",
    ],
    "Waldstadt": [
        r"\bwaldstadt\b",
        r"waldstadtzentrum",
        r"waldstadt-zentrum",
    ],
    "Rintheim": [
        r"\brintheim\b",
        r"fächerbad",
        r"stadtteilbibliothek\s+rintheim",
    ],
    "Durlach": [
        r"\bdurlach\b",
        r"\bpfinzgaumuseum\b",
        r"\bkarlsburg\b",
        r"gemeindezentrum\s+durlach",
        r"st\.?\s+peter\s+und\s+paul\s+kirche\s+durlach",
        r"stadtbibliothek\s+durlach",
        r"trinitatiskirche\s+durlach",
    ],
    "Karlsruhe-Innenstadt": [
        r"\bstaatstheater\b",
        r"\bkonzerthaus\b",
        r"\bbadische[-\s]landesbibliothek\b",
        r"\bzkm\b",
        r"\bkunsthalle\b",
        r"\btollhaus\b",
        r"\bjubez\b",
        r"\bbadischer\s+kunstverein\b",
    ],
}

# Kultur URL categories that trigger the Innenstadt catch-all when no district is matched
INNENSTADT_CATEGORIES = {"theater", "musik", "literatur", "ausstellungen", "kunst", "kultur"}


MAX_CONTENT_BYTES = 10 * 1024 * 1024  # 10 MB safety limit


def fetch_url(url, timeout=30):
    """Fetch a URL and return text content."""
    parsed = urlparse(url)
    if parsed.scheme not in {"http", "https"}:
        print(f"  Skipping unsupported URL scheme: {url}", flush=True)
        return None
    req = urllib.request.Request(
        url,
        headers={"User-Agent": "StutenseeEvents/1.0 (Karlsruhe scraper)"}
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return resp.read(MAX_CONTENT_BYTES).decode("utf-8", errors="replace")
    except Exception as e:
        print(f"  Error fetching {url}: {e}", flush=True)
        return None


def parse_pubdate(pubdate_str):
    """Parse RSS pubDate into date_start and time_raw strings."""
    if not pubdate_str:
        return "", ""
    try:
        cleaned = pubdate_str.strip()
        parts = cleaned.rsplit(" ", 1)  # split off timezone offset
        dt_str = parts[0]
        dt = datetime.strptime(dt_str, "%a, %d %b %Y %H:%M:%S")
        date_start = dt.strftime("%Y-%m-%d")
        time_raw = dt.strftime("%H:%M")
        return date_start, time_raw
    except (ValueError, IndexError):
        return "", ""


def extract_venue_location(html):
    """Extract venue location name from an event detail page (first vcard)."""
    # First look for the venue vcard (has id="box_ort" or is the first vcard in the details section)
    m = re.search(r'<div[^>]*class="detail-block vcard"[^>]*id="box_ort"[^>]*>.*?<h5[^>]*class="strong fn org"[^>]*>(.*?)</h5>', html, re.DOTALL)
    if m:
        loc = re.sub(r'<[^>]+>', '', m.group(1)).strip()
        if loc:
            return loc
    # Fallback: first hcard org name
    m = re.search(r'<h5[^>]*class="strong fn org"[^>]*>(.*?)</h5>', html, re.DOTALL)
    if m:
        loc = re.sub(r'<[^>]+>', '', m.group(1)).strip()
        if loc:
            return loc
    # <span class="location"> fallback
    m = re.search(r'<span class="location">(.*?)</span>', html, re.DOTALL)
    if m:
        loc = m.group(1).strip()
        if loc:
            return loc
    return ""


def extract_organizer(html):
    """Extract organizer name from an event detail page (second vcard)."""
    # Find all fn.org elements and take the last one (organizer comes after venue)
    matches = re.findall(r'<h5[^>]*class="strong fn org"[^>]*>(.*?)</h5>', html, re.DOTALL)
    if len(matches) >= 2:
        org = re.sub(r'<[^>]+>', '', matches[1]).strip()
        if org:
            return org
    # Fallback: look for "Veranstalter" keyword followed by text
    m = re.search(r'Veranstalter\s*(.*?)(?:<br|<p|<div|$)', html, re.DOTALL)
    if m:
        org = re.sub(r'<[^>]+>', '', m.group(1)).strip()
        if org and len(org) < 100:
            return org
    return ""


def extract_short_description(html):
    """Extract the short description from an event detail page."""
    m = re.search(r'<p[^>]*id="shortDescription"[^>]*>(.*?)</p>', html, re.DOTALL)
    if m:
        desc = re.sub(r'<[^>]+>', '', m.group(1)).strip()
        if desc:
            return desc
    return ""


def extract_category_from_url(url):
    """Extract event category from URL path like /stadtleben/ or /musik/."""
    m = re.search(r'/db/termine/([a-z]+)/', url)
    if m:
        cat = m.group(1)
        # Map German URL slugs to readable tags
        cat_map = {
            "musik": "Musik",
            "theater": "Theater",
            "literatur": "Literatur",
            "kunst": "Kunst",
            "kinder": "Kinder",
            "stadtleben": "Stadtleben",
            "natur": "Natur",
            "familie": "Familie",
            "ausstellung": "Ausstellung",
            "vortrag": "Vortrag",
            "workshop": "Workshop",
            "markt": "Markt",
            "fest": "Fest",
            "sport": "Sport",
            "religion": "Religion",
            "glaube": "Glaube",
            "kulinarik": "Kulinarik",
            "brauchtum": "Brauchtum",
        }
        return cat_map.get(cat, cat.capitalize())
    return ""


def matches_district(text, district):
    """Check if text matches location patterns for a given district."""
    for pattern in DISTRICT_PATTERNS[district]:
        if re.search(pattern, text, re.IGNORECASE):
            return True
    return False


def get_district_from_text(text):
    """Returns district name if text indicates event is in that district."""
    for district in DISTRICT_PATTERNS:
        if matches_district(text, district):
            return district
    return None


GERMAN_MONTHS = {
    "januar": 1, "februar": 2, "märz": 3, "maerz": 3, "april": 4,
    "mai": 5, "juni": 6, "juli": 7, "august": 8, "september": 9,
    "oktober": 10, "november": 11, "dezember": 12,
}


def parse_date_from_body(html):
    """Parse date from HTML body (venue page or event page fallback)."""
    # Try DD.MM.YYYY
    m = re.search(r'(\d{1,2})\.(\d{1,2})\.(\d{4})', html)
    if m:
        day, month, year = int(m.group(1)), int(m.group(2)), int(m.group(3))
        try:
            dt = datetime(year, month, day)
            return dt.strftime("%Y-%m-%d")
        except ValueError:
            return ""
    # Try German format: "5. Juni 2026" or "05. Juni 2026"
    m = re.search(r'(\d{1,2})\.\s*([A-Za-zäöüÄÖÜ]+)\s*(\d{4})', html)
    if m:
        day = int(m.group(1))
        month_name = m.group(2).lower()
        year = int(m.group(3))
        if month_name in GERMAN_MONTHS:
            month = GERMAN_MONTHS[month_name]
            try:
                dt = datetime(year, month, day)
                return dt.strftime("%Y-%m-%d")
            except ValueError:
                return ""
    return ""


def scrape_venue_page(venue_id, district):
    """Scrape a venue page for events happening at that venue.
    
    Venue pages (e.g. /db/termine/533488) list events hosted at a specific
    location. This catches events not included in the RSS feed.
    """
    venue_url = f"https://kalender.karlsruhe.de/db/termine/{venue_id}"
    html = fetch_url(venue_url)
    if not html:
        return []
    
    events = []
    # Find event links (each venue page lists events as image links)
    for m in re.finditer(
        r'<a\s+href="(https://kalender\.karlsruhe\.de/db/termine/[a-z]+/[a-z0-9_-]+)"[^>]*class="listimg"',
        html
    ):
        event_url = m.group(1)
        
        # Skip if already fetched (venue pages can list the same event twice)
        if event_url in [e["event_url"] for e in events]:
            continue
        
        # Quick check: skip weekly markets (already covered by Wochenmarkt scraper)
        if "wochenmarkt" in event_url.lower():
            continue
        
        # Fetch the event detail page
        detail_html = fetch_url(event_url)
        if not detail_html:
            continue
        
        # Extract title from page title
        title = ""
        m2 = re.search(r'<title>(.*?)</title>', detail_html, re.DOTALL)
        if m2:
            title = m2.group(1).strip()
            # Remove prefix like "Karlsruhe: Veranstaltungskalender - "
            title = re.sub(r'^.*?-\s*', '', title)
        
        if not title:
            continue
        
        # Skip cancelled events
        if re.search(r'ENTFÄLLT|abgesagt|cancelled', title, re.IGNORECASE):
            continue
        
        # Extract date
        date_start = parse_date_from_body(detail_html)
        if not date_start:
            # Try the h2 heading
            m2 = re.search(r'<h2[^>]*>(.*?)</h2>', detail_html)
            if m2:
                date_start = parse_date_from_body(m2.group(1))
        if not date_start:
            # Skip events without a date — can't usefully curate them
            continue
        
        # Extract time from cleaned page text
        # Strip HTML tags to get plain text, then use the same time parser
        page_text = re.sub(r'<[^>]+>', ' ', detail_html)
        page_text = re.sub(r'\s+', ' ', page_text)
        time_raw = parse_time_from_desc(page_text)
        if not time_raw:
            # Fallback: try "HH Uhr" without minutes in main content
            m2 = re.search(r'<main[^>]*>.*?(\d{1,2})\s*Uhr', detail_html, re.DOTALL)
            if m2:
                hours = int(m2.group(1))
                if 0 <= hours <= 23:
                    time_raw = f"{hours:02d}:00"
        
        # Extract location
        location = extract_venue_location(detail_html)
        if not location:
            location = district
        
        # Extract organizer
        organizer = extract_organizer(detail_html)
        
        # Extract description (prefer short description, fall back to meta)
        desc = extract_short_description(detail_html)
        if not desc:
            m2 = re.search(r'<meta\s+name="description"\s+content="([^"]+)"', detail_html)
            if m2:
                desc = m2.group(1)
        
        # Extract category from URL for tags
        category = extract_category_from_url(event_url)
        
        # Build tags: district + category
        tags_list = [district]
        if category:
            tags_list.append(category)
        
        events.append({
            "title": title,
            "date_start": date_start,
            "date_end": date_start,
            "time_raw": time_raw,
            "location": location,
            "organizer": organizer,
            "description": desc,
            "event_url": event_url,
            "district": district,
            "_source": "venue_page",
            "tags": tags_list,
        })
        
        print(f"  [venue page {venue_id}] '{title}' → {district}", flush=True)
    
    return events


def parse_time_from_desc(desc):
    """Parse time from description. Avoids matching date patterns like '29.05'."""
    # Remove date patterns (DD.MM.YYYY or DD.MM.YY) to avoid false time matches
    cleaned = re.sub(r'\d{1,2}\.\d{1,2}\.\d{2,4}', ' ', desc)
    # First try "HH  bis  HH:MM" pattern (start time, not end time)
    # This must be checked BEFORE simple "HH:MM" to correctly parse "16 bis 16.45 Uhr" as 16:00
    m = re.search(r'(\d{1,2})(?:[:.](\d{2}))?\s+bis\s+\d{1,2}(?:[:.]\d{2})', cleaned)
    if m:
        hours = int(m.group(1))
        mins = int(m.group(2) or "00")
        if 0 <= hours <= 23 and 0 <= mins <= 59:
            return f"{hours:02d}:{mins:02d}"
    # Then try "HH:MM Uhr" or "HH.MM Uhr" or "HH:MM" or "HH.MM"
    # Use (?!\d) lookahead to avoid matching decimal numbers like "1.000" as "1:00"
    m = re.search(r'(\d{1,2})[:.](\d{2})(?!\d)\s*(?:Uhr)?', cleaned)
    if m:
        hours = int(m.group(1))
        mins = int(m.group(2))
        if 0 <= hours <= 23 and 0 <= mins <= 59:
            return f"{hours:02d}:{mins:02d}"
    # Finally try "HH Uhr" (without colon/dot, e.g. "19 Uhr")
    m = re.search(r'(?<!\d)(\d{1,2})\s*Uhr(?!\d)', cleaned)
    if m:
        hours = int(m.group(1))
        if 0 <= hours <= 23:
            return f"{hours:02d}:00"
    return ""


def scrape_karlsruhe():
    """Main scraper function."""
    print("  Fetching Karlsruhe RSS feed...", flush=True)
    rss_content = fetch_url(RSS_URL)
    if not rss_content:
        raise Exception(f"Failed to fetch RSS feed at {RSS_URL} (HTTP error or connection failure)")

    # Parse RSS XML
    root = ET.fromstring(rss_content)
    items = root.findall(".//item")

    all_events = []
    matched_count = 0
    skipped_no_district = 0
    skipped_weekly_market = 0

    print(f"  RSS items: {len(items)}", flush=True)

    for item in items:
        title_el = item.find("title")
        desc_el = item.find("description")
        link_el = item.find("link")
        pubdate_el = item.find("pubDate")

        title = title_el.text.strip() if title_el is not None and title_el.text else ""
        desc = desc_el.text.strip() if desc_el is not None and desc_el.text else ""
        link = link_el.text.strip() if link_el is not None and link_el.text else ""
        pubdate = pubdate_el.text.strip() if pubdate_el is not None and pubdate_el.text else ""

        if not title:
            continue

        # Skip weekly market events (already covered by Wochenmarkt scraper)
        if "wochenmarkt" in title.lower():
            skipped_weekly_market += 1
            continue

        # Skip cancelled events (marked "-- ENTFÄLLT --" in title)
        if re.search(r'ENTFÄLLT|abgesagt|cancelled', title, re.IGNORECASE):
            print(f"  [skip cancelled] '{title}'", flush=True)
            continue

        # Step 1: Check title + RSS description for district indicators
        rss_text = f"{title} {desc}"
        district = get_district_from_text(rss_text)

        # Step 2: If not found in RSS data, try fetching the detail page
        detail_html = None
        if link and link != SOURCE_URL:
            detail_html = fetch_url(link)
            if detail_html and not district:
                # Check structured location fields first
                location_text = extract_venue_location(detail_html)
                if location_text:
                    district = get_district_from_text(location_text)
                # Check page title
                if not district:
                    m = re.search(r'<title>(.*?)</title>', detail_html, re.DOTALL)
                    if m:
                        district = get_district_from_text(m.group(1))
                # Fallback: check key page sections for district mentions
                # This catches venues like "KunstRaum Neureut" where the district
                # name appears in venue/org fields not caught above
                if not district:
                    # Check the main content area (between <main> and </main>)
                    m = re.search(r'<main[^>]*>(.*?)</main>', detail_html, re.DOTALL)
                    if m:
                        main_text = re.sub(r'<[^>]+>', ' ', m.group(1))
                        main_text = re.sub(r'\s+', ' ', main_text)
                        district = get_district_from_text(main_text)
                    # Check meta description
                    if not district:
                        m = re.search(r'<meta\s+name="description"\s+content="([^"]+)"', detail_html)
                        if m:
                            district = get_district_from_text(m.group(1))
                    if district:
                        print(f"  [district found in page content] '{title}' → {district}", flush=True)

        # Phase 1: Innenstadt catch-all — if no district matched but the event
        # is a Kultur category (theater, musik, literatur, etc.), tag it as
        # Karlsruhe-Innenstadt so downtown events are captured for users
        # willing to travel ~12km to the city center.
        if not district:
            category = extract_category_from_url(link if link else "")
            if category and category.lower() in INNENSTADT_CATEGORIES:
                district = "Karlsruhe-Innenstadt"
                print(f"  [innenstadt catch-all] '{title}' → {category}", flush=True)
            else:
                skipped_no_district += 1
                continue

        # Parse date/time from pubDate
        date_start, time_raw = parse_pubdate(pubdate)

        # Try to get more precise time from description
        time_from_desc = parse_time_from_desc(desc)
        if time_from_desc:
            time_raw = time_from_desc

        # Extract location from description
        location = "Karlsruhe"
        desc_parts = desc.split(" - ")
        for part in desc_parts:
            part = part.strip()
            # Skip time/age/fee fragments
            if part and not re.match(r'^[\d\s:\.\-bisUhr]+$', part) \
               and not part.startswith(("Für", "Kostenfrei", "ohne", "Marktzeiten", "kostenfrei")):
                if any(c.isupper() for c in part) and len(part) > 3:
                    location = part
                    break

        # Use detail page location if available (more precise)
        organizer = ""
        category = extract_category_from_url(link if link else "")
        if detail_html:
            detail_loc = extract_venue_location(detail_html)
            if detail_loc:
                location = detail_loc
            # Extract organizer from detail page
            organizer = extract_organizer(detail_html)
            # Extract better description
            short_desc = extract_short_description(detail_html)
            if short_desc:
                desc = short_desc
        
        # Build tags: district + category
        tags_list = [district]
        if category:
            tags_list.append(category)

        matched_count += 1
        all_events.append({
            "title": title,
            "date_start": date_start,
            "date_end": date_start,
            "time_raw": time_raw,
            "location": location,
            "organizer": organizer,
            "description": desc,
            "event_url": link if link else RSS_URL,
            "district": district,
            "tags": tags_list,
        })

    # Step 3: Scrape known venue pages for events not in RSS feed
    known_urls = {e["event_url"] for e in all_events}
    venue_events = 0
    for venue_id, district in KNOWN_VENUES.items():
        ve = scrape_venue_page(venue_id, district)
        for e in ve:
            if e["event_url"] not in known_urls:
                all_events.append(e)
                known_urls.add(e["event_url"])
                venue_events += 1

    print(f"  Karlsruhe matched: {matched_count} events (RSS)", flush=True)
    print(f"  From venue pages: {venue_events} events", flush=True)
    print(f"  Skipped (no district): {skipped_no_district}", flush=True)
    print(f"  Skipped (weekly market): {skipped_weekly_market}", flush=True)

    return {
        "source_url": SOURCE_URL,
        "events": all_events,
    }


if __name__ == "__main__":
    result = scrape_karlsruhe()
    print(f"\nFound {len(result['events'])} events in districts")
    for e in result["events"]:
        print(f"  [{e['district']:10s}] {e['date_start']} | {e['time_raw']:5s} | {e['title'][:50]} | {e['location'][:30]}")
