/**
 * Creates a real SQLite in-memory database with the curated_events schema
 * and sample data for integration testing.
 *
 * Test dates are computed dynamically to always be in the future,
 * preventing date_from default filters from excluding all test data.
 */
import Database from 'better-sqlite3';

/** Return ISO date string for N days from today. */
function daysFromNow(n) {
  const d = new Date();
  d.setDate(d.getDate() + n);
  return d.toISOString().slice(0, 10);
}

function buildSampleEvents() {
  const t = daysFromNow;
  return [
    {
      title: '10 Jahre Red Horse Festival',
      date_start: t(5),
      date_end: null,
      time_raw: '13:30',
      location: 'Jugendzentrum GrauBau',
      organizer: 'Jugendzentrum GrauBau',
      description: '',
      event_url: 'https://www.meinstutensee.de/veranstaltungen/10-jahre-red-horse-festival-3/',
      sources: 'https://meinstutensee.de/termine/',
      tags: 'Fest,Blankenloch',
    },
    {
      title: 'Hope is a dangerous thing mit der Saxofonistin Asy',
      date_start: t(10),
      date_end: null,
      time_raw: '20:00',
      location: 'Kulturhaus',
      organizer: 'Kulturverein',
      description: 'Ein besonderes Musikerlebnis',
      event_url: '',
      sources: 'test',
      tags: 'Musik,Kultur',
    },
    {
      title: 'Wochenmarkt Blankenloch',
      date_start: t(3),
      date_end: null,
      time_raw: '07:00 – 13:00',
      location: 'Blankenloch, Neuer Markt',
      organizer: 'Stadt Stutensee',
      description: 'Wochenmarkt in Blankenloch',
      event_url: 'https://www.stutensee.de/',
      sources: 'https://www.stutensee.de/',
      tags: 'Markt,Blankenloch',
    },
    {
      title: 'Internationaler Museumstag',
      date_start: t(7),
      date_end: null,
      time_raw: '13:00',
      location: 'Städtisches Museum, Bruchsal',
      organizer: 'Stadt Bruchsal',
      description: 'Eintritt in Schloss Bruchsal: 8 Euro, ermäßigt 4 Euro',
      event_url: 'https://www.bruchsal.de/',
      sources: 'https://www.bruchsal.de/',
      tags: 'Kultur,Bruchsal',
    },
    {
      title: 'Fußball WM 2026 – Gemeinsam Jubeln',
      date_start: t(14),
      date_end: null,
      time_raw: '20:45',
      location: 'Vereinsheim',
      organizer: 'Fanclub',
      description: 'Public Viewing zur WM',
      event_url: '',
      sources: 'test',
      tags: 'Sport',
    },
    {
      title: 'Test &amp; Demo &lt;Event&gt;',
      date_start: t(2),
      date_end: null,
      time_raw: '',
      location: 'Test Location &amp; Co',
      organizer: 'Test Org',
      description: '',
      event_url: '',
      sources: 'test',
      tags: 'Sonstiges,Test',
    },
  ];
}

const SAMPLE_EVENTS = buildSampleEvents();

export function createTestDb() {
  const db = new Database(':memory:');

  db.exec(`
    CREATE TABLE curated_events (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      title TEXT NOT NULL,
      date_start TEXT,
      date_end TEXT,
      time_raw TEXT,
      location TEXT,
      organizer TEXT,
      description TEXT,
      event_url TEXT,
      sources TEXT,
      tags TEXT,
      recurring_group_id INTEGER,
      is_passed INTEGER DEFAULT 0,
      featured INTEGER DEFAULT 0
    );
    
    CREATE TABLE raw_events (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      title TEXT NOT NULL,
      date_start TEXT,
      date_end TEXT,
      time_raw TEXT,
      location TEXT,
      organizer TEXT,
      description TEXT,
      event_url TEXT,
      sources TEXT,
      tags TEXT,
      source_url TEXT
    );
  `);

  const insertCurated = db.prepare(`
    INSERT INTO curated_events (title, date_start, date_end, time_raw, location, organizer, description, event_url, sources, tags)
    VALUES (@title, @date_start, @date_end, @time_raw, @location, @organizer, @description, @event_url, @sources, @tags)
  `);

  const insertRaw = db.prepare(`
    INSERT INTO raw_events (title, date_start, date_end, time_raw, location, organizer, description, event_url, sources, tags, source_url)
    VALUES (@title, @date_start, @date_end, @time_raw, @location, @organizer, @description, @event_url, @sources, @tags, @sources)
  `);

  for (const event of SAMPLE_EVENTS) {
    insertCurated.run(event);
    insertRaw.run(event);
  }

  return db;
}

export { SAMPLE_EVENTS };
