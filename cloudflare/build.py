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

# ── Minify CSS in <style> blocks ────────────────────────────────────

def minify_css(css):
    """Basic CSS minification."""
    # Remove comments
    css = re.sub(r'/\*.*?\*/', '', css, flags=re.DOTALL)
    # Remove whitespace around { } : ; , 
    css = re.sub(r'\s*{\s*', '{', css)
    css = re.sub(r'\s*}\s*', '}', css)
    css = re.sub(r'\s*:\s*', ':', css)
    css = re.sub(r'\s*;\s*', ';', css)
    css = re.sub(r'\s*,\s*', ',', css)
    # Collapse multiple spaces to one, then remove leading/trailing spaces per line
    css = re.sub(r'\s+', ' ', css)
    # Remove space before !important
    css = re.sub(r'\s+!important', '!important', css)
    # Remove 0px → 0 (but keep 0 in values like 0.5)
    css = re.sub(r':0(?:(?:\.\d+)?(?:px|pt|em|rem|%))', ':0', css)
    css = re.sub(r'\s0(?:(?:\.\d+)?(?:px|pt|em|rem|%))', ' 0', css)
    # Shorten hex colors: #ffffff → #fff etc.
    css = re.sub(r'#([0-9a-fA-F])\1([0-9a-fA-F])\2([0-9a-fA-F])\3', r'#\1\2\3', css)
    # Remove trailing semicolons before closing brace
    css = re.sub(r';}', '}', css)
    # Remove empty rules
    css = re.sub(r'[^}]+{}\s*', '', css)
    return css.strip()

def minify_html_template(html):
    """Minify HTML template."""
    # Remove HTML comments BUT preserve SSR placeholders (<!--SSR_*-->)
    def preserve_ssr(m):
        if m.group(0).startswith('<!--SSR_'):
            return m.group(0)
        return ''
    html = re.sub(r'<!--[^\[][\s\S]*?-->', preserve_ssr, html)
    # Remove extra whitespace between tags
    html = re.sub(r'>\s+<', '><', html)
    
    # Process CSS blocks
    def minify_style_block(m):
        return f'<style>{minify_css(m.group(1))}</style>'
    html = re.sub(r'<style>(.*?)</style>', minify_style_block, html, flags=re.DOTALL)
    
    # Collapse whitespace outside <script> blocks to avoid mangling JS
    parts = re.split(r'(<script[^>]*>.*?</script>)', html, flags=re.DOTALL)
    html = ''.join(
        re.sub(r'\s{2,}', ' ', part) if not part.strip().startswith('<script') else part
        for part in parts
    )
    
    return html

html = minify_html_template(html)

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
