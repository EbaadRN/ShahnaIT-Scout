# app.py - WITH BULK RESUME UPLOAD ONLY (No other changes)
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
        
        button, .btn {
            background: #1A4D4A;
            color: white;
            border: none;
            padding: 10px 20px;
            margin: 5px;
            cursor: pointer;
            border-radius: 8px;
            font-size: 14px;
        }
        button:hover, .btn:hover {
            background: #2A6B67;
        }
        
        .tab-btn {
            background: white;
            color: #1A4D4A;
            border: 1px solid #1A4D4A;
            padding: 10px 20px;
            margin: 5px;
            cursor: pointer;
            border-radius: 8px;
        }
        .tab-btn:hover {
            background: #1A4D4A;
            color: white;
        }
        .tab-btn.active {
            background: #1A4D4A;
            color: white;
        }
        
        .card { background: white; padding: 15px; margin: 10px 0; border-radius: 8px; border-left: 4px solid #1A4D4A; }
        input, select, textarea { width: 100%; padding: 8px; margin: 5px 0; border: 1px solid #ccc; border-radius: 5px; }
        .skill-tag { background: #F5F0E8; padding: 3px 8px; border-radius: 15px; display: inline-block; margin: 2px; }
        .match-high { background: #1B6B2E; color: white; padding: 2px 8px; border-radius: 15px; display: inline-block; }
        .match-medium { background: #CC5500; color: white; padding: 2px 8px; border-radius: 15px; display: inline-block; }
        .match-low { background: #B22222; color: white; padding: 2px 8px; border-radius: 15px; display: inline-block; }
        .alert-success { background: #1B6B2E; color: white; padding: 10px; border-radius: 8px; margin: 10px 0; }
        .alert-error { background: #B22222; color: white; padding: 10px; border-radius: 8px; margin: 10px 0; }
        .spinner { border: 3px solid #f3f3f3; border-top: 3px solid #1A4D4A; border-radius: 50%; width: 30px; height: 30px; animation: spin 1s linear infinite; margin: 10px auto; }
        @keyframes spin { 0% { transform: rotate(0deg); } 100% { transform: rotate(360deg); } }
        .flex { display: flex; gap: 10px; }
        .flex-1 { flex: 1; }
        .filter-bar { background: white; padding: 10px; border-radius: 8px; margin-bottom: 15px; display: flex; gap: 10px; flex-wrap: wrap; }
        
        /* Bulk upload styles */
        .file-list { background: #F9F6F0; border-radius: 8px; padding: 10px; margin-top: 10px; max-height: 150px; overflow-y: auto; }
        .file-list-item { padding: 5px; border-bottom: 1px solid #ddd; font-size: 12px; display: flex; justify-content: space-between; }
        .remove-file { color: #B22222; cursor: pointer; margin-left: 10px; }
        .progress-bar { background: #ddd; border-radius: 10px; height: 15px; margin: 10px 0; overflow: hidden; }
        .progress-fill { background: #1B6B2E; width: 0%; height: 100%; transition: width 0.3s; }
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
        <button id="exportBtn">📥 Export CSV</button>
        <div class="filter-bar">
            <input type="text" id="searchBox" placeholder="Search by name...">
            <select id="scoreSelect">
                <option value="all">All Scores</option>
                <option value="high">High (70%+)</option>
                <option value="medium">Medium (40-69%)</option>
                <option value="low">Low (<40%)</option>
            </select>
            <button id="clearBtn">Clear Filters</button>
        </div>
        <div id="candidatesList"></div>
    </div>
    
    <div id="panel3" style="display:none;">
        <div class="card">
            <h3>📄 Single Resume Upload</h3>
            <p>AI will auto-fill candidate details</p>
            <input type="file" id="resumeFile" accept=".pdf,.docx">
            <button id="parseBtn">🔍 Parse & Save Candidate</button>
            <div id="parseResult"></div>
        </div>
        
        <!-- NEW: Bulk Resume Upload Section -->
        <div class="card" style="margin-top: 20px;">
            <h3>📚 Bulk Resume Upload (Select Multiple Files)</h3>
            <p>Hold Ctrl (or Cmd on Mac) to select multiple PDF/DOCX files at once</p>
            <input type="file" id="multiResumeFiles" multiple accept=".pdf,.docx">
            <div id="selectedFilesList" class="file-list" style="display:none;"></div>
            <button id="bulkUploadBtn">🚀 Upload & Parse All Selected Files</button>
            <div id="bulkUploadResult"></div>
        </div>
    </div>
    
    <div id="panel4" style="display:none;">
        <div class="card">
            <h3>➕ Create New Job</h3>
            <input type="text" id="jobTitle" placeholder="Job Title *">
            <input type="text" id="jobCompany" placeholder="Company Name">
            <textarea id="jobDesc" rows="4" placeholder="Job Description"></textarea>
            <button id="createJobBtn">Create Job</button>
        </div>
    </div>
    
    <div id="panel5" style="display:none;">
        <div class="card">
            <h3>🔍 AI Match Analysis</h3>
            <div class="flex">
                <div class="flex-1"><select id="jobSelect"><option value="">-- Select Job --</option></select></div>
                <div class="flex-1"><select id="candidateSelect"><option value="">-- Select Candidate --</option></select></div>
            </div>
            <button id="analyzeBtn">🤖 Run AI Analysis</button>
            <div id="analysisResult"></div>
        </div>
    </div>
</div>

<script>
    let allJobs = [], allCandidates = [];
    let selectedBulkFiles = [];
    
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
    
    // ========== BULK UPLOAD FUNCTIONS ==========
    document.getElementById('multiResumeFiles').addEventListener('change', function(e) {
        selectedBulkFiles = Array.from(e.target.files);
        const fileListDiv = document.getElementById('selectedFilesList');
        if (selectedBulkFiles.length > 0) {
            let html = '<strong>Selected files (' + selectedBulkFiles.length + '):</strong><br>';
            selectedBulkFiles.forEach((file, index) => {
                html += `<div class="file-list-item">
                    📄 ${escapeHtml(file.name)} (${(file.size / 1024).toFixed(1)} KB)
                    <span class="remove-file" onclick="removeBulkFile(${index})">✕ Remove</span>
                </div>`;
            });
            fileListDiv.innerHTML = html;
            fileListDiv.style.display = 'block';
        } else {
            fileListDiv.style.display = 'none';
        }
    });
    
    function removeBulkFile(index) {
        selectedBulkFiles.splice(index, 1);
        const dataTransfer = new DataTransfer();
        selectedBulkFiles.forEach(file => dataTransfer.items.add(file));
        document.getElementById('multiResumeFiles').files = dataTransfer.files;
        
        const fileListDiv = document.getElementById('selectedFilesList');
        if (selectedBulkFiles.length > 0) {
            let html = '<strong>Selected files (' + selectedBulkFiles.length + '):</strong><br>';
            selectedBulkFiles.forEach((file, idx) => {
                html += `<div class="file-list-item">
                    📄 ${escapeHtml(file.name)} (${(file.size / 1024).toFixed(1)} KB)
                    <span class="remove-file" onclick="removeBulkFile(${idx})">✕ Remove</span>
                </div>`;
            });
            fileListDiv.innerHTML = html;
            fileListDiv.style.display = 'block';
        } else {
            fileListDiv.style.display = 'none';
        }
    }
    
    document.getElementById('bulkUploadBtn').onclick = async function() {
        if (selectedBulkFiles.length === 0) { alert('Please select files first'); return; }
        
        const div = document.getElementById('bulkUploadResult');
        div.innerHTML = '<div class="spinner"></div><p>📚 Processing ' + selectedBulkFiles.length + ' files...</p>';
        
        let successCount = 0;
        let failCount = 0;
        let errors = [];
        
        for (let i = 0; i < selectedBulkFiles.length; i++) {
            const file = selectedBulkFiles[i];
            const fd = new FormData();
            fd.append('resume', file);
            
            const percent = Math.round((i / selectedBulkFiles.length) * 100);
            div.innerHTML = `<div class="progress-bar"><div class="progress-fill" style="width: ${percent}%"></div></div><p>📄 Processing ${i+1} of ${selectedBulkFiles.length}: ${escapeHtml(file.name)}...</p>`;
            
            try {
                const res = await fetch('/api/parse-resume', { method: 'POST', body: fd });
                const result = await res.json();
                
                if (result.error) {
                    failCount++;
                    errors.push(`${file.name}: ${result.error}`);
                } else {
                    const saveRes = await fetch('/api/candidates', { method: 'POST', headers: {'Content-Type':'application/json'}, body: JSON.stringify(result) });
                    if (saveRes.ok) {
                        successCount++;
                    } else {
                        failCount++;
                        errors.push(`${file.name}: Save failed`);
                    }
                }
            } catch(e) {
                failCount++;
                errors.push(`${file.name}: ${e.message}`);
            }
        }
        
        let resultHtml = `<div class="alert-success"><h4>✅ Bulk Upload Complete!</h4>`;
        resultHtml += `<p><strong>Total files:</strong> ${selectedBulkFiles.length}</p>`;
        resultHtml += `<p><strong>Successfully parsed & saved:</strong> ${successCount}</p>`;
        resultHtml += `<p><strong>Failed:</strong> ${failCount}</p>`;
        
        if (errors.length > 0) {
            resultHtml += `<div style="margin-top: 10px;"><strong>⚠️ Errors:</strong><ul>`;
            errors.forEach(err => {
                resultHtml += `<li>${escapeHtml(err)}</li>`;
            });
            resultHtml += `</ul></div>`;
        }
        
        resultHtml += `<button class="btn" onclick="document.getElementById('tab2').click()" style="margin-top: 15px;">View All Candidates</button></div>`;
        div.innerHTML = resultHtml;
        
        // Clear selection
        selectedBulkFiles = [];
        document.getElementById('multiResumeFiles').value = '';
        document.getElementById('selectedFilesList').style.display = 'none';
        
        loadCandidates();
    };
    
    async function loadJobs() {
        const res = await fetch('/api/jobs');
        allJobs = await res.json();
        const container = document.getElementById('jobsList');
        if(!allJobs.length) { container.innerHTML = '<div class="card">No jobs yet. Create one.</div>'; return; }
        container.innerHTML = allJobs.map(j => `<div class="card"><h3>${escapeHtml(j.title)}</h3>${j.company ? `<p>🏢 ${escapeHtml(j.company)}</p>` : ''}<small>${new Date(j.created_at).toLocaleDateString()}</small></div>`).join('');
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
        if(!candidates.length) { container.innerHTML = '<div class="card">No candidates yet. Upload resumes.</div>'; return; }
        container.innerHTML = candidates.map(c => {
            const name = (c.first_name + ' ' + c.last_name).trim() || 'Unknown';
            const skills = c.core_skills ? JSON.parse(c.core_skills) : [];
            const matchClass = c.match_score >= 70 ? 'match-high' : (c.match_score >= 40 ? 'match-medium' : 'match-low');
            return `<div class="card">
                <h3>👤 ${escapeHtml(name)}</h3>
                ${c.email ? `<p>📧 ${escapeHtml(c.email)}</p>` : ''}
                <p>🔧 ${skills.slice(0,3).map(s => `<span class="skill-tag">${escapeHtml(s.skill)}</span>`).join('')}</p>
                ${c.match_score ? `<p>🎯 Score: <span class="${matchClass}">${c.match_score}%</span></p>` : ''}
                <small>📅 ${new Date(c.created_at).toLocaleDateString()}</small>
            </div>`;
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
        if(!file) { alert('Please select a file'); return; }
        const fd = new FormData(); fd.append('resume', file);
        const div = document.getElementById('parseResult');
        div.innerHTML = '<div class="spinner"></div><p>🤖 AI parsing resume...</p>';
        try {
            const res = await fetch('/api/parse-resume', { method: 'POST', body: fd });
            const result = await res.json();
            if(result.error) { div.innerHTML = `<div class="alert-error">${result.error}</div>`; return; }
            div.innerHTML = `<div class="alert-success"><h4>✅ Resume Parsed Successfully</h4>
                <p><strong>Name:</strong> ${escapeHtml(result.first_name || '')} ${escapeHtml(result.last_name || '')}</p>
                <p><strong>Email:</strong> ${escapeHtml(result.email || '')}</p>
                <p><strong>Phone:</strong> ${escapeHtml(result.phone || '')}</p>
                <p><strong>Skills:</strong> ${result.core_skills ? result.core_skills.map(s => `<span class="skill-tag">${escapeHtml(s.skill)}</span>`).join('') : 'None'}</p>
                <button id="saveBtn">💾 Save Candidate</button></div>`;
            document.getElementById('saveBtn').onclick = async function() {
                const saveRes = await fetch('/api/candidates', { method: 'POST', headers: {'Content-Type':'application/json'}, body: JSON.stringify(result) });
                if(saveRes.ok) { alert('Candidate saved successfully!'); div.innerHTML = ''; document.getElementById('resumeFile').value = ''; loadCandidates(); showPanel(2); }
                else alert('Error saving candidate');
            };
        } catch(e) { div.innerHTML = '<div class="alert-error">Error parsing resume</div>'; }
    };
    
    document.getElementById('createJobBtn').onclick = async function() {
        const data = {
            title: document.getElementById('jobTitle').value,
            company: document.getElementById('jobCompany').value,
            description: document.getElementById('jobDesc').value
        };
        if(!data.title) { alert('Job title required'); return; }
        const btn = this;
        btn.disabled = true;
        btn.textContent = 'Creating...';
        try {
            const res = await fetch('/api/jobs', { method: 'POST', headers: {'Content-Type':'application/json'}, body: JSON.stringify(data) });
            if(res.ok) {
                alert('Job created successfully!');
                document.getElementById('jobTitle').value = '';
                document.getElementById('jobCompany').value = '';
                document.getElementById('jobDesc').value = '';
                showPanel(1);
                loadJobs();
            } else { alert('Error creating job'); }
        } catch(e) { alert('Error creating job'); }
        finally { btn.disabled = false; btn.textContent = 'Create Job'; }
    };
    
    document.getElementById('analyzeBtn').onclick = async function() {
        const jobId = document.getElementById('jobSelect').value;
        const candidateId = document.getElementById('candidateSelect').value;
        if(!jobId || !candidateId) { alert('Please select both a Job and a Candidate'); return; }
        const job = allJobs.find(j => j.id == jobId);
        const cand = allCandidates.find(c => c.id == candidateId);
        const div = document.getElementById('analysisResult');
        div.innerHTML = '<div class="spinner"></div><p>🤖 AI analyzing match...</p>';
        try {
            const res = await fetch('/api/analyze-match', { method: 'POST', headers: {'Content-Type':'application/json'}, body: JSON.stringify({ job_id: jobId, candidate_id: candidateId, jd_text: job.description || '', resume_text: cand.resume_text || '' }) });
            const result = await res.json();
            if(result.error) { div.innerHTML = `<div class="alert-error">${result.error}</div>`; return; }
            const matchClass = result.match_score >= 70 ? 'match-high' : (result.match_score >= 40 ? 'match-medium' : 'match-low');
            div.innerHTML = `<div class="alert-success"><h4>📊 Analysis Complete</h4>
                <p><strong>🎯 Match Score:</strong> <span class="${matchClass}">${result.match_score || 0}%</span></p>
                <p><strong>📌 Recommendation:</strong> ${result.recommendation || 'Review'}</p>
                <small>✅ Analysis saved to candidate record</small></div>`;
            loadCandidates();
        } catch(e) { div.innerHTML = '<div class="alert-error">Analysis failed</div>'; }
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
