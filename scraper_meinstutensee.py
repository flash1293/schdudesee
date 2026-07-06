import urllib.request
import re
import json
import html as html_mod

SOURCE_URL = "https://www.meinstutensee.de/termine"

def fetch_url(url, timeout=30):
    req = urllib.request.Request(url, headers={"User-Agent": "StutenseeEvents/1.0"})
    resp = urllib.request.urlopen(req, timeout=timeout)
    return resp.read().decode("utf-8", errors="replace")

def strip_html(text):
    """Remove HTML tags and decode entities."""
    text = re.sub(r"<[^>]+>", " ", text)
    text = re.sub(r"\s+", " ", text)
    return html_mod.unescape(text).strip()

def parse_date(date_str):
    """
    Parse EventON date format like '2026-7-6T16:00+2:00' or '2026-7-12'.
    Returns (date_iso "YYYY-MM-DD", time_raw "HH:MM" or "").
    Pipeline expects date_start/date_end as date-only.
    """
    if not date_str:
        return "", ""
    # Match: YYYY-M-DTHH:MM+TZ:00 or YYYY-M-D
    m = re.match(r"(\d{4})-(\d{1,2})-(\d{1,2})(?:T(\d{1,2}):(\d{2})(\+(\d{1,2}):(\d{2}))?)?", date_str)
    if not m:
        return "", ""
    y, mo, d = m.group(1), m.group(2).zfill(2), m.group(3).zfill(2)
    date_iso = f"{y}-{mo}-{d}"
    time_raw = ""
    if m.group(4):
        hh = m.group(4).zfill(2)
        mm = m.group(5)
        time_raw = f"{hh}:{mm}"
    return date_iso, time_raw

def scrape_meinstutensee():
    events = []
    seen = set()

    html_content = fetch_url(SOURCE_URL)

    # Extract all JSON-LD blocks
    ld_blocks = re.findall(
        r'<script type="application/ld\+json">(.*?)</script>',
        html_content, re.DOTALL
    )

    for ld in ld_blocks:
        try:
            data = json.loads(ld)
        except json.JSONDecodeError:
            continue

        if data.get("@type") != "Event":
            continue

        title = data.get("name", "")
        if not title:
            continue

        start_raw = data.get("startDate", "")
        end_raw = data.get("endDate", "")

        date_start, time_raw = parse_date(start_raw)
        date_end, _ = parse_date(end_raw) if end_raw else ("", "")

        # Dedup: use start date + title
        dedup_key = f"{date_start[:10]}|{title.lower()}"
        if dedup_key in seen:
            continue
        seen.add(dedup_key)

        # Location
        loc_name = ""
        loc_addr = ""
        locations = data.get("location", [])
        if locations and isinstance(locations, list) and len(locations) > 0:
            loc = locations[0]
            loc_name = loc.get("name", "")
            addr = loc.get("address", {})
            if isinstance(addr, dict):
                loc_addr = addr.get("streetAddress", "")
        location = loc_name
        if loc_addr and loc_addr != loc_name:
            location = f"{loc_name}, {loc_addr}"

        # Organizer
        organizer = ""
        organizers = data.get("organizer", [])
        if organizers and isinstance(organizers, list) and len(organizers) > 0:
            org = organizers[0]
            organizer = org.get("name", "")

        # Description — strip WordPress block placeholders
        description = data.get("description", "")
        description = strip_html(description)
        # Remove empty WordPress block placeholders
        description = re.sub(r"wp:\w+\s*\{[^}]*\}\s*", "", description)
        description = re.sub(r"/wp:\w+", "", description)
        description = re.sub(r"\s+", " ", description).strip()

        event_url = data.get("url", "")

        events.append({
            "title": html_mod.unescape(title),
            "date_start": date_start,
            "date_end": date_end if date_end else None,
            "time_raw": time_raw,
            "location": location,
            "organizer": organizer,
            "description": description,
            "event_url": html_mod.unescape(event_url),
        })

    return {"source_url": SOURCE_URL, "events": events}
