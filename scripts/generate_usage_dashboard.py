#!/usr/bin/env python3
"""Generate an HTML dashboard from OpenCode Go token usage data."""

import json
import sys
import os
import html as html_mod
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from fetch_token_usage import fetch_html, extract_usage

OUTPUT_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "usage_dashboard.html")

def esc(s):
    if s is None:
        return ""
    return html_mod.escape(str(s))

def build():
    html_content = fetch_html()
    usage = extract_usage(html_content)

    now = datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC")

    rolling = usage.get("rolling", {})
    weekly = usage.get("weekly", {})
    monthly = usage.get("monthly", {})
    balance = usage.get("balance", 0)
    card_last4 = usage.get("card_last4", "")

    monthly_pct = monthly.get("usage_percent", 0)
    alert = monthly_pct >= 80

    def usage_card(label, data, alert_on=False):
        pct = data.get("usage_percent", 0)
        status = data.get("status", "unknown")
        reset = data.get("reset_in", "N/A")
        is_alert = alert_on and pct >= 80
        bar_color = "#dc2626" if is_alert else "#2563eb"
        bg_color = "#fef2f2" if is_alert else "var(--card-bg)"
        border = "2px solid #dc2626" if is_alert else "none"
        badge = '<span class="alert-badge">⚠ ALERT</span>' if is_alert else ""
        return f"""
    <div class="card" style="background:{bg_color};border:{border}">
      <h2>{esc(label)} {badge}</h2>
      <div class="big-pct">{pct}%</div>
      <div class="bar-track"><div class="bar-fill" style="width:{min(pct,100)}%;background:{bar_color}"></div></div>
      <table>
        <tr><td class="label-col">Status</td><td>{esc(status)}</td></tr>
        <tr><td class="label-col">Used</td><td>{pct}%</td></tr>
        <tr><td class="label-col">Resets in</td><td>{esc(reset)}</td></tr>
      </table>
    </div>"""

    html_out = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Token Usage Dashboard</title>
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
  .grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(300px, 1fr)); gap: 16px; margin-bottom: 20px; }}
  .card {{ background: var(--card-bg); border-radius: 10px; padding: 16px 20px; box-shadow: 0 1px 3px var(--card-shadow); }}
  .card h2 {{ font-size: 1rem; margin-bottom: 8px; color: var(--text); border-bottom: 2px solid var(--border); padding-bottom: 8px; display: flex; justify-content: space-between; align-items: center; }}
  .alert-badge {{ font-size: 0.65rem; color: #fff; background: #dc2626; padding: 2px 8px; border-radius: 4px; font-weight: 700; letter-spacing: 0.3px; }}
  .big-pct {{ font-size: 2.5rem; font-weight: 700; padding: 8px 0 4px; }}
  .bar-track {{ height: 12px; background: var(--border); border-radius: 6px; overflow: hidden; margin-bottom: 12px; }}
  .bar-fill {{ height: 100%; border-radius: 6px; transition: width .5s ease; min-width: 2px; }}
  table {{ width: 100%; border-collapse: collapse; font-size: 0.82rem; }}
  td {{ padding: 5px 0; border-bottom: 1px solid var(--border); }}
  .label-col {{ color: var(--subtitle); width: 40%; }}
  .kpi-row {{ display: flex; gap: 12px; flex-wrap: wrap; margin-bottom: 20px; }}
  .kpi {{ background: var(--card-bg); border-radius: 10px; padding: 14px 18px; flex: 1; min-width: 140px; box-shadow: 0 1px 3px var(--card-shadow); }}
  .kpi .value {{ font-size: 1.4rem; font-weight: 700; color: var(--accent); }}
  .kpi .label {{ font-size: 0.75rem; color: var(--subtitle); margin-top: 2px; text-transform: uppercase; letter-spacing: 0.4px; }}
  .alert-banner {{ background: var(--alert-bg); border: 1px solid var(--alert-border); border-radius: 8px; padding: 12px 16px; margin-bottom: 16px; color: var(--alert-text); font-weight: 600; font-size: 0.9rem; text-align: center; }}
  .footer {{ text-align: center; color: var(--footer); font-size: 0.75rem; padding: 20px 0 10px; }}
  @media (max-width: 600px) {{ .grid {{ grid-template-columns: 1fr; }} }}
</style>
</head>
<body>
<div class="top-bar">
  <div>
    <h1>Token Usage Dashboard</h1>
    <div class="subtitle">Generated {esc(now)}</div>
  </div>
  <label class="toggle-wrap">
    <span>Dark</span>
    <input type="checkbox" id="darkToggle">
    <span class="toggle-slider"></span>
  </label>
</div>

{"".join('<div class="alert-banner">⚠ Monthly usage at ' + str(monthly_pct) + '% — exceeds 80% threshold!</div>' if alert else "")}

<div class="kpi-row">
  <div class="kpi"><div class="value">${balance:.2f}</div><div class="label">Account Balance</div></div>
  <div class="kpi"><div class="value">{esc(card_last4 or "---")}</div><div class="label">Card (last 4)</div></div>
</div>

<div class="grid">
  {usage_card("Rolling Usage", rolling)}
  {usage_card("Weekly Usage", weekly)}
  {usage_card("Monthly Usage", monthly, alert_on=True)}
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

    print(f"Usage dashboard written to {OUTPUT_PATH}")
    print(f"  Rolling: {rolling.get('usage_percent', '?')}% (resets in {rolling.get('reset_in', '?')})")
    print(f"  Weekly:  {weekly.get('usage_percent', '?')}% (resets in {weekly.get('reset_in', '?')})")
    print(f"  Monthly: {monthly.get('usage_percent', '?')}% (resets in {monthly.get('reset_in', '?')})")
    print(f"  Balance: ${balance:.2f}")

if __name__ == "__main__":
    build()
