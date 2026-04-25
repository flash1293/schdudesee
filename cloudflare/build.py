#!/usr/bin/env python3
"""Build cloudflare/src/worker.js with inlined index.html."""

import json, re

with open("../index.html") as f:
    html = f.read()

# Minify slightly: remove extra whitespace
html = re.sub(r'>\s+<', '><', html)
html = re.sub(r'\s{2,}', ' ', html)

with open("src/worker.js") as f:
    worker = f.read()

# Replace the import line with the inlined HTML
inlined = f"const indexHtml = {json.dumps(html, ensure_ascii=False)};\n"
worker = re.sub(r'import indexHtml from.*\n', inlined, worker)

with open("src/worker.js", "w") as f:
    f.write(worker)

print("Built cloudflare/src/worker.js with inlined HTML")
