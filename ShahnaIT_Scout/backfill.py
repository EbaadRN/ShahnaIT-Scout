"""One-time backfill: fills EMPTY current_company / designation / current_role from each candidate's stored resume text."""
import sqlite3
from flask import Blueprint, jsonify, request, session
import nlp_engine

bp = Blueprint('backfill', __name__)
DB_PATH = '/data/shahnai.db'


@bp.route('/api/admin/backfill-candidates', methods=['GET'])
def backfill_candidates():
    if (session.get('role') or '').lower() != 'admin':
        return jsonify({'error': 'Admin only'}), 403
    dry = request.args.get('dry') == '1'
    after = int(request.args.get('after') or 0)
    limit = max(1, min(int(request.args.get('limit') or 5), 20))
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    c.execute("SELECT id, first_name, last_name, resume_text, current_company, designation, current_role FROM candidates "
              "WHERE id > ? AND (COALESCE(current_company,'')='' OR COALESCE(designation,'')='') AND COALESCE(resume_text,'')<>'' "
              "ORDER BY id LIMIT ?", (after, limit))
    rows = c.fetchall()
    updated, skipped, preview = 0, 0, []
    for r in rows:
        try:
            p = nlp_engine.parse_resume(r['resume_text'][:6000])
        except Exception:
            p = {'error': 'parse failed'}
        if p.get('error'):
            skipped += 1
            continue
        company = r['current_company'] or p.get('current_company') or ''
        desig = r['designation'] or p.get('designation') or ''
        role = r['current_role'] or p.get('current_role') or ''
        if (company, desig, role) == ((r['current_company'] or ''), (r['designation'] or ''), (r['current_role'] or '')):
            continue
        updated += 1
        preview.append({'id': r['id'], 'name': f"{r['first_name']} {r['last_name']}", 'company': company, 'designation': desig})
        if not dry:
            c.execute('UPDATE candidates SET current_company = ?, designation = ?, current_role = ? WHERE id = ?', (company, desig, role, r['id']))
    if not dry:
        conn.commit()
    last_id = rows[-1]['id'] if rows else after
    conn.close()
    nxt = f"/api/admin/backfill-candidates?after={last_id}" + ("&dry=1" if dry else "")
    return jsonify({'dry_run': dry, 'checked': len(rows), 'updated': updated, 'skipped': skipped, 'preview': preview,
                    'finished': len(rows) < limit, 'next_page': None if len(rows) < limit else nxt})
    dry = request.args.get('dry') == '1'
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    c.execute("SELECT id, first_name, last_name, resume_text, current_company, designation, current_role FROM candidates "
              "WHERE (COALESCE(current_company,'')='' OR COALESCE(designation,'')='') AND COALESCE(resume_text,'')<>''")
    rows = c.fetchall()
    updated, skipped, preview = 0, 0, []
    for r in rows:
        try:
            p = nlp_engine.parse_resume(r['resume_text'])
        except Exception:
            p = {'error': 'parse failed'}
        if p.get('error'):
            skipped += 1
            continue
        company = r['current_company'] or p.get('current_company') or ''
        desig = r['designation'] or p.get('designation') or ''
        role = r['current_role'] or p.get('current_role') or ''
        if (company, desig, role) == ((r['current_company'] or ''), (r['designation'] or ''), (r['current_role'] or '')):
            continue
        updated += 1
        if len(preview) < 25:
            preview.append({'id': r['id'], 'name': f"{r['first_name']} {r['last_name']}", 'company': company, 'designation': desig})
        if not dry:
            c.execute('UPDATE candidates SET current_company = ?, designation = ?, current_role = ? WHERE id = ?', (company, desig, role, r['id']))
    if not dry:
        conn.commit()
    conn.close()
    return jsonify({'dry_run': dry, 'checked': len(rows), 'updated': updated, 'skipped': skipped, 'preview': preview})
