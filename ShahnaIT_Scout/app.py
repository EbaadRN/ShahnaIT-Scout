from flask import Flask, render_template_string, jsonify, request, send_file
from datetime import datetime
import os
import re
import json
import base64
import io
from werkzeug.utils import secure_filename

app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'dev-secret-key')
app.config['MAX_CONTENT_LENGTH'] = 50 * 1024 * 1024
app.config['UPLOAD_FOLDER'] = 'uploads'
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

ALLOWED_EXTENSIONS = {'pdf', 'docx', 'doc', 'jpg', 'png', 'jpeg', 'txt'}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

# ============= GEMINI AI CONFIGURATION =============
GEMINI_AVAILABLE = False
gemini_model = None

# Try to load Gemini AI (optional - app works without it)
try:
    import google.generativeai as genai
    GEMINI_API_KEY = os.environ.get('GEMINI_API_KEY', '')
    if GEMINI_API_KEY:
        genai.configure(api_key=GEMINI_API_KEY)
        gemini_model = genai.GenerativeModel('gemini-pro')
        GEMINI_AVAILABLE = True
        print("=" * 50)
        print("Gemini AI: AVAILABLE")
        print("=" * 50)
    else:
        print("=" * 50)
        print("Gemini AI: NOT CONFIGURED - Add GEMINI_API_KEY to enable")
        print("Get free API key from: https://makersuite.google.com/app/apikey")
        print("=" * 50)
except ImportError:
    print("=" * 50)
    print("Gemini AI: NOT INSTALLED - Run: pip install google-generativeai")
    print("=" * 50)
except Exception as e:
    print(f"Gemini AI: ERROR - {e}")

# ============= DATA STORES =============
jobs = []
candidates = []
applications = []
interviews = []
offers = []
clients = []
next_id = 1

# ============= BASIC PARSING (ALWAYS WORKS) =============
def extract_text_from_file(file):
    text = ''
    filename = file.filename.lower()
    file.seek(0)
    if filename.endswith('.pdf'):
        try:
            import PyPDF2
            reader = PyPDF2.PdfReader(file)
            for page in reader.pages:
                page_text = page.extract_text()
                if page_text:
                    text += page_text
        except:
            text = ''
    elif filename.endswith('.docx'):
        try:
            import docx
            doc = docx.Document(file)
            text = '\n'.join([para.text for para in doc.paragraphs])
        except:
            text = ''
    else:
        try:
            text = file.read().decode('utf-8')
        except:
            text = ''
    return text

def parse_resume_basic(text):
    """Basic extraction - works 100% without AI"""
    import re
    result = {
        'first_name': '',
        'last_name': '',
        'email': '',
        'phone': '',
        'address': '',
        'linkedin_url': '',
        'current_role': '',
        'notice_period': None,
        'employment_status': '',
        'work_history': [],
        'certifications': [],
        'top_skills': []
    }
    
    # Extract email
    email_match = re.search(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b', text)
    if email_match:
        result['email'] = email_match.group(0)
    
    # Extract phone
    phone_match = re.search(r'\b\d{10}\b', text)
    if phone_match:
        result['phone'] = phone_match.group(0)
    
    # Extract name
    lines = text.split('\n')
    for line in lines[:5]:
        line = line.strip()
        if line and not any(x in line.lower() for x in ['resume', 'curriculum', 'email', 'phone']):
            parts = line.split()
            if len(parts) >= 2:
                result['first_name'] = parts[0]
                result['last_name'] = parts[1] if len(parts) > 1 else ''
                break
    
    # Extract current role
    role_keywords = ['developer', 'engineer', 'manager', 'lead', 'architect', 'analyst']
    for line in lines[:20]:
        for role in role_keywords:
            if role in line.lower():
                if len(line.split()) <= 8:
                    result['current_role'] = line.strip()
                    break
            if result['current_role']:
                break
        if result['current_role']:
            break
    
    # Extract skills
    skill_list = ['Python', 'Java', 'JavaScript', 'React', 'Angular', 'Vue', 'Node.js', 
                  'Django', 'Flask', 'Spring', 'AWS', 'Azure', 'Docker', 'Kubernetes',
                  'SQL', 'MongoDB', 'PostgreSQL', 'Git', 'Machine Learning', 'Data Science']
    found_skills = []
    for skill in skill_list:
        if skill.lower() in text.lower():
            found_skills.append(skill)
    result['top_skills'] = found_skills[:5]
    
    return result

# ============= GEMINI AI PARSING (OPTIONAL) =============
def parse_resume_with_gemini(text):
    """AI-powered resume parsing - returns None if fails"""
    if not GEMINI_AVAILABLE:
        return None
    try:
        prompt = f"""You are a professional resume parser. Extract information from this resume.

RESUME TEXT:
{text[:3500]}

Return ONLY valid JSON with these exact keys (no extra text, no markdown):
{{
    "first_name": "",
    "last_name": "",
    "email": "",
    "phone": "",
    "address": "",
    "linkedin_url": "",
    "current_role": "",
    "notice_period": null,
    "employment_status": "",
    "work_history": [],
    "certifications": [],
    "top_skills": []
}}

For work_history, use array of objects with: company, role, duration_from, duration_to
For top_skills, use array of 5 skills as "skill: years"

If information not found, use empty string or null."""
        
        response = gemini_model.generate_content(prompt)
        json_str = response.text
        # Clean markdown
        json_str = re.sub(r'```json\n?', '', json_str)
        json_str = re.sub(r'```\n?', '', json_str)
        return json.loads(json_str)
    except Exception as e:
        print(f"Gemini parsing error: {e}")
        return None

def analyze_profile_with_gemini(candidate_data, job_data):
    """AI analysis: relevance score and genuineness check"""
    if not GEMINI_AVAILABLE:
        return None
    
    prompt = f"""You are an expert recruitment analyst. Analyze this candidate profile against the job requirement.

CANDIDATE PROFILE:
- Name: {candidate_data.get('name', '')}
- Current Role: {candidate_data.get('current_role', '')}
- Skills: {candidate_data.get('skills', '')}
- Experience: {candidate_data.get('total_experience', 0)} years
- Work History: {candidate_data.get('work_history', [])}

JOB REQUIREMENT:
- Title: {job_data.get('title', '')}
- Required Skills: {job_data.get('skills_required', '')}
- Experience Needed: {job_data.get('experience_min', 0)}-{job_data.get('experience_max', 10)} years

Return ONLY valid JSON:
{{
    "relevance_score": 0-100,
    "relevance_reason": "brief explanation",
    "genuineness_score": 0-100,
    "genuineness_reason": "brief explanation",
    "strengths": ["strength1", "strength2"],
    "weaknesses": ["weakness1", "weakness2"],
    "recommendation": "Hire/Interview/Reject"
}}

Be honest and critical."""
    
    try:
        response = gemini_model.generate_content(prompt)
        json_str = response.text
        json_str = re.sub(r'```json\n?', '', json_str)
        json_str = re.sub(r'```\n?', '', json_str)
        return json.loads(json_str)
    except Exception as e:
        print(f"Analysis error: {e}")
        return None

def parse_jd_with_gemini(text):
    """AI-powered JD parsing"""
    if not GEMINI_AVAILABLE:
        return None
    try:
        prompt = f"""Extract information from this job description.

JD TEXT:
{text[:3500]}

Return ONLY valid JSON:
{{
    "job_title": "",
    "experience_min": 0,
    "experience_max": 5,
    "budget_min": null,
    "budget_max": null,
    "work_location": "",
    "work_location_city": "",
    "responsibilities": [],
    "mandatory_skills": [],
    "preferred_skills": [],
    "good_to_have_skills": [],
    "education_qualification": "",
    "work_timings": "",
    "number_of_openings": 1
}}

If not found, use empty string, null, or []."""
        
        response = gemini_model.generate_content(prompt)
        json_str = response.text
        json_str = re.sub(r'```json\n?', '', json_str)
        json_str = re.sub(r'```\n?', '', json_str)
        return json.loads(json_str)
    except Exception as e:
        print(f"JD parsing error: {e}")
        return None

def parse_jd_basic(text):
    """Basic JD extraction - always works"""
    import re
    result = {
        'job_title': '',
        'experience_min': 0,
        'experience_max': 5,
        'budget_min': None,
        'budget_max': None,
        'work_location': 'Remote',
        'work_location_city': '',
        'responsibilities': [],
        'mandatory_skills': [],
        'preferred_skills': [],
        'good_to_have_skills': [],
        'education_qualification': '',
        'work_timings': '',
        'number_of_openings': 1
    }
    
    lines = text.split('\n')
    for line in lines[:10]:
        if any(word in line.lower() for word in ['developer', 'engineer', 'manager', 'lead']):
            if len(line.split()) <= 8:
                result['job_title'] = line.strip()
                break
    
    exp_match = re.search(r'(\d+)\s*-\s*(\d+)\s*years?', text.lower())
    if exp_match:
        result['experience_min'] = int(exp_match.group(1))
        result['experience_max'] = int(exp_match.group(2))
    
    skill_list = ['Python', 'Java', 'JavaScript', 'React', 'AWS', 'Docker', 'SQL']
    found = []
    for skill in skill_list:
        if skill.lower() in text.lower():
            found.append(skill)
    result['mandatory_skills'] = found
    
    return result

def calculate_match_score(job_skills, candidate_skills):
    if not job_skills or not candidate_skills:
        return 0
    job_list = [s.strip().lower() for s in job_skills.split(',') if s.strip()]
    cand_list = [s.strip().lower() for s in candidate_skills.split(',') if s.strip()]
    if not job_list:
        return 0
    matches = sum(1 for s in job_list if s in cand_list)
    return round((matches / len(job_list)) * 100, 2)

# ============= API ROUTES =============

@app.route('/api/gemini/status', methods=['GET'])
def gemini_status():
    return jsonify({
        'available': GEMINI_AVAILABLE,
        'message': 'Gemini AI is ready' if GEMINI_AVAILABLE else 'Gemini AI not configured. Add GEMINI_API_KEY to enable.'
    })

@app.route('/api/candidates/parse-with-gemini', methods=['POST'])
def parse_candidate_with_gemini():
    if 'file' not in request.files:
        return jsonify({'error': 'No file uploaded'}), 400
    
    file = request.files['file']
    text = extract_text_from_file(file)
    
    if not text:
        return jsonify({'error': 'Could not extract text from file'}), 400
    
    # Try Gemini first
    gemini_result = parse_resume_with_gemini(text)
    if gemini_result:
        return jsonify({
            'success': True, 
            'data': gemini_result, 
            'method': 'gemini_ai',
            'ai_available': True
        })
    
    # Fallback to basic
    basic_result = parse_resume_basic(text)
    return jsonify({
        'success': True, 
        'data': basic_result, 
        'method': 'basic',
        'ai_available': False,
        'message': 'Gemini AI not available. Using basic extraction.'
    })

@app.route('/api/analyze/profile', methods=['POST'])
def analyze_profile():
    data = request.json
    candidate_id = data.get('candidate_id')
    job_id = data.get('job_id')
    
    candidate = next((c for c in candidates if c['id'] == candidate_id), None)
    job = next((j for j in jobs if j['id'] == job_id), None)
    
    if not candidate or not job:
        return jsonify({'error': 'Candidate or job not found'}), 404
    
    analysis = analyze_profile_with_gemini(candidate, job)
    
    if analysis:
        return jsonify({'success': True, 'analysis': analysis, 'ai_available': True})
    else:
        # Fallback basic analysis
        match_score = calculate_match_score(job.get('skills_required', ''), candidate.get('skills', ''))
        return jsonify({
            'success': True, 
            'analysis': {
                'relevance_score': match_score,
                'relevance_reason': 'Based on skill matching',
                'genuineness_score': 75,
                'genuineness_reason': 'Profile appears consistent',
                'strengths': ['Skills match requirements'],
                'weaknesses': [],
                'recommendation': 'Interview' if match_score > 60 else 'Review'
            },
            'ai_available': False
        })

@app.route('/api/jobs/parse-with-gemini', methods=['POST'])
def parse_job_with_gemini():
    data = request.json
    jd_text = data.get('jd_text', '')
    
    if not jd_text:
        return jsonify({'error': 'No JD text provided'}), 400
    
    gemini_result = parse_jd_with_gemini(jd_text)
    if gemini_result:
        return jsonify({'success': True, 'data': gemini_result, 'method': 'gemini_ai'})
    
    basic_result = parse_jd_basic(jd_text)
    return jsonify({'success': True, 'data': basic_result, 'method': 'basic'})
# ============= DASHBOARD HTML TEMPLATE =============
DASHBOARD_TEMPLATE = '''
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>ShahnaIT Scout - Recruitment Suite</title>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.1.3/dist/css/bootstrap.min.css" rel="stylesheet">
    <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/bootstrap-icons@1.8.1/font/bootstrap-icons.css">
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body { font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; background: #F5F2EB; }
        
        .sidebar {
            position: fixed;
            left: 0;
            top: 0;
            width: 280px;
            height: 100vh;
            background: #0D3B3F;
            color: white;
            overflow-y: auto;
            z-index: 1000;
        }
        .sidebar .logo { padding: 25px; text-align: center; border-bottom: 1px solid rgba(255,255,255,0.1); }
        .sidebar .logo h3 { font-size: 1.6rem; font-weight: 700; }
        .sidebar .logo p { font-size: 0.75rem; opacity: 0.7; }
        .sidebar .nav-item {
            padding: 14px 25px;
            margin: 5px 0;
            cursor: pointer;
            display: flex;
            align-items: center;
            gap: 12px;
            transition: all 0.3s;
            border-left: 3px solid transparent;
        }
        .sidebar .nav-item:hover { background: rgba(255,255,255,0.1); }
        .sidebar .nav-item.active { background: rgba(255,255,255,0.15); border-left-color: #D4A574; }
        .sidebar .nav-item i { font-size: 1.2rem; width: 25px; }
        
        .main-content { margin-left: 280px; padding: 25px 35px; min-height: 100vh; }
        .page-header { margin-bottom: 30px; }
        .page-header h1 { font-size: 1.8rem; font-weight: 600; color: #0D3B3F; }
        .page-header p { color: #6c757d; font-size: 0.9rem; }
        
        .stats-grid { display: grid; grid-template-columns: repeat(4, 1fr); gap: 25px; margin-bottom: 35px; }
        .stat-card {
            background: white;
            border-radius: 16px;
            padding: 20px;
            transition: all 0.3s;
            cursor: pointer;
            border: 1px solid #e8e0d5;
        }
        .stat-card:hover { transform: translateY(-5px); box-shadow: 0 8px 25px rgba(0,0,0,0.1); }
        .stat-icon { width: 50px; height: 50px; border-radius: 12px; display: flex; align-items: center; justify-content: center; font-size: 1.6rem; margin-bottom: 15px; }
        .stat-value { font-size: 2rem; font-weight: 700; color: #0D3B3F; }
        .stat-label { color: #8b7d6b; font-size: 0.85rem; }
        
        .btn-teal { background: #0D3B3F; border: none; padding: 10px 22px; border-radius: 30px; color: white; }
        .btn-teal:hover { background: #1a5a5f; }
        .btn-beige { background: #D4A574; border: none; padding: 10px 22px; border-radius: 30px; color: white; }
        .btn-beige:hover { background: #c49a6c; }
        .btn-outline-teal { background: transparent; border: 1px solid #0D3B3F; padding: 10px 22px; border-radius: 30px; color: #0D3B3F; }
        .btn-outline-teal:hover { background: #0D3B3F; color: white; }
        
        .modern-table { background: white; border-radius: 16px; overflow: hidden; border: 1px solid #e8e0d5; }
        .modern-table th { background: #F5F2EB; padding: 15px 20px; color: #0D3B3F; }
        .modern-table td { padding: 12px 20px; border-bottom: 1px solid #f0ebe4; }
        
        .candidate-name { color: #0D3B3F; cursor: pointer; font-weight: 600; }
        .candidate-name:hover { text-decoration: underline; color: #D4A574; }
        
        .badge-open { background: #4caf50; color: white; padding: 4px 12px; border-radius: 20px; font-size: 0.7rem; }
        .badge-closed { background: #f44336; color: white; padding: 4px 12px; border-radius: 20px; font-size: 0.7rem; }
        .badge-draft { background: #ff9800; color: white; padding: 4px 12px; border-radius: 20px; font-size: 0.7rem; }
        
        .modal-modern .modal-content { border-radius: 20px; border: none; }
        .modal-modern .modal-header { background: #0D3B3F; color: white; border-radius: 20px 20px 0 0; padding: 18px 25px; }
        
        .work-history-table { width: 100%; border-collapse: collapse; margin-top: 10px; }
        .work-history-table th, .work-history-table td { border: 1px solid #dee2e6; padding: 8px; text-align: left; }
        .work-history-table th { background: #f8f9fa; }
        
        .doc-list { list-style: none; padding: 0; }
        .doc-list li { padding: 8px; border-bottom: 1px solid #eee; display: flex; justify-content: space-between; }
        
        .ai-badge { background: linear-gradient(135deg, #667eea, #764ba2); color: white; padding: 2px 8px; border-radius: 12px; font-size: 0.7rem; margin-left: 8px; }
        
        @media (max-width: 1000px) { .stats-grid { grid-template-columns: repeat(2, 1fr); } }
        @media (max-width: 768px) { .sidebar { left: -280px; } .main-content { margin-left: 0; } .stats-grid { grid-template-columns: 1fr; } }
    </style>
</head>
<body>
    <div class="sidebar">
        <div class="logo">
            <h3><i class="bi bi-robot"></i> ShahnaIT</h3>
            <p>Recruitment Suite</p>
        </div>
        <div class="nav-item active" data-page="dashboard"><i class="bi bi-speedometer2"></i> Dashboard</div>
        <div class="nav-item" data-page="jobs"><i class="bi bi-briefcase"></i> Jobs</div>
        <div class="nav-item" data-page="candidates"><i class="bi bi-people"></i> Candidates</div>
        <div class="nav-item" data-page="applications"><i class="bi bi-file-check"></i> Applications</div>
        <div class="nav-item" data-page="interviews"><i class="bi bi-calendar-check"></i> Interviews</div>
        <div class="nav-item" data-page="offers"><i class="bi bi-envelope-paper"></i> Offers</div>
        <div class="nav-item" data-page="clients"><i class="bi bi-building"></i> Clients</div>
        <div class="nav-item" data-page="aitools"><i class="bi bi-stars"></i> AI Tools</div>
    </div>
    
    <div class="main-content">
        <!-- Dashboard Page -->
        <div id="dashboardPage">
            <div class="page-header"><h1>Recruitment Dashboard</h1><p>Track your hiring pipeline</p></div>
            <div class="stats-grid" id="statsGrid">
                <div class="stat-card"><div class="stat-icon" style="background:#0D3B3F20;color:#0D3B3F;"><i class="bi bi-briefcase"></i></div><div class="stat-value" id="openPositions">0</div><div class="stat-label">Open Positions</div></div>
                <div class="stat-card"><div class="stat-icon" style="background:#D4A57420;color:#D4A574;"><i class="bi bi-people"></i></div><div class="stat-value" id="totalCandidates">0</div><div class="stat-label">Total Candidates</div></div>
                <div class="stat-card"><div class="stat-icon" style="background:#0D3B3F20;color:#0D3B3F;"><i class="bi bi-calendar-check"></i></div><div class="stat-value" id="interviewsToday">0</div><div class="stat-label">Interviews Today</div></div>
                <div class="stat-card"><div class="stat-icon" style="background:#D4A57420;color:#D4A574;"><i class="bi bi-envelope-paper"></i></div><div class="stat-value" id="offersSent">0</div><div class="stat-label">Offers Sent</div></div>
            </div>
            <div class="row mt-3"><div class="col-md-12">
                <div class="card p-3"><h5>Quick Actions</h5>
                <div class="d-flex gap-3 flex-wrap">
                    <button class="btn-teal" onclick="openJobModal()">Create Job</button>
                    <button class="btn-beige" onclick="openCandidateModal()">Add Candidate</button>
                    <button class="btn-outline-teal" onclick="openResumeUploadModal()">Upload Resume</button>
                    <button class="btn-teal" onclick="openClientModal()">Add Client</button>
                </div></div>
            </div></div>
        </div>
        
        <!-- Jobs Page -->
        <div id="jobsPage" style="display: none;">
            <div class="page-header"><h1>Job Descriptions</h1></div>
            <div class="d-flex gap-2 mb-3">
                <button class="btn-teal" onclick="openJobModal()">Create Job</button>
                <button class="btn-beige" onclick="openJDUploadModal()">Upload JD</button>
                <button class="btn-outline-teal" onclick="openJDPasteModal()">Paste JD Text</button>
            </div>
            <div class="modern-table"><table class="table"><thead><tr><th>ID</th><th>Title</th><th>Client</th><th>Location</th><th>Experience</th><th>Status</th><th>Actions</th></tr></thead><tbody id="jobsTable"></tbody></table></div>
        </div>
        
        <!-- Candidates Page -->
        <div id="candidatesPage" style="display: none;">
            <div class="page-header"><h1>Candidates Database</h1></div>
            <div class="row mb-3">
                <div class="col-md-4"><input type="text" class="form-control" id="candidateSearch" placeholder="Search by skill (e.g., Java Developer)"></div>
                <div class="col-md-2"><button class="btn-teal" onclick="searchCandidates()">Search</button></div>
                <div class="col-md-2"><button class="btn-beige" onclick="openCandidateModal()">Add Candidate</button></div>
                <div class="col-md-2"><button class="btn-outline-teal" onclick="openResumeUploadModal()">Upload Resume</button></div>
            </div>
            <div class="modern-table"><table class="table"><thead><tr><th>ID</th><th>Name</th><th>Email</th><th>Current Role</th><th>Top Skills</th><th>Actions</th></tr></thead><tbody id="candidatesTable"></tbody></table></div>
        </div>
        
        <!-- Applications Page -->
        <div id="applicationsPage" style="display: none;">
            <div class="page-header"><h1>Applications</h1></div>
            <div class="modern-table"><table class="table"><thead><tr><th>ID</th><th>Candidate</th><th>Job</th><th>Match Score</th><th>Status</th><th>Actions</th></tr></thead><tbody id="applicationsTable"></tbody></table></div>
        </div>
        
        <!-- Interviews Page -->
        <div id="interviewsPage" style="display: none;">
            <div class="page-header"><h1>Interviews</h1></div>
            <div class="modern-table"><table class="table"><thead><tr><th>ID</th><th>Candidate</th><th>Job</th><th>Interviewer</th><th>Date</th><th>Status</th></tr></thead><tbody id="interviewsTable"></tbody></td></div>
        </div>
        
        <!-- Offers Page -->
        <div id="offersPage" style="display: none;">
            <div class="page-header"><h1>Offer Letters</h1></div>
            <div class="modern-table"><table class="table"><thead><tr><th>ID</th><th>Candidate</th><th>Job</th><th>Salary</th><th>Status</th></tr></thead><tbody id="offersTable"></tbody></table></div>
        </div>
        
        <!-- Clients Page -->
        <div id="clientsPage" style="display: none;">
            <div class="page-header"><h1>Clients</h1></div>
            <button class="btn-teal mb-3" onclick="openClientModal()">Add Client</button>
            <div class="modern-table"><table class="table"><thead><tr><th>ID</th><th>Company</th><th>Contact</th><th>Email</th><th>JDs</th><th>Actions</th></tr></thead><tbody id="clientsTable"></tbody></table></div>
        </div>
        
        <!-- AI Tools Page -->
        <div id="aitoolsPage" style="display: none;">
            <div class="page-header"><h1>AI Tools</h1><p>Powered by Gemini AI</p></div>
            <div class="row">
                <div class="col-md-6">
                    <div class="card mb-3"><div class="card-header bg-primary text-white">Resume Parsing</div>
                    <div class="card-body"><input type="file" class="form-control" id="aiResumeFile" accept=".pdf,.docx"><button class="btn-teal mt-2" onclick="parseWithAI()">Parse with AI</button><div id="aiResult" class="mt-3"></div></div></div>
                </div>
                <div class="col-md-6">
                    <div class="card mb-3"><div class="card-header bg-primary text-white">Profile Analysis</div>
                    <div class="card-body"><select class="form-select mb-2" id="analyzeCandidateId"><option value="">Select Candidate</option></select><select class="form-select mb-2" id="analyzeJobId"><option value="">Select Job</option></select><button class="btn-teal" onclick="analyzeProfile()">Analyze Match</button><div id="analysisResult" class="mt-3"></div></div></div>
                </div>
            </div>
            <div class="card"><div class="card-header bg-primary text-white">Gemini Status</div>
            <div class="card-body" id="geminiStatus">Checking...</div></div>
        </div>
    </div>
    
    <!-- Job Modal -->
    <div class="modal fade modal-modern" id="jobModal" tabindex="-1"><div class="modal-dialog"><div class="modal-content"><div class="modal-header"><h5 class="modal-title">Create Job</h5><button type="button" class="btn-close btn-close-white" data-bs-dismiss="modal"></button></div><div class="modal-body"><input type="text" class="form-control mb-2" id="jobTitle" placeholder="Job Title"><input type="text" class="form-control mb-2" id="jobLocation" placeholder="Location"><select class="form-select mb-2" id="jobClientId"><option value="">Select Client</option></select><textarea class="form-control mb-2" id="jobSkills" rows="3" placeholder="Required Skills (comma separated)"></textarea><input type="number" class="form-control mb-2" id="jobExpMin" placeholder="Min Experience"><input type="number" class="form-control mb-2" id="jobExpMax" placeholder="Max Experience"><select class="form-select mb-2" id="jobStatus"><option value="open">Open</option><option value="closed">Closed</option></select><button class="btn-teal w-100" onclick="createJob()">Create Job</button></div></div></div></div>
    
    <!-- Candidate Modal -->
    <div class="modal fade modal-modern" id="candidateModal" tabindex="-1"><div class="modal-dialog modal-lg"><div class="modal-content"><div class="modal-header"><h5 class="modal-title">Add Candidate</h5><button type="button" class="btn-close btn-close-white" data-bs-dismiss="modal"></button></div><div class="modal-body"><div class="row"><div class="col-md-6"><input type="text" class="form-control mb-2" id="candFirstName" placeholder="First Name"></div><div class="col-md-6"><input type="text" class="form-control mb-2" id="candLastName" placeholder="Last Name"></div><div class="col-md-6"><input type="email" class="form-control mb-2" id="candEmail" placeholder="Email"></div><div class="col-md-6"><input type="text" class="form-control mb-2" id="candPhone" placeholder="Phone"></div><div class="col-md-12"><textarea class="form-control mb-2" id="candSkills" rows="2" placeholder="Skills (comma separated)"></textarea></div><div class="col-md-6"><input type="text" class="form-control mb-2" id="candCurrentRole" placeholder="Current Role"></div><div class="col-md-6"><input type="number" class="form-control mb-2" id="candExperience" placeholder="Experience (years)"></div><div class="col-md-12"><label>Work History</label><div id="workHistoryContainer"></div><button type="button" class="btn btn-sm btn-outline-primary mt-1" onclick="addWorkHistoryRow()">+ Add Company</button></div><div class="col-md-12 mt-2"><label>Certifications</label><div id="certificationsContainer"></div><button type="button" class="btn btn-sm btn-outline-primary mt-1" onclick="addCertificationRow()">+ Add Certification</button></div></div><button class="btn-beige w-100 mt-3" onclick="createCandidate()">Save Candidate</button></div></div></div></div>
    
    <!-- Resume Upload Modal -->
    <div class="modal fade modal-modern" id="resumeUploadModal" tabindex="-1"><div class="modal-dialog"><div class="modal-content"><div class="modal-header"><h5 class="modal-title">Upload Resume</h5><button type="button" class="btn-close btn-close-white" data-bs-dismiss="modal"></button></div><div class="modal-body"><input type="file" class="form-control" id="resumeFile" accept=".pdf,.docx"><div id="resumeProgress" class="mt-2" style="display:none"><div class="spinner-border spinner-border-sm"></div> Parsing...</div><div id="resumeResult" class="mt-3" style="display:none"><pre id="resumeData" class="bg-light p-2 rounded small"></pre><button class="btn-teal w-100 mt-2" onclick="createCandidateFromResume()">Create Candidate</button></div><button class="btn-beige w-100 mt-2" onclick="uploadAndParseResume()">Parse Resume</button></div></div></div></div>
    
    <!-- JD Upload Modal -->
    <div class="modal fade modal-modern" id="jdUploadModal" tabindex="-1"><div class="modal-dialog"><div class="modal-content"><div class="modal-header"><h5 class="modal-title">Upload JD Document</h5><button type="button" class="btn-close btn-close-white" data-bs-dismiss="modal"></button></div><div class="modal-body"><input type="file" class="form-control" id="jdFile" accept=".pdf,.docx,.txt"><div id="jdProgress" class="mt-2" style="display:none"><div class="spinner-border spinner-border-sm"></div> Processing...</div><div id="jdResult" class="mt-3" style="display:none"><pre id="jdData" class="bg-light p-2 rounded small"></pre><button class="btn-teal w-100 mt-2" onclick="createJobFromParsedJD()">Create Job</button></div><button class="btn-beige w-100" onclick="uploadAndParseJD()">Parse JD</button></div></div></div></div>
    
    <!-- JD Paste Modal -->
    <div class="modal fade modal-modern" id="jdPasteModal" tabindex="-1"><div class="modal-dialog modal-lg"><div class="modal-content"><div class="modal-header"><h5 class="modal-title">Paste JD Text</h5><button type="button" class="btn-close btn-close-white" data-bs-dismiss="modal"></button></div><div class="modal-body"><textarea class="form-control" id="jdPasteText" rows="10" placeholder="Paste job description here..."></textarea><div id="jdPasteProgress" class="mt-2" style="display:none"><div class="spinner-border spinner-border-sm"></div> Analyzing...</div><div id="jdPasteResult" class="mt-3" style="display:none"><pre id="jdPasteData" class="bg-light p-2 rounded small"></pre><button class="btn-teal w-100 mt-2" onclick="createJobFromParsedJDPaste()">Create Job</button></div><button class="btn-beige w-100 mt-2" onclick="parsePastedJD()">Analyze JD</button></div></div></div></div>
    
    <!-- Client Modal -->
    <div class="modal fade modal-modern" id="clientModal" tabindex="-1"><div class="modal-dialog"><div class="modal-content"><div class="modal-header"><h5 class="modal-title">Add Client</h5><button type="button" class="btn-close btn-close-white" data-bs-dismiss="modal"></button></div><div class="modal-body"><input type="text" class="form-control mb-2" id="clientName" placeholder="Company Name"><input type="text" class="form-control mb-2" id="clientContact" placeholder="Contact Person"><input type="email" class="form-control mb-2" id="clientEmail" placeholder="Email"><input type="text" class="form-control mb-2" id="clientPhone" placeholder="Phone"><button class="btn-teal w-100" onclick="createClient()">Add Client</button></div></div></div></div>
    
    <!-- Candidate Profile Modal -->
    <div class="modal fade modal-modern" id="candidateProfileModal" tabindex="-1"><div class="modal-dialog modal-lg"><div class="modal-content"><div class="modal-header"><h5 class="modal-title">Candidate Profile</h5><button type="button" class="btn-close btn-close-white" data-bs-dismiss="modal"></button></div><div class="modal-body" id="candidateProfileContent"></div></div></div></div>
    
    <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.1.3/dist/js/bootstrap.bundle.min.js"></script>
    <script>
        let parsedResumeData = null;
        let parsedJDData = null;
        
        // Navigation
        document.querySelectorAll('.nav-item').forEach(item => {
            item.addEventListener('click', function() {
                document.querySelectorAll('.nav-item').forEach(n => n.classList.remove('active'));
                this.classList.add('active');
                var pages = ['dashboard', 'jobs', 'candidates', 'applications', 'interviews', 'offers', 'clients', 'aitools'];
                pages.forEach(function(p) {
                    var el = document.getElementById(p + 'Page');
                    if (el) el.style.display = 'none';
                });
                var pageName = this.getAttribute('data-page');
                var activePage = document.getElementById(pageName + 'Page');
                if (activePage) activePage.style.display = 'block';
                if (pageName === 'dashboard') loadDashboard();
                if (pageName === 'jobs') loadJobs();
                if (pageName === 'candidates') loadCandidates();
                if (pageName === 'applications') loadApplications();
                if (pageName === 'interviews') loadInterviews();
                if (pageName === 'offers') loadOffers();
                if (pageName === 'clients') loadClients();
                if (pageName === 'aitools') loadAITools();
            });
        });
        
        async function loadDashboard() {
            try {
                var res = await fetch('/api/dashboard/stats');
                var data = await res.json();
                document.getElementById('openPositions').innerText = data.open_positions || 0;
                document.getElementById('totalCandidates').innerText = data.total_candidates || 0;
                document.getElementById('interviewsToday').innerText = data.interviews_today || 0;
                document.getElementById('offersSent').innerText = data.offers_sent || 0;
            } catch(e) { console.log(e); }
        }
        
        async function loadJobs() {
            try {
                var res = await fetch('/api/jobs');
                var jobs = await res.json();
                var tbody = document.getElementById('jobsTable');
                if (jobs.length === 0) { tbody.innerHTML = '<tr><td colspan="7" class="text-center">No jobs created</td></tr>'; return; }
                var html = '';
                for (var i = 0; i < jobs.length; i++) {
                    var j = jobs[i];
                    html += '<tr><td>' + j.id + '</td><td>' + j.title + '</td><td>' + (j.client_name || '-') + '</td><td>' + (j.location || 'Remote') + '</td><td>' + (j.experience_min || 0) + '-' + (j.experience_max || 5) + ' yrs</td><td><span class="badge-open">' + j.status + '</span></td><td><button class="btn-teal btn-sm" onclick="createApplicationForJob(' + j.id + ')">Apply</button></td></tr>';
                }
                tbody.innerHTML = html;
            } catch(e) { console.log(e); }
        }
        
        async function loadCandidates() {
            try {
                var res = await fetch('/api/candidates');
                var data = await res.json();
                var tbody = document.getElementById('candidatesTable');
                if (data.candidates.length === 0) { tbody.innerHTML = '<tr><td colspan="6" class="text-center">No candidates added</td></tr>'; return; }
                var html = '';
                for (var i = 0; i < data.candidates.length; i++) {
                    var c = data.candidates[i];
                    html += '<tr><td>' + c.id + '</td><td><span class="candidate-name" onclick="viewCandidateProfile(' + c.id + ')">' + c.name + '</span></td><td>' + c.email + '</td><td>' + (c.current_role || '-') + '</td><td>' + (c.top_skills || c.skills || '-') + '</td><td><button class="btn-beige btn-sm" onclick="createApplicationForCandidate(' + c.id + ')">Apply</button></td></tr>';
                }
                tbody.innerHTML = html;
            } catch(e) { console.log(e); }
        }
        
        async function loadApplications() {
            try {
                var res = await fetch('/api/applications');
                var apps = await res.json();
                var tbody = document.getElementById('applicationsTable');
                if (apps.length === 0) { tbody.innerHTML = '<tr><td colspan="6" class="text-center">No applications</td></tr>'; return; }
                var html = '';
                for (var i = 0; i < apps.length; i++) {
                    var a = apps[i];
                    var badgeClass = a.match_score >= 70 ? 'badge-open' : (a.match_score >= 50 ? 'badge-draft' : 'badge-closed');
                    html += '<tr><td>' + a.id + '</td><td>' + (a.candidate_name || '-') + '</td><td>' + (a.job_title || '-') + '</td><td><span class="' + badgeClass + '">' + (a.match_score || 0) + '%</span></td><td>' + a.status + '</td><td><button class="btn-outline-teal btn-sm" onclick="moveApplication(' + a.id + ')">Move</button></td></tr>';
                }
                tbody.innerHTML = html;
            } catch(e) { console.log(e); }
        }
        
        async function loadInterviews() {
            try {
                var res = await fetch('/api/interviews');
                var interviews = await res.json();
                var tbody = document.getElementById('interviewsTable');
                if (interviews.length === 0) { tbody.innerHTML = '<tr><td colspan="6" class="text-center">No interviews scheduled</td></tr>'; return; }
                var html = '';
                for (var i = 0; i < interviews.length; i++) {
                    var iv = interviews[i];
                    html += '<tr><td>' + iv.id + '</td><td>' + iv.candidate_name + '</td><td>' + iv.job_title + '</td><td>' + (iv.interviewer_name || 'TBD') + '</td><td>' + (iv.scheduled_time || 'TBD') + '</td><td>' + iv.status + '</td></tr>';
                }
                tbody.innerHTML = html;
            } catch(e) { console.log(e); }
        }
        
        async function loadOffers() {
            try {
                var res = await fetch('/api/offers');
                var offers = await res.json();
                var tbody = document.getElementById('offersTable');
                if (offers.length === 0) { tbody.innerHTML = '<tr><td colspan="5" class="text-center">No offers generated</td></tr>'; return; }
                var html = '';
                for (var i = 0; i < offers.length; i++) {
                    var o = offers[i];
                    html += '<tr><td>' + o.id + '</td><td>' + o.candidate_name + '</td><td>' + o.job_title + '</td><td>$' + (o.base_salary || 0) + '</td><td>' + o.status + '</td></tr>';
                }
                tbody.innerHTML = html;
            } catch(e) { console.log(e); }
        }
        
        async function loadClients() {
            try {
                var res = await fetch('/api/clients');
                var clients = await res.json();
                var tbody = document.getElementById('clientsTable');
                if (clients.length === 0) { tbody.innerHTML = '<tr><td colspan="6" class="text-center">No clients added</td></tr>'; return; }
                var html = '';
                for (var i = 0; i < clients.length; i++) {
                    var cl = clients[i];
                    html += '<tr><td>' + cl.id + '</td><td>' + cl.name + '</td><td>' + (cl.contact_person || '-') + '</td><td>' + cl.email + '</td><td>' + (cl.jd_count || 0) + '</td><td><button class="btn-teal btn-sm" onclick="viewClientJDs(' + cl.id + ')">View JDs</button></td></tr>';
                }
                tbody.innerHTML = html;
            } catch(e) { console.log(e); }
        }
        
        async function loadAITools() {
            var statusDiv = document.getElementById('geminiStatus');
            try {
                var res = await fetch('/api/gemini/status');
                var data = await res.json();
                if (data.available) {
                    statusDiv.innerHTML = '<div class="alert alert-success"><i class="bi bi-check-circle"></i> Gemini AI is AVAILABLE! <br>You can use AI resume parsing, JD analysis, and profile matching.</div>';
                } else {
                    statusDiv.innerHTML = '<div class="alert alert-warning"><i class="bi bi-exclamation-triangle"></i> Gemini AI is NOT configured.<br>Add GEMINI_API_KEY to enable AI features.<br>Get free API key from: <a href="https://makersuite.google.com/app/apikey" target="_blank">Google AI Studio</a></div>';
                }
            } catch(e) { statusDiv.innerHTML = '<div class="alert alert-danger">Error checking AI status</div>'; }
            
            var candSelect = document.getElementById('analyzeCandidateId');
            var jobSelect = document.getElementById('analyzeJobId');
            var candRes = await fetch('/api/candidates');
            var candData = await candRes.json();
            candSelect.innerHTML = '<option value="">Select Candidate</option>' + candData.candidates.map(c => '<option value="' + c.id + '">' + c.name + '</option>').join('');
            var jobRes = await fetch('/api/jobs');
            var jobData = await jobRes.json();
            jobSelect.innerHTML = '<option value="">Select Job</option>' + jobData.map(j => '<option value="' + j.id + '">' + j.title + '</option>').join('');
        }
        
        async function createJob() {
            var title = document.getElementById('jobTitle').value;
            if (!title) { alert('Enter job title'); return; }
            var data = {
                title: title,
                location: document.getElementById('jobLocation').value,
                client_id: document.getElementById('jobClientId').value || null,
                skills_required: document.getElementById('jobSkills').value,
                experience_min: parseInt(document.getElementById('jobExpMin').value) || 0,
                experience_max: parseInt(document.getElementById('jobExpMax').value) || 5,
                status: document.getElementById('jobStatus').value
            };
            var res = await fetch('/api/jobs', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(data) });
            var result = await res.json();
            if (result.success) { alert('Job created!'); bootstrap.Modal.getInstance(document.getElementById('jobModal')).hide(); loadJobs(); loadDashboard(); }
        }
        
        async function createCandidate() {
            var firstName = document.getElementById('candFirstName').value;
            var lastName = document.getElementById('candLastName').value;
            if (!firstName) { alert('Enter first name'); return; }
            
            var workHistory = [];
            document.querySelectorAll('.work-history-row').forEach(row => {
                workHistory.push({
                    company: row.querySelector('.wh-company')?.value,
                    role: row.querySelector('.wh-role')?.value,
                    duration_from: row.querySelector('.wh-from')?.value,
                    duration_to: row.querySelector('.wh-to')?.value
                });
            });
            
            var certifications = [];
            document.querySelectorAll('.cert-row').forEach(row => {
                var cert = row.querySelector('.cert-name')?.value;
                if (cert) certifications.push(cert);
            });
            
            var data = {
                first_name: firstName,
                last_name: lastName,
                email: document.getElementById('candEmail').value,
                phone: document.getElementById('candPhone').value,
                skills: document.getElementById('candSkills').value,
                current_role: document.getElementById('candCurrentRole').value,
                total_experience: parseFloat(document.getElementById('candExperience').value) || 0,
                work_history: workHistory,
                certifications: certifications
            };
            var res = await fetch('/api/candidates', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(data) });
            var result = await res.json();
            if (result.success) { alert('Candidate added!'); bootstrap.Modal.getInstance(document.getElementById('candidateModal')).hide(); loadCandidates(); loadDashboard(); }
        }
        
        async function createClient() {
            var name = document.getElementById('clientName').value;
            if (!name) { alert('Enter company name'); return; }
            var data = { name: name, contact_person: document.getElementById('clientContact').value, email: document.getElementById('clientEmail').value, phone: document.getElementById('clientPhone').value };
            var res = await fetch('/api/clients', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(data) });
            var result = await res.json();
            if (result.success) { alert('Client added!'); bootstrap.Modal.getInstance(document.getElementById('clientModal')).hide(); loadClients(); }
        }
        
        async function uploadAndParseResume() {
            var file = document.getElementById('resumeFile').files[0];
            if (!file) { alert('Select a file'); return; }
            var formData = new FormData();
            formData.append('file', file);
            document.getElementById('resumeProgress').style.display = 'block';
            var res = await fetch('/api/candidates/parse-with-gemini', { method: 'POST', body: formData });
            var result = await res.json();
            document.getElementById('resumeProgress').style.display = 'none';
            if (result.success) {
                parsedResumeData = result.data;
                document.getElementById('resumeData').textContent = JSON.stringify(result.data, null, 2);
                document.getElementById('resumeResult').style.display = 'block';
                if (result.method === 'gemini_ai') {
                    document.getElementById('resumeData').innerHTML = '<span class="ai-badge">AI Parsed</span><br>' + document.getElementById('resumeData').innerHTML;
                }
            } else { alert('Error parsing resume'); }
        }
        
        function createCandidateFromResume() {
            if (parsedResumeData) {
                document.getElementById('candFirstName').value = parsedResumeData.first_name || '';
                document.getElementById('candLastName').value = parsedResumeData.last_name || '';
                document.getElementById('candEmail').value = parsedResumeData.email || '';
                document.getElementById('candPhone').value = parsedResumeData.phone || '';
                document.getElementById('candSkills').value = Array.isArray(parsedResumeData.top_skills) ? parsedResumeData.top_skills.join(', ') : '';
                document.getElementById('candCurrentRole').value = parsedResumeData.current_role || '';
                if (parsedResumeData.work_history && parsedResumeData.work_history.length > 0) {
                    document.getElementById('workHistoryContainer').innerHTML = '';
                    parsedResumeData.work_history.forEach(wh => addWorkHistoryRow(wh.company, wh.role, wh.duration_from, wh.duration_to));
                }
                if (parsedResumeData.certifications && parsedResumeData.certifications.length > 0) {
                    document.getElementById('certificationsContainer').innerHTML = '';
                    parsedResumeData.certifications.forEach(cert => addCertificationRow(cert));
                }
                bootstrap.Modal.getInstance(document.getElementById('resumeUploadModal')).hide();
                new bootstrap.Modal(document.getElementById('candidateModal')).show();
            }
        }
        
        async function uploadAndParseJD() {
            var file = document.getElementById('jdFile').files[0];
            if (!file) { alert('Select a file'); return; }
            var formData = new FormData();
            formData.append('file', file);
            document.getElementById('jdProgress').style.display = 'block';
            var res = await fetch('/api/jobs/parse-with-gemini-file', { method: 'POST', body: formData });
            var result = await res.json();
            document.getElementById('jdProgress').style.display = 'none';
            if (result.success) {
                parsedJDData = result.data;
                document.getElementById('jdData').textContent = JSON.stringify(result.data, null, 2);
                document.getElementById('jdResult').style.display = 'block';
            } else { alert('Error parsing JD'); }
        }
        
        async function parsePastedJD() {
            var text = document.getElementById('jdPasteText').value;
            if (!text) { alert('Paste JD text first'); return; }
            document.getElementById('jdPasteProgress').style.display = 'block';
            var res = await fetch('/api/jobs/parse-with-gemini', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ jd_text: text }) });
            var result = await res.json();
            document.getElementById('jdPasteProgress').style.display = 'none';
            if (result.success) {
                parsedJDData = result.data;
                document.getElementById('jdPasteData').textContent = JSON.stringify(result.data, null, 2);
                document.getElementById('jdPasteResult').style.display = 'block';
            } else { alert('Error parsing JD'); }
        }
        
        function createJobFromParsedJD() {
            if (parsedJDData) {
                document.getElementById('jobTitle').value = parsedJDData.job_title || '';
                document.getElementById('jobSkills').value = Array.isArray(parsedJDData.mandatory_skills) ? parsedJDData.mandatory_skills.join(', ') : '';
                document.getElementById('jobExpMin').value = parsedJDData.experience_min || 0;
                document.getElementById('jobExpMax').value = parsedJDData.experience_max || 5;
                bootstrap.Modal.getInstance(document.getElementById('jdUploadModal')).hide();
                new bootstrap.Modal(document.getElementById('jobModal')).show();
            }
        }
        
        function createJobFromParsedJDPaste() {
            if (parsedJDData) {
                document.getElementById('jobTitle').value = parsedJDData.job_title || '';
                document.getElementById('jobSkills').value = Array.isArray(parsedJDData.mandatory_skills) ? parsedJDData.mandatory_skills.join(', ') : '';
                document.getElementById('jobExpMin').value = parsedJDData.experience_min || 0;
                document.getElementById('jobExpMax').value = parsedJDData.experience_max || 5;
                bootstrap.Modal.getInstance(document.getElementById('jdPasteModal')).hide();
                new bootstrap.Modal(document.getElementById('jobModal')).show();
            }
        }
        
        async function createApplicationForJob(jobId) {
            var candidateId = prompt('Enter Candidate ID:');
            if (!candidateId) return;
            var res = await fetch('/api/applications', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ candidate_id: parseInt(candidateId), jd_id: jobId }) });
            var result = await res.json();
            if (result.success) alert('Application created! Match Score: ' + result.match_score + '%');
            loadApplications();
        }
        
        async function createApplicationForCandidate(candidateId) {
            var jobId = prompt('Enter Job ID:');
            if (!jobId) return;
            var res = await fetch('/api/applications', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ candidate_id: candidateId, jd_id: parseInt(jobId) }) });
            var result = await res.json();
            if (result.success) alert('Application created! Match Score: ' + result.match_score + '%');
            loadApplications();
        }
        
        async function moveApplication(appId) {
            var stage = prompt('Enter stage (screening / interview / offer / hired / rejected):');
            if (stage) {
                await fetch('/api/applications/' + appId + '/move', { method: 'PUT', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ stage: stage }) });
                loadApplications();
            }
        }
        
        async function viewCandidateProfile(candidateId) {
            var res = await fetch('/api/candidates/' + candidateId);
            var c = await res.json();
            var workHistoryHtml = '';
            if (c.work_history && c.work_history.length > 0) {
                workHistoryHtml = '<h6>Work History</h6><table class="work-history-table"><thead><tr><th>Company</th><th>Role</th><th>From</th><th>To</th></tr></thead><tbody>';
                c.work_history.forEach(wh => {
                    workHistoryHtml += '<tr><td>' + (wh.company || '') + '</td><td>' + (wh.role || '') + '</td><td>' + (wh.duration_from || '') + '</td><td>' + (wh.duration_to || '') + '</td></tr>';
                });
                workHistoryHtml += '</tbody></table>';
            }
            var certHtml = '';
            if (c.certifications && c.certifications.length > 0) {
                certHtml = '<h6>Certifications</h6><ul>' + c.certifications.map(cert => '<li>' + cert + '</li>').join('') + '</ul>';
            }
            document.getElementById('candidateProfileContent').innerHTML = `
                <h5>${c.name}</h5>
                <p><strong>Email:</strong> ${c.email}<br>
                <strong>Phone:</strong> ${c.phone || 'N/A'}<br>
                <strong>Current Role:</strong> ${c.current_role || 'N/A'}<br>
                <strong>Experience:</strong> ${c.total_experience || 0} years<br>
                <strong>Skills:</strong> ${c.skills || 'N/A'}</p>
                ${workHistoryHtml}
                ${certHtml}
                <hr>
                <button class="btn-teal btn-sm" onclick="copyProfileToClipboard()">Copy Profile</button>
            `;
            window.currentCandidateProfile = c;
            new bootstrap.Modal(document.getElementById('candidateProfileModal')).show();
        }
        
        function copyProfileToClipboard() {
            if (window.currentCandidateProfile) {
                var text = `Name: ${window.currentCandidateProfile.name}\nEmail: ${window.currentCandidateProfile.email}\nPhone: ${window.currentCandidateProfile.phone || 'N/A'}\nCurrent Role: ${window.currentCandidateProfile.current_role || 'N/A'}\nExperience: ${window.currentCandidateProfile.total_experience || 0} years\nSkills: ${window.currentCandidateProfile.skills || 'N/A'}\nWork History: ${JSON.stringify(window.currentCandidateProfile.work_history || [])}\nCertifications: ${window.currentCandidateProfile.certifications || []}`;
                navigator.clipboard.writeText(text);
                alert('Profile copied to clipboard!');
            }
        }
        
        async function searchCandidates() {
            var skill = document.getElementById('candidateSearch').value;
            if (!skill) { loadCandidates(); return; }
            var res = await fetch('/api/candidates/search?skill=' + encodeURIComponent(skill));
            var data = await res.json();
            var tbody = document.getElementById('candidatesTable');
            if (data.candidates.length === 0) { tbody.innerHTML = '<tr><td colspan="6" class="text-center">No candidates found for "' + skill + '"</td></tr>'; return; }
            var html = '';
            for (var i = 0; i < data.candidates.length; i++) {
                var c = data.candidates[i];
                html += '<tr><td>' + c.id + '</td><td><span class="candidate-name" onclick="viewCandidateProfile(' + c.id + ')">' + c.name + '</span></td><td>' + c.email + '</td><td>' + (c.current_role || '-') + '</td><td>' + (c.skills || '-') + '</td><td><button class="btn-beige btn-sm" onclick="createApplicationForCandidate(' + c.id + ')">Apply</button></td></tr>';
            }
            tbody.innerHTML = html;
        }
        
        async function analyzeProfile() {
            var candidateId = document.getElementById('analyzeCandidateId').value;
            var jobId = document.getElementById('analyzeJobId').value;
            if (!candidateId || !jobId) { alert('Select both candidate and job'); return; }
            var res = await fetch('/api/analyze/profile', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ candidate_id: parseInt(candidateId), job_id: parseInt(jobId) }) });
            var result = await res.json();
            if (result.success && result.analysis) {
                var analysis = result.analysis;
                var aiBadge = result.ai_available ? '<span class="ai-badge">AI Analysis</span>' : '<span class="badge bg-secondary">Basic Analysis</span>';
                document.getElementById('analysisResult').innerHTML = aiBadge + `
                    <div class="mt-2"><strong>Relevance Score:</strong> ${analysis.relevance_score}%<br>
                    <strong>Relevance Reason:</strong> ${analysis.relevance_reason}<br>
                    <strong>Genuineness Score:</strong> ${analysis.genuineness_score}%<br>
                    <strong>Genuineness Reason:</strong> ${analysis.genuineness_reason}<br>
                    <strong>Recommendation:</strong> <span class="badge ${analysis.recommendation === 'Hire' ? 'badge-open' : 'badge-draft'}">${analysis.recommendation}</span></div>
                    <strong>Strengths:</strong><ul>${(analysis.strengths || []).map(s => '<li>' + s + '</li>').join('')}</ul>
                    <strong>Weaknesses:</strong><ul>${(analysis.weaknesses || []).map(w => '<li>' + w + '</li>').join('')}</ul>
                `;
            } else { alert('Analysis failed'); }
        }
        
        async function parseWithAI() {
            var file = document.getElementById('aiResumeFile').files[0];
            if (!file) { alert('Select a resume file'); return; }
            var formData = new FormData();
            formData.append('file', file);
            document.getElementById('aiResult').innerHTML = '<div class="spinner-border"></div> Analyzing with AI...';
            var res = await fetch('/api/candidates/parse-with-gemini', { method: 'POST', body: formData });
            var result = await res.json();
            if (result.success) {
                document.getElementById('aiResult').innerHTML = `<div class="alert alert-success">AI Parsing Complete!<br><pre class="bg-light p-2 small">${JSON.stringify(result.data, null, 2)}</pre></div>`;
            } else { document.getElementById('aiResult').innerHTML = '<div class="alert alert-danger">Parsing failed</div>'; }
        }
        
        function addWorkHistoryRow(company = '', role = '', from = '', to = '') {
            var container = document.getElementById('workHistoryContainer');
            var row = document.createElement('div');
            row.className = 'row work-history-row mb-2';
            row.innerHTML = '<div class="col-3"><input type="text" class="form-control wh-company" placeholder="Company" value="' + company + '"></div><div class="col-3"><input type="text" class="form-control wh-role" placeholder="Role" value="' + role + '"></div><div class="col-2"><input type="text" class="form-control wh-from" placeholder="From" value="' + from + '"></div><div class="col-2"><input type="text" class="form-control wh-to" placeholder="To" value="' + to + '"></div><div class="col-2"><button class="btn btn-danger btn-sm" onclick="this.parentElement.parentElement.remove()">Remove</button></div>';
            container.appendChild(row);
        }
        
        function addCertificationRow(cert = '') {
            var container = document.getElementById('certificationsContainer');
            var row = document.createElement('div');
            row.className = 'row cert-row mb-2';
            row.innerHTML = '<div class="col-10"><input type="text" class="form-control cert-name" placeholder="Certification" value="' + cert + '"></div><div class="col-2"><button class="btn btn-danger btn-sm" onclick="this.parentElement.parentElement.remove()">Remove</button></div>';
            container.appendChild(row);
        }
        
        async function loadClientDropdown() {
            var res = await fetch('/api/clients');
            var clients = await res.json();
            var select = document.getElementById('jobClientId');
            select.innerHTML = '<option value="">Select Client</option>' + clients.map(c => '<option value="' + c.id + '">' + c.name + '</option>').join('');
        }
        
        function openJobModal() { loadClientDropdown(); new bootstrap.Modal(document.getElementById('jobModal')).show(); }
        function openCandidateModal() { document.getElementById('candidateForm')?.reset(); new bootstrap.Modal(document.getElementById('candidateModal')).show(); }
        function openResumeUploadModal() { document.getElementById('resumeFile').value = ''; document.getElementById('resumeResult').style.display = 'none'; new bootstrap.Modal(document.getElementById('resumeUploadModal')).show(); }
        function openJDUploadModal() { document.getElementById('jdFile').value = ''; document.getElementById('jdResult').style.display = 'none'; new bootstrap.Modal(document.getElementById('jdUploadModal')).show(); }
        function openJDPasteModal() { document.getElementById('jdPasteText').value = ''; document.getElementById('jdPasteResult').style.display = 'none'; new bootstrap.Modal(document.getElementById('jdPasteModal')).show(); }
        function openClientModal() { new bootstrap.Modal(document.getElementById('clientModal')).show(); }
        function viewClientJDs(clientId) { alert('View JDs for client ' + clientId); }
        
        loadDashboard(); loadJobs(); loadCandidates(); loadApplications(); loadInterviews(); loadOffers(); loadClients();
        setInterval(loadDashboard, 30000);
    </script>
</body>
</html>
'''
# ============= API ROUTES =============

@app.route('/')
def index():
    return render_template_string(DASHBOARD_TEMPLATE)

@app.route('/health')
def health():
    return jsonify({'status': 'ok', 'timestamp': datetime.now().isoformat()})

@app.route('/api/dashboard/stats')
def dashboard_stats():
    interviews_today = 0
    for i in interviews:
        if i.get('status') == 'scheduled':
            interviews_today += 1
    return jsonify({
        'open_positions': len([j for j in jobs if j.get('status') == 'open']),
        'total_candidates': len(candidates),
        'interviews_today': interviews_today,
        'offers_sent': len([o for o in offers if o.get('status') == 'sent'])
    })

# ============= JOBS API =============
@app.route('/api/jobs', methods=['GET', 'POST'])
def manage_jobs():
    global next_id
    if request.method == 'POST':
        data = request.json
        job = {
            'id': next_id,
            'title': data.get('title', 'Untitled'),
            'location': data.get('location', 'Remote'),
            'client_id': data.get('client_id'),
            'client_name': None,
            'skills_required': data.get('skills_required', ''),
            'experience_min': data.get('experience_min', 0),
            'experience_max': data.get('experience_max', 5),
            'budget_min': data.get('budget_min'),
            'budget_max': data.get('budget_max'),
            'work_location': data.get('work_location', 'Remote'),
            'responsibilities': data.get('responsibilities', []),
            'mandatory_skills': data.get('mandatory_skills', []),
            'preferred_skills': data.get('preferred_skills', []),
            'education_qualification': data.get('education_qualification', ''),
            'number_of_openings': data.get('number_of_openings', 1),
            'status': data.get('status', 'open'),
            'applications': 0,
            'created_at': datetime.now().isoformat()
        }
        # Get client name if client_id provided
        if job['client_id']:
            client = next((c for c in clients if c['id'] == job['client_id']), None)
            if client:
                job['client_name'] = client.get('name')
        jobs.append(job)
        next_id += 1
        return jsonify({'success': True, 'job_id': job['id']})
    return jsonify(jobs)

@app.route('/api/jobs/<int:job_id>', methods=['GET'])
def get_job(job_id):
    job = next((j for j in jobs if j['id'] == job_id), None)
    if not job:
        return jsonify({'error': 'Job not found'}), 404
    return jsonify(job)

@app.route('/api/jobs/parse-with-gemini-file', methods=['POST'])
def parse_jd_with_gemini_file():
    if 'file' not in request.files:
        return jsonify({'error': 'No file uploaded'}), 400
    file = request.files['file']
    text = extract_text_from_file(file)
    if not text:
        return jsonify({'error': 'Could not extract text'}), 400
    gemini_result = parse_jd_with_gemini(text)
    if gemini_result:
        return jsonify({'success': True, 'data': gemini_result, 'method': 'gemini_ai'})
    basic_result = parse_jd_basic(text)
    return jsonify({'success': True, 'data': basic_result, 'method': 'basic'})

@app.route('/api/jobs/parse-with-gemini', methods=['POST'])
def parse_jd_text_with_gemini():
    data = request.json
    jd_text = data.get('jd_text', '')
    if not jd_text:
        return jsonify({'error': 'No JD text provided'}), 400
    gemini_result = parse_jd_with_gemini(jd_text)
    if gemini_result:
        return jsonify({'success': True, 'data': gemini_result, 'method': 'gemini_ai'})
    basic_result = parse_jd_basic(jd_text)
    return jsonify({'success': True, 'data': basic_result, 'method': 'basic'})

# ============= CANDIDATES API =============
@app.route('/api/candidates', methods=['GET', 'POST'])
def manage_candidates():
    global next_id
    if request.method == 'POST':
        data = request.json
        candidate = {
            'id': next_id,
            'first_name': data.get('first_name', ''),
            'last_name': data.get('last_name', ''),
            'name': f"{data.get('first_name', '')} {data.get('last_name', '')}".strip(),
            'email': data.get('email', ''),
            'phone': data.get('phone', ''),
            'skills': data.get('skills', ''),
            'current_role': data.get('current_role', ''),
            'total_experience': data.get('total_experience', 0),
            'work_history': data.get('work_history', []),
            'certifications': data.get('certifications', []),
            'top_skills': data.get('top_skills', []),
            'documents': [],
            'created_at': datetime.now().isoformat()
        }
        candidates.append(candidate)
        next_id += 1
        return jsonify({'success': True, 'candidate_id': candidate['id']})
    
    page = int(request.args.get('page', 1))
    per_page = 20
    filtered = candidates
    start = (page - 1) * per_page
    end = start + per_page
    return jsonify({
        'candidates': filtered[start:end],
        'total': len(filtered),
        'page': page,
        'pages': (len(filtered) + per_page - 1) // per_page
    })

@app.route('/api/candidates/<int:candidate_id>', methods=['GET'])
def get_candidate(candidate_id):
    candidate = next((c for c in candidates if c['id'] == candidate_id), None)
    if not candidate:
        return jsonify({'error': 'Candidate not found'}), 404
    return jsonify(candidate)

@app.route('/api/candidates/search', methods=['GET'])
def search_candidates_by_skill():
    skill = request.args.get('skill', '').lower()
    if not skill:
        return jsonify({'candidates': candidates[:20], 'total': len(candidates)})
    
    # Search by skill keyword in skills, current_role, or work_history
    results = []
    for c in candidates:
        c_skills = (c.get('skills', '') + ' ' + c.get('current_role', '')).lower()
        if skill in c_skills:
            results.append(c)
        else:
            # Also search in work history roles
            for wh in c.get('work_history', []):
                if skill in wh.get('role', '').lower():
                    results.append(c)
                    break
    
    return jsonify({'candidates': results[:50], 'total': len(results)})

@app.route('/api/candidates/<int:candidate_id>/documents', methods=['POST'])
def upload_candidate_document(candidate_id):
    candidate = next((c for c in candidates if c['id'] == candidate_id), None)
    if not candidate:
        return jsonify({'error': 'Candidate not found'}), 404
    
    if 'file' not in request.files:
        return jsonify({'error': 'No file uploaded'}), 400
    
    file = request.files['file']
    if not allowed_file(file.filename):
        return jsonify({'error': 'File type not allowed'}), 400
    
    filename = secure_filename(file.filename)
    file_content = file.read()
    
    doc = {
        'id': len(candidate.get('documents', [])) + 1,
        'filename': filename,
        'content_type': file.content_type,
        'data': base64.b64encode(file_content).decode('utf-8'),
        'uploaded_at': datetime.now().isoformat()
    }
    
    if 'documents' not in candidate:
        candidate['documents'] = []
    candidate['documents'].append(doc)
    
    return jsonify({'success': True, 'document_id': doc['id'], 'filename': filename})

@app.route('/api/candidates/<int:candidate_id>/documents', methods=['GET'])
def get_candidate_documents(candidate_id):
    candidate = next((c for c in candidates if c['id'] == candidate_id), None)
    if not candidate:
        return jsonify({'error': 'Candidate not found'}), 404
    
    docs = []
    for doc in candidate.get('documents', []):
        docs.append({
            'id': doc['id'],
            'filename': doc['filename'],
            'uploaded_at': doc['uploaded_at']
        })
    return jsonify({'documents': docs})

@app.route('/api/candidates/<int:candidate_id>/documents/<int:doc_id>', methods=['GET'])
def view_candidate_document(candidate_id, doc_id):
    candidate = next((c for c in candidates if c['id'] == candidate_id), None)
    if not candidate:
        return jsonify({'error': 'Candidate not found'}), 404
    
    doc = next((d for d in candidate.get('documents', []) if d['id'] == doc_id), None)
    if not doc:
        return jsonify({'error': 'Document not found'}), 404
    
    file_data = base64.b64decode(doc['data'])
    return send_file(
        io.BytesIO(file_data),
        mimetype=doc['content_type'],
        as_attachment=False,
        download_name=doc['filename']
    )
    if 'file' not in request.files:
        return jsonify({'error': 'No file uploaded'}), 400
    
    file = request.files['file']
    text = extract_text_from_file(file)
    
    if not text:
        return jsonify({'error': 'Could not extract text from file'}), 400
    
    gemini_result = parse_resume_with_gemini(text)
    if gemini_result:
        return jsonify({
            'success': True, 
            'data': gemini_result, 
            'method': 'gemini_ai',
            'ai_available': True
        })
    
    basic_result = parse_resume_basic(text)
    return jsonify({
        'success': True, 
        'data': basic_result, 
        'method': 'basic',
        'ai_available': False,
        'message': 'Gemini AI not available. Using basic extraction.'
    })

# ============= APPLICATIONS API =============
@app.route('/api/applications', methods=['GET', 'POST'])
def manage_applications():
    if request.method == 'POST':
        data = request.json
        job = next((j for j in jobs if j['id'] == data.get('jd_id')), None)
        candidate = next((c for c in candidates if c['id'] == data.get('candidate_id')), None)
        match_score = calculate_match_score(job.get('skills_required', '') if job else '', candidate.get('skills', '') if candidate else '')
        application = {
            'id': len(applications) + 1,
            'candidate_id': data.get('candidate_id'),
            'jd_id': data.get('jd_id'),
            'candidate_name': candidate.get('name') if candidate else '',
            'job_title': job.get('title') if job else '',
            'match_score': match_score,
            'status': 'new',
            'application_date': datetime.now().date().isoformat(),
            'created_at': datetime.now().isoformat()
        }
        applications.append(application)
        if job:
            job['applications'] = job.get('applications', 0) + 1
        return jsonify({'success': True, 'application_id': application['id'], 'match_score': match_score})
    return jsonify(applications)

@app.route('/api/applications/<int:app_id>/move', methods=['PUT'])
def move_application(app_id):
    data = request.json
    for app in applications:
        if app['id'] == app_id:
            app['status'] = data.get('stage', app['status'])
            break
    return jsonify({'success': True})

# ============= INTERVIEWS API =============
@app.route('/api/interviews', methods=['GET', 'POST'])
def manage_interviews():
    if request.method == 'POST':
        data = request.json
        app_id = data.get('application_id')
        application = next((a for a in applications if a['id'] == app_id), None)
        if not application:
            return jsonify({'error': 'Application not found'}), 404
        candidate = next((c for c in candidates if c['id'] == application.get('candidate_id')), None)
        job = next((j for j in jobs if j['id'] == application.get('jd_id')), None)
        interview = {
            'id': len(interviews) + 1,
            'application_id': app_id,
            'candidate_name': candidate.get('name') if candidate else '',
            'job_title': job.get('title') if job else '',
            'interviewer_name': data.get('interviewer_name', ''),
            'scheduled_time': data.get('scheduled_time'),
            'round_type': data.get('round_type', 'Technical'),
            'status': 'scheduled',
            'created_at': datetime.now().isoformat()
        }
        interviews.append(interview)
        application['status'] = 'interview-scheduled'
        return jsonify({'success': True, 'interview_id': interview['id']})
    return jsonify(interviews)

# ============= OFFERS API =============
@app.route('/api/offers', methods=['GET', 'POST'])
def manage_offers():
    if request.method == 'POST':
        data = request.json
        app_id = data.get('application_id')
        application = next((a for a in applications if a['id'] == app_id), None)
        if not application:
            return jsonify({'error': 'Application not found'}), 404
        candidate = next((c for c in candidates if c['id'] == application.get('candidate_id')), None)
        job = next((j for j in jobs if j['id'] == application.get('jd_id')), None)
        offer = {
            'id': len(offers) + 1,
            'application_id': app_id,
            'candidate_name': candidate.get('name') if candidate else '',
            'job_title': job.get('title') if job else '',
            'base_salary': data.get('base_salary', 0),
            'joining_date': data.get('joining_date'),
            'status': 'draft',
            'created_at': datetime.now().isoformat()
        }
        offers.append(offer)
        application['status'] = 'offered'
        return jsonify({'success': True, 'offer_id': offer['id']})
    return jsonify(offers)

# ============= CLIENTS API =============
@app.route('/api/clients', methods=['GET', 'POST'])
def manage_clients():
    global next_id
    if request.method == 'POST':
        data = request.json
        client = {
            'id': next_id,
            'name': data.get('name', ''),
            'contact_person': data.get('contact_person', ''),
            'email': data.get('email', ''),
            'phone': data.get('phone', ''),
            'jd_count': 0,
            'created_at': datetime.now().isoformat()
        }
        clients.append(client)
        next_id += 1
        return jsonify({'success': True, 'client_id': client['id']})
    return jsonify(clients)

@app.route('/api/clients/<int:client_id>/jobs', methods=['GET'])
def get_client_jobs(client_id):
    client_jobs = [j for j in jobs if j.get('client_id') == client_id]
    return jsonify(client_jobs)

# ============= AI PROFILE ANALYSIS =============
@app.route('/api/analyze/profile', methods=['POST'])
def analyze_profile():
    data = request.json
    candidate_id = data.get('candidate_id')
    job_id = data.get('job_id')
    
    candidate = next((c for c in candidates if c['id'] == candidate_id), None)
    job = next((j for j in jobs if j['id'] == job_id), None)
    
    if not candidate or not job:
        return jsonify({'error': 'Candidate or job not found'}), 404
    
    analysis = analyze_profile_with_gemini(candidate, job)
    
    if analysis:
        return jsonify({'success': True, 'analysis': analysis, 'ai_available': True})
    else:
        match_score = calculate_match_score(job.get('skills_required', ''), candidate.get('skills', ''))
        return jsonify({
            'success': True, 
            'analysis': {
                'relevance_score': match_score,
                'relevance_reason': 'Based on skill matching',
                'genuineness_score': 75,
                'genuineness_reason': 'Profile appears consistent',
                'strengths': ['Skills match requirements'],
                'weaknesses': [],
                'recommendation': 'Interview' if match_score > 60 else 'Review'
            },
            'ai_available': False
        })

# ============= GEMINI STATUS =============
@app.route('/api/gemini/status', methods=['GET'])
def gemini_status():
    return jsonify({
        'available': GEMINI_AVAILABLE,
        'message': 'Gemini AI is ready' if GEMINI_AVAILABLE else 'Gemini AI not configured. Add GEMINI_API_KEY to enable.'
    })
    # ============= ADDITIONAL API ROUTES =============

@app.route('/api/candidates/enhanced', methods=['POST'])
def create_enhanced_candidate():
    """Create candidate with full profile including work history and certifications"""
    global next_id
    data = request.json
    
    candidate = {
        'id': next_id,
        'first_name': data.get('first_name', ''),
        'last_name': data.get('last_name', ''),
        'name': f"{data.get('first_name', '')} {data.get('last_name', '')}".strip(),
        'email': data.get('email', ''),
        'phone': data.get('phone', ''),
        'address': data.get('address', ''),
        'linkedin_url': data.get('linkedin_url', ''),
        'current_role': data.get('current_role', ''),
        'notice_period': data.get('notice_period'),
        'employment_status': data.get('employment_status', ''),
        'total_experience': data.get('total_experience', 0),
        'skills': data.get('skills', ''),
        'work_history': data.get('work_history', []),
        'certifications': data.get('certifications', []),
        'top_skills': data.get('top_skills', []),
        'documents': [],
        'source': data.get('source', 'manual'),
        'ai_enriched': data.get('ai_enriched', False),
        'created_at': datetime.now().isoformat(),
        'updated_at': datetime.now().isoformat()
    }
    candidates.append(candidate)
    next_id += 1
    
    return jsonify({'success': True, 'candidate_id': candidate['id'], 'message': 'Candidate created successfully'})

@app.route('/api/candidates/<int:candidate_id>/enrich', methods=['POST'])
def enrich_candidate_with_ai(candidate_id):
    """Enrich existing candidate profile using AI"""
    candidate = next((c for c in candidates if c['id'] == candidate_id), None)
    if not candidate:
        return jsonify({'error': 'Candidate not found'}), 404
    
    if not GEMINI_AVAILABLE:
        return jsonify({'error': 'Gemini AI not available', 'ai_available': False}), 400
    
    # Create a summary of existing candidate data
    candidate_text = f"""
    Name: {candidate.get('name', '')}
    Current Role: {candidate.get('current_role', '')}
    Skills: {candidate.get('skills', '')}
    Experience: {candidate.get('total_experience', 0)} years
    Work History: {json.dumps(candidate.get('work_history', []))}
    """
    
    prompt = f"""Based on this candidate profile, suggest improvements and missing information.
    
    Candidate: {candidate_text}
    
    Return ONLY valid JSON with:
    {{
        "suggested_skills": ["skill1", "skill2"],
        "suggested_certifications": ["cert1", "cert2"],
        "market_value": "estimated salary range",
        "career_progression": "suggested next role",
        "profile_strength": "Weak/Good/Strong/Excellent",
        "missing_info": ["field1", "field2"]
    }}"""
    
    try:
        response = gemini_model.generate_content(prompt)
        json_str = re.sub(r'```json\n?|```\n?', '', response.text)
        enrichment = json.loads(json_str)
        
        # Update candidate with suggestions
        if enrichment.get('suggested_skills'):
            current_skills = candidate.get('skills', '')
            new_skills = ', '.join(enrichment['suggested_skills'])
            if current_skills:
                candidate['skills'] = current_skills + ', ' + new_skills
            else:
                candidate['skills'] = new_skills
        
        if enrichment.get('suggested_certifications'):
            candidate['certifications'] = candidate.get('certifications', []) + enrichment['suggested_certifications']
        
        candidate['ai_enriched'] = True
        candidate['updated_at'] = datetime.now().isoformat()
        
        return jsonify({
            'success': True, 
            'enrichment': enrichment,
            'message': 'Candidate profile enriched with AI suggestions'
        })
    except Exception as e:
        return jsonify({'error': f'AI enrichment failed: {str(e)}'}), 500

@app.route('/api/reports/candidate-summary', methods=['GET'])
def candidate_summary_report():
    """Generate summary report of all candidates"""
    total_candidates = len(candidates)
    avg_experience = sum(c.get('total_experience', 0) for c in candidates) / max(total_candidates, 1)
    
    # Skill frequency analysis
    skill_freq = {}
    for c in candidates:
        skills = c.get('skills', '').split(',')
        for skill in skills:
            skill = skill.strip().lower()
            if skill:
                skill_freq[skill] = skill_freq.get(skill, 0) + 1
    
    top_skills = sorted(skill_freq.items(), key=lambda x: x[1], reverse=True)[:10]
    
    # Source breakdown
    source_stats = {}
    for c in candidates:
        source = c.get('source', 'manual')
        source_stats[source] = source_stats.get(source, 0) + 1
    
    return jsonify({
        'total_candidates': total_candidates,
        'average_experience_years': round(avg_experience, 1),
        'top_skills': [{'skill': s[0], 'count': s[1]} for s in top_skills],
        'source_breakdown': source_stats,
        'ai_enriched_count': len([c for c in candidates if c.get('ai_enriched')]),
        'generated_at': datetime.now().isoformat()
    })

@app.route('/api/reports/job-pipeline', methods=['GET'])
def job_pipeline_report():
    """Get pipeline statistics for all jobs"""
    job_stats = []
    for job in jobs:
        job_apps = [a for a in applications if a.get('jd_id') == job['id']]
        job_stats.append({
            'job_id': job['id'],
            'title': job['title'],
            'status': job.get('status', 'unknown'),
            'total_applications': len(job_apps),
            'shortlisted': len([a for a in job_apps if a.get('status') == 'shortlisted']),
            'interviewed': len([a for a in job_apps if a.get('status') in ['interview-scheduled', 'interviewed']]),
            'offered': len([a for a in job_apps if a.get('status') == 'offered']),
            'hired': len([a for a in job_apps if a.get('status') == 'hired']),
            'rejected': len([a for a in job_apps if a.get('status') == 'rejected'])
        })
    
    return jsonify({
        'jobs': job_stats,
        'total_applications': len(applications),
        'total_open_positions': len([j for j in jobs if j.get('status') == 'open']),
        'generated_at': datetime.now().isoformat()
    })

@app.route('/api/search/global', methods=['GET'])
def global_search():
    """Search across candidates, jobs, and applications"""
    query = request.args.get('q', '').lower()
    if not query:
        return jsonify({'candidates': [], 'jobs': [], 'applications': []})
    
    # Search candidates
    matched_candidates = []
    for c in candidates:
        if (query in c.get('name', '').lower() or 
            query in c.get('email', '').lower() or 
            query in c.get('skills', '').lower() or
            query in c.get('current_role', '').lower()):
            matched_candidates.append({
                'id': c['id'],
                'type': 'candidate',
                'name': c.get('name'),
                'email': c.get('email'),
                'current_role': c.get('current_role')
            })
    
    # Search jobs
    matched_jobs = []
    for j in jobs:
        if (query in j.get('title', '').lower() or 
            query in j.get('skills_required', '').lower() or
            query in j.get('location', '').lower()):
            matched_jobs.append({
                'id': j['id'],
                'type': 'job',
                'title': j.get('title'),
                'location': j.get('location'),
                'status': j.get('status')
            })
    
    # Search applications
    matched_applications = []
    for a in applications:
        if (query in a.get('candidate_name', '').lower() or 
            query in a.get('job_title', '').lower()):
            matched_applications.append({
                'id': a['id'],
                'type': 'application',
                'candidate_name': a.get('candidate_name'),
                'job_title': a.get('job_title'),
                'status': a.get('status'),
                'match_score': a.get('match_score')
            })
    
    return jsonify({
        'candidates': matched_candidates[:10],
        'jobs': matched_jobs[:10],
        'applications': matched_applications[:10],
        'total_results': len(matched_candidates) + len(matched_jobs) + len(matched_applications)
    })

@app.route('/api/export/candidates/csv', methods=['GET'])
def export_candidates_csv():
    """Export all candidates to CSV"""
    output = io.StringIO()
    writer = csv.writer(output)
    
    writer.writerow(['ID', 'Name', 'Email', 'Phone', 'Current Role', 'Skills', 'Experience', 'Work History', 'Certifications', 'Created At'])
    
    for c in candidates:
        writer.writerow([
            c.get('id'),
            c.get('name'),
            c.get('email'),
            c.get('phone', ''),
            c.get('current_role', ''),
            c.get('skills', ''),
            c.get('total_experience', 0),
            json.dumps(c.get('work_history', [])),
            json.dumps(c.get('certifications', [])),
            c.get('created_at', '')
        ])
    
    output.seek(0)
    return send_file(
        io.BytesIO(output.getvalue().encode('utf-8')),
        mimetype='text/csv',
        as_attachment=True,
        download_name=f'candidates_export_{datetime.now().strftime("%Y%m%d_%H%M%S")}.csv'
    )

@app.route('/api/export/applications/csv', methods=['GET'])
def export_applications_csv():
    """Export all applications to CSV"""
    output = io.StringIO()
    writer = csv.writer(output)
    
    writer.writerow(['ID', 'Candidate', 'Job', 'Match Score', 'Status', 'Application Date', 'Created At'])
    
    for a in applications:
        writer.writerow([
            a.get('id'),
            a.get('candidate_name'),
            a.get('job_title'),
            a.get('match_score', 0),
            a.get('status'),
            a.get('application_date'),
            a.get('created_at')
        ])
    
    output.seek(0)
    return send_file(
        io.BytesIO(output.getvalue().encode('utf-8')),
        mimetype='text/csv',
        as_attachment=True,
        download_name=f'applications_export_{datetime.now().strftime("%Y%m%d_%H%M%S")}.csv'
    )

# ============= DOCUMENT UPLOAD HELPERS =============
@app.route('/api/upload', methods=['POST'])
def upload_file():
    """Generic file upload endpoint"""
    if 'file' not in request.files:
        return jsonify({'error': 'No file uploaded'}), 400
    
    file = request.files['file']
    if not allowed_file(file.filename):
        return jsonify({'error': 'File type not allowed'}), 400
    
    filename = secure_filename(file.filename)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    unique_filename = f"{timestamp}_{filename}"
    filepath = os.path.join(app.config['UPLOAD_FOLDER'], unique_filename)
    file.save(filepath)
    
    return jsonify({
        'success': True,
        'filename': unique_filename,
        'original_name': filename,
        'path': filepath,
        'uploaded_at': datetime.now().isoformat()
    })

# ============= ERROR HANDLERS =============
@app.errorhandler(404)
def not_found(error):
    return jsonify({'error': 'Resource not found', 'status': 404}), 404

@app.errorhandler(500)
def internal_error(error):
    return jsonify({'error': 'Internal server error', 'status': 500}), 500

@app.errorhandler(413)
def too_large(error):
    return jsonify({'error': 'File too large (max 50MB)', 'status': 413}), 413

# ============= INITIALIZATION =============
def init_sample_data():
    """Initialize sample data for testing"""
    if len(candidates) == 0 and len(jobs) == 0:
        # Sample Client
        clients.append({
            'id': 1,
            'name': 'Tech Solutions Inc',
            'contact_person': 'John Smith',
            'email': 'john@techsolutions.com',
            'phone': '9876543210',
            'jd_count': 0,
            'created_at': datetime.now().isoformat()
        })
        
        # Sample Job
        jobs.append({
            'id': 1,
            'title': 'Senior Python Developer',
            'location': 'Remote',
            'client_id': 1,
            'client_name': 'Tech Solutions Inc',
            'skills_required': 'Python, Django, PostgreSQL, AWS, Docker',
            'experience_min': 3,
            'experience_max': 8,
            'status': 'open',
            'applications': 0,
            'created_at': datetime.now().isoformat()
        })
        
        # Sample Candidate
        candidates.append({
            'id': 1,
            'first_name': 'John',
            'last_name': 'Doe',
            'name': 'John Doe',
            'email': 'john.doe@example.com',
            'phone': '9876543210',
            'skills': 'Python, Django, Flask, PostgreSQL, AWS',
            'current_role': 'Senior Software Engineer',
            'total_experience': 5,
            'work_history': [
                {'company': 'ABC Corp', 'role': 'Software Engineer', 'duration_from': '2019', 'duration_to': '2022'},
                {'company': 'XYZ Ltd', 'role': 'Senior Developer', 'duration_from': '2022', 'duration_to': 'Present'}
            ],
            'certifications': ['AWS Certified Developer', 'Python Professional'],
            'created_at': datetime.now().isoformat()
        })
        
        # Sample Application
        applications.append({
            'id': 1,
            'candidate_id': 1,
            'jd_id': 1,
            'candidate_name': 'John Doe',
            'job_title': 'Senior Python Developer',
            'match_score': 85,
            'status': 'new',
            'application_date': datetime.now().date().isoformat(),
            'created_at': datetime.now().isoformat()
        })
        
        print("Sample data initialized")

# Uncomment to initialize sample data
# init_sample_data()

# ============= MAIN =============
if __name__ == '__main__':
    port = int(os.environ.get('PORT', 8080))
    print("=" * 60)
    print("SHAHNAIT SCOUT - RECRUITMENT MANAGEMENT SYSTEM")
    print("=" * 60)
    print(f"Server running on port: {port}")
    print(f"Gemini AI: {'AVAILABLE' if GEMINI_AVAILABLE else 'NOT CONFIGURED'}")
    if not GEMINI_AVAILABLE:
        print("To enable AI features, add GEMINI_API_KEY to environment variables")
        print("Get free API key from: https://makersuite.google.com/app/apikey")
    print("=" * 60)
    print("API Endpoints:")
    print("  GET  /health - Health check")
    print("  GET  /api/dashboard/stats - Dashboard statistics")
    print("  GET  /api/jobs - List jobs")
    print("  POST /api/jobs - Create job")
    print("  GET  /api/candidates - List candidates")
    print("  POST /api/candidates - Create candidate")
    print("  GET  /api/applications - List applications")
    print("  POST /api/applications - Create application")
    print("  POST /api/candidates/parse-with-gemini - AI resume parsing")
    print("  POST /api/analyze/profile - AI profile analysis")
    print("=" * 60)
    app.run(host='0.0.0.0', port=port, debug=False)
