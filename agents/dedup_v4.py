"""
Agentic dedup v4: Find cross-source duplicates among one-time events.
"""
import sqlite3
import re
import sys
from collections import defaultdict
from difflib import SequenceMatcher

DB_PATH = "/Users/joereuter/Clones/schdudesee/stutensee_events.db"

def normalize_date(d):
    """Normalize various date formats to YYYY-MM-DD."""
    if d is None:
        return None
    d = d.strip()
    # "2026-5-1T1" -> "2026-05-01"
    m = re.match(r'^(\d{4})-(\d{1,2})-(\d{1,2})', d)
    if m:
        return f"{m.group(1)}-{int(m.group(2)):02d}-{int(m.group(3)):02d}"
    return d

def normalize_title(t):
    """Normalize title for comparison."""
    if t is None:
        return ""
    t = t.lower().strip()
    t = re.sub(r'[^\w\s]', '', t)
    t = re.sub(r'\s+', ' ', t).strip()
    return t

def tokenize(s):
    return set(normalize_title(s).split())

def location_similar(loc1, loc2):
    """Check if two locations refer to roughly the same place."""
    if not loc1 or not loc2 or loc1.strip() == '' or loc2.strip() == '':
        return True  # missing location = can't rule out
    l1 = loc1.lower().strip()
    l2 = loc2.lower().strip()
    if l1 == l2:
        return True
    # Check if one contains the other
    if l1 in l2 or l2 in l1:
        return True
    # Check token overlap
    t1 = tokenize(loc1)
    t2 = tokenize(loc2)
    common = t1 & t2
    # Common should contain key place identifier
    place_keywords = {'stutensee', 'blankenloch', 'friedrichstal', 'spöck', 'spoeck',
                      'büchig', 'buechig', 'staffort', 'waldstraße', 'marktplatz',
                      'vereinsheim', 'feuerwehrhaus', 'feuerwehr', 'rathausvorplatz',
                      'gymnasiumstraße', 'sportplatz', 'eggensteiner'}
    common_places = common & place_keywords
    if len(common_places) >= 1:
        return True
    # If locations share significant token overlap
    if len(common) >= 2:
        return True
    return False

def title_similar(t1, t2, threshold=0.6):
    """Check if two titles likely refer to the same event."""
    if not t1 or not t2:
        return False
    n1 = normalize_title(t1)
    n2 = normalize_title(t2)
    if n1 == n2:
        return True
    # Token comparison
    tokens1 = set(n1.split())
    tokens2 = set(n2.split())
    # Remove very common tokens
    common_stop = {'und', 'der', 'die', 'das', 'mit', 'für', 'am', 'im', 'auf', 'ein',
                   'eine', 'dem', 'den', 'in', 'von', 'des', 'zum', 'zur'}
    t1_filtered = tokens1 - common_stop
    t2_filtered = tokens2 - common_stop
    
    if not t1_filtered or not t2_filtered:
        return False
    
    # Jaccard similarity on filtered tokens
    intersection = t1_filtered & t2_filtered
    union = t1_filtered | t2_filtered
    jaccard = len(intersection) / len(union) if union else 0
    
    if jaccard >= 0.5:
        return True
    
    # Check if one title is contained in the other (after normalization)
    if n1 in n2 or n2 in n1:
        return True
    
    # SequenceMatcher for fuzzy match
    ratio = SequenceMatcher(None, n1, n2).ratio()
    if ratio >= threshold:
        return True
    
    return False

def pick_best_title(titles):
    """Pick the best title from a list."""
    # Prefer the one with proper capitalization (not all lowercase)
    best = None
    best_score = -1
    for t in titles:
        if not t:
            continue
        score = 0
        # Longer is generally better
        score += len(t) * 0.5
        # Proper capitalization (has uppercase letters)
        if t != t.lower():
            score += 2
        # Not starting with lowercase
        if t[0].isupper():
            score += 1
        # Prefer non-empty over empty
        if t.strip():
            score += 1
        if score > best_score:
            best_score = score
            best = t
    return best

def pick_best_description(descriptions):
    """Pick the longest non-empty description."""
    best = ""
    for d in descriptions:
        if d and len(d.strip()) > len(best):
            best = d.strip()
    return best

def merge_sources(sources_list):
    """Merge sources into comma-separated unique list."""
    merged = []
    seen = set()
    for s in sources_list:
        if not s:
            continue
        for part in s.split(','):
            part = part.strip()
            if part and part not in seen:
                seen.add(part)
                merged.append(part)
    return ','.join(merged)

def main():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    # Read all one-time events
    cursor.execute("""
        SELECT id, title, date_start, date_end, time_raw, location, organizer,
               description, event_url, sources, tags, recurring_group_id
        FROM curated_events
        WHERE recurring_group_id IS NULL
        ORDER BY date_start
    """)
    rows = cursor.fetchall()
    print(f"Total one-time events: {len(rows)}", file=sys.stderr)
    
    # Index by normalized date
    by_date = defaultdict(list)
    date_norm_map = {}  # original -> normalized
    
    for r in rows:
        nd = normalize_date(r['date_start'])
        date_norm_map[r['date_start']] = nd
        by_date[nd].append(r)
    
    # For events with same date, find cross-source duplicates
    # Group by (normalized_date + normalized_location_area)
    # Then within each group, find title-similar events
    
    all_groups = []  # list of lists of row dicts
    
    def sort_key(item):
        d, _ = item
        return (d is None, d) if d is not None else (1, '')
    
    for date, events in sorted(by_date.items(), key=sort_key):
        if len(events) < 2:
            continue
        
        # Group by general location area
        loc_groups = defaultdict(list)
        for e in events:
            loc = e['location'] if e['location'] else ''
            # Extract area keyword
            area = 'unknown'
            if loc:
                loc_lower = loc.lower()
                if 'blankenloch' in loc_lower:
                    area = 'blankenloch'
                elif 'friedrichstal' in loc_lower:
                    area = 'friedrichstal'
                elif 'spöck' in loc_lower or 'spoeck' in loc_lower:
                    area = 'spöck'
                elif 'büchig' in loc_lower or 'buechig' in loc_lower:
                    area = 'büchig'
                elif 'staffort' in loc_lower:
                    area = 'staffort'
                elif 'stutensee' in loc_lower:
                    area = 'stutensee'
            loc_groups[area].append(e)
        
        for area, loc_events in loc_groups.items():
            if len(loc_events) < 2:
                continue
            
            # Within same area + same date, check for title similarity
            # Compare all pairs
            matched = set()
            groups = []
            
            for i in range(len(loc_events)):
                if i in matched:
                    continue
                group = [i]
                matched.add(i)
                for j in range(i + 1, len(loc_events)):
                    if j in matched:
                        continue
                    if title_similar(loc_events[i]['title'], loc_events[j]['title']):
                        # Verify location is also similar
                        if location_similar(loc_events[i]['location'], loc_events[j]['location']):
                            group.append(j)
                            matched.add(j)
                if len(group) > 1:
                    groups.append([loc_events[idx] for idx in group])
            
            all_groups.extend(groups)
    
    print(f"Duplicate groups found: {len(all_groups)}", file=sys.stderr)
    
    # Process duplicates
    total_merged = 0
    total_deleted = 0
    examples = []
    
    for group in all_groups:
        # Verify dates are ±1 day
        dates = [normalize_date(e['date_start']) for e in group]
        date_set = set(dates)
        
        # Pick survivor (keep the one with lowest id = first created)
        # Actually, we should keep the BEST one, not just the first
        survivor_idx = 0
        best_score = -1
        for idx, e in enumerate(group):
            score = 0
            if e['title']:
                score += 1
            if e['location']:
                score += 2
            if e['description'] and e['description'].strip():
                score += 3
            if e['sources'] and len(e['sources'].split(',')) > 1:
                score += 1
            if score > best_score:
                best_score = score
                survivor_idx = idx
        
        survivor = group[survivor_idx]
        duplicates = [e for i, e in enumerate(group) if i != survivor_idx]
        
        # Merge data into survivor
        all_titles = [e['title'] for e in group]
        all_descs = [e['description'] for e in group]
        all_sources = [e['sources'] for e in group]
        all_locations = [e['location'] for e in group]
        
        # Best title
        best_title = pick_best_title(all_titles)
        
        # Best description
        best_desc = pick_best_description(all_descs)
        
        # Merge sources
        merged_sources = merge_sources(all_sources)
        
        # Best location (prefer non-empty)
        best_location = ''
        for loc in all_locations:
            if loc and len(loc) > len(best_location):
                best_location = loc
        
        # Update survivor
        cursor.execute("""
            UPDATE curated_events
            SET title = ?, description = ?, sources = ?, location = ?,
                updated_at = datetime('now'), dedup_round = COALESCE(dedup_round, 0) + 1
            WHERE id = ?
        """, (best_title, best_desc, merged_sources, best_location, survivor['id']))
        
        # Delete duplicates and their raw_to_curated mappings
        for dup in duplicates:
            cursor.execute("DELETE FROM raw_to_curated WHERE curated_id = ?", (dup['id'],))
            cursor.execute("DELETE FROM curated_events WHERE id = ?", (dup['id'],))
            total_deleted += 1
        
        total_merged += 1
        
        # Generate example description
        if total_merged <= 5:
            title_str = ' / '.join(all_titles)
            date_str = survivor['date_start'] or '?'
            loc_str = best_location or '?'
            src_str = '|'.join(set(s.split(',')[0].strip() for s in all_sources if s))
            examples.append(f"  {title_str}")
            examples.append(f"    Date: {date_str}, Location: {loc_str}")
            examples.append(f"    Sources: {src_str}")
            examples.append(f"    Kept title: '{best_title}', deleted {len(duplicates)} dup(s)")
    
    conn.commit()
    conn.close()
    
    # Report
    report = []
    report.append(f"Total duplicate groups merged: {total_merged}")
    report.append(f"Total duplicate rows deleted: {total_deleted}")
    report.append("")
    if examples:
        report.append("Examples:")
        report.extend(examples)
    report.append("")
    report.append("Summary:")
    report.append(f"- Found {total_merged} groups of cross-source duplicates")
    report.append(f"- Deleted {total_deleted} duplicate rows")
    report.append(f"- Updated {total_merged} surviving rows with merged data")
    
    return '\n'.join(report)

if __name__ == '__main__':
    result = main()
    print(result)
