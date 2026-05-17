/**
 * D1-compatible wrapper around better-sqlite3.
 * Allows running Cloudflare Worker tests against a real SQLite database.
 *
 * The D1 API: db.prepare(sql).bind(...args).first() | .all()
 * This wrapper maps that to better-sqlite3's prepared statements.
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
        // For invalid SQL, return a prepared statement that will throw on run
        return createFailingStmt(err);
      }

      return createBoundStmt(stmt);
    },
    // Allow closing the underlying DB
    close() {
      db.close();
    },
  };
}

function createBoundStmt(stmt) {
  const binder = (...args) => {
    if (args.length === 0) {
      return createExecStmt(stmt);
    }
    return createExecStmt(stmt.bind(...args));
  };

  return {
    // Direct call: .first() or .all() (no bind)
    first: (...args) => {
      if (args.length > 0) {
        // If called with arguments, treat as bind+first
        return createExecStmt(stmt.bind(...args)).first();
      }
      return createExecStmt(stmt).first();
    },
    all: (...args) => {
      if (args.length > 0) {
        return createExecStmt(stmt.bind(...args)).all();
      }
      return createExecStmt(stmt).all();
    },
    bind: binder,
  };
}

function createExecStmt(stmt) {
  return {
    first() {
      const row = stmt.get();
      return row || null;
    },
    all() {
      const rows = stmt.all();
      return { results: rows };
    },
    run() {
      return stmt.run();
    },
  };
}

function createFailingStmt(err) {
  const fail = () => { throw err; };
  return {
    first: fail,
    all: fail,
    bind: () => ({
      first: fail,
      all: fail,
      run: fail,
    }),
  };
}
