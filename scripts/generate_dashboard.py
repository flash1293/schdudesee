#!/usr/bin/env python3
"""Generate an HTML dashboard from the Stutensee events database."""

import sqlite3
import html
from collections import Counter
from datetime import datetime

DB_PATH = "/shared/work/stutensee_events.db"
OUTPUT_PATH = "/skillet/dashboard.html"

def q(conn, sql, params=()):
    cur = conn.cursor()
    cur.execute(sql, params)
    return cur.fetchall()

def esc(s):
    if s is None:
        return ""
    return html.escape(str(s))

def build():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row

    total_raw = q(conn, "SELECT COUNT(*) FROM raw_events")[0][0]
    total_curated = q(conn, "SELECT COUNT(*) FROM curated_events")[0][0]

    raw_with_null_dates = q(conn, "SELECT COUNT(*) FROM raw_events WHERE date_start IS NULL")[0][0]
    curated_with_null_dates = q(conn, "SELECT COUNT(*) FROM curated_events WHERE date_start IS NULL")[0][0]

    # Events by source
    sources = q(conn, """
        SELECT
            CASE
                WHEN source_url LIKE '%stutenseekinderkalender%' THEN 'stutenseekinderkalender.de'
                WHEN source_url LIKE '%karlsdorf-neuthard%' THEN 'karlsdorf-neuthard.de'
                WHEN source_url LIKE '%stutensee.de%' THEN 'stutensee.de'
                WHEN source_url LIKE '%weingarten-baden%' THEN 'weingarten-baden.de'
                WHEN source_url LIKE '%egg-leo%' THEN 'egg-leo.de'
                WHEN source_url LIKE '%meinstutensee%' THEN 'meinstutensee.de'
                WHEN source_url LIKE '%buergerwerkstatt%' THEN 'buergerwerkstatt-stutensee.de'
                WHEN source_url LIKE '%clubs_batch%' THEN 'Vereinswebsites (Batch)'
                WHEN source_url LIKE '%kath-stutensee%' THEN 'kath-stutensee-weingarten.de'
                WHEN source_url LIKE '%hagsfeld%' THEN 'hagsfeld.de'
                WHEN source_url LIKE '%gewerbeverein%' THEN 'gewerbeverein-stutensee.org'
                WHEN source_url LIKE '%rintheim%' THEN 'rintheim-bv.de'
                ELSE 'other'
            END as source_group,
            COUNT(*) as cnt
        FROM raw_events
        GROUP BY source_group
        ORDER BY cnt DESC
    """)

    # Individual tags (split comma-separated)
    tag_rows = q(conn, "SELECT tags FROM curated_events WHERE tags IS NOT NULL AND tags != ''")
    tag_counter = Counter()
    for row in tag_rows:
        for t in row[0].split(","):
            t = t.strip()
            if t:
                tag_counter[t] += 1
    top_tags = tag_counter.most_common(30)

    # District-level tags (Blankenloch, Friedrichstal, Spöck, Staffort, Neuthard)
    districts = ["Blankenloch", "Friedrichstal", "Spöck", "Staffort", "Neuthard"]
    district_counts = {}
    for d in districts:
        district_counts[d] = sum(1 for row in tag_rows if d in row[0].split(","))

    # Events by source in curated (from tags or source tracking)
    # We'll use the 'sources' column in curated_events
    curated_sources_raw = q(conn, "SELECT sources FROM curated_events WHERE sources IS NOT NULL AND sources != ''")
    source_counter = Counter()
    for row in curated_sources_raw:
        src = row[0].strip()
        if src:
            source_counter[src] += 1
    top_curated_sources = source_counter.most_common(15)

    # Events by month
    monthly = q(conn, """
        SELECT substr(date_start, 1, 7) as m, COUNT(*)
        FROM curated_events
        WHERE date_start IS NOT NULL
        GROUP BY m ORDER BY m
    """)

    # Top organizers
    organizers = q(conn, """
        SELECT organizer, COUNT(*) as cnt
        FROM curated_events
        WHERE organizer IS NOT NULL AND organizer != ''
        GROUP BY organizer
        ORDER BY cnt DESC
        LIMIT 20
    """)

    # Recurring groups
    recurring_groups_count = q(conn, """
        SELECT COUNT(DISTINCT recurring_group_id)
        FROM curated_events
        WHERE recurring_group_id IS NOT NULL
    """)[0][0]
    recurring_events_count = q(conn, """
        SELECT COUNT(*)
        FROM curated_events
        WHERE recurring_group_id IS NOT NULL
    """)[0][0]

    # Unique organizers
    unique_orgs = q(conn, """
        SELECT COUNT(DISTINCT organizer)
        FROM curated_events
        WHERE organizer IS NOT NULL AND organizer != ''
    """)[0][0]

    # Date range
    date_min = q(conn, "SELECT MIN(date_start) FROM curated_events")[0][0]
    date_max = q(conn, "SELECT MAX(date_start) FROM curated_events")[0][0]

    conn.close()

    # Build HTML
    now = datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC")
    pct_recurring = round(recurring_events_count / total_curated * 100, 1) if total_curated else 0
    pct_raw_to_curated = round(total_curated / total_raw * 100, 1) if total_raw else 0

    source_rows = "".join(
        f"<tr><td>{esc(s)}</td><td>{c}</td><td>{'▰' * min(int(c / max(1, max(cc for _, cc in sources)) * 30), 30)}</td></tr>"
        for s, c in sources
    )

    curated_source_rows = "".join(
        f"<tr><td>{esc(s)}</td><td>{c}</td><td>{'▰' * min(int(c / max(1, max(cc for _, cc in top_curated_sources)) * 30), 30)}</td></tr>"
        for s, c in top_curated_sources
    )

    tag_rows_html = "".join(
        f"<tr><td>{esc(t)}</td><td>{c}</td><td>{'▰' * min(int(c / max(1, tag_counter.most_common(1)[0][1]) * 30), 30)}</td></tr>"
        for t, c in top_tags
    )

    district_rows = "".join(
        f"<tr><td>{d}</td><td>{district_counts[d]}</td><td>{'▰' * min(int(district_counts[d] / max(1, max(district_counts.values())) * 30), 30)}</td></tr>"
        for d in districts
    )

    monthly_rows = ""
    max_monthly = max((c for _, c in monthly), default=1)
    for m, c in monthly:
        bar = int(c / max_monthly * 30)
        monthly_rows += f"<tr><td>{esc(m)}</td><td>{c}</td><td>{'▰' * bar}</td></tr>\n"

    org_rows = "".join(
        f"<tr><td>{esc(o)}</td><td>{c}</td><td>{'▰' * min(int(c / max(1, max(cc for _, cc in organizers)) * 30), 30)}</td></tr>"
        for o, c in organizers
    )

    html_out = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>was-geht-stutensee.de — Data Dashboard</title>
<style>
  :root {{ --bg: #f5f7fa; --text: #1a1a2e; --card-bg: #fff; --card-shadow: rgba(0,0,0,0.08);
    --border: #e2e8f0; --row-border: #f1f5f9; --row-hover: #f8fafc;
    --subtitle: #666; --th-color: #64748b; --accent: #2563eb; --footer: #94a3b8; }}
  @media (prefers-color-scheme: dark) {{ :root {{ --bg: #0f172a; --text: #e2e8f0; --card-bg: #1e293b;
    --card-shadow: rgba(0,0,0,0.3); --border: #334155; --row-border: #334155; --row-hover: #1e293b;
    --subtitle: #94a3b8; --th-color: #94a3b8; --accent: #60a5fa; --footer: #64748b; }} }}
  .dark {{ --bg: #0f172a; --text: #e2e8f0; --card-bg: #1e293b; --card-shadow: rgba(0,0,0,0.3);
    --border: #334155; --row-border: #334155; --row-hover: #1e293b; --subtitle: #94a3b8;
    --th-color: #94a3b8; --accent: #60a5fa; --footer: #64748b; }}
  * {{ margin: 0; padding: 0; box-sizing: border-box; }}
  body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; background: var(--bg); color: var(--text); padding: 20px; }}
  h1 {{ font-size: 1.6rem; margin-bottom: 4px; }}
  .subtitle {{ color: var(--subtitle); font-size: 0.9rem; margin-bottom: 24px; }}
  .top-bar {{ display: flex; justify-content: space-between; align-items: flex-start; flex-wrap: wrap; gap: 8px; }}
  .toggle-wrap {{ display: flex; align-items: center; gap: 6px; font-size: 0.8rem; color: var(--subtitle); cursor: pointer; user-select: none; }}
  .toggle-wrap input {{ display: none; }}
  .toggle-slider {{ width: 36px; height: 20px; background: var(--border); border-radius: 10px; position: relative; transition: .2s; flex-shrink: 0; }}
  .toggle-slider::after {{ content: ''; width: 16px; height: 16px; background: var(--accent); border-radius: 50%; position: absolute; top: 2px; left: 2px; transition: .2s; }}
  .toggle-wrap input:checked + .toggle-slider {{ background: var(--accent); }}
  .toggle-wrap input:checked + .toggle-slider::after {{ left: 18px; background: var(--card-bg); }}
  .kpi-row {{ display: flex; gap: 12px; flex-wrap: wrap; margin-bottom: 24px; }}
  .kpi {{ background: var(--card-bg); border-radius: 10px; padding: 16px 20px; flex: 1; min-width: 140px; box-shadow: 0 1px 3px var(--card-shadow); }}
  .kpi .value {{ font-size: 1.8rem; font-weight: 700; color: var(--accent); }}
  .kpi .label {{ font-size: 0.8rem; color: var(--subtitle); margin-top: 4px; text-transform: uppercase; letter-spacing: 0.5px; }}
  .grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(380px, 1fr)); gap: 16px; margin-bottom: 24px; }}
  .card {{ background: var(--card-bg); border-radius: 10px; padding: 16px 20px; box-shadow: 0 1px 3px var(--card-shadow); }}
  .card h2 {{ font-size: 1.05rem; margin-bottom: 12px; color: var(--text); border-bottom: 2px solid var(--border); padding-bottom: 8px; }}
  table {{ width: 100%; border-collapse: collapse; font-size: 0.85rem; }}
  th {{ text-align: left; padding: 6px 8px; border-bottom: 1px solid var(--border); color: var(--th-color); font-weight: 600; font-size: 0.75rem; text-transform: uppercase; letter-spacing: 0.3px; }}
  td {{ padding: 6px 8px; border-bottom: 1px solid var(--row-border); }}
  tr:hover td {{ background: var(--row-hover); }}
  .bar {{ color: var(--accent); font-size: 0.7rem; letter-spacing: 1px; }}
  .footer {{ text-align: center; color: var(--footer); font-size: 0.75rem; padding: 20px 0 10px; }}
  .full {{ grid-column: 1 / -1; }}
  @media (max-width: 600px) {{ .grid {{ grid-template-columns: 1fr; }} }}
</style>
</head>
<body>
<div class="top-bar">
  <div>
    <h1>was-geht-stutensee.de — Data Dashboard</h1>
    <div class="subtitle">Generated {now} &middot; SQLite database at {esc(DB_PATH)}</div>
  </div>
  <label class="toggle-wrap">
    <span>Dark</span>
    <input type="checkbox" id="darkToggle">
    <span class="toggle-slider"></span>
  </label>
</div>
<script>
  (function() {{
    if (window.matchMedia('(prefers-color-scheme: dark)').matches) {{
      document.getElementById('darkToggle').checked = true;
      document.body.classList.add('dark');
    }}
    document.getElementById('darkToggle').addEventListener('change', function(e) {{
      document.body.classList.toggle('dark', e.target.checked);
    }});
  }})();
</script>

<div class="kpi-row">
  <div class="kpi"><div class="value">{total_raw:,}</div><div class="label">Raw Events</div></div>
  <div class="kpi"><div class="value">{total_curated:,}</div><div class="label">Curated Events</div></div>
  <div class="kpi"><div class="value">{pct_raw_to_curated}%</div><div class="label">Curated / Raw</div></div>
  <div class="kpi"><div class="value">{unique_orgs:,}</div><div class="label">Unique Organizers</div></div>
  <div class="kpi"><div class="value">{recurring_groups_count}</div><div class="label">Recurring Groups</div></div>
  <div class="kpi"><div class="value">{pct_recurring}%</div><div class="label">Events in Recurring Groups</div></div>
</div>

<div class="kpi-row">
  <div class="kpi"><div class="value">{esc(date_min or 'N/A')}</div><div class="label">Earliest Event</div></div>
  <div class="kpi"><div class="value">{esc(date_max or 'N/A')}</div><div class="label">Latest Event</div></div>
  <div class="kpi"><div class="value">{raw_with_null_dates:,}</div><div class="label">Raw Events Missing Dates</div></div>
  <div class="kpi"><div class="value">{curated_with_null_dates:,}</div><div class="label">Curated Events Missing Dates</div></div>
</div>

<div class="grid">
  <div class="card full">
    <h2>Events by Month ({len(monthly)} months)</h2>
    <div style="max-height: 300px; overflow-y: auto;">
    <table>
      <tr><th>Month</th><th>Count</th><th></th></tr>
      {monthly_rows}
    </table>
    </div>
  </div>

  <div class="card">
    <h2>Raw Events by Source</h2>
    <div style="max-height: 350px; overflow-y: auto;">
    <table>
      <tr><th>Source</th><th>Count</th><th></th></tr>
      {source_rows}
    </table>
    </div>
  </div>

  <div class="card">
    <h2>Curated Events by Source</h2>
    <div style="max-height: 350px; overflow-y: auto;">
    <table>
      <tr><th>Source</th><th>Count</th><th></th></tr>
      {curated_source_rows}
    </table>
    </div>
  </div>

  <div class="card">
    <h2>Top Tags (individual)</h2>
    <div style="max-height: 350px; overflow-y: auto;">
    <table>
      <tr><th>Tag</th><th>Count</th><th></th></tr>
      {tag_rows_html}
    </table>
    </div>
  </div>

  <div class="card">
    <h2>Events by District</h2>
    <div style="max-height: 250px; overflow-y: auto;">
    <table>
      <tr><th>District</th><th>Events</th><th></th></tr>
      {district_rows}
    </table>
    </div>
  </div>

  <div class="card">
    <h2>Top Organizers</h2>
    <div style="max-height: 400px; overflow-y: auto;">
    <table>
      <tr><th>Organizer</th><th>Events</th><th></th></tr>
      {org_rows}
    </table>
    </div>
  </div>
</div>

<div class="footer">
  Generated by <strong>Pinsel</strong> (Data Analytics bot) &middot; YEAP Platform
</div>
</body>
</html>"""

    with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
        f.write(html_out)

    print(f"Dashboard written to {OUTPUT_PATH}")
    print(f"  Raw events: {total_raw:,}")
    print(f"  Curated events: {total_curated:,}")
    print(f"  Unique organizers: {unique_orgs:,}")
    print(f"  Recurring groups: {recurring_groups_count}")
    print(f"  Date range: {date_min} to {date_max}")

if __name__ == "__main__":
    build()
