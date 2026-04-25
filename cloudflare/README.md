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
wrangler d1 create was-geht-stutensee
# Copy the database_id from output into wrangler.toml
wrangler d1 execute was-geht-stutensee --file dump.sql
```

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
