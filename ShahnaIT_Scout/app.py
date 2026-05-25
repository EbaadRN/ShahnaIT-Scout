# app.py - Complete Professional Recruitment System
from flask import Flask, request, jsonify, render_template, session, redirect, url_for
from flask_sqlalchemy import SQLAlchemy
from flask_mail import Mail, Message
from datetime import datetime, date, timedelta
from sqlalchemy import func, and_, or_
import os
import json
import re
import hashlib
import secrets
from functools import wraps

app = Flask(__name__)

# ============= CONFIGURATION =============
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', secrets.token_hex(32))
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL', 'sqlite:///recruitment.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SQLALCHEMY_ENGINE_OPTIONS'] = {
    'pool_size': 10,
    'pool_recycle': 3600,
    'pool_pre_ping': True
}

# Email Configuration
app.config['MAIL_SERVER'] = os.environ.get('MAIL_SERVER', 'smtp.gmail.com')
app.config['MAIL_PORT'] = int(os.environ.get('MAIL_PORT', 587))
app.config['MAIL_USE_TLS'] = True
app.config['MAIL_USERNAME'] = os.environ.get('MAIL_USERNAME', '')
app.config['MAIL_PASSWORD'] = os.environ.get('MAIL_PASSWORD', '')
app.config['MAIL_DEFAULT_SENDER'] = os.environ.get('MAIL_DEFAULT_SENDER', 'noreply@shahnaiT.com')

db = SQLAlchemy(app)
mail = Mail(app)

# ============= COMPLETE DATABASE MODELS =============

class User(db.Model):
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(200), nullable=False)
    role = db.Column(db.Enum('admin', 'recruiter', 'manager', 'client'), default='recruiter')
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    last_login = db.Column(db.DateTime)

class Client(db.Model):
    __tablename__ = 'clients'
    id = db.Column(db.Integer, primary_key=True)
    company_name = db.Column(db.String(255), nullable=False)
    industry = db.Column(db.String(100))
    website = db.Column(db.String(255))
    contact_person = db.Column(db.String(255))
    email = db.Column(db.String(255))
    phone = db.Column(db.String(20))
    address = db.Column(db.Text)
    gst_number = db.Column(db.String(50))
    payment_terms = db.Column(db.String(100))
    status = db.Column(db.Enum('active', 'inactive', 'prospect'), default='active')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class JobDescription(db.Model):
    __tablename__ = 'job_descriptions'
    id = db.Column(db.Integer, primary_key=True)
    client_id = db.Column(db.Integer, db.ForeignKey('clients.id'))
    jd_code = db.Column(db.String(50), unique=True)
    title = db.Column(db.String(255), nullable=False)
    department = db.Column(db.String(100))
    location = db.Column(db.String(255))
    location_type = db.Column(db.Enum('remote', 'onsite', 'hybrid'), default='remote')
    employment_type = db.Column(db.Enum('full-time', 'part-time', 'contract', 'freelance', 'internship'), default='full-time')
    experience_min = db.Column(db.Integer, default=0)
    experience_max = db.Column(db.Integer, default=10)
    salary_min = db.Column(db.Numeric(10,2))
    salary_max = db.Column(db.Numeric(10,2))
    salary_currency = db.Column(db.String(3), default='USD')
    no_of_positions = db.Column(db.Integer, default=1)
    skills_required = db.Column(db.Text)
    skills_preferred = db.Column(db.Text)
    qualifications = db.Column(db.Text)
    certifications = db.Column(db.Text)
    responsibilities = db.Column(db.Text)
    benefits = db.Column(db.Text)
    status = db.Column(db.Enum('draft', 'published', 'open', 'in-progress', 'on-hold', 'closed', 'fulfilled'), default='draft')
    priority = db.Column(db.Enum('low', 'medium', 'high', 'urgent'), default='medium')
    source = db.Column(db.String(100))
    publish_date = db.Column(db.Date)
    target_closure_date = db.Column(db.Date)
    actual_closure_date = db.Column(db.Date)
    created_by = db.Column(db.Integer, db.ForeignKey('users.id'))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    client = db.relationship('Client', backref='job_descriptions')
    creator = db.relationship('User', backref='created_jds')

class Candidate(db.Model):
    __tablename__ = 'candidates'
    id = db.Column(db.Integer, primary_key=True)
    candidate_code = db.Column(db.String(50), unique=True)
    first_name = db.Column(db.String(100), nullable=False)
    last_name = db.Column(db.String(100))
    email = db.Column(db.String(255), unique=True, nullable=False)
    phone = db.Column(db.String(20))
    alternate_phone = db.Column(db.String(20))
    date_of_birth = db.Column(db.Date)
    gender = db.Column(db.Enum('male', 'female', 'other', 'prefer-not-to-say'))
    nationality = db.Column(db.String(100))
    current_location = db.Column(db.String(255))
    preferred_locations = db.Column(db.Text)
    current_company = db.Column(db.String(255))
    current_designation = db.Column(db.String(255))
    total_experience_years = db.Column(db.Numeric(4,1), default=0)
    total_experience_months = db.Column(db.Integer, default=0)
    relevant_experience = db.Column(db.Numeric(4,1), default=0)
    current_salary = db.Column(db.Numeric(10,2))
    current_salary_currency = db.Column(db.String(3), default='USD')
    expected_salary = db.Column(db.Numeric(10,2))
    expected_salary_currency = db.Column(db.String(3), default='USD')
    notice_period_days = db.Column(db.Integer)
    notice_period_negotiable = db.Column(db.Boolean, default=False)
    skills = db.Column(db.Text)
    skills_weighted = db.Column(db.Text)  # JSON for weighted skills
    qualifications = db.Column(db.Text)
    certifications = db.Column(db.Text)
    languages = db.Column(db.Text)
    resume_url = db.Column(db.String(500))
    resume_text = db.Column(db.Text)
    linkedin_url = db.Column(db.String(500))
    github_url = db.Column(db.String(500))
    portfolio_url = db.Column(db.String(500))
    source = db.Column(db.Enum('linkedin', 'naukri', 'indeed', 'referral', 'website', 'walk-in', 'job-portal', 'other'))
    source_detail = db.Column(db.String(255))
    referred_by = db.Column(db.String(255))
    tags = db.Column(db.Text)  # Comma separated tags
    status = db.Column(db.Enum('active', 'inactive', 'blacklisted'), default='active')
    created_by = db.Column(db.Integer, db.ForeignKey('users.id'))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class CandidateApplication(db.Model):
    __tablename__ = 'candidate_applications'
    id = db.Column(db.Integer, primary_key=True)
    candidate_id = db.Column(db.Integer, db.ForeignKey('candidates.id'))
    jd_id = db.Column(db.Integer, db.ForeignKey('job_descriptions.id'))
    application_code = db.Column(db.String(50), unique=True)
    application_date = db.Column(db.Date, default=date.today)
    match_score = db.Column(db.Numeric(5,2), default=0)
    match_details = db.Column(db.Text)  # JSON with detailed matching
    status = db.Column(db.Enum(
        'new', 'screening', 'shortlisted', 'interview-scheduled', 
        'interviewed', 'technical-review', 'hr-review', 'selected', 
        'offered', 'offer-accepted', 'offer-declined', 'joined', 
        'rejected', 'on-hold', 'withdrawn', 'blacklisted'
    ), default='new')
    current_stage = db.Column(db.String(50), default='application_received')
    screening_score = db.Column(db.Integer)
    screening_notes = db.Column(db.Text)
    rejection_reason = db.Column(db.Text)
    rejection_stage = db.Column(db.String(50))
    expected_joining_date = db.Column(db.Date)
    actual_joining_date = db.Column(db.Date)
    offer_details = db.Column(db.Text)
    notes = db.Column(db.Text)
    created_by = db.Column(db.Integer, db.ForeignKey('users.id'))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    candidate = db.relationship('Candidate', backref='applications')
    job = db.relationship('JobDescription', backref='applications')

class InterviewRound(db.Model):
    __tablename__ = 'interview_rounds'
    id = db.Column(db.Integer, primary_key=True)
    application_id = db.Column(db.Integer, db.ForeignKey('candidate_applications.id'))
    round_number = db.Column(db.Integer, default=1)
    round_name = db.Column(db.String(100))
    round_type = db.Column(db.Enum(
        'telephonic', 'video', 'face-to-face', 'technical', 
        'coding', 'system-design', 'managerial', 'hr', 
        'client', 'assessment', 'group-discussion', 'final'
    ))
    interviewer_name = db.Column(db.String(255))
    interviewer_email = db.Column(db.String(255))
    interviewer_designation = db.Column(db.String(255))
    scheduled_start = db.Column(db.DateTime)
    scheduled_end = db.Column(db.DateTime)
    actual_start = db.Column(db.DateTime)
    actual_end = db.Column(db.DateTime)
    duration_minutes = db.Column(db.Integer, default=60)
    meeting_link = db.Column(db.String(500))
    meeting_password = db.Column(db.String(100))
    location = db.Column(db.String(255))
    status = db.Column(db.Enum('scheduled', 'confirmed', 'rescheduled', 'completed', 'no-show', 'cancelled'), default='scheduled')
    feedback = db.Column(db.Text)
    rating_technical = db.Column(db.Integer)
    rating_communication = db.Column(db.Integer)
    rating_cultural = db.Column(db.Integer)
    overall_rating = db.Column(db.Integer)
    result = db.Column(db.Enum('pass', 'fail', 'on-hold', 'second-round'))
    decision_notes = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class OfferLetter(db.Model):
    __tablename__ = 'offer_letters'
    id = db.Column(db.Integer, primary_key=True)
    application_id = db.Column(db.Integer, db.ForeignKey('candidate_applications.id'))
    offer_code = db.Column(db.String(50), unique=True)
    offer_date = db.Column(db.Date, default=date.today)
    valid_until = db.Column(db.Date)
    designation = db.Column(db.String(255))
    department = db.Column(db.String(100))
    location = db.Column(db.String(255))
    base_salary = db.Column(db.Numeric(10,2))
    bonus_percentage = db.Column(db.Numeric(5,2), default=0)
    joining_bonus = db.Column(db.Numeric(10,2), default=0)
    benefits = db.Column(db.Text)
    terms_conditions = db.Column(db.Text)
    status = db.Column(db.Enum('draft', 'sent', 'viewed', 'accepted', 'declined', 'expired', 'revised'), default='draft')
    response_date = db.Column(db.Date)
    rejection_reason = db.Column(db.Text)
    revised_salary = db.Column(db.Numeric(10,2))
    negotiations = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class ActivityLog(db.Model):
    __tablename__ = 'activity_logs'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    entity_type = db.Column(db.String(50))
    entity_id = db.Column(db.Integer)
    action = db.Column(db.String(100))
    details = db.Column(db.Text)
    ip_address = db.Column(db.String(50))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class PipelineStage(db.Model):
    __tablename__ = 'pipeline_stages'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    order = db.Column(db.Integer, nullable=False)
    color = db.Column(db.String(7), default='#6c757d')
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

# ============= HELPER FUNCTIONS =============

def generate_code(prefix):
    """Generate unique code like JD-001, CAN-001"""
    last_record = db.session.query(func.max(db.text(f"{prefix.lower()}_code"))).first()
    if last_record and last_record[0]:
        last_num = int(last_record[0].split('-')[1])
        new_num = last_num + 1
    else:
        new_num = 1
    return f"{prefix}-{new_num:04d}"

def extract_skills_advanced(text):
    """Advanced skill extraction with weighting"""
    skill_database = {
        'programming_languages': ['Python', 'Java', 'JavaScript', 'C++', 'C#', 'Go', 'Ruby', 'PHP', 'Swift', 'Kotlin', 'TypeScript'],
        'frameworks': ['Django', 'Flask', 'Spring', 'React', 'Angular', 'Vue', 'Node.js', 'Express', 'Rails', 'Laravel'],
        'databases': ['MySQL', 'PostgreSQL', 'MongoDB', 'Redis', 'Oracle', 'SQL Server', 'Cassandra', 'DynamoDB'],
        'cloud': ['AWS', 'Azure', 'GCP', 'Heroku', 'DigitalOcean', 'Kubernetes', 'Docker', 'Terraform'],
        'data_science': ['Machine Learning', 'Deep Learning', 'NLP', 'Computer Vision', 'TensorFlow', 'PyTorch', 'Pandas', 'NumPy'],
        'soft_skills': ['Leadership', 'Communication', 'Teamwork', 'Problem Solving', 'Time Management', 'Critical Thinking']
    }
    
    text_lower = text.lower()
    found_skills = {'exact': [], 'partial': [], 'weighted': {}}
    
    for category, skills in skill_database.items():
        for skill in skills:
            if skill.lower() in text_lower:
                weight = 1.0
                if category == 'programming_languages':
                    weight = 1.5
                elif category == 'frameworks':
                    weight = 1.3
                found_skills['exact'].append(skill)
                found_skills['weighted'][skill] = weight
            elif any(word in text_lower for word in skill.lower().split()):
                found_skills['partial'].append(skill)
    
    return found_skills

def calculate_match_score_advanced(jd_skills, candidate_skills):
    """Advanced matching with weighted scoring"""
    if not jd_skills or not candidate_skills:
        return 0, {}
    
    jd_skills_list = [s.strip().lower() for s in jd_skills.split(',') if s.strip()]
    candidate_skills_list = [s.strip().lower() for s in candidate_skills.split(',') if s.strip()]
    
    match_details = {
        'exact_matches': [],
        'partial_matches': [],
        'missing_skills': [],
        'score_breakdown': {}
    }
    
    exact_matches = [s for s in jd_skills_list if s in candidate_skills_list]
    partial_matches = [s for s in jd_skills_list if any(cs for cs in candidate_skills_list if s in cs or cs in s)]
    missing_skills = [s for s in jd_skills_list if s not in exact_matches and s not in partial_matches]
    
    match_details['exact_matches'] = exact_matches
    match_details['partial_matches'] = partial_matches
    match_details['missing_skills'] = missing_skills
    
    # Calculate weighted score
    exact_score = (len(exact_matches) / len(jd_skills_list)) * 100 if jd_skills_list else 0
    partial_score = (len(partial_matches) / len(jd_skills_list)) * 50 if jd_skills_list else 0
    
    match_details['score_breakdown'] = {
        'exact_match_score': round(exact_score, 2),
        'partial_match_score': round(partial_score, 2),
        'total_score': round(min(100, exact_score + partial_score), 2)
    }
    
    total_score = min(100, exact_score + partial_score)
    
    return round(total_score, 2), match_details

def log_activity(user_id, entity_type, entity_id, action, details=None, ip=None):
    """Log user activity"""
    log = ActivityLog(
        user_id=user_id,
        entity_type=entity_type,
        entity_id=entity_id,
        action=action,
        details=json.dumps(details) if details else None,
        ip_address=ip
    )
    db.session.add(log)
    db.session.commit()

def send_email_with_template(recipient, template_name, data):
    """Send templated email"""
    templates = {
        'application_received': {
            'subject': 'Application Received - {job_title}',
            'body': """Dear {candidate_name},

Thank you for applying for the {job_title} position at {company_name}.

We have received your application and our team is reviewing it. You will be notified about the next steps soon.

Application ID: {application_id}
Match Score: {match_score}%

Best regards,
Recruitment Team
ShahnaIT Scout"""
        },
        'interview_scheduled': {
            'subject': 'Interview Scheduled - {job_title}',
            'body': """Dear {candidate_name},

Your interview has been scheduled for the {job_title} position.

📅 Date: {interview_date}
⏰ Time: {interview_time}
👤 Interviewer: {interviewer}
🔗 Meeting Link: {meeting_link}

Please join 5 minutes before the scheduled time.

Best regards,
Recruitment Team"""
        },
        'offer_letter': {
            'subject': 'Offer Letter - {job_title}',
            'body': """Dear {candidate_name},

Congratulations! We are pleased to offer you the position of {job_title} at {company_name}.

📄 Offer Details:
- Designation: {designation}
- Location: {location}
- Base Salary: {salary}
- Joining Date: {joining_date}

Please review the attached offer letter and respond by {valid_until}.

We look forward to having you on the team!

Best regards,
Recruitment Team"""
        },
        'rejection': {
            'subject': 'Application Update - {job_title}',
            'body': """Dear {candidate_name},

Thank you for your interest in the {job_title} position at {company_name}.

After careful review, we regret to inform you that we have decided to move forward with other candidates whose qualifications more closely match our current requirements.

We appreciate your interest and encourage you to apply for future openings.

Best regards,
Recruitment Team"""
        }
    }
    
    template = templates.get(template_name, {})
    if template:
        subject = template['subject'].format(**data)
        body = template['body'].format(**data)
        
        try:
            msg = Message(subject, recipients=[recipient])
            msg.body = body
            mail.send(msg)
            return True
        except Exception as e:
            print(f"Email error: {e}")
            return False
    return False

# ============= API ROUTES =============

@app.route('/')
def index():
    """Main dashboard"""
    return render_template('dashboard.html')

@app.route('/api/dashboard/stats')
def dashboard_stats():
    """Get complete dashboard statistics"""
    stats = {
        'overview': {
            'total_jobs': JobDescription.query.count(),
            'open_positions': JobDescription.query.filter(JobDescription.status.in_(['open', 'published'])).count(),
            'total_candidates': Candidate.query.count(),
            'active_candidates': Candidate.query.filter_by(status='active').count(),
            'total_applications': CandidateApplication.query.count(),
            'applications_this_month': CandidateApplication.query.filter(
                func.month(CandidateApplication.application_date) == datetime.now().month
            ).count(),
            'interviews_today': InterviewRound.query.filter(
                func.date(InterviewRound.scheduled_start) == date.today(),
                InterviewRound.status == 'scheduled'
            ).count(),
            'interviews_this_week': InterviewRound.query.filter(
                func.week(InterviewRound.scheduled_start) == datetime.now().isocalendar()[1]
            ).count(),
            'offers_sent': OfferLetter.query.filter_by(status='sent').count(),
            'offers_accepted': OfferLetter.query.filter_by(status='accepted').count(),
            'hired_this_month': CandidateApplication.query.filter(
                CandidateApplication.status == 'joined',
                func.month(CandidateApplication.actual_joining_date) == datetime.now().month
            ).count(),
            'conversion_rate': 0
        },
        'pipeline': {
            'new': CandidateApplication.query.filter_by(status='new').count(),
            'screening': CandidateApplication.query.filter_by(status='screening').count(),
            'shortlisted': CandidateApplication.query.filter_by(status='shortlisted').count(),
            'interview_scheduled': CandidateApplication.query.filter_by(status='interview-scheduled').count(),
            'interviewed': CandidateApplication.query.filter_by(status='interviewed').count(),
            'selected': CandidateApplication.query.filter_by(status='selected').count(),
            'offered': CandidateApplication.query.filter_by(status='offered').count(),
            'joined': CandidateApplication.query.filter_by(status='joined').count(),
            'rejected': CandidateApplication.query.filter_by(status='rejected').count()
        },
        'sources': db.session.query(
            Candidate.source, func.count(Candidate.id)
        ).group_by(Candidate.source).all(),
        'recent_activities': ActivityLog.query.order_by(ActivityLog.created_at.desc()).limit(20).all(),
        'top_performing_jds': db.session.query(
            JobDescription.title, func.count(CandidateApplication.id).label('app_count')
        ).join(CandidateApplication).group_by(JobDescription.id).order_by(db.text('app_count DESC')).limit(5).all()
    }
    
    # Calculate conversion rate
    total_apps = stats['overview']['total_applications']
    hired = stats['overview']['hired_this_month']
    stats['overview']['conversion_rate'] = round((hired / total_apps) * 100, 2) if total_apps > 0 else 0
    
    # Format for JSON response
    return jsonify({
        'overview': stats['overview'],
        'pipeline': stats['pipeline'],
        'sources': [{'source': s[0], 'count': s[1]} for s in stats['sources'] if s[0]],
        'recent_activities': [{
            'id': a.id,
            'action': a.action,
            'details': json.loads(a.details) if a.details else None,
            'created_at': a.created_at.isoformat() if a.created_at else None
        } for a in stats['recent_activities']],
        'top_jds': [{'title': j[0], 'applications': j[1]} for j in stats['top_performing_jds']]
    })

@app.route('/api/jds', methods=['GET', 'POST'])
def manage_jds():
    """List, create, and manage job descriptions"""
    
    if request.method == 'GET':
        # Get all JDs with filters
        status_filter = request.args.get('status')
        priority_filter = request.args.get('priority')
        client_filter = request.args.get('client_id')
        
        query = JobDescription.query
        if status_filter:
            query = query.filter_by(status=status_filter)
        if priority_filter:
            query = query.filter_by(priority=priority_filter)
        if client_filter:
            query = query.filter_by(client_id=client_filter)
        
        jds = query.order_by(JobDescription.created_at.desc()).all()
        
        return jsonify([{
            'id': j.id,
            'code': j.jd_code,
            'title': j.title,
            'client': j.client.company_name if j.client else None,
            'location': j.location,
            'location_type': j.location_type,
            'employment_type': j.employment_type,
            'experience_min': j.experience_min,
            'experience_max': j.experience_max,
            'salary_min': float(j.salary_min) if j.salary_min else None,
            'salary_max': float(j.salary_max) if j.salary_max else None,
            'status': j.status,
            'priority': j.priority,
            'applications': len(j.applications),
            'filled_positions': len([a for a in j.applications if a.status == 'joined']),
            'created_at': j.created_at.isoformat() if j.created_at else None
        } for j in jds])
    
    elif request.method == 'POST':
        data = request.json
        
        # Generate JD code
        jd_code = generate_code('JD')
        
        jd = JobDescription(
            jd_code=jd_code,
            client_id=data.get('client_id'),
            title=data.get('title'),
            department=data.get('department'),
            location=data.get('location'),
            location_type=data.get('location_type', 'remote'),
            employment_type=data.get('employment_type', 'full-time'),
            experience_min=data.get('experience_min', 0),
            experience_max=data.get('experience_max', 10),
            salary_min=data.get('salary_min'),
            salary_max=data.get('salary_max'),
            no_of_positions=data.get('no_of_positions', 1),
            skills_required=data.get('skills_required'),
            skills_preferred=data.get('skills_preferred'),
            qualifications=data.get('qualifications'),
            responsibilities=data.get('responsibilities'),
            benefits=data.get('benefits'),
            status=data.get('status', 'draft'),
            priority=data.get('priority', 'medium'),
            target_closure_date=datetime.strptime(data.get('target_closure_date'), '%Y-%m-%d').date() if data.get('target_closure_date') else None
        )
        
        db.session.add(jd)
        db.session.commit()
        
        # Log activity
        log_activity(None, 'job_description', jd.id, 'created', {'title': jd.title})
        
        return jsonify({'success': True, 'jd_id': jd.id, 'jd_code': jd.jd_code})

@app.route('/api/jds/<int:jd_id>/parse', methods=['POST'])
def parse_jd_document(jd_id):
    """Parse uploaded JD document and auto-fill details"""
    
    if 'file' not in request.files:
        return jsonify({'error': 'No file uploaded'}), 400
    
    file = request.files['file']
    
    # Extract text from document
    text = ''
    if file.filename.endswith('.pdf'):
        import PyPDF2
        reader = PyPDF2.PdfReader(file)
        for page in reader.pages:
            text += page.extract_text()
    elif file.filename.endswith('.docx'):
        import docx
        doc = docx.Document(file)
        text = '\n'.join([para.text for para in doc.paragraphs])
    else:
        text = file.read().decode('utf-8')
    
    # Parse using NLP/AI
    extracted = {
        'title': extract_job_title(text),
        'skills_required': extract_skills_advanced(text)['exact'],
        'qualifications': extract_qualifications(text),
        'experience_min': extract_experience(text)['min'],
        'experience_max': extract_experience(text)['max'],
        'location': extract_location(text),
        'employment_type': extract_employment_type(text),
        'responsibilities': extract_responsibilities(text)
    }
    
    # Update JD with extracted data
    jd = JobDescription.query.get(jd_id)
    if jd:
        jd.title = extracted['title'] or jd.title
        jd.skills_required = ', '.join(extracted['skills_required']) if extracted['skills_required'] else jd.skills_required
        jd.qualifications = extracted['qualifications'] or jd.qualifications
        jd.experience_min = extracted['experience_min'] or jd.experience_min
        jd.experience_max = extracted['experience_max'] or jd.experience_max
        jd.location = extracted['location'] or jd.location
        jd.employment_type = extracted['employment_type'] or jd.employment_type
        jd.responsibilities = extracted['responsibilities'] or jd.responsibilities
        db.session.commit()
    
    return jsonify({
        'success': True,
        'extracted': extracted,
        'message': 'JD parsed successfully'
    })

# Helper functions for parsing
def extract_job_title(text):
    """Extract job title from text"""
    patterns = [
        r'Job Title:?\s*(.+?)(?:\n|$)',
        r'Position:?\s*(.+?)(?:\n|$)',
        r'Role:?\s*(.+?)(?:\n|$)',
        r'^([A-Z][a-z]+ (?:[A-Z][a-z]+ )*(?:Developer|Engineer|Manager|Architect|Lead|Consultant))'
    ]
    for pattern in patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            return match.group(1).strip()
    return None

def extract_qualifications(text):
    """Extract qualifications from text"""
    keywords = ['Bachelor', 'Master', 'B.Tech', 'M.Tech', 'BCA', 'MCA', 'MBA', 'PhD', 'Degree', 'Diploma']
    found = []
    for keyword in keywords:
        if keyword.lower() in text.lower():
            context = re.search(f'.{{0,50}}{keyword}.{{0,100}}', text, re.IGNORECASE)
            if context:
                found.append(context.group().strip())
    return '\n'.join(found[:3]) if found else None

def extract_experience(text):
    """Extract experience requirements"""
    patterns = [
        r'(\d+)\s*-\s*(\d+)\s*years?',
        r'(\d+)\s*\+\s*years?',
        r'minimum\s+(\d+)\s*years?',
        r'(\d+)\s*years?\s+experience'
    ]
    result = {'min': None, 'max': None}
    for pattern in patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            if len(match.groups()) == 2:
                result['min'] = int(match.group(1))
                result['max'] = int(match.group(2))
            else:
                result['min'] = int(match.group(1))
                result['max'] = int(match.group(1)) + 5
            break
    return result

def extract_location(text):
    """Extract location from text"""
    location_patterns = [
        r'Location:?\s*(.+?)(?:\n|$)',
        r'Work Location:?\s*(.+?)(?:\n|$)',
        r'Based in:?\s*(.+?)(?:\n|$)'
    ]
    for pattern in location_patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            return match.group(1).strip()
    
    # Look for common city names
    cities = ['Bangalore', 'Mumbai', 'Delhi', 'Hyderabad', 'Chennai', 'Pune', 'Kolkata', 'Ahmedabad', 'Remote']
    for city in cities:
        if city.lower() in text.lower():
            return city
    return None

def extract_employment_type(text):
    """Extract employment type"""
    text_lower = text.lower()
    if 'remote' in text_lower:
        return 'remote'
    elif 'hybrid' in text_lower:
        return 'hybrid'
    elif 'onsite' in text_lower or 'office' in text_lower:
        return 'onsite'
    return 'full-time'

def extract_responsibilities(text):
    """Extract responsibilities from text"""
    patterns = [
        r'Responsibilities:?(.+?)(?:\n\n|\Z)',
        r'Key Responsibilities:?(.+?)(?:\n\n|\Z)',
        r'What you\'ll do:?(.+?)(?:\n\n|\Z)'
    ]
    for pattern in patterns:
        match = re.search(pattern, text, re.IGNORECASE | re.DOTALL)
        if match:
            return match.group(1).strip()
    return None

@app.route('/api/candidates', methods=['GET', 'POST'])
def manage_candidates():
    """List, create, and manage candidates"""
    
    if request.method == 'GET':
        # Get candidates with filters
        status_filter = request.args.get('status')
        skill_filter = request.args.get('skill')
        source_filter = request.args.get('source')
        page = int(request.args.get('page', 1))
        per_page = int(request.args.get('per_page', 20))
        
        query = Candidate.query.filter_by(status='active')
        
        if skill_filter:
            query = query.filter(Candidate.skills.ilike(f'%{skill_filter}%'))
        if source_filter:
            query = query.filter_by(source=source_filter)
        
        pagination = query.paginate(page=page, per_page=per_page, error_out=False)
        
        return jsonify({
            'candidates': [{
                'id': c.id,
                'code': c.candidate_code,
                'name': f"{c.first_name} {c.last_name}",
                'email': c.email,
                'phone': c.phone,
                'current_company': c.current_company,
                'current_designation': c.current_designation,
                'total_experience': float(c.total_experience_years) if c.total_experience_years else 0,
                'skills': c.skills,
                'source': c.source,
                'created_at': c.created_at.isoformat() if c.created_at else None
            } for c in pagination.items],
            'total': pagination.total,
            'page': page,
            'per_page': per_page,
            'pages': pagination.pages
        })
    
    elif request.method == 'POST':
        data = request.json
        
        # Check if candidate exists
        existing = Candidate.query.filter_by(email=data.get('email')).first()
        if existing:
            return jsonify({'error': 'Candidate with this email already exists', 'candidate_id': existing.id}), 409
        
        # Generate candidate code
        candidate_code = generate_code('CAN')
        
        candidate = Candidate(
            candidate_code=candidate_code,
            first_name=data.get('first_name'),
            last_name=data.get('last_name'),
            email=data.get('email'),
            phone=data.get('phone'),
            current_location=data.get('current_location'),
            current_company=data.get('current_company'),
            current_designation=data.get('current_designation'),
            total_experience_years=data.get('total_experience', 0),
            skills=data.get('skills'),
            qualifications=data.get('qualifications'),
            expected_salary=data.get('expected_salary'),
            notice_period_days=data.get('notice_period'),
            source=data.get('source', 'website'),
            status='active'
        )
        
        db.session.add(candidate)
        db.session.commit()
        
        log_activity(None, 'candidate', candidate.id, 'created', {'name': f"{candidate.first_name} {candidate.last_name}"})
        
        return jsonify({'success': True, 'candidate_id': candidate.id, 'candidate_code': candidate.candidate_code})

@app.route('/api/candidates/parse-resume', methods=['POST'])
def parse_resume():
    """Parse uploaded resume and auto-fill candidate details"""
    
    if 'file' not in request.files:
        return jsonify({'error': 'No file uploaded'}), 400
    
    file = request.files['file']
    
    # Extract text from resume
    text = ''
    if file.filename.endswith('.pdf'):
        import PyPDF2
        reader = PyPDF2.PdfReader(file)
        for page in reader.pages:
            text += page.extract_text()
    elif file.filename.endswith('.docx'):
        import docx
        doc = docx.Document(file)
        text = '\n'.join([para.text for para in doc.paragraphs])
    else:
        text = file.read().decode('utf-8')
    
    # Parse resume data
    parsed = {
        'first_name': extract_name(text)['first'],
        'last_name': extract_name(text)['last'],
        'email': extract_email(text),
        'phone': extract_phone(text),
        'skills': extract_skills_advanced(text)['exact'],
        'qualifications': extract_qualifications(text),
        'total_experience': extract_experience(text)['max'],
        'current_company': extract_company(text),
        'current_designation': extract_designation(text),
        'current_location': extract_location(text)
    }
    
    return jsonify({
        'success': True,
        'data': parsed
    })

def extract_name(text):
    """Extract name from text"""
    # Look for name patterns at the beginning of resume
    lines = text.split('\n')[:10]
    for line in lines:
        # Name typically appears in first few lines, all caps or title case
        if len(line.strip().split()) <= 3 and line.strip() and not any(x in line.lower() for x in ['resume', 'curriculum', 'vitae', 'email', 'phone']):
            name_parts = line.strip().split()
            if len(name_parts) >= 2:
                return {'first': name_parts[0], 'last': name_parts[-1]}
    return {'first': None, 'last': None}

def extract_email(text):
    """Extract email from text"""
    pattern = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
    match = re.search(pattern, text)
    return match.group(0) if match else None

def extract_phone(text):
    """Extract phone number from text"""
    patterns = [
        r'\b\d{10}\b',
        r'\b\d{3}[-.]?\d{3}[-.]?\d{4}\b',
        r'\+\d{1,2}\s?\d{10}\b'
    ]
    for pattern in patterns:
        match = re.search(pattern, text)
        if match:
            return match.group(0)
    return None

def extract_company(text):
    """Extract current company from text"""
    # Look for "Current Company" or "Work Experience" sections
    patterns = [
        r'Current Company:?\s*(.+?)(?:\n|$)',
        r'Employer:?\s*(.+?)(?:\n|$)',
        r'Work Experience.*?\n(?:.*?\n){1,5}?(.+?)(?:\n|$)'
    ]
    for pattern in patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            return match.group(1).strip()
    return None

def extract_designation(text):
    """Extract current designation from text"""
    patterns = [
        r'Designation:?\s*(.+?)(?:\n|$)',
        r'Title:?\s*(.+?)(?:\n|$)',
        r'Position:?\s*(.+?)(?:\n|$)'
    ]
    for pattern in patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            return match.group(1).strip()
    
    # Look for common job titles
    titles = ['Developer', 'Engineer', 'Manager', 'Lead', 'Architect', 'Consultant', 'Analyst', 'Specialist']
    for title in titles:
        if title.lower() in text.lower():
            context = re.search(f'.{{0,30}}{title}.{{0,30}}', text, re.IGNORECASE)
            if context:
                return context.group().strip()
    return None

@app.route('/api/applications', methods=['GET', 'POST'])
def manage_applications():
    """Manage candidate applications"""
    
    if request.method == 'POST':
        data = request.json
        
        # Check if application already exists
        existing = CandidateApplication.query.filter_by(
            candidate_id=data.get('candidate_id'),
            jd_id=data.get('jd_id')
        ).first()
        
        if existing:
            return jsonify({'error': 'Application already exists', 'application_id': existing.id}), 409
        
        # Calculate match score
        jd = JobDescription.query.get(data.get('jd_id'))
        candidate = Candidate.query.get(data.get('candidate_id'))
        
        match_score, match_details = calculate_match_score_advanced(
            jd.skills_required if jd else '',
            candidate.skills if candidate else ''
        )
        
        # Generate application code
        app_code = generate_code('APP')
        
        application = CandidateApplication(
            application_code=app_code,
            candidate_id=data.get('candidate_id'),
            jd_id=data.get('jd_id'),
            match_score=match_score,
            match_details=json.dumps(match_details),
            status='new',
            application_date=date.today()
        )
        
        db.session.add(application)
        db.session.commit()
        
        # Send email notification
        if candidate and jd:
            send_email_with_template(
                candidate.email,
                'application_received',
                {
                    'candidate_name': f"{candidate.first_name} {candidate.last_name}",
                    'job_title': jd.title,
                    'company_name': jd.client.company_name if jd.client else 'our company',
                    'application_id': application.application_code,
                    'match_score': match_score
                }
            )
        
        log_activity(None, 'application', application.id, 'created', {'candidate': candidate.candidate_code, 'job': jd.jd_code if jd else None})
        
        return jsonify({'success': True, 'application_id': application.id, 'match_score': match_score})
    
    elif request.method == 'GET':
        # Get all applications with filters
        status_filter = request.args.get('status')
        jd_filter = request.args.get('jd_id')
        
        query = CandidateApplication.query
        if status_filter:
            query = query.filter_by(status=status_filter)
        if jd_filter:
            query = query.filter_by(jd_id=jd_filter)
        
        applications = query.order_by(CandidateApplication.created_at.desc()).all()
        
        return jsonify([{
            'id': a.id,
            'code': a.application_code,
            'candidate': {
                'id': a.candidate.id,
                'name': f"{a.candidate.first_name} {a.candidate.last_name}",
                'email': a.candidate.email
            } if a.candidate else None,
            'job': {
                'id': a.job.id,
                'title': a.job.title
            } if a.job else None,
            'match_score': float(a.match_score) if a.match_score else 0,
            'status': a.status,
            'application_date': a.application_date.isoformat() if a.application_date else None
        } for a in applications])

@app.route('/api/applications/<int:app_id>/move', methods=['PUT'])
def move_application_stage(app_id):
    """Move application to next pipeline stage"""
    data = request.json
    new_stage = data.get('stage')
    
    application = CandidateApplication.query.get_or_404(app_id)
    old_stage = application.status
    application.status = new_stage
    application.updated_at = datetime.utcnow()
    
    db.session.commit()
    
    log_activity(None, 'application', app_id, 'stage_changed', {
        'from': old_stage,
        'to': new_stage
    })
    
    # Trigger actions based on stage
    if new_stage == 'shortlisted':
        # Send shortlisted email
        if application.candidate:
            send_email_with_template(
                application.candidate.email,
                'interview_scheduled' if data.get('schedule_interview') else 'shortlisted',
                {
                    'candidate_name': f"{application.candidate.first_name} {application.candidate.last_name}",
                    'job_title': application.job.title if application.job else 'the position'
                }
            )
    elif new_stage == 'rejected':
        # Send rejection email
        if application.candidate:
            send_email_with_template(
                application.candidate.email,
                'rejection',
                {
                    'candidate_name': f"{application.candidate.first_name} {application.candidate.last_name}",
                    'job_title': application.job.title if application.job else 'the position',
                    'company_name': application.job.client.company_name if application.job and application.job.client else 'our company'
                }
            )
    
    return jsonify({'success': True, 'message': f'Moved from {old_stage} to {new_stage}'})

@app.route('/api/interviews', methods=['GET', 'POST'])
def manage_interviews():
    """Schedule and manage interviews"""
    
    if request.method == 'POST':
        data = request.json
        
        interview = InterviewRound(
            application_id=data.get('application_id'),
            round_number=data.get('round_number', 1),
            round_name=data.get('round_name'),
            round_type=data.get('round_type'),
            interviewer_name=data.get('interviewer_name'),
            interviewer_email=data.get('interviewer_email'),
            scheduled_start=datetime.fromisoformat(data.get('scheduled_start')) if data.get('scheduled_start') else None,
            scheduled_end=datetime.fromisoformat(data.get('scheduled_end')) if data.get('scheduled_end') else None,
            meeting_link=data.get('meeting_link'),
            status='scheduled'
        )
        
        db.session.add(interview)
        
        # Update application status
        application = CandidateApplication.query.get(data.get('application_id'))
        if application:
            application.status = 'interview-scheduled'
        
        db.session.commit()
        
        # Send interview invitation
        application = CandidateApplication.query.get(data.get('application_id'))
        if application and application.candidate:
            send_email_with_template(
                application.candidate.email,
                'interview_scheduled',
                {
                    'candidate_name': f"{application.candidate.first_name} {application.candidate.last_name}",
                    'job_title': application.job.title if application.job else 'the position',
                    'interview_date': interview.scheduled_start.strftime('%B %d, %Y') if interview.scheduled_start else 'TBD',
                    'interview_time': interview.scheduled_start.strftime('%I:%M %p') if interview.scheduled_start else 'TBD',
                    'interviewer': interview.interviewer_name or 'our team',
                    'meeting_link': interview.meeting_link or 'will be shared separately'
                }
            )
        
        return jsonify({'success': True, 'interview_id': interview.id})
    
    elif request.method == 'GET':
        # Get upcoming interviews
        today = datetime.now()
        interviews = InterviewRound.query.filter(
            InterviewRound.scheduled_start >= today,
            InterviewRound.status == 'scheduled'
        ).order_by(InterviewRound.scheduled_start).limit(50).all()
        
        return jsonify([{
            'id': i.id,
            'candidate_name': f"{i.application.candidate.first_name} {i.application.candidate.last_name}" if i.application and i.application.candidate else None,
            'job_title': i.application.job.title if i.application and i.application.job else None,
            'round_type': i.round_type,
            'interviewer': i.interviewer_name,
            'scheduled_start': i.scheduled_start.isoformat() if i.scheduled_start else None,
            'meeting_link': i.meeting_link,
            'status': i.status
        } for i in interviews])

@app.route('/api/interviews/<int:interview_id>/feedback', methods=['POST'])
def submit_interview_feedback(interview_id):
    """Submit feedback for an interview"""
    data = request.json
    
    interview = InterviewRound.query.get_or_404(interview_id)
    interview.feedback = data.get('feedback')
    interview.rating_technical = data.get('rating_technical')
    interview.rating_communication = data.get('rating_communication')
    interview.rating_cultural = data.get('rating_cultural')
    interview.overall_rating = data.get('overall_rating')
    interview.result = data.get('result')
    interview.status = 'completed'
    interview.actual_end = datetime.now()
    
    db.session.commit()
    
    # Update application status based on interview result
    if interview.application:
        if data.get('result') == 'pass':
            # Move to next round or select
            if interview.round_number >= 3:  # Assuming 3 rounds max
                interview.application.status = 'selected'
            else:
                interview.application.status = 'interviewed'
        elif data.get('result') == 'fail':
            interview.application.status = 'rejected'
    
    db.session.commit()
    
    log_activity(None, 'interview', interview_id, 'feedback_submitted', {
        'result': data.get('result'),
        'rating': data.get('overall_rating')
    })
    
    return jsonify({'success': True})

@app.route('/api/offers', methods=['GET', 'POST'])
def manage_offers():
    """Generate and manage offer letters"""
    
    if request.method == 'POST':
        data = request.json
        
        application = CandidateApplication.query.get(data.get('application_id'))
        if not application:
            return jsonify({'error': 'Application not found'}), 404
        
        # Generate offer code
        offer_code = generate_code('OFF')
        
        offer = OfferLetter(
            offer_code=offer_code,
            application_id=data.get('application_id'),
            offer_date=date.today(),
            valid_until=datetime.strptime(data.get('valid_until'), '%Y-%m-%d').date() if data.get('valid_until') else date.today() + timedelta(days=15),
            designation=data.get('designation'),
            location=data.get('location'),
            base_salary=data.get('base_salary'),
            bonus_percentage=data.get('bonus_percentage', 0),
            joining_bonus=data.get('joining_bonus', 0),
            benefits=data.get('benefits'),
            terms_conditions=data.get('terms_conditions'),
            status='draft'
        )
        
        db.session.add(offer)
        
        # Update application status
        application.status = 'offered'
        
        db.session.commit()
        
        return jsonify({'success': True, 'offer_id': offer.id, 'offer_code': offer.offer_code})
    
    elif request.method == 'GET':
        offers = OfferLetter.query.order_by(OfferLetter.created_at.desc()).limit(50).all()
        
        return jsonify([{
            'id': o.id,
            'code': o.offer_code,
            'candidate_name': f"{o.application.candidate.first_name} {o.application.candidate.last_name}" if o.application and o.application.candidate else None,
            'job_title': o.application.job.title if o.application and o.application.job else None,
            'base_salary': float(o.base_salary) if o.base_salary else None,
            'status': o.status,
            'offer_date': o.offer_date.isoformat() if o.offer_date else None,
            'valid_until': o.valid_until.isoformat() if o.valid_until else None
        } for o in offers])

@app.route('/api/offers/<int:offer_id>/send', methods=['POST'])
def send_offer(offer_id):
    """Send offer letter to candidate"""
    
    offer = OfferLetter.query.get_or_404(offer_id)
    offer.status = 'sent'
    db.session.commit()
    
    # Send email with offer
    if offer.application and offer.application.candidate:
        send_email_with_template(
            offer.application.candidate.email,
            'offer_letter',
            {
                'candidate_name': f"{offer.application.candidate.first_name} {offer.application.candidate.last_name}",
                'job_title': offer.application.job.title if offer.application.job else 'the position',
                'company_name': offer.application.job.client.company_name if offer.application.job and offer.application.job.client else 'our company',
                'designation': offer.designation,
                'location': offer.location,
                'salary': f"${float(offer.base_salary):,.2f}" if offer.base_salary else 'TBD',
                'joining_date': offer.application.expected_joining_date.strftime('%B %d, %Y') if offer.application.expected_joining_date else 'TBD',
                'valid_until': offer.valid_until.strftime('%B %d, %Y') if offer.valid_until else 'TBD'
            }
        )
    
    log_activity(None, 'offer', offer_id, 'sent', {'candidate': offer.application.candidate.email if offer.application and offer.application.candidate else None})
    
    return jsonify({'success': True, 'message': 'Offer sent successfully'})

@app.route('/api/clients', methods=['GET', 'POST'])
def manage_clients():
    """Manage client companies"""
    
    if request.method == 'POST':
        data = request.json
        
        client = Client(
            company_name=data.get('company_name'),
            industry=data.get('industry'),
            contact_person=data.get('contact_person'),
            email=data.get('email'),
            phone=data.get('phone'),
            address=data.get('address'),
            status='active'
        )
        
        db.session.add(client)
        db.session.commit()
        
        return jsonify({'success': True, 'client_id': client.id})
    
    elif request.method == 'GET':
        clients = Client.query.filter_by(status='active').all()
        
        return jsonify([{
            'id': c.id,
            'company_name': c.company_name,
            'industry': c.industry,
            'contact_person': c.contact_person,
            'email': c.email,
            'phone': c.phone,
            'active_jobs': len([j for j in c.job_descriptions if j.status in ['open', 'published']])
        } for c in clients])

@app.route('/api/reports/pipeline', methods=['GET'])
def pipeline_report():
    """Get pipeline analytics"""
    
    # Get date range
    days = int(request.args.get('days', 30))
    start_date = date.today() - timedelta(days=days)
    
    # Daily pipeline data
    daily_data = db.session.query(
        func.date(CandidateApplication.created_at).label('date'),
        func.count(CandidateApplication.id).label('applications')
    ).filter(
        CandidateApplication.created_at >= start_date
    ).group_by(func.date(CandidateApplication.created_at)).all()
    
    # Stage distribution
    stage_distribution = db.session.query(
        CandidateApplication.status,
        func.count(CandidateApplication.id)
    ).group_by(CandidateApplication.status).all()
    
    # Source effectiveness
    source_effectiveness = db.session.query(
        Candidate.source,
        func.count(Candidate.id).label('total'),
        func.count(CandidateApplication.id).label('hired')
    ).outerjoin(CandidateApplication).group_by(Candidate.source).all()
    
    # Time to fill analysis
    filled_jobs = JobDescription.query.filter(
        JobDescription.status == 'fulfilled',
        JobDescription.actual_closure_date.isnot(None),
        JobDescription.publish_date.isnot(None)
    ).all()
    
    time_to_fill = []
    for job in filled_jobs:
        days_to_fill = (job.actual_closure_date - job.publish_date).days
        time_to_fill.append(days_to_fill)
    
    avg_time_to_fill = sum(time_to_fill) / len(time_to_fill) if time_to_fill else 0
    
    return jsonify({
        'daily_applications': [{'date': d[0].isoformat(), 'count': d[1]} for d in daily_data],
        'stage_distribution': [{'stage': s[0], 'count': s[1]} for s in stage_distribution],
        'source_effectiveness': [{
            'source': s[0],
            'total': s[1],
            'hired': s[2] or 0,
            'conversion_rate': round((s[2] or 0) / s[1] * 100, 2) if s[1] > 0 else 0
        } for s in source_effectiveness],
        'average_time_to_fill_days': round(avg_time_to_fill, 1)
    })

# ============= INITIALIZATION =============

def init_pipeline_stages():
    """Initialize default pipeline stages"""
    stages = [
        ('New Application', 1, '#6c757d'),
        ('Screening', 2, '#17a2b8'),
        ('Shortlisted', 3, '#28a745'),
        ('Interview Scheduled', 4, '#007bff'),
        ('Interviewed', 5, '#ffc107'),
        ('Technical Review', 6, '#fd7e14'),
        ('Selected', 7, '#20c997'),
        ('Offered', 8, '#6610f2'),
        ('Joined', 9, '#28a745')
    ]
    
    for name, order, color in stages:
        existing = PipelineStage.query.filter_by(name=name).first()
        if not existing:
            stage = PipelineStage(name=name, order=order, color=color)
            db.session.add(stage)
    
    db.session.commit()

@app.cli.command('init-db')
def init_db():
    """Initialize database with all tables and default data"""
    db.create_all()
    init_pipeline_stages()
    
    # Create default admin user if not exists
    admin = User.query.filter_by(username='admin').first()
    if not admin:
        admin = User(
            username='admin',
            email='admin@shahnaiT.com',
            password_hash=hashlib.sha256('admin123'.encode()).hexdigest(),
            role='admin'
        )
        db.session.add(admin)
        db.session.commit()
    
    print("✅ Database initialized successfully!")
    print("✅ Default admin user created: admin / admin123")
    print("✅ Pipeline stages created")

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=int(os.environ.get('PORT', 5000)))
