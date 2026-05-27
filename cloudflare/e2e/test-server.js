/**
 * Test server for Playwright e2e tests.
 * Wraps the Cloudflare Worker fetch handler with a mock D1 environment
 * and intercepts LLM API calls to return canned responses.
 *
 * Usage: node e2e/test-server.js [port]
 */

import http from 'node:http';
import { resolve, dirname } from 'node:path';
import { fileURLToPath } from 'node:url';
import Database from 'better-sqlite3';
import { createD1 } from '../src/d1-wrapper.js';
import { createTestDb } from '../src/test-db.js';

const __dirname = dirname(fileURLToPath(import.meta.url));
const workerPath = resolve(__dirname, '../src/worker.js');
const worker = await import(workerPath);

const PORT = parseInt(process.argv[2] || '8787');

// ── Mock env ─────────────────────────────────────────────────────────

const db = createTestDb();
export const env = {
  STUTENSEE_DB: createD1(db),
  LLM_API_KEY: 'mock-key',
  LLM_BASE_URL: 'http://localhost:19999/mock-llm', // intercepted by mock fetch
};

// ── Mock LLM responses ────────────────────────────────────────────────

/** Canned responses for different chat queries. */
const MOCK_LLM_RESPONSES = {
  default: {
    choices: [{
      index: 0,
      message: {
        role: 'assistant',
        content: 'Das ist ein spannendes Event! Hier sind die Veranstaltungen, die ich gefunden habe:\n\n- **10 Jahre Red Horse Festival** am 16.05.2026 im Jugendzentrum GrauBau\n\nMöchtest du mehr Details zu einem Event erfahren?',
      },
    }],
    usage: { prompt_tokens: 100, completion_tokens: 50, total_tokens: 150 },
  },
};

function makeMockLLMResponse(messages) {
  // Simple logic: if the user is asking about "heute" or "morgen", return a relevant response
  const userMsg = messages.find(m => m.role === 'user')?.content?.toLowerCase() || '';
  if (userMsg.includes('heute')) {
    return {
      choices: [{
        index: 0,
        message: {
          role: 'assistant',
          content: 'Heute habe ich folgende Veranstaltungen gefunden: **10 Jahre Red Horse Festival** um 13:30 im Jugendzentrum GrauBau. Viel Spaß!',
        },
      }],
    };
  }
  return MOCK_LLM_RESPONSES.default;
}

// ── Intercept fetch for LLM calls ────────────────────────────────────

const originalFetch = globalThis.fetch;
globalThis.fetch = async (url, options) => {
  if (typeof url === 'string' && url.includes('/mock-llm/chat/completions')) {
    const body = JSON.parse(options.body);
    const mockResponse = makeMockLLMResponse(body.messages);
    return new Response(JSON.stringify(mockResponse), {
      status: 200,
      headers: { 'Content-Type': 'application/json' },
    });
  }
  return originalFetch(url, options);
};

// ── HTTP Server ──────────────────────────────────────────────────────

const server = http.createServer(async (req, res) => {
  try {
    // Collect request body
    const chunks = [];
    for await (const chunk of req) {
      chunks.push(chunk);
    }
    const body = Buffer.concat(chunks);

    // Build a standard Request object
    const url = new URL(req.url, `http://localhost:${PORT}`);
    const request = new Request(url, {
      method: req.method,
      headers: Object.entries(req.headers).reduce((acc, [k, v]) => {
        if (k !== 'host' && k !== 'connection') acc[k] = v;
        return acc;
      }, {}),
      body: req.method !== 'GET' && req.method !== 'HEAD' ? body : undefined,
    });

    // Call the worker's fetch handler
    const ctx = { waitUntil: (p) => p };
    const response = await worker.default.fetch(request, env, ctx);

    // Send response back
    res.writeHead(response.status, Object.fromEntries(response.headers));
    res.end(await response.text());
  } catch (err) {
    console.error('Test server error:', err);
    res.writeHead(500, { 'Content-Type': 'text/plain' });
    res.end(`Internal Server Error: ${err.message}`);
  }
});

server.listen(PORT, () => {
  console.log(`Test server running on http://localhost:${PORT}`);
});

// Graceful shutdown
process.on('SIGINT', () => {
  console.log('Shutting down test server...');
  server.close();
  if (db) db.close();
  process.exit(0);
});

process.on('SIGTERM', () => {
  server.close();
  if (db) db.close();
  process.exit(0);
});
