/* ==========================================================================
   Hey, Stutensee! — client-side rendering & filtering
   The server renders the first page; this file hydrates behaviour and
   re-renders whenever filters change.
   ========================================================================== */

let currentPage = 1;
let totalPages = 1;
let searchTimeout;

// Inline stroke icons (mirrors the server-side icons in _worker.js).
const ICON = {
  clock: '<svg class="icon" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><circle cx="12" cy="12" r="9"/><path d="M12 7v5l3 2"/></svg>',
  pin: '<svg class="icon" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M20 10c0 6-8 12-8 12S4 16 4 10a8 8 0 1 1 16 0z"/><circle cx="12" cy="10" r="3"/></svg>',
  arrow: '<svg class="icon" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M5 12h14M13 6l6 6-6 6"/></svg>',
  star: '<svg class="icon" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="currentColor" aria-hidden="true"><path d="m12 3.6 2.6 5.3 5.9.9-4.3 4.1 1 5.8-5.2-2.7-5.2 2.7 1-5.8L3.5 9.8l5.9-.9z"/></svg>',
  search: '<svg class="icon" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" aria-hidden="true"><circle cx="11" cy="11" r="7"/><path d="m20 20-3.5-3.5"/></svg>',
  chat: '<svg class="icon" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M21 11.5a8.4 8.4 0 0 1-8.5 8.5 9 9 0 0 1-3.8-.9L3 21l1.9-5.7A8.5 8.5 0 0 1 12.5 3 8.4 8.4 0 0 1 21 11.5z"/></svg>',
  chevLeft: '<svg class="icon" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="m15 18-6-6 6-6"/></svg>',
  chevRight: '<svg class="icon" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="m9 18 6-6-6-6"/></svg>',
};

let themeTags = [];
let locationTags = [];
let organizerTags = [];

let selectedThemes = [];
let selectedLocations = [];
let selectedOrganizer = '';
let showRecurring = true;
let condensedMode = false;

// ── Formatting helpers ────────────────────────────────────────────────

function showLoading() {
  const container = document.getElementById('events');
  container.innerHTML = `
    <div class="skeleton-card"><div class="skeleton-badge"></div><div class="skeleton-lines"><div class="skeleton"></div><div class="skeleton"></div><div class="skeleton"></div></div></div>
    <div class="skeleton-card"><div class="skeleton-badge"></div><div class="skeleton-lines"><div class="skeleton"></div><div class="skeleton"></div><div class="skeleton"></div></div></div>
    <div class="skeleton-card"><div class="skeleton-badge"></div><div class="skeleton-lines"><div class="skeleton"></div><div class="skeleton"></div><div class="skeleton"></div></div></div>
  `;
}

function debounceSearch() {
  updateSearchField();
  clearTimeout(searchTimeout);
  searchTimeout = setTimeout(() => loadEvents(1), 300);
}

function fmtDate(iso) {
  if (!iso) return '?';
  const p = iso.split('-');
  return p.length === 3 ? `${p[2]}.${p[1]}.${p[0]}` : iso;
}

function relativeDate(iso) {
  if (!iso) return '';
  const today = new Date();
  today.setHours(0, 0, 0, 0);
  const parts = iso.split('-');
  if (parts.length !== 3) return fmtDate(iso);
  const event = new Date(parseInt(parts[0]), parseInt(parts[1]) - 1, parseInt(parts[2]));
  event.setHours(0, 0, 0, 0);
  const diffMs = event - today;
  const diffDays = Math.round(diffMs / 86400000);
  if (diffDays < 0) return fmtDate(iso);
  if (diffDays === 0) return 'Heute';
  if (diffDays === 1) return 'Morgen';
  if (diffDays <= 60) return `In ${diffDays} Tagen`;
  const diffMonths = (event.getFullYear() - today.getFullYear()) * 12 + (event.getMonth() - today.getMonth());
  if (diffMonths <= 0) return fmtDate(iso);
  return `In ${diffMonths} Monaten`;
}

function relativeDayLabel(iso) {
  const rel = relativeDate(iso);
  return /^(Heute|Morgen|In \d)/.test(rel) ? rel : '';
}

function weekdayDe(iso) {
  if (!iso) return '';
  const names = ['Sonntag', 'Montag', 'Dienstag', 'Mittwoch', 'Donnerstag', 'Freitag', 'Samstag'];
  const d = new Date(`${iso}T00:00:00`);
  return isNaN(d.getTime()) ? '' : names[d.getDay()];
}

function formatCount(n) {
  return String(n).replace(/\B(?=(\d{3})+(?!\d))/g, '.');
}

// Description cleanup: scraped pages often carry icon rows, contact blocks and
// metadata labels ("Datum", "Veranstalter", "Auf Karte anzeigen"). We keep only
// prose-like lines and drop the rest so cards don't show machine noise.
const DESC_JUNK_LINE = /^(?:icon\.[\w.]+|auf karte anzeigen|karte|zur website|website|e-?mail(?: schreiben)?|telefonnummer:?|faxnummer:?|veranstalter|veranstaltungsort|datum|uhrzeit|beschreibung|anfahrt|öffnungszeiten|kontakt)$/i;
const DESC_CONTACT_LINE = /^(?:postfach\b|tel\.?:?\s|\+?\(?\d[\d\s()\/-]{8,}$|.*@.*\.[a-z]{2,}$)/i;
const DESC_WEEKDAY_RE = /\b(?:montag|dienstag|mittwoch|donnerstag|freitag|samstag|sonntag)\b/gi;

function normalizeText(raw) {
  return String(raw || '').replace(/\u00a0/g, ' ').replace(/\r/g, '').replace(/[ \t]+/g, ' ').trim();
}

/** Split a scraped description into blocks that still contain readable prose. */
function descriptionBlocks(raw) {
  if (!raw) return [];
  const text = normalizeText(raw);
  const blocks = [];
  for (const chunk of text.split(/\n\s*\n/)) {
    const kept = [];
    for (const rawLine of chunk.split('\n')) {
      const line = rawLine.trim();
      if (!line) continue;
      if (DESC_JUNK_LINE.test(line) || DESC_CONTACT_LINE.test(line)) continue;
      if (line.split(/\s+/).length < 7 && !/[.!?]$/.test(line)) continue;
      kept.push(line);
    }
    const joined = kept.join(' ').replace(/\s{2,}/g, ' ').trim();
    if (joined.length < 40) continue;
    if ((joined.match(DESC_WEEKDAY_RE) || []).length >= 3 && joined.length < 400) continue;
    blocks.push(joined);
  }
  return blocks;
}

function cleanDescription(raw) {
  const blocks = descriptionBlocks(raw);
  if (blocks.length) return blocks.join('\n\n');
  const text = normalizeText(raw);
  const looksScraped = /(?:icon\.|Auf Karte anzeigen|Zur Website|Telefonnummer|Faxnummer|E-Mail schreiben)/i.test(text) || /^Datum$/m.test(text);
  return looksScraped ? '' : text.replace(/\s+/g, ' ');
}

function summarizeDescription(raw) {
  const blocks = descriptionBlocks(raw);
  if (!blocks.length) return cleanDescription(raw);
  return blocks.reduce((a, b) => (b.length > a.length ? b : a));
}

function timeLabel(raw) {
  const t = (raw || '').trim();
  if (!t) return '';
  if (/^0?0[:.]00(\s*(–|-|bis)\s*0?0[:.]00)?$/.test(t)) return 'Ganztägig';
  return t;
}

function categoryOf(tags) {
  return tags.find(t => themeTags.includes(t) && t !== 'Sonstiges') || '';
}

function formatDateBadge(dateStr) {
  if (!dateStr) return { day: '?', month: '??' };
  const parts = dateStr.split('-');
  if (parts.length === 3) {
    const d = parseInt(parts[2], 10);
    const months = ['Jan','Feb','Mär','Apr','Mai','Jun','Jul','Aug','Sep','Okt','Nov','Dez'];
    const m = months[parseInt(parts[1], 10) - 1] || '??';
    return { day: d, month: m };
  }
  return { day: dateStr, month: '' };
}

function slugify(str) {
  if (!str) return '';
  return str.toLowerCase()
    .replace(/[ä]/g, 'ae').replace(/[ö]/g, 'oe').replace(/[ü]/g, 'ue').replace(/[ß]/g, 'ss')
    .replace(/[^a-z0-9]+/g, '-').replace(/^-+|-+$/g, '').substring(0, 80);
}

function esc(s) {
  if (s === null || s === undefined) return '';
  return String(s)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#39;');
}

/** Escape a string for use as a single-quoted JS argument inside an HTML attribute. */
function jsArg(value) {
  return esc(value).replace(/&#39;/g, "\\'");
}

// ── Filters ───────────────────────────────────────────────────────────

function countBadge(n) {
  return n ? ` <span class="count-badge">${n}</span>` : '';
}

function setButtonLabel(btn, label, count = 0) {
  if (!btn) return;
  const text = btn.querySelector('.filter-btn-text');
  const target = text || btn;
  if (text) text.textContent = label;
  else target.textContent = label;
  const existing = btn.querySelector('.count-badge');
  if (existing) existing.remove();
  if (count > 0) {
    const badge = document.createElement('span');
    badge.className = 'count-badge';
    badge.textContent = String(count);
    (text || btn).after(badge);
  }
}

function updateFilterButtons() {
  const themeBtn = document.getElementById('theme-btn');
  const locationBtn = document.getElementById('location-btn');
  const organizerBtn = document.getElementById('organizer-btn');

  if (themeBtn) {
    themeBtn.classList.toggle('active', selectedThemes.length > 0);
    setButtonLabel(themeBtn, 'Kategorie', selectedThemes.length);
  }
  if (locationBtn) {
    locationBtn.classList.toggle('active', selectedLocations.length > 0);
    setButtonLabel(locationBtn, selectedLocations[0] || 'Ortsteil');
    locationBtn.title = selectedLocations[0] || 'Nach Ortsteil filtern';
  }
  if (organizerBtn) {
    organizerBtn.classList.toggle('active', !!selectedOrganizer);
    setButtonLabel(organizerBtn, selectedOrganizer || 'Veranstalter');
    organizerBtn.title = selectedOrganizer || 'Nach Veranstalter filtern';
  }
}

function updateActiveTags() {
  const container = document.getElementById('active-tags');
  if (!container) return;
  const items = [];
  selectedThemes.forEach(t => items.push({ type: 'theme', value: t, label: t }));
  selectedLocations.forEach(t => items.push({ type: 'location', value: t, label: t }));
  if (selectedOrganizer) items.push({ type: 'organizer', value: selectedOrganizer, label: selectedOrganizer });

  container.innerHTML = items.map(i =>
    `<span class="active-tag">${esc(i.label)}<button type="button" class="remove" aria-label="${esc(i.label)} entfernen" onclick="selectTag('${i.type}','${jsArg(i.value)}')">×</button></span>`
  ).join('');

  const reset = document.getElementById('reset-filters');
  if (reset) reset.hidden = items.length === 0;
}

function updateSearchField() {
  const input = document.getElementById('search');
  const field = input && input.closest('.field-search');
  if (field) field.classList.toggle('has-value', !!input.value);
}

function clearSearch() {
  const input = document.getElementById('search');
  if (!input) return;
  input.value = '';
  updateSearchField();
  input.focus();
  loadEvents(1);
}

function resetFilters() {
  selectedThemes = [];
  selectedLocations = [];
  selectedOrganizer = '';
  showRecurring = true;
  const recurring = document.getElementById('show-recurring');
  if (recurring) recurring.checked = true;

  const search = document.getElementById('search');
  if (search) search.value = '';
  const dateFrom = document.getElementById('date-from');
  if (dateFrom) dateFrom.value = new Date().toISOString().slice(0, 10);

  document.querySelectorAll('.popover-dropdown .chip').forEach(c => {
    c.classList.remove('active');
    c.setAttribute('aria-checked', 'false');
  });
  closeAllPopovers();
  updateSearchField();
  updateFilterButtons();
  updateActiveTags();
  loadEvents(1);
}

async function loadTags() {
  const [themeRes, districtRes, organizerRes] = await Promise.all([
    fetch('/api/theme'),
    fetch('/api/districts'),
    fetch('/api/organizer')
  ]);
  themeTags = await themeRes.json();
  locationTags = await districtRes.json();
  organizerTags = await organizerRes.json();

  const themeDropdown = document.getElementById('theme-dropdown');
  if (themeDropdown) {
    themeDropdown.innerHTML = themeTags.map(t =>
      `<span class="chip${selectedThemes.includes(t) ? ' active' : ''}" role="checkbox" aria-checked="${selectedThemes.includes(t)}" tabindex="0" data-tag="${esc(t)}" onclick="selectTag('theme','${jsArg(t)}')" onkeydown="if(event.key==='Enter'||event.key===' '){event.preventDefault();selectTag('theme','${jsArg(t)}')}">${esc(t)}</span>`
    ).join('');
  }

  const locationDropdown = document.getElementById('location-dropdown');
  if (locationDropdown) {
    locationDropdown.innerHTML = locationTags.map(t =>
      `<span class="chip${selectedLocations.includes(t) ? ' active' : ''}" role="checkbox" aria-checked="${selectedLocations.includes(t)}" tabindex="0" data-tag="${esc(t)}" onclick="selectTag('location','${jsArg(t)}')" onkeydown="if(event.key==='Enter'||event.key===' '){event.preventDefault();selectTag('location','${jsArg(t)}')}">${esc(t)}</span>`
    ).join('');
  }

  renderOrganizers();
}

function renderOrganizers() {
  const input = document.getElementById('organizer-search');
  const container = document.getElementById('organizer-chips');
  if (!container) return;
  const query = (input?.value || '').toLowerCase();
  container.innerHTML = organizerTags
    .filter(o => o.toLowerCase().includes(query))
    .map(o =>
      `<span class="chip${selectedOrganizer === o ? ' active' : ''}" role="checkbox" aria-checked="${selectedOrganizer === o}" tabindex="0" data-organizer="${esc(o)}" onclick="selectTag('organizer','${jsArg(o)}')" onkeydown="if(event.key==='Enter'||event.key===' '){event.preventDefault();selectTag('organizer','${jsArg(o)}')}">${esc(o)}</span>`
    ).join('');
}

function filterOrganizers() {
  renderOrganizers();
}

function selectTag(type, tag) {
  if (type === 'theme') {
    const idx = selectedThemes.indexOf(tag);
    if (idx >= 0) selectedThemes.splice(idx, 1); else selectedThemes.push(tag);
    document.querySelectorAll('#theme-dropdown .chip').forEach(c => {
      const active = selectedThemes.includes(c.dataset.tag);
      c.classList.toggle('active', active);
      c.setAttribute('aria-checked', String(active));
    });
  } else if (type === 'location') {
    selectedLocations = selectedLocations[0] === tag ? [] : [tag];
    document.querySelectorAll('#location-dropdown .chip').forEach(c => {
      const active = selectedLocations.includes(c.dataset.tag);
      c.classList.toggle('active', active);
      c.setAttribute('aria-checked', String(active));
    });
    closeAllPopovers();
  } else if (type === 'organizer') {
    selectedOrganizer = selectedOrganizer === tag ? '' : tag;
    document.querySelectorAll('#organizer-dropdown .chip').forEach(c => {
      const active = c.dataset.organizer === selectedOrganizer;
      c.classList.toggle('active', active);
      c.setAttribute('aria-checked', String(active));
    });
    closeAllPopovers();
  }
  updateFilterButtons();
  updateActiveTags();
  loadEvents(1);
}

function toggleFilterPopover(type) {
  const dropdown = document.getElementById(type + '-dropdown');
  const btn = document.getElementById(type + '-btn');
  if (!dropdown || !btn) return;
  const isOpen = dropdown.classList.contains('open');
  if (isOpen) {
    dropdown.classList.remove('open');
    btn.setAttribute('aria-expanded', 'false');
  } else {
    closeAllPopovers();
    dropdown.classList.add('open');
    btn.setAttribute('aria-expanded', 'true');
    // On mobile the panels become bottom sheets — dim the page behind them.
    document.body.classList.add('sheet-open');
    if (type === 'organizer') {
      const input = document.getElementById('organizer-search');
      if (input) { input.value = ''; input.focus(); }
      renderOrganizers();
    }
  }
}

function closeAllPopovers() {
  document.querySelectorAll('.popover-dropdown, .settings-dropdown').forEach(d => d.classList.remove('open'));
  document.querySelectorAll('.filter-btn').forEach(b => b.setAttribute('aria-expanded', 'false'));
  document.body.classList.remove('sheet-open');
}

document.addEventListener('click', function (e) {
  if (!e.target.closest('.filter-popover')) closeAllPopovers();
});

document.addEventListener('keydown', function (e) {
  if (e.key === 'Escape') closeAllPopovers();
});

function applyCondensedToDom() {
  document.querySelectorAll('.event').forEach(el => {
    el.classList.toggle('condensed', condensedMode);
    el.classList.remove('expanded');
    el.onclick = condensedMode ? function () { this.classList.toggle('expanded'); } : null;
  });
}

function toggleCondensed() {
  condensedMode = document.getElementById('condensed-toggle').checked;
  localStorage.setItem('condensed', condensedMode ? '1' : '');
  applyCondensedToDom();
}

function toggleRecurringFilter() {
  showRecurring = document.getElementById('show-recurring').checked;
  localStorage.setItem('showRecurring', showRecurring ? '1' : '');
  loadEvents(1);
}

// ── Featured ──────────────────────────────────────────────────────────

function renderFeaturedCard(e) {
  const tags = (e.tags || '').split(',').map(t => t.trim()).filter(Boolean);
  const locTags = tags.filter(t => locationTags.includes(t));
  const category = categoryOf(tags) || 'Empfohlen';
  const badge = formatDateBadge(e.date_start);
  const path = '/events/' + e.id + '/' + slugify(e.title);
  const place = e.location || locTags[0] || '';
  const time = timeLabel(e.time_raw);
  return `<article class="featured-card" aria-label="${esc(e.title)}">
    <div class="fc-badge"><span class="fc-day">${badge.day}</span><span class="fc-month">${badge.month}</span></div>
    <div class="fc-body">
      <span class="fc-kicker">${esc(category)}</span>
      <h3 class="fc-title"><a href="${esc(path)}">${esc(e.title)}</a></h3>
      <div class="fc-meta">
        ${time ? `<span>${ICON.clock}<span>${esc(time)}</span></span>` : ''}
        ${place ? `<span>${ICON.pin}<span>${esc(place)}</span></span>` : ''}
      </div>
    </div>
  </article>`;
}

function renderFeaturedSection(events) {
  if (!events || events.length === 0) return '';
  let html = `<section class="featured" aria-labelledby="featured-heading">
    <div class="featured-head">
      <h2 class="featured-heading" id="featured-heading">${ICON.star} Empfohlen</h2>
      <span class="featured-sub">Handverlesene Termine</span>
    </div>
    <div class="featured-grid">`;
  for (const e of events) html += renderFeaturedCard(e);
  html += '</div></section>';
  return html;
}

function renderFeaturedSectionToDOM(events) {
  const container = document.getElementById('featured-container');
  if (!container) return;
  container.innerHTML = renderFeaturedSection(events);
}

async function loadFeaturedEvents() {
  try {
    const r = await fetch('/api/featured');
    if (!r.ok) return;
    const events = await r.json();
    renderFeaturedSectionToDOM(events);
  } catch (e) {
    console.error('Featured events fetch error:', e);
  }
}


// ── Events ────────────────────────────────────────────────────────────

function updateStickyTop() {
  const bar = document.querySelector('.controls-wrap');
  if (!bar) return;
  document.documentElement.style.setProperty('--toolbar-h', bar.offsetHeight + 'px');
}

let resizeTimer;
window.addEventListener('resize', () => {
  clearTimeout(resizeTimer);
  resizeTimer = setTimeout(updateStickyTop, 100);
});

function syncUrl(page) {
  if (window.location.pathname !== '/') return;
  const params = new URLSearchParams();
  if (page > 1) params.set('page', page);
  const search = document.getElementById('search').value.trim();
  if (search) params.set('search', search);
  const dateFrom = document.getElementById('date-from').value;
  const today = new Date().toISOString().slice(0, 10);
  if (dateFrom && dateFrom !== today) params.set('date_from', dateFrom);
  selectedThemes.forEach(t => params.append('tag', t));
  selectedLocations.forEach(t => params.append('tag', t));
  if (selectedOrganizer) params.set('organizer', selectedOrganizer);
  if (!showRecurring) params.set('hide_recurring', 'true');
  const qs = params.toString();
  history.replaceState(null, '', qs ? `/?${qs}` : '/');
}

/** Hide the featured rail while a search/filter is active. */
function updateFeaturedVisibility() {
  const container = document.getElementById('featured-container');
  if (!container) return;
  const search = document.getElementById('search');
  const filtering = !!search?.value.trim() || selectedThemes.length > 0 || selectedLocations.length > 0 || !!selectedOrganizer;
  container.hidden = filtering;
}

function updateResultCount(total) {
  const el = document.getElementById('results-count');
  if (!el) return;
  el.textContent = total > 0 ? `${formatCount(total)} ${total === 1 ? 'Termin' : 'Termine'}` : '';
}

async function loadEvents(page) {
  currentPage = page;
  const search = document.getElementById('search').value;
  const dateFrom = document.getElementById('date-from').value;
  const params = new URLSearchParams({ page, per_page: 12, search });
  if (dateFrom) params.set('date_from', dateFrom);
  selectedThemes.forEach(t => params.append('tag', t));
  selectedLocations.forEach(t => params.append('tag', t));
  if (selectedOrganizer) params.set('organizer', selectedOrganizer);
  if (!showRecurring) params.set('hide_recurring', '1');
  showLoading();
  try {
    const r = await fetch(`/api/list?${params}`);
    const data = await r.json();
    totalPages = data.total_pages;
    updateResultCount(data.total);
    renderEvents(data.events);
    renderPagination();
    updateFeaturedVisibility();
  } catch (err) {
    console.error('Event load error:', err);
    renderEvents([]);
  }
  syncUrl(page);
  updateStickyTop();
}

function renderEvents(events) {
  const container = document.getElementById('events');
  const searchQuery = document.getElementById('search').value.trim();
  events = (events || []).filter(e => e.date_start);

  let html = '';
  if (searchQuery) {
    html += `<button type="button" class="chat-cta" data-query="${esc(searchQuery)}" onclick="openChatWithQuery(this.dataset.query)">
      <span class="chat-cta-icon">${ICON.chat}</span>
      <span class="chat-cta-copy">
        <span class="chat-cta-title">Im KI-Chat weiterfragen</span>
        <span class="chat-cta-text">Fragen zu „${esc(searchQuery)}“ – z. B. nach Terminen, Orten oder Details.</span>
      </span>
      <span class="chat-cta-arrow">${ICON.arrow}</span>
    </button>`;
  }

  if (events.length === 0) {
    const hasFilters = !!searchQuery || selectedThemes.length > 0 || selectedLocations.length > 0 || !!selectedOrganizer;
    container.innerHTML = html + `<div class="empty">
      <div class="empty-icon">${ICON.search}</div>
      <p class="empty-title">Keine Termine gefunden</p>
      <p class="empty-text">Versuche einen anderen Suchbegriff, ein späteres Startdatum oder weniger Filter.</p>
      ${hasFilters ? '<button type="button" class="empty-reset" onclick="resetFilters()">Alle Filter zurücksetzen</button>' : ''}
    </div>`;
    return;
  }

  let lastDate = '';
  for (const e of events) {
    if (e.date_start !== lastDate) {
      lastDate = e.date_start;
      const badge = formatDateBadge(e.date_start);
      const rel = relativeDayLabel(e.date_start);
      html += `<div class="date-separator" role="separator" aria-label="${esc(fmtDate(e.date_start))}">
        <span class="ds-day">${badge.day}</span>
        <span class="ds-month">${badge.month}</span>
        <span class="ds-weekday">${esc(weekdayDe(e.date_start))}</span>
        ${rel ? `<span class="ds-rel${rel === 'Heute' ? ' today' : ''}">${esc(rel)}</span>` : ''}
      </div>`;
    }

    const tags = e.tags ? e.tags.split(',').map(t => t.trim()).filter(Boolean) : [];
    const locTags = tags.filter(t => locationTags.includes(t));
    const category = categoryOf(tags);
    const time = timeLabel(e.time_raw);
    const detailHref = '/events/' + e.id + '/' + slugify(e.title);
    const place = e.location || locTags[0] || '';
    const description = summarizeDescription(e.description);

    html += `<article class="event${condensedMode ? ' condensed' : ''}" id="event-${e.id}" aria-label="${esc(e.title)}"${condensedMode ? ' onclick="this.classList.toggle(\'expanded\')"' : ''}>
      <div class="event-body">
        <div class="event-top${category ? '' : ' no-cat'}">
          ${category ? `<span class="event-cat">${esc(category)}</span>` : ''}
          ${time ? `<span class="event-time">${ICON.clock}${esc(time)}</span>` : ''}
        </div>
        <h2><a href="${detailHref}">${esc(e.title)}</a>${place ? `<span class="condensed-location">${esc(place)}</span>` : ''}</h2>
        ${place ? `<p class="event-where">${ICON.pin}<span>${esc(place)}</span></p>` : ''}
        ${description ? `<p class="event-desc">${esc(description)}</p>` : ''}
        <div class="event-tags">
          ${e.organizer ? `<span class="tag tag-organizer" title="Veranstalter">${esc(e.organizer)}</span>` : ''}
          ${locTags.slice(0, 2).map(t => `<span class="tag tag-location">${esc(t)}</span>`).join('')}
          <a class="event-more" href="${detailHref}" aria-label="Details zu ${esc(e.title)}">Details${ICON.arrow}</a>
        </div>
        ${e.recurring_group_id ? `<button type="button" class="recurring-toggle" onclick="event.stopPropagation();toggleRecurring(${e.id}, ${e.recurring_group_id}, this)">▸ Alle Termine</button><div id="recurring-${e.id}" class="recurring-list" style="display:none"></div>` : ''}
      </div>
    </article>`;
  }
  container.innerHTML = html;
}

async function toggleRecurring(eventId, groupId, el) {
  const list = document.getElementById('recurring-' + eventId);
  if (!list) return;
  if (list.style.display === 'block') {
    list.style.display = 'none';
    if (el) el.innerHTML = '▸ Alle Termine';
    return;
  }
  if (el) el.innerHTML = '▾ Alle Termine';
  if (list.dataset.loaded) {
    list.style.display = 'block';
    return;
  }
  list.innerHTML = '<div class="loading-spinner"><span class="spinner"></span>Termine werden geladen…</div>';
  list.style.display = 'block';
  const r = await fetch('/api/same/' + groupId);
  const events = await r.json();
  list.innerHTML = '<table><tr><th>Datum</th><th>Zeit</th><th>Ort</th></tr>' + events.map(e =>
    `<tr><td>${fmtDate(e.date_start)}${e.date_end && e.date_end !== e.date_start ? '–' + fmtDate(e.date_end) : ''}</td><td>${esc(e.time_raw || '—')}</td><td>${esc(e.location || '?')}</td></tr>`
  ).join('') + '</table>';
  list.dataset.loaded = '1';
}

// ── Pagination ────────────────────────────────────────────────────────

function pageWindow(current, total) {
  if (total <= 7) return Array.from({ length: total }, (_, i) => i + 1);
  const pages = new Set([1, total, current, current - 1, current + 1]);
  if (current <= 3) [2, 3, 4].forEach(p => pages.add(p));
  if (current >= total - 2) [total - 1, total - 2, total - 3].forEach(p => pages.add(p));
  const sorted = [...pages].filter(p => p >= 1 && p <= total).sort((a, b) => a - b);
  const out = [];
  let prev = 0;
  for (const p of sorted) {
    if (prev && p - prev > 1) out.push(null);
    out.push(p);
    prev = p;
  }
  return out;
}

function renderPagination() {
  const el = document.getElementById('pagination');
  if (!el) return;
  if (totalPages <= 1) {
    el.innerHTML = '';
    return;
  }
  let html = '<nav aria-label="Seitennavigation">';
  html += currentPage > 1
    ? `<button type="button" class="page-btn" onclick="loadEvents(${currentPage - 1})" aria-label="Vorherige Seite">${ICON.chevLeft}</button>`
    : `<span class="page-btn" aria-hidden="true">${ICON.chevLeft}</span>`;

  for (const p of pageWindow(currentPage, totalPages)) {
    if (p === null) {
      html += '<span class="page-ellipsis" aria-hidden="true">…</span>';
    } else if (p === currentPage) {
      html += `<span class="page-btn current" aria-current="page">${p}</span>`;
    } else {
      html += `<button type="button" class="page-btn" onclick="loadEvents(${p})">${p}</button>`;
    }
  }

  html += currentPage < totalPages
    ? `<button type="button" class="page-btn" onclick="loadEvents(${currentPage + 1})" aria-label="Nächste Seite">${ICON.chevRight}</button>`
    : `<span class="page-btn" aria-hidden="true">${ICON.chevRight}</span>`;
  html += `<span class="page-info">Seite ${currentPage} von ${totalPages}</span>`;
  html += '</nav>';
  el.innerHTML = html;
}

// ── Theme ─────────────────────────────────────────────────────────────

function toggleDark() {
  const isDark = document.documentElement.classList.toggle('dark');
  document.documentElement.setAttribute('data-theme', isDark ? 'dark' : 'light');
  localStorage.setItem('dark', isDark ? '1' : '0');
  const btn = document.getElementById('dark-toggle');
  if (btn) {
    btn.setAttribute('aria-pressed', String(isDark));
    btn.setAttribute('aria-label', isDark ? 'Helles Design einschalten' : 'Dunkles Design einschalten');
  }
}

function initTheme() {
  const isDark = document.documentElement.classList.contains('dark');
  const btn = document.getElementById('dark-toggle');
  if (btn) {
    btn.setAttribute('aria-pressed', String(isDark));
    btn.setAttribute('aria-label', isDark ? 'Helles Design einschalten' : 'Dunkles Design einschalten');
  }
  window.matchMedia('(prefers-color-scheme: dark)').addEventListener('change', e => {
    if (localStorage.getItem('dark') !== null) return;
    document.documentElement.classList.toggle('dark', e.matches);
    document.documentElement.setAttribute('data-theme', e.matches ? 'dark' : 'light');
    const b = document.getElementById('dark-toggle');
    if (b) b.setAttribute('aria-pressed', String(e.matches));
  });
}

// ── Bootstrap ─────────────────────────────────────────────────────────

function applyFilterParams(params) {
  if (!params) return;

  selectedThemes = Array.isArray(params.selectedThemes) ? params.selectedThemes : [];
  selectedLocations = Array.isArray(params.selectedLocations) ? params.selectedLocations : [];
  if (params.selectedOrganizer) selectedOrganizer = params.selectedOrganizer;
  if (params.search) {
    const search = document.getElementById('search');
    if (search) search.value = params.search;
  }
  if (params.date_from) {
    const dateFrom = document.getElementById('date-from');
    if (dateFrom) dateFrom.value = params.date_from;
  }
  if (params.showRecurring !== undefined) {
    showRecurring = params.showRecurring;
    const toggle = document.getElementById('show-recurring');
    if (toggle) toggle.checked = showRecurring;
  }

  document.querySelectorAll('#theme-dropdown .chip').forEach(c => {
    const active = selectedThemes.includes(c.dataset.tag);
    c.classList.toggle('active', active);
    c.setAttribute('aria-checked', String(active));
  });
  document.querySelectorAll('#location-dropdown .chip').forEach(c => {
    const active = selectedLocations.includes(c.dataset.tag);
    c.classList.toggle('active', active);
    c.setAttribute('aria-checked', String(active));
  });
  document.querySelectorAll('#organizer-dropdown .chip').forEach(c => {
    const active = c.dataset.organizer === selectedOrganizer;
    c.classList.toggle('active', active);
    c.setAttribute('aria-checked', String(active));
  });

  updateFilterButtons();
  updateActiveTags();
  updateSearchField();
  updateFeaturedVisibility();
}

(function init() {
  initTheme();

  const dateInput = document.getElementById('date-from');
  if (dateInput && !dateInput.value) dateInput.value = new Date().toISOString().slice(0, 10);

  if (localStorage.getItem('condensed')) {
    const t = document.getElementById('condensed-toggle');
    if (t) t.checked = true;
    condensedMode = true;
  }
  if (localStorage.getItem('showRecurring') === '') {
    const t = document.getElementById('show-recurring');
    if (t) t.checked = false;
    showRecurring = false;
  }

  updateSearchField();
  updateStickyTop();
  updateFeaturedVisibility();
  loadTags();

  const ssrData = document.getElementById('ssr-data');
  if (ssrData) {
    try {
      const data = JSON.parse(ssrData.textContent);
      // Restore filter state from the URL before deciding how to render.
      if (data.params) {
        if (data.params.districtKeys) locationTags = data.params.districtKeys;
        if (data.params.themeKeys) themeTags = data.params.themeKeys;
        applyFilterParams(data.params);
      }
      if (data.events && data.events.length > 0 && data.totalPages > 0) {
        currentPage = data.page;
        totalPages = data.totalPages;
        if (data.featuredEvents && data.featuredEvents.length > 0) {
          const featContainer = document.getElementById('featured-container');
          if (featContainer && !featContainer.querySelector('.featured')) {
            renderFeaturedSectionToDOM(data.featuredEvents);
          }
        }
        updateResultCount(data.total);
        // Keep the server-rendered cards to avoid a layout flash; only the
        // interactive parts (pagination, counts) get re-rendered.
        renderPagination();
        applyCondensedToDom();
        updateStickyTop();
        ssrData.remove();
      } else {
        loadEvents(1);
        loadFeaturedEvents();
      }
    } catch (e) {
      console.error('SSR data error:', e);
      loadEvents(1);
      loadFeaturedEvents();
    }
  } else {
    loadEvents(1);
    loadFeaturedEvents();
  }

  // Keep the sticky date separators aligned with the toolbar height.
  if (typeof ResizeObserver !== 'undefined') {
    const bar = document.querySelector('.controls-wrap');
    if (bar) new ResizeObserver(updateStickyTop).observe(bar);
  }
})();
