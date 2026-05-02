#!/usr/bin/env python3
"""Fetch OpenCode Go token usage from the workspace page."""
import re, json, sys, subprocess, os
from datetime import datetime, timedelta

COOKIE = "oc_locale=en; auth=REDACTED_OPENCODE_COOKIE"

def fetch_html():
    url = "https://opencode.ai/workspace/wrk_01KQ2E2BZJGDF8W0XG6T3NPQAC/go"
    result = subprocess.run(
        ["curl", "-s", "-b", COOKIE, url],
        capture_output=True, text=True, timeout=30
    )
    return result.stdout

def extract_usage(html):
    data = {}

    m = re.search(r'rollingUsage:\$R\[\d+\]=\{status:"([^"]+)",resetInSec:(\d+),usagePercent:(\d+)\}', html)
    if m:
        data['rolling'] = {
            'status': m.group(1),
            'reset_in_sec': int(m.group(2)),
            'usage_percent': int(m.group(3)),
            'reset_in': str(timedelta(seconds=int(m.group(2))))
        }

    m = re.search(r'weeklyUsage:\$R\[\d+\]=\{status:"([^"]+)",resetInSec:(\d+),usagePercent:(\d+)\}', html)
    if m:
        data['weekly'] = {
            'status': m.group(1),
            'reset_in_sec': int(m.group(2)),
            'usage_percent': int(m.group(3)),
            'reset_in': str(timedelta(seconds=int(m.group(2))))
        }

    m = re.search(r'monthlyUsage:\$R\[\d+\]=\{status:"([^"]+)",resetInSec:(\d+),usagePercent:(\d+)\}', html)
    if m:
        data['monthly'] = {
            'status': m.group(1),
            'reset_in_sec': int(m.group(2)),
            'usage_percent': int(m.group(3)),
            'reset_in': str(timedelta(seconds=int(m.group(2))))
        }

    m = re.search(r'balance:(\d+)', html)
    if m:
        data['balance'] = int(m.group(1)) / 100000000

    m = re.search(r'paymentMethodLast4:"(\d+)"', html)
    if m:
        data['card_last4'] = m.group(1)

    data['fetched_at'] = datetime.utcnow().isoformat()
    return data

def main():
    html = fetch_html()
    usage = extract_usage(html)
    print(json.dumps(usage, indent=2))
    return usage

if __name__ == "__main__":
    main()
