(function () {
    'use strict';
    const HEADERS = ['Date of Submission', 'Candidate Name', 'Total Exp', 'Relevant Exp', 'Mobile No', 'Email ID',
        'Requirement (SIT-R-)', 'Client Name', 'HR who proposed', 'CCTC', 'ECTC', 'Location',
        'Onsite/Hybrid/Remote', 'Freelancing (Yes/No)', 'C2C/C2H/FTE', 'Last Working Day', 'Notice Period', 'Remarks'];
    const NL = String.fromCharCode(10), CR = String.fromCharCode(13), NBSP = String.fromCharCode(160);
    const state = { candidateId: null, sending: false, closeTimer: null };
    const $ = (id) => document.getElementById(id);
    const esc = (s) => String(s == null ? '' : s).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')
        .replace(/"/g, '&quot;').replace(/'/g, '&#39;');
    const cellText = (el) => (el.innerText || el.textContent || '').split(CR).join('').split(NBSP).join(' ').trim();
    const toast = (msg, type) => { if (typeof showToast === 'function') showToast(msg, type); };

    function parseList(v) {
        try { const x = typeof v === 'string' ? JSON.parse(v || '[]') : (v || []); return Array.isArray(x) ? x : []; }
        catch (e) { return []; }
    }
    const withYears = (v) => { const s = String(v == null ? '' : v).trim(); return /^[0-9]+([.][0-9]+)?$/.test(s) ? s + ' yrs' : s; };

    // ---- the first row, from the saved candidate record (same 18 columns as the Reports page) ----
    function todayLabel() {
        const d = new Date(), m = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'];
        return String(d.getDate()).padStart(2, '0') + '-' + m[d.getMonth()] + '-' + d.getFullYear();
    }
    function candidateRow(c) {
        const rel = String(c.relevant_exp || '').trim() || parseList(c.relevant_experience)
            .map((e) => (e && e.skill) ? e.skill + (e.years ? ' - ' + e.years + ' yrs' : '') : '').filter(Boolean).join(', ');
        const notice = parseInt(c.notice_period_days, 10);
        let hr = '';
        try { hr = (currentUser && (currentUser.full_name || currentUser.email)) || ''; } catch (e) { /* not logged in yet */ }
        const s = (v) => (v == null ? '' : String(v));
        return [
            todayLabel(),                                                  // Date of Submission
            [c.first_name, c.last_name].filter(Boolean).join(' ').trim(),  // Candidate Name
            withYears(c.years_of_experience),                              // Total Exp
            rel,                                                           // Relevant Exp
            s(c.phone),                                                    // Mobile No
            s(c.email),                                                    // Email ID
            s(c.proposed_requirement),                                     // Requirement (SIT-R-)
            s(c.proposed_client),                                          // Client Name
            hr,                                                            // HR who proposed
            s(c.current_ctc),                                              // CCTC
            s(c.expected_ctc),                                             // ECTC
            c.location || c.address || '',                                 // Location
            s(c.work_mode),                                                // Onsite/Hybrid/Remote
            s(c.freelancing),                                              // Freelancing (Yes/No)
            s(c.engagement_type),                                          // C2C/C2H/FTE
            s(c.last_working_day),                                         // Last Working Day
            notice > 0 ? notice + ' days' : '',                            // Notice Period
            '',                                                            // Remarks
        ];
    }

    // ---- table construction ----
    function cell(value, header) {
        const d = document.createElement('div');
        d.className = 'dp-c' + (header ? ' dp-hd' : '');
        d.contentEditable = 'true';
        d.spellcheck = false;
        d.textContent = value || '';
        return d;
    }
    function xButton(title, handler) {
        const b = document.createElement('button');
        b.type = 'button'; b.className = 'dp-x'; b.title = title; b.tabIndex = -1;
        b.setAttribute('aria-label', title); b.textContent = '✕';
        b.addEventListener('click', handler);
        return b;
    }
    const headRow = () => $('dpTable').querySelector('thead tr');
    const bodyRows = () => Array.from($('dpTable').querySelectorAll('tbody tr'));
    const colCount = () => headRow().querySelectorAll('th:not(.dp-ctl)').length;

    function addHeader(value) {
        const th = document.createElement('th');
        th.appendChild(cell(value, true));
        th.appendChild(xButton('Remove this column', () => removeCol(th)));
        headRow().insertBefore(th, headRow().querySelector('th.dp-ctl'));
    }
    function addBodyRow(values) {
        const tr = document.createElement('tr');
        const n = colCount();
        for (let i = 0; i < n; i++) { const td = document.createElement('td'); td.appendChild(cell(values ? values[i] : '', false)); tr.appendChild(td); }
        const ctl = document.createElement('td'); ctl.className = 'dp-ctl';
        ctl.appendChild(xButton('Remove this row', () => removeRow(tr)));
        tr.appendChild(ctl);
        $('dpTable').querySelector('tbody').appendChild(tr);
        return tr;
    }
    function buildTable(headers, rows) {
        const t = $('dpTable');
        t.innerHTML = '<thead><tr><th class="dp-ctl"></th></tr></thead><tbody></tbody>';   // th.dp-ctl = spacer above the row-delete buttons
        headers.forEach((h) => addHeader(h));
        rows.forEach((r) => addBodyRow(r));
    }
    function removeCol(th) {
        if (colCount() <= 1) { setStatus('err', 'The tracker needs at least one column.'); return; }
        const idx = Array.prototype.indexOf.call(headRow().children, th);
        th.remove();
        bodyRows().forEach((tr) => { if (tr.children[idx]) tr.children[idx].remove(); });
    }
    function removeRow(tr) {
        if (bodyRows().length <= 1) { Array.from(tr.querySelectorAll('.dp-c')).forEach((c) => (c.textContent = '')); return; }
        tr.remove();
    }
    window.dpAddRow = function () { const tr = addBodyRow(null); const c = tr.querySelector('.dp-c'); if (c) c.focus(); };
    window.dpAddCol = function () {
        addHeader('New column');
        const idx = colCount() - 1;
        bodyRows().forEach((tr) => {
            const td = document.createElement('td'); td.appendChild(cell('', false));
            tr.insertBefore(td, tr.children[idx]);
        });
        const hd = headRow().querySelectorAll('.dp-hd')[idx]; if (hd) { hd.focus(); document.execCommand && document.execCommand('selectAll'); }
    };

    // ---- the table as simple, safe HTML (the server re-parses and re-renders it anyway) ----
    function tableHtml() {
        const heads = Array.from($('dpTable').querySelectorAll('thead .dp-hd')).map(cellText);
        const rows = bodyRows().map((tr) => Array.from(tr.querySelectorAll('.dp-c')).map(cellText)).filter((r) => r.some((v) => v !== ''));
        const c = (tag, v) => '<' + tag + '>' + esc(v).split(NL).join('<br>') + '</' + tag + '>';
        return '<table><thead><tr>' + heads.map((h) => c('th', h)).join('') + '</tr></thead><tbody>' +
            rows.map((r) => '<tr>' + r.map((v) => c('td', v)).join('') + '</tr>').join('') + '</tbody></table>';
    }

    // ---- status + busy state ----
    function setStatus(kind, msg) {
        const s = $('dpStatus');
        s.className = 'dp-status' + (kind ? ' ' + kind : '');
        s.textContent = '';
        if (!msg) return;
        if (kind === 'busy') { const sp = document.createElement('span'); sp.className = 'dp-spin'; s.appendChild(sp); }
        s.appendChild(document.createTextNode(msg));
    }
    function setSending(on) {
        state.sending = on;
        $('dpSendBtn').disabled = on; $('dpCancelBtn').disabled = on;
        $('dpSendBtn').textContent = on ? 'Sending…' : '📤 Send';
    }

    // ---- open / close ----
    window.openDispatchModal = function () {
        const c = (typeof currentCandidateData !== 'undefined') ? currentCandidateData : null;
        if (!c || !c.id) { toast('Open a candidate profile first.', 'error'); return; }
        clearTimeout(state.closeTimer);
        state.candidateId = c.id;
        const name = [c.first_name, c.last_name].filter(Boolean).join(' ').trim();
        $('dpCandidateLabel').textContent = name;
        buildTable(HEADERS, [candidateRow(c)]);
        $('dpRecipient').value = '';
        $('dpReplyTo').value = '';
        $('dpSubject').value = 'Profile Proposal - ' + (name || 'Candidate');
        $('dpMask').checked = false;
        $('dpBlank').value = 0;
        setStatus('');
        setSending(false);
        $('dispatchModal').style.display = 'block';
        $('dpRecipient').focus();
    };
    window.dpClose = function () {
        if (state.sending) return;
        clearTimeout(state.closeTimer);
        $('dispatchModal').style.display = 'none';
    };
    document.addEventListener('keydown', (e) => {
        if (e.key === 'Escape' && $('dispatchModal') && $('dispatchModal').style.display === 'block') window.dpClose();
    });
    document.addEventListener('paste', (e) => {          // keep cells plain text: no rich HTML from Word/web pages
        if (!e.target.closest || !e.target.closest('#dpTable .dp-c')) return;
        e.preventDefault();
        const t = (e.clipboardData || window.clipboardData).getData('text/plain');
        document.execCommand('insertText', false, t);
    });

    // ---- send ----
    window.dpSend = async function () {
        if (state.sending) return;
                const emailRe = /^[^@,; ]+@[^@,; ]+[.][^@,; ]{2,}$/;
        const list = $('dpRecipient').value.split(/[,;]/).map((s) => s.trim()).filter(Boolean);
        const badAddr = list.find((a) => !emailRe.test(a));
        if (!list.length || badAddr) {
            setStatus('err', badAddr ? '"' + badAddr + '" is not a valid email address.' : 'Please enter at least one recipient email address.');
            $('dpRecipient').focus(); return;
        }
        if (list.length > 10) { setStatus('err', 'You can send to at most 10 recipients at a time.'); $('dpRecipient').focus(); return; }
        const email = list.join(', ');
        const replyTo = $('dpReplyTo').value.trim();
        if (replyTo && !emailRe.test(replyTo)) {
            setStatus('err', 'The Reply-To address is not a valid email address.'); $('dpReplyTo').focus(); return;
        }
        const mask = $('dpMask').checked;
        let blank = parseInt($('dpBlank').value, 10); if (!(blank >= 0)) blank = 0; blank = Math.min(blank, 10);
        if (!mask && !window.confirm('Phone and email WILL be included in the resume sent to ' + email + '.' + NL + NL + 'Continue?')) return;

        const payload = {
            candidate_id: state.candidateId,
            recipient_email: email,
            reply_to_email: replyTo,
            email_subject: $('dpSubject').value.trim(),
            table_html: tableHtml(),
            mask_contact_details: mask,
            add_blank_projects: blank,
        };
        setSending(true);
        setStatus('busy', 'Generating the resume and sending the email…');
        const ctl = new AbortController(); const timer = setTimeout(() => ctl.abort(), 60000);
        try {
            const res = await fetch('/api/dispatch-proposal', {
                method: 'POST', headers: { 'Content-Type': 'application/json' },
                credentials: 'same-origin', body: JSON.stringify(payload), signal: ctl.signal,
            });
            let j = {}; try { j = await res.json(); } catch (e) { /* non-JSON error page */ }
            if (res.status === 401) {
                setStatus('err', 'Your session has expired. Please log in again, then retry.');
            } else if (res.ok && j.success) {
                setStatus('ok', '✔ ' + (j.message || 'Proposal sent.'));
                toast(j.message || 'Proposal sent.', 'success');
                state.closeTimer = setTimeout(() => { setSending(false); window.dpClose(); }, 2500);
                return;
            } else {
                setStatus('err', j.error || ('Could not send the proposal (HTTP ' + res.status + ').'));
            }
        } catch (e) {
            setStatus('err', e && e.name === 'AbortError' ? 'The request timed out. Check your inbox log before retrying.' : 'Network error. Please try again.');
        } finally {
            clearTimeout(timer);
        }
        setSending(false);
    };
})();
