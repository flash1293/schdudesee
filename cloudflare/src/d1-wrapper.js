/**
 * D1-compatible wrapper around better-sqlite3.
 * Allows running Cloudflare Worker tests against a real SQLite database.
 *
 * D1: db.prepare(sql).bind(...args).first() | .all()
 * better-sqlite3: stmt.get(...params) | stmt.all(...params)
 *
 * This wrapper maps D1's chained API to better-sqlite3's per-execution params,
 * avoiding permanent bind() which would prevent reusing the statement.
 */
import Database from 'better-sqlite3';

export function createD1(dbOrMemory = ':memory:') {
  const db = typeof dbOrMemory === 'string' ? new Database(dbOrMemory) : dbOrMemory;

  return {
    prepare(sql) {
      let stmt;
      try {
        stmt = db.prepare(sql);
      } catch (err) {
        return createFailingStmt(err);
      }
      return createBoundStmt(stmt);
    },
    close() {
      db.close();
    },
  };
}

function createBoundStmt(stmt) {
  // The binder wraps params and returns execution methods.
  // Uses per-execution params (better-sqlite3 pattern) instead of
  // permanent .bind() (which would prevent reusing the statement).
  const binder = (...args) => ({
    first() {
      const row = args.length ? stmt.get(...args) : stmt.get();
      return row || null;
    },
    all() {
      const rows = args.length ? stmt.all(...args) : stmt.all();
      return { results: rows };
    },
    run() {
      return args.length ? stmt.run(...args) : stmt.run();
    },
  });

  return {
    // Direct calls: .first() / .all() with optional positional params
    first: (...args) => binder(...args).first(),
    all: (...args) => binder(...args).all(),
    run: (...args) => binder(...args).run(),
    bind: binder,
  };
}

function createFailingStmt(err) {
  const fail = () => { throw err; };
  return {
    first: fail,
    all: fail,
    run: fail,
    bind: () => ({ first: fail, all: fail, run: fail }),
  };
}
