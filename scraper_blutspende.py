#!/usr/bin/env python3
"""
Scraper for DRK Blutspendedienst — Stutensee blood donation appointments.
https://www.blutspende.de/blutspendetermine/stadt/stutensee-08215109
"""

import re
import html
import urllib.request


def fetch_url(url, timeout=30):
    req = urllib.request.Request(url, headers={"User-Agent": "StutenseeEvents/1.0"})
    resp = urllib.request.urlopen(req, timeout=timeout)
    return resp.read().decode("utf-8", errors="replace")


def scrape_blutspende():
    url = "https://www.blutspende.de/blutspendetermine/stadt/stutensee-08215109"
    events = []

    try:
        html_content = fetch_url(url)
    except Exception as e:
        print(f"  Error fetching Blutspende page: {e}", flush=True)
        return {"source_url": url, "events": []}

    # Each event card is inside .item.clearfix within .terminliste
    for item in re.findall(
        r'<div\s+class="item\s+clearfix"[^>]*>(.*?)</div>\s*</div>\s*</div>\s*</div>\s*</div>',
        html_content,
        re.DOTALL,
    ):
        # Extract date from <p> inside .datum
        date_m = re.search(r'<p[^>]*>(\d{2})\.(\d{2})\.(\d{4})</p>', item)
        if not date_m:
            continue
        iso_date = f"{date_m.group(3)}-{date_m.group(2).zfill(2)}-{date_m.group(1).zfill(2)}"

        # Spendeart (always "Blutspende")
        type_m = re.search(r'<p\s+class="spendeart"[^>]*>([^<]+)</p>', item)
        title = type_m.group(1).strip() if type_m else "Blutspende"

        # Location from .adresse
        loc_m = re.search(r'<div\s+class="adresse"[^>]*>(.*?)</div>', item, re.DOTALL)
        location = ""
        venue = ""
        street = ""
        if loc_m:
            adr = loc_m.group(1)
            parts = [p.strip() for p in re.split(r'<br\s*/?>', adr) if p.strip()]
            # First <strong> is city line
            city_m = re.search(r'<strong>(.*?)</strong>', adr)
            if city_m:
                location = city_m.group(1).strip()
            # Second <strong> is time
            time_m = re.search(r'<strong>(\d{1,2}:\d{2}\s*-\s*\d{1,2}:\d{2}\s*Uhr)</strong>', adr)
            time_raw = time_m.group(1) if time_m else ""
            # Venue name and street are the non-strong plain text lines
            plain_parts = [re.sub(r'<[^>]+>', '', p).strip() for p in parts]
            plain_parts = [p for p in plain_parts if p and re.search(r'\d{1,2}:\d{2}', p) is None]
            if len(plain_parts) >= 2:
                venue = plain_parts[-2]  # second-to-last plain line
                street = plain_parts[-1] if len(plain_parts) >= 2 else ""
            elif len(plain_parts) == 1:
                venue = plain_parts[0]
        else:
            time_raw = ""

        full_location = ", ".join(p for p in [location, venue, street] if p)

        # Event URL
        link_m = re.search(r'<a\s+[^>]*href="(/blutspendetermine/termine/\d+)"', item)
        event_url = "https://www.blutspende.de" + link_m.group(1) if link_m else ""

        events.append({
            "title": title,
            "date_start": iso_date,
            "date_end": None,
            "time_raw": time_raw,
            "location": full_location,
            "organizer": "DRK-Blutspendedienst Baden-Württemberg – Hessen gGmbH",
            "description": "",
            "event_url": event_url,
        })

    return {"source_url": url, "events": events}


if __name__ == "__main__":
    result = scrape_blutspende()
    print(f"Found {len(result['events'])} event(s)")
    for e in result["events"]:
        print(f"  {e['date_start']} | {e['title']} | {e['time_raw']} | {e['location']}")
        print(f"    URL: {e['event_url']}")
