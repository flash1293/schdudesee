import urllib.request
import xml.etree.ElementTree as ET
import re
from datetime import datetime

RSS_URL = "https://vsv-buechig.net/feed/"
SOURCE_URL = "https://vsv-buechig.net/"

GERMAN_MONTHS = {
    'Januar': '01', 'Februar': '02', 'März': '03', 'April': '04',
    'Mai': '05', 'Juni': '06', 'Juli': '07', 'August': '08',
    'September': '09', 'Oktober': '10', 'November': '11', 'Dezember': '12'
}

SKIP_TITLE_PATTERNS = [
    r'kreisklasse', r'\d+\s*:\s*\d+', r'\d+\.\s*spieltag',
    r'freundschafts.spieletag', r'bautagebuch',
    r'generalversammlung', r'mitgliederversammlung',
    r'arbeitseinsatz',
]

DATE_IN_TITLE = re.compile(r'am\s+(\d{1,2})\.\s*([A-Za-zäöüß]+)\s*(\d{4})', re.IGNORECASE)
DATE_RAW = re.compile(r'(\d{2})\.(\d{2})\.(\d{4})')
DATE_IN_TEXT = re.compile(r'(\d{1,2})\.\s*([A-Za-zäöüß]+)\s*(\d{4})', re.IGNORECASE)

HTML_ENTITIES = {
    '&uuml;': 'ü', '&ouml;': 'ö', '&auml;': 'ä', '&szlig;': 'ß',
    '&Uuml;': 'Ü', '&Ouml;': 'Ö', '&Auml;': 'Ä',
    '&nbsp;': ' ', '&lt;': '<', '&gt;': '>', '&amp;': '&',
    '&#8211;': '–', '&#8222;': '„', '&#8220;': '“',
    '&#8217;': "'", '&#8230;': '…', '&#038;': '&',
}

def clean_html(text):
    text = re.sub(r'<[^>]+>', '', text)
    for code, char in HTML_ENTITIES.items():
        text = text.replace(code, char)
    return ' '.join(text.split()).strip()

def extract_date_from_text(text):
    for src in [DATE_IN_TITLE, DATE_IN_TEXT]:
        m = src.search(text)
        if m:
            month = GERMAN_MONTHS.get(m.group(2))
            if month:
                return f"{m.group(3)}-{month}-{m.group(1).zfill(2)}"
    m = DATE_RAW.search(text)
    if m:
        return f"{m.group(3)}-{m.group(2)}-{m.group(1)}"
    return ""

def should_skip(title):
    for pat in SKIP_TITLE_PATTERNS:
        if re.search(pat, title.lower()):
            return True
    return False

def scrape_vsv_buechig():
    try:
        req = urllib.request.Request(RSS_URL, headers={"User-Agent": "StutenseeEvents/1.0"})
        resp = urllib.request.urlopen(req, timeout=30)
        xml_data = resp.read().decode("utf-8", errors="replace")

        root = ET.fromstring(xml_data)
        events = []
        today = datetime.now().strftime("%Y-%m-%d")

        for item in root.findall('.//item'):
            title = item.findtext('title', '')
            link = item.findtext('link', '')
            desc_html = item.findtext('description', '')
            categories = [c.text for c in item.findall('category') if c.text]

            if should_skip(title):
                continue

            description = clean_html(desc_html)
            combined = f"{title} {description}"

            date_start = extract_date_from_text(combined)
            if not date_start:
                continue

            if date_start <= today:
                continue

            location = "VSV Büchig-Sportpark, Waldstraße 56, 76297 Stutensee-Büchig"
            cat_str = ', '.join(categories).lower()
            if 'auswärts' in cat_str or 'gast' in cat_str.lower():
                location = "Stutensee-Büchig"

            events.append({
                "title": title.strip(),
                "date_start": date_start,
                "date_end": None,
                "time_raw": "",
                "location": location,
                "organizer": "VSV Büchig e.V.",
                "description": description,
                "event_url": link,
            })

        return {"source_url": SOURCE_URL, "events": events}

    except Exception as e:
        print(f"VSV Büchig scraper error: {e}")
        return {"source_url": SOURCE_URL, "events": []}

if __name__ == "__main__":
    result = scrape_vsv_buechig()
    print(f"Found {len(result['events'])} events")
    for ev in result['events']:
        print(f"  {ev['date_start']} - {ev['title']}")
