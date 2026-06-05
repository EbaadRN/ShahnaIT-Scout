# app.py - SUPER SIMPLE WORKING VERSION
import os
from flask import Flask, render_template_string
from flask_cors import CORS
from routes.candidates import candidates_bp
from routes.jobs import jobs_bp
from routes.analyze import analyze_bp
from routes.export import export_bp
from routes.documents import documents_bp
from models.database import init_db

app = Flask(__name__)
CORS(app)

# Initialize database
init_db()

# Create documents folder if not exists
os.makedirs('/tmp/candidate_docs', exist_ok=True)

# Register all blueprints
app.register_blueprint(candidates_bp, url_prefix='/api')
app.register_blueprint(jobs_bp, url_prefix='/api')
app.register_blueprint(analyze_bp, url_prefix='/api')
app.register_blueprint(export_bp, url_prefix='/api')
app.register_blueprint(documents_bp, url_prefix='/api')

# SIMPLE HTML - ALL BUTTONS WORK
HTML_TEMPLATE = '''
<!DOCTYPE html>
<html>
<head>
    <title>ShahnaIT Scout</title>
    <style>
        body { font-family: Arial, sans-serif; background: #F9F6F0; margin: 0; padding: 20px; }
        .header { background: #1D5E5A; color: white; padding: 15px; border-radius: 10px; margin-bottom: 20px; }
        .tabs { display: flex; gap: 5px; margin-bottom: 20px; flex-wrap: wrap; }
        .tab-btn { background: white; border: none; padding: 10px 20px; cursor: pointer; border-radius: 8px; }
        .tab-btn.active { background: #1D5E5A; color: white; }
        .card { background: white; border-radius: 10px; padding: 15px; margin-bottom: 15px; border-left: 3px solid #1D5E5A; }
        button { background: #1D5E5A; color: white; border: none; padding: 8px 20px; border-radius: 20px; cursor: pointer; margin: 5px; }
        input, select, textarea { width: 100%; padding: 8px; margin: 5px 0 10px 0; border: 1px solid #ccc; border-radius: 5px; }
        .skill-tag { background: #F9F6F0; padding: 3px 8px; border-radius: 15px; display: inline-block; margin: 2px; font-size: 12px; }
        .match-high { background: #1B6B2E; color: white; padding: 2px 8px; border-radius: 15px; display: inline-block; }
        .match-medium { background: #CC5500; color: white; padding: 2px 8px; border-radius: 15px; display: inline-block; }
        .match-low { background: #B22222; color: white; padding: 2px 8px; border-radius: 15px; display: inline-block; }
        .alert-success { background: #1B6B2E; color: white; padding: 10px; border-radius: 8px; margin: 10px 0; }
        .alert-error { background: #B22222; color: white; padding: 10px; border-radius: 8px; margin: 10px 0; }
        .spinner { border: 3px solid #f3f3f3; border-top: 3px solid #1D5E5A; border-radius: 50%; width: 30px; height: 30px; animation: spin 1s linear infinite; margin: 10px auto; }
        @keyframes spin { 0% { transform: rotate(0deg); } 100% { transform: rotate(360deg); } }
        .modal { display: none; position: fixed; z-index: 1000; left: 0; top: 0; width: 100%; height: 100%; background: rgba(0,0,0,0.5); }
        .modal-content { background: #F9F6F0; margin: 50px auto; border-radius: 10px; max-width: 600px; width: 90%; }
        .modal-header { background: #1D5E5A; color: white; padding: 10px 15px; border-radius: 10px 10px 0 0; display: flex; justify-content: space-between; }
        .modal-body { padding: 15px; max-height: 60vh; overflow-y: auto; }
        .close { cursor: pointer; font-size: 20px; }
        .flex { display: flex; gap: 10px; }
        .flex-1 { flex: 1; }
        .filter-bar { background: white; padding: 10px; border-radius: 10px; margin-bottom: 15px; display: flex; gap: 10px; flex-wrap: wrap; }
        .filter-bar input, .filter-bar select { width: auto; flex: 1; margin: 0; }
    </style>
</head>
<body>
<div style="max-width: 1200px; margin: 0 auto;">
    <div class="header">
        <h1>🎯 ShahnaIT Scout</h1>
        <p>AI-Powered Recruitment Platform</p>
    </div>
    
    <div class="tabs">
        <button class="tab-btn active" id="jobsTabBtn">📋 Jobs</button>
        <button class="tab-btn" id="candidatesTabBtn">👥 Candidates</button>
        <button class="tab-btn" id="uploadTabBtn">📄 Upload Resume</button>
        <button class="tab-btn" id="createJobTabBtn">➕ Create Job</button>
        <button class="tab-btn" id="analyzeTabBtn">🔍 Analyze Match</button>
    </div>
    
    <div id="jobsPanel"><div id="jobsList"></div></div>
    
    <div id="candidatesPanel" style="display:none;">
        <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 10px;">
            <h2>Candidates <span id="candidateCount"></span></h2>
            <button id="exportBtn">📥 Export CSV</button>
        </div>
        <div class="filter-bar">
            <input type="text" id="searchBox" placeholder="Search by name..." onkeyup="filterCandidates()">
            <select id="scoreFilter" onchange="filterCandidates()">
                <option value="all">All Scores</option>
                <option value="high">High (70%+)</option>
                <option value="medium">Medium (40-69%)</option>
                <option value="low">Low (<40%)</option>
            </select>
            <button id="clearFilterBtn">Clear</button>
        </div>
        <div id="candidatesList"></div>
    </div>
    
    <div id="uploadPanel" style="display:none;">
        <div class="card">
            <h3>Upload Resume (PDF/DOCX)</h3>
            <input type="file" id="resumeInput" accept=".pdf,.docx">
            <button id="parseBtn">🔍 Parse & Save</button>
            <div id="parseResult"></div>
        </div>
    </div>
    
    <div id="createJobPanel" style="display:none;">
        <div class="card">
            <h3>Create New Job</h3>
            <input type="text" id="jobTitleInput" placeholder="Job Title *">
            <input type="text" id="jobCompanyInput" placeholder="Company Name">
            <textarea id="jobDescInput" rows="4" placeholder="Job Description"></textarea>
            <button id="createJobSubmitBtn">Create Job</button>
        </div>
    </div>
    
    <div id="analyzePanel" style="display:none;">
        <div class="card">
            <h3>AI Match Analysis</h3>
            <div class="flex">
                <div class="flex-1"><select id="jobSelectBox"><option value="">-- Select Job --</option></select></div>
                <div class="flex-1"><select id="candidateSelectBox"><option value="">-- Select Candidate --</option></select></div>
            </div>
            <button id="runAnalysisBtn">🤖 Run Analysis</button>
            <div id="analysisResult"></div>
        </div>
    </div>
</div>

<div id="candidateDetailModal" class="modal">
    <div class="modal-content">
        <div class="modal-header"><h2>Candidate Details</h2><span class="close" onclick="closeModal()">&times;</span></div>
        <div class="modal-body" id="candidateDetailBody"></div>
    </div>
</div>

<script>
    let allJobs = [], allCandidates = [];
    
    // Tab Switching
    document.getElementById('jobsTabBtn').onclick = function() { showPanel('jobs'); loadJobs(); };
    document.getElementById('candidatesTabBtn').onclick = function() { showPanel('candidates'); loadCandidates(); };
    document.getElementById('uploadTabBtn').onclick = function() { showPanel('upload'); };
    document.getElementById('createJobTabBtn').onclick = function() { showPanel('createJob'); };
    document.getElementById('analyzeTabBtn').onclick = function() { showPanel('analyze'); loadJobs(); loadCandidates(); };
    
    function showPanel(panel) {
        document.getElementById('jobsPanel').style.display = 'none';
        document.getElementById('candidatesPanel').style.display = 'none';
        document.getElementById('uploadPanel').style.display = 'none';
        document.getElementById('createJobPanel').style.display = 'none';
        document.getElementById('analyzePanel').style.display = 'none';
        document.getElementById(panel + 'Panel').style.display = 'block';
        
        document.querySelectorAll('.tab-btn').forEach(btn => btn.classList.remove('active'));
        if (panel === 'jobs') document.getElementById('jobsTabBtn').classList.add('active');
        if (panel === 'candidates') document.getElementById('candidatesTabBtn').classList.add('active');
        if (panel === 'upload') document.getElementById('uploadTabBtn').classList.add('active');
        if (panel === 'createJob') document.getElementById('createJobTabBtn').classList.add('active');
        if (panel === 'analyze') document.getElementById('analyzeTabBtn').classList.add('active');
    }
    
    async function loadJobs() {
        const res = await fetch('/api/jobs');
        allJobs = await res.json();
        const container = document.getElementById('jobsList');
        if (!allJobs.length) { container.innerHTML = '<div class="card">No jobs yet. Create one.</div>'; return; }
        container.innerHTML = allJobs.map(j => `<div class="card"><h3>${escapeHtml(j.title)}</h3>${j.company ? `<p>${escapeHtml(j.company)}</p>` : ''}<small>${new Date(j.created_at).toLocaleDateString()}</small></div>`).join('');
        document.getElementById('jobSelectBox').innerHTML = '<option value="">-- Select Job --</option>' + allJobs.map(j => `<option value="${j.id}">${escapeHtml(j.title)}</option>`).join('');
    }
    
    async function loadCandidates() {
        const res = await fetch('/api/candidates');
        allCandidates = await res.json();
        filterCandidates();
        document.getElementById('candidateSelectBox').innerHTML = '<option value="">-- Select Candidate --</option>' + allCandidates.map(c => `<option value="${c.id}">${escapeHtml(c.first_name + ' ' + c.last_name || 'Unknown')}</option>`).join('');
    }
    
    function filterCandidates() {
        const search = document.getElementById('searchBox').value.toLowerCase();
        const score = document.getElementById('scoreFilter').value;
        let filtered = allCandidates;
        if (search) filtered = filtered.filter(c => (c.first_name + ' ' + c.last_name).toLowerCase().includes(search));
        if (score === 'high') filtered = filtered.filter(c => (c.match_score || 0) >= 70);
        else if (score === 'medium') filtered = filtered.filter(c => (c.match_score || 0) >= 40 && (c.match_score || 0) < 70);
        else if (score === 'low') filtered = filtered.filter(c => (c.match_score || 0) < 40);
        renderCandidateList(filtered);
        document.getElementById('candidateCount').innerHTML = `(${filtered.length})`;
    }
    
    function renderCandidateList(candidates) {
        const container = document.getElementById('candidatesList');
        if (!candidates.length) { container.innerHTML = '<div class="card">No candidates found</div>'; return; }
        container.innerHTML = candidates.map(c => {
            const name = (c.first_name + ' ' + c.last_name).trim() || 'Unknown';
            const skills = c.core_skills ? JSON.parse(c.core_skills) : [];
            const matchClass = c.match_score >= 70 ? 'match-high' : (c.match_score >= 40 ? 'match-medium' : 'match-low');
            return `<div class="card" onclick="viewCandidate(${c.id})">
                <h3>👤 ${escapeHtml(name)}</h3>
                <p>${skills.slice(0,3).map(s => `<span class="skill-tag">${escapeHtml(s.skill)}</span>`).join('')}</p>
                ${c.match_score ? `<p>Score: <span class="${matchClass}">${c.match_score}%</span></p>` : ''}
                <small>${new Date(c.created_at).toLocaleDateString()}</small>
            </div>`;
        }).join('');
    }
    
    document.getElementById('clearFilterBtn').onclick = function() {
        document.getElementById('searchBox').value = '';
        document.getElementById('scoreFilter').value = 'all';
        filterCandidates();
    };
    
    async function viewCandidate(id) {
        const c = allCandidates.find(c => c.id == id);
        if (!c) return;
        const name = (c.first_name + ' ' + c.last_name).trim();
        const skills = c.core_skills ? JSON.parse(c.core_skills) : [];
        const certs = c.certifications ? JSON.parse(c.certifications) : [];
        
        document.getElementById('candidateDetailBody').innerHTML = `
            <div class="detail-row"><strong>Name:</strong> ${escapeHtml(name)}</div>
            <div class="detail-row"><strong>Email:</strong> ${escapeHtml(c.email || 'N/A')}</div>
            <div class="detail-row"><strong>Phone:</strong> ${escapeHtml(c.phone || 'N/A')}</div>
            <div class="detail-row"><strong>Role:</strong> ${escapeHtml(c.current_role || 'N/A')}</div>
            <h4>Skills</h4>
            ${skills.map(s => `<span class="skill-tag">${escapeHtml(s.skill)} (${s.years_of_experience || 0}y)</span>`).join('') || 'None'}
            <h4>Certifications</h4>
            ${certs.map(c => `<div>${escapeHtml(c)}</div>`).join('') || 'None'}
            <button onclick="closeModal()" style="margin-top:10px;">Close</button>
        `;
        document.getElementById('candidateDetailModal').style.display = 'block';
    }
    
    function closeModal() { document.getElementById('candidateDetailModal').style.display = 'none'; }
    window.exportToCSV = () => window.location.href = '/api/export-candidates';
    document.getElementById('exportBtn').onclick = () => window.location.href = '/api/export-candidates';
    
    // Parse Resume
    document.getElementById('parseBtn').onclick = async function() {
        const file = document.getElementById('resumeInput').files[0];
        if (!file) { alert('Select a file'); return; }
        const fd = new FormData(); fd.append('resume', file);
        const div = document.getElementById('parseResult');
        div.innerHTML = '<div class="spinner"></div><p>Parsing...</p>';
        try {
            const res = await fetch('/api/parse-resume', { method: 'POST', body: fd });
            const result = await res.json();
            if (result.error) { div.innerHTML = `<div class="alert-error">${result.error}</div>`; return; }
            div.innerHTML = `<div class="alert-success"><h4>✅ Parsed</h4><p><strong>Name:</strong> ${escapeHtml(result.first_name || '')} ${escapeHtml(result.last_name || '')}</p><p><strong>Email:</strong> ${escapeHtml(result.email || '')}</p><p><strong>Phone:</strong> ${escapeHtml(result.phone || '')}</p><p><strong>Skills:</strong> ${result.core_skills ? result.core_skills.map(s => `<span class="skill-tag">${escapeHtml(s.skill)}</span>`).join('') : 'None'}</p><button id="saveCandidateBtn">💾 Save Candidate</button></div>`;
            document.getElementById('saveCandidateBtn').onclick = async function() {
                const saveRes = await fetch('/api/candidates', { method: 'POST', headers: {'Content-Type':'application/json'}, body: JSON.stringify(result) });
                if (saveRes.ok) { alert('Saved!'); div.innerHTML = ''; document.getElementById('resumeInput').value = ''; loadCandidates(); showPanel('candidates'); }
                else alert('Error');
            };
        } catch(e) { div.innerHTML = '<div class="alert-error">Error</div>'; }
    };
    
    // Create Job
    document.getElementById('createJobSubmitBtn').onclick = async function() {
        const data = {
            title: document.getElementById('jobTitleInput').value,
            company: document.getElementById('jobCompanyInput').value,
            description: document.getElementById('jobDescInput').value
        };
        if (!data.title) { alert('Title required'); return; }
        const res = await fetch('/api/jobs', { method: 'POST', headers: {'Content-Type':'application/json'}, body: JSON.stringify(data) });
        if (res.ok) {
            alert('Job created!');
            document.getElementById('jobTitleInput').value = '';
            document.getElementById('jobCompanyInput').value = '';
            document.getElementById('jobDescInput').value = '';
            showPanel('jobs');
            loadJobs();
        } else { alert('Error'); }
    };
    
    // Analyze Match
    document.getElementById('runAnalysisBtn').onclick = async function() {
        const jobId = document.getElementById('jobSelectBox').value;
        const candidateId = document.getElementById('candidateSelectBox').value;
        if (!jobId || !candidateId) { alert('Select both'); return; }
        const job = allJobs.find(j => j.id == jobId);
        const cand = allCandidates.find(c => c.id == candidateId);
        const div = document.getElementById('analysisResult');
        div.innerHTML = '<div class="spinner"></div><p>Analyzing...</p>';
        try {
            const res = await fetch('/api/analyze-match', { method: 'POST', headers: {'Content-Type':'application/json'}, body: JSON.stringify({ job_id: jobId, candidate_id: candidateId, jd_text: job.description || '', resume_text: cand.resume_text || '' }) });
            const result = await res.json();
            if (result.error) { div.innerHTML = `<div class="alert-error">${result.error}</div>`; return; }
            const matchClass = result.match_score >= 70 ? 'match-high' : (result.match_score >= 40 ? 'match-medium' : 'match-low');
            div.innerHTML = `<div class="alert-success"><h4>Analysis Complete</h4><p><strong>Score:</strong> <span class="${matchClass}">${result.match_score || 0}%</span></p><p><strong>Recommendation:</strong> ${result.recommendation || 'Review'}</p><small>✅ Saved</small></div>`;
            loadCandidates();
        } catch(e) { div.innerHTML = '<div class="alert-error">Failed</div>'; }
    };
    
    function escapeHtml(str) { if (!str) return ''; return str.replace(/[&<>]/g, function(m) { if (m === '&') return '&amp;'; if (m === '<') return '&lt;'; if (m === '>') return '&gt;'; return m; }); }
    
    // Initialize
    showPanel('jobs');
    loadJobs();
    loadCandidates();
</script>
</body>
</html>
'''

@app.route('/')
def index():
    return HTML_TEMPLATE

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
