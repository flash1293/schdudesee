#!/usr/bin/env python3
"""Generate an HTML dashboard from Cloudflare Workers analytics."""

import json
import os
import html as html_mod
import urllib.request
from datetime import datetime, timezone

# Credentials from env vars (set via /shared/config/cloudflare.env)
ACCOUNT_ID = os.environ.get("CF_ACCOUNT_ID", "REDACTED_CF_ACCOUNT_ID")
API_TOKEN = os.environ.get("CF_API_TOKEN", "REDACTED_CF_API_TOKEN")
WORKER_PROD = "was-geht-stutensee"
WORKER_STAG = "was-geht-stutensee-staging"
OUTPUT_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "cf_analytics.html")

GRAPHQL_URL = "https://api.cloudflare.com/client/v4/graphql"

def esc(s):
    if s is None:
        return ""
    return html_mod.escape(str(s))

def run_graphql(query):
    payload = json.dumps({"query": query}).encode()
    req = urllib.request.Request(
        GRAPHQL_URL,
        data=payload,
        headers={
            "Authorization": "Bearer " + API_TOKEN,
            "Content-Type": "application/json"
        }
    )
    resp = urllib.request.urlopen(req, timeout=30)
    return json.loads(resp.read())

def build():
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    week_ago_dt = datetime.now(timezone.utc)
    week_ago = week_ago_dt.strftime("%Y-%m-%d")
    month_ago_dt = datetime.now(timezone.utc).timestamp() - 30*86400
    month_ago = datetime.fromtimestamp(month_ago_dt, tz=timezone.utc).strftime("%Y-%m-%d")

    alerts = []
    anomalies = []

    # Prod daily summary
    query_prod_daily = '''
    { viewer { accounts(filter: {accountTag: "''' + ACCOUNT_ID + '''"}) {
      prod: workersInvocationsAdaptive(limit: 60, filter: {datetime_geq: "''' + week_ago + '''T00:00:00Z", scriptName: "''' + WORKER_PROD + '''"}) {
        sum { requests errors subrequests }
        dimensions { date }
      }
      stag: workersInvocationsAdaptive(limit: 60, filter: {datetime_geq: "''' + week_ago + '''T00:00:00Z", scriptName: "''' + WORKER_STAG + '''"}) {
        sum { requests errors subrequests }
        dimensions { date }
      }
      prodHourly: workersInvocationsAdaptive(limit: 48, filter: {datetime_geq: "''' + today + '''T00:00:00Z", scriptName: "''' + WORKER_PROD + '''"}) {
        sum { requests errors }
        dimensions { datetimeHour }
      }
      stagHourly: workersInvocationsAdaptive(limit: 48, filter: {datetime_geq: "''' + today + '''T00:00:00Z", scriptName: "''' + WORKER_STAG + '''"}) {
        sum { requests errors }
        dimensions { datetimeHour }
      }
      prodTotal: workersInvocationsAdaptive(limit: 1, filter: {datetime_geq: "''' + month_ago + '''T00:00:00Z", scriptName: "''' + WORKER_PROD + '''"}) {
        sum { requests errors subrequests }
      }
      stagTotal: workersInvocationsAdaptive(limit: 1, filter: {datetime_geq: "''' + month_ago + '''T00:00:00Z", scriptName: "''' + WORKER_STAG + '''"}) {
        sum { requests errors subrequests }
      }
    }}}
    '''

    data = run_graphql(query_prod_daily)
    accounts = data.get("data", {}).get("viewer", {}).get("accounts", [{}])[0]

    prod_daily = accounts.get("prod", [])
    stag_daily = accounts.get("stag", [])
    prod_hourly = accounts.get("prodHourly", [])
    stag_hourly = accounts.get("stagHourly", [])
    prod_total_raw = accounts.get("prodTotal", [{}])
    stag_total_raw = accounts.get("stagTotal", [{}])

    prod_total = prod_total_raw[0].get("sum", {}) if prod_total_raw else {}
    stag_total = stag_total_raw[0].get("sum", {}) if stag_total_raw else {}

    prod_total_req = prod_total.get("requests", 0)
    prod_total_err = prod_total.get("errors", 0)
    stag_total_req = stag_total.get("requests", 0)
    stag_total_err = stag_total.get("errors", 0)

    # Aggregate today's prod requests
    today_prod_req = sum(h.get("sum", {}).get("requests", 0) for h in prod_hourly)
    today_stag_req = sum(h.get("sum", {}).get("requests", 0) for h in stag_hourly)
    today_prod_err = sum(h.get("sum", {}).get("errors", 0) for h in prod_hourly)
    today_stag_err = sum(h.get("sum", {}).get("errors", 0) for h in stag_hourly)

    # Check for anomalies: >100 errors in a day or error rate >5%
    for entry in prod_daily:
        s = entry.get("sum", {})
        d = entry.get("dimensions", {}).get("date", "")
        reqs = s.get("requests", 0)
        errs = s.get("errors", 0)
        if reqs > 0 and errs / reqs > 0.05:
            anomalies.append(f"High error rate on {d}: {errs}/{reqs} ({round(errs/reqs*100,1)}%)")

    if prod_total_req > 0 and prod_total_err / prod_total_req > 0.05:
        alerts.append(f"⚠ Production error rate: {prod_total_err}/{prod_total_req} ({round(prod_total_err/prod_total_req*100,1)}%)")

    if today_prod_err > 100:
        alerts.append(f"⚠ {today_prod_err} production errors today — investigate")

    # Build HTML
    prod_req_7d = sum(e.get("sum", {}).get("requests", 0) for e in prod_daily)
    stag_req_7d = sum(e.get("sum", {}).get("requests", 0) for e in stag_daily)

    max_prod_daily = max((e.get("sum", {}).get("requests", 0) for e in prod_daily), default=1)
    max_stag_daily = max((e.get("sum", {}).get("requests", 0) for e in stag_daily), default=1)

    prod_bar_rows = ""
    for e in sorted(prod_daily, key=lambda x: x.get("dimensions", {}).get("date", "")):
        d = e.get("dimensions", {}).get("date", "")
        s = e.get("sum", {})
        r = s.get("requests", 0)
        er = s.get("errors", 0)
        bar = int(r / max_prod_daily * 30)
        err_str = f" ⚠ {er} err" if er > 0 else ""
        prod_bar_rows += f"<tr><td>{esc(d)}</td><td>{r}</td><td>{'▰' * bar}</td><td>{er}{err_str}</td></tr>\n"

    stag_bar_rows = ""
    for e in sorted(stag_daily, key=lambda x: x.get("dimensions", {}).get("date", "")):
        d = e.get("dimensions", {}).get("date", "")
        s = e.get("sum", {})
        r = s.get("requests", 0)
        er = s.get("errors", 0)
        bar = int(r / max_stag_daily * 30)
        stag_bar_rows += f"<tr><td>{esc(d)}</td><td>{r}</td><td>{'▰' * bar}</td><td>{er}</td></tr>\n"

    # Hourly for today
    max_hourly = max((h.get("sum", {}).get("requests", 0) for h in prod_hourly), default=1)
    hourly_rows = ""
    for h in sorted(prod_hourly, key=lambda x: x.get("dimensions", {}).get("datetimeHour", "")):
        dt = h.get("dimensions", {}).get("datetimeHour", "")
        r = h.get("sum", {}).get("requests", 0)
        e = h.get("sum", {}).get("errors", 0)
        bar = int(r / max_hourly * 30)
        # Show just the hour part
        hour = dt[11:16] if len(dt) >= 16 else dt
        hourly_rows += f"<tr><td>{esc(hour)}</td><td>{r}</td><td>{'▰' * bar}</td><td>{e}</td></tr>\n"

    alarm_banners = "".join(f'<div class="alert-banner">⚠ {esc(a)}</div>' for a in alerts) if alerts else ""
    anomaly_list = "".join(f"<li>{esc(a)}</li>" for a in anomalies) if anomalies else "<li>None</li>"
    total_errors = prod_total_err + stag_total_err

    html_out = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Cloudflare Analytics Dashboard</title>
<style>
  :root {{ --bg: #f5f7fa; --text: #1a1a2e; --card-bg: #fff; --card-shadow: rgba(0,0,0,0.08);
    --border: #e2e8f0; --subtitle: #666; --accent: #2563eb; --footer: #94a3b8;
    --alert-bg: #fef2f2; --alert-border: #dc2626; --alert-text: #991b1b; }}
  @media (prefers-color-scheme: dark) {{ :root {{ --bg: #0f172a; --text: #e2e8f0; --card-bg: #1e293b;
    --card-shadow: rgba(0,0,0,0.3); --border: #334155; --subtitle: #94a3b8; --accent: #60a5fa;
    --footer: #64748b; --alert-bg: #451a1a; --alert-border: #dc2626; --alert-text: #fca5a5; }} }}
  .dark {{ --bg: #0f172a; --text: #e2e8f0; --card-bg: #1e293b; --card-shadow: rgba(0,0,0,0.3);
    --border: #334155; --subtitle: #94a3b8; --accent: #60a5fa; --footer: #64748b;
    --alert-bg: #451a1a; --alert-border: #dc2626; --alert-text: #fca5a5; }}
  * {{ margin: 0; padding: 0; box-sizing: border-box; }}
  body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
    background: var(--bg); color: var(--text); padding: 20px; }}
  h1 {{ font-size: 1.5rem; }}
  .subtitle {{ color: var(--subtitle); font-size: 0.85rem; margin: 4px 0 20px; }}
  .top-bar {{ display: flex; justify-content: space-between; align-items: flex-start; flex-wrap: wrap; gap: 8px; }}
  .toggle-wrap {{ display: flex; align-items: center; gap: 6px; font-size: 0.8rem; color: var(--subtitle); cursor: pointer; user-select: none; }}
  .toggle-wrap input {{ display: none; }}
  .toggle-slider {{ width: 36px; height: 20px; background: var(--border); border-radius: 10px; position: relative; transition: .2s; flex-shrink: 0; }}
  .toggle-slider::after {{ content: ''; width: 16px; height: 16px; background: var(--accent); border-radius: 50%; position: absolute; top: 2px; left: 2px; transition: .2s; }}
  .toggle-wrap input:checked + .toggle-slider {{ background: var(--accent); }}
  .toggle-wrap input:checked + .toggle-slider::after {{ left: 18px; background: var(--card-bg); }}
  .alert-banner {{ background: var(--alert-bg); border: 1px solid var(--alert-border); border-radius: 8px; padding: 12px 16px; margin-bottom: 16px; color: var(--alert-text); font-weight: 600; font-size: 0.9rem; text-align: center; }}
  .kpi-row {{ display: flex; gap: 12px; flex-wrap: wrap; margin-bottom: 20px; }}
  .kpi {{ background: var(--card-bg); border-radius: 10px; padding: 14px 18px; flex: 1; min-width: 140px; box-shadow: 0 1px 3px var(--card-shadow); }}
  .kpi .value {{ font-size: 1.4rem; font-weight: 700; color: var(--accent); }}
  .kpi .label {{ font-size: 0.75rem; color: var(--subtitle); margin-top: 2px; text-transform: uppercase; letter-spacing: 0.4px; }}
  .grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(380px, 1fr)); gap: 16px; margin-bottom: 20px; }}
  .card {{ background: var(--card-bg); border-radius: 10px; padding: 16px 20px; box-shadow: 0 1px 3px var(--card-shadow); }}
  .card h2 {{ font-size: 1rem; margin-bottom: 8px; color: var(--text); border-bottom: 2px solid var(--border); padding-bottom: 8px; }}
  table {{ width: 100%; border-collapse: collapse; font-size: 0.82rem; }}
  th {{ text-align: left; padding: 5px 6px; border-bottom: 1px solid var(--border); color: var(--subtitle); font-weight: 600; font-size: 0.72rem; text-transform: uppercase; letter-spacing: 0.3px; }}
  td {{ padding: 5px 6px; border-bottom: 1px solid var(--border); }}
  .full {{ grid-column: 1 / -1; }}
  .footer {{ text-align: center; color: var(--footer); font-size: 0.75rem; padding: 20px 0 10px; }}
  .anomaly-box {{ background: var(--card-bg); border-radius: 8px; padding: 12px 16px; margin-bottom: 16px; border-left: 4px solid var(--accent); }}
  .anomaly-box h3 {{ font-size: 0.9rem; margin-bottom: 6px; }}
  .anomaly-box ul {{ margin-left: 18px; font-size: 0.82rem; }}
  .anomaly-box li {{ margin-bottom: 3px; }}
  @media (max-width: 600px) {{ .grid {{ grid-template-columns: 1fr; }} }}
</style>
</head>
<body>
<div class="top-bar">
  <div>
    <h1>Cloudflare Analytics Dashboard</h1>
    <div class="subtitle">Generated {esc(now)} &middot; Workers: {esc(WORKER_PROD)} / {esc(WORKER_STAG)}</div>
  </div>
  <label class="toggle-wrap">
    <span>Dark</span>
    <input type="checkbox" id="darkToggle">
    <span class="toggle-slider"></span>
  </label>
</div>

{alarm_banners}

<div class="anomaly-box">
  <h3>Anomaly Detection</h3>
  <ul>{anomaly_list}</ul>
</div>

<div class="kpi-row">
  <div class="kpi"><div class="value">{prod_total_req:,}</div><div class="label">Prod Total Requests</div></div>
  <div class="kpi"><div class="value">{total_errors}</div><div class="label">Total Errors</div></div>
  <div class="kpi"><div class="value">{prod_total_err}/{prod_total_req} ({round(prod_total_err/prod_total_req*100,2) if prod_total_req else 0}%)</div><div class="label">Prod Error Rate</div></div>
  <div class="kpi"><div class="value">{prod_req_7d:,}</div><div class="label">Prod Requests (7d)</div></div>
  <div class="kpi"><div class="value">{today_prod_req}</div><div class="label">Prod Requests Today</div></div>
  <div class="kpi"><div class="value">{stag_total_req:,}</div><div class="label">Staging Total Req</div></div>
</div>

<div class="grid">
  <div class="card full">
    <h2>Production — Daily Requests (Last 7 Days)</h2>
    <div style="max-height: 280px; overflow-y: auto;">
    <table><tr><th>Date</th><th>Requests</th><th></th><th>Errors</th></tr>
    {prod_bar_rows}
    </table>
    </div>
  </div>

  <div class="card">
    <h2>Staging — Daily Requests</h2>
    <div style="max-height: 280px; overflow-y: auto;">
    <table><tr><th>Date</th><th>Requests</th><th></th><th>Errors</th></tr>
    {stag_bar_rows}
    </table>
    </div>
  </div>

  <div class="card">
    <h2>Production — Hourly (Today)</h2>
    <div style="max-height: 350px; overflow-y: auto;">
    <table><tr><th>Hour</th><th>Requests</th><th></th><th>Errors</th></tr>
    {hourly_rows}
    </table>
    </div>
  </div>

  <div class="card">
    <h2>Worker Info</h2>
    <table>
      <tr><td>Worker (Prod)</td><td>{esc(WORKER_PROD)}</td></tr>
      <tr><td>Worker (Staging)</td><td>{esc(WORKER_STAG)}</td></tr>
      <tr><td>Account ID</td><td style="font-family: monospace; font-size: 0.75rem;">{esc(ACCOUNT_ID[:12])}...</td></tr>
      <tr><td>Data Source</td><td>Cloudflare GraphQL API</td></tr>
      <tr><td>Refresh</td><td>Hourly</td></tr>
    </table>
  </div>
</div>

<div class="footer">
  Generated by <strong>Pinsel</strong> (Data Analytics bot) &middot; YEAP Platform
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
</body>
</html>"""

    with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
        f.write(html_out)

    print(f"CF Analytics dashboard written to {OUTPUT_PATH}")
    print(f"  Prod requests: {prod_total_req:,} | Errors: {prod_total_err}")
    print(f"  Staging requests: {stag_total_req:,} | Errors: {stag_total_err}")
    print(f"  Today prod: {today_prod_req} req, {today_prod_err} err")
    print(f"  Anomalies: {len(anomalies)}")
    print(f"  Alerts: {len(alerts)}")

    if alerts:
        print(f"  ⚠ ALERTS:")
        for a in alerts:
            print(f"    {a}")

if __name__ == "__main__":
    build()
