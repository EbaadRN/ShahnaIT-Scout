# app.py - COMPLETE WORKING VERSION with HTTP Gemini API
import os
import re
import sqlite3
import csv
import io
import json
import requests
from datetime import datetime
from flask import Flask, request, jsonify, render_template_string, Response
from flask_cors import CORS
from werkzeug.utils import secure_filename
import PyPDF2
import docx

app = Flask(__name__)
CORS(app)

# Configuration
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024
app.config['UPLOAD_FOLDER'] = '/tmp'
ALLOWED_EXTENSIONS = {'pdf', 'docx'}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

# ============ GEMINI SETUP - HTTP DIRECT API ============
GEMINI_ENABLED = False
GEMINI_API_KEY = os.getenv('GEMINI_API_KEY')

if GEMINI_API_KEY:
    GEMINI_ENABLED = True
    print("✅✅✅ Gemini API configured - Using HTTP direct calls ✅✅✅")
else:
    print("❌ No GEMINI_API_KEY found")

def analyze_with_gemini(resume_text, jd_text):
    """Comprehensive JD vs Resume analysis using HTTP Gemini API"""
    if not GEMINI_API_KEY:
        return None
    
    # Truncate texts to avoid token limits
    resume_text = resume_text[:2000]
    jd_text = jd_text[:2000]
    
    prompt = f"""You are an expert recruitment analyst. Analyze this resume against the job description.

JOB DESCRIPTION:
{jd_text}

RESUME:
{resume_text}

Return ONLY valid JSON with these exact fields (no other text before or after the JSON):
{{
    "match_score": 75,
    "relevance_feedback": "The candidate has strong experience in required technologies...",
    "genuineness_score": 85,
    "genuineness_feedback": "Profile appears authentic with consistent work history...",
    "strengths": ["React expertise", "Cloud experience", "Leadership"],
    "gaps": ["Missing Python", "Limited database experience"],
    "recommendation": "interview"
}}

Do not include any text before or after the JSON. Just the JSON object."""
    
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key={GEMINI_API_KEY}"
    
    payload = {
        "contents": [{
            "parts": [{"text": prompt}]
        }],
        "generationConfig": {
            "temperature": 0.1,
            "maxOutputTokens": 1000,
            "responseMimeType": "application/json"
        }
    }
    
    try:
        print(f"Calling Gemini API for analysis...")
        response = requests.post(url, json=payload, timeout=30)
        print(f"Response status: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            
            if 'candidates' in data and len(data['candidates']) > 0:
                text_response = data['candidates'][0]['content']['parts'][0]['text']
                print(f"Raw response received")
                
                # Clean the response
                text_response = text_response.strip()
                if text_response.startswith('```json'):
                    text_response = text_response[7:]
                if text_response.startswith('```'):
                    text_response = text_response[3:]
                if text_response.endswith('```'):
                    text_response = text_response[:-3]
                
                # Try to parse JSON
                result = json.loads(text_response)
                
                # Ensure all fields exist
                default_result = {
                    'match_score': 0,
                    'relevance_feedback': 'Analysis completed but no specific feedback generated.',
                    'genuineness_score': 50,
                    'genuineness_feedback': 'Unable to assess authenticity fully.',
                    'strengths': [],
                    'gaps': [],
                    'recommendation': 'review'
                }
                default_result.update(result)
                
                print(f"✅ Gemini analysis successful - Match: {default_result['match_score']}%")
                return default_result
            else:
                print(f"No candidates in response")
                return None
        else:
            print(f"API error: {response.status_code}")
            return None
    except json.JSONDecodeError as e:
        print(f"JSON parse error: {e}")
        return None
    except Exception as e:
        print(f"Gemini API error: {e}")
        return None

def parse_resume_with_gemini(resume_text):
    """Simple resume parsing using HTTP Gemini API"""
    if not GEMINI_API_KEY:
        return None
    
    resume_text = resume_text[:2000]
    
    prompt = f"""Extract information from this resume. Return ONLY valid JSON.

Resume: {resume_text}

Return JSON: {{"name": "", "email": "", "phone": "", "skills": [], "work_history": "", "certifications": ""}}"""
    
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key={GEMINI_API_KEY}"
    
    payload = {
        "contents": [{
            "parts": [{"text": prompt}]
        }],
        "generationConfig": {
            "temperature": 0.1,
            "maxOutputTokens": 500,
            "responseMimeType": "application/json"
        }
    }
    
    try:
        response = requests.post(url, json=payload, timeout=30)
        if response.status_code == 200:
            data = response.json()
            if 'candidates' in data and len(data['candidates']) > 0:
                text_response = data['candidates'][0]['content']['parts'][0]['text']
                text_response = text_response.strip()
                if text_response.startswith('```json'):
                    text_response = text_response[7:]
                if text_response.startswith('```'):
                    text_response = text_response[3:]
                if text_response.endswith('```'):
                    text_response = text_response[:-3]
                return json.loads(text_response)
        return None
    except Exception as e:
        print(f"Gemini parse error: {e}")
        return None

# ============ DATABASE SETUP ============
def init_db():
    conn = sqlite3.connect('shahnai.db')
    c = conn.cursor()
    
    c.execute('''CREATE TABLE IF NOT EXISTS jobs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        title TEXT NOT NULL,
        company TEXT,
        description TEXT,
        requirements TEXT,
        required_skills TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )''')
    
    c.execute('''CREATE TABLE IF NOT EXISTS candidates (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT,
        email TEXT,
        phone TEXT,
        skills TEXT,
        work_history TEXT,
        certifications TEXT,
        education TEXT,
        resume_text TEXT,
        job_id INTEGER,
        match_score INTEGER,
        relevance_feedback TEXT,
        genuineness_score INTEGER,
        genuineness_feedback TEXT,
        strengths TEXT,
        gaps TEXT,
        recommendation TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )''')
    
    conn.commit()
    conn.close()
    print("✅ Database initialized")

init_db()

# ============ SKILLS DATABASE FOR BASIC PARSING ============
COMMON_SKILLS = [
    'Python', 'Java', 'JavaScript', 'TypeScript', 'React', 'Angular', 'Vue', 'Node.js',
    'SQL', 'MongoDB', 'PostgreSQL', 'MySQL', 'AWS', 'Azure', 'GCP', 'Docker', 'Kubernetes',
    'Machine Learning', 'AI', 'Data Science', 'Excel', 'Tableau', 'Power BI',
    'HTML', 'CSS', 'Git', 'REST API', 'GraphQL', 'C++', 'C#', '.NET', 'PHP', 'Ruby',
    'Leadership', 'Project Management', 'Agile', 'Scrum', 'Communication'
]

def extract_skills_from_text(text):
    if not text:
        return []
    text_lower = text.lower()
    found_skills = []
    for skill in COMMON_SKILLS:
        if skill.lower() in text_lower:
            found_skills.append(skill)
    return found_skills

def calculate_match_score(candidate_skills, job_skills):
    if not job_skills:
        return 0
    candidate_set = set([s.lower() for s in candidate_skills])
    job_set = set([s.lower() for s in job_skills])
    if not job_set:
        return 0
    matches = len(candidate_set.intersection(job_set))
    score = int((matches / len(job_set)) * 100)
    return min(score, 100)

# ============ RESUME TEXT EXTRACTION ============
def extract_text_from_pdf(file_path):
    try:
        text = ""
        with open(file_path, 'rb') as file:
            pdf_reader = PyPDF2.PdfReader(file)
            for page in pdf_reader.pages:
                page_text = page.extract_text()
                if page_text:
                    text += page_text
        return text
    except Exception as e:
        print(f"PDF error: {e}")
        return ""

def extract_text_from_docx(file_path):
    try:
        doc = docx.Document(file_path)
        text = "\n".join([p.text for p in doc.paragraphs])
        return text
    except Exception as e:
        print(f"DOCX error: {e}")
        return ""

def extract_email(text):
    pattern = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
    emails = re.findall(pattern, text)
    return emails[0] if emails else ""

def extract_phone(text):
    patterns = [
        r'\b\d{10}\b',
        r'\b\d{3}[-.]?\d{3}[-.]?\d{4}\b',
        r'\(\d{3}\)\s*\d{3}[-.]?\d{4}'
    ]
    for pattern in patterns:
        phones = re.findall(pattern, text)
        if phones:
            return phones[0]
    return ""

def extract_name(text):
    lines = text.strip().split('\n')
    if lines:
        first_line = lines[0].strip()
        if len(first_line) < 50 and len(first_line) > 2:
            return first_line
    return "Unknown"

def extract_work_history(text):
    lines = text.split('\n')
    experience = []
    keywords = ['experience', 'work', 'employment', 'job', 'position', 'role', 'senior', 'lead']
    for line in lines[:60]:
        line_lower = line.lower()
        if any(kw in line_lower for kw in keywords):
            clean_line = re.sub(r'\s+', ' ', line).strip()
            if 10 < len(clean_line) < 300:
                experience.append(clean_line)
    return ' | '.join(experience[:3]) if experience else ""

def extract_certifications(text):
    cert_keywords = ['certified', 'certification', 'certificate', 'PMP', 'CISSP', 'AWS',
                     'Scrum', 'ITIL', 'CPA', 'CFA', 'CCNA', 'MCSE', 'COMPTIA']
    found = []
    text_lower = text.lower()
    for keyword in cert_keywords:
        if keyword.lower() in text_lower:
            sentences = re.split(r'[.!?\n]+', text)
            for sentence in sentences:
                if keyword.lower() in sentence.lower():
                    clean = re.sub(r'\s+', ' ', sentence).strip()
                    if 5 < len(clean) < 150:
                        found.append(clean)
                        break
    return ' | '.join(found[:3]) if found else ""

def parse_resume_file(file_path, jd_text=None):
    """Parse resume - uses Gemini if available, falls back to basic"""
    if file_path.endswith('.pdf'):
        text = extract_text_from_pdf(file_path)
    elif file_path.endswith('.docx'):
        text = extract_text_from_docx(file_path)
    else:
        text = ""
    
    if not text:
        return {'error': 'Could not extract text from file'}
    
    result = {
        'name': extract_name(text),
        'email': extract_email(text),
        'phone': extract_phone(text),
        'skills': extract_skills_from_text(text),
        'work_history': extract_work_history(text),
        'certifications': extract_certifications(text),
        'resume_text': text[:2000],
        'ai_used': False
    }
    
    # Try Gemini for enhanced parsing if available
    if GEMINI_API_KEY:
        gemini_result = parse_resume_with_gemini(text)
        if gemini_result:
            result['name'] = gemini_result.get('name', result['name'])
            result['email'] = gemini_result.get('email', result['email'])
            result['phone'] = gemini_result.get('phone', result['phone'])
            result['skills'] = gemini_result.get('skills', result['skills'])
            result['work_history'] = gemini_result.get('work_history', result['work_history'])
            result['certifications'] = gemini_result.get('certifications', result['certifications'])
            result['ai_used'] = True
            print("✅ Used Gemini for resume parsing")
    
    # If JD provided, also analyze match
    if jd_text and GEMINI_API_KEY:
        analysis = analyze_with_gemini(text, jd_text)
        if analysis:
            result['match_score'] = analysis.get('match_score', 0)
            result['relevance_feedback'] = analysis.get('relevance_feedback', '')
            result['genuineness_score'] = analysis.get('genuineness_score', 0)
            result['genuineness_feedback'] = analysis.get('genuineness_feedback', '')
            result['strengths'] = analysis.get('strengths', [])
            result['gaps'] = analysis.get('gaps', [])
            result['recommendation'] = analysis.get('recommendation', 'review')
            print("✅ Used Gemini for JD matching")
    
    return result

# ============ HTML TEMPLATE ============
HTML_TEMPLATE = '''
<!DOCTYPE html>
<html>
<head>
    <title>ShahnaIT Scout - Recruitment Platform</title>
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body { background-color: #F5F0E8; font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; color: #2C3E50; }
        .container { max-width: 1400px; margin: 0 auto; padding: 20px; }
        
        .header { background: linear-gradient(135deg, #1A4D4A 0%, #0F3533 100%); color: white; padding: 30px; border-radius: 16px; margin-bottom: 30px; }
        .header h1 { font-size: 2em; margin-bottom: 10px; }
        
        .badge-ai { display: inline-block; background: #27AE60; font-size: 12px; padding: 4px 12px; border-radius: 20px; margin-left: 10px; vertical-align: middle; }
        
        .tabs { display: flex; gap: 5px; margin-bottom: 30px; background: white; padding: 10px; border-radius: 12px; flex-wrap: wrap; }
        .tab-btn { background: transparent; border: none; padding: 12px 24px; font-size: 15px; cursor: pointer; color: #7F8C8D; border-radius: 8px; transition: all 0.3s; }
        .tab-btn:hover { background: #F5F0E8; color: #1A4D4A; }
        .tab-btn.active { background: #1A4D4A; color: white; }
        
        .card { background: white; border-radius: 12px; padding: 24px; margin-bottom: 20px; box-shadow: 0 2px 8px rgba(0,0,0,0.08); border-left: 4px solid #1A4D4A; transition: transform 0.2s; }
        .card:hover { transform: translateY(-2px); }
        .card h3 { color: #1A4D4A; margin-bottom: 12px; }
        
        .btn-primary { background: #1A4D4A; color: white; border: none; padding: 12px 24px; border-radius: 8px; cursor: pointer; font-weight: 600; margin-right: 10px; margin-bottom: 10px; transition: all 0.3s; }
        .btn-primary:hover { background: #2A6B67; transform: translateY(-1px); }
        .btn-secondary { background: #7F8C8D; color: white; border: none; padding: 12px 24px; border-radius: 8px; cursor: pointer; }
        
        input, textarea, select { width: 100%; padding: 12px; margin: 10px 0 15px 0; border: 1px solid #ddd; border-radius: 8px; font-size: 14px; }
        input:focus, textarea:focus, select:focus { outline: none; border-color: #1A4D4A; }
        
        .alert-success { background: #27AE60; color: white; padding: 14px; border-radius: 8px; margin: 10px 0; }
        .alert-error { background: #E74C3C; color: white; padding: 14px; border-radius: 8px; margin: 10px 0; }
        .alert-info { background: #3498DB; color: white; padding: 14px; border-radius: 8px; margin: 10px 0; }
        
        .spinner { border: 3px solid #F5F0E8; border-top: 3px solid #1A4D4A; border-radius: 50%; width: 40px; height: 40px; animation: spin 0.8s linear infinite; margin: 20px auto; }
        @keyframes spin { 0% { transform: rotate(0deg); } 100% { transform: rotate(360deg); } }
        
        .skill-tag { display: inline-block; background: #F5F0E8; padding: 4px 12px; border-radius: 20px; margin: 3px; font-size: 12px; }
        .match-high { color: #27AE60; font-weight: bold; font-size: 1.1em; }
        .match-medium { color: #F39C12; font-weight: bold; font-size: 1.1em; }
        .match-low { color: #E74C3C; font-weight: bold; font-size: 1.1em; }
        
        .flex { display: flex; gap: 20px; flex-wrap: wrap; }
        .flex-2 { flex: 2; }
        .flex-1 { flex: 1; }
        
        @media (max-width: 768px) { .container { padding: 10px; } .tab-btn { padding: 8px 16px; } .flex { flex-direction: column; } }
        .text-center { text-align: center; }
        .mt-20 { margin-top: 20px; }
        .mb-20 { margin-bottom: 20px; }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🎯 ShahnaIT Scout 
                {% if gemini_enabled %}
                <span class="badge-ai">🤖 AI ENHANCED</span>
                {% else %}
                <span class="badge-ai" style="background:#E74C3C;">⚠️ AI DISABLED</span>
                {% endif %}
            </h1>
            <p>Intelligent Recruitment Platform with AI Resume Analysis, JD Matching & Profile Authenticity Scoring</p>
        </div>
        
        <div class="tabs">
            <button class="tab-btn active" onclick="showTab('jobs')">📋 Jobs</button>
            <button class="tab-btn" onclick="showTab('candidates')">👥 Candidates</button>
            <button class="tab-btn" onclick="showTab('upload')">📄 Upload Resume</button>
            <button class="tab-btn" onclick="showTab('create-job')">➕ Create Job</button>
            <button class="tab-btn" onclick="showTab('analyze')">🔍 Analyze Match</button>
        </div>
        
        <div id="jobs-tab"><div id="jobs-list" class="mt-20"></div></div>
        
        <div id="candidates-tab" style="display:none;">
            <button class="btn-primary" onclick="exportToCSV()">📥 Export to CSV</button>
            <div id="candidates-list" class="mt-20"></div>
        </div>
        
        <div id="upload-tab" style="display:none;">
            <div class="card">
                <h3>📄 Upload Resume (PDF or DOCX)</h3>
                {% if gemini_enabled %}
                <div class="alert-info" style="background:#27AE60;">✅ Gemini AI is ACTIVE - Enhanced parsing enabled</div>
                {% else %}
                <div class="alert-info" style="background:#F39C12;">⚠️ Gemini AI is DISABLED - Add GEMINI_API_KEY to Railway variables</div>
                {% endif %}
                <input type="file" id="resume-file" accept=".pdf,.docx">
                <select id="upload-job-select" style="margin: 10px 0;">
                    <option value="">-- Optional: Select Job for Match Analysis --</option>
                </select>
                <button class="btn-primary" onclick="uploadResume()">🔍 Parse Resume & Analyze</button>
                <div id="parse-result" class="mt-20"></div>
            </div>
        </div>
        
        <div id="create-job-tab" style="display:none;">
            <div class="card">
                <h3>➕ Create New Job Posting</h3>
                <form onsubmit="createJob(event)">
                    <input type="text" id="job-title" placeholder="Job Title *" required>
                    <input type="text" id="job-company" placeholder="Company Name">
                    <textarea id="job-desc" rows="5" placeholder="Job Description (skills will be auto-extracted)"></textarea>
                    <textarea id="job-reqs" rows="3" placeholder="Requirements (optional)"></textarea>
                    <button type="submit" class="btn-primary">Create Job</button>
                </form>
            </div>
        </div>
        
        <div id="analyze-tab" style="display:none;">
            <div class="card">
                <h3>🔍 AI-Powered Resume-JD Match Analysis</h3>
                <p>Get match score, relevance feedback, profile authenticity assessment, and hiring recommendation</p>
                
                <div class="flex">
                    <div class="flex-1">
                        <label>📋 Select Job Description</label>
                        <select id="analyze-job-select" class="mb-20">
                            <option value="">-- Select a Job --</option>
                        </select>
                    </div>
                    <div class="flex-1">
                        <label>👤 Select Resume/Candidate</label>
                        <select id="analyze-candidate-select" class="mb-20">
                            <option value="">-- Select a Candidate --</option>
                        </select>
                    </div>
                </div>
                
                <button class="btn-primary" onclick="analyzeMatch()">🔍 Run AI Analysis</button>
                <div id="analyze-result" class="mt-20"></div>
            </div>
        </div>
    </div>
    
    <script>
        let jobsData = [];
        let candidatesData = [];
        let geminiEnabled = {{ 'true' if gemini_enabled else 'false' }};
        
        function showTab(tabName) {
            const tabs = ['jobs', 'candidates', 'upload', 'create-job', 'analyze'];
            tabs.forEach(tab => {
                const el = document.getElementById(tab + '-tab');
                if (el) el.style.display = 'none';
            });
            document.getElementById(tabName + '-tab').style.display = 'block';
            
            document.querySelectorAll('.tab-btn').forEach(btn => btn.classList.remove('active'));
            if (event && event.target) event.target.classList.add('active');
            
            if (tabName === 'jobs') loadJobs();
            if (tabName === 'candidates') loadCandidates();
            if (tabName === 'analyze') { loadJobs(); loadCandidates(); }
            if (tabName === 'upload') loadJobs();
        }
        
        async function loadJobs() {
            try {
                const response = await fetch('/api/jobs');
                jobsData = await response.json();
                const container = document.getElementById('jobs-list');
                if (!jobsData.length) {
                    container.innerHTML = '<div class="card text-center">No jobs yet. Create one using the "Create Job" tab.</div>';
                    return;
                }
                container.innerHTML = jobsData.map(job => `
                    <div class="card">
                        <h3>${escapeHtml(job.title)}</h3>
                        ${job.company ? `<p><strong>Company:</strong> ${escapeHtml(job.company)}</p>` : ''}
                        ${job.required_skills ? `<p><strong>🔧 Required Skills:</strong> ${job.required_skills.split(',').map(s => `<span class="skill-tag">${escapeHtml(s.trim())}</span>`).join('')}</p>` : ''}
                        <small>📅 Created: ${new Date(job.created_at).toLocaleDateString()}</small>
                    </div>
                `).join('');
                
                const jobOptions = '<option value="">-- Select a Job --</option>' + jobsData.map(job => `<option value="${job.id}">${escapeHtml(job.title)}</option>`).join('');
                const jobSelects = ['analyze-job-select', 'upload-job-select'];
                jobSelects.forEach(id => {
                    const select = document.getElementById(id);
                    if (select) select.innerHTML = jobOptions;
                });
            } catch (error) {
                document.getElementById('jobs-list').innerHTML = '<div class="alert-error">Error loading jobs</div>';
            }
        }
        
        async function loadCandidates() {
            try {
                const response = await fetch('/api/candidates');
                candidatesData = await response.json();
                const container = document.getElementById('candidates-list');
                if (!candidatesData.length) {
                    container.innerHTML = '<div class="card text-center">No candidates yet. Upload resumes to add candidates.</div>';
                    return;
                }
                container.innerHTML = candidatesData.map(c => {
                    const matchClass = c.match_score >= 70 ? 'match-high' : (c.match_score >= 40 ? 'match-medium' : 'match-low');
                    return `
                    <div class="card">
                        <h3>${escapeHtml(c.name || 'Unknown')}</h3>
                        ${c.email ? `<p><strong>📧 Email:</strong> ${escapeHtml(c.email)}</p>` : ''}
                        ${c.phone ? `<p><strong>📞 Phone:</strong> ${escapeHtml(c.phone)}</p>` : ''}
                        ${c.skills ? `<p><strong>🔧 Skills:</strong> ${c.skills.split(',').map(s => `<span class="skill-tag">${escapeHtml(s.trim())}</span>`).join('')}</p>` : ''}
                        ${c.work_history ? `<p><strong>💼 Work History:</strong> ${escapeHtml(c.work_history.substring(0, 200))}${c.work_history.length > 200 ? '...' : ''}</p>` : ''}
                        ${c.certifications ? `<p><strong>📜 Certifications:</strong> ${escapeHtml(c.certifications)}</p>` : ''}
                        ${c.match_score ? `<p><strong>🎯 Match Score:</strong> <span class="${matchClass}">${c.match_score}%</span></p>` : ''}
                        ${c.genuineness_score ? `<p><strong>✅ Genuineness Score:</strong> ${c.genuineness_score}%</p>` : ''}
                        ${c.recommendation ? `<p><strong>📌 Recommendation:</strong> <span class="skill-tag">${escapeHtml(c.recommendation)}</span></p>` : ''}
                        <small>📅 Added: ${new Date(c.created_at).toLocaleDateString()}</small>
                    </div>`;
                }).join('');
                
                const candidateSelect = document.getElementById('analyze-candidate-select');
                if (candidateSelect) {
                    candidateSelect.innerHTML = '<option value="">-- Select a Candidate --</option>' + 
                        candidatesData.map(c => `<option value="${c.id}">${escapeHtml(c.name || 'Unknown')}</option>`).join('');
                }
            } catch (error) {
                document.getElementById('candidates-list').innerHTML = '<div class="alert-error">Error loading candidates</div>';
            }
        }
        
        async function uploadResume() {
            const fileInput = document.getElementById('resume-file');
            const file = fileInput.files[0];
            if (!file) { alert('Please select a file'); return; }
            
            const jobSelect = document.getElementById('upload-job-select');
            const jobId = jobSelect ? jobSelect.value : null;
            const selectedJob = jobId ? jobsData.find(j => j.id == jobId) : null;
            
            const formData = new FormData();
            formData.append('resume', file);
            if (selectedJob && selectedJob.description) {
                formData.append('jd_text', selectedJob.description);
            }
            
            const resultDiv = document.getElementById('parse-result');
            resultDiv.innerHTML = '<div class="spinner"></div><p class="text-center">Parsing resume' + (geminiEnabled ? ' with AI...' : '...') + '</p>';
            
            try {
                const response = await fetch('/api/parse-resume', {
                    method: 'POST',
                    body: formData
                });
                const result = await response.json();
                
                if (result.error) {
                    resultDiv.innerHTML = `<div class="alert-error">${result.error}</div>`;
                    return;
                }
                
                let aiBadge = result.ai_used ? '<span style="background:#27AE60; padding:2px 8px; border-radius:12px; margin-left:10px; font-size:12px;">🤖 AI</span>' : '<span style="background:#F39C12; padding:2px 8px; border-radius:12px; margin-left:10px; font-size:12px;">⚙️ Basic</span>';
                
                resultDiv.innerHTML = `
                    <div class="alert-success">
                        <h4>✅ Resume Parsed! ${aiBadge}</h4>
                        <p><strong>Name:</strong> ${escapeHtml(result.name || 'Not found')}</p>
                        <p><strong>Email:</strong> ${escapeHtml(result.email || 'Not found')}</p>
                        <p><strong>Phone:</strong> ${escapeHtml(result.phone || 'Not found')}</p>
                        <p><strong>Skills:</strong> ${result.skills ? result.skills.map(s => `<span class="skill-tag">${escapeHtml(s)}</span>`).join('') : 'None'}</p>
                        <p><strong>Work History:</strong> ${escapeHtml((result.work_history || 'None').substring(0, 200))}${result.work_history && result.work_history.length > 200 ? '...' : ''}</p>
                        <p><strong>Certifications:</strong> ${escapeHtml(result.certifications || 'None')}</p>
                        ${result.match_score ? `<p><strong>🎯 Match Score:</strong> <span class="${result.match_score >= 70 ? 'match-high' : (result.match_score >= 40 ? 'match-medium' : 'match-low')}">${result.match_score}%</span></p>` : ''}
                        ${result.genuineness_score ? `<p><strong>✅ Genuineness Score:</strong> ${result.genuineness_score}%</p>` : ''}
                        ${result.recommendation ? `<p><strong>📌 Recommendation:</strong> <span class="skill-tag">${escapeHtml(result.recommendation)}</span></p>` : ''}
                        ${result.relevance_feedback ? `<p><strong>📝 Feedback:</strong> ${escapeHtml(result.relevance_feedback)}</p>` : ''}
                        <button class="btn-primary" onclick='saveCandidate(${JSON.stringify(result).replace(/'/g, "\\'")})' style="margin-top:15px">💾 Save Candidate</button>
                    </div>
                `;
            } catch (error) {
                resultDiv.innerHTML = '<div class="alert-error">Error parsing resume</div>';
            }
        }
        
        async function saveCandidate(candidateData) {
            try {
                const response = await fetch('/api/candidates', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify(candidateData)
                });
                if (response.ok) {
                    alert('Candidate saved successfully!');
                    document.getElementById('parse-result').innerHTML = '';
                    document.getElementById('resume-file').value = '';
                    loadCandidates();
                } else {
                    alert('Error saving candidate');
                }
            } catch (error) {
                alert('Error saving candidate');
            }
        }
        
        async function analyzeMatch() {
            const jobId = document.getElementById('analyze-job-select').value;
            const candidateId = document.getElementById('analyze-candidate-select').value;
            
            if (!jobId || !candidateId) {
                alert('Please select both a Job and a Candidate');
                return;
            }
            
            const job = jobsData.find(j => j.id == jobId);
            const candidate = candidatesData.find(c => c.id == candidateId);
            
            if (!job || !candidate) {
                alert('Job or Candidate not found');
                return;
            }
            
            const resultDiv = document.getElementById('analyze-result');
            resultDiv.innerHTML = '<div class="spinner"></div><p class="text-center">🤖 Running AI analysis with Gemini...</p>';
            
            try {
                const response = await fetch('/api/analyze-match', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({
                        job_id: parseInt(jobId),
                        candidate_id: parseInt(candidateId),
                        jd_text: job.description || '',
                        resume_text: candidate.resume_text || ''
                    })
                });
                
                const result = await response.json();
                
                if (result.error) {
                    resultDiv.innerHTML = `<div class="alert-error">❌ ${result.error}</div>`;
                    return;
                }
                
                const matchClass = result.match_score >= 70 ? 'match-high' : (result.match_score >= 40 ? 'match-medium' : 'match-low');
                const genuinenessClass = result.genuineness_score >= 70 ? 'match-high' : (result.genuineness_score >= 40 ? 'match-medium' : 'match-low');
                
                resultDiv.innerHTML = `
                    <div class="alert-success">
                        <h4>📊 AI Analysis Complete</h4>
                        <div class="flex">
                            <div class="flex-1">
                                <p><strong>🎯 Match Score:</strong> <span class="${matchClass}">${result.match_score || 0}%</span></p>
                                <p><strong>✅ Genuineness Score:</strong> <span class="${genuinenessClass}">${result.genuineness_score || 0}%</span></p>
                                <p><strong>📌 Recommendation:</strong> <span class="skill-tag">${escapeHtml(result.recommendation || 'Review')}</span></p>
                            </div>
                            <div class="flex-1">
                                <p><strong>💪 Strengths:</strong> ${result.strengths ? result.strengths.map(s => `<span class="skill-tag">${escapeHtml(s)}</span>`).join('') : 'None identified'}</p>
                                <p><strong>⚠️ Gaps:</strong> ${result.gaps ? result.gaps.map(g => `<span class="skill-tag">${escapeHtml(g)}</span>`).join('') : 'None identified'}</p>
                            </div>
                        </div>
                        <p><strong>📝 Relevance Feedback:</strong> ${escapeHtml(result.relevance_feedback || 'N/A')}</p>
                        <p><strong>🔍 Authenticity Assessment:</strong> ${escapeHtml(result.genuineness_feedback || 'N/A')}</p>
                    </div>
                `;
            } catch (error) {
                resultDiv.innerHTML = '<div class="alert-error">❌ Error during analysis. Please check that Gemini API key is configured correctly.</div>';
            }
        }
        
        async function exportToCSV() {
            window.location.href = '/api/export-candidates';
        }
        
        async function createJob(event) {
            event.preventDefault();
            const jobData = {
                title: document.getElementById('job-title').value,
                company: document.getElementById('job-company').value,
                description: document.getElementById('job-desc').value,
                requirements: document.getElementById('job-reqs').value
            };
            if (!jobData.title) { alert('Job title is required'); return; }
            
            try {
                const response = await fetch('/api/jobs', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify(jobData)
                });
                if (response.ok) {
                    alert('Job created successfully!');
                    document.getElementById('job-title').value = '';
                    document.getElementById('job-company').value = '';
                    document.getElementById('job-desc').value = '';
                    document.getElementById('job-reqs').value = '';
                    showTab('jobs');
                    loadJobs();
                } else {
                    alert('Error creating job');
                }
            } catch (error) {
                alert('Error creating job');
            }
        }
        
        function escapeHtml(text) {
            if (!text) return '';
            if (typeof text !== 'string') text = String(text);
            const div = document.createElement('div');
            div.textContent = text;
            return div.innerHTML;
        }
        
        loadJobs();
        loadCandidates();
    </script>
</body>
</html>
'''

# ============ API ROUTES ============
@app.route('/')
def index():
    return render_template_string(HTML_TEMPLATE, gemini_enabled=GEMINI_ENABLED)

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
    description = data.get('description', '')
    required_skills = extract_skills_from_text(description)
    skills_str = ', '.join(required_skills)
    
    conn = sqlite3.connect('shahnai.db')
    c = conn.cursor()
    c.execute('''INSERT INTO jobs (title, company, description, requirements, required_skills) 
                 VALUES (?, ?, ?, ?, ?)''',
              (data.get('title'), data.get('company'), description, data.get('requirements', ''), skills_str))
    conn.commit()
    conn.close()
    return jsonify({'message': 'Job created', 'extracted_skills': required_skills})

@app.route('/api/jobs/<int:job_id>', methods=['GET'])
def get_job(job_id):
    conn = sqlite3.connect('shahnai.db')
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    c.execute('SELECT * FROM jobs WHERE id = ?', (job_id,))
    job = c.fetchone()
    conn.close()
    if job:
        return jsonify(dict(job))
    return jsonify({'error': 'Job not found'}), 404

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
    skills_str = ', '.join(data.get('skills', [])) if isinstance(data.get('skills'), list) else data.get('skills', '')
    strengths_str = ', '.join(data.get('strengths', [])) if isinstance(data.get('strengths'), list) else data.get('strengths', '')
    gaps_str = ', '.join(data.get('gaps', [])) if isinstance(data.get('gaps'), list) else data.get('gaps', '')
    
    conn = sqlite3.connect('shahnai.db')
    c = conn.cursor()
    c.execute('''INSERT INTO candidates (name, email, phone, skills, work_history, certifications, 
                 resume_text, job_id, match_score, relevance_feedback, genuineness_score, 
                 genuineness_feedback, strengths, gaps, recommendation) 
                 VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)''',
              (data.get('name'), data.get('email'), data.get('phone'), skills_str,
               data.get('work_history'), data.get('certifications'), data.get('resume_text', ''),
               data.get('job_id'), data.get('match_score'), data.get('relevance_feedback'),
               data.get('genuineness_score'), data.get('genuineness_feedback'),
               strengths_str, gaps_str, data.get('recommendation')))
    conn.commit()
    conn.close()
    return jsonify({'message': 'Candidate saved'})

@app.route('/api/analyze-match', methods=['POST'])
def analyze_match():
    """Endpoint for JD vs Resume analysis with Gemini HTTP API"""
    data = request.json
    resume_text = data.get('resume_text', '')
    jd_text = data.get('jd_text', '')
    
    if not resume_text or not jd_text:
        return jsonify({'error': 'Missing resume or job description'}), 400
    
    if not GEMINI_API_KEY:
        return jsonify({'error': 'Gemini AI not configured. Add GEMINI_API_KEY to Railway variables.'}), 503
    
    result = analyze_with_gemini(resume_text, jd_text)
    
    if result:
        return jsonify(result)
    else:
        return jsonify({'error': 'Gemini analysis failed. Please check API key and try again.'}), 500

@app.route('/api/export-candidates', methods=['GET'])
def export_candidates():
    conn = sqlite3.connect('shahnai.db')
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    c.execute('SELECT * FROM candidates ORDER BY created_at DESC')
    candidates = [dict(row) for row in c.fetchall()]
    conn.close()
    
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(['ID', 'Name', 'Email', 'Phone', 'Skills', 'Work History', 'Certifications', 
                     'Match Score', 'Relevance Feedback', 'Genuineness Score', 'Genuineness Feedback',
                     'Strengths', 'Gaps', 'Recommendation', 'Created Date'])
    for c in candidates:
        writer.writerow([
            c.get('id', ''), c.get('name', ''), c.get('email', ''), c.get('phone', ''),
            c.get('skills', ''), c.get('work_history', ''), c.get('certifications', ''),
            c.get('match_score', ''), c.get('relevance_feedback', ''), 
            c.get('genuineness_score', ''), c.get('genuineness_feedback', ''),
            c.get('strengths', ''), c.get('gaps', ''), c.get('recommendation', ''),
            c.get('created_at', '')
        ])
    
    output.seek(0)
    return Response(
        output.getvalue(),
        mimetype='text/csv',
        headers={'Content-Disposition': 'attachment; filename=candidates_export.csv'}
    )

@app.route('/api/parse-resume', methods=['POST'])
def parse_resume():
    if 'resume' not in request.files:
        return jsonify({'error': 'No file uploaded'}), 400
    
    file = request.files['resume']
    if file.filename == '':
        return jsonify({'error': 'No file selected'}), 400
    
    if not allowed_file(file.filename):
        return jsonify({'error': 'Invalid file type. Use PDF or DOCX'}), 400
    
    # Get JD text if provided
    jd_text = request.form.get('jd_text', None)
    
    filename = secure_filename(file.filename)
    filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
    file.save(filepath)
    
    result = parse_resume_file(filepath, jd_text)
    os.remove(filepath)
    
    return jsonify(result)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
