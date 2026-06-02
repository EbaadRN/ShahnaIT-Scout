# app.py - COMPLETE WITH GROQ API (Faster, No Billing Issues)
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

# ============ GROQ API SETUP ============
GROQ_ENABLED = False
GROQ_API_KEY = os.getenv('GROQ_API_KEY')

if GROQ_API_KEY and GROQ_API_KEY.startswith('gsk_'):
    GROQ_ENABLED = True
    print("✅✅✅ Groq API configured - Ready for fast AI analysis ✅✅✅")
else:
    print("❌ No valid GROQ_API_KEY found")

def call_groq_api(prompt, max_tokens=1000):
    """Call Groq API for AI analysis"""
    if not GROQ_API_KEY:
        return None
    
    url = "https://api.groq.com/openai/v1/chat/completions"
    
    headers = {
        "Authorization": f"Bearer {GROQ_API_KEY}",
        "Content-Type": "application/json"
    }
    
    payload = {
        "model": "llama-3.3-70b-versatile",
        "messages": [
            {
                "role": "user",
                "content": prompt
            }
        ],
        "temperature": 0.1,
        "max_tokens": max_tokens
    }
    
    try:
        print(f"Calling Groq API...")
        response = requests.post(url, json=payload, headers=headers, timeout=30)
        
        if response.status_code == 200:
            data = response.json()
            result_text = data['choices'][0]['message']['content']
            print(f"✅ Groq API call successful")
            return result_text
        else:
            print(f"Groq API error: {response.status_code} - {response.text[:100]}")
            return None
    except Exception as e:
        print(f"Groq API error: {e}")
        return None

def analyze_with_groq(resume_text, jd_text):
    """JD vs Resume analysis using Groq API"""
    if not GROQ_API_KEY:
        return None
    
    # Truncate texts to avoid token limits
    resume_text = resume_text[:2500]
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
    
    response_text = call_groq_api(prompt, max_tokens=1000)
    
    if response_text:
        try:
            response_text = response_text.strip()
            if response_text.startswith('```json'):
                response_text = response_text[7:]
            if response_text.startswith('```'):
                response_text = response_text[3:]
            if response_text.endswith('```'):
                response_text = response_text[:-3]
            
            result = json.loads(response_text)
            print(f"✅ Groq analysis successful - Match: {result.get('match_score', 0)}%")
            return result
        except json.JSONDecodeError as e:
            print(f"JSON parse error: {e}")
            return None
    
    return None

def parse_resume_with_groq(resume_text):
    """Parse resume using Groq API"""
    if not GROQ_API_KEY:
        return None
    
    resume_text = resume_text[:2500]
    
    prompt = f"""Extract information from this resume. Return ONLY valid JSON.

Resume: {resume_text}

Return JSON: {{"name": "", "email": "", "phone": "", "skills": [], "work_history": "", "certifications": ""}}"""
    
    response_text = call_groq_api(prompt, max_tokens=500)
    
    if response_text:
        try:
            response_text = response_text.strip()
            if response_text.startswith('```json'):
                response_text = response_text[7:]
            if response_text.startswith('```'):
                response_text = response_text[3:]
            if response_text.endswith('```'):
                response_text = response_text[:-3]
            return json.loads(response_text)
        except:
            return None
    
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

# ============ BASIC PARSING FALLBACK ============
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
    found = []
    for skill in COMMON_SKILLS:
        if skill.lower() in text_lower:
            found.append(skill)
    return found

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
    pattern = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
    emails = re.findall(pattern, text)
    return emails[0] if emails else ""

def extract_phone(text):
    pattern = r'\b\d{10}\b|\b\d{3}[-.]?\d{3}[-.]?\d{4}\b'
    phones = re.findall(pattern, text)
    return phones[0] if phones else ""

def extract_name(text):
    lines = text.strip().split('\n')
    if lines and len(lines[0]) < 50 and len(lines[0]) > 2:
        return lines[0].strip()
    return "Unknown"

def extract_work_history(text):
    lines = text.split('\n')
    experience = []
    keywords = ['experience', 'work', 'employment', 'job', 'position', 'role', 'senior']
    for line in lines[:50]:
        if any(kw in line.lower() for kw in keywords):
            clean = re.sub(r'\s+', ' ', line).strip()
            if 10 < len(clean) < 300:
                experience.append(clean)
    return ' | '.join(experience[:3]) if experience else ""

def extract_certifications(text):
    certs = ['PMP', 'CISSP', 'AWS', 'Scrum', 'ITIL', 'CPA', 'CFA', 'CCNA', 'MCSE']
    found = []
    for cert in certs:
        if cert.lower() in text.lower():
            found.append(cert)
    return ', '.join(found) if found else ""

def parse_resume_file(file_path, jd_text=None):
    if file_path.endswith('.pdf'):
        text = extract_text_from_pdf(file_path)
    else:
        text = extract_text_from_docx(file_path)
    
    if not text:
        return {'error': 'Could not extract text'}
    
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
    
    if GROQ_API_KEY:
        groq_result = parse_resume_with_groq(text)
        if groq_result:
            result['name'] = groq_result.get('name', result['name'])
            result['email'] = groq_result.get('email', result['email'])
            result['phone'] = groq_result.get('phone', result['phone'])
            result['skills'] = groq_result.get('skills', result['skills'])
            result['work_history'] = groq_result.get('work_history', result['work_history'])
            result['certifications'] = groq_result.get('certifications', result['certifications'])
            result['ai_used'] = True
    
    if jd_text and GROQ_API_KEY:
        analysis = analyze_with_groq(text, jd_text)
        if analysis:
            result['match_score'] = analysis.get('match_score', 0)
            result['relevance_feedback'] = analysis.get('relevance_feedback', '')
            result['genuineness_score'] = analysis.get('genuineness_score', 0)
            result['genuineness_feedback'] = analysis.get('genuineness_feedback', '')
            result['strengths'] = analysis.get('strengths', [])
            result['gaps'] = analysis.get('gaps', [])
            result['recommendation'] = analysis.get('recommendation', 'review')
    
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
        
        .card { background: white; border-radius: 12px; padding: 24px; margin-bottom: 20px; box-shadow: 0 2px 8px rgba(0,0,0,0.08); border-left: 4px solid #1A4D4A; }
        .card h3 { color: #1A4D4A; margin-bottom: 12px; }
        
        .btn-primary { background: #1A4D4A; color: white; border: none; padding: 12px 24px; border-radius: 8px; cursor: pointer; font-weight: 600; margin-right: 10px; margin-bottom: 10px; }
        .btn-primary:hover { background: #2A6B67; }
        .btn-secondary { background: #7F8C8D; color: white; border: none; padding: 12px 24px; border-radius: 8px; cursor: pointer; }
        
        input, textarea, select { width: 100%; padding: 12px; margin: 10px 0 15px 0; border: 1px solid #ddd; border-radius: 8px; }
        input:focus, textarea:focus, select:focus { outline: none; border-color: #1A4D4A; }
        
        .alert-success { background: #27AE60; color: white; padding: 14px; border-radius: 8px; margin: 10px 0; }
        .alert-error { background: #E74C3C; color: white; padding: 14px; border-radius: 8px; margin: 10px 0; }
        .alert-info { background: #3498DB; color: white; padding: 14px; border-radius: 8px; margin: 10px 0; }
        
        .spinner { border: 3px solid #F5F0E8; border-top: 3px solid #1A4D4A; border-radius: 50%; width: 40px; height: 40px; animation: spin 0.8s linear infinite; margin: 20px auto; }
        @keyframes spin { 0% { transform: rotate(0deg); } 100% { transform: rotate(360deg); } }
        
        .skill-tag { display: inline-block; background: #F5F0E8; padding: 4px 12px; border-radius: 20px; margin: 3px; font-size: 12px; }
        .match-high { color: #27AE60; font-weight: bold; }
        .match-medium { color: #F39C12; font-weight: bold; }
        .match-low { color: #E74C3C; font-weight: bold; }
        
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
                {% if groq_enabled %}
                <span class="badge-ai">⚡ GROQ AI ENHANCED</span>
                {% else %}
                <span class="badge-ai" style="background:#E74C3C;">⚠️ AI DISABLED</span>
                {% endif %}
            </h1>
            <p>Intelligent Recruitment Platform with Groq AI Analysis, JD Matching & Profile Authenticity Scoring</p>
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
                {% if groq_enabled %}
                <div class="alert-info" style="background:#27AE60;">⚡ Groq AI is ACTIVE - Fast & Free</div>
                {% else %}
                <div class="alert-info" style="background:#F39C12;">⚠️ Add GROQ_API_KEY to Railway</div>
                {% endif %}
                <input type="file" id="resume-file" accept=".pdf,.docx">
                <select id="upload-job-select" style="margin: 10px 0;">
                    <option value="">-- Optional: Select Job for Match Analysis --</option>
                </select>
                <button class="btn-primary" onclick="uploadResume()">🔍 Parse Resume</button>
                <div id="parse-result" class="mt-20"></div>
            </div>
        </div>
        
        <div id="create-job-tab" style="display:none;">
            <div class="card">
                <h3>➕ Create New Job Posting</h3>
                <form onsubmit="createJob(event)">
                    <input type="text" id="job-title" placeholder="Job Title *" required>
                    <input type="text" id="job-company" placeholder="Company Name">
                    <textarea id="job-desc" rows="5" placeholder="Job Description"></textarea>
                    <textarea id="job-reqs" rows="3" placeholder="Requirements"></textarea>
                    <button type="submit" class="btn-primary">Create Job</button>
                </form>
            </div>
        </div>
        
        <div id="analyze-tab" style="display:none;">
            <div class="card">
                <h3>🔍 AI-Powered Resume-JD Match Analysis</h3>
                <div class="flex">
                    <div class="flex-1">
                        <label>📋 Select Job</label>
                        <select id="analyze-job-select" class="mb-20">
                            <option value="">-- Select a Job --</option>
                        </select>
                    </div>
                    <div class="flex-1">
                        <label>👤 Select Candidate</label>
                        <select id="analyze-candidate-select" class="mb-20">
                            <option value="">-- Select a Candidate --</option>
                        </select>
                    </div>
                </div>
                <button class="btn-primary" onclick="analyzeMatch()">🤖 Run Groq AI Analysis</button>
                <div id="analyze-result" class="mt-20"></div>
            </div>
        </div>
    </div>
    
    <script>
        let jobsData = [];
        let candidatesData = [];
        
        function showTab(tabName) {
            document.querySelectorAll('[id$="-tab"]').forEach(el => el.style.display = 'none');
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
                    container.innerHTML = '<div class="card">No jobs yet. Create one.</div>';
                    return;
                }
                container.innerHTML = jobsData.map(job => `
                    <div class="card">
                        <h3>${escapeHtml(job.title)}</h3>
                        ${job.company ? `<p>🏢 ${escapeHtml(job.company)}</p>` : ''}
                        ${job.required_skills ? `<p>🔧 ${job.required_skills.split(',').map(s => `<span class="skill-tag">${escapeHtml(s.trim())}</span>`).join('')}</p>` : ''}
                        <small>📅 ${new Date(job.created_at).toLocaleDateString()}</small>
                    </div>
                `).join('');
                
                const options = '<option value="">-- Select Job --</option>' + jobsData.map(j => `<option value="${j.id}">${escapeHtml(j.title)}</option>`).join('');
                ['analyze-job-select', 'upload-job-select'].forEach(id => {
                    const el = document.getElementById(id);
                    if (el) el.innerHTML = options;
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
                    container.innerHTML = '<div class="card">No candidates yet. Upload resumes.</div>';
                    return;
                }
                container.innerHTML = candidatesData.map(c => {
                    const matchClass = c.match_score >= 70 ? 'match-high' : (c.match_score >= 40 ? 'match-medium' : 'match-low');
                    return `
                    <div class="card">
                        <h3>${escapeHtml(c.name || 'Unknown')}</h3>
                        ${c.email ? `<p>📧 ${escapeHtml(c.email)}</p>` : ''}
                        ${c.phone ? `<p>📞 ${escapeHtml(c.phone)}</p>` : ''}
                        ${c.skills ? `<p>🔧 ${c.skills.split(',').map(s => `<span class="skill-tag">${escapeHtml(s.trim())}</span>`).join('')}</p>` : ''}
                        ${c.match_score ? `<p>🎯 Match: <span class="${matchClass}">${c.match_score}%</span></p>` : ''}
                        <small>📅 ${new Date(c.created_at).toLocaleDateString()}</small>
                    </div>`;
                }).join('');
                
                const select = document.getElementById('analyze-candidate-select');
                if (select) {
                    select.innerHTML = '<option value="">-- Select Candidate --</option>' + candidatesData.map(c => `<option value="${c.id}">${escapeHtml(c.name || 'Unknown')}</option>`).join('');
                }
            } catch (error) {
                document.getElementById('candidates-list').innerHTML = '<div class="alert-error">Error loading candidates</div>';
            }
        }
        
        async function uploadResume() {
            const file = document.getElementById('resume-file').files[0];
            if (!file) { alert('Select a file'); return; }
            
            const jobSelect = document.getElementById('upload-job-select');
            const jobId = jobSelect.value;
            const job = jobsData.find(j => j.id == jobId);
            
            const formData = new FormData();
            formData.append('resume', file);
            if (job && job.description) formData.append('jd_text', job.description);
            
            const resultDiv = document.getElementById('parse-result');
            resultDiv.innerHTML = '<div class="spinner"></div><p class="text-center">Parsing with Groq AI...</p>';
            
            try {
                const response = await fetch('/api/parse-resume', { method: 'POST', body: formData });
                const result = await response.json();
                
                if (result.error) {
                    resultDiv.innerHTML = `<div class="alert-error">${result.error}</div>`;
                    return;
                }
                
                resultDiv.innerHTML = `
                    <div class="alert-success">
                        <h4>✅ Resume Parsed ${result.ai_used ? '⚡ Groq AI' : '⚙️ Basic'}</h4>
                        <p><strong>Name:</strong> ${escapeHtml(result.name)}</p>
                        <p><strong>Email:</strong> ${escapeHtml(result.email)}</p>
                        <p><strong>Phone:</strong> ${escapeHtml(result.phone)}</p>
                        <p><strong>Skills:</strong> ${result.skills ? result.skills.map(s => `<span class="skill-tag">${escapeHtml(s)}</span>`).join('') : 'None'}</p>
                        ${result.match_score ? `<p><strong>🎯 Match Score:</strong> ${result.match_score}%</p>` : ''}
                        ${result.recommendation ? `<p><strong>📌 Recommendation:</strong> ${escapeHtml(result.recommendation)}</p>` : ''}
                        <button class="btn-primary" onclick='saveCandidate(${JSON.stringify(result).replace(/'/g, "\\'")})'>💾 Save</button>
                    </div>
                `;
            } catch (error) {
                resultDiv.innerHTML = '<div class="alert-error">Error parsing resume</div>';
            }
        }
        
        async function saveCandidate(data) {
            const response = await fetch('/api/candidates', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify(data)
            });
            if (response.ok) {
                alert('Candidate saved!');
                document.getElementById('parse-result').innerHTML = '';
                document.getElementById('resume-file').value = '';
                loadCandidates();
            }
        }
        
        async function analyzeMatch() {
            const jobId = document.getElementById('analyze-job-select').value;
            const candidateId = document.getElementById('analyze-candidate-select').value;
            if (!jobId || !candidateId) { alert('Select both Job and Candidate'); return; }
            
            const job = jobsData.find(j => j.id == jobId);
            const candidate = candidatesData.find(c => c.id == candidateId);
            
            const resultDiv = document.getElementById('analyze-result');
            resultDiv.innerHTML = '<div class="spinner"></div><p>Running Groq AI analysis...</p>';
            
            try {
                const response = await fetch('/api/analyze-match', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({ jd_text: job.description || '', resume_text: candidate.resume_text || '' })
                });
                const result = await response.json();
                
                if (result.error) {
                    resultDiv.innerHTML = `<div class="alert-error">${result.error}</div>`;
                    return;
                }
                
                resultDiv.innerHTML = `
                    <div class="alert-success">
                        <h4>📊 Groq AI Analysis Complete</h4>
                        <p><strong>🎯 Match Score:</strong> <span class="${result.match_score >= 70 ? 'match-high' : (result.match_score >= 40 ? 'match-medium' : 'match-low')}">${result.match_score}%</span></p>
                        <p><strong>✅ Genuineness:</strong> ${result.genuineness_score}%</p>
                        <p><strong>📌 Recommendation:</strong> ${escapeHtml(result.recommendation)}</p>
                        <p><strong>💪 Strengths:</strong> ${result.strengths ? result.strengths.map(s => `<span class="skill-tag">${escapeHtml(s)}</span>`).join('') : 'None'}</p>
                        <p><strong>⚠️ Gaps:</strong> ${result.gaps ? result.gaps.map(g => `<span class="skill-tag">${escapeHtml(g)}</span>`).join('') : 'None'}</p>
                        <p><strong>📝 Feedback:</strong> ${escapeHtml(result.relevance_feedback)}</p>
                        <p><strong>🔍 Authenticity:</strong> ${escapeHtml(result.genuineness_feedback)}</p>
                    </div>
                `;
            } catch (error) {
                resultDiv.innerHTML = '<div class="alert-error">Analysis failed. Check API key.</div>';
            }
        }
        
        async function exportToCSV() { window.location.href = '/api/export-candidates'; }
        
        async function createJob(event) {
            event.preventDefault();
            const data = {
                title: document.getElementById('job-title').value,
                company: document.getElementById('job-company').value,
                description: document.getElementById('job-desc').value,
                requirements: document.getElementById('job-reqs').value
            };
            if (!data.title) { alert('Job title required'); return; }
            
            const response = await fetch('/api/jobs', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify(data)
            });
            if (response.ok) {
                alert('Job created!');
                document.getElementById('job-title').value = '';
                document.getElementById('job-company').value = '';
                document.getElementById('job-desc').value = '';
                document.getElementById('job-reqs').value = '';
                showTab('jobs');
                loadJobs();
            }
        }
        
        function escapeHtml(text) { if (!text) return ''; const div = document.createElement('div'); div.textContent = text; return div.innerHTML; }
        
        loadJobs();
        loadCandidates();
    </script>
</body>
</html>
'''

# ============ API ROUTES ============
@app.route('/')
def index():
    return render_template_string(HTML_TEMPLATE, groq_enabled=GROQ_ENABLED)

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
    desc = data.get('description', '')
    skills = extract_skills_from_text(desc)
    conn = sqlite3.connect('shahnai.db')
    c = conn.cursor()
    c.execute('INSERT INTO jobs (title, company, description, requirements, required_skills) VALUES (?, ?, ?, ?, ?)',
              (data.get('title'), data.get('company'), desc, data.get('requirements', ''), ', '.join(skills)))
    conn.commit()
    conn.close()
    return jsonify({'message': 'Job created'})

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
    skills = ', '.join(data.get('skills', [])) if isinstance(data.get('skills'), list) else data.get('skills', '')
    strengths = ', '.join(data.get('strengths', [])) if isinstance(data.get('strengths'), list) else data.get('strengths', '')
    gaps = ', '.join(data.get('gaps', [])) if isinstance(data.get('gaps'), list) else data.get('gaps', '')
    
    conn = sqlite3.connect('shahnai.db')
    c = conn.cursor()
    c.execute('''INSERT INTO candidates (name, email, phone, skills, work_history, certifications, 
                 resume_text, job_id, match_score, relevance_feedback, genuineness_score, 
                 genuineness_feedback, strengths, gaps, recommendation) 
                 VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)''',
              (data.get('name'), data.get('email'), data.get('phone'), skills,
               data.get('work_history'), data.get('certifications'), data.get('resume_text', ''),
               data.get('job_id'), data.get('match_score'), data.get('relevance_feedback'),
               data.get('genuineness_score'), data.get('genuineness_feedback'),
               strengths, gaps, data.get('recommendation')))
    conn.commit()
    conn.close()
    return jsonify({'message': 'Candidate saved'})

@app.route('/api/analyze-match', methods=['POST'])
def analyze_match():
    data = request.json
    resume_text = data.get('resume_text', '')
    jd_text = data.get('jd_text', '')
    
    if not resume_text or not jd_text:
        return jsonify({'error': 'Missing text'}), 400
    
    if not GROQ_API_KEY:
        return jsonify({'error': 'Groq API key missing. Add GROQ_API_KEY to Railway variables.'}), 503
    
    result = analyze_with_groq(resume_text, jd_text)
    
    if result:
        return jsonify(result)
    else:
        return jsonify({'error': 'Groq analysis failed. Check API key.'}), 500

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
    writer.writerow(['ID', 'Name', 'Email', 'Phone', 'Skills', 'Match Score', 'Recommendation', 'Created Date'])
    for c in candidates:
        writer.writerow([c.get('id'), c.get('name'), c.get('email'), c.get('phone'), c.get('skills'), c.get('match_score'), c.get('recommendation'), c.get('created_at')])
    
    output.seek(0)
    return Response(output.getvalue(), mimetype='text/csv', headers={'Content-Disposition': 'attachment; filename=candidates.csv'})

@app.route('/api/parse-resume', methods=['POST'])
def parse_resume():
    if 'resume' not in request.files:
        return jsonify({'error': 'No file'}), 400
    
    file = request.files['resume']
    if file.filename == '':
        return jsonify({'error': 'No file'}), 400
    
    if not allowed_file(file.filename):
        return jsonify({'error': 'Invalid file type'}), 400
    
    jd_text = request.form.get('jd_text', None)
    filename = secure_filename(file.filename)
    filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
    file.save(filepath)
    
    result = parse_resume_file(filepath, jd_text)
    os.remove(filepath)
    
    return jsonify(result)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
