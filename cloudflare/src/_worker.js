import { ensureAnalyticsTable, logRequest } from './_analytics.js';

// ── SSR Constants ─────────────────────────────────────────────────────
const THEME_KEYS = new Set(['Sport','Musik','Kultur','Kirche','Kinder','Fest','Markt','Workshop','Bildung','Natur','Senioren','Digital','Handwerk','Essen','Treff','Politik','Verein','Wohltätigkeit','Sonstiges']);

const TAG_EMOJIS = {
  'Sport':'⚽','Musik':'🎵','Kultur':'🎭','Kirche':'⛪','Kinder':'🧒','Fest':'🎉',
  'Markt':'🛒','Workshop':'🔧','Bildung':'📚','Natur':'🌿','Senioren':'👴','Digital':'💻',
  'Handwerk':'✂️','Essen':'🍽️','Treff':'☕','Politik':'🗳️','Verein':'🤝','Wohltätigkeit':'❤️',
  'Sonstiges':'📌'
};

const SSR_PER_PAGE = 50;

// ── Exports ───────────────────────────────────────────────────────────
export default {
  async fetch(request, env, ctx) {
    const startTime = Date.now();
    try { await ensureAnalyticsTable(env); } catch {}
    let response;
    try {
      response = await routeRequest(request, env);
    } catch (err) {
      console.error('Worker error:', err.message);
      response = new Response('Internal error', { status: 500 });
    }
    ctx.waitUntil(logRequest(env, request, response, startTime));
    return response;
  }
};

// ── Router ────────────────────────────────────────────────────────────
async function routeRequest(request, env) {
  const url = new URL(request.url);

  // Serve SSR-enhanced HTML for the main page
  if (url.pathname === '/') return serveSsrPage(env, url);

  // Static assets
  if (url.pathname === '/favicon.png' && typeof faviconB64 !== 'undefined' && faviconB64) {
    const img = Uint8Array.from(atob(faviconB64), c => c.charCodeAt(0));
    return new Response(img, { headers: { 'content-type': 'image/png', 'cache-control': 'public, max-age=86400' } });
  }

  // API routes
  if (url.pathname === '/api/list') return serveEvents(env, url);
  if (url.pathname === '/api/theme') return serveTags(env);
  if (url.pathname === '/api/districts') return serveDistricts(env);
  if (url.pathname === '/api/organizer') return serveOrganizers(env);
  if (url.pathname === '/api/info') return serveStats(env);
  if (url.pathname === '/api/stats') return serveReqStats(env);
  if (url.pathname === '/robots.txt') return serveRobotsTxt();
  if (url.pathname.startsWith('/api/same/')) return serveRecurring(env, url.pathname.split('/').pop());
  if (url.pathname === '/llms.txt') return serveLlmTxt();
  if (url.pathname === '/.well-known/security.txt') return serveSecurityTxt();
  if (url.pathname === '/sitemap.xml') return serveSitemapXml(env);

  // Event detail pages: /events/{id}/{slug}
  if (url.pathname.startsWith('/events/')) return serveEventPage(env, url);

  return new Response('Not found', { status: 404 });
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
  return slugify(event.title);
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
  const dateFrom = p.get('date_from') || '';
  const organizer = p.get('organizer') || '';
  const hideRecurring = p.get('hide_recurring') === 'true';

  const db = env.STUTENSEE_DB;
  const wheres = ["tags != 'blocked'"];
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
    `SELECT id, title, date_start, date_end, time_raw, location, organizer, description, event_url, sources, tags, recurring_group_id
     FROM curated_events ${where} ORDER BY date_start ASC, id LIMIT ? OFFSET ?`
  ).bind(...args, perPage, offset).all();

  return { events: results, total, page, totalPages, perPage };
}

/** Render a single event card HTML (server-side). */
function renderEventCard(event, condensedMode = false) {
  const e = event;
  const tags = (e.tags || '').split(',').map(t => t.trim()).filter(Boolean);
  const themeTags = tags.filter(t => THEME_KEYS.has(t));
  const locTags = tags.filter(t => !THEME_KEYS.has(t));

  // Build emoji HTML
  const themeEmojis = themeTags.map(t => TAG_EMOJIS[t] || '📌').filter(Boolean);
  let emojiHtml = '';
  const hasTwo = themeEmojis.length === 2;
  if (themeEmojis.length === 0) {
    emojiHtml = '<span class="ce">📌</span>';
  } else if (themeEmojis.length === 1) {
    emojiHtml = `<span class="ce">${escapeHtml(themeEmojis[0])}</span>`;
  } else {
    emojiHtml = `<span class="ce ce-tl">${escapeHtml(themeEmojis[0])}</span><span class="ce ce-br ce-double">${escapeHtml(themeEmojis[1])}</span>`;
  }

  const titleEscaped = escapeHtml(e.title);
  const locationEscaped = e.location ? escapeHtml(e.location) : '';
  const organizerEscaped = e.organizer ? escapeHtml(e.organizer) : '';
  const descEscaped = e.description ? escapeHtml(e.description) : '';
  const eventUrl = e.event_url || '';
  const path = eventPath(e);
  const eventDetailPath = path;

  // Title with link
  let titleHtml;
  if (eventUrl) {
    titleHtml = `<a href="${escapeHtml(eventUrl)}" target="_blank" rel="noopener">${titleEscaped}<span class="ext-link">↗</span></a>`;
  } else {
    titleHtml = `<a href="${escapeHtml(eventDetailPath)}">${titleEscaped}</a>`;
  }

  // Add a link to the event detail page even if it has an external URL
  // The title itself links to the external URL (if present), but we also make the whole card clickable via the event detail page
  const eventDetailLink = eventUrl ? ` <a href="${escapeHtml(eventDetailPath)}" style="font-size:12px;opacity:0.4;text-decoration:none;color:inherit" title="Details">🔗</a>` : '';

  // Condensed location hint
  const condensedLocHtml = locTags.length > 0
    ? locTags.map(t => ` 📍 ${escapeHtml(t)}`).join('')
    : (locationEscaped ? ` 📍 ${locationEscaped}` : '');

  // Build the card
  let html = `<div class="event" id="event-${e.id}">
      <div class="event-body">
        <h2><span class="cat-emojis${hasTwo ? ' has-two' : ''}">${emojiHtml}</span><span class="cat-title">${titleHtml}${eventDetailLink}<span class="condensed-location">${condensedLocHtml}</span></span></h2>
        <div class="event-meta">
          ${e.date_start ? `<span>📅 ${fmtDate(e.date_start)}${e.date_end && e.date_end !== e.date_start ? ` – ${fmtDate(e.date_end)}` : ''}</span>` : ''}
          ${e.time_raw ? `<span>🕐 ${escapeHtml(e.time_raw)}</span>` : ''}
          ${locationEscaped ? `<span>📍 ${locationEscaped}</span>` : ''}
        </div>
        ${descEscaped ? `<div class="event-desc">${descEscaped}</div>` : ''}
        ${organizerEscaped || locTags.length > 0 ? `<div class="event-tags">${organizerEscaped ? `<span class="tag tag-organizer">${organizerEscaped}</span>` : ''}${locTags.map(t => `<span class="tag tag-location">📍 ${escapeHtml(t)}</span>`).join('')}</div>` : ''}
        ${e.recurring_group_id ? `<span class="recurring-toggle" onclick="event.stopPropagation();toggleRecurring(${e.id}, ${e.recurring_group_id}, this)">▸ Alle Termine</span><div id="recurring-${e.id}" class="recurring-list" style="display:none"></div>` : ''}
      </div>
    </div>`;
  return html;
}

/** Render multiple event cards. */
function renderEventCards(events) {
  return events.map(e => renderEventCard(e)).join('\n');
}

/** Render JSON-LD for an array of events. */
function renderJsonLd(events) {
  if (!events || events.length === 0) return '';
  const items = events.map(e => {
    const tags = (e.tags || '').split(',').map(t => t.trim()).filter(Boolean);
    const locTags = tags.filter(t => !THEME_KEYS.has(t));
    const locationName = locTags.length > 0 ? locTags[0] : (e.location || 'Stutensee');
    const desc = e.description ? decode(e.description) : `Veranstaltung in ${locationName}`;
    const url = e.event_url || `https://was-geht-stutensee.de${eventPath(e)}`;
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

/** Render pagination as <a> links for crawlers. */
function renderPaginationLinks(page, totalPages, params) {
  if (totalPages <= 1) return '';

  function buildUrl(p) {
    const u = new URL('https://was-geht-stutensee.de/');
    if (p > 1) u.searchParams.set('page', p);
    if (params) {
      for (const [k, v] of params) {
        if (k !== 'page') u.searchParams.append(k, v);
      }
    }
    return u.pathname + u.search;
  }

  let html = '';
  if (page > 1) html += `<a href="${buildUrl(1)}" class="page-link">« Erste</a> <a href="${buildUrl(page - 1)}" class="page-link" rel="prev">‹ Zurück</a> `;
  html += `<span class="page-info">Seite ${page} von ${totalPages}</span> `;
  if (page < totalPages) html += `<a href="${buildUrl(page + 1)}" class="page-link" rel="next">Weiter ›</a> <a href="${buildUrl(totalPages)}" class="page-link">Letzte »</a>`;
  return html;
}

/** Render the intro paragraph. */
function renderIntro() {
  return `<div class="intro-text" style="margin-bottom:12px;padding:8px 0;font-size:14px;color:var(--text-muted);line-height:1.6">
    <p>Was geht, Stutensee? Der Veranstaltungskalender für Stutensee und Umgebung. Entdecke Feste, Märkte, Konzerte, Sportevents, kirchliche Termine, Kinderangebote und mehr in <strong>Blankenloch</strong>, <strong>Büchig</strong>, <strong>Friedrichstal</strong>, <strong>Spöck</strong>, <strong>Staffort</strong> und allen anderen Ortsteilen. Gefiltert nach Kategorie, Ort und Datum.</p>
  </div>`;
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
function injectIntoTemplate(template, { events, page, totalPages, jsonLd, paginationHtml, introHtml, initialData, ogTags }) {
  return template
    .replace('<!--SSR_OG_TAGS-->', ogTags || '')
    .replace('<!--SSR_JSON_LD-->', jsonLd || '')
    .replace('<!--SSR_INTRO-->', introHtml || '')
    .replace('<!--SSR_EVENTS-->', events || '')
    .replace('<!--SSR_PAGINATION-->', paginationHtml || '')
    .replace('<!--SSR_INITIAL_DATA-->', initialData ? `<script id="ssr-data" type="application/json">${jsonForScriptTag(initialData)}</script>` : '');
}

/** Serve the main page with SSR content injected. Gracefully falls back to plain SPA if DB is unavailable. */
async function serveSsrPage(env, url) {
  try {
    const result = await fetchEventsForSsr(env, url);

    // Render event cards
    const eventCardsHtml = renderEventCards(result.events);

    // Render JSON-LD
    const jsonLdHtml = renderJsonLd(result.events);

    // Render pagination links
    const paginationHtml = renderPaginationLinks(result.page, result.totalPages, url.searchParams);

    // Render intro text (only on page 1)
    const introHtml = result.page === 1 ? renderIntro() : '';

    // Build initial data for JS hydration
    const params = {
      search: url.searchParams.get('search') || '',
      date_from: url.searchParams.get('date_from') || '',
      selectedThemes: url.searchParams.getAll('tag').filter(t => THEME_KEYS.has(t)),
      selectedLocations: url.searchParams.getAll('tag').filter(t => !THEME_KEYS.has(t)),
      selectedOrganizer: url.searchParams.get('organizer') || '',
      showRecurring: url.searchParams.get('hide_recurring') !== 'true',
      condensedMode: false,
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
      })),
      page: result.page,
      totalPages: result.totalPages,
      total: result.total,
      paginationHtml,
      params,
    };

    // Build OG tags for homepage
    const ogTitle = `Was geht, Stutensee? – Veranstaltungen und Termine in Stutensee`;
    const ogDesc = `Alle Veranstaltungen in Stutensee auf einen Blick: Feste, Märkte, Sport, Kirche, Kinderangebote und mehr.`;
    const ogUrl = url.searchParams.has('page')
      ? `https://was-geht-stutensee.de/?page=${result.page}`
      : 'https://was-geht-stutensee.de/';
    const ogTags = renderOgTags(ogTitle, ogDesc, ogUrl);

    // Inject into template
    const html = injectIntoTemplate(indexHtml, {
      events: eventCardsHtml,
      page: result.page,
      totalPages: result.totalPages,
      jsonLd: jsonLdHtml,
      paginationHtml,
      introHtml,
      initialData,
      ogTags,
    });

    return new Response(html, { headers: { 'content-type': 'text/html;charset=utf-8', 'cache-control': 'public, max-age=300' } });
  } catch (err) {
    // Fallback: serve plain SPA without SSR (e.g. when DB is unavailable)
    return new Response(indexHtml, { headers: { 'content-type': 'text/html;charset=utf-8' } });
  }
}

/** Serve an individual event page at /events/{id}/{slug}. */
async function serveEventPage(env, url) {
  const parts = url.pathname.split('/'); // ['', 'events', '{id}', '{slug}']
  if (!/^[0-9]+$/.test(parts[2])) return new Response('Not found', { status: 404 });
  const eventId = parseInt(parts[2]);

  const row = await env.STUTENSEE_DB.prepare(
    `SELECT id, title, date_start, date_end, time_raw, location, organizer, description, event_url, sources, tags, recurring_group_id
     FROM curated_events WHERE id = ? AND tags != 'blocked'`
  ).bind(eventId).first();

  if (!row) return new Response('Not found', { status: 404 });

  const e = {
    id: row.id, title: decode(row.title), date_start: row.date_start || '', date_end: row.date_end,
    time_raw: row.time_raw, location: decode(row.location), organizer: decode(row.organizer),
    description: decode(row.description), event_url: decode(row.event_url || ''),
    sources: decode(row.sources || ''), tags: row.tags || '',
    recurring_group_id: row.recurring_group_id,
  };

  const tags = (e.tags || '').split(',').map(t => t.trim()).filter(Boolean);
  const locTags = tags.filter(t => !THEME_KEYS.has(t));
  const locationName = locTags.length > 0 ? locTags[0] : (e.location || 'Stutensee');

  // Build page title and meta
  const pageTitle = `${e.title} – Was geht, Stutensee?`;
  const metaDesc = `${e.title} am ${fmtDate(e.date_start)}${e.location ? ' in ' + e.location : ' in ' + locationName}. ${e.description ? e.description.substring(0, 150) : 'Alle Veranstaltungen in Stutensee auf einen Blick.'}`;

  // JSON-LD
  const jsonLd = renderJsonLd([{ ...e, title: row.title, description: row.description }]);

  // OG tags for event detail page
  const eventUrl = `https://was-geht-stutensee.de${eventPath(row)}`;
  const ogTagsHtml = renderOgTags(pageTitle, metaDesc, eventUrl, 'article');

  // Build HTML
  const themeTags = tags.filter(t => THEME_KEYS.has(t));
  const themeEmojis = themeTags.map(t => TAG_EMOJIS[t] || '📌').filter(Boolean);
  let emojiHtml = '';
  const hasTwo = themeEmojis.length === 2;
  if (themeEmojis.length === 0) {
    emojiHtml = '<span class="ce">📌</span>';
  } else if (themeEmojis.length === 1) {
    emojiHtml = `<span class="ce">${escapeHtml(themeEmojis[0])}</span>`;
  } else {
    emojiHtml = `<span class="ce ce-tl">${escapeHtml(themeEmojis[0])}</span><span class="ce ce-br ce-double">${escapeHtml(themeEmojis[1])}</span>`;
  }

  const body = `<!DOCTYPE html>
<html lang="de">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>${escapeHtml(pageTitle)}</title>
<meta name="description" content="${escapeHtml(metaDesc)}">
<meta name="robots" content="index,follow">
<link rel="canonical" href="https://was-geht-stutensee.de${eventPath(row)}">
<link rel="icon" type="image/png" href="/favicon.png">
${ogTagsHtml}
${jsonLd}
<style>
:root{--bg:#f4f6f8;--text:#111827;--text-muted:#4b5563;--card-bg:#fff;--card-border:#e2e8f0;--primary:#0d3a71;--desc:#4a5568;--tag-org-bg:#fef3c7;--tag-org-text:#92400e;--tag-loc-bg:#ede9fe;--tag-loc-text:#5b21b6;--tag-bg:#fef3c7;--tag-text:#92400e;--footer-text:#4b5563;--shadow:0 2px 8px rgba(13,124,102,0.06)}
html.dark{--bg:#0f172a;--text:#e2e8f0;--text-muted:#94a3b8;--card-bg:#1e293b;--card-border:#334155;--primary:#1e40af;--link:#60a5fa;--link-hover:#93c5fd;--desc:#cbd5e1;--tag-org-bg:#422006;--tag-org-text:#fbbf24;--tag-loc-bg:#1e1b4b;--tag-loc-text:#a78bfa;--tag-bg:#422006;--tag-text:#fbbf24;--footer-text:#94a3b8;--shadow:0 2px 8px rgba(0,0,0,0.3)}
*,*::before,*::after{box-sizing:border-box;margin:0;padding:0}
body{font-family:system-ui,-apple-system,sans-serif;background:var(--bg);color:var(--text);line-height:1.6;min-height:100vh}
header{background:#0d3a71;color:#fff;padding:10px 24px}
.header-inner{max-width:1100px;margin:0 auto;display:flex;align-items:center;gap:14px}
.header-text h1{font-size:22px;font-weight:700}
.container{max-width:700px;margin:40px auto;padding:0 20px}
.card{background:var(--card-bg);border:1px solid var(--card-border);border-radius:12px;padding:24px 28px;box-shadow:var(--shadow)}
.card h1{font-size:24px;font-weight:700;margin-bottom:16px;display:flex;align-items:flex-start;gap:8px}
.meta{font-size:14px;color:var(--text-muted);margin-bottom:12px;display:flex;flex-wrap:wrap;gap:8px 16px}
.meta .label{font-weight:600;color:var(--text)}
.desc{font-size:15px;color:var(--desc);line-height:1.7;margin-top:16px}
.tags{margin-top:16px;display:flex;flex-wrap:wrap;gap:6px}
.tag{display:inline-block;font-size:12px;font-weight:600;padding:4px 12px;border-radius:20px}
.tag-organizer{background:var(--tag-org-bg);color:var(--tag-org-text)}
.tag-location{background:var(--tag-loc-bg);color:var(--tag-loc-text)}
.tag-tag{background:var(--tag-bg);color:var(--tag-text)}
a{color:var(--link,var(--primary))}
a:hover{color:var(--link-hover,var(--primary))}
.back-link{display:inline-block;margin-bottom:24px;color:var(--link,var(--primary));text-decoration:none;font-size:14px;font-weight:600}
.back-link:hover{text-decoration:underline}
footer{text-align:center;padding:24px;font-size:12px;color:var(--footer-text)}
@media(max-width:700px){.container{padding:0 12px}.card{padding:16px 18px}.card h1{font-size:20px}}
</style>
<script>
(function(){var d=document.documentElement,s=localStorage.getItem('dark');if(s!==null){if(s==='1')d.classList.add('dark')}else if(window.matchMedia('(prefers-color-scheme:dark)').matches){d.classList.add('dark')}})()
</script>
</head>
<body>
<header><div class="header-inner"><div class="header-text"><h1>Was geht, Stutensee?</h1></div></div></header>
<div class="container">
  <a href="/" class="back-link">← Zurück zur Übersicht</a>
  <div class="card">
    <h1><span class="cat-emojis${hasTwo ? ' has-two' : ''}">${emojiHtml}</span>${escapeHtml(e.title)}</h1>
    <div class="meta">
      ${e.date_start ? '<div><span class="label">Datum:</span> ' + fmtDate(e.date_start) + (e.date_end && e.date_end !== e.date_start ? ' – ' + fmtDate(e.date_end) : '') + '</div>' : ''}
      ${e.time_raw ? '<div><span class="label">Zeit:</span> ' + escapeHtml(e.time_raw) + '</div>' : ''}
      ${e.location ? '<div><span class="label">Ort:</span> ' + escapeHtml(e.location) + '</div>' : ''}
      ${e.organizer ? '<div><span class="label">Veranstalter:</span> ' + escapeHtml(e.organizer) + '</div>' : ''}
      ${e.event_url ? '<div><span class="label">Link:</span> <a href="' + escapeHtml(e.event_url) + '" target="_blank" rel="noopener">' + escapeHtml(e.event_url) + '</a></div>' : ''}
    </div>
    ${e.description ? '<div class="desc">' + escapeHtml(e.description) + '</div>' : ''}
    <div class="tags">
      ${tags.filter(t => THEME_KEYS.has(t)).map(t => '<span class="tag tag-tag">' + escapeHtml(t) + '</span>').join('')}
      ${locTags.map(t => '<span class="tag tag-location">📍 ' + escapeHtml(t) + '</span>').join('')}
      ${e.organizer ? '<span class="tag tag-organizer">' + escapeHtml(e.organizer) + '</span>' : ''}
    </div>
  </div>
</div>
<footer>Was geht, Stutensee?</footer>
</body>
</html>`;

  return new Response(body, { headers: { 'content-type': 'text/html;charset=utf-8', 'cache-control': 'public, max-age=3600' } });
}

/** Update sitemap to include event URLs. */
async function serveSitemapXml(env) {
  // Fetch up to 1000 event IDs for the sitemap
  let urls = '<url><loc>https://was-geht-stutensee.de/</loc><changefreq>daily</changefreq><priority>1.0</priority></url>';

  try {
    const { results } = await env.STUTENSEE_DB.prepare(
      `SELECT id, title FROM curated_events WHERE tags != 'blocked' ORDER BY date_start DESC LIMIT 1000`
    ).all();

    for (const row of results) {
      urls += `<url><loc>https://was-geht-stutensee.de${eventPath(row)}</loc><changefreq>monthly</changefreq><priority>0.5</priority></url>`;
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

async function serveReqStats(env) {
  if (!env.REQUEST_DB) return json({ error: 'Analytics not configured' }, 404);
  const totals = await env.REQUEST_DB.prepare(
    'SELECT COUNT(*) as total, COALESCE(SUM(response_size),0) as total_bytes, COALESCE(ROUND(AVG(latency_ms),1),0) as avg_latency FROM request_log'
  ).first();
  const byPath = await env.REQUEST_DB.prepare(
    'SELECT path, COUNT(*) as count, COALESCE(ROUND(AVG(latency_ms),1),0) as avg_latency, COALESCE(SUM(response_size),0) as total_bytes FROM request_log GROUP BY path ORDER BY count DESC LIMIT 20'
  ).all();
  const recent = await env.REQUEST_DB.prepare(
    'SELECT timestamp, path, status, response_size, latency_ms, search_query, tags_filter, organizer_filter, location_filter, date_from FROM request_log ORDER BY id DESC LIMIT 50'
  ).all();
  return json({
    totals: { total: totals.total, total_bytes: totals.total_bytes, avg_latency: totals.avg_latency },
    by_path: byPath.results,
    recent: recent.results,
  });
}

function serveRobotsTxt() {
  return new Response('User-agent: *\nAllow: /\nSitemap: https://was-geht-stutensee.de/sitemap.xml\n', {
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

function serveSecurityTxt() {
  return new Response(`# Security Contact
# If you find a security issue on was-geht-stutensee.de, please report it.
Contact: mailto:email@johannes-reuter.de
Canonical: https://was-geht-stutensee.de/.well-known/security.txt
Preferred-Languages: de, en
Expires: 2027-05-24T14:00:00.000Z
`, {
    headers: { 'content-type': 'text/plain;charset=utf-8', 'cache-control': 'public, max-age=86400' }
  });
}


