# app.py - COMPLETE VERSION with Improved Groq Accuracy & Elegant Colors
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
        "temperature": 0.0,      # Deterministic output for consistency
        "top_p": 0.95,           # Focused sampling
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

# ============ HTML TEMPLATE with Elegant Color Scheme ============
HTML_TEMPLATE = '''
<!DOCTYPE html>
<html>
<head>
    <title>ShahnaIT Scout - Recruitment Intelligence Platform</title>
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        
        /* Elegant Color Scheme */
        :root {
            --bg-primary: #F9F6F0;      /* Warm Ivory */
            --bg-card: #FFFFFF;          /* Soft White */
            --primary-dark: #1A3A3A;     /* Deep Forest */
            --primary: #1D5E5A;          /* Deep Teal */
            --primary-light: #2A7A76;    /* Lighter Teal */
            --text-dark: #3A4A4A;        /* Soft Dark */
            --text-light: #6B7B7B;       /* Muted Gray */
            --accent-gold: #C9A96E;      /* Gold Accent */
            --success: #1B6B2E;          /* Elegant Green */
            --warning: #CC5500;           /* Warm Orange */
            --danger: #B22222;            /* Soft Red */
            --border-light: #EAE5DC;      /* Subtle Border */
        }
        
        body { 
            background-color: var(--bg-primary); 
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; 
            color: var(--text-dark); 
        }
        
        .container { 
            max-width: 1400px; 
            margin: 0 auto; 
            padding: 20px; 
        }
        
        /* Header with elegant gradient */
        .header { 
            background: linear-gradient(135deg, var(--primary-dark) 0%, var(--primary) 100%); 
            color: white; 
            padding: 35px; 
            border-radius: 20px; 
            margin-bottom: 35px;
            box-shadow: 0 10px 30px rgba(0,0,0,0.08);
            border-bottom: 3px solid var(--accent-gold);
        }
        
        .header h1 { 
            font-size: 2.2em; 
            margin-bottom: 10px; 
            font-weight: 600;
            letter-spacing: -0.5px;
        }
        
        .header p { 
            opacity: 0.85; 
            font-size: 1.05em;
        }
        
        .badge-ai { 
            display: inline-block; 
            background: linear-gradient(135deg, var(--primary-light), var(--primary));
            font-size: 12px; 
            padding: 5px 14px; 
            border-radius: 30px; 
            margin-left: 12px; 
            vertical-align: middle;
            font-weight: 500;
            letter-spacing: 0.3px;
        }
        
        /* Elegant Tabs */
        .tabs { 
            display: flex; 
            gap: 8px; 
            margin-bottom: 35px; 
            background: var(--bg-card); 
            padding: 12px 20px; 
            border-radius: 60px; 
            flex-wrap: wrap;
            box-shadow: 0 2px 10px rgba(0,0,0,0.04);
        }
        
        .tab-btn { 
            background: transparent; 
            border: none; 
            padding: 10px 28px; 
            font-size: 15px; 
            cursor: pointer; 
            color: var(--text-light); 
            border-radius: 40px; 
            transition: all 0.3s ease;
            font-weight: 500;
        }
        
        .tab-btn:hover { 
            background: var(--bg-primary); 
            color: var(--primary); 
        }
        
        .tab-btn.active { 
            background: var(--primary); 
            color: white; 
            box-shadow: 0 2px 8px rgba(29,94,90,0.3);
        }
        
        /* Sophisticated Cards */
        .card { 
            background: var(--bg-card); 
            border-radius: 20px; 
            padding: 28px; 
            margin-bottom: 24px; 
            box-shadow: 0 4px 15px rgba(0,0,0,0.05); 
            border-left: 4px solid var(--primary); 
            cursor: pointer; 
            transition: all 0.3s ease;
        }
        
        .card:hover { 
            transform: translateY(-3px); 
            box-shadow: 0 12px 25px rgba(0,0,0,0.1);
        }
        
        .card.no-click { cursor: default; }
        .card.no-click:hover { transform: none; }
        
        .card h3 { 
            color: var(--primary-dark); 
            margin-bottom: 12px; 
            font-size: 1.3em;
            font-weight: 600;
        }
        
        .card h4 { 
            color: var(--primary-dark); 
            margin: 18px 0 12px 0; 
            font-weight: 600;
        }
        
        /* Buttons */
        .btn-primary { 
            background: linear-gradient(135deg, var(--primary), var(--primary-dark));
            color: white; 
            border: none; 
            padding: 12px 28px; 
            border-radius: 40px; 
            cursor: pointer; 
            font-weight: 600; 
            margin: 10px 5px;
            transition: all 0.3s ease;
            font-size: 14px;
            letter-spacing: 0.3px;
        }
        
        .btn-primary:hover { 
            background: linear-gradient(135deg, var(--primary-light), var(--primary));
            transform: translateY(-1px);
            box-shadow: 0 4px 12px rgba(29,94,90,0.3);
        }
        
        /* Form Elements */
        input, textarea, select { 
            width: 100%; 
            padding: 14px; 
            margin: 10px 0; 
            border: 1px solid var(--border-light); 
            border-radius: 12px;
            background: var(--bg-card);
            color: var(--text-dark);
            transition: all 0.3s ease;
            font-size: 14px;
        }
        
        input:focus, textarea:focus, select:focus { 
            outline: none; 
            border-color: var(--primary); 
            box-shadow: 0 0 0 3px rgba(29,94,90,0.1);
        }
        
        /* Alert Messages */
        .alert-success { 
            background: linear-gradient(135deg, var(--success), #0E5A24);
            color: white; 
            padding: 18px; 
            border-radius: 16px; 
            margin: 15px 0; 
        }
        
        .alert-error { 
            background: linear-gradient(135deg, var(--danger), #8B1A1A);
            color: white; 
            padding: 18px; 
            border-radius: 16px; 
            margin: 15px 0; 
        }
        
        .alert-info { 
            background: linear-gradient(135deg, var(--primary), var(--primary-dark));
            color: white; 
            padding: 14px; 
            border-radius: 12px; 
            margin: 10px 0; 
        }
        
        /* Spinner */
        .spinner { 
            border: 3px solid var(--bg-primary); 
            border-top: 3px solid var(--primary); 
            border-radius: 50%; 
            width: 45px; 
            height: 45px; 
            animation: spin 0.8s linear infinite; 
            margin: 25px auto; 
        }
        
        @keyframes spin { 
            0% { transform: rotate(0deg); } 
            100% { transform: rotate(360deg); } 
        }
        
        /* Skill Tags - Elegant */
        .skill-tag { 
            display: inline-block; 
            background: var(--bg-primary); 
            padding: 5px 14px; 
            border-radius: 30px; 
            margin: 4px; 
            font-size: 12px; 
            color: var(--primary-dark); 
            font-weight: 500;
            border: 1px solid var(--border-light);
        }
        
        /* Match Score Pills */
        .match-high { 
            background: linear-gradient(135deg, var(--success), #0E5A24);
            color: white; 
            display: inline-block; 
            padding: 5px 16px; 
            border-radius: 30px; 
            font-weight: 600;
        }
        
        .match-medium { 
            background: linear-gradient(135deg, var(--warning), #A84400);
            color: white; 
            display: inline-block; 
            padding: 5px 16px; 
            border-radius: 30px; 
            font-weight: 600;
        }
        
        .match-low { 
            background: linear-gradient(135deg, var(--danger), #8B1A1A);
            color: white; 
            display: inline-block; 
            padding: 5px 16px; 
            border-radius: 30px; 
            font-weight: 600;
        }
        
        /* Recommendation Badges */
        .recommend-hire { 
            background: linear-gradient(135deg, var(--success), #0E5A24);
            color: white; 
            display: inline-block; 
            padding: 5px 16px; 
            border-radius: 30px; 
            font-weight: 600;
        }
        
        .recommend-interview { 
            background: linear-gradient(135deg, var(--warning), #A84400);
            color: white; 
            display: inline-block; 
            padding: 5px 16px; 
            border-radius: 30px; 
            font-weight: 600;
        }
        
        .recommend-reject { 
            background: linear-gradient(135deg, var(--danger), #8B1A1A);
            color: white; 
            display: inline-block; 
            padding: 5px 16px; 
            border-radius: 30px; 
            font-weight: 600;
        }
        
        /* Analysis Sections */
        .analysis-section { 
            background: var(--bg-card); 
            padding: 24px; 
            border-radius: 20px; 
            margin: 18px 0; 
            border-left: 4px solid var(--accent-gold);
            box-shadow: 0 2px 10px rgba(0,0,0,0.04);
        }
        
        .analysis-section h4 { 
            color: var(--primary-dark); 
            margin-bottom: 15px; 
            font-weight: 600;
        }
        
        .analysis-section p { 
            color: var(--text-dark); 
            margin: 10px 0; 
            line-height: 1.6; 
        }
        
        .analysis-section ul { 
            margin-left: 25px; 
            margin-top: 10px; 
        }
        
        .analysis-section li { 
            color: var(--text-dark); 
            margin: 8px 0; 
            line-height: 1.5; 
        }
        
        /* Pre-screen Questions Box */
        .pre-screen-questions { 
            background: linear-gradient(135deg, #F0F7F0, #E8F2E8);
            padding: 22px; 
            border-radius: 20px; 
            margin: 18px 0; 
            border-left: 4px solid var(--success);
        }
        
        .pre-screen-questions h4 { 
            color: var(--success); 
            margin-bottom: 12px; 
            font-weight: 600;
        }
        
        .pre-screen-questions li { 
            color: var(--text-dark); 
            margin: 8px 0; 
            margin-left: 25px; 
            line-height: 1.5; 
        }
        
        /* Modal - Elegant */
        .modal { 
            display: none; 
            position: fixed; 
            z-index: 1000; 
            left: 0; 
            top: 0; 
            width: 100%; 
            height: 100%; 
            background: rgba(0,0,0,0.5); 
            overflow-y: auto; 
        }
        
        .modal-content { 
            background: var(--bg-primary); 
            margin: 40px auto; 
            border-radius: 28px; 
            width: 90%; 
            max-width: 850px; 
            box-shadow: 0 25px 50px rgba(0,0,0,0.25);
        }
        
        .modal-header { 
            background: linear-gradient(135deg, var(--primary-dark), var(--primary));
            color: white; 
            padding: 25px 30px; 
            border-radius: 28px 28px 0 0; 
            display: flex; 
            justify-content: space-between; 
            align-items: center;
        }
        
        .modal-header h2 { 
            margin: 0; 
            font-weight: 600;
        }
        
        .modal-body { 
            padding: 30px; 
            max-height: 70vh; 
            overflow-y: auto; 
        }
        
        .close { 
            color: white; 
            font-size: 32px; 
            cursor: pointer; 
            transition: all 0.2s;
        }
        
        .close:hover { 
            color: var(--accent-gold); 
            transform: scale(1.1);
        }
        
        /* Layout Utilities */
        .flex { display: flex; gap: 24px; flex-wrap: wrap; }
        .flex-1 { flex: 1; }
        
        label { 
            color: var(--primary-dark); 
            font-weight: 600; 
            margin-bottom: 6px; 
            display: block;
            font-size: 14px;
        }
        
        hr {
            border: none;
            border-top: 1px solid var(--border-light);
            margin: 20px 0;
        }
        
        @media (max-width: 768px) { 
            .container { padding: 12px; } 
            .tab-btn { padding: 8px 18px; font-size: 13px; }
            .card { padding: 20px; }
            .modal-content { margin: 20px; width: auto; }
            .flex { flex-direction: column; gap: 15px; }
        }
        
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
                <span class="badge-ai" style="background:#B22222;">⚠️ AI DISABLED</span>
                {% endif %}
            </h1>
            <p>Intelligent Recruitment Platform with Advanced AI Analysis, JD Matching & Profile Authenticity Scoring</p>
        </div>
        
        <div class="tabs">
            <button class="tab-btn active" onclick="showTab('jobs')">📋 Jobs</button>
            <button class="tab-btn" onclick="showTab('candidates')">👥 Candidates</button>
            <button class="tab-btn" onclick="showTab('upload')">📄 Upload Resume</button>
            <button class="tab-btn" onclick="showTab('create-job')">➕ Create Job</button>
            <button class="tab-btn" onclick="showTab('analyze')">🔍 Detailed Analysis</button>
        </div>
        
        <div id="jobs-tab"><div id="jobs-list" class="mt-20"></div></div>
        
        <div id="candidates-tab" style="display:none;">
            <button class="btn-primary" onclick="exportToCSV()">📥 Export CSV</button>
            <div id="candidates-list" class="mt-20"></div>
        </div>
        
        <div id="upload-tab" style="display:none;">
            <div class="card no-click">
                <h3>📄 Upload Resume (PDF/DOCX)</h3>
                {% if groq_enabled %}
                <div class="alert-info">⚡ Groq AI is ACTIVE - Enhanced parsing enabled</div>
                {% endif %}
                <input type="file" id="resume-file" accept=".pdf,.docx">
                <button class="btn-primary" id="parseBtn">🔍 Parse Resume</button>
                <div id="parse-result" class="mt-20"></div>
            </div>
        </div>
        
        <div id="create-job-tab" style="display:none;">
            <div class="card no-click">
                <h3>➕ Create New Job</h3>
                <form id="jobForm">
                    <input type="text" id="job-title" placeholder="Job Title *" required>
                    <input type="text" id="job-company" placeholder="Company Name">
                    <textarea id="job-desc" rows="5" placeholder="Job Description (be detailed for better matching)"></textarea>
                    <button type="submit" class="btn-primary">Create Job</button>
                </form>
            </div>
        </div>
        
        <div id="analyze-tab" style="display:none;">
            <div class="card no-click">
                <h3>🔍 AI-Powered Resume-JD Match Analysis</h3>
                <p>Get comprehensive analysis including executive summary, domain assessment, genuineness scoring, and pre-screening questions.</p>
                <div class="flex">
                    <div class="flex-1">
                        <label>📋 Select Job</label>
                        <select id="analyze-job-select" class="mb-20">
                            <option value="">-- Select Job --</option>
                        </select>
                    </div>
                    <div class="flex-1">
                        <label>👤 Select Candidate</label>
                        <select id="analyze-candidate-select" class="mb-20">
                            <option value="">-- Select Candidate --</option>
                        </select>
                    </div>
                </div>
                <button class="btn-primary" id="analyzeBtn">🤖 Run AI Analysis</button>
                <div id="analyze-result" class="mt-20"></div>
            </div>
        </div>
    </div>
    
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
        }
        
        async function loadJobs() {
            try {
                const response = await fetch('/api/jobs');
                jobsData = await response.json();
                const container = document.getElementById('jobs-list');
                if (!jobsData.length) {
                    container.innerHTML = '<div class="card no-click">📋 No jobs yet. Create one using the "Create Job" tab.</div>';
                    return;
                }
                container.innerHTML = jobsData.map(job => `
                    <div class="card no-click">
                        <h3>${escapeHtml(job.title)}</h3>
                        ${job.company ? `<p>🏢 ${escapeHtml(job.company)}</p>` : ''}
                        <small>📅 Created: ${new Date(job.created_at).toLocaleDateString()}</small>
                    </div>
                `).join('');
                
                const options = '<option value="">-- Select Job --</option>' + jobsData.map(j => `<option value="${j.id}">${escapeHtml(j.title)}</option>`).join('');
                document.getElementById('analyze-job-select').innerHTML = options;
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
                    container.innerHTML = '<div class="card no-click">👥 No candidates yet. Upload resumes to add candidates.</div>';
                    return;
                }
                container.innerHTML = candidatesData.map(c => {
                    const matchClass = c.match_score >= 70 ? 'match-high' : (c.match_score >= 40 ? 'match-medium' : 'match-low');
                    const recClass = c.recommendation === 'hire' ? 'recommend-hire' : (c.recommendation === 'interview' ? 'recommend-interview' : 'recommend-reject');
                    return `
                    <div class="card" onclick="viewCandidate(${c.id})">
                        <h3>👤 ${escapeHtml(c.name || 'Unknown')}</h3>
                        ${c.email ? `<p>📧 ${escapeHtml(c.email)}</p>` : ''}
                        ${c.skills ? `<p>🔧 ${c.skills.split(',').slice(0,4).map(s => `<span class="skill-tag">${escapeHtml(s.trim())}</span>`).join('')}${c.skills.split(',').length > 4 ? '...' : ''}</p>` : ''}
                        ${c.match_score ? `<p>🎯 Score: <span class="${matchClass}">${c.match_score}%</span></p>` : ''}
                        ${c.recommendation ? `<p>📌 <span class="${recClass}">${escapeHtml(c.recommendation).toUpperCase()}</span></p>` : ''}
                        <small>📅 Added: ${new Date(c.created_at).toLocaleDateString()}</small>
                    </div>`;
                }).join('');
                
                const options = '<option value="">-- Select Candidate --</option>' + candidatesData.map(c => `<option value="${c.id}">${escapeHtml(c.name || 'Unknown')}</option>`).join('');
                document.getElementById('analyze-candidate-select').innerHTML = options;
            } catch (error) {
                document.getElementById('candidates-list').innerHTML = '<div class="alert-error">Error loading candidates</div>';
            }
        }
        
        async function viewCandidate(candidateId) {
            const candidate = candidatesData.find(c => c.id == candidateId);
            if (!candidate) return;
            
            document.getElementById('modalTitle').innerHTML = `👤 ${escapeHtml(candidate.name || 'Unknown')}`;
            
            let analysisHtml = '';
            if (candidate.detailed_analysis && candidate.detailed_analysis !== 'null') {
                try {
                    const analysis = JSON.parse(candidate.detailed_analysis);
                    if (analysis.executive_summary) {
                        analysisHtml += `<div class="analysis-section"><h4>📊 Executive Summary</h4><p>${escapeHtml(analysis.executive_summary.final_verdict || '')}</p></div>`;
                    }
                    if (analysis.domain_assessment) {
                        analysisHtml += `<div class="analysis-section"><h4>🏢 Domain Assessment</h4><p>${escapeHtml(analysis.domain_assessment.analysis || '')}</p></div>`;
                    }
                    if (analysis.genuineness_assessment) {
                        analysisHtml += `<div class="analysis-section"><h4>🔍 Genuineness Score: ${analysis.genuineness_assessment.score || 0}/10</h4>${analysis.genuineness_assessment.positives && analysis.genuineness_assessment.positives.length ? `<ul>${analysis.genuineness_assessment.positives.map(p => `<li>✅ ${escapeHtml(p)}</li>`).join('')}</ul>` : ''}</div>`;
                    }
                    if (analysis.pre_screening_questions && analysis.pre_screening_questions.length) {
                        analysisHtml += `<div class="pre-screen-questions"><h4>📝 Pre-Screening Questions</h4><ul>${analysis.pre_screening_questions.map(q => `<li>${escapeHtml(q)}</li>`).join('')}</ul></div>`;
                    }
                    if (analysis.final_verdict) {
                        analysisHtml += `<div class="analysis-section"><h4>⚖️ Final Verdict</h4><p>${escapeHtml(analysis.final_verdict.final_call || '')}</p></div>`;
                    }
                } catch(e) { analysisHtml = '<div class="alert-info">Analysis data available</div>'; }
            } else {
                analysisHtml = '<div class="alert-info">ℹ️ No detailed analysis available yet. Go to "Detailed Analysis" tab to analyze this candidate against a job.</div>';
            }
            
            document.getElementById('modalBody').innerHTML = `
                <div class="card no-click"><h3>📧 Contact Information</h3><p>📧 ${escapeHtml(candidate.email || 'Not provided')}<br>📞 ${escapeHtml(candidate.phone || 'Not provided')}</p></div>
                <div class="card no-click"><h3>🔧 Skills</h3><p>${candidate.skills ? candidate.skills.split(',').map(s => `<span class="skill-tag">${escapeHtml(s.trim())}</span>`).join('') : 'No skills listed'}</p></div>
                <div class="card no-click"><h3>💼 Work History</h3><p>${escapeHtml(candidate.work_history || 'No work history available')}</p></div>
                <div class="card no-click"><h3>📜 Certifications</h3><p>${escapeHtml(candidate.certifications || 'No certifications listed')}</p></div>
                <div class="card no-click"><h3>🎯 Match Score</h3><p><span class="${candidate.match_score >= 70 ? 'match-high' : (candidate.match_score >= 40 ? 'match-medium' : 'match-low')}">${candidate.match_score || 0}%</span></p></div>
                <div class="card no-click"><h3>📌 Recommendation</h3><p><span class="${candidate.recommendation === 'hire' ? 'recommend-hire' : (candidate.recommendation === 'interview' ? 'recommend-interview' : 'recommend-reject')}">${escapeHtml(candidate.recommendation || 'Not reviewed').toUpperCase()}</span></p></div>
                <hr>
                <h3 style="color: var(--primary-dark); margin-top: 10px;">🤖 AI Analysis Results</h3>
                ${analysisHtml}
                <button class="btn-primary" onclick="closeModal()" style="margin-top: 20px;">Close</button>
            `;
            document.getElementById('candidateModal').style.display = 'block';
        }
        
        function closeModal() {
            document.getElementById('candidateModal').style.display = 'none';
        }
        
        // Parse Resume
        document.getElementById('parseBtn').onclick = async function() {
            const file = document.getElementById('resume-file').files[0];
            if (!file) { alert('Please select a file'); return; }
            
            const formData = new FormData();
            formData.append('resume', file);
            
            const resultDiv = document.getElementById('parse-result');
            resultDiv.innerHTML = '<div class="spinner"></div><p class="text-center">Parsing resume with AI...</p>';
            
            try {
                const response = await fetch('/api/parse-resume', { method: 'POST', body: formData });
                const result = await response.json();
                
                if (result.error) {
                    resultDiv.innerHTML = `<div class="alert-error">❌ ${result.error}</div>`;
                    return;
                }
                
                window.currentCandidate = result;
                
                resultDiv.innerHTML = `
                    <div class="alert-success">
                        <h4>✅ Resume Parsed Successfully ${result.ai_used ? '⚡ with Groq AI' : ''}</h4>
                        <p><strong>Name:</strong> ${escapeHtml(result.name)}</p>
                        <p><strong>Email:</strong> ${escapeHtml(result.email)}</p>
                        <p><strong>Phone:</strong> ${escapeHtml(result.phone)}</p>
                        <p><strong>Skills:</strong> ${result.skills ? result.skills.map(s => `<span class="skill-tag">${escapeHtml(s)}</span>`).join('') : 'None'}</p>
                        <button class="btn-primary" id="saveBtn">💾 Save Candidate to Database</button>
                    </div>
                `;
                
                document.getElementById('saveBtn').onclick = async function() {
                    const saveResponse = await fetch('/api/candidates', {
                        method: 'POST',
                        headers: {'Content-Type': 'application/json'},
                        body: JSON.stringify(window.currentCandidate)
                    });
                    if (saveResponse.ok) {
                        alert('✅ Candidate saved successfully!');
                        resultDiv.innerHTML = '';
                        document.getElementById('resume-file').value = '';
                        loadCandidates();
                    } else {
                        alert('❌ Error saving candidate');
                    }
                };
            } catch (error) {
                resultDiv.innerHTML = '<div class="alert-error">❌ Error parsing resume</div>';
            }
        };
        
        // Analyze Match
        document.getElementById('analyzeBtn').onclick = async function() {
            const jobId = document.getElementById('analyze-job-select').value;
            const candidateId = document.getElementById('analyze-candidate-select').value;
            if (!jobId || !candidateId) { alert('Please select both a Job and a Candidate'); return; }
            
            const job = jobsData.find(j => j.id == jobId);
            const candidate = candidatesData.find(c => c.id == candidateId);
            
            const resultDiv = document.getElementById('analyze-result');
            resultDiv.innerHTML = '<div class="spinner"></div><p>🤖 Running detailed AI analysis with Groq...</p>';
            
            try {
                const response = await fetch('/api/analyze-match', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({ 
                        job_id: jobId, candidate_id: candidateId,
                        jd_text: job.description || '', resume_text: candidate.resume_text || ''
                    })
                });
                const result = await response.json();
                
                if (result.error) {
                    resultDiv.innerHTML = `<div class="alert-error">❌ ${result.error}</div>`;
                    return;
                }
                
                const matchClass = result.match_score >= 70 ? 'match-high' : (result.match_score >= 40 ? 'match-medium' : 'match-low');
                const recClass = result.recommendation === 'hire' ? 'recommend-hire' : (result.recommendation === 'interview' ? 'recommend-interview' : 'recommend-reject');
                
                let analysisHtml = '';
                if (result.executive_summary) {
                    analysisHtml += `<div class="analysis-section"><h4>📊 Executive Summary</h4><p>${escapeHtml(result.executive_summary.final_verdict || '')}</p></div>`;
                }
                if (result.domain_assessment) {
                    analysisHtml += `<div class="analysis-section"><h4>🏢 Domain Assessment</h4><p>${escapeHtml(result.domain_assessment.analysis || '')}</p></div>`;
                }
                if (result.genuineness_assessment) {
                    analysisHtml += `<div class="analysis-section"><h4>🔍 Genuineness Score: ${result.genuineness_assessment.score || 0}/10</h4>${result.genuineness_assessment.positives && result.genuineness_assessment.positives.length ? `<ul>${result.genuineness_assessment.positives.map(p => `<li>✅ ${escapeHtml(p)}</li>`).join('')}</ul>` : ''}</div>`;
                }
                if (result.pre_screening_questions && result.pre_screening_questions.length) {
                    analysisHtml += `<div class="pre-screen-questions"><h4>📝 Pre-Screening Questions</h4><ul>${result.pre_screening_questions.map(q => `<li>${escapeHtml(q)}</li>`).join('')}</ul></div>`;
                }
                if (result.final_verdict) {
                    analysisHtml += `<div class="analysis-section"><h4>⚖️ Final Verdict</h4><p>${escapeHtml(result.final_verdict.final_call || '')}</p></div>`;
                }
                
                resultDiv.innerHTML = `
                    <div class="alert-success">
                        <h4>📊 Groq AI Analysis Complete</h4>
                        <p><strong>🎯 Match Score:</strong> <span class="${matchClass}">${result.match_score || 0}%</span></p>
                        <p><strong>📌 Recommendation:</strong> <span class="${recClass}">${escapeHtml(result.recommendation || 'Review').toUpperCase()}</span></p>
                        ${analysisHtml}
                        <hr>
                        <p><small>✅ Analysis has been automatically saved to the candidate record. Click on the candidate name in the Candidates tab to view stored analysis anytime.</small></p>
                    </div>
                `;
                loadCandidates();
            } catch (error) {
                resultDiv.innerHTML = '<div class="alert-error">❌ Analysis failed. Please check your API key and try again.</div>';
            }
        };
        
        window.exportToCSV = function() { window.location.href = '/api/export-candidates'; };
        
        document.getElementById('jobForm').onsubmit = async function(e) {
            e.preventDefault();
            const data = {
                title: document.getElementById('job-title').value,
                company: document.getElementById('job-company').value,
                description: document.getElementById('job-desc').value
            };
            if (!data.title) { alert('Job title is required'); return; }
            
            const response = await fetch('/api/jobs', { method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify(data) });
            if (response.ok) {
                alert('✅ Job created successfully!');
                document.getElementById('job-title').value = '';
                document.getElementById('job-company').value = '';
                document.getElementById('job-desc').value = '';
                showTab('jobs');
                loadJobs();
            } else {
                alert('❌ Error creating job');
            }
        };
        
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
