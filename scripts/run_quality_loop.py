#!/usr/bin/env python3
"""
Quality Loop — Orchestrates the quality judge + post-scrape feedback loop.

Called after scrape_and_merge completes, on the changed/added event files.

Usage:
  python3 scripts/run_quality_loop.py events/curated/*.json
  python3 scripts/run_quality_loop.py --files-from-git-diff

Process:
  1. Run quality judge on all input events
  2. If any fail, apply post_scrape rules
  3. Re-run quality judge on fixed events
  4. Loop until all pass or max iterations reached
  5. Print summary
"""

import json, os, sys, glob, subprocess, time
from pathlib import Path

SCRIPTS_DIR = os.path.dirname(os.path.abspath(__file__))
EVENTS_DIR = os.path.join(SCRIPTS_DIR, "..", "events", "curated")
MAX_ITERATIONS = 5


def load_events(filepaths):
    events = []
    for fp in filepaths:
        with open(fp) as f:
            e = json.load(f)
        e["_filepath"] = fp
        events.append(e)
    return events


def save_event(event):
    fp = event.get("_filepath")
    if not fp:
        return
    copy = {k: v for k, v in event.items() if k != "_filepath"}
    with open(fp, "w") as f:
        json.dump(copy, f, indent=2, ensure_ascii=False)
        f.write("\n")


def run_quality_judge(events, parallel=8):
    """Run the quality judge on events in parallel using ThreadPoolExecutor.
    Returns (passed, failed) lists. Events are judged in-place and saved to disk."""
    import importlib.util
    spec = importlib.util.spec_from_file_location("qj",
        os.path.join(SCRIPTS_DIR, "quality_judge.py"))
    qj = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(qj)

    print(f"  🧠 Judging {len(events)} events (parallel={parallel})...")
    passed, failed = qj.judge_events_parallel(events, max_workers=parallel)
    return passed, failed


def run_post_scrape(events):
    """Apply post-scrape rules to events, returns list of changed event titles."""
    import importlib.util
    spec = importlib.util.spec_from_file_location("ps",
        os.path.join(SCRIPTS_DIR, "post_scrape.py"))
    ps = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(ps)

    changed = []
    for event in events:
        rules_applied = ps.apply_all_rules(event)
        if rules_applied:
            title = event.get("title", "???")
            print(f"  ✏️  Fixed: {title[:50]} — {', '.join(rules_applied)}")
            changed.append(event)
    return changed


def get_git_diff_events(base_ref="origin/main"):
    """Get list of added/modified event files from git diff."""
    result = subprocess.run(
        ["git", "diff", "--name-only", "--diff-filter=AM", f"{base_ref}...HEAD",
         "--", f"{EVENTS_DIR}/*.json"],
        capture_output=True, text=True, check=False
    )
    files = [f.strip() for f in result.stdout.strip().split('\n') if f.strip()]
    return files


def main():
    import argparse
    parser = argparse.ArgumentParser(description="Quality loop orchestrator")
    parser.add_argument("files", nargs="*", help="Event JSON files to process")
    parser.add_argument("--files-from-git-diff", action="store_true",
                        help="Get changed files from git diff (origin/main...HEAD)")
    parser.add_argument("--base-ref", default="origin/main",
                        help="Base ref for git diff (default: origin/main)")
    parser.add_argument("--max-iterations", type=int, default=MAX_ITERATIONS)
    parser.add_argument("--parallel", type=int, default=8,
                        help="Number of parallel LLM calls (default: 8)")
    args = parser.parse_args()

    # Determine which files to process
    if args.files_from_git_diff:
        filepaths = get_git_diff_events(args.base_ref)
    elif args.files:
        filepaths = args.files
    else:
        print("Specify files or --files-from-git-diff")
        return 1

    if not filepaths:
        print("✅ No events to check.")
        return 0

    print(f"📋 Processing {len(filepaths)} events through quality loop...\n")

    events = load_events(filepaths)

    iteration = 0
    all_passed = []
    all_failed = events[:]
    loop_history = []

    while iteration < args.max_iterations and all_failed:
        iteration += 1
        print(f"\n{'='*60}")
        print(f"🔄 Iteration {iteration}")
        print(f"{'='*60}")

        # Judge current failed events (in parallel)
        passed, failed = run_quality_judge(all_failed, parallel=args.parallel)
        all_passed.extend(passed)
        all_failed = failed

        loop_history.append({
            "iteration": iteration,
            "passed": len(passed),
            "failed": len(failed),
        })

        if not all_failed:
            print(f"\n✅ All events passed!")
            break

        # Apply post-scrape rules to failed events
        print(f"\n🔧 Applying post-scrape rules to {len(all_failed)} failed events...")
        changed = run_post_scrape(all_failed)
        if not changed:
            print("  No rules could fix the remaining issues.")
            break
        print(f"  {len(changed)} events modified by rules.")

        # Re-judge will happen on next iteration

    # Save all events (also done incrementally during judging)
    for event in all_passed + all_failed:
        save_event(event)

    # Final summary
    print(f"\n{'='*60}")
    print(f"📊 QUALITY LOOP SUMMARY")
    print(f"{'='*60}")
    for h in loop_history:
        print(f"  Iteration {h['iteration']}: {h['passed']} passed, {h['failed']} failed")
    print(f"\n  Total: {len(all_passed)} passed, {len(all_failed)} failed")
    if all_failed:
        print(f"\n❌ Events still failing:")
        for e in all_failed:
            q = e.get("_quality", {})
            print(f"  • {e.get('title', '???')} ({q.get('overall_score', 0):.2f}) — {q.get('summary', '')[:100]}")
    else:
        print(f"\n✅ All events passed quality check!")

    return 0 if not all_failed else 1


if __name__ == "__main__":
    sys.exit(main())
