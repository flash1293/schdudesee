import { describe, it, expect, beforeAll, afterAll } from 'vitest';
import { resolve, dirname } from 'path';
import { fileURLToPath } from 'url';

import { createD1 } from './d1-wrapper.js';
import { createTestDb } from './test-db.js';

// Import the built worker
const workerPath = resolve(dirname(fileURLToPath(import.meta.url)), 'worker.js');
const worker = await import(workerPath);

// ── Helpers ──────────────────────────────────────────────────────────

/** Call the worker's fetch handler with a mock env and ctx. */
async function callWorker(path, options = {}) {
  const { method = 'GET', headers = {}, env = {} } = options;
  const url = `https://was-geht-stutensee.de${path}`;
  const request = new Request(url, { method, headers });
  const ctx = { waitUntil: (p) => p }; // mock ctx for waitUntil
  return worker.default.fetch(request, env, ctx);
}

// ── Setup ────────────────────────────────────────────────────────────

let db;
let env;

beforeAll(() => {
  db = createTestDb();
  env = { STUTENSEE_DB: createD1(db) };
});

afterAll(() => {
  if (db) db.close();
});

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
    it('returns all events with pagination', async () => {
      const res = await callWorker('/api/list?per_page=50', { env });
      expect(res.status).toBe(200);
      const data = await res.json();
      expect(data).toHaveProperty('events');
      expect(Array.isArray(data.events)).toBe(true);
      expect(data.total).toBeGreaterThan(0);
      expect(data.page).toBe(1);
      expect(data.per_page).toBe(50);
    });

    it('returns events with correct fields', async () => {
      const res = await callWorker('/api/list?per_page=10', { env });
      const data = await res.json();
      const event = data.events[0];
      expect(event).toHaveProperty('id');
      expect(event).toHaveProperty('title');
      expect(event).toHaveProperty('date_start');
      expect(event).toHaveProperty('tags');
    });

    it('filters by search term', async () => {
      const res = await callWorker('/api/list?search=Festival', { env });
      const data = await res.json();
      expect(data.total).toBeGreaterThan(0);
      // All returned events should mention "Festival" somewhere
      for (const event of data.events) {
        const haystack = (event.title + ' ' + event.location + ' ' + event.organizer + ' ' + event.description).toLowerCase();
        expect(haystack).toContain('festival');
      }
    });

    it('filters by date_from', async () => {
      const res = await callWorker('/api/list?date_from=2026-06-01', { env });
      const data = await res.json();
      expect(data.total).toBeGreaterThan(0);
      for (const event of data.events) {
        expect(event.date_start >= '2026-06-01').toBe(true);
      }
    });

    it('filters by tag', async () => {
      const res = await callWorker('/api/list?tag=Musik', { env });
      const data = await res.json();
      expect(data.total).toBeGreaterThan(0);
      for (const event of data.events) {
        expect(event.tags).toContain('Musik');
      }
    });

    it('filters by organizer', async () => {
      const res = await callWorker('/api/list?organizer=Stadt+Stutensee', { env });
      const data = await res.json();
      expect(data.total).toBeGreaterThan(0);
    });

    it('handles long search strings (50+ chars) without crashing', async () => {
      const res = await callWorker('/api/list?search=' + 'a'.repeat(100), { env });
      expect(res.status).toBe(200);
    });

    it('handles the original buggy search string', async () => {
      const res = await callWorker(
        '/api/list?search=Hope+is+a+dangerous+thing+mit+der+Saxofonistin+Asy',
        { env }
      );
      expect(res.status).toBe(200);
    });

    it('handles special characters in search', async () => {
      const res = await callWorker('/api/list?search=' + encodeURIComponent('Test & Demo <Event>'), { env });
      expect(res.status).toBe(200);
    });

    it('paginates correctly', async () => {
      // Get total count first
      const all = await callWorker('/api/list?per_page=100', { env });
      const totalAll = (await all.json()).total;

      // Get first page with small per_page
      const page1 = await callWorker('/api/list?page=1&per_page=2', { env });
      const d1 = await page1.json();
      expect(d1.events.length).toBeLessThanOrEqual(2);
      expect(d1.total_pages).toBe(Math.ceil(totalAll / 2));
    });

    it('clamps per_page between 1 and 100', async () => {
      const res1 = await callWorker('/api/list?per_page=0', { env });
      expect(res1.status).toBe(200);
      const data1 = await res1.json();
      expect(data1.per_page).toBe(1);
      const res2 = await callWorker('/api/list?per_page=999', { env });
      expect(res2.status).toBe(200);
      const data2 = await res2.json();
      expect(data2.per_page).toBe(100);
    });

    it('returns CORS headers', async () => {
      const res = await callWorker('/api/list', { env });
      expect(res.headers.get('access-control-allow-origin')).toBe('*');
    });

    it('decodes HTML entities in titles and locations', async () => {
      const res = await callWorker('/api/list?search=' + encodeURIComponent('Test & Demo <Event>'), { env });
      const data = await res.json();
      for (const event of data.events) {
        expect(event.title).not.toContain('&amp;');
        expect(event.title).not.toContain('&lt;');
      }
    });
  });

  // ── /api/theme ─────────────────────────────────────────────────────

  describe('GET /api/theme', () => {
    it('returns sorted tag list', async () => {
      const res = await callWorker('/api/theme', { env });
      expect(res.status).toBe(200);
      const data = await res.json();
      expect(Array.isArray(data)).toBe(true);
      expect(data.length).toBeGreaterThan(0);
      // Should be sorted
      for (let i = 1; i < data.length; i++) {
        expect(data[i - 1] <= data[i]).toBe(true);
      }
    });
  });

  // ── /api/districts ─────────────────────────────────────────────────

  describe('GET /api/districts', () => {
    it('returns sorted district list', async () => {
      const res = await callWorker('/api/districts', { env });
      expect(res.status).toBe(200);
      const data = await res.json();
      expect(Array.isArray(data)).toBe(true);
      expect(data.length).toBeGreaterThan(0);
    });
  });

  // ── /api/organizer ─────────────────────────────────────────────────

  describe('GET /api/organizer', () => {
    it('returns organizer list', async () => {
      const res = await callWorker('/api/organizer', { env });
      expect(res.status).toBe(200);
      const data = await res.json();
      expect(Array.isArray(data)).toBe(true);
      expect(data.length).toBeGreaterThan(0);
    });
  });

  // ── /api/info ──────────────────────────────────────────────────────

  describe('GET /api/info', () => {
    it('returns stats with raw and curated counts', async () => {
      const res = await callWorker('/api/info', { env });
      expect(res.status).toBe(200);
      const data = await res.json();
      expect(data).toHaveProperty('raw');
      expect(data).toHaveProperty('curated');
      expect(typeof data.raw).toBe('number');
      expect(typeof data.curated).toBe('number');
      expect(data.raw).toBeGreaterThan(0);
      expect(data.curated).toBeGreaterThan(0);
    });
  });

  // ── /api/stats (request analytics) ──────────────────────────────

  describe('GET /api/stats', () => {
    it('returns 404 when REQUEST_DB is not configured', async () => {
      const res = await callWorker('/api/stats', { env });
      expect(res.status).toBe(404);
    });

    it('returns analytics data when REQUEST_DB is configured', async () => {
      const { createD1 } = await import('./d1-wrapper.js');
      const Database = (await import('better-sqlite3')).default;
      const analyticsDb = new Database(':memory:');
      const analyticsD1 = createD1(analyticsDb);

      // Create table and insert a sample log entry
      await analyticsD1.prepare(`
        CREATE TABLE request_log (
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
        )
      `).run();

      await analyticsD1.prepare(
        'INSERT INTO request_log (timestamp, path, method, status, response_size, latency_ms) VALUES (?, ?, ?, ?, ?, ?)'
      ).bind('2026-05-18T12:00:00Z', '/api/list', 'GET', 200, 1500, 42.5).run();

      const res = await callWorker('/api/stats', { env: { ...env, REQUEST_DB: analyticsD1 } });
      expect(res.status).toBe(200);
      const data = await res.json();
      expect(data).toHaveProperty('totals');
      expect(data).toHaveProperty('by_path');
      expect(data).toHaveProperty('recent');
      expect(data.totals.total).toBe(1);
      expect(data.recent.length).toBeGreaterThan(0);

      analyticsDb.close();
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
  });

  // ── Error Handling ─────────────────────────────────────────────────

  describe('Error handling', () => {
    it('returns 500 when DB is missing (graceful error handling)', async () => {
      const res = await callWorker('/api/list', { env: {} });
      expect(res.status).toBe(500);
    });
  });
});
