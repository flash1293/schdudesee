import urllib.request
import re
import html
from datetime import datetime

HOME_URL = "https://rintheim-bv.de/"
SOURCE_URL = "https://rintheim-bv.de"

GERMAN_MONTHS = {
    'Januar': '01', 'Februar': '02', 'März': '03', 'April': '04',
    'Mai': '05', 'Juni': '06', 'Juli': '07', 'August': '08',
    'September': '09', 'Oktober': '10', 'November': '11', 'Dezember': '12'
}

DATE_GERMAN = re.compile(r'(?:am\s+)?(\d{1,2})\.\s*([A-Za-zäöüß]+)\s*(\d{4})', re.IGNORECASE)
DATE_SHORT = re.compile(r'(\d{1,2})\.(\d{1,2})\.(\d{2,4})')
TIME_RAW = re.compile(r'(?:um\s+)?(\d{1,2})(?::(\d{2}))?\s*Uhr')
TIME_RANGE = re.compile(r'(\d{1,2})(?::(\d{2}))?\s*(?:-|–|bis)\s*(\d{1,2})(?::(\d{2}))?\s*Uhr')
DATE_SUFFIX = re.compile(r'\s+(?:am\s+)?\d{1,2}\.\d{1,2}\.\d{2,4}(?:[,;]\s*[^,;]+)?\s*$')

HTML_ENTITIES = {
    '&auml;': 'ä', '&ouml;': 'ö', '&uuml;': 'ü', '&szlig;': 'ß',
    '&Auml;': 'Ä', '&Ouml;': 'Ö', '&Uuml;': 'Ü',
    '&nbsp;': ' ', '&amp;': '&', '&#8211;': '–', '&#8222;': '„',
    '&#8220;': '“', '&#8217;': "'", '&#8230;': '…',
}

def clean(text):
    for code, char in HTML_ENTITIES.items():
        text = text.replace(code, char)
    return ' '.join(text.split()).strip()

def extract_date(text):
    m = DATE_GERMAN.search(text)
    if m:
        month = GERMAN_MONTHS.get(m.group(2))
        if month:
            return f"{m.group(3)}-{month}-{m.group(1).zfill(2)}"
    m = DATE_SHORT.search(text)
    if m:
        y = m.group(3)
        y = "20" + y if len(y) == 2 else y
        return f"{y}-{m.group(2).zfill(2)}-{m.group(1).zfill(2)}"
    return ""

def extract_time(text):
    m = TIME_RANGE.search(text)
    if m:
        return f"{m.group(1)}:{m.group(2) or '00'}–{m.group(3)}:{m.group(4) or '00'}"
    m = TIME_RAW.search(text)
    if m:
        return f"{m.group(1)}:{m.group(2) or '00'}"
    return ""

def strip_title(title):
    return DATE_SUFFIX.sub('', title).strip()

def scrape_rintheim():
    try:
        req = urllib.request.Request(HOME_URL, headers={"User-Agent": "StutenseeEvents/1.0"})
        resp = urllib.request.urlopen(req, timeout=30)
        html_content = resp.read().decode("utf-8", errors="replace")

        events = []
        today = datetime.now().strftime("%Y-%m-%d")

        post_starts = [m.start() for m in re.finditer(r'<h2 class="entry-title">', html_content)]

        for pos in post_starts:
            block = html_content[pos:pos+10000]
            title_m = re.search(r'<a[^>]*href="([^"]*)"[^>]*rel="bookmark">([^<]+)</a>', block)
            if not title_m:
                continue

            url = title_m.group(1)
            title = clean(title_m.group(2))
            date_start = extract_date(title)
            if not date_start or date_start <= today:
                continue

            time_raw = extract_time(title)
            clean_title = strip_title(title)

            desc_m = re.search(r'<div class="entry-content">(.*?)(?:<h2\s|<footer|</article>|$)', block, re.DOTALL)
            desc = ""
            if desc_m:
                desc = clean(re.sub(r'<[^>]+>', ' ', desc_m.group(1)))[:300]

            events.append({
                "title": clean_title,
                "date_start": date_start,
                "date_end": None,
                "time_raw": time_raw,
                "location": "Karlsruhe-Rintheim",
                "organizer": "Bürgerverein Rintheim",
                "description": desc,
                "event_url": html.unescape(url),
            })

        return {"source_url": SOURCE_URL, "events": events}

    except Exception as e:
        print(f"Rintheim scraper error: {e}")
        return {"source_url": SOURCE_URL, "events": []}
