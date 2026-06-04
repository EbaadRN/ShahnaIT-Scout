# app.py - SIMPLIFIED WORKING VERSION
import os
import re
import sqlite3
import csv
import io
import json
import requests
import shutil
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
    print("✅ Groq API configured")

def call_groq_api(prompt, max_tokens=2000):
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
    prompt = f"""Parse this resume. Return ONLY valid JSON.

RESUME: {resume_text[:3000]}

Return: {{"first_name": "", "last_name": "", "middle_name": "", "phone": "", "email": "", "address": "", "linkedin": "", "current_role": "", "employment_status": "working", "work_experience": [], "certifications": [], "core_skills": [], "education": ""}}"""
    response = call_groq_api(prompt, max_tokens=2000)
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

# ============ FALLBACK PARSING ============
def fallback_parse_resume(text):
    lines = text.strip().split('\n')
    name = lines[0].strip() if lines else "Unknown"
    name_parts = name.split()
    first_name = name_parts[0] if name_parts else ""
    last_name = name_parts[-1] if len(name_parts) > 1 else ""
    
    email_match = re.search(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b', text)
    email = email_match.group(0) if email_match else ""
    
    phone_match = re.search(r'\b\d{10}\b|\b\d{3}[-.]?\d{3}[-.]?\d{4}\b', text)
    phone = phone_match.group(0) if phone_match else ""
    
    common_skills = ['Python', 'Java', 'JavaScript', 'React', 'Angular', 'Node.js', 'SQL', 'AWS', 'Docker']
    found_skills = []
    for skill in common_skills:
        if skill.lower() in text.lower():
            found_skills.append({"skill": skill, "years_of_experience": 0})
    
    return {
        'first_name': first_name,
        'last_name': last_name,
        'middle_name': "",
        'phone': phone,
        'email': email,
        'address': "",
        'linkedin': "",
        'current_role': "",
        'employment_status': "working",
        'notice_period_days': 0,
        'work_experience': [],
        'certifications': [],
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

# ============ DATABASE ============
def init_db():
    conn = sqlite3.connect('shahnai.db')
    c = conn.cursor()
    c.execute('DROP TABLE IF EXISTS candidates')
    c.execute('''CREATE TABLE candidates (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        first_name TEXT, last_name TEXT, middle_name TEXT, phone TEXT, email TEXT,
        address TEXT, linkedin TEXT, other_social TEXT, current_role TEXT,
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

# ============ HTML TEMPLATE ============
HTML_TEMPLATE = '''
<!DOCTYPE html>
<html>
<head>
    <title>ShahnaIT Scout</title>
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body { background-color: #F9F6F0; font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; }
        .container { max-width: 1400px; margin: 0 auto; padding: 20px; }
        .header { background: linear-gradient(135deg, #1A3A3A 0%, #1D5E5A 100%); color: white; padding: 30px; border-radius: 20px; margin-bottom: 30px; }
        .header h1 { font-size: 2em; }
        .tabs { display: flex; gap: 10px; margin-bottom: 30px; background: white; padding: 15px; border-radius: 60px; flex-wrap: wrap; }
        .tab-btn { background: transparent; border: none; padding: 10px 28px; font-size: 15px; cursor: pointer; color: #666; border-radius: 40px; transition: all 0.3s; }
        .tab-btn:hover { background: #F9F6F0; color: #1D5E5A; }
        .tab-btn.active { background: #1D5E5A; color: white; }
        .card { background: white; border-radius: 20px; padding: 24px; margin-bottom: 20px; box-shadow: 0 2px 10px rgba(0,0,0,0.05); border-left: 4px solid #1D5E5A; cursor: pointer; transition: all 0.2s; }
        .card:hover { transform: translateY(-2px); box-shadow: 0 4px 15px rgba(0,0,0,0.1); }
        .card.no-click { cursor: default; }
        .card.no-click:hover { transform: none; }
        .btn-primary { background: #1D5E5A; color: white; border: none; padding: 10px 24px; border-radius: 40px; cursor: pointer; font-weight: 600; margin: 5px; }
        .btn-primary:hover { background: #2A7A76; }
        .btn-secondary { background: #6B7B7B; color: white; border: none; padding: 8px 20px; border-radius: 40px; cursor: pointer; }
        input, textarea, select { width: 100%; padding: 12px 16px; border: 1px solid #EAE5DC; border-radius: 16px; background: white; margin-bottom: 15px; }
        .skill-tag { display: inline-block; background: #F9F6F0; padding: 4px 12px; border-radius: 30px; margin: 3px; font-size: 12px; color: #1D5E5A; }
        .match-high { background: #1B6B2E; color: white; padding: 2px 10px; border-radius: 30px; display: inline-block; }
        .match-medium { background: #CC5500; color: white; padding: 2px 10px; border-radius: 30px; display: inline-block; }
        .match-low { background: #B22222; color: white; padding: 2px 10px; border-radius: 30px; display: inline-block; }
        .alert-success { background: #1B6B2E; color: white; padding: 15px; border-radius: 16px; margin: 10px 0; }
        .alert-error { background: #B22222; color: white; padding: 15px; border-radius: 16px; margin: 10px 0; }
        .alert-info { background: #3498DB; color: white; padding: 15px; border-radius: 16px; margin: 10px 0; }
        .spinner { border: 3px solid #F9F6F0; border-top: 3px solid #1D5E5A; border-radius: 50%; width: 45px; height: 45px; animation: spin 0.8s linear infinite; margin: 20px auto; }
        @keyframes spin { 0% { transform: rotate(0deg); } 100% { transform: rotate(360deg); } }
        .modal { display: none; position: fixed; z-index: 1000; left: 0; top: 0; width: 100%; height: 100%; background: rgba(0,0,0,0.5); overflow-y: auto; }
        .modal-content { background: #F9F6F0; margin: 50px auto; border-radius: 28px; max-width: 800px; width: 90%; }
        .modal-header { background: #1D5E5A; color: white; padding: 20px; border-radius: 28px 28px 0 0; display: flex; justify-content: space-between; }
        .modal-body { padding: 25px; max-height: 70vh; overflow-y: auto; }
        .close { font-size: 28px; cursor: pointer; color: white; }
        .detail-row { display: flex; margin-bottom: 10px; border-bottom: 1px solid #EAE5DC; padding-bottom: 8px; }
        .detail-label { width: 130px; font-weight: 600; color: #1A3A3A; }
        .detail-value { flex: 1; color: #2C3E3E; }
        .search-bar { display: flex; gap: 10px; margin-bottom: 20px; }
        .search-bar input { margin-bottom: 0; }
        .flex { display: flex; gap: 15px; flex-wrap: wrap; }
        .flex-1 { flex: 1; }
        @media (max-width: 768px) { .container { padding: 10px; } .tab-btn { padding: 8px 16px; } }
    </style>
</head>
<body>
<div class="container">
    <div class="header">
        <h1>🎯 ShahnaIT Scout <span style="background:#27AE60; padding:4px 12px; border-radius:30px; font-size:12px;">⚡ GROQ AI</span></h1>
        <p>Intelligent Recruitment Platform with AI Analysis</p>
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
        <button class="btn-primary" onclick="exportToCSV()">📥 Export CSV</button>
        <div class="search-bar"><input type="text" id="search-input" placeholder="🔍 Search by name or skills..." onkeyup="filterCandidates()"><button class="btn-secondary" onclick="clearSearch()">Clear</button></div>
        <div id="candidates-list"></div>
    </div>
    
    <div id="upload-tab" style="display:none;">
        <div class="card no-click">
            <h3>📄 Upload Resume</h3>
            <div class="alert-info">🤖 AI will auto-fill candidate details</div>
            <input type="file" id="resume-file" accept=".pdf,.docx">
            <button class="btn-primary" id="parse-resume-btn">🔍 Parse & Auto-Fill</button>
            <div id="parse-result"></div>
        </div>
    </div>
    
    <div id="create-job-tab" style="display:none;">
        <div class="card no-click">
            <h3>➕ Create Job</h3>
            <form id="job-form">
                <input type="text" id="job-title" placeholder="Job Title *" required>
                <input type="text" id="job-company" placeholder="Company Name">
                <textarea id="job-desc" rows="5" placeholder="Job Description"></textarea>
                <button type="submit" class="btn-primary">Create Job</button>
            </form>
        </div>
    </div>
    
    <div id="analyze-tab" style="display:none;">
        <div class="card no-click">
            <h3>🔍 AI Match Analysis</h3>
            <div class="flex">
                <div class="flex-1"><select id="job-select"></select></div>
                <div class="flex-1"><select id="candidate-select"></select></div>
            </div>
            <button class="btn-primary" id="analyze-btn">🤖 Run Groq AI Analysis</button>
            <div id="analyze-result"></div>
        </div>
    </div>
</div>

<div id="candidateModal" class="modal">
    <div class="modal-content">
        <div class="modal-header"><h2 id="modal-title">Candidate Profile</h2><span class="close" onclick="closeModal()">&times;</span></div>
        <div class="modal-body" id="modal-body">Loading...</div>
    </div>
</div>

<script>
    let jobsData = [];
    let candidatesData = [];
    
    function showTab(tabName) {
        document.getElementById('jobs-tab').style.display = 'none';
        document.getElementById('candidates-tab').style.display = 'none';
        document.getElementById('upload-tab').style.display = 'none';
        document.getElementById('create-job-tab').style.display = 'none';
        document.getElementById('analyze-tab').style.display = 'none';
        document.getElementById(tabName + '-tab').style.display = 'block';
        
        document.querySelectorAll('.tab-btn').forEach(btn => btn.classList.remove('active'));
        if (event && event.target) event.target.classList.add('active');
        
        if (tabName === 'jobs') loadJobs();
        if (tabName === 'candidates') loadCandidates();
        if (tabName === 'analyze') { loadJobs(); loadCandidates(); }
    }
    
    async function loadJobs() {
        const res = await fetch('/api/jobs');
        jobsData = await res.json();
        const container = document.getElementById('jobs-list');
        if (!jobsData.length) { container.innerHTML = '<div class="card no-click">No jobs yet. Create one.</div>'; return; }
        container.innerHTML = jobsData.map(job => `<div class="card no-click"><h3>${escapeHtml(job.title)}</h3>${job.company ? `<p>🏢 ${escapeHtml(job.company)}</p>` : ''}<small>📅 ${new Date(job.created_at).toLocaleDateString()}</small></div>`).join('');
        document.getElementById('job-select').innerHTML = '<option value="">-- Select Job --</option>' + jobsData.map(j => `<option value="${j.id}">${escapeHtml(j.title)}</option>`).join('');
    }
    
    async function loadCandidates() {
        const res = await fetch('/api/candidates');
        candidatesData = await res.json();
        renderCandidates(candidatesData);
        document.getElementById('candidate-select').innerHTML = '<option value="">-- Select Candidate --</option>' + candidatesData.map(c => `<option value="${c.id}">${escapeHtml(c.first_name + ' ' + c.last_name || 'Unknown')}</option>`).join('');
    }
    
    function renderCandidates(candidates) {
        const container = document.getElementById('candidates-list');
        if (!candidates.length) { container.innerHTML = '<div class="card no-click">No candidates yet. Upload resumes.</div>'; return; }
        container.innerHTML = candidates.map(c => {
            const fullName = `${c.first_name || ''} ${c.last_name || ''}`.trim() || 'Unknown';
            const skills = c.core_skills ? JSON.parse(c.core_skills) : [];
            return `<div class="card" onclick="viewCandidate(${c.id})"><h3>👤 ${escapeHtml(fullName)}</h3>${c.email ? `<p>📧 ${escapeHtml(c.email)}</p>` : ''}<p>🔧 ${skills.slice(0,3).map(s => `<span class="skill-tag">${escapeHtml(s.skill)}</span>`).join('')}</p>${c.match_score ? `<p>🎯 Score: <span class="${c.match_score >= 70 ? 'match-high' : (c.match_score >= 40 ? 'match-medium' : 'match-low')}">${c.match_score}%</span></p>` : ''}<small>📅 ${new Date(c.created_at).toLocaleDateString()}</small></div>`;
        }).join('');
    }
    
    function filterCandidates() {
        const term = document.getElementById('search-input').value.toLowerCase();
        const filtered = candidatesData.filter(c => {
            const name = `${c.first_name || ''} ${c.last_name || ''}`.toLowerCase();
            const skills = c.core_skills ? JSON.parse(c.core_skills).map(s => s.skill.toLowerCase()).join(' ') : '';
            return name.includes(term) || skills.includes(term);
        });
        renderCandidates(filtered);
    }
    
    function clearSearch() { document.getElementById('search-input').value = ''; renderCandidates(candidatesData); }
    
    async function viewCandidate(id) {
        const c = candidatesData.find(c => c.id == id);
        if (!c) return;
        const fullName = `${c.first_name || ''} ${c.last_name || ''}`.trim();
        const workExp = JSON.parse(c.work_experience || '[]');
        const skills = JSON.parse(c.core_skills || '[]');
        document.getElementById('modal-body').innerHTML = `
            <div class="detail-row"><div class="detail-label">Name:</div><div class="detail-value">${escapeHtml(fullName)}</div></div>
            <div class="detail-row"><div class="detail-label">Email:</div><div class="detail-value">${escapeHtml(c.email || 'N/A')}</div></div>
            <div class="detail-row"><div class="detail-label">Phone:</div><div class="detail-value">${escapeHtml(c.phone || 'N/A')}</div></div>
            <div class="detail-row"><div class="detail-label">Current Role:</div><div class="detail-value">${escapeHtml(c.current_role || 'N/A')}</div></div>
            <h4>💼 Skills</h4>${skills.map(s => `<span class="skill-tag">${escapeHtml(s.skill)} (${s.years_of_experience || '?'} yrs)</span>`).join('') || 'None'}
            <h4>💼 Work Experience</h4>${workExp.map(w => `<div><strong>${escapeHtml(w.company)}</strong> - ${escapeHtml(w.role)}</div>`).join('') || 'None'}
            <button class="btn-primary" onclick="closeModal()" style="margin-top:15px;">Close</button>
        `;
        document.getElementById('candidateModal').style.display = 'block';
    }
    
    function closeModal() { document.getElementById('candidateModal').style.display = 'none'; }
    
    // Parse Resume
    document.getElementById('parse-resume-btn').onclick = async function() {
        const file = document.getElementById('resume-file').files[0];
        if (!file) { alert('Select a file'); return; }
        const fd = new FormData();
        fd.append('resume', file);
        const div = document.getElementById('parse-result');
        div.innerHTML = '<div class="spinner"></div><p>Parsing with Groq AI...</p>';
        try {
            const res = await fetch('/api/parse-resume', { method: 'POST', body: fd });
            const result = await res.json();
            if (result.error) { div.innerHTML = `<div class="alert-error">${result.error}</div>`; return; }
            div.innerHTML = `<div class="alert-success"><h4>✅ Resume Parsed</h4><p><strong>Name:</strong> ${escapeHtml(result.first_name || '')} ${escapeHtml(result.last_name || '')}</p><p><strong>Email:</strong> ${escapeHtml(result.email || '')}</p><p><strong>Phone:</strong> ${escapeHtml(result.phone || '')}</p><p><strong>Skills:</strong> ${result.core_skills ? result.core_skills.map(s => `<span class="skill-tag">${escapeHtml(s.skill)}</span>`).join('') : 'None'}</p><button class="btn-primary" id="save-candidate-btn">💾 Save Candidate</button></div>`;
            document.getElementById('save-candidate-btn').onclick = async function() {
                const saveRes = await fetch('/api/candidates', { method: 'POST', headers: {'Content-Type':'application/json'}, body: JSON.stringify(result) });
                if (saveRes.ok) { alert('Candidate saved!'); div.innerHTML = ''; document.getElementById('resume-file').value = ''; loadCandidates(); }
                else alert('Error saving');
            };
        } catch(e) { div.innerHTML = '<div class="alert-error">Error parsing</div>'; }
    };
    
    // Analyze Match
    document.getElementById('analyze-btn').onclick = async function() {
        const jobId = document.getElementById('job-select').value;
        const candidateId = document.getElementById('candidate-select').value;
        if (!jobId || !candidateId) { alert('Select both Job and Candidate'); return; }
        const job = jobsData.find(j => j.id == jobId);
        const cand = candidatesData.find(c => c.id == candidateId);
        const div = document.getElementById('analyze-result');
        div.innerHTML = '<div class="spinner"></div><p>Groq AI analyzing...</p>';
        try {
            const res = await fetch('/api/analyze-match', { method: 'POST', headers: {'Content-Type':'application/json'}, body: JSON.stringify({ jd_text: job.description || '', resume_text: cand.resume_text || '' }) });
            const result = await res.json();
            if (result.error) { div.innerHTML = `<div class="alert-error">${result.error}</div>`; return; }
            const matchClass = result.match_score >= 70 ? 'match-high' : (result.match_score >= 40 ? 'match-medium' : 'match-low');
            div.innerHTML = `<div class="alert-success"><h4>📊 Analysis Complete</h4><p><strong>Match Score:</strong> <span class="${matchClass}">${result.match_score || 0}%</span></p><p><strong>Recommendation:</strong> ${result.recommendation || 'Review'}</p>${result.executive_summary ? `<div style="margin-top:10px;">${escapeHtml(result.executive_summary.final_verdict || '')}</div>` : ''}${result.pre_screening_questions ? `<div style="margin-top:10px;"><strong>Questions:</strong><ul>${result.pre_screening_questions.map(q => `<li>${escapeHtml(q)}</li>`).join('')}</ul></div>` : ''}<small>✅ Analysis saved</small></div>`;
        } catch(e) { div.innerHTML = '<div class="alert-error">Analysis failed</div>'; }
    };
    
    window.exportToCSV = function() { window.location.href = '/api/export-candidates'; };
    
    document.getElementById('job-form').onsubmit = async function(e) {
        e.preventDefault();
        const data = { title: document.getElementById('job-title').value, company: document.getElementById('job-company').value, description: document.getElementById('job-desc').value };
        if (!data.title) { alert('Title required'); return; }
        const res = await fetch('/api/jobs', { method: 'POST', headers: {'Content-Type':'application/json'}, body: JSON.stringify(data) });
        if (res.ok) { alert('Job created!'); document.getElementById('job-title').value = ''; document.getElementById('job-company').value = ''; document.getElementById('job-desc').value = ''; showTab('jobs'); loadJobs(); }
        else alert('Error');
    };
    
    function escapeHtml(str) { if (!str) return ''; return str.replace(/[&<>]/g, function(m) { if (m === '&') return '&amp;'; if (m === '<') return '&lt;'; if (m === '>') return '&gt;'; return m; }); }
    
    loadJobs();
    loadCandidates();
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
    filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
    file.save(filepath)
    
    if filename.endswith('.pdf'):
        text = extract_text_from_pdf(filepath)
    else:
        text = extract_text_from_docx(filepath)
    
    if not text:
        os.remove(filepath)
        return jsonify({'error': 'Could not extract text'}), 400
    
    result = parse_resume_file(filepath)
    os.remove(filepath)
    
    if not result.get('error'):
        result['file_path'] = filepath
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
    skills = json.dumps(data.get('core_skills', []))
    work_exp = json.dumps(data.get('work_experience', []))
    certs = json.dumps(data.get('certifications', []))
    
    conn = sqlite3.connect('shahnai.db')
    c = conn.cursor()
    c.execute('''INSERT INTO candidates 
        (first_name, last_name, middle_name, phone, email, address, linkedin,
         current_role, employment_status, notice_period_days, work_experience, certifications,
         core_skills, education, resume_text, resume_filename)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)''',
        (data.get('first_name'), data.get('last_name'), data.get('middle_name'),
         data.get('phone'), data.get('email'), data.get('address'), data.get('linkedin'),
         data.get('current_role'), data.get('employment_status'), data.get('notice_period_days', 0),
         work_exp, certs, skills, data.get('education'), data.get('resume_text'), data.get('resume_filename')))
    
    candidate_id = c.lastrowid
    conn.commit()
    conn.close()
    return jsonify({'message': 'Candidate saved', 'id': candidate_id})

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
    
    if not resume_text or not jd_text:
        return jsonify({'error': 'Missing text'}), 400
    
    if not GROQ_ENABLED:
        return jsonify({'error': 'Groq API not configured'}), 503
    
    result = analyze_match_with_groq(resume_text, jd_text)
    
    if result:
        return jsonify(result)
    
    return jsonify({'error': 'Analysis failed'}), 500

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
