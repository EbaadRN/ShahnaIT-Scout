# app.py - COMPLETE WORKING VERSION
from flask import Flask, request, jsonify, render_template, redirect, url_for
from flask_sqlalchemy import SQLAlchemy
from flask_mail import Mail, Message
from datetime import datetime, date, timedelta
import os
import json
import re
from sqlalchemy import and_, or_, func

app = Flask(__name__)

# Configuration - Use environment variables for production
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL', 'mysql+pymysql://root:password@localhost:3306/recruitment_db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'dev-secret-key-change-in-production')

# Email configuration
app.config['MAIL_SERVER'] = os.environ.get('MAIL_SERVER', 'smtp.gmail.com')
app.config['MAIL_PORT'] = int(os.environ.get('MAIL_PORT', 587))
app.config['MAIL_USE_TLS'] = True
app.config['MAIL_USERNAME'] = os.environ.get('MAIL_USERNAME', '')
app.config['MAIL_PASSWORD'] = os.environ.get('MAIL_PASSWORD', '')
app.config['MAIL_DEFAULT_SENDER'] = os.environ.get('MAIL_DEFAULT_SENDER', 'noreply@recruitment.com')

db = SQLAlchemy(app)
mail = Mail(app)

# ============= DATABASE MODELS =============

class Client(db.Model):
    __tablename__ = 'clients'
    id = db.Column(db.Integer, primary_key=True)
    company_name = db.Column(db.String(255), nullable=False)
    industry = db.Column(db.String(100))
    contact_person = db.Column(db.String(255))
    email = db.Column(db.String(255))
    phone = db.Column(db.String(20))
    address = db.Column(db.Text)
    status = db.Column(db.Enum('active', 'inactive', 'prospect'), default='active')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class JobDescription(db.Model):
    __tablename__ = 'job_descriptions'
    id = db.Column(db.Integer, primary_key=True)
    client_id = db.Column(db.Integer, db.ForeignKey('clients.id'))
    title = db.Column(db.String(255), nullable=False)
    department = db.Column(db.String(100))
    location = db.Column(db.String(255))
    employment_type = db.Column(db.Enum('full-time', 'part-time', 'contract', 'freelance'))
    experience_required = db.Column(db.String(50))
    salary_range_min = db.Column(db.Numeric(10,2))
    salary_range_max = db.Column(db.Numeric(10,2))
    no_of_positions = db.Column(db.Integer, default=1)
    skills_required = db.Column(db.Text)
    qualifications = db.Column(db.Text)
    responsibilities = db.Column(db.Text)
    status = db.Column(db.Enum('draft', 'open', 'in-progress', 'on-hold', 'closed', 'fulfilled'), default='draft')
    priority = db.Column(db.Enum('low', 'medium', 'high', 'urgent'), default='medium')
    target_closure_date = db.Column(db.Date)
    actual_closure_date = db.Column(db.Date)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    client = db.relationship('Client', backref='job_descriptions')

class Candidate(db.Model):
    __tablename__ = 'candidates'
    id = db.Column(db.Integer, primary_key=True)
    first_name = db.Column(db.String(100), nullable=False)
    last_name = db.Column(db.String(100))
    email = db.Column(db.String(255), unique=True, nullable=False)
    phone = db.Column(db.String(20))
    current_location = db.Column(db.String(255))
    current_company = db.Column(db.String(255))
    current_designation = db.Column(db.String(255))
    total_experience = db.Column(db.Numeric(4,1))
    relevant_experience = db.Column(db.Numeric(4,1))
    current_salary = db.Column(db.Numeric(10,2))
    expected_salary = db.Column(db.Numeric(10,2))
    notice_period = db.Column(db.Integer)
    skills = db.Column(db.Text)
    qualifications = db.Column(db.Text)
    resume_path = db.Column(db.String(500))
    source = db.Column(db.Enum('job-portal', 'linkedin', 'referral', 'website', 'agency', 'walk-in', 'other'))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class CandidateApplication(db.Model):
    __tablename__ = 'candidate_applications'
    id = db.Column(db.Integer, primary_key=True)
    candidate_id = db.Column(db.Integer, db.ForeignKey('candidates.id'))
    jd_id = db.Column(db.Integer, db.ForeignKey('job_descriptions.id'))
    application_date = db.Column(db.Date, default=date.today)
    match_percentage = db.Column(db.Numeric(5,2))
    status = db.Column(db.Enum('applied', 'screening', 'shortlisted', 'interview-scheduled', 
                                'interviewed', 'selected', 'offered', 'offer-accepted', 
                                'offer-declined', 'joined', 'rejected', 'on-hold'), default='applied')
    screening_score = db.Column(db.Integer)
    screening_remarks = db.Column(db.Text)
    rejection_reason = db.Column(db.Text)
    expected_joining_date = db.Column(db.Date)
    actual_joining_date = db.Column(db.Date)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    candidate = db.relationship('Candidate', backref='applications')
    job = db.relationship('JobDescription', backref='applications')

class InterviewRound(db.Model):
    __tablename__ = 'interview_rounds'
    id = db.Column(db.Integer, primary_key=True)
    application_id = db.Column(db.Integer, db.ForeignKey('candidate_applications.id'))
    round_number = db.Column(db.Integer, default=1)
    round_type = db.Column(db.Enum('telephonic', 'video', 'face-to-face', 'technical', 'hr', 'client', 'assessment'))
    interviewer_name = db.Column(db.String(255))
    interviewer_email = db.Column(db.String(255))
    scheduled_date = db.Column(db.DateTime)
    actual_date = db.Column(db.DateTime)
    duration_minutes = db.Column(db.Integer, default=60)
    meeting_link = db.Column(db.String(500))
    status = db.Column(db.Enum('scheduled', 'rescheduled', 'completed', 'no-show', 'cancelled'), default='scheduled')
    feedback = db.Column(db.Text)
    rating = db.Column(db.Integer)
    result = db.Column(db.Enum('pass', 'fail', 'on-hold'))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    application = db.relationship('CandidateApplication', backref='interviews')

class OfferLetter(db.Model):
    __tablename__ = 'offer_letters'
    id = db.Column(db.Integer, primary_key=True)
    application_id = db.Column(db.Integer, db.ForeignKey('candidate_applications.id'))
    offer_date = db.Column(db.Date, default=date.today)
    offer_valid_till = db.Column(db.Date)
    designation_offered = db.Column(db.String(255))
    salary_offered = db.Column(db.Numeric(10,2))
    joining_bonus = db.Column(db.Numeric(10,2))
    other_benefits = db.Column(db.Text)
    status = db.Column(db.Enum('draft', 'sent', 'accepted', 'declined', 'revised'), default='draft')
    candidate_response_date = db.Column(db.Date)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class ClientProposal(db.Model):
    __tablename__ = 'client_proposals'
    id = db.Column(db.Integer, primary_key=True)
    jd_id = db.Column(db.Integer, db.ForeignKey('job_descriptions.id'))
    client_id = db.Column(db.Integer, db.ForeignKey('clients.id'))
    proposal_date = db.Column(db.Date, default=date.today)
    candidate_count = db.Column(db.Integer, default=0)
    shortlisted_count = db.Column(db.Integer, default=0)
    proposed_candidates = db.Column(db.Text)  # JSON array
    status = db.Column(db.Enum('draft', 'submitted', 'client-review', 'approved', 'rejected'), default='draft')
    client_feedback = db.Column(db.Text)
    billing_amount = db.Column(db.Numeric(10,2))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class CommunicationLog(db.Model):
    __tablename__ = 'communication_logs'
    id = db.Column(db.Integer, primary_key=True)
    entity_type = db.Column(db.Enum('client', 'candidate'))
    entity_id = db.Column(db.Integer)
    communication_type = db.Column(db.Enum('email', 'call', 'sms', 'whatsapp', 'meeting'))
    direction = db.Column(db.Enum('inbound', 'outbound'))
    subject = db.Column(db.String(500))
    content = db.Column(db.Text)
    communication_date = db.Column(db.DateTime, default=datetime.utcnow)
    follow_up_required = db.Column(db.Boolean, default=False)
    follow_up_date = db.Column(db.Date)

# ============= HELPER FUNCTIONS =============

def extract_skills_from_text(text):
    """Simple keyword-based skill extraction"""
    common_skills = ['Python', 'Java', 'JavaScript', 'SQL', 'AWS', 'Docker', 'Kubernetes', 
                     'React', 'Angular', 'Vue', 'Node.js', 'Django', 'Flask', 'Spring Boot',
                     'MongoDB', 'PostgreSQL', 'MySQL', 'Redis', 'Git', 'CI/CD', 'Terraform',
                     'Machine Learning', 'AI', 'Data Science', 'Excel', 'Project Management']
    found_skills = []
    text_lower = text.lower()
    for skill in common_skills:
        if skill.lower() in text_lower:
            found_skills.append(skill)
    return found_skills

def calculate_match_score(jd_skills, candidate_skills):
    """Calculate match percentage between JD and candidate"""
    if not jd_skills or not candidate_skills:
        return 0
    jd_set = set(s.lower() for s in jd_skills)
    cand_set = set(s.lower() for s in candidate_skills)
    if not jd_set:
        return 0
    matches = len(jd_set.intersection(cand_set))
    return round((matches / len(jd_set)) * 100, 2)

def send_email(recipient, subject, body):
    """Send email using Flask-Mail"""
    try:
        msg = Message(subject, recipients=[recipient])
        msg.body = body
        mail.send(msg)
        return True
    except Exception as e:
        print(f"Email error: {e}")
        return False

# ============= API ROUTES =============

@app.route('/')
def index():
    return render_template('dashboard.html')

@app.route('/api/dashboard')
def dashboard():
    """Get dashboard statistics"""
    stats = {
        'open_positions': JobDescription.query.filter_by(status='open').count(),
        'total_candidates': Candidate.query.count(),
        'interviews_today': InterviewRound.query.filter(
            func.date(InterviewRound.scheduled_date) == date.today()
        ).count(),
        'offers_accepted': OfferLetter.query.filter_by(status='accepted').count(),
        'pipeline': {
            'applied': CandidateApplication.query.filter_by(status='applied').count(),
            'shortlisted': CandidateApplication.query.filter_by(status='shortlisted').count(),
            'interviewed': CandidateApplication.query.filter_by(status='interviewed').count(),
            'offered': CandidateApplication.query.filter_by(status='offered').count(),
            'joined': CandidateApplication.query.filter_by(status='joined').count()
        }
    }
    return jsonify(stats)

@app.route('/api/jds')
def get_jds():
    """Get all job descriptions"""
    jds = JobDescription.query.all()
    return jsonify([{
        'id': j.id,
        'title': j.title,
        'client': j.client.company_name if j.client else 'N/A',
        'status': j.status,
        'priority': j.priority,
        'candidates': CandidateApplication.query.filter_by(jd_id=j.id).count()
    } for j in jds])

@app.route('/api/jd/upload', methods=['POST'])
def upload_jd():
    """Create new job description"""
    data = request.form
    skills_text = data.get('skills_required', '')
    skills_list = extract_skills_from_text(skills_text) if skills_text else []
    
    jd = JobDescription(
        title=data.get('title'),
        client_id=data.get('client_id') or None,
        location=data.get('location'),
        employment_type=data.get('employment_type'),
        experience_required=data.get('experience_required'),
        skills_required=','.join(skills_list) if skills_list else data.get('skills_required'),
        qualifications=data.get('qualifications'),
        responsibilities=data.get('responsibilities'),
        status=data.get('status', 'open'),
        priority=data.get('priority', 'medium'),
        no_of_positions=int(data.get('no_of_positions', 1))
    )
    db.session.add(jd)
    db.session.commit()
    
    return jsonify({'success': True, 'jd_id': jd.id, 'extracted_skills': skills_list})

@app.route('/api/candidates')
def get_candidates():
    """Get all candidates with filters"""
    status_filter = request.args.get('status', '')
    skill_filter = request.args.get('skill', '')
    
    query = Candidate.query
    if status_filter:
        # Filter by application status
        query = query.join(CandidateApplication).filter(CandidateApplication.status == status_filter)
    if skill_filter:
        query = query.filter(Candidate.skills.ilike(f'%{skill_filter}%'))
    
    candidates = query.limit(100).all()
    return jsonify([{
        'id': c.id,
        'name': f"{c.first_name} {c.last_name}",
        'email': c.email,
        'skills': c.skills,
        'current_company': c.current_company,
        'total_experience': float(c.total_experience) if c.total_experience else 0
    } for c in candidates])

@app.route('/api/candidates/match/<int:jd_id>')
def match_candidates(jd_id):
    """Find matching candidates for a JD"""
    jd = JobDescription.query.get_or_404(jd_id)
    jd_skills = [s.strip() for s in (jd.skills_required or '').split(',') if s.strip()]
    
    candidates = Candidate.query.all()
    matches = []
    for candidate in candidates:
        cand_skills = [s.strip() for s in (candidate.skills or '').split(',') if s.strip()]
        score = calculate_match_score(jd_skills, cand_skills)
        if score >= 30:
            matches.append({
                'candidate_id': candidate.id,
                'name': f"{candidate.first_name} {candidate.last_name}",
                'email': candidate.email,
                'match_percentage': score
            })
    
    matches.sort(key=lambda x: x['match_percentage'], reverse=True)
    return jsonify({'matches': matches[:20]})

@app.route('/api/applications', methods=['POST'])
def create_application():
    """Create a candidate application"""
    data = request.json
    application = CandidateApplication(
        candidate_id=data.get('candidate_id'),
        jd_id=data.get('jd_id'),
        status='applied'
    )
    db.session.add(application)
    db.session.commit()
    return jsonify({'success': True, 'application_id': application.id})

@app.route('/api/applications/<int:app_id>/status', methods=['PUT'])
def update_application_status(app_id):
    """Update application status"""
    data = request.json
    application = CandidateApplication.query.get_or_404(app_id)
    old_status = application.status
    application.status = data.get('status')
    application.updated_at = datetime.utcnow()
    
    # Send email notification on status change
    if data.get('status') == 'shortlisted' and application.candidate:
        send_email(
            application.candidate.email,
            f"Application Update - {application.job.title if application.job else 'Job'}",
            f"Dear {application.candidate.first_name},\n\nYou have been shortlisted for the position. We will contact you soon for an interview.\n\nBest regards,\nRecruitment Team"
        )
    
    db.session.commit()
    return jsonify({'success': True})

@app.route('/api/interviews', methods=['POST'])
def schedule_interview():
    """Schedule an interview"""
    data = request.json
    interview = InterviewRound(
        application_id=data.get('application_id'),
        round_number=data.get('round_number', 1),
        round_type=data.get('round_type'),
        interviewer_name=data.get('interviewer_name'),
        interviewer_email=data.get('interviewer_email'),
        scheduled_date=datetime.fromisoformat(data.get('scheduled_date')) if data.get('scheduled_date') else None,
        meeting_link=data.get('meeting_link')
    )
    db.session.add(interview)
    
    # Update application status
    app = CandidateApplication.query.get(data.get('application_id'))
    if app:
        app.status = 'interview-scheduled'
    
    db.session.commit()
    return jsonify({'success': True, 'interview_id': interview.id})

@app.route('/api/proposals', methods=['POST'])
def create_proposal():
    """Create a client proposal"""
    data = request.json
    proposal = ClientProposal(
        jd_id=data.get('jd_id'),
        client_id=data.get('client_id'),
        candidate_count=data.get('candidate_count', 0),
        shortlisted_count=data.get('shortlisted_count', 0),
        proposed_candidates=json.dumps(data.get('proposed_candidates', [])),
        status='draft'
    )
    db.session.add(proposal)
    db.session.commit()
    return jsonify({'success': True, 'proposal_id': proposal.id})

@app.route('/api/proposals/<int:jd_id>')
def get_proposals(jd_id):
    """Get proposals for a JD"""
    proposals = ClientProposal.query.filter_by(jd_id=jd_id).all()
    return jsonify([{
        'id': p.id,
        'candidate_count': p.candidate_count,
        'status': p.status,
        'created_at': p.created_at.isoformat() if p.created_at else None
    } for p in proposals])

@app.route('/api/recent-activities')
def recent_activities():
    """Get recent activities"""
    activities = []
    
    # Recent applications
    recent_apps = CandidateApplication.query.order_by(CandidateApplication.created_at.desc()).limit(5).all()
    for app in recent_apps:
        activities.append({
            'type': 'application',
            'message': f"New application from {app.candidate.first_name if app.candidate else 'Candidate'} for {app.job.title if app.job else 'Job'}",
            'time': app.created_at.isoformat() if app.created_at else None
        })
    
    # Recent interviews
    recent_interviews = InterviewRound.query.order_by(InterviewRound.created_at.desc()).limit(3).all()
    for interview in recent_interviews:
        activities.append({
            'type': 'interview',
            'message': f"Interview scheduled: {interview.round_type} round with {interview.interviewer_name}",
            'time': interview.created_at.isoformat() if interview.created_at else None
        })
    
    return jsonify(activities)

# ============= CLI COMMANDS =============

@app.cli.command('init-db')
def init_db():
    """Initialize database - creates all tables"""
    db.create_all()
    print("✅ Database tables created successfully!")

@app.cli.command('seed-demo')
def seed_demo():
    """Add demo data for testing"""
    # Add demo client
    client = Client(company_name="TechCorp Solutions", industry="IT Services", status="active")
    db.session.add(client)
    db.session.commit()
    
    # Add demo JD
    jd = JobDescription(
        client_id=client.id,
        title="Senior Python Developer",
        location="Remote",
        employment_type="full-time",
        skills_required="Python, Django, SQL, AWS",
        status="open",
        priority="high"
    )
    db.session.add(jd)
    
    # Add demo candidate
    candidate = Candidate(
        first_name="John",
        last_name="Doe",
        email="john.doe@example.com",
        skills="Python, Django, PostgreSQL, AWS",
        total_experience=5.0,
        source="linkedin"
    )
    db.session.add(candidate)
    db.session.commit()
    
    print("✅ Demo data added successfully!")

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)