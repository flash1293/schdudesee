import urllib.request
import json
import re
import html as html_mod

SOURCE_URL = "https://landfunker.de/terminkalender-events-veranstaltungen-bruchsal-bretten-kraichtal-waghaeusel-philippsburg-noerdl-lkr-karlsruhe"
API_BASE = "https://landfunker.de/wp-json/stec/v5"
AJAX_URL = "https://landfunker.de/wp-admin/admin-ajax.php"

def fetch_json(url, timeout=30):
    req = urllib.request.Request(url, headers={
        "User-Agent": "StutenseeEvents/1.0",
        "X-WP-Nonce": _nonce(),
    })
    resp = urllib.request.urlopen(req, timeout=timeout)
    return json.loads(resp.read().decode("utf-8", errors="replace"))

_nonce_cache = None

def _nonce():
    global _nonce_cache
    if _nonce_cache:
        return _nonce_cache
    try:
        url = f"{AJAX_URL}?action=stec_rest_nonce"
        req = urllib.request.Request(url, headers={"User-Agent": "StutenseeEvents/1.0"})
        resp = urllib.request.urlopen(req, timeout=15)
        data = json.loads(resp.read().decode("utf-8", errors="replace"))
        if data.get("success"):
            _nonce_cache = data["data"]
            return _nonce_cache
    except Exception:
        pass
    return ""

def strip_html(text):
    text = re.sub(r"<[^>]+>", " ", text)
    text = re.sub(r"\s+", " ", text)
    return html_mod.unescape(text).strip()

def parse_date(date_str):
    """Parse '2026-08-02T17:00' to ('2026-08-02', '17:00')"""
    if not date_str:
        return "", ""
    parts = date_str.split("T")
    date_part = parts[0]
    time_part = ""
    if len(parts) > 1:
        tm = parts[1].split("+")[0].split("-")[0]  # Remove timezone offset
        if ":" in tm:
            time_part = tm[:5]  # HH:MM
    return date_part, time_part

def scrape_landfunker():
    events = []
    seen = set()

    # Fetch lookup tables (paginated)
    loc_map = {}
    org_map = {}
    for endpoint, target_map in [("locations", loc_map), ("organizers", org_map)]:
        page = 1
        while True:
            try:
                items = fetch_json(f"{API_BASE}/{endpoint}?per_page=100&page={page}")
            except Exception:
                break
            if not items or not isinstance(items, list) or len(items) == 0:
                break
            for item in items:
                target_map[item["id"]] = item.get("name", "")
            if len(items) < 100:
                break
            page += 1

    # Fetch events (paginated)
    page = 1
    while True:
        try:
            data = fetch_json(f"{API_BASE}/events?per_page=100&page={page}")
        except Exception:
            break

        if not data or not isinstance(data, list) or len(data) == 0:
            break

        for ev in data:
            meta = ev.get("meta", {})
            title = strip_html(ev.get("title", {}).get("rendered", ""))
            if not title:
                continue

            start_raw = meta.get("start_date", "")
            end_raw = meta.get("end_date", "")
            all_day = meta.get("all_day", False)

            date_start, time_raw = parse_date(start_raw)
            date_end, _ = parse_date(end_raw)

            if all_day:
                time_raw = ""

            # Dedup
            dedup_key = f"{date_start}|{title.lower()}"
            if dedup_key in seen:
                continue
            seen.add(dedup_key)

            # Location
            loc_ids = ev.get("stec_loc", [])
            location = ""
            if loc_ids:
                loc_names = [loc_map.get(lid, "") for lid in loc_ids]
                location = ", ".join(filter(None, loc_names))

            # Organizer
            org_ids = ev.get("stec_org", [])
            organizer = ""
            if org_ids:
                org_names = [org_map.get(oid, "") for oid in org_ids]
                organizer = ", ".join(filter(None, org_names))

            # Description
            description = strip_html(ev.get("content", {}).get("rendered", ""))

            # URL
            event_url = ev.get("link", "")

            events.append({
                "title": title,
                "date_start": date_start,
                "date_end": date_end if date_end else None,
                "time_raw": time_raw,
                "location": location,
                "organizer": organizer,
                "description": description,
                "event_url": event_url,
            })

        # Check if more pages
        if len(data) < 100:
            break
        page += 1

    return {"source_url": SOURCE_URL, "events": events}
