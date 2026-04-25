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
            normalized_title TEXT,
            date_start TEXT,
            date_end TEXT,
            time_raw TEXT,
            location TEXT,
            organizer TEXT,
            description TEXT,
            event_url TEXT,
            sources TEXT,
            dedup_round INTEGER,
            created_at TEXT DEFAULT (datetime('now')),
            updated_at TEXT DEFAULT (datetime('now'))
        );

        CREATE TABLE IF NOT EXISTS raw_to_curated (
            raw_id INTEGER NOT NULL,
            curated_id INTEGER NOT NULL,
            dedup_round INTEGER NOT NULL,
            PRIMARY KEY (raw_id, curated_id),
            FOREIGN KEY (raw_id) REFERENCES raw_events(id),
            FOREIGN KEY (curated_id) REFERENCES curated_events(id)
        );

        CREATE INDEX IF NOT EXISTS idx_curated_dates ON curated_events(date_start);
        CREATE INDEX IF NOT EXISTS idx_curated_title ON curated_events(normalized_title);
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

def export_raw_batches(batch_size=500):
    conn = get_conn()
    c = conn.cursor()
    rows = c.execute("SELECT id, source_url, title, date_start, date_end, time_raw, location, organizer, description, event_url FROM raw_events ORDER BY date_start, title").fetchall()
    conn.close()
    batches = []
    for i in range(0, len(rows), batch_size):
        batch = rows[i:i+batch_size]
        events = []
        for r in batch:
            events.append({
                "id": r[0],
                "source_url": r[1],
                "title": r[2],
                "date_start": r[3],
                "date_end": r[4],
                "time_raw": r[5],
                "location": r[6],
                "organizer": r[7],
                "description": r[8],
                "event_url": r[9],
            })
        batches.append(events)
    return batches

def insert_curated_batch(curated_events, dedup_round=1):
    conn = get_conn()
    c = conn.cursor()
    count = 0
    for ev in curated_events:
        raw_ids = ev.pop("raw_ids", [])
        c.execute("""
            INSERT INTO curated_events
                (title, normalized_title, date_start, date_end, time_raw, location, organizer, description, event_url, sources, dedup_round)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            ev.get("title"),
            ev.get("normalized_title"),
            ev.get("date_start"),
            ev.get("date_end"),
            ev.get("time_raw"),
            ev.get("location"),
            ev.get("organizer"),
            ev.get("description"),
            ev.get("event_url"),
            ev.get("sources"),
            dedup_round
        ))
        curated_id = c.lastrowid
        for rid in raw_ids:
            try:
                c.execute("INSERT OR IGNORE INTO raw_to_curated (raw_id, curated_id, dedup_round) VALUES (?, ?, ?)",
                          (rid, curated_id, dedup_round))
            except Exception:
                pass
        count += 1
    conn.commit()
    conn.close()
    return count

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
    elif len(sys.argv) > 1 and sys.argv[1] == "export-batches":
        import math
        batches = export_raw_batches()
        print(json.dumps({"total_batches": len(batches), "batch_size": 500, "total_events": sum(len(b) for b in batches)}))
        for i, batch in enumerate(batches):
            with open(f"/tmp/dedup_batch_{i}.json", "w") as f:
                json.dump({"batch_id": i, "events": batch}, f, ensure_ascii=False)
        print(f"Exported {len(batches)} batches to /tmp/dedup_batch_*.json")
    elif len(sys.argv) > 1 and sys.argv[1] == "load-curated":
        data = json.loads(sys.stdin.read())
        events = data.get("events", [])
        round_num = data.get("dedup_round", 1)
        n = insert_curated_batch(events, round_num)
        print(f"Loaded {n} curated events (round {round_num})")
    elif len(sys.argv) > 1 and sys.argv[1] == "stats":
        raw, curated, by_source = get_stats()
        print(f"Raw events: {raw}")
        print(f"Curated events: {curated}")
        for s, n in by_source:
            print(f"  {s}: {n}")
    else:
        print("Usage: python db.py [init|insert|export-batches|load-curated|dedup|stats]")
