"""
scraper_kickers_buechig.py — Manually curated events from SV Kickers Büchig.

Source: http://www.kickers-buechig.de/termine.html?file=tl_files%2FTermine%2FTermine+2026.pdf
Update: Annually when the new Termine PDF is published (usually January).
        Extract public events only — skip members' meetings, board sittings,
        and Altpapiersammlung (paper recycling drives).
"""

SOURCE_URL = "http://www.kickers-buechig.de"

# Curated public events for 2026 (extracted from Termine 2026.pdf, 2026-07-06).
# Only events of general public interest are included.
# Internal meetings (MV, Förderkreissitzung) and Altpapiersammlung are excluded.
KICKERS_BUECHIG_EVENTS = [
    {
        "title": "Jugendwinterfeier",
        "date_start": "2026-01-31",
        "date_end": None,
        "time_raw": "",
        "location": "Waldsportplatz, 76297 Stutensee-Büchig",
        "organizer": "SV Kickers Büchig",
        "description": "Winterfeier für die Jugendabteilung des SV Kickers Büchig.",
        "event_url": "http://www.kickers-buechig.de",
    },
    {
        "title": "Kinderfasching",
        "date_start": "2026-02-17",
        "date_end": None,
        "time_raw": "",
        "location": "Bürgerwaldhalle, 76297 Stutensee-Büchig",
        "organizer": "SV Kickers Büchig",
        "description": "Faschingsveranstaltung für Kinder.",
        "event_url": "http://www.kickers-buechig.de",
    },
    {
        "title": "Maifest",
        "date_start": "2026-05-01",
        "date_end": None,
        "time_raw": "10:00",
        "location": "Waldsportplatz, 76297 Stutensee-Büchig",
        "organizer": "SV Kickers Büchig",
        "description": "Traditionelles Maifest am Waldsportplatz Büchig. Beginn um 10:00 Uhr. Parken bei der Bürgerwaldhalle.",
        "event_url": "http://www.kickers-buechig.de",
    },
    {
        "title": "Sportfest / Hubert-Uhländer-Cup",
        "date_start": "2026-07-17",
        "date_end": "2026-07-19",
        "time_raw": "",
        "location": "Waldsportplatz, 76297 Stutensee-Büchig",
        "organizer": "SV Kickers Büchig",
        "description": "SVB-Sportfest mit Einweihung des Trainingsplatzes und Jugendfußball-Turnier (Hubert-Uhländer-Cup).",
        "event_url": "http://www.kickers-buechig.de",
    },
    {
        "title": "KSC Fußballcamp",
        "date_start": "2026-08-04",
        "date_end": "2026-08-07",
        "time_raw": "",
        "location": "Waldsportplatz, 76297 Stutensee-Büchig",
        "organizer": "Förderkreis Fußballjugend SV Kickers Büchig",
        "description": "Fußballcamp in Kooperation mit dem Karlsruher SC für Kinder und Jugendliche.",
        "event_url": "http://www.kickers-buechig.de",
    },
    {
        "title": "U14-REWE-CUP",
        "date_start": "2026-09-19",
        "date_end": None,
        "time_raw": "",
        "location": "Waldsportplatz, 76297 Stutensee-Büchig",
        "organizer": "SV Kickers Büchig",
        "description": "Jugendfußballturnier für U14-Mannschaften.",
        "event_url": "http://www.kickers-buechig.de",
    },
    {
        "title": "Schlachtfest",
        "date_start": "2026-10-10",
        "date_end": None,
        "time_raw": "",
        "location": "Bürgerwaldhalle, 76297 Stutensee-Büchig",
        "organizer": "Förderkreis Fußballjugend SV Kickers Büchig",
        "description": "Traditionelles Schlachtfest des Förderkreises Fußballjugend.",
        "event_url": "http://www.kickers-buechig.de",
    },
    {
        "title": "Winterfeier",
        "date_start": "2026-12-19",
        "date_end": None,
        "time_raw": "",
        "location": "Bürgerwaldhalle, 76297 Stutensee-Büchig",
        "organizer": "SV Kickers Büchig",
        "description": "Jahresabschluss-Winterfeier des SV Kickers Büchig.",
        "event_url": "http://www.kickers-buechig.de",
    },
]


def scrape_kickers_buechig():
    """Return hardcoded public events from SV Kickers Büchig Termine 2026 PDF.
    
    Updated annually when the new PDF is published. Only public-interest
    events are included (no member meetings, board sittings, or paper drives).
    """
    return {
        "source_url": SOURCE_URL,
        "events": KICKERS_BUECHIG_EVENTS,
    }


if __name__ == "__main__":
    result = scrape_kickers_buechig()
    print(f"Found {len(result['events'])} events")
    for ev in result["events"]:
        end = f" – {ev['date_end']}" if ev['date_end'] else ""
        print(f"  {ev['date_start']}{end} - {ev['title']}")
