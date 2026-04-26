#!/usr/bin/env python3
"""Re-tag chunk_005.json — ONE content tag mostly, max 2, no Treff/Verein overuse."""
import json, re

DISTRICT_TAGS = {'Blankenloch', 'Büchig', 'Friedrichstal', 'Spöck', 'Staffort'}

def n(text):
    if not text:
        return ''
    t = text.lower()
    t = re.sub(r'&#[0-9]+;', ' ', t)
    t = re.sub(r'&[a-z]+;', ' ', t)
    t = re.sub(r'[•–—→»«""''\u2013\u2014\u2019\u201c\u201d,\\.!?():/+–-]', ' ', t)
    t = re.sub(r'\s+', ' ', t).strip()
    return t

def age_range_raw(title):
    """Check age range pattern in raw (unnormalized) title."""
    if not title:
        return False
    t = title.lower()
    t = re.sub(r'&#[0-9]+;|&[a-z]+;', ' ', t)
    return bool(re.search(r'\b\d+\s*[-–]\s*\d+\s*jahre', t))

def tag_event(event):
    raw_title = event.get('title', '')
    title = n(raw_title)
    desc = n(event.get('description', ''))
    org  = n(event.get('organizer', ''))
    txt  = f'{title} {desc} {org}'
    existing = [t.strip() for t in event.get('tags', '').split(',') if t.strip()]
    districts = [t for t in existing if t in DISTRICT_TAGS]

    # Age-range pattern like "(10-14 Jahre)" or "(3–6 Jahre)" is a strong signal
    has_age_range = age_range_raw(raw_title)

    # Strong signals
    church_org = bool(re.search(r'(kirchengemeinde|ev\b|michaelisgemeinde|pfarr|kirche)', org))
    is_church_service = bool(re.search(r'\b(gottesdienst|andacht|segen|konfirmation|tauf|ökumenisch|taizé|glaubenskurs|christenlehre|familiengottesdienst)\b', txt))

    is_karneval_club = 'karneval' in org or 'piraten' in org

    # --- Primary tag selection (priority order) ---

    tag = None

    # 1. Kirche (only for actual services/religious events, not kid groups hosted by church)
    if is_church_service:
        tag = 'Kirche'

    # 2. Fest (festivals, carnival celebrations, parties)
    if not tag and re.search(r'\b(fest\b|feier\b|party\b|karneval|fasching|prunksitzung|gaudiwurm|bunter abend|sommerfest|maifest|weihnachtsfeier|jahresabschlussfeier)\b', txt):
        tag = 'Fest'

    # 3. Markt
    if not tag and re.search(r'\b(flohmarkt|trödel\b|adventsbasar|weihnachtsmarkt|kleiderbasar)\b', txt):
        tag = 'Markt'

    # 4. Sport (dance/garde training, sports training, chess, gymnastics)
    if not tag and re.search(r'\b(training|trainier|choreografi|tanzschritt|sport\b|tanz(en|training)?|turnen|gymnastik|schach|bewegung|fitness|karate|judo|kinderturnen|kindersport)\b', txt):
        tag = 'Sport'

    # 5. Kinder (children/youth events — match in title/org strongly, desc if clearly kid-focused)
    kid_title = f'{title} {org}'
    if not tag:
        if re.search(r'\b(krabbelgruppe|kükenstube|baby|eltern.*kind|jugendrotkreuz|pfadfinder|wölfling|jugendrotkreuz|wölfling|jugend|teens?\b|mädchen(?![^ ]))\b', kid_title):
            tag = 'Kinder'
        elif has_age_range:
            tag = 'Kinder'
        elif re.search(r'\bkinder\b', kid_title):
            tag = 'Kinder'
        elif re.search(r'\bmodellbahn\b', kid_title):
            tag = 'Kinder'

    # 6. Musik (choir, band, orchestra, singing as main activity)
    music_strong = re.search(r'\b(chor\b|musikverein|orchester|bläser|posaunenchor|gesangverein|sängerbund|konzert|chorprobe)\b', txt)
    music_normal = re.search(r'\b(musik|sing[ea]n|gesang|band\b|gitarre|flöte|geige|klavier)\b', txt)
    if not tag and (music_strong or (music_normal and not is_karneval_club and not has_age_range)):
        tag = 'Musik'

    # 7. Bildung
    if not tag and re.search(r'\b(vortrag|fortbildung|seminar|erste.*hilfe|selbsthilfegruppe|infoabend|referen|bildung)\b', txt):
        tag = 'Bildung'

    # 8. Wohltätigkeit (charity, refugee help, DRK, social work)
    if not tag and re.search(r'\b(flüchtling|integration|tee.*spielstube|spende|helf|\bdrk\b|obdachlosen|sozial|hilfe\b|danksagung)\b', txt):
        tag = 'Wohltätigkeit'

    # 9. Natur
    if not tag and re.search(r'\b(wanderung|natur|garten\b|wald\b|exkursion|radtour|fahrradtour)\b', txt):
        tag = 'Natur'

    # 10. Senioren
    if not tag and re.search(r'\b(senior|oldie|rentner|egem|altentreff|gedächtnistraining|sturzprophylaxe)\b', txt):
        tag = 'Senioren'

    # 11. Digital
    if not tag and re.search(r'\b(digital|computer|handy\b|smartphone|edv\b|medienkompetenz|programmier)\b', txt):
        tag = 'Digital'

    # 12. Handwerk
    if not tag and re.search(r'\b(töpfern|töpferei|nähkurs|nähen|stricken|häkeln|heimwerken|reparatur\b|modellbau)\b', txt):
        tag = 'Handwerk'

    # 13. Essen
    if not tag and re.search(r'\b(kochen\b|backen\b|frühstück|brunch|kochkurs|grillen\b|kaffee.*kuchen|kulinarisch)\b', txt):
        tag = 'Essen'

    # 14. Kultur (theatre, exhibitions, art, museum, creative workshops without age range)
    if not tag and re.search(r'\b(ausstellung|vernissage|theater|bühne|kunst\b|kino\b|film\b|literatur|lesung|museum|geschichte|fotografie|kabarett|kreativ|malen|basteln|gestalten|bücherei|bibliothek|vorlesen)\b', txt):
        tag = 'Kultur'

    # 15. Politik
    if not tag and re.search(r'\b(politik|partei|wahl\b|gemeinderat|stadtrat|bürgerversammlung|ortsbeirat)\b', txt):
        tag = 'Politik'

    # 16. Treff/gesellig (low priority)
    if not tag and re.search(r'\b(stammtisch|spiele.*(nachmittag|abend|treff)|spieleabend|offener treff|kaffeeklatsch|gesellig)\b', txt):
        tag = 'Treff'

    # 17. Verein (meetings, assemblies)
    if not tag and re.search(r'\b(jahreshauptversammlung|mitgliederversammlung|vorstandssitzung)\b', txt):
        tag = 'Verein'

    # 18. Fallback — scan for anything meaningful
    if not tag:
        if church_org:
            tag = 'Kirche'
        elif 'kreativ' in txt or re.search(r'\b(spiel|bastel)\b', txt):
            tag = 'Kultur'
        else:
            tag = 'Sonstiges'

    # --- Maybe add a second tag (rarely — only clear, strong secondary theme) ---
    secondary = None

    if tag not in ('Fest', 'Markt') and re.search(r'\b(karneval|prunksitzung|gaudiwurm|bunter abend)\b', txt):
        secondary = 'Fest'
    elif tag == 'Kinder' and re.search(r'\b(sport|training|turnen|tanz)\b', txt):
        secondary = 'Sport'
    elif tag == 'Kinder' and music_strong:
        secondary = 'Musik'
    elif tag == 'Sport' and has_age_range:
        secondary = 'Kinder'

    # Block nonsense pairs
    if secondary and {tag, secondary} in [{'Kirche', 'Kinder'}, {'Kirche', 'Fest'}, {'Fest', 'Markt'}]:
        secondary = None

    result_tags = [tag]
    if secondary:
        result_tags.append(secondary)
    result_tags += districts
    return ','.join(result_tags)


def main():
    with open('/Users/joereuter/Clones/schdudesee/retag_batches/chunk_005.json', 'r') as f:
        data = json.load(f)

    results = {"errors": [], "results": {}}
    for event in data:
        eid = event.get('id')
        if not eid:
            results["errors"].append(f"Missing id for event: {event.get('title','?')}")
            continue
        try:
            results["results"][str(eid)] = tag_event(event)
        except Exception as e:
            results["errors"].append(f"Error processing event {eid}: {e}")

    with open('/Users/joereuter/Clones/schdudesee/retag_batches/results_005.json', 'w') as f:
        json.dump(results, f, ensure_ascii=False, indent=2)

    total = len(data)
    ok = len(results["results"])
    err = len(results["errors"])
    print(f"Processed {total} events: {ok} ok, {err} errors")

    single = double = 0
    tag_counts = {}
    for v in results["results"].values():
        parts = [t.strip() for t in v.split(',') if t.strip()]
        content = [t for t in parts if t not in DISTRICT_TAGS]
        if len(content) == 1: single += 1
        elif len(content) >= 2: double += 1
        for t in content:
            tag_counts[t] = tag_counts.get(t, 0) + 1

    print(f"\nSingle content tag: {single}")
    print(f"Double content tag: {double}")
    print("\nContent tag distribution:")
    for tag, count in sorted(tag_counts.items(), key=lambda x: -x[1]):
        print(f"  {tag}: {count}")

    # Sample results
    all_items = list(results["results"].items())
    print("\nSample (first 10):")
    for eid, tags in all_items[:10]:
        print(f"  {eid}: {tags}")
    print("\nSonstiges check:")
    sonst = [(eid, tags) for eid, tags in all_items if 'Sonstiges' in tags]
    for eid, tags in sonst[:5]:
        ev = next(e for e in data if str(e['id']) == eid)
        print(f"  {eid}: {tags}  ({ev['title'][:60]})")
    print(f"  ... total Sonstiges: {len(sonst)}")

if __name__ == '__main__':
    main()
