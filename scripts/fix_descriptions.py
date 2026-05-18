import sqlite3
import re
import html

db = sqlite3.connect('/Users/joereuter/Clones/schdudesee/stutensee_events.db')
cur = db.cursor()

cur.execute('''SELECT id, title, date_start, description, sources FROM curated_events''')
all_events = cur.fetchall()

html_entity_fixed = 0
short_desc_fixed = 0
ellipsis_fixed = 0
weiterlesen_fixed = 0
raw_copied = 0
total_changed = 0

fix_log = []

for eid, title, date_start, desc, sources in all_events:
    original = desc
    if desc is None:
        desc = ''
    changed = False

    # 1. Strip HTML tags (like <style>, <div>, <!-- -->, etc.)
    new_desc = re.sub(r'<[^>]*>', '', desc)
    if new_desc != desc:
        desc = new_desc
        changed = True

    # 2. Decode HTML entities
    new_desc = html.unescape(desc)
    if new_desc != desc:
        desc = new_desc
        html_entity_fixed += 1
        changed = True

    # 3. Remove "weiterlesen" suffix
    if re.search(r'\s*weiterlesen\s*$', desc, re.IGNORECASE):
        desc = re.sub(r'\s*weiterlesen\s*$', '', desc, flags=re.IGNORECASE)
        weiterlesen_fixed += 1
        changed = True

    # 4. Fix "..." to empty
    if desc.strip() == '...':
        desc = ''
        ellipsis_fixed += 1
        changed = True

    # 5. Fix very short descriptions (< 5 chars, not empty)
    stripped = desc.strip()
    if len(stripped) > 0 and len(stripped) < 5:
        old = desc
        # Try raw_events
        cur2 = db.cursor()
        cur2.execute('''
            SELECT description FROM raw_events
            WHERE (title = ? OR title LIKE ?)
            AND date_start = ?
            AND description IS NOT NULL AND length(description) > 5
            ORDER BY length(description) DESC LIMIT 1
        ''', (title, f'%{title}%', date_start))
        row = cur2.fetchone()
        if row and row[0] and len(row[0].strip()) > 5:
            desc = row[0]
            raw_copied += 1
            changed = True
            fix_log.append((eid, title, 'very_short->raw_copy', old[:40], desc[:60]))
        else:
            desc = ''
            short_desc_fixed += 1
            changed = True
            fix_log.append((eid, title, 'very_short->cleared', old, ''))

    if changed:
        cur.execute('UPDATE curated_events SET description = ?, updated_at = datetime("now") WHERE id = ?', (desc, eid))
        if not any(l[0] == eid for l in fix_log):
            fix_log.append((eid, title, 'html_entities/cleanup', original[:60] if original else '(null)', desc[:60] if desc else '(empty)'))
        total_changed += 1

db.commit()
db.close()

print(f'Total events checked: {len(all_events)}')
print(f'Total descriptions changed: {total_changed}')
print(f'  - HTML entity decoding: {html_entity_fixed}')
print(f'  - HTML tag stripping: {sum(1 for l in fix_log if l[2] == "html_entities/cleanup")}')
print(f'  - "weiterlesen" removed: {weiterlesen_fixed}')
print(f'  - "..." cleared: {ellipsis_fixed}')
print(f'  - Very short desc fixed: {short_desc_fixed + raw_copied}')
print(f'    (raw copy: {raw_copied}, cleared: {short_desc_fixed})')
print()
print('Change log:')
for eid, title, kind, before, after in fix_log:
    print(f'  [{kind}] ID={eid} "{title}"')
    print(f'    Before: {before!r}')
    print(f'    After:  {after!r}')
