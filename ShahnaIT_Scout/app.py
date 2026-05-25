from flask import Flask, request, jsonify, render_template
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime, date
import os
import re
import hashlib

app = Flask(__name__)

# Configuration
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'dev-secret-key-change-in-production')
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL', 'sqlite:///recruitment.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

# ============= DATABASE MODELS =============

class JobDescription(db.Model):
    __tablename__ = 'job_descriptions'
    id = db.Column(db.Integer, primary_key=True)
    jd_code = db.Column(db.String(50), unique=True)
    title = db.Column(db.String(255), nullable=False)
    client_name = db.Column(db.String(255))
    location = db.Column(db.String(255))
    location_type = db.Column(db.String(50), default='remote')
    employment_type = db.Column(db.String(50), default='full-time')
    experience_min = db.Column(db.Integer, default=0)
    experience_max = db.Column(db.Integer, default=10)
    skills_required = db.Column(db.Text)
    qualifications = db.Column(db.Text)
    responsibilities = db.Column(db.Text)
    status = db.Column(db.String(50), default='open')
    priority = db.Column(db.String(50), default='medium')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class Candidate(db.Model):
    __tablename__ = 'candidates'
    id = db.Column(db.Integer, primary_key=True)
    candidate_code = db.Column(db.String(50), unique=True)
    first_name = db.Column(db.String(100), nullable=False)
    last_name = db.Column(db.String(100))
    email = db.Column(db.String(255), unique=True, nullable=False)
    phone = db.Column(db.String(20))
    current_company = db.Column(db.String(255))
    current_designation = db.Column(db.String(255))
    total_experience = db.Column(db.Float, default=0)
    skills = db.Column(db.Text)
    qualifications = db.Column(db.Text)
    current_location = db.Column(db.String(255))
    expected_salary = db.Column(db.Float)
    notice_period = db.Column(db.Integer)
    source = db.Column(db.String(100))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class CandidateApplication(db.Model):
    __tablename__ = 'candidate_applications'
    id = db.Column(db.Integer, primary_key=True)
    application_code = db.Column(db.String(50), unique=True)
    candidate_id = db.Column(db.Integer, db.ForeignKey('candidates.id'))
    jd_id = db.Column(db.Integer, db.ForeignKey('job_descriptions.id'))
    match_score = db.Column(db.Float, default=0)
    status = db.Column(db.String(50), default='new')
    application_date = db.Column(db.Date, default=date.today)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    candidate = db.relationship('Candidate', backref='applications')
    job = db.relationship('JobDescription', backref='applications')

# ============= HELPER FUNCTIONS =============

def generate_code(prefix):
    """Generate unique code like JD-001"""
    if prefix == 'JD':
        last = JobDescription.query.order_by(JobDescription.id.desc()).first()
        last_num = int(last.jd_code.split('-')[1]) if last and last.jd_code else 0
    elif prefix == 'CAN':
        last = Candidate.query.order_by(Candidate.id.desc()).first()
        last_num = int(last.candidate_code.split('-')[1]) if last and last.candidate_code else 0
    elif prefix == 'APP':
        last = CandidateApplication.query.order_by(CandidateApplication.id.desc()).first()
        last_num = int(last.application_code.split('-')[1]) if last and last.application_code else 0
    else:
        last_num = 0
    
    new_num = last_num + 1
    return f"{prefix}-{new_num:04d}"

def extract_skills_from_text(text):
    """Extract skills from text"""
    common_skills = ['Python', 'Java', 'JavaScript', 'SQL', 'AWS', 'Docker', 
                     'React', 'Angular', 'Node.js', 'Django', 'Flask', 'MongoDB',
                     'PostgreSQL', 'Git', 'Kubernetes', 'TensorFlow', 'Machine Learning']
    found = []
    text_lower = text.lower()
    for skill in common_skills:
        if skill.lower() in text_lower:
            found.append(skill)
    return found

def calculate_match_score(jd_skills, candidate_skills):
    """Calculate match percentage"""
    if not jd_skills or not candidate_skills:
        return 0
    
    jd_list = [s.strip().lower() for s in jd_skills.split(',') if s.strip()]
    cand_list = [s.strip().lower() for s in candidate_skills.split(',') if s.strip()]
    
    if not jd_list:
        return 0
    
    matches = sum(1 for s in jd_list if s in cand_list)
    return round((matches / len(jd_list)) * 100, 2)

def extract_text_from_file(file):
    """Extract text from uploaded file"""
    text = ''
    filename = file.filename.lower()
    
    if filename.endswith('.pdf'):
        try:
            import PyPDF2
            reader = PyPDF2.PdfReader(file)
            for page in reader.pages:
                text += page.extract_text() or ''
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

# ============= API ROUTES =============

@app.route('/')
def index():
    """Main dashboard"""
    return render_template('dashboard.html')

@app.route('/api/dashboard/stats')
def dashboard_stats():
    """Get dashboard statistics"""
    stats = {
        'overview': {
            'total_jobs': JobDescription.query.count(),
            'open_positions': JobDescription.query.filter_by(status='open').count(),
            'total_candidates': Candidate.query.count(),
            'interviews_today': 0,
            'offers_accepted': 0
        },
        'pipeline': {
            'new': CandidateApplication.query.filter_by(status='new').count(),
            'shortlisted': CandidateApplication.query.filter_by(status='shortlisted').count(),
            'interviewed': CandidateApplication.query.filter_by(status='interviewed').count(),
            'selected': CandidateApplication.query.filter_by(status='selected').count(),
            'rejected': CandidateApplication.query.filter_by(status='rejected').count()
        },
        'recent_activities': [],
        'top_jds': []
    }
    return jsonify(stats)

@app.route('/api/jds', methods=['GET', 'POST'])
def manage_jds():
    """List and create job descriptions"""
    
    if request.method == 'POST':
        data = request.json
        
        jd = JobDescription(
            jd_code=generate_code('JD'),
            title=data.get('title'),
            client_name=data.get('client_name'),
            location=data.get('location'),
            location_type=data.get('location_type', 'remote'),
            employment_type=data.get('employment_type', 'full-time'),
            experience_min=data.get('experience_min', 0),
            experience_max=data.get('experience_max', 10),
            skills_required=data.get('skills_required'),
            qualifications=data.get('qualifications'),
            responsibilities=data.get('responsibilities'),
            status=data.get('status', 'open'),
            priority=data.get('priority', 'medium')
        )
        
        db.session.add(jd)
        db.session.commit()
        
        return jsonify({'success': True, 'jd_id': jd.id, 'jd_code': jd.jd_code})
    
    else:
        jds = JobDescription.query.order_by(JobDescription.created_at.desc()).all()
        return jsonify([{
            'id': j.id,
            'code': j.jd_code,
            'title': j.title,
            'client': j.client_name,
            'location': j.location,
            'employment_type': j.employment_type,
            'experience_min': j.experience_min,
            'experience_max': j.experience_max,
            'status': j.status,
            'priority': j.priority,
            'applications': len(j.applications),
            'created_at': j.created_at.isoformat() if j.created_at else None
        } for j in jds])

@app.route('/api/jds/<int:jd_id>/parse', methods=['POST'])
def parse_jd_document(jd_id):
    """Parse uploaded JD document"""
    
    if 'file' not in request.files:
        return jsonify({'error': 'No file uploaded'}), 400
    
    file = request.files['file']
    text = extract_text_from_file(file)
    
    # Extract information
    extracted = {
        'title': extract_job_title(text),
        'skills_required': ', '.join(extract_skills_from_text(text)),
        'qualifications': extract_qualifications(text),
        'location': extract_location(text),
        'responsibilities': extract_responsibilities(text)
    }
    
    # Update JD with extracted data
    jd = JobDescription.query.get(jd_id)
    if jd and extracted['title']:
        jd.title = extracted['title']
        jd.skills_required = extracted['skills_required']
        jd.qualifications = extracted['qualifications']
        jd.location = extracted['location'] or jd.location
        jd.responsibilities = extracted['responsibilities']
        db.session.commit()
    
    return jsonify({'success': True, 'extracted': extracted})

# Helper extraction functions
def extract_job_title(text):
    patterns = [r'Job Title:?\s*(.+?)(?:\n|$)', r'Position:?\s*(.+?)(?:\n|$)', r'Role:?\s*(.+?)(?:\n|$)']
    for pattern in patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            return match.group(1).strip()
    
    # Look for common patterns
    lines = text.split('\n')[:10]
    for line in lines:
        if len(line.strip().split()) <= 6 and any(word in line.lower() for word in ['developer', 'engineer', 'manager', 'analyst']):
            return line.strip()
    return None

def extract_qualifications(text):
    keywords = ['Bachelor', 'Master', 'B.Tech', 'MCA', 'MBA', 'Degree']
    found = []
    for keyword in keywords:
        if keyword.lower() in text.lower():
            context = re.search(f'.{{0,50}}{keyword}.{{0,100}}', text, re.IGNORECASE)
            if context:
                found.append(context.group().strip())
    return '\n'.join(found[:3])

def extract_location(text):
    patterns = [r'Location:?\s*(.+?)(?:\n|$)', r'Work Location:?\s*(.+?)(?:\n|$)']
    for pattern in patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            return match.group(1).strip()
    
    cities = ['Bangalore', 'Mumbai', 'Delhi', 'Hyderabad', 'Chennai', 'Pune', 'Remote']
    for city in cities:
        if city.lower() in text.lower():
            return city
    return None

def extract_responsibilities(text):
    patterns = [r'Responsibilities:?(.+?)(?:\n\n|\Z)', r'Key Responsibilities:?(.+?)(?:\n\n|\Z)']
    for pattern in patterns:
        match = re.search(pattern, text, re.IGNORECASE | re.DOTALL)
        if match:
            return match.group(1).strip()[:500]
    return None

@app.route('/api/candidates', methods=['GET', 'POST'])
def manage_candidates():
    """List and create candidates"""
    
    if request.method == 'POST':
        data = request.json
        
        # Check for existing candidate
        existing = Candidate.query.filter_by(email=data.get('email')).first()
        if existing:
            return jsonify({'error': 'Candidate already exists', 'candidate_id': existing.id}), 409
        
        candidate = Candidate(
            candidate_code=generate_code('CAN'),
            first_name=data.get('first_name'),
            last_name=data.get('last_name'),
            email=data.get('email'),
            phone=data.get('phone'),
            current_company=data.get('current_company'),
            current_designation=data.get('current_designation'),
            total_experience=data.get('total_experience', 0),
            skills=data.get('skills'),
            qualifications=data.get('qualifications'),
            current_location=data.get('current_location'),
            expected_salary=data.get('expected_salary'),
            notice_period=data.get('notice_period'),
            source=data.get('source', 'website')
        )
        
        db.session.add(candidate)
        db.session.commit()
        
        return jsonify({'success': True, 'candidate_id': candidate.id, 'candidate_code': candidate.candidate_code})
    
    else:
        page = int(request.args.get('page', 1))
        per_page = 20
        search = request.args.get('skill', '')
        
        query = Candidate.query
        if search:
            query = query.filter(
                db.or_(
                    Candidate.first_name.ilike(f'%{search}%'),
                    Candidate.last_name.ilike(f'%{search}%'),
                    Candidate.email.ilike(f'%{search}%'),
                    Candidate.skills.ilike(f'%{search}%')
                )
            )
        
        pagination = query.order_by(Candidate.created_at.desc()).paginate(page=page, per_page=per_page)
        
        return jsonify({
            'candidates': [{
                'id': c.id,
                'code': c.candidate_code,
                'name': f"{c.first_name} {c.last_name}",
                'email': c.email,
                'phone': c.phone,
                'current_company': c.current_company,
                'current_designation': c.current_designation,
                'total_experience': c.total_experience,
                'skills': c.skills,
                'source': c.source,
                'created_at': c.created_at.isoformat() if c.created_at else None
            } for c in pagination.items],
            'total': pagination.total,
            'page': page,
            'pages': pagination.pages
        })

@app.route('/api/candidates/parse-resume', methods=['POST'])
def parse_resume():
    """Parse uploaded resume"""
    
    if 'file' not in request.files:
        return jsonify({'error': 'No file uploaded'}), 400
    
    file = request.files['file']
    text = extract_text_from_file(file)
    
    parsed = {
        'first_name': extract_name(text)['first'],
        'last_name': extract_name(text)['last'],
        'email': extract_email(text),
        'phone': extract_phone(text),
        'skills': extract_skills_from_text(text),
        'qualifications': extract_qualifications(text),
        'current_company': extract_company(text),
        'current_designation': extract_designation(text),
        'current_location': extract_location(text)
    }
    
    return jsonify({'success': True, 'data': parsed})

def extract_name(text):
    lines = text.split('\n')[:10]
    for line in lines:
        if len(line.strip().split()) <= 3 and line.strip():
            parts = line.strip().split()
            if len(parts) >= 2:
                return {'first': parts[0], 'last': parts[-1]}
    return {'first': None, 'last': None}

def extract_email(text):
    pattern = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
    match = re.search(pattern, text)
    return match.group(0) if match else None

def extract_phone(text):
    patterns = [r'\b\d{10}\b', r'\b\d{3}[-.]?\d{3}[-.]?\d{4}\b']
    for pattern in patterns:
        match = re.search(pattern, text)
        if match:
            return match.group(0)
    return None

def extract_company(text):
    patterns = [r'Current Company:?\s*(.+?)(?:\n|$)', r'Employer:?\s*(.+?)(?:\n|$)']
    for pattern in patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            return match.group(1).strip()
    return None

def extract_designation(text):
    patterns = [r'Designation:?\s*(.+?)(?:\n|$)', r'Title:?\s*(.+?)(?:\n|$)']
    for pattern in patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            return match.group(1).strip()
    return None

@app.route('/api/applications', methods=['GET', 'POST'])
def manage_applications():
    """Manage candidate applications"""
    
    if request.method == 'POST':
        data = request.json
        
        # Calculate match score
        jd = JobDescription.query.get(data.get('jd_id'))
        candidate = Candidate.query.get(data.get('candidate_id'))
        
        match_score = calculate_match_score(
            jd.skills_required if jd else '',
            candidate.skills if candidate else ''
        )
        
        application = CandidateApplication(
            application_code=generate_code('APP'),
            candidate_id=data.get('candidate_id'),
            jd_id=data.get('jd_id'),
            match_score=match_score,
            status='new'
        )
        
        db.session.add(application)
        db.session.commit()
        
        return jsonify({'success': True, 'application_id': application.id, 'match_score': match_score})
    
    else:
        applications = CandidateApplication.query.order_by(CandidateApplication.created_at.desc()).all()
        return jsonify([{
            'id': a.id,
            'code': a.application_code,
            'candidate_name': f"{a.candidate.first_name} {a.candidate.last_name}" if a.candidate else None,
            'job_title': a.job.title if a.job else None,
            'match_score': a.match_score,
            'status': a.status,
            'application_date': a.application_date.isoformat() if a.application_date else None
        } for a in applications])

@app.route('/api/applications/<int:app_id>/move', methods=['PUT'])
def move_application_stage(app_id):
    """Move application to next stage"""
    data = request.json
    application = CandidateApplication.query.get_or_404(app_id)
    application.status = data.get('stage')
    db.session.commit()
    return jsonify({'success': True})

@app.route('/api/clients', methods=['GET'])
def get_clients():
    """Get list of clients (simplified)"""
    # Get unique client names from jobs
    clients = db.session.query(JobDescription.client_name).filter(JobDescription.client_name.isnot(None)).distinct().all()
    return jsonify([{'id': i+1, 'company_name': c[0]} for i, c in enumerate(clients)])

# ============= DATABASE INITIALIZATION =============

@app.cli.command('init-db')
def init_db_command():
    """Initialize database"""
    db.create_all()
    print("✅ Database initialized successfully!")

# ============= MAIN =============

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(debug=False, host='0.0.0.0', port=port)
