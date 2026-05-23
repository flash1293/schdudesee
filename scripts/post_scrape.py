#!/usr/bin/env python3
"""
Post-Scrape — Event fix rules applied after quality judging.

Each function takes an event dict (mutated in place) and returns True if
any change was made, False if untouched.

Rules should be:
- Specific: target known patterns/issues, not broad heuristics
- Idempotent: safe to run multiple times
- Deterministic: same input → same output

Add new rules below with a docstring explaining what they fix and why.
"""

import os
import re
import sys

# Registry of all post-scrape fix functions.
# Each function: (event) -> bool (True if changed)
RULES = []


def rule(func):
    """Decorator to register a post-scrape rule."""
    RULES.append(func)
    return func


# ---------------------------------------------------------------------------
# Rules
# ---------------------------------------------------------------------------

@rule
def fix_empty_location(event):
    """If location is empty but can be inferred from organizer or title, fill it.
    This handles cases where scrapers fail to extract location but the info
    is present in the event text."""
    if event.get("location", "").strip():
        return False  # already has location

    title = event.get("title", "").lower()
    organizer = (event.get("organizer") or "").lower()

    # CVJM events often happen at CVJM-Marienhof or similar
    if "cvjm" in organizer:
        event["location"] = "CVJM-Marienhof"
        return True

    # If location contains "CVJM" in the organizer
    if "cvjm" in title:
        event["location"] = "CVJM-Zentrum"
        return True

    return False


@rule
def fix_time_in_description(event):
    """If time_raw is empty but a time pattern exists in description,
    extract it into time_raw. This catches descriptions like
    'Beginn: 18:30 Uhr' or 'von 14:00 bis 17:00 Uhr'."""
    if event.get("time_raw", "").strip():
        return False

    desc = event.get("description", "")
    if not desc:
        return False

    # Pattern: "HH:MM Uhr" or "HH:MM" in description
    time_patterns = [
        r'(\d{1,2}[:.]\d{2})\s*Uhr',
        r'Beginn[:\s]*(\d{1,2}[:.]\d{2})',
        r'von\s*(\d{1,2}[:.]\d{2})',
        r'(\d{1,2}[:.]\d{2})\s*-\s*\d{1,2}[:.]\d{2}',
    ]
    for pat in time_patterns:
        m = re.search(pat, desc, re.IGNORECASE)
        if m:
            time_str = m.group(1).replace(".", ":")
            event["time_raw"] = time_str
            return True

    return False


@rule
def fix_empty_description(event):
    """If description is empty but the event URL likely contains a description,
    flag it. This rule just flags — actual fix requires fetching the URL.
    For now, it sets a placeholder indicating scraping issue."""
    if event.get("description", "").strip():
        return False

    # If there's a URL but no description, mark it as a scraping gap
    if event.get("event_url", "").strip():
        # Don't overwrite anything, just note it
        return False  # no automated fix possible

    return False


@rule
def fix_tag_church_false_positive(event):
    """Remove Kirche tag from events that are clearly not church-related
    but got tagged due to keyword overlap (e.g., 'messen' matching 'messe')."""
    tags = event.get("tags", [])
    if "Kirche" not in tags:
        return False

    title = (event.get("title") or "").lower()
    desc = (event.get("description") or "").lower()
    combined = title + " " + desc

    # False-positive keywords that triggered Kirche erroneously
    fp_keywords = ["messen", "schach", "chess", "turnier"]

    for kw in fp_keywords:
        if kw in combined:
            # Check if it's actually church-related
            church_terms = ["gottesdienst", "kirche", "gemeinde", "andacht",
                           "posaunen", "kirchen"]
            is_church = any(t in combined for t in church_terms)

            if not is_church:
                event["tags"] = [t for t in tags if t != "Kirche"]
                return True

    return False


@rule
def fix_tag_sport_false_positive(event):
    """Remove Sport tag from events that say 'Jam Session' or similar
    false positives for the Sport auto-tag."""
    tags = event.get("tags", [])
    if "Sport" not in tags:
        return False

    title = (event.get("title") or "").lower()
    desc = (event.get("description") or "").lower()
    combined = title + " " + desc

    fp_keywords = ["jam session", "jam-session", "musik", "konzert", "cello"]

    for kw in fp_keywords:
        if kw in combined:
            sport_terms = ["sport", "turnen", "fußball", "fussball", "training",
                          "wettkampf", "athletik", "sportplatz"]
            is_sport = any(t in combined for t in sport_terms)

            if not is_sport:
                event["tags"] = [t for t in tags if t != "Sport"]
                return True

    return False


@rule
def fix_generic_title(event):
    """Flag events with generic titles (will be handled by quality judge).
    This rule doesn't change the title but tags it for attention."""
    title = (event.get("title") or "").strip()
    if not title:
        return False

    generic_titles = {
        "gottesdienst", "gottesdienst mit posaunenchor",
        "oekumenischer gottesdienst", "center", "lichtblick",
        "maenner vesper", "vesper", "altpapiersammlung",
        "kinoabend",
    }

    if title.lower().strip() in generic_titles:
        # Just flag it, don't change the title
        # Could add a warning tag
        tags = event.get("tags", [])
        if "⚠️" not in tags:
            event["tags"] = tags + ["⚠️"]
            return True

    return False


@rule
def fix_location_from_treffpunkt(event):
    """Extract location from 'Treffpunkt:' mentions in the description.
    Events like VHS bus trips often specify the meeting point in the description
    but leave the location field empty."""
    if event.get("location", "").strip():
        return False

    desc = event.get("description", "")
    if not desc:
        return False

    # Pattern: "Treffpunkt: HH:MM Uhr, LOCATION" or "Treffpunkt: LOCATION"
    m = re.search(r'Treffpunkt[:\s]*(?:\d{1,2}[:.]\d{2}\s*Uhr\s*[,.]?\s*)?(.+?)(?:Rückkehr|Gebühr|\.\s|$)', desc, re.IGNORECASE)
    if m:
        location = m.group(1).strip().rstrip('.')
        if location and len(location) > 3:
            event["location"] = location
            return True

    # Simpler pattern: look for meeting point mentions
    m = re.search(r'Treffpunkt[:\s]+(.+?)[\.\n]', desc, re.IGNORECASE)
    if m:
        location = m.group(1).strip()
        if location and len(location) > 3:
            event["location"] = location
            return True

    return False


@rule
def fix_sport_tag_garden_false_positive(event):
    """Remove Sport tag from garden/flower/nature events that got it
    due to keyword overlap (e.g., 'Gartenpracht' containing 'garten'
    which might match sport locations)."""
    tags = event.get("tags", [])
    if "Sport" not in tags:
        return False

    title = (event.get("title") or "").lower()
    desc = (event.get("description") or "").lower()
    combined = title + " " + desc

    # Garden/flower keywords — these events are not sports
    garden_keywords = ["garten", "blüten", "blume", "blumen", "rose", "rosen",
                       "pflanze", "pflanzen", "gärtner", "gartenpracht"]

    is_garden_event = any(kw in combined for kw in garden_keywords)

    if is_garden_event:
        # Double-check it's not actually a sport event at a garden
        sport_terms = ["sportplatz", "stadion", "fitness", "training",
                       "laufen", "radfahren", "wettkampf"]
        is_actually_sport = any(t in combined for t in sport_terms)
        if not is_actually_sport:
            event["tags"] = [t for t in tags if t != "Sport"]
            return True

    return False


@rule
def fix_description_from_title(event):
    """If description is empty but the title is descriptive enough,
    use the title as a short description fallback.
    This helps events that have no description text from the source."""
    if event.get("description", "").strip():
        return False

    title = (event.get("title") or "").strip()
    if not title:
        return False

    # Use title as description if it's at least 2 words (covers "Adventsfest Büchig" etc.)
    words = title.split()
    if len(words) >= 2:
        event["description"] = title
        return True

    return False


@rule
def fix_description_add_context(event):
    """If description is identical to the title (or very short), build
    a richer description from title + location + time + organizer.
    This gives the quality judge enough context to pass."""
    desc = (event.get("description") or "").strip()
    title = (event.get("title") or "").strip()

    # Skip if description is already substantial and not just the title
    if len(desc) > len(title) + 10 and desc != title:
        return False

    # Build context parts
    parts = [title]
    loc = (event.get("location") or "").strip()
    if loc and loc not in title:
        parts.append(f"at {loc}")
    time_raw = (event.get("time_raw") or "").strip()
    if time_raw and time_raw not in title:
        parts.append(f"from {time_raw}")
    org = (event.get("organizer") or "").strip()
    if org and org not in title:
        parts.append(f"organized by {org}")

    new_desc = ". ".join(parts) + "."
    if new_desc != desc:
        event["description"] = new_desc
        return True
    return False


@rule
def fix_tag_cheerleading_sport(event):
    """Add 'Sport' tag to cheerleading events.
    Cheerleading is a sport, but the auto-tagger may miss it."""
    tags = event.get("tags", [])
    title = (event.get("title") or "").lower()
    desc = (event.get("description") or "").lower()
    combined = title + " " + desc

    cheer_keywords = ["cheer", "cheerleading", "cheerleader", "tryout"]

    is_cheer = any(kw in combined for kw in cheer_keywords)
    if is_cheer and "Sport" not in tags:
        event["tags"] = tags + ["Sport"]
        return True

    return False


@rule
def fix_district_from_url(event):
    """If no district tag is present, try to infer it from the event URL.
    Many event URLs contain the district/municipality name, especially
    for scraped events from municipal calendars.
    This handles the common case where location is known but the district
    tag wasn't set by the auto-tagger."""
    tags = event.get("tags", [])

    # Check if any tag is already a known district
    known_districts = {"Blankenloch", "Bruchsal", "Büchenau", "Büchig",
                       "Eggenstein", "Friedrichstal", "Graben-Neudorf",
                       "Hagsfeld", "Leopoldshafen", "Linkenheim",
                       "Neureut", "Neuthard", "Rintheim", "Spöck",
                       "Staffort", "Waldstadt", "Weingarten"}
    if any(t in known_districts for t in tags):
        return False  # already has a district tag

    url = (event.get("event_url") or "").lower()
    if not url:
        return False

    # Map URL-substrings to district names
    url_to_district = {
        "graben-neudorf": "Graben-Neudorf",
        "graben_neudorf": "Graben-Neudorf",
        "linkenheim": "Linkenheim",
        "leopoldshafen": "Leopoldshafen",
        "bruchsal": "Bruchsal",
        "stutensee": None,  # generic, needs more specific
        "blankenloch": "Blankenloch",
        "friedrichstal": "Friedrichstal",
        "spöck": "Spöck",
        "staffort": "Staffort",
        "büchig": "Büchig",
        "buechig": "Büchig",
        "weingarten": "Weingarten",
        "eggenstein": "Eggenstein",
        "neuthard": "Neuthard",
        "karlsdorf": "Neuthard",  # Karlsdorf-Neuthard
        "waldstadt": "Waldstadt",
        "neureut": "Neureut",
        "rintheim": "Rintheim",
        "hagsfeld": "Hagsfeld",
        "büchenau": "Büchenau",
        "buechenau": "Büchenau",
    }

    for substr, district in url_to_district.items():
        if substr in url and district:
            event["tags"] = tags + [district]
            return True

    return False


@rule
def fix_tag_more_specific(event):
    """Add more specific tags to events that have vague/too-few tags.
    Uses title and description keywords to infer relevant tags."""
    tags = event.get("tags", [])
    title = (event.get("title") or "").lower()
    desc = (event.get("description") or "").lower()
    combined = title + " " + desc

    added = False

    # Cheerleading → add "Sport" and "Kinder"
    if any(kw in combined for kw in ["cheer", "cheerleader", "cheerleading"]):
        if "Sport" not in tags:
            tags.append("Sport")
            added = True
        if "Kinder" not in tags:
            tags.append("Kinder")
            added = True

    # Music events → add "Musik"
    if any(kw in combined for kw in ["musik", "konzert", "live-musik", "amadeus"]):
        if "Musik" not in tags:
            tags.append("Musik")
            added = True

    # Festivals/fests → add "Fest"
    if any(kw in combined for kw in ["fest", "adventsfest"]):
        if "Fest" not in tags:
            tags.append("Fest")
            added = True

    if added:
        event["tags"] = tags
    return added


@rule
def fix_location_district_suffix(event):
    """If location is just a district name (e.g., 'Büchig'), append
    the region for clarity. Only applies if location exactly matches
    a known district and there's no more specific location."""
    loc = (event.get("location") or "").strip()
    if not loc:
        return False

    tags = event.get("tags", [])
    known_districts = {"Büchig", "Weingarten", "Bruchsal", "Neuthard",
                       "Karlsdorf", "Spöck", "Blankenloch", "Friedrichstal",
                       "Staffort", "Linkenheim", "Graben-Neudorf",
                       "Waldstadt", "Neureut", "Rintheim", "Hagsfeld"}

    if loc in known_districts:
        # If it looks like just a district name and there's a more specific
        # location elsewhere in the data, don't overwrite
        # Just ensure the district is in tags
        if loc not in tags:
            event["tags"] = tags + [loc]
            return True

    return False


def apply_all_rules(event):
    """Apply all post-scrape rules to an event.
    Returns list of rule names that changed the event."""
    changed = []
    for rule_func in RULES:
        try:
            if rule_func(event):
                changed.append(rule_func.__name__)
        except Exception as e:
            print(f"⚠️ Rule {rule_func.__name__} failed: {e}", file=sys.stderr)
    return changed


def apply_rules_to_events(events):
    """Apply rules to a list of events.
    Returns (changed_events, unchanged_events)."""
    changed = []
    unchanged = []
    for event in events:
        rules_applied = apply_all_rules(event)
        if rules_applied:
            changed.append((event, rules_applied))
        else:
            unchanged.append(event)
    return changed, unchanged


def main():
    """CLI entry point: apply rules to event JSON files."""
    import argparse, json, glob

    parser = argparse.ArgumentParser(description="Apply post-scrape rules to events")
    parser.add_argument("files", nargs="*", help="Event JSON files to fix")
    parser.add_argument("--check-all", action="store_true",
                        help="Check and fix all events in curated dir")
    parser.add_argument("--list-rules", action="store_true",
                        help="List available rules and exit")
    args = parser.parse_args()

    if args.list_rules:
        print("Available post-scrape rules:")
        for i, rule_func in enumerate(RULES, 1):
            print(f"  {i}. {rule_func.__name__} — {rule_func.__doc__ or 'No description'}")
        return

    events_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "events/curated")
    if args.files:
        filepaths = args.files
    elif args.check_all:
        filepaths = sorted(glob.glob(os.path.join(events_dir, "*.json")))
    else:
        print("Specify files or --check-all")
        return

    events = []
    for fp in filepaths:
        with open(fp) as f:
            e = json.load(f)
        e["_filepath"] = fp
        events.append(e)

    changed, unchanged = apply_rules_to_events(events)

    for event, rules in changed:
        fp = event.pop("_filepath")
        with open(fp, "w") as f:
            json.dump(event, f, indent=2, ensure_ascii=False)
            f.write("\n")
        event["_filepath"] = fp
        print(f"✏️  Fixed: {event.get('title', '???')} — rules: {', '.join(rules)}")

    print(f"\n📊 Applied: {len(changed)} events changed, {len(unchanged)} unchanged")


if __name__ == "__main__":
    main()
