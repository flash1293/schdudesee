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
import time
from datetime import datetime, date
from urllib.parse import urljoin

import urllib.request
from bs4 import BeautifulSoup

BASE_URL = "https://www.hagsfeld.de"
LIST_URL = BASE_URL + "/termine"
ORGANIZER = "Bürgerkommission Hagsfeld e.V."


def fetch_url(url: str, attempts: int = 3) -> str:
    """Fetch a URL, retrying on transient network errors (timeouts, 502s).

    The site is occasionally slow and briefly unavailable — fetching used to
    fail silently and the run recorded "0 fetched" even though the website had
    plenty of events, which tripped the health check as if the source had gone
    dark. Failures now retry and, if they persist, propagate so the run reports
    them as an ERROR instead of an empty result.
    """
    last_error: Exception | None = None
    for attempt in range(attempts):
        try:
            req = urllib.request.Request(
                url, headers={"User-Agent": "Mozilla/5.0 (compatible; StutenseeEvents/1.0)"}
            )
            with urllib.request.urlopen(req, timeout=30) as resp:
                return resp.read().decode("utf-8", errors="replace")
        except Exception as e:
            last_error = e
            if attempt + 1 < attempts:
                time.sleep(2 * (attempt + 1))
    raise last_error


def parse_datetime_attr(dt_value: str) -> tuple[str | None, str | None]:
    """
    Parse a datetime attribute value from Contao's <time> element.
    Returns (date_start, time_raw).
    Examples:
      '2026-05-01' -> ('2026-05-01', None)
      '2026-05-01T11:00:00+02:00' -> ('2026-05-01', '11:00')
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
    """
    Parse a German date range text like '11.06.2026–14.06.2026'.
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


def parse_event_list(html: str) -> list[dict]:
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

            # Fetch detail page for more info. A transient failure on one detail
            # page must not lose the event: fall back to the list-page data.
            location = ""
            description = ""
            try:
                detail_html = fetch_url(detail_url, attempts=2)
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
                                        description = re.sub(r"<[^>]+>", "", desc).strip()
                                if not date_end:
                                    ed = item.get("endDate")
                                    if ed and ed != item.get("startDate"):
                                        date_end = ed[:10]
                                break
                    except Exception:
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
            except Exception:
                pass  # keep the (title, date) from the list page

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
    all_events: list[dict] = []
    seen_urls: set[str] = set()

    for page_num in range(1, 3):  # up to 2 pages
        url = LIST_URL if page_num == 1 else f"{LIST_URL}?page_e103={page_num}"
        try:
            html = fetch_url(url)
        except urllib.error.HTTPError as e:
            # The site answers 404 (instead of an empty page) when the requested
            # calendar page does not exist — e.g. after the pagination param name
            # changed or the upcoming list shrank to less than a full page. This
            # simply means there are no more pages; stop instead of failing the
            # whole source.
            if e.code == 404 and page_num > 1:
                break
            raise
        events = parse_event_list(html)
        if not events:
            break
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
    print(f"fetched {len(result['events'])} events from {result['source_url']}")
