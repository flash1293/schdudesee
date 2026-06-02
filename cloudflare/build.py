#!/usr/bin/env python3
"""
Build the final cloudflare/src/worker.js from source parts.

Source of truth: cloudflare/src/_worker.js (hand-written logic, no base64 blobs)
Generated: cloudflare/src/worker.js (logic + inlined HTML + favicon)

Usage: cd cloudflare && python3 build.py
"""

import re, base64, os, hashlib

build_dir = os.path.dirname(os.path.abspath(__file__))

with open(os.path.join(build_dir, "..", "index.html")) as f:
    html = f.read()

# ── Content-hashed asset URLs ──────────────────────────────────────
# Read JS files, compute SHA256 hashes, use hashed filenames so we can
# cache them indefinitely.
def hash_file(relpath):
    full = os.path.join(build_dir, relpath)
    with open(full, "rb") as f:
        data = f.read()
    h = hashlib.sha256(data).hexdigest()[:12]
    return h, data

app_hash, app_data = hash_file("src/app.js")
chat_hash, chat_data = hash_file("src/chat.js")

app_hashed_js = f"app.{app_hash}.js"
chat_hashed_js = f"chat.{chat_hash}.js"

# Replace references in the HTML template
html = html.replace('src="/app.js"', f'src="/{app_hashed_js}"')
html = html.replace('src="/chat.js"', f'src="/{chat_hashed_js}"')
html = html.replace('href="/app.js"', f'href="/{app_hashed_js}"')
html = html.replace('href="/chat.js"', f'href="/{chat_hashed_js}"')
# favicon still uses a simple cache-bust for now (binary, small)
html = html.replace('href="/favicon.png"', f'href="/favicon.png?v={app_hash[:8]}"')

# Add preload hints so the browser discovers JS early
preload_hints = f'<link rel="preload" href="/{app_hashed_js}" as="script">\n<link rel="preload" href="/{chat_hashed_js}" as="script">\n'
html = html.replace('<link rel="icon"', preload_hints + '<link rel="icon"')

# ── Inline CSS ─────────────────────────────────────────────────────
with open(os.path.join(build_dir, "src", "style.css")) as f:
    all_css = f.read()

# Minify CSS: strip comments and collapse whitespace
all_css = re.sub(r'/\*.*?\*/', '', all_css, flags=re.DOTALL)
all_css = re.sub(r'\s{2,}', ' ', all_css)
all_css = all_css.strip()

html = html.replace('STYLE_CSS_PLACEHOLDER', all_css)

# ── HTML minification ──────────────────────────────────────────────
# Remove extra whitespace between tags
html = re.sub(r'>\s+<', '><', html)

# Collapse whitespace only *outside* <script> blocks
parts = re.split(r'(<script[^>]*>.*?</script>)', html, flags=re.DOTALL)
html = ''.join(
    re.sub(r'\s{2,}', ' ', part) if not part.strip().startswith('<script') else part
    for part in parts
)

# ── Encode template as base64 ──────────────────────────────────────
encoded = base64.b64encode(html.encode("utf-8")).decode("ascii")
inlined = f'const indexHtml = new TextDecoder().decode(Uint8Array.from(atob("{encoded}"), c=>c.charCodeAt(0)));\n'

# ── Inline static assets ──────────────────────────────────────────
# Helper to inline a file as a base64 constant
def inline_bytes(data, var_name):
    b64 = base64.b64encode(data).decode("ascii")
    return f'const {var_name} = new TextDecoder().decode(Uint8Array.from(atob("{b64}"), c=>c.charCodeAt(0)));\n'

app_js_line = inline_bytes(app_data, "appJs")
chat_js_line = inline_bytes(chat_data, "chatJs")

# Favicon (binary)
favicon_path = os.path.join(build_dir, "favicon.png")
if os.path.exists(favicon_path):
    with open(favicon_path, "rb") as f:
        favicon_b64 = base64.b64encode(f.read()).decode("ascii")
    favicon_line = f'const faviconB64 = "{favicon_b64}";\n'
else:
    favicon_line = "const faviconB64 = null;\n"

# ── Worker source ──────────────────────────────────────────────────
with open(os.path.join(build_dir, "src", "_worker.js")) as f:
    worker_src = f.read()

# ── Assemble final worker ─────────────────────────────────────────
worker = inlined + favicon_line + app_js_line + chat_js_line + worker_src

with open(os.path.join(build_dir, "src", "worker.js"), "w") as f:
    f.write(worker)

print(f"Built cloudflare/src/worker.js")
print(f"  app.js  → /{app_hashed_js}")
print(f"  chat.js → /{chat_hashed_js}")
