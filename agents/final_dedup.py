"""
Final dedup pass: merge remaining date-format duplicates and cross-source duplicates.
Only merges where we are highly confident (same title, same normalized date).
"""
import sqlite3
import re
import sys

DB_PATH = "/Users/joereuter/Clones/schdudesee/stutensee_events.db"

def normalize_date(d):
    if d is None:
        return None
    d = d.strip()
    m = re.match(r'^(\d{4})-(\d{1,2})-(\d{1,2})', d)
    if m:
        return f"{m.group(1)}-{int(m.group(2)):02d}-{int(m.group(3)):02d}"
    return d

def main():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = OFF")
    cursor = conn.cursor()
    
    # Find identical-title events on the same normalized date
    cursor.execute("""
        SELECT c1.id as id1, c2.id as id2,
               c1.title, c1.date_start as ds1, c2.date_start as ds2,
               c1.location as loc1, c2.location as loc2,
               c1.sources as src1, c2.sources as src2,
               c1.description as desc1, c2.description as desc2
        FROM curated_events c1
        JOIN curated_events c2 ON c1.id < c2.id 
            AND c1.title = c2.title
            AND c1.recurring_group_id IS NULL 
            AND c2.recurring_group_id IS NULL
        WHERE c1.date_start IS NOT NULL AND c2.date_start IS NOT NULL
    """)
    
    rows = cursor.fetchall()
    
    # Group by normalized date
    by_ndate = {}
    for r in rows:
        nd1 = normalize_date(r['ds1'])
        nd2 = normalize_date(r['ds2'])
        if nd1 and nd2 and nd1 == nd2:
            key = (r['title'], nd1)
            if key not in by_ndate:
                by_ndate[key] = []
            by_ndate[key].append(r)
    
    print(f"Date-format duplicate pairs found: {sum(len(v) for v in by_ndate.values())}", file=sys.stderr)
    print(f"Unique (title, normalized date) groups: {len(by_ndate)}", file=sys.stderr)
    
    # For each group, merge
    total_merged = 0
    total_deleted = 0
    examples = []
    merged_ids = set()  # Track IDs already merged to avoid re-processing
    
    for (title, ndate), pairs in sorted(by_ndate.items()):
        # Collect all unique IDs involved
        ids = set()
        for p in pairs:
            ids.add(p['id1'])
            ids.add(p['id2'])
        ids = [i for i in ids if i not in merged_ids]
        if len(ids) < 2:
            continue
        
        # Get full row data for each ID
        cursor.execute(f"""
            SELECT id, title, date_start, date_end, time_raw, location, organizer,
                   description, event_url, sources
            FROM curated_events
            WHERE id IN ({','.join('?' for _ in ids)})
        """, ids)
        events = cursor.fetchall()
        
        if len(events) < 2:
            continue
        
        # Pick survivor (lowest id or best data)
        # Prefer the one with non-generic location, then more sources, then longer description
        def event_score(e):
            s = 0
            loc = e['location'] or ''
            if loc and 'vereinsheim/vereinsgelände' not in loc.lower():
                s += 3
            if loc and len(loc) > 10:
                s += 2
            sources = e['sources'] or ''
            s += len([x for x in sources.split(',') if x.strip()]) * 2
            desc = e['description'] or ''
            if desc.strip():
                s += 3
            # Prefer normal date format over "2026-5-1T1"
            ds = e['date_start'] or ''
            if re.match(r'^\d{4}-\d{2}-\d{2}$', ds):
                s += 2
            return s
        
        events_sorted = sorted(events, key=event_score, reverse=True)
        survivor = events_sorted[0]
        duplicates = events_sorted[1:]
        
        # Merge data
        best_location = ''
        for e in events:
            loc = e['location'] or ''
            if len(loc) > len(best_location):
                best_location = loc
        
        # Merge sources
        all_sources = set()
        for e in events:
            for s in (e['sources'] or '').split(','):
                s = s.strip()
                if s:
                    all_sources.add(s)
        merged_sources = ','.join(sorted(all_sources))
        
        # Best description (longest)
        best_desc = ''
        for e in events:
            d = e['description'] or ''
            if len(d.strip()) > len(best_desc):
                best_desc = d.strip()
        
        cursor.execute("""
            UPDATE curated_events
            SET description = ?, sources = ?, location = ?,
                updated_at = datetime('now'), dedup_round = COALESCE(dedup_round, 0) + 1
            WHERE id = ?
        """, (best_desc, merged_sources, best_location, survivor['id']))
        
        for dup in duplicates:
            cursor.execute("DELETE FROM raw_to_curated WHERE curated_id = ?", (dup['id'],))
            cursor.execute("DELETE FROM curated_events WHERE id = ?", (dup['id'],))
            merged_ids.add(dup['id'])
            total_deleted += 1
        
        merged_ids.add(survivor['id'])
        total_merged += 1
        
        if total_merged <= 8:
            date_formats = '/'.join(e['date_start'] for e in events)
            loc_str = best_location or '?'
            src_str = '|'.join(sorted(all_sources))
            examples.append(f"  '{title}' ({date_formats})")
            examples.append(f"    Location: {loc_str}, Sources: {src_str}")
            examples.append(f"    Kept id={survivor['id']}, deleted {len(duplicates)} dup(s)")
    
    conn.commit()
    conn.close()
    
    report_lines = []
    report_lines.append(f"Date-format duplicate groups merged: {total_merged}")
    report_lines.append(f"Duplicate rows deleted: {total_deleted}")
    report_lines.append("")
    if examples:
        report_lines.append("Examples:")
        report_lines.extend(examples)
    report_lines.append("")
    report_lines.append("Summary:")
    report_lines.append(f"- Found {total_merged} groups of date-format/cross-source duplicates")
    report_lines.append(f"- Deleted {total_deleted} duplicate rows")
    report_lines.append(f"- Updated {total_merged} surviving rows with merged data")
    
    return '\n'.join(report_lines)

if __name__ == '__main__':
    result = main()
    print(result)
