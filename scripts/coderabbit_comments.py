#!/usr/bin/env python3
"""
Fetch CodeRabbit review comments from a GitHub pull request.

Outputs each comment with its file, line number, severity, title, body,
and resolved state. Also prints a summary table.

Usage:
    python3 scripts/coderabbit_comments.py <PR-number>
    python3 scripts/coderabbit_comments.py 96

Requires GITHUB_TOKEN env var or uses the PAT embedded in the git remote.
"""

import json
import os
import re
import subprocess
import sys
from pathlib import Path

REPO = "flash1293/schdudesee"
GITHUB_API = "https://api.github.com"
GRAPHQL_URL = f"{GITHUB_API}/graphql"


def get_token():
    """Get GitHub token from env or git remote URL."""
    token = os.environ.get("GITHUB_TOKEN")
    if token:
        return token
    # Fallback: extract from git remote
    try:
        result = subprocess.run(
            ["git", "remote", "get-url", "origin"],
            capture_output=True, text=True, cwd=Path(__file__).resolve().parent.parent,
        )
        url = result.stdout.strip()
        # Format: https://<token>@github.com/...
        if "@" in url and "github.com" in url:
            token = url.split("://")[1].split("@")[0]
            if token:
                return token
    except Exception:
        pass
    print("ERROR: No GITHUB_TOKEN found. Set GITHUB_TOKEN env var.", file=sys.stderr)
    sys.exit(1)


def graphql_query(token, query, variables=None):
    """Execute a GraphQL query against the GitHub API."""
    payload = {"query": query}
    if variables:
        payload["variables"] = variables
    import urllib.request

    req = urllib.request.Request(
        GRAPHQL_URL,
        data=json.dumps(payload).encode(),
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        },
    )
    try:
        with urllib.request.urlopen(req) as resp:
            data = json.loads(resp.read().decode())
        if "errors" in data:
            print(f"GraphQL errors: {data['errors']}", file=sys.stderr)
            return None
        return data.get("data")
    except Exception as e:
        print(f"GraphQL request failed: {e}", file=sys.stderr)
        return None


def rest_get(token, url):
    """Execute a REST GET request against the GitHub API."""
    import urllib.request

    req = urllib.request.Request(
        url,
        headers={
            "Authorization": f"Bearer {token}",
            "Accept": "application/vnd.github.v3+json",
        },
    )
    try:
        with urllib.request.urlopen(req) as resp:
            return json.loads(resp.read().decode())
    except Exception as e:
        print(f"REST request failed: {e}", file=sys.stderr)
        return None


def extract_severity(body):
    """Extract severity label from CodeRabbit comment body."""
    sev_map = {
        "🔴 Critical": "critical",
        "🟠 Major": "major",
        "🟡 Medium": "medium",
        "⚪ Minor": "minor",
        "⚡ Quick win": "quick-win",
    }
    for emoji_label, sev in sev_map.items():
        if emoji_label in body:
            return sev
    return "unknown"


def extract_title(body):
    """Extract the title from a CodeRabbit comment body."""
    # Title is usually the first **bold** line after the severity header
    for line in body.split("\n"):
        line = line.strip()
        if line.startswith("**") and line.endswith("**"):
            return line.strip("*")
    return "(no title)"


def fetch_comments_graphql(token, pr_number):
    """Fetch CodeRabbit review threads via GraphQL (with resolved state)."""
    query = """
    query($owner: String!, $repo: String!, $pr: Int!) {
      repository(owner: $owner, name: $repo) {
        pullRequest(number: $pr) {
          title
          url
          reviewThreads(first: 50) {
            nodes {
              isResolved
              resolvedBy { login }
              comments(first: 10) {
                nodes {
                  body
                  path
                  line
                  author { login }
                  createdAt
                }
              }
            }
          }
        }
      }
    }
    """
    data = graphql_query(token, query, {
        "owner": REPO.split("/")[0],
        "repo": REPO.split("/")[1],
        "pr": int(pr_number),
    })
    if not data:
        return None

    pr_data = data.get("repository", {}).get("pullRequest")
    if not pr_data:
        print("PR not found.", file=sys.stderr)
        return None

    threads = pr_data.get("reviewThreads", {}).get("nodes", [])
    comments = []
    for thread in threads:
        if not thread:
            continue
        is_resolved = thread.get("isResolved", False)
        resolved_by = thread.get("resolvedBy", {})
        resolved_by_login = resolved_by.get("login") if resolved_by else None
        for node in thread.get("comments", {}).get("nodes", []):
            if not node:
                continue
            author = node.get("author", {}).get("login", "")
            # Only include CodeRabbit comments
            if "coderabbit" not in author.lower():
                continue
            body = node.get("body", "")
            comments.append({
                "path": node.get("path", ""),
                "line": node.get("line"),
                "author": author,
                "body": body,
                "created_at": node.get("createdAt", ""),
                "is_resolved": is_resolved,
                "resolved_by": resolved_by_login,
                "severity": extract_severity(body),
                "title": extract_title(body),
            })

    return {
        "pr_title": pr_data.get("title", ""),
        "pr_url": pr_data.get("url", ""),
        "comments": comments,
    }


def fetch_comments_rest(token, pr_number):
    """Fallback: fetch CodeRabbit PR review comments via REST API (no resolved state)."""
    url = f"{GITHUB_API}/repos/{REPO}/pulls/{pr_number}/comments?per_page=100"
    data = rest_get(token, url)
    if data is None:
        return None

    comments = []
    for c in data:
        author = c.get("user", {}).get("login", "")
        if "coderabbit" not in author.lower():
            continue
        body = c.get("body", "")
        comments.append({
            "path": c.get("path", ""),
            "line": c.get("line"),
            "author": author,
            "body": body,
            "created_at": c.get("created_at", ""),
            "is_resolved": None,  # Not available via REST
            "resolved_by": None,
            "severity": extract_severity(body),
            "title": extract_title(body),
            "html_url": c.get("html_url", ""),
        })

    # Also get PR title
    pr_url = f"{GITHUB_API}/repos/{REPO}/pulls/{pr_number}"
    pr_data = rest_get(token, pr_url)
    pr_title = pr_data.get("title", "") if pr_data else ""

    return {
        "pr_title": pr_title,
        "pr_url": f"https://github.com/{REPO}/pull/{pr_number}",
        "comments": comments,
    }


def format_comment(c):
    """Format a single comment for display."""
    resolved_status = "✅ Resolved" if c["is_resolved"] else "🔴 Open"
    if c["is_resolved"] and c.get("resolved_by"):
        resolved_status += f" (by {c['resolved_by']})"
    elif c["is_resolved"] is None:
        resolved_status = "❓ Unknown (REST fallback)"

    sev_icon = {
        "critical": "🔴",
        "major": "🟠",
        "medium": "🟡",
        "minor": "⚪",
        "quick-win": "⚡",
        "unknown": "❔",
    }.get(c["severity"], "❔")

    lines = [
        f"### {sev_icon} {c['severity'].upper()}: {c['title']}",
        f"**File:** `{c['path']}` (line {c['line'] or 'N/A'})",
        f"**Status:** {resolved_status}",
        f"**Author:** {c['author']}",
        f"**Created:** {c['created_at']}",
        "```",
        c["body"][:500] + ("..." if len(c["body"]) > 500 else ""),
        "```",
    ]
    return "\n".join(lines) + "\n"


def print_summary(comments):
    """Print a summary table of comments."""
    if not comments:
        print("No CodeRabbit comments found.")
        return

    total = len(comments)
    resolved = sum(1 for c in comments if c["is_resolved"])
    open_c = sum(1 for c in comments if c["is_resolved"] is False)
    unknown = sum(1 for c in comments if c["is_resolved"] is None)
    by_severity = {}
    for c in comments:
        by_severity.setdefault(c["severity"], 0)
        by_severity[c["severity"]] += 1

    print("## 📋 CodeRabbit Comments Summary")
    print()
    print(f"**Total comments:** {total}")
    print(f"**🔴 Open:** {open_c}")
    print(f"**✅ Resolved:** {resolved}")
    if unknown:
        print(f"**❓ Unknown state:** {unknown} (fetched via REST fallback)")
    print()
    print("### By Severity")
    for sev in ["critical", "major", "medium", "minor", "quick-win", "unknown"]:
        count = by_severity.get(sev, 0)
        if count:
            icon = {"critical": "🔴", "major": "🟠", "medium": "🟡", "minor": "⚪", "quick-win": "⚡", "unknown": "❔"}[sev]
            print(f"- {icon} **{sev.capitalize()}**: {count}")
    print()

    # Per-file breakdown
    by_file = {}
    for c in comments:
        by_file.setdefault(c["path"], []).append(c)
    print("### By File")
    for path, cs in sorted(by_file.items()):
        open_count = sum(1 for c in cs if c["is_resolved"] is False)
        resolved_count = sum(1 for c in cs if c["is_resolved"] is True)
        status = f"{open_count} open, {resolved_count} resolved" if open_count else f"✅ all resolved"
        print(f"- `{path}` — {len(cs)} comments ({status})")
    print()


def print_detailed(comments, pr_title, pr_url):
    """Print detailed view of all comments."""
    print(f"# CodeRabbit Comments for PR: {pr_title}")
    print(f"PR URL: {pr_url}")
    print()
    print_summary(comments)

    if not comments:
        return

    print("---")
    print("## Detailed Comments")
    print()
    for i, c in enumerate(comments, 1):
        print(format_comment(c))
        if i < len(comments):
            print("---")
            print()


def main():
    if len(sys.argv) < 2:
        print(f"Usage: {sys.argv[0]} <PR-number> [--json]", file=sys.stderr)
        print(f"  {sys.argv[0]} 96", file=sys.stderr)
        print(f"  {sys.argv[0]} 96 --json    # machine-readable output", file=sys.stderr)
        sys.exit(1)

    pr_number = sys.argv[1]
    as_json = "--json" in sys.argv

    token = get_token()

    # Try GraphQL first (has resolved state)
    result = fetch_comments_graphql(token, pr_number)

    # Fallback to REST if GraphQL fails
    if result is None:
        print("GraphQL query failed, falling back to REST API...", file=sys.stderr)
        result = fetch_comments_rest(token, pr_number)

    if result is None or result.get("comments") is None:
        print("Failed to fetch comments.", file=sys.stderr)
        sys.exit(1)

    comments = result["comments"]

    if as_json:
        print(json.dumps({
            "pr_number": int(pr_number),
            "pr_title": result["pr_title"],
            "pr_url": result["pr_url"],
            "total_comments": len(comments),
            "open_count": sum(1 for c in comments if c["is_resolved"] is False),
            "resolved_count": sum(1 for c in comments if c["is_resolved"] is True),
            "comments": comments,
        }, indent=2, ensure_ascii=False))
    else:
        print_detailed(comments, result["pr_title"], result["pr_url"])


if __name__ == "__main__":
    main()
