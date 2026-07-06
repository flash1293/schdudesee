

let currentPage = 1;
let totalPages = 1;
let searchTimeout;
let selectedTag = '';

function showLoading() {
  const container = document.getElementById('events');
  container.innerHTML = `
    <div class="skeleton-card"><div class="skeleton-badge"></div><div class="skeleton-lines"><div class="skeleton"></div><div class="skeleton"></div><div class="skeleton"></div></div></div>
    <div class="skeleton-card"><div class="skeleton-badge"></div><div class="skeleton-lines"><div class="skeleton"></div><div class="skeleton"></div><div class="skeleton"></div></div></div>
    <div class="skeleton-card"><div class="skeleton-badge"></div><div class="skeleton-lines"><div class="skeleton"></div><div class="skeleton"></div><div class="skeleton"></div></div></div>
  `;
}

function debounceSearch() {
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
const TAG_EMOJIS = {
  'Sport':'⚽','Musik':'🎵','Kultur':'🎭','Kirche':'⛪','Kinder':'🧒','Fest':'🎉',
  'Markt':'🛒','Workshop':'🔧','Bildung':'📚','Natur':'🌿','Senioren':'👴','Digital':'💻',
  'Handwerk':'✂️','Essen':'🍽️','Treff':'☕','Politik':'🗳️','Verein':'🤝','Wohltätigkeit':'❤️',
  'Sonstiges':'📌'
};
let themeTags = [];
let locationTags = [];
let organizerTags = [];

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
  themeDropdown.innerHTML = themeTags.map(t =>
    `<span class="chip${selectedThemes.includes(t) ? ' active' : ''}" data-tag="${esc(t)}" onclick="selectTag('theme','${esc(t)}')">${TAG_EMOJIS[t] || ''} ${esc(t)}</span>`
  ).join('');

  const locationDropdown = document.getElementById('location-dropdown');
  locationDropdown.innerHTML = locationTags.map(t =>
    `<span class="chip chip-location${selectedLocations.includes(t) ? ' active' : ''}" data-tag="${esc(t)}" onclick="selectTag('location','${esc(t)}')">📍 ${esc(t)}</span>`
  ).join('');

  renderOrganizers();
}

function renderOrganizers() {
  const query = (document.getElementById('organizer-search')?.value || '').toLowerCase();
  const container = document.getElementById('organizer-chips');
  container.innerHTML = organizerTags
    .filter(o => o.toLowerCase().includes(query))
    .map(o =>
      `<span class="chip${selectedOrganizer === o ? ' active' : ''}" data-organizer="${esc(o)}" onclick="selectTag('organizer','${esc(o)}')">${esc(o)}</span>`
    ).join('');
}

function filterOrganizers() {
  renderOrganizers();
}

let condensedMode = false;

// Apply filter params from SSR initial data to UI controls
function applyFilterParams(params) {
  if (!params) return;

  // Validate arrays and set filter state
  selectedThemes = Array.isArray(params.selectedThemes) ? params.selectedThemes : [];
  selectedLocations = Array.isArray(params.selectedLocations) ? params.selectedLocations : [];
  if (params.selectedOrganizer) selectedOrganizer = params.selectedOrganizer;
  if (params.search) document.getElementById('search').value = params.search;
  if (params.date_from) document.getElementById('date-from').value = params.date_from;
  if (params.showRecurring !== undefined) {
    showRecurring = params.showRecurring;
    document.getElementById('show-recurring').checked = showRecurring;
    document.getElementById('show-recurring-mobile').checked = showRecurring;
  }
  if (params.condensedMode !== undefined) {
    condensedMode = params.condensedMode;
    document.getElementById('condensed-toggle').checked = params.condensedMode;
    document.getElementById('condensed-toggle-mobile').checked = params.condensedMode;
  }

  // Sync theme chips and button
  document.querySelectorAll('#theme-dropdown .chip').forEach(c => {
    c.classList.toggle('active', selectedThemes.includes(c.dataset.tag));
  });
  document.getElementById('theme-btn').classList.toggle('active', selectedThemes.length > 0);
  document.getElementById('theme-btn').textContent = selectedThemes.length > 0
    ? `Kategorie (${selectedThemes.length}) ▾` : 'Kategorie ▾';

  // Sync location chips and button
  document.querySelectorAll('#location-dropdown .chip').forEach(c => {
    c.classList.toggle('active', selectedLocations.includes(c.dataset.tag));
  });
  document.getElementById('location-btn').classList.toggle('active', selectedLocations.length > 0);
  document.getElementById('location-btn').textContent = selectedLocations.length > 0
    ? `📍 ${selectedLocations[0]}` : 'Ortsteil';

  // Sync organizer chip and button
  document.querySelectorAll('#organizer-dropdown .chip').forEach(c => {
    c.classList.toggle('active', c.dataset.organizer === selectedOrganizer);
  });
  document.getElementById('organizer-btn').classList.toggle('active', !!selectedOrganizer);
  document.getElementById('organizer-btn').textContent = selectedOrganizer
    ? `Veranstalter ▸` : 'Veranstalter ▾';

  // Update active tags display
  updateActiveTags();
}

function toggleCondensed() {
  condensedMode = document.getElementById('condensed-toggle').checked;
  localStorage.setItem('condensed', condensedMode ? '1' : '');
  document.getElementById('condensed-toggle-mobile').checked = condensedMode;
  document.querySelectorAll('.event').forEach(el => {
    el.classList.toggle('condensed', condensedMode);
    if (condensedMode) {
      el.onclick = function() { this.classList.toggle('expanded'); };
    } else {
      el.onclick = null;
    }
  });
}

let selectedThemes = [];
let selectedLocations = [];
let selectedOrganizer = '';
let showRecurring = true;

function selectTag(type, tag) {
  if (type === 'theme') {
    const idx = selectedThemes.indexOf(tag);
    if (idx >= 0) selectedThemes.splice(idx, 1); else selectedThemes.push(tag);
    document.querySelectorAll('#theme-dropdown .chip').forEach(c => {
      c.classList.toggle('active', selectedThemes.includes(c.dataset.tag));
    });
    document.getElementById('theme-btn').classList.toggle('active', selectedThemes.length > 0);
    document.getElementById('theme-btn').textContent = selectedThemes.length > 0
      ? `Kategorie (${selectedThemes.length}) ▾` : 'Kategorie ▾';
  } else if (type === 'location') {
    if (selectedLocations[0] === tag) {
      selectedLocations = [];
    } else {
      selectedLocations = [tag];
    }
    document.querySelectorAll('#location-dropdown .chip').forEach(c => {
      c.classList.toggle('active', selectedLocations.includes(c.dataset.tag));
    });
    document.getElementById('location-btn').classList.toggle('active', selectedLocations.length > 0);
    document.getElementById('location-btn').textContent = selectedLocations.length > 0
      ? `📍 ${tag}` : 'Ortsteil';
    closeAllPopovers();
  } else if (type === 'organizer') {
    selectedOrganizer = selectedOrganizer === tag ? '' : tag;
    document.querySelectorAll('#organizer-dropdown .chip').forEach(c => {
      c.classList.toggle('active', c.dataset.organizer === selectedOrganizer);
    });
    document.getElementById('organizer-btn').classList.toggle('active', !!selectedOrganizer);
    document.getElementById('organizer-btn').textContent = selectedOrganizer
      ? `Veranstalter ▸` : 'Veranstalter ▾';
    closeAllPopovers();
  }
  updateActiveTags();
  loadEvents(1);
}

function updateActiveTags() {
  const container = document.getElementById('active-tags');
  let html = '';
  selectedThemes.forEach(t => html += `<span class="active-tag">${TAG_EMOJIS[t] || ''} ${esc(t)} <span class="remove" onclick="selectTag('theme','${esc(t)}')">×</span></span>`);
  if (selectedOrganizer) html += `<span class="active-tag" style="background:#fef3c7;color:#92400e">📋 ${esc(selectedOrganizer)} <span class="remove" onclick="selectTag('organizer','${esc(selectedOrganizer)}')">×</span></span>`;
  container.innerHTML = html;
}

function toggleFilterPopover(type) {
  const dropdown = document.getElementById(type + '-dropdown');
  const btn = document.getElementById(type + '-btn');
  const isOpen = dropdown.classList.contains('open');
  if (isOpen) {
    dropdown.classList.remove('open');
    if (btn) btn.setAttribute('aria-expanded', 'false');
  } else {
    closeAllPopovers();
    dropdown.classList.add('open');
    if (btn) btn.setAttribute('aria-expanded', 'true');
    if (type === 'organizer') {
      const input = document.getElementById('organizer-search');
      if (input) { input.value = ''; input.focus(); }
      renderOrganizers();
    }
  }
}

function toggleSettingsDropdown() {
  document.getElementById('settings-dropdown').classList.toggle('open');
  document.querySelector('.settings-btn').classList.toggle('active');
}

function closeAllPopovers() {
  document.querySelectorAll('.popover-dropdown').forEach(d => d.classList.remove('open'));
  document.querySelectorAll('.filter-btn').forEach(b => b.setAttribute('aria-expanded', 'false'));
}

document.addEventListener('click', function(e) {
  if (!e.target.closest('.filter-popover')) closeAllPopovers();
  if (!e.target.closest('.settings-btn') && !e.target.closest('.settings-dropdown')) {
    document.getElementById('settings-dropdown').classList.remove('open');
    document.querySelector('.settings-btn')?.classList.remove('active');
  }
});

function toggleTag(el) {
  if (el.classList.contains('active')) {
    el.classList.remove('active');
    selectedTag = '';
  } else {
    document.querySelectorAll('.tag-filter .chip').forEach(c => c.classList.remove('active'));
    el.classList.add('active');
    selectedTag = el.dataset.tag;
  }
  loadEvents(1);
}

function toggleRecurringFilter() {
  showRecurring = document.getElementById('show-recurring').checked;
  localStorage.setItem('showRecurring', showRecurring ? '1' : '');
  document.getElementById('show-recurring-mobile').checked = showRecurring;
  loadEvents(1);
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

function renderFeaturedCard(e) {
  const tags = (e.tags || '').split(',').map(t => t.trim()).filter(Boolean);
  const locTags = tags.filter(t => locationTags.includes(t));
  const themeTags = tags.filter(t => themeTags.includes(t));
  const themeEmojis = themeTags.map(t => TAG_EMOJIS[t] || '📌').filter(Boolean);
  const emojiHtml = themeEmojis.length > 0 ? themeEmojis[0] : '📌';
  const badge = formatDateBadge(e.date_start);
  const path = '/events/' + e.id + '/' + slugify(e.title);
  return `<article class="featured-card" aria-label="${esc(e.title)}">
    <div class="fc-badge"><span class="fc-badge-day">${badge.day}.</span><span class="fc-badge-month">${badge.month}</span></div>
    <div class="fc-body">
      <span class="fc-emoji">${emojiHtml}</span>
      <h3 class="fc-title"><a href="${e.event_url ? esc(e.event_url) : path}"${e.event_url ? ' target="_blank" rel="noopener"' : ''}>${esc(e.title)}${e.event_url ? '<span class="ext-link">↗</span>' : ''}</a></h3>
      ${e.location ? `<div class="fc-location">📍 ${esc(locTags.length > 0 ? locTags[0] : e.location)}</div>` : ''}
    </div>
  </article>`;
}

function renderFeaturedSection(events) {
  if (!events || events.length === 0) return '';
  let html = '<section class="featured-section"><h2 class="featured-heading"><span class="featured-star">⭐</span> Empfohlen</h2><div class="featured-grid">';
  for (const e of events) html += renderFeaturedCard(e);
  html += '</div></section>';
  return html;
}

function renderFeaturedSectionToDOM(events) {
  const container = document.getElementById('featured-container');
  if (!container) return;
  const html = renderFeaturedSection(events);
  container.innerHTML = html;
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

async function loadEvents(page) {
  currentPage = page;
  const search = document.getElementById('search').value;
  const dateFrom = document.getElementById('date-from').value;
  const params = new URLSearchParams({page, per_page: 12, search});
  if (dateFrom) params.set('date_from', dateFrom);
  selectedThemes.forEach(t => params.append('tag', t));
  selectedLocations.forEach(t => params.append('tag', t));
  if (selectedOrganizer) params.set('organizer', selectedOrganizer);
  if (!showRecurring) params.set('hide_recurring', '1');
  showLoading();
  const r = await fetch(`/api/list?${params}`);
  const data = await r.json();
  totalPages = data.total_pages;
  renderEvents(data.events);
  renderPagination();
  updateStickyTop();
}

function updateStickyTop() {
  const filter = document.querySelector('.controls-wrap');
  if (!filter) return;
  const h = filter.offsetHeight;
  document.querySelectorAll('.date-separator').forEach(el => {
    el.style.setProperty('top', (h + 6) + 'px', 'important');
  });
}

let resizeTimer;
window.addEventListener('resize', () => {
  clearTimeout(resizeTimer);
  resizeTimer = setTimeout(updateStickyTop, 100);
});

function renderEvents(events) {
  const container = document.getElementById('events');
  const searchQuery = document.getElementById('search').value.trim();
  // Skip events without a date
  events = events.filter(e => e.date_start);
  let html = '';
  // If user is searching, prepend a CTA to ask the chatbot
  if (searchQuery) {
    const escapedQuery = esc(searchQuery);
    const jsSafe = escapedQuery.replace(/\\/g, '\\\\').replace(/'/g, "\\'");
    html += `<div class="chat-cta" onclick="openChatWithQuery('${jsSafe}')" style="cursor:pointer;background:var(--primary-light);border:1px solid var(--primary);border-radius:var(--radius-sm);padding:14px 16px;margin-bottom:8px;display:flex;align-items:center;gap:10px;grid-column:1/-1;">
      <span style="font-size:24px;flex-shrink:0;">🤖</span>
      <div>
        <div style="font-weight:600;font-size:14px;color:var(--text)">Frag den KI-Assistenten</div>
        <div style="font-size:12px;color:var(--text-muted);margin-top:2px">Stelle Fragen zu "<strong>${escapedQuery}</strong>" im Chat — z.B. nach Terminen, Orten oder Details</div>
      </div>
      <span style="font-size:18px;margin-left:auto;flex-shrink:0;">💬</span>
    </div>`;
  }
  if (events.length === 0) {
    container.innerHTML = html || '<div class="empty"><div class="empty-icon">🔍</div>Keine Veranstaltungen gefunden</div>';
    return;
  }
  let lastDate = '';
  for (const e of events) {
    if (e.date_start !== lastDate) {
      lastDate = e.date_start;
      const badge = formatDateBadge(e.date_start);
      html += `<div class="date-separator"><span class="date-sep-day">${badge.day}.</span><span class="date-sep-month"> ${badge.month}</span><span class="date-sep-date"> ${relativeDate(e.date_start)}</span></div>`;
    }
    const tags = e.tags ? e.tags.split(',').map(t => t.trim()) : [];
    const themeEmojis = tags.filter(t => TAG_EMOJIS[t]).map(t => TAG_EMOJIS[t]);
    let emojiHtml;
    if (themeEmojis.length === 0) {
      emojiHtml = '<span class="ce">📌</span>';
    } else if (themeEmojis.length === 2) {
      emojiHtml = `<span class="ce ce-tl">${themeEmojis[0]}</span><span class="ce ce-br ce-double">${themeEmojis[1]}</span>`;
    } else {
      emojiHtml = `<span class="ce">${themeEmojis[0]}</span>`;
    }
    const hasTwo = themeEmojis.length === 2 ? ' has-two' : '';
    const locTags = tags.filter(t => locationTags.includes(t));
    const detailHref = '/events/' + e.id + '/' + slugify(e.title);
    const detailLink = e.event_url ? `<a href="${detailHref}" class="detail-link" title="Details">🔗</a>` : '';
    html += `<article class="event${condensedMode ? ' condensed' : ''}" id="event-${e.id}" aria-label="${esc(e.title)}"${condensedMode ? ' onclick="this.classList.toggle(\'expanded\')"' : ''}>
      <div class="event-body">
        <h2><span class="cat-emojis${hasTwo}">${emojiHtml}</span><span class="cat-title">${e.event_url ? `<a href="${esc(e.event_url)}" target="_blank" rel="noopener" onclick="event.stopPropagation()">${esc(e.title)}<span class="ext-link">↗</span></a>` : `<a href="${detailHref}">${esc(e.title)}</a>`}${detailLink}<span class="condensed-location">${locTags.length > 0 ? locTags.map(t => ` 📍 ${esc(t)}`).join('') : (e.location ? ` 📍 ${esc(e.location)}` : '')}</span></span></h2>
        <div class="event-meta">
          ${e.time_raw ? `<span>🕐 ${esc(e.time_raw)}</span>` : ''}
          ${e.location ? `<span>📍 ${esc(e.location)}</span>` : ''}
        </div>
        ${e.description ? `<div class="event-desc">${esc(e.description)}</div>` : ''}
        ${e.organizer || locTags.length > 0 || condensedMode ? `<div class="event-tags">${e.organizer ? `<span class="tag tag-organizer">${esc(e.organizer)}</span>` : ''}${locTags.map(t => `<span class="tag tag-location">📍 ${esc(t)}</span>`).join('')}${condensedMode ? `<a href="${detailHref}" class="tag tag-detail" onclick="event.stopPropagation()">➡ Details</a>` : ''}</div>` : ''}
        ${e.recurring_group_id ? `<span class="recurring-toggle" onclick="event.stopPropagation();toggleRecurring(${e.id}, ${e.recurring_group_id}, this)">▸ Alle Termine</span><div id="recurring-${e.id}" class="recurring-list" style="display:none"></div>` : ''}
      </div>
    </article>`;
  }
  container.innerHTML = html;
}

async function toggleRecurring(eventId, groupId, el) {
  const list = document.getElementById('recurring-' + eventId);
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
  const r = await fetch('/api/same/' + groupId);
  const events = await r.json();
  list.innerHTML = '<table><tr><th>Datum</th><th>Zeit</th><th>Ort</th></tr>' + events.map(e =>
    `<tr><td>${fmtDate(e.date_start)}${e.date_end && e.date_end !== e.date_start ? '–' + fmtDate(e.date_end) : ''}</td><td>${esc(e.time_raw || '—')}</td><td>${esc(e.location || '?')}</td></tr>`
  ).join('') + '</table>';
  list.dataset.loaded = '1';
  list.style.display = 'block';
}

function renderPagination() {
  const el = document.getElementById('pagination');
  let html = '<nav aria-label="Seitennavigation">';
  html += `<button onclick="loadEvents(1)" ${currentPage <= 1 ? 'disabled' : ''}>« Erste</button>`;
  html += `<button onclick="loadEvents(${currentPage - 1})" ${currentPage <= 1 ? 'disabled' : ''}>‹ Zurück</button>`;
  html += `<span class="page-info" aria-current="page">Seite ${currentPage} von ${totalPages}</span>`;
  html += `<button onclick="loadEvents(${currentPage + 1})" ${currentPage >= totalPages ? 'disabled' : ''}>Weiter ›</button>`;
  html += `<button onclick="loadEvents(${totalPages})" ${currentPage >= totalPages ? 'disabled' : ''}>Letzte »</button>`;
  html += '</nav>';
  el.innerHTML = html;
}

function slugify(str) {
  if (!str) return '';
  return str.toLowerCase()
    .replace(/[ä]/g, 'ae').replace(/[ö]/g, 'oe').replace(/[ü]/g, 'ue').replace(/[ß]/g, 'ss')
    .replace(/[^a-z0-9]+/g, '-').replace(/^-+|-+$/g, '').substring(0, 80);
}

function esc(s) {
  if (!s) return '';
  const d = document.createElement('div');
  d.textContent = s;
  return d.innerHTML;
}

function toggleDark() {
  document.documentElement.classList.toggle('dark');
  const isDark = document.documentElement.classList.contains('dark');
  localStorage.setItem('dark', isDark ? '1' : '0');
  document.getElementById('dark-toggle').textContent = isDark ? '☀️' : '🌙';
}

  /* Dark mode init */
  (function initDark() {
    const saved = localStorage.getItem('dark');
    const prefersDark = window.matchMedia('(prefers-color-scheme: dark)').matches;
    const isDark = saved === '1' || (saved === null && prefersDark);
    if (isDark) {
      document.documentElement.classList.add('dark');
      document.getElementById('dark-toggle').textContent = '☀️';
    }
    window.matchMedia('(prefers-color-scheme: dark)').addEventListener('change', e => {
      if (localStorage.getItem('dark') !== null) return;
      if (e.matches) {
        document.documentElement.classList.add('dark');
        document.getElementById('dark-toggle').textContent = '☀️';
      } else {
        document.documentElement.classList.remove('dark');
        document.getElementById('dark-toggle').textContent = '🌙';
      }
    });
  })();

  document.getElementById('date-from').value = new Date().toISOString().slice(0, 10);
  if (localStorage.getItem('condensed')) {
    document.getElementById('condensed-toggle').checked = true;
    document.getElementById('condensed-toggle-mobile').checked = true;
    condensedMode = true;
  }
  if (localStorage.getItem('showRecurring') === '') {
    document.getElementById('show-recurring').checked = false;
    document.getElementById('show-recurring-mobile').checked = false;
    showRecurring = false;
  }
  loadTags();
  // Check for server-side rendered initial data
  const ssrData = document.getElementById('ssr-data');
  if (ssrData) {
    try {
      const data = JSON.parse(ssrData.textContent);
      if (data.events && data.events.length > 0 && data.totalPages > 0) {
        currentPage = data.page;
        totalPages = data.totalPages;
        // Seed locationTags/themeTags from SSR data so renderEvents can
        // identify district/theme tags before loadTags() completes.
        if (data.params) {
          if (data.params.districtKeys) locationTags = data.params.districtKeys;
          if (data.params.themeKeys) themeTags = data.params.themeKeys;
          applyFilterParams(data.params);
        }
        // Render featured section if data present (SSR may have already placed HTML,
        // but this ensures client-side consistency if SSR featured fetch failed)
        if (data.featuredEvents && data.featuredEvents.length > 0) {
          const featContainer = document.getElementById('featured-container');
          if (featContainer && !featContainer.querySelector('.featured-section')) {
            renderFeaturedSectionToDOM(data.featuredEvents);
          }
        }
        // Don't re-render events — keep the SSR HTML to avoid layout flash.
        // Just replace pagination with JS-driven buttons and set up state.
        renderPagination();
        // Clean up
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
