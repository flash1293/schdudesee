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
from urllib.parse import urlsplit, unquote

REPO = "flash1293/schdudesee"
GITHUB_API = "https://api.github.com"
GRAPHQL_URL = f"{GITHUB_API}/graphql"
HTTP_TIMEOUT_SECONDS = 15


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
            check=False,
        )
        url = result.stdout.strip()
        if url.startswith("https://") and "@" in url and "github.com" in url:
            userinfo = urlsplit(url).netloc.split("@", 1)[0]
            # Supports both "<token>" and "<user>:<token>" userinfo forms.
            token = unquote(userinfo.split(":", 1)[-1])
            if token:
                return token
    except (subprocess.SubprocessError, ValueError) as exc:
        print(f"WARN: failed to parse token from remote URL: {exc}", file=sys.stderr)
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
        with urllib.request.urlopen(req, timeout=HTTP_TIMEOUT_SECONDS) as resp:
            data = json.loads(resp.read().decode())
        if "errors" in data:
            print(f"GraphQL errors: {data['errors']}", file=sys.stderr)
            return None
        return data.get("data")
    except Exception as e:
        print(f"GraphQL request failed: {e}", file=sys.stderr)
        return None


def rest_get(token, url):
    """Execute a REST GET request against the GitHub API. Returns (data, next_url)."""
    import urllib.request

    req = urllib.request.Request(
        url,
        headers={
            "Authorization": f"Bearer {token}",
            "Accept": "application/vnd.github.v3+json",
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=HTTP_TIMEOUT_SECONDS) as resp:
            data = json.loads(resp.read().decode())
            # Parse Link header for pagination
            link_header = resp.headers.get("Link", "")
            next_url = None
            if link_header:
                for part in link_header.split(","):
                    part = part.strip()
                    if 'rel="next"' in part:
                        next_url = part.split(";")[0].strip("<>")
            return data, next_url
    except Exception as e:
        print(f"REST request failed: {e}", file=sys.stderr)
        return None, None


def rest_get_all(token, url):
    """Fetch all pages of a REST endpoint.
    Raises RuntimeError if the first page fails (avoiding silent empty results).
    Subsequent page failures log a warning and return partial data."""
    all_data = []
    next_url = url
    page = 0
    while next_url:
        page += 1
        data, next_url = rest_get(token, next_url)
        if data is None:
            if page == 1:
                raise RuntimeError(f"Failed to fetch first page from {url}")
            print(f"⚠️  Warning: page {page} fetch failed, returning partial data", file=sys.stderr)
            break
        if isinstance(data, list):
            all_data.extend(data)
        else:
            # Single object (e.g. PR metadata) — no pagination needed
            return data
    return all_data


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
    """Fetch CodeRabbit review threads via GraphQL (with resolved state), paginating all pages."""
    owner, repo = REPO.split("/")
    pr_num = int(pr_number)

    # Paginate reviewThreads
    all_threads = []
    threads_cursor = None
    threads_page_size = 50

    while True:
        query = """
        query($owner: String!, $repo: String!, $pr: Int!, $threadsCursor: String) {
          repository(owner: $owner, name: $repo) {
            pullRequest(number: $pr) {
              title
              url
              reviewThreads(first: 50, after: $threadsCursor) {
                pageInfo { hasNextPage endCursor }
                nodes {
                  isResolved
                  resolvedBy { login }
                  comments(first: 10) {
                    pageInfo { hasNextPage endCursor }
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
            "owner": owner,
            "repo": repo,
            "pr": pr_num,
            "threadsCursor": threads_cursor,
        })
        if not data:
            return None

        pr_data = data.get("repository", {}).get("pullRequest")
        if not pr_data:
            print("PR not found.", file=sys.stderr)
            return None

        pr_title = pr_data.get("title", "")
        pr_url = pr_data.get("url", "")

        thread_page = pr_data.get("reviewThreads", {})
        thread_nodes = thread_page.get("nodes", [])
        all_threads.extend(t for t in thread_nodes if t)

        page_info = thread_page.get("pageInfo", {})
        if not page_info.get("hasNextPage"):
            break
        threads_cursor = page_info.get("endCursor")

    # Now process all collected threads and paginate comments within each
    inline_comments = []
    for thread in all_threads:
        is_resolved = thread.get("isResolved", False)
        resolved_by = thread.get("resolvedBy", {})
        resolved_by_login = resolved_by.get("login") if resolved_by else None

        # Collect all comments in this thread (may need pagination)
        all_comment_nodes = []
        comment_page = thread.get("comments", {})
        comment_nodes = comment_page.get("nodes", [])
        all_comment_nodes.extend(c for c in comment_nodes if c)

        # Note: For typical CodeRabbit threads, 10 comments is almost always enough.
        # Paginating per-thread comments would require re-fetching each thread with a cursor,
        # which is very heavy. The 10 limit covers virtually all CodeRabbit threads.
        # If needed, this can be extended later.

        for node in all_comment_nodes:
            author = node.get("author", {}).get("login", "")
            if "coderabbit" not in author.lower():
                continue
            body = node.get("body", "")
            inline_comments.append({
                "path": node.get("path", ""),
                "line": node.get("line"),
                "author": author,
                "body": body,
                "created_at": node.get("createdAt", ""),
                "is_resolved": is_resolved,
                "resolved_by": resolved_by_login,
                "severity": extract_severity(body),
                "title": extract_title(body),
                "type": "inline",
            })

    # Also fetch review-level comments (body of reviews like "outside diff" comments)
    try:
        review_comments = fetch_review_bodies_rest(token, pr_number)
    except RuntimeError as e:
        print(f"⚠️  Failed to fetch review-level comments: {e}", file=sys.stderr)
        review_comments = []

    all_comments = inline_comments + review_comments

    return {
        "pr_title": pr_title,
        "pr_url": pr_url,
        "comments": all_comments,
    }


def fetch_review_bodies_rest(token, pr_number):
    """Fetch PR review bodies (which may contain 'outside diff' comments from CodeRabbit). Paginates all pages."""
    url = f"{GITHUB_API}/repos/{REPO}/pulls/{pr_number}/reviews?per_page=100"
    data = rest_get_all(token, url)
    if data is None:
        return []

    review_comments = []
    for r in data:
        author = r.get("user", {}).get("login", "")
        if "coderabbit" not in author.lower():
            continue
        body = r.get("body", "")
        if not body:
            continue
        # Only include if it contains "outside diff" or actual actionable content
        if "outside" in body.lower() or "actionable comments" in body.lower():
            review_comments.append({
                "path": "(review comment)",
                "line": None,
                "author": author,
                "body": body,
                "created_at": r.get("submitted_at", ""),
                "is_resolved": None,
                "resolved_by": None,
                "severity": "review",
                "title": "CodeRabbit Review Comment (outside diff)",
                "type": "review",
            })
    return review_comments


def fetch_comments_rest(token, pr_number):
    """Fallback: fetch CodeRabbit PR review comments via REST API (no resolved state). Paginates all pages."""
    url = f"{GITHUB_API}/repos/{REPO}/pulls/{pr_number}/comments?per_page=100"
    try:
        data = rest_get_all(token, url)
    except RuntimeError:
        print("⚠️  REST API fetch failed entirely.", file=sys.stderr)
        return None
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
    pr_api_url = f"{GITHUB_API}/repos/{REPO}/pulls/{pr_number}"
    pr_data, _ = rest_get(token, pr_api_url)  # single object, no pagination
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
        resolved_status = "❓ N/A (review-level comment)"

    sev_icon = {
        "critical": "🔴",
        "major": "🟠",
        "medium": "🟡",
        "minor": "⚪",
        "quick-win": "⚡",
        "review": "📋",
        "unknown": "❔",
    }.get(c["severity"], "❔")

    ctype = c.get("type", "inline")
    type_tag = "📝 Review-level" if ctype == "review" else "💬 Inline"

    lines = [
        f"### {type_tag} {sev_icon} {c['severity'].upper()}: {c['title']}",
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
    inline = sum(1 for c in comments if c.get("type") == "inline")
    reviews = sum(1 for c in comments if c.get("type") == "review")
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
    print(f"  - 💬 **Inline:** {inline}")
    print(f"  - 📋 **Review-level (outside diff):** {reviews}")
    print(f"**🔴 Open:** {open_c}")
    print(f"**✅ Resolved:** {resolved}")
    if unknown:
        print(f"**❓ N/A:** {unknown} (review-level comments)")
    print()
    print("### By Severity")
    for sev in ["critical", "major", "medium", "minor", "quick-win", "review", "unknown"]:
        count = by_severity.get(sev, 0)
        if count:
            icon = {"critical": "🔴", "major": "🟠", "medium": "🟡", "minor": "⚪", "quick-win": "⚡", "review": "📋", "unknown": "❔"}[sev]
            print(f"- {icon} **{sev.capitalize()}**: {count}")
    print()

    # Per-file breakdown (only for inline)
    inline_only = [c for c in comments if c.get("type") == "inline"]
    if inline_only:
        by_file = {}
        for c in inline_only:
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

    pr_number_raw = sys.argv[1]
    as_json = "--json" in sys.argv

    # Validate PR number early
    try:
        pr_number = int(pr_number_raw)
        if pr_number <= 0:
            raise ValueError
    except ValueError:
        print(f"ERROR: Invalid PR number '{pr_number_raw}'. Expected a positive integer.", file=sys.stderr)
        sys.exit(1)

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
