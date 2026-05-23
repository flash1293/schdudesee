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

import re

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
    import sys
    main()
