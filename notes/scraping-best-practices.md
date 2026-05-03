# Scraping Best Practices

Lessons learned from the Stutensee events pipeline — a practical guide for building reliable scrapers.

## 1. Validate URL Parameters Actually Work

Before relying on any URL parameter, **verify it modifies the response**.

**The Bruchsal lesson:** The monthly calendar URL `?month=YYYY-MM` appeared to work (returned HTTP 200), but the parameter was silently ignored — the same events were returned regardless of the month value. This was only caught when we compared the RSS feed (5 events) against the actual monthly view (24+ events).

**Checklist:**
- Fetch the URL with at least two different parameter values and compare response length/event count
- If the responses are identical, the parameter is probably ignored
- Test edge cases: `?month=2026-01` vs `?month=2026-06` vs `?month=BADVALUE`
- For date parameters, verify events returned actually fall within the requested range

## 2. Handle Pagination Properly

**Common patterns and how to test them:**

| Pattern | Detection | Verification |
|---------|-----------|-------------|
| Query param (`?page=N`) | Page 1 and page 2 should return different content | Compare event IDs or titles |
| Path segment (`/seite-2/`) | Common in TYPO3 sites | Check for `a[title='Letzte Seite']` or `button[disabled]` |
| Infinite scroll / JS-loaded | Not scrapable via simple HTTP | Mark as requires headless browser or skip |
| Calendar month views (`?month=YYYY-MM`) | Iterate months forward/backward | Verify events per month differ |

**Key rules:**
- Always fetch page 1, 2, and the last page to verify pagination works
- If page 1 and page 2 return identical content, the pagination mechanism is broken or misunderstood
- Set a maximum page limit (e.g., 100) to prevent infinite loops
- Detect pagination end by: empty result set, 404, missing "next" link, or server returning a non-200 status

## 3. Verify HTML Selectors Against the Live DOM

Don't assume selectors from one CMS pattern apply to another — verify on the actual target.

**Verification protocol:**
1. Fetch the raw HTML from the live URL (use `curl` or Python `requests`)
2. Parse with BeautifulSoup and test each selector
3. Check: does `soup.select_one(".hw_record__title span")` return the title?
4. Check: what happens when a field is missing (e.g., no location, no time)?
5. Print the first 3 matched elements to confirm data quality

**Common pitfalls:**
- CSS classes may differ between sites using the same CMS (e.g., TYPO3 hwveranstaltung can have per-site theming)
- Elements might be commented out or conditionally rendered
- JavaScript-rendered content won't appear in HTTP response — check the raw HTML first

## 4. Error Handling for Site Changes

Sites change. Build scrapers that fail gracefully.

**Defensive patterns:**
```python
# Guard against missing elements
title_el = soup.select_one(".hw_record__title span")
if not title_el:
    print(f"  WARNING: Title element not found on page {page}")
    continue  # or break, depending on severity

# Guard against parse errors
date_start = None
try:
    date_text = date_el.get_text(strip=True)
    date_start = parse_german_date(date_text)
except (AttributeError, ValueError):
    print(f"  WARNING: Could not parse date from '{date_text}'")
```

**Log levels:**
- Missing optional fields (time, location): log warning, continue with `None`
- Missing required fields (title, date): log error, skip event
- Missing all events on page: log warning, check if site structure changed
- HTTP error (timeout, 500): log error, retry once, then break

## 5. Testing Approach

### Pre-commit verification
Run the scraper against a single source before integrating:

```bash
# Add --sources flag to run_pipeline.py
python3 run_pipeline.py --sources "Bruchsal"
```

Expected output:
- Source URL printed
- Number of events fetched and inserted
- Any errors or warnings

### Pre-deployment check
Before deploying to production, verify:
1. **Event count is reasonable** — not 0 (broken selector) and not 10,000x normal (pagination bug)
2. **Date range makes sense** — events span expected future dates, not all on the same day
3. **Titles are clean** — no HTML tags, no encoding issues
4. **Dedup rate is sane** — if 95% of events got deduped, check if source URL is correct
5. **District tag applied** — verify in local DB: `SELECT COUNT(*) FROM curated_events WHERE tags LIKE '%Bruchsal%'`

### Monitoring (post-deploy)
- Compare event counts across pipeline runs
- Alert if a source returns 0 events twice in a row (site likely changed)
- Periodically re-verify selectors (sites may update their templates)

## 6. SSL and Connectivity Issues

Our container may have SSL verification issues (e.g., bruchsal.de SSL cert not trusted). Don't assume a site is down — it may be a local connectivity problem.

**Diagnostic steps:**
```python
# Try with SSL verification disabled
import requests
resp = requests.get(url, verify=False, timeout=10)

# From command line
curl -sk https://example.com  # -k skips SSL verification
```

**If the site is only accessible via GH Actions (different IP):**
- Build and test the scraper locally using `--sources` flag
- Test the full pipeline on GH Actions before cutting over
- The SSL cert issue is often container-specific

## 7. Date/Time Parsing

German date formats are common in our sources:

| Format | Example | Parser |
|--------|---------|--------|
| `DD.MM.YYYY` | `03.05.2026` | `datetime.strptime(d, "%d.%m.%Y")` |
| `DD.MM.YY` | `03.05.26` | `re` + manual year handling |
| `Sonntag, 03.05.2026` | with weekday prefix | Strip prefix, then parse DD.MM.YYYY |
| `09.05.2026 bis 10.05.2026` | date range | Extract start and end |
| `14:00 Uhr` or `14:00 Uhr bis 17:00 Uhr` | time | `re` for optional end time |

**Rule:** Always parse to ISO format (`YYYY-MM-DD`) before inserting into the DB.

## 8. Duplicate Detection Strategy

Our pipeline dedup uses: `(source_url, event_url, date_start, title)` as a uniqueness constraint.

**Implications:**
- If `event_url` is always empty, dedup falls back to title+date — not reliable
- Always capture the full detail URL if available
- For RSS feeds, use `<guid>` or `<link>` as the event URL
- For calendar listings without detail pages, use a hash of `title + date + location`

## 9. Common Pitfalls Quick Reference

| Symptom | Likely Cause | Fix |
|---------|-------------|-----|
| 0 events fetched | Selector wrong or page structure changed | Re-verify selectors on live HTML |
| 5 events instead of 200 | Only RSS/API feed used; missing HTML iteration | Add monthly calendar or pagination |
| All events on same date | `?month=` parameter ignored | Test parameter affects output |
| Duplicate events across runs | No reliable `event_url` or dedup key | Ensure unique identifier per event |
| Encoding errors | German characters (ö, ä, ü, ß) in HTML | Use `resp.encoding = 'utf-8'` or `'latin-1'` |
| 404/connection errors | URL changed or site restructured | Check for site relaunch (CMS migration) |
| Events not tagged | `tag_untagged()` skips already-merged events | Run `retag_districts.py` after pipeline |

## 10. CMS-Specific Notes

| CMS | Known Sites | Key Selectors | Gotchas |
|-----|------------|--------------|---------|
| **TYPO3 hwveranstaltung** | weingarten-baden.de, graben-neudorf.de | `.hwveranstaltung__record`, `.hw_record__title span` | Class names confirmed per-site |
| **dvv-Mastertemplates** | bruchsal.de | `a.titel[href*='zmdetail']`, RSS feed at `/zmrss/` | `?month=` parameter may be ignored; prefer RSS or HTML iteration |
| **WordPress (Simple Calendar)** | musikverein-weingarten.de | `li.simcal-event`, `.simcal-event-title` | Google Calendar events are JS-rendered; Simple Calendar provides server-rendered fallback |
| **ECICS** | karlsdorf-neuthard.de, cvjm-weingarten.de | `div.ec-item-box`, `h2.ec-title`, `.d1`, `.d2` | Date/time in separate spans; pagination via `a.next` |
| **WordPress (custom posts)** | linkenheim-hochstetten.de | `.post-title a`, `.date-time` | Paginated listing; detail pages for full description |

---

*Document maintained by Lupe (Researcher). Updated 2026-05-03 based on first-cycle scraper implementations.*
