/**
 * Request analytics module for was-geht-stutensee.de
 *
 * Logs basic request metrics to a separate D1 database.
 * No personal data (no IP, no user-agent, no browser info).
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
 *     search_query TEXT,                 -- ?search=... (for /api/list)
 *     tags_filter TEXT,                  -- ?tag=... (comma-separated)
 *     organizer_filter TEXT,             -- ?organizer=...
 *     location_filter TEXT,              -- ?location=...
 *     date_from TEXT                     -- ?date_from=...
 *   )
 */

const SCHEMA = `
  CREATE TABLE IF NOT EXISTS request_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp TEXT NOT NULL,
    path TEXT NOT NULL,
    method TEXT NOT NULL,
    status INTEGER,
    response_size INTEGER,
    latency_ms REAL,
    search_query TEXT,
    tags_filter TEXT,
    organizer_filter TEXT,
    location_filter TEXT,
    date_from TEXT
  );
  CREATE INDEX IF NOT EXISTS idx_request_log_timestamp ON request_log(timestamp);
  CREATE INDEX IF NOT EXISTS idx_request_log_path ON request_log(path);
`;

/**
 * Ensure the analytics table exists.
 */
export async function ensureAnalyticsTable(env) {
  if (!env.REQUEST_DB) return; // silently skip if not configured
  try {
    await env.REQUEST_DB.prepare(SCHEMA).all();
  } catch (err) {
    // Don't crash the request if analytics DB fails
    console.error('Analytics DB init failed:', err.message);
  }
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

  const params = url.searchParams;
  let searchQuery = null;
  let tagsFilter = null;
  let organizerFilter = null;
  let locationFilter = null;
  let dateFrom = null;

  // Only extract param details for /api/* endpoints
  if (url.pathname.startsWith('/api/')) {
    searchQuery = params.get('search') || null;
    dateFrom = params.get('date_from') || null;
    organizerFilter = params.get('organizer') || null;
    locationFilter = params.get('location') || null;

    const tags = params.getAll('tag');
    tagsFilter = tags.length > 0 ? tags.join(',') : null;
  }

  try {
    await env.REQUEST_DB.prepare(
      `INSERT INTO request_log (timestamp, path, method, status, response_size, latency_ms, search_query, tags_filter, organizer_filter, location_filter, date_from)
       VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)`
    ).bind(
      new Date().toISOString(),
      url.pathname,
      request.method,
      response.status,
      responseSize,
      latencyMs,
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
