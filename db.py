import sqlite3
import json
import hashlib
from datetime import datetime

DB_PATH = "stutensee_events.db"

def get_conn():
    return sqlite3.connect(DB_PATH)

def init_db():
    conn = get_conn()
    c = conn.cursor()
    c.executescript("""
        CREATE TABLE IF NOT EXISTS raw_events (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            source_url TEXT NOT NULL,
            title TEXT,
            date_start TEXT,
            date_end TEXT,
            time_raw TEXT,
            location TEXT,
            organizer TEXT,
            description TEXT,
            event_url TEXT,
            raw_html_hash TEXT,
            scraped_at TEXT DEFAULT (datetime('now')),
            UNIQUE(source_url, event_url, date_start, title)
        );

        CREATE TABLE IF NOT EXISTS curated_events (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            date_start TEXT,
            date_end TEXT,
            time_raw TEXT,
            location TEXT,
            organizer TEXT,
            description TEXT,
            event_url TEXT,
            sources TEXT,
            created_at TEXT DEFAULT (datetime('now')),
            updated_at TEXT DEFAULT (datetime('now'))
        );

        CREATE INDEX IF NOT EXISTS idx_curated_dates ON curated_events(date_start);
        CREATE INDEX IF NOT EXISTS idx_curated_title ON curated_events(title);
    """)
    conn.commit()
    conn.close()

def insert_raw_events(events, source_url):
    conn = get_conn()
    c = conn.cursor()
    count = 0
    for ev in events:
        h = hashlib.sha256(json.dumps(ev, sort_keys=True).encode()).hexdigest()
        try:
            c.execute("""
                INSERT OR IGNORE INTO raw_events
                    (source_url, title, date_start, date_end, time_raw, location, organizer, description, event_url, raw_html_hash)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                source_url,
                ev.get("title"),
                ev.get("date_start"),
                ev.get("date_end"),
                ev.get("time_raw"),
                ev.get("location"),
                ev.get("organizer"),
                ev.get("description"),
                ev.get("event_url"),
                h
            ))
            if c.rowcount > 0:
                count += 1
        except sqlite3.IntegrityError:
            pass
    conn.commit()
    conn.close()
    return count

def dedup_into_curated():
    conn = get_conn()
    c = conn.cursor()

    c.execute("DELETE FROM curated_events")

    c.execute("""
        INSERT INTO curated_events (title, date_start, date_end, time_raw, location, organizer, description, event_url, sources)
        SELECT
            title,
            date_start,
            date_end,
            time_raw,
            location,
            organizer,
            description,
            event_url,
            GROUP_CONCAT(DISTINCT source_url)
        FROM raw_events
        WHERE title IS NOT NULL AND title != ''
        GROUP BY LOWER(TRIM(title)), COALESCE(date_start, ''), COALESCE(location, '')
        ORDER BY date_start ASC
    """)

    conn.commit()
    count = c.execute("SELECT COUNT(*) FROM curated_events").fetchone()[0]
    conn.close()
    return count

def get_stats():
    conn = get_conn()
    c = conn.cursor()
    raw_count = c.execute("SELECT COUNT(*) FROM raw_events").fetchone()[0]
    curated_count = c.execute("SELECT COUNT(*) FROM curated_events").fetchone()[0]
    by_source = c.execute("""
        SELECT source_url, COUNT(*) FROM raw_events GROUP BY source_url ORDER BY COUNT(*) DESC
    """).fetchall()
    conn.close()
    return raw_count, curated_count, by_source

if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1 and sys.argv[1] == "init":
        init_db()
        print("DB initialized")
    elif len(sys.argv) > 1 and sys.argv[1] == "dedup":
        count = dedup_into_curated()
        raw, curated, by_source = get_stats()
        print(f"Raw: {raw}, Curated: {curated}")
        for s, n in by_source:
            print(f"  {s}: {n}")
    elif len(sys.argv) > 1 and sys.argv[1] == "insert":
        data = json.loads(sys.stdin.read())
        source_url = data.get("source_url", "unknown")
        events = data.get("events", [])
        n = insert_raw_events(events, source_url)
        print(f"Inserted {n} raw events from {source_url}")
    elif len(sys.argv) > 1 and sys.argv[1] == "stats":
        raw, curated, by_source = get_stats()
        print(f"Raw events: {raw}")
        print(f"Curated events: {curated}")
        for s, n in by_source:
            print(f"  {s}: {n}")
    else:
        print("Usage: python db.py [init|insert|dedup|stats]")
