#!/usr/bin/env python3
import sqlite3
conn = sqlite3.connect('events/events.db')
c = conn.cursor()
print('DROP TABLE IF EXISTS curated_events;')
for sql, in c.execute("SELECT sql FROM sqlite_master WHERE sql IS NOT NULL AND name = 'curated_events'"):
    print(sql + ';')
def esc(v):
    if v is None: return 'NULL'
    if isinstance(v, (int, float)): return str(v)
    s = str(v).replace("'", "''")
    return f"'{s}'"
for row in c.execute('SELECT * FROM curated_events'):
    vals = ', '.join(esc(v) for v in row)
    print(f'INSERT INTO curated_events VALUES ({vals});')
conn.close()
