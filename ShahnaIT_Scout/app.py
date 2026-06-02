# app.py - COMPLETE VERSION with Clickable Candidate Profiles & Stored Analysis
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

def call_groq_api(prompt, max_tokens=2500):
    """Call Groq API for AI analysis"""
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
        print(f"Calling Groq API...")
        response = requests.post(url, json=payload, headers=headers, timeout=45)
        if response.status_code == 200:
            data = response.json()
            result_text = data['choices'][0]['message']['content']
            print(f"✅ Groq API call successful")
            return result_text
        else:
            print(f"Groq API error: {response.status_code}")
            return None
    except Exception as e:
        print(f"Groq API error: {e}")
        return None

def analyze_with_groq_detailed(resume_text, jd_text, candidate_name=""):
    """Comprehensive JD vs Resume analysis with detailed format"""
    if not GROQ_API_KEY:
        return None
    
    resume_text = resume_text[:3000]
    jd_text = jd_text[:2500]
    
    name_instruction = f"Analyzing resume for: {candidate_name}" if candidate_name else ""
    
    prompt = f"""You are an expert recruitment analyst. {name_instruction} Analyze this resume against the job description in EXTREME DETAIL.

JOB DESCRIPTION:
{jd_text}

RESUME:
{resume_text}

Return ONLY valid JSON with these exact fields:

{{
    "executive_summary": {{
        "overall_relevance": "Very High/High/Medium/Low",
        "final_verdict": "text"
    }},
    "relevance_analysis": {{
        "mandatory_experience": [
            {{"requirement": "text", "match": "✅/⚠️/❌", "confidence": "High/Medium/Low"}}
        ],
        "technical_skills": [
            {{"requirement": "text", "match": "✅/⚠️/❌"}}
        ]
    }},
    "domain_assessment": {{
        "status": "✅ Met / ⚠️ Needs confirmation / ❌ Not met",
        "analysis": "text",
        "pre_screen_question": "text"
    }},
    "genuineness_assessment": {{
        "score": 0,
        "positives": ["positive1", "positive2"],
        "minor_concerns": [{{"concern": "text", "severity": "Low/Medium"}}]
    }},
    "final_verdict": {{
        "decision": "Proceed to interview / Reject / Need more info",
        "risk_level": "Low/Medium/High",
        "final_call": "text"
    }},
    "pre_screening_questions": ["question1", "question2", "question3", "question4", "question5"],
    "match_score": 0,
    "recommendation": "hire/interview/reject"
}}"""
    
    response_text = call_groq_api(prompt, max_tokens=2500)
    
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
            print(f"✅ Detailed Groq analysis successful")
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

# ============ DATABASE SETUP WITH AUTO-FIX ============
def init_db():
    conn = sqlite3.connect('shahnai.db')
    c = conn.cursor()
    
    # Drop and recreate candidates table with correct schema
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
        match_score INTEGER,
        recommendation TEXT,
        detailed_analysis TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )''')
    
    c.execute('''CREATE TABLE IF NOT EXISTS jobs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        title TEXT NOT NULL,
        company TEXT,
        description TEXT,
        requirements TEXT,
        required_skills TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )''')
    
    conn.commit()
    conn.close()
    print("✅ Database initialized with correct schema")

init_db()

# ============ BASIC PARSING FALLBACK ============
COMMON_SKILLS = [
    'Python', 'Java', 'JavaScript', 'TypeScript', 'React', 'Angular', 'Vue', 'Node.js',
    'SQL', 'MongoDB', 'PostgreSQL', 'MySQL', 'AWS', 'Azure', 'GCP', 'Docker', 'Kubernetes',
    'Machine Learning', 'AI', 'Data Science', 'Excel', 'Tableau', 'Power BI',
    'HTML', 'CSS', 'Git', 'REST API', 'GraphQL', 'Power Apps', 'Power Automate', 'Azure DevOps',
    'Salesforce', 'Apex', 'LWC', 'Sales Cloud', 'Service Cloud'
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
    pattern = r'\b\d{10}\b|\b\d{3}[-.]?\d{3}[-.]?\d{4}\b|\+\d{2}\s?\d{10}\b'
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
            result['work_history'] = groq_result.get('work_history', result['work_history'])
            result['certifications'] = groq_result.get('certifications', result['certifications'])
            result['ai_used'] = True
    
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
        .container { max-width: 1600px; margin: 0 auto; padding: 20px; }
        
        .header { background: linear-gradient(135deg, #1A4D4A 0%, #0F3533 100%); color: white; padding: 30px; border-radius: 16px; margin-bottom: 30px; }
        .header h1 { font-size: 2em; margin-bottom: 10px; }
        
        .badge-ai { display: inline-block; background: #27AE60; font-size: 12px; padding: 4px 12px; border-radius: 20px; margin-left: 10px; vertical-align: middle; }
        
        .tabs { display: flex; gap: 5px; margin-bottom: 30px; background: white; padding: 10px; border-radius: 12px; flex-wrap: wrap; }
        .tab-btn { background: transparent; border: none; padding: 12px 24px; font-size: 15px; cursor: pointer; color: #555; border-radius: 8px; transition: all 0.3s; }
        .tab-btn:hover { background: #E8E0D0; color: #1A4D4A; }
        .tab-btn.active { background: #1A4D4A; color: white; }
        
        .card { background: white; border-radius: 12px; padding: 24px; margin-bottom: 20px; box-shadow: 0 2px 8px rgba(0,0,0,0.08); border-left: 4px solid #1A4D4A; cursor: pointer; transition: transform 0.2s, box-shadow 0.2s; }
        .card:hover { transform: translateY(-2px); box-shadow: 0 4px 12px rgba(0,0,0,0.15); }
        .card h3 { color: #1A4D4A; margin-bottom: 12px; }
        .card h4 { color: #1A4D4A; margin: 15px 0 10px 0; }
        .card p { color: #2C3E50; line-height: 1.5; }
        
        .btn-primary { background: #1A4D4A; color: white; border: none; padding: 12px 24px; border-radius: 8px; cursor: pointer; font-weight: 600; margin-right: 10px; margin-bottom: 10px; }
        .btn-primary:hover { background: #2A6B67; }
        .btn-close { background: #7F8C8D; color: white; border: none; padding: 8px 16px; border-radius: 8px; cursor: pointer; margin-top: 15px; }
        .btn-close:hover { background: #95A5A6; }
        
        input, textarea, select { width: 100%; padding: 12px; margin: 10px 0 15px 0; border: 1px solid #ddd; border-radius: 8px; background: white; color: #2C3E50; }
        input:focus, textarea:focus, select:focus { outline: none; border-color: #1A4D4A; }
        
        .alert-success { background: #27AE60; color: white; padding: 14px; border-radius: 8px; margin: 10px 0; }
        .alert-error { background: #E74C3C; color: white; padding: 14px; border-radius: 8px; margin: 10px 0; }
        .alert-info { background: #3498DB; color: white; padding: 14px; border-radius: 8px; margin: 10px 0; }
        
        .spinner { border: 3px solid #F5F0E8; border-top: 3px solid #1A4D4A; border-radius: 50%; width: 40px; height: 40px; animation: spin 0.8s linear infinite; margin: 20px auto; }
        @keyframes spin { 0% { transform: rotate(0deg); } 100% { transform: rotate(360deg); } }
        
        .skill-tag { display: inline-block; background: #E8E0D0; padding: 4px 12px; border-radius: 20px; margin: 3px; font-size: 12px; color: #1A4D4A; font-weight: 500; }
        
        .match-high { background: #2E7D32; color: white; display: inline-block; padding: 4px 12px; border-radius: 20px; font-weight: bold; }
        .match-medium { background: #E65100; color: white; display: inline-block; padding: 4px 12px; border-radius: 20px; font-weight: bold; }
        .match-low { background: #C62828; color: white; display: inline-block; padding: 4px 12px; border-radius: 20px; font-weight: bold; }
        
        .recommend-hire { background: #2E7D32; color: white; display: inline-block; padding: 4px 12px; border-radius: 20px; font-weight: bold; }
        .recommend-interview { background: #E65100; color: white; display: inline-block; padding: 4px 12px; border-radius: 20px; font-weight: bold; }
        .recommend-reject { background: #C62828; color: white; display: inline-block; padding: 4px 12px; border-radius: 20px; font-weight: bold; }
        .recommend-review { background: #7F8C8D; color: white; display: inline-block; padding: 4px 12px; border-radius: 20px; font-weight: bold; }
        
        .analysis-section { background: white; padding: 20px; border-radius: 12px; margin: 15px 0; border-left: 4px solid #1A4D4A; box-shadow: 0 1px 3px rgba(0,0,0,0.1); }
        .analysis-section h4 { color: #1A4D4A; margin-bottom: 15px; font-size: 1.1em; }
        .analysis-section p { color: #2C3E50; margin: 8px 0; line-height: 1.5; }
        .analysis-section ul { margin-left: 20px; margin-top: 8px; }
        .analysis-section li { color: #2C3E50; margin: 6px 0; line-height: 1.4; }
        
        .pre-screen-questions { background: #E8F5E9; padding: 20px; border-radius: 12px; margin: 15px 0; border-left: 4px solid #2E7D32; }
        .pre-screen-questions h4 { color: #1B5E20; margin-bottom: 12px; }
        .pre-screen-questions li { color: #2C3E50; margin: 8px 0; margin-left: 20px; line-height: 1.4; }
        
        /* Modal styles for candidate details */
        .modal { display: none; position: fixed; z-index: 1000; left: 0; top: 0; width: 100%; height: 100%; background-color: rgba(0,0,0,0.5); overflow-y: auto; }
        .modal-content { background-color: #F5F0E8; margin: 30px auto; padding: 0; border-radius: 16px; width: 90%; max-width: 800px; box-shadow: 0 4px 20px rgba(0,0,0,0.2); }
        .modal-header { background: #1A4D4A; color: white; padding: 20px; border-radius: 16px 16px 0 0; display: flex; justify-content: space-between; align-items: center; }
        .modal-header h2 { margin: 0; }
        .modal-body { padding: 24px; max-height: 70vh; overflow-y: auto; }
        .close { color: white; font-size: 28px; font-weight: bold; cursor: pointer; }
        .close:hover { color: #ccc; }
        
        .flex { display: flex; gap: 20px; flex-wrap: wrap; }
        .flex-2 { flex: 2; }
        .flex-1 { flex: 1; }
        
        label { color: #1A4D4A; font-weight: 600; margin-bottom: 5px; display: block; }
        
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
            <p>Intelligent Recruitment Platform with Detailed AI Analysis, JD Matching & Profile Authenticity Scoring</p>
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
            <button class="btn-primary" onclick="exportToCSV()">📥 Export to CSV</button>
            <div id="candidates-list" class="mt-20"></div>
        </div>
        
        <div id="upload-tab" style="display:none;">
            <div class="card">
                <h3>📄 Upload Resume (PDF or DOCX)</h3>
                {% if groq_enabled %}
                <div class="alert-info" style="background:#27AE60;">⚡ Groq AI is ACTIVE - Detailed analysis ready</div>
                {% else %}
                <div class="alert-info" style="background:#F39C12;">⚠️ Add GROQ_API_KEY to Railway</div>
                {% endif %}
                <input type="file" id="resume-file" accept=".pdf,.docx">
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
                <h3>🔍 Detailed AI-Powered Resume-JD Match Analysis</h3>
                <p>Get comprehensive analysis including executive summary, relevance assessment, domain analysis, genuineness assessment, and pre-screening questions.</p>
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
                <button class="btn-primary" onclick="analyzeMatch()">🤖 Run Detailed AI Analysis</button>
                <div id="analyze-result" class="mt-20"></div>
            </div>
        </div>
    </div>
    
    <!-- Modal for Candidate Details -->
    <div id="candidateModal" class="modal">
        <div class="modal-content">
            <div class="modal-header">
                <h2 id="modalTitle">Candidate Details</h2>
                <span class="close" onclick="closeModal()">&times;</span>
            </div>
            <div class="modal-body" id="modalBody">
                Loading...
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
                const jobSelect = document.getElementById('analyze-job-select');
                if (jobSelect) jobSelect.innerHTML = options;
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
                    const recClass = c.recommendation === 'hire' ? 'recommend-hire' : (c.recommendation === 'interview' ? 'recommend-interview' : 'recommend-reject');
                    return `
                    <div class="card" onclick="viewCandidate(${c.id})">
                        <h3>👤 ${escapeHtml(c.name || 'Unknown')}</h3>
                        ${c.email ? `<p>📧 ${escapeHtml(c.email)}</p>` : ''}
                        ${c.phone ? `<p>📞 ${escapeHtml(c.phone)}</p>` : ''}
                        ${c.skills ? `<p>🔧 ${c.skills.split(',').slice(0,5).map(s => `<span class="skill-tag">${escapeHtml(s.trim())}</span>`).join('')}${c.skills.split(',').length > 5 ? '...' : ''}</p>` : ''}
                        ${c.match_score ? `<p>🎯 Match Score: <span class="${matchClass}">${c.match_score}%</span></p>` : ''}
                        ${c.recommendation ? `<p>📌 Recommendation: <span class="${recClass}">${escapeHtml(c.recommendation)}</span></p>` : ''}
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
        
        async function viewCandidate(candidateId) {
            const candidate = candidatesData.find(c => c.id == candidateId);
            if (!candidate) return;
            
            const modal = document.getElementById('candidateModal');
            const modalTitle = document.getElementById('modalTitle');
            const modalBody = document.getElementById('modalBody');
            
            modalTitle.innerHTML = `👤 ${escapeHtml(candidate.name || 'Unknown')}`;
            
            let analysisHtml = '';
            if (candidate.detailed_analysis) {
                try {
                    const analysis = JSON.parse(candidate.detailed_analysis);
                    
                    if (analysis.executive_summary) {
                        analysisHtml += `
                            <div class="analysis-section">
                                <h4>📊 Executive Summary</h4>
                                <p><strong>Overall Relevance:</strong> ${escapeHtml(analysis.executive_summary.overall_relevance || 'N/A')}</p>
                                <p><strong>Final Verdict:</strong> ${escapeHtml(analysis.executive_summary.final_verdict || 'N/A')}</p>
                            </div>
                        `;
                    }
                    
                    if (analysis.relevance_analysis) {
                        analysisHtml += `<div class="analysis-section"><h4>📋 Relevance Analysis</h4>`;
                        if (analysis.relevance_analysis.mandatory_experience) {
                            analysisHtml += `<p><strong>Mandatory Experience:</strong></p><ul>`;
                            analysis.relevance_analysis.mandatory_experience.forEach(item => {
                                analysisHtml += `<li>${escapeHtml(item.requirement)}: ${escapeHtml(item.match)} (${escapeHtml(item.confidence || 'N/A')})</li>`;
                            });
                            analysisHtml += `</ul>`;
                        }
                        if (analysis.relevance_analysis.technical_skills) {
                            analysisHtml += `<p><strong>Technical Skills:</strong></p><ul>`;
                            analysis.relevance_analysis.technical_skills.forEach(item => {
                                analysisHtml += `<li>${escapeHtml(item.requirement)}: ${escapeHtml(item.match)}</li>`;
                            });
                            analysisHtml += `</ul>`;
                        }
                        analysisHtml += `</div>`;
                    }
                    
                    if (analysis.domain_assessment) {
                        analysisHtml += `
                            <div class="analysis-section">
                                <h4>🏢 Domain Assessment</h4>
                                <p><strong>Status:</strong> ${escapeHtml(analysis.domain_assessment.status || 'N/A')}</p>
                                <p>${escapeHtml(analysis.domain_assessment.analysis || '')}</p>
                                ${analysis.domain_assessment.pre_screen_question ? `<p><strong>Pre-screen Question:</strong> ${escapeHtml(analysis.domain_assessment.pre_screen_question)}</p>` : ''}
                            </div>
                        `;
                    }
                    
                    if (analysis.genuineness_assessment) {
                        analysisHtml += `
                            <div class="analysis-section">
                                <h4>🔍 Genuineness Assessment</h4>
                                <p><strong>Score:</strong> ${analysis.genuineness_assessment.score || 'N/A'}/10</p>
                                ${analysis.genuineness_assessment.positives ? `<p><strong>✅ Positives:</strong></p><ul>${analysis.genuineness_assessment.positives.map(p => `<li>${escapeHtml(p)}</li>`).join('')}</ul>` : ''}
                                ${analysis.genuineness_assessment.minor_concerns ? `<p><strong>🟡 Minor Concerns:</strong></p><ul>${analysis.genuineness_assessment.minor_concerns.map(c => `<li>${escapeHtml(c.concern)} - ${escapeHtml(c.severity || 'Low')}</li>`).join('')}</ul>` : ''}
                            </div>
                        `;
                    }
                    
                    if (analysis.pre_screening_questions && analysis.pre_screening_questions.length) {
                        analysisHtml += `
                            <div class="pre-screen-questions">
                                <h4>📝 Pre-Screening Questions</h4>
                                <ul>
                                    ${analysis.pre_screening_questions.map(q => `<li>${escapeHtml(q)}</li>`).join('')}
                                </ul>
                            </div>
                        `;
                    }
                    
                    if (analysis.final_verdict) {
                        analysisHtml += `
                            <div class="analysis-section">
                                <h4>⚖️ Final Verdict</h4>
                                <p><strong>Decision:</strong> <span class="${analysis.final_verdict.decision === 'Proceed to interview' ? 'recommend-hire' : 'recommend-reject'}">${escapeHtml(analysis.final_verdict.decision || 'N/A')}</span></p>
                                <p><strong>Risk Level:</strong> ${escapeHtml(analysis.final_verdict.risk_level || 'N/A')}</p>
                                <p><strong>Final Call:</strong> ${escapeHtml(analysis.final_verdict.final_call || 'N/A')}</p>
                            </div>
                        `;
                    }
                } catch(e) {
                    analysisHtml = '<div class="alert-info">Analysis data available but format may be corrupted.</div>';
                }
            } else {
                analysisHtml = '<div class="alert-info">No detailed analysis available yet. Run the Detailed Analysis for this candidate.</div>';
            }
            
            modalBody.innerHTML = `
                <div class="card" style="cursor: default;">
                    <h3>📧 Contact Information</h3>
                    <p><strong>Email:</strong> ${escapeHtml(candidate.email || 'Not provided')}</p>
                    <p><strong>Phone:</strong> ${escapeHtml(candidate.phone || 'Not provided')}</p>
                </div>
                
                <div class="card" style="cursor: default;">
                    <h3>🔧 Skills</h3>
                    <p>${candidate.skills ? candidate.skills.split(',').map(s => `<span class="skill-tag">${escapeHtml(s.trim())}</span>`).join('') : 'No skills listed'}</p>
                </div>
                
                <div class="card" style="cursor: default;">
                    <h3>💼 Work History</h3>
                    <p>${escapeHtml(candidate.work_history || 'No work history available')}</p>
                </div>
                
                <div class="card" style="cursor: default;">
                    <h3>📜 Certifications</h3>
                    <p>${escapeHtml(candidate.certifications || 'No certifications listed')}</p>
                </div>
                
                <div class="card" style="cursor: default;">
                    <h3>📊 Match Score & Recommendation</h3>
                    <p><strong>Match Score:</strong> <span class="${candidate.match_score >= 70 ? 'match-high' : (candidate.match_score >= 40 ? 'match-medium' : 'match-low')}">${candidate.match_score || 0}%</span></p>
                    <p><strong>Recommendation:</strong> <span class="${candidate.recommendation === 'hire' ? 'recommend-hire' : (candidate.recommendation === 'interview' ? 'recommend-interview' : 'recommend-reject')}">${escapeHtml(candidate.recommendation || 'Not reviewed')}</span></p>
                </div>
                
                <div class="card" style="cursor: default;">
                    <h3>📅 Added On</h3>
                    <p>${new Date(candidate.created_at).toLocaleString()}</p>
                </div>
                
                <h3 style="margin-top: 20px; color: #1A4D4A;">🤖 AI Analysis Results</h3>
                ${analysisHtml}
                
                <button class="btn-close" onclick="closeModal()">Close</button>
            `;
            
            modal.style.display = 'block';
        }
        
        function closeModal() {
            document.getElementById('candidateModal').style.display = 'none';
        }
        
        window.onclick = function(event) {
            const modal = document.getElementById('candidateModal');
            if (event.target == modal) {
                modal.style.display = 'none';
            }
        }
        
        async function uploadResume() {
            const file = document.getElementById('resume-file').files[0];
            if (!file) { alert('Select a file'); return; }
            
            const formData = new FormData();
            formData.append('resume', file);
            
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
                        <button class="btn-primary" onclick='saveCandidate(${JSON.stringify(result).replace(/'/g, "\\'")})'>💾 Save Candidate</button>
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
            } else {
                const error = await response.json();
                alert('Error saving candidate: ' + (error.error || 'Unknown error'));
            }
        }
        
        async function analyzeMatch() {
            const jobId = document.getElementById('analyze-job-select').value;
            const candidateId = document.getElementById('analyze-candidate-select').value;
            if (!jobId || !candidateId) { alert('Select both Job and Candidate'); return; }
            
            const job = jobsData.find(j => j.id == jobId);
            const candidate = candidatesData.find(c => c.id == candidateId);
            
            const resultDiv = document.getElementById('analyze-result');
            resultDiv.innerHTML = '<div class="spinner"></div><p>Running detailed Groq AI analysis...</p>';
            
            try {
                const response = await fetch('/api/analyze-match', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({ 
                        job_id: jobId,
                        candidate_id: candidateId,
                        jd_text: job.description || '', 
                        resume_text: candidate.resume_text || '',
                        candidate_name: candidate.name || ''
                    })
                });
                const result = await response.json();
                
                if (result.error) {
                    resultDiv.innerHTML = `<div class="alert-error">${result.error}</div>`;
                    return;
                }
                
                let analysisHtml = `<h3 style="color: #1A4D4A; margin-bottom: 15px;">👤 Analysis for: ${escapeHtml(candidate.name || 'Candidate')}</h3>`;
                
                if (result.executive_summary) {
                    analysisHtml += `
                        <div class="analysis-section">
                            <h4>📊 Executive Summary</h4>
                            <p><strong>Overall Relevance:</strong> ${escapeHtml(result.executive_summary.overall_relevance || 'N/A')}</p>
                            <p><strong>Final Verdict:</strong> ${escapeHtml(result.executive_summary.final_verdict || 'N/A')}</p>
                        </div>
                    `;
                }
                
                if (result.relevance_analysis) {
                    analysisHtml += `<div class="analysis-section"><h4>📋 Relevance Analysis</h4>`;
                    if (result.relevance_analysis.mandatory_experience) {
                        analysisHtml += `<p><strong>Mandatory Experience:</strong></p><ul>`;
                        result.relevance_analysis.mandatory_experience.forEach(item => {
                            analysisHtml += `<li>${escapeHtml(item.requirement)}: ${escapeHtml(item.match)} (${escapeHtml(item.confidence || 'N/A')})</li>`;
                        });
                        analysisHtml += `</ul>`;
                    }
                    if (result.relevance_analysis.technical_skills) {
                        analysisHtml += `<p><strong>Technical Skills:</strong></p><ul>`;
                        result.relevance_analysis.technical_skills.forEach(item => {
                            analysisHtml += `<li>${escapeHtml(item.requirement)}: ${escapeHtml(item.match)}</li>`;
                        });
                        analysisHtml += `</ul>`;
                    }
                    analysisHtml += `</div>`;
                }
                
                if (result.domain_assessment) {
                    analysisHtml += `
                        <div class="analysis-section">
                            <h4>🏢 Domain Assessment</h4>
                            <p><strong>Status:</strong> ${escapeHtml(result.domain_assessment.status || 'N/A')}</p>
                            <p>${escapeHtml(result.domain_assessment.analysis || '')}</p>
                            ${result.domain_assessment.pre_screen_question ? `<p><strong>Pre-screen Question:</strong> ${escapeHtml(result.domain_assessment.pre_screen_question)}</p>` : ''}
                        </div>
                    `;
                }
                
                if (result.genuineness_assessment) {
                    analysisHtml += `
                        <div class="analysis-section">
                            <h4>🔍 Genuineness Assessment</h4>
                            <p><strong>Score:</strong> ${result.genuineness_assessment.score || 'N/A'}/10</p>
                            ${result.genuineness_assessment.positives ? `<p><strong>✅ Positives:</strong></p><ul>${result.genuineness_assessment.positives.map(p => `<li>${escapeHtml(p)}</li>`).join('')}</ul>` : ''}
                            ${result.genuineness_assessment.minor_concerns ? `<p><strong>🟡 Minor Concerns:</strong></p><ul>${result.genuineness_assessment.minor_concerns.map(c => `<li>${escapeHtml(c.concern)} - ${escapeHtml(c.severity || 'Low')}</li>`).join('')}</ul>` : ''}
                        </div>
                    `;
                }
                
                if (result.pre_screening_questions && result.pre_screening_questions.length) {
                    analysisHtml += `
                        <div class="pre-screen-questions">
                            <h4>📝 Pre-Screening Questions</h4>
                            <ul>
                                ${result.pre_screening_questions.map(q => `<li>${escapeHtml(q)}</li>`).join('')}
                            </ul>
                        </div>
                    `;
                }
                
                if (result.final_verdict) {
                    analysisHtml += `
                        <div class="analysis-section">
                            <h4>⚖️ Final Verdict</h4>
                            <p><strong>Decision:</strong> <span class="${result.final_verdict.decision === 'Proceed to interview' ? 'recommend-hire' : 'recommend-reject'}">${escapeHtml(result.final_verdict.decision || 'N/A')}</span></p>
                            <p><strong>Risk Level:</strong> ${escapeHtml(result.final_verdict.risk_level || 'N/A')}</p>
                            <p><strong>Final Call:</strong> ${escapeHtml(result.final_verdict.final_call || 'N/A')}</p>
                        </div>
                    `;
                }
                
                const matchClass = result.match_score >= 70 ? 'match-high' : (result.match_score >= 40 ? 'match-medium' : 'match-low');
                const recClass = result.recommendation === 'hire' ? 'recommend-hire' : (result.recommendation === 'interview' ? 'recommend-interview' : 'recommend-reject');
                
                resultDiv.innerHTML = `
                    <div class="alert-success">
                        <h4>📊 Detailed Groq AI Analysis Complete</h4>
                        <p><strong>🎯 Match Score:</strong> <span class="${matchClass}">${result.match_score || 0}%</span></p>
                        <p><strong>📌 Recommendation:</strong> <span class="${recClass}">${escapeHtml(result.recommendation || 'Review')}</span></p>
                        ${analysisHtml}
                        <p style="margin-top: 10px; color: #27AE60;"><small>✅ Analysis has been automatically saved to the candidate record. Click on the candidate name in Candidates tab to view stored analysis.</small></p>
                    </div>
                `;
                
                loadCandidates();
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
            } else {
                alert('Error creating job');
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
    
    conn = sqlite3.connect('shahnai.db')
    c = conn.cursor()
    c.execute('''INSERT INTO candidates (name, email, phone, skills, work_history, certifications, resume_text) 
                 VALUES (?, ?, ?, ?, ?, ?, ?)''',
              (data.get('name'), data.get('email'), data.get('phone'), skills,
               data.get('work_history', ''), data.get('certifications', ''), data.get('resume_text', '')))
    conn.commit()
    conn.close()
    return jsonify({'message': 'Candidate saved'})

@app.route('/api/candidates/<int:candidate_id>', methods=['PUT'])
def update_candidate(candidate_id):
    data = request.json
    conn = sqlite3.connect('shahnai.db')
    c = conn.cursor()
    c.execute('''UPDATE candidates 
                 SET match_score = ?, recommendation = ?, detailed_analysis = ?
                 WHERE id = ?''',
              (data.get('match_score'), data.get('recommendation'), data.get('detailed_analysis'), candidate_id))
    conn.commit()
    conn.close()
    return jsonify({'message': 'Candidate updated'})

@app.route('/api/analyze-match', methods=['POST'])
def analyze_match():
    data = request.json
    resume_text = data.get('resume_text', '')
    jd_text = data.get('jd_text', '')
    job_id = data.get('job_id')
    candidate_id = data.get('candidate_id')
    candidate_name = data.get('candidate_name', '')
    
    if not resume_text or not jd_text:
        return jsonify({'error': 'Missing text'}), 400
    
    if not GROQ_API_KEY:
        return jsonify({'error': 'Groq API key missing. Add GROQ_API_KEY to Railway variables.'}), 503
    
    result = analyze_with_groq_detailed(resume_text, jd_text, candidate_name)
    
    if result:
        match_score = result.get('match_score', 0)
        recommendation = result.get('recommendation', 'review')
        
        if candidate_id:
            detailed_json = json.dumps(result, indent=2)
            conn = sqlite3.connect('shahnai.db')
            c = conn.cursor()
            c.execute('''UPDATE candidates 
                         SET match_score = ?, recommendation = ?, detailed_analysis = ?
                         WHERE id = ?''',
                      (match_score, recommendation, detailed_json, candidate_id))
            conn.commit()
            conn.close()
            print(f"✅ Detailed analysis saved to candidate {candidate_id}")
        
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
        writer.writerow([
            c.get('id', ''), c.get('name', ''), c.get('email', ''), c.get('phone', ''),
            c.get('skills', ''), c.get('match_score', ''), c.get('recommendation', ''), c.get('created_at', '')
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
        return jsonify({'error': 'No file'}), 400
    
    file = request.files['resume']
    if file.filename == '':
        return jsonify({'error': 'No file'}), 400
    
    if not allowed_file(file.filename):
        return jsonify({'error': 'Invalid file type'}), 400
    
    filename = secure_filename(file.filename)
    filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
    file.save(filepath)
    
    result = parse_resume_file(filepath)
    os.remove(filepath)
    
    return jsonify(result)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
