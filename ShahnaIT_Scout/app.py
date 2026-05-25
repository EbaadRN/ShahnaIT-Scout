from flask import Flask, render_template, jsonify, request
from datetime import datetime
import os

app = Flask(__name__)

# Simple in-memory storage
jobs = []
candidates = []
applications = []
next_id = 1

@app.route('/')
def index():
    return render_template('dashboard.html')

@app.route('/api/dashboard/stats')
def dashboard_stats():
    return jsonify({
        'overview': {
            'open_positions': len([j for j in jobs if j.get('status') == 'open']),
            'total_candidates': len(candidates),
            'total_applications': len(applications),
            'interviews_today': 0,
            'offers_accepted': 0
        },
        'pipeline': {
            'new': len([a for a in applications if a.get('status') == 'new']),
            'shortlisted': 0,
            'interviewed': 0,
            'selected': 0,
            'rejected': 0
        },
        'recent_activities': [],
        'top_jds': []
    })

@app.route('/api/jds', methods=['GET', 'POST'])
def manage_jds():
    global next_id
    if request.method == 'POST':
        data = request.json
        job = {
            'id': next_id,
            'code': f"JD-{next_id:04d}",
            'title': data.get('title'),
            'client_name': data.get('client_name'),
            'location': data.get('location'),
            'employment_type': data.get('employment_type', 'full-time'),
            'status': data.get('status', 'open'),
            'priority': data.get('priority', 'medium'),
            'skills_required': data.get('skills_required'),
            'applications': 0,
            'created_at': datetime.now().isoformat()
        }
        jobs.append(job)
        next_id += 1
        return jsonify({'success': True, 'jd_id': job['id'], 'jd_code': job['code']})
    return jsonify(jobs)

@app.route('/api/candidates', methods=['GET', 'POST'])
def manage_candidates():
    global next_id
    if request.method == 'POST':
        data = request.json
        existing = next((c for c in candidates if c.get('email') == data.get('email')), None)
        if existing:
            return jsonify({'error': 'Candidate already exists', 'candidate_id': existing['id']}), 409
        
        candidate = {
            'id': next_id,
            'code': f"CAN-{next_id:04d}",
            'first_name': data.get('first_name'),
            'last_name': data.get('last_name'),
            'name': f"{data.get('first_name')} {data.get('last_name')}",
            'email': data.get('email'),
            'phone': data.get('phone'),
            'current_company': data.get('current_company'),
            'current_designation': data.get('current_designation'),
            'total_experience': data.get('total_experience', 0),
            'skills': data.get('skills'),
            'source': data.get('source', 'website'),
            'created_at': datetime.now().isoformat()
        }
        candidates.append(candidate)
        next_id += 1
        return jsonify({'success': True, 'candidate_id': candidate['id'], 'candidate_code': candidate['code']})
    
    page = int(request.args.get('page', 1))
    per_page = 20
    search = request.args.get('skill', '')
    
    filtered = candidates
    if search:
        filtered = [c for c in candidates if search.lower() in c.get('name', '').lower() or search.lower() in c.get('skills', '').lower()]
    
    start = (page - 1) * per_page
    end = start + per_page
    paginated = filtered[start:end]
    
    return jsonify({
        'candidates': paginated,
        'total': len(filtered),
        'page': page,
        'pages': (len(filtered) + per_page - 1) // per_page
    })

@app.route('/api/applications', methods=['GET', 'POST'])
def manage_applications():
    global next_id
    if request.method == 'POST':
        data = request.json
        job = next((j for j in jobs if j['id'] == data.get('jd_id')), None)
        candidate = next((c for c in candidates if c['id'] == data.get('candidate_id')), None)
        
        match_score = 0
        if job and candidate:
            job_skills = set(job.get('skills_required', '').lower().split(','))
            cand_skills = set(candidate.get('skills', '').lower().split(','))
            if job_skills and cand_skills:
                matches = len(job_skills.intersection(cand_skills))
                match_score = round((matches / len(job_skills)) * 100, 2)
        
        application = {
            'id': next_id,
            'code': f"APP-{next_id:04d}",
            'candidate_id': data.get('candidate_id'),
            'candidate_name': candidate.get('name') if candidate else None,
            'jd_id': data.get('jd_id'),
            'job_title': job.get('title') if job else None,
            'match_score': match_score,
            'status': 'new',
            'application_date': datetime.now().date().isoformat()
        }
        applications.append(application)
        next_id += 1
        
        if job:
            job['applications'] = job.get('applications', 0) + 1
        
        return jsonify({'success': True, 'application_id': application['id'], 'match_score': match_score})
    return jsonify(applications)

@app.route('/api/applications/<int:app_id>/move', methods=['PUT'])
def move_application_stage(app_id):
    data = request.json
    for app in applications:
        if app['id'] == app_id:
            app['status'] = data.get('stage')
            break
    return jsonify({'success': True})

@app.route('/api/candidates/parse-resume', methods=['POST'])
def parse_resume():
    return jsonify({
        'success': True,
        'data': {
            'first_name': 'Sample',
            'last_name': 'Candidate',
            'email': 'sample@example.com',
            'phone': '1234567890',
            'skills': ['Python', 'JavaScript', 'SQL'],
            'qualifications': 'Bachelor of Technology',
            'current_company': 'Tech Corp',
            'current_designation': 'Software Engineer'
        }
    })

@app.route('/api/clients', methods=['GET'])
def get_clients():
    return jsonify([])

# ============= THIS IS THE IMPORTANT PART - AT THE BOTTOM =============
if __name__ == '__main__':
    port = int(os.environ.get('PORT', 8080))
    app.run(debug=False, host='0.0.0.0', port=port)
