#!/usr/bin/env python3
"""
scraper_bruchsal.py — Scraper for Bruchsal (Baden) event sources.

CMS: dvv-Mastertemplates by Pirobase with dvv-Zusatzmodule 10.13.0.5
Approach:
1. RSS feed — fast check for upcoming events
2. Paginated list view — comprehensive event set (pages 1-8)
3. Detail pages — full event data (description, categories)
"""

import re
import xml.etree.ElementTree as ET
from concurrent.futures import ThreadPoolExecutor, as_completed
from urllib.parse import urljoin
from datetime import datetime, date

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
    except Exception:
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


def clean_event_url(url):
    if not url:
        return url
    return re.sub(r'[?&]zm\.sid=[^&]+', '', url).rstrip('?&')

def parse_detail_page(html, session):
    """Parse a Bruchsal event detail page for full data."""
    soup = BeautifulSoup(html, "html.parser")
    detail = {}

    def find_label_data(label_pattern):
        label = soup.find(class_="label", string=re.compile(label_pattern, re.I))
        if label:
            data_el = label.find_next_sibling()
            if data_el:
                return data_el.get_text(" ", strip=True)
        return None

    def parse_location(data_div):
        parts = []
        kopf = data_div.select_one(".kopf")
        if kopf:
            titel = kopf.select_one(".titel")
            value = kopf.select_one(".value")
            name = " ".join(p for p in [
                titel.get_text(strip=True) if titel else "",
                value.get_text(strip=True) if value else ""
            ] if p)
            if name:
                parts.append(name)
        street = data_div.select_one(".street-address")
        if street:
            parts.append(street.get_text(strip=True))
        cityline = data_div.select_one(".cityline")
        if cityline:
            plz = cityline.select_one(".postal-code")
            loc = cityline.select_one(".locality")
            city = " ".join(p for p in [
                plz.get_text(strip=True) if plz else "",
                loc.get_text(strip=True) if loc else ""
            ] if p)
            if city:
                parts.append(city)
        return ", ".join(parts)

    def parse_organizer(data_div):
        kopf = data_div.select_one(".kopf")
        if kopf:
            return kopf.get_text(" ", strip=True)
        return None

    detail["description"] = find_label_data(r"Beschreibung")
    loc_label = soup.find(class_="label", string=re.compile(r"Veranstaltungsort", re.I))
    if loc_label:
        loc_div = loc_label.find_next_sibling()
        if loc_div:
            detail["location"] = parse_location(loc_div)
    org_label = soup.find(class_="label", string=re.compile(r"Veranstalter", re.I))
    if org_label:
        org_div = org_label.find_next_sibling()
        if org_div:
            detail["organizer"] = parse_organizer(org_div)

    cat_el = soup.select_one(".zusatzbezeichnung, .zusatzbezeichnungen")
    if cat_el:
        detail["category"] = cat_el.get_text(strip=True)

    return detail


def scrape_rss(session):
    """Parse the RSS feed for upcoming events (fast, 5 items)."""
    events = []
    rss_text = fetch_url(RSS_URL, session)
    if not rss_text:
        return events

    try:
        root = ET.fromstring(rss_text)
    except ET.ParseError:
        return events

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
            title = re.sub(r"^[\s-]*\d{2}\.\d{2}\.\d{4}([\s-]*\d{2}\.\d{2}\.\d{4})*\s*", "", title_text).strip()

            organization = desc_soup.select_one(".organization")
            location = organization.get_text(strip=True) if organization else ""

            org_header = desc_soup.find("h4", string=re.compile(r"Veranstalter", re.I))
            organizer = ""
            if org_header:
                org_data = org_header.find_next_sibling()
                if org_data:
                    organizer = org_data.get_text(strip=True)

            events.append({
                "title": title, "date_start": date_start, "date_end": None,
                "time_raw": time_raw, "location": location, "organizer": organizer,
                "description": "", "event_url": link, "district": "Bruchsal",
            })
        except Exception:
            continue
    return events


def parse_zmitem_list_page(soup):
    """Parse events from a page of .zmitem elements (paginated list view)."""
    events = []
    for item in soup.select(".zmitem"):
        try:
            link = item.select_one('a.titel[href*="zmdetail"]') or item.select_one('a[href*="zmdetail"]')
            if not link:
                continue
            title = re.sub(r"^[\s-]*\d{2}\.\d{2}\.\d{4}([\s-]*\d{2}\.\d{2}\.\d{4})*\s*", "", link.get_text(strip=True)).strip()
            href = link.get("href", "")
            event_url = urljoin(BASE_URL, href) if href else ""

            time_el = item.select_one(".zmitem__time")
            time_text = time_el.get_text(strip=True) if time_el else ""
            date_str = parse_german_date(time_text)
            if not date_str:
                continue
            time_raw = parse_time(time_text)

            kat_el = item.select_one(".zmitem__kat")
            category = kat_el.get_text(" ", strip=True) if kat_el else ""

            events.append({
                "title": title,
                "date_start": date_str,
                "date_end": None,
                "time_raw": time_raw,
                "location": "",
                "organizer": "",
                "description": "",
                "category": category,
                "event_url": event_url,
                "district": "Bruchsal",
            })
        except Exception:
            continue
    return events


def scrape_paginated_list(session):
    """Parse the paginated event list view (pages 1-8)."""
    all_events = []
    seen_urls = set()

    for page_num in range(1, 9):
        url = f"{CALENDAR_URL}?page={page_num}" if page_num > 1 else CALENDAR_URL
        html = fetch_url(url, session)
        if not html:
            continue
        soup = BeautifulSoup(html, "html.parser")
        page_events = parse_zmitem_list_page(soup)
        if not page_events:
            break
        for ev in page_events:
            if ev["event_url"] not in seen_urls:
                seen_urls.add(ev["event_url"])
                all_events.append(ev)

    return all_events


def enrich_from_detail(event, session):
    """Fetch detail page to enrich an event with description, location, organizer."""
    if not event.get("event_url"):
        return event
    html = fetch_url(event["event_url"], session)
    if html:
        detail = parse_detail_page(html, session)
        if detail.get("description"):
            event["description"] = detail["description"]
        if detail.get("location"):
            event["location"] = detail["location"]
        if detail.get("organizer"):
            event["organizer"] = detail["organizer"]
    return event


def scrape_bruchsal():
    session = requests.Session()
    session.headers.update({"User-Agent": "Mozilla/5.0 (compatible; StutenseeBot/1.0)"})

    all_events = scrape_rss(session)
    seen_urls = {e.get("event_url", "") for e in all_events if e.get("event_url")}

    list_events = scrape_paginated_list(session)
    for ev in list_events:
        if ev.get("event_url") and ev["event_url"] not in seen_urls:
            seen_urls.add(ev["event_url"])
            all_events.append(ev)

    def enrich(event):
        return enrich_from_detail(event, session)

    enriched = []
    with ThreadPoolExecutor(max_workers=5) as executor:
        futures = {executor.submit(enrich, ev): i for i, ev in enumerate(all_events)}
        for future in as_completed(futures):
            try:
                enriched.append(future.result())
            except Exception:
                enriched.append(all_events[futures[future]])

    for ev in enriched:
        ev["event_url"] = clean_event_url(ev.get("event_url"))

    return {
        "source_url": CALENDAR_URL,
        "events": enriched,
    }


if __name__ == "__main__":
    result = scrape_bruchsal()
    print(f"Found {len(result['events'])} events from Bruchsal")
    for e in result["events"][:10]:
        print(f"  {e['date_start']} | {e['title'][:50]} | {e['time_raw']} | {e['location'][:25]}")
    if len(result["events"]) > 10:
        print(f"  ... and {len(result['events']) - 10} more")
