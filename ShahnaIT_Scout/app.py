# app.py - ULTRA SIMPLE WORKING VERSION
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

init_db()
os.makedirs('/tmp/candidate_docs', exist_ok=True)

app.register_blueprint(candidates_bp, url_prefix='/api')
app.register_blueprint(jobs_bp, url_prefix='/api')
app.register_blueprint(analyze_bp, url_prefix='/api')
app.register_blueprint(export_bp, url_prefix='/api')
app.register_blueprint(documents_bp, url_prefix='/api')

HTML_TEMPLATE = '''
<!DOCTYPE html>
<html>
<head>
    <title>ShahnaIT Scout</title>
    <style>
        body { font-family: Arial; background: #F5F0E8; margin: 0; padding: 20px; }
        .header { background: #1A4D4A; color: white; padding: 20px; border-radius: 10px; margin-bottom: 20px; }
        button { background: #1A4D4A; color: white; border: none; padding: 10px 20px; margin: 5px; cursor: pointer; border-radius: 8px; }
        .card { background: white; padding: 15px; margin: 10px 0; border-radius: 8px; border-left: 4px solid #1A4D4A; }
        input, select, textarea { width: 100%; padding: 8px; margin: 5px 0; border: 1px solid #ccc; border-radius: 5px; }
        .skill-tag { background: #F5F0E8; padding: 3px 8px; border-radius: 15px; display: inline-block; margin: 2px; }
        .match-high { background: #1B6B2E; color: white; padding: 2px 8px; border-radius: 15px; display: inline-block; }
        .match-medium { background: #CC5500; color: white; padding: 2px 8px; border-radius: 15px; display: inline-block; }
        .match-low { background: #B22222; color: white; padding: 2px 8px; border-radius: 15px; display: inline-block; }
        .alert-success { background: #1B6B2E; color: white; padding: 10px; border-radius: 8px; margin: 10px 0; }
        .spinner { border: 3px solid #f3f3f3; border-top: 3px solid #1A4D4A; border-radius: 50%; width: 30px; height: 30px; animation: spin 1s linear infinite; margin: 10px auto; }
        @keyframes spin { 0% { transform: rotate(0deg); } 100% { transform: rotate(360deg); } }
        .flex { display: flex; gap: 10px; }
        .flex-1 { flex: 1; }
        .tab-btn { background: white; border: none; padding: 10px 20px; margin: 5px; cursor: pointer; border-radius: 8px; }
        .tab-btn.active { background: #1A4D4A; color: white; }
        .filter-bar { background: white; padding: 10px; border-radius: 8px; margin-bottom: 15px; display: flex; gap: 10px; flex-wrap: wrap; }
    </style>
</head>
<body>
<div style="max-width: 1000px; margin: 0 auto;">
    <div class="header">
        <h1>🎯 ShahnaIT Scout</h1>
        <p>AI-Powered Recruitment Platform</p>
    </div>
    
    <div>
        <button class="tab-btn active" id="tab1">📋 Jobs</button>
        <button class="tab-btn" id="tab2">👥 Candidates</button>
        <button class="tab-btn" id="tab3">📄 Upload Resume</button>
        <button class="tab-btn" id="tab4">➕ Create Job</button>
        <button class="tab-btn" id="tab5">🔍 Analyze Match</button>
    </div>
    
    <div id="panel1"><div id="jobsList"></div></div>
    <div id="panel2" style="display:none;">
        <button id="exportBtn">Export CSV</button>
        <div class="filter-bar">
            <input type="text" id="searchBox" placeholder="Search...">
            <select id="scoreSelect">
                <option value="all">All Scores</option>
                <option value="high">High (70%+)</option>
                <option value="medium">Medium (40-69%)</option>
                <option value="low">Low (<40%)</option>
            </select>
            <button id="clearBtn">Clear</button>
        </div>
        <div id="candidatesList"></div>
    </div>
    <div id="panel3" style="display:none;">
        <div class="card">
            <h3>Upload Resume</h3>
            <input type="file" id="resumeFile" accept=".pdf,.docx">
            <button id="parseBtn">Parse & Save</button>
            <div id="parseResult"></div>
        </div>
    </div>
    <div id="panel4" style="display:none;">
        <div class="card">
            <h3>Create Job</h3>
            <input type="text" id="jobTitle" placeholder="Job Title">
            <input type="text" id="jobCompany" placeholder="Company">
            <textarea id="jobDesc" rows="3" placeholder="Description"></textarea>
            <button id="createJobBtn">Create</button>
        </div>
    </div>
    <div id="panel5" style="display:none;">
        <div class="card">
            <h3>AI Match Analysis</h3>
            <div class="flex">
                <div class="flex-1"><select id="jobSelect"></select></div>
                <div class="flex-1"><select id="candidateSelect"></select></div>
            </div>
            <button id="analyzeBtn">Run Analysis</button>
            <div id="analysisResult"></div>
        </div>
    </div>
</div>

<script>
    let allJobs = [], allCandidates = [];
    
    // Tab switching
    document.getElementById('tab1').onclick = function() { showPanel(1); loadJobs(); };
    document.getElementById('tab2').onclick = function() { showPanel(2); loadCandidates(); };
    document.getElementById('tab3').onclick = function() { showPanel(3); };
    document.getElementById('tab4').onclick = function() { showPanel(4); };
    document.getElementById('tab5').onclick = function() { showPanel(5); loadJobs(); loadCandidates(); };
    
    function showPanel(num) {
        for(let i=1; i<=5; i++) {
            document.getElementById('panel'+i).style.display = 'none';
            document.getElementById('tab'+i).classList.remove('active');
        }
        document.getElementById('panel'+num).style.display = 'block';
        document.getElementById('tab'+num).classList.add('active');
    }
    
    async function loadJobs() {
        const res = await fetch('/api/jobs');
        allJobs = await res.json();
        const container = document.getElementById('jobsList');
        if(!allJobs.length) { container.innerHTML = '<div class="card">No jobs yet</div>'; return; }
        container.innerHTML = allJobs.map(j => `<div class="card"><h3>${escapeHtml(j.title)}</h3><small>${new Date(j.created_at).toLocaleDateString()}</small></div>`).join('');
        document.getElementById('jobSelect').innerHTML = '<option value="">-- Select Job --</option>' + allJobs.map(j => `<option value="${j.id}">${escapeHtml(j.title)}</option>`).join('');
    }
    
    async function loadCandidates() {
        const res = await fetch('/api/candidates');
        allCandidates = await res.json();
        filterCandidates();
        document.getElementById('candidateSelect').innerHTML = '<option value="">-- Select Candidate --</option>' + allCandidates.map(c => `<option value="${c.id}">${escapeHtml(c.first_name + ' ' + c.last_name || 'Unknown')}</option>`).join('');
    }
    
    function filterCandidates() {
        const search = document.getElementById('searchBox').value.toLowerCase();
        const score = document.getElementById('scoreSelect').value;
        let filtered = allCandidates;
        if(search) filtered = filtered.filter(c => (c.first_name + ' ' + c.last_name).toLowerCase().includes(search));
        if(score === 'high') filtered = filtered.filter(c => (c.match_score || 0) >= 70);
        else if(score === 'medium') filtered = filtered.filter(c => (c.match_score || 0) >= 40 && (c.match_score || 0) < 70);
        else if(score === 'low') filtered = filtered.filter(c => (c.match_score || 0) < 40);
        renderCandidates(filtered);
    }
    
    function renderCandidates(candidates) {
        const container = document.getElementById('candidatesList');
        if(!candidates.length) { container.innerHTML = '<div class="card">No candidates</div>'; return; }
        container.innerHTML = candidates.map(c => {
            const name = (c.first_name + ' ' + c.last_name).trim() || 'Unknown';
            const skills = c.core_skills ? JSON.parse(c.core_skills) : [];
            const matchClass = c.match_score >= 70 ? 'match-high' : (c.match_score >= 40 ? 'match-medium' : 'match-low');
            return `<div class="card"><h3>${escapeHtml(name)}</h3><p>${skills.slice(0,3).map(s => `<span class="skill-tag">${escapeHtml(s.skill)}</span>`).join('')}</p>${c.match_score ? `<p>Score: <span class="${matchClass}">${c.match_score}%</span></p>` : ''}<small>${new Date(c.created_at).toLocaleDateString()}</small></div>`;
        }).join('');
    }
    
    document.getElementById('searchBox').onkeyup = filterCandidates;
    document.getElementById('scoreSelect').onchange = filterCandidates;
    document.getElementById('clearBtn').onclick = function() {
        document.getElementById('searchBox').value = '';
        document.getElementById('scoreSelect').value = 'all';
        filterCandidates();
    };
    
    document.getElementById('exportBtn').onclick = () => window.location.href = '/api/export-candidates';
    
    document.getElementById('parseBtn').onclick = async function() {
        const file = document.getElementById('resumeFile').files[0];
        if(!file) { alert('Select file'); return; }
        const fd = new FormData(); fd.append('resume', file);
        const div = document.getElementById('parseResult');
        div.innerHTML = '<div class="spinner"></div><p>Parsing...</p>';
        try {
            const res = await fetch('/api/parse-resume', { method: 'POST', body: fd });
            const result = await res.json();
            if(result.error) { div.innerHTML = `<div class="alert-success" style="background:#B22222">${result.error}</div>`; return; }
            div.innerHTML = `<div class="alert-success"><h4>✅ Parsed</h4><p><strong>Name:</strong> ${escapeHtml(result.first_name || '')} ${escapeHtml(result.last_name || '')}</p><p><strong>Skills:</strong> ${result.core_skills ? result.core_skills.map(s => `<span class="skill-tag">${escapeHtml(s.skill)}</span>`).join('') : 'None'}</p><button id="saveBtn">💾 Save</button></div>`;
            document.getElementById('saveBtn').onclick = async function() {
                const saveRes = await fetch('/api/candidates', { method: 'POST', headers: {'Content-Type':'application/json'}, body: JSON.stringify(result) });
                if(saveRes.ok) { alert('Saved!'); div.innerHTML = ''; document.getElementById('resumeFile').value = ''; loadCandidates(); showPanel(2); }
                else alert('Error');
            };
        } catch(e) { div.innerHTML = '<div class="alert-success" style="background:#B22222">Error</div>'; }
    };
    
    document.getElementById('createJobBtn').onclick = async function() {
        const data = {
            title: document.getElementById('jobTitle').value,
            company: document.getElementById('jobCompany').value,
            description: document.getElementById('jobDesc').value
        };
        if(!data.title) { alert('Title required'); return; }
        const res = await fetch('/api/jobs', { method: 'POST', headers: {'Content-Type':'application/json'}, body: JSON.stringify(data) });
        if(res.ok) {
            alert('Job created!');
            document.getElementById('jobTitle').value = '';
            document.getElementById('jobCompany').value = '';
            document.getElementById('jobDesc').value = '';
            showPanel(1);
            loadJobs();
        } else { alert('Error'); }
    };
    
    document.getElementById('analyzeBtn').onclick = async function() {
        const jobId = document.getElementById('jobSelect').value;
        const candidateId = document.getElementById('candidateSelect').value;
        if(!jobId || !candidateId) { alert('Select both'); return; }
        const job = allJobs.find(j => j.id == jobId);
        const cand = allCandidates.find(c => c.id == candidateId);
        const div = document.getElementById('analysisResult');
        div.innerHTML = '<div class="spinner"></div><p>Analyzing...</p>';
        try {
            const res = await fetch('/api/analyze-match', { method: 'POST', headers: {'Content-Type':'application/json'}, body: JSON.stringify({ job_id: jobId, candidate_id: candidateId, jd_text: job.description || '', resume_text: cand.resume_text || '' }) });
            const result = await res.json();
            if(result.error) { div.innerHTML = `<div class="alert-success" style="background:#B22222">${result.error}</div>`; return; }
            const matchClass = result.match_score >= 70 ? 'match-high' : (result.match_score >= 40 ? 'match-medium' : 'match-low');
            div.innerHTML = `<div class="alert-success"><h4>Analysis Complete</h4><p>Score: <span class="${matchClass}">${result.match_score || 0}%</span></p><p>${result.recommendation || 'Review'}</p><small>✅ Saved</small></div>`;
            loadCandidates();
        } catch(e) { div.innerHTML = '<div class="alert-success" style="background:#B22222">Failed</div>'; }
    };
    
    function escapeHtml(str) { if(!str) return ''; return str.replace(/[&<>]/g, function(m) { if(m==='&') return '&amp;'; if(m==='<') return '&lt;'; if(m==='>') return '&gt;'; return m; }); }
    
    showPanel(1);
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
