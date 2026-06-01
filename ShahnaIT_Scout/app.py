# app.py - WORKING GEMINI INTEGRATION (Latest API)
import os
import re
import sqlite3
import csv
import io
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

# ============ GEMINI SETUP WITH LATEST API ============
GEMINI_ENABLED = False

try:
    # Try to import Gemini
    import google.generativeai as genai
    print("✅ Google Generative AI imported")
    
    api_key = os.getenv('GEMINI_API_KEY')
    if api_key:
        genai.configure(api_key=api_key)
        # Use the correct model name
        gemini_model = genai.GenerativeModel('gemini-1.5-flash')
        GEMINI_ENABLED = True
        print("✅✅✅ GEMINI AI IS ACTIVE! ✅✅✅")
    else:
        print("❌ No API key found")
except Exception as e:
    print(f"❌ Gemini setup error: {e}")

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
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )''')
    
    conn.commit()
    conn.close()
    print("✅ Database initialized")

init_db()

# ============ SKILLS DATABASE ============
COMMON_SKILLS = [
    'Python', 'Java', 'JavaScript', 'TypeScript', 'React', 'Angular', 'Vue', 'Node.js',
    'SQL', 'MongoDB', 'PostgreSQL', 'MySQL', 'AWS', 'Azure', 'GCP', 'Docker', 'Kubernetes',
    'Machine Learning', 'AI', 'Data Science', 'Excel', 'Tableau', 'Power BI',
    'HTML', 'CSS', 'Git', 'REST API', 'GraphQL'
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

def parse_with_gemini(resume_text):
    """Parse resume using Gemini - FIXED VERSION"""
    if not GEMINI_ENABLED:
        return None
    
    try:
        # Simple, direct prompt
        prompt = f"""
        Extract information from this resume. Return ONLY valid JSON, no other text.
        
        Resume: {resume_text[:3000]}
        
        Return JSON with these exact keys:
        {{
            "name": "full name here",
            "email": "email here", 
            "phone": "phone number here",
            "skills": ["skill1", "skill2", "skill3"],
            "work_history": "brief work history summary",
            "certifications": "certifications here"
        }}
        """
        
        response = gemini_model.generate_content(prompt)
        response_text = response.text
        
        # Clean up the response
        response_text = response_text.strip()
        if response_text.startswith('```json'):
            response_text = response_text[7:]
        if response_text.startswith('```'):
            response_text = response_text[3:]
        if response_text.endswith('```'):
            response_text = response_text[:-3]
        
        # Parse JSON
        import json
        result = json.loads(response_text)
        print(f"✅ Gemini parsed: {result.get('name', 'Unknown')}")
        return result
        
    except Exception as e:
        print(f"Gemini error: {e}")
        return None

def parse_resume_file(file_path):
    """Parse resume - uses Gemini if available"""
    if file_path.endswith('.pdf'):
        text = extract_text_from_pdf(file_path)
    elif file_path.endswith('.docx'):
        text = extract_text_from_docx(file_path)
    else:
        text = ""
    
    if not text:
        return {'error': 'Could not extract text from file'}
    
    # Try Gemini first
    gemini_result = parse_with_gemini(text)
    
    if gemini_result:
        # Use Gemini results
        skills = gemini_result.get('skills', [])
        if isinstance(skills, str):
            skills = [s.strip() for s in skills.split(',')]
        
        return {
            'name': gemini_result.get('name', extract_name(text)),
            'email': gemini_result.get('email', extract_email(text)),
            'phone': gemini_result.get('phone', extract_phone(text)),
            'skills': skills if skills else extract_skills_from_text(text),
            'work_history': gemini_result.get('work_history', extract_work_history(text)),
            'certifications': gemini_result.get('certifications', extract_certifications(text)),
            'resume_text': text[:1000],
            'ai_used': True
        }
    else:
        # Fallback to basic parsing
        return {
            'name': extract_name(text),
            'email': extract_email(text),
            'phone': extract_phone(text),
            'skills': extract_skills_from_text(text),
            'work_history': extract_work_history(text),
            'certifications': extract_certifications(text),
            'resume_text': text[:1000],
            'ai_used': False
        }

# ============ HELPER FUNCTIONS ============
def extract_text_from_pdf(file_path):
    try:
        text = ""
        with open(file_path, 'rb') as file:
            pdf_reader = PyPDF2.PdfReader(file)
            for page in pdf_reader.pages:
                text += page.extract_text()
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
    pattern = r'\b\d{3}[-.]?\d{3}[-.]?\d{4}\b'
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
    keywords = ['experience', 'work', 'employment', 'job', 'position', 'role']
    for line in lines[:50]:
        line_lower = line.lower()
        if any(kw in line_lower for kw in keywords):
            clean_line = re.sub(r'\s+', ' ', line).strip()
            if 10 < len(clean_line) < 300:
                experience.append(clean_line)
    return ' | '.join(experience[:3]) if experience else ""

def extract_certifications(text):
    cert_keywords = ['certified', 'certification', 'certificate', 'PMP', 'CISSP', 'AWS']
    found = []
    text_lower = text.lower()
    for keyword in cert_keywords:
        if keyword.lower() in text_lower:
            sentences = re.split(r'[.!?]+', text)
            for sentence in sentences:
                if keyword.lower() in sentence.lower():
                    clean = re.sub(r'\s+', ' ', sentence).strip()
                    if len(clean) < 100:
                        found.append(clean)
                        break
    return ' | '.join(found[:3]) if found else ""

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
        .tab-btn { background: transparent; border: none; padding: 12px 24px; font-size: 15px; cursor: pointer; color: #7F8C8D; border-radius: 8px; }
        .tab-btn:hover { background: #F5F0E8; color: #1A4D4A; }
        .tab-btn.active { background: #1A4D4A; color: white; }
        
        .card { background: white; border-radius: 12px; padding: 24px; margin-bottom: 20px; box-shadow: 0 2px 8px rgba(0,0,0,0.08); border-left: 4px solid #1A4D4A; }
        .card h3 { color: #1A4D4A; margin-bottom: 12px; }
        
        .btn-primary { background: #1A4D4A; color: white; border: none; padding: 12px 24px; border-radius: 8px; cursor: pointer; font-weight: 600; margin-right: 10px; margin-bottom: 10px; }
        .btn-primary:hover { background: #2A6B67; }
        
        input, textarea { width: 100%; padding: 12px; margin: 10px 0 15px 0; border: 1px solid #ddd; border-radius: 8px; }
        input:focus, textarea:focus { outline: none; border-color: #1A4D4A; }
        
        .alert-success { background: #27AE60; color: white; padding: 14px; border-radius: 8px; margin: 10px 0; }
        .alert-error { background: #E74C3C; color: white; padding: 14px; border-radius: 8px; margin: 10px 0; }
        
        .spinner { border: 3px solid #F5F0E8; border-top: 3px solid #1A4D4A; border-radius: 50%; width: 40px; height: 40px; animation: spin 0.8s linear infinite; margin: 20px auto; }
        @keyframes spin { 0% { transform: rotate(0deg); } 100% { transform: rotate(360deg); } }
        
        .skill-tag { display: inline-block; background: #F5F0E8; padding: 4px 12px; border-radius: 20px; margin: 3px; font-size: 12px; }
        
        @media (max-width: 768px) { .container { padding: 10px; } .tab-btn { padding: 8px 16px; } }
        .text-center { text-align: center; }
        .mt-20 { margin-top: 20px; }
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
            <p>Intelligent Recruitment Platform with {% if gemini_enabled %}Gemini AI{% else %}Smart{% endif %} Parsing</p>
        </div>
        
        <div class="tabs">
            <button class="tab-btn active" onclick="showTab('jobs')">📋 Jobs</button>
            <button class="tab-btn" onclick="showTab('candidates')">👥 Candidates</button>
            <button class="tab-btn" onclick="showTab('upload')">📄 Upload Resume</button>
            <button class="tab-btn" onclick="showTab('create-job')">➕ Create Job</button>
        </div>
        
        <div id="jobs-tab"><div id="jobs-list"></div></div>
        
        <div id="candidates-tab" style="display:none;">
            <button class="btn-primary" onclick="exportToCSV()">📥 Export to CSV</button>
            <div id="candidates-list"></div>
        </div>
        
        <div id="upload-tab" style="display:none;">
            <div class="card">
                <h3>📄 Upload Resume (PDF or DOCX)</h3>
                {% if gemini_enabled %}
                <p style="color: #27AE60; margin-bottom: 10px;">✅ Gemini AI is ACTIVE - Your resume will be parsed with AI!</p>
                {% else %}
                <p style="color: #E74C3C; margin-bottom: 10px;">❌ Gemini AI is DISABLED - Add GEMINI_API_KEY to Railway</p>
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
                    <textarea id="job-desc" rows="4" placeholder="Job Description"></textarea>
                    <button type="submit" class="btn-primary">Create Job</button>
                </form>
            </div>
        </div>
    </div>
    
    <script>
        let jobsData = [];
        let geminiEnabled = {{ 'true' if gemini_enabled else 'false' }};
        
        function showTab(tabName) {
            document.getElementById('jobs-tab').style.display = 'none';
            document.getElementById('candidates-tab').style.display = 'none';
            document.getElementById('upload-tab').style.display = 'none';
            document.getElementById('create-job-tab').style.display = 'none';
            document.getElementById(tabName + '-tab').style.display = 'block';
            document.querySelectorAll('.tab-btn').forEach(btn => btn.classList.remove('active'));
            event.target.classList.add('active');
            if (tabName === 'jobs') loadJobs();
            if (tabName === 'candidates') loadCandidates();
        }
        
        async function loadJobs() {
            try {
                const response = await fetch('/api/jobs');
                jobsData = await response.json();
                const container = document.getElementById('jobs-list');
                if (jobsData.length === 0) {
                    container.innerHTML = '<div class="card text-center">No jobs yet.</div>';
                    return;
                }
                container.innerHTML = jobsData.map(job => `
                    <div class="card">
                        <h3>${escapeHtml(job.title)}</h3>
                        ${job.company ? `<p><strong>Company:</strong> ${escapeHtml(job.company)}</p>` : ''}
                        ${job.required_skills ? `<p><strong>🔧 Skills:</strong> ${job.required_skills.split(',').map(s => `<span class="skill-tag">${s.trim()}</span>`).join('')}</p>` : ''}
                        <small>📅 Created: ${new Date(job.created_at).toLocaleDateString()}</small>
                    </div>
                `).join('');
            } catch (error) {
                document.getElementById('jobs-list').innerHTML = '<div class="alert-error">Error loading jobs</div>';
            }
        }
        
        async function loadCandidates() {
            try {
                const response = await fetch('/api/candidates');
                const candidates = await response.json();
                const container = document.getElementById('candidates-list');
                if (candidates.length === 0) {
                    container.innerHTML = '<div class="card text-center">No candidates yet.</div>';
                    return;
                }
                container.innerHTML = candidates.map(c => `
                    <div class="card">
                        <h3>${escapeHtml(c.name || 'Unknown')}</h3>
                        ${c.email ? `<p><strong>📧 Email:</strong> ${escapeHtml(c.email)}</p>` : ''}
                        ${c.phone ? `<p><strong>📞 Phone:</strong> ${escapeHtml(c.phone)}</p>` : ''}
                        ${c.skills ? `<p><strong>🔧 Skills:</strong> ${c.skills.split(',').map(s => `<span class="skill-tag">${s.trim()}</span>`).join('')}</p>` : ''}
                        ${c.work_history ? `<p><strong>💼 Work History:</strong> ${escapeHtml(c.work_history)}</p>` : ''}
                        ${c.certifications ? `<p><strong>📜 Certifications:</strong> ${escapeHtml(c.certifications)}</p>` : ''}
                        <small>📅 Added: ${new Date(c.created_at).toLocaleDateString()}</small>
                    </div>
                `).join('');
            } catch (error) {
                document.getElementById('candidates-list').innerHTML = '<div class="alert-error">Error loading candidates</div>';
            }
        }
        
        async function exportToCSV() {
            window.location.href = '/api/export-candidates';
        }
        
        async function uploadResume() {
            const fileInput = document.getElementById('resume-file');
            const file = fileInput.files[0];
            if (!file) { alert('Please select a file'); return; }
            
            const formData = new FormData();
            formData.append('resume', file);
            
            const resultDiv = document.getElementById('parse-result');
            resultDiv.innerHTML = '<div class="spinner"></div><p class="text-center">Parsing resume...</p>';
            
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
                
                let aiBadge = result.ai_used ? '<span style="background:#27AE60; padding:2px 8px; border-radius:12px; margin-left:10px; font-size:12px;">🤖 AI</span>' : '';
                
                let jobSelector = '';
                if (jobsData.length > 0) {
                    jobSelector = `
                        <select id="job-select" style="margin: 15px 0; width: 100%; padding: 10px;">
                            <option value="">Select job for match score</option>
                            ${jobsData.map(job => `<option value="${job.id}">${job.title}</option>`).join('')}
                        </select>
                    `;
                }
                
                resultDiv.innerHTML = `
                    <div class="alert-success">
                        <h4>✅ Resume Parsed! ${aiBadge}</h4>
                        <p><strong>Name:</strong> ${escapeHtml(result.name || 'Not found')}</p>
                        <p><strong>Email:</strong> ${escapeHtml(result.email || 'Not found')}</p>
                        <p><strong>Phone:</strong> ${escapeHtml(result.phone || 'Not found')}</p>
                        <p><strong>Skills:</strong> ${result.skills ? result.skills.map(s => `<span class="skill-tag">${escapeHtml(s)}</span>`).join('') : 'None'}</p>
                        <p><strong>Work History:</strong> ${escapeHtml(result.work_history || 'None')}</p>
                        <p><strong>Certifications:</strong> ${escapeHtml(result.certifications || 'None')}</p>
                        ${jobSelector}
                        <button class="btn-primary" onclick='saveCandidateWithJob(${JSON.stringify(result).replace(/'/g, "\\'")})'>💾 Save Candidate</button>
                    </div>
                `;
            } catch (error) {
                resultDiv.innerHTML = '<div class="alert-error">Error parsing resume</div>';
            }
        }
        
        async function saveCandidateWithJob(candidateData) {
            const jobSelect = document.getElementById('job-select');
            const jobId = jobSelect ? jobSelect.value : null;
            const dataToSave = { ...candidateData };
            if (jobId) {
                dataToSave.job_id = parseInt(jobId);
            }
            
            try {
                const response = await fetch('/api/candidates', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify(dataToSave)
                });
                if (response.ok) {
                    alert('Candidate saved!');
                    document.getElementById('parse-result').innerHTML = '';
                    document.getElementById('resume-file').value = '';
                    loadCandidates();
                }
            } catch (error) {
                alert('Error saving');
            }
        }
        
        async function createJob(event) {
            event.preventDefault();
            const jobData = {
                title: document.getElementById('job-title').value,
                company: document.getElementById('job-company').value,
                description: document.getElementById('job-desc').value
            };
            if (!jobData.title) { alert('Job title required'); return; }
            
            const response = await fetch('/api/jobs', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify(jobData)
            });
            if (response.ok) {
                alert('Job created!');
                document.getElementById('job-title').value = '';
                document.getElementById('job-company').value = '';
                document.getElementById('job-desc').value = '';
                showTab('jobs');
                loadJobs();
            }
        }
        
        function escapeHtml(text) {
            if (!text) return '';
            const div = document.createElement('div');
            div.textContent = text;
            return div.innerHTML;
        }
        
        loadJobs();
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
    c.execute('''INSERT INTO jobs (title, company, description, required_skills) 
                 VALUES (?, ?, ?, ?)''',
              (data.get('title'), data.get('company'), description, skills_str))
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
    skills_str = ', '.join(data.get('skills', [])) if isinstance(data.get('skills'), list) else data.get('skills', '')
    
    conn = sqlite3.connect('shahnai.db')
    c = conn.cursor()
    c.execute('''INSERT INTO candidates (name, email, phone, skills, work_history, certifications, resume_text, job_id, match_score) 
                 VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)''',
              (data.get('name'), data.get('email'), data.get('phone'), skills_str,
               data.get('work_history'), data.get('certifications'), data.get('resume_text', ''),
               data.get('job_id'), data.get('match_score')))
    conn.commit()
    conn.close()
    return jsonify({'message': 'Candidate saved'})

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
    writer.writerow(['ID', 'Name', 'Email', 'Phone', 'Skills', 'Work History', 'Certifications', 'Match Score', 'Created Date'])
    for c in candidates:
        writer.writerow([c.get('id', ''), c.get('name', ''), c.get('email', ''), c.get('phone', ''), c.get('skills', ''), c.get('work_history', ''), c.get('certifications', ''), c.get('match_score', ''), c.get('created_at', '')])
    
    output.seek(0)
    return Response(output.getvalue(), mimetype='text/csv', headers={'Content-Disposition': 'attachment; filename=candidates_export.csv'})

@app.route('/api/parse-resume', methods=['POST'])
def parse_resume():
    if 'resume' not in request.files:
        return jsonify({'error': 'No file uploaded'}), 400
    
    file = request.files['resume']
    if file.filename == '':
        return jsonify({'error': 'No file selected'}), 400
    
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
