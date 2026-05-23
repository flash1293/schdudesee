#!/usr/bin/env python3
"""
Quality Judge — LLM-based event quality evaluation.

Evaluates events across multiple axes using a low-cost model via OpenRouter.
Adds a _quality field to event JSONs with structured judgments.

Usage:
  python3 scripts/quality_judge.py events/curated/*.json
  python3 scripts/quality_judge.py --rerun-failed events/curated/*.json
  python3 scripts/quality_judge.py --check-all events/curated/*.json

Output:
  Each event file gets a _quality field added in-place.
  Prints a summary of passed/failed events to stdout.
"""

import json, os, sys, glob, time, re
from urllib.request import Request, urlopen
from urllib.error import URLError

OPENROUTER_API_KEY = os.environ.get("OPENROUTER_API_KEY")
if not OPENROUTER_API_KEY:
    print("❌ OPENROUTER_API_KEY environment variable not set", file=sys.stderr)
    sys.exit(1)
MODEL = "stepfun/step-3.5-flash"  # step-fash 3.5 via OpenRouter
API_URL = "https://openrouter.ai/api/v1/chat/completions"
MAX_RETRIES = 3
RETRY_DELAY = 2

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

Rate each axis 0.0-1.0 and list specific issues:
- title_quality: Is the title clear, descriptive and meaningful?
- location_extraction: Is the location properly extracted (not empty)?
- time_extraction: Is a time/start time present and properly extracted?
- description_quality: Is the description informative and helpful?
- tag_quality: Are the tags appropriate and accurate?
- duplicate_risk: Is this event a likely duplicate of another event in the context?

Return ONLY valid JSON (no markdown, no explanations) with this exact structure:
{{"judgments":{{"title_quality":{{"score":0.9,"issues":[]}},"location_extraction":{{"score":0.5,"issues":["issue"]}},"time_extraction":{{"score":0.8,"issues":[]}},"description_quality":{{"score":0.7,"issues":[]}},"tag_quality":{{"score":0.6,"issues":["issue"]}},"duplicate_risk":{{"score":1.0,"issues":[]}}}},"overall_score":0.75,"passed":true,"summary":"Brief summary"}}"""


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
                and e.get("title") != event.get("title")):
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
    context_str = json.dumps(context_events, indent=2, ensure_ascii=False) if context_events else "None"
    event_json = json.dumps(event, indent=2, ensure_ascii=False)

    prompt = EVALUATION_PROMPT_TEMPLATE.format(event_json=event_json, context_json=context_str)

    body = json.dumps({
        "model": MODEL,
        "messages": [
            {"role": "user", "content": prompt}
        ],
        "temperature": 0.01,  # low temp to reduce rambling
        "max_tokens": 8192,  # need room for reasoning + content
    }).encode()

    headers = {
        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
        "Content-Type": "application/json",
        "HTTP-Referer": "https://github.com/flash1293/schdudesee",
    }

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

    event["_quality"] = {
        "judgments": judgment.get("judgments", {}),
        "overall_score": judgment.get("overall_score", 0.0),
        "passed": judgment.get("passed", False),
        "summary": judgment.get("summary", ""),
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


def main():
    import argparse
    parser = argparse.ArgumentParser(description="Quality judge for events")
    parser.add_argument("files", nargs="*", help="Event JSON files to judge")
    parser.add_argument("--rerun-failed", action="store_true",
                        help="Only re-judge events that have a _quality.passed == false")
    parser.add_argument("--check-all", action="store_true",
                        help="Check all events in curated dir")
    parser.add_argument("--max-events", type=int, default=0,
                        help="Limit number of events to process (0 = all)")
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

    print(f"🧠 Judging {len(events)} events...")

    passed = []
    failed = []

    for i, event in enumerate(events, 1):
        title = event.get("title", "???")
        print(f"  [{i}/{len(events)}] {title[:50]}...", end=" ", flush=True)
        try:
            judged = judge_event(event, events)
            save_event(judged)
            if judged["_quality"]["passed"]:
                score = judged["_quality"]["overall_score"]
                print(f"✅ ({score:.2f})")
                passed.append(judged)
            else:
                score = judged["_quality"]["overall_score"]
                summary = judged["_quality"]["summary"][:80]
                print(f"❌ ({score:.2f}) {summary}")
                failed.append(judged)
        except Exception as e:
            print(f"⚠️ Error: {e}")
            event["_quality"] = {
                "judgments": {},
                "overall_score": 0.0,
                "passed": False,
                "summary": f"Error during judgment: {str(e)}"
            }
            save_event(event)
            failed.append(event)

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
