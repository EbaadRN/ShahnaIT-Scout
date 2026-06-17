# app.py - COMPLETE WITH BULK RESUME UPLOAD
import os
import sqlite3
import json
import re
import io
import csv
import shutil
import base64
from datetime import datetime
from flask import Flask, render_template_string, request, jsonify, send_file, Response
from flask_cors import CORS
from werkzeug.utils import secure_filename
import PyPDF2
import docx
import requests

app = Flask(__name__)
CORS(app)

# Configuration
app.config['MAX_CONTENT_LENGTH'] = 50 * 1024 * 1024
app.config['UPLOAD_FOLDER'] = '/tmp'
app.config['DOCUMENTS_FOLDER'] = '/tmp/candidate_docs'
app.config['JOB_DOCUMENTS_FOLDER'] = '/tmp/job_docs'

os.makedirs(app.config['DOCUMENTS_FOLDER'], exist_ok=True)
os.makedirs(app.config['JOB_DOCUMENTS_FOLDER'], exist_ok=True)

# ============ DATABASE SETUP ============
DB_PATH = 'shahnai.db'

def init_db():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    
    c.execute('DROP TABLE IF EXISTS candidates')
    c.execute('''CREATE TABLE candidates (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        first_name TEXT, last_name TEXT, middle_name TEXT, phone TEXT, email TEXT,
        address TEXT, linkedin TEXT, other_social TEXT, current_role TEXT,
        current_ctc TEXT, expected_ctc TEXT,
        employment_status TEXT, notice_period_days INTEGER DEFAULT 0,
        work_experience TEXT, certifications TEXT, core_skills TEXT, education TEXT,
        resume_text TEXT, resume_filename TEXT, match_score INTEGER DEFAULT 0,
        recommendation TEXT DEFAULT '', detailed_analysis TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )''')
    
    c.execute('DROP TABLE IF EXISTS candidate_documents')
    c.execute('''CREATE TABLE candidate_documents (
        id INTEGER PRIMARY KEY AUTOINCREMENT, candidate_id INTEGER,
        filename TEXT, original_filename TEXT, file_path TEXT, file_type TEXT,
        is_resume BOOLEAN DEFAULT 0, uploaded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (candidate_id) REFERENCES candidates(id)
    )''')
    
    c.execute('DROP TABLE IF EXISTS jobs')
    c.execute('''CREATE TABLE jobs (
        id INTEGER PRIMARY KEY AUTOINCREMENT, title TEXT NOT NULL,
        company TEXT, description TEXT, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )''')
    
    c.execute('''CREATE TABLE IF NOT EXISTS job_documents (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        job_id INTEGER,
        filename TEXT,
        original_filename TEXT,
        file_path TEXT,
        file_type TEXT,
        uploaded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (job_id) REFERENCES jobs(id)
    )''')
    
    conn.commit()
    conn.close()
    print("✅ Database initialized")

init_db()

# ============ GROQ API SETUP ============
GROQ_ENABLED = False
GROQ_API_KEY = os.getenv('GROQ_API_KEY')

if GROQ_API_KEY and GROQ_API_KEY.startswith('gsk_'):
    GROQ_ENABLED = True
    print("✅✅✅ Groq API configured")

def call_groq_api(prompt, max_tokens=2500):
    if not GROQ_API_KEY:
        return None
    url = "https://api.groq.com/openai/v1/chat/completions"
    headers = {"Authorization": f"Bearer {GROQ_API_KEY}", "Content-Type": "application/json"}
    payload = {
        "model": "llama-3.3-70b-versatile",
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.1,
        "max_tokens": max_tokens
    }
    try:
        response = requests.post(url, json=payload, headers=headers, timeout=45)
        if response.status_code == 200:
            result = response.json()['choices'][0]['message']['content']
            result = result.strip()
            if result.startswith('```json'):
                result = result[7:]
            if result.startswith('```'):
                result = result[3:]
            if result.endswith('```'):
                result = result[:-3]
            return result
        return None
    except Exception as e:
        print(f"Groq error: {e}")
        return None

def parse_resume_with_groq(resume_text):
    prompt = f"""Parse this resume. Extract years of experience for each skill. Return ONLY valid JSON.

RESUME: {resume_text[:3500]}

Return: {{
    "first_name": "",
    "last_name": "",
    "middle_name": "",
    "phone": "",
    "email": "",
    "address": "",
    "linkedin": "",
    "current_role": "",
    "current_ctc": "",
    "expected_ctc": "",
    "employment_status": "working",
    "notice_period_days": 0,
    "work_experience": [],
    "certifications": [],
    "core_skills": [],
    "education": ""
}}"""
    response = call_groq_api(prompt, max_tokens=2500)
    if response:
        try:
            return json.loads(response)
        except:
            return None
    return None

def analyze_match_with_groq(resume_text, jd_text):
    if not GROQ_ENABLED:
        return None
    prompt = f"""Analyze this resume against the job description. Return ONLY valid JSON.

JOB: {jd_text[:2500]}
RESUME: {resume_text[:3000]}

Return: {{"match_score": 0, "recommendation": "hire/interview/reject", "executive_summary": {{"final_verdict": "text"}}, "pre_screening_questions": []}}"""
    response = call_groq_api(prompt, max_tokens=1500)
    if response:
        try:
            return json.loads(response)
        except:
            return None
    return None

# ============ RESUME PARSING HELPERS ============
def extract_text_from_pdf(file_path):
    try:
        text = ""
        with open(file_path, 'rb') as file:
            reader = PyPDF2.PdfReader(file)
            for page in reader.pages:
                text += page.extract_text()
        return text
    except:
        return ""

def extract_text_from_docx(file_path):
    try:
        doc = docx.Document(file_path)
        return "\n".join([p.text for p in doc.paragraphs])
    except:
        return ""

def extract_email(text):
    match = re.search(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b', text)
    return match.group(0) if match else ""

def extract_phone(text):
    match = re.search(r'\b\d{10}\b|\b\d{3}[-.]?\d{3}[-.]?\d{4}\b|\+\d{2}\s?\d{10}\b', text)
    return match.group(0) if match else ""

def extract_years_from_text(text, skill):
    patterns = [
        r'(\d+)\+?\s*years? of experience in ' + re.escape(skill),
        r'(\d+)\+?\s*years? in ' + re.escape(skill),
        r'(\d+)\+?\s*yrs? of experience with ' + re.escape(skill),
        r'(\d+)\+?\s*years?.*?' + re.escape(skill),
    ]
    for pattern in patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            return int(match.group(1))
    return 0

def extract_name_from_text(text):
    lines = text.strip().split('\n')
    name = lines[0].strip() if lines else "Unknown"
    name_parts = name.split()
    first_name = name_parts[0] if name_parts else ""
    last_name = name_parts[-1] if len(name_parts) > 1 else ""
    middle_name = " ".join(name_parts[1:-1]) if len(name_parts) > 2 else ""
    return first_name, last_name, middle_name

def fallback_parse_resume(text):
    first_name, last_name, middle_name = extract_name_from_text(text)
    email = extract_email(text)
    phone = extract_phone(text)
    
    common_skills = [
        'Python', 'Java', 'JavaScript', 'React', 'Angular', 'Node.js', 'SQL', 'AWS', 
        'Docker', 'Kubernetes', 'Git', 'Azure', 'Salesforce', 'Power Apps', 'Entra ID'
    ]
    found_skills = []
    for skill in common_skills:
        if skill.lower() in text.lower():
            years = extract_years_from_text(text, skill)
            found_skills.append({"skill": skill, "years_of_experience": years})
    
    return {
        'first_name': first_name,
        'last_name': last_name,
        'middle_name': middle_name,
        'phone': phone,
        'email': email,
        'address': "",
        'linkedin': "",
        'current_role': "",
        'current_ctc': "",
        'expected_ctc': "",
        'employment_status': "working",
        'notice_period_days': 0,
        'work_experience': [],
        'certifications': [],
        'core_skills': found_skills[:5],
        'education': "",
        'resume_text': text[:3000],
        'ai_used': False
    }

def save_candidate_to_db(candidate_data):
    skills = json.dumps(candidate_data.get('core_skills', []))
    work_exp = json.dumps(candidate_data.get('work_experience', []))
    certs = json.dumps(candidate_data.get('certifications', []))
    
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('''INSERT INTO candidates 
        (first_name, last_name, middle_name, phone, email, address, linkedin,
         current_role, current_ctc, expected_ctc,
         employment_status, notice_period_days, work_experience, certifications,
         core_skills, education, resume_text, resume_filename)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)''',
        (candidate_data.get('first_name'), candidate_data.get('last_name'), candidate_data.get('middle_name'),
         candidate_data.get('phone'), candidate_data.get('email'), candidate_data.get('address'), candidate_data.get('linkedin'),
         candidate_data.get('current_role'), candidate_data.get('current_ctc'), candidate_data.get('expected_ctc'),
         candidate_data.get('employment_status'), candidate_data.get('notice_period_days', 0),
         work_exp, certs, skills, candidate_data.get('education'), candidate_data.get('resume_text'), candidate_data.get('resume_filename')))
    
    candidate_id = c.lastrowid
    conn.commit()
    conn.close()
    return candidate_id

# ============ HTML TEMPLATE ============
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
        .tab-btn.active { background: #1A4D4A; color: white; }
        .card { background: white; padding: 15px; margin: 10px 0; border-radius: 8px; border-left: 4px solid #1A4D4A; cursor: pointer; transition: transform 0.2s; }
        .card:hover { transform: translateY(-2px); box-shadow: 0 2px 8px rgba(0,0,0,0.1); }
        .card.no-click { cursor: default; }
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
        .company-item { background: #F9F6F0; padding: 8px; margin-bottom: 5px; border-radius: 5px; border-left: 3px solid #1A4D4A; }
        .btn-edit { background: #C9A96E; }
        .btn-secondary { background: #6B7B7B; }
        .doc-link { cursor: pointer; color: #1A4D4A; text-decoration: underline; }
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
        <button class="tab-btn active" id="tabJobs">📋 Jobs</button>
        <button class="tab-btn" id="tabCandidates">👥 Candidates</button>
        <button class="tab-btn" id="tabUpload">📄 Upload Resume</button>
        <button class="tab-btn" id="tabCreateJob">➕ Create Job</button>
        <button class="tab-btn" id="tabAnalyze">🔍 Analyze Match</button>
    </div>
    
    <div id="jobsPanel"><div id="jobsList"></div></div>
    <div id="candidatesPanel" style="display:none;"><button id="exportBtn">📥 Export CSV</button><div class="filter-bar"><input type="text" id="searchBox" placeholder="Search..."><select id="scoreSelect"><option value="all">All Scores</option><option value="high">High (70%+)</option><option value="medium">Medium (40-69%)</option><option value="low">Low (<40%)</option></select><button id="clearBtn">Clear</button></div><div id="candidatesList"></div></div>
    
    <div id="uploadPanel" style="display:none;">
        <div class="card no-click">
            <h3>📄 Single Resume Upload</h3>
            <input type="file" id="resumeFile" accept=".pdf,.docx">
            <button id="parseBtn">🔍 Parse & Save</button>
            <div id="parseResult"></div>
        </div>
        
        <div class="card no-click" style="margin-top: 20px;">
            <h3>📚 Bulk Resume Upload (Select Multiple Files)</h3>
            <p>Hold Ctrl (or Cmd on Mac) to select multiple PDF/DOCX files</p>
            <input type="file" id="multiResumeFiles" multiple accept=".pdf,.docx">
            <div id="selectedFilesList" class="file-list" style="display:none;"></div>
            <button id="bulkUploadBtn" class="btn">🚀 Upload & Parse All</button>
            <div id="bulkUploadResult"></div>
        </div>
    </div>
    
    <div id="createJobPanel" style="display:none;"><div class="card no-click"><h3>➕ Create Job</h3><input type="text" id="jobTitle" placeholder="Job Title *"><input type="text" id="jobCompany" placeholder="Company"><textarea id="jobDesc" rows="4" placeholder="Job Description"></textarea><button id="createJobBtn">Create Job</button></div></div>
    <div id="analyzePanel" style="display:none;">
    <div class="card no-click">
        <h3>🔍 AI Match Analysis - Single Candidate</h3>
        <div class="flex">
            <div class="flex-1"><select id="jobSelect"></select></div>
            <div class="flex-1"><select id="candidateSelect"></select></div>
        </div>
        <button id="analyzeBtn">🤖 Run Analysis</button>
        <div id="analysisResult"></div>
    </div>
    
    <div class="card no-click" style="margin-top: 20px;">
        <h3>📊 Match JD Against ALL Candidates</h3>
        <p>Select a Job to see how ALL candidates match (even 1% matches)</p>
        <div class="flex">
            <div class="flex-1"><select id="batchJobSelect"></select></div>
        </div>
        <button id="batchAnalyzeBtn">🎯 Match Against All Candidates</button>
        <div id="batchAnalysisResult"></div>
    </div>
</div>
</div>

<!-- Modals -->
<div id="candidateModal" class="modal"><div class="modal-content"><div class="modal-header"><h2>Candidate Profile</h2><span class="close" onclick="closeModal()">&times;</span></div><div class="modal-body" id="modalBody"></div></div></div>
<div id="editModal" class="modal"><div class="modal-content"><div class="modal-header"><h2>✏️ Edit Candidate</h2><span class="close" onclick="closeEditModal()">&times;</span></div><div class="modal-body" id="editModalBody"></div></div></div>
<div id="docModal" class="modal"><div class="modal-content"><div class="modal-header"><h2>📎 Add Document</h2><span class="close" onclick="closeDocModal()">&times;</span></div><div class="modal-body"><input type="file" id="docFile"><button id="uploadDocBtn" class="btn">Upload</button><div id="docUploadStatus"></div></div></div></div>
<div id="previewModal" class="modal"><div class="modal-content"><div class="modal-header"><h2>Preview</h2><span class="close" onclick="closePreviewModal()">&times;</span></div><div class="modal-body" id="previewBody"></div></div></div>
<div id="editJobModal" class="modal"><div class="modal-content"><div class="modal-header"><h2>✏️ Edit Job</h2><span class="close" onclick="closeEditJobModal()">&times;</span></div><div class="modal-body" id="editJobModalBody"></div></div></div>

<script>
    let allJobs = [], allCandidates = [], currentCandidateId = null;
    let selectedBulkFiles = [];
    
    // Tab switching
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
        if(panel === 'jobs') document.getElementById('tabJobs').classList.add('active');
        if(panel === 'candidates') document.getElementById('tabCandidates').classList.add('active');
        if(panel === 'upload') document.getElementById('tabUpload').classList.add('active');
        if(panel === 'createJob') document.getElementById('tabCreateJob').classList.add('active');
        if(panel === 'analyze') document.getElementById('tabAnalyze').classList.add('active');
    }
    
    async function loadJobs() {
        const res = await fetch('/api/jobs');
        allJobs = await res.json();
        const container = document.getElementById('jobsList');
        if(!allJobs.length) { container.innerHTML = '<div class="card no-click">No jobs yet</div>'; return; }
        container.innerHTML = allJobs.map(j => `<div class="card" onclick="editJob(${j.id})"><h3>${escapeHtml(j.title)}</h3>${j.company ? `<p>🏢 ${escapeHtml(j.company)}</p>` : ''}<small>${new Date(j.created_at).toLocaleDateString()}</small></div>`).join('');
        document.getElementById('jobSelect').innerHTML = '<option value="">-- Select Job --</option>' + allJobs.map(j => `<option value="${j.id}">${escapeHtml(j.title)}</option>`).join('');
        document.getElementById('batchJobSelect').innerHTML = '<option value="">-- Select Job --</option>' + allJobs.map(j => `<option value="${j.id}">${escapeHtml(j.title)}</option>`).join('');
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
        if(!candidates.length) { container.innerHTML = '<div class="card no-click">No candidates</div>'; return; }
        container.innerHTML = candidates.map(c => {
            const name = (c.first_name + ' ' + c.last_name).trim() || 'Unknown';
            const skills = c.core_skills ? JSON.parse(c.core_skills) : [];
            const matchClass = c.match_score >= 70 ? 'match-high' : (c.match_score >= 40 ? 'match-medium' : 'match-low');
            return `<div class="card" onclick="viewCandidate(${c.id})"><h3>👤 ${escapeHtml(name)}</h3>${c.email ? `<p>📧 ${escapeHtml(c.email)}</p>` : ''}<p>🔧 ${skills.slice(0,3).map(s => `<span class="skill-tag">${escapeHtml(s.skill)}</span>`).join('')}</p>${c.match_score ? `<p>🎯 Score: <span class="${matchClass}">${c.match_score}%</span></p>` : ''}<small>${new Date(c.created_at).toLocaleDateString()}</small></div>`;
        }).join('');
    }
    
    document.getElementById('searchBox').onkeyup = filterCandidates;
    document.getElementById('scoreSelect').onchange = filterCandidates;
    document.getElementById('clearBtn').onclick = function() { document.getElementById('searchBox').value = ''; document.getElementById('scoreSelect').value = 'all'; filterCandidates(); };
    
    // Edit Job
    window.editJob = async function(id) {
        const job = allJobs.find(j => j.id == id);
        const docRes = await fetch(`/api/jobs/${id}/documents`);
        const documents = await docRes.json();
        let docsHtml = '';
        if (documents.length > 0) {
            docsHtml = '<h4>Attached Documents</h4><div class="file-list">';
            documents.forEach(doc => { docsHtml += `<div class="file-list-item">📄 ${escapeHtml(doc.original_filename)} <span class="remove-file" onclick="deleteJobDocument(${doc.id}, ${id})">✕ Remove</span></div>`; });
            docsHtml += '</div>';
        }
        document.getElementById('editJobModalBody').innerHTML = `<form id="editJobForm"><label>Job Title</label><input type="text" id="editJobTitle" value="${escapeHtml(job.title || '')}"><label>Company</label><input type="text" id="editJobCompany" value="${escapeHtml(job.company || '')}"><label>Description</label><textarea id="editJobDesc" rows="5">${escapeHtml(job.description || '')}</textarea><h4>Attach Document</h4><input type="file" id="jobDocFile"><button type="button" id="uploadJobDocBtn" class="btn btn-secondary">Upload</button><div id="jobDocUploadStatus"></div>${docsHtml}<div style="margin-top:20px;"><button type="submit" class="btn">Save</button><button type="button" class="btn btn-secondary" onclick="closeEditJobModal()">Cancel</button></div></form>`;
        document.getElementById('editJobModal').style.display = 'block';
        document.getElementById('uploadJobDocBtn').onclick = async function() {
            const file = document.getElementById('jobDocFile').files[0];
            if (!file) return;
            const fd = new FormData(); fd.append('document', file); fd.append('job_id', id);
            document.getElementById('jobDocUploadStatus').innerHTML = '<div class="spinner"></div>';
            const res = await fetch('/api/jobs/upload-document', { method: 'POST', body: fd });
            if (res.ok) { alert('Uploaded!'); editJob(id); }
            document.getElementById('jobDocUploadStatus').innerHTML = '';
        };
        document.getElementById('editJobForm').onsubmit = async (e) => {
            e.preventDefault();
            const data = { title: document.getElementById('editJobTitle').value, company: document.getElementById('editJobCompany').value, description: document.getElementById('editJobDesc').value };
            const res = await fetch(`/api/jobs/${id}`, { method: 'PUT', headers: {'Content-Type':'application/json'}, body: JSON.stringify(data) });
            if (res.ok) { alert('Job updated!'); closeEditJobModal(); loadJobs(); }
        };
    };
    
    window.deleteJobDocument = async function(docId, jobId) {
        if (confirm('Delete?')) { await fetch(`/api/jobs/documents/${docId}`, { method: 'DELETE' }); editJob(jobId); }
    };
    function closeEditJobModal() { document.getElementById('editJobModal').style.display = 'none'; }
    window.closeEditJobModal = closeEditJobModal;
    
    // View Candidate
    window.viewCandidate = async function(id) {
        currentCandidateId = id;
        const c = allCandidates.find(c => c.id == id);
        const skills = c.core_skills ? JSON.parse(c.core_skills) : [];
        const certs = c.certifications ? JSON.parse(c.certifications) : [];
        const workExp = c.work_experience ? JSON.parse(c.work_experience) : [];
        const docRes = await fetch(`/api/candidates/${id}/documents`);
        const documents = await docRes.json();
        const resumeDoc = documents.find(d => d.is_resume === 1);
        const otherDocs = documents.filter(d => !d.is_resume);
        
        document.getElementById('modalBody').innerHTML = <div style="display:flex; gap:10px; justify-content:flex-end; margin-bottom:15px;"><button class="btn btn-edit" onclick="openEditModal(${c.id})">✏️ Edit</button><button class="btn btn-secondary" onclick="openDocModal(${c.id})">📎 Add Document</button><button class="btn btn-secondary" onclick="copyAllDetails()">📋 Copy</button><button class="btn" style="background: #C9A96E; color: white;" onclick="exportPDF(${c.id})">📄 Export PDF</button></div>
            <div class="detail-row"><div class="detail-label">Name:</div><div class="detail-value">${escapeHtml((c.first_name||'') + ' ' + (c.last_name||''))}</div></div>
            <div class="detail-row"><div class="detail-label">Phone:</div><div class="detail-value">${escapeHtml(c.phone || 'N/A')}</div></div>
            <div class="detail-row"><div class="detail-label">Email:</div><div class="detail-value">${escapeHtml(c.email || 'N/A')}</div></div>
            <div class="detail-row"><div class="detail-label">Role:</div><div class="detail-value">${escapeHtml(c.current_role || 'N/A')}</div></div>
            <div class="detail-row"><div class="detail-label">CTC:</div><div class="detail-value">Current: ${escapeHtml(c.current_ctc || 'N/A')} | Expected: ${escapeHtml(c.expected_ctc || 'N/A')}</div></div>
            <div class="detail-row"><div class="detail-label">Status:</div><div class="detail-value">${escapeHtml(c.employment_status || 'N/A')}${c.notice_period_days ? ` (${c.notice_period_days} days)` : ''}</div></div>
            <h4>Work Experience</h4>${workExp.map(w => `<div class="company-item"><strong>${escapeHtml(w.company)}</strong> — ${escapeHtml(w.role)}<br><small>${escapeHtml(w.start_date||'')} - ${escapeHtml(w.end_date||'Present')}</small></div>`).join('') || '<p>None</p>'}
            <h4>Skills</h4>${skills.map(s => `<span class="skill-with-years">${escapeHtml(s.skill)} (${s.years_of_experience||0}y)</span>`).join('') || '<p>None</p>'}
            <h4>Certifications</h4>${certs.map(cert => `<div>📜 ${escapeHtml(cert)}</div>`).join('') || '<p>None</p>'}
            <h4>Resume</h4>${resumeDoc ? `<div><span class="doc-link" onclick="previewDocument(${resumeDoc.id})">📄 ${escapeHtml(resumeDoc.original_filename)}</span> <span style="background:#1B6B2E;color:white;padding:2px 8px;border-radius:12px;font-size:10px;">Original</span></div>` : '<p>None</p>'}
                        <h4>Other Documents</h4>${otherDocs.map(d => `<div><span class="doc-link" onclick="previewDocument(${d.id})">📄 ${escapeHtml(d.original_filename)}</span></div>`).join('') || '<p>None</p>'}
            
            <h4>📝 Notes</h4>
            <div id="notesList-${c.id}" style="max-height: 200px; overflow-y: auto; margin-bottom: 10px;">
                <div class="spinner" style="width: 20px; height: 20px;"></div>
            </div>
            <div style="display: flex; gap: 8px; margin-top: 5px;">
                <input type="text" id="newNote-${c.id}" placeholder="Add a note..." style="flex: 1; padding: 6px;">
                <button class="btn btn-secondary" style="padding: 6px 12px;" onclick="addNote(${c.id})">➕ Add</button>
            </div>
            
            <button class="btn" onclick="closeModal()">Close</button>`;
            loadNotes(c.id);
        document.getElementById('candidateModal').style.display = 'block';
    };
    
    window.previewDocument = async function(docId) {
        const res = await fetch(`/api/documents/${docId}/preview`);
        const data = await res.json();
        document.getElementById('previewBody').innerHTML = data.type === 'image' ? `<img src="data:image/png;base64,${data.content}" style="max-width:100%;">` : `<div style="white-space:pre-wrap; background:white; padding:15px;">${escapeHtml(data.content)}</div>`;
        document.getElementById('previewModal').style.display = 'block';
    };
    function closePreviewModal() { document.getElementById('previewModal').style.display = 'none'; }
    window.closePreviewModal = closePreviewModal;
    
    window.copyAllDetails = function() {
        let text = '';
        document.querySelectorAll('#modalBody .detail-row, #modalBody .company-item, #modalBody .skill-with-years').forEach(el => text += el.innerText + '\\n');
        navigator.clipboard.writeText(text);
        alert('Copied!');
    };
    
    function closeModal() { document.getElementById('candidateModal').style.display = 'none'; }
    window.closeModal = closeModal;
    function closeEditModal() { document.getElementById('editModal').style.display = 'none'; }
    window.closeEditModal = closeEditModal;
    function closeDocModal() { document.getElementById('docModal').style.display = 'none'; }
    window.closeDocModal = closeDocModal;
    
    window.openEditModal = async function(id) {
        const c = allCandidates.find(c => c.id == id);
        const skillsStr = c.core_skills ? JSON.parse(c.core_skills).map(s => s.skill).join(', ') : '';
        const certsStr = c.certifications ? JSON.parse(c.certifications).join(', ') : '';
        document.getElementById('editModalBody').innerHTML = `<form id="editForm"><div class="flex"><div class="flex-1"><label>First Name</label><input type="text" id="editFirst" value="${escapeHtml(c.first_name||'')}"></div><div class="flex-1"><label>Middle</label><input type="text" id="editMiddle" value="${escapeHtml(c.middle_name||'')}"></div><div class="flex-1"><label>Last</label><input type="text" id="editLast" value="${escapeHtml(c.last_name||'')}"></div></div><div class="flex"><div class="flex-1"><label>Email</label><input type="email" id="editEmail" value="${escapeHtml(c.email||'')}"></div><div class="flex-1"><label>Phone</label><input type="text" id="editPhone" value="${escapeHtml(c.phone||'')}"></div></div><div class="flex"><div class="flex-1"><label>Current CTC</label><input type="text" id="editCurrentCTC" value="${escapeHtml(c.current_ctc||'')}"></div><div class="flex-1"><label>Expected CTC</label><input type="text" id="editExpectedCTC" value="${escapeHtml(c.expected_ctc||'')}"></div></div><label>Address</label><input type="text" id="editAddress" value="${escapeHtml(c.address||'')}"><label>LinkedIn</label><input type="text" id="editLinkedin" value="${escapeHtml(c.linkedin||'')}"><label>Current Role</label><input type="text" id="editRole" value="${escapeHtml(c.current_role||'')}"><div class="flex"><div class="flex-1"><label>Status</label><select id="editStatus"><option value="working" ${c.employment_status==='working'?'selected':''}>Working</option><option value="bench" ${c.employment_status==='bench'?'selected':''}>Bench</option><option value="notice_period" ${c.employment_status==='notice_period'?'selected':''}>Notice</option></select></div><div class="flex-1"><label>Notice Days</label><input type="number" id="editNoticeDays" value="${c.notice_period_days||0}"></div></div><label>Education</label><textarea id="editEducation" rows="2">${escapeHtml(c.education||'')}</textarea><label>📝 Notes</label><textarea id="editNotes" rows="3" style="background: #FFF8E1; border-left: 4px solid #C9A96E; padding: 10px;">${escapeHtml(c.notes||'')}</textarea><label>Skills (comma)</label><input type="text" id="editSkills" value="${escapeHtml(skillsStr)}"><label>Certifications (comma)</label><input type="text" id="editCerts" value="${escapeHtml(certsStr)}"><div style="margin-top:20px;"><button type="submit" class="btn">Save</button><button type="button" class="btn btn-secondary" onclick="closeEditModal()">Cancel</button></div></form>`;
        document.getElementById('editModal').style.display = 'block';
        document.getElementById('editForm').onsubmit = async (e) => {
            e.preventDefault();
            const skillsArray = document.getElementById('editSkills').value.split(',').map(s => ({skill: s.trim(), years_of_experience: 0})).filter(s => s.skill);
            const certsArray = document.getElementById('editCerts').value.split(',').map(c => c.trim()).filter(c => c);
            const data = {
                first_name: document.getElementById('editFirst').value, middle_name: document.getElementById('editMiddle').value, last_name: document.getElementById('editLast').value,
                email: document.getElementById('editEmail').value, phone: document.getElementById('editPhone').value,
                current_ctc: document.getElementById('editCurrentCTC').value, expected_ctc: document.getElementById('editExpectedCTC').value,
                address: document.getElementById('editAddress').value, linkedin: document.getElementById('editLinkedin').value,
                current_role: document.getElementById('editRole').value, employment_status: document.getElementById('editStatus').value,
                notice_period_days: parseInt(document.getElementById('editNoticeDays').value) || 0, education: document.getElementById('editEducation').value,
                notes: document.getElementById('editNotes').value, core_skills: JSON.stringify(skillsArray), certifications: JSON.stringify(certsArray)
            };
            const res = await fetch(`/api/candidates/${id}`, { method: 'PUT', headers: {'Content-Type':'application/json'}, body: JSON.stringify(data) });
            if (res.ok) { alert('Updated!'); closeEditModal(); loadCandidates(); viewCandidate(id); }
            else alert('Error');
        };
    };
    
    window.openDocModal = function(id) { currentCandidateId = id; document.getElementById('docModal').style.display = 'block'; };
    document.getElementById('uploadDocBtn').onclick = async function() {
        const file = document.getElementById('docFile').files[0];
        if (!file || !currentCandidateId) return;
        const fd = new FormData(); fd.append('document', file); fd.append('candidate_id', currentCandidateId);
        document.getElementById('docUploadStatus').innerHTML = '<div class="spinner"></div>';
        const res = await fetch('/api/candidates/upload-document', { method: 'POST', body: fd });
        if (res.ok) { alert('Uploaded!'); closeDocModal(); viewCandidate(currentCandidateId); }
        document.getElementById('docUploadStatus').innerHTML = '';
    };
    
    document.getElementById('exportBtn').onclick = () => window.location.href = '/api/export-candidates';
    
    document.getElementById('parseBtn').onclick = async function() {
        const file = document.getElementById('resumeFile').files[0];
        if(!file) return;
        const fd = new FormData(); fd.append('resume', file);
        const div = document.getElementById('parseResult');
        div.innerHTML = '<div class="spinner"></div><p>Parsing...</p>';
        const res = await fetch('/api/parse-resume', { method: 'POST', body: fd });
        const result = await res.json();
        if(result.error) { div.innerHTML = `<div class="alert-error">${result.error}</div>`; return; }
        div.innerHTML = `<div class="alert-success"><h4>✅ Parsed</h4><p><strong>Name:</strong> ${escapeHtml(result.first_name||'')} ${escapeHtml(result.last_name||'')}</p><p><strong>Email:</strong> ${escapeHtml(result.email||'')}</p><p><strong>Phone:</strong> ${escapeHtml(result.phone||'')}</p><p><strong>Skills:</strong> ${result.core_skills ? result.core_skills.map(s => `<span class="skill-tag">${escapeHtml(s.skill)}</span>`).join('') : 'None'}</p><button id="saveBtn">💾 Save</button></div>`;
        document.getElementById('saveBtn').onclick = async function() {
            const saveRes = await fetch('/api/candidates', { method: 'POST', headers: {'Content-Type':'application/json'}, body: JSON.stringify(result) });
            if(saveRes.ok) { alert('Saved! Resume auto-attached!'); div.innerHTML = ''; document.getElementById('resumeFile').value = ''; loadCandidates(); showPanel('candidates'); }
            else alert('Error');
        };
    };
    
    document.getElementById('createJobBtn').onclick = async function() {
        const data = { title: document.getElementById('jobTitle').value, company: document.getElementById('jobCompany').value, description: document.getElementById('jobDesc').value };
        if(!data.title) return;
        const res = await fetch('/api/jobs', { method: 'POST', headers: {'Content-Type':'application/json'}, body: JSON.stringify(data) });
        if(res.ok) { alert('Job created!'); document.getElementById('jobTitle').value = ''; document.getElementById('jobCompany').value = ''; document.getElementById('jobDesc').value = ''; showPanel('jobs'); loadJobs(); }
        else alert('Error');
    };
    
    document.getElementById('analyzeBtn').onclick = async function() {
        const jobId = document.getElementById('jobSelect').value;
        const candidateId = document.getElementById('candidateSelect').value;
        if(!jobId || !candidateId) return;
        const job = allJobs.find(j => j.id == jobId);
        const cand = allCandidates.find(c => c.id == candidateId);
        const div = document.getElementById('analysisResult');
        div.innerHTML = '<div class="spinner"></div><p>Analyzing...</p>';
        const res = await fetch('/api/analyze-match', { method: 'POST', headers: {'Content-Type':'application/json'}, body: JSON.stringify({ job_id: jobId, candidate_id: candidateId, jd_text: job.description || '', resume_text: cand.resume_text || '' }) });
        const result = await res.json();
        if(result.error) { div.innerHTML = `<div class="alert-error">${result.error}</div>`; return; }
        const matchClass = result.match_score >= 70 ? 'match-high' : (result.match_score >= 40 ? 'match-medium' : 'match-low');
        div.innerHTML = `<div class="alert-success"><h4>Analysis</h4><p>Score: <span class="${matchClass}">${result.match_score || 0}%</span></p><p>${result.recommendation || 'Review'}</p><small>✅ Saved</small></div>`;
        loadCandidates();
    };
    
    // ========== BULK RESUME UPLOAD ==========
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
        } else {
            fileListDiv.style.display = 'none';
        }
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
        } else {
            fileListDiv.style.display = 'none';
        }
    };
    
    document.getElementById('bulkUploadBtn').onclick = async function() {
        if (selectedBulkFiles.length === 0) {
            alert('Please select files first');
            return;
        }
        
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
            div.innerHTML = `<div class="progress-bar"><div class="progress-fill" style="width: ${percent}%"></div></div>
    <div style="max-height: 300px; overflow-y: auto; margin-top: 10px;">
    <div><strong>📄 ${i+1} of ${selectedBulkFiles.length}:</strong> ${escapeHtml(file.name)}</div>
    <div id="liveStatus${i}" style="font-size: 13px; margin-left: 20px; margin-bottom: 10px;">⏳ Parsing...</div>
    </div>`;
            
            try {
                const res = await fetch('/api/parse-resume', { method: 'POST', body: fd });
                const result = await res.json();
document.getElementById(`liveStatus${i}`).innerHTML = result.error ? '❌ Parse failed: ' + escapeHtml(result.error) : '✅ Parsed successfully, saving...';
                
                if (result.error) {
                    failCount++;
                    errors.push(`${file.name}: ${result.error}`);
                } else {
                    const saveRes = await fetch('/api/candidates', { 
                        method: 'POST', 
                        headers: {'Content-Type': 'application/json'}, 
                        body: JSON.stringify(result) 
                    });
                    document.getElementById(`liveStatus${i}`).innerHTML = saveRes.ok ? '✅ Saved! Resume auto-attached.' : '❌ Save failed';
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
                document.getElementById(`liveStatus${i}`).innerHTML = `❌ Error: ${escapeHtml(e.message)}`;
            }
        }
        
        let resultHtml = `<div class="alert-success"><h4>✅ Bulk Upload Complete!</h4>`;
        resultHtml += `<p><strong>Total files:</strong> ${selectedBulkFiles.length}</p>`;
        resultHtml += `<p><strong>Successfully saved:</strong> ${successCount}</p>`;
        resultHtml += `<p><strong>Failed:</strong> ${failCount}</p>`;
        
        if (errors.length > 0 && errors.length <= 10) {
            resultHtml += `<div style="margin-top: 10px;"><strong>⚠️ Errors:</strong><ul>`;
            errors.forEach(err => { resultHtml += `<li>${escapeHtml(err)}</li>`; });
            resultHtml += `</ul></div>`;
        } else if (errors.length > 10) {
            resultHtml += `<p><strong>⚠️ ${errors.length} errors occurred. Check console for details.</strong></p>`;
        }
        
        resultHtml += `<button class="btn" onclick="document.getElementById('tabCandidates').click()" style="margin-top: 15px;">View All Candidates</button></div>`;
        div.innerHTML = resultHtml;
        
        // Clear selection
        selectedBulkFiles = [];
        document.getElementById('multiResumeFiles').value = '';
        document.getElementById('selectedFilesList').style.display = 'none';
        
        loadCandidates();
    };

        // ========== BATCH ANALYZE - Match JD Against ALL Candidates ==========
    document.getElementById('batchAnalyzeBtn').onclick = async function() {
        const jobId = document.getElementById('batchJobSelect').value;
        if (!jobId) { alert('Please select a Job'); return; }
        
        const job = allJobs.find(j => j.id == jobId);
        if (!job) { alert('Job not found'); return; }
        
        const div = document.getElementById('batchAnalysisResult');
        div.innerHTML = '<div class="spinner"></div><p>📊 Analyzing ' + allCandidates.length + ' candidates...</p>';
        
        try {
            const res = await fetch('/api/batch-analyze', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({ jd_text: job.description || '' })
            });
            const results = await res.json();
            
            if (results.error) {
                div.innerHTML = `<div class="alert-error">${results.error}</div>`;
                return;
            }
            
            let html = `<div class="alert-success"><h4>📊 Analysis Complete</h4>`;
            html += `<p><strong>Job:</strong> ${escapeHtml(job.title)}</p>`;
            html += `<p><strong>Total Candidates:</strong> ${results.length}</p>`;
            html += `<p><strong>Candidates with any match (>0%):</strong> ${results.filter(r => r.match_score > 0).length}</p>`;
            html += `<hr><div style="max-height: 500px; overflow-y: auto;">`;
            
            results.forEach((r, index) => {
                const matchClass = r.match_score >= 70 ? 'match-high' : (r.match_score >= 40 ? 'match-medium' : 'match-low');
                html += `<div class="card" style="cursor: pointer; margin: 8px 0;" onclick="viewCandidate(${r.candidate_id})">
                    <div style="display: flex; justify-content: space-between; align-items: center;">
                        <div><strong>#${index + 1}</strong> 👤 ${escapeHtml(r.name)}${r.email ? `<br><small>📧 ${escapeHtml(r.email)}</small>` : ''}</div>
                        <div><span class="${matchClass}">${r.match_score}%</span><br><small>${r.recommendation || 'Review'}</small></div>
                    </div>
                </div>`;
            });
            
            html += `</div><button class="btn" onclick="document.getElementById('tabCandidates').click()" style="margin-top:15px;">View All Candidates</button></div>`;
            div.innerHTML = html;
            
        } catch(e) {
            div.innerHTML = '<div class="alert-error">Analysis failed</div>';
        }
    };
        // ========== NOTES FUNCTIONS ==========
    async function loadNotes(candidateId) {
        const container = document.getElementById(`notesList-${candidateId}`);
        if (!container) return;
        
        try {
            const res = await fetch(`/api/candidates/${candidateId}/notes`);
            const notes = await res.json();
            
            if (notes.length === 0) {
                container.innerHTML = '<p style="color: #666; font-style: italic; margin: 5px 0;">No notes yet. Add one above.</p>';
                return;
            }
            
            let html = '';
            notes.forEach(note => {
                const date = new Date(note.created_at).toLocaleString();
                html += `
                    <div style="background: #F9F6F0; padding: 8px; border-radius: 6px; margin-bottom: 6px; border-left: 3px solid #1A4D4A;">
                        <div style="display: flex; justify-content: space-between; align-items: flex-start;">
                            <div style="flex: 1; font-size: 13px;">${escapeHtml(note.note_text)}</div>
                            <button class="btn" style="background: #B22222; padding: 2px 8px; font-size: 10px; margin-left: 8px;" onclick="deleteNote(${note.id}, ${candidateId})">✕</button>
                        </div>
                        <small style="color: #666; font-size: 10px;">📅 ${date}</small>
                    </div>
                `;
            });
            container.innerHTML = html;
        } catch(e) {
            container.innerHTML = '<p style="color: #B22222;">Failed to load notes</p>';
        }
    }
    
    window.addNote = async function(candidateId) {
        const input = document.getElementById(`newNote-${candidateId}`);
        const noteText = input.value.trim();
        
        if (!noteText) {
            alert('Please enter a note');
            return;
        }
        
        try {
            const res = await fetch(`/api/candidates/${candidateId}/notes`, {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({ note_text: noteText })
            });
            
            if (res.ok) {
                input.value = '';
                loadNotes(candidateId);
            } else {
                alert('Failed to add note');
            }
        } catch(e) {
            alert('Error adding note');
        }
    };
    
    window.deleteNote = async function(noteId, candidateId) {
        if (!confirm('Delete this note?')) return;
        
        try {
            const res = await fetch(`/api/candidates/notes/${noteId}`, {
                method: 'DELETE'
            });
            
            if (res.ok) {
                loadNotes(candidateId);
            } else {
                alert('Failed to delete note');
            }
        } catch(e) {
            alert('Error deleting note');
        }
    };
    function escapeHtml(str) { if(!str) return ''; return str.replace(/[&<>]/g, function(m) { if(m==='&') return '&amp;'; if(m==='<') return '&lt;'; if(m==='>') return '&gt;'; return m; }); }
    
    showPanel('jobs');
    loadJobs();
    loadCandidates();
</script>
</body>
</html>
'''

# ============ API ROUTES ============
@app.route('/')
def index():
    return HTML_TEMPLATE

@app.route('/api/jobs', methods=['GET'])
def get_jobs():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    c.execute('SELECT * FROM jobs ORDER BY created_at DESC')
    jobs = [dict(row) for row in c.fetchall()]
    conn.close()
    return jsonify(jobs)

@app.route('/api/jobs', methods=['POST'])
def create_job():
    data = request.json
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('INSERT INTO jobs (title, company, description) VALUES (?, ?, ?)',
              (data.get('title'), data.get('company'), data.get('description', '')))
    conn.commit()
    conn.close()
    return jsonify({'message': 'Job created'})

@app.route('/api/jobs/<int:job_id>', methods=['PUT'])
def update_job(job_id):
    data = request.json
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('UPDATE jobs SET title = ?, company = ?, description = ? WHERE id = ?',
              (data.get('title'), data.get('company'), data.get('description', ''), job_id))
    conn.commit()
    conn.close()
    return jsonify({'message': 'Job updated'})

@app.route('/api/jobs/<int:job_id>/documents', methods=['GET'])
def get_job_documents(job_id):
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    c.execute('SELECT * FROM job_documents WHERE job_id = ? ORDER BY uploaded_at DESC', (job_id,))
    docs = [dict(row) for row in c.fetchall()]
    conn.close()
    return jsonify(docs)

@app.route('/api/jobs/upload-document', methods=['POST'])
def upload_job_document():
    job_id = request.form.get('job_id')
    if 'document' not in request.files:
        return jsonify({'error': 'No file'}), 400
    file = request.files['document']
    if file.filename == '':
        return jsonify({'error': 'No file'}), 400
    
    original_filename = file.filename
    filename = secure_filename(f"{job_id}_{datetime.now().timestamp()}_{file.filename}")
    filepath = os.path.join(app.config['JOB_DOCUMENTS_FOLDER'], filename)
    file.save(filepath)
    
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('INSERT INTO job_documents (job_id, filename, original_filename, file_path, file_type) VALUES (?, ?, ?, ?, ?)',
              (job_id, filename, original_filename, filepath, original_filename.split('.')[-1]))
    conn.commit()
    conn.close()
    return jsonify({'message': 'Document uploaded'})

@app.route('/api/jobs/documents/<int:doc_id>', methods=['DELETE'])
def delete_job_document(doc_id):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('SELECT file_path FROM job_documents WHERE id = ?', (doc_id,))
    row = c.fetchone()
    if row and os.path.exists(row[0]):
        os.remove(row[0])
    c.execute('DELETE FROM job_documents WHERE id = ?', (doc_id,))
    conn.commit()
    conn.close()
    return jsonify({'message': 'Document deleted'})

@app.route('/api/candidates', methods=['GET'])
def get_candidates():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    c.execute('SELECT * FROM candidates ORDER BY created_at DESC')
    candidates = [dict(row) for row in c.fetchall()]
    conn.close()
    return jsonify(candidates)

@app.route('/api/candidates', methods=['POST'])
def create_candidate():
    data = request.json
    candidate_id = save_candidate_to_db(data)
    
    file_path = data.get('file_path')
    original_filename = data.get('original_filename')
    
    if file_path and os.path.exists(file_path):
        permanent_filename = secure_filename(f"{candidate_id}_{datetime.now().timestamp()}_{original_filename}")
        permanent_path = os.path.join(app.config['DOCUMENTS_FOLDER'], permanent_filename)
        shutil.move(file_path, permanent_path)
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        c.execute('INSERT INTO candidate_documents (candidate_id, filename, original_filename, file_path, file_type, is_resume) VALUES (?, ?, ?, ?, ?, ?)',
                  (candidate_id, permanent_filename, original_filename, permanent_path, original_filename.split('.')[-1], 1))
        conn.commit()
        conn.close()
    
    return jsonify({'message': 'Candidate saved', 'id': candidate_id})

@app.route('/api/candidates/<int:candidate_id>', methods=['PUT'])
def update_candidate(candidate_id):
    data = request.json
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('''UPDATE candidates SET 
        first_name=?, middle_name=?, last_name=?, email=?, phone=?, address=?, linkedin=?,
        current_role=?, current_ctc=?, expected_ctc=?,
        employment_status=?, notice_period_days=?, education=?,
        core_skills=?, certifications=?
        WHERE id=?''',
        (data.get('first_name'), data.get('middle_name'), data.get('last_name'),
         data.get('email'), data.get('phone'), data.get('address'), data.get('linkedin'),
         data.get('current_role'), data.get('current_ctc'), data.get('expected_ctc'),
         data.get('employment_status'), data.get('notice_period_days', 0),
         data.get('education'), data.get('core_skills'), data.get('certifications'), candidate_id))
    conn.commit()
    conn.close()
    return jsonify({'message': 'Candidate updated'})

@app.route('/api/candidates/<int:candidate_id>/documents', methods=['GET'])
def get_candidate_documents(candidate_id):
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    c.execute('SELECT * FROM candidate_documents WHERE candidate_id = ? ORDER BY is_resume DESC', (candidate_id,))
    docs = [dict(row) for row in c.fetchall()]
    conn.close()
    return jsonify(docs)

@app.route('/api/candidates/upload-document', methods=['POST'])
def upload_candidate_document():
    candidate_id = request.form.get('candidate_id')
    if 'document' not in request.files:
        return jsonify({'error': 'No file'}), 400
    file = request.files['document']
    if file.filename == '':
        return jsonify({'error': 'No file'}), 400
    
    original_filename = file.filename
    filename = secure_filename(f"{candidate_id}_{datetime.now().timestamp()}_{file.filename}")
    filepath = os.path.join(app.config['DOCUMENTS_FOLDER'], filename)
    file.save(filepath)
    
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('INSERT INTO candidate_documents (candidate_id, filename, original_filename, file_path, file_type, is_resume) VALUES (?, ?, ?, ?, ?, ?)',
              (candidate_id, filename, original_filename, filepath, original_filename.split('.')[-1], 0))
    conn.commit()
    conn.close()
    return jsonify({'message': 'Document uploaded'})

@app.route('/api/documents/<int:doc_id>/preview', methods=['GET'])
def preview_document(doc_id):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('SELECT * FROM candidate_documents WHERE id = ?', (doc_id,))
    doc = c.fetchone()
    conn.close()
    if doc and os.path.exists(doc[4]):
        file_path = doc[4]
        file_type = doc[5]
        
        if file_type == 'pdf':
            text = extract_text_from_pdf(file_path)
            return jsonify({'type': 'text', 'content': text[:2000]})
        elif file_type == 'docx':
            text = extract_text_from_docx(file_path)
            return jsonify({'type': 'text', 'content': text[:2000]})
        elif file_type in ['png', 'jpg', 'jpeg']:
            with open(file_path, 'rb') as f:
                img_data = base64.b64encode(f.read()).decode('utf-8')
                return jsonify({'type': 'image', 'content': img_data})
    
    return jsonify({'error': 'File not found'}), 404

@app.route('/api/parse-resume', methods=['POST'])
def parse_resume():
    if 'resume' not in request.files:
        return jsonify({'error': 'No file'}), 400
    file = request.files['resume']
    if file.filename == '':
        return jsonify({'error': 'No file'}), 400
    
    filename = secure_filename(file.filename)
    original_filename = file.filename
    temp_filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
    file.save(temp_filepath)
    
    if filename.endswith('.pdf'):
        text = extract_text_from_pdf(temp_filepath)
    else:
        text = extract_text_from_docx(temp_filepath)
    
    if not text:
        os.remove(temp_filepath)
        return jsonify({'error': 'Could not extract text'}), 400
    
    parsed = parse_resume_with_groq(text)
    if parsed and parsed.get('first_name'):
        parsed['resume_text'] = text[:3000]
        parsed['ai_used'] = True
    else:
        parsed = fallback_parse_resume(text)
        parsed['ai_used'] = False
    
    parsed['file_path'] = temp_filepath
    parsed['original_filename'] = original_filename
    
    return jsonify(parsed)

@app.route('/api/analyze-match', methods=['POST'])
def analyze_match():
    data = request.json
    resume_text = data.get('resume_text', '')
    jd_text = data.get('jd_text', '')
    candidate_id = data.get('candidate_id')
    
    if not resume_text or not jd_text:
        return jsonify({'error': 'Missing text'}), 400
    
    if not GROQ_ENABLED:
        return jsonify({'error': 'Groq API not configured'}), 503
    
    result = analyze_match_with_groq(resume_text, jd_text)
    
    if result and candidate_id:
        detailed_json = json.dumps(result, indent=2)
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        c.execute('UPDATE candidates SET match_score = ?, recommendation = ?, detailed_analysis = ? WHERE id = ?',
                  (result.get('match_score', 0), result.get('recommendation', 'review'), detailed_json, candidate_id))
        conn.commit()
        conn.close()
        return jsonify(result)
    elif result:
        return jsonify(result)
    
    return jsonify({'error': 'Analysis failed'}), 500

@app.route('/api/export-candidates', methods=['GET'])
def export_candidates():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    c.execute('SELECT id, first_name, last_name, email, phone, current_role, match_score, created_at FROM candidates ORDER BY created_at DESC')
    rows = c.fetchall()
    conn.close()
    
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(['ID', 'First Name', 'Last Name', 'Email', 'Phone', 'Current Role', 'Match Score', 'Created Date'])
    for row in rows:
        writer.writerow([row['id'], row['first_name'] or '', row['last_name'] or '',
                         row['email'] or '', row['phone'] or '', row['current_role'] or '',
                         row['match_score'] or 0, row['created_at']])
    output.seek(0)
    return Response(output.getvalue(), mimetype='text/csv', headers={'Content-Disposition': 'attachment; filename=candidates.csv'})
@app.route('/api/batch-analyze', methods=['POST'])
def batch_analyze():
    data = request.json
    jd_text = data.get('jd_text', '')
    
    if not jd_text:
        return jsonify({'error': 'Missing job description'}), 400
    
    # Get all candidates
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    c.execute('SELECT id, first_name, last_name, email, resume_text FROM candidates ORDER BY created_at DESC')
    candidates = [dict(row) for row in c.fetchall()]
    conn.close()
    
    # Extract keywords from JD
    jd_lower = jd_text.lower()
    jd_words = set(re.findall(r'\b[a-zA-Z]{3,}\b', jd_lower))
    
    results = []
    for cand in candidates:
        name = (cand.get('first_name', '') + ' ' + cand.get('last_name', '')).strip() or 'Unknown'
        resume_text = cand.get('resume_text', '') or ''
        
        if not resume_text:
            results.append({
                'candidate_id': cand['id'],
                'name': name,
                'email': cand.get('email', ''),
                'match_score': 0,
                'recommendation': 'No resume text'
            })
            continue
        
        # Keyword matching
        resume_lower = resume_text.lower()
        resume_words = set(re.findall(r'\b[a-zA-Z]{3,}\b', resume_lower))
        
        common = resume_words & jd_words
        match_score = min(100, int(len(common) / max(len(jd_words), 1) * 100))
        
        recommendation = 'hire' if match_score >= 70 else ('interview' if match_score >= 40 else 'reject')
        
        results.append({
            'candidate_id': cand['id'],
            'name': name,
            'email': cand.get('email', ''),
            'match_score': match_score,
            'recommendation': recommendation
        })
    
    # Sort by match score (highest first)
    results.sort(key=lambda x: x['match_score'], reverse=True)
    return jsonify(results)
# ========== NOTES API ROUTES ==========
@app.route('/api/candidates/<int:candidate_id>/notes', methods=['GET'])
def get_candidate_notes(candidate_id):
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    c.execute('SELECT id, note_text, created_at FROM candidate_notes WHERE candidate_id = ? ORDER BY created_at DESC', (candidate_id,))
    notes = [dict(row) for row in c.fetchall()]
    conn.close()
    return jsonify(notes)

@app.route('/api/candidates/<int:candidate_id>/notes', methods=['POST'])
def add_candidate_note(candidate_id):
    data = request.json
    note_text = data.get('note_text', '')
    if not note_text:
        return jsonify({'error': 'Note text required'}), 400
    
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('INSERT INTO candidate_notes (candidate_id, note_text) VALUES (?, ?)', (candidate_id, note_text))
    conn.commit()
    conn.close()
    return jsonify({'message': 'Note added'})

@app.route('/api/candidates/notes/<int:note_id>', methods=['DELETE'])
def delete_candidate_note(note_id):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('DELETE FROM candidate_notes WHERE id = ?', (note_id,))
    conn.commit()
    conn.close()
    return jsonify({'message': 'Note deleted'})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
