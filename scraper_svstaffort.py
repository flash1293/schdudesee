import urllib.request
import re
import html as html_mod
from datetime import datetime

SOURCE_URL = "https://svstaffort.de/sv2/bin/index.php?c=Termine"
BASE_URL = "https://svstaffort.de/sv2/bin/"

DATE_TIME_RE = re.compile(r'(\d{1,2})\.(\d{1,2})\.(\d{4})\s*@?\s*(\d{1,2}):(\d{2})')
DATE_ONLY_RE = re.compile(r'(\d{1,2})\.(\d{1,2})\.(\d{4})')

HTML_ENTITIES = {
    '&auml;': 'ä', '&ouml;': 'ö', '&uuml;': 'ü', '&szlig;': 'ß',
    '&Auml;': 'Ä', '&Ouml;': 'Ö', '&Uuml;': 'Ü',
    '&nbsp;': ' ', '&amp;': '&', '&#8211;': '–', '&#8222;': '„',
    '&#8220;': '“', '&#8217;': "'", '&#8230;': '…', '&#038;': '&',
}


def clean(text):
    """Decode HTML entities and collapse whitespace."""
    for code, char in HTML_ENTITIES.items():
        text = text.replace(code, char)
    text = re.sub(r'<[^>]+>', ' ', text)
    return ' '.join(text.split()).strip()


def parse_date_time(raw):
    """
    Parse 'DD.MM.YYYY @ HH:MM' or 'DD.MM.YYYY'.
    Returns (date_iso "YYYY-MM-DD", time_raw "HH:MM" or "").
    """
    if not raw or not raw.strip():
        return "", ""

    m = DATE_TIME_RE.search(raw)
    if m:
        date_iso = f"{m.group(3)}-{m.group(2).zfill(2)}-{m.group(1).zfill(2)}"
        time_raw = f"{m.group(4)}:{m.group(5)}"
        return date_iso, time_raw

    m = DATE_ONLY_RE.search(raw)
    if m:
        date_iso = f"{m.group(3)}-{m.group(2).zfill(2)}-{m.group(1).zfill(2)}"
        return date_iso, ""

    return "", ""


def fetch_page(url, timeout=30):
    """Fetch a URL and return decoded HTML."""
    req = urllib.request.Request(url, headers={"User-Agent": "StutenseeEvents/1.0"})
    resp = urllib.request.urlopen(req, timeout=timeout)
    return resp.read().decode("utf-8", errors="replace")


def scrape_svstaffort():
    events = []
    today = datetime.now().strftime("%Y-%m-%d")

    try:
        html_content = fetch_page(SOURCE_URL)
    except Exception as e:
        print(f"SV Staffort scraper error (fetch): {e}")
        return {"source_url": SOURCE_URL, "events": []}

    # Extract the table body: everything between <table> and </table>
    table_m = re.search(r'<table>(.*?)</table>', html_content, re.DOTALL)
    if not table_m:
        print("SV Staffort scraper: no table found")
        return {"source_url": SOURCE_URL, "events": []}

    table_html = table_m.group(1)

    # Find all rows (skip the header row with <th>)
    rows = re.findall(r'<tr>(.*?)</tr>', table_html, re.DOTALL)

    for row in rows:
        if '<th>' in row:
            continue

        # Extract cells: <td>...</td>
        cells = re.findall(r'<td>(.*?)</td>', row, re.DOTALL)
        if len(cells) < 3:
            continue

        title_cell = cells[0]
        location = clean(cells[1]) if len(cells) > 1 else ""
        start_raw = clean(cells[2]) if len(cells) > 2 else ""
        end_raw = clean(cells[3]) if len(cells) > 3 else ""

        # Extract title and URL from <a href='...'>TITLE</a>
        link_m = re.search(r"<a\s+href='([^']*)'>([^<]*)</a>", title_cell)
        if not link_m:
            continue

        rel_url = link_m.group(1)
        title = clean(link_m.group(2))
        event_url = BASE_URL + rel_url

        if not title:
            continue

        date_start, time_raw = parse_date_time(start_raw)
        date_end, _ = parse_date_time(end_raw) if end_raw else ("", "")

        if not date_start:
            continue

        # Skip past events
        if date_start <= today:
            continue

        # Try to fetch description from individual event page
        description = ""
        try:
            detail_html = fetch_page(event_url)
            # Description is in the last <p> inside <div id='mr_inhalt'>
            content_m = re.search(r"id='mr_inhalt'>(.*?)</div>\s*<script", detail_html, re.DOTALL)
            if content_m:
                content = content_m.group(1)
                # Find description paragraphs (skip h3 title, date p, location p)
                paras = re.findall(r'<p>(.*?)</p>', content, re.DOTALL)
                # Description is usually the last paragraph
                if paras:
                    # Filter out the date paragraph (contains @) and short paragraphs
                    desc_candidates = [p for p in paras if '@' not in p and len(clean(p)) > 3]
                    if desc_candidates:
                        description = clean(desc_candidates[-1])[:500]
        except Exception:
            pass  # Non-critical: description is optional

        # Build location string
        loc_parts = []
        if location:
            loc_parts.append(location)
        loc_parts.append("Staffort")
        location_full = ", ".join(loc_parts)

        events.append({
            "title": title,
            "date_start": date_start,
            "date_end": date_end if date_end else None,
            "time_raw": time_raw,
            "location": location_full,
            "organizer": "SV Staffort e.V.",
            "description": description,
            "event_url": event_url,
        })

    return {"source_url": SOURCE_URL, "events": events}
