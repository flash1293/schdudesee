# Tag Quality Review — Standardized Flagging Criteria

## Purpose
To ensure consistent tagging across all batches (6–11) regardless of which bot reviews them.

## Severity Levels

### 🔴 HIGH — Wrong tag (must fix)
The tag is objectively incorrect for the event content.

| Pattern | Example | Suggested Fix |
|---------|---------|---------------|
| "Sport" on non-sport events | Eltern-Kind-Kreis (playgroup), Gartenfest, Abenteuer-Zwerge | Remove "Sport". Note: "Sport" + "Kinder" together is fine for actual kids' sports (Garde dance training, etc.) |
| "Workshop" on regular groups | Jugendrotkreuz, Pfadfinder (regular youth clubs, not workshops) | Replace with "Treff" or "Natur" |
| "Musik" on non-music events | Modellbahn-AG (model railway), Eltern-Baby-Café | Remove "Musik", add appropriate tags |
| "Kinder" missing on children-only events | Kükenstube (childcare under-3), Garde groups | Add "Kinder" |

### 🟠 MEDIUM — Wrong location tag (should fix)
Location tag doesn't match the actual venue location.

| Pattern | Example | Suggested Fix |
|---------|---------|---------------|
| Wrong district tagged | "Blankenloch" for events at GrauBau (not in Blankenloch) | Verify address, correct location tag |
| Wrong municipality | "Neuthard" for Karlsdorf events | Correct to "Karlsdorf" |

### 🟡 MEDIUM — Missing obvious tag (should add)
Event clearly relates to a theme that isn't tagged.

| Pattern | Example | Suggested Fix |
|---------|---------|---------------|
| Missing "Kultur" | Korallengarde (dance group) has "Sport, Musik" but missing "Kultur" | Add "Kultur" |
| Missing "Kirche" | Church-organized events (Christvesper, Heiligabend) missing "Kirche" | Add "Kirche" |
| Missing "Senioren" | Senior-targeted events missing "Senioren" | Add "Senioren" |
| Under-tagged (0-1 theme tags) | Adventsfeier tagged only `Neuthard` (no theme tag) | Add appropriate theme tag |

### 🟢 LOW — Debatable tag (flag as questionable)
Tag is technically not wrong but somewhat misleading or debatable.

| Pattern | Example | Note |
|---------|---------|------|
| Borderline "Musik" | Eltern-Baby-Café tagged "Musik" — no music mentioned but might happen | Flag as questionable |
| Missing fringe tag | Event might tangentially relate to a theme | Flag as suggestion |

### ℹ️ INFO — Can't validate (note only)
Description is empty or too short to determine if tags are correct.

| Pattern | Example | Action |
|---------|---------|--------|
| Empty description | No `description` field or `< 15 chars` | Note as unverifiable |
| Minimal description | Only time/location info, no content | Note as unverifiable |

## Decision Flowchart

```
Does the event have a description?
  ├── No / Too short → ℹ️ Flag as "can't validate"
  └── Yes → 
       Are any tags factually wrong for the event?
        ├── Yes → 🔴 HIGH (wrong tag)
        └── No →
             Is the location tag wrong?
              ├── Yes → 🟠 MEDIUM (wrong location)
              └── No →
                   Is an obvious theme tag missing?
                    ├── Yes → 🟡 MEDIUM (missing tag)
                    └── No →
                         Is a tag debatable/questionable?
                          ├── Yes → 🟢 LOW (questionable)
                          └── No → ✅ No issues
```

## Reporting Format

For each flagged event, use this format:

**EVENT:** `<filename>.json`  
**TITLE:** `<event title>`  
**SEVERITY:** `🔴/🟠/🟡/🟢/ℹ️`  
**CURRENT TAGS:** `tag1, tag2, ...`  
**ISSUE:** `<what's wrong>`  
**SUGGESTION:** `<correct tags or action>`  

For recurring patterns (5+ events with same title and same issue), use a grouped report:

**PATTERN:** `<title pattern>`  
**SEVERITY:** `🔴/🟠/🟡/🟢/ℹ️`  
**AFFECTED FILES:** `<file1, file2, ... or count>`  
**CURRENT TAGS:** `tag1, tag2, ...`  
**ISSUE:** `<what's wrong>`  
**SUGGESTION:** `<correct tags or action>`  

## Quick Reference: Common Tag Meanings

| Tag | What it means | Should have when... |
|-----|---------------|---------------------|
| Sport | Physical activity, exercise, sports | Running, gymnastics, ball sports, dance training |
| Kultur | Arts, culture, performance | Dance groups, theatre, concerts, exhibitions |
| Fest | Festival, celebration | Parties, markets, seasonal events |
| Musik | Music-related | Choirs, concerts, instrument practice |
| Kinder | Children's event | Activities for children 0-16 |
| Treff | Social gathering, meetup | Parent groups, coffee mornings, clubs |
| Natur | Nature, outdoors | Hiking, gardening, nature walks, Pfadfinder |
| Kirche | Church-related | Services, bible study, church events |
| Bildung | Education, learning | Courses, workshops (actual), training |
| Senioren | Senior-focused | Events for elderly, senior meetups |
| Handwerk | Crafts, DIY | Workshops (actual crafting), repair cafes |
| Verein | Club/organization event | Any club-hosted event |
| Politik | Political/governmental | Council meetings, political events |
| Essen | Food-related | Markets, cooking, food festivals |
| Wohltätigkeit | Charity | Fundraisers, charity events |

## Notes
- Location tags (Blankenloch, Friedrichstal, Spöck, Büchig, Staffort, Neuthard, Karlsdorf, Graben, Neudorf, Eggenstein, Weingarten, etc.) should match the actual venue location, not the organizer's home base.
- Some events legitimately have multiple location tags (e.g., city-wide events).
- Recurring events should be checked individually — don't assume all instances of the same series share the same tag issues.
- **Multi-issue events:** An event can have issues at multiple levels. Report at the highest severity level but note all findings.
- **Bulk flagging heuristic:** If 5+ instances of the same titled event share the exact same tag pattern, flag them as a group with a bulk recommendation rather than listing each file individually.
