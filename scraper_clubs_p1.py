"""
scraper_clubs_p1.py — Batch 1 of club website scrapers for Stutensee events.

Structure: 10 club sites, each with own scrape_X() function.
All return events in the standard format.
Uses urllib.request + regex to match project style.
"""

import re
import json
import urllib.request
import urllib.parse
import html as html_mod


SOURCE_URL = "clubs_batch1"


def fetch_url(url, timeout=30):
    req = urllib.request.Request(url, headers={"User-Agent": "StutenseeEvents/1.0"})
    resp = urllib.request.urlopen(req, timeout=timeout)
    return resp.read().decode("utf-8", errors="replace")


def parse_german_date(text):
    dm = re.search(r'(\d{1,2})\.(\d{1,2})\.(\d{4})', text)
    if dm:
        return f"{dm.group(3)}-{int(dm.group(2)):02d}-{int(dm.group(1)):02d}"
    dm2 = re.search(r'(\d{1,2})\.(\d{1,2})\.(\d{2})(?!\d)', text)
    if dm2:
        y = "20" + dm2.group(3)
        return f"{y}-{int(dm2.group(2)):02d}-{int(dm2.group(1)):02d}"
    return ""


def strip_html(text):
    text = re.sub(r'<[^>]+>', ' ', text)
    text = re.sub(r'\s+', ' ', text).strip()
    return html_mod.unescape(text)


def scrape_bc_spoeck():
    """Badminton-Club Spöck — WordPress site. Try common events sub-pages."""
    events = []
    base = "https://bc-spoeck.de"
    urls_to_try = [
        base + "/",
        base + "/veranstaltungen/",
        base + "/events/",
        base + "/kalender/",
        base + "/termine/",
    ]
    seen = set()
    for url in urls_to_try:
        try:
            html_content = fetch_url(url, timeout=10)
        except Exception:
            continue
        for block in re.findall(
            r'<article[^>]*>(.*?)</article>',
            html_content, re.DOTALL
        ):
            title_m = re.search(r'<h[1-6][^>]*>(.*?)</h[1-6]>', block)
            date_m = re.search(r'(\d{1,2})\.(\d{1,2})\.(\d{4})', block)
            if not title_m or not date_m:
                continue
            title = strip_html(title_m.group(1))
            if not title or len(title) < 3:
                continue
            iso = f"{date_m.group(3)}-{int(date_m.group(2)):02d}-{int(date_m.group(1)):02d}"
            link_m = re.search(r'<a[^>]*href="([^"]+)"[^>]*>', block)
            event_url = urllib.parse.urljoin(base, link_m.group(1)) if link_m else base
            key = (title, iso)
            if key in seen:
                continue
            seen.add(key)
            events.append({
                "title": title,
                "date_start": iso,
                "date_end": None,
                "time_raw": "",
                "location": "Spöck",
                "organizer": "Badminton-Club Spöck",
                "description": "",
                "event_url": event_url,
            })
    return events


def scrape_bdp_adler():
    """BdP Stamm Adler — WordPress + The Events Calendar. Use REST API."""
    events = []
    api_url = "https://www.bdp-adler.de/wp-json/tribe/events/v1/events?per_page=50"
    try:
        data = json.loads(fetch_url(api_url, timeout=15))
    except Exception:
        return events
    for e in data.get("events", []):
        title = html_mod.unescape(e.get("title", ""))
        start = e.get("start_date", "")
        end = e.get("end_date", "")
        iso_start = start[:10] if start else ""
        iso_end = end[:10] if end else ""
        time_raw = start[11:16] if len(start) > 16 else ""
        v = e.get("venue", {}) or {}
        venue_parts = []
        if isinstance(v, dict):
            for k in ["venue", "address", "city"]:
                val = v.get(k, "")
                if val:
                    venue_parts.append(val)
        location = ", ".join(venue_parts)
        desc = html_mod.unescape(e.get("description", "") or "")
        desc = re.sub(r'<[^>]+>', '', desc).strip()
        events.append({
            "title": title,
            "date_start": iso_start,
            "date_end": iso_end,
            "time_raw": time_raw,
            "location": location,
            "organizer": "BdP Stamm Adler",
            "description": desc,
            "event_url": e.get("url", ""),
        })
    return events


def scrape_cvjm_spoeck():
    """CVJM Spöck — ecics CMS with /eventcalendar?calendar=16."""
    events = []
    url = "https://www.cvjm-spoeck.de/eventcalendar?calendar=16"
    try:
        html_content = fetch_url(url, timeout=10)
    except Exception:
        return events
    for item in re.findall(
        r'<div[^>]*class="ec-item-box"[^>]*>(.*?)</div>\s*</div>',
        html_content, re.DOTALL
    ):
        d1_m = re.search(r'<span class="d1">(\d{2})\.(\d{2})\.(\d{4})', item)
        if not d1_m:
            continue
        iso_start = f"{d1_m.group(3)}-{d1_m.group(2)}-{d1_m.group(1)}"
        d2_m = re.search(r'<span class="d2">(\d{2})\.(\d{2})\.(\d{4})', item)
        iso_end = f"{d2_m.group(3)}-{d2_m.group(2)}-{d2_m.group(1)}" if d2_m else None
        title_m = re.search(r'<h3[^>]*class="title"[^>]*>(.*?)</h3>', item)
        title = strip_html(title_m.group(1)) if title_m else ""
        if not title:
            continue
        events.append({
            "title": title,
            "date_start": iso_start,
            "date_end": iso_end,
            "time_raw": "",
            "location": "CVJM Spöck, Fröbelweg 1, 76297 Stutensee-Spöck",
            "organizer": "CVJM Spöck",
            "description": "",
            "event_url": "https://www.cvjm-spoeck.de/eventcalendar?calendar=16",
        })
    return events


def scrape_ev_kirche_friedrichstal():
    """Ev. Kirche Friedrichstal — ekistuwei CMS (same as Michaelisgemeinde)."""
    events = []
    base = "https://www.ekistuwei.de"
    urls_to_try = [
        "/gemeinden/kirchengemeinde-friedrichstal/",
        "/termine/",
    ]
    for path in urls_to_try:
        try:
            html_content = fetch_url(base + path, timeout=10)
        except Exception:
            continue
        for block in re.findall(
            r'<div[^>]*class="[^"]*termineintrag[^"]*"[^>]*>(.*?)</div>',
            html_content, re.DOTALL
        ):
            date_m = re.search(r'(\d{1,2})\.(\d{1,2})\.(\d{4})', block)
            title_m = re.search(r'<h[1-6][^>]*>(.*?)</h[1-6]>', block)
            if date_m and title_m:
                iso = f"{date_m.group(3)}-{int(date_m.group(2)):02d}-{int(date_m.group(1)):02d}"
                title = strip_html(title_m.group(1))
                events.append({
                    "title": title,
                    "date_start": iso,
                    "date_end": None,
                    "time_raw": "",
                    "location": "Friedrichstal",
                    "organizer": "Evangelische Kirchengemeinde Friedrichstal",
                    "description": "",
                    "event_url": base + path,
                })
        if events:
            break
    return events


def scrape_blankenloch_dlrg():
    """DLRG Ortsgruppe Blankenloch — TYPO3 site. Check termines JSON and iCal."""
    events = []
    try:
        html_content = fetch_url(
            "https://blankenloch.dlrg.de/die-ortsgruppe/termine/", timeout=10
        )
    except Exception:
        return events
    for block in re.findall(
        r'<div[^>]*class="[^"]*news[^"]*"[^>]*>(.*?)</div>',
        html_content, re.DOTALL
    ):
        date_m = re.search(r'(\d{1,2})\.(\d{1,2})\.(\d{4})', block)
        title_m = re.search(r'<h[1-6][^>]*>(.*?)</h[1-6]>', block)
        if date_m and title_m:
            iso = f"{date_m.group(3)}-{int(date_m.group(2)):02d}-{int(date_m.group(1)):02d}"
            title = strip_html(title_m.group(1))
            events.append({
                "title": title,
                "date_start": iso,
                "date_end": None,
                "time_raw": "",
                "location": "Blankenloch",
                "organizer": "DLRG Ortsgruppe Blankenloch",
                "description": "",
                "event_url": "https://blankenloch.dlrg.de/die-ortsgruppe/termine/",
            })
    return events


def scrape_spoeck_dlrg():
    """DLRG Gruppe Spöck — TYPO3 site. News contain event dates."""
    events = []
    try:
        html_content = fetch_url("https://spoeck.dlrg.de/", timeout=10)
    except Exception:
        return events
    for block in re.findall(
        r'<div[^>]*class="card[^"]*"[^>]*>(.*?)</div>\s*</div>',
        html_content, re.DOTALL
    ):
        date_m = re.search(r'(\d{1,2})\.(\d{1,2})\.(\d{4})', block)
        title_m = re.search(r'<h5[^>]*class="card-title"[^>]*>(.*?)</h5>', block)
        if not title_m:
            title_m = re.search(r'<h5[^>]*>(.*?)</h5>', block)
        link_m = re.search(r'<a[^>]*href="([^"]+)"[^>]*>', block)
        if date_m and title_m:
            iso = f"{date_m.group(3)}-{int(date_m.group(2)):02d}-{int(date_m.group(1)):02d}"
            title = strip_html(title_m.group(1))
            url = link_m.group(1) if link_m else ""
            if url and not url.startswith("http"):
                url = "https://spoeck.dlrg.de" + url
            events.append({
                "title": title,
                "date_start": iso,
                "date_end": None,
                "time_raw": "",
                "location": "Spöck",
                "organizer": "DLRG Gruppe Spöck",
                "description": "",
                "event_url": url or "https://spoeck.dlrg.de/",
            })
    return events


def scrape_drk_notfallhilfe():
    """DRK Ortsverein Blankenloch (drk-notfallhilfe.de -> drk-blankenloch.de)."""
    events = []
    base = "https://drk-blankenloch.de"
    urls_to_try = [base + "/", base + "/termine/", base + "/veranstaltungen/"]
    seen = set()
    for url in urls_to_try:
        try:
            html_content = fetch_url(url, timeout=10)
        except Exception:
            continue
        for block in re.findall(
            r'<article[^>]*>(.*?)</article>',
            html_content, re.DOTALL
        ):
            title_m = re.search(r'<h[1-6][^>]*>(.*?)</h[1-6]>', block)
            date_m = re.search(r'(\d{1,2})\.(\d{1,2})\.(\d{4})', block)
            link_m = re.search(r'<a[^>]*href="([^"]+)"[^>]*>', block)
            if not title_m or not date_m:
                continue
            title = strip_html(title_m.group(1))
            iso = f"{date_m.group(3)}-{int(date_m.group(2)):02d}-{int(date_m.group(1)):02d}"
            event_url = link_m.group(1) if link_m else base
            if event_url.startswith("/"):
                event_url = base + event_url
            key = (title, iso)
            if key in seen:
                continue
            seen.add(key)
            events.append({
                "title": title,
                "date_start": iso,
                "date_end": None,
                "time_raw": "",
                "location": "Blankenloch",
                "organizer": "DRK Ortsverein Blankenloch",
                "description": "",
                "event_url": event_url,
            })
    return events


def scrape_drkspoeck():
    """DRK Ortsverein Spöck — TYPO3 site. Check news and termines pages."""
    events = []
    base = "https://www.drkspoeck.de"
    urls_to_try = [
        base + "/nc.html",
        base + "/aktuelles/veranstaltungen/termine.html",
        base + "/nc/aktuelles/veranstaltungen/termine.html",
    ]
    seen = set()
    for url in urls_to_try:
        try:
            html_content = fetch_url(url, timeout=10)
        except Exception:
            continue
        for block in re.findall(
            r'<article[^>]*>(.*?)</article>',
            html_content, re.DOTALL
        ):
            title_m = re.search(r'<h[1-6][^>]*>(.*?)</h[1-6]>', block)
            date_m = re.search(r'(\d{1,2})\.(\d{1,2})\.(\d{4})', block)
            if not title_m or not date_m:
                continue
            title = strip_html(title_m.group(1))
            iso = f"{date_m.group(3)}-{int(date_m.group(2)):02d}-{int(date_m.group(1)):02d}"
            link_m = re.search(r'<a[^>]*href="([^"]+)"[^>]*>', block)
            event_url = link_m.group(1) if link_m else url
            if event_url.startswith("/"):
                event_url = base + event_url
            key = (title, iso)
            if key in seen:
                continue
            seen.add(key)
            events.append({
                "title": title,
                "date_start": iso,
                "date_end": None,
                "time_raw": "",
                "location": "Spöck, Alte Schule",
                "organizer": "DRK Ortsverein Spöck",
                "description": "",
                "event_url": event_url,
            })
    return events


def scrape_drk_staffort():
    """DRK Ortsverein Staffort — WordPress blog posts with dates."""
    events = []
    base = "https://drk-staffort.de"
    try:
        html_content = fetch_url(base + "/", timeout=10)
    except Exception:
        return events
    seen = set()
    for block in re.findall(
        r'<article[^>]*>(.*?)</article>',
        html_content, re.DOTALL
    ):
        title_m = re.search(r'<h3[^>]*class="entry-title"[^>]*>(.*?)</h3>', block)
        date_m = re.search(r'<time[^>]*datetime="([^"]+)"', block)
        link_m = re.search(r'<a[^>]*href="([^"]+)"[^>]*>', block)
        if not title_m:
            title_m = re.search(r'<h3[^>]*>(.*?)</h3>', block)
        if not title_m:
            continue
        title = strip_html(title_m.group(1))
        iso = ""
        if date_m:
            iso = date_m.group(1)[:10]
        if not iso:
            date_m2 = re.search(r'(\d{1,2})\.(\d{1,2})\.(\d{4})', block)
            if date_m2:
                iso = f"{date_m2.group(3)}-{int(date_m2.group(2)):02d}-{int(date_m2.group(1)):02d}"
        if not iso:
            continue
        event_url = link_m.group(1) if link_m else base
        if event_url.startswith("/"):
            event_url = base + event_url
        key = (title, iso)
        if key in seen:
            continue
        seen.add(key)
        events.append({
            "title": title,
            "date_start": iso,
            "date_end": None,
            "time_raw": "",
            "location": "Staffort",
            "organizer": "DRK Ortsverein Staffort",
            "description": "",
            "event_url": event_url,
        })
    return events


def scrape_michaelisgemeinde():
    """Michaelisgemeinde Blankenloch — ekistuwei CMS."""
    events = []
    base = "https://www.ekistuwei.de"
    paths = [
        "/gemeinden/michaelisgemeinde-blankenloch/",
        "/termine/",
    ]
    for path in paths:
        try:
            html_content = fetch_url(base + path, timeout=10)
        except Exception:
            continue
        for block in re.findall(
            r'<div[^>]*class="[^"]*termineintrag[^"]*"[^>]*>(.*?)</div>',
            html_content, re.DOTALL
        ):
            date_m = re.search(r'(\d{1,2})\.(\d{1,2})\.(\d{4})', block)
            title_m = re.search(r'<h[1-6][^>]*>(.*?)</h[1-6]>', block)
            if date_m and title_m:
                iso = f"{date_m.group(3)}-{int(date_m.group(2)):02d}-{int(date_m.group(1)):02d}"
                title = strip_html(title_m.group(1))
                events.append({
                    "title": title,
                    "date_start": iso,
                    "date_end": None,
                    "time_raw": "",
                    "location": "Blankenloch",
                    "organizer": "Michaelisgemeinde Blankenloch",
                    "description": "",
                    "event_url": base + path,
                })
        if events:
            break
    return events


def scrape_clubs_p1():
    all_events = []
    scrapers = [
        ("bc-spoeck.de", scrape_bc_spoeck),
        ("bdp-adler.de", scrape_bdp_adler),
        ("cvjm-spoeck.de", scrape_cvjm_spoeck),
        ("ev-kirche-friedrichstal.de", scrape_ev_kirche_friedrichstal),
        ("blankenloch.dlrg.de", scrape_blankenloch_dlrg),
        ("spoeck.dlrg.de", scrape_spoeck_dlrg),
        ("drk-notfallhilfe.de", scrape_drk_notfallhilfe),
        ("drkspoeck.de", scrape_drkspoeck),
        ("drk-staffort.de", scrape_drk_staffort),
        ("michaelisgemeinde.de", scrape_michaelisgemeinde),
    ]
    for name, func in scrapers:
        try:
            site_events = func()
            all_events.extend(site_events)
        except Exception:
            pass
    return {
        "source_url": SOURCE_URL,
        "events": all_events,
    }


if __name__ == "__main__":
    result = scrape_clubs_p1()
    print(f"Found {len(result['events'])} total events")
    for e in result["events"][:20]:
        print(f"  {e['date_start']} | {e['title']} | {e['organizer']}")
    if len(result["events"]) > 20:
        print(f"  ... and {len(result['events']) - 20} more")
