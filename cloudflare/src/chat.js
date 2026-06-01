
// ── Chatbox ───────────────────────────────────────────────────────────
let chatInjected = false;
function injectChat() {
  if (chatInjected) return;
  chatInjected = true;
  // Inject chat CSS
  const style = document.createElement('style');
  style.textContent =
    '.chat-sidebar{width:50%;max-width:520px;min-width:340px;display:none;flex-direction:column;background:var(--card-bg);border-left:1px solid var(--border);overflow:hidden}' +
    '.chat-sidebar.open{display:flex}' +
    '@media(min-width:901px){.chat-open{display:flex;flex-direction:row;height:100vh;overflow:hidden}.chat-open .page-left{overflow-y:auto;height:100vh}.chat-open .chat-sidebar{height:100vh}.chat-open header{padding:6px 16px}.chat-open .schdudesee-logo{height:44px}}' +
    '.chat-sidebar .chat-header{background:var(--primary);color:#fff;padding:12px 16px;font-weight:600;font-size:15px;display:flex;align-items:center;gap:8px;flex-shrink:0}' +
    '.chat-sidebar .chat-header span{flex:1}' +
    '.chat-sidebar .chat-close{background:none;border:none;color:#fff;font-size:20px;cursor:pointer;padding:0 4px;opacity:0.8}' +
    '.chat-sidebar .chat-close:hover{opacity:1}' +
    '.chat-sidebar .chat-messages{flex:1;overflow-y:auto;padding:12px;display:flex;flex-direction:column;gap:8px;scroll-behavior:smooth}' +
    '.chat-sidebar .chat-msg{max-width:85%;padding:8px 12px;border-radius:12px;font-size:13px;line-height:1.5;word-wrap:break-word;animation:fadeInUp 0.2s ease}' +
    '.chat-sidebar .chat-msg.user{background:var(--primary);color:#fff;align-self:flex-end;border-bottom-right-radius:4px}' +
    '.chat-sidebar .chat-msg.assistant{background:var(--primary-light);color:var(--text);align-self:flex-start;border-bottom-left-radius:4px}' +
    '.chat-sidebar .chat-msg.system{background:var(--gold-light);color:var(--tag-org-text);align-self:center;font-size:12px;padding:4px 10px;border-radius:8px}' +
    '.chat-sidebar .chat-msg .event-card{background:var(--card-bg);border:1px solid var(--border);border-radius:8px;padding:8px 10px;margin-top:6px;cursor:pointer;transition:box-shadow 0.2s}' +
    '.chat-sidebar .chat-msg .event-card:hover{box-shadow:0 2px 8px rgba(0,0,0,0.1)}' +
    '.chat-sidebar .chat-msg .event-card .ev-title{font-weight:600;font-size:13px;color:var(--text)}' +
    '.chat-sidebar .chat-msg .event-card .ev-meta{font-size:11px;color:var(--text-muted);margin-top:2px}' +
    '.chat-sidebar .chat-msg .event-card .ev-desc{font-size:11px;color:var(--desc-text);margin-top:2px;display:-webkit-box;-webkit-line-clamp:2;-webkit-box-orient:vertical;overflow:hidden}' +
    '.chat-sidebar .chat-input-wrap{display:flex;gap:8px;padding:10px 12px;border-top:1px solid var(--border);flex-shrink:0}' +
    '.chat-sidebar .chat-input{flex:1;border:1.5px solid var(--border);border-radius:20px;padding:8px 14px;font-size:13px;font-family:inherit;background:var(--bg);color:var(--text);outline:none;transition:border-color 0.2s}' +
    '.chat-sidebar .chat-input:focus{border-color:var(--primary)}' +
    '.chat-sidebar .chat-send{width:36px;height:36px;border-radius:50%;background:var(--primary);color:#fff;border:none;cursor:pointer;font-size:16px;display:flex;align-items:center;justify-content:center;flex-shrink:0;transition:background 0.2s}' +
    '.chat-sidebar .chat-send:hover{background:var(--primary-dark,var(--primary))}' +
    '.chat-sidebar .chat-send:disabled{opacity:0.5;cursor:default}' +
    '.chat-sidebar .chat-loading{display:flex;align-items:center;gap:6px;padding:8px 12px;font-size:12px;color:var(--text-muted)}' +
    '.chat-sidebar .chat-loading .dots{display:flex;gap:3px}' +
    '.chat-sidebar .chat-loading .dots span{width:6px;height:6px;border-radius:50%;background:var(--text-muted);animation:bounce 1.4s ease-in-out infinite}' +
    '.chat-sidebar .chat-loading .dots span:nth-child(2){animation-delay:0.16s}' +
    '.chat-sidebar .chat-loading .dots span:nth-child(3){animation-delay:0.32s}' +
    '@keyframes bounce{0%,80%,100%{transform:scale(0)}40%{transform:scale(1)}}' +
    '@media(max-width:900px){.chat-sidebar{position:fixed;top:0;left:0;right:auto;width:100%;max-width:none;height:100%;z-index:999;border-left:none;border-radius:0;animation:slideUp 0.25s ease}@keyframes slideUp{from{transform:translateY(20px);opacity:0}to{transform:translateY(0);opacity:1}}}';
  document.head.appendChild(style);
  const mount = document.getElementById('chat-mount');
  if (!mount) return;
  mount.innerHTML =
    '<aside class="chat-sidebar" id="chat-sidebar">' +
      '<div class="chat-header">' +
        '<span>🤖 Veranstaltungs-Chat</span>' +
        '<button type="button" class="chat-close" aria-label="Chat schließen" onclick="toggleChat()">✕</button>' +
      '</div>' +
      '<div class="chat-messages" id="chat-messages">' +
        '<div class="chat-msg assistant">Hallo! Ich bin der KI-Assistent für "Hey, Stutensee!". Du kannst mich nach Veranstaltungen fragen, z.B. "Was ist am Wochenende los?" oder "Gibt es Sportevents im Juni?".</div>' +
      '</div>' +
      '<div class="chat-input-wrap">' +
        '<input class="chat-input" id="chat-input" type="text" placeholder="Frage nach Veranstaltungen..." aria-label="Nachricht eingeben" onkeydown="if(event.key===\'Enter\')sendChat()">' +
        '<button type="button" class="chat-send" id="chat-send" aria-label="Nachricht senden" onclick="sendChat()">➤</button>' +
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
    .replace(/[^a-z0-9]+/g, '-').replace(/^-|-$/g, '');
}

