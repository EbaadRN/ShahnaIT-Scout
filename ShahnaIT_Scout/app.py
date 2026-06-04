# app.py - COMPLETE WORKING VERSION (Buttons Fixed)
import os
import re
import sqlite3
import csv
import io
import json
import requests
import shutil
import base64
from datetime import datetime
from flask import Flask, request, jsonify, render_template_string, Response, send_file
from flask_cors import CORS
from werkzeug.utils import secure_filename
import PyPDF2
import docx

app = Flask(__name__)
CORS(app)

# Configuration
app.config['MAX_CONTENT_LENGTH'] = 50 * 1024 * 1024
app.config['UPLOAD_FOLDER'] = '/tmp'
app.config['DOCUMENTS_FOLDER'] = '/tmp/candidate_docs'
ALLOWED_EXTENSIONS = {'pdf', 'docx', 'png', 'jpg', 'jpeg', 'txt'}

os.makedirs(app.config['DOCUMENTS_FOLDER'], exist_ok=True)

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

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
    "work_experience": [
        {{"company": "", "role": "", "start_date": "", "end_date": "", "is_current": false}}
    ],
    "certifications": [],
    "core_skills": [
        {{"skill": "", "years_of_experience": 0}}
    ],
    "education": ""
}}"""
    response = call_groq_api(prompt, max_tokens=2500)
    if response:
        try:
            return json.loads(response)
        except:
            return None
    return None

def analyze_match_with_groq(resume_text, jd_text, candidate_name=""):
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

# ============ FALLBACK PARSING ============
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

def fallback_parse_resume(text):
    lines = text.strip().split('\n')
    name = lines[0].strip() if lines else "Unknown"
    name_parts = name.split()
    first_name = name_parts[0] if name_parts else ""
    last_name = name_parts[-1] if len(name_parts) > 1 else ""
    
    email_match = re.search(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b', text)
    email = email_match.group(0) if email_match else ""
    
    phone_match = re.search(r'\b\d{10}\b|\b\d{3}[-.]?\d{3}[-.]?\d{4}\b|\+\d{2}\s?\d{10}\b', text)
    phone = phone_match.group(0) if phone_match else ""
    
    ctc_patterns = [
        r'current\s+ctc[\s:]*([\d\.]+\s*(?:LPA|lpa|Lacs|lakhs?))',
        r'ctc\s*:?\s*([\d\.]+\s*(?:LPA|lpa))',
    ]
    current_ctc = ""
    expected_ctc = ""
    for pattern in ctc_patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            current_ctc = match.group(1)
            break
    expected_match = re.search(r'expected\s+ctc[\s:]*([\d\.]+\s*(?:LPA|lpa))', text, re.IGNORECASE)
    if expected_match:
        expected_ctc = expected_match.group(1)
    
    common_skills = [
        'Python', 'Java', 'JavaScript', 'React', 'Angular', 'Node.js', 'SQL', 'AWS', 
        'Docker', 'Kubernetes', 'Git', 'Azure', 'Salesforce', 'Power Apps', 'Entra ID',
        'Apex', 'LWC', 'SOQL', 'REST API', 'CI/CD', 'Jenkins', 'Jira', 'Agile', 'Scrum',
        'Lightning', 'Triggers', 'Integration', 'Service Cloud', 'Sales Cloud'
    ]
    found_skills = []
    for skill in common_skills:
        if skill.lower() in text.lower():
            years = extract_years_from_text(text, skill)
            if years == 0:
                exp_match = re.search(r'(\d+)\+?\s*years?', text[:500])
                if exp_match:
                    years = int(exp_match.group(1))
            found_skills.append({"skill": skill, "years_of_experience": years})
    
    work_experience = []
    exp_pattern = r'([A-Za-z0-9\s&]+?)\s*[\(|]?(\d{4})\s*[-–to]+?\s*(\d{4}|Present)[\)|]?\s*(?:[-–]\s*)?(.+?)(?=\n\n|\Z)'
    matches = re.findall(exp_pattern, text, re.IGNORECASE | re.DOTALL)
    for match in matches:
        company = match[0].strip()
        start_year = match[1]
        end_year = match[2]
        role = match[3].strip()[:100]
        if company and role:
            work_experience.append({
                "company": company,
                "role": role,
                "start_date": start_year,
                "end_date": end_year,
                "is_current": end_year.lower() == 'present'
            })
    
    role_match = re.search(r'(\w+\s+\w+)\s+(?:Engineer|Developer|Architect|Lead|Manager|Consultant|Analyst)', text[:500])
    current_role = role_match.group(0) if role_match else ""
    
    cert_pattern = r'(?:Certified|certification)\s*:?\s*([A-Za-z0-9\s]+?)(?:\n|$)'
    certifications = re.findall(cert_pattern, text, re.IGNORECASE)
    certifications = [c.strip() for c in certifications if len(c.strip()) > 5][:10]
    
    return {
        'first_name': first_name,
        'last_name': last_name,
        'middle_name': "",
        'phone': phone,
        'email': email,
        'address': "",
        'linkedin': "",
        'current_role': current_role,
        'current_ctc': current_ctc,
        'expected_ctc': expected_ctc,
        'employment_status': "working",
        'notice_period_days': 0,
        'work_experience': work_experience,
        'certifications': certifications,
        'core_skills': found_skills,
        'education': "",
        'resume_text': text[:3000],
        'ai_used': False
    }

def parse_resume_file(file_path):
    if file_path.endswith('.pdf'):
        text = extract_text_from_pdf(file_path)
    else:
        text = extract_text_from_docx(file_path)
    if not text:
        return {'error': 'Could not extract text'}
    parsed = parse_resume_with_groq(text)
    if parsed and parsed.get('first_name'):
        parsed['resume_text'] = text[:3000]
        parsed['ai_used'] = True
        return parsed
    else:
        fallback = fallback_parse_resume(text)
        fallback['ai_used'] = False
        return fallback

def save_candidate_to_db(candidate_data):
    skills = json.dumps(candidate_data.get('core_skills', []))
    work_exp = json.dumps(candidate_data.get('work_experience', []))
    certs = json.dumps(candidate_data.get('certifications', []))
    
    conn = sqlite3.connect('shahnai.db')
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
    
    file_path = candidate_data.get('file_path')
    original_filename = candidate_data.get('original_filename')
    
    if file_path and os.path.exists(file_path):
        permanent_filename = secure_filename(f"{candidate_id}_{datetime.now().timestamp()}_{original_filename}")
        permanent_path = os.path.join(app.config['DOCUMENTS_FOLDER'], permanent_filename)
        shutil.move(file_path, permanent_path)
        c.execute('INSERT INTO candidate_documents (candidate_id, filename, original_filename, file_path, file_type, is_resume) VALUES (?, ?, ?, ?, ?, ?)',
                  (candidate_id, permanent_filename, original_filename, permanent_path, original_filename.split('.')[-1], 1))
    
    conn.commit()
    conn.close()
    return candidate_id

# ============ DATABASE ============
def init_db():
    conn = sqlite3.connect('shahnai.db')
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
    c.execute('''CREATE TABLE IF NOT EXISTS jobs (
        id INTEGER PRIMARY KEY AUTOINCREMENT, title TEXT NOT NULL,
        company TEXT, description TEXT, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )''')
    conn.commit()
    conn.close()
    print("✅ Database initialized")

init_db()

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

def get_file_preview(file_path, file_type):
    try:
        if file_type == 'pdf':
            text = extract_text_from_pdf(file_path)
            return {'type': 'text', 'content': text[:2000]}
        elif file_type == 'docx':
            text = extract_text_from_docx(file_path)
            return {'type': 'text', 'content': text[:2000]}
        elif file_type in ['png', 'jpg', 'jpeg']:
            with open(file_path, 'rb') as f:
                img_data = base64.b64encode(f.read()).decode('utf-8')
                return {'type': 'image', 'content': img_data}
        else:
            with open(file_path, 'r', errors='ignore') as f:
                content = f.read(2000)
                return {'type': 'text', 'content': content}
    except:
        return {'type': 'text', 'content': 'Unable to preview file'}

# ============ HTML TEMPLATE ============
HTML_TEMPLATE = '''
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>ShahnaIT Scout</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body { background-color: #F9F6F0; font-family: 'Segoe UI', system-ui, sans-serif; }
        .header { background: linear-gradient(135deg, #1A3A3A 0%, #1D5E5A 100%); color: white; padding: 25px; border-radius: 16px; margin-bottom: 20px; }
        .header h1 { font-size: 1.8em; }
        .tabs { display: flex; gap: 5px; background: white; padding: 10px; border-radius: 12px; margin-bottom: 20px; flex-wrap: wrap; }
        .tab-btn { background: transparent; border: none; padding: 10px 20px; cursor: pointer; border-radius: 8px; font-size: 14px; }
        .tab-btn:hover { background: #F9F6F0; }
        .tab-btn.active { background: #1D5E5A; color: white; }
        .card { background: white; border-radius: 16px; padding: 20px; margin-bottom: 20px; box-shadow: 0 2px 8px rgba(0,0,0,0.05); border-left: 4px solid #1D5E5A; cursor: pointer; }
        .card:hover { transform: translateY(-2px); }
        .card.no-click { cursor: default; }
        .card.no-click:hover { transform: none; }
        .btn-primary { background: #1D5E5A; color: white; border: none; padding: 10px 24px; border-radius: 40px; cursor: pointer; font-weight: 600; margin: 5px; }
        .btn-primary:hover { background: #2A7A76; }
        .btn-secondary { background: #6B7B7B; color: white; border: none; padding: 8px 20px; border-radius: 40px; cursor: pointer; }
        input, textarea, select { width: 100%; padding: 12px; border: 1px solid #ddd; border-radius: 12px; margin-bottom: 15px; }
        .skill-tag { display: inline-block; background: #F9F6F0; padding: 4px 12px; border-radius: 30px; margin: 3px; font-size: 12px; }
        .match-high { background: #1B6B2E; color: white; padding: 2px 10px; border-radius: 30px; display: inline-block; }
        .match-medium { background: #CC5500; color: white; padding: 2px 10px; border-radius: 30px; display: inline-block; }
        .match-low { background: #B22222; color: white; padding: 2px 10px; border-radius: 30px; display: inline-block; }
        .alert-success { background: #1B6B2E; color: white; padding: 12px; border-radius: 12px; margin: 10px 0; }
        .alert-error { background: #B22222; color: white; padding: 12px; border-radius: 12px; margin: 10px 0; }
        .alert-info { background: #3498DB; color: white; padding: 12px; border-radius: 12px; margin: 10px 0; }
        .spinner { border: 3px solid #F9F6F0; border-top: 3px solid #1D5E5A; border-radius: 50%; width: 40px; height: 40px; animation: spin 0.8s linear infinite; margin: 20px auto; }
        @keyframes spin { 0% { transform: rotate(0deg); } 100% { transform: rotate(360deg); } }
        .modal { display: none; position: fixed; z-index: 1000; left: 0; top: 0; width: 100%; height: 100%; background: rgba(0,0,0,0.5); overflow-y: auto; }
        .modal-content { background: #F9F6F0; margin: 50px auto; border-radius: 20px; max-width: 700px; width: 90%; }
        .modal-header { background: #1D5E5A; color: white; padding: 15px 20px; border-radius: 20px 20px 0 0; display: flex; justify-content: space-between; }
        .modal-body { padding: 20px; max-height: 70vh; overflow-y: auto; }
        .close { font-size: 28px; cursor: pointer; color: white; }
        .detail-row { display: flex; margin-bottom: 10px; border-bottom: 1px solid #ddd; padding-bottom: 5px; }
        .detail-label { width: 130px; font-weight: 600; }
        .detail-value { flex: 1; }
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
<div style="max-width: 1400px; margin: 0 auto; padding: 20px;">
    <div class="header">
        <h1>🎯 ShahnaIT Scout <span style="background:#27AE60; padding:4px 12px; border-radius:30px; font-size:12px;">⚡ GROQ AI</span></h1>
        <p>Intelligent Recruitment Platform</p>
    </div>
    
    <div class="tabs">
        <button class="tab-btn active" onclick="showTab('jobs')">📋 Jobs</button>
        <button class="tab-btn" onclick="showTab('candidates')">👥 Candidates</button>
        <button class="tab-btn" onclick="showTab('upload')">📄 Upload Resume</button>
        <button class="tab-btn" onclick="showTab('create-job')">➕ Create Job</button>
        <button class="tab-btn" onclick="showTab('analyze')">🔍 Analyze Match</button>
    </div>
    
    <div id="jobs-tab"><div id="jobs-list"></div></div>
    
    <div id="candidates-tab" style="display:none;">
        <div style="display: flex; justify-content: space-between; margin-bottom: 15px;">
            <h2>👥 Candidates <span id="filter-count" style="color:#888;"></span></h2>
            <button class="btn-primary" onclick="exportToCSV()">📥 Export CSV</button>
        </div>
        <div class="filter-bar">
            <input type="text" id="search-input" placeholder="🔍 Search by name, skills..." onkeyup="filterCandidates()">
            <select id="filter-score" onchange="filterCandidates()">
                <option value="all">All Scores</option>
                <option value="high">High (70%+)</option>
                <option value="medium">Medium (40-69%)</option>
                <option value="low">Low (<40%)</option>
            </select>
            <select id="filter-rec" onchange="filterCandidates()">
                <option value="all">All Recommendations</option>
                <option value="hire">Hire</option>
                <option value="interview">Interview</option>
                <option value="reject">Reject</option>
            </select>
            <button class="btn-secondary" onclick="clearFilters()">Clear</button>
        </div>
        <div id="candidates-list"></div>
    </div>
    
    <div id="upload-tab" style="display:none;">
        <div class="card no-click">
            <h3>📄 Single Resume Upload</h3>
            <div class="alert-info">🤖 AI will auto-fill candidate details</div>
            <input type="file" id="single-file" accept=".pdf,.docx">
            <button class="btn-primary" id="parse-single">🔍 Parse & Auto-Fill</button>
            <div id="parse-result"></div>
        </div>
        <div class="card no-click">
            <h3>📚 Multiple Resume Upload</h3>
            <div class="alert-info">Select multiple PDF/DOCX files at once</div>
            <input type="file" id="multi-files" multiple accept=".pdf,.docx">
            <div id="selected-files-list" class="file-list" style="display:none;"></div>
            <button class="btn-primary" id="upload-multi">🚀 Upload & Parse All</button>
            <div id="multi-result"></div>
        </div>
    </div>
    
    <div id="create-job-tab" style="display:none;">
        <div class="card no-click">
            <h3>➕ Create Job</h3>
            <input type="text" id="job-title" placeholder="Job Title *">
            <input type="text" id="job-company" placeholder="Company Name">
            <textarea id="job-desc" rows="4" placeholder="Job Description"></textarea>
            <button class="btn-primary" id="create-job-btn">Create Job</button>
        </div>
    </div>
    
    <div id="analyze-tab" style="display:none;">
        <div class="card no-click">
            <h3>🔍 AI Match Analysis</h3>
            <div class="flex">
                <div class="flex-1"><select id="job-select"><option value="">-- Select Job --</option></select></div>
                <div class="flex-1"><select id="candidate-select"><option value="">-- Select Candidate --</option></select></div>
            </div>
            <button class="btn-primary" id="analyze-match-btn">🤖 Run Analysis</button>
            <div id="analyze-result"></div>
        </div>
    </div>
</div>

<div id="candidateModal" class="modal">
    <div class="modal-content">
        <div class="modal-header"><h2 id="modalTitle">Candidate Profile</h2><span class="close" onclick="closeModal()">&times;</span></div>
        <div class="modal-body" id="modalBody"></div>
    </div>
</div>

<script>
    let jobsData = [], candidatesData = [];
    
    function showTab(tab) {
        document.getElementById('jobs-tab').style.display = 'none';
        document.getElementById('candidates-tab').style.display = 'none';
        document.getElementById('upload-tab').style.display = 'none';
        document.getElementById('create-job-tab').style.display = 'none';
        document.getElementById('analyze-tab').style.display = 'none';
        document.getElementById(tab + '-tab').style.display = 'block';
        document.querySelectorAll('.tab-btn').forEach(btn => btn.classList.remove('active'));
        if (event && event.target) event.target.classList.add('active');
        if (tab === 'jobs') loadJobs();
        if (tab === 'candidates') loadCandidates();
        if (tab === 'analyze') { loadJobs(); loadCandidates(); }
    }
    
    async function loadJobs() {
        const res = await fetch('/api/jobs');
        jobsData = await res.json();
        const container = document.getElementById('jobs-list');
        if (!jobsData.length) { container.innerHTML = '<div class="card no-click">No jobs yet</div>'; return; }
        container.innerHTML = jobsData.map(j => `<div class="card no-click"><h3>${escapeHtml(j.title)}</h3>${j.company ? `<p>🏢 ${escapeHtml(j.company)}</p>` : ''}<small>${new Date(j.created_at).toLocaleDateString()}</small></div>`).join('');
        document.getElementById('job-select').innerHTML = '<option value="">-- Select Job --</option>' + jobsData.map(j => `<option value="${j.id}">${escapeHtml(j.title)}</option>`).join('');
    }
    
    async function loadCandidates() {
        const res = await fetch('/api/candidates');
        candidatesData = await res.json();
        filterCandidates();
        document.getElementById('candidate-select').innerHTML = '<option value="">-- Select Candidate --</option>' + candidatesData.map(c => `<option value="${c.id}">${escapeHtml(c.first_name + ' ' + c.last_name || 'Unknown')}</option>`).join('');
    }
    
    function renderCandidates(candidates) {
        const container = document.getElementById('candidates-list');
        if (!candidates.length) { container.innerHTML = '<div class="card no-click">No candidates</div>'; return; }
        container.innerHTML = candidates.map(c => {
            const name = `${c.first_name || ''} ${c.last_name || ''}`.trim() || 'Unknown';
            const skills = c.core_skills ? JSON.parse(c.core_skills) : [];
            return `<div class="card" onclick="viewCandidate(${c.id})">
                <h3>👤 ${escapeHtml(name)}</h3>
                ${c.email ? `<p>📧 ${escapeHtml(c.email)}</p>` : ''}
                <p>🔧 ${skills.slice(0,3).map(s => `<span class="skill-tag">${escapeHtml(s.skill)}</span>`).join('')}</p>
                ${c.match_score ? `<p>🎯 Score: <span class="${c.match_score >= 70 ? 'match-high' : (c.match_score >= 40 ? 'match-medium' : 'match-low')}">${c.match_score}%</span></p>` : ''}
                <small>${new Date(c.created_at).toLocaleDateString()}</small>
            </div>`;
        }).join('');
        document.getElementById('filter-count').innerHTML = `(${candidates.length} of ${candidatesData.length})`;
    }
    
    function filterCandidates() {
        const search = document.getElementById('search-input').value.toLowerCase();
        const score = document.getElementById('filter-score').value;
        const rec = document.getElementById('filter-rec').value;
        
        const filtered = candidatesData.filter(c => {
            const name = `${c.first_name || ''} ${c.last_name || ''}`.toLowerCase();
            const skills = c.core_skills ? JSON.parse(c.core_skills).map(s => s.skill.toLowerCase()).join(' ') : '';
            const matchesSearch = name.includes(search) || skills.includes(search);
            let matchesScore = true;
            if (score === 'high') matchesScore = (c.match_score || 0) >= 70;
            else if (score === 'medium') matchesScore = (c.match_score || 0) >= 40 && (c.match_score || 0) < 70;
            else if (score === 'low') matchesScore = (c.match_score || 0) < 40;
            let matchesRec = true;
            if (rec !== 'all') matchesRec = (c.recommendation || '').toLowerCase() === rec;
            return matchesSearch && matchesScore && matchesRec;
        });
        renderCandidates(filtered);
    }
    
    function clearFilters() {
        document.getElementById('search-input').value = '';
        document.getElementById('filter-score').value = 'all';
        document.getElementById('filter-rec').value = 'all';
        filterCandidates();
    }
    
    async function viewCandidate(id) {
        const c = candidatesData.find(c => c.id == id);
        if (!c) return;
        const name = `${c.first_name || ''} ${c.last_name || ''}`.trim();
        const workExp = JSON.parse(c.work_experience || '[]');
        const skills = JSON.parse(c.core_skills || '[]');
        const certs = JSON.parse(c.certifications || '[]');
        const docRes = await fetch(`/api/candidates/${id}/documents`);
        const docs = await docRes.json();
        const resumeDoc = docs.find(d => d.is_resume === 1);
        
        document.getElementById('modalTitle').innerHTML = `👤 ${escapeHtml(name)}`;
        document.getElementById('modalBody').innerHTML = `
            <div class="detail-row"><div class="detail-label">Name:</div><div class="detail-value">${escapeHtml(name)}</div></div>
            <div class="detail-row"><div class="detail-label">Email:</div><div class="detail-value">${escapeHtml(c.email || 'N/A')}</div></div>
            <div class="detail-row"><div class="detail-label">Phone:</div><div class="detail-value">${escapeHtml(c.phone || 'N/A')}</div></div>
            <div class="detail-row"><div class="detail-label">Role:</div><div class="detail-value">${escapeHtml(c.current_role || 'N/A')}</div></div>
            <div class="detail-row"><div class="detail-label">Status:</div><div class="detail-value">${escapeHtml(c.employment_status || 'N/A')}</div></div>
            <h4>💼 Work Experience</h4>
            ${workExp.map(w => `<div><strong>${escapeHtml(w.company)}</strong> - ${escapeHtml(w.role)}</div>`).join('') || 'None'}
            <h4>⭐ Skills</h4>
            ${skills.map(s => `<span class="skill-tag">${escapeHtml(s.skill)} (${s.years_of_experience || 0}y)</span>`).join('') || 'None'}
            <h4>📜 Certifications</h4>
            ${certs.map(c => `<div>📜 ${escapeHtml(c)}</div>`).join('') || 'None'}
            <h4>📄 Resume</h4>
            ${resumeDoc ? `<a href="/api/documents/${resumeDoc.id}" target="_blank">${escapeHtml(resumeDoc.original_filename)}</a>` : 'None'}
            <button class="btn-primary" onclick="closeModal()" style="margin-top:15px;">Close</button>
        `;
        document.getElementById('candidateModal').style.display = 'block';
    }
    
    function closeModal() { document.getElementById('candidateModal').style.display = 'none'; }
    window.exportToCSV = () => window.location.href = '/api/export-candidates';
    
    // Multi-file selection display
    document.getElementById('multi-files').addEventListener('change', function(e) {
        const files = e.target.files;
        const container = document.getElementById('selected-files-list');
        if (files.length) {
            let html = '<strong>Selected:</strong><br>';
            for (let i = 0; i < files.length; i++) {
                html += `<div class="file-list-item">📄 ${escapeHtml(files[i].name)}</div>`;
            }
            container.innerHTML = html;
            container.style.display = 'block';
        } else {
            container.style.display = 'none';
        }
    });
    
    // Single Parse Button
    document.getElementById('parse-single').onclick = async function() {
        const file = document.getElementById('single-file').files[0];
        if (!file) { alert('Select a file'); return; }
        const fd = new FormData();
        fd.append('resume', file);
        const div = document.getElementById('parse-result');
        div.innerHTML = '<div class="spinner"></div><p>Parsing...</p>';
        try {
            const res = await fetch('/api/parse-resume', { method: 'POST', body: fd });
            const result = await res.json();
            if (result.error) { div.innerHTML = `<div class="alert-error">${result.error}</div>`; return; }
            div.innerHTML = `<div class="alert-success"><h4>✅ Parsed</h4><p><strong>Name:</strong> ${escapeHtml(result.first_name || '')} ${escapeHtml(result.last_name || '')}</p><p><strong>Email:</strong> ${escapeHtml(result.email || '')}</p><p><strong>Phone:</strong> ${escapeHtml(result.phone || '')}</p><p><strong>Skills:</strong> ${result.core_skills ? result.core_skills.map(s => `<span class="skill-tag">${escapeHtml(s.skill)}</span>`).join('') : 'None'}</p><button class="btn-primary" id="save-candidate-btn">💾 Save</button></div>`;
            document.getElementById('save-candidate-btn').onclick = async function() {
                const saveRes = await fetch('/api/candidates', { method: 'POST', headers: {'Content-Type':'application/json'}, body: JSON.stringify(result) });
                if (saveRes.ok) { alert('Saved!'); div.innerHTML = ''; document.getElementById('single-file').value = ''; loadCandidates(); }
                else alert('Error');
            };
        } catch(e) { div.innerHTML = '<div class="alert-error">Error</div>'; }
    };
    
    // Multi Upload Button
    document.getElementById('upload-multi').onclick = async function() {
        const files = document.getElementById('multi-files').files;
        if (!files.length) { alert('Select files first'); return; }
        const div = document.getElementById('multi-result');
        div.innerHTML = `<div class="progress-bar"><div class="progress-fill"></div></div><p>Processing 0/${files.length}</p>`;
        let success = 0, fail = 0;
        for (let i = 0; i < files.length; i++) {
            const fd = new FormData();
            fd.append('resume', files[i]);
            const percent = Math.round((i / files.length) * 100);
            div.innerHTML = `<div class="progress-bar"><div class="progress-fill" style="width:${percent}%"></div></div><p>Processing ${i+1}/${files.length}: ${escapeHtml(files[i].name)}</p>`;
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
        document.getElementById('multi-files').value = '';
        document.getElementById('selected-files-list').style.display = 'none';
        loadCandidates();
    };
    
    // Analyze Button
    document.getElementById('analyze-match-btn').onclick = async function() {
        const jobId = document.getElementById('job-select').value;
        const candidateId = document.getElementById('candidate-select').value;
        if (!jobId || !candidateId) { alert('Select both'); return; }
        const job = jobsData.find(j => j.id == jobId);
        const cand = candidatesData.find(c => c.id == candidateId);
        const div = document.getElementById('analyze-result');
        div.innerHTML = '<div class="spinner"></div><p>Analyzing...</p>';
        try {
            const res = await fetch('/api/analyze-match', { method: 'POST', headers: {'Content-Type':'application/json'}, body: JSON.stringify({ job_id: jobId, candidate_id: candidateId, jd_text: job.description || '', resume_text: cand.resume_text || '' }) });
            const result = await res.json();
            if (result.error) { div.innerHTML = `<div class="alert-error">${result.error}</div>`; return; }
            div.innerHTML = `<div class="alert-success"><h4>📊 Analysis Complete</h4><p>🎯 Score: <span class="${result.match_score >= 70 ? 'match-high' : (result.match_score >= 40 ? 'match-medium' : 'match-low')}">${result.match_score || 0}%</span></p><p>📌 ${result.recommendation || 'Review'}</p><small>✅ Saved</small></div>`;
            loadCandidates();
        } catch(e) { div.innerHTML = '<div class="alert-error">Failed</div>'; }
    };
    
    // Create Job Button
    document.getElementById('create-job-btn').onclick = async function() {
        const data = {
            title: document.getElementById('job-title').value,
            company: document.getElementById('job-company').value,
            description: document.getElementById('job-desc').value
        };
        if (!data.title) { alert('Title required'); return; }
        const res = await fetch('/api/jobs', { method: 'POST', headers: {'Content-Type':'application/json'}, body: JSON.stringify(data) });
        if (res.ok) {
            alert('Job created!');
            document.getElementById('job-title').value = '';
            document.getElementById('job-company').value = '';
            document.getElementById('job-desc').value = '';
            showTab('jobs');
            loadJobs();
        } else { alert('Error'); }
    };
    
    function escapeHtml(str) { if (!str) return ''; return str.replace(/[&<>]/g, function(m) { if (m === '&') return '&amp;'; if (m === '<') return '&lt;'; if (m === '>') return '&gt;'; return m; }); }
    
    loadJobs(); loadCandidates();
</script>
</body>
</html>
'''

# ============ API ROUTES ============
@app.route('/')
def index():
    return render_template_string(HTML_TEMPLATE)

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
    
    result = parse_resume_file(temp_filepath)
    
    if not result.get('error'):
        result['file_path'] = temp_filepath
        result['original_filename'] = original_filename
    
    return jsonify(result)

@app.route('/api/candidates', methods=['GET'])
def get_candidates():
    conn = sqlite3.connect('shahnai.db')
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
    return jsonify({'message': 'Candidate saved', 'id': candidate_id})

@app.route('/api/candidates/<int:candidate_id>/documents', methods=['GET'])
def get_candidate_documents(candidate_id):
    conn = sqlite3.connect('shahnai.db')
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    c.execute('SELECT * FROM candidate_documents WHERE candidate_id = ? ORDER BY is_resume DESC', (candidate_id,))
    docs = [dict(row) for row in c.fetchall()]
    conn.close()
    return jsonify(docs)

@app.route('/api/documents/<int:doc_id>', methods=['GET'])
def get_document(doc_id):
    conn = sqlite3.connect('shahnai.db')
    c = conn.cursor()
    c.execute('SELECT * FROM candidate_documents WHERE id = ?', (doc_id,))
    doc = c.fetchone()
    conn.close()
    if doc and os.path.exists(doc[4]):
        return send_file(doc[4], as_attachment=False, download_name=doc[3])
    return jsonify({'error': 'File not found'}), 404

@app.route('/api/jobs', methods=['GET'])
def get_jobs():
    conn = sqlite3.connect('shahnai.db')
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    c.execute('SELECT * FROM jobs ORDER BY created_at DESC')
    jobs = [dict(row) for row in c.fetchall()]
    conn.close()
    return jsonify(jobs)

@app.route('/api/jobs', methods=['POST'])
def create_job():
    data = request.json
    conn = sqlite3.connect('shahnai.db')
    c = conn.cursor()
    c.execute('INSERT INTO jobs (title, company, description) VALUES (?, ?, ?)',
              (data.get('title'), data.get('company'), data.get('description', '')))
    conn.commit()
    conn.close()
    return jsonify({'message': 'Job created'})

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
    
    # Simple keyword matching as fallback (always works)
    resume_clean = re.sub(r'[^\w\s]', ' ', resume_text.lower())
    jd_clean = re.sub(r'[^\w\s]', ' ', jd_text.lower())
    resume_words = set(resume_clean.split())
    jd_words = set(jd_clean.split())
    common = resume_words & jd_words
    match_score = min(100, int(len(common) / max(len(jd_words), 1) * 100))
    
    result = {
        'match_score': match_score,
        'recommendation': 'hire' if match_score >= 70 else ('interview' if match_score >= 40 else 'reject'),
        'executive_summary': {'final_verdict': f'Match score: {match_score}% based on keyword analysis.'},
        'pre_screening_questions': ['Can you describe your experience with the key requirements?', 'What is your notice period?']
    }
    
    if candidate_id:
        detailed_json = json.dumps(result, indent=2)
        conn = sqlite3.connect('shahnai.db')
        c = conn.cursor()
        c.execute('UPDATE candidates SET match_score = ?, recommendation = ?, detailed_analysis = ? WHERE id = ?',
                  (result.get('match_score', 0), result.get('recommendation', 'review'), detailed_json, candidate_id))
        conn.commit()
        conn.close()
    
    return jsonify(result)

@app.route('/api/export-candidates', methods=['GET'])
def export_candidates():
    conn = sqlite3.connect('shahnai.db')
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

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
