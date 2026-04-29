#!/usr/bin/env python3
"""
scraper_hagsfeld.py — Scraper for Hagsfeld community events.

Sources:
  - hagsfeld.de/termine — Contao CMS calendar (primary, ~12 events)
  - asv-hagsfeld.de — domain is parked, no event data

Structure (Contao):
  List pages at /termine (with ?page_e103=N pagination)
  Each event entry has <a> (title, link) and <time datetime="ISO">
  Detail pages at /termine/SLUG have location, description, JSON-LD
"""

import re
import sys
from datetime import datetime, date
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup

BASE_URL = "https://www.hagsfeld.de"
LIST_URL = BASE_URL + "/termine"
ORGANIZER = "Bürgerkommission Hagsfeld e.V."


def fetch_url(url: str, session: requests.Session) -> str | None:
    try:
        resp = session.get(url, timeout=30)
        resp.raise_for_status()
        return resp.text
    except Exception:
        return None


def parse_datetime_attr(dt_value: str) -> tuple[str | None, str | None]:
    """Parse a datetime attribute value from Contao's <time> element.
    Returns (date_start, time_raw).
    Examples:
      '2026-05-01' -> ('2026-05-01', None)
      '2026-05-01T11:00:00+02:00' -> ('2026-05-01', '11:00')
      '2026-06-11T14:00:00+01:00' -> ('2026-06-11', '14:00')
    """
    m = re.match(r"(\d{4}-\d{2}-\d{2})", dt_value)
    if not m:
        return (None, None)
    date_start = m.group(1)
    time_raw = None
    time_m = re.search(r"T(\d{2}:\d{2})", dt_value)
    if time_m:
        time_raw = time_m.group(1)
    return (date_start, time_raw)


def parse_date_range(text: str) -> tuple[str | None, str | None]:
    """Parse a German date range text like '11.06.2026–14.06.2026'.
    Returns (date_start, date_end).
    """
    dates = re.findall(r"(\d{2})\.(\d{2})\.(\d{4})", text)
    if len(dates) >= 1:
        start = f"{dates[0][2]}-{dates[0][1]}-{dates[0][0]}"
        end = None
        if len(dates) >= 2:
            end = f"{dates[1][2]}-{dates[1][1]}-{dates[1][0]}"
        return (start, end)
    return (None, None)


def parse_event_list(html: str, session: requests.Session) -> list[dict]:
    """Parse events from a list page, then enrich with detail page data."""
    soup = BeautifulSoup(html, "html.parser")
    events = []

    event_divs = soup.select("div.event.layout_upcoming.upcoming.cal_1")
    if not event_divs:
        event_divs = soup.find_all("div", class_=lambda c: c and "event" in c and "layout_upcoming" in c)

    for div in event_divs:
        try:
            link_el = div.find("a")
            if not link_el:
                continue
            title = link_el.get_text(strip=True)
            href = link_el.get("href", "")
            detail_url = urljoin(LIST_URL, href)

            time_el = div.find("time", class_="date")
            if not time_el:
                continue

            dt_value = time_el.get("datetime", "")
            text_content = time_el.get_text(strip=True)

            # Try to get date/time from datetime attribute first
            date_start, time_raw = parse_datetime_attr(dt_value)

            # Handle date ranges (e.g. "11.06.2026–14.06.2026") from the text
            date_end = None
            if "–" in text_content or "-" in text_content.replace("–", "-"):
                s, e = parse_date_range(text_content)
                if s and not date_start:
                    date_start = s
                if e:
                    date_end = e
                # Also check if datetime attribute has date_end in detail page

            # Fetch detail page for more info
            location = ""
            description = ""
            detail_html = fetch_url(detail_url, session)
            if detail_html:
                detail_soup = BeautifulSoup(detail_html, "html.parser")
                # Try JSON-LD first (most reliable)
                for script in detail_soup.find_all("script", type="application/ld+json"):
                    try:
                        import json
                        data = json.loads(script.string)
                        if isinstance(data, dict):
                            graph = data.get("@graph", [])
                        elif isinstance(data, list):
                            graph = data
                        else:
                            graph = []
                        for item in graph:
                            if isinstance(item, dict) and item.get("@type") == "Event":
                                if not location:
                                    loc = item.get("location", {})
                                    if isinstance(loc, dict):
                                        location = loc.get("name", "")
                                if not description:
                                    desc = item.get("description", "")
                                    if desc:
                                        # Strip HTML tags
                                        desc_clean = re.sub(r"<[^>]+>", "", desc).strip()
                                        description = desc_clean
                                if not date_end:
                                    ed = item.get("endDate")
                                    if ed and ed != item.get("startDate"):
                                        date_end = ed[:10]
                                break
                    except (json.JSONDecodeError, AttributeError):
                        continue

                # Fallback: parse HTML
                if not location:
                    loc_p = detail_soup.select_one("p.location")
                    if loc_p:
                        location = loc_p.get_text(strip=True)
                if not description:
                    ce_text = detail_soup.select_one("div.ce_text.block")
                    if ce_text:
                        desc_parts = []
                        for p in ce_text.find_all("p"):
                            t = p.get_text(strip=True)
                            if t:
                                desc_parts.append(t)
                        description = "\n\n".join(desc_parts) if desc_parts else ""

            events.append({
                "title": title,
                "date_start": date_start,
                "date_end": date_end,
                "time_raw": time_raw,
                "location": location,
                "organizer": ORGANIZER,
                "description": description,
                "event_url": detail_url,
            })
        except Exception:
            continue

    return events


def scrape_hagsfeld() -> dict:
    session = requests.Session()
    session.headers.update({"User-Agent": "Mozilla/5.0 (compatible; StutenseeBot/1.0)"})

    all_events = []
    seen_urls = set()

    for page_num in range(1, 3):  # 2 pages
        if page_num == 1:
            url = LIST_URL
        else:
            url = f"{LIST_URL}?page_e103={page_num}"

        html = fetch_url(url, session)
        if not html:
            continue

        events = parse_event_list(html, session)
        for e in events:
            if e["event_url"] not in seen_urls:
                seen_urls.add(e["event_url"])
                all_events.append(e)

    return {
        "source_url": LIST_URL,
        "events": all_events,
    }


if __name__ == "__main__":
    result = scrape_hagsfeld()
    print(f"Found {len(result['events'])} events from Hagsfeld")
    for e in result["events"]:
        loc = e["location"] or "—"
        desc = e["description"][:60] + "..." if len(e.get("description", "")) > 60 else e.get("description", "")
        print(f"  {e['date_start']} {e['time_raw'] or '':>5} | {e['title'][:40]:40} | {loc[:25]:25} | {desc[:40]}")
