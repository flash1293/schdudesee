#!/usr/bin/env python3
"""Re-tag all curated event JSONs using current auto_tag() logic from scrape_and_merge.py, without re-scraping.

This imports auto_tag() directly from scrape_and_merge.py, so any changes to the
tagging logic are automatically picked up.
"""
import json, sys, os, glob

# Import auto_tag from the main pipeline module
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from scrape_and_merge import auto_tag


def retag_all():
    out_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "events/curated")
    files = sorted(glob.glob(os.path.join(out_dir, "*.json")))
    print(f"Found {len(files)} curated event JSONs", flush=True)
    
    updated = 0
    unchanged = 0
    for fpath in files:
        with open(fpath, "r") as f:
            ev = json.load(f)
        
        old_tags = list(ev.get("tags", []))
        
        # Re-tag using updated auto_tag logic (replace entirely)
        new_auto_tags = auto_tag(
            ev.get("title", ""),
            ev.get("description", ""),
            ev.get("location", ""),
            ev.get("organizer", "")
        )
        
        ev["tags"] = new_auto_tags
        
        if ev["tags"] != old_tags:
            with open(fpath, "w") as f:
                json.dump(ev, f, ensure_ascii=False, indent=2)
                f.write("\n")
            updated += 1
        else:
            unchanged += 1
    
    print(f"Updated {updated} / {len(files)} files ({unchanged} unchanged)", flush=True)


if __name__ == "__main__":
    retag_all()
