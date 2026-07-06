#!/usr/bin/env bash
set -e
cd "$(dirname "$0")"

echo "==> Building worker with inlined HTML..."
python3 build.py

echo "==> Exporting database for D1..."
python3 -c "
import sqlite3
conn = sqlite3.connect('../stutensee_events.db')
c = conn.cursor()
# Drop first to avoid conflicts
print('DROP TABLE IF EXISTS event_embeddings;')
print('DROP TABLE IF EXISTS raw_to_curated;')
print('DROP TABLE IF EXISTS curated_events;')
print('DROP TABLE IF EXISTS raw_events;')
for sql, name in c.execute(\"SELECT sql, name FROM sqlite_master WHERE sql IS NOT NULL AND name NOT LIKE 'sqlite_%' AND name NOT LIKE '%idx_%'\"):
    print(sql + ';')
print()
for sql in c.execute(\"SELECT sql FROM sqlite_master WHERE sql LIKE 'CREATE INDEX%'\"):
    print(sql[0] + ';')
print()
def esc(v):
    if v is None: return 'NULL'
    if isinstance(v, (int, float)): return str(v)
    s = str(v).replace(\"'\", \"''\")
    return f\"'{s}'\"
for table in ['raw_events', 'curated_events', 'raw_to_curated']:
    c.execute(f'SELECT * FROM {table}')
    cols = ', '.join(d[0] for d in c.description)
    for row in c.fetchall():
        vals = \", \".join(esc(v) for v in row)
        print(f\"INSERT INTO {table} ({cols}) VALUES ({vals});\")
conn.close()
" > dump_d1.sql

echo "==> Importing data into D1..."
npx wrangler d1 execute was-geht-stutensee --file dump_d1.sql --remote

echo "==> Deploying worker..."
npx wrangler deploy

echo "==> Done!"
