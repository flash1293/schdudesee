#!/usr/bin/env python3
"""
Quality Judge — LLM-based event quality evaluation.

Evaluates events across multiple axes using a cheap/fast model.
Adds a _quality field to event JSONs with structured judgments.

Default model: deepseek-v4-flash (cheap ~$0.000015/call).
Override via MODEL env var, API via OPENROUTER_API_KEY or LLM_API_KEY.

Usage:
  python3 scripts/quality_judge.py events/curated/*.json
  python3 scripts/quality_judge.py --rerun-failed events/curated/*.json
  python3 scripts/quality_judge.py --check-all events/curated/*.json

Output:
  Each event file gets a _quality field added in-place.
  Prints a summary of passed/failed events to stdout.
"""

import json, os, sys, glob, time, re
from concurrent.futures import ThreadPoolExecutor, as_completed
from urllib.request import Request, urlopen
from urllib.error import URLError

# API configuration — supports OpenRouter (primary) and OpenAI-compatible (fallback)
OPENROUTER_API_KEY = os.environ.get("OPENROUTER_API_KEY")
LLM_API_KEY = os.environ.get("LLM_API_KEY") or OPENROUTER_API_KEY
LLM_BASE_URL = os.environ.get("LLM_BASE_URL", "https://openrouter.ai/api/v1")

# Use deepseek-v4-flash as default — cheap and fast. Override via MODEL env var.
MODEL = os.environ.get("MODEL", "deepseek-v4-flash")
API_URL = f"{LLM_BASE_URL.rstrip('/')}/chat/completions"

if not OPENROUTER_API_KEY and not LLM_API_KEY:
    print("❌ No API key found. Set OPENROUTER_API_KEY or LLM_API_KEY.", file=sys.stderr)
    sys.exit(1)

MAX_RETRIES = 3
RETRY_DELAY = 2

# Minimum quality score for an event to be considered passing.
# Override via QUALITY_MIN_SCORE env var.
MIN_QUALITY_SCORE = float(os.environ.get("QUALITY_MIN_SCORE", "0.6"))

EVENTS_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "events/curated")

# Quality criteria / axes
AXES = [
    "title_quality",
    "location_extraction",
    "time_extraction",
    "description_quality",
    "tag_quality",
    "duplicate_risk",
]

AXIS_DESCRIPTIONS = {
    "title_quality": "Is the title clear, descriptive and meaningful? (not too short, not generic)",
    "location_extraction": "Is the location properly extracted and not empty/missing? Is it specific enough?",
    "time_extraction": "Is a time/start time present and properly extracted?",
    "description_quality": "Is the description informative and helpful? Is it empty or too short?",
    "tag_quality": "Are the tags appropriate and accurate for this event? Are any missing or wrong?",
    "duplicate_risk": "Is this event likely a duplicate of another event on the same date in the same district?",
}

EVALUATION_PROMPT_TEMPLATE = """Evaluate this event entry for quality:

{event_json}

Context - other events in same district on same date:
{context_json}

Available event categories (tags): {available_tags}

Available districts: {available_districts}

Rate each axis 0.0-1.0 and list specific issues:
- title_quality: Is the title clear, descriptive and meaningful?
- location_extraction: Is the location properly extracted (not empty)?
- time_extraction: Is a time/start time present and properly extracted?
- description_quality: Is the description informative and helpful?
- tag_quality: Are the tags appropriate and accurate? Consider the available categories and districts above. The LAST tag should be a district.
- duplicate_risk: Is this event a likely duplicate of another event in the context?

Return ONLY valid JSON (no markdown, no explanations) with this exact structure:
{{"judgments":{{"title_quality":{{"score":0.9,"issues":[]}},"location_extraction":{{"score":0.5,"issues":["issue"]}},"time_extraction":{{"score":0.8,"issues":[]}},"description_quality":{{"score":0.7,"issues":[]}},"tag_quality":{{"score":0.6,"issues":["issue"]}},"duplicate_risk":{{"score":1.0,"issues":[]}}}},"overall_score":0.75,"passed":true,"summary":"Brief summary"}}"""

# Canonical lists for tag_quality evaluation
AVAILABLE_TAGS = [
    "Bildung", "Digital", "Essen", "Fest", "Handwerk", "Kinder", "Kirche",
    "Kultur", "Literatur", "Markt", "Musik", "Natur", "Politik", "Senioren",
    "Sonstiges", "Sport", "Stadtleben", "Treff", "Verein", "Wohltätigkeit",
    "Workshop", "Ausstellungen",
]

AVAILABLE_DISTRICTS = [
    "Blankenloch", "Bruchsal", "Büchenau", "Büchig", "Eggenstein",
    "Friedrichstal", "Graben-Neudorf", "Hagsfeld", "Leopoldshafen",
    "Linkenheim", "Neureut", "Neuthard", "Rintheim", "Spöck",
    "Staffort", "Waldstadt", "Weingarten",
]


def load_events(filepaths=None):
    """Load event JSONs from file paths or all events in curated dir."""
    if not filepaths:
        filepaths = sorted(glob.glob(os.path.join(EVENTS_DIR, "*.json")))
    events = []
    for fp in filepaths:
        with open(fp) as f:
            e = json.load(f)
        e["_filepath"] = fp
        events.append(e)
    return events


def get_context_events(event, all_events):
    """Get other events in the same district on the same date for context.
    Uses the last tag as the district."""
    tags = event.get("tags", [])
    district = tags[-1] if tags else "unknown"
    date = event.get("date_start", "")
    same = []
    for e in all_events:
        e_tags = e.get("tags", [])
        e_district = e_tags[-1] if e_tags else "unknown"
        if (e_district == district and e.get("date_start") == date
                and e.get("_filepath") != event.get("_filepath")):
            same.append({
                "title": e.get("title", ""),
                "time_raw": e.get("time_raw", ""),
                "location": e.get("location", ""),
                "organizer": e.get("organizer", ""),
                "tags": e.get("tags", []),
            })
    return same


def call_llm(event, context_events):
    """Call OpenRouter step-fash 3.5 to judge an event."""
    # Strip internal metadata before sending to LLM
    sanitized_event = {k: v for k, v in event.items() if not k.startswith("_")}
    sanitized_context = []
    for ce in context_events:
        sanitized_context.append({k: v for k, v in ce.items() if not k.startswith("_")})
    context_str = json.dumps(sanitized_context, indent=2, ensure_ascii=False) if sanitized_context else "None"
    event_json = json.dumps(sanitized_event, indent=2, ensure_ascii=False)

    available_tags_str = ", ".join(sorted(AVAILABLE_TAGS))
    available_districts_str = ", ".join(sorted(AVAILABLE_DISTRICTS))

    prompt = EVALUATION_PROMPT_TEMPLATE.format(
        event_json=event_json, context_json=context_str,
        available_tags=available_tags_str, available_districts=available_districts_str,
    )

    body = json.dumps({
        "model": MODEL,
        "messages": [
            {"role": "user", "content": prompt}
        ],
        "temperature": 0.01,  # low temp to reduce rambling
        "max_tokens": 8192,  # need room for reasoning + content
    }).encode()

    api_key = OPENROUTER_API_KEY or LLM_API_KEY
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
        "User-Agent": "YEAP-QualityJudge/1.0",
    }
    if OPENROUTER_API_KEY:
        headers["HTTP-Referer"] = "https://github.com/flash1293/schdudesee"

    for attempt in range(MAX_RETRIES):
        try:
            req = Request(API_URL, data=body, headers=headers, method="POST")
            with urlopen(req, timeout=120) as resp:
                data = json.loads(resp.read())
            content = data["choices"][0]["message"]["content"]
            if not content or not content.strip():
                raise ValueError("Empty response from LLM")
            content = content.strip()
            # Handle markdown code block wrapping
            if "```" in content:
                content = content.split("```")[1]
                if content.startswith("json"):
                    content = content[4:]
                content = content.strip()
            return json.loads(content)
        except Exception as e:
            if attempt < MAX_RETRIES - 1:
                time.sleep(RETRY_DELAY)
            else:
                return {
                    "judgments": {ax: {"score": 0.5, "issues": [f"LLM call failed: {str(e)}"]}
                                  for ax in AXES},
                    "overall_score": 0.0,
                    "passed": False,
                    "summary": f"Quality judgment failed: {str(e)}"
                }


def judge_event(event, all_events):
    """Judge a single event and return it with _quality field added."""
    context = get_context_events(event, all_events)
    if "_quality" in event:
        del event["_quality"]  # clear previous judgment

    judgment = call_llm(event, context)

    # Normalize types — model may return strings
    def as_float(v, default=0.0):
        try:
            return float(v)
        except (TypeError, ValueError):
            return default

    event["_quality"] = {
        "judgments": judgment.get("judgments", {}),
        "overall_score": as_float(judgment.get("overall_score")),
        "passed": as_float(judgment.get("overall_score")) >= MIN_QUALITY_SCORE,
        "summary": str(judgment.get("summary", "")),
    }
    return event


def save_event(event):
    """Save the event JSON back to file, restoring _filepath after."""
    fp = event.get("_filepath")
    if not fp:
        raise ValueError("Event has no _filepath")
    # Save without the internal field
    event_copy = {k: v for k, v in event.items() if k != "_filepath"}
    with open(fp, "w") as f:
        json.dump(event_copy, f, indent=2, ensure_ascii=False)
        f.write("\n")


def judge_events_parallel(events, max_workers=8):
    """Judge all events in parallel using ThreadPoolExecutor.
    Returns (passed, failed) lists. Events are judged in-place and saved to disk."""
    from concurrent.futures import ThreadPoolExecutor, as_completed

    passed = []
    failed = []
    completed = 0
    total = len(events)

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        future_to_event = {
            executor.submit(judge_event, event, events): event
            for event in events
        }

        for future in as_completed(future_to_event):
            event = future_to_event[future]
            title = event.get("title", "???")
            completed += 1
            try:
                judged = future.result()
                save_event(judged)
                if judged["_quality"]["passed"]:
                    score = judged["_quality"]["overall_score"]
                    print(f"  [{completed}/{total}] ✅ {title[:50]} ({score:.2f})")
                    passed.append(judged)
                else:
                    score = judged["_quality"]["overall_score"]
                    summary = judged["_quality"]["summary"][:80]
                    print(f"  [{completed}/{total}] ❌ {title[:50]} ({score:.2f}) {summary}")
                    failed.append(judged)
            except Exception as e:
                print(f"  [{completed}/{total}] ⚠️ {title[:50]} — {e}")
                event["_quality"] = {
                    "judgments": {},
                    "overall_score": 0.0,
                    "passed": False,
                    "summary": f"Error during judgment: {str(e)}"
                }
                save_event(event)
                failed.append(event)

    return passed, failed


def main():
    """CLI entry point for quality judgment.
    Parses args, loads events, and runs parallel judging.
    Returns 0 if all pass, 1 if any fail."""
    import argparse

    parser = argparse.ArgumentParser(description="Quality judge for events")
    parser.add_argument("files", nargs="*", help="Event JSON files to judge")
    parser.add_argument("--rerun-failed", action="store_true",
                        help="Only re-judge events that have a _quality.passed == false")
    parser.add_argument("--check-all", action="store_true",
                        help="Check all events in curated dir")
    parser.add_argument("--max-events", type=int, default=0,
                        help="Limit number of events to process (0 = all)")
    parser.add_argument("--parallel", type=int, default=8,
                        help="Number of parallel LLM calls (default: 8)")
    args = parser.parse_args()

    if args.files:
        filepaths = args.files
    elif args.check_all:
        filepaths = sorted(glob.glob(os.path.join(EVENTS_DIR, "*.json")))
    else:
        filepaths = sorted(glob.glob(os.path.join(EVENTS_DIR, "*.json")))

    events = load_events(filepaths)

    if args.rerun_failed:
        events = [e for e in events
                  if e.get("_quality", {}).get("passed") == False]

    if args.max_events > 0:
        events = events[:args.max_events]

    if not events:
        print("✅ No events to judge.")
        return

    print(f"🧠 Judging {len(events)} events (parallel={args.parallel})...")
    passed, failed = judge_events_parallel(events, max_workers=args.parallel)

    print(f"\n{'='*50}")
    print(f"📊 Results: {len(passed)} passed, {len(failed)} failed out of {len(events)}")
    if failed:
        print(f"\n❌ Failed events:")
        for e in failed:
            q = e.get("_quality", {})
            print(f"  • {e.get('title', '???')} — {q.get('summary', '')[:100]}")
    print(f"{'='*50}")

    return 0 if not failed else 1


if __name__ == "__main__":
    sys.exit(main())
