#!/usr/bin/env python3
"""
PR Summary Generator for event curated JSON files.
Generates a markdown table showing added/modified/removed events.

Usage (CI):
  python3 scripts/pr_summary.py

Uses environment variables:
  GITHUB_BASE_REF — base branch (default: main)

Outputs a markdown table to stdout for use in GitHub PR comments.
"""

import json, os, subprocess, sys
from pathlib import Path

EVENTS_DIR = 'events/curated'

GENERIC_TITLES = {
    'gottesdienst', 'gottesdienst mit posaunenchor', 'oekumenischer gottesdienst',
    'center', 'lichtblick', 'maenner vesper', 'vesper',
    'altpapiersammlung',
}

def flag_generic_title(title):
    tl = title.lower().strip()
    if tl in GENERIC_TITLES:
        return f'{title} ⚠️'
    if len(title.split()) <= 2 and len(title) < 20:
        return f'{title} ⚠️'
    return title

def make_event_row(e, action):
    title = flag_generic_title(e.get('title', '???'))
    date_str = e.get('date_start', '')
    if e.get('date_end'):
        date_str += f' – {e["date_end"]}'
    location = str(e.get('location') or '—').replace('|', '/')
    tags_val = e.get('tags') or '—'
    if isinstance(tags_val, list):
        tags_val = ','.join(tags_val)
    tags = tags_val.replace('|', '/')
    organizer = str(e.get('organizer') or '—').replace('|', '/')
    return f'| {title} | {date_str} | {location} | {tags} | {organizer} | {action} |'

def get_changed_files(base_ref):
    try:
        result = subprocess.run(
            ['git', 'diff', '--name-status', f"{base_ref}...HEAD", '--', f'{EVENTS_DIR}/*.json'],
            capture_output=True, text=True, check=False
        )
    except FileNotFoundError:
        print('⚠️ Error: git not available.', file=sys.stderr)
        sys.exit(0)
    if result.returncode != 0:
        print(f'⚠️ Error: git diff failed (exit code {result.returncode}): {result.stderr.strip()}', file=sys.stderr)
        sys.exit(1)
    added, modified, deleted = [], [], []
    for line in result.stdout.strip().split('\n'):
        if not line.strip():
            continue
        parts = line.split('\t')
        status = parts[0]
        # R* and C* statuses have 3 parts: R100 oldfile newfile
        filepath = parts[-1]  # Last part is always the destination path
        if status == 'A':
            added.append(filepath)
        elif status == 'M':
            modified.append(filepath)
        elif status == 'D':
            deleted.append(filepath)
        elif status.startswith('R'):
            deleted.append(filepath)  # Treat renames as deletions + additions
        elif status.startswith('C'):
            added.append(filepath)    # Treat copies as additions
    return added, modified, deleted

def read_event_from_ref(filepath, ref):
    try:
        content = subprocess.run(
            ['git', 'show', f'{ref}:{filepath}'],
            capture_output=True, text=True, check=True
        )
        if not content.stdout.strip():
            return None
        data = json.loads(content.stdout)
        data['file'] = os.path.basename(filepath)
        return data
    except (subprocess.CalledProcessError, json.JSONDecodeError):
        return None

def main():
    base_ref = os.environ.get('GITHUB_BASE_REF', 'origin/main')
    if not base_ref.startswith('origin/'):
        # Ensure we have the base ref available for three-dot diff
        result = subprocess.run(['git', 'fetch', 'origin', base_ref], capture_output=True, text=True, check=False)
        if result.returncode != 0:
            print(f'⚠️ Could not fetch origin/{base_ref}, falling back to two-dot diff. Error: {result.stderr.strip()}', file=sys.stderr)
            base_ref = f'origin/{base_ref}'
        else:
            base_ref = f'origin/{base_ref}'

    added_files, modified_files, deleted_files = get_changed_files(base_ref)

    if not added_files and not modified_files and not deleted_files:
        print('No event changes detected in this PR.')
        return

    added_events = []
    for f in added_files:
        e = read_event_from_ref(f, 'HEAD')
        if e:
            added_events.append(e)

    modified_events = []
    for f in modified_files:
        e = read_event_from_ref(f, 'HEAD')
        if e:
            modified_events.append(e)

    table_header = '| Title | Date | Location | Tags | Organizer | Action |\n'
    table_header += '|-------|------|----------|------|-----------|--------|'

    sections = []
    if added_events:
        t = f'### ➕ Added Events ({len(added_events)})\n\n' + table_header + '\n'
        for e in added_events:
            t += make_event_row(e, '➕ Added') + '\n'
        sections.append(t)
    if modified_events:
        t = f'### ✏️ Modified Events ({len(modified_events)})\n\n' + table_header + '\n'
        for e in modified_events:
            t += make_event_row(e, '✏️ Modified') + '\n'
        sections.append(t)
    if deleted_files:
        t = f'### ➖ Removed Events ({len(deleted_files)})\n\n| File | Action |\n|------|--------|\n'
        for f in deleted_files:
            t += f'| {os.path.basename(f)} | ➖ Removed |\n'
        sections.append(t)

    print('\n'.join(sections))

if __name__ == '__main__':
    main()
