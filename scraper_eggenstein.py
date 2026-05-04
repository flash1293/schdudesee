import urllib.request
import re
import html

BASE = "https://www.egg-leo.de/Veranstaltungen?item=eventDate&view=find&doPage=1&limit=15&offset={}"
SOURCE = "https://www.egg-leo.de/Veranstaltungen"

def fetch_url(url):
    req = urllib.request.Request(url, headers={"User-Agent": "StutenseeEvents/1.0"})
    resp = urllib.request.urlopen(req, timeout=30)
    return resp.read().decode("utf-8", errors="replace")

def parse_date(date_str):
    parts = date_str.split(".")
    if len(parts) >= 3:
        y = "20" + parts[2] if len(parts[2]) == 2 else parts[2]
        return f"{y}-{parts[1].zfill(2)}-{parts[0].zfill(2)}"
    return ""

def scrape_eggenstein():
    events = []
    seen = set()
    for page in range(10):
        offset = page * 15
        html_content = fetch_url(BASE.format(offset))
        blocks = re.findall(
            r'<div class="cVeka_stripes_eventDate(?:Odd|Even)[^"]*"[^>]*>.*?<div style="clear:\s*both;">\s*</div>\s*</div>',
            html_content, re.DOTALL
        )
        if not blocks:
            break
        for b in blocks:
            date_m = re.search(r'cVeka_stripes_date[^>]*>.*?,\s*([\d.]+)', b, re.DOTALL)
            title_m = re.search(r'cVeka_stripes_title[^>]*>\s*<a\s+href="([^"]+)"[^>]*>([^<]+)</a>', b, re.DOTALL)
            teaser_m = re.search(r'cVeka_stripes_teaser[^>]*>([^<]+)', b)
            loc_m = re.search(r'cVeka_box_location[^>]*>Veranstaltungsort:\s*(.*?)(?:</div>|$)', b, re.DOTALL)
            org_m = re.search(r'cVeka_box_organizer[^>]*>Veranstalter:\s*(.*?)(?:</div>|$)', b, re.DOTALL)

            date_str = date_m.group(1).strip() if date_m else ""
            iso = parse_date(date_str)
            title = title_m.group(2).strip() if title_m else ""
            event_url = title_m.group(1).strip() if title_m else ""
            teaser = re.sub(r'<[^>]+>', '', teaser_m.group(1)).strip() if teaser_m else ""
            loc = re.sub(r'<[^>]+>', '', loc_m.group(1)).strip() if loc_m else ""
            org = re.sub(r'<[^>]+>', '', org_m.group(1)).strip() if org_m else ""

            dedup_key = f"{iso}|{title}"
            if not iso or not title or dedup_key in seen:
                continue
            seen.add(dedup_key)

            events.append({
                "title": title, "date_start": iso, "date_end": None,
                "time_raw": "", "location": loc, "organizer": org,
                "description": html.unescape(teaser), "event_url": html.unescape(event_url),
            })
    return {"source_url": SOURCE, "events": events}
