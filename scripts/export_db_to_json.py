#!/usr/bin/env python3
"""
Export stutensee_events.db curated events to events/curated/*.json
One file per event, matching the EXACT format and filename scheme
used by scrape_and_merge.py.
"""

import json, os, re, sqlite3
from collections import defaultdict


DB = "/shared/work/stutensee_events.db"
OUT_DIR = "/shared/work/events/curated"


def slugify(title, max_len=60):
    """Must match scrape_and_merge.py exactly."""
    s = title.lower().strip()
    s = s.replace('\u00e4', 'ae').replace('\u00f6', 'oe').replace('\u00fc', 'ue').replace('\u00df', 'ss')
    s = re.sub(r'[^a-z0-9\s-]', '', s)
    s = re.sub(r'[\s-]+', '-', s).strip('-')
    if len(s) > max_len:
        s = s[:max_len].rstrip('-')
    return s or "event"


def build_filename(event):
    """Must match scrape_and_merge.py exactly."""
    date = event.get("date_start", "unknown") or "unknown"
    slug = slugify(event.get("title", "event"))
    return f"{date}_{slug}.json"


def write_event_json(event, out_dir, existing_filenames=None):
    """Must match scrape_and_merge.py's write_event_json exactly."""
    os.makedirs(out_dir, exist_ok=True)

    sources = event.get("sources", []) or []
    if isinstance(sources, str):
        sources = [s.strip() for s in sources.split(",") if s.strip()]

    tags = event.get("tags", []) or []
    if isinstance(tags, str):
        tags = [t.strip() for t in tags.split(",") if t.strip()]

    ev = {
        "title": event.get("title", ""),
        "date_start": event.get("date_start", ""),
        "date_end": event.get("date_end"),
        "time_raw": event.get("time_raw", ""),
        "location": event.get("location", ""),
        "organizer": event.get("organizer", ""),
        "description": event.get("description", ""),
        "event_url": event.get("event_url", ""),
        "sources": sources,
        "tags": tags,
        "recurring_group_id": event.get("recurring_group_id"),
    }

    filename = build_filename(ev)
    
    # Handle duplicate filenames
    if existing_filenames is not None:
        base, ext = os.path.splitext(filename)
        counter = 1
        while filename in existing_filenames:
            filename = f"{base}_{counter}{ext}"
            counter += 1
        existing_filenames.add(filename)
    
    filepath = os.path.join(out_dir, filename)
    new_content = json.dumps(ev, indent=2, ensure_ascii=False) + "\n"

    # Only write if content differs (to avoid unnecessary diffs)
    if os.path.exists(filepath):
        with open(filepath, "r", encoding="utf-8") as f:
            if f.read() == new_content:
                return filename

    with open(filepath, "w", encoding="utf-8") as f:
        f.write(new_content)

    return filename


def main():
    os.makedirs(OUT_DIR, exist_ok=True)

    conn = sqlite3.connect(DB)
    conn.row_factory = sqlite3.Row
    rows = conn.execute("SELECT * FROM curated_events ORDER BY date_start, title").fetchall()
    conn.close()

    print(f"Exporting {len(rows)} curated events from DB to {OUT_DIR}/")

    # Build lookup of existing files (before we modify anything)
    existing = set()
    if os.path.isdir(OUT_DIR):
        existing = set(os.listdir(OUT_DIR))

    written = set()
    existing_filenames = set()
    for row in rows:
        ev = dict(row)
        filename = write_event_json(ev, OUT_DIR, existing_filenames)
        written.add(filename)

    # Remove stale files (.json only) that are no longer in the DB
    stale = existing - written
    stale_json = {f for f in stale if f.endswith('.json')}
    for f in sorted(stale_json):
        filepath = os.path.join(OUT_DIR, f)
        if os.path.exists(filepath):
            os.remove(filepath)

    final_count = len([f for f in os.listdir(OUT_DIR) if f.endswith('.json')])

    print(f"Wrote {len(written)} JSON files")
    if stale_json:
        print(f"Removed {len(stale_json)} stale files")
    print(f"Final JSON file count: {final_count}")
    print(f"DB curated count: {len(rows)}")
    
    if final_count == len(rows):
        print("✅ JSON files in sync with DB!")
    else:
        print(f"⚠️ Mismatch: {final_count} files vs {len(rows)} DB events")


if __name__ == "__main__":
    main()
