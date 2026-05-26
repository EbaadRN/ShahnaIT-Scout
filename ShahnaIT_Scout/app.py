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
