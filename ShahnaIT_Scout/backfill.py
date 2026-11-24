"""One-time backfill: fills EMPTY current_company / designation / current_role from each candidate's stored resume text."""
import json
import os
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
    ids = [int(x) for x in (request.args.get('ids') or '').split(',') if x.strip().isdigit()]
    if ids:  # redo mode: re-parse exactly these candidates and overwrite their company/designation
        c.execute("SELECT id, first_name, last_name, resume_text, current_company, designation, current_role FROM candidates "
                  "WHERE id IN (%s) AND COALESCE(resume_text,'')<>'' ORDER BY id" % ",".join("?" * len(ids)), ids)
    else:
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
        company = (p.get('current_company') or '') if ids else (r['current_company'] or p.get('current_company') or '')
        desig = (p.get('designation') or '') if ids else (r['designation'] or p.get('designation') or '')
        role = (p.get('current_role') or '') if ids else (r['current_role'] or p.get('current_role') or '')
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
                    'finished': bool(ids) or len(rows) < limit, 'next_page': None if ids or len(rows) < limit else nxt})
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
        company = (p.get('current_company') or '') if ids else (r['current_company'] or p.get('current_company') or '')
        desig = (p.get('designation') or '') if ids else (r['designation'] or p.get('designation') or '')
        role = (p.get('current_role') or '') if ids else (r['current_role'] or p.get('current_role') or '')
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


@bp.route('/api/admin/drive-check', methods=['GET'])
def drive_check():
    """Diagnoses the Google Drive backup: env var, libraries, folder access, and a real 1-byte upload (deleted right after)."""
    if (session.get('role') or '').lower() != 'admin':
        return jsonify({'error': 'Admin only'}), 403
    out = {}
    raw = os.environ.get('GOOGLE_SERVICE_ACCOUNT', '')
    out['env_set'] = bool(raw)
    if not raw:
        out['problem'] = 'GOOGLE_SERVICE_ACCOUNT is not set on Railway.'
        return jsonify(out)
    try:
        sa = json.loads(raw)
        out['service_account_email'] = sa.get('client_email')
    except Exception as e:
        out['problem'] = 'GOOGLE_SERVICE_ACCOUNT is not valid JSON: ' + str(e)[:150]
        return jsonify(out)
    try:
        from google.oauth2 import service_account
        from googleapiclient.discovery import build
        from googleapiclient.errors import HttpError
        from googleapiclient.http import MediaInMemoryUpload
    except ImportError as e:
        out['problem'] = 'Google libraries are missing: ' + str(e) + '. Add google-api-python-client and google-auth to requirements.txt.'
        return jsonify(out)
    folder_id = os.environ.get('GOOGLE_DRIVE_FOLDER_ID') or '0ANhiqKbE7xeZUk9PVA'
    out['folder_id'] = folder_id
    try:
        creds = service_account.Credentials.from_service_account_info(sa, scopes=['https://www.googleapis.com/auth/drive'])
        svc = build('drive', 'v3', credentials=creds, cache_discovery=False)
    except Exception as e:
        out['problem'] = 'Could not sign in with the service account key: ' + str(e)[:200]
        return jsonify(out)
    try:
        f = svc.files().get(fileId=folder_id, fields='id,name,mimeType,driveId,owners(emailAddress),capabilities(canAddChildren)', supportsAllDrives=True).execute()
        out['folder'] = {'name': f.get('name'), 'is_folder': f.get('mimeType') == 'application/vnd.google-apps.folder',
                         'in_shared_drive': bool(f.get('driveId')), 'owner': [o.get('emailAddress') for o in f.get('owners', [])],
                         'service_account_can_add_files': (f.get('capabilities') or {}).get('canAddChildren')}
    except HttpError as e:
        out['problem'] = 'The service account cannot see this folder (wrong folder ID, or the folder is not shared with the service account email above): ' + str(e)[:200]
        return jsonify(out)
    except Exception as e:
        out['problem'] = 'Folder lookup failed: ' + str(e)[:200]
        return jsonify(out)
    try:
        media = MediaInMemoryUpload(b'drive check', mimetype='text/plain')
        made = svc.files().create(body={'name': 'drive-check.txt', 'parents': [folder_id]}, media_body=media, supportsAllDrives=True, fields='id').execute()
        out['upload'] = 'OK - the service account can upload to this folder'
        try:
            svc.files().delete(fileId=made['id'], supportsAllDrives=True).execute()
            out['cleanup'] = 'test file removed'
        except Exception as ce:
            out['cleanup'] = 'could not auto-delete the test file (delete drive-check.txt by hand): ' + str(ce)[:120]
    except Exception as e:
        msg = str(e)
        out['upload_error'] = msg[:400]
        if 'storage quota' in msg.lower() or 'storagequotaexceeded' in msg.lower():
            out['problem'] = ('Service accounts have no storage of their own, so they cannot create files in a normal My Drive folder. '
                              'Use a folder inside a Shared Drive (service account added as a member), or have the service account act as a real user.')
    return jsonify(out)
