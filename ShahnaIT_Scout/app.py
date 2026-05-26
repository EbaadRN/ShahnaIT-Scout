from flask import Flask, jsonify, request, render_template_string
from datetime import datetime
import os
import sys

app = Flask(__name__)

# HTML Dashboard Template
DASHBOARD_TEMPLATE = '''
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>ShahnaIT Scout - Recruitment Management System</title>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.1.3/dist/css/bootstrap.min.css" rel="stylesheet">
    <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/bootstrap-icons@1.8.1/font/bootstrap-icons.css">
    <style>
        body { background: #f4f6f9; }
        .navbar-brand { font-weight: bold; }
        .stat-card {
            background: white;
            border-radius: 15px;
            padding: 20px;
            margin-bottom: 20px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.05);
            transition: transform 0.2s;
        }
        .stat-card:hover { transform: translateY(-5px); }
        .stat-value { font-size: 2rem; font-weight: bold; }
        .stat-label { color: #666; font-size: 0.85rem; }
    </style>
</head>
<body>
    <nav class="navbar navbar-dark bg-dark">
        <div class="container-fluid">
            <span class="navbar-brand">
                <i class="bi bi-robot"></i> ShahnaIT Scout - Professional Recruitment
            </span>
        </div>
    </nav>
    
    <div class="container mt-4">
        <!-- Stats Row -->
        <div class="row" id="statsRow">
            <div class="col-md-3">
                <div class="stat-card text-center">
                    <div class="stat-value" id="openPositions">0</div>
                    <div class="stat-label">Open Positions</div>
                </div>
            </div>
            <div class="col-md-3">
                <div class="stat-card text-center">
                    <div class="stat-value" id="totalCandidates">0</div>
                    <div class="stat-label">Total Candidates</div>
                </div>
            </div>
            <div class="col-md-3">
                <div class="stat-card text-center">
                    <div class="stat-value" id="totalApplications">0</div>
                    <div class="stat-label">Applications</div>
                </div>
            </div>
            <div class="col-md-3">
                <div class="stat-card text-center">
                    <div class="stat-value" id="matchRate">0%</div>
                    <div class="stat-label">Avg Match Rate</div>
                </div>
            </div>
        </div>
        
        <!-- Tabs -->
        <ul class="nav nav-tabs" id="myTab" role="tablist">
            <li class="nav-item">
                <button class="nav-link active" data-bs-toggle="tab" data-bs-target="#jobs">📋 Job Descriptions</button>
            </li>
            <li class="nav-item">
                <button class="nav-link" data-bs-toggle="tab" data-bs-target="#candidates">👥 Candidates</button>
            </li>
            <li class="nav-item">
                <button class="nav-link" data-bs-toggle="tab" data-bs-target="#applications">📄 Applications</button>
            </li>
        </ul>
        
        <div class="tab-content mt-3">
            <!-- Jobs Tab -->
            <div class="tab-pane fade show active" id="jobs">
                <button class="btn btn-primary mb-3" onclick="showJobModal()">+ Create Job Description</button>
                <div class="table-responsive">
                    <table class="table table-hover">
                        <thead class="table-light">
                            <tr><th>Code</th><th>Title</th><th>Location</th><th>Status</th><th>Applications</th><th>Actions</th></tr>
                        </thead>
                        <tbody id="jobsTable"></tbody>
                    </table>
                </div>
            </div>
            
            <!-- Candidates Tab -->
            <div class="tab-pane fade" id="candidates">
                <button class="btn btn-success mb-3" onclick="showCandidateModal()">+ Add Candidate</button>
                <div class="table-responsive">
                    <table class="table table-hover">
                        <thead class="table-light">
                            <tr><th>Code</th><th>Name</th><th>Email</th><th>Actions</th></tr>
                        </thead>
                        <tbody id="candidatesTable"></tbody>
                    </table>
                </div>
            </div>
            
            <!-- Applications Tab -->
            <div class="tab-pane fade" id="applications">
                <div class="table-responsive">
                    <table class="table table-hover">
                        <thead class="table-light">
                            <tr><th>ID</th><th>Candidate</th><th>Job</th><th>Match Score</th><th>Status</th><th>Actions</th></tr>
                        </thead>
                        <tbody id="applicationsTable"></tbody>
                    </table>
                </div>
            </div>
        </div>
    </div>
    
    <!-- Job Modal -->
    <div class="modal fade" id="jobModal" tabindex="-1">
        <div class="modal-dialog">
            <div class="modal-content">
                <div class="modal-header bg-primary text-white">
                    <h5 class="modal-title">Create Job Description</h5>
                    <button type="button" class="btn-close" data-bs-dismiss="modal"></button>
                </div>
                <div class="modal-body">
                    <input type="text" class="form-control mb-2" id="jobTitle" placeholder="Job Title" required>
                    <input type="text" class="form-control mb-2" id="jobLocation" placeholder="Location">
                    <select class="form-control mb-2" id="jobStatus">
                        <option value="open">Open</option>
                        <option value="draft">Draft</option>
                        <option value="closed">Closed</option>
                    </select>
                    <button class="btn btn-primary w-100" onclick="createJob()">Create Job</button>
                </div>
            </div>
        </div>
    </div>
    
    <!-- Candidate Modal -->
    <div class="modal fade" id="candidateModal" tabindex="-1">
        <div class="modal-dialog">
            <div class="modal-content">
                <div class="modal-header bg-success text-white">
                    <h5 class="modal-title">Add Candidate</h5>
                    <button type="button" class="btn-close" data-bs-dismiss="modal"></button>
                </div>
                <div class="modal-body">
                    <input type="text" class="form-control mb-2" id="candFirstName" placeholder="First Name" required>
                    <input type="text" class="form-control mb-2" id="candLastName" placeholder="Last Name">
                    <input type="email" class="form-control mb-2" id="candEmail" placeholder="Email" required>
                    <button class="btn btn-success w-100" onclick="createCandidate()">Add Candidate</button>
                </div>
            </div>
        </div>
    </div>
    
    <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.1.3/dist/js/bootstrap.bundle.min.js"></script>
    <script>
        // Load all data on page load
        document.addEventListener('DOMContentLoaded', () => {
            loadStats();
            loadJobs();
            loadCandidates();
            loadApplications();
        });
        
        async function loadStats() {
            try {
                const res = await fetch('/api/dashboard/stats');
                const data = await res.json();
                document.getElementById('openPositions').innerText = data.overview.open_positions || 0;
                document.getElementById('totalCandidates').innerText = data.overview.total_candidates || 0;
                document.getElementById('totalApplications').innerText = data.overview.total_applications || 0;
            } catch(e) { console.error(e); }
        }
        
        async function loadJobs() {
            try {
                const res = await fetch('/api/jds');
                const jobs = await res.json();
                const tbody = document.getElementById('jobsTable');
                if (jobs.length === 0) {
                    tbody.innerHTML = '<tr><td colspan="6" class="text-center">No jobs created yet</td></tr>';
                    return;
                }
                tbody.innerHTML = jobs.map(job => `
                    <tr>
                        <td><code>${job.code}</code></td>
                        <td><strong>${job.title}</strong></td>
                        <td>${job.location || '-'}</td>
                        <td><span class="badge bg-success">${job.status}</span></td>
                        <td>${job.applications || 0}</td>
                        <td><button class="btn btn-sm btn-primary" onclick="createApplicationForJob(${job.id})">Create Application</button></td>
                    </tr>
                `).join('');
            } catch(e) { console.error(e); }
        }
        
        async function loadCandidates() {
            try {
                const res = await fetch('/api/candidates');
                const data = await res.json();
                const tbody = document.getElementById('candidatesTable');
                if (data.candidates.length === 0) {
                    tbody.innerHTML = '<tr><td colspan="4" class="text-center">No candidates added yet</td></tr>';
                    return;
                }
                tbody.innerHTML = data.candidates.map(c => `
                    <tr>
                        <td><code>${c.code}</code></td>
                        <td>${c.name}</td>
                        <td>${c.email}</td>
                        <td><button class="btn btn-sm btn-primary" onclick="createApplicationForCandidate(${c.id})">Apply to Job</button></td>
                    </tr>
                `).join('');
            } catch(e) { console.error(e); }
        }
        
        async function loadApplications() {
            try {
                const res = await fetch('/api/applications');
                const apps = await res.json();
                const tbody = document.getElementById('applicationsTable');
                if (apps.length === 0) {
                    tbody.innerHTML = '<tr><td colspan="6" class="text-center">No applications yet</td></tr>';
                    return;
                }
                tbody.innerHTML = apps.map(app => `
                    <tr>
                        <td>${app.id}</td>
                        <td>Candidate #${app.candidate_id}</td>
                        <td>Job #${app.jd_id}</td>
                        <td><span class="badge bg-info">${app.match_score || 0}%</span></td>
                        <td>${app.status}</td>
                        <td><button class="btn btn-sm btn-warning" onclick="moveStage(${app.id}, prompt('Enter stage: new/shortlisted/selected/rejected'))">Move</button></td>
                    </tr>
                `).join('');
            } catch(e) { console.error(e); }
        }
        
        async function createJob() {
            const title = document.getElementById('jobTitle').value;
            const location = document.getElementById('jobLocation').value;
            const status = document.getElementById('jobStatus').value;
            if (!title) { alert('Enter job title'); return; }
            
            const res = await fetch('/api/jds', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({title, location, status})
            });
            const result = await res.json();
            if (result.success) {
                alert(`Job created: ${result.jd_code}`);
                bootstrap.Modal.getInstance(document.getElementById('jobModal')).hide();
                loadJobs();
                loadStats();
                document.getElementById('jobTitle').value = '';
                document.getElementById('jobLocation').value = '';
            }
        }
        
        async function createCandidate() {
            const first_name = document.getElementById('candFirstName').value;
            const last_name = document.getElementById('candLastName').value;
            const email = document.getElementById('candEmail').value;
            if (!first_name || !email) { alert('Enter name and email'); return; }
            
            const res = await fetch('/api/candidates', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({first_name, last_name, email})
            });
            const result = await res.json();
            if (result.success) {
                alert(`Candidate added: ${result.candidate_code}`);
                bootstrap.Modal.getInstance(document.getElementById('candidateModal')).hide();
                loadCandidates();
                loadStats();
                document.getElementById('candFirstName').value = '';
                document.getElementById('candLastName').value = '';
                document.getElementById('candEmail').value = '';
            }
        }
        
        async function createApplicationForJob(jd_id) {
            const candidate_id = prompt('Enter Candidate ID:');
            if (!candidate_id) return;
            const res = await fetch('/api/applications', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({candidate_id: parseInt(candidate_id), jd_id})
            });
            const result = await res.json();
            if (result.success) {
                alert(`Application created! Match Score: ${result.match_score || 75}%`);
                loadApplications();
                loadStats();
            }
        }
        
        async function createApplicationForCandidate(candidate_id) {
            const jd_id = prompt('Enter Job ID:');
            if (!jd_id) return;
            const res = await fetch('/api/applications', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({candidate_id, jd_id: parseInt(jd_id)})
            });
            const result = await res.json();
            if (result.success) {
                alert(`Application created! Match Score: ${result.match_score || 75}%`);
                loadApplications();
                loadStats();
            }
        }
        
        async function moveStage(app_id, stage) {
            if (!stage) return;
            await fetch(`/api/applications/${app_id}/move`, {
                method: 'PUT',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({stage})
            });
            loadApplications();
        }
        
        function showJobModal() {
            new bootstrap.Modal(document.getElementById('jobModal')).show();
        }
        
        function showCandidateModal() {
            new bootstrap.Modal(document.getElementById('candidateModal')).show();
        }
        
        // Refresh every 30 seconds
        setInterval(() => {
            loadStats();
            loadJobs();
            loadCandidates();
            loadApplications();
        }, 30000);
    </script>
</body>
</html>
'''

# In-memory storage
jobs = []
candidates = []
applications = []
next_id = 1

@app.route('/')
def index():
    return render_template_string(DASHBOARD_TEMPLATE)

@app.route('/health')
def health():
    return jsonify({'status': 'ok', 'timestamp': datetime.now().isoformat()})

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
        data = request.get_json()
        job = {
            'id': next_id,
            'code': f"JD-{next_id:04d}",
            'title': data.get('title', 'Untitled'),
            'location': data.get('location', 'Remote'),
            'status': data.get('status', 'open'),
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
        data = request.get_json()
        candidate = {
            'id': next_id,
            'code': f"CAN-{next_id:04d}",
            'first_name': data.get('first_name', ''),
            'last_name': data.get('last_name', ''),
            'name': f"{data.get('first_name', '')} {data.get('last_name', '')}".strip(),
            'email': data.get('email', ''),
            'created_at': datetime.now().isoformat()
        }
        candidates.append(candidate)
        next_id += 1
        return jsonify({'success': True, 'candidate_id': candidate['id'], 'candidate_code': candidate['code']})
    
    return jsonify({
        'candidates': [{
            'id': c['id'],
            'code': c['code'],
            'name': c['name'],
            'email': c['email']
        } for c in candidates],
        'total': len(candidates),
        'page': 1,
        'pages': 1
    })

@app.route('/api/applications', methods=['GET', 'POST'])
def manage_applications():
    if request.method == 'POST':
        data = request.get_json()
        
        # Calculate simple match score
        job = next((j for j in jobs if j['id'] == data.get('jd_id')), None)
        candidate = next((c for c in candidates if c['id'] == data.get('candidate_id')), None)
        
        # Simple match score based on name similarity (just for demo)
        match_score = 75
        if job and candidate:
            if job['title'].lower() in candidate['name'].lower():
                match_score = 85
            else:
                match_score = 65
        
        application = {
            'id': len(applications) + 1,
            'candidate_id': data.get('candidate_id'),
            'jd_id': data.get('jd_id'),
            'status': 'new',
            'application_date': datetime.now().date().isoformat(),
            'match_score': match_score
        }
        applications.append(application)
        
        # Update job application count
        if job:
            job['applications'] = job.get('applications', 0) + 1
        
        return jsonify({'success': True, 'application_id': application['id'], 'match_score': match_score})
    return jsonify(applications)

@app.route('/api/applications/<int:app_id>/move', methods=['PUT'])
def move_application_stage(app_id):
    data = request.get_json()
    for app in applications:
        if app['id'] == app_id:
            app['status'] = data.get('stage', app['status'])
            break
    return jsonify({'success': True})

@app.route('/api/candidates/parse-resume', methods=['POST'])
def parse_resume():
    return jsonify({
        'success': True,
        'data': {
            'first_name': 'John',
            'last_name': 'Doe',
            'email': 'john@example.com',
            'phone': '9876543210',
            'skills': ['Python', 'JavaScript', 'SQL'],
            'qualifications': 'B.Tech Computer Science',
            'current_company': 'Tech Corp',
            'current_designation': 'Software Engineer'
        }
    })

@app.route('/api/clients', methods=['GET'])
def get_clients():
    return jsonify([])

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 8080))
    app.run(host='0.0.0.0', port=port, debug=False)
# Add these imports at the top (if not already there)
from difflib import SequenceMatcher

# ============= ENHANCED CANDIDATE SCORING =============

def calculate_weighted_match_score(job_skills, candidate_skills):
    """Advanced skill matching with partial matches"""
    if not job_skills or not candidate_skills:
        return 0, {}
    
    # Parse skills
    job_list = [s.strip().lower() for s in job_skills.split(',') if s.strip()]
    cand_list = [s.strip().lower() for s in candidate_skills.split(',') if s.strip()]
    
    if not job_list:
        return 0, {}
    
    match_details = {
        'exact_matches': [],
        'partial_matches': [],
        'missing_skills': []
    }
    
    total_score = 0
    for job_skill in job_list:
        best_match = 0
        best_match_name = None
        
        for cand_skill in cand_list:
            # Check exact match
            if job_skill == cand_skill:
                best_match = 100
                best_match_name = cand_skill
                match_details['exact_matches'].append(job_skill)
                break
            # Check partial match (e.g., "Python" vs "Python Django")
            elif job_skill in cand_skill or cand_skill in job_skill:
                best_match = 70
                best_match_name = cand_skill
                if job_skill not in match_details['partial_matches']:
                    match_details['partial_matches'].append(job_skill)
                break
            # Check similarity
            else:
                similarity = SequenceMatcher(None, job_skill, cand_skill).ratio() * 100
                if similarity > best_match and similarity > 50:
                    best_match = similarity
                    best_match_name = cand_skill
        
        if best_match == 0:
            match_details['missing_skills'].append(job_skill)
        
        total_score += best_match
    
    final_score = round(total_score / len(job_list), 2)
    
    return final_score, match_details

# ============= NOTES & COMMENTS =============

# Store notes in memory (will persist during session)
candidate_notes = {}
application_notes = {}

@app.route('/api/candidates/<int:candidate_id>/notes', methods=['GET', 'POST'])
def candidate_notes_api(candidate_id):
    """Get or add notes for a candidate"""
    if request.method == 'POST':
        data = request.json
        note = {
            'id': len(candidate_notes.get(candidate_id, [])) + 1,
            'text': data.get('text'),
            'author': data.get('author', 'Recruiter'),
            'created_at': datetime.now().isoformat()
        }
        if candidate_id not in candidate_notes:
            candidate_notes[candidate_id] = []
        candidate_notes[candidate_id].append(note)
        return jsonify({'success': True, 'note': note})
    else:
        return jsonify({'notes': candidate_notes.get(candidate_id, [])})

@app.route('/api/applications/<int:app_id>/notes', methods=['GET', 'POST'])
def application_notes_api(app_id):
    """Get or add notes for an application"""
    if request.method == 'POST':
        data = request.json
        note = {
            'id': len(application_notes.get(app_id, [])) + 1,
            'text': data.get('text'),
            'author': data.get('author', 'Recruiter'),
            'created_at': datetime.now().isoformat()
        }
        if app_id not in application_notes:
            application_notes[app_id] = []
        application_notes[app_id].append(note)
        return jsonify({'success': True, 'note': note})
    else:
        return jsonify({'notes': application_notes.get(app_id, [])})

# ============= INTERVIEW SCHEDULING =============

# Store interviews in memory
interviews = []

@app.route('/api/interviews', methods=['GET', 'POST'])
def manage_interviews():
    """Schedule and manage interviews"""
    if request.method == 'POST':
        data = request.json
        
        interview = {
            'id': len(interviews) + 1,
            'application_id': data.get('application_id'),
            'candidate_name': data.get('candidate_name'),
            'job_title': data.get('job_title'),
            'interviewer': data.get('interviewer'),
            'interviewer_email': data.get('interviewer_email'),
            'scheduled_time': data.get('scheduled_time'),
            'duration_minutes': data.get('duration_minutes', 60),
            'meeting_link': data.get('meeting_link'),
            'round_type': data.get('round_type', 'Technical'),
            'status': 'scheduled',
            'created_at': datetime.now().isoformat()
        }
        interviews.append(interview)
        
        # Update application status
        for app in applications:
            if app['id'] == data.get('application_id'):
                app['status'] = 'interview-scheduled'
                break
        
        return jsonify({'success': True, 'interview_id': interview['id']})
    else:
        # Return upcoming interviews
        now = datetime.now().isoformat()
        upcoming = [i for i in interviews if i.get('status') == 'scheduled']
        return jsonify(upcoming)

@app.route('/api/interviews/<int:interview_id>/complete', methods=['PUT'])
def complete_interview(interview_id):
    """Mark interview as completed with feedback"""
    data = request.json
    
    for interview in interviews:
        if interview['id'] == interview_id:
            interview['status'] = 'completed'
            interview['feedback'] = data.get('feedback')
            interview['rating'] = data.get('rating')
            interview['result'] = data.get('result')
            
            # Update application based on interview result
            if interview.get('application_id'):
                for app in applications:
                    if app['id'] == interview['application_id']:
                        if data.get('result') == 'pass':
                            app['status'] = 'interviewed'
                        else:
                            app['status'] = 'rejected'
                        break
            break
    
    return jsonify({'success': True})

# ============= OFFER LETTER GENERATOR =============

# Store offers in memory
offers = []

@app.route('/api/offers', methods=['GET', 'POST'])
def manage_offers():
    """Generate and manage offer letters"""
    if request.method == 'POST':
        data = request.json
        
        offer = {
            'id': len(offers) + 1,
            'application_id': data.get('application_id'),
            'candidate_name': data.get('candidate_name'),
            'candidate_email': data.get('candidate_email'),
            'job_title': data.get('job_title'),
            'base_salary': data.get('base_salary'),
            'joining_bonus': data.get('joining_bonus', 0),
            'joining_date': data.get('joining_date'),
            'status': 'draft',
            'created_at': datetime.now().isoformat(),
            'offer_letter_html': generate_offer_letter_html(data)
        }
        offers.append(offer)
        
        # Update application status
        for app in applications:
            if app['id'] == data.get('application_id'):
                app['status'] = 'offered'
                break
        
        return jsonify({'success': True, 'offer_id': offer['id'], 'offer_html': offer['offer_letter_html']})
    else:
        return jsonify(offers)

def generate_offer_letter_html(data):
    """Generate HTML for offer letter"""
    return f'''
    <!DOCTYPE html>
    <html>
    <head>
        <title>Offer Letter - {data.get('candidate_name')}</title>
        <style>
            body {{ font-family: Arial, sans-serif; margin: 50px; }}
            .container {{ max-width: 800px; margin: auto; }}
            .header {{ text-align: center; border-bottom: 2px solid #4CAF50; padding-bottom: 20px; }}
            .content {{ margin: 30px 0; }}
            .signature {{ margin-top: 50px; }}
            table {{ width: 100%; border-collapse: collapse; margin: 20px 0; }}
            td {{ padding: 10px; border: 1px solid #ddd; }}
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <h1>ShahnaIT Scout</h1>
                <h2>Offer of Employment</h2>
            </div>
            <div class="content">
                <p>Dear <strong>{data.get('candidate_name')}</strong>,</p>
                <p>We are pleased to offer you the position of <strong>{data.get('job_title')}</strong> at ShahnaIT Scout.</p>
                
                <h3>Offer Details</h3>
                <table>
                    <tr><td><strong>Position</strong></td><td>{data.get('job_title')}</td></tr>
                    <tr><td><strong>Base Salary</strong></td><td>${data.get('base_salary', 0):,.2f} per year</td></tr>
                    <tr><td><strong>Joining Bonus</strong></td><td>${data.get('joining_bonus', 0):,.2f}</td></tr>
                    <tr><td><strong>Expected Joining Date</strong></td><td>{data.get('joining_date')}</td></tr>
                </table>
                
                <h3>Terms & Conditions</h3>
                <p>This offer is valid for 15 days from the date of issuance. Please review the attached terms and conditions.</p>
                
                <p>We look forward to having you on our team!</p>
            </div>
            <div class="signature">
                <p>Sincerely,<br><strong>ShahnaIT Recruitment Team</strong></p>
            </div>
        </div>
    </body>
    </html>
    '''

# ============= REPORTS & ANALYTICS =============

@app.route('/api/reports/hiring-metrics', methods=['GET'])
def hiring_metrics():
    """Generate hiring analytics"""
    
    # Calculate time-to-hire
    time_to_hire = []
    for app in applications:
        if app.get('status') == 'joined' and app.get('created_at'):
            try:
                created = datetime.fromisoformat(app['created_at'])
                joined = datetime.fromisoformat(app.get('joined_at', app['created_at']))
                days = (joined - created).days
                time_to_hire.append(days)
            except:
                pass
    
    avg_time_to_hire = sum(time_to_hire) / len(time_to_hire) if time_to_hire else 0
    
    # Pipeline conversion rates
    total_apps = len(applications)
    if total_apps > 0:
        screening_rate = len([a for a in applications if a.get('status') in ['screening', 'shortlisted']]) / total_apps * 100
        interview_rate = len([a for a in applications if a.get('status') in ['interview-scheduled', 'interviewed']]) / total_apps * 100
        offer_rate = len([a for a in applications if a.get('status') in ['offered', 'offer-accepted']]) / total_apps * 100
        hire_rate = len([a for a in applications if a.get('status') == 'joined']) / total_apps * 100
    else:
        screening_rate = interview_rate = offer_rate = hire_rate = 0
    
    # Source effectiveness
    source_stats = {}
    for candidate in candidates:
        source = candidate.get('source', 'unknown')
        if source not in source_stats:
            source_stats[source] = {'total': 0, 'hired': 0}
        source_stats[source]['total'] += 1
    
    for app in applications:
        if app.get('status') == 'joined':
            candidate = next((c for c in candidates if c['id'] == app.get('candidate_id')), None)
            if candidate:
                source = candidate.get('source', 'unknown')
                if source in source_stats:
                    source_stats[source]['hired'] += 1
    
    source_effectiveness = []
    for source, stats in source_stats.items():
        conversion = round((stats['hired'] / stats['total']) * 100, 2) if stats['total'] > 0 else 0
        source_effectiveness.append({
            'source': source,
            'total': stats['total'],
            'hired': stats['hired'],
            'conversion_rate': conversion
        })
    
    return jsonify({
        'total_applications': total_apps,
        'average_time_to_hire_days': round(avg_time_to_hire, 1),
        'conversion_rates': {
            'screening': round(screening_rate, 1),
            'interview': round(interview_rate, 1),
            'offer': round(offer_rate, 1),
            'hire': round(hire_rate, 1)
        },
        'source_effectiveness': source_effectiveness,
        'applications_by_stage': {
            'new': len([a for a in applications if a.get('status') == 'new']),
            'screening': len([a for a in applications if a.get('status') in ['screening', 'shortlisted']]),
            'interview': len([a for a in applications if a.get('status') in ['interview-scheduled', 'interviewed']]),
            'offer': len([a for a in applications if a.get('status') in ['offered', 'offer-accepted']]),
            'hired': len([a for a in applications if a.get('status') == 'joined'])
        }
    })

# ============= RESUME UPLOAD & PARSING =============

@app.route('/api/candidates/parse-resume-enhanced', methods=['POST'])
def parse_resume_enhanced():
    """Enhanced resume parsing with better extraction"""
    if 'file' not in request.files:
        return jsonify({'error': 'No file uploaded'}), 400
    
    file = request.files['file']
    filename = file.filename.lower()
    
    text = ''
    
    # Extract text based on file type
    if filename.endswith('.pdf'):
        try:
            import PyPDF2
            reader = PyPDF2.PdfReader(file)
            for page in reader.pages:
                text += page.extract_text() or ''
        except:
            text = ''
    elif filename.endswith('.docx'):
        try:
            import docx
            doc = docx.Document(file)
            text = '\n'.join([para.text for para in doc.paragraphs])
        except:
            text = ''
    else:
        try:
            text = file.read().decode('utf-8')
        except:
            text = ''
    
    # Enhanced extraction
    parsed_data = {
        'first_name': extract_name_enhanced(text)['first'],
        'last_name': extract_name_enhanced(text)['last'],
        'email': extract_email_enhanced(text),
        'phone': extract_phone_enhanced(text),
        'skills': extract_skills_enhanced(text),
        'total_experience': extract_experience_enhanced(text),
        'current_company': extract_company_enhanced(text),
        'current_designation': extract_designation_enhanced(text),
        'current_location': extract_location_enhanced(text),
        'qualifications': extract_qualifications_enhanced(text),
        'languages': extract_languages(text),
        'certifications': extract_certifications(text)
    }
    
    return jsonify({
        'success': True,
        'data': parsed_data,
        'resume_text_preview': text[:500] + '...' if len(text) > 500 else text
    })

def extract_name_enhanced(text):
    """Enhanced name extraction"""
    lines = text.split('\n')[:15]
    for line in lines:
        line = line.strip()
        if len(line.split()) == 2 and not any(x in line.lower() for x in ['resume', 'curriculum', 'vitae', 'email', 'phone']):
            parts = line.split()
            if len(parts) == 2:
                return {'first': parts[0], 'last': parts[1]}
    return {'first': None, 'last': None}

def extract_email_enhanced(text):
    """Enhanced email extraction"""
    import re
    pattern = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
    match = re.search(pattern, text)
    return match.group(0) if match else None

def extract_phone_enhanced(text):
    """Enhanced phone extraction"""
    import re
    patterns = [
        r'\b\d{10}\b',
        r'\+\d{1,2}[-.\s]?\d{10}\b',
        r'\b\d{3}[-.]?\d{3}[-.]?\d{4}\b'
    ]
    for pattern in patterns:
        match = re.search(pattern, text)
        if match:
            return match.group(0)
    return None

def extract_skills_enhanced(text):
    """Enhanced skill extraction with broader skill database"""
    skill_database = [
        'Python', 'Java', 'JavaScript', 'TypeScript', 'C++', 'C#', 'Go', 'Ruby', 'PHP', 'Swift', 'Kotlin',
        'React', 'Angular', 'Vue', 'Node.js', 'Django', 'Flask', 'Spring', 'Express', 'Rails', 'Laravel',
        'MySQL', 'PostgreSQL', 'MongoDB', 'Redis', 'Oracle', 'SQL Server', 'Cassandra', 'DynamoDB',
        'AWS', 'Azure', 'GCP', 'Docker', 'Kubernetes', 'Terraform', 'Jenkins', 'Git', 'CI/CD',
        'TensorFlow', 'PyTorch', 'Scikit-learn', 'Pandas', 'NumPy', 'Machine Learning', 'Data Science',
        'Leadership', 'Project Management', 'Agile', 'Scrum', 'Communication', 'Teamwork'
    ]
    
    found = []
    text_lower = text.lower()
    for skill in skill_database:
        if skill.lower() in text_lower:
            found.append(skill)
    
    return found

def extract_experience_enhanced(text):
    """Enhanced experience extraction"""
    import re
    patterns = [
        r'(\d+)\s*\+\s*years?',
        r'(\d+)\s*years?\s+of\s+experience',
        r'total\s+experience\s*:?\s*(\d+)',
        r'experience\s*:?\s*(\d+)\s*years?'
    ]
    for pattern in patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            return float(match.group(1))
    return 0

def extract_company_enhanced(text):
    """Enhanced company extraction"""
    import re
    patterns = [
        r'Current\s+Company\s*:?\s*(.+?)(?:\n|$)',
        r'Employer\s*:?\s*(.+?)(?:\n|$)',
        r'Work\s+Experience.*?\n(?:.*?\n){1,3}?(.+?)(?:\n|$)'
    ]
    for pattern in patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            company = match.group(1).strip()
            if len(company) < 50:
                return company
    return None

def extract_designation_enhanced(text):
    """Enhanced designation extraction"""
    import re
    patterns = [
        r'Designation\s*:?\s*(.+?)(?:\n|$)',
        r'Title\s*:?\s*(.+?)(?:\n|$)',
        r'Position\s*:?\s*(.+?)(?:\n|$)'
    ]
    for pattern in patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            return match.group(1).strip()
    
    # Look for common titles
    titles = ['Developer', 'Engineer', 'Manager', 'Lead', 'Architect', 'Consultant', 'Analyst', 'Specialist']
    for title in titles:
        if title.lower() in text.lower():
            context = re.search(f'.{{0,30}}{title}.{{0,30}}', text, re.IGNORECASE)
            if context:
                return context.group().strip()
    return None

def extract_location_enhanced(text):
    """Enhanced location extraction"""
    import re
    cities = ['Bangalore', 'Mumbai', 'Delhi', 'Hyderabad', 'Chennai', 'Pune', 'Kolkata', 'Ahmedabad', 'Remote']
    for city in cities:
        if city.lower() in text.lower():
            return city
    
    pattern = r'Location\s*:?\s*(.+?)(?:\n|$)'
    match = re.search(pattern, text, re.IGNORECASE)
    return match.group(1).strip() if match else None

def extract_qualifications_enhanced(text):
    """Enhanced qualification extraction"""
    import re
    degrees = ['Bachelor', 'Master', 'B.Tech', 'M.Tech', 'BCA', 'MCA', 'MBA', 'PhD', 'B.Sc', 'M.Sc', 'Diploma', 'B.Com', 'M.Com']
    found = []
    for degree in degrees:
        if degree.lower() in text.lower():
            context = re.search(f'.{{0,50}}{degree}.{{0,50}}', text, re.IGNORECASE)
            if context:
                found.append(context.group().strip())
    return '\n'.join(found[:3]) if found else None

def extract_languages(text):
    """Extract languages from resume"""
    languages = ['English', 'Hindi', 'Spanish', 'French', 'German', 'Chinese', 'Japanese', 'Tamil', 'Telugu', 'Kannada', 'Malayalam', 'Bengali']
    found = []
    text_lower = text.lower()
    for lang in languages:
        if lang.lower() in text_lower:
            found.append(lang)
    return found

def extract_certifications(text):
    """Extract certifications from resume"""
    import re
    cert_patterns = [
        r'AWS\s+Certified',
        r'Azure\s+Certified',
        r'Google\s+Cloud',
        r'PMP',
        r'Scrum\s+Master',
        r'TOGAF',
        r'CISSP',
        r'CISM',
        r'CEH'
    ]
    found = []
    for pattern in cert_patterns:
        if re.search(pattern, text, re.IGNORECASE):
            found.append(pattern)
    return found
