import urllib.request
import json
import html

BASE_URL = "https://stutenseekinderkalender.de/wp-json/tribe/events/v1/events/?per_page=50&start_date=2025-01-01+00%3A00%3A00&end_date=2028-12-31+23%3A59%3A59&status=publish&page={}"
events_out = []

page = 1
while True:
    url = BASE_URL.format(page)
    print(f"Fetching page {page}...", file=__import__('sys').stderr)
    try:
        resp = urllib.request.urlopen(url)
        data = json.loads(resp.read())
    except Exception as e:
        print(f"Error on page {page}: {e}", file=__import__('sys').stderr)
        break

    for e in data.get("events", []):
        title = html.unescape(e.get("title", ""))
        url_field = e.get("url", "")
        start = e.get("start_date", "")
        end = e.get("end_date", "")
        venue_data = e.get("venue", {}) or {}
        venue = venue_data.get("venue", "") if isinstance(venue_data, dict) else ""
        venue_address = ""
        if isinstance(venue_data, dict):
            parts = [venue_data.get(k, "") for k in ["address", "city", "zip"]]
            venue_address = ", ".join(p for p in parts if p)

        organizer_data = e.get("organizer", []) or []
        organizers = []
        for o in (organizer_data if isinstance(organizer_data, list) else [organizer_data]):
            if isinstance(o, dict):
                organizers.append(o.get("organizer", ""))

        description = html.unescape(e.get("description", "").strip())
        if description:
            import re
            description = re.sub(r'<[^>]+>', '', description)
            description = html.unescape(description)

        date_start = start[:10] if start else ""
        date_end = end[:10] if end else ""
        time_raw = start[11:16] if len(start) > 16 else ""

        events_out.append({
            "title": title,
            "date_start": date_start,
            "date_end": date_end,
            "time_raw": time_raw,
            "location": f"{venue}, {venue_address}".strip(", "),
            "organizer": "; ".join(o for o in organizers if o),
            "description": description,
            "event_url": url_field,
        })

    total = data.get("total", 0)
    total_pages = data.get("total_pages", 1)
    has_next = data.get("next_rest_url")

    if not has_next:
        break

    page += 1
    if page > total_pages:
        break

result = {"source_url": "https://stutenseekinderkalender.de", "events": events_out}
print(json.dumps(result, ensure_ascii=False))
