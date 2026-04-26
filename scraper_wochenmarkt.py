def scrape_wochenmarkt():
    """Weekly markets in Stutensee: Wednesday Friedrichstal, Saturday Blankenloch."""
    from datetime import datetime, timedelta
    events = []
    today = datetime.now()
    # Generate next 26 weeks of market dates
    for week_offset in range(26):
        # Wednesday: Friedrichstal 14:00-18:00
        wed = today + timedelta(days=(2 - today.weekday()) % 7 + week_offset * 7)
        events.append({
            "title": "Wochenmarkt Friedrichstal",
            "date_start": wed.strftime("%Y-%m-%d"),
            "date_end": None,
            "time_raw": "14:00 – 18:00",
            "location": "Friedrichstal, Marktplatz (Oskar-Hornung-Haus)",
            "organizer": "Stadt Stutensee",
            "description": "Wochenmarkt in Friedrichstal. Mittwochs 14:00–18:00 Uhr auf dem Marktplatz.",
            "event_url": "https://www.stutensee.de/Buergerservice-A-Z/Dienstleistung?view=publish&item=service&id=4835"
        })
        # Saturday: Blankenloch 07:00-13:00
        sat = today + timedelta(days=(5 - today.weekday()) % 7 + week_offset * 7)
        events.append({
            "title": "Wochenmarkt Blankenloch",
            "date_start": sat.strftime("%Y-%m-%d"),
            "date_end": None,
            "time_raw": "07:00 – 13:00",
            "location": "Blankenloch, Neuer Markt (Michaeliskirche)",
            "organizer": "Stadt Stutensee",
            "description": "Wochenmarkt in Blankenloch. Samstags 07:00–13:00 Uhr am Neuen Markt.",
            "event_url": "https://www.stutensee.de/Buergerservice-A-Z/Dienstleistung?view=publish&item=service&id=4835"
        })
    return {"source_url": "https://www.stutensee.de/Buergerservice-A-Z/Dienstleistung?view=publish&item=service&id=4835", "events": events}
