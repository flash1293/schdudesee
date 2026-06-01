#!/usr/bin/env python3
"""
Build the final cloudflare/src/worker.js from source parts.

Source of truth: cloudflare/src/_worker.js (hand-written logic, no base64 blobs)
Generated: cloudflare/src/worker.js (logic + inlined HTML + favicon)

Usage: cd cloudflare && python3 build.py
"""

import re, base64, os

import time
build_version = str(int(time.time()))

with open("../index.html") as f:
    html = f.read()

# Add build version to static asset URLs for cache busting
html = html.replace('href="/app.js"', f'href="/app.js?v={build_version}"')
html = html.replace('href="/chat.js"', f'href="/chat.js?v={build_version}"')
html = html.replace('src="/app.js"', f'src="/app.js?v={build_version}"')
html = html.replace('src="/chat.js"', f'src="/chat.js?v={build_version}"')
html = html.replace('href="/favicon.png"', f'href="/favicon.png?v={build_version}"')

# Read all CSS (merged critical + deferred) and inject it inline
with open("src/style.css") as f:
    all_css = f.read()

# Minify CSS: strip comments and collapse whitespace
all_css = re.sub(r'/\*.*?\*/', '', all_css, flags=re.DOTALL)
all_css = re.sub(r'\s{2,}', ' ', all_css)
all_css = all_css.strip()

html = html.replace('STYLE_CSS_PLACEHOLDER', all_css)

# Minify slightly: remove extra whitespace between tags
html = re.sub(r'>\s+<', '><', html)

# Collapse whitespace only *outside* <script> blocks to avoid mangling JS
# (CF Workers gzip the response, so this is just a minor size optimization)
parts = re.split(r'(<script[^>]*>.*?</script>)', html, flags=re.DOTALL)
html = ''.join(
    re.sub(r'\s{2,}', ' ', part) if not part.strip().startswith('<script') else part
    for part in parts
)

# Encode as base64 to avoid any JS string escaping issues
encoded = base64.b64encode(html.encode("utf-8")).decode("ascii")
inlined = f'const indexHtml = new TextDecoder().decode(Uint8Array.from(atob("{encoded}"), c=>c.charCodeAt(0)));\n'

# Helper to inline a text file as a base64 constant
def inline_text_file(path, var_name):
    full_path = os.path.join(os.path.dirname(__file__), path)
    if os.path.exists(full_path):
        with open(full_path, "rb") as f:
            b64 = base64.b64encode(f.read()).decode("ascii")
        return f'const {var_name} = new TextDecoder().decode(Uint8Array.from(atob("{b64}"), c=>c.charCodeAt(0)));\n'
    return f'const {var_name} = "";\n'

# Also inline the favicon (binary)
favicon_path = os.path.join(os.path.dirname(__file__), "favicon.png")
if os.path.exists(favicon_path):
    with open(favicon_path, "rb") as f:
        favicon_b64 = base64.b64encode(f.read()).decode("ascii")
    favicon_line = f'const faviconB64 = "{favicon_b64}";\n'
else:
    favicon_line = "const faviconB64 = null;\n"

# Inline the static assets (JS files only — CSS is now inline in index.html)
app_js_line = inline_text_file("src/app.js", "appJs")
chat_js_line = inline_text_file("src/chat.js", "chatJs")

# Read the source logic (hand-written, no base64 blobs)
with open("src/_worker.js") as f:
    worker_src = f.read()

# Build the final worker: generated constants + hand-written logic
worker = inlined + favicon_line + app_js_line + chat_js_line + worker_src

with open("src/worker.js", "w") as f:
    f.write(worker)

print("Built cloudflare/src/worker.js from src/_worker.js + index.html + favicon")
