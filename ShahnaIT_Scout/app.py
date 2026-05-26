from flask import Flask, jsonify, request, render_template_string
from datetime import datetime
from difflib import SequenceMatcher
import os
import re

app = Flask(__name__)

# ============= HTML DASHBOARD TEMPLATE =============
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
        .kanban-column {
            background: #f8f9fa;
            border-radius: 10px;
            padding: 15px;
            min-width: 320px;
            max-width: 350px;
        }
        .kanban-cards {
            min-height: 400px;
            max-height: 70vh;
            overflow-y: auto;
        }
        .kanban-card {
            background: white;
            border-radius: 8px;
            padding: 12px;
            margin-bottom: 10px;
            cursor: grab;
            box-shadow: 0 1px 3px rgba(0,0,0,0.1);
            transition: transform 0.2s, box-shadow 0.2s;
        }
        .kanban-card:hover {
            transform: translateY(-2px);
            box-shadow: 0 4px 8px rgba(0,0,0,0.15);
        }
        .kanban-card:active { cursor: grabbing; }
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
        
        <!-- Buttons Row -->
        <div class="row mb-3">
            <div class="col-12">
                <button class="btn btn-info" onclick="showKanbanBoard()">
                    <i class="bi bi-kanban"></i> Kanban Pipeline
                </button>
                <button class="btn btn-warning" onclick="showReportsModal()">
                    <i class="bi bi-graph-up"></i> Reports
                </button>
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
            <li class="nav-item">
                <button class="nav-link" data-bs-toggle="tab" data-bs-target="#interviews">🎯 Interviews</button>
            </li>
            <li class="nav-item">
                <button class="nav-link" data-bs-toggle="tab" data-bs-target="#offers">📜 Offers</button>
            </li>
        </ul>
        
        <div class="tab-content mt-3">
            <!-- Jobs Tab -->
            <div class="tab-pane fade show active" id="jobs">
                <button class="btn btn-primary mb-3" onclick="showJobModal()">+ Create Job Description</button>
                <div class="table-responsive">
                    <table class="table table-hover">
                        <thead class="table-light"><tr><th>Code</th><th>Title</th><th>Location</th><th>Status</th><th>Applications</th><th>Actions</th></tr></thead>
                        <tbody id="jobsTable"></tbody>
                    </table>
                </div>
            </div>
            
            <!-- Candidates Tab -->
            <div class="tab-pane fade" id="candidates">
                <button class="btn btn-success mb-3" onclick="showCandidateModal()">+ Add Candidate</button>
                <button class="btn btn-outline-success mb-3" onclick="showResumeUploadModal()">📄 Upload Resume</button>
                <div class="table-responsive">
                    <table class="table table-hover">
                        <thead class="table-light"><tr><th>Code</th><th>Name</th><th>Email</th><th>Actions</th></tr></thead>
                        <tbody id="candidatesTable"></tbody>
                    </table>
                </div>
            </div>
            
            <!-- Applications Tab -->
            <div class="tab-pane fade" id="applications">
                <div class="table-responsive">
                    <table class="table table-hover">
                        <thead class="table-light"><tr><th>ID</th><th>Candidate</th><th>Job</th><th>Match Score</th><th>Status</th><th>Actions</th></tr></thead>
                        <tbody id="applicationsTable"></tbody>
                    </table>
                </div>
            </div>
            
            <!-- Interviews Tab -->
            <div class="tab-pane fade" id="interviews">
                <button class="btn btn-primary mb-3" onclick="showInterviewModal()">+ Schedule Interview</button>
                <div id="interviewsList"></div>
            </div>
            
            <!-- Offers Tab -->
            <div class="tab-pane fade" id="offers">
                <button class="btn btn-primary mb-3" onclick="showOfferModal()">+ Generate Offer</button>
                <div id="offersList"></div>
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
                    <input type="text" class="form-control mb-2" id="jobSkills" placeholder="Required Skills (comma separated)">
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
                    <input type="text" class="form-control mb-2" id="candSkills" placeholder="Skills (comma separated)">
                    <button class="btn btn-success w-100" onclick="createCandidate()">Add Candidate</button>
                </div>
            </div>
        </div>
    </div>
    
    <!-- Resume Upload Modal -->
    <div class="modal fade" id="resumeUploadModal" tabindex="-1">
        <div class="modal-dialog">
            <div class="modal-content">
                <div class="modal-header bg-info text-white">
                    <h5 class="modal-title">Upload Resume</h5>
                    <button type="button" class="btn-close" data-bs-dismiss="modal"></button>
                </div>
                <div class="modal-body">
                    <input type="file" class="form-control" id="resumeFile" accept=".pdf,.docx">
                    <div id="parseProgress" class="mt-2" style="display:none"><div class="spinner-border spinner-border-sm"></div> Parsing...</div>
                    <button class="btn btn-info mt-3 w-100" onclick="parseResume()">Parse Resume</button>
                    <div id="parsedData" class="mt-3" style="display:none">
                        <h6>Extracted Data:</h6>
                        <pre id="extractedJson" class="bg-light p-2 rounded small"></pre>
                        <button class="btn btn-success w-100" onclick="createCandidateFromResume()">Create Candidate</button>
                    </div>
                </div>
            </div>
        </div>
    </div>
    
    <!-- Interview Modal -->
    <div class="modal fade" id="interviewModal" tabindex="-1">
        <div class="modal-dialog">
            <div class="modal-content">
                <div class="modal-header bg-warning">
                    <h5 class="modal-title">Schedule Interview</h5>
                    <button type="button" class="btn-close" data-bs-dismiss="modal"></button>
                </div>
                <div class="modal-body">
                    <input type="number" class="form-control mb-2" id="interviewAppId" placeholder="Application ID" required>
                    <input type="text" class="form-control mb-2" id="interviewerName" placeholder="Interviewer Name">
                    <input type="email" class="form-control mb-2" id="interviewerEmail" placeholder="Interviewer Email">
                    <input type="datetime-local" class="form-control mb-2" id="interviewTime">
                    <input type="text" class="form-control mb-2" id="meetingLink" placeholder="Meeting Link (Google Meet/Zoom)">
                    <select class="form-control mb-2" id="roundType">
                        <option value="Technical">Technical Round</option>
                        <option value="HR">HR Round</option>
                        <option value="Managerial">Managerial Round</option>
                        <option value="Client">Client Round</option>
                    </select>
                    <button class="btn btn-warning w-100" onclick="scheduleInterview()">Schedule Interview</button>
                </div>
            </div>
        </div>
    </div>
    
    <!-- Offer Modal -->
    <div class="modal fade" id="offerModal" tabindex="-1">
        <div class="modal-dialog">
            <div class="modal-content">
                <div class="modal-header bg-primary text-white">
                    <h5 class="modal-title">Generate Offer Letter</h5>
                    <button type="button" class="btn-close" data-bs-dismiss="modal"></button>
                </div>
                <div class="modal-body">
                    <input type="number" class="form-control mb-2" id="offerAppId" placeholder="Application ID" required>
                    <input type="text" class="form-control mb-2" id="candidateNameOffer" placeholder="Candidate Name" required>
                    <input type="email" class="form-control mb-2" id="candidateEmailOffer" placeholder="Candidate Email" required>
                    <input type="text" class="form-control mb-2" id="jobTitleOffer" placeholder="Job Title" required>
                    <input type="number" class="form-control mb-2" id="baseSalary" placeholder="Base Salary ($)" required>
                    <input type="number" class="form-control mb-2" id="joiningBonus" placeholder="Joining Bonus ($)">
                    <input type="date" class="form-control mb-2" id="joiningDate">
                    <button class="btn btn-primary w-100" onclick="generateOffer()">Generate Offer</button>
                </div>
            </div>
        </div>
    </div>
    
    <!-- Reports Modal -->
    <div class="modal fade" id="reportsModal" tabindex="-1">
        <div class="modal-dialog modal-lg">
            <div class="modal-content">
                <div class="modal-header bg-info text-white">
                    <h5 class="modal-title">Recruitment Analytics</h5>
                    <button type="button" class="btn-close" data-bs-dismiss="modal"></button>
                </div>
                <div class="modal-body" id="reportsContent">
                    Loading...
                </div>
            </div>
        </div>
    </div>
    
    <!-- Kanban Modal -->
    <div class="modal fade" id="kanbanModal" tabindex="-1">
        <div class="modal-dialog modal-fullscreen">
            <div class="modal-content">
                <div class="modal-header bg-info text-white">
                    <h5 class="modal-title"><i class="bi bi-kanban"></i> Recruitment Pipeline</h5>
                    <button type="button" class="btn-close btn-close-white" data-bs-dismiss="modal"></button>
                </div>
                <div class="modal-body" style="overflow-x: auto;">
                    <div id="kanbanBoard" style="display: flex; gap: 20px; min-width: max-content; padding: 10px;"></div>
                </div>
            </div>
        </div>
    </div>
    
    <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.1.3/dist/js/bootstrap.bundle.min.js"></script>
    <script>
        let parsedResumeData = null;
        
        document.addEventListener('DOMContentLoaded', () => {
            loadStats(); loadJobs(); loadCandidates(); loadApplications(); loadInterviews(); loadOffers();
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
                if (jobs.length === 0) { tbody.innerHTML = '<tr><td colspan="6" class="text-center">No jobs created yet</td></tr>'; return; }
                tbody.innerHTML = jobs.map(job => `<tr><td><code>${job.code}</code></td><td><strong>${job.title}</strong></td><td>${job.location || '-'}</td><td><span class="badge bg-success">${job.status}</span></td><td>${job.applications || 0}</td><td><button class="btn btn-sm btn-primary" onclick="createApplicationForJob(${job.id})">Create Application</button></td></tr>`).join('');
            } catch(e) { console.error(e); }
        }
        
        async function loadCandidates() {
            try {
                const res = await fetch('/api/candidates');
                const data = await res.json();
                const tbody = document.getElementById('candidatesTable');
                if (data.candidates.length === 0) { tbody.innerHTML = '<tr><td colspan="4" class="text-center">No candidates added yet</td></tr>'; return; }
                tbody.innerHTML = data.candidates.map(c => `<tr><td><code>${c.code}</code></td><td>${c.name}</td><td>${c.email}</td><td><button class="btn btn-sm btn-primary" onclick="createApplicationForCandidate(${c.id})">Apply to Job</button></td></tr>`).join('');
            } catch(e) { console.error(e); }
        }
        
        async function loadApplications() {
            try {
                const res = await fetch('/api/applications');
                const apps = await res.json();
                const tbody = document.getElementById('applicationsTable');
                if (apps.length === 0) { tbody.innerHTML = '<tr><td colspan="6" class="text-center">No applications yet</td></tr>'; return; }
                tbody.innerHTML = apps.map(app => `<tr><td>${app.id}</td><td>Candidate #${app.candidate_id}</td><td>Job #${app.jd_id}</td><td><span class="badge bg-info">${app.match_score || 0}%</span></td><td>${app.status}</td><td><button class="btn btn-sm btn-warning" onclick="moveStage(${app.id}, prompt('Enter stage: new/shortlisted/selected/rejected'))">Move</button></td></tr>`).join('');
            } catch(e) { console.error(e); }
        }
        
        async function loadInterviews() {
            try {
                const res = await fetch('/api/interviews');
                const interviews = await res.json();
                const container = document.getElementById('interviewsList');
                if (interviews.length === 0) { container.innerHTML = '<div class="alert alert-info">No interviews scheduled</div>'; return; }
                container.innerHTML = `<div class="table-responsive"><table class="table table-hover"><thead class="table-light"><tr><th>Candidate</th><th>Job</th><th>Interviewer</th><th>Time</th><th>Status</th></tr></thead><tbody>${interviews.map(i => `<tr><td>${i.candidate_name}</td><td>${i.job_title}</td><td>${i.interviewer}</td><td>${new Date(i.scheduled_time).toLocaleString()}</td><td>${i.status}</td></tr>`).join('')}</tbody></table></div>`;
            } catch(e) { console.error(e); }
        }
        
        async function loadOffers() {
            try {
                const res = await fetch('/api/offers');
                const offers = await res.json();
                const container = document.getElementById('offersList');
                if (offers.length === 0) { container.innerHTML = '<div class="alert alert-info">No offers generated</div>'; return; }
                container.innerHTML = `<div class="table-responsive"><table class="table table-hover"><thead class="table-light"><tr><th>Candidate</th><th>Job</th><th>Salary</th><th>Status</th><th>Actions</th></tr></thead><tbody>${offers.map(o => `<tr><td>${o.candidate_name}</td><td>${o.job_title}</td><td>$${o.base_salary}</td><td>${o.status}</td><td><button class="btn btn-sm btn-primary" onclick="viewOffer(${o.id})">View</button></td></tr>`).join('')}</tbody></table></div>`;
            } catch(e) { console.error(e); }
        }
        
        async function createJob() {
            const title = document.getElementById('jobTitle').value;
            const location = document.getElementById('jobLocation').value;
            const skills = document.getElementById('jobSkills').value;
            const status = document.getElementById('jobStatus').value;
            if (!title) { alert('Enter job title'); return; }
            const res = await fetch('/api/jds', { method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify({title, location, skills_required: skills, status}) });
            const result = await res.json();
            if (result.success) { alert(`Job created: ${result.jd_code}`); bootstrap.Modal.getInstance(document.getElementById('jobModal')).hide(); loadJobs(); loadStats(); }
        }
        
        async function createCandidate() {
            const first_name = document.getElementById('candFirstName').value;
            const last_name = document.getElementById('candLastName').value;
            const email = document.getElementById('candEmail').value;
            const skills = document.getElementById('candSkills').value;
            if (!first_name || !email) { alert('Enter name and email'); return; }
            const res = await fetch('/api/candidates', { method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify({first_name, last_name, email, skills}) });
            const result = await res.json();
            if (result.success) { alert(`Candidate added: ${result.candidate_code}`); bootstrap.Modal.getInstance(document.getElementById('candidateModal')).hide(); loadCandidates(); loadStats(); }
        }
        
        async function createApplicationForJob(jd_id) {
            const candidate_id = prompt('Enter Candidate ID:');
            if (!candidate_id) return;
            const res = await fetch('/api/applications', { method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify({candidate_id: parseInt(candidate_id), jd_id}) });
            const result = await res.json();
            if (result.success) { alert(`Application created! Match Score: ${result.match_score}%`); loadApplications(); loadStats(); loadJobs(); }
        }
        
        async function createApplicationForCandidate(candidate_id) {
            const jd_id = prompt('Enter Job ID:');
            if (!jd_id) return;
            const res = await fetch('/api/applications', { method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify({candidate_id, jd_id: parseInt(jd_id)}) });
            const result = await res.json();
            if (result.success) { alert(`Application created! Match Score: ${result.match_score}%`); loadApplications(); loadStats(); loadJobs(); }
        }
        
        async function moveStage(app_id, stage) { if (!stage) return; await fetch(`/api/applications/${app_id}/move`, { method: 'PUT', headers: {'Content-Type': 'application/json'}, body: JSON.stringify({stage}) }); loadApplications(); }
        
        async function scheduleInterview() {
            const data = { application_id: parseInt(document.getElementById('interviewAppId').value), interviewer: document.getElementById('interviewerName').value, interviewer_email: document.getElementById('interviewerEmail').value, scheduled_time: document.getElementById('interviewTime').value, meeting_link: document.getElementById('meetingLink').value, round_type: document.getElementById('roundType').value, candidate_name: '', job_title: '' };
            const res = await fetch('/api/interviews', { method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify(data) });
            const result = await res.json();
            if (result.success) { alert('Interview scheduled!'); bootstrap.Modal.getInstance(document.getElementById('interviewModal')).hide(); loadInterviews(); }
        }
        
        async function generateOffer() {
            const data = { application_id: parseInt(document.getElementById('offerAppId').value), candidate_name: document.getElementById('candidateNameOffer').value, candidate_email: document.getElementById('candidateEmailOffer').value, job_title: document.getElementById('jobTitleOffer').value, base_salary: parseFloat(document.getElementById('baseSalary').value), joining_bonus: parseFloat(document.getElementById('joiningBonus').value) || 0, joining_date: document.getElementById('joiningDate').value };
            const res = await fetch('/api/offers', { method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify(data) });
            const result = await res.json();
            if (result.success) { const win = window.open(); win.document.write(result.offer_html); win.document.close(); bootstrap.Modal.getInstance(document.getElementById('offerModal')).hide(); loadOffers(); }
        }
        
        async function parseResume() {
            const file = document.getElementById('resumeFile').files[0];
            if (!file) { alert('Select a file'); return; }
            const formData = new FormData(); formData.append('file', file);
            document.getElementById('parseProgress').style.display = 'block';
            const res = await fetch('/api/candidates/parse-resume-enhanced', { method: 'POST', body: formData });
            const result = await res.json();
            document.getElementById('parseProgress').style.display = 'none';
            if (result.success) { parsedResumeData = result.data; document.getElementById('extractedJson').textContent = JSON.stringify(result.data, null, 2); document.getElementById('parsedData').style.display = 'block'; }
            else { alert('Error parsing resume'); }
        }
        
        function createCandidateFromResume() {
            if (parsedResumeData) {
                document.getElementById('candFirstName').value = parsedResumeData.first_name || '';
                document.getElementById('candLastName').value = parsedResumeData.last_name || '';
                document.getElementById('candEmail').value = parsedResumeData.email || '';
                document.getElementById('candSkills').value = Array.isArray(parsedResumeData.skills) ? parsedResumeData.skills.join(', ') : '';
                bootstrap.Modal.getInstance(document.getElementById('resumeUploadModal')).hide();
                new bootstrap.Modal(document.getElementById('candidateModal')).show();
            }
        }
        
        async function showReportsModal() {
            const res = await fetch('/api/reports/hiring-metrics');
            const data = await res.json();
            document.getElementById('reportsContent').innerHTML = `
                <h5>Hiring Metrics</h5>
                <div class="row"><div class="col-md-6"><div class="card mb-2"><div class="card-body"><h3>${data.total_applications}</h3><small>Total Applications</small></div></div></div>
                <div class="col-md-6"><div class="card mb-2"><div class="card-body"><h3>${data.average_time_to_hire_days} days</h3><small>Avg Time to Hire</small></div></div></div></div>
                <h6>Conversion Rates</h6><ul class="list-group mb-3">${Object.entries(data.conversion_rates).map(([k,v]) => `<li class="list-group-item d-flex justify-content-between"><span>${k}</span><strong>${v}%</strong></li>`).join('')}</ul>
                <h6>Applications by Stage</h6><ul class="list-group">${Object.entries(data.applications_by_stage).map(([k,v]) => `<li class="list-group-item d-flex justify-content-between"><span>${k}</span><strong>${v}</strong></li>`).join('')}</ul>`;
            new bootstrap.Modal(document.getElementById('reportsModal')).show();
        }
        
        async function showKanbanBoard() { await loadKanbanData(); new bootstrap.Modal(document.getElementById('kanbanModal')).show(); }
        
        let currentPipelineData = null;
        async function loadKanbanData() {
            const stagesRes = await fetch('/api/pipeline/stages');
            const stages = await stagesRes.json();
            const candidatesRes = await fetch('/api/pipeline/candidates');
            const candidates = await candidatesRes.json();
            currentPipelineData = candidates;
            const board = document.getElementById('kanbanBoard');
            board.innerHTML = stages.map(stage => {
                const stageCandidates = candidates[stage.id] || [];
                return `<div class="kanban-column"><div class="kanban-column-header" style="background: ${stage.color}; color: white; padding: 10px; border-radius: 8px; margin-bottom: 15px;"><strong>${stage.name}</strong><span class="badge bg-light text-dark ms-2">${stageCandidates.length}</span></div><div class="kanban-cards" data-stage="${stage.id}" style="min-height: 200px;">${stageCandidates.map(c => `<div class="kanban-card" draggable="true" data-candidate-id="${c.id}" data-application-id="${c.application_id || ''}"><div class="d-flex justify-content-between"><strong>${c.name}</strong>${c.match_score ? `<span class="badge bg-primary">${c.match_score}%</span>` : ''}</div><small class="text-muted d-block">${c.current_designation || 'Candidate'}</small><small class="text-muted">💼 ${c.total_experience || 0} years exp</small><div class="mt-2"><small class="text-muted">${c.skills ? c.skills.substring(0, 50) : 'No skills'}</small></div></div>`).join('')}</div></div>`;
            }).join('');
            setupDragAndDrop();
        }
        
        function setupDragAndDrop() {
            document.querySelectorAll('.kanban-card').forEach(card => { card.addEventListener('dragstart', e => { e.dataTransfer.setData('text/plain', JSON.stringify({ candidateId: card.dataset.candidateId, applicationId: card.dataset.applicationId })); e.target.style.opacity = '0.5'; }); card.addEventListener('dragend', e => { e.target.style.opacity = '1'; }); });
            document.querySelectorAll('.kanban-cards').forEach(column => { column.addEventListener('dragover', e => e.preventDefault()); column.addEventListener('drop', async e => { e.preventDefault(); const newStage = e.currentTarget.dataset.stage; const dragData = JSON.parse(e.dataTransfer.getData('text/plain')); const res = await fetch('/api/pipeline/move', { method: 'PUT', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ candidate_id: parseInt(dragData.candidateId), new_stage: newStage }) }); const result = await res.json(); if (result.success) loadKanbanData(); else alert(result.error || 'Error moving candidate. Create a job first.'); }); });
        }
        
        function viewOffer(id) { const offer = offers.find(o => o.id === id); if (offer) { const win = window.open(); win.document.write(offer.offer_letter_html); win.document.close(); } }
        
        function showJobModal() { new bootstrap.Modal(document.getElementById('jobModal')).show(); }
        function showCandidateModal() { new bootstrap.Modal(document.getElementById('candidateModal')).show(); }
        function showResumeUploadModal() { document.getElementById('resumeFile').value = ''; document.getElementById('parsedData').style.display = 'none'; new bootstrap.Modal(document.getElementById('resumeUploadModal')).show(); }
        function showInterviewModal() { new bootstrap.Modal(document.getElementById('interviewModal')).show(); }
        function showOfferModal() { new bootstrap.Modal(document.getElementById('offerModal')).show(); }
        
        setInterval(() => { loadStats(); loadJobs(); loadCandidates(); loadApplications(); }, 30000);
    </script>
</body>
</html>
'''

# ============= IN-MEMORY STORAGE =============
jobs = []
candidates = []
applications = []
interviews = []
offers = []
next_id = 1
candidate_notes = {}
application_notes = {}

# ============= PIPELINE STAGES =============
PIPELINE_STAGES = [
    {'id': 'new', 'name': '📋 New', 'color': '#6c757d', 'order': 1},
    {'id': 'screening', 'name': '🔍 Screening', 'color': '#17a2b8', 'order': 2},
    {'id': 'shortlisted', 'name': '⭐ Shortlisted', 'color': '#28a745', 'order': 3},
    {'id': 'interview', 'name': '🎯 Interview', 'color': '#007bff', 'order': 4},
    {'id': 'technical', 'name': '💻 Technical', 'color': '#fd7e14', 'order': 5},
    {'id': 'hr', 'name': '🤝 HR Round', 'color': '#6f42c1', 'order': 6},
    {'id': 'offer', 'name': '📄 Offer', 'color': '#20c997', 'order': 7},
    {'id': 'hired', 'name': '✅ Hired', 'color': '#28a745', 'order': 8},
    {'id': 'rejected', 'name': '❌ Rejected', 'color': '#dc3545', 'order': 9}
]

# ============= HELPER FUNCTIONS =============
def calculate_weighted_match_score(job_skills, candidate_skills):
    if not job_skills or not candidate_skills:
        return 0, {}
    job_list = [s.strip().lower() for s in job_skills.split(',') if s.strip()]
    cand_list = [s.strip().lower() for s in candidate_skills.split(',') if s.strip()]
    if not job_list:
        return 0, {}
    match_details = {'exact_matches': [], 'partial_matches': [], 'missing_skills': []}
    total_score = 0
    for job_skill in job_list:
        best_match = 0
        for cand_skill in cand_list:
            if job_skill == cand_skill:
                best_match = 100
                match_details['exact_matches'].append(job_skill)
                break
            elif job_skill in cand_skill or cand_skill in job_skill:
                best_match = 70
                if job_skill not in match_details['partial_matches']:
                    match_details['partial_matches'].append(job_skill)
                break
            else:
                similarity = SequenceMatcher(None, job_skill, cand_skill).ratio() * 100
                if similarity > best_match and similarity > 50:
                    best_match = similarity
        if best_match == 0:
            match_details['missing_skills'].append(job_skill)
        total_score += best_match
    final_score = round(total_score / len(job_list), 2)
    return final_score, match_details

# ============= RESUME PARSING FUNCTIONS =============
def extract_name_enhanced(text):
    if not text:
        return {'first': None, 'last': None}
    lines = text.split('\n')[:15]
    for line in lines:
        line = line.strip()
        if len(line.split()) == 2 and not any(x in line.lower() for x in ['resume', 'curriculum', 'vitae', 'email', 'phone', 'page']):
            parts = line.split()
            if len(parts) == 2:
                return {'first': parts[0], 'last': parts[1]}
    return {'first': None, 'last': None}

def extract_email_enhanced(text):
    if not text:
        return None
    pattern = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
    match = re.search(pattern, text)
    return match.group(0) if match else None

def extract_phone_enhanced(text):
    if not text:
        return None
    patterns = [r'\b\d{10}\b', r'\+\d{1,2}[-.\s]?\d{10}\b', r'\b\d{3}[-.]?\d{3}[-.]?\d{4}\b']
    for pattern in patterns:
        match = re.search(pattern, text)
        if match:
            return match.group(0)
    return None

def extract_skills_enhanced(text):
    skill_database = ['Python', 'Java', 'JavaScript', 'TypeScript', 'C++', 'C#', 'Go', 'Ruby', 'PHP', 'Swift', 'Kotlin', 'React', 'Angular', 'Vue', 'Node.js', 'Django', 'Flask', 'Spring', 'Express', 'MySQL', 'PostgreSQL', 'MongoDB', 'Redis', 'AWS', 'Azure', 'GCP', 'Docker', 'Kubernetes', 'Git', 'Machine Learning', 'Data Science', 'Project Management', 'Agile', 'Scrum']
    found = []
    text_lower = text.lower()
    for skill in skill_database:
        if skill.lower() in text_lower:
            found.append(skill)
    return found

def extract_experience_enhanced(text):
    if not text:
        return 0.0
    patterns = [r'(\d+)\s*\+\s*years?', r'(\d+)\s*years?\s+of\s+experience', r'total\s+experience\s*:?\s*(\d+)', r'experience\s*:?\s*(\d+)\s*years?']
    for pattern in patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            try:
                return float(match.group(1))
            except (ValueError, TypeError):
                pass
    return 0.0

def extract_company_enhanced(text):
    if not text:
        return None
    patterns = [r'Current\s+Company\s*:?\s*([^\n]+)', r'Employer\s*:?\s*([^\n]+)', r'Work\s+Experience[^\n]*\n\s*([^\n]+)']
    for pattern in patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            company = match.group(1).strip()
            if company and len(company) < 50 and not any(x in company.lower() for x in ['email', 'phone', 'skills']):
                return company
    return None

def extract_designation_enhanced(text):
    if not text:
        return None
    patterns = [r'Designation\s*:?\s*([^\n]+)', r'Title\s*:?\s*([^\n]+)', r'Position\s*:?\s*([^\n]+)']
    for pattern in patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            return match.group(1).strip()
    titles = ['Developer', 'Engineer', 'Manager', 'Lead', 'Architect', 'Consultant', 'Analyst', 'Specialist']
    for title in titles:
        pattern = rf'([A-Za-z\s]+{title})'
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            return match.group(1).strip()
    return None

def extract_location_enhanced(text):
    if not text:
        return None
    cities = ['Bangalore', 'Mumbai', 'Delhi', 'Hyderabad', 'Chennai', 'Pune', 'Kolkata', 'Ahmedabad', 'Remote', 'Gurgaon', 'Noida']
    for city in cities:
        if city.lower() in text.lower():
            return city
    pattern = r'Location\s*:?\s*([^\n]+)'
    match = re.search(pattern, text, re.IGNORECASE)
    return match.group(1).strip() if match else None

def extract_qualifications_enhanced(text):
    if not text:
        return None
    degrees = ['Bachelor', 'Master', 'B.Tech', 'M.Tech', 'BCA', 'MCA', 'MBA', 'PhD', 'B.Sc', 'M.Sc', 'Diploma', 'B.Com', 'M.Com']
    found = []
    for degree in degrees:
        pattern = f'{degree}[^\n]*'
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            found.append(match.group().strip())
    return '\n'.join(found[:3]) if found else None

def extract_languages(text):
    if not text:
        return []
    languages = ['English', 'Hindi', 'Spanish', 'French', 'German', 'Chinese', 'Japanese', 'Tamil', 'Telugu', 'Kannada', 'Malayalam', 'Bengali']
    found = []
    text_lower = text.lower()
    for lang in languages:
        if lang.lower() in text_lower:
            found.append(lang)
    return found

def extract_certifications(text):
    if not text:
        return []
    import re
    cert_patterns = ['AWS', 'Azure', 'Google Cloud', 'PMP', 'Scrum Master', 'CISSP', 'CEH']
    found = []
    for pattern in cert_patterns:
        if pattern.lower() in text.lower():
            found.append(pattern)
    return found

# ============= API ROUTES =============
@app.route('/')
def index():
    return render_template_string(DASHBOARD_TEMPLATE)

@app.route('/health')
def health():
    return jsonify({'status': 'ok', 'timestamp': datetime.now().isoformat()})

@app.route('/api/dashboard/stats')
def dashboard_stats():
    total_apps = len(applications)
    total_matches = sum([a.get('match_score', 0) for a in applications])
    avg_match = round(total_matches / total_apps, 1) if total_apps > 0 else 0
    return jsonify({
        'overview': {
            'open_positions': len([j for j in jobs if j.get('status') == 'open']),
            'total_candidates': len(candidates),
            'total_applications': total_apps,
            'avg_match_rate': avg_match,
            'interviews_today': len([i for i in interviews if i.get('status') == 'scheduled']),
            'offers_accepted': len([o for o in offers if o.get('status') == 'accepted'])
        },
        'pipeline': {
            'new': len([a for a in applications if a.get('status') == 'new']),
            'shortlisted': len([a for a in applications if a.get('status') in ['screening', 'shortlisted']]),
            'interviewed': len([a for a in applications if a.get('status') in ['interview-scheduled', 'interviewed']]),
            'selected': len([a for a in applications if a.get('status') == 'selected']),
            'rejected': len([a for a in applications if a.get('status') == 'rejected'])
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
            'id': next_id, 'code': f"JD-{next_id:04d}", 'title': data.get('title', 'Untitled'),
            'location': data.get('location', 'Remote'), 'status': data.get('status', 'open'),
            'skills_required': data.get('skills_required', ''), 'applications': 0,
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
            'id': next_id, 'code': f"CAN-{next_id:04d}", 'first_name': data.get('first_name', ''),
            'last_name': data.get('last_name', ''), 'name': f"{data.get('first_name', '')} {data.get('last_name', '')}".strip(),
            'email': data.get('email', ''), 'skills': data.get('skills', ''), 'source': data.get('source', 'manual'),
            'created_at': datetime.now().isoformat()
        }
        candidates.append(candidate)
        next_id += 1
        return jsonify({'success': True, 'candidate_id': candidate['id'], 'candidate_code': candidate['code']})
    return jsonify({'candidates': [{'id': c['id'], 'code': c['code'], 'name': c['name'], 'email': c['email']} for c in candidates], 'total': len(candidates), 'page': 1, 'pages': 1})

@app.route('/api/applications', methods=['GET', 'POST'])
def manage_applications():
    if request.method == 'POST':
        data = request.get_json()
        job = next((j for j in jobs if j['id'] == data.get('jd_id')), None)
        candidate = next((c for c in candidates if c['id'] == data.get('candidate_id')), None)
        match_score, _ = calculate_weighted_match_score(job.get('skills_required', '') if job else '', candidate.get('skills', '') if candidate else '')
        application = {
            'id': len(applications) + 1, 'candidate_id': data.get('candidate_id'), 'jd_id': data.get('jd_id'),
            'status': 'new', 'application_date': datetime.now().date().isoformat(), 'match_score': match_score,
            'created_at': datetime.now().isoformat()
        }
        applications.append(application)
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

@app.route('/api/candidates/parse-resume-enhanced', methods=['POST'])
def parse_resume_enhanced():
    if 'file' not in request.files:
        return jsonify({'error': 'No file uploaded'}), 400
    file = request.files['file']
    filename = file.filename.lower()
    text = ''
    if filename.endswith('.pdf'):
        try:
            import PyPDF2
            reader = PyPDF2.PdfReader(file)
            for page in reader.pages:
                page_text = page.extract_text()
                if page_text:
                    text += page_text
        except Exception:
            text = ''
    elif filename.endswith('.docx'):
        try:
            import docx
            doc = docx.Document(file)
            text = '\n'.join([para.text for para in doc.paragraphs])
        except Exception:
            text = ''
    else:
        try:
            text = file.read().decode('utf-8')
        except Exception:
            text = ''
    parsed_data = {
        'first_name': extract_name_enhanced(text)['first'], 'last_name': extract_name_enhanced(text)['last'],
        'email': extract_email_enhanced(text), 'phone': extract_phone_enhanced(text),
        'skills': extract_skills_enhanced(text), 'total_experience': extract_experience_enhanced(text),
        'current_company': extract_company_enhanced(text), 'current_designation': extract_designation_enhanced(text),
        'current_location': extract_location_enhanced(text), 'qualifications': extract_qualifications_enhanced(text),
        'languages': extract_languages(text), 'certifications': extract_certifications(text)
    }
    return jsonify({'success': True, 'data': parsed_data, 'resume_text_preview': text[:500] + '...' if len(text) > 500 else text})

@app.route('/api/candidates/parse-resume', methods=['POST'])
def parse_resume():
    return jsonify({'success': True, 'data': {'first_name': 'John', 'last_name': 'Doe', 'email': 'john@example.com', 'phone': '9876543210', 'skills': ['Python', 'JavaScript', 'SQL'], 'qualifications': 'B.Tech', 'current_company': 'Tech Corp', 'current_designation': 'Software Engineer'}})

@app.route('/api/candidates/<int:candidate_id>/notes', methods=['GET', 'POST'])
def candidate_notes_api(candidate_id):
    if request.method == 'POST':
        data = request.json
        note = {'id': len(candidate_notes.get(candidate_id, [])) + 1, 'text': data.get('text'), 'author': data.get('author', 'Recruiter'), 'created_at': datetime.now().isoformat()}
        if candidate_id not in candidate_notes:
            candidate_notes[candidate_id] = []
        candidate_notes[candidate_id].append(note)
        return jsonify({'success': True, 'note': note})
    return jsonify({'notes': candidate_notes.get(candidate_id, [])})

@app.route('/api/applications/<int:app_id>/notes', methods=['GET', 'POST'])
def application_notes_api(app_id):
    if request.method == 'POST':
        data = request.json
        note = {'id': len(application_notes.get(app_id, [])) + 1, 'text': data.get('text'), 'author': data.get('author', 'Recruiter'), 'created_at': datetime.now().isoformat()}
        if app_id not in application_notes:
            application_notes[app_id] = []
        application_notes[app_id].append(note)
        return jsonify({'success': True, 'note': note})
    return jsonify({'notes': application_notes.get(app_id, [])})

@app.route('/api/interviews', methods=['GET', 'POST'])
def manage_interviews():
    if request.method == 'POST':
        data = request.json
        application = next((a for a in applications if a['id'] == data.get('application_id')), None)
        candidate = next((c for c in candidates if c['id'] == application.get('candidate_id')), None) if application else None
        job = next((j for j in jobs if j['id'] == application.get('jd_id')), None) if application else None
        interview = {
            'id': len(interviews) + 1, 'application_id': data.get('application_id'),
            'candidate_name': f"{candidate.get('first_name', '')} {candidate.get('last_name', '')}".strip() if candidate else data.get('candidate_name'),
            'job_title': job.get('title') if job else data.get('job_title'),
            'interviewer': data.get('interviewer'), 'interviewer_email': data.get('interviewer_email'),
            'scheduled_time': data.get('scheduled_time'), 'duration_minutes': data.get('duration_minutes', 60),
            'meeting_link': data.get('meeting_link'), 'round_type': data.get('round_type', 'Technical'),
            'status': 'scheduled', 'created_at': datetime.now().isoformat()
        }
        interviews.append(interview)
        if application:
            application['status'] = 'interview-scheduled'
        return jsonify({'success': True, 'interview_id': interview['id']})
    return jsonify([i for i in interviews if i.get('status') == 'scheduled'])

@app.route('/api/interviews/<int:interview_id>/complete', methods=['PUT'])
def complete_interview(interview_id):
    data = request.json
    for interview in interviews:
        if interview['id'] == interview_id:
            interview['status'] = 'completed'
            interview['feedback'] = data.get('feedback')
            interview['rating'] = data.get('rating')
            interview['result'] = data.get('result')
            if interview.get('application_id'):
                for app in applications:
                    if app['id'] == interview['application_id']:
                        app['status'] = 'interviewed' if data.get('result') == 'pass' else 'rejected'
                        break
            break
    return jsonify({'success': True})

@app.route('/api/offers', methods=['GET', 'POST'])
def manage_offers():
    if request.method == 'POST':
        data = request.json
        offer = {
            'id': len(offers) + 1, 'application_id': data.get('application_id'),
            'candidate_name': data.get('candidate_name'), 'candidate_email': data.get('candidate_email'),
            'job_title': data.get('job_title'), 'base_salary': data.get('base_salary'),
            'joining_bonus': data.get('joining_bonus', 0), 'joining_date': data.get('joining_date'),
            'status': 'draft', 'created_at': datetime.now().isoformat(),
            'offer_letter_html': generate_offer_letter_html(data)
        }
        offers.append(offer)
        for app in applications:
            if app['id'] == data.get('application_id'):
                app['status'] = 'offered'
                break
        return jsonify({'success': True, 'offer_id': offer['id'], 'offer_html': offer['offer_letter_html']})
    return jsonify(offers)

def generate_offer_letter_html(data):
    base_salary = data.get('base_salary', 0)
    joining_bonus = data.get('joining_bonus', 0)
    try:
        salary_formatted = f"${float(base_salary):,.2f}" if base_salary else "TBD"
        bonus_formatted = f"${float(joining_bonus):,.2f}" if joining_bonus else "$0"
    except (ValueError, TypeError):
        salary_formatted = "TBD"
        bonus_formatted = "$0"
    return f'''<!DOCTYPE html><html><head><title>Offer Letter</title><style>body{{font-family:Arial;margin:50px;}}.container{{max-width:800px;margin:auto;}}.header{{text-align:center;border-bottom:2px solid #4CAF50;padding-bottom:20px;}}.content{{margin:30px 0;}}.signature{{margin-top:50px;}}table{{width:100%;border-collapse:collapse;margin:20px 0;}}td{{padding:10px;border:1px solid #ddd;}}</style></head><body><div class="container"><div class="header"><h1>ShahnaIT Scout</h1><h2>Offer of Employment</h2></div><div class="content"><p>Dear <strong>{data.get('candidate_name', 'Candidate')}</strong>,</p><p>We are pleased to offer you the position of <strong>{data.get('job_title', 'Position')}</strong> at ShahnaIT Scout.</p><h3>Offer Details</h3><table><tr><td><strong>Position</strong></td><td>{data.get('job_title', 'Position')}</td></tr><tr><td><strong>Base Salary</strong></td><td>{salary_formatted} per year</td></tr><tr><td><strong>Joining Bonus</strong></td><td>{bonus_formatted}</td></tr><tr><td><strong>Expected Joining Date</strong></td><td>{data.get('joining_date', 'TBD')}</td></tr></table><h3>Terms & Conditions</h3><p>This offer is valid for 15 days from the date of issuance.</p><p>We look forward to having you on our team!</p></div><div class="signature"><p>Sincerely,<br><strong>ShahnaIT Recruitment Team</strong></p></div></div></body></html>'''

@app.route('/api/reports/hiring-metrics', methods=['GET'])
def hiring_metrics():
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
    total_apps = len(applications)
    if total_apps > 0:
        screening_rate = len([a for a in applications if a.get('status') in ['screening', 'shortlisted']]) / total_apps * 100
        interview_rate = len([a for a in applications if a.get('status') in ['interview-scheduled', 'interviewed']]) / total_apps * 100
        offer_rate = len([a for a in applications if a.get('status') in ['offered', 'offer-accepted']]) / total_apps * 100
        hire_rate = len([a for a in applications if a.get('status') == 'joined']) / total_apps * 100
    else:
        screening_rate = interview_rate = offer_rate = hire_rate = 0
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
        source_effectiveness.append({'source': source, 'total': stats['total'], 'hired': stats['hired'], 'conversion_rate': conversion})
    return jsonify({
        'total_applications': total_apps, 'average_time_to_hire_days': round(avg_time_to_hire, 1),
        'conversion_rates': {'screening': round(screening_rate, 1), 'interview': round(interview_rate, 1), 'offer': round(offer_rate, 1), 'hire': round(hire_rate, 1)},
        'source_effectiveness': source_effectiveness,
        'applications_by_stage': {
            'new': len([a for a in applications if a.get('status') == 'new']),
            'screening': len([a for a in applications if a.get('status') in ['screening', 'shortlisted']]),
            'interview': len([a for a in applications if a.get('status') in ['interview-scheduled', 'interviewed']]),
            'offer': len([a for a in applications if a.get('status') in ['offered', 'offer-accepted']]),
            'hired': len([a for a in applications if a.get('status') == 'joined'])
        }
    })

@app.route('/api/pipeline/stages', methods=['GET'])
def get_pipeline_stages():
    return jsonify(PIPELINE_STAGES)

@app.route('/api/pipeline/candidates', methods=['GET'])
def get_pipeline_candidates():
    candidate_stage_map = {}
    for app in applications:
        candidate_stage_map[app.get('candidate_id')] = app.get('status', 'new')
    pipeline_data = {}
    for stage in PIPELINE_STAGES:
        stage_id = stage['id']
        pipeline_data[stage_id] = []
        for candidate in candidates:
            current_stage = candidate_stage_map.get(candidate['id'])
            if current_stage is None and stage_id == 'new':
                pipeline_data[stage_id].append({'id': candidate['id'], 'name': candidate['name'], 'email': candidate['email'], 'skills': candidate.get('skills', ''), 'current_company': candidate.get('current_company', ''), 'current_designation': candidate.get('current_designation', ''), 'total_experience': candidate.get('total_experience', 0), 'application_id': None, 'match_score': None})
            elif current_stage == stage_id:
                app = next((a for a in applications if a.get('candidate_id') == candidate['id']), None)
                pipeline_data[stage_id].append({'id': candidate['id'], 'name': candidate['name'], 'email': candidate['email'], 'skills': candidate.get('skills', ''), 'current_company': candidate.get('current_company', ''), 'current_designation': candidate.get('current_designation', ''), 'total_experience': candidate.get('total_experience', 0), 'application_id': app['id'] if app else None, 'match_score': app.get('match_score') if app else None})
    return jsonify(pipeline_data)

@app.route('/api/pipeline/move', methods=['PUT'])
def move_pipeline_candidate():
    data = request.json
    candidate_id = data.get('candidate_id')
    new_stage = data.get('new_stage')
    application = None
    for app in applications:
        if app.get('candidate_id') == candidate_id:
            application = app
            break
    if application:
        old_stage = application['status']
        application['status'] = new_stage
        application['updated_at'] = datetime.now().isoformat()
        return jsonify({'success': True, 'message': f'Moved from {old_stage} to {new_stage}', 'old_stage': old_stage, 'new_stage': new_stage})
    else:
        job = next((j for j in jobs if j.get('status') == 'open'), jobs[0] if jobs else None)
        if job:
            candidate = next((c for c in candidates if c['id'] == candidate_id), None)
            match_score, _ = calculate_weighted_match_score(job.get('skills_required', ''), candidate.get('skills', '') if candidate else '')
            new_application = {
                'id': len(applications) + 1, 'application_code': f"APP-{len(applications) + 1:04d}",
                'candidate_id': candidate_id, 'jd_id': job['id'], 'job_title': job['title'],
                'candidate_name': candidate['name'] if candidate else '', 'match_score': match_score,
                'status': new_stage, 'application_date': datetime.now().date().isoformat(),
                'created_at': datetime.now().isoformat()
            }
            applications.append(new_application)
            job['applications'] = job.get('applications', 0) + 1
            return jsonify({'success': True, 'message': f'Candidate moved to {new_stage}', 'new_stage': new_stage, 'match_score': match_score})
        else:
            return jsonify({'success': False, 'error': 'No open jobs available. Please create a job first.'}), 400

@app.route('/api/clients', methods=['GET'])
def get_clients():
    return jsonify([])

# ============= MAIN =============
if __name__ == '__main__':
    port = int(os.environ.get('PORT', 8080))
    app.run(host='0.0.0.0', port=port, debug=False)
