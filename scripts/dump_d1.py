#!/usr/bin/env python3
"""Dump curated_events and id_redirects from SQLite to SQL for D1 import.
Usage: python3 dump_d1.py [db_path] [d1_table_prefix]
  db_path: path to SQLite DB (default: events/events.db)
  d1_table_prefix: prefix for D1 table names (default: '', tables: curated_events, id_redirects)
"""
import sqlite3, sys

db_path = sys.argv[1] if len(sys.argv) > 1 else 'events/events.db'

TABLES = ['curated_events', 'id_redirects']

conn = sqlite3.connect(db_path)
c = conn.cursor()

def esc(v):
    if v is None: return 'NULL'
    if isinstance(v, (int, float)): return str(v)
    s = str(v).replace("'", "''")
    return f"'{s}'"

for table in TABLES:
    # Check if table exists
    exists = c.execute("SELECT name FROM sqlite_master WHERE type='table' AND name=?", (table,)).fetchone()
    if not exists:
        print(f"-- Table {table} not found, skipping")
        continue

    print(f'DROP TABLE IF EXISTS {table};')
    for sql, in c.execute("SELECT sql FROM sqlite_master WHERE sql IS NOT NULL AND name = ?", (table,)):
        print(sql + ';')
    for row in c.execute(f'SELECT * FROM {table}'):
        vals = ', '.join(esc(v) for v in row)
        print(f'INSERT INTO {table} VALUES ({vals});')

conn.close()
