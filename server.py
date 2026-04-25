import json
import sqlite3
import html
from http.server import HTTPServer, SimpleHTTPRequestHandler
import urllib.parse
import os
from datetime import datetime

DB_PATH = "stutensee_events.db"

class Handler(SimpleHTTPRequestHandler):
    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path
        params = urllib.parse.parse_qs(parsed.query)

        if path == "/":
            self.serve_file("index.html")
        elif path == "/api/events":
            self.serve_events(params)
        elif path == "/api/sources":
            self.serve_sources()
        elif path == "/api/stats":
            self.serve_stats()
        elif path == "/api/tags":
            self.serve_tags()
        elif path.startswith("/api/recurring/"):
            group_id = path.split("/api/recurring/")[1]
            self.serve_recurring(group_id)
        else:
            super().do_GET()

    def serve_file(self, filename):
        try:
            with open(filename, "rb") as f:
                self.send_response(200)
                if filename.endswith(".html"):
                    self.send_header("Content-Type", "text/html; charset=utf-8")
                self.end_headers()
                self.wfile.write(f.read())
        except FileNotFoundError:
            self.send_error(404, "File not found")

    def serve_events(self, params):
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()

        page = int(params.get("page", [1])[0])
        per_page = int(params.get("per_page", [50])[0])
        search = params.get("search", [""])[0]
        source_filter = params.get("source", [""])[0]
        sort = "date_start"
        order = "asc"
        month = params.get("month", [""])[0]
        from_today = params.get("from_today", ["true"])[0]
        date_from = params.get("date_from", [""])[0]
        date_to = params.get("date_to", [""])[0]

        where = []
        args = []

        if from_today == "true":
            where.append("(date_start >= ? OR date_start = '')")
            args.append(datetime.now().strftime("%Y-%m-%d"))

        if date_from:
            where.append("(date_start >= ? OR date_start = '')")
            args.append(date_from)

        if date_to:
            where.append("(date_start <= ? OR date_start = '')")
            args.append(date_to)

        if search:
            where.append("(title LIKE ? OR location LIKE ? OR organizer LIKE ?)")
            args.extend([f"%{search}%"] * 3)

        if source_filter:
            where.append("sources LIKE ?")
            args.append(f"%{source_filter}%")

        tag_filter = params.get("tag", [""])[0]
        if tag_filter:
            where.append("tags LIKE ?")
            args.append(f"%{tag_filter}%")

        if month:
            where.append("date_start LIKE ?")
            args.append(f"{month}%")

        where_clause = " AND ".join(where) if where else "1=1"

        valid_sorts = {"date_start", "title", "location"}
        if sort not in valid_sorts:
            sort = "date_start"
        if order not in ("asc", "desc"):
            order = "asc"

        count = c.execute(f"SELECT COUNT(*) FROM curated_events WHERE {where_clause}", args).fetchone()[0]

        offset = (page - 1) * per_page
        rows = c.execute(
            f"SELECT id, title, date_start, date_end, time_raw, location, organizer, description, event_url, sources, tags, recurring_group_id FROM curated_events WHERE {where_clause} ORDER BY {sort} {order}, id LIMIT ? OFFSET ?",
            args + [per_page, offset]
        ).fetchall()

        conn.close()

        events = []
        for r in rows:
            events.append({
                "id": r[0],
                "title": r[1],
                "date_start": r[2],
                "date_end": r[3],
                "time_raw": r[4],
                "location": r[5],
                "organizer": r[6],
                "description": r[7][:300] + "..." if r[7] and len(r[7]) > 300 else (r[7] or ""),
                "event_url": html.unescape(r[8]) if r[8] else "",
                "sources": html.unescape(r[9]) if r[9] else "",
                "tags": r[10] or "",
                "recurring_group_id": r[11],
            })

        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(json.dumps({
            "events": events,
            "total": count,
            "page": page,
            "per_page": per_page,
            "total_pages": (count + per_page - 1) // per_page,
        }, ensure_ascii=False).encode())

    def serve_sources(self):
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        rows = c.execute("SELECT DISTINCT sources FROM curated_events WHERE sources != '' ORDER BY sources").fetchall()
        conn.close()
        sources = list(set(s.strip() for r in rows for s in r[0].split(",") if s.strip()))
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(json.dumps(sorted(sources), ensure_ascii=False).encode())

    def serve_stats(self):
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        raw = c.execute("SELECT COUNT(*) FROM raw_events").fetchone()[0]
        curated = c.execute("SELECT COUNT(*) FROM curated_events").fetchone()[0]
        by_source = c.execute("""SELECT source_url, COUNT(*) FROM raw_events GROUP BY source_url ORDER BY COUNT(*) DESC""").fetchall()
        conn.close()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(json.dumps({
            "raw": raw,
            "curated": curated,
            "by_source": [{"source": s, "count": n} for s, n in by_source]
        }, ensure_ascii=False).encode())

    def serve_tags(self):
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        rows = c.execute("SELECT DISTINCT tags FROM curated_events WHERE tags IS NOT NULL AND tags != ''").fetchall()
        conn.close()
        tags = set()
        for r in rows:
            for t in r[0].split(","):
                t = t.strip()
                if t:
                    tags.add(t)
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(json.dumps(sorted(tags), ensure_ascii=False).encode())

    def serve_recurring(self, group_id):
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        rows = c.execute(
            "SELECT id, title, date_start, date_end, time_raw, location, organizer, description, event_url, sources, tags, recurring_group_id FROM curated_events WHERE recurring_group_id = ? ORDER BY date_start",
            (group_id,)
        ).fetchall()
        conn.close()
        events = []
        for r in rows:
            events.append({
                "id": r[0],
                "title": r[1],
                "date_start": r[2],
                "date_end": r[3],
                "time_raw": r[4],
                "location": r[5],
                "organizer": r[6],
                "description": r[7][:300] + "..." if r[7] and len(r[7]) > 300 else (r[7] or ""),
                "event_url": html.unescape(r[8]) if r[8] else "",
                "sources": html.unescape(r[9]) if r[9] else "",
                "tags": r[10] or "",
                "recurring_group_id": r[11],
            })
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(json.dumps(events, ensure_ascii=False).encode())

    def log_message(self, format, *args):
        pass

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    server = HTTPServer(("", port), Handler)
    print(f"Server running at http://localhost:{port}")
    server.serve_forever()
