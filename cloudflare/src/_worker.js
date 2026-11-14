import { ensureAnalyticsTable, logRequest, classifyUserAgent } from './_analytics.js';

// ── SSR Constants ─────────────────────────────────────────────────────
const THEME_KEYS = new Set(['Sport','Musik','Kultur','Kirche','Kinder','Fest','Markt','Workshop','Bildung','Natur','Senioren','Digital','Handwerk','Essen','Treff','Politik','Verein','Wohltätigkeit','Sonstiges']);

const DISTRICT_KEYS = new Set(['Blankenloch','Bruchsal','Bretten','Büchenau','Büchig','Durlach','Eggenstein','Friedrichstal','Graben-Neudorf','Hagsfeld','Karlsruhe-Innenstadt','Leopoldshafen','Linkenheim','Neureut','Neuthard','Rintheim','Spöck','Staffort','Waldstadt','Weingarten']);
const DISTRICT_LIST_STR = [...DISTRICT_KEYS].sort().join(', ');

const SSR_PER_PAGE = 12;

// Inline stroke icons (no emoji, consistent weight across platforms).
const ICON = {
  clock: '<svg class="icon" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><circle cx="12" cy="12" r="9"/><path d="M12 7v5l3 2"/></svg>',
  pin: '<svg class="icon" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M20 10c0 6-8 12-8 12S4 16 4 10a8 8 0 1 1 16 0z"/><circle cx="12" cy="10" r="3"/></svg>',
  arrow: '<svg class="icon" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M5 12h14M13 6l6 6-6 6"/></svg>',
  star: '<svg class="icon" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="currentColor" aria-hidden="true"><path d="m12 3.6 2.6 5.3 5.9.9-4.3 4.1 1 5.8-5.2-2.7-5.2 2.7 1-5.8L3.5 9.8l5.9-.9z"/></svg>',
};

// ── Exports ───────────────────────────────────────────────────────────
export default {
  async fetch(request, env, ctx) {
    const startTime = Date.now();
    try { await ensureAnalyticsTable(env); } catch {}
    let response;
    try {
      response = await routeRequest(request, env, ctx);
    } catch (err) {
      console.error('Worker error:', err.message);
      response = new Response('Internal error', { status: 500 });
    }
    ctx.waitUntil(logRequest(env, request, response, startTime));
    return response;
  }
};

// ── Router ────────────────────────────────────────────────────────────
async function routeRequest(request, env, ctx) {
  const url = new URL(request.url);

  // Serve SSR-enhanced HTML for the main page
  if (url.pathname === '/') return serveSsrPage(env, url);

  // Static assets (served from build-embedded constants)
  if (url.pathname === '/favicon.png' && typeof faviconB64 !== 'undefined' && faviconB64) {
    const img = Uint8Array.from(atob(faviconB64), c => c.charCodeAt(0));
    return new Response(img, { headers: { 'content-type': 'image/png', 'cache-control': 'public, max-age=86400' } });
  }
  // Redirect /favicon.ico to /favicon.png (browser convention)
  if (url.pathname === '/favicon.ico') {
    return new Response(null, { status: 301, headers: { 'location': '/favicon.png', 'cache-control': 'public, max-age=31536000' } });
  }

  // Serve app.*.js (hashed) or app.js with long cache for hashed, short for unhashed
  if ((url.pathname === '/app.js' || /^\/app\.[a-f0-9]+\.js$/.test(url.pathname)) && typeof appJs !== 'undefined' && appJs) {
    const isHashed = /^\/app\.[a-f0-9]+\.js$/.test(url.pathname);
    return new Response(appJs, { headers: { 'content-type': 'application/javascript;charset=utf-8', 'cache-control': isHashed ? 'public, max-age=31536000, immutable' : 'public, max-age=86400' } });
  }
  if ((url.pathname === '/chat.js' || /^\/chat\.[a-f0-9]+\.js$/.test(url.pathname)) && typeof chatJs !== 'undefined' && chatJs) {
    const isHashed = /^\/chat\.[a-f0-9]+\.js$/.test(url.pathname);
    return new Response(chatJs, { headers: { 'content-type': 'application/javascript;charset=utf-8', 'cache-control': isHashed ? 'public, max-age=31536000, immutable' : 'public, max-age=86400' } });
  }

  // API routes
  if (url.pathname === '/api/list') return serveEvents(env, url);
  if (url.pathname === '/api/featured') return serveFeatured(env);
  if (url.pathname === '/api/chat' && request.method === 'POST') return serveChat(request, env);
  if (url.pathname === '/api/theme') return cachedResponse(env, ctx, url.toString(), CACHE_TTL_DAILY, () => serveTags(env));
  if (url.pathname === '/api/districts') return cachedResponse(env, ctx, url.toString(), CACHE_TTL_DAILY, () => serveDistricts(env));
  if (url.pathname === '/api/organizer') return cachedResponse(env, ctx, url.toString(), CACHE_TTL_DAILY, () => serveOrganizers(env));
  if (url.pathname === '/api/info') return serveStats(env);
  if (url.pathname === '/api/stats') return serveReqStats(env);
  if (url.pathname === '/robots.txt') return serveRobotsTxt();
  if (url.pathname.startsWith('/api/same/')) return serveRecurring(env, url.pathname.split('/').pop());
  if (url.pathname === '/llms.txt') return serveLlmTxt();
  if (url.pathname === '/.well-known/security.txt') return serveSecurityTxt();
  if (url.pathname === '/sitemap.xml') return cachedResponse(env, ctx, url.toString(), CACHE_TTL_DAILY, () => serveSitemapXml(env));

  // Event detail pages: /events/{id}/{slug}
  if (url.pathname.startsWith('/events/')) return serveEventPage(env, url, ctx);

  return serve404();
}

// ── Cache helpers (reduce full-table D1 scans on read-only data) ──────
const CACHE_TTL_DAILY = 86400; // DB is rebuilt once daily by the pipeline
const EVENT_INDEX_CACHE_KEY = 'https://hey-stutensee.de/__internal__/event-index-v1';

/** Wrap a read-only producer in the Cache API. Falls back to direct production
 *  when the Cache API is unavailable (e.g. in unit tests). */
async function cachedResponse(env, ctx, key, ttlSeconds, producer) {
  if (typeof caches === 'undefined' || !caches.default) {
    return producer();
  }
  const cache = caches.default;
  const cached = await cache.match(key);
  if (cached) return cached;
  const response = await producer();
  if (response && response.ok) {
    const copy = response.clone();
    copy.headers.set('cache-control', `public, max-age=${ttlSeconds}`);
    if (ctx && typeof ctx.waitUntil === 'function') ctx.waitUntil(cache.put(key, copy));
    else await cache.put(key, copy);
  }
  return response;
}

/** Full {id,title} event list, cached daily. Lets the slug fallback do an
 *  in-memory lookup instead of full-scanning curated_events on every old URL. */
async function getEventIndex(env, ctx) {
  const load = async () => {
    const { results } = await env.STUTENSEE_DB.prepare(
      `SELECT id, title FROM curated_events WHERE tags != 'blocked'`
    ).all();
    return results.map(r => ({ id: r.id, title: r.title }));
  };
  if (typeof caches === 'undefined' || !caches.default) {
    return load();
  }
  const cache = caches.default;
  const cached = await cache.match(EVENT_INDEX_CACHE_KEY);
  if (cached) return await cached.json();
  const list = await load();
  const response = new Response(JSON.stringify(list), {
    headers: { 'content-type': 'application/json', 'cache-control': `public, max-age=${CACHE_TTL_DAILY}` }
  });
  if (ctx && typeof ctx.waitUntil === 'function') ctx.waitUntil(cache.put(EVENT_INDEX_CACHE_KEY, response.clone()));
  else await cache.put(EVENT_INDEX_CACHE_KEY, response);
  return list;
}

// ── SSR Helpers ───────────────────────────────────────────────────────

/** Create a URL-safe slug from an event title. */
function slugify(str) {
  if (!str) return '';
  return str
    .toLowerCase()
    .replace(/[ä]/g, 'ae').replace(/[ö]/g, 'oe').replace(/[ü]/g, 'ue').replace(/[ß]/g, 'ss')
    .replace(/[^a-z0-9]+/g, '-')
    .replace(/^-+|-+$/g, '')
    .substring(0, 80);
}

/** Simple HTML-escape (no DOM available in worker). */
function escapeHtml(s) {
  if (!s) return '';
  return s
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;');
}

/** Inline brand mark (S + waves). `suffix` keeps SVG clip-path ids unique per page. */
function brandMarkSvg(suffix = 'x') {
  const id = escapeHtml(String(suffix).replace(/[^a-z0-9_-]/gi, ''));
  return `<svg xmlns="http://www.w3.org/2000/svg" viewBox="4 4 100 96" focusable="false" aria-hidden="true">
      <defs>
        <clipPath id="s-clip-${id}"><text x="54" y="78" text-anchor="middle" font-family="system-ui,-apple-system,sans-serif" font-weight="800" font-size="80">S</text></clipPath>
        <clipPath id="tip-clip-${id}"><rect x="52" y="8" width="24" height="32"/></clipPath>
      </defs>
      <text x="54" y="78" text-anchor="middle" font-family="system-ui,-apple-system,sans-serif" font-weight="800" font-size="80" fill="none" stroke="#ffffff" stroke-width="4" stroke-linejoin="round">S</text>
      <text x="54" y="78" text-anchor="middle" font-family="system-ui,-apple-system,sans-serif" font-weight="800" font-size="80" fill="#fab800">S</text>
      <text x="54" y="78" text-anchor="middle" font-family="system-ui,-apple-system,sans-serif" font-weight="800" font-size="80" fill="#dd291a" clip-path="url(#tip-clip-${id})">S</text>
      <g clip-path="url(#s-clip-${id})">
        <path d="M-5 60 Q5 54 15 60 Q25 66 35 60 Q45 54 55 60 Q65 66 75 60 Q85 54 95 60" stroke="#0d3a71" stroke-width="10" fill="none" stroke-linecap="round"/>
        <path d="M-5 69 Q5 63 15 69 Q25 75 35 69 Q45 63 55 69 Q65 75 75 69 Q85 63 95 69" stroke="#1a5299" stroke-width="10" fill="none" stroke-linecap="round"/>
        <path d="M-5 78 Q5 72 15 78 Q25 84 35 78 Q45 72 55 78 Q65 84 75 78 Q85 72 95 78" stroke="#3a7bc8" stroke-width="10" fill="none" stroke-linecap="round"/>
      </g>
    </svg>`;
}

/** Safely serialize a value for embedding in a <script> tag (prevents XSS via </script>). */
function jsonForScriptTag(value) {
  return JSON.stringify(value)
    .replace(/</g, '\\u003c')
    .replace(/\u2028/g, '\\u2028')
    .replace(/\u2029/g, '\\u2029');
}

/** Format ISO date to German format. */
function fmtDate(iso) {
  if (!iso) return '?';
  const p = iso.split('-');
  return p.length === 3 ? `${p[2]}.${p[1]}.${p[0]}` : iso;
}

/** Build a URL slug from an event title (without the ID prefix). */
function eventSlug(event) {
  return slugify(decode(event.title || ''));
}

/** Build the full event URL path: /events/{id}/{slug}. */
function eventPath(event) {
  return `/events/${event.id}/${eventSlug(event)}`;
}

/** Fetch events and related metadata for SSR. Returns {events, total, page, totalPages, ...}. */
async function fetchEventsForSsr(env, url) {
  const p = url.searchParams;
  const page = Math.max(1, parseInt(p.get('page') || '1'));
  const perPage = SSR_PER_PAGE;
  const search = (p.get('search') || '').slice(0, 48);
  const tags = p.getAll('tag').filter(Boolean);
  const dateFrom = p.get('date_from') || new Date().toISOString().slice(0, 10);
  const organizer = p.get('organizer') || '';
  const hideRecurring = p.get('hide_recurring') === 'true';

  const db = env.STUTENSEE_DB;
  const wheres = ["tags != 'blocked'", "is_passed = 0", "(featured = 0 OR featured IS NULL)"];
  const args = [];

  if (dateFrom) { wheres.push("date_start >= ?"); args.push(dateFrom); }
  if (search) { wheres.push("(title LIKE ? OR location LIKE ? OR organizer LIKE ?)"); args.push(`%${search}%`, `%${search}%`, `%${search}%`); }
  for (const t of tags) { wheres.push("tags LIKE ?"); args.push(`%${t}%`); }
  if (organizer) { wheres.push("organizer = ?"); args.push(organizer); }
  if (hideRecurring) { wheres.push("recurring_group_id IS NULL"); }

  const where = wheres.length ? 'WHERE ' + wheres.join(' AND ') : '';
  const offset = (page - 1) * perPage;

  const total = (await db.prepare(`SELECT COUNT(*) as c FROM curated_events ${where}`).bind(...args).first()).c;
  const totalPages = Math.ceil(total / perPage);

  const { results } = await db.prepare(
    `SELECT id, title, date_start, date_end, time_raw, location, organizer, description, event_url, sources, tags, recurring_group_id, featured
     FROM curated_events ${where} ORDER BY date_start ASC, featured DESC, id LIMIT ? OFFSET ?`
  ).bind(...args, perPage, offset).all();

  return { events: results, total, page, totalPages, perPage, dateFrom };
}

/** Fetch up to 6 upcoming featured events for the hero section. */
async function fetchFeaturedEvents(env) {
  const db = env.STUTENSEE_DB;
  const { results } = await db.prepare(
    `SELECT id, title, date_start, date_end, time_raw, location, organizer, description, event_url, sources, tags, recurring_group_id, featured
     FROM curated_events WHERE featured = 1 AND tags != 'blocked'
     AND (tags LIKE '%Blankenloch%' OR tags LIKE '%Friedrichstal%' OR tags LIKE '%Spöck%' OR tags LIKE '%Staffort%' OR tags LIKE '%Büchig%')
     ORDER BY date_start ASC LIMIT 4`
  ).all();
  return results;
}

// ── Card presentation helpers ─────────────────────────────────────────

// Description cleanup: scraped pages often carry icon rows, contact blocks and
// metadata labels ("Datum", "Veranstalter", "Auf Karte anzeigen"). We keep only
// prose-like lines and drop the rest so cards don't show machine noise.
const DESC_JUNK_LINE = /^(?:icon\.[\w.]+|auf karte anzeigen|karte|zur website|website|e-?mail(?: schreiben)?|telefonnummer:?|faxnummer:?|veranstalter|veranstaltungsort|datum|uhrzeit|beschreibung|anfahrt|öffnungszeiten|kontakt)$/i;
const DESC_CONTACT_LINE = /^(?:postfach\b|tel\.?:?\s|\+?\(?\d[\d\s()\/-]{8,}$|.*@.*\.[a-z]{2,}$)/i;
const DESC_WEEKDAY_RE = /\b(?:montag|dienstag|mittwoch|donnerstag|freitag|samstag|sonntag)\b/gi;

function normalizeText(raw) {
  return String(raw || '').replace(/\u00a0/g, ' ').replace(/\r/g, '').replace(/[ \t]+/g, ' ').trim();
}

/** Split a scraped description into blocks that still contain readable prose. */
function descriptionBlocks(raw) {
  if (!raw) return [];
  const text = normalizeText(raw);
  const blocks = [];
  for (const chunk of text.split(/\n\s*\n/)) {
    const kept = [];
    for (const rawLine of chunk.split('\n')) {
      const line = rawLine.trim();
      if (!line) continue;
      if (DESC_JUNK_LINE.test(line) || DESC_CONTACT_LINE.test(line)) continue;
      if (line.split(/\s+/).length < 7 && !/[.!?]$/.test(line)) continue;
      kept.push(line);
    }
    const joined = kept.join(' ').replace(/\s{2,}/g, ' ').trim();
    if (joined.length < 40) continue;
    if ((joined.match(DESC_WEEKDAY_RE) || []).length >= 3 && joined.length < 400) continue;
    blocks.push(joined);
  }
  return blocks;
}

function cleanDescription(raw) {
  const blocks = descriptionBlocks(raw);
  if (blocks.length) return blocks.join('\n\n');
  const text = normalizeText(raw);
  const looksScraped = /(?:icon\.|Auf Karte anzeigen|Zur Website|Telefonnummer|Faxnummer|E-Mail schreiben)/i.test(text) || /^Datum$/m.test(text);
  return looksScraped ? '' : text.replace(/\s+/g, ' ');
}

function summarizeDescription(raw) {
  const blocks = descriptionBlocks(raw);
  if (!blocks.length) return cleanDescription(raw);
  return blocks.reduce((a, b) => (b.length > a.length ? b : a));
}

/** Human time label: "19:00 Uhr", "Ganztägig", or empty when unknown. */
function timeLabel(raw) {
  const t = (raw || '').trim();
  if (!t) return '';
  if (/^0?0[:.]00(\s*(–|-|bis)\s*0?0[:.]00)?$/.test(t)) return 'Ganztägig';
  return t;
}

/** First meaningful category tag of an event. */
function categoryOf(tags) {
  return tags.find(t => THEME_KEYS.has(t) && t !== 'Sonstiges') || '';
}

/** German weekday for an ISO date string. */
function weekdayDe(iso) {
  if (!iso) return '';
  const names = ['Sonntag', 'Montag', 'Dienstag', 'Mittwoch', 'Donnerstag', 'Freitag', 'Samstag'];
  const d = new Date(`${iso}T00:00:00`);
  return isNaN(d.getTime()) ? '' : names[d.getDay()];
}

/** Format an integer with German thousands separators. */
function formatCount(n) {
  return String(n).replace(/\B(?=(\d{3})+(?!\d))/g, '.');
}

/** Relative day label, only when it is meaningful ("Heute", "Morgen", "In 5 Tagen"). */
function relativeDayLabel(iso) {
  const rel = relativeDate(iso);
  return /^(Heute|Morgen|In \d)/.test(rel) ? rel : '';
}

/** Render a single event card HTML (server-side). */
function renderEventCard(event, condensedMode = false) {
  const e = event;
  const tags = (e.tags || '').split(',').map(t => t.trim()).filter(Boolean);
  const locTags = tags.filter(t => DISTRICT_KEYS.has(t));
  const category = categoryOf(tags);

  const title = decode(e.title || '');
  const location = decode(e.location || '');
  const organizer = decode(e.organizer || '');
  const description = summarizeDescription(decode(e.description || ''));
  const time = timeLabel(e.time_raw);
  const path = eventPath(e);
  const place = location || locTags[0] || '';

  const titleEscaped = escapeHtml(title);
  const titleAria = escapeHtml(title || 'Veranstaltung');
  const condensedLoc = place ? `<span class="condensed-location">${escapeHtml(place)}</span>` : '';

  const recur = e.recurring_group_id
    ? `<button type="button" class="recurring-toggle" onclick="event.stopPropagation();toggleRecurring(${e.id}, ${e.recurring_group_id}, this)">▸ Alle Termine</button><div id="recurring-${e.id}" class="recurring-list" style="display:none"></div>`
    : '';

  return `<article class="event${condensedMode ? ' condensed' : ''}" id="event-${e.id}" aria-label="${titleAria}">
      <div class="event-body">
        <div class="event-top${category ? '' : ' no-cat'}">
          ${category ? `<span class="event-cat">${escapeHtml(category)}</span>` : ''}
          ${time ? `<span class="event-time">${ICON.clock}${escapeHtml(time)}</span>` : ''}
        </div>
        <h2><a href="${escapeHtml(path)}">${titleEscaped}</a>${condensedLoc}</h2>
        ${place ? `<p class="event-where">${ICON.pin}<span>${escapeHtml(place)}</span></p>` : ''}
        ${description ? `<p class="event-desc">${escapeHtml(description)}</p>` : ''}
        <div class="event-tags">
          ${organizer ? `<span class="tag tag-organizer" title="Veranstalter">${escapeHtml(organizer)}</span>` : ''}
          ${locTags.slice(0, 2).map(t => `<span class="tag tag-location">${escapeHtml(t)}</span>`).join('')}
          <a class="event-more" href="${escapeHtml(path)}" aria-label="Details zu ${titleAria}">Details${ICON.arrow}</a>
        </div>
        ${recur}
      </div>
    </article>`;
}

/** Format a date string into a badge object { day, month }. */
function formatDateBadge(dateStr) {
  if (!dateStr) return { day: '?', month: '??' };
  const parts = dateStr.split('-');
  if (parts.length === 3) {
    const d = parseInt(parts[2], 10);
    const months = ['Jan','Feb','Mär','Apr','Mai','Jun','Jul','Aug','Sep','Okt','Nov','Dez'];
    const m = months[parseInt(parts[1], 10) - 1] || '??';
    return { day: d, month: m };
  }
  return { day: dateStr, month: '' };
}

/** Compute a relative date label (same as client-side for consistency). */
function relativeDate(iso) {
  if (!iso) return '';
  const today = new Date();
  today.setHours(0, 0, 0, 0);
  const parts = iso.split('-');
  if (parts.length !== 3) return fmtDate(iso);
  const event = new Date(parseInt(parts[0]), parseInt(parts[1]) - 1, parseInt(parts[2]));
  event.setHours(0, 0, 0, 0);
  const diffMs = event - today;
  const diffDays = Math.round(diffMs / 86400000);
  if (diffDays < 0) return fmtDate(iso);
  if (diffDays === 0) return 'Heute';
  if (diffDays === 1) return 'Morgen';
  if (diffDays <= 60) return `In ${diffDays} Tagen`;
  const diffMonths = (event.getFullYear() - today.getFullYear()) * 12 + (event.getMonth() - today.getMonth());
  if (diffMonths <= 0) return fmtDate(iso);
  return `In ${diffMonths} Monaten`;
}

/** Render multiple event cards with sticky date separators. */
function renderEventCards(events) {
  if (!events || events.length === 0) return '';
  const dated = events.filter(e => e.date_start);
  if (dated.length === 0) return '';
  let lastDate = null;
  const parts = [];
  for (const e of dated) {
    if (e.date_start !== lastDate) {
      lastDate = e.date_start;
      const badge = formatDateBadge(e.date_start);
      const rel = relativeDayLabel(e.date_start);
      parts.push(`<div class="date-separator" role="separator" aria-label="${escapeHtml(fmtDate(e.date_start))}">
        <span class="ds-day">${badge.day}</span>
        <span class="ds-month">${badge.month}</span>
        <span class="ds-weekday">${weekdayDe(e.date_start)}</span>
        ${rel ? `<span class="ds-rel${rel === 'Heute' ? ' today' : ''}">${escapeHtml(rel)}</span>` : ''}
      </div>`);
    }
    parts.push(renderEventCard(e));
  }
  return parts.join('\n');
}

/** Render a single featured event card. */
function renderFeaturedCard(event) {
  const e = event;
  const tags = (e.tags || '').split(',').map(t => t.trim()).filter(Boolean);
  const locTags = tags.filter(t => DISTRICT_KEYS.has(t));
  const category = categoryOf(tags) || 'Empfohlen';
  const badge = formatDateBadge(e.date_start);
  const path = eventPath(e);
  const title = decode(e.title || '');
  const place = decode(e.location || '') || locTags[0] || '';
  const time = timeLabel(e.time_raw);

  return `<article class="featured-card" aria-label="${escapeHtml(title || 'Veranstaltung')}">
    <div class="fc-badge"><span class="fc-day">${badge.day}</span><span class="fc-month">${badge.month}</span></div>
    <div class="fc-body">
      <span class="fc-kicker">${escapeHtml(category)}</span>
      <h3 class="fc-title"><a href="${escapeHtml(path)}">${escapeHtml(title)}</a></h3>
      <div class="fc-meta">
        ${time ? `<span>${ICON.clock}<span>${escapeHtml(time)}</span></span>` : ''}
        ${place ? `<span>${ICON.pin}<span>${escapeHtml(place)}</span></span>` : ''}
      </div>
    </div>
  </article>`;
}

/** Render the featured events section. */
function renderFeaturedSection(events) {
  if (!events || events.length === 0) return '';
  let html = `<section class="featured" aria-labelledby="featured-heading">
    <div class="featured-head">
      <h2 class="featured-heading" id="featured-heading">${ICON.star} Empfohlen</h2>
      <span class="featured-sub">Handverlesene Termine</span>
    </div>
    <div class="featured-grid">`;
  for (const e of events) {
    html += renderFeaturedCard(e);
  }
  html += '</div></section>';
  return html;
}

/** Render JSON-LD for an array of events. */
function renderJsonLd(events) {
  if (!events || events.length === 0) return '';
  const items = events.map(e => {
    const tags = (e.tags || '').split(',').map(t => t.trim()).filter(Boolean);
    const locTags = tags.filter(t => DISTRICT_KEYS.has(t));
    const locationName = locTags.length > 0 ? locTags[0] : (e.location || 'Stutensee');
    const desc = e.description ? decode(e.description) : `Veranstaltung in ${locationName}`;
    const url = e.event_url || `https://hey-stutensee.de${eventPath(e)}`;
    return {
      '@context': 'https://schema.org',
      '@type': 'Event',
      name: decode(e.title),
      startDate: e.date_start || undefined,
      endDate: e.date_end || undefined,
      eventAttendanceMode: 'https://schema.org/OfflineEventAttendanceMode',
      eventStatus: 'https://schema.org/EventScheduled',
      location: {
        '@type': 'Place',
        name: locationName,
        address: { '@type': 'PostalAddress', addressLocality: locationName }
      },
      description: desc,
      url,
      organizer: e.organizer ? {
        '@type': 'Organization',
        name: decode(e.organizer)
      } : undefined,
      image: undefined,
    };
  });
  return `<script type="application/ld+json">${jsonForScriptTag(items.length === 1 ? items[0] : items)}</script>`;
}

/** Render breadcrumb JSON-LD for a page. */
function renderBreadcrumbJsonLd(items) {
  if (!items || items.length === 0) return '';
  const itemListElement = items.map((item, i) => ({
    '@type': 'ListItem',
    position: i + 1,
    name: item.name,
    item: item.url,
  }));
  return `<script type="application/ld+json">${jsonForScriptTag({
    '@context': 'https://schema.org',
    '@type': 'BreadcrumbList',
    itemListElement,
  })}</script>`;
}

/** Build the list of page numbers to show (with null markers for ellipses). */
function pageWindow(current, total) {
  if (total <= 7) return Array.from({ length: total }, (_, i) => i + 1);
  const pages = new Set([1, total, current, current - 1, current + 1]);
  if (current <= 3) [2, 3, 4].forEach(p => pages.add(p));
  if (current >= total - 2) [total - 1, total - 2, total - 3].forEach(p => pages.add(p));
  const sorted = [...pages].filter(p => p >= 1 && p <= total).sort((a, b) => a - b);
  const out = [];
  let prev = 0;
  for (const p of sorted) {
    if (prev && p - prev > 1) out.push(null);
    out.push(p);
    prev = p;
  }
  return out;
}

/** Render pagination as <a> links for crawlers (JS upgrades it to buttons). */
function renderPaginationLinks(page, totalPages, params) {
  if (totalPages <= 1) return '';

  function buildUrl(p) {
    const u = new URL('https://hey-stutensee.de/');
    if (p > 1) u.searchParams.set('page', p);
    if (params) {
      for (const [k, v] of params) {
        if (k !== 'page') u.searchParams.append(k, v);
      }
    }
    return u.pathname + u.search;
  }

  const prevIcon = '<svg class="icon" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="m15 18-6-6 6-6"/></svg>';
  const nextIcon = '<svg class="icon" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="m9 18 6-6-6-6"/></svg>';

  let html = '<nav aria-label="Seitennavigation">';
  if (page > 1) {
    html += `<a href="${buildUrl(page - 1)}" class="page-link" rel="prev" aria-label="Vorherige Seite">${prevIcon}</a>`;
  } else {
    html += `<span class="page-btn" aria-hidden="true">${prevIcon}</span>`;
  }

  for (const p of pageWindow(page, totalPages)) {
    if (p === null) {
      html += '<span class="page-ellipsis" aria-hidden="true">…</span>';
    } else if (p === page) {
      html += `<span class="page-link current" aria-current="page">${p}</span>`;
    } else {
      html += `<a href="${buildUrl(p)}" class="page-link">${p}</a>`;
    }
  }

  if (page < totalPages) {
    html += `<a href="${buildUrl(page + 1)}" class="page-link" rel="next" aria-label="Nächste Seite">${nextIcon}</a>`;
  } else {
    html += `<span class="page-btn" aria-hidden="true">${nextIcon}</span>`;
  }
  html += `<span class="page-info">Seite ${page} von ${totalPages}</span>`;
  html += '</nav>';
  return html;
}

/** Render the hero intro paragraph (page 1 only). */
function renderIntro() {
  return `<p class="hero-intro">Der Veranstaltungskalender für Stutensee und Umgebung – Feste, Märkte, Konzerte, Sport und Kinderangebote aus <strong>Blankenloch</strong>, <strong>Büchig</strong>, <strong>Friedrichstal</strong>, <strong>Spöck</strong> und <strong>Staffort</strong>.</p>`;
}

/** Render OG meta tags and Twitter Card tags. */
function renderOgTags(title, description, url, type = 'website') {
  const escapedTitle = escapeHtml(title);
  const escapedDesc = escapeHtml(description);
  const escapedUrl = escapeHtml(url);
  return `<meta property="og:title" content="${escapedTitle}">
<meta property="og:description" content="${escapedDesc}">
<meta property="og:type" content="${type}">
<meta property="og:url" content="${escapedUrl}">
<meta property="og:locale" content="de_DE">
<meta name="twitter:card" content="summary_large_image">
<meta name="twitter:title" content="${escapedTitle}">
<meta name="twitter:description" content="${escapedDesc}">
`;
}

/** Inject SSR content into the HTML template. */
function injectIntoTemplate(template, { events, page, totalPages, jsonLd, breadcrumbJsonLd, paginationHtml, introHtml, featuredHtml, countHtml, initialData, ogTags }) {
  return template
    .replace('<!--SSR_COUNT-->', countHtml || '')
    .replace('<!--SSR_OG_TAGS-->', ogTags || '')
    .replace('<!--SSR_JSON_LD-->', jsonLd || '')
    .replace('<!--SSR_BREADCRUMB-->', breadcrumbJsonLd || '')
    .replace('<!--SSR_FEATURED-->', featuredHtml || '')
    .replace('<!--SSR_INTRO-->', introHtml || '')
    .replace('<!--SSR_EVENTS-->', events || '')
    .replace('<!--SSR_PAGINATION-->', paginationHtml || '')
    .replace('<!--SSR_INITIAL_DATA-->', initialData ? `<script id="ssr-data" type="application/json">${jsonForScriptTag(initialData)}</script>` : '');
}

/** Serve the main page with SSR content injected. Gracefully falls back to plain SPA if DB is unavailable. */
async function serveSsrPage(env, url) {
  try {
    const result = await fetchEventsForSsr(env, url);

    // Fetch featured events (only on page 1)
    let featuredEvents = [];
    if (result.page === 1) {
      try {
        featuredEvents = await fetchFeaturedEvents(env);
      } catch (e) {
        // Non-critical: featured section can fail silently
        console.error('Featured events fetch error:', e.message);
      }
    }

    // Render event cards
    const eventCardsHtml = renderEventCards(result.events);

    // Render featured section (only on page 1)
    const featuredHtml = result.page === 1 ? renderFeaturedSection(featuredEvents) : '';

    // Render JSON-LD (include featured events)
    const jsonLdHtml = renderJsonLd(result.events);

    // Render pagination links
    const paginationHtml = renderPaginationLinks(result.page, result.totalPages, url.searchParams);

    // Render breadcrumb for listing pages
    const breadcrumbItems = [{ name: 'Hey, Stutensee!', url: 'https://hey-stutensee.de/' }];
    if (result.page > 1) {
      breadcrumbItems.push({ name: `Seite ${result.page}`, url: `https://hey-stutensee.de/?page=${result.page}` });
    }
    const breadcrumbJsonLdHtml = renderBreadcrumbJsonLd(breadcrumbItems);

    // Render intro text (only on page 1)
    const introHtml = result.page === 1 ? renderIntro() : '';

    // Build initial data for JS hydration (use actual dateFrom used in SSR query)
    const params = {
      search: url.searchParams.get('search') || '',
      date_from: result.dateFrom || '',
      selectedThemes: url.searchParams.getAll('tag').filter(t => THEME_KEYS.has(t)),
      selectedLocations: url.searchParams.getAll('tag').filter(t => DISTRICT_KEYS.has(t)),
      selectedOrganizer: url.searchParams.get('organizer') || '',
      showRecurring: url.searchParams.get('hide_recurring') !== 'true',
      condensedMode: false,
      districtKeys: [...DISTRICT_KEYS],
      themeKeys: [...THEME_KEYS],
    };

    // Build initial data payload for JS
    const initialData = {
      events: result.events.map(e => ({
        id: e.id,
        title: decode(e.title),
        date_start: e.date_start || '',
        date_end: e.date_end,
        time_raw: e.time_raw,
        location: decode(e.location),
        organizer: decode(e.organizer),
        description: decode(e.description),
        event_url: decode(e.event_url || ''),
        sources: decode(e.sources || ''),
        tags: e.tags || '',
        recurring_group_id: e.recurring_group_id,
        featured: e.featured || 0,
      })),
      featuredEvents: featuredEvents.map(e => ({
        id: e.id,
        title: decode(e.title),
        date_start: e.date_start || '',
        date_end: e.date_end,
        time_raw: e.time_raw,
        location: decode(e.location),
        organizer: decode(e.organizer),
        description: decode(e.description),
        event_url: decode(e.event_url || ''),
        sources: decode(e.sources || ''),
        tags: e.tags || '',
        recurring_group_id: e.recurring_group_id,
        featured: e.featured || 0,
      })),
      page: result.page,
      totalPages: result.totalPages,
      total: result.total,
      paginationHtml,
      params,
    };

    // Build OG tags for homepage
    const ogTitle = `Hey, Stutensee! – Veranstaltungen und Termine`;
    const ogDesc = `Alle Veranstaltungen in Stutensee auf einen Blick: Feste, Märkte, Sport, Kirche, Kinderangebote und mehr.`;
    const ogUrl = url.searchParams.has('page')
      ? `https://hey-stutensee.de/?page=${result.page}`
      : 'https://hey-stutensee.de/';
    const ogTags = renderOgTags(ogTitle, ogDesc, ogUrl);

    // Inject into template
    const countHtml = result.total > 0
      ? `${formatCount(result.total)} ${result.total === 1 ? 'Termin' : 'Termine'}`
      : '';

    const html = injectIntoTemplate(indexHtml, {
      events: eventCardsHtml,
      countHtml,
      page: result.page,
      totalPages: result.totalPages,
      jsonLd: jsonLdHtml,
      breadcrumbJsonLd: breadcrumbJsonLdHtml,
      paginationHtml,
      introHtml,
      featuredHtml,
      initialData,
      ogTags,
    });

    return new Response(html, { headers: { 'content-type': 'text/html;charset=utf-8', 'cache-control': 'public, max-age=300' } });
  } catch (err) {
    // Fallback: serve plain SPA without SSR (e.g. when DB is unavailable)
    return new Response(indexHtml, { headers: { 'content-type': 'text/html;charset=utf-8' } });
  }
}

// ── Chat API (LLM with RAG) ──────────────────────────────────────────

const CHAT_MODEL = 'deepseek-v4-flash';
const CHAT_MAX_ROUNDS = 5;
const CHAT_SYSTEM_PROMPT = `Du bist ein hilfreicher Assistent für die Veranstaltungsseite "Hey, Stutensee!". 
Du hilfst Nutzern, Veranstaltungen in Stutensee und Umgebung zu finden.

## Verfügbare Ortsteile/Distrikte
Veranstaltungen sind nach Ortsteilen getaggt. Hier ist die vollständige Liste aller verfügbaren Ortsteile: ${DISTRICT_LIST_STR}.
Stutensee selbst besteht aus den Ortsteilen: Blankenloch, Büchig, Friedrichstal, Spöck, Staffort.
Wenn ein Nutzer nach einem Ortsteil fragt (z.B. "Büchig", "Spöck"), verwende den genauen Namen im location-Parameter.

## Verfügbare Kategorien (Tags)
Veranstaltungen können folgende Kategorien haben: Sport, Musik, Kultur, Kirche, Kinder, Fest, Markt, Workshop, Bildung, Natur, Senioren, Digital, Handwerk, Essen, Treff, Politik, Verein, Wohltätigkeit, Sonstiges.

## Werkzeuge
Du hast Zugriff auf folgende Werkzeuge:

1. **search_events** — Durchsuche Veranstaltungen nach Suchbegriff, Datum, Ort, Kategorie oder Veranstalter.
   Parameter: query (Suchbegriff), date_from (YYYY-MM-DD), date_to (YYYY-MM-DD), tags (Array, z.B. ["Sport","Musik"]), location (Ortsteil, z.B. "Büchig", "Blankenloch"), organizer (Veranstalter), page, per_page (max 20)
   
2. **get_event_details** — Rufe die vollständigen Details einer Veranstaltung ab.
   Parameter: event_id (integer)

## Wichtige Regeln
- Antworte immer auf Deutsch.
- Wenn ein Nutzer nach "heute", "morgen", "dieses Wochenende" etc. fragt, berechne die passenden Daten.
- Präsentiere Veranstaltungen übersichtlich mit Datum, Titel, Ort und kurzer Beschreibung.
- Wenn du mehrere Ergebnisse hast, fasse sie kurz zusammen.
- Frage bei Bedarf nach, um die Suche einzugrenzen (z.B. "Welche Kategorie interessiert dich?" oder "In welchem Ortsteil?").`;

const CHAT_TOOLS = [
  {
    type: 'function',
    function: {
      name: 'search_events',
      description: 'Suche nach Veranstaltungen in Stutensee mit verschiedenen Filtern',
      parameters: {
        type: 'object',
        properties: {
          query: { type: 'string', description: 'Suchbegriff für Titel oder Beschreibung' },
          date_from: { type: 'string', description: 'Startdatum (YYYY-MM-DD)' },
          date_to: { type: 'string', description: 'Enddatum (YYYY-MM-DD)' },
          tags: { type: 'array', items: { type: 'string' }, description: 'Kategorien: Sport, Musik, Kultur, Kirche, Kinder, Fest, Markt, Workshop, Bildung, Natur, Senioren, Digital, Handwerk, Essen, Treff, Politik, Verein, Wohltätigkeit, Sonstiges' },
          location: { type: 'string', description: 'Ortsteil/Distrikt (z.B. Blankenloch, Büchig, Friedrichstal, Spöck, Staffort, Bruchsal, Eggenstein, Graben-Neudorf, Linkenheim, Weingarten)' },
          organizer: { type: 'string', description: 'Veranstalter-Name' },
          page: { type: 'integer', description: 'Seitenzahl (Standard: 1)' },
          per_page: { type: 'integer', description: 'Ergebnisse pro Seite (max 20, Standard: 10)' },
        },
      },
    },
  },
  {
    type: 'function',
    function: {
      name: 'get_event_details',
      description: 'Rufe detaillierte Informationen zu einer einzelnen Veranstaltung ab',
      parameters: {
        type: 'object',
        properties: {
          event_id: { type: 'integer', description: 'ID der Veranstaltung' },
        },
        required: ['event_id'],
      },
    },
  },
];

/** Handle POST /api/chat — LLM-powered event search with RAG. */
async function serveChat(request, env) {
  try {
    const { messages } = await request.json();
    if (!messages || !Array.isArray(messages) || messages.length === 0) {
      return json({ error: 'Messages array is required' }, 400);
    }

    const today = new Date().toISOString().slice(0, 10);
    const systemPrompt = CHAT_SYSTEM_PROMPT + `\n\nHeutiges Datum: ${today}.`;
    const llmMessages = [{ role: 'system', content: systemPrompt }, ...messages];
    let result = await callLLM(llmMessages, CHAT_TOOLS, env);
    let collectedEvents = [];
    let totalUsage = { prompt_tokens: 0, completion_tokens: 0, total_tokens: 0 };

    // Track usage across rounds
    if (result.usage) {
      totalUsage.prompt_tokens += result.usage.prompt_tokens || 0;
      totalUsage.completion_tokens += result.usage.completion_tokens || 0;
      totalUsage.total_tokens += result.usage.total_tokens || 0;
    }

    for (let round = 0; round < CHAT_MAX_ROUNDS; round++) {
      if (!result || !result.choices || result.choices.length === 0 || !result.choices[0].message) {
        return json({ error: 'Ungültige Antwort vom KI-Assistenten', usage: totalUsage }, 502);
      }
      const msg = result.choices[0].message;
      if (!msg.tool_calls || msg.tool_calls.length === 0) {
        // No more tool calls — we're done
        return json({ message: msg, events: collectedEvents, usage: totalUsage });
      }

      // Execute each tool call
      llmMessages.push({
        role: 'assistant',
        content: msg.content || null,
        tool_calls: msg.tool_calls,
        ...(msg.reasoning_content ? { reasoning_content: msg.reasoning_content } : {}),
      });
      for (const tc of msg.tool_calls) {
        const fn = tc.function;
        let toolResult;
        try {
          const args = JSON.parse(fn.arguments);
          if (fn.name === 'search_events') {
            toolResult = await searchEvents(args, env);
            if (toolResult.events && toolResult.events.length > 0) {
              collectedEvents = collectedEvents.concat(toolResult.events);
            }
          } else if (fn.name === 'get_event_details') {
            toolResult = await getEventDetails(args, env);
            if (toolResult.id) {
              collectedEvents.push(toolResult);
            }
          } else {
            toolResult = { error: `Unknown tool: ${fn.name}` };
          }
        } catch (err) {
          toolResult = { error: err.message };
        }
        llmMessages.push({ role: 'tool', tool_call_id: tc.id, content: JSON.stringify(toolResult) });
      }

      result = await callLLM(llmMessages, CHAT_TOOLS, env);
      if (result.usage) {
        totalUsage.prompt_tokens += result.usage.prompt_tokens || 0;
        totalUsage.completion_tokens += result.usage.completion_tokens || 0;
        totalUsage.total_tokens += result.usage.total_tokens || 0;
      }
    }

    // Max rounds reached — return whatever we have
    const finalMsg = result && result.choices && result.choices[0] ? result.choices[0].message : null;
    if (!finalMsg) {
      return json({ error: 'Ungültige Antwort vom KI-Assistenten', usage: totalUsage }, 502);
    }
    return json({ message: finalMsg, events: collectedEvents, usage: totalUsage });
  } catch (err) {
    console.error('Chat error:', err.message);
    return json({ error: err.message }, 500);
  }
}

/** Call the LLM API (opencode.ai). Returns {choices, usage}. */
async function callLLM(messages, tools, env) {
  const apiKey = env.LLM_API_KEY;
  const baseUrl = env.LLM_BASE_URL || 'https://opencode.ai/zen/go/v1';
  if (!apiKey) {
    throw new Error('LLM_API_KEY not configured');
  }

  const response = await fetch(`${baseUrl}/chat/completions`, {
    method: 'POST',
    headers: {
      'Authorization': `Bearer ${apiKey}`,
      'Content-Type': 'application/json',
      'User-Agent': 'YEAP-Worker/1.0',
    },
    body: JSON.stringify({
      model: CHAT_MODEL,
      messages,
      tools,
      max_tokens: 1024,
    }),
    signal: AbortSignal.timeout(30000),
  });

  if (!response.ok) {
    const err = await response.text();
    throw new Error(`LLM API error ${response.status}: ${err.slice(0, 200)}`);
  }

  const data = await response.json();

  // Log token usage for cost tracking
  if (data.usage) {
    const { prompt_tokens, completion_tokens, total_tokens } = data.usage;
    // Model pricing: deepseek-v4-flash ~$0.15/M input, ~$0.60/M output (estimate)
    const inputCost = prompt_tokens * 0.15 / 1_000_000;
    const outputCost = completion_tokens * 0.60 / 1_000_000;
    console.log(`[COST] prompt=${prompt_tokens} output=${completion_tokens} total=${total_tokens} est_cost=${(inputCost + outputCost).toFixed(6)}`);
  }

  return data;
}

/** Search events in D1 database (date_from defaults to today for SSR/API parity). */
async function searchEvents(params, env) {
  const db = env.STUTENSEE_DB;
  const page = Math.max(1, params.page || 1);
  const perPage = Math.min(20, Math.max(1, params.per_page || 12));
  const wheres = ["tags != 'blocked'", "is_passed = 0"];
  const args = [];

  if (params.query) {
    wheres.push("(title LIKE ? OR description LIKE ? OR location LIKE ? OR organizer LIKE ?)");
    const q = `%${params.query}%`;
    args.push(q, q, q, q);
  }
  const dateFrom = params.date_from || new Date().toISOString().slice(0, 10);
  if (dateFrom) { wheres.push("date_start >= ?"); args.push(dateFrom); }
  if (params.date_to) { wheres.push("date_start <= ?"); args.push(params.date_to); }
  if (params.tags && params.tags.length > 0) {
    for (const t of params.tags) { wheres.push("tags LIKE ?"); args.push(`%${t}%`); }
  }
  if (params.location) { wheres.push("(location LIKE ? OR tags LIKE ?)"); args.push(`%${params.location}%`, `%${params.location}%`); }
  if (params.organizer) { wheres.push("organizer = ?"); args.push(params.organizer); }

  const where = wheres.length ? 'WHERE ' + wheres.join(' AND ') : '';
  const offset = (page - 1) * perPage;

  const total = (await db.prepare(`SELECT COUNT(*) as c FROM curated_events ${where}`).bind(...args).first()).c;
  const { results } = await db.prepare(
    `SELECT id, title, date_start, date_end, time_raw, location, organizer, description, event_url, tags, featured
     FROM curated_events ${where} ORDER BY date_start ASC, featured DESC, id LIMIT ? OFFSET ?`
  ).bind(...args, perPage, offset).all();

  const events = results.map(r => ({
    id: r.id,
    title: decode(r.title),
    date_start: r.date_start || '',
    date_end: r.date_end,
    time_raw: r.time_raw,
    location: decode(r.location),
    organizer: decode(r.organizer),
    description: decode(r.description || '').substring(0, 200),
    event_url: decode(r.event_url || ''),
    tags: r.tags || '',
    featured: r.featured || 0,
  }));

  return { events, total, page, per_page: perPage, total_pages: Math.ceil(total / perPage) };
}

/** Get single event details from D1. */
async function getEventDetails(params, env) {
  const db = env.STUTENSEE_DB;
  const row = await db.prepare(
    `SELECT id, title, date_start, date_end, time_raw, location, organizer, description, event_url, tags, is_passed, featured
     FROM curated_events WHERE id = ? AND tags != 'blocked'`
  ).bind(params.event_id).first();

  if (!row) return { error: 'Event not found' };

  return {
    id: row.id,
    title: decode(row.title),
    date_start: row.date_start || '',
    date_end: row.date_end,
    time_raw: row.time_raw || '',
    location: decode(row.location),
    organizer: decode(row.organizer),
    description: decode(row.description || ''),
    event_url: decode(row.event_url || ''),
    tags: row.tags || '',
    is_passed: row.is_passed || 0,
    featured: row.featured || 0,
  };
}

/** Serve an individual event page at /events/{id}/{slug}. */
async function serveEventPage(env, url, ctx) {
  const parts = url.pathname.split('/'); // ['', 'events', '{id}', '{slug}']
  if (!/^[0-9]+$/.test(parts[2])) return serve404();
  const eventId = parseInt(parts[2]);

  const row = await env.STUTENSEE_DB.prepare(
    `SELECT id, title, date_start, date_end, time_raw, location, organizer, description, event_url, sources, tags, recurring_group_id, is_passed, featured
     FROM curated_events WHERE id = ? AND tags != 'blocked'`
  ).bind(eventId).first();

  if (!row) {
    // Old URL recovery: try id_redirects first (ID-based mapping from backup DBs),
    // then fall back to slug-based lookup.

    // Check id_redirects table (mapping from old autoincrement IDs to new hash IDs)
    let redirected = false;
    try {
      const redirect = await env.STUTENSEE_DB.prepare(
        `SELECT new_id FROM id_redirects WHERE old_id = ?`
      ).bind(eventId).first();
      if (redirect) {
        const urlSlug = parts[3] || '';
        const newRow = await env.STUTENSEE_DB.prepare(
          `SELECT id, title FROM curated_events WHERE id = ? AND tags != 'blocked'`
        ).bind(redirect.new_id).first();
        if (newRow) {
          // Validate: only redirect if URL slug matches target's slug (or no slug in URL).
          // Prevents stale redirect map entries from sending users to wrong events.
          if (!urlSlug || eventSlug(newRow) === urlSlug) {
            const newPath = eventPath(newRow);
            return new Response(null, { status: 301, headers: { 'location': newPath + url.search, 'cache-control': 'public, max-age=31536000' } });
          }
          // Slug mismatch — fall through to slug-based lookup below
        }
      }
    } catch (e) {
      // id_redirects table may not exist yet; fall through to slug lookup
    }

    // Slug-based fallback (only for old-style URLs with low IDs)
    const urlSlug = parts[3] || '';
    if (urlSlug && eventId < 100000) {
      try {
        const index = await getEventIndex(env, ctx);
        for (const r of index) {
          if (eventSlug(r) === urlSlug) {
            const newPath = eventPath(r);
            return new Response(null, { status: 301, headers: { 'location': newPath + url.search, 'cache-control': 'public, max-age=31536000' } });
          }
        }
      } catch (e) {
        // Slug fallback failed
      }
    }

    return serve404();
  }

  // Validate slug: redirect to canonical URL if slug doesn't match
  const correctPath = eventPath(row);
  if (url.pathname !== correctPath) {
    return new Response(null, { status: 301, headers: { 'location': correctPath + url.search, 'cache-control': 'public, max-age=86400' } });
  }

  const e = {
    id: row.id, title: decode(row.title), date_start: row.date_start || '', date_end: row.date_end,
    time_raw: row.time_raw, location: decode(row.location), organizer: decode(row.organizer),
    description: decode(row.description), event_url: decode(row.event_url || ''),
    sources: decode(row.sources || ''), tags: row.tags || '',
    recurring_group_id: row.recurring_group_id,
    is_passed: row.is_passed || 0,
    featured: row.featured || 0,
  };

  const tags = (e.tags || '').split(',').map(t => t.trim()).filter(Boolean);
  const locTags = tags.filter(t => DISTRICT_KEYS.has(t));
  const locationName = locTags.length > 0 ? locTags[0] : (e.location || 'Stutensee');

  // Build page title and meta
  const pageTitle = `${e.title} – Hey, Stutensee!`;
  const metaDesc = `${e.title} am ${fmtDate(e.date_start)}${e.location ? ' in ' + e.location : ' in ' + locationName}. ${e.description ? summarizeDescription(e.description).substring(0, 150) : 'Alle Veranstaltungen in Stutensee auf einen Blick.'}`;

  // JSON-LD — use the hey-stutensee.de canonical URL, not external source
  const jsonLd = renderJsonLd([{ ...e, title: row.title, description: row.description, event_url: null }]);

  // OG tags for event detail page
  const eventUrl = `https://hey-stutensee.de${eventPath(row)}`;

  // Breadcrumb JSON-LD
  const breadcrumbJsonLd = renderBreadcrumbJsonLd([
    { name: 'Hey, Stutensee!', url: 'https://hey-stutensee.de/' },
    { name: e.title, url: eventUrl },
  ]);

  const ogTagsHtml = renderOgTags(pageTitle, metaDesc, eventUrl, 'article');

  // Build HTML
  const themeTags = tags.filter(t => THEME_KEYS.has(t));
  const category = categoryOf(tags);
  const detailTime = timeLabel(e.time_raw);
  const description = cleanDescription(e.description || '');
  const badge = formatDateBadge(e.date_start);
  const place = e.location || locTags[0] || '';
  const relDay = relativeDayLabel(e.date_start);

  let sourceLink = '';
  if (e.event_url) {
    let host = 'Zur Veranstaltungsseite';
    try { host = new URL(e.event_url).hostname.replace(/^www\./, ''); } catch {}
    sourceLink = `<a class="detail-cta" href="${escapeHtml(e.event_url)}" target="_blank" rel="noopener">
      <span>Zur Veranstaltungsseite</span>
      <svg class="icon" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M14 4h6v6M20 4l-9 9M19 14v5a1 1 0 0 1-1 1H5a1 1 0 0 1-1-1V6a1 1 0 0 1 1-1h5"/></svg>
    </a>
    <p class="detail-source">Quelle: <a href="${escapeHtml(e.event_url)}" target="_blank" rel="noopener">${escapeHtml(host)}</a></p>`;
  }

  const facts = [
    e.date_start ? { label: 'Datum', value: fmtDate(e.date_start) + (e.date_end && e.date_end !== e.date_start ? ' – ' + fmtDate(e.date_end) : '') } : null,
    detailTime ? { label: 'Uhrzeit', value: detailTime } : null,
    e.organizer ? { label: 'Veranstalter', value: e.organizer } : null,
  ].filter(Boolean);

  const body = `<!DOCTYPE html>
<html lang="de">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>${escapeHtml(pageTitle)}</title>
<meta name="description" content="${escapeHtml(metaDesc)}">
<meta name="robots" content="index,follow">
<meta name="theme-color" content="#0d3a71">
<link rel="canonical" href="https://hey-stutensee.de${eventPath(row)}">
<link rel="icon" type="image/png" href="/favicon.png">
${ogTagsHtml}
${jsonLd}
${breadcrumbJsonLd}
<script>
(function(){try{var s=localStorage.getItem('dark');var d=s===null?window.matchMedia('(prefers-color-scheme: dark)').matches:s==='1';if(d)document.documentElement.classList.add('dark');}catch(e){}})();
</script>
<style>
:root{--bg:#f6f4ef;--surface:#fff;--surface-2:#fbfaf7;--text:#16212e;--text-muted:#5b6979;--text-faint:#8593a2;--border:#e5e0d6;--border-strong:#d3ccbe;--navy:#0d3a71;--navy-deep:#0a2c56;--primary-light:#edf2f9;--gold:#fab800;--gold-ink:#7a5200;--gold-light:#fff6dd;--tag-org-bg:#efeae1;--tag-org-text:#5b6979;--radius:14px;--radius-sm:10px;--shadow:0 10px 28px -22px rgba(18,35,58,.45),0 1px 2px rgba(18,35,58,.05);--transition:180ms cubic-bezier(.2,.7,.3,1)}
html.dark{--bg:#0b1524;--surface:#122134;--surface-2:#0f1c2d;--text:#e9eff7;--text-muted:#a2b3c6;--text-faint:#7f92a8;--border:#203149;--border-strong:#2c415e;--primary-light:#17293f;--gold-ink:#f7c948;--gold-light:#2a2415;--tag-org-bg:#182a3f;--tag-org-text:#a2b3c6;--shadow:0 12px 30px -20px rgba(0,0,0,.9),0 1px 2px rgba(0,0,0,.4)}
*,*::before,*::after{box-sizing:border-box;margin:0;padding:0}
body{font-family:system-ui,-apple-system,"Segoe UI",Roboto,sans-serif;background:var(--bg);color:var(--text);line-height:1.6;min-height:100vh;display:flex;flex-direction:column;-webkit-font-smoothing:antialiased}
a{color:var(--navy);overflow-wrap:anywhere}
html.dark a{color:#8ab4f0}
h1{font-weight:800;letter-spacing:-.7px;line-height:1.15}
.icon{width:18px;height:18px;flex:none}
:focus-visible{outline:2px solid var(--navy);outline-offset:2px;border-radius:4px}
.site-header{background:radial-gradient(120% 220% at 88% -40%,rgba(250,184,0,.16) 0,rgba(250,184,0,0) 55%),linear-gradient(180deg,#104380 0,#0c3567 100%);color:#fff}
.header-inner{max-width:808px;margin:0 auto;padding:14px 24px;display:flex;align-items:center;justify-content:space-between;gap:16px}
.brand{display:flex;align-items:center;gap:12px;color:#fff;text-decoration:none;min-width:0}
.brand-mark{display:grid;place-items:center;width:42px;height:42px;flex:none;border-radius:12px;background:#fff;box-shadow:0 4px 12px rgba(4,18,38,.28)}
.brand-mark svg{width:32px;height:32px}
.brand-copy{display:flex;flex-direction:column;line-height:1.15}
.brand-title{font-size:19px;font-weight:750;letter-spacing:-.3px}
.brand-sub{margin-top:2px;font-size:10.5px;font-weight:650;letter-spacing:.11em;text-transform:uppercase;color:rgba(255,255,255,.62)}
.header-actions{display:flex;align-items:center;gap:8px;flex:none}
.icon-btn{display:inline-flex;align-items:center;justify-content:center;gap:7px;height:38px;min-width:38px;padding:0 12px;border:1px solid rgba(255,255,255,.18);border-radius:10px;background:rgba(255,255,255,.07);color:#fff;font-size:13px;font-weight:600;text-decoration:none;cursor:pointer;transition:background var(--transition),border-color var(--transition)}
.icon-btn:hover{background:rgba(255,255,255,.15);border-color:rgba(255,255,255,.32);color:#fff}
#dark-toggle .icon-moon{display:none}
html.dark #dark-toggle .icon-sun{display:none}
html.dark #dark-toggle .icon-moon{display:block}
.detail-wrap{flex:1;width:100%;max-width:760px;margin:0 auto;padding:26px 24px 48px}
.back-link{display:inline-flex;align-items:center;gap:5px;margin-bottom:16px;color:var(--text-muted);text-decoration:none;font-size:13px;font-weight:600}
.back-link:hover{color:var(--text)}
.detail-card{background:var(--surface);border:1px solid var(--border);border-radius:18px;padding:30px 32px 28px;box-shadow:var(--shadow)}
.detail-head{display:flex;gap:18px;align-items:flex-start}
.detail-date{display:flex;flex-direction:column;align-items:center;justify-content:center;gap:1px;width:64px;height:70px;flex:none;border-radius:14px;background:var(--navy);color:#fff;line-height:1}
.dd-day{font-size:26px;font-weight:800;letter-spacing:-.7px}
.dd-month{font-size:10.5px;font-weight:700;letter-spacing:.12em;text-transform:uppercase;color:rgba(255,255,255,.72)}
.dd-weekday{margin-top:3px;font-size:9px;font-weight:600;letter-spacing:.06em;text-transform:uppercase;color:rgba(255,255,255,.5)}
.detail-kicker{display:flex;gap:6px;flex-wrap:wrap;margin-bottom:6px}
.pill{display:inline-block;padding:2px 9px;border-radius:999px;background:var(--primary-light);color:var(--navy);font-size:10.5px;font-weight:700;letter-spacing:.06em;text-transform:uppercase}
html.dark .pill{color:#b6d0f7}
.pill.gold{background:var(--gold-light);color:var(--gold-ink)}
.detail-card h1{font-size:clamp(22px,3.2vw,29px);margin-bottom:8px}
.detail-place{display:flex;align-items:flex-start;gap:5px;font-size:14px;color:var(--text-muted)}
.detail-place .icon{width:14px;height:14px;margin-top:3px;color:var(--text-faint)}
.banner{margin:18px 0 0;padding:10px 14px;border-radius:10px;background:var(--gold-light);color:var(--gold-ink);font-size:13px;font-weight:600;border:1px solid rgba(250,184,0,.35)}
.facts{display:grid;grid-template-columns:repeat(auto-fit,minmax(150px,1fr));gap:1px;margin:22px 0 0;border:1px solid var(--border);border-radius:12px;overflow:hidden;background:var(--border)}
.fact{background:var(--surface-2);padding:12px 14px}
.fact dt{font-size:10.5px;font-weight:700;letter-spacing:.09em;text-transform:uppercase;color:var(--text-faint);margin-bottom:2px}
.fact dd{font-size:14px;font-weight:600;color:var(--text)}
.desc{margin-top:22px;font-size:15px;line-height:1.75;color:var(--text-muted);white-space:pre-line}
.tags{display:flex;flex-wrap:wrap;gap:6px;margin-top:22px;padding-top:18px;border-top:1px solid var(--border)}
.tag{display:inline-block;padding:3px 10px;border-radius:999px;font-size:11.5px;font-weight:600}
.tag-organizer{background:var(--tag-org-bg);color:var(--tag-org-text)}
.tag-location{background:var(--primary-light);color:var(--navy)}
html.dark .tag-location{color:#b6d0f7}
.tag-tag{background:var(--gold-light);color:var(--gold-ink)}
.detail-cta{display:inline-flex;align-items:center;gap:8px;margin-top:22px;padding:11px 18px;border-radius:11px;background:var(--navy);color:#fff;text-decoration:none;font-size:14px;font-weight:650;transition:background var(--transition),transform var(--transition)}
.detail-cta:hover{background:var(--navy-deep);color:#fff;transform:translateY(-1px)}
.detail-cta .icon{width:15px;height:15px}
.detail-source{margin-top:8px;font-size:12px;color:var(--text-faint)}
.detail-source a{color:var(--text-muted)}
.site-footer{border-top:1px solid var(--border);background:var(--surface-2);padding:22px 24px;text-align:center;font-size:12.5px;color:var(--text-muted)}
.site-footer .linklike{border:0;background:none;padding:0;color:var(--text-muted);font:inherit;text-decoration:underline;text-underline-offset:2px;cursor:pointer}
.imprint{max-width:62ch;margin:14px auto 0;padding:14px 16px;border:1px solid var(--border);border-radius:10px;background:var(--surface);font-size:12.5px;line-height:1.65;text-align:left;color:var(--text-muted)}
.imprint strong{color:var(--text)}
@media(max-width:640px){
  .header-inner{padding:11px 14px}
  .brand-sub{display:none}
  .brand-title{font-size:17px}
  .brand-mark{width:38px;height:38px;border-radius:11px}
  .brand-mark svg{width:29px;height:29px}
  .detail-wrap{padding:18px 14px 36px}
  .detail-card{padding:20px 18px 22px;border-radius:16px}
  .detail-head{gap:13px}
  .detail-date{width:54px;height:60px;border-radius:12px}
  .dd-day{font-size:22px}
  .dd-weekday{display:none}
}
@media(prefers-reduced-motion:reduce){*{transition-duration:.01ms!important;animation-duration:.01ms!important}}
</style>
</head>
<body>
<header class="site-header">
  <div class="header-inner">
    <a class="brand" href="/" aria-label="Hey, Stutensee! – Startseite">
      <span class="brand-mark" aria-hidden="true">${brandMarkSvg('detail')}</span>
      <span class="brand-copy"><span class="brand-title">Hey, Stutensee!</span><span class="brand-sub">Veranstaltungen &amp; Termine</span></span>
    </a>
    <div class="header-actions">
      <button type="button" id="dark-toggle" class="icon-btn" onclick="toggleDark()" aria-label="Dunkles Design umschalten" title="Hell / Dunkel">
        <svg class="icon icon-sun" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" aria-hidden="true"><circle cx="12" cy="12" r="4"/><path d="M12 2v2M12 20v2M4.9 4.9l1.4 1.4M17.7 17.7l1.4 1.4M2 12h2M20 12h2M4.9 19.1l1.4-1.4M17.7 6.3l1.4-1.4"/></svg>
        <svg class="icon icon-moon" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M21 12.8A9 9 0 1 1 11.2 3a7 7 0 0 0 9.8 9.8z"/></svg>
      </button>
      <a class="icon-btn" href="/">Alle Termine</a>
    </div>
  </div>
</header>

<main class="detail-wrap">
  <a href="/" class="back-link">← Zurück zur Übersicht</a>
  <article class="detail-card" aria-label="${escapeHtml(e.title)}">
    <div class="detail-head">
      <div class="detail-date" aria-hidden="true">
        <span class="dd-day">${badge.day}</span>
        <span class="dd-month">${badge.month}</span>
        <span class="dd-weekday">${weekdayDe(e.date_start)}</span>
      </div>
      <div>
        <div class="detail-kicker">
          ${category ? `<span class="pill">${escapeHtml(category)}</span>` : ''}
          ${e.featured ? '<span class="pill gold">Empfohlen</span>' : ''}
          ${relDay === 'Heute' ? '<span class="pill gold">Heute</span>' : relDay === 'Morgen' ? '<span class="pill gold">Morgen</span>' : ''}
        </div>
        <h1>${escapeHtml(e.title)}</h1>
        ${place ? `<p class="detail-place">${ICON.pin}<span>${escapeHtml(place)}</span></p>` : ''}
      </div>
    </div>

    ${e.is_passed ? '<p class="banner">Diese Veranstaltung hat bereits stattgefunden.</p>' : ''}

    <dl class="facts">
      ${facts.map(f => `<div class="fact"><dt>${f.label}</dt><dd>${escapeHtml(f.value)}</dd></div>`).join('')}
    </dl>

    ${description ? `<div class="desc">${escapeHtml(description)}</div>` : ''}

    ${sourceLink}

    <div class="tags">
      ${themeTags.map(t => `<span class="tag tag-tag">${escapeHtml(t)}</span>`).join('')}
      ${locTags.map(t => `<span class="tag tag-location">${escapeHtml(t)}</span>`).join('')}
      ${e.organizer ? `<span class="tag tag-organizer">${escapeHtml(e.organizer)}</span>` : ''}
    </div>
  </article>
</main>

<footer class="site-footer">
  <button type="button" class="linklike" onclick="document.getElementById('imprint').hidden = !document.getElementById('imprint').hidden">Impressum</button>
  <span aria-hidden="true"> · </span>
  <span>Keine Cookies, kein Tracking</span>
  <div id="imprint" class="imprint" hidden>
    <strong>Angaben gemäß § 5 TMG</strong><br>
    Johannes Reuter · E-Mail: <span id="imprint-email"></span>
    <div style="margin-top:8px"><strong>Datenschutz</strong><br>Diese Seite erhebt keine personenbezogenen Daten. Es werden keine Cookies gesetzt, kein Tracking durchgeführt und keine Analysedienste genutzt.</div>
  </div>
</footer>
<script>
function toggleDark(){var d=document.documentElement.classList.toggle('dark');localStorage.setItem('dark',d?'1':'0');var b=document.getElementById('dark-toggle');b.setAttribute('aria-pressed',String(d));}
document.getElementById('imprint-email').textContent='email@johannes-reuter.de';
</script>
</body>
</html>`;

  return new Response(body, { headers: { 'content-type': 'text/html;charset=utf-8', 'cache-control': 'public, max-age=3600' } });
}

/** Update sitemap to include event URLs. */
async function serveSitemapXml(env) {
  // Fetch all event IDs for the sitemap. Google supports up to 50,000 URLs per sitemap,
  // so cap at 50,000 as a safety net.
  const today = new Date().toISOString().slice(0, 10);
  let urls = `<url><loc>https://hey-stutensee.de/</loc><lastmod>${today}</lastmod><changefreq>daily</changefreq><priority>1.0</priority></url>`;

  try {
    const { results } = await env.STUTENSEE_DB.prepare(
      `SELECT id, title, updated_at FROM curated_events WHERE tags != 'blocked' ORDER BY date_start DESC LIMIT 50000`
    ).all();

    for (const row of results) {
      const lastmod = row.updated_at ? row.updated_at.slice(0, 10) : today;
      urls += `<url><loc>https://hey-stutensee.de${eventPath(row)}</loc><lastmod>${lastmod}</lastmod><changefreq>monthly</changefreq><priority>0.5</priority></url>`;
    }
  } catch (err) {
    console.error('Sitemap generation error:', err.message);
  }

  return new Response(`<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
${urls}
</urlset>`, {
    headers: { 'content-type': 'application/xml;charset=utf-8', 'cache-control': 'public, max-age=86400' }
  });
}

// ── Existing Helpers ──────────────────────────────────────────────────

function decode(s) {
  if (!s) return '';
  return s.replace(/&amp;/g, '&').replace(/&lt;/g, '<').replace(/&gt;/g, '>').replace(/&quot;/g, '"')
    .replace(/&#(\d+);/g, (_, n) => String.fromCharCode(n));
}

function json(data, status = 200) {
  const body = JSON.stringify(data);
  return new Response(body, {
    status,
    headers: {
      'content-type': 'application/json;charset=utf-8',
      'access-control-allow-origin': '*',
      'content-length': new TextEncoder().encode(body).length.toString(),
    }
  });
}

async function serveFeatured(env) {
  const db = env.STUTENSEE_DB;
  const { results } = await db.prepare(
    `SELECT id, title, date_start, date_end, time_raw, location, organizer, description, event_url, sources, tags, recurring_group_id, featured
     FROM curated_events WHERE featured = 1 AND tags != 'blocked'
     AND (tags LIKE '%Blankenloch%' OR tags LIKE '%Friedrichstal%' OR tags LIKE '%Spöck%' OR tags LIKE '%Staffort%' OR tags LIKE '%Büchig%')
     ORDER BY date_start ASC LIMIT 4`
  ).all();
  return json(results.map(r => ({
    id: r.id, title: decode(r.title), date_start: r.date_start || '', date_end: r.date_end,
    time_raw: r.time_raw, location: decode(r.location), organizer: decode(r.organizer),
    description: decode(r.description), event_url: decode(r.event_url || ''),
    sources: decode(r.sources || ''), tags: r.tags || '', featured: r.featured || 0,
    recurring_group_id: r.recurring_group_id,
  })));
}

async function serveEvents(env, url) {
  const p = url.searchParams;
  const page = Math.max(1, parseInt(p.get('page') || '1'));
  const perPage = Math.min(100, Math.max(1, parseInt(p.get('per_page') || '50')));
  const search = (p.get('search') || '').slice(0, 48);
  const tags = p.getAll('tag').filter(Boolean);
  const dateFrom = p.get('date_from') || new Date().toISOString().slice(0, 10);
  const organizer = p.get('organizer') || '';

  const db = env.STUTENSEE_DB;
  const wheres = ["tags != 'blocked'", "is_passed = 0", "(featured = 0 OR featured IS NULL)"];
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
    `SELECT id, title, date_start, date_end, time_raw, location, organizer, description, event_url, sources, tags, recurring_group_id, featured
     FROM curated_events ${where} ORDER BY date_start ASC, featured DESC, id LIMIT ? OFFSET ?`
  ).bind(...args, perPage, offset).all();

  return json({
    events: results.map(r => ({
      id: r.id, title: decode(r.title), date_start: r.date_start || '', date_end: r.date_end,
      time_raw: r.time_raw, location: decode(r.location), organizer: decode(r.organizer),
      description: decode(r.description), event_url: decode(r.event_url || ''),
      sources: decode(r.sources || ''), tags: r.tags || '', featured: r.featured || 0,
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
  const { results } = await env.STUTENSEE_DB.prepare(
    "SELECT DISTINCT tags FROM curated_events WHERE tags IS NOT NULL AND tags != '' AND tags != 'blocked'"
  ).all();
  const set = new Set();
  for (const r of results) {
    for (const t of r.tags.split(',')) { const s = t.trim(); if (s && THEME_KEYS.has(s)) set.add(s); }
  }
  return json([...set].sort());
}

async function serveDistricts(env) {
  const { results } = await env.STUTENSEE_DB.prepare(
    "SELECT DISTINCT tags FROM curated_events WHERE tags IS NOT NULL AND tags != '' AND tags != 'blocked'"
  ).all();
  const set = new Set();
  for (const r of results) {
    for (const t of r.tags.split(',')) { const s = t.trim(); if (s && DISTRICT_KEYS.has(s)) set.add(s); }
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

async function serveReqStats(env) {
  if (!env.REQUEST_DB) return json({ error: 'Analytics not configured' }, 404);
  const totals = await env.REQUEST_DB.prepare(
    'SELECT COUNT(*) as total, COALESCE(SUM(response_size),0) as total_bytes, COALESCE(ROUND(AVG(latency_ms),1),0) as avg_latency FROM request_log'
  ).first();
  const byPath = await env.REQUEST_DB.prepare(
    'SELECT path, COUNT(*) as count, COALESCE(ROUND(AVG(latency_ms),1),0) as avg_latency, COALESCE(SUM(response_size),0) as total_bytes FROM request_log GROUP BY path ORDER BY count DESC LIMIT 20'
  ).all();
  const recent = await env.REQUEST_DB.prepare(
    'SELECT timestamp, path, status, response_size, latency_ms, search_query, tags_filter, organizer_filter, location_filter, date_from, user_agent FROM request_log ORDER BY id DESC LIMIT 50'
  ).all();

  // Classify recent entries by User-Agent
  let browser = 0, bot = 0, unknown = 0, empty = 0;
  for (const r of recent.results) {
    const cat = classifyUserAgent(r.user_agent);
    if (cat === 'browser') browser++;
    else if (cat === 'bot') bot++;
    else if (cat === 'unknown') unknown++;
    else empty++;
  }

  // Lifetime breakdown using simple SQL patterns (no regex needed)
  let uaBreakdown = { browser, bot, unknown, empty, total: recent.results.length };
  try {
    const totalsUa = await env.REQUEST_DB.prepare(
      `SELECT COUNT(*) as total FROM request_log`
    ).first();
    // Use SQL LIKE patterns for the most common cases — faster than JS for large tables
    const browserCount = await env.REQUEST_DB.prepare(
      `SELECT COUNT(*) as c FROM request_log WHERE user_agent LIKE '%Mozilla%'`
    ).first();
    const botCount = await env.REQUEST_DB.prepare(
      `SELECT COUNT(*) as c FROM request_log WHERE user_agent IS NOT NULL AND user_agent != '' AND (
         user_agent LIKE '%curl%' OR user_agent LIKE '%wget%' OR user_agent LIKE '%python%'
         OR user_agent LIKE '%Go-http-client%' OR user_agent LIKE '%bot%'
         OR user_agent LIKE '%Bot%' OR user_agent LIKE '%crawler%'
         OR user_agent LIKE '%spider%' OR user_agent LIKE '%scanner%'
         OR user_agent LIKE '%Cloudflare%'
       )`
    ).first();
    const emptyCount = await env.REQUEST_DB.prepare(
      `SELECT COUNT(*) as c FROM request_log WHERE user_agent IS NULL OR user_agent = ''`
    ).first();
    const browserVal = browserCount.c || 0;
    const botVal = botCount.c || 0;
    const emptyVal = emptyCount.c || 0;
    const totalVal = totalsUa.total || 0;
    uaBreakdown = {
      browser: browserVal,
      bot: botVal,
      unknown: Math.max(0, totalVal - browserVal - botVal - emptyVal),
      empty: emptyVal,
      total: totalVal,
    };
  } catch (err) {
    // user_agent column may not exist yet (migration pending) — fall back to recent-only breakdown
    console.error('Lifetime UA breakdown failed:', err.message);
  }

  // Daily breakdown: classify using same logic as classifyUserAgent (bot first, then browser)
  let daily = [];
  try {
    const dailyRows = await env.REQUEST_DB.prepare(
      `SELECT DATE(timestamp) as day,
        COUNT(*) as total,
        COUNT(CASE WHEN path != '/api/stats' THEN 1 END) as total_no_self,
        COUNT(CASE
          WHEN user_agent IS NULL OR user_agent = '' THEN NULL
          WHEN LOWER(user_agent) LIKE '%bot%' OR LOWER(user_agent) LIKE '%crawler%' OR LOWER(user_agent) LIKE '%spider%' OR LOWER(user_agent) LIKE '%scanner%' OR LOWER(user_agent) LIKE '%crawling%' OR LOWER(user_agent) LIKE '%curl%' OR LOWER(user_agent) LIKE '%wget%' OR LOWER(user_agent) LIKE '%python%' OR LOWER(user_agent) LIKE '%go-http%' OR LOWER(user_agent) LIKE '%okhttp%' OR LOWER(user_agent) LIKE '%googlebot%' OR LOWER(user_agent) LIKE '%googleother%' OR LOWER(user_agent) LIKE '%bingbot%' OR LOWER(user_agent) LIKE '%duckduckbot%' OR LOWER(user_agent) LIKE '%baiduspider%' OR LOWER(user_agent) LIKE '%yandexbot%' OR LOWER(user_agent) LIKE '%facebookexternalhit%' OR LOWER(user_agent) LIKE '%slackbot%' OR LOWER(user_agent) LIKE '%discordbot%' OR LOWER(user_agent) LIKE '%twitterbot%' OR LOWER(user_agent) LIKE '%ahrefsbot%' OR LOWER(user_agent) LIKE '%semrushbot%' OR LOWER(user_agent) LIKE '%mj12bot%' OR LOWER(user_agent) LIKE '%dotbot%' OR LOWER(user_agent) LIKE '%cloudflare%' THEN 1
        END) as bot,
        COUNT(CASE
          WHEN LOWER(user_agent) LIKE '%bot%' OR LOWER(user_agent) LIKE '%crawler%' OR LOWER(user_agent) LIKE '%spider%' OR LOWER(user_agent) LIKE '%scanner%' OR LOWER(user_agent) LIKE '%crawling%' OR LOWER(user_agent) LIKE '%curl%' OR LOWER(user_agent) LIKE '%wget%' OR LOWER(user_agent) LIKE '%python%' OR LOWER(user_agent) LIKE '%go-http%' OR LOWER(user_agent) LIKE '%okhttp%' OR LOWER(user_agent) LIKE '%googlebot%' OR LOWER(user_agent) LIKE '%googleother%' OR LOWER(user_agent) LIKE '%bingbot%' OR LOWER(user_agent) LIKE '%duckduckbot%' OR LOWER(user_agent) LIKE '%baiduspider%' OR LOWER(user_agent) LIKE '%yandexbot%' OR LOWER(user_agent) LIKE '%facebookexternalhit%' OR LOWER(user_agent) LIKE '%slackbot%' OR LOWER(user_agent) LIKE '%discordbot%' OR LOWER(user_agent) LIKE '%twitterbot%' OR LOWER(user_agent) LIKE '%ahrefsbot%' OR LOWER(user_agent) LIKE '%semrushbot%' OR LOWER(user_agent) LIKE '%mj12bot%' OR LOWER(user_agent) LIKE '%dotbot%' OR LOWER(user_agent) LIKE '%cloudflare%' OR user_agent IS NULL OR user_agent = '' THEN NULL
          WHEN LOWER(user_agent) LIKE '%mozilla%' OR LOWER(user_agent) LIKE '%chrome%' OR LOWER(user_agent) LIKE '%safari%' OR LOWER(user_agent) LIKE '%firefox%' OR LOWER(user_agent) LIKE '%edge%' OR LOWER(user_agent) LIKE '%opr/%' THEN 1
        END) as browser,
        COUNT(CASE WHEN user_agent IS NULL OR user_agent = '' THEN 1 END) as empty,
        COUNT(CASE WHEN path = '/' AND (
          LOWER(user_agent) LIKE '%mozilla%' OR LOWER(user_agent) LIKE '%chrome%' OR LOWER(user_agent) LIKE '%safari%' OR LOWER(user_agent) LIKE '%firefox%' OR LOWER(user_agent) LIKE '%edge%' OR LOWER(user_agent) LIKE '%opr/%'
        ) AND NOT (LOWER(user_agent) LIKE '%bot%' OR LOWER(user_agent) LIKE '%crawler%' OR LOWER(user_agent) LIKE '%spider%' OR LOWER(user_agent) LIKE '%scanner%' OR LOWER(user_agent) LIKE '%crawling%' OR LOWER(user_agent) LIKE '%curl%' OR LOWER(user_agent) LIKE '%wget%' OR LOWER(user_agent) LIKE '%python%' OR LOWER(user_agent) LIKE '%go-http%' OR LOWER(user_agent) LIKE '%okhttp%' OR LOWER(user_agent) LIKE '%googlebot%' OR LOWER(user_agent) LIKE '%googleother%' OR LOWER(user_agent) LIKE '%cloudflare%') THEN 1 END) as homepage_browser
       FROM request_log GROUP BY day ORDER BY day DESC`
    ).all();
    daily = dailyRows.results || [];
    // Compute 'unknown' for each day
    for (const d of daily) {
      d.unknown = Math.max(0, d.total - (d.browser||0) - (d.bot||0) - (d.empty||0));
    }
  } catch (err) {
    console.error('Daily breakdown failed:', err.message);
  }

  return json({
    totals: { total: totals.total, total_bytes: totals.total_bytes, avg_latency: totals.avg_latency },
    by_path: byPath.results,
    recent: recent.results,
    user_agent_breakdown: uaBreakdown,
    daily: daily,
  });
}

function serveRobotsTxt() {
  return new Response('User-agent: *\nAllow: /\nSitemap: https://hey-stutensee.de/sitemap.xml\n', {
    headers: { 'content-type': 'text/plain;charset=utf-8' }
  });
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
  return new Response(`# Hey, Stutensee! — Event Calendar API

## About
Hey, Stutensee! is an event calendar for Stutensee, Germany. It aggregates events from 20+ sources including the official city calendar, club websites, cultural institutions, and neighboring municipalities. All data is served via a Cloudflare Worker backed by D1 (SQLite-compatible) database.

## Base URL
https://hey-stutensee.de (production)
https://was-geht-stutensee-staging.email-0d0.workers.dev (staging)

## API Endpoints

### GET /api/list — List events
Returns paginated events with optional filtering.

Query parameters:
- page (int, default: 1) — page number
- per_page (int, default: 50, max: 100) — events per page
- search (string) — search in title, location, organizer
- tag (string, repeatable) — filter by theme or district tag
- date_from (ISO date, e.g. 2026-05-06) — show events from this date onward (defaults to today if omitted)
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

function serveSecurityTxt() {
  return new Response(`# Security Contact
# If you find a security issue on hey-stutensee.de, please report it.
Contact: mailto:email@johannes-reuter.de
Canonical: https://hey-stutensee.de/.well-known/security.txt
Preferred-Languages: de, en
Expires: 2027-05-24T14:00:00.000Z
`, {
    headers: { 'content-type': 'text/plain;charset=utf-8', 'cache-control': 'public, max-age=86400' }
  });
}

function serve404() {
  const page = `<!DOCTYPE html>
<html lang="de">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Seite nicht gefunden – Hey, Stutensee!</title>
<meta name="robots" content="noindex,follow">
<meta name="theme-color" content="#0d3a71">
<link rel="icon" type="image/png" href="/favicon.png">
<script>(function(){try{var s=localStorage.getItem('dark');var d=s===null?window.matchMedia('(prefers-color-scheme: dark)').matches:s==='1';if(d)document.documentElement.classList.add('dark');}catch(e){}})();</script>
<style>
:root{--bg:#f6f4ef;--surface:#fff;--surface-2:#fbfaf7;--text:#16212e;--text-muted:#5b6979;--text-faint:#8593a2;--border:#e5e0d6;--navy:#0d3a71;--navy-deep:#0a2c56;--gold:#fab800;--shadow:0 20px 50px -30px rgba(18,35,58,.5),0 1px 2px rgba(18,35,58,.05)}
html.dark{--bg:#0b1524;--surface:#122134;--surface-2:#0f1c2d;--text:#e9eff7;--text-muted:#a2b3c6;--text-faint:#7f92a8;--border:#203149;--shadow:0 24px 60px -30px rgba(0,0,0,.9)}
*,*::before,*::after{box-sizing:border-box;margin:0;padding:0}
body{font-family:system-ui,-apple-system,"Segoe UI",Roboto,sans-serif;background:var(--bg);color:var(--text);min-height:100vh;display:flex;flex-direction:column;-webkit-font-smoothing:antialiased}
a{color:inherit}
.site-header{background:radial-gradient(120% 220% at 88% -40%,rgba(250,184,0,.16) 0,rgba(250,184,0,0) 55%),linear-gradient(180deg,#104380 0,#0c3567 100%);color:#fff}
.header-inner{max-width:808px;margin:0 auto;padding:14px 24px;display:flex;align-items:center;justify-content:space-between;gap:16px}
.brand{display:flex;align-items:center;gap:12px;color:#fff;text-decoration:none}
.brand-mark{display:grid;place-items:center;width:42px;height:42px;flex:none;border-radius:12px;background:#fff;box-shadow:0 4px 12px rgba(4,18,38,.28)}
.brand-mark svg{width:32px;height:32px}
.brand-copy{display:flex;flex-direction:column;line-height:1.15}
.brand-title{font-size:19px;font-weight:750;letter-spacing:-.3px}
.brand-sub{margin-top:2px;font-size:10.5px;font-weight:650;letter-spacing:.11em;text-transform:uppercase;color:rgba(255,255,255,.62)}
main{flex:1;display:flex;align-items:center;justify-content:center;padding:32px 20px}
.card{width:100%;max-width:460px;padding:44px 38px;border:1px solid var(--border);border-radius:18px;background:var(--surface);box-shadow:var(--shadow);text-align:center}
.code{font-size:64px;font-weight:800;line-height:1;letter-spacing:-3px;color:var(--navy)}
html.dark .code{color:#8ab4f0}
h1{font-size:20px;font-weight:750;letter-spacing:-.3px;margin:10px 0 8px}
p{font-size:14.5px;line-height:1.65;color:var(--text-muted);margin-bottom:22px}
.btn{display:inline-flex;align-items:center;gap:7px;padding:11px 20px;border-radius:11px;background:var(--navy);color:#fff;text-decoration:none;font-size:14px;font-weight:650}
.btn:hover{background:var(--navy-deep)}
.site-footer{border-top:1px solid var(--border);background:var(--surface-2);padding:20px 24px;text-align:center;font-size:12.5px;color:var(--text-muted)}
.site-footer button{border:0;background:none;padding:0;color:var(--text-muted);font:inherit;text-decoration:underline;text-underline-offset:2px;cursor:pointer}
.imprint{max-width:60ch;margin:12px auto 0;padding:14px 16px;border:1px solid var(--border);border-radius:10px;background:var(--surface);font-size:12.5px;line-height:1.65;text-align:left;color:var(--text-muted)}
.imprint strong{color:var(--text)}
@media(max-width:520px){.card{padding:32px 22px}.header-inner{padding:11px 14px}.brand-sub{display:none}.brand-title{font-size:17px}}
</style>
</head>
<body>
<header class="site-header">
  <div class="header-inner">
    <a class="brand" href="/" aria-label="Hey, Stutensee! – Startseite">
      <span class="brand-mark" aria-hidden="true">${brandMarkSvg('404')}</span>
      <span class="brand-copy"><span class="brand-title">Hey, Stutensee!</span><span class="brand-sub">Veranstaltungen &amp; Termine</span></span>
    </a>
  </div>
</header>
<main>
  <div class="card">
    <div class="code">404</div>
    <h1>Seite nicht gefunden</h1>
    <p>Diese Seite existiert nicht mehr. Vielleicht wurde der Veranstaltungskalender aktualisiert und der Link ist veraltet.</p>
    <a href="/" class="btn">Zurück zum Kalender</a>
  </div>
</main>
<footer class="site-footer">
  <button type="button" onclick="document.getElementById('imprint').hidden = !document.getElementById('imprint').hidden">Impressum</button>
  <span aria-hidden="true"> · </span>
  <span>Keine Cookies, kein Tracking</span>
  <div id="imprint" class="imprint" hidden>
    <strong>Angaben gemäß § 5 TMG</strong><br>Johannes Reuter · E-Mail: <span id="imprint-email"></span>
    <div style="margin-top:8px"><strong>Datenschutz</strong><br>Diese Seite erhebt keine personenbezogenen Daten. Es werden keine Cookies gesetzt, kein Tracking durchgeführt und keine Analysedienste genutzt.</div>
  </div>
</footer>
<script>document.getElementById('imprint-email').textContent='email@johannes-reuter.de';</script>
</body>
</html>`;
  return new Response(page, {
    status: 404,
    headers: { 'content-type': 'text/html;charset=utf-8' }
  });
}


