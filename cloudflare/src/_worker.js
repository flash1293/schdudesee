import { ensureAnalyticsTable, logRequest, classifyUserAgent } from './_analytics.js';

// ── SSR Constants ─────────────────────────────────────────────────────
const THEME_KEYS = new Set(['Sport','Musik','Kultur','Kirche','Kinder','Fest','Markt','Workshop','Bildung','Natur','Senioren','Digital','Handwerk','Essen','Treff','Politik','Verein','Wohltätigkeit','Sonstiges']);

const DISTRICT_KEYS = new Set(['Blankenloch','Bruchsal','Bretten','Büchenau','Büchig','Durlach','Eggenstein','Friedrichstal','Graben-Neudorf','Hagsfeld','Karlsruhe-Innenstadt','Leopoldshafen','Linkenheim','Neureut','Neuthard','Rintheim','Spöck','Staffort','Waldstadt','Weingarten']);
const DISTRICT_LIST_STR = [...DISTRICT_KEYS].sort().join(', ');

const TAG_EMOJIS = {
  'Sport':'⚽','Musik':'🎵','Kultur':'🎭','Kirche':'⛪','Kinder':'🧒','Fest':'🎉',
  'Markt':'🛒','Workshop':'🔧','Bildung':'📚','Natur':'🌿','Senioren':'👴','Digital':'💻',
  'Handwerk':'✂️','Essen':'🍽️','Treff':'☕','Politik':'🗳️','Verein':'🤝','Wohltätigkeit':'❤️',
  'Sonstiges':'📌'
};

const SSR_PER_PAGE = 12;

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
  if (url.pathname === '/api/chat' && request.method === 'POST') return serveChat(request, env);
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
  const dateFrom = p.get('date_from') || new Date().toISOString().slice(0, 10);
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

  return { events: results, total, page, totalPages, perPage, dateFrom };
}

/** Render a single event card HTML (server-side). */
function renderEventCard(event, condensedMode = false) {
  const e = event;
  const tags = (e.tags || '').split(',').map(t => t.trim()).filter(Boolean);
  const themeTags = tags.filter(t => THEME_KEYS.has(t));
  const locTags = tags.filter(t => DISTRICT_KEYS.has(t));

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

  // Build the detail link (visible link emoji for events that have an external URL)
  const detailLink = eventUrl
    ? `<a href="${escapeHtml(eventDetailPath)}" class="detail-link" title="Details">🔗</a>`
    : '';

  // Title with link
  let titleHtml;
  if (eventUrl) {
    titleHtml = `<a href="${escapeHtml(eventUrl)}" target="_blank" rel="noopener" onclick="event.stopPropagation()">${titleEscaped}<span class="ext-link">↗</span></a>`;
  } else {
    titleHtml = `<a href="${escapeHtml(eventDetailPath)}">${titleEscaped}</a>`;
  }

  // Condensed location hint
  const condensedLocHtml = locTags.length > 0
    ? locTags.map(t => ` 📍 ${escapeHtml(t)}`).join('')
    : (locationEscaped ? ` 📍 ${locationEscaped}` : '');

  // Build the card
  const titleAria = escapeHtml(e.title || 'Veranstaltung');
  let html = `<article class="event" id="event-${e.id}" aria-label="${titleAria}">
      <div class="event-body">
        <h2><span class="cat-emojis${hasTwo ? ' has-two' : ''}">${emojiHtml}</span><span class="cat-title">${titleHtml}${detailLink}<span class="condensed-location">${condensedLocHtml}</span></span></h2>
        <div class="event-meta">
          ${e.date_start ? `<span>📅 ${fmtDate(e.date_start)}${e.date_end && e.date_end !== e.date_start ? ` – ${fmtDate(e.date_end)}` : ''}</span>` : ''}
          ${e.time_raw ? `<span>🕐 ${escapeHtml(e.time_raw)}</span>` : ''}
          ${locationEscaped ? `<span>📍 ${locationEscaped}</span>` : ''}
        </div>
        ${descEscaped ? `<div class="event-desc">${descEscaped}</div>` : ''}
        ${organizerEscaped || locTags.length > 0 ? `<div class="event-tags">${organizerEscaped ? `<span class="tag tag-organizer">${organizerEscaped}</span>` : ''}${locTags.map(t => `<span class="tag tag-location">📍 ${escapeHtml(t)}</span>`).join('')}</div>` : ''}
        ${e.recurring_group_id ? `<span class="recurring-toggle" onclick="event.stopPropagation();toggleRecurring(${e.id}, ${e.recurring_group_id}, this)">▸ Alle Termine</span><div id="recurring-${e.id}" class="recurring-list" style="display:none"></div>` : ''}
      </div>
    </article>`;
  return html;
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

/** Render multiple event cards with date separators. Skips events without a date. */
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
      parts.push(`<div class="date-separator"><span class="date-sep-day">${badge.day}.</span><span class="date-sep-month"> ${badge.month}</span><span class="date-sep-date"> ${relativeDate(e.date_start)}</span></div>`);
    }
    parts.push(renderEventCard(e));
  }
  return parts.join('\n');
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

/** Render pagination as <a> links for crawlers. */
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

  let html = '<nav aria-label="Seitennavigation">';
  if (page > 1) html += `<a href="${buildUrl(1)}" class="page-link">« Erste</a> <a href="${buildUrl(page - 1)}" class="page-link" rel="prev">‹ Zurück</a> `;
  html += `<span class="page-info" aria-current="page">Seite ${page} von ${totalPages}</span> `;
  if (page < totalPages) html += `<a href="${buildUrl(page + 1)}" class="page-link" rel="next">Weiter ›</a> <a href="${buildUrl(totalPages)}" class="page-link">Letzte »</a>`;
  html += '</nav>';
  return html;
}

/** Render the intro paragraph. */
function renderIntro() {
  return `<div class="intro-text" style="margin-bottom:12px;padding:8px 0;font-size:14px;color:var(--text-muted);line-height:1.6">
    <p>Hey, Stutensee! Der Veranstaltungskalender für Stutensee und Umgebung. Entdecke Feste, Märkte, Konzerte, Sportevents, kirchliche Termine, Kinderangebote und mehr in <strong>Blankenloch</strong>, <strong>Büchig</strong>, <strong>Friedrichstal</strong>, <strong>Spöck</strong>, <strong>Staffort</strong> und allen anderen Ortsteilen. Gefiltert nach Kategorie, Ort und Datum.</p>
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
function injectIntoTemplate(template, { events, page, totalPages, jsonLd, breadcrumbJsonLd, paginationHtml, introHtml, initialData, ogTags }) {
  return template
    .replace('<!--SSR_OG_TAGS-->', ogTags || '')
    .replace('<!--SSR_JSON_LD-->', jsonLd || '')
    .replace('<!--SSR_BREADCRUMB-->', breadcrumbJsonLd || '')
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
    const html = injectIntoTemplate(indexHtml, {
      events: eventCardsHtml,
      page: result.page,
      totalPages: result.totalPages,
      jsonLd: jsonLdHtml,
      breadcrumbJsonLd: breadcrumbJsonLdHtml,
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
  const wheres = ["tags != 'blocked'"];
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
    `SELECT id, title, date_start, date_end, time_raw, location, organizer, description, event_url, tags
     FROM curated_events ${where} ORDER BY date_start ASC, id LIMIT ? OFFSET ?`
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
  }));

  return { events, total, page, per_page: perPage, total_pages: Math.ceil(total / perPage) };
}

/** Get single event details from D1. */
async function getEventDetails(params, env) {
  const db = env.STUTENSEE_DB;
  const row = await db.prepare(
    `SELECT id, title, date_start, date_end, time_raw, location, organizer, description, event_url, tags
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
  };
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

  if (!row) {
    // Old URL recovery: try slug first (more reliable than positional ID mapping),
    // then fall back to id_redirects table.

    const urlSlug = parts[3] || '';
    if (urlSlug && eventId < 100000) {
      try {
        const { results } = await env.STUTENSEE_DB.prepare(
          `SELECT id, title FROM curated_events WHERE tags != 'blocked'`
        ).all();
        for (const r of results) {
          if (eventSlug(r) === urlSlug) {
            const newPath = eventPath(r);
            return new Response(null, { status: 301, headers: { 'location': newPath + url.search, 'cache-control': 'public, max-age=31536000' } });
          }
        }
      } catch (e) {
        // Fallback failed; try id_redirects below
      }
    }

    // Check id_redirects table (positional mapping from old autoincrement IDs)
    try {
      const redirect = await env.STUTENSEE_DB.prepare(
        `SELECT new_id FROM id_redirects WHERE old_id = ?`
      ).bind(eventId).first();
      if (redirect) {
        const newRow = await env.STUTENSEE_DB.prepare(
          `SELECT id, title FROM curated_events WHERE id = ? AND tags != 'blocked'`
        ).bind(redirect.new_id).first();
        if (newRow) {
          const newPath = eventPath(newRow);
          return new Response(null, { status: 301, headers: { 'location': newPath + url.search, 'cache-control': 'public, max-age=31536000' } });
        }
      }
    } catch (e) {
      // id_redirects table may not exist yet
    }

    return new Response('Not found', { status: 404 });
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
  };

  const tags = (e.tags || '').split(',').map(t => t.trim()).filter(Boolean);
  const locTags = tags.filter(t => DISTRICT_KEYS.has(t));
  const locationName = locTags.length > 0 ? locTags[0] : (e.location || 'Stutensee');

  // Build page title and meta
  const pageTitle = `${e.title} – Hey, Stutensee!`;
  const metaDesc = `${e.title} am ${fmtDate(e.date_start)}${e.location ? ' in ' + e.location : ' in ' + locationName}. ${e.description ? e.description.substring(0, 150) : 'Alle Veranstaltungen in Stutensee auf einen Blick.'}`;

  // JSON-LD
  const jsonLd = renderJsonLd([{ ...e, title: row.title, description: row.description }]);

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
<link rel="canonical" href="https://hey-stutensee.de${eventPath(row)}">
<link rel="icon" type="image/png" href="/favicon.png">
${ogTagsHtml}
${jsonLd}
${breadcrumbJsonLd}
<style>
:root{--bg:#f4f6f8;--text:#111827;--text-muted:#4b5563;--card-bg:#fff;--card-border:#e2e8f0;--primary:#0d3a71;--desc:#4a5568;--tag-org-bg:#fef3c7;--tag-org-text:#92400e;--tag-loc-bg:#ede9fe;--tag-loc-text:#5b21b6;--tag-bg:#fef3c7;--tag-text:#92400e;--footer-text:#4b5563;--imprint-text:#374151;--shadow:0 2px 8px rgba(13,124,102,0.06)}
html.dark{--bg:#0f172a;--text:#e2e8f0;--text-muted:#94a3b8;--card-bg:#1e293b;--card-border:#334155;--primary:#1e40af;--link:#60a5fa;--link-hover:#93c5fd;--desc:#cbd5e1;--tag-org-bg:#422006;--tag-org-text:#fbbf24;--tag-loc-bg:#1e1b4b;--tag-loc-text:#a78bfa;--tag-bg:#422006;--tag-text:#fbbf24;--footer-text:#94a3b8;--imprint-text:#94a3b8;--shadow:0 2px 8px rgba(0,0,0,0.3)}
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
function toggleDark(){document.documentElement.classList.toggle('dark');var isDark=document.documentElement.classList.contains('dark');localStorage.setItem('dark',isDark?'1':'0');document.getElementById('dark-toggle').textContent=isDark?'☀️':'🌙'}
(function(){var d=document.documentElement,s=localStorage.getItem('dark');if(s!==null){if(s==='1')d.classList.add('dark')}else if(window.matchMedia('(prefers-color-scheme:dark)').matches){d.classList.add('dark')}document.getElementById('dark-toggle').textContent=d.classList.contains('dark')?'☀️':'🌙';window.matchMedia('(prefers-color-scheme:dark)').addEventListener('change',function(e){if(localStorage.getItem('dark')!==null)return;if(e.matches){d.classList.add('dark')}else{d.classList.remove('dark')}document.getElementById('dark-toggle').textContent=d.classList.contains('dark')?'☀️':'🌙'})})()
</script>
</head>
<body>
<header><div class="header-inner"><div class="header-text"><h1>Hey, Stutensee!</h1></div></div></header>
<div class="container">
  <a href="/" class="back-link">← Zurück zur Übersicht</a>
  <article class="card" aria-label="${escapeHtml(e.title)}">
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
  </article>
</div>
<footer><a href="#" onclick="event.preventDefault();document.getElementById('imprint').style.display='block'" style="color:var(--footer-text);text-decoration:underline">Impressum</a><span style="margin:0 8px">·</span><span id="dark-toggle" onclick="toggleDark()" style="cursor:pointer;font-size:16px" title="Dark Mode umschalten">🌙</span><div id="imprint" style="display:none;margin-top:12px;color:var(--imprint-text);line-height:1.6"><strong>Angaben gemäß §5 TMG</strong><br>Johannes Reuter<br>E-Mail: email@johannes-reuter.de<br><br><strong>Haftung für Inhalte</strong><br>Als Diensteanbieter sind wir für eigene Inhalte auf dieser Seite verantwortlich.<br><strong>Datenschutz</strong><br>Diese Seite erhebt keinerlei personenbezogene Daten. Es werden keine Cookies gesetzt, kein Tracking durchgeführt und keine Analysedienste genutzt.</div></footer>
</body>
</html>`;

  return new Response(body, { headers: { 'content-type': 'text/html;charset=utf-8', 'cache-control': 'public, max-age=3600' } });
}

/** Update sitemap to include event URLs. */
async function serveSitemapXml(env) {
  // Fetch all event IDs for the sitemap. Google supports up to 50,000 URLs per sitemap,
  // so cap at 50,000 as a safety net.
  let urls = '<url><loc>https://hey-stutensee.de/</loc><changefreq>daily</changefreq><priority>1.0</priority></url>';

  try {
    const { results } = await env.STUTENSEE_DB.prepare(
      `SELECT id, title FROM curated_events WHERE tags != 'blocked' ORDER BY date_start DESC LIMIT 50000`
    ).all();

    for (const row of results) {
      urls += `<url><loc>https://hey-stutensee.de${eventPath(row)}</loc><changefreq>monthly</changefreq><priority>0.5</priority></url>`;
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
  const dateFrom = p.get('date_from') || new Date().toISOString().slice(0, 10);
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

  return json({
    totals: { total: totals.total, total_bytes: totals.total_bytes, avg_latency: totals.avg_latency },
    by_path: byPath.results,
    recent: recent.results,
    user_agent_breakdown: uaBreakdown,
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


