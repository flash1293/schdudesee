#!/usr/bin/env python3
"""
Scraper for Gewerbeverein Stutensee events page.
https://gewerbeverein-stutensee.org/veranstaltungen

Events are static HTML embedded via WPBakery Page Builder.
Primary source: <ul> list inside vc_message_box (16 events for 2026).
Secondary source: individual wpb_text_column event cards with h3 + date paragraphs.
"""
import re
import json
import sys
import urllib.request
import html as html_mod


SOURCE_URL = "https://gewerbeverein-stutensee.org/veranstaltungen"


def fetch_url(url, timeout=30):
    req = urllib.request.Request(url, headers={"User-Agent": "StutenseeEvents/1.0"})
    resp = urllib.request.urlopen(req, timeout=timeout)
    return resp.read().decode("utf-8", errors="replace")


def parse_date(day, month):
    """Convert DD.MM to YYYY-MM-DD. Year is 2026 (all current events are 2026)."""
    return f"2026-{int(month):02d}-{int(day):02d}"


def strip_html(text):
    text = re.sub(r'<[^>]+>', ' ', text)
    text = text.replace('&amp;', '&').replace('&#8211;', '–').replace('&#8222;', '"').replace('&#8220;', '"')
    text = text.replace('&nbsp;', ' ').replace('&ndash;', '–')
    text = re.sub(r'\s+', ' ', text).strip()
    return text


def parse_li_item(li_html):
    """Parse a single <li> element from the event list."""
    text = strip_html(li_html)
    if not text:
        return None

    event = {}

    # Extract date: "Sa., 17.01." or "Mo., 02.02." etc.
    date_m = re.match(r'\w+\.,?\s*(\d{1,2})\.(\d{1,2})\.', text)
    if not date_m:
        return None
    day, month = date_m.groups()
    event['date_start'] = parse_date(day, month)

    remaining = text[date_m.end():].strip()

    # Extract title (all-caps word after optional time prefix)
    title_m = re.search(r'([A-ZÖÄÜ][A-ZÖÄÜ]+(?:/[A-ZÖÄÜ]+)?)', remaining)
    if title_m:
        event['title'] = title_m.group(1).strip()
    else:
        return None

    # Extract time: look for patterns like "14:00 Uhr", "18.00 Uhr", "ca. 13:00 Uhr", "ab 18:00 Uhr"
    time_m = re.search(r'(ca\.|ab)?\s*(\d{1,2})[:.](\d{2})\s*Uhr', remaining)
    if time_m:
        prefix = time_m.group(1) or ""
        h, m = time_m.group(2), time_m.group(3)
        event['time_raw'] = f"{prefix + ' ' if prefix else ''}{int(h):02d}:{m} Uhr"

    # Extract location: everything after the title, after removing "|" separators
    loc_parts = re.split(r'\s*\|\s*', remaining)
    title_idx = None
    for i, part in enumerate(loc_parts):
        if event['title'] in part:
            title_idx = i
            break

    if title_idx is not None:
        parts_after = [p.strip() for p in loc_parts[title_idx + 1:] if p.strip()]
        venue = loc_parts[title_idx].split(event['title'], 1)[-1].strip().strip('|').strip()
        if venue:
            parts_after.insert(0, venue)
        if parts_after:
            event['location'] = ' | '.join(parts_after)

    return event


def parse_detail_cards(html):
    """Extract additional details from individual event cards (wpb_text_column with h3)."""
    cards = {}
    blocks = re.findall(
        r'<div class="wpb_text_column wpb_content_element[^"]*">\s*<div class="wpb_wrapper">(.*?)</div>\s*</div>',
        html, re.DOTALL
    )
    for block in blocks:
        title_m = re.search(r'<h3>(.*?)</h3>', block)
        date_m = re.search(r'(\d{1,2})\.(\d{1,2})\.(\d{4})', block)
        desc_m = re.search(r'<p>(.*?)</p>', block, re.DOTALL)
        if title_m and date_m:
            title = strip_html(title_m.group(1)).strip().upper()
            day, month, year = date_m.groups()
            key = f"{year}-{int(month):02d}-{int(day):02d}"
            card = {'title': strip_html(title_m.group(1)).strip()}
            if desc_m:
                desc = strip_html(desc_m.group(1))
                if desc:
                    card['description'] = desc
            cards[key] = card
    return cards


def scrape_gewerbeverein():
    """Scrape all events from Gewerbeverein Stutensee."""
    html = fetch_url(SOURCE_URL)

    events = []
    seen_keys = set()

    # Extract the main event <ul> list from the vc_message_box
    ul_m = re.search(
        r'<div class="vc_message_box[^"]*"[^>]*>.*?<ul>(.*?)</ul>',
        html, re.DOTALL
    )
    if not ul_m:
        return {"source_url": SOURCE_URL, "events": []}

    ul_html = ul_m.group(1)
    li_items = re.findall(r'<li>(.*?)</li>', ul_html, re.DOTALL)

    detail_cards = parse_detail_cards(html)

    for li in li_items:
        item = parse_li_item(li)
        if not item:
            continue

        date_key = item['date_start']
        if date_key in seen_keys:
            continue
        seen_keys.add(date_key)

        event = {
            "title": item['title'],
            "date_start": item['date_start'],
            "date_end": None,
            "time_raw": item.get('time_raw', ''),
            "location": item.get('location', ''),
            "organizer": "Gewerbeverein Stutensee",
            "description": "",
            "event_url": SOURCE_URL,
        }

        # Enrich with detail card data if available
        if date_key in detail_cards:
            card = detail_cards[date_key]
            if 'description' in card and card['description']:
                event['description'] = card['description']

        events.append(event)

    return {"source_url": SOURCE_URL, "events": events}


def main():
    result = scrape_gewerbeverein()
    print(json.dumps(result, ensure_ascii=False, indent=2))
    sys.stderr.write(f"Found {len(result['events'])} events\n")


if __name__ == '__main__':
    main()
