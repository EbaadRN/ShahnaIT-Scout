
// ============================================
// PROPOSAL REPORTS (Master Reporting Engine)
// ============================================
const rpState = { range: 'day', loaded: false };
const rpEl = (id) => document.getElementById(id);

function rpIsoToday() {
    const d = new Date();
    return d.getFullYear() + '-' + String(d.getMonth() + 1).padStart(2, '0') + '-' + String(d.getDate()).padStart(2, '0');
}

function rpSetRange(range) {
    rpState.range = range;
    document.querySelectorAll('#rpRangeSeg button').forEach((b) => b.classList.toggle('active', b.dataset.range === range));
    const custom = range === 'custom';
    rpEl('rpDateWrap').style.display = custom ? 'none' : '';
    rpEl('rpStartWrap').style.display = custom ? '' : 'none';
    rpEl('rpEndWrap').style.display = custom ? '' : 'none';
}

function rpParams(format) {
    const p = new URLSearchParams({ range: rpState.range, format: format || 'json' });
    if (rpState.range === 'custom') { p.set('start', rpEl('rpStart').value); p.set('end', rpEl('rpEnd').value); }
    else p.set('date', rpEl('rpDate').value);
    const hr = rpEl('rpHr').value.trim(), skill = rpEl('rpSkill').value.trim(), client = rpEl('rpClient').value.trim();
    if (hr) p.set('hr', hr);
    if (skill) p.set('skill', skill);
    if (client) p.set('client', client);
    return p.toString();
}

async function rpOpen() {
    if (!rpEl('rpDate').value) rpEl('rpDate').value = rpIsoToday();
    if (!rpEl('rpStart').value) rpEl('rpStart').value = rpEl('rpEnd').value = rpIsoToday();
    if (!rpState.loaded) {
        rpState.loaded = true;
        document.querySelectorAll('#rpRangeSeg button').forEach((b) => b.addEventListener('click', () => { rpSetRange(b.dataset.range); rpLoad(); }));
        ['rpDate', 'rpStart', 'rpEnd'].forEach((id) => rpEl(id).addEventListener('change', rpLoad));
        ['rpHr', 'rpSkill', 'rpClient'].forEach((id) => rpEl(id).addEventListener('keydown', (e) => { if (e.key === 'Enter') rpLoad(); }));
        try {
            const res = await fetch('/api/reports/filter-options', { credentials: 'same-origin' });
            if (res.ok) {
                const o = await res.json();
                const fill = (id, list) => { rpEl(id).innerHTML = ''; (list || []).forEach((v) => { const op = document.createElement('option'); op.value = v; rpEl(id).appendChild(op); }); };
                fill('rpHrList', o.hr); fill('rpClientList', o.clients);
                rpEl('rpHrWrap').style.display = o.see_all ? '' : 'none';    // recruiters only ever see their own proposals
            }
        } catch (e) { /* the datalists are optional */ }
    }
    rpLoad();
}

function rpReset() {
    rpSetRange('day');
    rpEl('rpDate').value = rpEl('rpStart').value = rpEl('rpEnd').value = rpIsoToday();
    rpEl('rpHr').value = rpEl('rpSkill').value = rpEl('rpClient').value = '';
    rpLoad();
}

async function rpLoad() {
    const summary = rpEl('rpSummary'), table = rpEl('rpTable');
    summary.textContent = 'Loading…';
    try {
        const res = await fetch('/api/reports/proposals?' + rpParams('json'), { credentials: 'same-origin' });
        const j = await res.json().catch(() => ({}));
        if (!res.ok) { summary.textContent = ''; table.innerHTML = ''; showToast(j.error || 'Could not load the report', 'error'); return; }
        summary.textContent = j.range.label + '  ·  ' + j.count + ' proposal' + (j.count === 1 ? '' : 's') + (j.truncated ? '  (first 5000 shown)' : '');
        table.textContent = '';
        const thead = table.createTHead().insertRow();
        j.columns.forEach((c) => { const th = document.createElement('th'); th.textContent = c; thead.appendChild(th); });
        const body = table.createTBody();
        if (!j.rows.length) {
            const td = body.insertRow().insertCell(); td.colSpan = j.columns.length; td.className = 'rp-empty';
            td.textContent = '📭 No proposals found for these filters.';
            return;
        }
        const labels = {}; j.groups.forEach((g) => { labels[g.date] = g.label + '  -  ' + g.count + ' proposal' + (g.count === 1 ? '' : 's'); });
        let last = null;
        j.rows.forEach((r) => {
            if (r._date !== last) {
                last = r._date;
                const td = body.insertRow().insertCell(); td.colSpan = j.columns.length; td.className = 'rp-band'; td.textContent = labels[last] || last;
            }
            const tr = body.insertRow();
            j.columns.forEach((c) => { tr.insertCell().textContent = r[c] || ''; });     // textContent: tracker values are never rendered as HTML
        });
    } catch (e) {
        summary.textContent = '';
        showToast('Network error while loading the report', 'error');
    }
}

async function rpDownload(format) {
    const btn = rpEl(format === 'xlsx' ? 'rpXlsxBtn' : 'rpPdfBtn');
    const label = btn.textContent; btn.disabled = true; btn.textContent = 'Preparing…';
    try {
        const res = await fetch('/api/reports/proposals?' + rpParams(format), { credentials: 'same-origin' });
        if (!res.ok) { const j = await res.json().catch(() => ({})); showToast(j.error || 'Download failed', 'error'); return; }
        const blob = await res.blob();
        const m = /filename="?([^";]+)"?/.exec(res.headers.get('Content-Disposition') || '');
        const a = document.createElement('a');
        a.href = URL.createObjectURL(blob); a.download = m ? m[1] : 'Proposals.' + format;
        document.body.appendChild(a); a.click(); a.remove();
        setTimeout(() => URL.revokeObjectURL(a.href), 4000);
    } catch (e) {
        showToast('Network error while downloading', 'error');
    } finally {
        btn.disabled = false; btn.textContent = label;
    }
}

const tabProposalReports = document.getElementById('tabProposalReports');
if (tabProposalReports) tabProposalReports.onclick = function () { showPanel('proposalReports'); rpOpen(); };
