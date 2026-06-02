# app.py - COMPLETE WORKING VERSION with Fixed Save Button
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
else:
    print("❌ No valid GROQ_API_KEY found")

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
            data = response.json()
            return data['choices'][0]['message']['content']
        return None
    except Exception as e:
        print(f"Groq API error: {e}")
        return None

def analyze_with_groq_detailed(resume_text, jd_text, candidate_name=""):
    if not GROQ_API_KEY:
        return None
    
    resume_text = resume_text[:3000]
    jd_text = jd_text[:2500]
    
    prompt = f"""Analyze this resume against the job description.

JOB DESCRIPTION:
{jd_text}

RESUME:
{resume_text}

Return ONLY JSON:
{{
    "executive_summary": {{"overall_relevance": "text", "final_verdict": "text"}},
    "relevance_analysis": {{
        "mandatory_experience": [{{"requirement": "text", "match": "✅/⚠️/❌", "confidence": "High/Medium/Low"}}],
        "technical_skills": [{{"requirement": "text", "match": "✅/⚠️/❌"}}]
    }},
    "domain_assessment": {{"status": "text", "analysis": "text", "pre_screen_question": "text"}},
    "genuineness_assessment": {{"score": 0, "positives": [], "minor_concerns": []}},
    "final_verdict": {{"decision": "text", "risk_level": "Low/Medium/High", "final_call": "text"}},
    "pre_screening_questions": [],
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
            return json.loads(response_text)
        except:
            return None
    return None

def parse_resume_with_groq(resume_text):
    if not GROQ_API_KEY:
        return None
    
    prompt = f"""Extract from resume. Return ONLY JSON: Resume: {resume_text[:2500]}

Return: {{"name": "", "email": "", "phone": "", "skills": [], "work_history": "", "certifications": ""}}"""
    
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
        recommendation TEXT DEFAULT 'review',
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
    print("✅ Database initialized")

init_db()

# ============ BASIC PARSING ============
COMMON_SKILLS = [
    'Python', 'Java', 'JavaScript', 'TypeScript', 'React', 'Angular', 'Vue', 'Node.js',
    'SQL', 'MongoDB', 'PostgreSQL', 'MySQL', 'AWS', 'Azure', 'Docker', 'Kubernetes',
    'Power Apps', 'Power Automate', 'Azure DevOps', 'Dataverse', 'SharePoint', 'Git'
]

def extract_skills_from_text(text):
    if not text:
        return []
    text_lower = text.lower()
    return [s for s in COMMON_SKILLS if s.lower() in text_lower]

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
    return lines[0].strip() if lines and len(lines[0]) < 50 else "Unknown"

def extract_work_history(text):
    lines = text.split('\n')
    experience = []
    keywords = ['experience', 'work', 'employment', 'job', 'position', 'role']
    for line in lines[:50]:
        if any(kw in line.lower() for kw in keywords):
            clean = re.sub(r'\s+', ' ', line).strip()
            if 10 < len(clean) < 300:
                experience.append(clean)
    return ' | '.join(experience[:3]) if experience else ""

def extract_certifications(text):
    certs = ['PMP', 'CISSP', 'AWS', 'Scrum', 'ITIL']
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
            result['work_history'] = groq_result.get('work_history', result['work_history'])
            result['certifications'] = groq_result.get('certifications', result['certifications'])
            result['ai_used'] = True
    
    return result

# ============ HTML TEMPLATE ============
HTML_TEMPLATE = '''
<!DOCTYPE html>
<html>
<head>
    <title>ShahnaIT Scout</title>
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body { background-color: #F5F0E8; font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; color: #2C3E50; }
        .container { max-width: 1400px; margin: 0 auto; padding: 20px; }
        
        .header { background: linear-gradient(135deg, #1A4D4A 0%, #0F3533 100%); color: white; padding: 30px; border-radius: 16px; margin-bottom: 30px; }
        .header h1 { font-size: 2em; margin-bottom: 10px; }
        
        .badge-ai { display: inline-block; background: #27AE60; font-size: 12px; padding: 4px 12px; border-radius: 20px; margin-left: 10px; vertical-align: middle; }
        
        .tabs { display: flex; gap: 5px; margin-bottom: 30px; background: white; padding: 10px; border-radius: 12px; flex-wrap: wrap; }
        .tab-btn { background: transparent; border: none; padding: 12px 24px; font-size: 15px; cursor: pointer; color: #555; border-radius: 8px; }
        .tab-btn:hover { background: #E8E0D0; color: #1A4D4A; }
        .tab-btn.active { background: #1A4D4A; color: white; }
        
        .card { background: white; border-radius: 12px; padding: 24px; margin-bottom: 20px; box-shadow: 0 2px 8px rgba(0,0,0,0.08); border-left: 4px solid #1A4D4A; cursor: pointer; transition: transform 0.2s; }
        .card:hover { transform: translateY(-2px); box-shadow: 0 4px 12px rgba(0,0,0,0.15); }
        .card.no-click { cursor: default; }
        .card h3 { color: #1A4D4A; margin-bottom: 12px; }
        
        .btn-primary { background: #1A4D4A; color: white; border: none; padding: 12px 24px; border-radius: 8px; cursor: pointer; font-weight: 600; margin: 10px 5px; }
        .btn-primary:hover { background: #2A6B67; }
        
        input, textarea, select { width: 100%; padding: 12px; margin: 10px 0; border: 1px solid #ddd; border-radius: 8px; }
        input:focus, textarea:focus, select:focus { outline: none; border-color: #1A4D4A; }
        
        .alert-success { background: #27AE60; color: white; padding: 14px; border-radius: 8px; margin: 10px 0; }
        .alert-error { background: #E74C3C; color: white; padding: 14px; border-radius: 8px; margin: 10px 0; }
        .alert-info { background: #3498DB; color: white; padding: 14px; border-radius: 8px; margin: 10px 0; }
        
        .spinner { border: 3px solid #F5F0E8; border-top: 3px solid #1A4D4A; border-radius: 50%; width: 40px; height: 40px; animation: spin 0.8s linear infinite; margin: 20px auto; }
        @keyframes spin { 0% { transform: rotate(0deg); } 100% { transform: rotate(360deg); } }
        
        .skill-tag { display: inline-block; background: #E8E0D0; padding: 4px 12px; border-radius: 20px; margin: 3px; font-size: 12px; color: #1A4D4A; }
        .match-high { background: #2E7D32; color: white; padding: 4px 12px; border-radius: 20px; display: inline-block; }
        .match-medium { background: #E65100; color: white; padding: 4px 12px; border-radius: 20px; display: inline-block; }
        .match-low { background: #C62828; color: white; padding: 4px 12px; border-radius: 20px; display: inline-block; }
        
        .analysis-section { background: white; padding: 20px; border-radius: 12px; margin: 15px 0; border-left: 4px solid #1A4D4A; }
        .pre-screen-questions { background: #E8F5E9; padding: 20px; border-radius: 12px; margin: 15px 0; }
        
        .modal { display: none; position: fixed; z-index: 1000; left: 0; top: 0; width: 100%; height: 100%; background: rgba(0,0,0,0.5); overflow-y: auto; }
        .modal-content { background: #F5F0E8; margin: 30px auto; border-radius: 16px; width: 90%; max-width: 800px; }
        .modal-header { background: #1A4D4A; color: white; padding: 20px; border-radius: 16px 16px 0 0; display: flex; justify-content: space-between; }
        .modal-body { padding: 24px; max-height: 70vh; overflow-y: auto; }
        .close { color: white; font-size: 28px; cursor: pointer; }
        
        .flex { display: flex; gap: 20px; flex-wrap: wrap; }
        .flex-1 { flex: 1; }
        
        @media (max-width: 768px) { .container { padding: 10px; } .tab-btn { padding: 8px 16px; } }
        .text-center { text-align: center; }
        .mt-20 { margin-top: 20px; }
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
            <p>Intelligent Recruitment Platform with AI Analysis</p>
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
            <button class="btn-primary" onclick="exportToCSV()">📥 Export CSV</button>
            <div id="candidates-list" class="mt-20"></div>
        </div>
        
        <div id="upload-tab" style="display:none;">
            <div class="card no-click">
                <h3>📄 Upload Resume (PDF/DOCX)</h3>
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
                    <textarea id="job-desc" rows="5" placeholder="Job Description"></textarea>
                    <button type="submit" class="btn-primary">Create Job</button>
                </form>
            </div>
        </div>
        
        <div id="analyze-tab" style="display:none;">
            <div class="card no-click">
                <h3>🔍 AI-Powered Resume-JD Analysis</h3>
                <div class="flex">
                    <div class="flex-1">
                        <select id="analyze-job-select">
                            <option value="">-- Select Job --</option>
                        </select>
                    </div>
                    <div class="flex-1">
                        <select id="analyze-candidate-select">
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
                    container.innerHTML = '<div class="card no-click">No jobs yet. Create one.</div>';
                    return;
                }
                container.innerHTML = jobsData.map(job => `
                    <div class="card no-click">
                        <h3>${escapeHtml(job.title)}</h3>
                        ${job.company ? `<p>🏢 ${escapeHtml(job.company)}</p>` : ''}
                        <small>📅 ${new Date(job.created_at).toLocaleDateString()}</small>
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
                    container.innerHTML = '<div class="card no-click">No candidates yet. Upload resumes.</div>';
                    return;
                }
                container.innerHTML = candidatesData.map(c => `
                    <div class="card" onclick="viewCandidate(${c.id})">
                        <h3>👤 ${escapeHtml(c.name || 'Unknown')}</h3>
                        ${c.email ? `<p>📧 ${escapeHtml(c.email)}</p>` : ''}
                        ${c.skills ? `<p>🔧 ${c.skills.split(',').slice(0,3).map(s => `<span class="skill-tag">${escapeHtml(s.trim())}</span>`).join('')}</p>` : ''}
                        <small>📅 ${new Date(c.created_at).toLocaleDateString()}</small>
                    </div>
                `).join('');
                
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
                        analysisHtml += `<div class="analysis-section"><h4>📊 Summary</h4><p>${escapeHtml(analysis.executive_summary.final_verdict || '')}</p></div>`;
                    }
                    if (analysis.pre_screening_questions && analysis.pre_screening_questions.length) {
                        analysisHtml += `<div class="pre-screen-questions"><h4>📝 Questions</h4><ul>${analysis.pre_screening_questions.map(q => `<li>${escapeHtml(q)}</li>`).join('')}</ul></div>`;
                    }
                } catch(e) { analysisHtml = '<div class="alert-info">Analysis available</div>'; }
            } else {
                analysisHtml = '<div class="alert-info">No analysis yet. Run analysis in Analyze Match tab.</div>';
            }
            
            document.getElementById('modalBody').innerHTML = `
                <div class="card no-click"><h3>📧 Contact</h3><p>Email: ${escapeHtml(candidate.email || 'N/A')}<br>Phone: ${escapeHtml(candidate.phone || 'N/A')}</p></div>
                <div class="card no-click"><h3>🔧 Skills</h3><p>${candidate.skills ? candidate.skills.split(',').map(s => `<span class="skill-tag">${escapeHtml(s.trim())}</span>`).join('') : 'None'}</p></div>
                <div class="card no-click"><h3>💼 Work History</h3><p>${escapeHtml(candidate.work_history || 'N/A')}</p></div>
                <div class="card no-click"><h3>📜 Certifications</h3><p>${escapeHtml(candidate.certifications || 'N/A')}</p></div>
                <h3 style="color:#1A4D4A;">🤖 AI Analysis</h3>
                ${analysisHtml}
                <button class="btn-primary" onclick="closeModal()">Close</button>
            `;
            document.getElementById('candidateModal').style.display = 'block';
        }
        
        function closeModal() {
            document.getElementById('candidateModal').style.display = 'none';
        }
        
        // Parse Button
        document.getElementById('parseBtn').onclick = async function() {
            const file = document.getElementById('resume-file').files[0];
            if (!file) { alert('Select a file'); return; }
            
            const formData = new FormData();
            formData.append('resume', file);
            
            const resultDiv = document.getElementById('parse-result');
            resultDiv.innerHTML = '<div class="spinner"></div><p class="text-center">Parsing...</p>';
            
            try {
                const response = await fetch('/api/parse-resume', { method: 'POST', body: formData });
                const result = await response.json();
                
                if (result.error) {
                    resultDiv.innerHTML = `<div class="alert-error">${result.error}</div>`;
                    return;
                }
                
                resultDiv.innerHTML = `
                    <div class="alert-success">
                        <h4>✅ Resume Parsed ${result.ai_used ? '⚡ AI' : ''}</h4>
                        <p><strong>Name:</strong> ${escapeHtml(result.name)}</p>
                        <p><strong>Email:</strong> ${escapeHtml(result.email)}</p>
                        <p><strong>Phone:</strong> ${escapeHtml(result.phone)}</p>
                        <p><strong>Skills:</strong> ${result.skills ? result.skills.map(s => `<span class="skill-tag">${escapeHtml(s)}</span>`).join('') : 'None'}</p>
                        <button class="btn-primary" onclick="saveCandidateToDB(${JSON.stringify(result).replace(/"/g, '&quot;')})">💾 Save Candidate</button>
                    </div>
                `;
            } catch (error) {
                resultDiv.innerHTML = '<div class="alert-error">Error parsing</div>';
            }
        };
        
        // Save Candidate Function
        window.saveCandidateToDB = async function(candidateData) {
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
        };
        
        // Analyze Button
        document.getElementById('analyzeBtn').onclick = async function() {
            const jobId = document.getElementById('analyze-job-select').value;
            const candidateId = document.getElementById('analyze-candidate-select').value;
            if (!jobId || !candidateId) { alert('Select both Job and Candidate'); return; }
            
            const job = jobsData.find(j => j.id == jobId);
            const candidate = candidatesData.find(c => c.id == candidateId);
            
            const resultDiv = document.getElementById('analyze-result');
            resultDiv.innerHTML = '<div class="spinner"></div><p>Running AI analysis...</p>';
            
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
                    resultDiv.innerHTML = `<div class="alert-error">${result.error}</div>`;
                    return;
                }
                
                const matchClass = result.match_score >= 70 ? 'match-high' : (result.match_score >= 40 ? 'match-medium' : 'match-low');
                resultDiv.innerHTML = `
                    <div class="alert-success">
                        <h4>📊 Analysis Complete</h4>
                        <p><strong>🎯 Match Score:</strong> <span class="${matchClass}">${result.match_score || 0}%</span></p>
                        <p><strong>📌 Recommendation:</strong> ${escapeHtml(result.recommendation || 'Review')}</p>
                        ${result.executive_summary ? `<div class="analysis-section"><p>${escapeHtml(result.executive_summary.final_verdict || '')}</p></div>` : ''}
                        <p><small>✅ Analysis saved to candidate record</small></p>
                    </div>
                `;
                loadCandidates();
            } catch (error) {
                resultDiv.innerHTML = '<div class="alert-error">Analysis failed</div>';
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
                showTab('jobs');
                loadJobs();
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
    desc = data.get('description', '')
    skills = extract_skills_from_text(desc)
    conn = sqlite3.connect('shahnai.db')
    c = conn.cursor()
    c.execute('INSERT INTO jobs (title, company, description, required_skills) VALUES (?, ?, ?, ?)',
              (data.get('title'), data.get('company'), desc, ', '.join(skills)))
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

@app.route('/api/analyze-match', methods=['POST'])
def analyze_match():
    data = request.json
    resume_text = data.get('resume_text', '')
    jd_text = data.get('jd_text', '')
    candidate_id = data.get('candidate_id')
    
    if not resume_text or not jd_text:
        return jsonify({'error': 'Missing text'}), 400
    
    if not GROQ_API_KEY:
        return jsonify({'error': 'Groq API key missing'}), 503
    
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
        return jsonify({'error': 'Invalid file type'}), 400
    
    filename = secure_filename(file.filename)
    filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
    file.save(filepath)
    
    result = parse_resume_file(filepath)
    os.remove(filepath)
    
    return jsonify(result)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
