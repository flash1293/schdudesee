#!/usr/bin/env python3
"""
PR Summary Generator for event curated JSON files.
Generates a markdown table showing added/modified/removed events.

Usage:
  python3 scripts/pr_summary.py <base_ref> <head_ref>

Outputs a markdown table to stdout for use in GitHub PR comments.
"""

import json, os, sys, glob
from pathlib import Path

EVENTS_DIR = 'events/curated'

def parse_event(filepath):
    """Parse a single event JSON file."""
    try:
        with open(filepath) as f:
            data = json.load(f)
        return {
            'title': data.get('title', '???'),
            'date_start': data.get('date_start', ''),
            'date_end': data.get('date_end', ''),
            'location': data.get('location', ''),
            'organizer': data.get('organizer', ''),
            'tags': data.get('tags', ''),
            'description': data.get('description', ''),
            'time_raw': data.get('time_raw', ''),
            'event_url': data.get('event_url', ''),
            'file': os.path.basename(filepath),
        }
    except (json.JSONDecodeError, FileNotFoundError) as e:
        return None

def get_event_files(ref=None):
    """Get all event JSON files, optionally at a specific git ref."""
    if ref:
        # Use git to list files at the given ref
        import subprocess
        try:
            result = subprocess.run(
                ['git', 'ls-tree', '-r', '--name-only', ref, EVENTS_DIR],
                capture_output=True, text=True, check=True
            )
            files = [f for f in result.stdout.strip().split('\n') if f.endswith('.json')]
            events = []
            for f in files:
                content = subprocess.run(
                    ['git', 'show', f'{ref}:{f}'],
                    capture_output=True, text=True
                )
                if content.returncode == 0 and content.stdout.strip():
                    try:
                        data = json.loads(content.stdout)
                        data['file'] = os.path.basename(f)
                        events.append(data)
                    except json.JSONDecodeError:
                        pass
            return events
        except subprocess.CalledProcessError:
            return []
    else:
        # Read from filesystem
        pattern = os.path.join(EVENTS_DIR, '*.json')
        events = []
        for fpath in sorted(glob.glob(pattern)):
            event = parse_event(fpath)
            if event:
                events.append(event)
        return events

def make_table(events, action):
    """Build markdown table rows for a list of events."""
    if not events:
        return ''
    rows = []
    for e in events:
        title = e.get('title', '???')
        # Flag generic titles
        if title.lower() in ['gottesdienst', 'gottesdienst mit posaunenchor', 'oekumenischer gottesdienst',
                              'center', 'lichtblick', 'maenner vesper', 'vesper']:
            title = f'{title} ⚠️'
        date_str = e.get('date_start', '')
        if e.get('date_end'):
            date_str += f' – {e["date_end"]}'
        location = e.get('location', '') or '—'
        tags = e.get('tags', '') or '—'
        organizer = e.get('organizer', '') or '—'
        rows.append(f'| {title} | {date_str} | {location} | {tags} | {organizer} | {action} |')
    return '\n'.join(rows)

def main():
    import subprocess
    
    # Get current branch name for header
    branch = os.environ.get('GITHUB_HEAD_REF', '')
    pr_title = os.environ.get('GITHUB_PR_TITLE', '')

    # Get base and head refs
    base_ref = os.environ.get('GITHUB_BASE_REF', 'main')
    
    # Get list of changed event files
    result = subprocess.run(
        ['git', 'diff', '--name-status', f'origin/{base_ref}...HEAD', '--', 'events/curated/*.json'],
        capture_output=True, text=True, check=False
    )
    
    added_files = []
    modified_files = []
    deleted_files = []
    
    for line in result.stdout.strip().split('\n'):
        if not line.strip():
            continue
        parts = line.split('\t')
        if len(parts) != 2:
            continue
        status, filepath = parts
        filename = os.path.basename(filepath)
        if status == 'A':
            added_files.append(filepath)
        elif status == 'M':
            modified_files.append(filepath)
        elif status == 'D':
            deleted_files.append(filepath)
    
    # Parse events from current HEAD for added/modified
    added_events = []
    for f in added_files:
        content = subprocess.run(
            ['git', 'show', f'HEAD:{f}'],
            capture_output=True, text=True
        )
        if content.returncode == 0 and content.stdout.strip():
            try:
                data = json.loads(content.stdout)
                data['file'] = os.path.basename(f)
                added_events.append(data)
            except json.JSONDecodeError:
                pass
    
    # Modified: show the new version
    modified_events = []
    for f in modified_files:
        content = subprocess.run(
            ['git', 'show', f'HEAD:{f}'],
            capture_output=True, text=True
        )
        if content.returncode == 0 and content.stdout.strip():
            try:
                data = json.loads(content.stdout)
                data['file'] = os.path.basename(f)
                modified_events.append(data)
            except json.JSONDecodeError:
                pass
    
    # Deleted: can't parse JSON from deleted files, list filenames
    deleted_events = [os.path.basename(f) for f in deleted_files]

    # Build the markdown
    lines = []
    total = len(added_events) + len(modified_events) + len(deleted_events)
    
    if total == 0:
        print('No event changes detected in this PR.')
        return
    
    table_header = '| Title | Date | Location | Tags | Organizer | Action |\n'
    table_header += '|-------|------|----------|------|-----------|--------|'
    
    tables = []
    
    if added_events:
        t = f'### ➕ Added Events ({len(added_events)})\n\n'
        t += table_header + '\n'
        for e in added_events:
            title = e.get('title', '???')
            date_str = e.get('date_start', '')
            if e.get('date_end'):
                date_str += f' – {e["date_end"]}'
            location = e.get('location', '') or '—'
            tags = e.get('tags', '') or '—'
            organizer = e.get('organizer', '') or '—'
            t += f'| {title} | {date_str} | {location} | {tags} | {organizer} | ➕ Added |\n'
        tables.append(t)
    
    if modified_events:
        t = f'### ✏️ Modified Events ({len(modified_events)})\n\n'
        t += table_header + '\n'
        for e in modified_events:
            title = e.get('title', '???')
            date_str = e.get('date_start', '')
            if e.get('date_end'):
                date_str += f' – {e["date_end"]}'
            location = e.get('location', '') or '—'
            tags = e.get('tags', '') or '—'
            organizer = e.get('organizer', '') or '—'
            t += f'| {title} | {date_str} | {location} | {tags} | {organizer} | ✏️ Modified |\n'
        tables.append(t)
    
    if deleted_events:
        t = f'### ➖ Removed Events ({len(deleted_events)})\n\n'
        t += '| File | Action |\n'
        t += '|------|--------|\n'
        for f in deleted_events:
            t += f'| {f} | ➖ Removed |\n'
        tables.append(t)
    
    print('\n'.join(tables))

if __name__ == '__main__':
    main()
