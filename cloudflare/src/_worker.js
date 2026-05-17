export default {
  async fetch(request, env) {
    const url = new URL(request.url);
    if (url.pathname === '/') {
      return new Response(indexHtml, { headers: { 'content-type': 'text/html;charset=utf-8' } });
    }
    if (url.pathname === '/favicon.png' && typeof faviconB64 !== 'undefined' && faviconB64) {
      const img = Uint8Array.from(atob(faviconB64), c => c.charCodeAt(0));
      return new Response(img, { headers: { 'content-type': 'image/png', 'cache-control': 'public, max-age=86400' } });
    }
    if (url.pathname === '/api/list') return serveEvents(env, url);
    if (url.pathname === '/api/theme') return serveTags(env);
    if (url.pathname === '/api/districts') return serveDistricts(env);
    if (url.pathname === '/api/organizer') return serveOrganizers(env);
    if (url.pathname === '/api/info') return serveStats(env);
    if (url.pathname.startsWith('/api/same/')) return serveRecurring(env, url.pathname.split('/').pop());
    if (url.pathname === '/llms.txt') return serveLlmTxt();
    return new Response('Not found', { status: 404 });
  }
};

function decode(s) {
  if (!s) return '';
  return s.replace(/&amp;/g, '&').replace(/&lt;/g, '<').replace(/&gt;/g, '>').replace(/&quot;/g, '"')
    .replace(/&#(\d+);/g, (_, n) => String.fromCharCode(n));
}

function json(data, status = 200) {
  return new Response(JSON.stringify(data), {
    status,
    headers: { 'content-type': 'application/json;charset=utf-8', 'access-control-allow-origin': '*' }
  });
}

async function serveEvents(env, url) {
  const p = url.searchParams;
  const page = Math.max(1, parseInt(p.get('page') || '1'));
  const perPage = Math.min(100, Math.max(1, parseInt(p.get('per_page') || '50')));
  const search = (p.get('search') || '').slice(0, 48);
  const tags = p.getAll('tag').filter(Boolean);
  const dateFrom = p.get('date_from') || '';
  const organizer = p.get('organizer') || '';

  const db = env.STUTENSEE_DB;
  const wheres = ["tags != 'blocked'"];
  const args = [];

  if (dateFrom) { wheres.push("date_start >= ?"); args.push(dateFrom); }
  if (search) { wheres.push("(title LIKE ? OR location LIKE ? OR organizer LIKE ?)"); args.push(`%${search}%`, `%${search}%`, `%${search}%`); }
  for (const t of tags) { wheres.push("tags LIKE ?"); args.push(`%${t}%`); }
  if (organizer) { wheres.push("organizer = ?"); args.push(organizer); }
  if (p.get('hide_recurring')) { wheres.push("recurring_group_id IS NULL"); }

  const where = wheres.length ? 'WHERE ' + wheres.join(' AND ') : '';
  const offset = (page - 1) * perPage;

  const total = (await db.prepare(`SELECT COUNT(*) as c FROM curated_events ${where}`).bind(...args).first()).c;
  const { results } = await db.prepare(
    `SELECT id, title, date_start, date_end, time_raw, location, organizer, description, event_url, sources, tags, recurring_group_id
     FROM curated_events ${where} ORDER BY date_start ASC, id LIMIT ? OFFSET ?`
  ).bind(...args, perPage, offset).all();

  return json({
    events: results.map(r => ({
      id: r.id, title: decode(r.title), date_start: r.date_start || '', date_end: r.date_end,
      time_raw: r.time_raw, location: decode(r.location), organizer: decode(r.organizer),
      description: decode(r.description), event_url: decode(r.event_url || ''),
      sources: decode(r.sources || ''), tags: r.tags || '',
      recurring_group_id: r.recurring_group_id,
    })),
    total, page, per_page: perPage,
    total_pages: Math.ceil(total / perPage),
  });
}

async function serveOrganizers(env) {
  const { results } = await env.STUTENSEE_DB.prepare(
    "SELECT DISTINCT organizer FROM curated_events WHERE organizer IS NOT NULL AND organizer != '' AND tags != 'blocked' ORDER BY organizer"
  ).all();
  return json(results.map(r => decode(r.organizer)));
}

async function serveTags(env) {
  const themeKeys = new Set(['Sport','Musik','Kultur','Kirche','Kinder','Fest','Markt','Workshop','Bildung','Natur','Senioren','Digital','Handwerk','Essen','Treff','Politik','Verein','Wohltätigkeit','Sonstiges']);
  const { results } = await env.STUTENSEE_DB.prepare(
    "SELECT DISTINCT tags FROM curated_events WHERE tags IS NOT NULL AND tags != '' AND tags != 'blocked'"
  ).all();
  const set = new Set();
  for (const r of results) {
    for (const t of r.tags.split(',')) { const s = t.trim(); if (s && themeKeys.has(s)) set.add(s); }
  }
  return json([...set].sort());
}

async function serveDistricts(env) {
  const themeKeys = new Set(['Sport','Musik','Kultur','Kirche','Kinder','Fest','Markt','Workshop','Bildung','Natur','Senioren','Digital','Handwerk','Essen','Treff','Politik','Verein','Wohltätigkeit','Sonstiges']);
  const { results } = await env.STUTENSEE_DB.prepare(
    "SELECT DISTINCT tags FROM curated_events WHERE tags IS NOT NULL AND tags != '' AND tags != 'blocked'"
  ).all();
  const set = new Set();
  for (const r of results) {
    for (const t of r.tags.split(',')) { const s = t.trim(); if (s && !themeKeys.has(s)) set.add(s); }
  }
  return json([...set].sort());
}

async function serveStats(env) {
  const [raw, curated] = await Promise.all([
    env.STUTENSEE_DB.prepare('SELECT COUNT(*) as c FROM raw_events').first(),
    env.STUTENSEE_DB.prepare('SELECT COUNT(*) as c FROM curated_events').first(),
  ]);
  return json({ raw: raw.c, curated: curated.c });
}

async function serveRecurring(env, groupId) {
  const { results } = await env.STUTENSEE_DB.prepare(
    `SELECT id, title, date_start, date_end, time_raw, location, organizer, substr(description,1,300) as description,
            event_url, sources, tags, recurring_group_id
     FROM curated_events WHERE recurring_group_id = ? ORDER BY date_start`
  ).bind(groupId).all();
  return json(results.map(r => ({
    id: r.id, title: decode(r.title), date_start: r.date_start || '', date_end: r.date_end,
    time_raw: r.time_raw, location: decode(r.location), organizer: decode(r.organizer),
    description: decode(r.description), event_url: decode(r.event_url || ''),
    sources: decode(r.sources || ''), tags: r.tags || '',
    recurring_group_id: r.recurring_group_id,
  })));
}

function serveLlmTxt() {
  return new Response(`# Was geht, Stutensee? — Event Calendar API

## About
Was geht, Stutensee? is an event calendar for Stutensee, Germany. It aggregates events from 20+ sources including the official city calendar, club websites, cultural institutions, and neighboring municipalities. All data is served via a Cloudflare Worker backed by D1 (SQLite-compatible) database.

## Base URL
https://was-geht-stutensee.de (production)
https://was-geht-stutensee-staging.email-0d0.workers.dev (staging)

## API Endpoints

### GET /api/list — List events
Returns paginated events with optional filtering.

Query parameters:
- page (int, default: 1) — page number
- per_page (int, default: 50, max: 100) — events per page
- search (string) — search in title, location, organizer
- tag (string, repeatable) — filter by theme or district tag
- date_from (ISO date, e.g. 2026-05-06) — show events from this date onward
- organizer (string) — filter by exact organizer name
- hide_recurring (boolean) — if set, hide recurring event series

Response:
{
  "events": [
    {
      "id": 1234,
      "title": "Event Title",
      "date_start": "2026-05-10",
      "date_end": null,
      "time_raw": "19:00",
      "location": "Venue, Street, City",
      "organizer": "Organizer Name",
      "description": "Event description text.",
      "event_url": "https://example.com/event",
      "sources": "https://source1.de,https://source2.de",
      "tags": "Sport,Fest,Blankenloch",
      "recurring_group_id": null
    }
  ],
  "total": 150,
  "page": 1,
  "per_page": 50,
  "total_pages": 3
}

Notes:
- title, location, organizer, description, event_url, sources are HTML-decoded
- tags is a comma-separated string of theme tags (e.g. Sport, Musik, Kultur, Kirche, Kinder, Fest, Markt) and district tags (e.g. Blankenloch, Büchig, Friedrichstal, Spöck, Staffort, Weingarten, Bruchsal, etc.)
- district tags are auto-derived from location text
- events without a date_start are excluded
- blocked/spam events have tags='blocked' and are excluded

### GET /api/theme — List theme categories
Returns sorted array of all active theme tags (e.g. ["Bildung","Digital","Essen","Fest","Handwerk","Kinder","Kirche","Kultur","Markt","Musik","Natur","Politik","Senioren","Sport","Treff","Verein","Wohltätigkeit","Workshop","Sonstiges"]).

### GET /api/districts — List district tags
Returns sorted array of all active district/location tags (e.g. ["Blankenloch","Bruchsal","Büchig","Eggenstein","Friedrichstal","Graben-Neudorf","Hagsfeld","Leopoldshafen","Linkenheim","Neuthard","Rintheim","Spöck","Staffort","Waldstadt","Weingarten"]).

### GET /api/organizer — List organizers
Returns sorted array of unique organizer names.

### GET /api/info — Event counts
Returns raw event count and curated event count: { "raw": 6000, "curated": 5400 }

### GET /api/same/:id — Recurring events
Returns all events in the same recurring group as the event with the given ID.

### GET / — Web UI
Returns the full single-page application HTML with inline CSS and JS. Features include:
- Search by keyword
- Date range filter
- Filter by theme category (emoji-based)
- Filter by district/location
- Filter by organizer
- Toggle between normal and compact view
- Toggle recurring events visibility
- Pagination
- Recurring event group expansion

## Data Freshness
Event data is updated weekly via a scraping pipeline (scrape_and_merge.py). Sources include:
- stutensee.de (official city calendar)
- stutenseekinderkalender.de (children's calendar)
- meinstutensee.de (community calendar)
- Individual club/verein websites (40+)
- Neighboring municipality calendars (Linkenheim, Graben-Neudorf, Weingarten, Bruchsal, Eggenstein, etc.)

## Terms
This API is free and public. No authentication required. No rate limiting currently enforced. Data is provided as-is without guarantee of completeness or accuracy.`, {
    headers: { 'content-type': 'text/plain;charset=utf-8', 'cache-control': 'public, max-age=3600' }
  });
}
