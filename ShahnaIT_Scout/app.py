from flask import Flask, render_template_string, jsonify, request
from datetime import datetime
import os

app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'dev-secret-key')

# ============= MODERN DASHBOARD - BEIGE & DARK TEAL THEME =============
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
        
        body {
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            background: #F5F2EB;
        }
        
        /* Dark Teal Sidebar */
        .sidebar {
            position: fixed;
            left: 0;
            top: 0;
            width: 280px;
            height: 100vh;
            background: #0D3B3F;
            color: white;
            overflow-y: auto;
            z-index: 1000;
            box-shadow: 2px 0 10px rgba(0,0,0,0.1);
        }
        
        .sidebar .logo {
            padding: 25px;
            text-align: center;
            border-bottom: 1px solid rgba(255,255,255,0.1);
        }
        
        .sidebar .logo h3 {
            font-size: 1.6rem;
            font-weight: 700;
        }
        
        .sidebar .logo p {
            font-size: 0.75rem;
            opacity: 0.7;
        }
        
        .sidebar .nav-item {
            padding: 14px 25px;
            margin: 5px 0;
            cursor: pointer;
            display: flex;
            align-items: center;
            gap: 12px;
            transition: all 0.3s;
            border-left: 3px solid transparent;
        }
        
        .sidebar .nav-item:hover {
            background: rgba(255,255,255,0.1);
        }
        
        .sidebar .nav-item.active {
            background: rgba(255,255,255,0.15);
            border-left-color: #D4A574;
        }
        
        .sidebar .nav-item i {
            font-size: 1.2rem;
            width: 25px;
        }
        
        /* Main Content */
        .main-content {
            margin-left: 280px;
            padding: 25px 35px;
            min-height: 100vh;
        }
        
        /* Header */
        .page-header {
            margin-bottom: 30px;
        }
        
        .page-header h1 {
            font-size: 1.8rem;
            font-weight: 600;
            color: #0D3B3F;
        }
        
        .page-header p {
            color: #6c757d;
            font-size: 0.9rem;
        }
        
        /* Stats Cards - Beige & Teal */
        .stats-grid {
            display: grid;
            grid-template-columns: repeat(4, 1fr);
            gap: 25px;
            margin-bottom: 35px;
        }
        
        .stat-card {
            background: white;
            border-radius: 16px;
            padding: 20px;
            transition: all 0.3s;
            cursor: pointer;
            border: 1px solid #e8e0d5;
            box-shadow: 0 2px 8px rgba(0,0,0,0.04);
        }
        
        .stat-card:hover {
            transform: translateY(-5px);
            box-shadow: 0 8px 25px rgba(0,0,0,0.1);
        }
        
        .stat-icon {
            width: 50px;
            height: 50px;
            border-radius: 12px;
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 1.6rem;
            margin-bottom: 15px;
        }
        
        .stat-value {
            font-size: 2rem;
            font-weight: 700;
            color: #0D3B3F;
        }
        
        .stat-label {
            color: #8b7d6b;
            font-size: 0.85rem;
        }
        
        .stat-trend {
            font-size: 0.7rem;
            margin-top: 8px;
            color: #2e7d32;
        }
        
        /* Chart Cards */
        .chart-card {
            background: white;
            border-radius: 16px;
            padding: 20px;
            margin-bottom: 25px;
            border: 1px solid #e8e0d5;
        }
        
        .chart-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 20px;
            padding-bottom: 10px;
            border-bottom: 1px solid #f0ebe4;
        }
        
        .chart-header h5 {
            font-weight: 600;
            color: #0D3B3F;
            margin: 0;
        }
        
        /* Buttons - Dark Teal & Beige */
        .btn-teal {
            background: #0D3B3F;
            border: none;
            padding: 10px 22px;
            border-radius: 30px;
            font-weight: 500;
            transition: all 0.3s;
            color: white;
        }
        
        .btn-teal:hover {
            background: #1a5a5f;
            transform: translateY(-2px);
            color: white;
        }
        
        .btn-beige {
            background: #D4A574;
            border: none;
            padding: 10px 22px;
            border-radius: 30px;
            font-weight: 500;
            transition: all 0.3s;
            color: white;
        }
        
        .btn-beige:hover {
            background: #c49a6c;
            transform: translateY(-2px);
            color: white;
        }
        
        .btn-outline-teal {
            background: transparent;
            border: 1px solid #0D3B3F;
            padding: 10px 22px;
            border-radius: 30px;
            font-weight: 500;
            transition: all 0.3s;
            color: #0D3B3F;
        }
        
        .btn-outline-teal:hover {
            background: #0D3B3F;
            color: white;
        }
        
        /* Tables */
        .modern-table {
            background: white;
            border-radius: 16px;
            overflow: hidden;
            border: 1px solid #e8e0d5;
        }
        
        .modern-table th {
            background: #F5F2EB;
            padding: 15px 20px;
            font-weight: 600;
            color: #0D3B3F;
            border: none;
        }
        
        .modern-table td {
            padding: 12px 20px;
            vertical-align: middle;
            border-bottom: 1px solid #f0ebe4;
        }
        
        /* Badges */
        .badge-open { background: #4caf50; color: white; padding: 4px 12px; border-radius: 20px; font-size: 0.7rem; }
        .badge-closed { background: #f44336; color: white; padding: 4px 12px; border-radius: 20px; font-size: 0.7rem; }
        .badge-draft { background: #ff9800; color: white; padding: 4px 12px; border-radius: 20px; font-size: 0.7rem; }
        
        /* Modals */
        .modal-modern .modal-content {
            border-radius: 20px;
            border: none;
        }
        
        .modal-modern .modal-header {
            background: #0D3B3F;
            color: white;
            border-radius: 20px 20px 0 0;
            padding: 18px 25px;
        }
        
        /* Responsive */
        @media (max-width: 1000px) {
            .stats-grid { grid-template-columns: repeat(2, 1fr); }
        }
        
        @media (max-width: 768px) {
            .sidebar { left: -280px; }
            .main-content { margin-left: 0; }
            .stats-grid { grid-template-columns: 1fr; }
        }
    </style>
</head>
<body>
    <div class="sidebar">
        <div class="logo">
            <h3><i class="bi bi-robot"></i> ShahnaIT</h3>
            <p>Recruitment Suite</p>
        </div>
        <div class="nav-item active" data-page="dashboard">
            <i class="bi bi-speedometer2"></i> Dashboard
        </div>
        <div class="nav-item" data-page="jobs">
            <i class="bi bi-briefcase"></i> Jobs
        </div>
        <div class="nav-item" data-page="candidates">
            <i class="bi bi-people"></i> Candidates
        </div>
        <div class="nav-item" data-page="applications">
            <i class="bi bi-file-check"></i> Applications
        </div>
        <div class="nav-item" data-page="interviews">
            <i class="bi bi-calendar-check"></i> Interviews
        </div>
        <div class="nav-item" data-page="offers">
            <i class="bi bi-envelope-paper"></i> Offers
        </div>
    </div>
    
    <div class="main-content">
        <!-- Dashboard Page -->
        <div id="dashboardPage">
            <div class="page-header">
                <h1>Recruitment Dashboard</h1>
                <p>Track your hiring pipeline, candidates, and analytics</p>
            </div>
            <div class="stats-grid" id="statsGrid">
                <div class="stat-card"><div class="stat-icon" style="background:#0D3B3F20;color:#0D3B3F;"><i class="bi bi-briefcase"></i></div><div class="stat-value" id="openPositions">0</div><div class="stat-label">Open Positions</div><div class="stat-trend"><i class="bi bi-arrow-up"></i> +12%</div></div>
                <div class="stat-card"><div class="stat-icon" style="background:#D4A57420;color:#D4A574;"><i class="bi bi-people"></i></div><div class="stat-value" id="totalCandidates">0</div><div class="stat-label">Total Candidates</div><div class="stat-trend"><i class="bi bi-arrow-up"></i> +8%</div></div>
                <div class="stat-card"><div class="stat-icon" style="background:#0D3B3F20;color:#0D3B3F;"><i class="bi bi-calendar-check"></i></div><div class="stat-value" id="interviewsToday">0</div><div class="stat-label">Interviews Today</div><div class="stat-trend">AI Scheduler Active</div></div>
                <div class="stat-card"><div class="stat-icon" style="background:#D4A57420;color:#D4A574;"><i class="bi bi-envelope-paper"></i></div><div class="stat-value" id="offersSent">0</div><div class="stat-label">Offers Sent</div><div class="stat-trend"><i class="bi bi-arrow-up"></i> +5%</div></div>
            </div>
            <div class="row mt-3">
                <div class="col-md-12">
                    <div class="chart-card">
                        <div class="chart-header">
                            <h5><i class="bi bi-lightning-charge"></i> Quick Actions</h5>
                        </div>
                        <div class="d-flex gap-3 flex-wrap">
                            <button class="btn-teal" onclick="openJobModal()"><i class="bi bi-plus-circle"></i> Create Job</button>
                            <button class="btn-beige" onclick="openCandidateModal()"><i class="bi bi-person-plus"></i> Add Candidate</button>
                            <button class="btn-outline-teal" onclick="openApplicationModal()"><i class="bi bi-file-check"></i> Create Application</button>
                        </div>
                    </div>
                </div>
            </div>
        </div>
        
        <!-- Jobs Page -->
        <div id="jobsPage" style="display: none;">
            <div class="page-header">
                <h1>Job Descriptions</h1>
                <p>Manage all your job openings</p>
            </div>
            <button class="btn-teal mb-3" onclick="openJobModal()"><i class="bi bi-plus-circle"></i> Create Job</button>
            <div class="modern-table">
                <table class="table">
                    <thead><tr><th>ID</th><th>Title</th><th>Location</th><th>Skills</th><th>Status</th><th>Applications</th><th>Actions</th></tr></thead>
                    <tbody id="jobsTable"></tbody>
                </table>
            </div>
        </div>
        
        <!-- Candidates Page -->
        <div id="candidatesPage" style="display: none;">
            <div class="page-header">
                <h1>Candidates Database</h1>
                <p>Manage your talent pool</p>
            </div>
            <button class="btn-beige mb-3" onclick="openCandidateModal()"><i class="bi bi-person-plus"></i> Add Candidate</button>
            <div class="modern-table">
                <table class="table">
                    <thead><tr><th>ID</th><th>Name</th><th>Email</th><th>Skills</th><th>Experience</th><th>Actions</th></tr></thead>
                    <tbody id="candidatesTable"></tbody>
                </table>
            </div>
        </div>
        
        <!-- Applications Page -->
        <div id="applicationsPage" style="display: none;">
            <div class="page-header">
                <h1>Applications</h1>
                <p>Track all candidate applications</p>
            </div>
            <button class="btn-outline-teal mb-3" onclick="openApplicationModal()"><i class="bi bi-file-check"></i> Create Application</button>
            <div class="modern-table">
                <table class="table">
                    <thead><tr><th>ID</th><th>Candidate</th><th>Job</th><th>Match Score</th><th>Status</th><th>Actions</th></tr></thead>
                    <tbody id="applicationsTable"></tbody>
                </table>
            </div>
        </div>
        
        <!-- Interviews Page -->
        <div id="interviewsPage" style="display: none;">
            <div class="page-header">
                <h1>Interviews</h1>
                <p>Schedule and manage interviews</p>
            </div>
            <div class="modern-table">
                <table class="table">
                    <thead><tr><th>ID</th><th>Candidate</th><th>Job</th><th>Interviewer</th><th>Date</th><th>Status</th></tr></thead>
                    <tbody id="interviewsTable"></tbody>
                </table>
            </div>
        </div>
        
        <!-- Offers Page -->
        <div id="offersPage" style="display: none;">
            <div class="page-header">
                <h1>Offer Letters</h1>
                <p>Generate and manage offers</p>
            </div>
            <div class="modern-table">
                <table class="table">
                    <thead><tr><th>ID</th><th>Candidate</th><th>Job</th><th>Salary</th><th>Status</th></tr></thead>
                    <tbody id="offersTable"></tbody>
                </table>
            </div>
        </div>
    </div>
    
    <!-- Job Modal -->
    <div class="modal fade modal-modern" id="jobModal" tabindex="-1">
        <div class="modal-dialog">
            <div class="modal-content">
                <div class="modal-header">
                    <h5 class="modal-title"><i class="bi bi-briefcase"></i> Create Job</h5>
                    <button type="button" class="btn-close btn-close-white" data-bs-dismiss="modal"></button>
                </div>
                <div class="modal-body">
                    <input type="text" class="form-control mb-3" id="jobTitle" placeholder="Job Title">
                    <input type="text" class="form-control mb-3" id="jobLocation" placeholder="Location">
                    <textarea class="form-control mb-3" id="jobSkills" rows="3" placeholder="Required Skills (comma separated)"></textarea>
                    <select class="form-select mb-3" id="jobStatus">
                        <option value="open">Open</option>
                        <option value="draft">Draft</option>
                        <option value="closed">Closed</option>
                    </select>
                    <button class="btn-teal w-100" onclick="createJob()">Create Job</button>
                </div>
            </div>
        </div>
    </div>
    
    <!-- Candidate Modal -->
    <div class="modal fade modal-modern" id="candidateModal" tabindex="-1">
        <div class="modal-dialog">
            <div class="modal-content">
                <div class="modal-header">
                    <h5 class="modal-title"><i class="bi bi-person-plus"></i> Add Candidate</h5>
                    <button type="button" class="btn-close btn-close-white" data-bs-dismiss="modal"></button>
                </div>
                <div class="modal-body">
                    <input type="text" class="form-control mb-3" id="candName" placeholder="Full Name">
                    <input type="email" class="form-control mb-3" id="candEmail" placeholder="Email">
                    <input type="text" class="form-control mb-3" id="candPhone" placeholder="Phone">
                    <textarea class="form-control mb-3" id="candSkills" rows="3" placeholder="Skills (comma separated)"></textarea>
                    <input type="number" class="form-control mb-3" id="candExp" placeholder="Experience (years)">
                    <button class="btn-beige w-100" onclick="createCandidate()">Add Candidate</button>
                </div>
            </div>
        </div>
    </div>
    
    <!-- Application Modal -->
    <div class="modal fade modal-modern" id="applicationModal" tabindex="-1">
        <div class="modal-dialog">
            <div class="modal-content">
                <div class="modal-header">
                    <h5 class="modal-title"><i class="bi bi-file-check"></i> Create Application</h5>
                    <button type="button" class="btn-close btn-close-white" data-bs-dismiss="modal"></button>
                </div>
                <div class="modal-body">
                    <select class="form-select mb-3" id="appCandidateId">
                        <option value="">Select Candidate</option>
                    </select>
                    <select class="form-select mb-3" id="appJobId">
                        <option value="">Select Job</option>
                    </select>
                    <div id="matchPreview" class="alert alert-info mb-3" style="display: none;">
                        AI Match Score: <strong id="matchScorePreview">0</strong>%
                    </div>
                    <button class="btn-outline-teal w-100" onclick="createApplication()">Create Application</button>
                </div>
            </div>
        </div>
    </div>
    
    <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.1.3/dist/js/bootstrap.bundle.min.js"></script>
    <script>
        // Navigation
        document.querySelectorAll('.nav-item').forEach(function(item) {
            item.addEventListener('click', function() {
                document.querySelectorAll('.nav-item').forEach(function(n) { n.classList.remove('active'); });
                this.classList.add('active');
                var pages = ['dashboard', 'jobs', 'candidates', 'applications', 'interviews', 'offers'];
                for (var i = 0; i < pages.length; i++) {
                    var pageEl = document.getElementById(pages[i] + 'Page');
                    if (pageEl) pageEl.style.display = 'none';
                }
                var pageName = this.getAttribute('data-page');
                var activePage = document.getElementById(pageName + 'Page');
                if (activePage) activePage.style.display = 'block';
                
                if (pageName === 'dashboard') loadDashboard();
                if (pageName === 'jobs') loadJobs();
                if (pageName === 'candidates') loadCandidates();
                if (pageName === 'applications') loadApplications();
                if (pageName === 'interviews') loadInterviews();
                if (pageName === 'offers') loadOffers();
            });
        });
        
        // Load Dashboard Stats
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
        
        // Load Jobs
        async function loadJobs() {
            try {
                var res = await fetch('/api/jobs');
                var jobs = await res.json();
                var tbody = document.getElementById('jobsTable');
                if (jobs.length === 0) {
                    tbody.innerHTML = '<tr><td colspan="7" class="text-center">No jobs created</td></tr>';
                    return;
                }
                var html = '';
                for (var i = 0; i < jobs.length; i++) {
                    var j = jobs[i];
                    html += '<tr><td>' + j.id + '</td><td><strong>' + j.title + '</strong></td><td>' + (j.location || 'Remote') + '</td><td>' + (j.skills_required || '-') + '</td><td><span class="badge-open">' + j.status + '</span></td><td>' + (j.applications || 0) + '</td><td><button class="btn-teal btn-sm" onclick="openApplicationForJob(' + j.id + ')">Apply</button></td></tr>';
                }
                tbody.innerHTML = html;
            } catch(e) { console.log(e); }
        }
        
        // Load Candidates
        async function loadCandidates() {
            try {
                var res = await fetch('/api/candidates');
                var data = await res.json();
                var tbody = document.getElementById('candidatesTable');
                if (data.candidates.length === 0) {
                    tbody.innerHTML = '<tr><td colspan="6" class="text-center">No candidates added</td></tr>';
                    return;
                }
                var html = '';
                for (var i = 0; i < data.candidates.length; i++) {
                    var c = data.candidates[i];
                    html += '<tr><td>' + c.id + '</td><td><strong>' + c.name + '</strong></td><td>' + c.email + '</td><td>' + (c.skills || '-') + '</td><td>' + (c.total_experience || 0) + ' years</td><td><button class="btn-beige btn-sm" onclick="openApplicationForCandidate(' + c.id + ')">Apply</button></td></tr>';
                }
                tbody.innerHTML = html;
            } catch(e) { console.log(e); }
        }
        
        // Load Applications
        async function loadApplications() {
            try {
                var res = await fetch('/api/applications');
                var apps = await res.json();
                var tbody = document.getElementById('applicationsTable');
                if (apps.length === 0) {
                    tbody.innerHTML = '<tr><td colspan="6" class="text-center">No applications</td></tr>';
                    return;
                }
                var html = '';
                for (var i = 0; i < apps.length; i++) {
                    var a = apps[i];
                    var badgeClass = a.match_score >= 70 ? 'badge-open' : (a.match_score >= 50 ? 'badge-draft' : 'badge-closed');
                    html += '<tr><td>' + a.id + '</td><td>' + (a.candidate_name || '-') + '</td><td>' + (a.job_title || '-') + '</td><td><span class="' + badgeClass + '">' + (a.match_score || 0) + '%</span></td><td>' + a.status + '</td><td><button class="btn-outline-teal btn-sm" onclick="moveApplication(' + a.id + ')">Move</button></td></tr>';
                }
                tbody.innerHTML = html;
            } catch(e) { console.log(e); }
        }
        
        // Load Interviews
        async function loadInterviews() {
            try {
                var res = await fetch('/api/interviews');
                var interviews = await res.json();
                var tbody = document.getElementById('interviewsTable');
                if (interviews.length === 0) {
                    tbody.innerHTML = '<tr><td colspan="6" class="text-center">No interviews scheduled</td></tr>';
                    return;
                }
                var html = '';
                for (var i = 0; i < interviews.length; i++) {
                    var iv = interviews[i];
                    html += '<tr><td>' + iv.id + '</td><td>' + iv.candidate_name + '</td><td>' + iv.job_title + '</td><td>' + (iv.interviewer_name || 'TBD') + '</td><td>' + (iv.scheduled_time ? new Date(iv.scheduled_time).toLocaleString() : 'TBD') + '</td><td>' + iv.status + '</td></tr>';
                }
                tbody.innerHTML = html;
            } catch(e) { console.log(e); }
        }
        
        // Load Offers
        async function loadOffers() {
            try {
                var res = await fetch('/api/offers');
                var offers = await res.json();
                var tbody = document.getElementById('offersTable');
                if (offers.length === 0) {
                    tbody.innerHTML = '<tr><td colspan="5" class="text-center">No offers generated</td></tr>';
                    return;
                }
                var html = '';
                for (var i = 0; i < offers.length; i++) {
                    var o = offers[i];
                    html += '<tr><td>' + o.id + '</td><td>' + o.candidate_name + '</td><td>' + o.job_title + '</td><td>$' + (o.base_salary || 0) + '</td><td>' + o.status + '</td></tr>';
                }
                tbody.innerHTML = html;
            } catch(e) { console.log(e); }
        }
        
        // Create Job
        async function createJob() {
            var title = document.getElementById('jobTitle').value;
            if (!title) { alert('Enter job title'); return; }
            var data = {
                title: title,
                location: document.getElementById('jobLocation').value,
                skills_required: document.getElementById('jobSkills').value,
                status: document.getElementById('jobStatus').value
            };
            var res = await fetch('/api/jobs', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(data)
            });
            var result = await res.json();
            if (result.success) {
                alert('Job created!');
                var modal = bootstrap.Modal.getInstance(document.getElementById('jobModal'));
                modal.hide();
                loadJobs();
                loadDashboard();
                document.getElementById('jobTitle').value = '';
                document.getElementById('jobLocation').value = '';
                document.getElementById('jobSkills').value = '';
            }
        }
        
        // Create Candidate
        async function createCandidate() {
            var name = document.getElementById('candName').value;
            var email = document.getElementById('candEmail').value;
            if (!name || !email) { alert('Enter name and email'); return; }
            var nameParts = name.split(' ');
            var data = {
                first_name: nameParts[0],
                last_name: nameParts.slice(1).join(' '),
                email: email,
                phone: document.getElementById('candPhone').value,
                skills: document.getElementById('candSkills').value,
                total_experience: parseFloat(document.getElementById('candExp').value) || 0
            };
            var res = await fetch('/api/candidates', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(data)
            });
            var result = await res.json();
            if (result.success) {
                alert('Candidate added!');
                var modal = bootstrap.Modal.getInstance(document.getElementById('candidateModal'));
                modal.hide();
                loadCandidates();
                loadDashboard();
                document.getElementById('candName').value = '';
                document.getElementById('candEmail').value = '';
                document.getElementById('candSkills').value = '';
            }
        }
        
        // Create Application
        async function createApplication() {
            var candidateId = document.getElementById('appCandidateId').value;
            var jobId = document.getElementById('appJobId').value;
            if (!candidateId || !jobId) { alert('Select candidate and job'); return; }
            var res = await fetch('/api/applications', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    candidate_id: parseInt(candidateId),
                    jd_id: parseInt(jobId)
                })
            });
            var result = await res.json();
            if (result.success) {
                alert('Application created! Match Score: ' + result.match_score + '%');
                var modal = bootstrap.Modal.getInstance(document.getElementById('applicationModal'));
                modal.hide();
                loadApplications();
                loadJobs();
                loadDashboard();
            }
        }
        
        // Move Application Stage
        async function moveApplication(appId) {
            var stage = prompt('Enter stage (screening / interview / offer / hired / rejected):');
            if (stage) {
                await fetch('/api/applications/' + appId + '/move', {
                    method: 'PUT',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ stage: stage })
                });
                loadApplications();
            }
        }
        
        // Helper Functions
        async function openApplicationForJob(jobId) {
            await loadCandidateDropdown();
            document.getElementById('appJobId').value = jobId;
            new bootstrap.Modal(document.getElementById('applicationModal')).show();
        }
        
        async function openApplicationForCandidate(candidateId) {
            await loadJobDropdown();
            document.getElementById('appCandidateId').value = candidateId;
            new bootstrap.Modal(document.getElementById('applicationModal')).show();
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
        
        function openJobModal() { new bootstrap.Modal(document.getElementById('jobModal')).show(); }
        function openCandidateModal() { new bootstrap.Modal(document.getElementById('candidateModal')).show(); }
        function openApplicationModal() { loadCandidateDropdown(); loadJobDropdown(); new bootstrap.Modal(document.getElementById('applicationModal')).show(); }
        
        // Initialize
        loadDashboard();
        loadJobs();
        loadCandidates();
        loadApplications();
        loadInterviews();
        loadOffers();
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
        'offers_sent': len([o for o in offers if o.get('status') == 'sent'])
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

@app.route('/api/interviews', methods=['GET', 'POST'])
def manage_interviews():
    if request.method == 'POST':
        data = request.json
        app_id = data.get('application_id')
        application = next((a for a in applications if a['id'] == app_id), None)
        if not application:
            return jsonify({'error': 'Application not found'}), 404
        candidate = next((c for c in candidates if c['id'] == application.get('candidate_id')), None)
        job = next((j for j in jobs if j['id'] == application.get('jd_id')), None)
        interview = {
            'id': len(interviews) + 1,
            'application_id': app_id,
            'candidate_name': candidate.get('name') if candidate else '',
            'job_title': job.get('title') if job else '',
            'interviewer_name': data.get('interviewer_name', ''),
            'scheduled_time': data.get('scheduled_time'),
            'round_type': data.get('round_type', 'Technical'),
            'status': 'scheduled',
            'created_at': datetime.now().isoformat()
        }
        interviews.append(interview)
        application['status'] = 'interview-scheduled'
        return jsonify({'success': True})
    
    return jsonify(interviews)

@app.route('/api/offers', methods=['GET', 'POST'])
def manage_offers():
    if request.method == 'POST':
        data = request.json
        app_id = data.get('application_id')
        application = next((a for a in applications if a['id'] == app_id), None)
        if not application:
            return jsonify({'error': 'Application not found'}), 404
        candidate = next((c for c in candidates if c['id'] == application.get('candidate_id')), None)
        job = next((j for j in jobs if j['id'] == application.get('jd_id')), None)
        offer = {
            'id': len(offers) + 1,
            'application_id': app_id,
            'candidate_name': candidate.get('name') if candidate else '',
            'job_title': job.get('title') if job else '',
            'base_salary': data.get('base_salary', 0),
            'joining_date': data.get('joining_date'),
            'status': 'draft',
            'created_at': datetime.now().isoformat()
        }
        offers.append(offer)
        application['status'] = 'offered'
        return jsonify({'success': True, 'offer_id': offer['id']})
    
    return jsonify(offers)

# ============= MAIN =============
if __name__ == '__main__':
    port = int(os.environ.get('PORT', 8080))
    print("=" * 50)
    print("ShahnaIT Scout - Recruitment System")
    print("=" * 50)
    print(f"Server running on port: {port}")
    print("=" * 50)
    app.run(host='0.0.0.0', port=port, debug=False)
