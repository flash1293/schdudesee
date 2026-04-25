# Was geht, Stutensee? — Cloudflare Deployment

## Prerequisites

- `wrangler` CLI: `npm install -g wrangler`
- Logged in: `wrangler login`

## Deploy DB

```bash
# Create D1 database
wrangler d1 create was-geht-stutensee

# Copy the database_id from output into wrangler.toml

# Import the data
wrangler d1 execute was-geht-stutensee --file dump.sql
```

## Build & Deploy Worker

```bash
# Inline the HTML into the worker
python3 build.py

# Deploy
wrangler deploy
```

## Update wrangler.toml

After `wrangler d1 create`, copy the returned `database_id` into `wrangler.toml`.

## Full Re-Deploy

```bash
python3 build.py && wrangler deploy
```
