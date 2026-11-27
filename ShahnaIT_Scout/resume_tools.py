"""Admin tools: re-read candidates' ORIGINAL resume files with the new extractor / parser.

ONE CLICK FOR ALL CANDIDATES (runs in the background, safe to close the tab):
    /api/admin/reextract-all?dry=1      preview run - counts what would change, changes nothing
    /api/admin/reextract-all            real run
    /api/admin/reextract-status         progress + results (refresh this page)
  What the real run does for every candidate that has its original file:
    * replaces resume_text with the full, clean text (fixes JD matching for old candidates)
    * fills fields that are still EMPTY (phone, company, designation, skills ...)
    * if the saved NAME is clearly broken ('Professional Summary', 'Page N', '09/2023 Present', blank),
      re-parses that profile and corrects name, contact, designation, company, location and experience
  It never overwrites a valid name or any field your team has filled in.

Batch / single-ID tools (still available):
    /api/admin/reextract-resumes?dry=1 | ?mode=fill | &after=<id>&limit=<n>
    /api/admin/reextract-resumes?mode=redo&ids=10,11&dry=1     force re-parse of chosen IDs
"""
import json
import os
import re
import sqlite3
import threading
import time

from flask import Blueprint, jsonify, request, session

import nlp_engine

bp = Blueprint('resume_tools', __name__)
DB_PATH = '/data/shahnai.db'
STATUS_PATH = '/data/reextract_status.json'
_ROOTS = ('/data',)
_LOCK = threading.Lock()
_BASIC = ('first_name', 'middle_name', 'last_name', 'email', 'phone', 'linkedin', 'location', 'designation', 'current_role',
          'current_company', 'years_of_experience')
_LISTS = ('core_skills', 'education', 'work_experience', 'certifications')


def _safe(path):
    if not path:
        return None
    try:
        real = os.path.realpath(str(path))
    except (OSError, ValueError):
        return None
    if any(real.startswith(r + os.sep) for r in _ROOTS) and os.path.isfile(real):
        return real
    return None


def _empty(v):
    if v is None:
        return True
    return str(v).strip() in ('', '[]', '{}', '0', '0.0', 'null', 'None')


def name_is_broken(first, middle, last):
    """True for names the old parser got wrong: blank, headings, dates, labels, job titles."""
    full = ' '.join(str(x or '').strip() for x in (first, middle, last)).strip()
    if not full:
        return True
    if re.search(r'[:/()@\d|•]', full):
        return True
    toks = [t.strip(".-'") for t in full.split() if t.strip(".-'")]
    return not nlp_engine._valid_name(toks)


_TOK_OK = re.compile(r"[A-Za-z][A-Za-z.'\-]*$")


def _tc(s):
    out = []
    for w in s.split():
        if re.fullmatch(r"[A-Za-z]{2,}", w) and (w.isupper() or w.islower()):
            out.append(w[0].upper() + w[1:].lower())
        elif len(w) <= 2 or "." in w:
            out.append(w.upper())                         # initials: 'N.S', 'B.R.', 'K'
        else:
            out.append(w)
    return " ".join(out)


def _dedupe(tokens):
    out = []
    for t in tokens:
        if t and t.lower().strip(".") not in [x.lower().strip(".") for x in out]:
            out.append(t)
    return out


def _evidence(tokens, text, extra):
    """How many name tokens (3+ letters) are confirmed by the resume's top lines or the e-mail / LinkedIn / file name."""
    name_lines = [ln.lower() for ln in text.split("\n")[:40] if 0 < len(ln.split()) <= 6]   # names sit on short lines
    head = " | ".join(name_lines)
    blob = re.sub(r"[^a-z]", "", extra.lower())
    hits = 0
    for t in tokens:
        w = t.lower().strip(".")
        if len(w) >= 3 and (re.search(r"\b" + re.escape(w) + r"\b", head) or w in blob):
            hits += 1
    return hits


def _salvage_old_name(first, middle, last):
    """Old first/last look like a real name -> keep them (title-cased) and drop a junk middle name. Else None."""
    def ok(t):
        parts = t.split()
        return bool(parts) and len(parts) <= 2 and all(_TOK_OK.match(x) and x.lower().strip(".") not in nlp_engine._NAME_STOP for x in parts)
    f, m, l = (str(x or "").strip() for x in (first, middle, last))
    if not ok(f) or (l and not ok(l)):
        return None
    if l and l.lower() == f.lower():
        l = ""
    mid = m if (m and ok(m) and m.lower() not in (f.lower(), l.lower())) else ""
    return {"first_name": _tc(f), "middle_name": _tc(mid) if mid else "", "last_name": _tc(l) if l else ""}


def _process(r, cols, mode, text):
    """Return (updates dict, report item) for one candidate row."""
    updates = {}
    old = r['resume_text'] or ''
    if text != old:
        updates['resume_text'] = text[:60000]
    p = None
    broken = 'first_name' in cols and name_is_broken(r['first_name'], r['middle_name'] if 'middle_name' in cols else '', r['last_name'])
    if mode in ('fill', 'redo', 'auto'):
        p = nlp_engine.parse_resume(text, filename=r['resume_original_filename'] if 'resume_original_filename' in cols else None)
        if p.get('error'):
            p = None
    name_fix, review = None, False
    if mode == 'auto' and 'first_name' in cols:
        extra = ' '.join(str(x or '') for x in ((p or {}).get('email'), (p or {}).get('linkedin'), r['email'] if 'email' in cols else '',
                                                r['resume_original_filename'] if 'resume_original_filename' in cols else ''))
        pt = [x for x in ((p or {}).get('first_name'), (p or {}).get('middle_name'), (p or {}).get('last_name')) if x]
        p_ok = bool(pt) and not name_is_broken(*(pt + ['', ''])[:1], ' '.join(pt[1:-1]) if len(pt) > 2 else '', pt[-1] if len(pt) > 1 else '')
        p_ev = _evidence(pt, text, extra) if p_ok else 0
        if broken:
            salv = _salvage_old_name(r['first_name'], r['middle_name'] if 'middle_name' in cols else '', r['last_name'])
            ot = [x for x in (salv or {}).values() if x]
            o_ev = _evidence(ot, text, extra) if salv else 0
            if salv and o_ev >= 1 and o_ev >= p_ev:
                name_fix = salv
            elif p_ok and p_ev >= 1:
                name_fix = {'first_name': p.get('first_name'), 'middle_name': p.get('middle_name') or '', 'last_name': p.get('last_name') or ''}
            if not name_fix:
                review = True
        else:
            # valid single-word name -> add the surname only when the e-mail / LinkedIn / file name confirms it
            cur = [x for x in (r['first_name'], r['middle_name'] if 'middle_name' in cols else '', r['last_name']) if str(x or '').strip()]
            cur_l = [str(x).strip().lower() for x in cur]
            all_toks = ' '.join(str(x) for x in cur).split()
            if len(_dedupe(all_toks)) < len(all_toks):        # 'Srinivas Mogili Mogili' -> 'Srinivas Mogili'
                name_fix = {'first_name': all_toks[0], 'middle_name': ' '.join(all_toks[1:-1]), 'last_name': all_toks[-1] if len(all_toks) > 1 else ''}
            elif p_ok and len(cur) == 1 and len(pt) >= 2 and pt[0].lower() == cur_l[0]:
                added = [t for t in pt[1:] if len(t) >= 3]
                blob = re.sub(r"[^a-z]", "", extra.lower())
                if added and all(t.lower() in blob for t in added):
                    name_fix = {'first_name': r['first_name'], 'middle_name': p.get('middle_name') or '', 'last_name': p.get('last_name') or ''}
        if name_fix:
            toks = _dedupe(' '.join(str(name_fix[k] or '') for k in ('first_name', 'middle_name', 'last_name')).split())
            name_fix = {'first_name': _tc(toks[0]) if toks else '', 'last_name': _tc(toks[-1]) if len(toks) > 1 else '',
                        'middle_name': _tc(' '.join(toks[1:-1])) if len(toks) > 2 else ''}
            for k, v in name_fix.items():
                if k in cols and str(v) != str(r[k] or ''):
                    updates[k] = v
    if p:
        overwrite = mode == 'redo'
        for k in _BASIC:
            if k in ('first_name', 'middle_name', 'last_name') and mode != 'redo':
                continue                                  # names change only through the checked name logic above
            v = p.get(k)
            if k not in cols or _empty(v):
                continue
            if overwrite and str(v) != str(r[k] or ''):
                updates[k] = v
            elif _empty(r[k]):
                updates[k] = v
        for k in _LISTS:
            v = p.get(k)
            if k in cols and v and (overwrite or _empty(r[k])):
                updates[k] = json.dumps(v)
    item = {'id': r['id'], 'name': ' '.join(str(r[k] or '') for k in ('first_name', 'last_name')).strip(),
            'text_chars_before': len(old), 'text_chars_after': len(text), 'filled': [k for k in updates if k != 'resume_text']}
    if any(k in updates for k in ('first_name', 'middle_name', 'last_name')):
        item['old_name'] = ' '.join(str(r[k] or '') for k in ('first_name', 'middle_name', 'last_name') if k in cols).strip()
        item['new_name'] = ' '.join(str(updates.get(k, r[k] if k in cols else '') or '') for k in ('first_name', 'middle_name', 'last_name')).replace('  ', ' ').strip()
    if review:
        item['needs_review'] = True
    return updates, item


def _apply(c, cid, updates):
    sets = ', '.join('%s = ?' % k for k in updates)
    c.execute('UPDATE candidates SET %s WHERE id = ?' % sets, list(updates.values()) + [cid])


# ------------------------------------------------------------------ one click for everyone (background)
def _read_status():
    try:
        with open(STATUS_PATH) as fh:
            return json.load(fh)
    except Exception:
        return {}


def _write_status(st):
    tmp = STATUS_PATH + '.tmp'
    with open(tmp, 'w') as fh:
        json.dump(st, fh)
    os.replace(tmp, STATUS_PATH)


def _run_all(dry):
    st = {'state': 'running', 'dry_run': dry, 'started_at': time.strftime('%Y-%m-%d %H:%M:%S'), 'heartbeat': time.time(),
          'done': 0, 'total': 0, 'text_updated': 0, 'names_fixed': 0, 'fields_filled': 0, 'no_file': 0, 'unreadable': [],
          'tiny_text': [], 'fixed_names': [], 'names_need_review': [], 'errors': []}
    try:
        conn = sqlite3.connect(DB_PATH, timeout=30)
        conn.row_factory = sqlite3.Row
        c = conn.cursor()
        c.execute('PRAGMA table_info(candidates)')
        cols = {x[1] for x in c.fetchall()}
        c.execute('SELECT id FROM candidates ORDER BY id')
        ids = [x[0] for x in c.fetchall()]
        st['total'] = len(ids)
        _write_status(st)
        for n, cid in enumerate(ids, 1):
            try:
                c.execute('SELECT * FROM candidates WHERE id = ?', (cid,))
                r = c.fetchone()
                path = _safe(r['resume_file_path'] if r is not None and 'resume_file_path' in cols else None)
                if not path:
                    st['no_file'] += 1
                else:
                    try:
                        text = nlp_engine.extract_text(path)
                    except Exception:
                        text = ''
                    if len(text) < 60:
                        st['unreadable'].append(cid)
                    else:
                        if len(text) < 500:
                            st['tiny_text'].append(cid)
                        updates, item = _process(r, cols, 'auto', text)
                        if 'resume_text' in updates:
                            st['text_updated'] += 1
                        if item.get('new_name'):
                            st['names_fixed'] += 1
                            if len(st['fixed_names']) < 400:
                                st['fixed_names'].append([cid, item.get('old_name', item['name']), item['new_name']])
                        if item.get('needs_review') and len(st['names_need_review']) < 400:
                            st['names_need_review'].append([cid, ' '.join(str(r[k] or '') for k in ('first_name', 'middle_name', 'last_name') if k in cols).strip()])
                        st['fields_filled'] += len(item['filled'])
                        if updates and not dry:
                            _apply(c, cid, updates)
            except Exception as e:                       # one bad file never stops the run
                if len(st['errors']) < 50:
                    st['errors'].append([cid, str(e)[:120]])
            st['done'] = n
            if n % 20 == 0:
                if not dry:
                    conn.commit()
                st['heartbeat'] = time.time()
                _write_status(st)
        if not dry:
            conn.commit()
        conn.close()
        st['state'] = 'finished'
    except Exception as e:
        st['state'] = 'failed'
        st['errors'].append([0, str(e)[:200]])
    st['heartbeat'] = time.time()
    st['finished_at'] = time.strftime('%Y-%m-%d %H:%M:%S')
    _write_status(st)


@bp.route('/api/admin/reextract-all', methods=['GET'])
def reextract_all():
    if (session.get('role') or '').lower() != 'admin':
        return jsonify({'error': 'Admin only'}), 403
    dry = request.args.get('dry') == '1'
    with _LOCK:
        st = _read_status()
        if st.get('state') == 'running' and time.time() - float(st.get('heartbeat') or 0) < 180:
            return jsonify({'message': 'Already running - open /api/admin/reextract-status to watch progress', 'status': st})
        _write_status({'state': 'running', 'dry_run': dry, 'heartbeat': time.time(), 'done': 0, 'total': 0})
        threading.Thread(target=_run_all, args=(dry,), daemon=True).start()
    return jsonify({'message': ('Preview started' if dry else 'Started') + ' - open /api/admin/reextract-status and refresh it to watch progress'})


@bp.route('/api/admin/reextract-status', methods=['GET'])
def reextract_status():
    if (session.get('role') or '').lower() != 'admin':
        return jsonify({'error': 'Admin only'}), 403
    st = _read_status()
    if st.get('state') == 'running' and time.time() - float(st.get('heartbeat') or 0) > 180:
        st['state'] = 'stopped (server restarted) - open /api/admin/reextract-all again to continue; it is safe to repeat'
    if st.get('total'):
        st['percent'] = round(100.0 * st.get('done', 0) / st['total'], 1)
    return jsonify(st or {'state': 'not started'})


# ------------------------------------------------------------------ batch / chosen-ID tool
@bp.route('/api/admin/reextract-resumes', methods=['GET'])
def reextract_resumes():
    if (session.get('role') or '').lower() != 'admin':
        return jsonify({'error': 'Admin only'}), 403
    dry = request.args.get('dry') == '1'
    mode = request.args.get('mode') or 'text'
    mode = mode if mode in ('text', 'fill', 'redo') else 'text'
    ids = [int(x) for x in (request.args.get('ids') or '').split(',') if x.strip().isdigit()][:50]
    if mode == 'redo' and not ids:
        return jsonify({'error': 'mode=redo needs ids, e.g. ?mode=redo&ids=10,11&dry=1'}), 400
    after = int(request.args.get('after') or 0)
    limit = max(1, min(int(request.args.get('limit') or 10), 25))
    conn = sqlite3.connect(DB_PATH, timeout=30)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    c.execute('PRAGMA table_info(candidates)')
    cols = {r[1] for r in c.fetchall()}
    if ids:
        c.execute('SELECT * FROM candidates WHERE id IN (%s) ORDER BY id' % ','.join('?' * len(ids)), ids)
    else:
        c.execute('SELECT * FROM candidates WHERE id > ? ORDER BY id LIMIT ?', (after, limit))
    rows = c.fetchall()
    report = {'checked': len(rows), 'text_updated': 0, 'fields_filled': 0, 'no_file': [], 'unreadable': [], 'preview': []}
    for r in rows:
        path = _safe(r['resume_file_path'] if 'resume_file_path' in cols else None)
        if not path:
            report['no_file'].append(r['id'])
            continue
        try:
            text = nlp_engine.extract_text(path)
        except Exception:
            text = ''
        if len(text) < 60:
            report['unreadable'].append(r['id'])
            continue
        updates, item = _process(r, cols, mode, text)
        if not updates:
            continue
        if 'resume_text' in updates:
            report['text_updated'] += 1
        report['fields_filled'] += len(item['filled'])
        report['preview'].append(item)
        if not dry:
            _apply(c, r['id'], updates)
    if not dry:
        conn.commit()
    last_id = rows[-1]['id'] if rows else after
    conn.close()
    finished = bool(ids) or len(rows) < limit
    q = '/api/admin/reextract-resumes?after=%d' % last_id + ('&dry=1' if dry else '') + ('&mode=%s' % mode if mode != 'text' else '')
    report.update({'dry_run': dry, 'mode': mode, 'finished': finished, 'next_page': None if finished else q})
    return jsonify(report)
