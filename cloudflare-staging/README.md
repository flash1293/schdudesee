# Was geht, Stutensee? — Cloudflare Deployment

## Prerequisites

- `wrangler` CLI: `npm install -g wrangler`
- Logged in: `wrangler login`

## Deploy

```bash
python3 build.py && wrangler deploy
```

## First-time setup

```bash
wrangler d1 create was-geht-stutensee-staging
# Copy the database_id from output into wrangler.toml

# Load the current event data (built from the event files in this repo)
python3 ../scripts/build_db.py
python3 ../scripts/dump_d1.py > /tmp/dump_d1.sql
wrangler d1 execute was-geht-stutensee-staging --file /tmp/dump_d1.sql --remote
```

The old `dump.sql` snapshot was removed — `./deploy.sh` regenerates the dump from
the repo data on every run, so a committed copy only goes stale.

## Custom Domain

The worker deploys to `was-geht-stutensee.<your-account>.workers.dev` by default.

To use `was-geht-stutensee.de`, add a CNAME record in your DNS provider pointing to the workers.dev URL:

```
CNAME was-geht-stutensee.de → was-geht-stutensee.<your-account>.workers.dev
```

Or point the nameservers to Cloudflare and set it via the dashboard (Workers & Pages → your worker → Triggers → Custom Domain).

## Full Re-Deploy

```bash
./deploy.sh
```

## Favicon

Place a `favicon.png` in the project root. The build script inlines it into the
worker. If missing, the favicon route returns 404.

```bash
./deploy.sh
```
