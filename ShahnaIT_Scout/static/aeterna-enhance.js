/* =========================================================================
   ShahnaIT Scout × Aeterna — progressive enhancement layer.
   Loaded (deferred) after Scout's own script. It never touches the database,
   the API, or Scout's business logic: it re-skins what Scout renders and
   replaces only the Kanban *view* (same /api/candidates calls, same payload).
   ========================================================================= */
(function () {
  'use strict';
  if (window.__aeterna) return;
  window.__aeterna = true;

  /* ------------------------------ helpers -------------------------------- */
  const esc = (s) => (typeof window.escapeHtml === 'function' ? window.escapeHtml(String(s ?? '')) :
    String(s ?? '').replace(/[&<>"']/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c])));
  const $ = (s, r = document) => r.querySelector(s);
  const toast = (msg, kind) => {
    const fn = window['toast' + (kind === 'error' ? 'Error' : 'Success')];
    if (typeof fn === 'function') fn(msg); else console.log(msg);
  };
  const candidatesCache = () => (typeof allCandidates !== 'undefined' && Array.isArray(allCandidates) ? allCandidates : []);

  const ICON = {
    users: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round"><path d="M16 20v-1.5a3.5 3.5 0 0 0-3.5-3.5h-5A3.5 3.5 0 0 0 4 18.5V20"/><circle cx="10" cy="8" r="3.5"/><path d="M20 20v-1.4a3.5 3.5 0 0 0-2.5-3.35M15.5 4.7a3.5 3.5 0 0 1 0 6.6"/></svg>',
    briefcase: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round"><rect x="3" y="7" width="18" height="13" rx="2.5"/><path d="M9 7V5.5A1.5 1.5 0 0 1 10.5 4h3A1.5 1.5 0 0 1 15 5.5V7M3 13h18"/></svg>',
    calendar: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round"><rect x="3.5" y="5" width="17" height="15" rx="2.5"/><path d="M8 3v4M16 3v4M3.5 10h17"/></svg>',
    inbox: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round"><path d="M3 13l2.6-7.2A2 2 0 0 1 7.5 4.5h9a2 2 0 0 1 1.9 1.3L21 13v5a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z"/><path d="M3 13h5l1 2.5h6L16 13h5"/></svg>',
    file: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round"><path d="M14 3H7a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h10a2 2 0 0 0 2-2V8z"/><path d="M14 3v5h5M9 13h6M9 17h6"/></svg>',
    mail: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="3" y="5" width="18" height="14" rx="2.5"/><path d="m3.5 7 8.5 6 8.5-6"/></svg>',
    phone: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M5 4h4l2 5-2.5 1.5a11 11 0 0 0 5 5L15 13l5 2v4a2 2 0 0 1-2 2A16 16 0 0 1 3 6a2 2 0 0 1 2-2"/></svg>',
    link: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M10 14a4 4 0 0 0 5.7 0l3-3a4 4 0 0 0-5.7-5.7l-1 1M14 10a4 4 0 0 0-5.7 0l-3 3A4 4 0 0 0 11 18.7l1-1"/></svg>',
    pin: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M12 21s7-5.6 7-11a7 7 0 0 0-14 0c0 5.4 7 11 7 11z"/><circle cx="12" cy="10" r="2.5"/></svg>',
    clock: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="9"/><path d="M12 7v5l3 2"/></svg>',
    download: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M12 4v11m0 0-4-4m4 4 4-4M5 20h14"/></svg>',
    eye: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M2 12s3.6-7 10-7 10 7 10 7-3.6 7-10 7S2 12 2 12z"/><circle cx="12" cy="12" r="3"/></svg>',
    copy: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="9" y="9" width="11" height="11" rx="2"/><path d="M5 15V6a2 2 0 0 1 2-2h8"/></svg>',
    grip: '<svg viewBox="0 0 12 16" fill="currentColor"><circle cx="3" cy="3" r="1.3"/><circle cx="9" cy="3" r="1.3"/><circle cx="3" cy="8" r="1.3"/><circle cx="9" cy="8" r="1.3"/><circle cx="3" cy="13" r="1.3"/><circle cx="9" cy="13" r="1.3"/></svg>',
  };

  /* ----------------------- match score components ------------------------ */
  const tier = (n) => (n >= 70 ? 'hi' : n >= 40 ? 'mid' : 'lo');
  const num = (v) => { const n = Math.round(Number(v)); return Number.isFinite(n) && n > 0 ? Math.min(n, 100) : 0; };

  function matchPill(score) {
    const n = num(score);
    return n ? `<span class="ae-match ${tier(n)}" title="AI match against the job description">Match Score: ${n}%</span>`
             : `<span class="ae-match none" title="Run Analyze Match to score this candidate">Match Score: —</span>`;
  }
  function ring(score, size = 84, stroke = 7) {
    const n = num(score), r = (size - stroke) / 2, c = 2 * Math.PI * r;
    return `<span class="ae-ring ${n ? tier(n) : ''}" style="width:${size}px;height:${size}px;font-size:${Math.round(size * .27)}px">
      <svg width="${size}" height="${size}" viewBox="0 0 ${size} ${size}" fill="none">
        <circle class="trk" cx="${size / 2}" cy="${size / 2}" r="${r}" stroke-width="${stroke}"/>
        <circle class="val" cx="${size / 2}" cy="${size / 2}" r="${r}" stroke-width="${stroke}" stroke-dasharray="${c}" stroke-dashoffset="${c * (1 - n / 100)}"/>
      </svg><b>${n ? n + '%' : '—'}</b></span>`;
  }

  /* ------------------------------ empty states --------------------------- */
  const EMPTY = {
    candidates: { icon: 'users', title: 'No candidates yet', text: 'Upload a resume to start building your talent pipeline. Candidates you add will appear here.', cta: ['Upload a resume', 'tabUpload'] },
    jobs: { icon: 'briefcase', title: 'No jobs yet', text: 'Create your first job requirement and Scout will start matching candidates against it.', cta: ['Create a job', 'tabCreateJob'] },
    interviews: { icon: 'calendar', title: 'No interviews scheduled', text: 'Scheduled interviews will show up here with their status and verdicts.', cta: null },
    generic: { icon: 'inbox', title: 'Nothing here yet', text: 'Once there is something to show, it will appear on this screen.', cta: null },
  };
  window.aeEmpty = function (kind, o = {}) {
    const d = Object.assign({}, EMPTY[kind] || EMPTY.generic, o);
    const cta = d.cta && document.getElementById(d.cta[1]) ? `<button class="ae-btn" type="button" onclick="document.getElementById('${d.cta[1]}').click()">${esc(d.cta[0])}</button>` : '';
    return `<div class="ae-empty${d.compact ? ' compact' : ''}" role="status"><div class="ae-empty-icon">${ICON[d.icon] || ICON.inbox}</div><h3>${esc(d.title)}</h3><p>${esc(d.text)}</p>${cta}</div>`;
  };
  const EMPTY_RE = /^\W*no\s+([a-z ]{3,40}?)\s*(?:found|yet|available|scheduled|uploaded|to show)?[.!]*$/i;
  const KIND_WORDS = [['candidate', 'candidates'], ['resume', 'candidates'], ['job', 'jobs'], ['requirement', 'jobs'], ['interview', 'interviews'],
                      ['onboard', 'generic'], ['client', 'generic'], ['invoice', 'generic'], ['expense', 'generic'], ['payslip', 'generic'], ['user', 'generic']];
  function convertEmpty(root) {
    const hosts = root.matches?.('.card.no-click, div, p') ? [root] : [];
    root.querySelectorAll?.('.card.no-click, div, p').forEach((n) => hosts.push(n));
    for (const n of hosts) {
      if (n.closest('.ae-empty, .modal, .card-details, table, select, label, button')) continue;
      const txt = (n.textContent || '').trim();
      if (txt.length > 60 || !EMPTY_RE.test(txt)) continue;
      if (n.querySelector('.card, input, button, select')) continue;
      const hit = KIND_WORDS.find(([w]) => txt.toLowerCase().includes(w));
      if (!hit) continue;
      const target = n.closest('.card.no-click') || n;
      if ((target.textContent || '').trim().length > 70) continue;
      const kind = hit[1];
      const opts = kind === 'generic' ? { title: txt.replace(/[.!]+$/, '').replace(/^\W+/, ''), text: 'This list will fill up as you add data.', compact: true } : {};
      target.outerHTML = window.aeEmpty(kind, opts);
    }
  }

  /* ---------------- recolour hard-coded legacy inline styles ------------- */
  const SETS = {
    navy: ['1b2a4a', '0f1d33', '1a1a2e', '16213e', '2c4270', '3b5998', '4361ee', '1a4d4a', '3f37c9', '1a237e', '0d9488'],
    pale: ['f0f4fa', 'f5f7fa', 'fafbfc', 'f2f5f9', 'e8edf5', 'f8f9fa', 'f1f3f4', 'e8f0fe', 'eef2f7', 'f9fafb', 'f8fafc'],
    grey: ['555', '555555', '666', '666666', '64748b', '5a6f8a', '2c3e5a', '5f6368', '475569', '4b5563'],
    faint: ['999', '999999', '94a3b8', '777', '777777', 'aaa', '888', '9ca3af'],
    line: ['d0d8e4', 'e2e8f0', 'a0b0c8', 'ddd', 'dddddd', 'e0e0e0', 'eee', 'e5e7eb', 'cbd5e1', 'ccc'],
    gold: ['c9a96e'], white: ['fff', 'ffffff'], blue: ['1a73e8', '2196f3', '1976d2', '3b82f6'],
    orange: ['ff9800', 'f59e0b', 'ff5722', 'ea580c'], green: ['4caf50', '10b981', '0d7b4a', '2c7a4a', '22c55e', '1b6b2e'], red: ['f44336', 'ef4444', 'c42020', 'dc2626'], purple: ['9c27b0', '6b4cb8', '8b5cf6'],
  };
  const lookup = {};
  Object.entries(SETS).forEach(([k, arr]) => arr.forEach((h) => (lookup[h] = k)));
  const HEX = /#([0-9a-f]{6}|[0-9a-f]{3})\b/gi;
  function mapHex(prop, m, h) {
    const k = lookup[h.toLowerCase()];
    if (!k) return m;
    if (prop === 'color') return ({ navy: 'var(--ae-ink)', grey: 'var(--ae-muted)', faint: 'var(--ae-faint)', blue: 'var(--teal-light)', orange: 'var(--ae-warn)', green: 'var(--ae-ok)', red: 'var(--ae-bad)', purple: 'var(--ae-muted)' })[k] || m;
    if (prop.startsWith('background')) return ({ navy: 'var(--ae-fill)', gold: 'var(--ae-fill)', pale: 'var(--ae-surface)', white: 'var(--ae-surface)', line: 'var(--ae-line)',
      blue: '#5d7c80', orange: '#b08d4f', green: '#2f6f5e', red: '#9c3f37', purple: '#7a6a86' })[k] || m;
    if (prop.startsWith('border') || prop === 'outline') return ({ line: 'var(--ae-line)', navy: 'var(--teal-light)', pale: 'var(--ae-line)' })[k] || m;
    return m;
  }
  function recolor(el) {
    const s = el.getAttribute && el.getAttribute('style');
    if (!s || s.indexOf('#') === -1 || el.dataset.aeRc) return;
    const out = s.replace(/([a-z-]+)\s*:\s*([^;]+)/gi, (full, prop, val) => prop.toLowerCase() + ':' + val.replace(HEX, (m, h) => mapHex(prop.toLowerCase(), m, h)));
    if (out !== s) el.setAttribute('style', out);
    el.dataset.aeRc = '1';
  }

  /* --------------------- candidate list: match score pill ---------------- */
  function decorateCandidateCards(root) {
    root.querySelectorAll?.('.candidate-card:not([data-ae-m])').forEach((card) => {
      card.dataset.aeM = '1';
      const badge = card.querySelector('.score-badge');
      const meta = card.querySelector('.candidate-meta');
      const host = meta || card.querySelector('.card-body');
      if (host) host.insertAdjacentHTML('afterbegin', matchPill(badge ? parseInt(badge.textContent, 10) : 0));
    });
  }

  /* --------------------------- profile hero (modal) ---------------------- */
  const url = (u) => { u = String(u || '').trim(); return !u ? '' : /^https?:\/\//i.test(u) ? u : 'https://' + u; };
  async function resumeAction(id, mode) {
    const base = `/api/candidates/${id}/${mode === 'view' ? 'view-resume' : 'download-resume'}`;
    try {
      const head = await fetch(base, { method: 'HEAD' });
      if (!head.ok) return toast('No resume file is stored for this candidate.', 'error');
    } catch (e) { /* network hiccup: let the browser try */ }
    window.open(base, '_blank');
  }
  window.aeResume = resumeAction;

  function buildHero(id) {
    const c = candidatesCache().find((x) => x.id == id);
    const body = document.getElementById('modalBody');
    if (!c || !body) return;
    body.querySelectorAll('.ae-hero, .ae-actions').forEach((n) => n.remove());
    const name = `${c.first_name || ''} ${c.last_name || ''}`.trim() || 'Unknown candidate';
    const role = c.designation || c.current_role || '';
    const yrs = c.years_of_experience ? `${esc(c.years_of_experience)} yrs experience` : '';
    const chips = [
      c.email && `<a class="ae-chip" href="mailto:${esc(c.email)}">${ICON.mail}<span>${esc(c.email)}</span></a>`,
      c.phone && `<a class="ae-chip" href="tel:${esc(String(c.phone).replace(/\s+/g, ''))}">${ICON.phone}<span>${esc(c.phone)}</span></a>`,
      c.linkedin && `<a class="ae-chip" href="${esc(url(c.linkedin))}" target="_blank" rel="noopener">${ICON.link}<span>LinkedIn</span></a>`,
      (c.location || c.address) && `<span class="ae-chip">${ICON.pin}<span>${esc(c.location || c.address)}</span></span>`,
      yrs && `<span class="ae-chip">${ICON.clock}<span>${yrs}</span></span>`,
    ].filter(Boolean).join('') || '<span class="ae-chip">No contact details on file</span>';

    const hero = document.createElement('div');
    hero.className = 'ae-hero';
    hero.innerHTML = `
      <div class="ae-hero-avatar" aria-hidden="true">${esc(name.charAt(0))}</div>
      <div style="min-width:0"><h2>${esc(name)}</h2><p class="role">${esc(role) || 'Role not specified'}</p><div class="ae-contact">${chips}</div></div>
      <div class="ae-hero-score">${ring(c.match_score, 92, 8)}<small>Match Score</small></div>`;
    const actions = document.createElement('div');
    actions.className = 'ae-actions';
    actions.innerHTML = `
      <button type="button" class="ae-btn is-primary" data-ae="dl">${ICON.download}Download resume</button>
      <button type="button" class="ae-btn outline" data-ae="view">${ICON.eye}View resume</button>
      <button type="button" class="ae-btn outline" data-ae="pdf">${ICON.file}Export profile PDF</button>
      ${c.email ? `<button type="button" class="ae-btn outline" data-ae="copy">${ICON.copy}Copy email</button>` : ''}`;
    actions.addEventListener('click', (e) => {
      const b = e.target.closest('[data-ae]'); if (!b) return;
      const k = b.dataset.ae;
      if (k === 'dl') resumeAction(id, 'download');
      else if (k === 'view') resumeAction(id, 'view');
      else if (k === 'pdf' && typeof window.exportPDF === 'function') window.exportPDF(id, e);
      else if (k === 'copy') navigator.clipboard?.writeText(c.email).then(() => toast('Email copied', 'success'));
    });
    body.insertBefore(actions, body.firstChild);
    body.insertBefore(hero, body.firstChild);
    const t = document.getElementById('modalCandidateName'); if (t) t.textContent = 'Candidate profile';
  }
  function hookViewCandidate() {
    const orig = window.viewCandidate;
    if (typeof orig !== 'function' || orig.__ae) return;
    window.viewCandidate = function (id) {
      const r = orig.apply(this, arguments);
      try { buildHero(id); } catch (e) { console.warn('[aeterna] hero', e); }
      return r;
    };
    window.viewCandidate.__ae = true;
  }

  /* -------------------------------- KANBAN ------------------------------- */
  const STAGE_DOT = { new: '#5d7c80', proposed: '#47696f', screening: '#b08d4f', technical_l1: '#2f5a61', technical_l2: '#2a5158', technical_l3: '#1f3a3f',
                      shortlisted: '#c4a15a', offer_letter_shared: '#2f6f5e', onboarded: '#1f4d40', rejected: '#9c3f37' };
  const FALLBACK_STAGES = [['new', 'New'], ['proposed', 'Proposed'], ['screening', 'Screening'], ['technical_l1', 'L1 Tech'], ['technical_l2', 'L2 Tech'],
                           ['technical_l3', 'L3 Tech'], ['shortlisted', 'Shortlisted'], ['offer_letter_shared', 'Offer'], ['onboarded', 'Onboarded'], ['rejected', 'Rejected']];
  const stages = () => (typeof kanbanStages !== 'undefined' && Array.isArray(kanbanStages) ? kanbanStages.map((s) => ({ id: s.id, name: s.name })) : FALLBACK_STAGES.map(([id, name]) => ({ id, name })));

  let kb = { drag: null, suppress: 0, data: [] };

  function cardHtml(c, j) {
    const name = `${c.first_name || ''} ${c.last_name || ''}`.trim() || 'Unknown';
    const when = c.created_at ? new Date(c.created_at).toLocaleDateString(undefined, { day: 'numeric', month: 'short' }) : '';
    return `<div class="ae-kcard" tabindex="0" role="button" data-id="${c.id}" data-name="${esc(name.toLowerCase())}" style="--j:${Math.min(j, 8)}" aria-label="${esc(name)}. Alt plus left or right arrow moves stage.">
      <span class="ae-kgrip" title="Drag to move">${ICON.grip}</span>
      <div style="min-width:0"><div class="ae-kname">${esc(name)}</div><div class="ae-krole">${esc(c.designation || c.current_role || 'Role not specified')}</div></div>
      <div class="ae-kfoot" style="grid-column:2">${matchPill(c.match_score)}<span class="ae-kdate">${esc(when)}</span></div></div>`;
  }
  function renderBoard(board, list) {
    const st = stages();
    const known = new Set(st.map((s) => s.id));
    board.innerHTML = st.map((s, i) => {
      const items = list.filter((c) => (known.has(c.stage || 'new') ? (c.stage || 'new') : 'new') === s.id);
      return `<section class="ae-col" data-stage="${s.id}" style="--i:${i};--dot:${STAGE_DOT[s.id] || '#5d7c80'}" aria-label="${esc(s.name)}">
        <header class="ae-col-head"><span class="ae-col-dot"></span><h3 class="ae-col-title">${esc(s.name)}</h3><span class="ae-col-count">${items.length}</span></header>
        <div class="ae-col-list">${items.map((c, k) => cardHtml(c, k)).join('')}<div class="ae-col-empty">Drop candidates here</div></div></section>`;
    }).join('');
  }
  function recount(board) {
    board.querySelectorAll('.ae-col').forEach((col) => {
      const n = col.querySelectorAll('.ae-kcard:not([hidden])').length;
      col.querySelector('.ae-col-count').textContent = n;
    });
  }

  window.loadKanban = async function () {
    const board = document.getElementById('kanbanBoard');
    if (!board) return;
    board.removeAttribute('style'); board.className = 'ae-board';
    const panel = board.parentElement;
    if (!panel.querySelector('.ae-ktools')) {
      panel.insertBefore(Object.assign(document.createElement('div'), {
        className: 'ae-ktools',
        innerHTML: '<input type="search" class="form-input" id="aeKSearch" placeholder="Filter by candidate name…" aria-label="Filter candidates"><span class="hint">Drag cards between stages · Alt + ← / → on a focused card also moves it</span>',
      }), board);
      $('#aeKSearch').addEventListener('input', (e) => {
        const q = e.target.value.trim().toLowerCase();
        board.querySelectorAll('.ae-kcard').forEach((k) => { k.hidden = !!q && !k.dataset.name.includes(q); });
        recount(board);
      });
    }
    board.innerHTML = stages().slice(0, 5).map(() => '<div class="ae-col" style="min-width:272px"><div class="ae-col-head"><span class="ae-col-title">&nbsp;</span></div><div class="ae-col-list"><div class="ae-skeleton"></div><div class="ae-skeleton"></div></div></div>').join('');
    try {
      const res = await fetch('/api/candidates');
      if (!res.ok) throw new Error('HTTP ' + res.status);
      const list = await res.json();
      kb.data = Array.isArray(list) ? list : [];
    } catch (err) {
      board.innerHTML = window.aeEmpty('generic', { title: 'Could not load the pipeline', text: 'Check your connection or sign in again, then retry.', compact: true });
      return;
    }
    if (!kb.data.length) { board.innerHTML = window.aeEmpty('candidates', { text: 'Your Kanban board will fill up as soon as you add candidates. Upload a resume to begin.' }); return; }
    renderBoard(board, kb.data);
    bindBoard(board);
  };

  async function moveCard(board, card, toStage) {
    const id = card.dataset.id, from = card.closest('.ae-col'), to = board.querySelector(`.ae-col[data-stage="${toStage}"]`);
    if (!to || from === to) return;
    const prevNext = card.nextElementSibling;
    to.querySelector('.ae-col-list').insertBefore(card, to.querySelector('.ae-col-empty'));
    card.classList.add('just-dropped'); setTimeout(() => card.classList.remove('just-dropped'), 600);
    recount(board);
    const label = to.getAttribute('aria-label');
    try {
      const r = await fetch('/api/candidates/' + id, { method: 'PUT', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ stage: toStage }) });
      const j = await r.json().catch(() => ({}));
      if (!r.ok || j.success === false) throw new Error(j.error || 'Update failed');
      const c = candidatesCache().find((x) => x.id == id); if (c) c.stage = toStage;
      const k = kb.data.find((x) => x.id == id); if (k) k.stage = toStage;
      toast(`Moved to ${label}`, 'success');
    } catch (err) {                       // roll back the optimistic move
      from.querySelector('.ae-col-list').insertBefore(card, prevNext && prevNext.parentNode === from.querySelector('.ae-col-list') ? prevNext : from.querySelector('.ae-col-empty'));
      recount(board);
      toast(err.message || 'Could not update stage', 'error');
    }
  }

  function bindBoard(board) {
    if (board.__bound) return; board.__bound = true;
    const colAt = (x, y) => { const e = document.elementFromPoint(x, y); return e && e.closest('.ae-col'); };
    const clear = () => board.querySelectorAll('.ae-col.is-over').forEach((c) => c.classList.remove('is-over'));

    board.addEventListener('pointerdown', (e) => {
      const card = e.target.closest('.ae-kcard');
      if (!card || (e.pointerType === 'mouse' && e.button !== 0)) return;
      if (e.pointerType === 'touch' && !e.target.closest('.ae-kgrip')) return;   // keep touch-scroll on the card body
      kb.drag = { card, x: e.clientX, y: e.clientY, on: false, ghost: null, dx: 0, dy: 0 };
    });
    window.addEventListener('pointermove', (e) => {
      const d = kb.drag; if (!d) return;
      if (!d.on) {
        if (Math.hypot(e.clientX - d.x, e.clientY - d.y) < 6) return;
        d.on = true;
        const rect = d.card.getBoundingClientRect();
        d.dx = e.clientX - rect.left; d.dy = e.clientY - rect.top;
        d.ghost = d.card.cloneNode(true); d.ghost.classList.add('ae-kghost'); d.ghost.classList.remove('is-dragging');
        d.ghost.style.animation = 'none'; d.ghost.style.width = rect.width + 'px';
        document.body.appendChild(d.ghost); d.card.classList.add('is-dragging'); document.body.classList.add('ae-dragging');
      }
      e.preventDefault();
      d.ghost.style.left = e.clientX - d.dx + 'px'; d.ghost.style.top = e.clientY - d.dy + 'px';
      clear(); const col = colAt(e.clientX, e.clientY); if (col) col.classList.add('is-over');
      const b = board.getBoundingClientRect();                                  // edge auto-scroll
      if (e.clientX > b.right - 70) board.scrollLeft += 16; else if (e.clientX < b.left + 70) board.scrollLeft -= 16;
      if (e.clientY > innerHeight - 60) scrollBy(0, 14); else if (e.clientY < 60) scrollBy(0, -14);
    }, { passive: false });
    const end = (e, cancel) => {
      const d = kb.drag; kb.drag = null; if (!d) return;
      if (!d.on) return;
      kb.suppress = Date.now() + 250;
      const col = cancel ? null : colAt(e.clientX, e.clientY);
      d.ghost.remove(); d.card.classList.remove('is-dragging'); document.body.classList.remove('ae-dragging'); clear();
      if (col) moveCard(board, d.card, col.dataset.stage);
    };
    window.addEventListener('pointerup', (e) => end(e, false));
    window.addEventListener('pointercancel', (e) => end(e, true));
    board.addEventListener('click', (e) => {
      if (Date.now() < kb.suppress) return;
      const card = e.target.closest('.ae-kcard');
      if (card && typeof window.viewCandidate === 'function') window.viewCandidate(+card.dataset.id);
    });
    board.addEventListener('keydown', (e) => {
      const card = e.target.closest('.ae-kcard'); if (!card) return;
      if (e.key === 'Enter') { window.viewCandidate?.(+card.dataset.id); return; }
      if (!e.altKey || !['ArrowLeft', 'ArrowRight'].includes(e.key)) return;
      e.preventDefault();
      const cols = [...board.querySelectorAll('.ae-col')], i = cols.indexOf(card.closest('.ae-col'));
      const next = cols[i + (e.key === 'ArrowRight' ? 1 : -1)];
      if (next) moveCard(board, card, next.dataset.stage).then(() => card.focus());
    });
    board.addEventListener('dragstart', (e) => e.preventDefault());
  }

  /* ----------------------------- footer + boot --------------------------- */
  function footer() {
    const mk = () => Object.assign(document.createElement('footer'), { className: 'ae-footer', innerHTML: 'An asset of <b>ShahnaIT</b>' });
    if (!$('body > .ae-footer')) document.body.appendChild(mk());
    const login = document.getElementById('loginOverlay');
    if (login && !login.querySelector('.ae-footer')) login.appendChild(mk());
  }
  function process(root) {
    if (root.nodeType !== 1) return;
    recolor(root); root.querySelectorAll('[style*="#"]').forEach(recolor);
    decorateCandidateCards(root.matches?.('.candidate-card') ? root.parentNode || root : root);
    convertEmpty(root);
  }

  function boot() {
    footer(); hookViewCandidate();
    if (window.Chart) { Chart.defaults.font.family = "'Source Sans 3', system-ui, sans-serif"; Chart.defaults.color = '#4f6e72'; }
    process(document.body);
    let queue = [], pending = false;
    new MutationObserver((muts) => {
      muts.forEach((m) => m.addedNodes.forEach((n) => n.nodeType === 1 && !n.classList?.contains('ae-footer') && queue.push(n)));
      if (!pending && queue.length) { pending = true; requestAnimationFrame(() => { const q = queue; queue = []; pending = false; q.forEach(process); }); }
    }).observe(document.body, { childList: true, subtree: true });
  }
  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', boot); else boot();
})();
