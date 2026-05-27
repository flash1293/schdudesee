# Tag Quality Review — Source Analysis

**Author:** Pinsel 📊
**Date:** 2026-05-27
**Context:** Analysis of `scrape_and_merge.py` keyword matching logic to identify root causes of false positive tags.

## How auto_tag Works

The `auto_tag()` function in `scrape_and_merge.py`:
1. Checks `TITLE_EXCLUSIVE_TAGS` (title-based forced tags)
2. Checks `ORGANIZER_EXCLUSIVE_TAGS` (organizer-based forced tags)
3. Scans `content_text = f"{title} {description}"` for each keyword in `KEYWORDS` dict
4. Keeps **only first 2** matching theme tags (`content_tags[:2]`)
5. Appends location tags (district matching)

Key issue: `if kw in content_text` does **substring matching without word boundaries**.

---

## Root Cause A: Substring Matching (No Word Boundaries)

The keyword matcher triggers on substrings within larger words, causing false positives.

### A1: "rad" → Sport keyword → matches in surnames
- **Keyword:** `rad` (Sport)
- **Matched in:** "Konrad" (contact surname in EKK description)
- **Affected:** 189 × Eltern-Kind-Kreis events
- **Context:** `"Ansprechpartnerin: Corinna Konrad, 01725618123"`
- **Fix:** Word-boundary regex or exclude common name patterns

### A2: "reiten" → Sport keyword → matches in German verbs
- **Keyword:** `reiten` (Sport, meaning horse-riding)
- **Matched in:** "bereiten" (as in "bereiten sich auf ... vor" = "prepare for")
- **Affected:** ~754 × Garde/Tanz events (Korallengarde, Seepferdchengarde, etc.)
- **Context:** `"...trainieren anspruchsvolle Choreografien und bereiten sich auf Auftritte..."`

### A3: "chor" → Musik keyword → matches in "Choreografien"
- **Keyword:** `chor` (Musik, meaning choir)
- **Matched in:** "Choreografien" (dance choreography)
- **Affected:** ~754 × Garde/Tanz events
- **Context:** Same as A2

### A4: "lieder" → Musik keyword → matches in "Mitgliedern"
- **Keyword:** `lieder` (Musik, meaning songs)
- **Matched in:** "Mitgliedern" (members)
- **Affected:** 189 × Modellbahn-AG events
- **Context:** `"...von Mitgliedern aus verschiedenen Klassenstufen..."`

---

## Root Cause B: `content_tags[:2]` Limit

Only the first 2 matching theme tags survive. False positives from Root Cause A occupy slots 1-2, pushing out legitimate tags.

| Event | Slot 1 (FP) | Slot 2 (FP/other) | Dropped at #3+ |
|-------|-------------|-------------------|----------------|
| Kükenstube (378×) | "Musik" (via `singen`) | "Kirche" (via `evangelisch`) | **"Kinder"** (via `kind`) |
| Korallengarde (754×) | "Sport" (via `reiten`) | "Musik" (via `chor`) | **"Kinder"** (via `kind`) |
| Eltern-Kind-Kreis (189×) | "Sport" (via `rad`) | "Kinder" (correct) | **"Treff"** (via `treff`) |

**Fix:** Increase limit to 3-4, OR clean false positives before truncating.

---

## Root Cause C: Missing Keyword Triggers

Some tags that should apply never match because no keyword triggers them:

| Missing Tag | Event | Reason | Affected |
|-------------|-------|--------|----------|
| "Kultur" | Korallengarde, Seepferdchengarde | "kultur" never in title/desc | **754** |
| "Kultur" | Seesternchengarde | "kultur" never in title/desc | **377** |

**Fix:** Add Garde/carnival keywords to Kultur: "Garde", "Fasching", "Karneval", "Kostüm", "Tanzgruppe"

---

## Root Cause D: Workshop Keywords Too Broad

"Workshop" matches `lernen`, `training`, `unterricht` — but regular youth/community groups use these words without being workshops.

| Event | Trigger | Affected |
|-------|---------|----------|
| Jugendrotkreuz "Dinos" | `lernen` in description | **189** |
| Pfadfinder*innengruppe | `lernen` in description | **188** |

**Fix options:**
1. Remove "lernen" from Workshop keywords
2. Add Jugendrotkreuz/Pfadfinder to FALSE_POSITIVE_CLEANUP
3. Add TITLE_EXCLUSIVE_TAGS to force "Treff" or "Natur" for these events

---

## Root Cause E: "Musik" Triggered by Common Activities

"singen" is a common activity in childcare/parent-child groups, but doesn't make them music events.

| Event | Trigger | Context | Affected |
|-------|---------|---------|----------|
| Kükenstube | `singen` | "Spielen, Singen, Geschichten..." | **378** |
| Eltern-Baby-Café | `singen` | "...beim Singen, Spielen und Basteln" | **189** |

**Fix:** Add these to FALSE_POSITIVE_CLEANUP for "Musik" when in childcare context.

---

## Summary of Fixes & Impact

| Fix | Code Change | FPs Removed | Tags Added | Effort |
|-----|-------------|-------------|------------|--------|
| A: Word boundaries | `re.search(r'\b' + kw + r'\b', text)` | ~1,886 | — | Low |
| B: Increase tag limit | `content_tags[:3]` or `[:4]` | — | ~1,321 | Trivial |
| C: Garde→Kultur rule | Add keywords or TITLE_EXCLUSIVE_TAGS | — | ~754 | Low |
| D: Workshop fix | Remove "lernen"/add FP cleanup | ~377 | — | Low |
| E: Musik fix | Add childcare events to FP cleanup | ~756 | — | Low |
| **Total** | | **~3,019** | **~2,075** | |

## Files Referenced

- `/shared/work/scrape_and_merge.py` — Main pipeline (1027 lines)
- `/shared/work/events/curated/*.json` — 5,427 curated event files
- `/shared/work/stutensee_events.db` — SQLite mirror of curated data
