# app.py - COMPLETE FIXED VERSION (Buttons Working)
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
        
        button, .btn { background: #1A4D4A; color: white; border: none; padding: 10px 20px; margin: 5px; cursor: pointer; border-radius: 8px; }
        button:hover, .btn:hover { background: #2A6B67; }
        
        .tab-btn { background: white; color: #1A4D4A; border: 1px solid #1A4D4A; padding: 10px 20px; margin: 5px; cursor: pointer; border-radius: 8px; }
        .tab-btn:hover { background: #1A4D4A; color: white; }
        .tab-btn.active { background: #1A4D4A; color: white; }
        
        .card { background: white; padding: 15px; margin: 10px 0; border-radius: 8px; border-left: 4px solid #1A4D4A; cursor: pointer; transition: transform 0.2s; }
        .card:hover { transform: translateY(-2px); box-shadow: 0 2px 8px rgba(0,0,0,0.1); }
        .card.no-click { cursor: default; }
        .card.no-click:hover { transform: none; }
        
        input, select, textarea { width: 100%; padding: 8px; margin: 5px 0; border: 1px solid #ccc; border-radius: 5px; }
        .skill-tag { background: #F5F0E8; padding: 3px 8px; border-radius: 15px; display: inline-block; margin: 2px; }
        .skill-with-years { background: #E8F5E9; padding: 3px 8px; border-radius: 15px; display: inline-block; margin: 2px; color: #1B5E20; }
        .match-high { background: #1B6B2E; color: white; padding: 2px 8px; border-radius: 15px; display: inline-block; }
        .match-medium { background: #CC5500; color: white; padding: 2px 8px; border-radius: 15px; display: inline-block; }
        .match-low { background: #B22222; color: white; padding: 2px 8px; border-radius: 15px; display: inline-block; }
        .alert-success { background: #1B6B2E; color: white; padding: 10px; border-radius: 8px; margin: 10px 0; }
        .alert-error { background: #B22222; color: white; padding: 10px; border-radius: 8px; margin: 10px 0; }
        .spinner { border: 3px solid #f3f3f3; border-top: 3px solid #1A4D4A; border-radius: 50%; width: 30px; height: 30px; animation: spin 1s linear infinite; margin: 10px auto; }
        @keyframes spin { 0% { transform: rotate(0deg); } 100% { transform: rotate(360deg); } }
        .flex { display: flex; gap: 10px; flex-wrap: wrap; }
        .flex-1 { flex: 1; }
        .filter-bar { background: white; padding: 10px; border-radius: 8px; margin-bottom: 15px; display: flex; gap: 10px; flex-wrap: wrap; }
        .filter-bar input, .filter-bar select { width: auto; flex: 1; }
        
        .modal { display: none; position: fixed; z-index: 1000; left: 0; top: 0; width: 100%; height: 100%; background: rgba(0,0,0,0.5); }
        .modal-content { background: #F5F0E8; margin: 50px auto; border-radius: 10px; max-width: 700px; width: 90%; }
        .modal-header { background: #1A4D4A; color: white; padding: 15px; border-radius: 10px 10px 0 0; display: flex; justify-content: space-between; }
        .modal-body { padding: 20px; max-height: 60vh; overflow-y: auto; }
        .close { cursor: pointer; font-size: 24px; }
        .detail-row { margin-bottom: 10px; display: flex; border-bottom: 1px solid #ddd; padding-bottom: 5px; }
        .detail-label { width: 130px; font-weight: bold; }
        .detail-value { flex: 1; }
        .company-item { background: #F9F6F0; padding: 10px; border-radius: 8px; margin-bottom: 8px; border-left: 3px solid #1A4D4A; }
        .doc-link { cursor: pointer; color: #1A4D4A; text-decoration: underline; }
        .btn-edit { background: #C9A96E; }
        .btn-secondary { background: #6B7B7B; }
        
        .file-list { background: #F9F6F0; border-radius: 8px; padding: 10px; margin-top: 10px; max-height: 150px; overflow-y: auto; }
        .file-list-item { padding: 5px; border-bottom: 1px solid #ddd; font-size: 12px; display: flex; justify-content: space-between; }
        .remove-file { color: #B22222; cursor: pointer; margin-left: 10px; }
        .progress-bar { background: #ddd; border-radius: 10px; height: 15px; margin: 10px 0; overflow: hidden; }
        .progress-fill { background: #1B6B2E; width: 0%; height: 100%; transition: width 0.3s; }
    </style>
</head>
<body>
<div style="max-width: 1200px; margin: 0 auto;">
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
        <div class="card no-click">
            <h3>📄 Single Resume Upload</h3>
            <p>AI will auto-fill candidate details. Resume will be automatically attached.</p>
            <input type="file" id="resumeFile" accept=".pdf,.docx">
            <button id="parseBtn">🔍 Parse & Save Candidate</button>
            <div id="parseResult"></div>
        </div>
        
        <div class="card no-click" style="margin-top: 20px;">
            <h3>📚 Bulk Resume Upload (Select Multiple Files)</h3>
            <p>Hold Ctrl (or Cmd on Mac) to select multiple PDF/DOCX files at once</p>
            <input type="file" id="multiResumeFiles" multiple accept=".pdf,.docx">
            <div id="selectedFilesList" class="file-list" style="display:none;"></div>
            <button id="bulkUploadBtn">🚀 Upload & Parse All Selected Files</button>
            <div id="bulkUploadResult"></div>
        </div>
    </div>
    
    <div id="panel4" style="display:none;">
        <div class="card no-click">
            <h3>➕ Create New Job</h3>
            <input type="text" id="jobTitle" placeholder="Job Title *">
            <input type="text" id="jobCompany" placeholder="Company Name">
            <textarea id="jobDesc" rows="4" placeholder="Job Description"></textarea>
            <button id="createJobBtn">Create Job</button>
        </div>
    </div>
    
    <div id="panel5" style="display:none;">
        <div class="card no-click">
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

<!-- Candidate Detail Modal -->
<div id="candidateModal" class="modal">
    <div class="modal-content">
        <div class="modal-header"><h2>Candidate Profile</h2><span class="close" onclick="closeModal()">&times;</span></div>
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

<!-- Add Document Modal -->
<div id="docModal" class="modal">
    <div class="modal-content">
        <div class="modal-header"><h2>📎 Add Document</h2><span class="close" onclick="closeDocModal()">&times;</span></div>
        <div class="modal-body">
            <input type="file" id="docFile" accept=".pdf,.docx,.png,.jpg,.jpeg">
            <button id="uploadDocBtn">Upload Document</button>
            <div id="docUploadStatus"></div>
        </div>
    </div>
</div>

<!-- Document Preview Modal -->
<div id="previewModal" class="modal">
    <div class="modal-content">
        <div class="modal-header"><h2>Document Preview</h2><span class="close" onclick="closePreviewModal()">&times;</span></div>
        <div class="modal-body" id="previewBody"></div>
    </div>
</div>

<script>
    document.addEventListener('DOMContentLoaded', function() {
        let allJobs = [], allCandidates = [], currentCandidateId = null;
        let selectedBulkFiles = [];
        
        // ========== TAB SWITCHING ==========
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
        
        // ========== LOAD JOBS ==========
        async function loadJobs() {
            const res = await fetch('/api/jobs');
            allJobs = await res.json();
            const container = document.getElementById('jobsList');
            if(!allJobs.length) { container.innerHTML = '<div class="card no-click">No jobs yet. Create one.</div>'; return; }
            container.innerHTML = allJobs.map(j => `<div class="card no-click"><h3>${escapeHtml(j.title)}</h3>${j.company ? `<p>🏢 ${escapeHtml(j.company)}</p>` : ''}<small>${new Date(j.created_at).toLocaleDateString()}</small></div>`).join('');
            document.getElementById('jobSelect').innerHTML = '<option value="">-- Select Job --</option>' + allJobs.map(j => `<option value="${j.id}">${escapeHtml(j.title)}</option>`).join('');
        }
        
        // ========== LOAD CANDIDATES ==========
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
            if(!candidates.length) { container.innerHTML = '<div class="card no-click">No candidates yet. Upload resumes.</div>'; return; }
            container.innerHTML = candidates.map(c => {
                const name = (c.first_name + ' ' + c.last_name).trim() || 'Unknown';
                const skills = c.core_skills ? JSON.parse(c.core_skills) : [];
                const matchClass = c.match_score >= 70 ? 'match-high' : (c.match_score >= 40 ? 'match-medium' : 'match-low');
                return `<div class="card" onclick="viewCandidate(${c.id})">
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
        
        // ========== VIEW CANDIDATE ==========
        window.viewCandidate = async function(id) {
            currentCandidateId = id;
            const c = allCandidates.find(c => c.id == id);
            if (!c) return;
            
            const fullName = (c.first_name || '') + ' ' + (c.last_name || '');
            const skills = c.core_skills ? JSON.parse(c.core_skills) : [];
            const certs = c.certifications ? JSON.parse(c.certifications) : [];
            const workExp = c.work_experience ? JSON.parse(c.work_experience) : [];
            
            const docRes = await fetch(`/api/candidates/${id}/documents`);
            const documents = await docRes.json();
            const resumeDoc = documents.find(d => d.is_resume === 1);
            const otherDocs = documents.filter(d => !d.is_resume);
            
            document.getElementById('modalBody').innerHTML = `
                <div style="display: flex; gap: 10px; justify-content: flex-end; margin-bottom: 15px;">
                    <button class="btn btn-edit" onclick="openEditModal(${id})">✏️ Edit Profile</button>
                    <button class="btn btn-secondary" onclick="openDocModal(${id})">📎 Add Document</button>
                    <button class="btn btn-secondary" onclick="copyAllDetails()">📋 Copy All</button>
                </div>
                <div class="detail-row"><div class="detail-label">Full Name:</div><div class="detail-value">${escapeHtml(fullName.trim() || 'Unknown')}</div></div>
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
                
                <button class="btn" onclick="closeModal()" style="margin-top: 20px;">Close</button>
            `;
            document.getElementById('candidateModal').style.display = 'block';
        };
        
        window.copyAllDetails = function() {
            let text = '';
            document.querySelectorAll('#modalBody .detail-row, #modalBody .company-item, #modalBody .skill-with-years').forEach(el => {
                text += el.innerText + '\n';
            });
            navigator.clipboard.writeText(text);
            alert('Copied to clipboard!');
        };
        
        window.previewDocument = async function(docId) {
            try {
                const res = await fetch(`/api/documents/${docId}/preview`);
                const data = await res.json();
                document.getElementById('previewBody').innerHTML = data.type === 'image' ? 
                    `<img src="data:image/png;base64,${data.content}" style="max-width:100%;">` : 
                    `<div style="white-space: pre-wrap; background: white; padding: 15px; border-radius: 8px;">${escapeHtml(data.content)}</div>`;
                document.getElementById('previewModal').style.display = 'block';
            } catch(e) { alert('Cannot preview'); }
        };
        
        function closePreviewModal() { document.getElementById('previewModal').style.display = 'none'; }
        window.closePreviewModal = closePreviewModal;
        
        function closeModal() { document.getElementById('candidateModal').style.display = 'none'; }
        window.closeModal = closeModal;
        
        // ========== EDIT CANDIDATE ==========
        window.openEditModal = async function(id) {
            const c = allCandidates.find(c => c.id == id);
            if (!c) return;
            
            const skillsStr = c.core_skills ? JSON.parse(c.core_skills).map(s => s.skill).join(', ') : '';
            const certsStr = c.certifications ? JSON.parse(c.certifications).join(', ') : '';
            
            document.getElementById('editModalBody').innerHTML = `
                <form id="editForm">
                    <div class="flex"><div class="flex-1"><label>First Name</label><input type="text" id="editFirst" value="${escapeHtml(c.first_name || '')}"></div>
                    <div class="flex-1"><label>Middle Name</label><input type="text" id="editMiddle" value="${escapeHtml(c.middle_name || '')}"></div>
                    <div class="flex-1"><label>Last Name</label><input type="text" id="editLast" value="${escapeHtml(c.last_name || '')}"></div></div>
                    <div class="flex"><div class="flex-1"><label>Email</label><input type="email" id="editEmail" value="${escapeHtml(c.email || '')}"></div>
                    <div class="flex-1"><label>Phone</label><input type="text" id="editPhone" value="${escapeHtml(c.phone || '')}"></div></div>
                    <div class="flex"><div class="flex-1"><label>Current CTC</label><input type="text" id="editCurrentCTC" value="${escapeHtml(c.current_ctc || '')}"></div>
                    <div class="flex-1"><label>Expected CTC</label><input type="text" id="editExpectedCTC" value="${escapeHtml(c.expected_ctc || '')}"></div></div>
                    <label>Address</label><input type="text" id="editAddress" value="${escapeHtml(c.address || '')}">
                    <label>LinkedIn</label><input type="text" id="editLinkedin" value="${escapeHtml(c.linkedin || '')}">
                    <label>Current Role</label><input type="text" id="editRole" value="${escapeHtml(c.current_role || '')}">
                    <div class="flex"><div class="flex-1"><label>Status</label><select id="editStatus"><option value="working" ${c.employment_status === 'working' ? 'selected' : ''}>Working</option><option value="bench" ${c.employment_status === 'bench' ? 'selected' : ''}>On Bench</option><option value="notice_period" ${c.employment_status === 'notice_period' ? 'selected' : ''}>Notice Period</option></select></div>
                    <div class="flex-1"><label>Notice Days</label><input type="number" id="editNoticeDays" value="${c.notice_period_days || 0}"></div></div>
                    <label>Education</label><textarea id="editEducation" rows="2">${escapeHtml(c.education || '')}</textarea>
                    <label>Skills (comma separated)</label><input type="text" id="editSkills" value="${escapeHtml(skillsStr)}">
                    <label>Certifications (comma separated)</label><input type="text" id="editCerts" value="${escapeHtml(certsStr)}">
                    <div style="margin-top: 20px;"><button type="submit" class="btn">Save Changes</button><button type="button" class="btn btn-secondary" onclick="closeEditModal()">Cancel</button></div>
                </form>
            `;
            document.getElementById('editModal').style.display = 'block';
            
            document.getElementById('editForm').onsubmit = async (e) => {
                e.preventDefault();
                const skillsArray = document.getElementById('editSkills').value.split(',').map(s => ({skill: s.trim(), years_of_experience: 0})).filter(s => s.skill);
                const certsArray = document.getElementById('editCerts').value.split(',').map(c => c.trim()).filter(c => c);
                const data = {
                    first_name: document.getElementById('editFirst').value,
                    middle_name: document.getElementById('editMiddle').value,
                    last_name: document.getElementById('editLast').value,
                    email: document.getElementById('editEmail').value,
                    phone: document.getElementById('editPhone').value,
                    current_ctc: document.getElementById('editCurrentCTC').value,
                    expected_ctc: document.getElementById('editExpectedCTC').value,
                    address: document.getElementById('editAddress').value,
                    linkedin: document.getElementById('editLinkedin').value,
                    current_role: document.getElementById('editRole').value,
                    employment_status: document.getElementById('editStatus').value,
                    notice_period_days: parseInt(document.getElementById('editNoticeDays').value) || 0,
                    education: document.getElementById('editEducation').value,
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
        
        // ========== ADD DOCUMENT ==========
        window.openDocModal = function(id) {
            currentCandidateId = id;
            document.getElementById('docModal').style.display = 'block';
        };
        
        function closeDocModal() { document.getElementById('docModal').style.display = 'none'; }
        window.closeDocModal = closeDocModal;
        
        document.getElementById('uploadDocBtn').onclick = async function() {
            const file = document.getElementById('docFile').files[0];
            if (!file || !currentCandidateId) { alert('Select a file'); return; }
            const fd = new FormData(); fd.append('document', file); fd.append('candidate_id', currentCandidateId);
            document.getElementById('docUploadStatus').innerHTML = '<div class="spinner"></div>';
            try {
                const res = await fetch('/api/candidates/upload-document', { method: 'POST', body: fd });
                if (res.ok) { alert('Document uploaded!'); closeDocModal(); viewCandidate(currentCandidateId); }
                else alert('Upload failed');
            } catch(e) { alert('Upload failed'); }
            document.getElementById('docUploadStatus').innerHTML = '';
        };
        
        // ========== EXPORT ==========
        document.getElementById('exportBtn').onclick = () => window.location.href = '/api/export-candidates';
        
        // ========== SINGLE UPLOAD ==========
        document.getElementById('parseBtn').onclick = async function() {
            const file = document.getElementById('resumeFile').files[0];
            if(!file) { alert('Select a file'); return; }
            const fd = new FormData(); fd.append('resume', file);
            const div = document.getElementById('parseResult');
            div.innerHTML = '<div class="spinner"></div><p>Parsing...</p>';
            try {
                const res = await fetch('/api/parse-resume', { method: 'POST', body: fd });
                const result = await res.json();
                if(result.error) { div.innerHTML = `<div class="alert-error">${result.error}</div>`; return; }
                div.innerHTML = `<div class="alert-success"><h4>✅ Parsed</h4>
                    <p><strong>Name:</strong> ${escapeHtml(result.first_name || '')} ${escapeHtml(result.last_name || '')}</p>
                    <p><strong>Email:</strong> ${escapeHtml(result.email || '')}</p>
                    <p><strong>Phone:</strong> ${escapeHtml(result.phone || '')}</p>
                    <p><strong>Skills:</strong> ${result.core_skills ? result.core_skills.map(s => `<span class="skill-tag">${escapeHtml(s.skill)}</span>`).join('') : 'None'}</p>
                    <button id="saveBtn">💾 Save Candidate</button></div>`;
                document.getElementById('saveBtn').onclick = async function() {
                    const saveRes = await fetch('/api/candidates', { method: 'POST', headers: {'Content-Type':'application/json'}, body: JSON.stringify(result) });
                    if(saveRes.ok) { alert('Saved!'); div.innerHTML = ''; document.getElementById('resumeFile').value = ''; loadCandidates(); showPanel(2); }
                    else alert('Error');
                };
            } catch(e) { div.innerHTML = '<div class="alert-error">Error</div>'; }
        };
        
        // ========== BULK UPLOAD ==========
        document.getElementById('multiResumeFiles').addEventListener('change', function(e) {
            selectedBulkFiles = Array.from(e.target.files);
            const fileListDiv = document.getElementById('selectedFilesList');
            if (selectedBulkFiles.length > 0) {
                let html = '<strong>Selected files (' + selectedBulkFiles.length + '):</strong><br>';
                selectedBulkFiles.forEach((file, index) => {
                    html += `<div class="file-list-item">📄 ${escapeHtml(file.name)} (${(file.size / 1024).toFixed(1)} KB)<span class="remove-file" onclick="removeBulkFile(${index})">✕ Remove</span></div>`;
                });
                fileListDiv.innerHTML = html;
                fileListDiv.style.display = 'block';
            } else { fileListDiv.style.display = 'none'; }
        });
        
        window.removeBulkFile = function(index) {
            selectedBulkFiles.splice(index, 1);
            const dataTransfer = new DataTransfer();
            selectedBulkFiles.forEach(file => dataTransfer.items.add(file));
            document.getElementById('multiResumeFiles').files = dataTransfer.files;
            
            const fileListDiv = document.getElementById('selectedFilesList');
            if (selectedBulkFiles.length > 0) {
                let html = '<strong>Selected files (' + selectedBulkFiles.length + '):</strong><br>';
                selectedBulkFiles.forEach((file, idx) => {
                    html += `<div class="file-list-item">📄 ${escapeHtml(file.name)} (${(file.size / 1024).toFixed(1)} KB)<span class="remove-file" onclick="removeBulkFile(${idx})">✕ Remove</span></div>`;
                });
                fileListDiv.innerHTML = html;
                fileListDiv.style.display = 'block';
            } else { fileListDiv.style.display = 'none'; }
        };
        
        document.getElementById('bulkUploadBtn').onclick = async function() {
            if (selectedBulkFiles.length === 0) { alert('Select files first'); return; }
            const div = document.getElementById('bulkUploadResult');
            div.innerHTML = '<div class="spinner"></div><p>Processing...</p>';
            let success = 0, fail = 0, errors = [];
            for (let i = 0; i < selectedBulkFiles.length; i++) {
                const fd = new FormData(); fd.append('resume', selectedBulkFiles[i]);
                div.innerHTML = `<div class="progress-bar"><div class="progress-fill" style="width:${Math.round((i/selectedBulkFiles.length)*100)}%"></div></div><p>${i+1}/${selectedBulkFiles.length}: ${escapeHtml(selectedBulkFiles[i].name)}</p>`;
                try {
                    const res = await fetch('/api/parse-resume', { method: 'POST', body: fd });
                    const result = await res.json();
                    if (!result.error) {
                        const saveRes = await fetch('/api/candidates', { method: 'POST', headers: {'Content-Type':'application/json'}, body: JSON.stringify(result) });
                        if (saveRes.ok) success++;
                        else { fail++; errors.push(`${selectedBulkFiles[i].name}: Save failed`); }
                    } else { fail++; errors.push(`${selectedBulkFiles[i].name}: ${result.error}`); }
                } catch(e) { fail++; errors.push(`${selectedBulkFiles[i].name}: ${e.message}`); }
            }
            let html = `<div class="alert-success"><h4>✅ Complete!</h4><p>Success: ${success} | Failed: ${fail}</p>`;
            if (errors.length) html += `<div><strong>Errors:</strong><ul>${errors.map(e => `<li>${escapeHtml(e)}</li>`).join('')}</ul></div>`;
            html += `<button class="btn" onclick="document.getElementById('tab2').click()">View Candidates</button></div>`;
            div.innerHTML = html;
            selectedBulkFiles = [];
            document.getElementById('multiResumeFiles').value = '';
            document.getElementById('selectedFilesList').style.display = 'none';
            loadCandidates();
        };
        
        // ========== CREATE JOB ==========
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
                showPanel(1); loadJobs();
            } else { alert('Error'); }
        };
        
        // ========== ANALYZE ==========
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
                if(result.error) { div.innerHTML = `<div class="alert-error">${result.error}</div>`; return; }
                const matchClass = result.match_score >= 70 ? 'match-high' : (result.match_score >= 40 ? 'match-medium' : 'match-low');
                div.innerHTML = `<div class="alert-success"><h4>Analysis</h4><p>Score: <span class="${matchClass}">${result.match_score || 0}%</span></p><p>${result.recommendation || 'Review'}</p><small>✅ Saved</small></div>`;
                loadCandidates();
            } catch(e) { div.innerHTML = '<div class="alert-error">Failed</div>'; }
        };
        
        function escapeHtml(str) { if(!str) return ''; return str.replace(/[&<>]/g, function(m) { if(m==='&') return '&amp;'; if(m==='<') return '&lt;'; if(m==='>') return '&gt;'; return m; }); }
        
        showPanel(1);
        loadJobs();
        loadCandidates();
    });
</script>
</body>
</html>
'''

@app.route('/')
def index():
    return HTML_TEMPLATE

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
