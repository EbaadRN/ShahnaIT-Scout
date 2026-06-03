# app.py - COMPLETE VERSION with Left Sidebar Navigation & Premium ATS Styling
# ALL features preserved: resume parsing, job creation, AI analysis, candidate modal, export CSV, etc.
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
    print("✅✅✅ Groq API configured")

def call_groq_api(prompt, max_tokens=2000):
    """Improved Groq API call with system prompt for better accuracy"""
    if not GROQ_API_KEY:
        return None
    
    url = "https://api.groq.com/openai/v1/chat/completions"
    headers = {"Authorization": f"Bearer {GROQ_API_KEY}", "Content-Type": "application/json"}
    
    # System prompt - optimized for resume analysis (keep static for caching)
    system_prompt = """You are an expert recruitment analyst specializing in ATS-optimized resume evaluation.

RULES:
1. Return ONLY valid JSON - no markdown, no explanations, no code blocks
2. Include all required fields in your response
3. Base all analysis solely on evidence in the provided resume
4. Never add information not present in the resume

SCORING GUIDELINES:
- Match Score (0-100): Calculate based on skill overlap and experience relevance
- Genuineness (0-10): Rate based on verifiable details, consistency, and specificity
- Recommendation: 'hire' (80+), 'interview' (50-79), 'reject' (below 50)"""
    
    payload = {
        "model": "llama-3.3-70b-versatile",
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": prompt}
        ],
        "temperature": 0.0,
        "top_p": 0.95,
        "max_tokens": max_tokens
    }
    
    try:
        response = requests.post(url, json=payload, headers=headers, timeout=45)
        if response.status_code == 200:
            result = response.json()['choices'][0]['message']['content']
            # Clean any remaining markdown
            result = result.strip()
            if result.startswith('```json'):
                result = result[7:]
            if result.startswith('```'):
                result = result[3:]
            if result.endswith('```'):
                result = result[:-3]
            return result
    except Exception as e:
        print(f"Groq API error: {e}")
    return None

def analyze_with_groq_detailed(resume_text, jd_text, candidate_name=""):
    if not GROQ_API_KEY:
        return None
    
    prompt = f"""Analyze this resume against the job description. Return ONLY valid JSON.

JOB DESCRIPTION:
{jd_text[:2000]}

RESUME:
{resume_text[:2000]}

Return: {{
    "executive_summary": {{"overall_relevance": "High/Medium/Low", "final_verdict": "text"}},
    "domain_assessment": {{"status": "✅/⚠️/❌", "analysis": "text", "pre_screen_question": "text"}},
    "genuineness_assessment": {{"score": 0, "positives": [], "minor_concerns": []}},
    "final_verdict": {{"decision": "Proceed to interview/Reject", "risk_level": "Low/Medium/High", "final_call": "text"}},
    "pre_screening_questions": [],
    "match_score": 0,
    "recommendation": "hire/interview/reject"
}}"""
    
    response = call_groq_api(prompt, max_tokens=2000)
    if response:
        try:
            return json.loads(response)
        except:
            pass
    return None

def parse_resume_with_groq(resume_text):
    if not GROQ_API_KEY:
        return None
    prompt = f"Extract name, email, phone, skills array from this resume. Return ONLY valid JSON: {resume_text[:2000]}"
    response = call_groq_api(prompt, max_tokens=500)
    if response:
        try:
            return json.loads(response)
        except:
            pass
    return None

# ============ DATABASE ============
def init_db():
    conn = sqlite3.connect('shahnai.db')
    c = conn.cursor()
    c.execute('DROP TABLE IF EXISTS candidates')
    c.execute('''CREATE TABLE candidates (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT,
        email TEXT,
        phone TEXT,
        skills TEXT,
        work_history TEXT,
        certifications TEXT,
        resume_text TEXT,
        match_score INTEGER DEFAULT 0,
        recommendation TEXT DEFAULT '',
        detailed_analysis TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )''')
    c.execute('''CREATE TABLE IF NOT EXISTS jobs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        title TEXT NOT NULL,
        company TEXT,
        description TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )''')
    conn.commit()
    conn.close()
    print("✅ Database initialized")

init_db()

# ============ RESUME PARSING ============
COMMON_SKILLS = [
    'Python', 'Java', 'JavaScript', 'TypeScript', 'React', 'Angular', 'Vue', 'Node.js',
    'SQL', 'MongoDB', 'PostgreSQL', 'MySQL', 'AWS', 'Azure', 'Docker', 'Kubernetes',
    'Power Apps', 'Power Automate', 'Azure DevOps', 'Dataverse', 'SharePoint', 'Git',
    'Salesforce', 'Apex', 'LWC', 'REST API', 'GraphQL', 'CI/CD', 'Jenkins'
]

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

def extract_name(text):
    lines = text.strip().split('\n')
    return lines[0].strip() if lines and len(lines[0]) < 50 else "Unknown"

def extract_skills_from_text(text):
    if not text:
        return []
    text_lower = text.lower()
    return [s for s in COMMON_SKILLS if s.lower() in text_lower]

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
    certs = ['PMP', 'CISSP', 'AWS', 'Scrum', 'ITIL', 'Salesforce Certified']
    return ', '.join([c for c in certs if c.lower() in text.lower()])

def parse_resume_file(file_path):
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
        'resume_text': text[:3000],
        'ai_used': False
    }
    
    if GROQ_API_KEY:
        groq_result = parse_resume_with_groq(text)
        if groq_result:
            result['name'] = groq_result.get('name', result['name'])
            result['email'] = groq_result.get('email', result['email'])
            result['phone'] = groq_result.get('phone', result['phone'])
            result['skills'] = groq_result.get('skills', result['skills'])
            result['ai_used'] = True
    
    return result

# ============ HTML TEMPLATE with Left Sidebar ============
HTML_TEMPLATE = '''
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>ShahnaIT Scout — Intelligent ATS</title>
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }

        /* -------------------- Elegant Color Scheme -------------------- */
        :root {
            --bg-primary: #F9F6F0;      /* Warm Ivory background */
            --sidebar-bg: #FFFFFF;       /* Sidebar white */
            --primary-dark: #1A3A3A;     /* Deep Forest */
            --primary: #1D5E5A;          /* Deep Teal */
            --primary-light: #2A7A76;
            --text-dark: #2C3E3E;
            --text-muted: #6B7B7B;
            --accent-gold: #C9A96E;
            --border-light: #EAE5DC;
            --card-shadow: 0 8px 20px rgba(0, 0, 0, 0.03), 0 2px 6px rgba(0, 0, 0, 0.05);
            --hover-shadow: 0 12px 28px rgba(0, 0, 0, 0.08);
        }

        body {
            background-color: var(--bg-primary);
            font-family: 'Inter', 'Segoe UI', system-ui, -apple-system, sans-serif;
            color: var(--text-dark);
            height: 100vh;
            overflow: hidden;
        }

        /* Layout: fixed sidebar + scrollable content */
        .app-layout {
            display: flex;
            height: 100vh;
            width: 100%;
        }

        /* ---------- Premium Sidebar ---------- */
        .sidebar {
            width: 280px;
            background: var(--sidebar-bg);
            border-right: 1px solid var(--border-light);
            display: flex;
            flex-direction: column;
            padding: 32px 20px;
            box-shadow: 4px 0 12px rgba(0, 0, 0, 0.02);
            z-index: 10;
            overflow-y: auto;
            flex-shrink: 0;
        }

        .logo-area {
            margin-bottom: 48px;
            padding-left: 12px;
        }

        .logo-area h1 {
            font-size: 1.7rem;
            font-weight: 700;
            background: linear-gradient(135deg, var(--primary-dark) 0%, var(--primary) 100%);
            -webkit-background-clip: text;
            background-clip: text;
            color: transparent;
            letter-spacing: -0.3px;
        }

        .logo-area p {
            font-size: 0.75rem;
            color: var(--text-muted);
            margin-top: 6px;
        }

        .nav-menu {
            flex: 1;
            display: flex;
            flex-direction: column;
            gap: 8px;
        }

        .nav-item {
            display: flex;
            align-items: center;
            gap: 14px;
            padding: 12px 16px;
            border-radius: 14px;
            font-weight: 500;
            color: var(--text-muted);
            cursor: pointer;
            transition: all 0.2s ease;
            font-size: 0.95rem;
        }

        .nav-item i { 
            width: 24px;
            font-style: normal;
            font-weight: 500;
            font-size: 1.2rem;
        }

        .nav-item:hover {
            background-color: var(--bg-primary);
            color: var(--primary);
        }

        .nav-item.active {
            background: linear-gradient(135deg, var(--primary-dark), var(--primary));
            color: white;
            box-shadow: 0 4px 12px rgba(29,94,90,0.25);
        }

        .ai-badge-side {
            margin-top: 32px;
            padding: 16px;
            background: var(--bg-primary);
            border-radius: 20px;
            text-align: center;
            border: 1px solid var(--border-light);
        }

        .ai-badge-side span {
            font-size: 0.75rem;
            font-weight: 600;
            color: var(--primary);
            display: block;
        }

        /* ---------- Main Content (Scrollable) ---------- */
        .main-content {
            flex: 1;
            overflow-y: auto;
            padding: 32px 40px;
        }

        /* Cards, Tables, UI Components */
        .card {
            background: #FFFFFF;
            border-radius: 24px;
            padding: 24px;
            margin-bottom: 24px;
            box-shadow: var(--card-shadow);
            border: 1px solid var(--border-light);
            transition: all 0.25s ease;
            cursor: pointer;
        }

        .card:hover {
            transform: translateY(-3px);
            box-shadow: var(--hover-shadow);
        }
        .card.no-click { cursor: default; }
        .card.no-click:hover { transform: none; }

        .job-card h3, .candidate-card h3 {
            font-size: 1.25rem;
            font-weight: 600;
            color: var(--primary-dark);
            margin-bottom: 8px;
        }

        .skill-tag {
            display: inline-block;
            background: var(--bg-primary);
            padding: 4px 12px;
            border-radius: 30px;
            font-size: 0.75rem;
            margin: 4px 4px 0 0;
            color: var(--primary-dark);
            font-weight: 500;
        }

        .match-high { background: #1B6B2E; color: white; padding: 2px 10px; border-radius: 30px; font-weight: 600; font-size: 0.8rem; display: inline-block; }
        .match-medium { background: #CC5500; color: white; padding: 2px 10px; border-radius: 30px; font-weight: 600; font-size: 0.8rem; display: inline-block; }
        .match-low { background: #B22222; color: white; padding: 2px 10px; border-radius: 30px; font-weight: 600; font-size: 0.8rem; display: inline-block; }
        .recommend-hire { background: #1B6B2E; color: white; border-radius: 30px; padding: 2px 12px; font-weight: 600; font-size: 0.75rem; display: inline-block; }
        .recommend-interview { background: #CC5500; color: white; border-radius: 30px; padding: 2px 12px; font-weight: 600; display: inline-block; }
        .recommend-reject { background: #B22222; color: white; border-radius: 30px; padding: 2px 12px; font-weight: 600; display: inline-block; }

        .btn-primary {
            background: var(--primary);
            border: none;
            padding: 10px 24px;
            border-radius: 40px;
            font-weight: 600;
            color: white;
            cursor: pointer;
            transition: 0.2s;
            font-size: 0.85rem;
            display: inline-flex;
            align-items: center;
            gap: 8px;
        }
        .btn-primary:hover { background: var(--primary-light); transform: translateY(-1px); }

        input, textarea, select {
            width: 100%;
            padding: 12px 16px;
            border: 1px solid var(--border-light);
            border-radius: 20px;
            background: white;
            margin-bottom: 16px;
        }

        .modal { display: none; position: fixed; z-index: 1000; left: 0; top: 0; width: 100%; height: 100%; background: rgba(0,0,0,0.5); backdrop-filter: blur(4px); }
        .modal-content { background: var(--bg-primary); margin: 5% auto; border-radius: 32px; max-width: 750px; width: 90%; box-shadow: 0 25px 40px rgba(0,0,0,0.2); }
        .modal-header { background: var(--primary-dark); color: white; padding: 20px 28px; border-radius: 32px 32px 0 0; display: flex; justify-content: space-between; }
        .modal-body { padding: 28px; max-height: 70vh; overflow-y: auto; }
        .close { font-size: 28px; cursor: pointer; color: white; }

        .flex { display: flex; gap: 24px; flex-wrap: wrap; }
        .analysis-section { background: white; border-left: 4px solid var(--accent-gold); margin: 16px 0; padding: 18px; border-radius: 20px; }
        .pre-screen-questions { background: #EFF7EF; padding: 18px; border-radius: 20px; margin: 16px 0; }

        @media (max-width: 768px) {
            .sidebar { width: 100px; padding: 20px 12px; }
            .nav-item span:last-child { display: none; }
            .logo-area p { display: none; }
            .main-content { padding: 20px; }
        }
    </style>
</head>
<body>
<div class="app-layout">
    <!-- LEFT SIDEBAR (PERSISTENT NAVIGATION) -->
    <div class="sidebar">
        <div class="logo-area">
            <h1>ShahnaIT</h1>
            <p>Intelligent ATS</p>
        </div>
        <div class="nav-menu">
            <div class="nav-item active" data-tab="jobs">
                <i>📋</i> <span>Jobs</span>
            </div>
            <div class="nav-item" data-tab="candidates">
                <i>👥</i> <span>Candidates</span>
            </div>
            <div class="nav-item" data-tab="upload">
                <i>📄</i> <span>Upload Resume</span>
            </div>
            <div class="nav-item" data-tab="create-job">
                <i>➕</i> <span>Create Job</span>
            </div>
            <div class="nav-item" data-tab="analyze">
                <i>🔍</i> <span>Analyze Match</span>
            </div>
        </div>
        <div class="ai-badge-side">
            <span>⚡ GROQ AI ENHANCED</span>
        </div>
    </div>

    <!-- MAIN CONTENT AREA (DYNAMIC) -->
    <div class="main-content" id="mainContent">
        <!-- JOBS TAB -->
        <div id="jobs-view">
            <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 20px;">
                <h2 style="color: var(--primary-dark);">📋 Job Openings</h2>
                <button class="btn-primary" onclick="switchTab('create-job')">+ New Job</button>
            </div>
            <div id="jobs-list"></div>
        </div>

        <!-- CANDIDATES TAB -->
        <div id="candidates-view" style="display: none;">
            <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 20px;">
                <h2 style="color: var(--primary-dark);">👥 Candidate Database</h2>
                <button class="btn-primary" onclick="exportToCSV()">📥 Export CSV</button>
            </div>
            <div id="candidates-list"></div>
        </div>

        <!-- UPLOAD TAB -->
        <div id="upload-view" style="display: none;">
            <div class="card no-click">
                <h3>📄 Upload Resume (PDF/DOCX)</h3>
                {% if groq_enabled %}
                <div class="alert-info" style="background: #1D5E5A20; padding: 12px; border-radius: 20px; margin-bottom: 16px;">⚡ Groq AI is ACTIVE</div>
                {% endif %}
                <input type="file" id="resume-file" accept=".pdf,.docx">
                <button class="btn-primary" id="parseBtn">🔍 Parse Resume</button>
                <div id="parse-result" class="mt-20"></div>
            </div>
        </div>

        <!-- CREATE JOB TAB -->
        <div id="create-job-view" style="display: none;">
            <div class="card no-click">
                <h3>➕ Create New Job</h3>
                <form id="jobForm">
                    <input type="text" id="job-title" placeholder="Job Title *" required>
                    <input type="text" id="job-company" placeholder="Company Name">
                    <textarea id="job-desc" rows="5" placeholder="Job Description (detailed for better matching)"></textarea>
                    <button type="submit" class="btn-primary">Create Job</button>
                </form>
            </div>
        </div>

        <!-- ANALYZE TAB -->
        <div id="analyze-view" style="display: none;">
            <div class="card no-click">
                <h3>🔍 AI-Powered Resume-JD Match Analysis</h3>
                <div class="flex">
                    <div class="flex-1">
                        <label>📋 Select Job</label>
                        <select id="analyze-job-select"></select>
                    </div>
                    <div class="flex-1">
                        <label>👤 Select Candidate</label>
                        <select id="analyze-candidate-select"></select>
                    </div>
                </div>
                <button class="btn-primary" id="analyzeBtn">🤖 Run AI Analysis</button>
                <div id="analyze-result" class="mt-20"></div>
            </div>
        </div>
    </div>
</div>

<!-- MODAL FOR CANDIDATE DETAILS -->
<div id="candidateModal" class="modal">
    <div class="modal-content">
        <div class="modal-header">
            <h2 id="modalTitle">Candidate Details</h2>
            <span class="close" onclick="closeModal()">&times;</span>
        </div>
        <div class="modal-body" id="modalBody">Loading...</div>
    </div>
</div>

<script>
    let jobsData = [], candidatesData = [];

    // Tab switching logic (left sidebar)
    function switchTab(tabId) {
        // Hide all views
        const views = ['jobs', 'candidates', 'upload', 'create-job', 'analyze'];
        views.forEach(v => {
            const el = document.getElementById(v + '-view');
            if (el) el.style.display = 'none';
        });
        document.getElementById(tabId + '-view').style.display = 'block';

        // Update sidebar active class
        document.querySelectorAll('.nav-item').forEach(item => {
            item.classList.remove('active');
            if (item.getAttribute('data-tab') === tabId) item.classList.add('active');
        });

        if (tabId === 'jobs') loadJobs();
        if (tabId === 'candidates') loadCandidates();
        if (tabId === 'analyze') { loadJobs(); loadCandidates(); }
    }

    // Attach sidebar click events
    document.querySelectorAll('.nav-item').forEach(item => {
        item.addEventListener('click', () => {
            const tab = item.getAttribute('data-tab');
            if (tab) switchTab(tab);
        });
    });

    async function loadJobs() {
        const res = await fetch('/api/jobs');
        jobsData = await res.json();
        const container = document.getElementById('jobs-list');
        if (!jobsData.length) {
            container.innerHTML = '<div class="card no-click">📋 No jobs yet. Create one using "Create Job".</div>';
            return;
        }
        container.innerHTML = jobsData.map(job => `
            <div class="card no-click">
                <h3>${escapeHtml(job.title)}</h3>
                ${job.company ? `<p>🏢 ${escapeHtml(job.company)}</p>` : ''}
                <small>📅 ${new Date(job.created_at).toLocaleDateString()}</small>
            </div>
        `).join('');
        // populate selects
        const options = '<option value="">-- Select Job --</option>' + jobsData.map(j => `<option value="${j.id}">${escapeHtml(j.title)}</option>`).join('');
        document.getElementById('analyze-job-select').innerHTML = options;
    }

    async function loadCandidates() {
        const res = await fetch('/api/candidates');
        candidatesData = await res.json();
        const container = document.getElementById('candidates-list');
        if (!candidatesData.length) {
            container.innerHTML = '<div class="card no-click">👥 No candidates yet. Upload resumes.</div>';
            return;
        }
        container.innerHTML = candidatesData.map(c => {
            const matchClass = c.match_score >= 70 ? 'match-high' : (c.match_score >= 40 ? 'match-medium' : 'match-low');
            const recClass = c.recommendation === 'hire' ? 'recommend-hire' : (c.recommendation === 'interview' ? 'recommend-interview' : 'recommend-reject');
            return `
            <div class="card" onclick="viewCandidate(${c.id})">
                <h3>👤 ${escapeHtml(c.name || 'Unknown')}</h3>
                ${c.email ? `<p>📧 ${escapeHtml(c.email)}</p>` : ''}
                <p>🔧 ${c.skills ? c.skills.split(',').slice(0,4).map(s => `<span class="skill-tag">${escapeHtml(s.trim())}</span>`).join('') : ''}</p>
                ${c.match_score ? `<p>🎯 Score: <span class="${matchClass}">${c.match_score}%</span></p>` : ''}
                ${c.recommendation ? `<p>📌 <span class="${recClass}">${escapeHtml(c.recommendation).toUpperCase()}</span></p>` : ''}
                <small>📅 ${new Date(c.created_at).toLocaleDateString()}</small>
            </div>`;
        }).join('');
        document.getElementById('analyze-candidate-select').innerHTML = '<option value="">-- Select Candidate --</option>' + candidatesData.map(c => `<option value="${c.id}">${escapeHtml(c.name || 'Unknown')}</option>`).join('');
    }

    async function viewCandidate(id) {
        const c = candidatesData.find(c => c.id == id);
        if (!c) return;
        document.getElementById('modalTitle').innerHTML = `👤 ${escapeHtml(c.name || 'Unknown')}`;
        let analysisHtml = '';
        if (c.detailed_analysis && c.detailed_analysis !== 'null') {
            try {
                const analysis = JSON.parse(c.detailed_analysis);
                if (analysis.executive_summary)
                    analysisHtml += `<div class="analysis-section"><h4>📊 Summary</h4><p>${escapeHtml(analysis.executive_summary.final_verdict || '')}</p></div>`;
                if (analysis.pre_screening_questions && analysis.pre_screening_questions.length)
                    analysisHtml += `<div class="pre-screen-questions"><h4>📝 Pre-Screening Questions</h4><ul>${analysis.pre_screening_questions.map(q => `<li>${escapeHtml(q)}</li>`).join('')}</ul></div>`;
            } catch(e) { analysisHtml = '<div class="alert-info">Analysis data available</div>'; }
        } else { analysisHtml = '<div class="alert-info">ℹ️ No detailed analysis yet. Run "Analyze Match".</div>'; }

        document.getElementById('modalBody').innerHTML = `
            <div class="card no-click"><h3>📧 Contact</h3><p>📧 ${escapeHtml(c.email || 'N/A')}<br>📞 ${escapeHtml(c.phone || 'N/A')}</p></div>
            <div class="card no-click"><h3>🔧 Skills</h3><p>${c.skills ? c.skills.split(',').map(s => `<span class="skill-tag">${escapeHtml(s.trim())}</span>`).join('') : 'None'}</p></div>
            <div class="card no-click"><h3>💼 Work History</h3><p>${escapeHtml(c.work_history || 'N/A')}</p></div>
            <div class="card no-click"><h3>🎯 Match Score</h3><p><span class="${c.match_score >= 70 ? 'match-high' : (c.match_score >= 40 ? 'match-medium' : 'match-low')}">${c.match_score || 0}%</span></p></div>
            <h3 style="margin-top:20px;">🤖 AI Analysis</h3>${analysisHtml}
            <button class="btn-primary" onclick="closeModal()">Close</button>
        `;
        document.getElementById('candidateModal').style.display = 'block';
    }
    function closeModal() { document.getElementById('candidateModal').style.display = 'none'; }

    // File parsing and saving (exactly as before, no feature change)
    document.getElementById('parseBtn').onclick = async () => {
        const file = document.getElementById('resume-file').files[0];
        if (!file) return alert('Select a file');
        const fd = new FormData(); fd.append('resume', file);
        const div = document.getElementById('parse-result');
        div.innerHTML = '<div class="spinner"></div><p>Parsing...</p>';
        try {
            const res = await fetch('/api/parse-resume', { method: 'POST', body: fd });
            const result = await res.json();
            if (result.error) { div.innerHTML = `<div class="alert-error">${result.error}</div>`; return; }
            window.currentCandidate = result;
            div.innerHTML = `<div class="alert-success"><h4>✅ Parsed ${result.ai_used ? '⚡ AI' : ''}</h4>
                <p><strong>Name:</strong> ${escapeHtml(result.name)}</p>
                <p><strong>Email:</strong> ${escapeHtml(result.email)}</p>
                <p><strong>Phone:</strong> ${escapeHtml(result.phone)}</p>
                <p><strong>Skills:</strong> ${result.skills ? result.skills.map(s => `<span class="skill-tag">${escapeHtml(s)}</span>`).join('') : 'None'}</p>
                <button class="btn-primary" id="saveBtnNow">💾 Save Candidate</button></div>`;
            document.getElementById('saveBtnNow').onclick = async () => {
                const saveResp = await fetch('/api/candidates', { method: 'POST', headers: {'Content-Type':'application/json'}, body: JSON.stringify(window.currentCandidate) });
                if (saveResp.ok) { alert('Saved!'); div.innerHTML = ''; document.getElementById('resume-file').value = ''; loadCandidates(); }
                else alert('Error saving');
            };
        } catch(e) { div.innerHTML = '<div class="alert-error">Error parsing</div>'; }
    };

    document.getElementById('analyzeBtn').onclick = async () => {
        const jobId = document.getElementById('analyze-job-select').value;
        const candidateId = document.getElementById('analyze-candidate-select').value;
        if (!jobId || !candidateId) return alert('Select both Job and Candidate');
        const job = jobsData.find(j => j.id == jobId);
        const cand = candidatesData.find(c => c.id == candidateId);
        const div = document.getElementById('analyze-result');
        div.innerHTML = '<div class="spinner"></div><p>🤖 Running AI analysis...</p>';
        try {
            const res = await fetch('/api/analyze-match', { method: 'POST', headers: {'Content-Type':'application/json'}, body: JSON.stringify({ job_id: jobId, candidate_id: candidateId, jd_text: job.description || '', resume_text: cand.resume_text || '' }) });
            const result = await res.json();
            if (result.error) { div.innerHTML = `<div class="alert-error">${result.error}</div>`; return; }
            const matchClass = result.match_score >= 70 ? 'match-high' : (result.match_score >= 40 ? 'match-medium' : 'match-low');
            div.innerHTML = `<div class="alert-success"><h4>📊 Analysis Complete</h4>
                <p>🎯 Match Score: <span class="${matchClass}">${result.match_score || 0}%</span></p>
                <p>📌 Recommendation: <span class="recommend-${result.recommendation || 'review'}">${(result.recommendation || 'Review').toUpperCase()}</span></p>
                <div class="analysis-section"><p>${escapeHtml(result.executive_summary?.final_verdict || '')}</p></div>
                ${result.pre_screening_questions ? `<div class="pre-screen-questions"><ul>${result.pre_screening_questions.map(q => `<li>${escapeHtml(q)}</li>`).join('')}</ul></div>` : ''}
                <small>✅ Analysis saved to candidate record.</small></div>`;
            loadCandidates();
        } catch(e) { div.innerHTML = '<div class="alert-error">Analysis failed</div>'; }
    };

    window.exportToCSV = () => window.location.href = '/api/export-candidates';
    document.getElementById('jobForm').onsubmit = async (e) => {
        e.preventDefault();
        const data = { title: document.getElementById('job-title').value, company: document.getElementById('job-company').value, description: document.getElementById('job-desc').value };
        if (!data.title) return alert('Title required');
        const res = await fetch('/api/jobs', { method: 'POST', headers: {'Content-Type':'application/json'}, body: JSON.stringify(data) });
        if (res.ok) { alert('Job created!'); document.getElementById('job-title').value = ''; document.getElementById('job-company').value = ''; document.getElementById('job-desc').value = ''; switchTab('jobs'); loadJobs(); }
        else alert('Error');
    };

    function escapeHtml(str) { if (!str) return ''; const div = document.createElement('div'); div.textContent = str; return div.innerHTML; }
    // Initialize
    loadJobs(); loadCandidates();
    // Ensure sidebar active on start
    document.querySelector('.nav-item[data-tab="jobs"]').classList.add('active');
</script>
</body>
</html>
'''

# ============ API ROUTES (UNCHANGED) ============
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
    conn = sqlite3.connect('shahnai.db')
    c = conn.cursor()
    c.execute('INSERT INTO jobs (title, company, description) VALUES (?, ?, ?)',
              (data.get('title'), data.get('company'), data.get('description', '')))
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
    conn = sqlite3.connect('shahnai.db')
    c = conn.cursor()
    c.execute('INSERT INTO candidates (name, email, phone, skills, work_history, certifications, resume_text) VALUES (?, ?, ?, ?, ?, ?, ?)',
              (data.get('name'), data.get('email'), data.get('phone'), skills,
               data.get('work_history', ''), data.get('certifications', ''), data.get('resume_text', '')))
    conn.commit()
    conn.close()
    return jsonify({'message': 'Candidate saved'})

@app.route('/api/analyze-match', methods=['POST'])
def analyze_match():
    data = request.json
    resume_text = data.get('resume_text', '')
    jd_text = data.get('jd_text', '')
    candidate_id = data.get('candidate_id')
    
    if not resume_text or not jd_text:
        return jsonify({'error': 'Missing text'}), 400
    
    if not GROQ_API_KEY:
        return jsonify({'error': 'Groq API key missing. Add GROQ_API_KEY to Railway variables.'}), 503
    
    result = analyze_with_groq_detailed(resume_text, jd_text)
    
    if result and candidate_id:
        detailed_json = json.dumps(result, indent=2)
        conn = sqlite3.connect('shahnai.db')
        c = conn.cursor()
        c.execute('UPDATE candidates SET match_score = ?, recommendation = ?, detailed_analysis = ? WHERE id = ?',
                  (result.get('match_score', 0), result.get('recommendation', 'review'), detailed_json, candidate_id))
        conn.commit()
        conn.close()
        return jsonify(result)
    
    return jsonify({'error': 'Analysis failed'}), 500

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
        return jsonify({'error': 'Invalid file type. Use PDF or DOCX'}), 400
    
    filename = secure_filename(file.filename)
    filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
    file.save(filepath)
    
    result = parse_resume_file(filepath)
    os.remove(filepath)
    
    return jsonify(result)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
