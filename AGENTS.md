# Was geht, Stutensee? — Architecture Guide

## Overview

A Stutensee event discovery platform. Scrapes ~20+ sources, deduplicates,
tags, detects recurring events, serves via Cloudflare Workers + D1.

## Data Flow

```
Source Websites
     ↓ (scraping agents + run_pipeline.py)
raw_events table (SQLite)
     ↓ (SQL dedup: exact title+date+location match)
curated_events table
     ↓ (agentic dedup: cross-source fuzzy matching)
     ↓ (auto tagging: keyword-based content + district tags)
     ↓ (recurring detection: weekly/biweekly/monthly)
curated_events → /api/* endpoints → Cloudflare Worker → Browser
```

## Key Files

| File | Purpose |
|------|---------|
| `run_pipeline.py` | Main orchestrator: scrapes 7 primary sources → dedup → tag → recurring |
| `detect_recurring.py` | Weekly/biweekly/monthly pattern detection |
| `server.py` | Local dev server (Python) |
| `db.py` | SQLite schema + insert/dedup helpers |
| `stutensee_events.db` | Local SQLite database (14MB, ~6400 raw, ~6200 curated) |
| `AGENTS.md` | This file — agent instructions |
| `vereins_homepages_annotated.txt` | 93 Verein homepages with event crawl status |

## Deployment

```
cd cloudflare && ./deploy.sh
```

This does: build worker → export DB → import to D1 → deploy worker.

**IMPORTANT:** Always run `./deploy.sh`, NOT just `wrangler deploy` or 
`python3 build.py`. The worker code AND the D1 database must both be updated.

The D1 database is re-created from scratch each time (DROP → CREATE → INSERT).

## Sources

### Primary (in run_pipeline.py)
- stutensee.de/Veranstaltungen — official city calendar
- stutenseekinderkalender.de — REST API (The Events Calendar)
- meinstutensee.de/termine/ — EventON JSON-LD
- buergerwerkstatt-stutensee.de — events + wochenplan
- kath-weistu.de — events + gottesdienste
- buechigerleben.de — community events
- flohmarkt-buechig.de — flea market dates

### Added via club crawl (41 sites with events)
93 club homepages discovered from stutensee.de/Vereine, 41 had event data.
These were scraped by agents but not yet added to run_pipeline.py.

### Other known sources (not yet in pipeline)
See `vereins_homepages_annotated.txt` for full list with status.

## Database Schema

### raw_events
Stores every scraped event as-is. UNIQUE on (source_url, event_url, date_start, title).
Auto-dedup on insert (INSERT OR IGNORE).

### curated_events
Cleaned, deduplicated event data. Created by rebuilding from raw_events each
pipeline run (SQL dedup groups by normalized title + date + location).

Columns: id, title, normalized_title, date_start, date_end, time_raw, location,
organizer, description, event_url, sources, tags, recurring_group_id, dedup_round

### raw_to_curated
Maps raw_events to curated_events for provenance tracking.

## Agentic Dedup

Run when new sources are added or duplicates are reported.

**Purpose:** Merge events that are the same real-world event but appear with
slightly different titles across sources (e.g. "Büchiger Maifest" vs "Maifest Büchig").

**Approach:**
1. Read all curated_events from DB
2. Normalize titles (lowercase, remove punctuation, normalize umlauts, strip suffixes)
3. Group by normalized title + same date (±1 day)
4. For groups with multiple entries, verify location similarity
5. Merge: keep best title, longest description, combine sources
6. Delete duplicates, update the surviving row

## Agentic Tagging

**Phase 1 — Content tags (max 2 per event):**
Read title + description + organizer, judge individually.
Tags: Sport, Musik, Kultur, Kirche, Kinder, Fest, Markt, Workshop, Bildung,
       Natur, Senioren, Digital, Handwerk, Essen, Treff, Politik, Verein,
       Wohltätigkeit, Sonstiges

**Phase 2 — District tags:**
Use LOCATION_MAP keywords to assign: Blankenloch, Büchig, Friedrichstal,
Spöck, Staffort. (Weingarten was removed — not part of Stutensee.)
Spöcker Weg is excluded from Spöck and mapped to Friedrichstal instead.

## Recurring Detection

Groups events by normalized title, detects weekly (7-day), biweekly (14-day),
and monthly (28-31 day) gaps. Assigns recurring_group_id to all matching
events in the same series.

## Standing Agent Instructions

When spawning a dedup agent, use this prompt template:

```
You are running agentic deduplication on the Stutensee events DB.

Read all curated_events from the DB at stutensee_events.db.
Find cross-source duplicates where the same real-world event has slightly
different titles (e.g. "Büchiger Maifest" vs "Maifest Büchig").

For each duplicate group:
1. Verify they're the same event (same date ±1 day, similar location)
2. Keep the best title, longest description, merge sources
3. Delete the duplicate row(s) from curated_events
4. Also delete corresponding raw_to_curated mappings

Report: how many duplicates found and merged.
```

When spawning a scrape agent, use this prompt template:

```
You are scraping Stutensee club websites for events. Read the batch file.

For EACH URL:
1. Fetch it with webfetch (format: html)
2. Look for event data: dates, titles, times, locations
3. Check sub-pages like /termine, /veranstaltungen, /events, /kalender
4. If WordPress, check for REST API at /wp-json/tribe/events/v1/events?per_page=50
5. Extract ALL events you can find

Write all extracted events as JSON array:
[{"source_url": "https://...", "events": [{"title": "...", "date_start": "2026-04-25", ...}]}]

Convert German dates (DD.MM.YYYY) to ISO format (YYYY-MM-DD).
```

## Update Workflow

Always follow this process when updating events:

1. **Backup the DB** — `cp stutensee_events.db stutensee_events.db.backup-$(date +%Y%m%d_%H%M%S)`
2. **Run the pipeline** — `python3 run_pipeline.py`
3. **Validate manually** — check new events, dates, descriptions, check for duplicates
4. **Adjust & rerun if needed** — fix scrapers, rerun, validate again (things change all the time)
5. **Deploy** — `cd cloudflare && ./deploy.sh`

The pipeline now: removes past events, fixes malformed dates, extracts rich data (location, organizer, description) from JSON-LD sources, and filters past events at insert time.

## Cloudflare Worker Build Process

The worker consists of two files:

- **Source (`cloudflare/src/_worker.js`):** Hand-written JavaScript logic — routes, API handlers, DB queries. **This is where you edit API/backend logic.**
- **Generated (`cloudflare/src/worker.js`):** The full worker with inlined HTML + favicon. **This is the deployed file. DO NOT EDIT DIRECTLY** — it's overwritten by `build.py`.

**How builds work:**
1. `cd cloudflare && python3 build.py` reads `../index.html` and `favicon.png`
2. Base64-encodes them, prepends to `src/_worker.js`, and writes to `src/worker.js`
3. `worker.js` is gitignored — only `_worker.js` is tracked

**When editing worker logic:** Edit `cloudflare/src/_worker.js`, then run `python3 build.py`.

**When editing the HTML/CSS:** Edit `../index.html` (the repo root), then run `python3 build.py` to re-inline it into the worker.

**Deploy:** `cd cloudflare && ./deploy.sh` builds the worker AND exports/imports the D1 database.

The site runs on Cloudflare Workers + D1:
- **Worker:** Handles /api/list, /api/theme, /api/info, /api/same/{id} and serves HTML
- **D1:** SQLite-compatible DB, ~14MB, re-imported on each deploy
- **Domain:** was-geht-stutensee.de (via Cloudflare nameservers)
- **Fallback:** was-geht-stutensee.*.workers.dev
