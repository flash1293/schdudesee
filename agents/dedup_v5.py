"""
Agentic dedup v5: Find cross-source duplicates among one-time events.
Also reconstruct missing Korallengarde events incorrectly merged by v4.

Strategy:
1. Reconstruct deleted Korallengarde events from raw_events
2. Fix corrupted Seepferdchengarde (them merged with Korallengarde)
3. Find REAL cross-source duplicates with strict matching:
   a. Same date, same location, different sources
   b. Titles must share a unique distinguishing word
   c. Only merge events from different sources (cross-source)
"""
import sqlite3
import re
import sys
from collections import defaultdict
from difflib import SequenceMatcher

DB_PATH = "/Users/joereuter/Clones/schdudesee/stutensee_events.db"

STOP_WORDS = {'und', 'der', 'die', 'das', 'mit', 'für', 'am', 'im', 'auf', 'ein',
              'eine', 'dem', 'den', 'in', 'von', 'des', 'zum', 'zur', 'bei', 'aus',
              'nach', 'vor', 'durch', 'über', 'unter', 'neben', 'an', 'einer',
              'eines', 'einem', 'einen', 'kein', 'keine', 'keinen', 'nicht',
              '0', '1', '2', '3', '4', '5', '6', '7', '8', '9', '10', '11', '12',
              '13', '14', '15', '16', '17', '18', '19', '20',
              '&amp;', '-', '–', ''}

def normalize_date(d):
    if d is None:
        return None
    d = d.strip()
    m = re.match(r'^(\d{4})-(\d{1,2})-(\d{1,2})', d)
    if m:
        return f"{m.group(1)}-{int(m.group(2)):02d}-{int(m.group(3)):02d}"
    return d

def normalize_title(t):
    if t is None:
        return ""
    t = t.lower().strip()
    t = re.sub(r'[^\w\säöüßö]', ' ', t)
    t = re.sub(r'\s+', ' ', t).strip()
    return t

def tokenize(s):
    """Return set of meaningful tokens (non-stop-words) from a string."""
    if not s:
        return set()
    n = normalize_title(s)
    tokens = set(n.split())
    return tokens - STOP_WORDS

def extract_key_tokens(title):
    """Extract distinctive content-bearing tokens from a title."""
    tokens = tokenize(title)
    # Remove pure numbers (ages like 10, 14, 6, etc.)
    tokens = {t for t in tokens if not re.match(r'^\d+$', t)}
    # Remove very short tokens
    tokens = {t for t in tokens if len(t) >= 3}
    return tokens

def location_similar(loc1, loc2):
    if not loc1 or not loc2 or loc1.strip() == '' or loc2.strip() == '':
        return True
    l1 = loc1.lower().strip()
    l2 = loc2.lower().strip()
    if l1 == l2:
        return True
    if l1 in l2 or l2 in l1:
        return True
    t1 = tokenize(loc1)
    t2 = tokenize(loc2)
    place_keywords = {'stutensee', 'blankenloch', 'friedrichstal', 'spöck', 'spoeck',
                      'büchig', 'buechig', 'staffort', 'waldstraße', 'waldstrasse',
                      'marktplatz', 'vereinsheim', 'feuerwehrhaus', 'feuerwehr',
                      'rathausvorplatz', 'gymnasiumstraße', 'gymnasiumstrasse',
                      'sportplatz', 'eggensteiner', 'seegrabenweg', 'kirchstraße',
                      'kirchstrasse', 'hirschstraße', 'hirschstrasse',
                      'begegnungszentrum', 'regenbogen', 'piraten'}
    common_places = t1 & t2 & place_keywords
    if len(common_places) >= 1:
        return True
    common = t1 & t2
    if len(common) >= 2:
        return True
    return False

def have_distinctive_token(titles):
    """Check if two titles have at least one distinctive (non-numeric, non-stop) token in common."""
    if len(titles) < 2:
        return True
    shared = None
    for t in titles:
        keys = extract_key_tokens(t)
        if shared is None:
            shared = keys
        else:
            shared = shared & keys
    # Must share at least one distinctive word
    return len(shared) >= 1 if shared else False

def is_cross_source(sources_list):
    """Check if events have different source URLs."""
    all_sources = set()
    for s in sources_list:
        if not s:
            continue
        for part in s.split(','):
            part = part.strip()
            if part:
                all_sources.add(part)
    return len(all_sources) >= 2

def title_similar_enough(t1, t2):
    """Check if two titles likely refer to the same event.
    More conservative than v4 to avoid false positives."""
    if not t1 or not t2:
        return False
    n1 = normalize_title(t1)
    n2 = normalize_title(t2)
    if n1 == n2:
        return True
    
    # Distinctive token check: at least one meaningful common token
    keys1 = extract_key_tokens(t1)
    keys2 = extract_key_tokens(t2)
    common_keys = keys1 & keys2
    
    if not common_keys:
        return False  # No distinctive token shared => different events
    
    # Check if one normalized title contains the other entirely
    if len(n1) >= 5 and len(n2) >= 5:
        if n1 in n2 or n2 in n1:
            return True
    
    # Token Jaccard on all tokens (not just key tokens)
    all_t1 = tokenize(t1)
    all_t2 = tokenize(t2)
    if not all_t1 or not all_t2:
        return False
    intersection = all_t1 & all_t2
    union = all_t1 | all_t2
    jaccard = len(intersection) / len(union)
    
    # Must have at least 40% token overlap AND share a distinctive token
    if jaccard >= 0.4 and len(common_keys) >= 1:
        return True
    
    # SequenceMatcher as fallback
    ratio = SequenceMatcher(None, n1, n2).ratio()
    if ratio >= 0.65 and len(common_keys) >= 1:
        return True
    
    return False

def pick_best_title(titles):
    best = None
    best_score = -1
    for t in titles:
        if not t:
            continue
        score = 0
        score += len(t) * 0.5
        if t != t.lower():
            score += 3
        if t[0].isupper():
            score += 2
        if t.strip():
            score += 1
        if score > best_score:
            best_score = score
            best = t
    return best

def pick_best_description(descriptions):
    best = ""
    for d in descriptions:
        if d and len(d.strip()) > len(best):
            best = d.strip()
    return best

def merge_sources(sources_list):
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

def reconstruct_korallengarde(conn):
    """Reconstruct Korallengarde events incorrectly deleted by v4 dedup.
    
    v4 incorrectly merged Korallengarde with Seepferdchengarde on same date+location.
    Since both came from the same source (stutenseekinderkalender.de), the Seepferdchengarde
    survivor was not corrupted. We just need to re-insert the missing Korallengarde rows.
    """
    cursor = conn.cursor()
    
    # Find dates where Korallengarde exists in raw_events but NOT in curated_events
    cursor.execute("""
        SELECT r.id, r.title, r.date_start, r.date_end, r.time_raw, r.location,
               r.organizer, r.description, r.event_url, r.source_url
        FROM raw_events r
        WHERE r.title LIKE '%Korallengarde%'
          AND r.date_start NOT IN (
              SELECT DISTINCT date_start FROM curated_events WHERE title LIKE '%Korallengarde%'
          )
    """)
    missing = cursor.fetchall()
    
    for row in missing:
        src = row['source_url'] if row['source_url'] else 'https://stutenseekinderkalender.de'
        cursor.execute("""
            INSERT INTO curated_events
            (title, date_start, date_end, time_raw, location, organizer,
             description, event_url, sources, tags, recurring_group_id)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, '', NULL)
        """, (
            row['title'],
            row['date_start'],
            row['date_end'],
            row['time_raw'],
            row['location'],
            row['organizer'],
            row['description'],
            row['event_url'],
            src
        ))
    
    conn.commit()
    print(f"  Reconstructed {len(missing)} Korallengarde events from raw_events", file=sys.stderr)

def find_and_merge_duplicates(conn):
    """Find genuine cross-source duplicates and merge them."""
    cursor = conn.cursor()
    
    # Read all one-time events
    cursor.execute("""
        SELECT id, title, date_start, date_end, time_raw, location, organizer,
               description, event_url, sources, tags
        FROM curated_events
        WHERE recurring_group_id IS NULL
        ORDER BY date_start
    """)
    rows = cursor.fetchall()
    print(f"Total one-time events before dedup: {len(rows)}", file=sys.stderr)
    
    # Index by normalized date
    by_date = defaultdict(list)
    for r in rows:
        nd = normalize_date(r['date_start'])
        by_date[nd].append(r)
    
    def sort_key(item):
        d, _ = item
        return (d is None, d) if d is not None else (1, '')
    
    all_groups = []
    
    for date, events in sorted(by_date.items(), key=sort_key):
        if len(events) < 2:
            continue
        
        # Group by general location area
        loc_groups = defaultdict(list)
        for e in events:
            loc = e['location'] if e['location'] else ''
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
                    if not title_similar_enough(loc_events[i]['title'], loc_events[j]['title']):
                        continue
                    if not location_similar(loc_events[i]['location'], loc_events[j]['location']):
                        continue
                    # Must be from different sources to count as cross-source
                    sources_i = loc_events[i]['sources'] or ''
                    sources_j = loc_events[j]['sources'] or ''
                    src_set_i = set(s.strip() for s in sources_i.split(',') if s.strip())
                    src_set_j = set(s.strip() for s in sources_j.split(',') if s.strip())
                    if src_set_i == src_set_j and len(src_set_i) > 0:
                        # Same source, not cross-source - skip unless date-format duplicates
                        # But date-format duplicates have same source AND same title
                        if normalize_title(loc_events[i]['title']) == normalize_title(loc_events[j]['title']):
                            pass  # This IS a date-format duplicate, merge it
                        else:
                            continue
                    
                    group.append(j)
                    matched.add(j)
                if len(group) > 1:
                    groups.append([loc_events[idx] for idx in group])
            
            all_groups.extend(groups)
    
    print(f"Duplicate groups found: {len(all_groups)}", file=sys.stderr)
    
    total_merged = 0
    total_deleted = 0
    examples = []
    
    for group in all_groups:
        # Verify distinctive token shared across ALL titles in group
        titles_list = [e['title'] for e in group]
        if not have_distinctive_token(titles_list):
            print(f"  SKIP (no shared distinctive token): {titles_list}", file=sys.stderr)
            continue
        
        # Pick survivor
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
        
        all_titles = [e['title'] for e in group]
        all_descs = [e['description'] for e in group]
        all_sources = [e['sources'] for e in group]
        all_locations = [e['location'] for e in group]
        
        best_title = pick_best_title(all_titles)
        best_desc = pick_best_description(all_descs)
        merged_sources = merge_sources(all_sources)
        best_location = ''
        for loc in all_locations:
            if loc and len(loc) > len(best_location):
                best_location = loc
        
        cursor.execute("""
            UPDATE curated_events
            SET title = ?, description = ?, sources = ?, location = ?,
                updated_at = datetime('now'), dedup_round = COALESCE(dedup_round, 0) + 1
            WHERE id = ?
        """, (best_title, best_desc, merged_sources, best_location, survivor['id']))
        
        for dup in duplicates:
            cursor.execute("DELETE FROM raw_to_curated WHERE curated_id = ?", (dup['id'],))
            cursor.execute("DELETE FROM curated_events WHERE id = ?", (dup['id'],))
            total_deleted += 1
        
        total_merged += 1
        
        if total_merged <= 10:
            title_str = ' / '.join(all_titles)
            date_str = survivor['date_start'] or '?'
            loc_str = best_location or '?'
            src_str = '|'.join(set(s.split(',')[0].strip() for s in all_sources if s))
            examples.append(f"  {title_str}")
            examples.append(f"    Date: {date_str}, Location: {loc_str}")
            examples.append(f"    Sources: {src_str}")
            examples.append(f"    Kept title: '{best_title}', deleted {len(duplicates)} dup(s)")
    
    conn.commit()
    
    report = []
    report.append(f"Total duplicate groups merged: {total_merged}")
    report.append(f"Total duplicate rows deleted: {total_deleted}")
    report.append("")
    if examples:
        report.append("Examples (first 10):")
        report.extend(examples)
    report.append("")
    report.append("Summary:")
    report.append(f"- Found {total_merged} groups of cross-source duplicates")
    report.append(f"- Deleted {total_deleted} duplicate rows")
    report.append(f"- Updated {total_merged} surviving rows with merged data")
    
    return '\n'.join(report)

def main():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = OFF")
    
    print("Step 1: Reconstruct incorrectly merged Korallengarde events...", file=sys.stderr)
    reconstruct_korallengarde(conn)
    
    print("\nStep 2: Find cross-source duplicates and merge...", file=sys.stderr)
    report = find_and_merge_duplicates(conn)
    
    conn.execute("PRAGMA foreign_keys = ON")
    conn.close()
    
    return report

if __name__ == '__main__':
    result = main()
    print(result)
    print(result, file=sys.stderr)
