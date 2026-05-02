#!/usr/bin/env python3
"""Fetch OpenCode Go token usage from the workspace page."""
import re, json, sys, subprocess, os
from datetime import datetime, timedelta

COOKIE = "oc_locale=en; auth=Fe26.2**90ea577c75a17d2ced6a2310e5b472c374e6c3028d91c8ef524461a09e1a03cc*bCsMFk853NiY_lsYCq225Q*-dxYqPT6fdn0ilLpsx4_UPXVnlo30hAjGI56Iqbt0Jwd7cbIukGJ7IU329m7z1Qx2KzzZTS_Lwh6FAjewpOmMSTpnMmUAA0k6fnyA42DmJFvttFxiACCGWS0BiYklU_eLSUAM5zLB7kXaEjRgSP-9pgBJRU5ihhD84IoJFpvkwZue4-HqmzlTbOn6FwGh-HPRelJANt2aPka2oCvpIBvIILYRMywZFBN0Xq4O1huRHfhyzBl79EyGhnFZZW3oi9lw_VVcohqRq0hsAcc3jvoI935wWrnQ3ouz5cyDorGFD6Wdgo3XRi9pfafUAbsBqsIT4n-IEmNqE92bkG17HY4HA*1808660586726*e53a8422d21f99a66c1a394e1d3ee445482ffe28b128e6eeec79d2380981a852*-BnQFfIISXbKVwzv691uO1zQ2exb5yfZrrWn9_LIPJg"

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
