"""
access_control.py - central role / ownership rules for ShahnaIT Scout.

Register ONCE in app.py (after the other blueprint lines):
    import access_control; access_control.init_access(app)

Roles:  admin  = everything
        manager = admin-style operational tabs (jobs, onboarded, exports), own candidates
        recruiter = own candidates only; no job/finance/onboarded data

What it enforces (server side, so hiding tabs is no longer the only protection):
  1. Session is re-checked on every request: disabled users are logged out at once,
     role/name changes (promotion, demotion, rename) apply immediately.
  2. Non-admins can only change candidates THEY uploaded (attachments, projects, education,
     status, propose, notes-delete, documents). Admin can change all.
  3. Non-admins cannot spoof the uploader on upload, nor re-assign ownership on edit.
  4. Manager editing a job no longer wipes budget / max salary (fields they cannot see).
  5. Recruiters never receive job budgets; /api/onboarded (salary, billing) is manager+.
  6. Job documents / JD parsing are manager+; CSV export is scoped to own candidates for recruiters.
  7. Admin user management: valid roles only, no self-lockout, never zero active admins,
     renaming a user keeps their candidates (ownership is by name).
"""
import csv
import io
import json
import re
import sqlite3

from flask import Response, g, jsonify, request, session

DB_PATH = '/data/shahnai.db'
ROLES = ('admin', 'manager', 'recruiter')
_SKIP_ENDPOINTS = {None, 'static', 'index', 'login', 'login_page', 'logout', 'get_me'}


def _db():
    conn = sqlite3.connect(DB_PATH, timeout=30)
    conn.row_factory = sqlite3.Row
    return conn


def _deny(msg, code=403):
    return jsonify({'success': False, 'error': msg}), code


def _role():
    return (session.get('role') or '').lower()


# ------------------------------------------------------------------ ownership helpers
def _owns(cand_id):
    """True if the logged-in user may change this candidate (admin, or uploader)."""
    if _role() == 'admin':
        return True
    name = (session.get('user_name') or '').strip()
    if not name:
        return False
    conn = _db()
    try:
        row = conn.execute('SELECT uploaded_by_name, uploaded_by FROM candidates WHERE id = ?',
                           (cand_id,)).fetchone()
    finally:
        conn.close()
    return bool(row) and name in ((row['uploaded_by_name'] or '').strip(), (row['uploaded_by'] or '').strip())


def _cand_from_child(table, row_id):
    conn = _db()
    try:
        row = conn.execute('SELECT candidate_id FROM %s WHERE id = ?' % table, (row_id,)).fetchone()
    finally:
        conn.close()
    return row['candidate_id'] if row else None


# ------------------------------------------------------------------ rule table
# (methods, path regex, kind, how-to-find-candidate)
_OWNER_RULES = [
    ({'POST', 'DELETE'}, r'^/api/candidates/(\d+)/attachments(?:/.*)?$', 'cand'),
    ({'POST'}, r'^/api/candidates/(\d+)/(?:projects|education-entries)$', 'cand'),
    ({'PUT'}, r'^/api/candidates/(\d+)/(?:propose|status)$', 'cand'),
    ({'PUT', 'DELETE'}, r'^/api/candidates/projects/(\d+)$', 'project'),
    ({'PUT', 'DELETE'}, r'^/api/candidates/education/(\d+)$', 'edu'),
    ({'DELETE'}, r'^/api/candidates/notes/(\d+)$', 'note'),
    ({'POST'}, r'^/api/candidates/upload-document$', 'form'),
]
_OWNER_RULES = [(m, re.compile(p), k) for m, p, k in _OWNER_RULES]

_MANAGER_RULES = [
    ({'POST'}, re.compile(r'^/api/jobs/(?:upload-document|parse-jd)$')),
    ({'DELETE'}, re.compile(r'^/api/jobs/documents/\d+$')),
    ({'GET'}, re.compile(r'^/api/onboarded$')),
]

_JOB_UPDATE_RE = re.compile(r'^/api/jobs/(\d+)$')
_JOB_COLS = ('title', 'company', 'description', 'roles_responsibilities', 'qualifications', 'required_skills',
             'certifications_required', 'working_mode', 'hybrid_days', 'office_location', 'business_model',
             'payroll_company', 'client_name', 'end_client', 'years_of_experience', 'budget', 'max_salary',
             'headcount')
_USER_UPDATE_RE = re.compile(r'^/api/auth/users/(\d+)$')


# ------------------------------------------------------------------ individual guards
def _refresh_session():
    """Re-read the user row. Returns an error response if the account is gone/disabled."""
    conn = _db()
    try:
        u = conn.execute('SELECT full_name, role, is_active FROM users WHERE id = ?',
                         (session.get('user_id'),)).fetchone()
    finally:
        conn.close()
    if not u or not u['is_active']:
        session.clear()
        return jsonify({'error': 'Your account is disabled or no longer exists', 'redirect': '/login'}), 401
    role = (u['role'] or 'recruiter').lower()
    if session.get('role') != role:
        session['role'] = role
    if session.get('user_name') != u['full_name']:
        session['user_name'] = u['full_name']
    return None


def _guard_owner(path):
    for methods, rx, kind in _OWNER_RULES:
        if request.method not in methods:
            continue
        m = rx.match(path)
        if not m:
            continue
        if kind == 'cand':
            cid = int(m.group(1))
        elif kind == 'project':
            cid = _cand_from_child('candidate_projects', int(m.group(1)))
        elif kind == 'edu':
            cid = _cand_from_child('candidate_education', int(m.group(1)))
        elif kind == 'note':
            cid = _cand_from_child('candidate_notes', int(m.group(1)))
        else:
            cid = request.form.get('candidate_id', type=int)
        if cid is None:
            return None            # let the view answer "not found" / "missing id"
        if not _owns(cid):
            return _deny('You can only change candidates you uploaded')
        return None
    return None


def _guard_manager(path):
    if _role() in ('admin', 'manager'):
        return None
    for methods, rx in _MANAGER_RULES:
        if request.method in methods and rx.match(path):
            return _deny('Manager access required')
    return None


def _recruiter_csv():
    """Recruiters export only their own candidates (managers/admin get the full app export)."""
    name = session.get('user_name') or ''
    conn = _db()
    try:
        rows = conn.execute(
            'SELECT id, first_name, last_name, email, phone, current_role, match_score, created_at '
            'FROM candidates WHERE uploaded_by_name = ? OR uploaded_by = ? ORDER BY created_at DESC',
            (name, name)).fetchall()
    finally:
        conn.close()
    out = io.StringIO()
    w = csv.writer(out)
    w.writerow(['ID', 'First Name', 'Last Name', 'Email', 'Phone', 'Current Role', 'Match Score', 'Created Date'])
    for r in rows:
        w.writerow([r['id'], r['first_name'] or '', r['last_name'] or '', r['email'] or '',
                    r['phone'] or '', r['current_role'] or '', r['match_score'] or 0, r['created_at']])
    return Response(out.getvalue(), mimetype='text/csv',
                    headers={'Content-Disposition': 'attachment; filename=my_candidates.csv'})


def _shape_body(path):
    """Edit the parsed JSON body in place (Flask caches it, so the view sees our changes)."""
    role = _role()
    data = request.get_json(silent=True)
    if not isinstance(data, dict):
        return None

    # upload: uploader is always the logged-in user unless admin
    if request.method == 'POST' and path == '/api/candidates' and role != 'admin':
        who = session.get('user_name') or ''
        data['uploaded_by'] = who
        data['uploaded_by_name'] = who

    # edit: nobody but admin may re-assign ownership
    if request.method == 'PUT' and re.match(r'^/api/candidates/\d+$', path) and role != 'admin':
        data.pop('uploaded_by', None)
        data.pop('uploaded_by_name', None)

    # job edit: never blank fields the form did not send; budget/max salary stay admin-only
    m = _JOB_UPDATE_RE.match(path)
    if m and request.method == 'PUT':
        conn = _db()
        try:
            row = conn.execute('SELECT * FROM jobs WHERE id = ?', (int(m.group(1)),)).fetchone()
        finally:
            conn.close()
        if row:
            keys = row.keys()
            for col in _JOB_COLS:
                if col in keys and (col not in data or (role != 'admin' and col in ('budget', 'max_salary'))):
                    data[col] = row[col]
    return None


def _guard_users(path):
    m = _USER_UPDATE_RE.match(path)
    if not (m and request.method == 'PUT' and _role() == 'admin'):
        return None
    uid = int(m.group(1))
    data = request.get_json(silent=True) or {}
    if 'role' in data and str(data['role']).lower() not in ROLES:
        return _deny('Invalid role', 400)
    if uid == session.get('user_id') and (
            ('role' in data and str(data['role']).lower() != 'admin')
            or ('is_active' in data and not data['is_active'])):
        return _deny('You cannot demote or disable your own account', 409)
    conn = _db()
    try:
        target = conn.execute('SELECT full_name, role, is_active FROM users WHERE id = ?', (uid,)).fetchone()
        if not target:
            return None
        demoting = ('role' in data and str(data['role']).lower() != 'admin') or \
                   ('is_active' in data and not data['is_active'])
        if target['role'] == 'admin' and target['is_active'] and demoting:
            left = conn.execute("SELECT COUNT(*) FROM users WHERE role='admin' AND is_active=1 AND id<>?",
                                (uid,)).fetchone()[0]
            if left == 0:
                return _deny('At least one active admin is required', 409)
    finally:
        conn.close()
    new_name = (data.get('full_name') or '').strip()
    if 'full_name' in data and not new_name:
        return _deny('Name cannot be empty', 400)
    if new_name and new_name != target['full_name']:
        g._rename = (target['full_name'], new_name)
    return None


# ------------------------------------------------------------------ hooks
def _before():
    ep = request.endpoint
    if request.method == 'OPTIONS' or ep in _SKIP_ENDPOINTS or 'user_id' not in session:
        return None                      # app.py's default-deny handles the logged-out case
    bad = _refresh_session()
    if bad:
        return bad
    path = request.path
    role = _role()

    if role != 'admin':
        r = _guard_manager(path) or _guard_owner(path)
        if r:
            return r
        if role == 'recruiter' and request.method == 'GET' and path == '/api/export-candidates':
            return _recruiter_csv()
    r = _guard_users(path)
    if r:
        return r
    _shape_body(path)
    return None


def _after(resp):
    try:
        # rename keeps ownership (candidates are matched to users by name)
        pair = getattr(g, '_rename', None)
        if pair and resp.status_code == 200:
            conn = _db()
            try:
                conn.execute('UPDATE candidates SET uploaded_by_name = ? WHERE uploaded_by_name = ?', (pair[1], pair[0]))
                conn.execute('UPDATE candidates SET uploaded_by = ? WHERE uploaded_by = ?', (pair[1], pair[0]))
                conn.commit()
            finally:
                conn.close()

        # recruiters/managers never receive job budgets
        if (request.method == 'GET' and request.path == '/api/jobs' and 'user_id' in session
                and _role() != 'admin' and resp.status_code == 200 and resp.is_json):
            rows = resp.get_json(silent=True)
            if isinstance(rows, list):
                for j in rows:
                    if isinstance(j, dict):
                        j.pop('budget', None)
                        j.pop('max_salary', None)
                resp.set_data(json.dumps(rows))

        if request.path.startswith('/api/') and request.method == 'GET':
            resp.headers.setdefault('Cache-Control', 'no-store')    # candidate data must not sit in shared caches
    except Exception:
        pass                                                         # never break a response because of this layer
    return resp


def init_access(app):
    app.before_request(_before)
    app.after_request(_after)
