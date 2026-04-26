#!/usr/bin/env python3
"""
Scraper for Pestalozzi-Schule Stutensee events page.
Contao CMS with event list module. Paginated.
"""

import re
import json
from urllib.request import Request, urlopen
from html import unescape


def fetch_url(url, timeout=30):
    req = Request(url, headers={"User-Agent": "StutenseeEvents/1.0"})
    resp = urlopen(req, timeout=timeout)
    return resp.read().decode("utf-8", errors="replace")


def parse_date(dd_mm_yyyy):
    parts = dd_mm_yyyy.split(".")
    return f"{parts[2]}-{parts[1].zfill(2)}-{parts[0].zfill(2)}"


SKIP_KEYWORDS = ["ferien", "keine schule"]


def scrape_pestalozzi():
    events = []
    base_url = "https://www.pestalozzi-schule-stutensee.de/termine.html"

    page = 1
    total_pages = 1
    while page <= total_pages:
        url = base_url if page == 1 else f"{base_url}?page_e101={page}"
        html = fetch_url(url)

        # Determine total pages from "Seite X von Y" on first fetch
        if page == 1:
            pages_m = re.search(r'Seite\s+(\d+)\s+von\s+(\d+)', html)
            if pages_m:
                total_pages = int(pages_m.group(2))

        # Split on event divs
        raw_blocks = re.findall(
            r'<div[^>]*class="[^"]*\bevent\b[^"]*\blayout_teaser\b[^"]*"[^>]*>.*?</div>\s*</div>',
            html, re.DOTALL
        )

        for block in raw_blocks:
            date_m = re.search(r'<span class="date">(\d{2}\.\d{2}\.\d{4})</span>', block)
            time_m = re.search(r'<span class="time">([^<]+)</span>', block)
            title_m = re.search(r'<h2>(.*?)</h2>', block)

            if not title_m:
                continue

            title = unescape(title_m.group(1).strip())
            title_lower = title.lower()

            if any(skip in title_lower for skip in SKIP_KEYWORDS):
                continue

            date_str = date_m.group(1) if date_m else ""
            iso_date = parse_date(date_str) if date_str else ""
            time_str = time_m.group(1).strip() if time_m else ""

            events.append({
                "title": title,
                "date_start": iso_date,
                "date_end": None,
                "time_raw": time_str,
                "location": "Pestalozzi-Schule Blankenloch, Hauptstraße 100, 76297 Stutensee",
                "organizer": "Pestalozzi-Schule Blankenloch",
                "description": "",
                "event_url": url,
            })

        page += 1

    return {
        "source_url": "https://www.pestalozzi-schule-stutensee.de/termine.html",
        "events": events,
    }


if __name__ == "__main__":
    result = scrape_pestalozzi()
    print(json.dumps(result, indent=2, ensure_ascii=False))
