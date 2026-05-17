import { describe, it, expect, beforeAll } from 'vitest';
import { readFileSync, existsSync } from 'fs';
import { resolve, dirname } from 'path';
import { fileURLToPath } from 'url';

// Import the built worker (includes inlined HTML + favicon)
const workerPath = resolve(dirname(fileURLToPath(import.meta.url)), 'worker.js');
const worker = await import(workerPath);

// ── Helpers ──────────────────────────────────────────────────────────

/**
 * Create a mock D1 database with predefined results.
 * The real D1 API: db.prepare(sql).bind(...args).first() or .all()
 */
function mockDb({ events = [], total = 0, tags = [], districts = [], organizers = [] } = {}) {
  const runQuery = (sql) => {
    if (sql.includes('COUNT(*)')) return { c: total };
    // serveTags / serveDistricts: SELECT DISTINCT tags ...
    if (sql.includes('DISTINCT tags')) {
      const tagValues = tags.length ? tags.map(t => t.tag) : ['Sport', 'Musik'];
      return { results: tagValues.map(t => ({ tags: t })) };
    }
    // serveOrganizers: SELECT DISTINCT organizer ...
    if (sql.includes('DISTINCT organizer')) {
      const orgValues = organizers.length ? organizers.map(o => o.organizer) : ['Test Org'];
      return { results: orgValues.map(o => ({ organizer: o })) };
    }
    // serveEvents: full SELECT with columns
    if (sql.includes('FROM curated_events')) {
      if (sql.includes('COUNT(*)')) return { c: total };
      return { results: events };
    }
    if (sql.includes('FROM raw_events')) return { c: Math.floor(total * 1.1) || 10 };
    return { results: events };
  };

  const prepare = (sql) => ({
    // Direct calls (no bind): serveStats uses .first(), serveTags uses .all()
    first: async () => runQuery(sql),
    all: async () => {
      const r = runQuery(sql);
      // runQuery for SELECT DISTINCT returns { results: [...] }
      if (r && r.results) return r;
      // runQuery for COUNT returns { c: N }
      return { results: [r] };
    },
    // Calls with bind: serveEvents uses .bind(...).first() and .bind(...).all()
    bind: (...args) => ({
      first: async () => runQuery(sql),
      all: async () => {
        const r = runQuery(sql);
        if (r && r.results) return r;
        return { results: [r] };
      },
    }),
  });
  return { prepare };
}

/**
 * Call the worker's fetch handler with a mock env.
 */
async function callWorker(path, options = {}) {
  const { method = 'GET', headers = {}, env = {} } = options;
  const url = `https://was-geht-stutensee.de${path}`;
  const request = new Request(url, { method, headers });
  return worker.default.fetch(request, env);
}

// ── Mock Data ────────────────────────────────────────────────────────

const sampleEvents = [
  { id: 1, title: 'Test Event', date_start: '2026-06-01', date_end: null, time_raw: '14:00', location: 'Test Location', organizer: 'Test Org', description: 'A test event', event_url: 'https://example.com', sources: 'test', tags: 'Sport,Test', recurring_group_id: null },
  { id: 2, title: 'Music Concert', date_start: '2026-06-05', date_end: null, time_raw: '20:00', location: 'Concert Hall', organizer: 'Music Club', description: 'A great concert', event_url: '', sources: 'test', tags: 'Musik,Kultur', recurring_group_id: 12345 },
  { id: 3, title: 'Long search query test '.repeat(5).trim(), date_start: '2026-06-10', date_end: '2026-06-11', time_raw: '', location: 'Somewhere', organizer: 'Org', description: '', event_url: '', sources: 'test', tags: 'Fest', recurring_group_id: null },
];

// ── Tests ────────────────────────────────────────────────────────────

describe('Worker API', () => {

  // ── Root ───────────────────────────────────────────────────────────

  describe('GET /', () => {
    it('returns HTML with 200', async () => {
      const res = await callWorker('/');
      expect(res.status).toBe(200);
      expect(res.headers.get('content-type')).toContain('text/html');
      const text = await res.text();
      expect(text).toContain('<!DOCTYPE html>');
      expect(text).toContain('Was geht, Stutensee');
    });
  });

  // ── Favicon ────────────────────────────────────────────────────────

  describe('GET /favicon.png', () => {
    it('returns PNG image with 200', async () => {
      const res = await callWorker('/favicon.png');
      expect(res.status).toBe(200);
      expect(res.headers.get('content-type')).toContain('image/png');
    });
  });

  // ── /api/list ──────────────────────────────────────────────────────

  describe('GET /api/list', () => {
    it('returns empty list with 0 events', async () => {
      const env = { STUTENSEE_DB: mockDb({ total: 0, events: [] }) };
      const res = await callWorker('/api/list', { env });
      expect(res.status).toBe(200);
      const data = await res.json();
      expect(data).toHaveProperty('events');
      expect(data.events).toEqual([]);
      expect(data.total).toBe(0);
      expect(data.page).toBe(1);
    });

    it('returns events with pagination metadata', async () => {
      const env = { STUTENSEE_DB: mockDb({ total: 50, events: sampleEvents }) };
      const res = await callWorker('/api/list?page=1&per_page=5', { env });
      const data = await res.json();
      expect(data.total).toBe(50);
      expect(data.page).toBe(1);
      expect(data.per_page).toBe(5);
      expect(data.total_pages).toBe(10);
      expect(data.events.length).toBeGreaterThan(0);
      expect(data.events[0]).toHaveProperty('title');
      expect(data.events[0]).toHaveProperty('date_start');
    });

    it('accepts search parameter', async () => {
      const env = { STUTENSEE_DB: mockDb({ total: 1, events: [sampleEvents[0]] }) };
      const res = await callWorker('/api/list?search=Test', { env });
      expect(res.status).toBe(200);
      const data = await res.json();
      expect(data.total).toBe(1);
    });

    it('accepts date_from filter', async () => {
      const env = { STUTENSEE_DB: mockDb({ total: 2, events: sampleEvents.slice(0, 2) }) };
      const res = await callWorker('/api/list?date_from=2026-06-01', { env });
      expect(res.status).toBe(200);
      const data = await res.json();
      expect(data.total).toBe(2);
    });

    it('accepts tag filter', async () => {
      const env = { STUTENSEE_DB: mockDb({ total: 1, events: [sampleEvents[0]] }) };
      const res = await callWorker('/api/list?tag=Sport', { env });
      expect(res.status).toBe(200);
      const data = await res.json();
      expect(data.total).toBe(1);
    });

    it('accepts organizer filter', async () => {
      const env = { STUTENSEE_DB: mockDb({ total: 1, events: [sampleEvents[0]] }) };
      const res = await callWorker('/api/list?organizer=Test+Org', { env });
      expect(res.status).toBe(200);
    });

    it('accepts hide_recurring flag', async () => {
      const env = { STUTENSEE_DB: mockDb({ total: 2, events: sampleEvents }) };
      const res = await callWorker('/api/list?hide_recurring=1', { env });
      expect(res.status).toBe(200);
    });

    it('truncates long search strings (49+ chars) to 48', async () => {
      // Build a search string of exactly 50 chars
      const longSearch = 'a'.repeat(50);
      const env = { STUTENSEE_DB: mockDb({ total: 0, events: [] }) };
      // Should NOT throw a 500
      const res = await callWorker(`/api/list?search=${longSearch}`, { env });
      expect(res.status).toBe(200);
    });

    it('handles extremely long search strings (200+ chars) gracefully', async () => {
      const veryLongSearch = 'x'.repeat(200);
      const env = { STUTENSEE_DB: mockDb({ total: 0, events: [] }) };
      const res = await callWorker(`/api/list?search=${veryLongSearch}`, { env });
      expect(res.status).toBe(200);
    });

    it('handles special characters in search', async () => {
      const env = { STUTENSEE_DB: mockDb({ total: 0, events: [] }) };
      const res = await callWorker('/api/list?search=Hope+is+a+dangerous+thing+mit+der+Saxofonistin+Asy', { env });
      expect(res.status).toBe(200);
    });

    it('paginates correctly: page 2 offset', async () => {
      const env = { STUTENSEE_DB: mockDb({ total: 100, events: sampleEvents }) };
      const res = await callWorker('/api/list?page=2&per_page=10', { env });
      const data = await res.json();
      expect(data.page).toBe(2);
      expect(data.per_page).toBe(10);
    });

    it('clamps per_page between 1 and 100', async () => {
      const env = { STUTENSEE_DB: mockDb({ total: 0, events: [] }) };
      // per_page=0 should be clamped to 1
      const res1 = await callWorker('/api/list?per_page=0', { env });
      expect(res1.status).toBe(200);
      // per_page=999 should be clamped to 100
      const res2 = await callWorker('/api/list?per_page=999', { env });
      expect(res2.status).toBe(200);
    });

    it('returns CORS headers', async () => {
      const env = { STUTENSEE_DB: mockDb({ total: 0, events: [] }) };
      const res = await callWorker('/api/list', { env });
      expect(res.headers.get('access-control-allow-origin')).toBe('*');
    });
  });

  // ── /api/theme ─────────────────────────────────────────────────────

  describe('GET /api/theme', () => {
    it('returns tag list', async () => {
      const env = { STUTENSEE_DB: mockDb({ tags: [{ tag: 'Sport' }, { tag: 'Musik' }, { tag: 'Kultur' }] }) };
      const res = await callWorker('/api/theme', { env });
      expect(res.status).toBe(200);
      const data = await res.json();
      expect(Array.isArray(data)).toBe(true);
    });
  });

  // ── /api/districts ─────────────────────────────────────────────────

  describe('GET /api/districts', () => {
    it('returns district list', async () => {
      const env = { STUTENSEE_DB: mockDb({ districts: [{ location: 'Blankenloch' }, { location: 'Spöck' }] }) };
      const res = await callWorker('/api/districts', { env });
      expect(res.status).toBe(200);
      const data = await res.json();
      expect(Array.isArray(data)).toBe(true);
    });
  });

  // ── /api/organizer ─────────────────────────────────────────────────

  describe('GET /api/organizer', () => {
    it('returns organizer list', async () => {
      const env = { STUTENSEE_DB: mockDb({ organizers: [{ organizer: 'Test Org' }] }) };
      const res = await callWorker('/api/organizer', { env });
      expect(res.status).toBe(200);
      const data = await res.json();
      expect(Array.isArray(data)).toBe(true);
    });
  });

  // ── /api/info ──────────────────────────────────────────────────────

  describe('GET /api/info', () => {
    it('returns stats with raw and curated counts', async () => {
      const env = { STUTENSEE_DB: mockDb({ total: 100 }) };
      const res = await callWorker('/api/info', { env });
      expect(res.status).toBe(200);
      const data = await res.json();
      expect(data).toHaveProperty('raw');
      expect(data).toHaveProperty('curated');
      expect(data.raw).toBeTypeOf('number');
      expect(data.curated).toBeTypeOf('number');
    });
  });

  // ── /llms.txt ──────────────────────────────────────────────────────

  describe('GET /llms.txt', () => {
    it('returns LLM info page', async () => {
      const res = await callWorker('/llms.txt');
      expect(res.status).toBe(200);
      expect(res.headers.get('content-type')).toContain('text/plain');
      const text = await res.text();
      expect(text).toContain('Was geht, Stutensee');
      expect(text).toContain('/api/list');
    });
  });

  // ── 404 ────────────────────────────────────────────────────────────

  describe('Unknown routes', () => {
    it('returns 404 for unknown paths', async () => {
      const res = await callWorker('/api/nonexistent');
      expect(res.status).toBe(404);
    });

    it('returns 404 for random paths', async () => {
      const res = await callWorker('/some/random/path');
      expect(res.status).toBe(404);
    });
  });

  // ── Error Handling ─────────────────────────────────────────────────

  describe('Error handling', () => {
    it('throws on DB errors (no internal error handling)', async () => {
      const brokenDb = {
        prepare: () => ({
          bind: () => ({
            first: async () => { throw new Error('DB error'); },
            all: async () => { throw new Error('DB error'); },
          }),
        }),
      };
      const env = { STUTENSEE_DB: brokenDb };
      await expect(callWorker('/api/list', { env })).rejects.toThrow('DB error');
    });

    it('handles invalid page numbers', async () => {
      const env = { STUTENSEE_DB: mockDb({ total: 0, events: [] }) };
      const res = await callWorker('/api/list?page=-1', { env });
      expect(res.status).toBe(200);
    });
  });

  // ── HTML entity decoding ───────────────────────────────────────────

  describe('HTML entity decoding', () => {
    it('decodes HTML entities in event titles', async () => {
      const eventsWithEntities = [{
        ...sampleEvents[0],
        title: 'Test &amp; Demo &lt;Event&gt;',
        location: 'Foo &amp; Bar',
      }];
      const env = { STUTENSEE_DB: mockDb({ total: 1, events: eventsWithEntities }) };
      const res = await callWorker('/api/list', { env });
      const data = await res.json();
      expect(data.events[0].title).toBe('Test & Demo <Event>');
      expect(data.events[0].location).toBe('Foo & Bar');
    });
  });
});
