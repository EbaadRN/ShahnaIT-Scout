from flask import Flask, render_template_string, jsonify, request
from datetime import datetime
import os

app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'dev-secret-key')

# ============= SIMPLE WORKING DASHBOARD =============
DASHBOARD_TEMPLATE = '''
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>ShahnaIT Scout - Recruitment System</title>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.1.3/dist/css/bootstrap.min.css" rel="stylesheet">
    <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/bootstrap-icons@1.8.1/font/bootstrap-icons.css">
    <style>
        body { background: #f0f2f5; font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; }
        .sidebar { position: fixed; left: 0; top: 0; width: 260px; height: 100vh; background: #1a1a2e; color: white; overflow-y: auto; }
        .sidebar .logo { text-align: center; padding: 20px; border-bottom: 1px solid rgba(255,255,255,0.1); }
        .sidebar .nav-item { padding: 12px 25px; cursor: pointer; display: flex; align-items: center; gap: 12px; transition: 0.3s; }
        .sidebar .nav-item:hover { background: rgba(255,255,255,0.1); }
        .sidebar .nav-item.active { background: #4361ee; border-left: 4px solid white; }
        .main-content { margin-left: 260px; padding: 20px 30px; }
        .stat-card { background: white; border-radius: 15px; padding: 20px; margin-bottom: 20px; box-shadow: 0 2px 10px rgba(0,0,0,0.05); transition: 0.3s; }
        .stat-card:hover { transform: translateY(-5px); }
        .stat-value { font-size: 2rem; font-weight: bold; }
        .stat-label { color: #666; font-size: 0.85rem; }
        .btn-primary { background: #4361ee; border: none; padding: 10px 20px; border-radius: 8px; color: white; }
        .btn-primary:hover { background: #3a0ca3; }
        .btn-success { background: #28a745; border: none; padding: 10px 20px; border-radius: 8px; color: white; }
        .btn-info { background: #17a2b8; border: none; padding: 10px 20px; border-radius: 8px; color: white; }
        .table { background: white; border-radius: 10px; overflow: hidden; }
        .modal-header { background: #4361ee; color: white; }
    </style>
</head>
<body>
    <div class="sidebar">
        <div class="logo">
            <h3><i class="bi bi-robot"></i> ShahnaIT</h3>
            <p>Recruitment Suite</p>
        </div>
        <div class="nav-item active" data-section="dashboard"><i class="bi bi-speedometer2"></i> Dashboard</div>
        <div class="nav-item" data-section="jobs"><i class="bi bi-briefcase"></i> Jobs</div>
        <div class="nav-item" data-section="candidates"><i class="bi bi-people"></i> Candidates</div>
        <div class="nav-item" data-section="applications"><i class="bi bi-file-check"></i> Applications</div>
        <div class="nav-item" data-section="interviews"><i class="bi bi-calendar-check"></i> Interviews</div>
        <div class="nav-item" data-section="offers"><i class="bi bi-envelope-paper"></i> Offers</div>
    </div>
    
    <div class="main-content">
        <div id="dashboardSection">
            <h2 class="mb-4">Recruitment Dashboard</h2>
            <div class="row">
                <div class="col-md-3"><div class="stat-card"><div class="stat-value" id="openPositions">0</div><div class="stat-label">Open Positions</div></div></div>
                <div class="col-md-3"><div class="stat-card"><div class="stat-value" id="totalCandidates">0</div><div class="stat-label">Total Candidates</div></div></div>
                <div class="col-md-3"><div class="stat-card"><div class="stat-value" id="interviewsToday">0</div><div class="stat-label">Interviews Today</div></div></div>
                <div class="col-md-3"><div class="stat-card"><div class="stat-value" id="offersSent">0</div><div class="stat-label">Offers Sent</div></div></div>
            </div>
            <div class="card mt-4"><div class="card-header">Quick Actions</div><div class="card-body">
                <button class="btn btn-primary m-1" onclick="showJobModal()">Create Job</button>
                <button class="btn btn-success m-1" onclick="showCandidateModal()">Add Candidate</button>
                <button class="btn btn-info m-1" onclick="showApplicationModal()">Create Application</button>
            </div></div>
        </div>
        
        <div id="jobsSection" style="display: none;"><h2>Jobs</h2><button class="btn btn-primary mb-3" onclick="showJobModal()">Create Job</button><div class="table-responsive"><table class="table table-bordered"><thead class="table-dark"><tr><th>ID</th><th>Title</th><th>Location</th><th>Status</th><th>Applications</th><th>Actions</th></tr></thead><tbody id="jobsTable"></tbody></table></div></div>
        
        <div id="candidatesSection" style="display: none;"><h2>Candidates</h2><button class="btn btn-success mb-3" onclick="showCandidateModal()">Add Candidate</button><div class="table-responsive"><table class="table table-bordered"><thead class="table-dark"><tr><th>ID</th><th>Name</th><th>Email</th><th>Skills</th><th>Experience</th><th>Actions</th></tr></thead><tbody id="candidatesTable"></tbody></table></div></div>
        
        <div id="applicationsSection" style="display: none;"><h2>Applications</h2><button class="btn btn-info mb-3" onclick="showApplicationModal()">Create Application</button><div class="table-responsive"><table class="table table-bordered"><thead class="table-dark"><tr><th>ID</th><th>Candidate</th><th>Job</th><th>Match Score</th><th>Status</th><th>Actions</th></tr></thead><tbody id="applicationsTable"></tbody></table></div></div>
        
        <div id="interviewsSection" style="display: none;"><h2>Interviews</h2><div class="table-responsive"><table class="table table-bordered"><thead class="table-dark"><tr><th>ID</th><th>Candidate</th><th>Job</th><th>Interviewer</th><th>Date</th><th>Status</th></tr></thead><tbody id="interviewsTable"></tbody></table></div></div>
        
        <div id="offersSection" style="display: none;"><h2>Offers</h2><div class="table-responsive"><table class="table table-bordered"><thead class="table-dark"><tr><th>ID</th><th>Candidate</th><th>Job</th><th>Salary</th><th>Status</th></tr></thead><tbody id="offersTable"></tbody></table></div></div>
    </div>
    
    <!-- Modals -->
    <div class="modal fade" id="jobModal" tabindex="-1"><div class="modal-dialog"><div class="modal-content"><div class="modal-header"><h5 class="modal-title">Create Job</h5><button type="button" class="btn-close btn-close-white" data-bs-dismiss="modal"></button></div><div class="modal-body"><input type="text" class="form-control mb-2" id="jobTitle" placeholder="Job Title"><input type="text" class="form-control mb-2" id="jobLocation" placeholder="Location"><textarea class="form-control mb-2" id="jobSkills" rows="3" placeholder="Required Skills (comma separated)"></textarea><select class="form-select mb-2" id="jobStatus"><option value="open">Open</option><option value="closed">Closed</option></select><button class="btn btn-primary w-100" onclick="createJob()">Create Job</button></div></div></div></div>
    
    <div class="modal fade" id="candidateModal" tabindex="-1"><div class="modal-dialog"><div class="modal-content"><div class="modal-header"><h5 class="modal-title">Add Candidate</h5><button type="button" class="btn-close btn-close-white" data-bs-dismiss="modal"></button></div><div class="modal-body"><input type="text" class="form-control mb-2" id="candName" placeholder="Full Name"><input type="email" class="form-control mb-2" id="candEmail" placeholder="Email"><input type="text" class="form-control mb-2" id="candPhone" placeholder="Phone"><textarea class="form-control mb-2" id="candSkills" rows="3" placeholder="Skills (comma separated)"></textarea><input type="number" class="form-control mb-2" id="candExp" placeholder="Experience (years)"><button class="btn btn-success w-100" onclick="createCandidate()">Add Candidate</button></div></div></div></div>
    
    <div class="modal fade" id="applicationModal" tabindex="-1"><div class="modal-dialog"><div class="modal-content"><div class="modal-header"><h5 class="modal-title">Create Application</h5><button type="button" class="btn-close btn-close-white" data-bs-dismiss="modal"></button></div><div class="modal-body"><select class="form-select mb-2" id="appCandidateId"><option value="">Select Candidate</option></select><select class="form-select mb-2" id="appJobId"><option value="">Select Job</option></select><button class="btn btn-info w-100" onclick="createApplication()">Create Application</button></div></div></div></div>
    
    <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.1.3/dist/js/bootstrap.bundle.min.js"></script>
    <script>
        // Navigation
        document.querySelectorAll('.nav-item').forEach(item => {
            item.addEventListener('click', function() {
                document.querySelectorAll('.nav-item').forEach(n => n.classList.remove('active'));
                this.classList.add('active');
                var sections = ['dashboard', 'jobs', 'candidates', 'applications', 'interviews', 'offers'];
                sections.forEach(function(s) {
                    var el = document.getElementById(s + 'Section');
                    if (el) el.style.display = 'none';
                });
                var sectionName = this.getAttribute('data-section');
                var sectionEl = document.getElementById(sectionName + 'Section');
                if (sectionEl) sectionEl.style.display = 'block';
                if (sectionName === 'dashboard') loadDashboard();
                if (sectionName === 'jobs') loadJobs();
                if (sectionName === 'candidates') loadCandidates();
                if (sectionName === 'applications') loadApplications();
            });
        });
        
        async function loadDashboard() {
            try {
                var res = await fetch('/api/dashboard/stats');
                var data = await res.json();
                document.getElementById('openPositions').innerText = data.open_positions || 0;
                document.getElementById('totalCandidates').innerText = data.total_candidates || 0;
                document.getElementById('interviewsToday').innerText = data.interviews_today || 0;
                document.getElementById('offersSent').innerText = data.offers_sent || 0;
            } catch(e) { console.log(e); }
        }
        
        async function loadJobs() {
            try {
                var res = await fetch('/api/jobs');
                var jobs = await res.json();
                var tbody = document.getElementById('jobsTable');
                if (jobs.length === 0) { tbody.innerHTML = '<tr><td colspan="6" class="text-center">No jobs created</td></tr>'; return; }
                var html = '';
                for (var i = 0; i < jobs.length; i++) {
                    var j = jobs[i];
                    html += '<tr><td>' + j.id + '</td><td>' + j.title + '</td><td>' + (j.location || 'Remote') + '</td><td><span class="badge bg-success">' + j.status + '</span></td><td>' + (j.applications || 0) + '</td><td><button class="btn btn-sm btn-primary" onclick="createApplicationForJob(' + j.id + ')">Apply</button></td></tr>';
                }
                tbody.innerHTML = html;
            } catch(e) { console.log(e); }
        }
        
        async function loadCandidates() {
            try {
                var res = await fetch('/api/candidates');
                var data = await res.json();
                var tbody = document.getElementById('candidatesTable');
                if (data.candidates.length === 0) { tbody.innerHTML = '<tr><td colspan="6" class="text-center">No candidates added</td></tr>'; return; }
                var html = '';
                for (var i = 0; i < data.candidates.length; i++) {
                    var c = data.candidates[i];
                    html += '<tr><td>' + c.id + '</td><td>' + c.name + '</td><td>' + c.email + '</td><td>' + (c.skills || '-') + '</td><td>' + (c.total_experience || 0) + ' years</td><td><button class="btn btn-sm btn-success" onclick="createApplicationForCandidate(' + c.id + ')">Apply</button></td></tr>';
                }
                tbody.innerHTML = html;
            } catch(e) { console.log(e); }
        }
        
        async function loadApplications() {
            try {
                var res = await fetch('/api/applications');
                var apps = await res.json();
                var tbody = document.getElementById('applicationsTable');
                if (apps.length === 0) { tbody.innerHTML = '<tr><td colspan="6" class="text-center">No applications</td></tr>'; return; }
                var html = '';
                for (var i = 0; i < apps.length; i++) {
                    var a = apps[i];
                    var badgeClass = a.match_score >= 70 ? 'bg-success' : (a.match_score >= 50 ? 'bg-warning' : 'bg-secondary');
                    html += '<tr><td>' + a.id + '</td><td>' + (a.candidate_name || '-') + '</td><td>' + (a.job_title || '-') + '</td><td><span class="badge ' + badgeClass + '">' + (a.match_score || 0) + '%</span></td><td>' + a.status + '</td><td><button class="btn btn-sm btn-info" onclick="moveApplication(' + a.id + ')">Move</button></td></tr>';
                }
                tbody.innerHTML = html;
            } catch(e) { console.log(e); }
        }
        
        async function createJob() {
            var title = document.getElementById('jobTitle').value;
            if (!title) { alert('Enter job title'); return; }
            var data = { title: title, location: document.getElementById('jobLocation').value, skills_required: document.getElementById('jobSkills').value, status: document.getElementById('jobStatus').value };
            var res = await fetch('/api/jobs', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(data) });
            var result = await res.json();
            if (result.success) { alert('Job created!'); var modal = bootstrap.Modal.getInstance(document.getElementById('jobModal')); modal.hide(); loadJobs(); loadDashboard(); }
        }
        
        async function createCandidate() {
            var name = document.getElementById('candName').value;
            var email = document.getElementById('candEmail').value;
            if (!name || !email) { alert('Enter name and email'); return; }
            var nameParts = name.split(' ');
            var data = { first_name: nameParts[0], last_name: nameParts.slice(1).join(' '), email: email, phone: document.getElementById('candPhone').value, skills: document.getElementById('candSkills').value, total_experience: parseFloat(document.getElementById('candExp').value) || 0 };
            var res = await fetch('/api/candidates', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(data) });
            var result = await res.json();
            if (result.success) { alert('Candidate added!'); var modal = bootstrap.Modal.getInstance(document.getElementById('candidateModal')); modal.hide(); loadCandidates(); loadDashboard(); }
        }
        
        async function createApplication() {
            var candidateId = document.getElementById('appCandidateId').value;
            var jobId = document.getElementById('appJobId').value;
            if (!candidateId || !jobId) { alert('Select candidate and job'); return; }
            var res = await fetch('/api/applications', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ candidate_id: parseInt(candidateId), jd_id: parseInt(jobId) }) });
            var result = await res.json();
            if (result.success) { alert('Application created! Match Score: ' + result.match_score + '%'); var modal = bootstrap.Modal.getInstance(document.getElementById('applicationModal')); modal.hide(); loadApplications(); loadJobs(); loadDashboard(); }
        }
        
        async function createApplicationForJob(jobId) {
            document.getElementById('appJobId').value = jobId;
            await loadCandidateDropdown();
            new bootstrap.Modal(document.getElementById('applicationModal')).show();
        }
        
        async function createApplicationForCandidate(candidateId) {
            document.getElementById('appCandidateId').value = candidateId;
            await loadJobDropdown();
            new bootstrap.Modal(document.getElementById('applicationModal')).show();
        }
        
        async function moveApplication(appId) {
            var stage = prompt('Enter stage (screening / interview / offer / hired / rejected):');
            if (stage) {
                await fetch('/api/applications/' + appId + '/move', { method: 'PUT', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ stage: stage }) });
                loadApplications();
            }
        }
        
        async function loadCandidateDropdown() {
            var res = await fetch('/api/candidates');
            var data = await res.json();
            var select = document.getElementById('appCandidateId');
            var html = '<option value="">Select Candidate</option>';
            for (var i = 0; i < data.candidates.length; i++) {
                html += '<option value="' + data.candidates[i].id + '">' + data.candidates[i].name + '</option>';
            }
            select.innerHTML = html;
        }
        
        async function loadJobDropdown() {
            var res = await fetch('/api/jobs');
            var jobs = await res.json();
            var select = document.getElementById('appJobId');
            var html = '<option value="">Select Job</option>';
            for (var i = 0; i < jobs.length; i++) {
                html += '<option value="' + jobs[i].id + '">' + jobs[i].title + '</option>';
            }
            select.innerHTML = html;
        }
        
        function showJobModal() { new bootstrap.Modal(document.getElementById('jobModal')).show(); }
        function showCandidateModal() { new bootstrap.Modal(document.getElementById('candidateModal')).show(); }
        function showApplicationModal() { loadCandidateDropdown(); loadJobDropdown(); new bootstrap.Modal(document.getElementById('applicationModal')).show(); }
        
        loadDashboard(); loadJobs(); loadCandidates(); loadApplications();
    </script>
</body>
</html>
'''

# ============= DATA STORES =============
jobs = []
candidates = []
applications = []
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

# ============= API ROUTES =============
@app.route('/')
def index():
    return render_template_string(DASHBOARD_TEMPLATE)

@app.route('/health')
def health():
    return jsonify({'status': 'ok', 'timestamp': datetime.now().isoformat()})

@app.route('/api/dashboard/stats')
def dashboard_stats():
    interviews_today = 0
    for i in interviews:
        if i.get('status') == 'scheduled':
            interviews_today += 1
    return jsonify({
        'open_positions': len([j for j in jobs if j.get('status') == 'open']),
        'total_candidates': len(candidates),
        'interviews_today': interviews_today,
        'offers_sent': 0
    })

@app.route('/api/jobs', methods=['GET', 'POST'])
def manage_jobs():
    global next_id
    if request.method == 'POST':
        data = request.json
        job = {
            'id': next_id,
            'title': data.get('title', 'Untitled'),
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
            'first_name': data.get('first_name', ''),
            'last_name': data.get('last_name', ''),
            'name': f"{data.get('first_name', '')} {data.get('last_name', '')}".strip(),
            'email': data.get('email', ''),
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

# ============= MAIN =============
if __name__ == '__main__':
    port = int(os.environ.get('PORT', 8080))
    print("=" * 50)
    print("ShahnaIT Scout - Recruitment System")
    print("=" * 50)
    print(f"Server running on port: {port}")
    print("=" * 50)
    app.run(host='0.0.0.0', port=port, debug=False)
