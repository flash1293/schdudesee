#!/usr/bin/env python3
"""Clean up event descriptions in curated_events table."""

import html
import re
import sqlite3

DB = "/Users/joereuter/Clones/schdudesee/stutensee_events.db"

conn = sqlite3.connect(DB)
conn.row_factory = sqlite3.Row
cur = conn.cursor()

cur.execute("SELECT id, title, normalized_title, description, date_start, sources FROM curated_events ORDER BY id")
rows = cur.fetchall()

stats = {
    "total": len(rows),
    "html_entities_decoded": 0,
    "html_tags_stripped": 0,
    "whitespace_normalized": 0,
    "empty_before": 0,
    "short_before": 0,
    "filled_from_sibling": 0,
    "scrap_garbage_removed": 0,
    "changed": 0,
    "unchanged": 0,
    "errors": 0,
}

# Build lookup by normalized_title
by_normalized = {}
# Also build lookup by exact title for when normalized_title is NULL
by_title = {}
for row in rows:
    nt = row["normalized_title"]
    if nt:
        by_normalized.setdefault(nt, []).append({
            "id": row["id"],
            "description": row["description"] or "",
        })
    t = row["title"]
    if t:
        by_title.setdefault(t, []).append({
            "id": row["id"],
            "normalized_title": row["normalized_title"],
            "description": row["description"] or "",
        })

def find_best_sibling(rid, candidates):
    best = None
    for sib in candidates:
        if sib["id"] == rid:
            continue
        sd = (sib["description"] or "").strip()
        if len(sd) >= 20:
            if best is None or len(sd) > len(best):
                best = sd
    return best

updates = []
for row in rows:
    rid = row["id"]
    title = row["title"]
    desc = row["description"] or ""

    orig = desc

    stripped_before = desc.strip()
    if not stripped_before:
        stats["empty_before"] += 1
    elif len(stripped_before) < 20:
        stats["short_before"] += 1

    # Decode HTML entities
    if "&" in desc and ";" in desc:
        decoded = html.unescape(desc)
        if decoded != desc:
            desc = decoded
            stats["html_entities_decoded"] += 1

    # Strip HTML tags
    stripped_tags = re.sub(r"<[^>]*>", "", desc)
    if stripped_tags != desc:
        desc = stripped_tags
        stats["html_tags_stripped"] += 1

    # Normalize whitespace
    desc = desc.replace("\u00a0", " ").replace("\u200b", "").replace("\u2009", " ")
    before_ws = desc
    desc = re.sub(r"[ \t]+", " ", desc)
    desc = re.sub(r"\n\s*\n", "\n", desc)
    desc = re.sub(r"\n+", "\n", desc)
    desc = desc.strip()
    if desc != before_ws:
        stats["whitespace_normalized"] += 1

    # Remove scraped CSS/tailwind garbage — common patterns from web scraping
    # Pattern 1: *]:pointer-events-auto scroll-mt-[calc(... )]" ... data-turn="..."
    # Pattern 2: remaining calc fragments like +min(200px,max(70px,20svh)))>
    desc = re.sub(
        r"\*?\](?:\s*:\s*[-a-zA-Z0-9_]+)*[-a-zA-Z0-9_=\"'\[\]\(\)+,\.#% \t]*?(?:scroll-mt-|dir=|tabindex|data-|data-testid|data-scroll-anchor|data-turn)[-a-zA-Z0-9_=\"'\[\]\(\)+,\.#% \t]*",
        "",
        desc,
    )
    desc = re.sub(
        r"\+min\([^)]+\)\)\)\s*>",
        "",
        desc,
    )
    # Remove any remaining standalone CSS calc-like fragments
    desc = re.sub(
        r"calc\([^)]*\)",
        "",
        desc,
    )
    # Remove leading/trailing garbage like "|" or extra whitespace artifacts
    desc = desc.strip().lstrip("|").strip()
    # Collapse multiple spaces again
    desc = re.sub(r"\s{2,}", " ", desc).strip()
    if desc != before_ws and desc != orig:
        stats["scrap_garbage_removed"] += 1

    # If description is empty or very short, try to fill from sibling
    nt = row["normalized_title"]
    if len(desc) < 20:
        best = None
        # Try matching by normalized_title first
        if nt and nt in by_normalized:
            best = find_best_sibling(rid, by_normalized[nt])
        # If no match, try matching by exact title
        if not best and title and title in by_title:
            best = find_best_sibling(rid, by_title[title])
        if best:
            desc = best
            stats["filled_from_sibling"] += 1

    if desc != orig:
        stats["changed"] += 1
        updates.append((desc, rid))
    else:
        stats["unchanged"] += 1

cur.executemany(
    "UPDATE curated_events SET description = ?, updated_at = datetime('now') WHERE id = ?",
    updates,
)
conn.commit()
conn.close()

print("=" * 60)
print("DESCRIPTION CLEANUP STATS")
print("=" * 60)
print(f"Total events processed:     {stats['total']}")
print(f"HTML entities decoded:      {stats['html_entities_decoded']}")
print(f"HTML tags stripped:         {stats['html_tags_stripped']}")
print(f"Whitespace normalized:      {stats['whitespace_normalized']}")
print(f"Scrap garbage removed:      {stats['scrap_garbage_removed']}")
print(f"Empty descriptions before:  {stats['empty_before']}")
print(f"Short descriptions before:  {stats['short_before']}")
print(f"Filled from sibling:        {stats['filled_from_sibling']}")
print(f"Descriptions changed:       {stats['changed']}")
print(f"Descriptions unchanged:     {stats['unchanged']}")
print(f"Errors:                     {stats['errors']}")

if updates:
    print(f"\nSample updates:")
    for desc, rid in updates[:5]:
        print(f"  ID {rid}: {desc[:120]}...")
