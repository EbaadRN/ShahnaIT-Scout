# app.py - COMPLETE WITH ALL FEATURES
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

# HTML TEMPLATE - COMPLETE WITH ALL FEATURES
HTML_TEMPLATE = '''
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>ShahnaIT Scout — Professional ATS</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body { background-color: #F9F6F0; font-family: 'Segoe UI', system-ui, sans-serif; }
        .container { max-width: 1400px; margin: 0 auto; padding: 20px; }
        .header { background: linear-gradient(135deg, #1A3A3A 0%, #1D5E5A 100%); color: white; padding: 25px; border-radius: 16px; margin-bottom: 20px; }
        .header h1 { font-size: 1.8em; }
        .tabs { display: flex; gap: 5px; background: white; padding: 10px; border-radius: 12px; margin-bottom: 20px; flex-wrap: wrap; }
        .tab-btn { background: transparent; border: none; padding: 10px 20px; cursor: pointer; border-radius: 8px; font-size: 14px; }
        .tab-btn:hover { background: #F9F6F0; }
        .tab-btn.active { background: #1D5E5A; color: white; }
        .card { background: white; border-radius: 16px; padding: 20px; margin-bottom: 20px; border-left: 4px solid #1D5E5A; cursor: pointer; transition: transform 0.2s; }
        .card:hover { transform: translateY(-2px); }
        .card.no-click { cursor: default; }
        .card.no-click:hover { transform: none; }
        .btn-primary { background: #1D5E5A; color: white; border: none; padding: 10px 24px; border-radius: 40px; cursor: pointer; font-weight: 600; margin: 5px; }
        .btn-primary:hover { background: #2A7A76; }
        .btn-secondary { background: #6B7B7B; color: white; border: none; padding: 8px 20px; border-radius: 40px; cursor: pointer; }
        .btn-edit { background: #C9A96E; color: white; border: none; padding: 6px 16px; border-radius: 30px; cursor: pointer; font-size: 12px; }
        input, textarea, select { width: 100%; padding: 12px; border: 1px solid #ddd; border-radius: 12px; margin-bottom: 15px; font-size: 14px; }
        .skill-tag { display: inline-block; background: #F9F6F0; padding: 4px 12px; border-radius: 30px; margin: 3px; font-size: 12px; color: #1D5E5A; }
        .skill-with-years { background: #E8F5E9; padding: 4px 12px; border-radius: 30px; margin: 3px; font-size: 12px; color: #1B5E20; }
        .match-high { background: #1B6B2E; color: white; padding: 2px 10px; border-radius: 30px; display: inline-block; }
        .match-medium { background: #CC5500; color: white; padding: 2px 10px; border-radius: 30px; display: inline-block; }
        .match-low { background: #B22222; color: white; padding: 2px 10px; border-radius: 30px; display: inline-block; }
        .alert-success { background: #1B6B2E; color: white; padding: 12px; border-radius: 12px; margin: 10px 0; }
        .alert-error { background: #B22222; color: white; padding: 12px; border-radius: 12px; margin: 10px 0; }
        .alert-info { background: #3498DB; color: white; padding: 12px; border-radius: 12px; margin: 10px 0; }
        .spinner { border: 3px solid #F9F6F0; border-top: 3px solid #1D5E5A; border-radius: 50%; width: 40px; height: 40px; animation: spin 0.8s linear infinite; margin: 20px auto; }
        @keyframes spin { 0% { transform: rotate(0deg); } 100% { transform: rotate(360deg); } }
        .modal { display: none; position: fixed; z-index: 1000; left: 0; top: 0; width: 100%; height: 100%; background: rgba(0,0,0,0.5); overflow-y: auto; }
        .modal-content { background: #F9F6F0; margin: 50px auto; border-radius: 20px; max-width: 900px; width: 90%; }
        .modal-header { background: #1D5E5A; color: white; padding: 15px 20px; border-radius: 20px 20px 0 0; display: flex; justify-content: space-between; align-items: center; }
        .modal-body { padding: 20px; max-height: 70vh; overflow-y: auto; }
        .close { font-size: 28px; cursor: pointer; color: white; }
        .doc-link { cursor: pointer; color: #1D5E5A; text-decoration: underline; }
        .doc-link:hover { color: #2A7A76; }
        .detail-row { display: flex; margin-bottom: 10px; border-bottom: 1px solid #ddd; padding-bottom: 5px; }
        .detail-label { width: 140px; font-weight: 600; color: #1A3A3A; }
        .detail-value { flex: 1; color: #2C3E3E; }
        .company-item { background: #F9F6F0; padding: 12px; border-radius: 16px; margin-bottom: 8px; border-left: 3px solid #1D5E5A; }
        .filter-bar { display: flex; gap: 10px; flex-wrap: wrap; background: white; padding: 15px; border-radius: 16px; margin-bottom: 20px; }
        .filter-bar input, .filter-bar select { margin: 0; flex: 1; min-width: 120px; }
        .flex { display: flex; gap: 15px; flex-wrap: wrap; }
        .flex-1 { flex: 1; }
        .file-list { background: #F9F6F0; border-radius: 12px; padding: 10px; margin-top: 10px; max-height: 150px; overflow-y: auto; }
        .file-list-item { padding: 5px; border-bottom: 1px solid #ddd; font-size: 12px; display: flex; justify-content: space-between; }
        .remove-file { color: #B22222; cursor: pointer; }
        .progress-bar { background: #ddd; border-radius: 20px; height: 20px; margin: 10px 0; overflow: hidden; }
        .progress-fill { background: #1B6B2E; width: 0%; height: 100%; transition: width 0.3s; }
        @media (max-width: 768px) { .container { padding: 10px; } .tab-btn { padding: 8px 12px; } .detail-label { width: 100px; } }
    </style>
</head>
<body>
<div class="container">
    <div class="header">
        <h1>🎯 ShahnaIT Scout <span style="background:#27AE60; padding:4px 12px; border-radius:30px; font-size:12px;">⚡ GROQ AI</span></h1>
        <p>Intelligent Recruitment Platform with AI Resume Parsing & Match Analysis</p>
    </div>
    
    <div class="tabs">
        <button class="tab-btn active" onclick="showTab('jobs')">📋 Jobs</button>
        <button class="tab-btn" onclick="showTab('candidates')">👥 Candidates</button>
        <button class="tab-btn" onclick="showTab('upload')">📄 Upload Resume</button>
        <button class="tab-btn" onclick="showTab('createJob')">➕ Create Job</button>
        <button class="tab-btn" onclick="showTab('analyze')">🔍 Analyze Match</button>
    </div>
    
    <!-- Jobs Tab -->
    <div id="jobsTab"><div id="jobsList"></div></div>
    
    <!-- Candidates Tab -->
    <div id="candidatesTab" style="display:none;">
        <div style="display: flex; justify-content: space-between; margin-bottom: 15px;">
            <h2>👥 Candidates <span id="filterCount"></span></h2>
            <button class="btn-primary" onclick="exportToCSV()">📥 Export CSV</button>
        </div>
        <div class="filter-bar">
            <input type="text" id="searchInput" placeholder="🔍 Search by name or skills..." onkeyup="filterCandidates()">
            <select id="scoreFilter" onchange="filterCandidates()">
                <option value="all">All Scores</option>
                <option value="high">High (70%+)</option>
                <option value="medium">Medium (40-69%)</option>
                <option value="low">Low (<40%)</option>
            </select>
            <button class="btn-primary" onclick="clearFilters()">Clear</button>
        </div>
        <div id="candidatesList"></div>
    </div>
    
    <!-- Upload Resume Tab -->
    <div id="uploadTab" style="display:none;">
        <div class="card no-click">
            <h3>📄 Single Resume Upload</h3>
            <div class="alert-info">🤖 AI will auto-fill candidate details. Resume will be automatically attached.</div>
            <input type="file" id="singleFile" accept=".pdf,.docx">
            <button class="btn-primary" id="singleUploadBtn">🔍 Parse & Save</button>
            <div id="singleResult"></div>
        </div>
        
        <div class="card no-click">
            <h3>📚 Multiple Resume Upload (Select Multiple Files)</h3>
            <div class="alert-info">Hold Ctrl (or Cmd on Mac) to select multiple PDF/DOCX files at once.</div>
            <input type="file" id="multiFiles" multiple accept=".pdf,.docx">
            <div id="multiFileList" class="file-list" style="display:none;"></div>
            <button class="btn-primary" id="multiUploadBtn">🚀 Upload & Parse All</button>
            <div id="multiResult"></div>
        </div>
        
        <div class="card no-click">
            <h3>📦 Bulk Resume Upload (ZIP File)</h3>
            <div class="alert-info">Upload a ZIP file containing multiple PDF/DOCX resumes.</div>
            <input type="file" id="zipFile" accept=".zip">
            <button class="btn-primary" id="bulkUploadBtn">🚀 Upload ZIP & Parse All</button>
            <div id="bulkResult"></div>
        </div>
    </div>
    
    <!-- Create Job Tab -->
    <div id="createJobTab" style="display:none;">
        <div class="card no-click">
            <h3>➕ Create New Job Posting</h3>
            <input type="text" id="jobTitle" placeholder="Job Title *">
            <input type="text" id="jobCompany" placeholder="Company Name">
            <textarea id="jobDesc" rows="5" placeholder="Job Description (be detailed for better matching)"></textarea>
            <button class="btn-primary" id="createJobBtn">Create Job</button>
        </div>
    </div>
    
    <!-- Analyze Match Tab -->
    <div id="analyzeTab" style="display:none;">
        <div class="card no-click">
            <h3>🔍 AI Match Analysis</h3>
            <div class="flex">
                <div class="flex-1"><select id="jobSelect"><option value="">-- Select Job --</option></select></div>
                <div class="flex-1"><select id="candidateSelect"><option value="">-- Select Candidate --</option></select></div>
            </div>
            <button class="btn-primary" id="analyzeBtn">🤖 Run AI Analysis</button>
            <div id="analyzeResult"></div>
        </div>
    </div>
</div>

<!-- Candidate Profile Modal -->
<div id="candidateModal" class="modal">
    <div class="modal-content">
        <div class="modal-header"><h2 id="modalTitle">Candidate Profile</h2><span class="close" onclick="closeModal()">&times;</span></div>
        <div class="modal-body" id="modalBody"></div>
    </div>
</div>

<!-- Edit Candidate Modal -->
<div id="editModal" class="modal">
    <div class="modal-content">
        <div class="modal-header"><h2>✏️ Edit Candidate</h2><span class="close" onclick="closeEditModal()">&times;</span></div>
        <div class="modal-body" id="editModalBody"></div>
    </div>
</div>

<!-- Document Preview Modal -->
<div id="docPreviewModal" class="modal">
    <div class="modal-content">
        <div class="modal-header"><h2 id="previewTitle">Document Preview</h2><span class="close" onclick="closeDocPreview()">&times;</span></div>
        <div class="modal-body" id="previewBody"></div>
    </div>
</div>

<script>
    let jobsData = [], candidatesData = [], currentCandidateId = null;
    
    function showTab(tab) {
        document.getElementById('jobsTab').style.display = 'none';
        document.getElementById('candidatesTab').style.display = 'none';
        document.getElementById('uploadTab').style.display = 'none';
        document.getElementById('createJobTab').style.display = 'none';
        document.getElementById('analyzeTab').style.display = 'none';
        document.getElementById(tab + 'Tab').style.display = 'block';
        document.querySelectorAll('.tab-btn').forEach(btn => btn.classList.remove('active'));
        if (event && event.target) event.target.classList.add('active');
        if (tab === 'jobs') loadJobs();
        if (tab === 'candidates') loadCandidates();
        if (tab === 'analyze') { loadJobs(); loadCandidates(); }
    }
    
    // Multi-file selection display
    document.getElementById('multiFiles').addEventListener('change', function(e) {
        const files = e.target.files;
        const container = document.getElementById('multiFileList');
        if (files.length > 0) {
            let html = '<strong>Selected files (' + files.length + '):</strong><br>';
            for (let i = 0; i < files.length; i++) {
                html += `<div class="file-list-item">📄 ${escapeHtml(files[i].name)}</div>`;
            }
            container.innerHTML = html;
            container.style.display = 'block';
        } else {
            container.style.display = 'none';
        }
    });
    
    async function loadJobs() {
        const res = await fetch('/api/jobs');
        jobsData = await res.json();
        const container = document.getElementById('jobsList');
        if (!jobsData.length) { container.innerHTML = '<div class="card no-click">No jobs yet. Create one.</div>'; return; }
        container.innerHTML = jobsData.map(j => `<div class="card no-click"><h3>${escapeHtml(j.title)}</h3>${j.company ? `<p>🏢 ${escapeHtml(j.company)}</p>` : ''}<small>${new Date(j.created_at).toLocaleDateString()}</small></div>`).join('');
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
        document.getElementById('filterCount').innerHTML = `(${filtered.length} of ${candidatesData.length})`;
    }
    
    function renderCandidates(candidates) {
        const container = document.getElementById('candidatesList');
        if (!candidates.length) { container.innerHTML = '<div class="card no-click">No candidates found</div>'; return; }
        container.innerHTML = candidates.map(c => {
            const name = `${c.first_name || ''} ${c.last_name || ''}`.trim() || 'Unknown';
            const skills = c.core_skills ? JSON.parse(c.core_skills) : [];
            const matchClass = c.match_score >= 70 ? 'match-high' : (c.match_score >= 40 ? 'match-medium' : 'match-low');
            return `<div class="card" onclick="viewCandidate(${c.id})">
                <h3>👤 ${escapeHtml(name)}</h3>
                ${c.email ? `<p>📧 ${escapeHtml(c.email)}</p>` : ''}
                <p>🔧 ${skills.slice(0,3).map(s => `<span class="skill-tag">${escapeHtml(s.skill)}${s.years_of_experience ? ` (${s.years_of_experience}y)` : ''}</span>`).join('')}</p>
                ${c.match_score ? `<p>🎯 Score: <span class="${matchClass}">${c.match_score}%</span></p>` : ''}
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
        currentCandidateId = id;
        const c = candidatesData.find(c => c.id == id);
        if (!c) return;
        
        const fullName = `${c.first_name || ''} ${c.middle_name || ''} ${c.last_name || ''}`.trim();
        const workExp = JSON.parse(c.work_experience || '[]');
        const skills = JSON.parse(c.core_skills || '[]');
        const certs = JSON.parse(c.certifications || '[]');
        
        const docRes = await fetch(`/api/candidates/${id}/documents`);
        const documents = await docRes.json();
        const resumeDoc = documents.find(d => d.is_resume === 1);
        const otherDocs = documents.filter(d => !d.is_resume);
        
        document.getElementById('modalBody').innerHTML = `
            <div style="display: flex; gap: 10px; justify-content: flex-end; margin-bottom: 15px;">
                <button class="btn-edit" onclick="openEditModal(${id})">✏️ Edit Profile</button>
                <button class="btn-secondary" onclick="openAddDocumentModal(${id})">📎 Add Document</button>
                <button class="btn-secondary" onclick="copyAllDetails()">📋 Copy All</button>
            </div>
            <div class="detail-row"><div class="detail-label">Full Name:</div><div class="detail-value">${escapeHtml(fullName)}</div></div>
            <div class="detail-row"><div class="detail-label">Phone:</div><div class="detail-value">${escapeHtml(c.phone || 'N/A')}</div></div>
            <div class="detail-row"><div class="detail-label">Email:</div><div class="detail-value">${escapeHtml(c.email || 'N/A')}</div></div>
            <div class="detail-row"><div class="detail-label">Current CTC:</div><div class="detail-value">${escapeHtml(c.current_ctc || 'N/A')}</div></div>
            <div class="detail-row"><div class="detail-label">Expected CTC:</div><div class="detail-value">${escapeHtml(c.expected_ctc || 'N/A')}</div></div>
            <div class="detail-row"><div class="detail-label">Address:</div><div class="detail-value">${escapeHtml(c.address || 'N/A')}</div></div>
            <div class="detail-row"><div class="detail-label">LinkedIn:</div><div class="detail-value">${escapeHtml(c.linkedin || 'N/A')}</div></div>
            <div class="detail-row"><div class="detail-label">Current Role:</div><div class="detail-value">${escapeHtml(c.current_role || 'N/A')}</div></div>
            <div class="detail-row"><div class="detail-label">Status:</div><div class="detail-value">${escapeHtml(c.employment_status || 'N/A')}${c.notice_period_days ? ` (${c.notice_period_days} days)` : ''}</div></div>
            
            <h4 style="margin-top: 20px;">💼 Work Experience</h4>
            ${workExp.map(w => `<div class="company-item"><strong>${escapeHtml(w.company)}</strong> — ${escapeHtml(w.role)}<br><small>${escapeHtml(w.start_date || '')} - ${escapeHtml(w.end_date || 'Present')}</small></div>`).join('') || '<p>None</p>'}
            
            <h4>⭐ Core Skills</h4>
            ${skills.map(s => `<span class="skill-with-years">${escapeHtml(s.skill)} (${s.years_of_experience || 0} yrs)</span>`).join('') || '<p>None</p>'}
            
            <h4>📜 Certifications</h4>
            ${certs.map(cert => `<div>📜 ${escapeHtml(cert)}</div>`).join('') || '<p>None</p>'}
            
            <h4>🎓 Education</h4>
            <p>${escapeHtml(c.education || 'N/A')}</p>
            
            <h4>📄 Resume</h4>
            ${resumeDoc ? `<div><span class="doc-link" onclick="previewDocument(${resumeDoc.id})">📄 ${escapeHtml(resumeDoc.original_filename)}</span> <span style="background:#1B6B2E; color:white; padding:2px 8px; border-radius:12px; font-size:10px;">Original Resume</span></div>` : '<p>No resume attached</p>'}
            
            <h4>📎 Other Documents (${otherDocs.length})</h4>
            ${otherDocs.map(d => `<div><span class="doc-link" onclick="previewDocument(${d.id})">📄 ${escapeHtml(d.original_filename)}</span></div>`).join('') || '<p>No additional documents</p>'}
            
            <button class="btn-primary" onclick="closeModal()" style="margin-top: 20px;">Close</button>
        `;
        document.getElementById('candidateModal').style.display = 'block';
    }
    
    async function previewDocument(docId) {
        try {
            const res = await fetch(`/api/documents/${docId}/preview`);
            const data = await res.json();
            document.getElementById('previewTitle').innerHTML = 'Document Preview';
            if (data.type === 'image') {
                document.getElementById('previewBody').innerHTML = `<img src="data:image/png;base64,${data.content}" style="max-width:100%;">`;
            } else {
                document.getElementById('previewBody').innerHTML = `<div style="white-space: pre-wrap; font-family: monospace; background: white; padding: 15px; border-radius: 12px;">${escapeHtml(data.content)}</div>`;
            }
            document.getElementById('docPreviewModal').style.display = 'block';
        } catch(e) {
            alert('Unable to preview document');
        }
    }
    
    function closeDocPreview() { document.getElementById('docPreviewModal').style.display = 'none'; }
    function closeModal() { document.getElementById('candidateModal').style.display = 'none'; }
    function closeEditModal() { document.getElementById('editModal').style.display = 'none'; }
    
    function copyAllDetails() {
        let text = '';
        document.querySelectorAll('#modalBody .detail-row, #modalBody .company-item, #modalBody .skill-with-years').forEach(el => {
            text += el.innerText + '\n';
        });
        navigator.clipboard.writeText(text);
        alert('Copied to clipboard!');
    }
    
    async function openEditModal(id) {
        const c = candidatesData.find(c => c.id == id);
        if (!c) return;
        
        const skillsStr = c.core_skills ? JSON.parse(c.core_skills).map(s => s.skill).join(', ') : '';
        const certsStr = c.certifications ? JSON.parse(c.certifications).join(', ') : '';
        
        document.getElementById('editModalBody').innerHTML = `
            <form id="editCandidateForm">
                <div class="flex">
                    <div class="flex-1"><label>First Name</label><input type="text" id="edit-first" value="${escapeHtml(c.first_name || '')}"></div>
                    <div class="flex-1"><label>Middle Name</label><input type="text" id="edit-middle" value="${escapeHtml(c.middle_name || '')}"></div>
                    <div class="flex-1"><label>Last Name</label><input type="text" id="edit-last" value="${escapeHtml(c.last_name || '')}"></div>
                </div>
                <div class="flex">
                    <div class="flex-1"><label>Email</label><input type="email" id="edit-email" value="${escapeHtml(c.email || '')}"></div>
                    <div class="flex-1"><label>Phone</label><input type="text" id="edit-phone" value="${escapeHtml(c.phone || '')}"></div>
                </div>
                <div class="flex">
                    <div class="flex-1"><label>Current CTC</label><input type="text" id="edit-current-ctc" value="${escapeHtml(c.current_ctc || '')}" placeholder="e.g., 12 LPA"></div>
                    <div class="flex-1"><label>Expected CTC</label><input type="text" id="edit-expected-ctc" value="${escapeHtml(c.expected_ctc || '')}" placeholder="e.g., 15 LPA"></div>
                </div>
                <label>Address</label><input type="text" id="edit-address" value="${escapeHtml(c.address || '')}">
                <label>LinkedIn</label><input type="text" id="edit-linkedin" value="${escapeHtml(c.linkedin || '')}">
                <label>Current Role</label><input type="text" id="edit-role" value="${escapeHtml(c.current_role || '')}">
                <div class="flex">
                    <div class="flex-1"><label>Employment Status</label>
                        <select id="edit-status">
                            <option value="working" ${c.employment_status === 'working' ? 'selected' : ''}>Working</option>
                            <option value="bench" ${c.employment_status === 'bench' ? 'selected' : ''}>On Bench</option>
                            <option value="notice_period" ${c.employment_status === 'notice_period' ? 'selected' : ''}>Notice Period</option>
                        </select>
                    </div>
                    <div class="flex-1"><label>Notice Period (days)</label><input type="number" id="edit-notice-days" value="${c.notice_period_days || 0}"></div>
                </div>
                <label>Education</label><textarea id="edit-education" rows="2">${escapeHtml(c.education || '')}</textarea>
                <label>Skills (comma separated)</label><input type="text" id="edit-skills" value="${escapeHtml(skillsStr)}">
                <label>Certifications (comma separated)</label><input type="text" id="edit-certs" value="${escapeHtml(certsStr)}">
                <div style="margin-top: 20px;"><button type="submit" class="btn-primary">Save Changes</button><button type="button" class="btn-secondary" onclick="closeEditModal()">Cancel</button></div>
            </form>
        `;
        document.getElementById('editModal').style.display = 'block';
        
        document.getElementById('editCandidateForm').onsubmit = async (e) => {
            e.preventDefault();
            const skillsArray = document.getElementById('edit-skills').value.split(',').map(s => ({skill: s.trim(), years_of_experience: 0})).filter(s => s.skill);
            const certsArray = document.getElementById('edit-certs').value.split(',').map(c => c.trim()).filter(c => c);
            
            const updatedData = {
                first_name: document.getElementById('edit-first').value,
                middle_name: document.getElementById('edit-middle').value,
                last_name: document.getElementById('edit-last').value,
                email: document.getElementById('edit-email').value,
                phone: document.getElementById('edit-phone').value,
                current_ctc: document.getElementById('edit-current-ctc').value,
                expected_ctc: document.getElementById('edit-expected-ctc').value,
                address: document.getElementById('edit-address').value,
                linkedin: document.getElementById('edit-linkedin').value,
                current_role: document.getElementById('edit-role').value,
                employment_status: document.getElementById('edit-status').value,
                notice_period_days: parseInt(document.getElementById('edit-notice-days').value) || 0,
                education: document.getElementById('edit-education').value,
                core_skills: JSON.stringify(skillsArray),
                certifications: JSON.stringify(certsArray)
            };
            
            const res = await fetch(`/api/candidates/${id}`, { method: 'PUT', headers: {'Content-Type':'application/json'}, body: JSON.stringify(updatedData) });
            if (res.ok) { alert('Candidate updated!'); closeEditModal(); loadCandidates(); viewCandidate(id); }
            else alert('Error updating');
        };
    }
    
    function openAddDocumentModal(id) { currentCandidateId = id; openDocModal(); }
    
    function openDocModal() {
        document.getElementById('docModal').style.display = 'block';
    }
    
    function closeDocModal() {
        document.getElementById('docModal').style.display = 'none';
    }
    
    window.exportToCSV = () => window.location.href = '/api/export-candidates';
    
    // Single Upload
    document.getElementById('singleUploadBtn').onclick = async function() {
        const file = document.getElementById('singleFile').files[0];
        if (!file) { alert('Select a file'); return; }
        const fd = new FormData(); fd.append('resume', file);
        const div = document.getElementById('singleResult');
        div.innerHTML = '<div class="spinner"></div><p>🤖 Groq AI parsing resume...</p>';
        try {
            const res = await fetch('/api/parse-resume', { method: 'POST', body: fd });
            const result = await res.json();
            if (result.error) { div.innerHTML = `<div class="alert-error">${result.error}</div>`; return; }
            div.innerHTML = `<div class="alert-success"><h4>✅ Resume Parsed</h4><p><strong>Name:</strong> ${escapeHtml(result.first_name || '')} ${escapeHtml(result.last_name || '')}</p><p><strong>Email:</strong> ${escapeHtml(result.email || '')}</p><p><strong>Phone:</strong> ${escapeHtml(result.phone || '')}</p><p><strong>Skills:</strong> ${result.core_skills ? result.core_skills.map(s => `<span class="skill-tag">${escapeHtml(s.skill)}</span>`).join('') : 'None'}</p><button class="btn-primary" id="saveCandidateBtn">💾 Save Candidate</button></div>`;
            document.getElementById('saveCandidateBtn').onclick = async function() {
                const saveRes = await fetch('/api/candidates', { method: 'POST', headers: {'Content-Type':'application/json'}, body: JSON.stringify(result) });
                if (saveRes.ok) { alert('Candidate saved! Resume auto-attached!'); div.innerHTML = ''; document.getElementById('singleFile').value = ''; loadCandidates(); showTab('candidates'); }
                else alert('Error saving');
            };
        } catch(e) { div.innerHTML = '<div class="alert-error">Error parsing</div>'; }
    };
    
    // Multi Upload
    document.getElementById('multiUploadBtn').onclick = async function() {
        const files = document.getElementById('multiFiles').files;
        if (!files.length) { alert('Select files first'); return; }
        const div = document.getElementById('multiResult');
        div.innerHTML = '<div class="spinner"></div><p>Processing...</p>';
        let success = 0, fail = 0;
        for (let i = 0; i < files.length; i++) {
            const fd = new FormData();
            fd.append('resume', files[i]);
            div.innerHTML = `<div class="progress-bar"><div class="progress-fill" style="width:${Math.round((i/files.length)*100)}%"></div></div><p>Processing ${i+1}/${files.length}: ${escapeHtml(files[i].name)}</p>`;
            try {
                const res = await fetch('/api/parse-resume', { method: 'POST', body: fd });
                const result = await res.json();
                if (!result.error) {
                    const saveRes = await fetch('/api/candidates', { method: 'POST', headers: {'Content-Type':'application/json'}, body: JSON.stringify(result) });
                    if (saveRes.ok) success++;
                    else fail++;
                } else { fail++; }
            } catch(e) { fail++; }
        }
        div.innerHTML = `<div class="alert-success"><h4>✅ Complete!</h4><p>Success: ${success} | Failed: ${fail}</p><button class="btn-primary" onclick="showTab('candidates')">View Candidates</button></div>`;
        document.getElementById('multiFiles').value = '';
        document.getElementById('multiFileList').style.display = 'none';
        loadCandidates();
    };
    
    // Bulk ZIP Upload
    document.getElementById('bulkUploadBtn').onclick = async function() {
        const file = document.getElementById('zipFile').files[0];
        if (!file) { alert('Select a ZIP file'); return; }
        const fd = new FormData(); fd.append('zip_file', file);
        const div = document.getElementById('bulkResult');
        div.innerHTML = '<div class="spinner"></div><p>Processing ZIP...</p>';
        try {
            const res = await fetch('/api/bulk-upload', { method: 'POST', body: fd });
            const result = await res.json();
            if (result.error) { div.innerHTML = `<div class="alert-error">${result.error}</div>`; return; }
            div.innerHTML = `<div class="alert-success"><h4>✅ Complete!</h4><p>Total: ${result.total} | Success: ${result.success} | Failed: ${result.failed}</p><button class="btn-primary" onclick="showTab('candidates')">View Candidates</button></div>`;
            document.getElementById('zipFile').value = '';
            loadCandidates();
        } catch(e) { div.innerHTML = '<div class="alert-error">Error</div>'; }
    };
    
    // Create Job
    document.getElementById('createJobBtn').onclick = async function() {
        const title = document.getElementById('jobTitle').value;
        const company = document.getElementById('jobCompany').value;
        const description = document.getElementById('jobDesc').value;
        if (!title) { alert('Job title required'); return; }
        const res = await fetch('/api/jobs', { method: 'POST', headers: {'Content-Type':'application/json'}, body: JSON.stringify({ title, company, description }) });
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
        div.innerHTML = '<div class="spinner"></div><p>🤖 AI analyzing...</p>';
        try {
            const res = await fetch('/api/analyze-match', { method: 'POST', headers: {'Content-Type':'application/json'}, body: JSON.stringify({ job_id: jobId, candidate_id: candidateId, jd_text: job.description || '', resume_text: cand.resume_text || '' }) });
            const result = await res.json();
            if (result.error) { div.innerHTML = `<div class="alert-error">${result.error}</div>`; return; }
            const matchClass = result.match_score >= 70 ? 'match-high' : (result.match_score >= 40 ? 'match-medium' : 'match-low');
            div.innerHTML = `<div class="alert-success"><h4>📊 Analysis Complete</h4><p><strong>🎯 Score:</strong> <span class="${matchClass}">${result.match_score || 0}%</span></p><p><strong>📌 Recommendation:</strong> ${result.recommendation || 'Review'}</p><div class="alert-info">${result.executive_summary?.final_verdict || ''}</div><small>✅ Saved</small></div>`;
            loadCandidates();
        } catch(e) { div.innerHTML = '<div class="alert-error">Failed</div>'; }
    };
    
    // Add Document Modal HTML
    const docModalHtml = `
    <div id="docModal" class="modal">
        <div class="modal-content">
            <div class="modal-header"><h2>📎 Add Document</h2><span class="close" onclick="closeDocModal()">&times;</span></div>
            <div class="modal-body"><input type="file" id="docFile" accept=".pdf,.docx,.png,.jpg,.jpeg"><button class="btn-primary" id="uploadDocBtn">Upload</button><div id="uploadStatus"></div></div>
        </div>
    </div>`;
    document.body.insertAdjacentHTML('beforeend', docModalHtml);
    
    document.getElementById('uploadDocBtn').onclick = async function() {
        const file = document.getElementById('docFile').files[0];
        if (!file || !currentCandidateId) return alert('Select a file');
        const fd = new FormData(); fd.append('document', file); fd.append('candidate_id', currentCandidateId);
        const res = await fetch('/api/candidates/upload-document', { method: 'POST', body: fd });
        if (res.ok) { alert('Document uploaded'); closeDocModal(); viewCandidate(currentCandidateId); }
        else alert('Upload failed');
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
