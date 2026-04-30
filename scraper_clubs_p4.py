#!/usr/bin/env python3
"""
Scraper for 9 Stutensee club sites (batch 4).

Sites:
  1. musikverein-blankenloch.de — JEvents calendar
  2. pferdefreunde-blankenloch.de — WordPress, image-based
  3. schuetzenverein-blankenloch-1913.de — IONOS, text-based Termine
  4. sgsw.de — WordPress, handball.net widget
  5. theatergruppehoffmann.de — IONOS, simple text
  6. tsg-blankenloch.de — Custom CMS, news-based
  7. tv-friedrichstal.de — Joomla, HTML table
  8. ttvbw.click-tt.de — click-TT (league site, no upcoming)
  9. ttf-spoeck.de — static HTML
"""
import re
import json
import sys
import urllib.request
import html as html_mod


def fetch_url(url, timeout=30):
    req = urllib.request.Request(url, headers={"User-Agent": "StutenseeEvents/1.0"})
    resp = urllib.request.urlopen(req, timeout=timeout)
    return resp.read().decode("utf-8", errors="replace")


def to_iso(d, m, y=None):
    if y is None:
        y = 2026
    return f"{int(y):04d}-{int(m):02d}-{int(d):02d}"


def strip_html(text):
    text = re.sub(r'<[^>]+>', ' ', text)
    text = text.replace('&amp;', '&').replace('&nbsp;', ' ').replace('&#8211;', '-')
    text = text.replace('&ouml;', 'ö').replace('&Ouml;', 'Ö')
    text = text.replace('&auml;', 'ä').replace('&Auml;', 'Ä')
    text = text.replace('&uuml;', 'ü').replace('&Uuml;', 'Ü')
    text = text.replace('&szlig;', 'ß').replace('&ndash;', '-')
    text = text.replace('&bdquo;', '"').replace('&ldquo;', '"')
    text = text.replace('&hellip;', '…')
    text = re.sub(r'\s+', ' ', text).strip()
    return text


def scrape_musikverein_blankenloch():
    """Parse homepage sidebar latest events table + homepage blog posts."""
    events = []
    month_names_de = {
        'Januar': 1, 'Februar': 2, 'März': 3, 'April': 4, 'Mai': 5, 'Juni': 6,
        'Juli': 7, 'August': 8, 'September': 9, 'Oktober': 10,
        'November': 11, 'Dezember': 12,
    }
    month_abbr = {
        'Jan': 1, 'Feb': 2, 'Mär': 3, 'Apr': 4, 'Mai': 5, 'Jun': 6,
        'Jul': 7, 'Aug': 8, 'Sep': 9, 'Okt': 10, 'Nov': 11, 'Dez': 12,
    }

    try:
        html = fetch_url("https://musikverein-blankenloch.de/")
    except Exception:
        return []

    table_rows = re.findall(
        r"<tr><td[^>]*class=\"mod_events_latest[^\"]*\"[^>]*>(.*?)</td></tr>",
        html, re.DOTALL
    )
    for row in table_rows:
        date_m = re.search(r'(\d{1,2})\s+(\w+)\s+(\d{4})', row)
        if not date_m:
            continue
        day_str, month_str, year_str = date_m.group(1), date_m.group(2), date_m.group(3)
        month_num = month_names_de.get(month_str) or month_abbr.get(month_str)
        if not month_num:
            continue
        date_start = to_iso(int(day_str), month_num, int(year_str))

        time_m = re.search(r'(\d{1,2}):(\d{2})(AM|PM)', row)
        time_raw = ""
        if time_m:
            h, m, ampm = int(time_m.group(1)), time_m.group(2), time_m.group(3)
            if ampm == 'PM' and h != 12:
                h += 12
            elif ampm == 'AM' and h == 12:
                h = 0
            time_raw = f"{h:02d}:{m}"

        title_m = re.search(r"<a[^>]*>(.*?)</a>", row)
        title = strip_html(title_m.group(1)) if title_m else ""
        if not title:
            continue

        events.append({
            "title": title,
            "date_start": date_start,
            "date_end": None,
            "time_raw": time_raw,
            "location": "",
            "organizer": "Musikverein Harmonie Blankenloch e.V.",
            "description": "",
            "event_url": "https://musikverein-blankenloch.de/",
        })

    blog_articles = re.findall(
        r'<div class="leading[^"]*"[^>]*>.*?<h2[^>]*>.*?<a[^>]*>(.*?)</a>',
        html, re.DOTALL
    )
    for art_title in blog_articles:
        title = strip_html(art_title)
        pos = html.find(art_title)
        if pos >= 0:
            context = html[max(0, pos-200):pos+200]
            date_m = re.search(r'(\d{1,2})\.\s*(\w+)\s+(\d{4})', context)
            if date_m:
                day_str, month_str, year_str = date_m.group(1), date_m.group(2), date_m.group(3)
                month_num = month_names_de.get(month_str)
                if month_num:
                    date_start = to_iso(int(day_str), month_num, int(year_str))
                    events.append({
                        "title": title,
                        "date_start": date_start,
                        "date_end": None,
                        "time_raw": "",
                        "location": "",
                        "organizer": "Musikverein Harmonie Blankenloch e.V.",
                        "description": "",
                        "event_url": "https://musikverein-blankenloch.de/",
                    })
    return events


def scrape_pferdefreunde_blankenloch():
    """WordPress site, events in images/text on homepage."""
    url = "https://pferdefreunde-blankenloch.de/"
    try:
        html = fetch_url(url)
    except Exception:
        return []

    events = []
    text = strip_html(html)

    date_patterns = re.findall(r'(\d{1,2})\.(\d{1,2})\.(\d{4})', text)
    seen = set()
    for d, m, y in date_patterns:
        key = to_iso(int(d), int(m), int(y))
        if key in seen:
            continue
        seen.add(key)
        year_int = int(y)
        if year_int < 2025 or year_int > 2027:
            continue
        events.append({
            "title": "Reitturnier",
            "date_start": key,
            "date_end": None,
            "time_raw": "",
            "location": "Reitanlage Blankenloch",
            "organizer": "Pferdefreunde Blankenloch 1972 e.V.",
            "description": "",
            "event_url": url,
        })

    img_alts = re.findall(r'alt="([^"]*)"', html)
    alt_text = ' '.join(img_alts)
    alt_dates = re.findall(r'(\d{1,2})[./](\d{1,2})(?:[./](\d{4}))?', alt_text)
    for match in alt_dates:
        d, m = int(match[0]), int(match[1])
        y = int(match[2]) if match[2] else 2026
        if y < 2025 or y > 2027:
            continue
        if m < 1 or m > 12 or d < 1 or d > 31:
            continue
        key = to_iso(d, m, y)
        if key not in seen:
            seen.add(key)
            events.append({
                "title": "Reitturnier",
                "date_start": key,
                "date_end": None,
                "time_raw": "",
                "location": "Reitanlage Blankenloch",
                "organizer": "Pferdefreunde Blankenloch 1972 e.V.",
                "description": "",
                "event_url": url,
            })
    return events


def scrape_schuetzenverein_blankenloch():
    """IONOS MyWebsite — parse h2 headers + date text on /termine."""
    url = "https://www.schuetzenverein-blankenloch-1913.de/termine/"
    try:
        html = fetch_url(url)
    except Exception:
        return []

    events = []
    blocks = re.findall(
        r'<div[^>]*class="n module-type-header diyfeLiveArea "[^>]*>.*?<h2>(.*?)</h2>.*?</div>\s*<div[^>]*class="n module-type-text diyfeLiveArea "[^>]*>(.*?)</div>',
        html, re.DOTALL
    )
    for title_html, body_html in blocks:
        title = strip_html(title_html)
        body_text = strip_html(body_html)

        dates_26 = re.findall(r'(\d{1,2})\.(\d{1,2})\.(\d{2})\b', body_text)
        dates_full = re.findall(r'(\d{1,2})\.(\d{1,2})\.(\d{4})', body_text)

        all_dates = []
        for d, m, y2 in dates_26:
            yy = int(y2)
            if yy == 26:
                all_dates.append((int(d), int(m), 2026))
        for d, m, y4 in dates_full:
            yyyy = int(y4)
            if yyyy in (2025, 2026, 2027):
                all_dates.append((int(d), int(m), yyyy))

        for d, m, y in all_dates:
            time_raw = ""
            time_m = re.search(
                r'(?:um|ab|von)\s*(\d{1,2})[:.](\d{2})\s*Uhr',
                body_text
            )
            if time_m:
                time_raw = f"{int(time_m.group(1)):02d}:{time_m.group(2)} Uhr"

            events.append({
                "title": title,
                "date_start": to_iso(d, m, y),
                "date_end": None,
                "time_raw": time_raw,
                "location": "Schützenhaus, Am Vogelpark 3, 76297 Stutensee",
                "organizer": "Schützenverein Blankenloch 1913 e.V.",
                "description": body_text[:200],
                "event_url": url,
            })

    return events


def scrape_sgsw():
    """WordPress blog posts with dates — match reports."""
    url = "https://sgsw.de/"
    try:
        html = fetch_url(url)
    except Exception:
        return []

    events = []
    articles = re.findall(
        r'<article[^>]*>(.*?)</article>',
        html, re.DOTALL
    )
    for art in articles:
        date_m = re.search(r'(\d{1,2})\.\s*(\w+)\s+(\d{4})', art)
        title_m = re.search(r'<h3>(.*?)</h3>', art)
        if not date_m or not title_m:
            continue
        day_str, month_str, year_str = date_m.group(1), date_m.group(2), date_m.group(3)
        month_map = {
            'Januar': 1, 'Februar': 2, 'März': 3, 'April': 4, 'Mai': 5, 'Juni': 6,
            'Juli': 7, 'August': 8, 'September': 9, 'Oktober': 10, 'November': 11, 'Dezember': 12,
        }
        month_num = month_map.get(month_str)
        if not month_num:
            continue
        year_int = int(year_str)
        if year_int < 2026 or year_int > 2027:
            continue

        title = strip_html(title_m.group(1))
        link_m = re.search(r'<a\s+href="([^"]+)"[^>]*>' + re.escape(title_m.group(1)) + r'</a>', art)
        event_url = link_m.group(1) if link_m else url

        events.append({
            "title": title,
            "date_start": to_iso(int(day_str), month_num, year_int),
            "date_end": None,
            "time_raw": "",
            "location": "",
            "organizer": "SG Stutensee-Weingarten",
            "description": "",
            "event_url": event_url,
        })
    return events


def scrape_theatergruppe_hoffmann():
    """IONOS site with dates in text on homepage and /veranstaltungen."""
    urls = [
        "https://www.theatergruppehoffmann.de/",
        "https://www.theatergruppehoffmann.de/veranstaltungen/",
    ]
    all_events = []
    seen = set()
    for url in urls:
        try:
            html = fetch_url(url)
        except Exception:
            continue
        text = strip_html(html)
        dates = re.findall(r'(\d{1,2})\.\s*und\s*(\d{1,2})\.(\d{1,2})\.(\d{4})', text)
        for d1, d2, m, y in dates:
            key = to_iso(int(d1), int(m), int(y))
            if key not in seen:
                seen.add(key)
                all_events.append({
                    "title": "Theateraufführung",
                    "date_start": key,
                    "date_end": to_iso(int(d2), int(m), int(y)),
                    "time_raw": "",
                    "location": "Festhalle Stutensee-Blankenloch",
                    "organizer": "Theatergruppe Hoffmann e.V.",
                    "description": "",
                    "event_url": url,
                })
        single = re.findall(r'(\d{1,2})\.(\d{1,2})\.(\d{4})', text)
        for d, m, y in single:
            key = to_iso(int(d), int(m), int(y))
            if key not in seen:
                seen.add(key)
                all_events.append({
                    "title": "Theateraufführung",
                    "date_start": key,
                    "date_end": None,
                    "time_raw": "",
                    "location": "Festhalle Stutensee-Blankenloch",
                    "organizer": "Theatergruppe Hoffmann e.V.",
                    "description": "",
                    "event_url": url,
                })
    return all_events


def scrape_tsg_blankenloch():
    """Custom CMS — parse news article blocks with dates on homepage."""
    url = "https://www.tsg-blankenloch.de/"
    try:
        html = fetch_url(url)
    except Exception:
        return []

    events = []
    articles = re.findall(
        r'<div[^>]*class="artikel"[^>]*>(.*?)</div>\s*</div>',
        html, re.DOTALL
    )
    for art in articles:
        h3_m = re.search(r'<h3[^>]*>(.*?)</h3>', art)
        date_m = re.search(r'(\d{1,2})\.(\d{1,2})\.(\d{4})', art)
        if not h3_m or not date_m:
            continue
        title = strip_html(h3_m.group(1))
        d, m, y = int(date_m.group(1)), int(date_m.group(2)), int(date_m.group(3))
        if y < 2025 or y > 2027:
            continue

        time_raw = ""
        time_m = re.search(r'(\d{1,2}):(\d{2})\s*Uhr', art)
        if time_m:
            time_raw = f"{int(time_m.group(1)):02d}:{time_m.group(2)} Uhr"

        link_m = re.search(r'<a\s+href="([^"]+)"', art)
        event_url = link_m.group(1) if link_m else url

        events.append({
            "title": title,
            "date_start": to_iso(d, m, y),
            "date_end": None,
            "time_raw": time_raw,
            "location": "TSG Blankenloch",
            "organizer": "Turn- und Sportgemeinschaft Blankenloch e.V.",
            "description": "",
            "event_url": event_url,
        })
    return events


def scrape_tv_friedrichstal():
    """Joomla — parse Veranstaltungskalender HTML table on homepage."""
    url = "https://www.tv-friedrichstal.de"
    try:
        html = fetch_url(url)
    except Exception:
        return []

    events = []
    table_m = re.search(
        r'<h3>Veranstaltungskalender 2026</h3>\s*<table[^>]*class="uk-table uk-table-striped"[^>]*>(.*?)</table>',
        html, re.DOTALL
    )
    if not table_m:
        table_m = re.search(
            r'Veranstaltungskalender 2026.*?<table[^>]*>(.*?)</table>',
            html, re.DOTALL
        )
    if not table_m:
        return []

    table_html = table_m.group(1)
    rows = re.findall(r'<tr>(.*?)</tr>', table_html, re.DOTALL)
    for row in rows:
        cells = re.findall(r'<t[dh][^>]*>(.*?)</t[dh]>', row, re.DOTALL)
        if len(cells) < 2:
            continue

        date_text = strip_html(cells[0])
        title = strip_html(cells[1])
        if not title:
            continue

        date_range_m = re.search(
            r'(\d{1,2})\.(\d{1,2})\.(\d{4})\s*[-–]\s*(\d{1,2})\.(\d{1,2})\.(\d{4})',
            date_text
        )
        time_raw = ""
        time_m = re.search(r'(\d{1,2}):(\d{2})\s*Uhr', title)
        if time_m:
            time_raw = f"{int(time_m.group(1)):02d}:{time_m.group(2)} Uhr"
            title = re.sub(r'\s*\d{1,2}:\d{2}\s*Uhr', '', title).strip()

        if date_range_m:
            start_d, start_m, start_y = date_range_m.group(1), date_range_m.group(2), date_range_m.group(3)
            end_d, end_m, end_y = date_range_m.group(4), date_range_m.group(5), date_range_m.group(6)
            events.append({
                "title": title,
                "date_start": to_iso(int(start_d), int(start_m), int(start_y)),
                "date_end": to_iso(int(end_d), int(end_m), int(end_y)),
                "time_raw": time_raw,
                "location": "TV Friedrichstal",
                "organizer": "Turnverein Friedrichstal 1899 e.V.",
                "description": "",
                "event_url": url,
            })
        else:
            date_m = re.search(r'(\d{1,2})\.(\d{1,2})\.(\d{4})', date_text)
            if not date_m:
                date_m = re.search(r'(\d{1,2})\.(\d{1,2})\.(\d{2})', date_text)
                if date_m:
                    y = "20" + date_m.group(3)
                    d, m = date_m.group(1), date_m.group(2)
                    events.append({
                        "title": title,
                        "date_start": to_iso(int(d), int(m), int(y)),
                        "date_end": None,
                        "time_raw": time_raw,
                        "location": "TV Friedrichstal",
                        "organizer": "Turnverein Friedrichstal 1899 e.V.",
                        "description": "",
                        "event_url": url,
                    })
            else:
                d, m, y = date_m.group(1), date_m.group(2), date_m.group(3)
                events.append({
                    "title": title,
                    "date_start": to_iso(int(d), int(m), int(y)),
                    "date_end": None,
                    "time_raw": time_raw,
                    "location": "TV Friedrichstal",
                    "organizer": "Turnverein Friedrichstal 1899 e.V.",
                    "description": "",
                    "event_url": url,
                })
    return events


def scrape_ttvbg_click_tt():
    """click-TT league site — no upcoming events found."""
    url = "https://ttvbw.click-tt.de/cgi-bin/WebObjects/nuLigaTTDE.woa/wa/clubInfoDisplay?club=27303"
    try:
        html = fetch_url(url)
    except Exception:
        return []
    return []


def scrape_ttf_spoeck():
    """Static HTML — single event listed."""
    url = "http://www.ttf-spoeck.de/"
    try:
        resp = urllib.request.urlopen(
            urllib.request.Request(url, headers={"User-Agent": "StutenseeEvents/1.0"}),
            timeout=30
        )
        html = resp.read().decode("utf-8", errors="replace")
    except Exception:
        return []

    events = []
    text = strip_html(html)

    date_m = re.search(r'den\s+(\d{1,2})\.\s*(\w+)', text)
    time_m = re.search(r'(\d{1,2}):(\d{2})\s*Uhr', text)

    if date_m:
        day_str, month_str = date_m.group(1), date_m.group(2)
        month_map = {
            'Januar': 1, 'Februar': 2, 'März': 3, 'April': 4, 'Mai': 5, 'Juni': 6,
            'Juli': 7, 'August': 8, 'September': 9, 'Oktober': 10,
            'November': 11, 'Dezember': 12,
        }
        month_num = month_map.get(month_str)
        if month_num:
            time_raw = ""
            if time_m:
                time_raw = f"{int(time_m.group(1)):02d}:{time_m.group(2)} Uhr"

            title = "2er Mannschaftsturnier"
            title_m = re.search(r'<h2>(.*?)</h2>', html)
            if title_m:
                title = strip_html(title_m.group(1))

            events.append({
                "title": title,
                "date_start": to_iso(int(day_str), month_num, 2026),
                "date_end": None,
                "time_raw": time_raw,
                "location": "Spechaahalle, Stutensee-Spöck",
                "organizer": "TTF Schwarz-Weiß Spöck 1954 e.V.",
                "description": "",
                "event_url": url,
            })
    return events


def scrape_clubs_p4():
    all_events = []

    sites = [
        ("Musikverein Blankenloch", scrape_musikverein_blankenloch),
        ("Pferdefreunde Blankenloch", scrape_pferdefreunde_blankenloch),
        ("Schützenverein Blankenloch", scrape_schuetzenverein_blankenloch),
        ("SG Stutensee-Weingarten", scrape_sgsw),
        ("Theatergruppe Hoffmann", scrape_theatergruppe_hoffmann),
        ("TSG Blankenloch", scrape_tsg_blankenloch),
        ("TV Friedrichstal", scrape_tv_friedrichstal),
        ("TTG Spöck (click-TT)", scrape_ttvbg_click_tt),
        ("TTF Spöck", scrape_ttf_spoeck),
    ]

    for name, func in sites:
        try:
            events = func()
            all_events.extend(events)
            sys.stderr.write(f"  {name}: {len(events)} events\n")
        except Exception as e:
            sys.stderr.write(f"  {name}: ERROR - {e}\n")

    return {"source_url": "clubs_batch4", "events": all_events}


def main():
    result = scrape_clubs_p4()
    result["events"] = [e for e in result["events"] if e["date_start"] >= "2026-01-01"]
    print(json.dumps(result, ensure_ascii=False, indent=2))
    sys.stderr.write(f"Total: {len(result['events'])} events\n")


if __name__ == '__main__':
    main()
