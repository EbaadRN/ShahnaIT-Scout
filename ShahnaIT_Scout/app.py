from flask import Flask, render_template_string, jsonify, request
from datetime import datetime
import os
import re
import json
import base64
import csv
import io

app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'dev-secret-key')
app.config['MAX_CONTENT_LENGTH'] = 100 * 1024 * 1024

# ============= FULL DASHBOARD HTML =============
DASHBOARD_TEMPLATE = '''
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>ShahnaIT Scout - Recruitment Suite</title>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.1.3/dist/css/bootstrap.min.css" rel="stylesheet">
    <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/bootstrap-icons@1.8.1/font/bootstrap-icons.css">
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body { font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; background: #f0f2f5; }
        .sidebar { position: fixed; left: 0; top: 0; width: 260px; height: 100vh; background: #1a1a2e; color: white; padding: 20px 0; overflow-y: auto; }
        .sidebar .logo { text-align: center; padding: 20px; border-bottom: 1px solid rgba(255,255,255,0.1); }
        .sidebar .logo h3 { font-size: 1.5rem; }
        .sidebar .nav-item { padding: 12px 25px; cursor: pointer; display: flex; align-items: center; gap: 12px; transition: 0.3s; }
        .sidebar .nav-item:hover { background: rgba(255,255,255,0.1); }
        .sidebar .nav-item.active { background: #4361ee; border-left: 4px solid white; }
        .main-content { margin-left: 260px; padding: 20px 30px; }
        .stat-card { background: white; border-radius: 15px; padding: 20px; margin-bottom: 20px; box-shadow: 0 2px 10px rgba(0,0,0,0.05); transition: 0.3s; cursor: pointer; }
        .stat-card:hover { transform: translateY(-5px); box-shadow: 0 5px 20px rgba(0,0,0,0.1); }
        .stat-value { font-size: 2rem; font-weight: bold; }
        .stat-label { color: #666; font-size: 0.85rem; }
        .btn-primary { background: #4361ee; border: none; padding: 10px 20px; border-radius: 8px; }
        .btn-primary:hover { background: #3a0ca3; }
        .modal-content { border-radius: 15px; }
        .modal-header { background: #4361ee; color: white; border-radius: 15px 15px 0 0; }
        .table { background: white; border-radius: 10px; overflow: hidden; }
        .badge-success { background: #4caf50; }
        .badge-warning { background: #ff9800; }
        .badge-danger { background: #f44336; }
        .badge-info { background: #2196f3; }
    </style>
</head>
<body>
    <div class="sidebar">
        <div class="logo">
            <h3><i class="bi bi-robot"></i> ShahnaIT</h3>
            <p>Recruitment Suite</p>
        </div>
        <div class="nav-menu">
            <div class="nav-item active" data-section="dashboard"><i class="bi bi-speedometer2"></i> Dashboard</div>
            <div class="nav-item" data-section="jds"><i class="bi bi-briefcase"></i> Job Descriptions</div>
            <div class="nav-item" data-section="candidates"><i class="bi bi-people"></i> Candidates</div>
            <div class="nav-item" data-section="applications"><i class="bi bi-file-check"></i> Applications</div>
            <div class="nav-item" data-section="pipeline"><i class="bi bi-kanban"></i> Pipeline</div>
            <div class="nav-item" data-section="interviews"><i class="bi bi-calendar-check"></i> Interviews</div>
            <div class="nav-item" data-section="offers"><i class="bi bi-envelope-paper"></i> Offers</div>
        </div>
    </div>
    
    <div class="main-content">
        <div id="dashboardSection">
            <h2 class="mb-4">Recruitment Dashboard</h2>
            <div class="row" id="statsRow">
                <div class="col-md-3"><div class="stat-card"><div class="stat-value" id="openPositions">0</div><div class="stat-label">Open Positions</div></div></div>
                <div class="col-md-3"><div class="stat-card"><div class="stat-value" id="totalCandidates">0</div><div class="stat-label">Total Candidates</div></div></div>
                <div class="col-md-3"><div class="stat-card"><div class="stat-value" id="interviewsToday">0</div><div class="stat-label">Interviews Today</div></div></div>
                <div class="col-md-3"><div class="stat-card"><div class="stat-value" id="offersSent">0</div><div class="stat-label">Offers Sent</div></div></div>
            </div>
            <div class="row mt-4">
                <div class="col-md-12">
                    <div class="card"><div class="card-header"><strong>Quick Actions</strong></div><div class="card-body">
                        <button class="btn btn-primary m-1" onclick="showJobModal()"><i class="bi bi-plus-circle"></i> Create Job</button>
                        <button class="btn btn-success m-1" onclick="showCandidateModal()"><i class="bi bi-person-plus"></i> Add Candidate</button>
                        <button class="btn btn-info m-1" onclick="showApplicationModal()"><i class="bi bi-file-check"></i> Create Application</button>
                        <button class="btn btn-warning m-1" onclick="showInterviewModal()"><i class="bi bi-calendar-plus"></i> Schedule Interview</button>
                    </div></div>
                </div>
            </div>
        </div>
        
        <div id="jdsSection" style="display: none;"><h2>Job Descriptions</h2><button class="btn btn-primary mb-3" onclick="showJobModal()">+ Create Job</button><div class="table-responsive"><table class="table table-bordered"><thead class="table-dark"><tr><th>ID</th><th>Title</th><th>Location</th><th>Status</th><th>Applications</th><th>Actions</th></tr></thead><tbody id="jobsTable"></tbody></table></div></div>
        
        <div id="candidatesSection" style="display: none;"><h2>Candidates</h2><button class="btn btn-success mb-3" onclick="showCandidateModal()">+ Add Candidate</button><div class="table-responsive"><table class="table table-bordered"><thead class="table-dark"><tr><th>ID</th><th>Name</th><th>Email</th><th>Skills</th><th>Experience</th><th>Actions</th></tr></thead><tbody id="candidatesTable"></tbody></table></div></div>
        
        <div id="applicationsSection" style="display: none;"><h2>Applications</h2><button class="btn btn-info mb-3" onclick="showApplicationModal()">+ Create Application</button><div class="table-responsive"><table class="table table-bordered"><thead class="table-dark"><td><th>ID</th><th>Candidate</th><th>Job</th><th>Match Score</th><th>Status</th><th>Actions</th></tr></thead><tbody id="applicationsTable"></tbody></table></div></div>
        
        <div id="pipelineSection" style="display: none;"><h2>Recruitment Pipeline</h2><div id="pipelineBoard" class="row"></div></div>
        
        <div id="interviewsSection" style="display: none;"><h2>Interviews</h2><button class="btn btn-warning mb-3" onclick="showInterviewModal()">+ Schedule Interview</button><div class="table-responsive"><table class="table table-bordered"><thead class="table-dark"><tr><th>ID</th><th>Candidate</th><th>Job</th><th>Interviewer</th><th>Date</th><th>Status</th><th>Actions</th></tr></thead><tbody id="interviewsTable"></tbody></table></div></div>
        
        <div id="offersSection" style="display: none;"><h2>Offer Letters</h2><button class="btn btn-primary mb-3" onclick="showOfferModal()">+ Generate Offer</button><div class="table-responsive"><table class="table table-bordered"><thead class="table-dark"><tr><th>ID</th><th>Candidate</th><th>Job</th><th>Salary</th><th>Status</th><th>Actions</th><tr></thead><tbody id="offersTable"></tbody></table></div></div>
    </div>
    
    <!-- Modals -->
    <div class="modal fade" id="jobModal" tabindex="-1"><div class="modal-dialog"><div class="modal-content"><div class="modal-header"><h5 class="modal-title">Create Job</h5><button type="button" class="btn-close" data-bs-dismiss="modal"></button></div><div class="modal-body"><input type="text" class="form-control mb-2" id="jobTitle" placeholder="Job Title"><input type="text" class="form-control mb-2" id="jobLocation" placeholder="Location"><textarea class="form-control mb-2" id="jobSkills" rows="3" placeholder="Required Skills (comma separated)"></textarea><select class="form-select mb-2" id="jobStatus"><option value="open">Open</option><option value="closed">Closed</option><option value="draft">Draft</option></select><button class="btn btn-primary w-100" onclick="createJob()">Create Job</button></div></div></div></div>
    
    <div class="modal fade" id="candidateModal" tabindex="-1"><div class="modal-dialog"><div class="modal-content"><div class="modal-header"><h5 class="modal-title">Add Candidate</h5><button type="button" class="btn-close" data-bs-dismiss="modal"></button></div><div class="modal-body"><input type="text" class="form-control mb-2" id="candName" placeholder="Full Name"><input type="email" class="form-control mb-2" id="candEmail" placeholder="Email"><input type="text" class="form-control mb-2" id="candPhone" placeholder="Phone"><textarea class="form-control mb-2" id="candSkills" rows="3" placeholder="Skills (comma separated)"></textarea><input type="number" class="form-control mb-2" id="candExp" placeholder="Experience (years)"><button class="btn btn-success w-100" onclick="createCandidate()">Add Candidate</button></div></div></div></div>
    
    <div class="modal fade" id="applicationModal" tabindex="-1"><div class="modal-dialog"><div class="modal-content"><div class="modal-header"><h5 class="modal-title">Create Application</h5><button type="button" class="btn-close" data-bs-dismiss="modal"></button></div><div class="modal-body"><select class="form-select mb-2" id="appCandidateId"><option value="">Select Candidate</option></select><select class="form-select mb-2" id="appJobId"><option value="">Select Job</option></select><button class="btn btn-info w-100" onclick="createApplication()">Create Application</button></div></div></div></div>
    
    <div class="modal fade" id="interviewModal" tabindex="-1"><div class="modal-dialog"><div class="modal-content"><div class="modal-header"><h5 class="modal-title">Schedule Interview</h5><button type="button" class="btn-close" data-bs-dismiss="modal"></button></div><div class="modal-body"><select class="form-select mb-2" id="interviewAppId"><option value="">Select Application</option></select><input type="text" class="form-control mb-2" id="interviewerName" placeholder="Interviewer Name"><input type="datetime-local" class="form-control mb-2" id="interviewDate"><select class="form-select mb-2" id="interviewType"><option value="Technical">Technical</option><option value="HR">HR</option><option value="Managerial">Managerial</option></select><button class="btn btn-warning w-100" onclick="scheduleInterview()">Schedule</button></div></div></div></div>
    
    <div class="modal fade" id="offerModal" tabindex="-1"><div class="modal-dialog"><div class="modal-content"><div class="modal-header"><h5 class="modal-title">Generate Offer</h5><button type="button" class="btn-close" data-bs-dismiss="modal"></button></div><div class="modal-body"><select class="form-select mb-2" id="offerAppId"><option value="">Select Application</option></select><input type="text" class="form-control mb-2" id="offerSalary" placeholder="Salary Amount"><input type="date" class="form-control mb-2" id="offerJoiningDate"><button class="btn btn-primary w-100" onclick="generateOffer()">Generate Offer</button></div></div></div></div>
    
    <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.1.3/dist/js/bootstrap.bundle.min.js"></script>
    <script>
        // Navigation
        document.querySelectorAll('.nav-item').forEach(item => {
            item.addEventListener('click', () => {
                document.querySelectorAll('.nav-item').forEach(n => n.classList.remove('active'));
                item.classList.add('active');
                const sections = ['dashboard', 'jds', 'candidates', 'applications', 'pipeline', 'interviews', 'offers'];
                sections.forEach(s => document.getElementById(s + 'Section').style.display = 'none');
                document.getElementById(item.dataset.section + 'Section').style.display = 'block';
                if (item.dataset.section === 'dashboard') loadDashboard();
                if (item.dataset.section === 'jds') loadJobs();
                if (item.dataset.section === 'candidates') loadCandidates();
                if (item.dataset.section === 'applications') loadApplications();
                if (item.dataset.section === 'interviews') loadInterviews();
                if (item.dataset.section === 'offers') loadOffers();
                if (item.dataset.section === 'pipeline') loadPipeline();
            });
        });
        
        async function loadDashboard() {
            try {
                const res = await fetch('/api/dashboard/stats');
                const data = await res.json();
                document.getElementById('openPositions').innerText = data.open_positions || 0;
                document.getElementById('totalCandidates').innerText = data.total_candidates || 0;
                document.getElementById('interviewsToday').innerText = data.interviews_today || 0;
                document.getElementById('offersSent').innerText = data.offers_sent || 0;
            } catch(e) { console.error(e); }
        }
        
        async function loadJobs() {
            try {
                const res = await fetch('/api/jobs');
                const jobs = await res.json();
                const tbody = document.getElementById('jobsTable');
                if (jobs.length === 0) { tbody.innerHTML = '<tr><td colspan="6" class="text-center">No jobs created</td></tr>'; return; }
                tbody.innerHTML = jobs.map(j => `<tr><td>${j.id}</td><td>${j.title}</td><td>${j.location || 'Remote'}</td><td><span class="badge ${j.status === 'open' ? 'bg-success' : 'bg-secondary'}">${j.status}</span></td><td>${j.applications || 0}</td><td><button class="btn btn-sm btn-primary" onclick="createApplicationForJob(${j.id})">Apply</button></td></tr>`).join('');
            } catch(e) { console.error(e); }
        }
        
        async function loadCandidates() {
            try {
                const res = await fetch('/api/candidates');
                const data = await res.json();
                const tbody = document.getElementById('candidatesTable');
                if (data.candidates.length === 0) { tbody.innerHTML = '<tr><td colspan="6" class="text-center">No candidates added</td></tr>'; return; }
                tbody.innerHTML = data.candidates.map(c => `<tr><td>${c.id}</td><td>${c.name}</td><td>${c.email}</td><td>${c.skills || '-'}</td><td>${c.total_experience || 0} years</td><td><button class="btn btn-sm btn-success" onclick="createApplicationForCandidate(${c.id})">Apply</button></td></tr>`).join('');
            } catch(e) { console.error(e); }
        }
        
        async function loadApplications() {
            try {
                const res = await fetch('/api/applications');
                const apps = await res.json();
                const tbody = document.getElementById('applicationsTable');
                if (apps.length === 0) { tbody.innerHTML = '<tr><td colspan="6" class="text-center">No applications</td></tr>'; return; }
                tbody.innerHTML = apps.map(a => `<tr><td>${a.id}</td><td>${a.candidate_name}</td><td>${a.job_title}</td><td><span class="badge ${a.match_score >= 70 ? 'bg-success' : a.match_score >= 50 ? 'bg-warning' : 'bg-secondary'}">${a.match_score}%</span></td><td>${a.status}</td><td><button class="btn btn-sm btn-info" onclick="moveApplication(${a.id})">Move</button></td></tr>`).join('');
            } catch(e) { console.error(e); }
        }
        
        async function loadInterviews() {
            try {
                const res = await fetch('/api/interviews');
                const interviews = await res.json();
                const tbody = document.getElementById('interviewsTable');
                if (interviews.length === 0) { tbody.innerHTML = '<tr><td colspan="7" class="text-center">No interviews scheduled</td></tr>'; return; }
                tbody.innerHTML = interviews.map(i => `<tr><td>${i.id}</td><td>${i.candidate_name}</td><td>${i.job_title}</td><td>${i.interviewer_name || 'TBD'}</td><td>${new Date(i.scheduled_time).toLocaleString()}</td><td>${i.status}</td><td><button class="btn btn-sm btn-warning" onclick="completeInterview(${i.id})">Complete</button></td></tr>`).join('');
            } catch(e) { console.error(e); }
        }
        
        async function loadOffers() {
            try {
                const res = await fetch('/api/offers');
                const offers = await res.json();
                const tbody = document.getElementById('offersTable');
                if (offers.length === 0) { tbody.innerHTML = '<tr><td colspan="6" class="text-center">No offers generated</td></tr>'; return; }
                tbody.innerHTML = offers.map(o => `<tr><td>${o.id}</td><td>${o.candidate_name}</td><td>${o.job_title}</td><td>$${o.base_salary}</td><td>${o.status}</td><td><button class="btn btn-sm btn-primary" onclick="viewOffer(${o.id})">View</button></td></tr>`).join('');
            } catch(e) { console.error(e); }
        }
        
        async function loadPipeline() {
            document.getElementById('pipelineBoard').innerHTML = '<div class="alert alert-info">Pipeline feature - Drag and drop coming soon</div>';
        }
        
        async function createJob() {
            const title = document.getElementById('jobTitle').value;
            if (!title) { alert('Enter job title'); return; }
            const data = { title, location: document.getElementById('jobLocation').value, skills_required: document.getElementById('jobSkills').value, status: document.getElementById('jobStatus').value };
            const res = await fetch('/api/jobs', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(data) });
            const result = await res.json();
            if (result.success) { alert('Job created!'); bootstrap.Modal.getInstance(document.getElementById('jobModal')).hide(); loadJobs(); loadDashboard(); document.getElementById('jobTitle').value = ''; }
        }
        
        async function createCandidate() {
            const name = document.getElementById('candName').value;
            const email = document.getElementById('candEmail').value;
            if (!name || !email) { alert('Enter name and email'); return; }
            const data = { first_name: name.split(' ')[0], last_name: name.split(' ').slice(1).join(' '), email, phone: document.getElementById('candPhone').value, skills: document.getElementById('candSkills').value, total_experience: parseFloat(document.getElementById('candExp').value) };
            const res = await fetch('/api/candidates', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(data) });
            const result = await res.json();
            if (result.success) { alert('Candidate added!'); bootstrap.Modal.getInstance(document.getElementById('candidateModal')).hide(); loadCandidates(); loadDashboard(); }
        }
        
        async function createApplication() {
            const candidate_id = document.getElementById('appCandidateId').value;
            const jd_id = document.getElementById('appJobId').value;
            if (!candidate_id || !jd_id) { alert('Select candidate and job'); return; }
            const res = await fetch('/api/applications', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ candidate_id: parseInt(candidate_id), jd_id: parseInt(jd_id) }) });
            const result = await res.json();
            if (result.success) { alert(`Application created! Match Score: ${result.match_score}%`); bootstrap.Modal.getInstance(document.getElementById('applicationModal')).hide(); loadApplications(); loadJobs(); loadDashboard(); }
        }
        
        async function createApplicationForJob(jd_id) { document.getElementById('appJobId').value = jd_id; await loadCandidateDropdown(); new bootstrap.Modal(document.getElementById('applicationModal')).show(); }
        async function createApplicationForCandidate(candidate_id) { document.getElementById('appCandidateId').value = candidate_id; await loadJobDropdown(); new bootstrap.Modal(document.getElementById('applicationModal')).show(); }
        
        async function scheduleInterview() {
            const app_id = document.getElementById('interviewAppId').value;
            if (!app_id) { alert('Select application'); return; }
            const data = { application_id: parseInt(app_id), interviewer_name: document.getElementById('interviewerName').value, scheduled_time: document.getElementById('interviewDate').value, round_type: document.getElementById('interviewType').value };
            const res = await fetch('/api/interviews', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(data) });
            if (res.ok) { alert('Interview scheduled!'); bootstrap.Modal.getInstance(document.getElementById('interviewModal')).hide(); loadInterviews(); }
        }
        
        async function generateOffer() {
            const app_id = document.getElementById('offerAppId').value;
            if (!app_id) { alert('Select application'); return; }
            const data = { application_id: parseInt(app_id), base_salary: parseFloat(document.getElementById('offerSalary').value), joining_date: document.getElementById('offerJoiningDate').value };
            const res = await fetch('/api/offers', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(data) });
            const result = await res.json();
            if (result.success) { alert('Offer generated!'); bootstrap.Modal.getInstance(document.getElementById('offerModal')).hide(); loadOffers(); }
        }
        
        async function moveApplication(id) { const stage = prompt('Enter new stage (screening/interview/offer/hired/rejected):'); if (stage) { await fetch(`/api/applications/${id}/move`, { method: 'PUT', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ stage }) }); loadApplications(); } }
        async function completeInterview(id) { await fetch(`/api/interviews/${id}/complete`, { method: 'PUT', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ result: 'pass', feedback: 'Completed' }) }); loadInterviews(); }
        function viewOffer(id) { alert(`View offer ${id}`); }
        
        async function loadCandidateDropdown() { const res = await fetch('/api/candidates'); const data = await res.json(); const select = document.getElementById('appCandidateId'); select.innerHTML = '<option value="">Select Candidate</option>' + data.candidates.map(c => `<option value="${c.id}">${c.name}</option>`).join(''); }
        async function loadJobDropdown() { const res = await fetch('/api/jobs'); const jobs = await res.json(); const select = document.getElementById('appJobId'); select.innerHTML = '<option value="">Select Job</option>' + jobs.map(j => `<option value="${j.id}">${j.title}</option>`).join(''); }
        async function loadAppDropdown() { const res = await fetch('/api/applications'); const apps = await res.json(); const select = document.getElementById('interviewAppId'); select.innerHTML = '<option value="">Select Application</option>' + apps.map(a => `<option value="${a.id}">${a.candidate_name} - ${a.job_title}</option>`).join(''); document.getElementById('offerAppId').innerHTML = select.innerHTML; }
        
        function showJobModal() { new bootstrap.Modal(document.getElementById('jobModal')).show(); }
        function showCandidateModal() { new bootstrap.Modal(document.getElementById('candidateModal')).show(); }
        function showApplicationModal() { loadCandidateDropdown(); loadJobDropdown(); new bootstrap.Modal(document.getElementById('applicationModal')).show(); }
        function showInterviewModal() { loadAppDropdown(); new bootstrap.Modal(document.getElementById('interviewModal')).show(); }
        function showOfferModal() { loadAppDropdown(); new bootstrap.Modal(document.getElementById('offerModal')).show(); }
        
        loadDashboard(); loadJobs(); loadCandidates(); loadApplications(); loadInterviews(); loadOffers();
    </script>
</body>
</html>
'''

# ============= DATA STORES =============
jobs = []
candidates = []
applications = []
interviews = []
offers = []
next_id = 1

# ============= HELPER FUNCTIONS =============
def calculate_match_score(job_skills, candidate_skills):
    if not job_skills or not candidate_skills:
        return 0
    job_list = [s.strip().lower() for s in job_skills.split(',') if s.strip()]
    cand_list = [s.strip().lower() for s in candidate_skills.split(',') if s.strip()]
    if not job_list:
        return 0
    matches = sum(1 for s in job_list if s in cand_list)
    return round((matches / len(job_list)) * 100, 2)

def generate_code(prefix):
    if prefix == 'JD':
        return f"JD-{len(jobs)+1:04d}"
    elif prefix == 'CAN':
        return f"CAN-{len(candidates)+1:04d}"
    elif prefix == 'APP':
        return f"APP-{len(applications)+1:04d}"
    elif prefix == 'OFF':
        return f"OFF-{len(offers)+1:04d}"
    return f"{prefix}-{next_id:04d}"

# ============= API ROUTES =============
@app.route('/')
def index():
    return render_template_string(DASHBOARD_TEMPLATE)

@app.route('/health')
def health():
    return jsonify({'status': 'ok', 'timestamp': datetime.now().isoformat()})

@app.route('/api/dashboard/stats')
def dashboard_stats():
    return jsonify({
        'open_positions': len([j for j in jobs if j.get('status') == 'open']),
        'total_candidates': len(candidates),
        'interviews_today': len([i for i in interviews if i.get('status') == 'scheduled']),
        'offers_sent': len([o for o in offers if o.get('status') == 'sent'])
    })

@app.route('/api/jobs', methods=['GET', 'POST'])
def manage_jobs():
    global next_id
    if request.method == 'POST':
        data = request.json
        job = {
            'id': next_id,
            'code': generate_code('JD'),
            'title': data.get('title'),
            'location': data.get('location', 'Remote'),
            'skills_required': data.get('skills_required', ''),
            'status': data.get('status', 'open'),
            'applications': 0,
            'created_at': datetime.now().isoformat()
        }
        jobs.append(job)
        next_id += 1
        return jsonify({'success': True, 'job_id': job['id']})
    return jsonify(jobs)

@app.route('/api/candidates', methods=['GET', 'POST'])
def manage_candidates():
    global next_id
    if request.method == 'POST':
        data = request.json
        candidate = {
            'id': next_id,
            'code': generate_code('CAN'),
            'first_name': data.get('first_name', ''),
            'last_name': data.get('last_name', ''),
            'name': f"{data.get('first_name', '')} {data.get('last_name', '')}".strip(),
            'email': data.get('email'),
            'phone': data.get('phone', ''),
            'skills': data.get('skills', ''),
            'total_experience': data.get('total_experience', 0),
            'created_at': datetime.now().isoformat()
        }
        candidates.append(candidate)
        next_id += 1
        return jsonify({'success': True, 'candidate_id': candidate['id']})
    
    page = int(request.args.get('page', 1))
    per_page = 20
    search = request.args.get('search', '')
    filtered = candidates
    if search:
        filtered = [c for c in candidates if search.lower() in c.get('name', '').lower() or search.lower() in c.get('email', '').lower()]
    start = (page - 1) * per_page
    end = start + per_page
    return jsonify({
        'candidates': filtered[start:end],
        'total': len(filtered),
        'page': page,
        'pages': (len(filtered) + per_page - 1) // per_page
    })

@app.route('/api/applications', methods=['GET', 'POST'])
def manage_applications():
    if request.method == 'POST':
        data = request.json
        job = next((j for j in jobs if j['id'] == data.get('jd_id')), None)
        candidate = next((c for c in candidates if c['id'] == data.get('candidate_id')), None)
        match_score = calculate_match_score(job.get('skills_required', '') if job else '', candidate.get('skills', '') if candidate else '')
        application = {
            'id': len(applications) + 1,
            'code': generate_code('APP'),
            'candidate_id': data.get('candidate_id'),
            'jd_id': data.get('jd_id'),
            'candidate_name': candidate.get('name') if candidate else '',
            'job_title': job.get('title') if job else '',
            'match_score': match_score,
            'status': 'new',
            'application_date': datetime.now().date().isoformat(),
            'created_at': datetime.now().isoformat()
        }
        applications.append(application)
        if job:
            job['applications'] = job.get('applications', 0) + 1
        return jsonify({'success': True, 'application_id': application['id'], 'match_score': match_score})
    return jsonify(applications)

@app.route('/api/applications/<int:app_id>/move', methods=['PUT'])
def move_application(app_id):
    data = request.json
    for app in applications:
        if app['id'] == app_id:
            app['status'] = data.get('stage', app['status'])
            break
    return jsonify({'success': True})

@app.route('/api/interviews', methods=['GET', 'POST'])
def manage_interviews():
    if request.method == 'POST':
        data = request.json
        application = next((a for a in applications if a['id'] == data.get('application_id')), None)
        candidate = next((c for c in candidates if c['id'] == application.get('candidate_id')), None) if application else None
        job = next((j for j in jobs if j['id'] == application.get('jd_id')), None) if application else None
        interview = {
            'id': len(interviews) + 1,
            'application_id': data.get('application_id'),
            'candidate_name': candidate.get('name') if candidate else '',
            'job_title': job.get('title') if job else '',
            'interviewer_name': data.get('interviewer_name', ''),
            'scheduled_time': data.get('scheduled_time'),
            'round_type': data.get('round_type', 'Technical'),
            'status': 'scheduled',
            'created_at': datetime.now().isoformat()
        }
        interviews.append(interview)
        if application:
            application['status'] = 'interview-scheduled'
        return jsonify({'success': True, 'interview_id': interview['id']})
    return jsonify(interviews)

@app.route('/api/interviews/<int:interview_id>/complete', methods=['PUT'])
def complete_interview(interview_id):
    for interview in interviews:
        if interview['id'] == interview_id:
            interview['status'] = 'completed'
            break
    return jsonify({'success': True})

@app.route('/api/offers', methods=['GET', 'POST'])
def manage_offers():
    if request.method == 'POST':
        data = request.json
        application = next((a for a in applications if a['id'] == data.get('application_id')), None)
        candidate = next((c for c in candidates if c['id'] == application.get('candidate_id')), None) if application else None
        job = next((j for j in jobs if j['id'] == application.get('jd_id')), None) if application else None
        offer = {
            'id': len(offers) + 1,
            'code': generate_code('OFF'),
            'application_id': data.get('application_id'),
            'candidate_name': candidate.get('name') if candidate else '',
            'job_title': job.get('title') if job else '',
            'base_salary': data.get('base_salary', 0),
            'joining_date': data.get('joining_date'),
            'status': 'draft',
            'created_at': datetime.now().isoformat()
        }
        offers.append(offer)
        if application:
            application['status'] = 'offered'
        return jsonify({'success': True, 'offer_id': offer['id']})
    return jsonify(offers)

# ============= MAIN =============
if __name__ == '__main__':
    port = int(os.environ.get('PORT', 8080))
    print("=" * 50)
    print("🚀 ShahnaIT Scout - Recruitment System")
    print("=" * 50)
    print(f"✅ Server running on port: {port}")
    print("=" * 50)
    app.run(host='0.0.0.0', port=port, debug=False)
