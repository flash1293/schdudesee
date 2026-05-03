#!/usr/bin/env python3
"""
scraper_bruchsal.py — Scraper for Bruchsal (Baden) event sources.

CMS: dvv-Mastertemplates by Pirobase with dvv-Zusatzmodule 10.13.0.5
Approach: Parse RSS feed with hCalendar microformats (preferred over HTML scraping)

Sources:
1. bruchsal.de — RSS feed with structured hCalendar event data
"""

import re
import xml.etree.ElementTree as ET
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup

BASE_URL = "https://www.bruchsal.de"
RSS_URL = urljoin(BASE_URL, "/site/Bruchsal-Internet-2023/zmrss/4614028/rss.xml")
CALENDAR_URL = urljoin(BASE_URL, "/erleben/freizeit/veranstaltungen")


def fetch_url(url, session=None, timeout=30):
    if session is None:
        session = requests.Session()
    try:
        resp = session.get(url, timeout=timeout, verify=False, headers={
            "User-Agent": "Mozilla/5.0 (compatible; StutenseeBot/1.0)"
        })
        resp.raise_for_status()
        return resp.text
    except Exception as e:
        return None


def parse_iso_date(text):
    if text and re.match(r"\d{4}-\d{2}-\d{2}", text):
        return text[:10]
    return None


def parse_german_date(text):
    if not text:
        return None
    m = re.search(r"(\d{2})\.(\d{2})\.(\d{4})", text)
    if m:
        return f"{m.group(3)}-{m.group(2)}-{m.group(1)}"
    return None


def parse_time(text):
    m = re.search(r"(\d{1,2}:\d{2})", text or "")
    return m.group(1) if m else ""


def scrape_bruchsal():
    session = requests.Session()
    session.headers.update({"User-Agent": "Mozilla/5.0 (compatible; StutenseeBot/1.0)"})

    all_events = []

    rss_text = fetch_url(RSS_URL, session)
    if not rss_text:
        return {"source_url": CALENDAR_URL, "events": []}

    try:
        root = ET.fromstring(rss_text)
    except ET.ParseError:
        return {"source_url": CALENDAR_URL, "events": []}

    items = root.findall(".//item")
    if not items:
        items = root.findall(".//{http://www.w3.org/2005/Atom}entry")

    for item in items:
        try:
            title_text = (item.findtext("title") or "").strip()

            link_el = item.find("link")
            link = ""
            if link_el is not None:
                link = link_el.get("href", "") or link_el.text or ""

            description_html = item.findtext("description") or ""
            desc_soup = BeautifulSoup(description_html, "html.parser")

            dtstart = desc_soup.select_one(".dtstart")
            date_start = parse_iso_date(dtstart.get("title", "") if dtstart else "")
            if not date_start and title_text:
                date_start = parse_german_date(title_text)
            if not date_start:
                continue

            uhr = desc_soup.select_one(".uhr")
            time_raw = parse_time(uhr.get_text(strip=True) if uhr else "")

            title = re.sub(r"^\d{2}\.\d{2}\.\d{4}\s*", "", title_text).strip()

            organization = desc_soup.select_one(".organization")
            location = organization.get_text(strip=True) if organization else ""

            street = desc_soup.select_one(".street-address")
            locality = desc_soup.select_one(".locality")
            postal_code = desc_soup.select_one(".postal-code")
            address_parts = []
            if street:
                address_parts.append(street.get_text(strip=True))
            cityline = ""
            if postal_code:
                cityline += postal_code.get_text(strip=True) + " "
            if locality:
                cityline += locality.get_text(strip=True)
            if cityline:
                address_parts.append(cityline.strip())
            if location and address_parts:
                location += ", " + ", ".join(address_parts)
            elif not location and address_parts:
                location = ", ".join(address_parts)

            org_header = desc_soup.find("h4", string=re.compile(r"Veranstalter", re.I))
            organizer = ""
            if org_header:
                org_data = org_header.find_next_sibling()
                if org_data:
                    organizer = org_data.get_text(strip=True)

            all_events.append({
                "title": title,
                "date_start": date_start,
                "date_end": None,
                "time_raw": time_raw,
                "location": location,
                "organizer": organizer,
                "description": "",
                "event_url": link,
                "district": "Bruchsal",
            })
        except Exception:
            continue

    return {
        "source_url": CALENDAR_URL,
        "events": all_events,
    }


if __name__ == "__main__":
    result = scrape_bruchsal()
    print(f"Found {len(result['events'])} events from Bruchsal")
    for e in result["events"]:
        print(f"  {e['date_start']} | {e['title'][:60]} | {e['time_raw']} | {e['location']}")
