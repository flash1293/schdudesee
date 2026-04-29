#!/usr/bin/env python3
"""
Scraper for Bürgerverein Waldstadt website.
https://www.bv-waldstadt.de/
Sources:
  - /buergerverein/termine/ - structured HTML table
  - / (homepage) - blog-style posts with dates in titles
"""

import re
import json
import sys
from urllib.request import Request, urlopen
from datetime import datetime
from bs4 import BeautifulSoup

SOURCE_URL = "https://www.bv-waldstadt.de/"
TERMINE_URL = "https://www.bv-waldstadt.de/buergerverein/termine/"
HOME_URL = "https://www.bv-waldstadt.de/"


def fetch_url(url, timeout=30):
    req = Request(url, headers={"User-Agent": "StutenseeEvents/1.0"})
    resp = urlopen(req, timeout=timeout)
    return resp.read().decode("utf-8", errors="replace")


def parse_date_iso(text):
    dm = re.search(r'(\d{1,2})\.(\d{1,2})\.(\d{4})', text)
    if dm:
        return f"{dm.group(3)}-{dm.group(2).zfill(2)}-{dm.group(1).zfill(2)}"
    dm = re.search(r'(\d{1,2})\.\s*([A-Za-z]+)\s*(\d{4})', text)
    if dm:
        months = {m.lower(): i for i, m in enumerate(
            ["", "Januar", "Februar", "März", "April", "Mai", "Juni",
             "Juli", "August", "September", "Oktober", "November", "Dezember"]) if m}
        month_num = months.get(dm.group(2).lower())
        if month_num:
            return f"{dm.group(3)}-{str(month_num).zfill(2)}-{dm.group(1).zfill(2)}"
    return ""


def extract_time(text):
    tm = re.search(r'(\d{1,2})[:.](\d{2})\s*Uhr', text)
    if tm:
        return f"{int(tm.group(1)):02d}:{tm.group(2)} Uhr"
    tm = re.search(r'(\d{1,2})\s*-\s*(\d{1,2})\s*Uhr', text)
    if tm:
        return f"{int(tm.group(1)):02d}:00 - {int(tm.group(2)):02d}:00 Uhr"
    return ""


def is_past(iso_date):
    if not iso_date:
        return False
    try:
        return datetime.strptime(iso_date, "%Y-%m-%d").date() < datetime.now().date()
    except:
        return True


def scrape_termine_table():
    events = []
    try:
        html = fetch_url(TERMINE_URL)
    except Exception as e:
        print(f"  Error fetching termine page: {e}", flush=True)
        return events

    soup = BeautifulSoup(html, "lxml")
    table = soup.find("table", class_="termine")
    if not table:
        return events

    for row in table.find_all("tr"):
        cells = row.find_all("td")
        if len(cells) < 4:
            continue

        date_text = cells[0].get_text(strip=True)
        iso_date = parse_date_iso(date_text)
        if not iso_date or is_past(iso_date):
            continue

        time_raw = cells[1].get_text(strip=True)

        title_cell = cells[2]
        title = title_cell.get_text(strip=True)
        link = title_cell.find("a")
        event_url = ""
        if link and link.get("href"):
            href = link["href"]
            event_url = "https://www.bv-waldstadt.de" + href if href.startswith("/") else href

        loc_cell = cells[3]
        loc_lines = loc_cell.get_text("\n").split("\n")
        loc_lines = [l.strip() for l in loc_lines if l.strip()]
        location = loc_lines[-1] if loc_lines else ""
        description = " ".join(l.strip() for l in loc_lines if l.strip())

        events.append({
            "title": title,
            "date_start": iso_date,
            "date_end": None,
            "time_raw": time_raw,
            "location": location,
            "organizer": "Bürgerverein Waldstadt e.V.",
            "description": description,
            "event_url": event_url,
        })

    return events


def scrape_homepage_posts():
    events = []
    try:
        html = fetch_url(HOME_URL)
    except Exception as e:
        print(f"  Error fetching homepage: {e}", flush=True)
        return events

    soup = BeautifulSoup(html, "lxml")
    posts = soup.find_all("div", class_="post")

    for post in posts:
        title_el = post.find("h2", class_="post-title")
        if not title_el:
            continue
        title = title_el.get_text(strip=True)

        iso_date = parse_date_iso(title)
        if not iso_date or is_past(iso_date):
            continue

        content_el = post.find("div", class_="post-content")
        content_text = content_el.get_text(" ", strip=True) if content_el else ""

        time_raw = extract_time(content_text)
        if not time_raw:
            time_raw = extract_time(title)

        location = "Waldstadt, Karlsruhe"
        lm = re.search(r'Ort[:\s]+([^\n.!]+)', content_text)
        if lm:
            location = lm.group(1).strip()
        else:
            lm2 = re.search(r'(Bürgerzentrum Waldstadt[^.!?\n]*)', content_text)
            if lm2:
                location = lm2.group(1).strip()
            else:
                lm3 = re.search(r'(Waldstadt-Zentrum)', content_text)
                if lm3:
                    location = lm3.group(1).strip()

        events.append({
            "title": title,
            "date_start": iso_date,
            "date_end": None,
            "time_raw": time_raw,
            "location": location,
            "organizer": "Bürgerverein Waldstadt e.V.",
            "description": content_text[:500],
            "event_url": SOURCE_URL,
        })

    return events


def scrape_waldstadt():
    events = []
    seen_keys = set()

    for ev in scrape_termine_table() + scrape_homepage_posts():
        key = (ev["date_start"], ev["title"])
        if key not in seen_keys:
            seen_keys.add(key)
            events.append(ev)

    return {"source_url": SOURCE_URL, "events": events}


def main():
    result = scrape_waldstadt()
    print(json.dumps(result, indent=2, ensure_ascii=False))
    sys.stderr.write(f"Found {len(result['events'])} events\n")


if __name__ == "__main__":
    main()
