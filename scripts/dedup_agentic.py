#!/usr/bin/env python3
"""
Agentic deduplication for Stutensee events database.
Two-phase: same-source exact-date dedup, then cross-source fuzzy dedup.
"""

import json
import sqlite3
import re
from collections import defaultdict
from datetime import datetime

DB_PATH = "/Users/joereuter/Clones/schdudesee/stutensee_events.db"


def connect():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def fetch_all_events(conn):
    cur = conn.execute("""
        SELECT id, title, date_start, date_end, time_raw, location, organizer,
               description, event_url, sources, tags, dedup_round
        FROM curated_events
        ORDER BY id
    """)
    return [dict(row) for row in cur.fetchall()]


def fetch_raw_ids(conn, curated_id):
    rows = conn.execute(
        "SELECT raw_id FROM raw_to_curated WHERE curated_id = ?", (curated_id,)
    ).fetchall()
    return [r["raw_id"] for r in rows]


def normalize_date(date_str):
    if not date_str or date_str.strip() == "":
        return None
    date_str = date_str.strip()
    date_str = re.sub(r'T\d*$', '', date_str).strip()
    for fmt in ("%Y-%m-%d",):
        try:
            return datetime.strptime(date_str, fmt).date()
        except ValueError:
            continue
    try:
        parts = [int(p) for p in date_str.split("-") if p]
        if len(parts) == 3:
            return datetime(parts[0], parts[1], parts[2]).date()
    except (ValueError, IndexError):
        return None
    return None


def is_date_close(d1, d2):
    if d1 is None or d2 is None:
        return False
    return abs((d1 - d2).days) <= 1


def levenshtein_ratio(s1, s2):
    if not s1 or not s2:
        return 0
    s1, s2 = s1.lower().strip(), s2.lower().strip()
    if len(s1) < len(s2):
        s1, s2 = s2, s1
    if len(s2) == 0:
        return 1.0 if len(s1) == 0 else 0.0
    prev_row = list(range(len(s2) + 1))
    for i, c1 in enumerate(s1):
        curr_row = [i + 1]
        for j, c2 in enumerate(s2):
            cost = 0 if c1 == c2 else 1
            curr_row.append(min(curr_row[-1] + 1, prev_row[j + 1] + 1, prev_row[j] + cost))
        prev_row = curr_row
    dist = prev_row[-1]
    max_len = max(len(s1), len(s2))
    return 1.0 - (dist / max_len)


def bigram_dice(s1, s2):
    grams1 = set(s1[i:i+2] for i in range(len(s1)-1))
    grams2 = set(s2[i:i+2] for i in range(len(s2)-1))
    if not grams1 or not grams2:
        return 0.0
    intersection = grams1 & grams2
    return 2.0 * len(intersection) / (len(grams1) + len(grams2))


def titles_similar(t1, t2):
    t1, t2 = t1.lower().strip(), t2.lower().strip()
    if t1 == t2:
        return True
    if t1 in t2 or t2 in t1:
        return True
    if levenshtein_ratio(t1, t2) >= 0.60:
        return True
    if bigram_dice(t1, t2) >= 0.60:
        return True
    return False


def normalize_location(loc):
    if not loc or loc.strip() == "":
        return ""
    loc = loc.strip().split(",")[0].strip()
    loc = re.sub(r'\s+\d{5}\s*.*$', '', loc)
    loc = re.sub(r'\b\d{5}\b', '', loc).strip().lower()
    loc = re.sub(r'[^a-zäöüß\s.-]', '', loc)
    loc = re.sub(r'\s+', ' ', loc).strip()
    return loc


def locations_match(l1, l2):
    n1, n2 = normalize_location(l1), normalize_location(l2)
    if not n1 or not n2:
        return None
    if len(n1) <= 2 or len(n2) <= 2:
        return n1 == n2
    if n1 in n2 or n2 in n1:
        return True
    return levenshtein_ratio(n1, n2) >= 0.55


def source_key(url):
    if not url:
        return ""
    for domain in [
        "meinstutensee.de", "stutensee.de", "stutenseekinderkalender.de",
        "buergerwerkstatt-stutensee.de", "bibliotheken.komm.one",
        "friedrichstal.org", "fcfriedrichstal.de", "fcspoeck.de",
        "flohmarkt-buechig.de", "kath-stutensee-weingarten.de",
        "tsg-blankenloch.de"
    ]:
        if domain in url:
            return domain
    return url


def pick_best_title(titles):
    valid = [t.strip() for t in titles if t and t.strip()]
    return min(valid, key=lambda t: (len(t), t)) if valid else titles[0]


def merge_events(group, conn, dedup_round=2):
    group.sort(key=lambda e: e["id"])
    keep = group[0]
    delete = group[1:]

    best_location = ""
    for e in group:
        loc = (e.get("location") or "").strip()
        if loc and len(loc) > len(best_location):
            best_location = loc

    best_title = pick_best_title([e["title"] for e in group])

    all_sources = []
    all_raw_ids = []
    for e in group:
        s = e.get("sources", "").strip()
        if s:
            for src in re.split(r'[,;]\s*', s):
                src = src.strip()
                if src and src not in all_sources:
                    all_sources.append(src)
        for rid in fetch_raw_ids(conn, e["id"]):
            if rid not in all_raw_ids:
                all_raw_ids.append(rid)

    descriptions = [(e.get("description") or "").strip() for e in group]
    descriptions = [d for d in descriptions if d]
    best_desc = max(descriptions, key=len) if descriptions else ""

    conn.execute(
        """UPDATE curated_events
           SET title = ?, description = ?, sources = ?, location = ?,
               updated_at = datetime('now')
           WHERE id = ?""",
        (best_title, best_desc, ", ".join(all_sources), best_location, keep["id"])
    )

    for rid in all_raw_ids:
        conn.execute(
            "INSERT OR IGNORE INTO raw_to_curated (raw_id, curated_id, dedup_round) VALUES (?, ?, ?)",
            (rid, keep["id"], dedup_round)
        )

    for e in delete:
        conn.execute("DELETE FROM raw_to_curated WHERE curated_id = ?", (e["id"],))
        conn.execute("DELETE FROM curated_events WHERE id = ?", (e["id"],))

    return keep["id"], [e["id"] for e in delete]


def run_same_source_dedup(conn, events):
    by_date = defaultdict(list)
    for i, e in enumerate(events):
        d = normalize_date(e["date_start"])
        if d:
            by_date[d].append(i)

    groups = []
    for date, indices in by_date.items():
        buckets = defaultdict(list)
        for idx in indices:
            e = events[idx]
            buckets[(source_key(e["sources"]), e["title"].lower().strip())].append(idx)

        for key, grp in buckets.items():
            if len(grp) < 2:
                continue
            grp_events = [events[i] for i in grp]

            grp_events.sort(key=lambda e: e["id"])

            def same_location_subgroups(group):
                subs = []
                remaining = list(group)
                while remaining:
                    sub = [remaining[0]]
                    remaining = remaining[1:]
                    for other in list(remaining):
                        lm = locations_match(
                            sub[0].get("location", ""),
                            other.get("location", "")
                        )
                        if lm is not False:
                            sub.append(other)
                            remaining.remove(other)
                    subs.append(sub)
                return [s for s in subs if len(s) > 1]

            subs = same_location_subgroups(grp_events)
            groups.extend(subs)

    merged = 0
    deleted = 0
    for g in groups:
        keep_id, delete_ids = merge_events(g, conn, dedup_round=2)
        merged += 1
        deleted += len(delete_ids)
        print(f"  Same-source: IDs {[e['id'] for e in g]} -> keep {keep_id} '{g[0]['title']}'")
    return merged, deleted


def run_cross_source_dedup(conn, events):
    for e in events:
        e["_parsed_date"] = normalize_date(e["date_start"])

    date_buckets = defaultdict(list)
    for i, e in enumerate(events):
        if e["_parsed_date"]:
            date_buckets[e["_parsed_date"]].append(i)

    sorted_dates = sorted(date_buckets.keys())
    adjacency = defaultdict(set)

    def compare(indices):
        for ii in range(len(indices)):
            for jj in range(ii + 1, len(indices)):
                a, b = indices[ii], indices[jj]
                ea, eb = events[a], events[b]
                sk_a, sk_b = source_key(ea["sources"]), source_key(eb["sources"])
                if sk_a == sk_b and sk_a != "":
                    continue

                if not is_date_close(ea["_parsed_date"], eb["_parsed_date"]):
                    continue
                if not titles_similar(ea["title"], eb["title"]):
                    continue

                loc_a = (ea.get("location") or "").strip()
                loc_b = (eb.get("location") or "").strip()
                loc_match = locations_match(loc_a, loc_b)

                if loc_match is None:
                    if ea["title"].lower().strip() != eb["title"].lower().strip():
                        continue
                elif loc_match is False:
                    continue

                adjacency[a].add(b)
                adjacency[b].add(a)

    for date in sorted_dates:
        compare(date_buckets[date])

    for k in range(len(sorted_dates) - 1):
        curr, nxt = sorted_dates[k], sorted_dates[k + 1]
        if (nxt - curr).days == 1:
            if len(date_buckets[curr]) <= 50 and len(date_buckets[nxt]) <= 50:
                for ci in date_buckets[curr]:
                    for ni in date_buckets[nxt]:
                        ea, eb = events[ci], events[ni]
                        sk_a, sk_b = source_key(ea["sources"]), source_key(eb["sources"])
                        if sk_a == sk_b and sk_a != "":
                            continue
                        if not titles_similar(ea["title"], eb["title"]):
                            continue
                        loc_a = (ea.get("location") or "").strip()
                        loc_b = (eb.get("location") or "").strip()
                        lm = locations_match(loc_a, loc_b)
                        if lm is None:
                            if ea["title"].lower().strip() != eb["title"].lower().strip():
                                continue
                        elif lm is False:
                            continue
                        adjacency[ci].add(ni)
                        adjacency[ni].add(ci)

    visited = set()
    groups = []
    for i in range(len(events)):
        if i in visited:
            continue
        stack = [i]
        g = []
        while stack:
            v = stack.pop()
            if v in visited:
                continue
            visited.add(v)
            g.append(v)
            for nb in adjacency[v]:
                if nb not in visited:
                    stack.append(nb)
        if len(g) > 1:
            groups.append([events[idx] for idx in g])

    merged = 0
    deleted = 0
    for g in groups:
        keep_id, delete_ids = merge_events(g, conn, dedup_round=2)
        merged += 1
        deleted += len(delete_ids)
        sources = set()
        for e in g:
            for s in re.split(r'[,;]\s*', (e.get("sources") or "").strip()):
                if s:
                    sources.add(s)
        print(f"  Cross-source: IDs {[e['id'] for e in g]} -> keep {keep_id} '{g[0]['title']}' [{', '.join(sorted(sources))}]")
    return merged, deleted


def main():
    conn = connect()

    events = fetch_all_events(conn)
    print(f"Total events: {len(events)}")

    all_deleted = 0

    print("\n=== Phase 1: Same-source dedup ===")
    m1, d1 = run_same_source_dedup(conn, events)
    all_deleted += d1

    events = fetch_all_events(conn)
    print(f"\nAfter phase 1: {len(events)} events remaining")

    print("\n=== Phase 2: Cross-source dedup ===")
    m2, d2 = run_cross_source_dedup(conn, events)
    all_deleted += d2

    conn.commit()
    conn.close()

    print(f"\n{'='*50}")
    print(f"STATS:")
    print(f"  Same-source groups merged: {m1}")
    print(f"  Cross-source groups merged: {m2}")
    print(f"  Total duplicates deleted: {all_deleted}")
    print(f"  Final event count (approx): {6191 - all_deleted}")
    print(f"{'='*50}")


if __name__ == "__main__":
    main()
