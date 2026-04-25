# Schdudesee Dedup Agents

## Cross-Source Agentic Dedup

Run when new sources are added or duplicates are reported.

**Purpose:** Merge events that are the same real-world event but appear with
slightly different titles across sources (e.g. "Büchiger Maifest" vs "Maifest Büchig").

**Trigger:** `python3 -c "exec(open('agents/dedup.py').read())"`

**Approach:**
1. Read all curated_events from DB
2. Normalize titles (lowercase, remove punctuation, normalize umlauts, strip suffixes)
3. Group by normalized title + same date (±1 day)
4. For groups with multiple entries, verify location similarity
5. Merge: keep best title, longest description, combine sources
6. Delete duplicates, update the surviving row

## Keyword-Based Tagger

Run after dedup to tag new untagged events.

**Trigger:** Built into `run_pipeline.py` as `tag_untagged()`

## Recurring Detection

Find weekly/biweekly/monthly event series.

**Trigger:** `python3 detect_recurring.py`

## Standing Agent Instructions

When spawning a dedup agent, use this prompt template:

```
You are running agentic deduplication on the Stutensee events DB.

Read all curated_events from the DB at stutensee_events.db.
Find cross-source duplicates where the same real-world event has slightly
different titles (e.g. "Büchiger Maifest" vs "Maifest Büchig").

For each duplicate group:
1. Verify they're the same event (same date ±1 day, similar location)
2. Keep the best title, longest description, merge sources
3. Delete the duplicate row(s) from curated_events
4. Also delete corresponding raw_to_curated mappings

Report: how many duplicates found and merged.
```
