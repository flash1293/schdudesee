import json, re, sys
from datetime import datetime

def normalize_title(title):
    if not title:
        return ""
    t = title.lower().strip()
    t = re.sub(r'\s*[-–—]\s*(?:ev\.?|e\.v\.?|eV)\s*$', '', t)
    t = re.sub(r'\s*[-–—]\s*(?:e\.v\.?|eV)\s*', '', t)
    t = re.sub(r'\s*\(.*?\)\s*', ' ', t)
    t = re.sub(r'[&]', ' und ', t)
    t = re.sub(r'[^\w\s]', ' ', t)
    t = re.sub(r'\s+', ' ', t).strip()
    return t

def load_batch(filepath):
    with open(filepath) as f:
        return json.load(f)["events"]

def dedup(events):
    groups = {}
    for ev in events:
        norm = normalize_title(ev.get("title", ""))
        date = ev.get("date_start", "")
        key = (norm, date)
        if key not in groups:
            groups[key] = []
        groups[key].append(ev)

    result = []
    for (norm, date), group in groups.items():
        if not norm:
            continue
        best = max(group, key=lambda e: len(e.get("description", "") or ""))
        sources = list(set(e.get("source_url", "") for e in group if e.get("source_url")))
        raw_ids = [e["id"] for e in group if "id" in e]

        result.append({
            "title": best.get("title", ""),
            "normalized_title": norm,
            "date_start": best.get("date_start", ""),
            "date_end": best.get("date_end", ""),
            "time_raw": best.get("time_raw", ""),
            "location": max((e.get("location", "") for e in group if e.get("location")), key=len, default=""),
            "organizer": "; ".join(set(e.get("organizer", "") for e in group if e.get("organizer"))),
            "description": best.get("description", ""),
            "event_url": best.get("event_url", ""),
            "sources": ", ".join(sources),
            "raw_ids": raw_ids,
        })
    return result

if __name__ == "__main__":
    files = sys.argv[1:]
    all_events = []
    for f in files:
        all_events.extend(load_batch(f))
    print(f"Loaded {len(all_events)} events from {len(files)} files", file=sys.stderr)
    curated = dedup(all_events)
    print(f"Deduped to {len(curated)} events", file=sys.stderr)
    out = {"dedup_round": 1, "events": curated}
    print(json.dumps(out, ensure_ascii=False))
