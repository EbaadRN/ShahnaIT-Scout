# app.py - SIMPLIFIED WORKING VERSION WITH ALL FEATURES
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

# SIMPLIFIED HTML TEMPLATE - ALL BUTTONS WORK
HTML_TEMPLATE = '''
<!DOCTYPE html>
<html>
<head>
    <title>ShahnaIT Scout</title>
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body { background-color: #F9F6F0; font-family: 'Segoe UI', Arial, sans-serif; }
        .container { max-width: 1200px; margin: 0 auto; padding: 15px; }
        .header { background: linear-gradient(135deg, #1A3A3A, #1D5E5A); color: white; padding: 20px; border-radius: 12px; margin-bottom: 20px; }
        .header h1 { font-size: 24px; }
        .tabs { display: flex; gap: 5px; background: white; padding: 8px; border-radius: 10px; margin-bottom: 20px; flex-wrap: wrap; }
        .tab-btn { background: none; border: none; padding: 8px 16px; cursor: pointer; border-radius: 8px; font-size: 14px; }
        .tab-btn:hover { background: #F9F6F0; }
        .tab-btn.active { background: #1D5E5A; color: white; }
        .card { background: white; border-radius: 12px; padding: 15px; margin-bottom: 15px; border-left: 3px solid #1D5E5A; cursor: pointer; }
        .card:hover { transform: translateY(-2px); box-shadow: 0 2px 8px rgba(0,0,0,0.1); }
        .card.no-click { cursor: default; }
        .btn-primary { background: #1D5E5A; color: white; border: none; padding: 8px 20px; border-radius: 30px; cursor: pointer; margin: 5px; }
        .btn-primary:hover { background: #2A7A76; }
        .btn-secondary { background: #6B7B7B; color: white; border: none; padding: 6px 15px; border-radius: 30px; cursor: pointer; }
        input, textarea, select { width: 100%; padding: 10px; border: 1px solid #ccc; border-radius: 8px; margin-bottom: 10px; }
        .skill-tag { display: inline-block; background: #F9F6F0; padding: 3px 10px; border-radius: 20px; margin: 2px; font-size: 11px; }
        .match-high { background: #1B6B2E; color: white; padding: 2px 8px; border-radius: 20px; display: inline-block; font-size: 12px; }
        .match-medium { background: #CC5500; color: white; padding: 2px 8px; border-radius: 20px; display: inline-block; font-size: 12px; }
        .match-low { background: #B22222; color: white; padding: 2px 8px; border-radius: 20px; display: inline-block; font-size: 12px; }
        .alert-success { background: #1B6B2E; color: white; padding: 10px; border-radius: 8px; margin: 10px 0; }
        .alert-error { background: #B22222; color: white; padding: 10px; border-radius: 8px; margin: 10px 0; }
        .alert-info { background: #3498DB; color: white; padding: 10px; border-radius: 8px; margin: 10px 0; }
        .spinner { border: 3px solid #f3f3f3; border-top: 3px solid #1D5E5A; border-radius: 50%; width: 40px; height: 40px; animation: spin 1s linear infinite; margin: 20px auto; }
        @keyframes spin { 0% { transform: rotate(0deg); } 100% { transform: rotate(360deg); } }
        .modal { display: none; position: fixed; z-index: 1000; left: 0; top: 0; width: 100%; height: 100%; background: rgba(0,0,0,0.5); }
        .modal-content { background: #F9F6F0; margin: 50px auto; border-radius: 16px; max-width: 700px; width: 90%; }
        .modal-header { background: #1D5E5A; color: white; padding: 12px 15px; border-radius: 16px 16px 0 0; display: flex; justify-content: space-between; }
        .modal-body { padding: 15px; max-height: 60vh; overflow-y: auto; }
        .close { font-size: 24px; cursor: pointer; color: white; }
        .detail-row { display: flex; margin-bottom: 8px; border-bottom: 1px solid #ddd; padding-bottom: 5px; }
        .detail-label { width: 120px; font-weight: 600; }
        .detail-value { flex: 1; }
        .filter-bar { display: flex; gap: 8px; flex-wrap: wrap; background: white; padding: 12px; border-radius: 12px; margin-bottom: 15px; }
        .filter-bar input, .filter-bar select { margin: 0; flex: 1; min-width: 100px; }
        .flex { display: flex; gap: 10px; flex-wrap: wrap; }
        .flex-1 { flex: 1; }
        .file-list { background: #F9F6F0; border-radius: 8px; padding: 8px; margin-top: 8px; max-height: 120px; overflow-y: auto; }
        .file-list-item { padding: 3px; font-size: 11px; }
        .progress-bar { background: #ddd; border-radius: 10px; height: 15px; margin: 8px 0; overflow: hidden; }
        .progress-fill { background: #1B6B2E; width: 0%; height: 100%; }
        @media (max-width: 600px) { .container { padding: 10px; } .tab-btn { padding: 6px 12px; } .detail-label { width: 90px; } }
    </style>
</head>
<body>
<div class="container">
    <div class="header">
        <h1>🎯 ShahnaIT Scout <span style="background:#27AE60; padding:3px 10px; border-radius:20px; font-size:12px;">⚡ AI</span></h1>
        <p>Recruitment Platform with AI Resume Parsing</p>
    </div>
    
    <div class="tabs">
        <button class="tab-btn active" onclick="showTab('jobs')">Jobs</button>
        <button class="tab-btn" onclick="showTab('candidates')">Candidates</button>
        <button class="tab-btn" onclick="showTab('upload')">Upload Resume</button>
        <button class="tab-btn" onclick="showTab('createJob')">Create Job</button>
        <button class="tab-btn" onclick="showTab('analyze')">Analyze Match</button>
    </div>
    
    <div id="jobsTab"><div id="jobsList"></div></div>
    
    <div id="candidatesTab" style="display:none;">
        <div style="display: flex; justify-content: space-between; margin-bottom: 10px;">
            <h2>Candidates <span id="filterCount"></span></h2>
            <button class="btn-primary" onclick="exportToCSV()">Export CSV</button>
        </div>
        <div class="filter-bar">
            <input type="text" id="searchInput" placeholder="Search..." onkeyup="filterCandidates()">
            <select id="scoreFilter" onchange="filterCandidates()">
                <option value="all">All Scores</option>
                <option value="high">High (70%+)</option>
                <option value="medium">Medium (40-69%)</option>
                <option value="low">Low (<40%)</option>
            </select>
            <button class="btn-secondary" onclick="clearFilters()">Clear</button>
        </div>
        <div id="candidatesList"></div>
    </div>
    
    <div id="uploadTab" style="display:none;">
        <div class="card no-click">
            <h3>Upload Resume (PDF/DOCX)</h3>
            <div class="alert-info">AI will auto-fill details</div>
            <input type="file" id="resumeFile" accept=".pdf,.docx">
            <button class="btn-primary" id="uploadBtn">Parse & Save</button>
            <div id="uploadResult"></div>
        </div>
        <div class="card no-click" style="margin-top:15px;">
            <h3>Multiple Files (Select Many)</h3>
            <input type="file" id="multiFiles" multiple accept=".pdf,.docx">
            <button class="btn-primary" id="multiUploadBtn">Upload All</button>
            <div id="multiResult"></div>
        </div>
    </div>
    
    <div id="createJobTab" style="display:none;">
        <div class="card no-click">
            <h3>Create Job</h3>
            <input type="text" id="jobTitle" placeholder="Job Title *">
            <input type="text" id="jobCompany" placeholder="Company">
            <textarea id="jobDesc" rows="4" placeholder="Job Description"></textarea>
            <button class="btn-primary" id="createJobBtn">Create Job</button>
        </div>
    </div>
    
    <div id="analyzeTab" style="display:none;">
        <div class="card no-click">
            <h3>Match Analysis</h3>
            <div class="flex">
                <div class="flex-1"><select id="jobSelect"></select></div>
                <div class="flex-1"><select id="candidateSelect"></select></div>
            </div>
            <button class="btn-primary" id="analyzeBtn">Run Analysis</button>
            <div id="analyzeResult"></div>
        </div>
    </div>
</div>

<div id="candidateModal" class="modal">
    <div class="modal-content">
        <div class="modal-header"><h2>Candidate Profile</h2><span class="close" onclick="closeModal()">&times;</span></div>
        <div class="modal-body" id="modalBody"></div>
    </div>
</div>

<script>
    let jobsData = [], candidatesData = [];
    
    function showTab(tab) {
        const tabs = ['jobs', 'candidates', 'upload', 'createJob', 'analyze'];
        tabs.forEach(t => document.getElementById(t + 'Tab').style.display = 'none');
        document.getElementById(tab + 'Tab').style.display = 'block';
        document.querySelectorAll('.tab-btn').forEach(btn => btn.classList.remove('active'));
        if (event && event.target) event.target.classList.add('active');
        if (tab === 'jobs') loadJobs();
        if (tab === 'candidates') loadCandidates();
        if (tab === 'analyze') { loadJobs(); loadCandidates(); }
    }
    
    async function loadJobs() {
        const res = await fetch('/api/jobs');
        jobsData = await res.json();
        const container = document.getElementById('jobsList');
        if (!jobsData.length) { container.innerHTML = '<div class="card no-click">No jobs yet</div>'; return; }
        container.innerHTML = jobsData.map(j => `<div class="card no-click"><h3>${escapeHtml(j.title)}</h3>${j.company ? `<p>${escapeHtml(j.company)}</p>` : ''}<small>${new Date(j.created_at).toLocaleDateString()}</small></div>`).join('');
        document.getElementById('jobSelect').innerHTML = '<option value="">-- Select Job --</option>' + jobsData.map(j => `<option value="${j.id}">${escapeHtml(j.title)}</option>`).join('');
    }
    
    async function loadCandidates() {
        const res = await fetch('/api/candidates');
        candidatesData = await res.json();
        filterCandidates();
        document.getElementById('candidateSelect').innerHTML = '<option value="">-- Select Candidate --</option>' + candidatesData.map(c => `<option value="${c.id}">${escapeHtml(c.first_name + ' ' + c.last_name || 'Unknown')}</option>`).join('');
    }
    
    function filterCandidates() {
        const search = document.getElementById('searchInput').value.toLowerCase();
        const score = document.getElementById('scoreFilter').value;
        let filtered = candidatesData;
        if (search) filtered = filtered.filter(c => (c.first_name + ' ' + c.last_name).toLowerCase().includes(search));
        if (score !== 'all') {
            if (score === 'high') filtered = filtered.filter(c => (c.match_score || 0) >= 70);
            else if (score === 'medium') filtered = filtered.filter(c => (c.match_score || 0) >= 40 && (c.match_score || 0) < 70);
            else if (score === 'low') filtered = filtered.filter(c => (c.match_score || 0) < 40);
        }
        renderCandidates(filtered);
        document.getElementById('filterCount').innerHTML = `(${filtered.length})`;
    }
    
    function renderCandidates(candidates) {
        const container = document.getElementById('candidatesList');
        if (!candidates.length) { container.innerHTML = '<div class="card no-click">No candidates</div>'; return; }
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
    
    function clearFilters() {
        document.getElementById('searchInput').value = '';
        document.getElementById('scoreFilter').value = 'all';
        filterCandidates();
    }
    
    async function viewCandidate(id) {
        const c = candidatesData.find(c => c.id == id);
        if (!c) return;
        const name = (c.first_name + ' ' + c.last_name).trim();
        const workExp = JSON.parse(c.work_experience || '[]');
        const skills = JSON.parse(c.core_skills || '[]');
        const certs = JSON.parse(c.certifications || '[]');
        const docRes = await fetch(`/api/candidates/${id}/documents`);
        const docs = await docRes.json();
        const resumeDoc = docs.find(d => d.is_resume === 1);
        
        document.getElementById('modalBody').innerHTML = `
            <div style="text-align:right; margin-bottom:10px;">
                <button class="btn-primary" onclick="copyDetails()">Copy All</button>
            </div>
            <div class="detail-row"><div class="detail-label">Name:</div><div class="detail-value">${escapeHtml(name)}</div></div>
            <div class="detail-row"><div class="detail-label">Email:</div><div class="detail-value">${escapeHtml(c.email || 'N/A')}</div></div>
            <div class="detail-row"><div class="detail-label">Phone:</div><div class="detail-value">${escapeHtml(c.phone || 'N/A')}</div></div>
            <div class="detail-row"><div class="detail-label">Role:</div><div class="detail-value">${escapeHtml(c.current_role || 'N/A')}</div></div>
            <h4>Work Experience</h4>
            ${workExp.map(w => `<div><strong>${escapeHtml(w.company)}</strong> - ${escapeHtml(w.role)}</div>`).join('') || 'None'}
            <h4>Skills</h4>
            ${skills.map(s => `<span class="skill-tag">${escapeHtml(s.skill)} (${s.years_of_experience || 0}y)</span>`).join('') || 'None'}
            <h4>Certifications</h4>
            ${certs.map(c => `<div>📜 ${escapeHtml(c)}</div>`).join('') || 'None'}
            <h4>Resume</h4>
            ${resumeDoc ? `<a href="/api/documents/${resumeDoc.id}" target="_blank">${escapeHtml(resumeDoc.original_filename)}</a>` : 'None'}
            <button class="btn-primary" onclick="closeModal()" style="margin-top:10px;">Close</button>
        `;
        document.getElementById('candidateModal').style.display = 'block';
    }
    
    function copyDetails() {
        let text = '';
        document.querySelectorAll('#modalBody .detail-row, #modalBody h4').forEach(el => text += el.innerText + '\n');
        navigator.clipboard.writeText(text);
        alert('Copied!');
    }
    
    function closeModal() { document.getElementById('candidateModal').style.display = 'none'; }
    window.exportToCSV = () => window.location.href = '/api/export-candidates';
    
    // Upload Button
    document.getElementById('uploadBtn').onclick = async function() {
        const file = document.getElementById('resumeFile').files[0];
        if (!file) { alert('Select a file'); return; }
        const fd = new FormData(); fd.append('resume', file);
        const div = document.getElementById('uploadResult');
        div.innerHTML = '<div class="spinner"></div><p>Parsing...</p>';
        try {
            const res = await fetch('/api/parse-resume', { method: 'POST', body: fd });
            const result = await res.json();
            if (result.error) { div.innerHTML = `<div class="alert-error">${result.error}</div>`; return; }
            div.innerHTML = `<div class="alert-success"><h4>✅ Parsed</h4><p><strong>Name:</strong> ${escapeHtml(result.first_name || '')} ${escapeHtml(result.last_name || '')}</p><p><strong>Email:</strong> ${escapeHtml(result.email || '')}</p><p><strong>Phone:</strong> ${escapeHtml(result.phone || '')}</p><p><strong>Skills:</strong> ${result.core_skills ? result.core_skills.map(s => `<span class="skill-tag">${escapeHtml(s.skill)}</span>`).join('') : 'None'}</p><button class="btn-primary" id="saveBtn">Save</button></div>`;
            document.getElementById('saveBtn').onclick = async function() {
                const saveRes = await fetch('/api/candidates', { method: 'POST', headers: {'Content-Type':'application/json'}, body: JSON.stringify(result) });
                if (saveRes.ok) { alert('Saved!'); div.innerHTML = ''; document.getElementById('resumeFile').value = ''; loadCandidates(); showTab('candidates'); }
                else alert('Error');
            };
        } catch(e) { div.innerHTML = '<div class="alert-error">Error</div>'; }
    };
    
    // Multi Upload
    document.getElementById('multiUploadBtn').onclick = async function() {
        const files = document.getElementById('multiFiles').files;
        if (!files.length) { alert('Select files'); return; }
        const div = document.getElementById('multiResult');
        div.innerHTML = '<div class="spinner"></div><p>Processing...</p>';
        let success = 0, fail = 0;
        for (let i = 0; i < files.length; i++) {
            const fd = new FormData(); fd.append('resume', files[i]);
            div.innerHTML = `<div class="progress-bar"><div class="progress-fill" style="width:${Math.round((i/files.length)*100)}%"></div></div><p>${i+1}/${files.length}: ${escapeHtml(files[i].name)}</p>`;
            try {
                const res = await fetch('/api/parse-resume', { method: 'POST', body: fd });
                if (!res.error) {
                    const saveRes = await fetch('/api/candidates', { method: 'POST', headers: {'Content-Type':'application/json'}, body: JSON.stringify(await res.json()) });
                    if (saveRes.ok) success++;
                    else fail++;
                } else fail++;
            } catch(e) { fail++; }
        }
        div.innerHTML = `<div class="alert-success"><h4>Complete!</h4><p>Success: ${success} | Failed: ${fail}</p><button class="btn-primary" onclick="showTab('candidates')">View</button></div>`;
        document.getElementById('multiFiles').value = '';
        loadCandidates();
    };
    
    // Create Job
    document.getElementById('createJobBtn').onclick = async function() {
        const data = {
            title: document.getElementById('jobTitle').value,
            company: document.getElementById('jobCompany').value,
            description: document.getElementById('jobDesc').value
        };
        if (!data.title) { alert('Title required'); return; }
        const res = await fetch('/api/jobs', { method: 'POST', headers: {'Content-Type':'application/json'}, body: JSON.stringify(data) });
        if (res.ok) {
            alert('Job created!');
            document.getElementById('jobTitle').value = '';
            document.getElementById('jobCompany').value = '';
            document.getElementById('jobDesc').value = '';
            showTab('jobs');
            loadJobs();
        } else { alert('Error'); }
    };
    
    // Analyze
    document.getElementById('analyzeBtn').onclick = async function() {
        const jobId = document.getElementById('jobSelect').value;
        const candidateId = document.getElementById('candidateSelect').value;
        if (!jobId || !candidateId) { alert('Select both'); return; }
        const job = jobsData.find(j => j.id == jobId);
        const cand = candidatesData.find(c => c.id == candidateId);
        const div = document.getElementById('analyzeResult');
        div.innerHTML = '<div class="spinner"></div><p>Analyzing...</p>';
        try {
            const res = await fetch('/api/analyze-match', { method: 'POST', headers: {'Content-Type':'application/json'}, body: JSON.stringify({ job_id: jobId, candidate_id: candidateId, jd_text: job.description || '', resume_text: cand.resume_text || '' }) });
            const result = await res.json();
            if (result.error) { div.innerHTML = `<div class="alert-error">${result.error}</div>`; return; }
            const matchClass = result.match_score >= 70 ? 'match-high' : (result.match_score >= 40 ? 'match-medium' : 'match-low');
            div.innerHTML = `<div class="alert-success"><h4>Analysis</h4><p>Score: <span class="${matchClass}">${result.match_score || 0}%</span></p><p>${result.recommendation || 'Review'}</p><small>✅ Saved</small></div>`;
            loadCandidates();
        } catch(e) { div.innerHTML = '<div class="alert-error">Failed</div>'; }
    };
    
    function escapeHtml(str) { if (!str) return ''; return str.replace(/[&<>]/g, function(m) { if (m === '&') return '&amp;'; if (m === '<') return '&lt;'; if (m === '>') return '&gt;'; return m; }); }
    
    loadJobs(); loadCandidates();
</script>
</body>
</html>
'''

@app.route('/')
def index():
    return HTML_TEMPLATE

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
