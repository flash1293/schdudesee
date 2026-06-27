/**
 * Request analytics module for was-geht-stutensee.de
 *
 * Logs basic request metrics to a separate D1 database.
 * Only stores User-Agent for bot/real-user classification — no IPs, no cookies.
 *
 * Schema:
 *   request_log (
 *     id INTEGER PRIMARY KEY AUTOINCREMENT,
 *     timestamp TEXT NOT NULL,           -- ISO 8601
 *     path TEXT NOT NULL,                -- e.g. /api/list
 *     method TEXT NOT NULL,              -- GET, POST, etc.
 *     status INTEGER,                    -- HTTP status code
 *     response_size INTEGER,             -- bytes
 *     latency_ms REAL,                   -- milliseconds
 *     user_agent TEXT,                   -- User-Agent header (for bot/real classification)
 *     search_query TEXT,                 -- ?search=... (for /api/list)
 *     tags_filter TEXT,                  -- ?tag=... (comma-separated)
 *     organizer_filter TEXT,             -- ?organizer=...
 *     location_filter TEXT,              -- ?location=...
 *     date_from TEXT                     -- ?date_from=...
 *   )
 */

const SCHEMA_TABLE = `
  CREATE TABLE IF NOT EXISTS request_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp TEXT NOT NULL,
    path TEXT NOT NULL,
    method TEXT NOT NULL,
    status INTEGER,
    response_size INTEGER,
    latency_ms REAL,
    user_agent TEXT,
    search_query TEXT,
    tags_filter TEXT,
    organizer_filter TEXT,
    location_filter TEXT,
    date_from TEXT
  );
`;

const SCHEMA_INDEX = `
  CREATE INDEX IF NOT EXISTS idx_request_log_timestamp ON request_log(timestamp);
`;

/**
 * Migrate existing tables: add user_agent column if missing.
 */
export async function migrateAnalyticsTable(env) {
  if (!env.REQUEST_DB) return;
  try {
    await env.REQUEST_DB.prepare('ALTER TABLE request_log ADD COLUMN user_agent TEXT').run();
  } catch (err) {
    // Column already exists or other benign error — ignore
  }
}

/**
 * Ensure the analytics table exists.
 */
export async function ensureAnalyticsTable(env) {
  if (!env.REQUEST_DB) return;
  try {
    // Run schema statements separately (D1 doesn't support multi-statement in one prepare)
    await env.REQUEST_DB.prepare(SCHEMA_TABLE).run();
    await env.REQUEST_DB.prepare(SCHEMA_INDEX).run();
    await migrateAnalyticsTable(env);
  } catch (err) {
    console.error('Analytics DB init failed:', err.message);
  }
}

/**
 * Classify a User-Agent string into a category.
 * Only uses the UA string — no active tracking, no cookies, no IPs.
 */
export function classifyUserAgent(ua) {
  if (!ua || ua.trim() === '') return 'empty';

  const u = ua.toLowerCase();

  // Known bot/crawler patterns
  const botPatterns = [
    'curl', 'wget', 'python-requests', 'python/',
    'go-http-client', 'okhttp', 'java/',
    'bot', 'crawler', 'spider', 'scanner', 'crawling',
    'googlebot', 'bingbot', 'yahoo! slurp', 'duckduckbot',
    'baiduspider', 'yandexbot', 'facebookexternalhit',
    'slackbot', 'discordbot', 'twitterbot',
    'ahrefsbot', 'semrushbot', 'mj12bot', 'dotbot',
    'cloudflare-alwaysonline', 'cloudflare-healthchecks',
  ];
  for (const pattern of botPatterns) {
    if (u.includes(pattern)) return 'bot';
  }

  // Known real browser indicators
  const browserPatterns = ['mozilla', 'chrome', 'safari', 'firefox', 'edge', 'opr/'];
  for (const pattern of browserPatterns) {
    if (u.includes(pattern)) return 'browser';
  }

  return 'unknown';
}

/**
 * Log a request to the analytics database.
 * Extracts relevant query params from event API calls.
 */
export async function logRequest(env, request, response, startTime) {
  if (!env.REQUEST_DB) return;

  const url = new URL(request.url);
  const latencyMs = (Date.now() - startTime);
  const contentLength = response.headers.get('content-length');
  const responseSize = contentLength ? parseInt(contentLength, 10) : 0;

  // Only store User-Agent for classification — no IP, no cookies
  const userAgent = request.headers.get('User-Agent') || null;

  const params = url.searchParams;
  let searchQuery = null;
  let tagsFilter = null;
  let organizerFilter = null;
  let locationFilter = null;
  let dateFrom = null;

  // Only extract param details for endpoints that use them
  if (url.pathname === '/api/list') {
    searchQuery = params.get('search') || null;
    dateFrom = params.get('date_from') || null;
    organizerFilter = params.get('organizer') || null;
    locationFilter = params.get('location') || null;

    const tags = params.getAll('tag');
    tagsFilter = tags.length > 0 ? tags.join(',') : null;
  }

  try {
    await env.REQUEST_DB.prepare(
      `INSERT INTO request_log (timestamp, path, method, status, response_size, latency_ms, user_agent, search_query, tags_filter, organizer_filter, location_filter, date_from)
       VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)`
    ).bind(
      new Date().toISOString(),
      url.pathname,
      request.method,
      response.status,
      responseSize,
      latencyMs,
      userAgent,
      searchQuery,
      tagsFilter,
      organizerFilter,
      locationFilter,
      dateFrom
    ).run();
  } catch (err) {
    // Don't crash the request if analytics DB fails
    console.error('Analytics log failed:', err.message);
  }
}
