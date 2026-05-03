import re
from concurrent.futures import ThreadPoolExecutor, as_completed
import scraper_clubs_p1, scraper_clubs_p2, scraper_clubs_p3, scraper_clubs_p4

_SCRAPERS = [
    ("Batch 1 (clubs 1-10)", scraper_clubs_p1.scrape_clubs_p1),
    ("Batch 2 (clubs 11-20)", scraper_clubs_p2.scrape_clubs_p2),
    ("Batch 3 (clubs 21-30)", scraper_clubs_p3.scrape_clubs_p3),
    ("Batch 4 (clubs 31-39)", scraper_clubs_p4.scrape_clubs_p4),
]


def is_outside_stutensee(location, title):
    if not location:
        return False
    loc_lower = location.lower()
    outside = {"forbach", "karben", "immenhausen"}
    for place in outside:
        if place in loc_lower:
            return True
    return False


def is_bad_event(ev):
    title = (ev.get("title") or "").strip()
    if not title:
        return True
    if not ev.get("date_start"):
        return True
    if is_outside_stutensee(ev.get("location", ""), title):
        return True
    return False


def scrape_clubs():
    all_events = []
    with ThreadPoolExecutor(max_workers=4) as executor:
        futures = {executor.submit(fn): name for name, fn in _SCRAPERS}
        for future in as_completed(futures):
            try:
                result = future.result()
                for ev in result.get("events", []):
                    if not is_bad_event(ev):
                        all_events.append(ev)
            except Exception:
                pass
    return {"source_url": "clubs_batch_all", "events": all_events}
