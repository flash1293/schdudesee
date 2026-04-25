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

The domain `was-geht-stutensee.de` must be added to your Cloudflare account first
(needs nameservers pointing to Cloudflare). The worker will then serve on it
automatically via `wrangler deploy`.

## Full Re-Deploy

```bash
./deploy.sh
```
