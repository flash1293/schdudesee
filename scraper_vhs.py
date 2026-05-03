"""
scraper_vhs.py — Scraper for VHS Karlsruhe Land (Stutensee events)

Structure:
- WordPress site with KuferWeb course management system
- Courses are listed via search results at /programm/kw/...
- Each course has a detail page with full info
- ICS export available per course at .../ics.php?knr={KURS_ID}
"""

import re
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, date
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup

BASE_URL = "https://www.vhs-karlsruhe-land.de"

STUTENSEE_DISTRICTS = [
    "Stutensee-Blankenloch",
    "Stutensee-B%C3%BCchig",
    "Stutensee-Friedrichstal",
    "Stutensee-Sp%C3%B6ck",
    "Stutensee-Staffort",
]

DISTRICT_MAP = {
    "Blankenloch": "Blankenloch",
    "Büchig": "Büchig",
    "Buchig": "Büchig",
    "Friedrichstal": "Friedrichstal",
    "Spöck": "Spöck",
    "Spock": "Spöck",
    "Staffort": "Staffort",
}

MONTH_MAP = {
    "Januar": 1, "Jan": 1, "Jänner": 1,
    "Februar": 2, "Feb": 2,
    "März": 3, "Maerz": 3, "Mär": 3,
    "April": 4, "Apr": 4,
    "Mai": 5,
    "Juni": 6, "Jun": 6,
    "Juli": 7, "Jul": 7,
    "August": 8, "Aug": 8,
    "September": 9, "Sep": 9,
    "Oktober": 10, "Okt": 10,
    "November": 11, "Nov": 11,
    "Dezember": 12, "Dez": 12,
}


def build_search_urls(start_date: str, end_date: str) -> list[str]:
    base = "/programm/kw/bereich/suche/suchesetzen/true/"
    urls = []
    for district in STUTENSEE_DISTRICTS:
        params = [
            ("kathaupt", "26;"),
            ("suchesetzen", "false;"),
            ("kfs_beginn_dat1", start_date),
            ("kfs_beginn_dat2", end_date),
            ("kfs_aussenst", district),
        ]
        qs = "&".join(f"{k}={v}" for k, v in params)
        urls.append(urljoin(BASE_URL, base + "?" + qs))
    return urls


def parse_german_date(text: str) -> str | None:
    text = text.strip()
    patterns = [
        r"(\d{2})\.(\d{2})\.(\d{4})",
        r"(\d{1,2})\.\s*([A-Za-zäöü]+)\s*(\d{4})",
    ]
    for pat in patterns:
        m = re.search(pat, text)
        if m:
            if pat == patterns[0]:
                return f"{m.group(3)}-{m.group(2)}-{m.group(1)}"
            else:
                day = m.group(1).zfill(2)
                month_name = m.group(2)
                year = m.group(3)
                for name, num in MONTH_MAP.items():
                    if month_name.lower().startswith(name.lower()[:3]):
                        return f"{year}-{num:02d}-{day}"
    return None


def parse_search_results(html: str) -> list[dict]:
    soup = BeautifulSoup(html, "html.parser")
    courses = []

    course_cards = soup.select("div.kw-ue")
    if not course_cards:
        course_cards = soup.find_all("div", class_="kw-ue")

    for card in course_cards:
        try:
            title_el = card.select_one(".kw-ue-title")
            if not title_el:
                continue
            title = title_el.get_text(strip=True)

            link_el = title_el.find("a") if title_el else None
            detail_url = None
            if link_el and link_el.get("href"):
                detail_url = urljoin(BASE_URL, link_el["href"])

            rows = card.find_all("div", class_="row")
            date_start = None
            time_raw = None
            location = None
            duration = None
            fee = None
            course_id = None

            for row in rows:
                text = row.get_text(" ", strip=True)
                if text.startswith("Beginn"):
                    date_start = parse_german_date(text)
                    time_match = re.search(r"(\d{2}:\d{2})\s*-\s*(\d{2}:\d{2})", text)
                    if time_match:
                        time_raw = f"{time_match.group(1)} - {time_match.group(2)}"
                elif text.startswith("Kursort"):
                    location = text.replace("Kursort", "", 1).strip()
                elif text.startswith("Dauer"):
                    duration = text.replace("Dauer", "", 1).strip()
                elif text.startswith("Gebühr") or text.startswith("Gebuehr"):
                    fee = text.replace("Gebühr", "").replace("Gebuehr", "", 1).strip()

            course_id = None
            if detail_url:
                id_match = re.search(r"/kurs/([A-Z0-9]+)/", detail_url)
                if id_match:
                    course_id = id_match.group(1)

            courses.append({
                "title": title,
                "date_start": date_start,
                "date_end": None,
                "time_raw": time_raw,
                "location": location,
                "fee": fee,
                "duration": duration,
                "course_id": course_id,
                "detail_url": detail_url,
            })
        except Exception as e:
            continue

    return courses


def parse_detail_page(html: str, base_data: dict) -> dict:
    soup = BeautifulSoup(html, "html.parser")

    description_parts = []
    desc_col = soup.select_one(".kw-kurs > .row .col-md-9 p")
    if desc_col:
        description_parts.append(desc_col.get_text(strip=True))

    location_header = soup.find(lambda t: t.name == "h3" and "Kursort" in t.get_text(strip=True))
    if location_header:
        loc_container = location_header.find_parent("div", class_="row")
        if loc_container:
            loc_text = loc_container.get_text(" ", strip=True)
            loc_text = loc_text.replace("Kursort", "", 1).strip()
            loc_text = loc_text.split("Google-Karte")[0].strip()
            if loc_text and not base_data.get("location"):
                base_data["location"] = loc_text
            elif loc_text and base_data.get("location"):
                base_data["location"] = loc_text

    instructor_header = soup.find(lambda t: t.name == "h3" and "Dozent" in t.get_text(strip=True))
    instructor = None
    if instructor_header:
        parent_row = instructor_header.find_parent("div", class_="row")
        if parent_row:
            h4 = parent_row.find("h4")
            if h4:
                instructor = h4.get_text(strip=True)

    fee_header = soup.find(lambda t: t.name == "b" and t.get_text(strip=True) == "Gebühr")
    if fee_header:
        fee_col = fee_header.find_parent("div", class_="row")
        if fee_col:
            fee_text = fee_col.get_text(" ", strip=True)
            fee_text = fee_text.replace("Gebühr", "", 1).strip()
            fee_text = fee_text.split("Euro")[0].strip() if "Euro" in fee_text else fee_text
            if fee_text:
                base_data["fee"] = fee_text

    beschreibung_header = soup.find(lambda t: t.name == "h3" and "Beschreibung" in t.get_text(strip=True))
    if beschreibung_header:
        dcol = beschreibung_header.find_next("div", class_="col-md-9")
        if dcol:
            for p in dcol.find_all("p"):
                t = p.get_text(strip=True)
                if t:
                    description_parts.append(t)

    description = "\n\n".join(description_parts) if description_parts else None

    result = dict(base_data)
    if description:
        result["description"] = description

    return result


def fetch_url(url: str, session: requests.Session = None) -> str | None:
    if session is None:
        session = requests.Session()
    try:
        resp = session.get(url, timeout=30)
        resp.raise_for_status()
        return resp.text
    except Exception as e:
        return None


def detect_district(location: str | None) -> str | None:
    if not location:
        return None
    for key, val in DISTRICT_MAP.items():
        if key.lower() in location.lower():
            return val
    return None


def scrape_vhs(start_date: str | None = None, end_date: str | None = None) -> dict:
    if start_date is None:
        start_date = "01.01.2026"
    if end_date is None:
        end_date = "31.12.2026"

    search_urls = build_search_urls(start_date, end_date)
    session = requests.Session()
    session.headers.update({
        "User-Agent": "Mozilla/5.0 (compatible; StutenseeBot/1.0)"
    })

    seen_ids = set()
    courses = []
    with ThreadPoolExecutor(max_workers=5) as executor:
        future_to_url = {executor.submit(fetch_url, surl, session): surl for surl in search_urls}
        for future in as_completed(future_to_url):
            html = future.result()
            if not html:
                continue
            for c in parse_search_results(html):
                cid = c.get("course_id")
                if cid and cid in seen_ids:
                    continue
                if cid:
                    seen_ids.add(cid)
                courses.append(c)

    events = []
    def fetch_detail(course):
        description = None
        location = course.get("location")
        district = detect_district(location)
        if not district:
            district = "Stutensee"

        detail_html = None
        if course.get("detail_url"):
            detail_html = fetch_url(course["detail_url"], session)

        return course, detail_html, district, location

    with ThreadPoolExecutor(max_workers=10) as executor:
        futures = [executor.submit(fetch_detail, c) for c in courses]
        for future in as_completed(futures):
            try:
                course, detail_html, district, location = future.result()
                description = None
                if detail_html:
                    full = parse_detail_page(detail_html, course)
                    description = full.get("description")
                    location = full.get("location", location)

                event = {
                    "title": course.get("title", ""),
                    "date_start": course.get("date_start"),
                    "date_end": course.get("date_end"),
                    "time_raw": course.get("time_raw"),
                    "location": location,
                    "district": district,
                    "organizer": "VHS Stutensee",
                    "description": description,
                    "event_url": course.get("detail_url") or search_url,
                    "fee": course.get("fee"),
                }
                events.append(event)
            except Exception:
                continue

    return {
        "source_url": "https://www.vhs-karlsruhe-land.de/standorte/stutensee/",
        "events": events,
        "total_raw_courses": len(courses),
    }


if __name__ == "__main__":
    result = scrape_vhs("01.01.2026", "31.12.2026")
    print(f"Found {len(result['events'])} events from VHS Stutensee")
    for e in result["events"][:5]:
        print(f"  - {e['title']} | {e['date_start']} | {e['location']} | {e['time_raw']}")
    if len(result["events"]) > 5:
        print(f"  ... and {len(result['events']) - 5} more")
