# app.py - Complete Working Version for ShahnaIT Scout
import os
import re
import sqlite3
from datetime import datetime
from flask import Flask, request, jsonify, render_template
from flask_cors import CORS
from werkzeug.utils import secure_filename
import PyPDF2
import docx

app = Flask(__name__)
CORS(app)

# Configuration
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB
app.config['UPLOAD_FOLDER'] = '/tmp'
ALLOWED_EXTENSIONS = {'pdf', 'docx'}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

# ============ DATABASE SETUP ============
def init_db():
    """Initialize SQLite database"""
    conn = sqlite3.connect('shahnai.db')
    c = conn.cursor()
    
    # Jobs table
    c.execute('''CREATE TABLE IF NOT EXISTS jobs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        title TEXT NOT NULL,
        company TEXT,
        description TEXT,
        requirements TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )''')
    
    # Candidates table
    c.execute('''CREATE TABLE IF NOT EXISTS candidates (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT,
        email TEXT,
        phone TEXT,
        skills TEXT,
        experience TEXT,
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

# ============ RESUME PARSING FUNCTIONS ============
def extract_text_from_pdf(file_path):
    """Extract text from PDF"""
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
    """Extract text from DOCX"""
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
    """Extract name from resume text"""
    lines = text.strip().split('\n')
    if lines and len(lines[0]) < 50 and len(lines[0]) > 2:
        return lines[0].strip()
    return "Unknown"

def extract_skills(text):
    """Extract skills from text"""
    common_skills = [
        'Python', 'Java', 'JavaScript', 'React', 'Angular', 'Vue', 'Node.js',
        'SQL', 'MongoDB', 'PostgreSQL', 'AWS', 'Docker', 'Kubernetes',
        'Machine Learning', 'AI', 'Data Science', 'Excel', 'Tableau',
        'Project Management', 'Agile', 'Scrum', 'Leadership', 'Communication',
        'Git', 'REST API', 'HTML', 'CSS', 'TypeScript', 'PHP', 'Ruby', 'C++', 'C#'
    ]
    found = []
    text_lower = text.lower()
    for skill in common_skills:
        if skill.lower() in text_lower:
            found.append(skill)
    return found

def parse_resume_file(file_path):
    """Main function to parse resume"""
    # Extract text based on file type
    if file_path.endswith('.pdf'):
        text = extract_text_from_pdf(file_path)
    elif file_path.endswith('.docx'):
        text = extract_text_from_docx(file_path)
    else:
        text = ""
    
    if not text:
        return {'error': 'Could not extract text from file'}
    
    return {
        'name': extract_name(text),
        'email': extract_email(text),
        'phone': extract_phone(text),
        'skills': extract_skills(text),
        'resume_text': text[:1000]
    }

# ============ HTML TEMPLATE ============
HTML_TEMPLATE = '''
<!DOCTYPE html>
<html>
<head>
    <title>ShahnaIT Scout - Recruitment Platform</title>
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }
        
        body {
            background-color: #F5F0E8;
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            color: #2C3E50;
        }
        
        .container {
            max-width: 1400px;
            margin: 0 auto;
            padding: 20px;
        }
        
        /* Header */
        .header {
            background: linear-gradient(135deg, #1A4D4A 0%, #0F3533 100%);
            color: white;
            padding: 30px;
            border-radius: 16px;
            margin-bottom: 30px;
            box-shadow: 0 4px 20px rgba(0,0,0,0.1);
        }
        
        .header h1 {
            font-size: 2em;
            margin-bottom: 10px;
        }
        
        /* Tabs */
        .tabs {
            display: flex;
            gap: 5px;
            margin-bottom: 30px;
            background: white;
            padding: 10px;
            border-radius: 12px;
            flex-wrap: wrap;
        }
        
        .tab-btn {
            background: transparent;
            border: none;
            padding: 12px 24px;
            font-size: 15px;
            cursor: pointer;
            color: #7F8C8D;
            border-radius: 8px;
            transition: all 0.3s;
        }
        
        .tab-btn:hover {
            background: #F5F0E8;
            color: #1A4D4A;
        }
        
        .tab-btn.active {
            background: #1A4D4A;
            color: white;
        }
        
        /* Cards */
        .card {
            background: white;
            border-radius: 12px;
            padding: 24px;
            margin-bottom: 20px;
            box-shadow: 0 2px 8px rgba(0,0,0,0.08);
            border-left: 4px solid #1A4D4A;
        }
        
        .card h3 {
            color: #1A4D4A;
            margin-bottom: 12px;
        }
        
        /* Buttons */
        .btn-primary {
            background: #1A4D4A;
            color: white;
            border: none;
            padding: 12px 24px;
            border-radius: 8px;
            cursor: pointer;
            font-size: 14px;
            font-weight: 600;
            transition: all 0.3s;
        }
        
        .btn-primary:hover {
            background: #2A6B67;
            transform: translateY(-1px);
        }
        
        /* Forms */
        input, textarea, select {
            width: 100%;
            padding: 12px;
            margin: 10px 0 15px 0;
            border: 1px solid #ddd;
            border-radius: 8px;
            font-size: 14px;
        }
        
        input:focus, textarea:focus {
            outline: none;
            border-color: #1A4D4A;
        }
        
        /* Alerts */
        .alert-success {
            background: #27AE60;
            color: white;
            padding: 14px;
            border-radius: 8px;
            margin: 10px 0;
        }
        
        .alert-error {
            background: #E74C3C;
            color: white;
            padding: 14px;
            border-radius: 8px;
            margin: 10px 0;
        }
        
        /* Spinner */
        .spinner {
            border: 3px solid #F5F0E8;
            border-top: 3px solid #1A4D4A;
            border-radius: 50%;
            width: 40px;
            height: 40px;
            animation: spin 0.8s linear infinite;
            margin: 20px auto;
        }
        
        @keyframes spin {
            0% { transform: rotate(0deg); }
            100% { transform: rotate(360deg); }
        }
        
        /* Match scores */
        .match-high { color: #27AE60; font-weight: bold; }
        .match-medium { color: #F39C12; font-weight: bold; }
        .match-low { color: #E74C3C; font-weight: bold; }
        
        /* Responsive */
        @media (max-width: 768px) {
            .container { padding: 10px; }
            .tab-btn { padding: 8px 16px; font-size: 13px; }
            .header h1 { font-size: 1.5em; }
        }
        
        .text-center { text-align: center; }
        .mt-20 { margin-top: 20px; }
        .mb-20 { margin-bottom: 20px; }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🎯 ShahnaIT Scout</h1>
            <p>Intelligent Recruitment Platform with Resume Parsing</p>
        </div>
        
        <div class="tabs">
            <button class="tab-btn active" onclick="showTab('jobs')">📋 Jobs</button>
            <button class="tab-btn" onclick="showTab('candidates')">👥 Candidates</button>
            <button class="tab-btn" onclick="showTab('upload')">📄 Upload Resume</button>
            <button class="tab-btn" onclick="showTab('create-job')">➕ Create Job</button>
        </div>
        
        <!-- Jobs Tab -->
        <div id="jobs-tab">
            <div id="jobs-list"></div>
        </div>
        
        <!-- Candidates Tab -->
        <div id="candidates-tab" style="display:none;">
            <div id="candidates-list"></div>
        </div>
        
        <!-- Upload Tab -->
        <div id="upload-tab" style="display:none;">
            <div class="card">
                <h3>📄 Upload Resume (PDF or DOCX)</h3>
                <p style="color:#666; margin-bottom:15px;">Upload a candidate's resume to extract name, email, phone, and skills.</p>
                <input type="file" id="resume-file" accept=".pdf,.docx">
                <button class="btn-primary" onclick="uploadResume()">🔍 Parse Resume</button>
                <div id="parse-result" class="mt-20"></div>
            </div>
        </div>
        
        <!-- Create Job Tab -->
        <div id="create-job-tab" style="display:none;">
            <div class="card">
                <h3>➕ Create New Job Posting</h3>
                <form onsubmit="createJob(event)">
                    <input type="text" id="job-title" placeholder="Job Title *" required>
                    <input type="text" id="job-company" placeholder="Company Name">
                    <textarea id="job-desc" rows="4" placeholder="Job Description"></textarea>
                    <textarea id="job-reqs" rows="4" placeholder="Requirements"></textarea>
                    <button type="submit" class="btn-primary">Create Job</button>
                </form>
            </div>
        </div>
    </div>
    
    <script>
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
                const jobs = await response.json();
                const container = document.getElementById('jobs-list');
                if (jobs.length === 0) {
                    container.innerHTML = '<div class="card text-center">No jobs yet. Create one using the "Create Job" tab.</div>';
                    return;
                }
                container.innerHTML = jobs.map(job => `
                    <div class="card">
                        <h3>${escapeHtml(job.title)}</h3>
                        ${job.company ? `<p><strong>Company:</strong> ${escapeHtml(job.company)}</p>` : ''}
                        ${job.description ? `<p>${escapeHtml(job.description.substring(0, 200))}${job.description.length > 200 ? '...' : ''}</p>` : ''}
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
                    container.innerHTML = '<div class="card text-center">No candidates yet. Upload resumes to add candidates.</div>';
                    return;
                }
                container.innerHTML = candidates.map(c => `
                    <div class="card">
                        <h3>${escapeHtml(c.name || 'Unknown')}</h3>
                        ${c.email ? `<p><strong>📧 Email:</strong> ${escapeHtml(c.email)}</p>` : ''}
                        ${c.phone ? `<p><strong>📞 Phone:</strong> ${escapeHtml(c.phone)}</p>` : ''}
                        ${c.skills ? `<p><strong>🔧 Skills:</strong> ${escapeHtml(c.skills)}</p>` : ''}
                        <small>📅 Added: ${new Date(c.created_at).toLocaleDateString()}</small>
                    </div>
                `).join('');
            } catch (error) {
                document.getElementById('candidates-list').innerHTML = '<div class="alert-error">Error loading candidates</div>';
            }
        }
        
        async function uploadResume() {
            const fileInput = document.getElementById('resume-file');
            const file = fileInput.files[0];
            if (!file) {
                alert('Please select a file');
                return;
            }
            
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
                
                resultDiv.innerHTML = `
                    <div class="alert-success">
                        <h4>✅ Resume Parsed Successfully!</h4>
                        <p><strong>Name:</strong> ${escapeHtml(result.name || 'Not found')}</p>
                        <p><strong>Email:</strong> ${escapeHtml(result.email || 'Not found')}</p>
                        <p><strong>Phone:</strong> ${escapeHtml(result.phone || 'Not found')}</p>
                        <p><strong>Skills:</strong> ${result.skills ? result.skills.join(', ') : 'None found'}</p>
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
        
        async function createJob(event) {
            event.preventDefault();
            const jobData = {
                title: document.getElementById('job-title').value,
                company: document.getElementById('job-company').value,
                description: document.getElementById('job-desc').value,
                requirements: document.getElementById('job-reqs').value
            };
            
            if (!jobData.title) {
                alert('Job title is required');
                return;
            }
            
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
    return HTML_TEMPLATE

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
    c.execute('INSERT INTO jobs (title, company, description, requirements) VALUES (?, ?, ?, ?)',
              (data.get('title'), data.get('company'), data.get('description'), data.get('requirements')))
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
    c.execute('''INSERT INTO candidates (name, email, phone, skills, resume_text) 
                 VALUES (?, ?, ?, ?, ?)''',
              (data.get('name'), data.get('email'), data.get('phone'), skills_str, data.get('resume_text', '')))
    conn.commit()
    conn.close()
    return jsonify({'message': 'Candidate saved'})

@app.route('/api/parse-resume', methods=['POST'])
def parse_resume():
    if 'resume' not in request.files:
        return jsonify({'error': 'No file uploaded'}), 400
    
    file = request.files['resume']
    if file.filename == '':
        return jsonify({'error': 'No file selected'}), 400
    
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
