
// ── Chatbox ───────────────────────────────────────────────────────────
let chatInjected = false;
function injectChat() {
  if (chatInjected) return;
  chatInjected = true;
  // Inject chat CSS
  const style = document.createElement('style');
  style.textContent =
    '.chat-sidebar{width:min(440px,46vw);min-width:340px;display:none;flex-direction:column;background:var(--surface);border-left:1px solid var(--border);overflow:hidden}' +
    '.chat-sidebar.open{display:flex}' +
    '@media(min-width:961px){.chat-open .chat-sidebar{height:100vh}}' +
    '.chat-sidebar .chat-header{display:flex;align-items:center;gap:10px;padding:14px 16px;background:var(--navy,#0d3a71);color:#fff;flex-shrink:0}' +
    '.chat-sidebar .chat-header-icon{display:grid;place-items:center;width:32px;height:32px;border-radius:9px;background:rgba(255,255,255,.14);flex:none}' +
    '.chat-sidebar .chat-header-icon svg{width:17px;height:17px}' +
    '.chat-sidebar .chat-header-copy{display:flex;flex-direction:column;line-height:1.2;flex:1;min-width:0}' +
    '.chat-sidebar .chat-header-title{font-size:14px;font-weight:700;letter-spacing:-.1px}' +
    '.chat-sidebar .chat-header-sub{font-size:10.5px;font-weight:600;letter-spacing:.08em;text-transform:uppercase;color:rgba(255,255,255,.6)}' +
    '.chat-sidebar .chat-close{display:grid;place-items:center;width:30px;height:30px;padding:0;border:1px solid rgba(255,255,255,.2);border-radius:8px;background:rgba(255,255,255,.08);color:#fff;cursor:pointer;transition:background .18s}' +
    '.chat-sidebar .chat-close:hover{background:rgba(255,255,255,.2)}' +
    '.chat-sidebar .chat-close svg{width:14px;height:14px}' +
    '.chat-sidebar .chat-messages{flex:1;overflow-y:auto;padding:16px;display:flex;flex-direction:column;gap:10px;background:var(--bg);scroll-behavior:smooth}' +
    '.chat-sidebar .chat-msg{max-width:88%;padding:10px 13px;border-radius:14px;font-size:13.5px;line-height:1.55;word-wrap:break-word}' +
    '.chat-sidebar .chat-msg.user{background:var(--navy,#0d3a71);color:#fff;align-self:flex-end;border-bottom-right-radius:5px}' +
    '.chat-sidebar .chat-msg.assistant{background:var(--surface);color:var(--text);border:1px solid var(--border);align-self:flex-start;border-bottom-left-radius:5px}' +
    '.chat-sidebar .chat-msg.system{background:var(--gold-light);color:var(--gold-ink);align-self:center;font-size:12px;padding:5px 11px;border-radius:9px}' +
    '.chat-sidebar .chat-msg .event-card{background:var(--surface-2);border:1px solid var(--border);border-radius:10px;padding:9px 11px;margin-top:7px;cursor:pointer;transition:border-color .18s,box-shadow .18s}' +
    '.chat-sidebar .chat-msg .event-card:hover{border-color:var(--border-strong);box-shadow:var(--shadow-sm)}' +
    '.chat-sidebar .chat-msg .event-card .ev-title{font-weight:650;font-size:13px;color:var(--text)}' +
    '.chat-sidebar .chat-msg .event-card .ev-meta{font-size:11.5px;color:var(--text-muted);margin-top:2px}' +
    '.chat-sidebar .chat-msg .event-card .ev-desc{font-size:11.5px;color:var(--text-muted);margin-top:3px;display:-webkit-box;-webkit-line-clamp:2;-webkit-box-orient:vertical;overflow:hidden}' +
    '.chat-sidebar .chat-input-wrap{display:flex;align-items:center;gap:8px;padding:12px;border-top:1px solid var(--border);background:var(--surface);flex-shrink:0}' +
    '.chat-sidebar .chat-input{flex:1;height:40px;border:1px solid var(--border);border-radius:11px;padding:0 13px;font-size:13.5px;font-family:inherit;background:var(--surface-2);color:var(--text);outline:none;transition:border-color .18s,box-shadow .18s}' +
    '.chat-sidebar .chat-input:focus{border-color:var(--navy,#0d3a71);box-shadow:var(--ring);background:var(--surface)}' +
    '.chat-sidebar .chat-send{width:40px;height:40px;border-radius:11px;background:var(--navy,#0d3a71);color:#fff;border:none;cursor:pointer;display:grid;place-items:center;flex-shrink:0;transition:background .18s,transform .18s}' +
    '.chat-sidebar .chat-send svg{width:16px;height:16px}' +
    '.chat-sidebar .chat-send:hover{background:var(--navy-deep,#0a2c56)}' +
    '.chat-sidebar .chat-send:active{transform:scale(.96)}' +
    '.chat-sidebar .chat-send:disabled{opacity:.45;cursor:default}' +
    '.chat-sidebar .chat-loading{display:flex;align-items:center;gap:7px;padding:8px 12px;font-size:12px;color:var(--text-muted)}' +
    '.chat-sidebar .chat-loading .dots{display:flex;gap:3px}' +
    '.chat-sidebar .chat-loading .dots span{width:6px;height:6px;border-radius:50%;background:var(--text-faint);animation:bounce 1.4s ease-in-out infinite}' +
    '.chat-sidebar .chat-loading .dots span:nth-child(2){animation-delay:.16s}' +
    '.chat-sidebar .chat-loading .dots span:nth-child(3){animation-delay:.32s}' +
    '@keyframes bounce{0%,80%,100%{transform:scale(0)}40%{transform:scale(1)}}' +
    '@media(max-width:960px){.chat-sidebar{position:fixed;inset:0;width:100%;min-width:0;max-width:none;height:100%;z-index:999;border-left:none}}';
  document.head.appendChild(style);
  const mount = document.getElementById('chat-mount');
  if (!mount) return;
  mount.innerHTML =
    '<aside class="chat-sidebar" id="chat-sidebar" aria-label="KI-Chat">' +
      '<div class="chat-header">' +
        '<span class="chat-header-icon" aria-hidden="true"><svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><path d="M21 11.5a8.4 8.4 0 0 1-8.5 8.5 9 9 0 0 1-3.8-.9L3 21l1.9-5.7A8.5 8.5 0 0 1 12.5 3 8.4 8.4 0 0 1 21 11.5z"/></svg></span>' +
        '<span class="chat-header-copy"><span class="chat-header-title">Termine-Chat</span><span class="chat-header-sub">KI-Assistent</span></span>' +
        '<button type="button" class="chat-close" aria-label="Chat schließen" onclick="toggleChat()"><svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round"><path d="M18 6 6 18M6 6l12 12"/></svg></button>' +
      '</div>' +
      '<div class="chat-messages" id="chat-messages">' +
        '<div class="chat-msg assistant">Hallo! Ich bin der KI-Assistent für „Hey, Stutensee!“. Frag mich nach Veranstaltungen – zum Beispiel „Was ist am Wochenende los?“ oder „Gibt es Sportevents im Juni?“.</div>' +
      '</div>' +
      '<div class="chat-input-wrap">' +
        '<input class="chat-input" id="chat-input" type="text" placeholder="Frage nach Veranstaltungen…" aria-label="Nachricht eingeben" onkeydown="if(event.key===\'Enter\')sendChat()">' +
        '<button type="button" class="chat-send" id="chat-send" aria-label="Nachricht senden" onclick="sendChat()"><svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M22 2 11 13M22 2l-7 20-4-9-9-4z"/></svg></button>' +
      '</div>' +
    '</aside>';
}

function toggleChat() {
  injectChat();
  const sidebar = document.getElementById('chat-sidebar');
  if (!sidebar) return;
  const isOpen = sidebar.classList.toggle('open');
  document.body.classList.toggle('chat-open', isOpen);
  // Focus input when opening
  if (isOpen) {
    const input = document.getElementById('chat-input');
    if (input) setTimeout(() => input.focus(), 100);
    if (window.innerWidth >= 901) {
      document.querySelector('.page-left')?.scrollTo(0, 0);
    }
  }
}

function openChatWithQuery(query) {
  injectChat();
  const sidebar = document.getElementById('chat-sidebar');
  if (!sidebar) return;
  sidebar.classList.add('open');
  document.body.classList.add('chat-open');
  const input = document.getElementById('chat-input');
  if (query && input) {
    input.value = query;
    sendChat();
  }
}

function addChatMessage(role, content, events) {
  const msgs = document.getElementById('chat-messages');
  const div = document.createElement('div');
  div.className = 'chat-msg ' + role;
  
  if (typeof content === 'string') {
    // Escape HTML to prevent XSS, then apply markdown-like formatting
    const escaped = esc(content);
    const formatted = escaped
      .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
      .replace(/\n/g, '<br>');
    div.innerHTML = formatted;
  } else {
    div.textContent = content;
  }
  
  if (events && events.length > 0) {
    events.forEach(ev => {
      const card = document.createElement('div');
      card.className = 'event-card';
      card.onclick = function() { window.location.href = '/events/' + ev.id + '/' + slugify(ev.title); };
      const dateStr = ev.date_start ? fmtDate(ev.date_start) + (ev.date_end && ev.date_end !== ev.date_start ? ' – ' + fmtDate(ev.date_end) : '') : '';
      card.innerHTML = '<div class="ev-title">' + esc(ev.title) + '</div>' +
        '<div class="ev-meta">' + dateStr + (ev.location ? ' · ' + esc(ev.location) : '') + '</div>' +
        (ev.description ? '<div class="ev-desc">' + esc(ev.description.substring(0, 100)) + '</div>' : '');
      div.appendChild(card);
    });
  }
  
  msgs.appendChild(div);
  msgs.scrollTop = msgs.scrollHeight;
}

function showChatLoading() {
  const msgs = document.getElementById('chat-messages');
  const div = document.createElement('div');
  div.className = 'chat-msg assistant chat-loading';
  div.id = 'chat-loading';
  div.innerHTML = '<span>Denke nach</span><span class="dots"><span></span><span></span><span></span></span>';
  msgs.appendChild(div);
  msgs.scrollTop = msgs.scrollHeight;
}

function hideChatLoading() {
  const el = document.getElementById('chat-loading');
  if (el) el.remove();
}

async function sendChat() {
  injectChat();
  const input = document.getElementById('chat-input');
  const sendBtn = document.getElementById('chat-send');
  if (!input || !sendBtn) return;
  const text = input.value.trim();
  if (!text || sendBtn.disabled) return;
  
  sendBtn.disabled = true;
  input.value = '';
  addChatMessage('user', text);
  showChatLoading();
  
  // Gather conversation history
  const msgs = document.getElementById('chat-messages');
  const messageNodes = msgs.querySelectorAll('.chat-msg:not(.chat-loading)');
  const messages = [];
  for (const node of messageNodes) {
    if (node.classList.contains('user')) {
      messages.push({ role: 'user', content: node.textContent });
    } else if (node.classList.contains('assistant') && !node.classList.contains('system')) {
      // Skip loading and system
      const eventCards = node.querySelectorAll('.event-card');
      if (eventCards.length === 0) {
        // Only add if there was text content
        const txt = node.textContent.trim();
        if (txt) messages.push({ role: 'assistant', content: txt });
      }
    }
  }
  
  try {
    const resp = await fetch('/api/chat', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ messages }),
    });
    const data = await resp.json();
    hideChatLoading();
    sendBtn.disabled = false;
    
    if (data.error) {
      addChatMessage('system', '❌ ' + data.error);
      return;
    }
    
    const msg = data.message;
    if (msg.content) {
      addChatMessage('assistant', msg.content, data.events || []);
    }
  } catch (err) {
    hideChatLoading();
    sendBtn.disabled = false;
    addChatMessage('system', '❌ Fehler: ' + err.message);
  }
}

function slugify(str) {
  if (!str) return '';
  return str.toLowerCase()
    .replace(/[ä]/g, 'ae').replace(/[ö]/g, 'oe').replace(/[ü]/g, 'ue').replace(/[ß]/g, 'ss')
    .replace(/[^a-z0-9]+/g, '-').replace(/^-+|-+$/g, '').substring(0, 80);
}

