#!/usr/bin/env bash
set -e
cd "$(dirname "$0")"

echo "==> Creating staging D1 database if needed..."
DB_ID=$(wrangler d1 list --json 2>/dev/null | python3 -c "
import sys, json
dbs = json.load(sys.stdin)
for db in dbs:
    if db['name'] == 'was-geht-stutensee-staging':
        print(db['uuid'])
        break
")
if [ -z "$DB_ID" ]; then
    echo "Creating new D1 database 'was-geht-stutensee-staging'..."
    DB_ID=$(wrangler d1 create was-geht-stutensee-staging 2>&1 | grep -oP 'database_id = "\K[^"]+')
    echo "Created with ID: $DB_ID"
else
    echo "Database already exists: $DB_ID"
fi

# Write the DB ID into wrangler.toml
sed -i "s/database_id = \"\"/database_id = \"$DB_ID\"/" wrangler.toml

echo "==> Building worker with staging HTML..."
python3 build.py

echo "==> Exporting database for D1..."
cd /workspace/extra/persist/schdudesee
python3 -c "
import sqlite3
conn = sqlite3.connect('stutensee_events.db')
c = conn.cursor()
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
for table in ['raw_events', 'curated_events', 'raw_to_curated', 'event_embeddings']:
    c.execute(f'SELECT * FROM {table}')
    cols = ', '.join(d[0] for d in c.description)
    for row in c.fetchall():
        print(f\"INSERT INTO {table} ({cols}) VALUES ({\", \".join(esc(v) for v in row)});\")
conn.close()
" > /tmp/staging_dump.sql

echo "==> Importing data into staging D1..."
cd /workspace/extra/persist/schdudesee/cloudflare-staging
wrangler d1 execute was-geht-stutensee-staging --file /tmp/staging_dump.sql --remote

echo "==> Deploying staging worker..."
wrangler deploy

echo "==> Staging deployment done!"
