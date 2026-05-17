#!/usr/bin/env python3
"""
Build the final cloudflare/src/worker.js from source parts.

Source of truth: cloudflare/src/_worker.js (hand-written logic, no base64 blobs)
Generated: cloudflare/src/worker.js (logic + inlined HTML + favicon)

Usage: cd cloudflare && python3 build.py
"""

import re, base64, os

with open("../index.html") as f:
    html = f.read()

# Minify slightly: remove extra whitespace
html = re.sub(r'>\s+<', '><', html)
html = re.sub(r'\s{2,}', ' ', html)

# Encode as base64 to avoid any JS string escaping issues
encoded = base64.b64encode(html.encode("utf-8")).decode("ascii")
inlined = f'const indexHtml = new TextDecoder().decode(Uint8Array.from(atob("{encoded}"), c=>c.charCodeAt(0)));\n'

# Also inline the favicon
favicon_path = os.path.join(os.path.dirname(__file__), "favicon.png")
if os.path.exists(favicon_path):
    with open(favicon_path, "rb") as f:
        favicon_b64 = base64.b64encode(f.read()).decode("ascii")
    favicon_line = f'const faviconB64 = "{favicon_b64}";\n'
else:
    favicon_line = "const faviconB64 = null;\n"

# Read the source logic (hand-written, no base64 blobs)
with open("src/_worker.js") as f:
    worker_src = f.read()

# Build the final worker: generated headers + hand-written logic
worker = inlined + favicon_line + worker_src

with open("src/worker.js", "w") as f:
    f.write(worker)

print("Built cloudflare/src/worker.js from src/_worker.js + index.html + favicon")
