#!/usr/bin/env python3
"""Dump curated_events from SQLite to SQL for D1 import.
Usage: python3 dump_d1.py [db_path] [d1_table]
  db_path: path to SQLite DB (default: events/events.db)
  d1_table: D1 table name (default: curated_events)
"""
import sqlite3, sys

db_path = sys.argv[1] if len(sys.argv) > 1 else 'events/events.db'
d1_table = sys.argv[2] if len(sys.argv) > 2 else 'curated_events'

conn = sqlite3.connect(db_path)
c = conn.cursor()
print(f'DROP TABLE IF EXISTS {d1_table};')
for sql, in c.execute("SELECT sql FROM sqlite_master WHERE sql IS NOT NULL AND name = ?", (d1_table,)):
    print(sql + ';')
def esc(v):
    if v is None: return 'NULL'
    if isinstance(v, (int, float)): return str(v)
    s = str(v).replace("'", "''")
    return f"'{s}'"
for row in c.execute(f'SELECT * FROM {d1_table}'):
    vals = ', '.join(esc(v) for v in row)
    print(f'INSERT INTO {d1_table} VALUES ({vals});')
conn.close()
