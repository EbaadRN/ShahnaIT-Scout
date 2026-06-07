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

# SIMPLE HTML - WILL DEFINITELY WORK
HTML_TEMPLATE = '''
<!DOCTYPE html>
<html>
<head>
    <title>ShahnaIT Scout</title>
    <style>
        body { font-family: Arial; background: #F5F0E8; margin: 0; padding: 20px; }
        .header { background: #1A4D4A; color: white; padding: 20px; border-radius: 10px; margin-bottom: 20px; }
        .tab-btn { background: white; border: none; padding: 10px 20px; margin: 5px; cursor: pointer; border-radius: 8px; }
        .tab-btn.active { background: #1A4D4A; color: white; }
        .card { background: white; padding: 15px; margin: 10px 0; border-radius: 8px; border-left: 4px solid #1A4D4A; cursor: pointer; }
        .btn { background: #1A4D4A; color: white; border: none; padding: 8px 20px; margin: 5px; cursor: pointer; border-radius: 20px; }
        input, select, textarea { width: 100%; padding: 8px; margin: 5px 0; border: 1px solid #ccc; border-radius: 5px; }
        .skill-tag { background: #F5F0E8; padding: 3px 8px; border-radius: 15px; display: inline-block; margin: 2px; font-size: 12px; }
        .match-high { background: #1B6B2E; color: white; padding: 2px 8px; border-radius: 15px; display: inline-block; }
        .match-medium { background: #CC5500; color: white; padding: 2px 8px; border-radius: 15px; display: inline-block; }
        .match-low { background: #B22222; color: white; padding: 2px 8px; border-radius: 15px; display: inline-block; }
        .alert-success { background: #1B6B2E; color: white; padding: 10px; border-radius: 8px; margin: 10px 0; }
        .alert-error { background: #B22222; color: white; padding: 10px; border-radius: 8px; margin: 10px 0; }
        .spinner { border: 3px solid #f3f3f3; border-top: 3px solid #1A4D4A; border-radius: 50%; width: 30px; height: 30px; animation: spin 1s linear infinite; margin: 10px auto; }
        @keyframes spin { 0% { transform: rotate(0deg); } 100% { transform: rotate(360deg); } }
        .modal { display: none; position: fixed; z-index: 1000; left: 0; top: 0; width: 100%; height: 100%; background: rgba(0,0,0,0.5); }
        .modal-content { background: #F5F0E8; margin: 50px auto; border-radius: 10px; max-width: 600px; width: 90%; }
        .modal-header { background: #1A4D4A; color: white; padding: 10px; border-radius: 10px 10px 0 0; display: flex; justify-content: space-between; }
        .modal-body { padding: 15px; max-height: 60vh; overflow-y: auto; }
        .close { cursor: pointer; }
        .detail-row { margin-bottom: 8px; display: flex; }
        .detail-label { width: 120px; font-weight: bold; }
        .filter-bar { background: white; padding: 10px; border-radius: 8px; margin-bottom: 15px; display: flex; gap: 10px; flex-wrap: wrap; }
        .flex { display: flex; gap: 10px; }
        .flex-1 { flex: 1; }
        @media (max-width: 600px) { body { padding: 10px; } .filter-bar input, .filter-bar select { width: 100%; } }
    </style>
</head>
<body>

<div style="max-width: 1000px; margin: 0 auto;">
    <div class="header">
        <h1>🎯 ShahnaIT Scout</h1>
        <p>AI-Powered Recruitment Platform</p>
    </div>
    
    <div>
        <button class="tab-btn active" id="tabJobs">📋 Jobs</button>
        <button class="tab-btn" id="tabCandidates">👥 Candidates</button>
        <button class="tab-btn" id="tabUpload">📄 Upload Resume</button>
        <button class="tab-btn" id="tabCreateJob">➕ Create Job</button>
        <button class="tab-btn" id="tabAnalyze">🔍 Analyze Match</button>
    </div>
    
    <!-- Jobs Panel -->
    <div id="jobsPanel" style="margin-top: 20px;">
        <div id="jobsList"></div>
    </div>
    
    <!-- Candidates Panel -->
    <div id="candidatesPanel" style="display:none; margin-top: 20px;">
        <div style="display: flex; justify-content: space-between;">
            <h3>Candidates <span id="candidateCount"></span></h3>
            <button class="btn" id="exportBtn">Export CSV</button>
        </div>
        <div class="filter-bar">
            <input type="text" id="searchBox" placeholder="Search by name...">
            <select id="scoreFilterSelect">
                <option value="all">All Scores</option>
                <option value="high">High (70%+)</option>
                <option value="medium">Medium (40-69%)</option>
                <option value="low">Low (<40%)</option>
            </select>
            <button class="btn" id="clearFilterBtn">Clear</button>
        </div>
        <div id="candidatesList"></div>
    </div>
    
    <!-- Upload Panel -->
    <div id="uploadPanel" style="display:none; margin-top: 20px;">
        <div class="card">
            <h3>Upload Resume (PDF/DOCX)</h3>
            <input type="file" id="resumeFile">
            <button class="btn" id="parseResumeButton">Parse & Save</button>
            <div id="parseResultDiv"></div>
        </div>
    </div>
    
    <!-- Create Job Panel -->
    <div id="createJobPanel" style="display:none; margin-top: 20px;">
        <div class="card">
            <h3>Create Job</h3>
            <input type="text" id="jobTitleField" placeholder="Job Title *">
            <input type="text" id="jobCompanyField" placeholder="Company">
            <textarea id="jobDescField" rows="4" placeholder="Job Description"></textarea>
            <button class="btn" id="createJobButton">Create Job</button>
        </div>
    </div>
    
    <!-- Analyze Panel -->
    <div id="analyzePanel" style="display:none; margin-top: 20px;">
        <div class="card">
            <h3>AI Match Analysis</h3>
            <div class="flex">
                <div class="flex-1"><select id="jobSelectBox"><option>-- Select Job --</option></select></div>
                <div class="flex-1"><select id="candidateSelectBox"><option>-- Select Candidate --</option></select></div>
            </div>
            <button class="btn" id="runAnalysisButton">Run Analysis</button>
            <div id="analysisResultDiv"></div>
        </div>
    </div>
</div>

<!-- Candidate Modal -->
<div id="candidateModal" class="modal">
    <div class="modal-content">
        <div class="modal-header"><h3>Candidate Profile</h3><span class="close" onclick="closeModal()">&times;</span></div>
        <div class="modal-body" id="candidateModalBody"></div>
    </div>
</div>

<!-- Edit Modal -->
<div id="editModal" class="modal">
    <div class="modal-content">
        <div class="modal-header"><h3>Edit Candidate</h3><span class="close" onclick="closeEditModal()">&times;</span></div>
        <div class="modal-body" id="editModalBody"></div>
    </div>
</div>

<script>
    let allJobs = [];
    let allCandidates = [];
    
    // ===== TAB SWITCHING =====
    document.getElementById('tabJobs').onclick = function() { showPanel('jobs'); loadJobs(); };
    document.getElementById('tabCandidates').onclick = function() { showPanel('candidates'); loadCandidates(); };
    document.getElementById('tabUpload').onclick = function() { showPanel('upload'); };
    document.getElementById('tabCreateJob').onclick = function() { showPanel('createJob'); };
    document.getElementById('tabAnalyze').onclick = function() { showPanel('analyze'); loadJobs(); loadCandidates(); };
    
    function showPanel(panel) {
        document.getElementById('jobsPanel').style.display = 'none';
        document.getElementById('candidatesPanel').style.display = 'none';
        document.getElementById('uploadPanel').style.display = 'none';
        document.getElementById('createJobPanel').style.display = 'none';
        document.getElementById('analyzePanel').style.display = 'none';
        document.getElementById(panel + 'Panel').style.display = 'block';
        
        document.querySelectorAll('.tab-btn').forEach(btn => btn.classList.remove('active'));
        if (panel === 'jobs') document.getElementById('tabJobs').classList.add('active');
        if (panel === 'candidates') document.getElementById('tabCandidates').classList.add('active');
        if (panel === 'upload') document.getElementById('tabUpload').classList.add('active');
        if (panel === 'createJob') document.getElementById('tabCreateJob').classList.add('active');
        if (panel === 'analyze') document.getElementById('tabAnalyze').classList.add('active');
    }
    
    // ===== LOAD JOBS =====
    async function loadJobs() {
        const res = await fetch('/api/jobs');
        allJobs = await res.json();
        const container = document.getElementById('jobsList');
        if (!allJobs.length) { container.innerHTML = '<div class="card">No jobs yet. Create one.</div>'; return; }
        container.innerHTML = allJobs.map(j => `<div class="card"><h3>${escapeHtml(j.title)}</h3>${j.company ? `<p>${escapeHtml(j.company)}</p>` : ''}<small>${new Date(j.created_at).toLocaleDateString()}</small></div>`).join('');
        document.getElementById('jobSelectBox').innerHTML = '<option value="">-- Select Job --</option>' + allJobs.map(j => `<option value="${j.id}">${escapeHtml(j.title)}</option>`).join('');
    }
    
    // ===== LOAD CANDIDATES =====
    async function loadCandidates() {
        const res = await fetch('/api/candidates');
        allCandidates = await res.json();
        filterCandidates();
        document.getElementById('candidateSelectBox').innerHTML = '<option value="">-- Select Candidate --</option>' + allCandidates.map(c => `<option value="${c.id}">${escapeHtml(c.first_name + ' ' + c.last_name || 'Unknown')}</option>`).join('');
    }
    
    function filterCandidates() {
        const search = document.getElementById('searchBox').value.toLowerCase();
        const score = document.getElementById('scoreFilterSelect').value;
        let filtered = allCandidates;
        if (search) filtered = filtered.filter(c => (c.first_name + ' ' + c.last_name).toLowerCase().includes(search));
        if (score === 'high') filtered = filtered.filter(c => (c.match_score || 0) >= 70);
        else if (score === 'medium') filtered = filtered.filter(c => (c.match_score || 0) >= 40 && (c.match_score || 0) < 70);
        else if (score === 'low') filtered = filtered.filter(c => (c.match_score || 0) < 40);
        renderCandidates(filtered);
        document.getElementById('candidateCount').innerHTML = `(${filtered.length})`;
    }
    
    function renderCandidates(candidates) {
        const container = document.getElementById('candidatesList');
        if (!candidates.length) { container.innerHTML = '<div class="card">No candidates</div>'; return; }
        container.innerHTML = candidates.map(c => {
            const name = (c.first_name + ' ' + c.last_name).trim() || 'Unknown';
            const skills = c.core_skills ? JSON.parse(c.core_skills) : [];
            const matchClass = c.match_score >= 70 ? 'match-high' : (c.match_score >= 40 ? 'match-medium' : 'match-low');
            return `<div class="card" onclick="viewCandidate(${c.id})">
                <h3>${escapeHtml(name)}</h3>
                <p>${skills.slice(0,3).map(s => `<span class="skill-tag">${escapeHtml(s.skill)}</span>`).join('')}</p>
                ${c.match_score ? `<p>Score: <span class="${matchClass}">${c.match_score}%</span></p>` : ''}
                <small>${new Date(c.created_at).toLocaleDateString()}</small>
            </div>`;
        }).join('');
    }
    
    document.getElementById('searchBox').onkeyup = filterCandidates;
    document.getElementById('scoreFilterSelect').onchange = filterCandidates;
    document.getElementById('clearFilterBtn').onclick = function() {
        document.getElementById('searchBox').value = '';
        document.getElementById('scoreFilterSelect').value = 'all';
        filterCandidates();
    };
    
    // ===== VIEW CANDIDATE =====
    window.viewCandidate = async function(id) {
        const c = allCandidates.find(c => c.id == id);
        if (!c) return;
        const name = (c.first_name + ' ' + c.last_name).trim();
        const skills = c.core_skills ? JSON.parse(c.core_skills) : [];
        const certs = c.certifications ? JSON.parse(c.certifications) : [];
        const workExp = c.work_experience ? JSON.parse(c.work_experience) : [];
        
        document.getElementById('candidateModalBody').innerHTML = `
            <div style="text-align:right; margin-bottom:10px;">
                <button class="btn" onclick="openEditModal(${c.id})">✏️ Edit</button>
                <button class="btn" onclick="copyDetails()">📋 Copy</button>
            </div>
            <div class="detail-row"><div class="detail-label">Name:</div><div>${escapeHtml(name)}</div></div>
            <div class="detail-row"><div class="detail-label">Email:</div><div>${escapeHtml(c.email || 'N/A')}</div></div>
            <div class="detail-row"><div class="detail-label">Phone:</div><div>${escapeHtml(c.phone || 'N/A')}</div></div>
            <div class="detail-row"><div class="detail-label">Role:</div><div>${escapeHtml(c.current_role || 'N/A')}</div></div>
            <div class="detail-row"><div class="detail-label">CTC:</div><div>Current: ${escapeHtml(c.current_ctc || 'N/A')} | Expected: ${escapeHtml(c.expected_ctc || 'N/A')}</div></div>
            <h4>Work Experience</h4>
            ${workExp.map(w => `<div><strong>${escapeHtml(w.company)}</strong> - ${escapeHtml(w.role)}</div>`).join('') || 'None'}
            <h4>Skills</h4>
            ${skills.map(s => `<span class="skill-tag">${escapeHtml(s.skill)} (${s.years_of_experience || 0}y)</span>`).join('') || 'None'}
            <h4>Certifications</h4>
            ${certs.map(cert => `<div>📜 ${escapeHtml(cert)}</div>`).join('') || 'None'}
            <button class="btn" onclick="closeModal()" style="margin-top:10px;">Close</button>
        `;
        document.getElementById('candidateModal').style.display = 'block';
    };
    
    window.copyDetails = function() {
        let text = '';
        document.querySelectorAll('#candidateModalBody .detail-row').forEach(el => text += el.innerText + '\n');
        navigator.clipboard.writeText(text);
        alert('Copied!');
    };
    
    function closeModal() { document.getElementById('candidateModal').style.display = 'none'; }
    window.closeModal = closeModal;
    
    // ===== EDIT CANDIDATE =====
    window.openEditModal = async function(id) {
        const c = allCandidates.find(c => c.id == id);
        if (!c) return;
        const skillsStr = c.core_skills ? JSON.parse(c.core_skills).map(s => s.skill).join(', ') : '';
        const certsStr = c.certifications ? JSON.parse(c.certifications).join(', ') : '';
        
        document.getElementById('editModalBody').innerHTML = `
            <form id="editForm">
                <label>First Name</label><input type="text" id="editFirst" value="${escapeHtml(c.first_name || '')}">
                <label>Last Name</label><input type="text" id="editLast" value="${escapeHtml(c.last_name || '')}">
                <label>Email</label><input type="email" id="editEmail" value="${escapeHtml(c.email || '')}">
                <label>Phone</label><input type="text" id="editPhone" value="${escapeHtml(c.phone || '')}">
                <label>Current Role</label><input type="text" id="editRole" value="${escapeHtml(c.current_role || '')}">
                <label>Current CTC</label><input type="text" id="editCurrentCTC" value="${escapeHtml(c.current_ctc || '')}">
                <label>Expected CTC</label><input type="text" id="editExpectedCTC" value="${escapeHtml(c.expected_ctc || '')}">
                <label>Address</label><input type="text" id="editAddress" value="${escapeHtml(c.address || '')}">
                <label>LinkedIn</label><input type="text" id="editLinkedin" value="${escapeHtml(c.linkedin || '')}">
                <label>Skills (comma separated)</label><input type="text" id="editSkills" value="${escapeHtml(skillsStr)}">
                <label>Certifications (comma separated)</label><input type="text" id="editCerts" value="${escapeHtml(certsStr)}">
                <div style="margin-top:15px;"><button type="submit" class="btn">Save</button><button type="button" class="btn" onclick="closeEditModal()">Cancel</button></div>
            </form>
        `;
        document.getElementById('editModal').style.display = 'block';
        
        document.getElementById('editForm').onsubmit = async (e) => {
            e.preventDefault();
            const skillsArray = document.getElementById('editSkills').value.split(',').map(s => ({skill: s.trim(), years_of_experience: 0})).filter(s => s.skill);
            const certsArray = document.getElementById('editCerts').value.split(',').map(c => c.trim()).filter(c => c);
            
            const data = {
                first_name: document.getElementById('editFirst').value,
                last_name: document.getElementById('editLast').value,
                email: document.getElementById('editEmail').value,
                phone: document.getElementById('editPhone').value,
                current_role: document.getElementById('editRole').value,
                current_ctc: document.getElementById('editCurrentCTC').value,
                expected_ctc: document.getElementById('editExpectedCTC').value,
                address: document.getElementById('editAddress').value,
                linkedin: document.getElementById('editLinkedin').value,
                core_skills: JSON.stringify(skillsArray),
                certifications: JSON.stringify(certsArray)
            };
            const res = await fetch(`/api/candidates/${id}`, { method: 'PUT', headers: {'Content-Type':'application/json'}, body: JSON.stringify(data) });
            if (res.ok) { alert('Updated!'); closeEditModal(); loadCandidates(); viewCandidate(id); }
            else alert('Error');
        };
    };
    
    function closeEditModal() { document.getElementById('editModal').style.display = 'none'; }
    window.closeEditModal = closeEditModal;
    
    // ===== EXPORT =====
    document.getElementById('exportBtn').onclick = () => window.location.href = '/api/export-candidates';
    
    // ===== PARSE RESUME =====
    document.getElementById('parseResumeButton').onclick = async function() {
        const file = document.getElementById('resumeFile').files[0];
        if (!file) { alert('Select a file'); return; }
        const fd = new FormData(); fd.append('resume', file);
        const div = document.getElementById('parseResultDiv');
        div.innerHTML = '<div class="spinner"></div><p>Parsing...</p>';
        try {
            const res = await fetch('/api/parse-resume', { method: 'POST', body: fd });
            const result = await res.json();
            if (result.error) { div.innerHTML = `<div class="alert-error">${result.error}</div>`; return; }
            div.innerHTML = `
                <div class="alert-success">
                    <h4>✅ Parsed</h4>
                    <p><strong>Name:</strong> ${escapeHtml(result.first_name || '')} ${escapeHtml(result.last_name || '')}</p>
                    <p><strong>Email:</strong> ${escapeHtml(result.email || '')}</p>
                    <p><strong>Phone:</strong> ${escapeHtml(result.phone || '')}</p>
                    <p><strong>Skills:</strong> ${result.core_skills ? result.core_skills.map(s => `<span class="skill-tag">${escapeHtml(s.skill)}</span>`).join('') : 'None'}</p>
                    <button class="btn" id="saveCandidateBtn">💾 Save</button>
                </div>
            `;
            document.getElementById('saveCandidateBtn').onclick = async function() {
                const saveRes = await fetch('/api/candidates', { method: 'POST', headers: {'Content-Type':'application/json'}, body: JSON.stringify(result) });
                if (saveRes.ok) { alert('Saved!'); div.innerHTML = ''; document.getElementById('resumeFile').value = ''; loadCandidates(); showPanel('candidates'); }
                else alert('Error');
            };
        } catch(e) { div.innerHTML = '<div class="alert-error">Error</div>'; }
    };
    
    // ===== CREATE JOB =====
    document.getElementById('createJobButton').onclick = async function() {
        const data = {
            title: document.getElementById('jobTitleField').value,
            company: document.getElementById('jobCompanyField').value,
            description: document.getElementById('jobDescField').value
        };
        if (!data.title) { alert('Title required'); return; }
        const res = await fetch('/api/jobs', { method: 'POST', headers: {'Content-Type':'application/json'}, body: JSON.stringify(data) });
        if (res.ok) {
            alert('Job created!');
            document.getElementById('jobTitleField').value = '';
            document.getElementById('jobCompanyField').value = '';
            document.getElementById('jobDescField').value = '';
            showPanel('jobs');
            loadJobs();
        } else { alert('Error'); }
    };
    
    // ===== ANALYZE =====
    document.getElementById('runAnalysisButton').onclick = async function() {
        const jobId = document.getElementById('jobSelectBox').value;
        const candidateId = document.getElementById('candidateSelectBox').value;
        if (!jobId || !candidateId) { alert('Select both'); return; }
        const job = allJobs.find(j => j.id == jobId);
        const cand = allCandidates.find(c => c.id == candidateId);
        const div = document.getElementById('analysisResultDiv');
        div.innerHTML = '<div class="spinner"></div><p>Analyzing...</p>';
        try {
            const res = await fetch('/api/analyze-match', { method: 'POST', headers: {'Content-Type':'application/json'}, body: JSON.stringify({ job_id: jobId, candidate_id: candidateId, jd_text: job.description || '', resume_text: cand.resume_text || '' }) });
            const result = await res.json();
            if (result.error) { div.innerHTML = `<div class="alert-error">${result.error}</div>`; return; }
            const matchClass = result.match_score >= 70 ? 'match-high' : (result.match_score >= 40 ? 'match-medium' : 'match-low');
            div.innerHTML = `<div class="alert-success"><h4>Analysis Complete</h4><p>Score: <span class="${matchClass}">${result.match_score || 0}%</span></p><p>${result.recommendation || 'Review'}</p><small>✅ Saved</small></div>`;
            loadCandidates();
        } catch(e) { div.innerHTML = '<div class="alert-error">Failed</div>'; }
    };
    
    function escapeHtml(str) { if (!str) return ''; return str.replace(/[&<>]/g, function(m) { if (m === '&') return '&amp;'; if (m === '<') return '&lt;'; if (m === '>') return '&gt;'; return m; }); }
    
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
