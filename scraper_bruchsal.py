#!/usr/bin/env python3
"""
scraper_bruchsal.py — Scraper for Bruchsal (Baden) event sources.

CMS: dvv-Mastertemplates by Pirobase with dvv-Zusatzmodule 10.13.0.5
Approach:
1. RSS feed — fast check for upcoming events
2. Monthly HTML calendar — full event set via ?month=YYYY-MM
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


def parse_detail_page(html, session):
    """Parse a Bruchsal event detail page for full data."""
    soup = BeautifulSoup(html, "html.parser")
    detail = {}

    # Description
    desc_label = soup.find("div", class_="label", string=re.compile(r"Beschreibung", re.I))
    if desc_label:
        data_div = desc_label.find_next_sibling("div", class_="data")
        if data_div:
            detail["description"] = data_div.get_text(" ", strip=True)

    # Location
    loc_label = soup.find("div", class_="label", string=re.compile(r"Veranstaltungsort", re.I))
    if loc_label:
        data_div = loc_label.find_next_sibling("div", class_="data")
        if data_div:
            detail["location"] = data_div.get_text(" ", strip=True)

    # Organizer
    org_label = soup.find("div", class_="label", string=re.compile(r"Veranstalter", re.I))
    if org_label:
        data_div = org_label.find_next_sibling("div", class_="data")
        if data_div:
            detail["organizer"] = data_div.get_text(" ", strip=True)

    # Category/Zusatzbezeichnung
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
            title = re.sub(r"^\d{2}\.\d{2}\.\d{4}\s*", "", title_text).strip()

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


def scrape_monthly_calendar(year, month, session):
    """Parse the monthly HTML calendar view for a given year/month."""
    month_str = f"{year}-{month:02d}"
    url = f"{CALENDAR_URL}?month={month_str}"
    html = fetch_url(url, session)
    if not html:
        return []

    soup = BeautifulSoup(html, "html.parser")
    events = []

    # Find all event links in the calendar
    for link in soup.select("a.titel[href*='zmdetail']"):
        try:
            title = link.get_text(strip=True)
            href = link.get("href", "")
            event_url = urljoin(BASE_URL, href) if href else ""

            # Find date: check td parent or any parent for date pattern
            date_str = ""
            for parent_el in [link.find_parent("td"), link.parent, link.parent.parent]:
                if parent_el:
                    ptext = parent_el.get_text(strip=True)
                    d = re.search(r"(\d{1,2})\.(\d{1,2})\.(\d{4})", ptext)
                    if d:
                        date_str = f"{d.group(3)}-{d.group(2).zfill(2)}-{d.group(1).zfill(2)}"
                        break

            if not date_str:
                continue

            events.append({
                "title": title,
                "date_start": date_str,
                "date_end": None,
                "time_raw": "",
                "location": "",
                "organizer": "",
                "description": "",
                "event_url": event_url,
                "district": "Bruchsal",
            })
        except Exception:
            continue

    return events


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

    # Step 1: RSS feed (fast upcoming events)
    all_events = scrape_rss(session)
    seen_urls = {e.get("event_url", "") for e in all_events if e.get("event_url")}

    # Step 2: Monthly calendar views (comprehensive)
    now = date.today()
    for year in range(2026, now.year + 1):
        start_month = 1 if year < now.year else 1
        end_month = 12 if year < now.year else now.month + 3
        for month in range(start_month, end_month + 1):
            month_events = scrape_monthly_calendar(year, month, session)
            for ev in month_events:
                if ev.get("event_url") and ev["event_url"] not in seen_urls:
                    seen_urls.add(ev["event_url"])
                    all_events.append(ev)

    # Step 3: Enrich with detail page data (parallel)
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
