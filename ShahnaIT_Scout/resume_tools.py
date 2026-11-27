"""Admin tool: re-read every candidate's ORIGINAL resume file with the new extractor.

Older candidates were saved with text from the old PDF/DOCX reader (broken spacing, DOCX tables
missing), which hurts both parsing and JD matching. This rebuilds `resume_text` from the stored file.

    /api/admin/reextract-resumes?dry=1            preview (changes nothing)
    /api/admin/reextract-resumes                  update resume_text only (safe: never touches edited fields)
    /api/admin/reextract-resumes?mode=fill        also fill fields that are still EMPTY (name, phone, company, skills ...)
    &after=<id>&limit=<n>                         batches (default 10, max 25); follow "next_page" until finished
"""
import json
import os
import sqlite3

from flask import Blueprint, jsonify, request, session

import nlp_engine

bp = Blueprint('resume_tools', __name__)
DB_PATH = '/data/shahnai.db'
_ROOTS = ('/data',)


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
    s = str(v).strip()
    return s in ('', '[]', '{}', '0', '0.0', 'null', 'None')


@bp.route('/api/admin/reextract-resumes', methods=['GET'])
def reextract_resumes():
    if (session.get('role') or '').lower() != 'admin':
        return jsonify({'error': 'Admin only'}), 403
    dry = request.args.get('dry') == '1'
    fill = request.args.get('mode') == 'fill'
    after = int(request.args.get('after') or 0)
    limit = max(1, min(int(request.args.get('limit') or 10), 25))
    conn = sqlite3.connect(DB_PATH, timeout=30)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    c.execute('PRAGMA table_info(candidates)')
    cols = {r[1] for r in c.fetchall()}
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
        updates = {}
        old = r['resume_text'] or ''
        if text != old:
            updates['resume_text'] = text[:60000]
        if fill:
            p = nlp_engine.parse_resume(text, filename=r['resume_original_filename'] if 'resume_original_filename' in cols else None)
            if not p.get('error'):
                simple = {'first_name': p.get('first_name'), 'middle_name': p.get('middle_name'), 'last_name': p.get('last_name'),
                          'email': p.get('email'), 'phone': p.get('phone'), 'linkedin': p.get('linkedin'), 'location': p.get('location'),
                          'designation': p.get('designation'), 'current_role': p.get('current_role'), 'current_company': p.get('current_company'),
                          'years_of_experience': p.get('years_of_experience')}
                lists = {'core_skills': p.get('core_skills'), 'education': p.get('education'), 'work_experience': p.get('work_experience'),
                         'certifications': p.get('certifications')}
                for k, v in simple.items():
                    if k in cols and _empty(r[k]) and not _empty(v):
                        updates[k] = v
                for k, v in lists.items():
                    if k in cols and _empty(r[k]) and v:
                        updates[k] = json.dumps(v)
        if not updates:
            continue
        if 'resume_text' in updates:
            report['text_updated'] += 1
        filled = [k for k in updates if k != 'resume_text']
        report['fields_filled'] += len(filled)
        report['preview'].append({'id': r['id'], 'name': ('%s %s' % (r['first_name'] or '', r['last_name'] or '')).strip(),
                                  'text_chars_before': len(old), 'text_chars_after': len(text), 'filled': filled})
        if not dry:
            sets = ', '.join('%s = ?' % k for k in updates)
            c.execute('UPDATE candidates SET %s WHERE id = ?' % sets, list(updates.values()) + [r['id']])
    if not dry:
        conn.commit()
    last_id = rows[-1]['id'] if rows else after
    conn.close()
    finished = len(rows) < limit
    q = '/api/admin/reextract-resumes?after=%d' % last_id + ('&dry=1' if dry else '') + ('&mode=fill' if fill else '')
    report.update({'dry_run': dry, 'mode': 'fill' if fill else 'text', 'finished': finished, 'next_page': None if finished else q})
    return jsonify(report)
