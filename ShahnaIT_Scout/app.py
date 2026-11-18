# app.py - SHAHNAIT SCOUT - AI-POWERED RECRUITMENT PLATFORM

# ============================================
# PDF GENERATION (ReportLab)
# ============================================
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter
from reportlab.lib.units import inch
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.lib import colors

# ============================================
# STANDARD LIBRARY
# ============================================
import os
import sqlite3
import json
import re
import io
import csv
import shutil
import base64
from datetime import datetime, timedelta
import traceback

# ============================================
# FLASK & WEB FRAMEWORK
# ============================================
from flask import Flask, render_template, request, jsonify, send_file, Response
from flask_cors import CORS
from werkzeug.utils import secure_filename
from fpdf import FPDF

# ============================================
# DOCUMENT PARSING
# ============================================
import PyPDF2
import docx

# ============================================
# AI & HTTP REQUESTS
# ============================================
import requests
# ============================================
# DATABASE CONNECTION HELPER
# ============================================
def get_db_connection():
    """Create and return a database connection"""
    conn = sqlite3.connect('shahnai.db')
    conn.row_factory = sqlite3.Row  # This enables dictionary-like access
    return conn
# ============ SPACY AUTO-DOWNLOAD ============
import subprocess
try:
    import spacy
    nlp = spacy.load('en_core_web_sm')
    print("✅ spaCy loaded")
except:
    print("📥 Downloading spaCy model...")
    subprocess.run(['python', '-m', 'spacy', 'download', 'en_core_web_sm'])
    import spacy
    nlp = spacy.load('en_core_web_sm')
    print("✅ spaCy loaded")
# ============ OPEN-SOURCE ANALYSIS ENGINE ============
import spacy
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
from sentence_transformers import SentenceTransformer
from textblob import TextBlob
import nltk
import re
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

def send_email(to_email, subject, body):
    """Send email via Hostinger SMTP"""
    smtp_email = os.environ.get('SMTP_EMAIL')
    smtp_password = os.environ.get('SMTP_PASSWORD')
    
    if not smtp_email or not smtp_password:
        print("⚠️ SMTP not configured")
        return False
    
    try:
        msg = MIMEMultipart()
        msg['From'] = smtp_email
        msg['To'] = to_email
        msg['Subject'] = subject
        msg.attach(MIMEText(body, 'html'))
        
        with smtplib.SMTP_SSL('smtp.hostinger.com', 465) as server:
            server.login(smtp_email, smtp_password)
            return server.send_message(msg)
        return True
    except Exception as e:
        print(f"Email error: {e}")
        return False

def send_telegram_message(message, to_admin=False):
    """Send message to Telegram group or admin"""
    bot_token = os.environ.get('TELEGRAM_BOT_TOKEN')
    chat_id = os.environ.get('TELEGRAM_ADMIN_CHAT_ID') if to_admin else os.environ.get('TELEGRAM_CHAT_ID')
    
    if not bot_token or not chat_id:
        print("⚠️ Telegram not configured")
        return False
    
    try:
        url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
        payload = {
            'chat_id': chat_id,
            'text': message,
            'parse_mode': 'HTML'
        }
        response = requests.post(url, json=payload, timeout=10)
        return response.status_code == 200
    except Exception as e:
        print(f"Telegram error: {e}")
        return False

# Download required NLTK data
try:
    nltk.download('punkt', quiet=True)
    nltk.download('averaged_perceptron_tagger', quiet=True)
except:
    pass

# Load NLP models (will download on first run)
try:
    # For semantic similarity (understanding meaning)
    semantic_model = SentenceTransformer('all-MiniLM-L6-v2')
    print("✅ Sentence Transformer loaded")
except Exception as e:
    print(f"⚠️ Sentence Transformer load failed: {e}")
    semantic_model = None

try:
    # For entity extraction (skills, etc.)
    nlp = spacy.load('en_core_web_sm')
    print("✅ spaCy loaded")
except Exception as e:
    print(f"⚠️ spaCy load failed: {e}")
    print("   Run: python -m spacy download en_core_web_sm")
    nlp = None

def extract_skills_with_spacy(text):
    """Extract skills using spaCy NER and pattern matching"""
    if not nlp:
        return []
    
    # Common tech skills keywords
    tech_skills = [
        'python', 'java', 'javascript', 'react', 'angular', 'node', 'sql', 'mongodb',
        'aws', 'azure', 'gcp', 'docker', 'kubernetes', 'jenkins', 'git', 'linux',
        'salesforce', 'apex', 'lightning', 'spark', 'hadoop', 'kafka', 'scala',
        'tableau', 'powerbi', 'excel', 'r', 'tensorflow', 'pytorch', 'nlp',
        'machine learning', 'deep learning', 'data science', 'analytics'
    ]
    
    doc = nlp(text.lower())
    found_skills = []
    
    for skill in tech_skills:
        if skill in text.lower():
            found_skills.append(skill)
    
    # Also extract entities that might be skills
    for ent in doc.ents:
        if ent.label_ in ['PRODUCT', 'ORG', 'WORK_OF_ART']:
            if len(ent.text) > 2:
                found_skills.append(ent.text.lower())
    
    return list(set(found_skills))

def calculate_semantic_similarity(text1, text2):
    """Calculate semantic similarity using Sentence Transformers"""
    if not semantic_model:
        return 0
    
    try:
        # Truncate if too long
        text1 = text1[:2000]
        text2 = text2[:2000]
        
        embeddings = semantic_model.encode([text1, text2])
        similarity = cosine_similarity([embeddings[0]], [embeddings[1]])[0][0]
        return similarity * 100  # Convert to percentage
    except Exception as e:
        print(f"Semantic similarity error: {e}")
        return 0

def calculate_keyword_similarity(text1, text2):
    """Calculate keyword overlap using TF-IDF"""
    try:
        vectorizer = TfidfVectorizer(stop_words='english', max_features=500)
        tfidf_matrix = vectorizer.fit_transform([text1, text2])
        similarity = cosine_similarity(tfidf_matrix[0:1], tfidf_matrix[1:2])[0][0]
        return similarity * 100
    except:
        return 0

def analyze_genuineness(text):
    """Check if resume seems genuine or AI-generated"""
    red_flags = []
    genuineness_score = 100
    
    # Check for suspicious patterns
    text_lower = text.lower()
    
    # 1. Check for excessive buzzwords (AI signal)
    buzzwords = [
        'proactive', 'synergy', 'leverage', 'paradigm', 'innovative',
        'results-oriented', 'thought leader', 'game-changer', 'disruptive',
        'cutting-edge', 'world-class', 'best-in-class'
    ]
    buzzword_count = sum(1 for word in buzzwords if word in text_lower)
    if buzzword_count > 5:
        genuineness_score -= 10
        red_flags.append(f"Excessive buzzwords ({buzzword_count} found)")
    
    # 2. Check for generic language patterns
    generic_phrases = [
        'worked in a fast-paced environment',
        'strong communication skills',
        'team player with leadership qualities',
        'proven track record of success',
        'highly motivated and self-driven'
    ]
    generic_count = sum(1 for phrase in generic_phrases if phrase in text_lower)
    if generic_count > 3:
        genuineness_score -= 10
        red_flags.append(f"Generic language patterns ({generic_count} found)")
    
    # 3. Check for keyword stuffing
    words = re.findall(r'\b[a-zA-Z]{3,}\b', text_lower)
    word_freq = {}
    for word in words:
        word_freq[word] = word_freq.get(word, 0) + 1
    
    repeated_words = [w for w, c in word_freq.items() if c > 5 and len(w) > 3]
    if repeated_words:
        genuineness_score -= 10
        red_flags.append(f"Keyword stuffing: {', '.join(repeated_words[:3])}")
    
    # 4. Check for sentiment polarity (overly positive = suspicious)
    try:
        blob = TextBlob(text)
        sentiment = blob.sentiment.polarity
        if sentiment > 0.8:
            genuineness_score -= 15
            red_flags.append("Overly positive sentiment (suspicious)")
    except:
        pass
    
    # 5. Check length (very short = suspicious)
    if len(text) < 500:
        genuineness_score -= 20
        red_flags.append("Resume too short (likely AI-generated)")
    
    # 6. Check for bullet point patterns (AI signal)
    bullet_count = text.count('•') + text.count('-') + text.count('*')
    if bullet_count > 30:
        genuineness_score -= 10
        red_flags.append("Excessive bullet points (suspicious)")
    
    # Clamp score
    genuineness_score = max(0, min(100, genuineness_score))
    
    # AI probability (inverse of genuineness with some adjustment)
    ai_probability = max(0, min(100, 100 - genuineness_score + 10))
    
    return {
        'genuineness_score': genuineness_score,
        'ai_generated_probability': ai_probability,
        'red_flags': red_flags
    }

def analyze_resume_locally(resume_text, jd_text):
    """Complete local analysis without any API calls"""
    
    # 1. Semantic similarity (understanding meaning)
    semantic_score = calculate_semantic_similarity(resume_text, jd_text)
    
    # 2. Keyword similarity (TF-IDF)
    keyword_score = calculate_keyword_similarity(resume_text, jd_text)
    
    # 3. Weighted match score (60% semantic, 40% keyword)
    match_score = int((semantic_score * 0.6) + (keyword_score * 0.4))
    match_score = max(0, min(100, match_score))
    
    # 4. Extract skills
    resume_skills = extract_skills_with_spacy(resume_text)
    jd_skills = extract_skills_with_spacy(jd_text)
    
    matching_skills = [s for s in resume_skills if s in jd_skills]
    missing_skills = [s for s in jd_skills if s not in resume_skills]
    
    # 5. Genuineness analysis
    genuineness_result = analyze_genuineness(resume_text)
    
    # 6. Category scores
    skill_match = int((len(matching_skills) / max(len(jd_skills), 1)) * 100)
    
    # Experience estimation (basic)
    years_pattern = r'(\d+)\+?\s*(?:years?|yrs?)'
    years_match = re.findall(years_pattern, resume_text.lower())
    experience_years = max([int(y) for y in years_match]) if years_match else 0
    experience_score = min(100, experience_years * 10)  # Rough estimate
    
    # Education check
    education_keywords = ['bachelor', 'master', 'phd', 'b.tech', 'm.tech', 'b.e.', 'm.e.', 'bca', 'mca', 'degree']
    education_score = 50 if any(edu in resume_text.lower() for edu in education_keywords) else 0
    
    # 7. Determine recommendation
    if match_score >= 70 and genuineness_result['genuineness_score'] >= 70:
        recommendation = 'hire'
    elif match_score >= 40 and genuineness_result['genuineness_score'] >= 50:
        recommendation = 'interview'
    else:
        recommendation = 'reject'
    
    # 8. Build strengths and weaknesses
    strengths = []
    weaknesses = []
    
    if match_score > 70:
        strengths.append("Strong alignment with job requirements")
    if len(matching_skills) > 5:
        strengths.append(f"Strong skill match ({len(matching_skills)} matching skills)")
    if experience_years > 5:
        strengths.append(f"Relevant experience ({experience_years}+ years)")
    if genuineness_result['genuineness_score'] > 80:
        strengths.append("Resume appears genuine and well-written")
    
    if match_score < 50:
        weaknesses.append("Weak alignment with job requirements")
    if len(missing_skills) > 5:
        weaknesses.append(f"Missing key skills ({len(missing_skills)} skills)")
    if experience_years < 2:
        weaknesses.append("Limited experience")
    if genuineness_result['genuineness_score'] < 60:
        weaknesses.append("Resume raises authenticity concerns")
    
    # 9. Executive summary
    summary = f"Candidate shows {match_score}% match with the JD. "
    if recommendation == 'hire':
        summary += "Strong candidate with good skill alignment and genuine resume. Recommend moving to interview/hire."
    elif recommendation == 'interview':
        summary += "Moderate match. Consider for interview with focus on missing skills."
    else:
        summary += "Weak match. Recommend reviewing other candidates."
    
    return {
        'match_score': match_score,
        'genuineness_score': genuineness_result['genuineness_score'],
        'ai_generated_probability': genuineness_result['ai_generated_probability'],
        'recommendation': recommendation,
        'reasoning': f"Match: {match_score}% (Semantic: {int(semantic_score)}%, Keyword: {int(keyword_score)}%). Genuineness: {genuineness_result['genuineness_score']}%.",
        'category_scores': {
            'skills_match': skill_match,
            'experience_match': experience_score,
            'education_match': education_score,
            'certifications_match': 0  # No certification extraction yet
        },
        'matching_skills': matching_skills[:10],
        'missing_skills': missing_skills[:10],
        'strengths': strengths[:5],
        'weaknesses': weaknesses[:5],
        'red_flags': genuineness_result['red_flags'],
        'executive_summary': summary,
        'pre_screening_questions': [
            f"Can you describe your experience with {missing_skills[0] if missing_skills else 'the key skills required'}?",
            "How do you handle challenging technical problems?",
            "What projects are you most proud of and why?"
        ]
    }
def analyze_skill_gap(resume_text, jd_text):
    """Analyze skill gaps between resume and JD"""
    
    # Extract skills from both
    resume_skills = extract_skills_with_spacy(resume_text)
    jd_skills = extract_skills_with_spacy(jd_text)
    
    # Find matching and missing skills
    matching_skills = [s for s in resume_skills if s in jd_skills]
    missing_skills = [s for s in jd_skills if s not in resume_skills]
    
    # Calculate gap percentage
    total_jd_skills = len(jd_skills)
    gap_percentage = 0
    if total_jd_skills > 0:
        gap_percentage = round((len(missing_skills) / total_jd_skills) * 100)
    
    # Generate learning path
    learning_path = []
    for skill in missing_skills[:5]:
        learning_path.append({
            "skill": skill,
            "resources": [
                f"📚 Take a course on {skill}",
                f"💻 Build a project using {skill}",
                f"📝 Practice {skill} interview questions",
                f"🔧 Get certified in {skill}"
            ],
            "estimated_hours": 20 if skill in ['Python', 'Java', 'JavaScript'] else 10
        })
    
    return {
        "matching_skills": matching_skills,
        "missing_skills": missing_skills,
        "gap_percentage": gap_percentage,
        "learning_path": learning_path,
        "total_jd_skills": total_jd_skills,
        "total_resume_skills": len(resume_skills)
    }
def generate_interview_questions(jd_text, resume_text, missing_skills):
    """Generate interview questions based on JD and candidate skills"""
    
    questions = {
        "technical": [],
        "behavioral": [],
        "skill_check": []
    }
    
    # Generate technical questions from JD
    tech_keywords = ['python', 'java', 'javascript', 'aws', 'docker', 'kubernetes', 
                     'sql', 'mongodb', 'react', 'angular', 'node', 'spark', 'hadoop']
    
    for skill in tech_keywords:
        if skill in jd_text.lower():
            questions["technical"].append(f"Can you explain your experience with {skill.title()}?")
            questions["technical"].append(f"How would you use {skill.title()} to solve a business problem?")
    
    # Generate skill check questions for missing skills
    for skill in missing_skills[:3]:
        questions["skill_check"].append(f"What's your understanding of {skill}?")
        questions["skill_check"].append(f"How would you approach learning {skill}?")
    
    # Behavioral questions
    behavioral = [
        "Tell me about a time you faced a difficult challenge at work.",
        "How do you handle disagreement with a team member?",
        "Describe a project you're most proud of.",
        "How do you stay updated with new technologies?",
        "Tell me about a time you failed and what you learned."
    ]
    questions["behavioral"] = behavioral[:3]
    
    # Add role-specific questions based on JD
    if 'senior' in jd_text.lower() or 'lead' in jd_text.lower():
        questions["behavioral"].append("How do you mentor junior developers?")
        questions["behavioral"].append("Describe your experience leading a team.")
    
    return questions

app = Flask(__name__)


def _load_secret_key():
    """Refuse to start without a strong, non-placeholder SECRET_KEY (a known key = forgeable admin sessions)."""
    key = (os.environ.get('SECRET_KEY') or '').strip()
    lowered = key.lower()
    placeholders = ('change', 'your', 'secret', 'example', 'placeholder')
    if len(key) < 32 or any(p in lowered for p in placeholders):
        raise RuntimeError(
            "SECRET_KEY is missing, too short (<32 chars) or still a placeholder. "
            "Generate one with:  python -c \"import secrets; print(secrets.token_hex(32))\"  "
            "and set it in the environment / .env file."
        )
    return key


app.secret_key = _load_secret_key()
app.config.update(
    SESSION_COOKIE_HTTPONLY=True,
    SESSION_COOKIE_SAMESITE='Lax',
    SESSION_COOKIE_SECURE=os.environ.get('SESSION_COOKIE_SECURE', '0') == '1',
)

_cors_origins = [o.strip() for o in os.environ.get('CORS_ORIGINS', '').split(',') if o.strip()]
if _cors_origins:
    CORS(app, supports_credentials=True, origins=_cors_origins)

# ============================================
# AUTHENTICATION
# ============================================
import hashlib
from functools import wraps
from flask import session, redirect, url_for

def login_required(role=None):
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if 'user_id' not in session:
                return jsonify({'error': 'Unauthorized', 'redirect': '/login'}), 401
            if role:
                user_role = (session.get('role') or '').lower()
                required_role = role.lower()
                if user_role != required_role and user_role != 'admin':
                    return jsonify({'error': 'Access denied. ' + role.capitalize() + ' role required.'}), 403
            return f(*args, **kwargs)
        return decorated_function
    return decorator

def get_current_user():
    """Get current logged-in user"""
    if 'user_id' not in session:
        return None
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    c.execute('SELECT id, email, full_name, role FROM users WHERE id = ? AND is_active = 1', (session['user_id'],))
    user = c.fetchone()
    conn.close()
    return dict(user) if user else None
# ============ PASSWORD HASHING (scrypt via Werkzeug; legacy SHA-256 is upgraded on login) ============
import hmac
from werkzeug.security import generate_password_hash, check_password_hash

MIN_PASSWORD_LENGTH = 10
_LEGACY_SHA256_RE = re.compile(r'^[0-9a-f]{64}$')
_RETIRED_PASSWORD_SHA256 = '32c78759d0cb23dd2134c29242867d42b2b335a15e360cfacf908ffb8c9a08e4'


def hash_password(password):
    try:
        return generate_password_hash(password, method='scrypt')
    except Exception:
        return generate_password_hash(password, method='pbkdf2:sha256:600000')


def verify_password(stored_hash, password):
    stored_hash = stored_hash or ''
    if _LEGACY_SHA256_RE.match(stored_hash):
        legacy = hashlib.sha256(password.encode()).hexdigest()
        valid = hmac.compare_digest(legacy, stored_hash)
        return valid, valid
    try:
        return check_password_hash(stored_hash, password), False
    except Exception:
        return False, False


def password_policy_error(password, email=''):
    if not isinstance(password, str) or len(password) < MIN_PASSWORD_LENGTH:
        return f'Password must be at least {MIN_PASSWORD_LENGTH} characters'
    if len(password) > 256:
        return 'Password is too long (max 256 characters)'
    if email and password.strip().lower() == email.strip().lower():
        return 'Password must not be the same as the email'
    if hashlib.sha256(password.encode()).hexdigest() == _RETIRED_PASSWORD_SHA256:
        return 'That password was publicly exposed and can no longer be used'
    return None


_DUMMY_PASSWORD_HASH = hash_password('not-a-real-password')   
# ---- DEFAULT-DENY: every route requires a session unless listed here -------------------------
PUBLIC_ENDPOINTS = {
    'index',
    'login',
    'login_page',
    'logout',
    'get_me',
    'static',
}


@app.before_request
def require_authentication():
    if request.method == 'OPTIONS':
        return None
    if request.endpoint is None:
        return None
    if request.endpoint in PUBLIC_ENDPOINTS:
        return None
    if 'user_id' not in session:
        return jsonify({'error': 'Unauthorized', 'redirect': '/login'}), 401
    return None

# Configuration
app.config['MAX_CONTENT_LENGTH'] = 50 * 1024 * 1024
app.config['UPLOAD_FOLDER'] = '/data/tmp'
app.config['DOCUMENTS_FOLDER'] = '/data/candidate_docs'
app.config['JOB_DOCUMENTS_FOLDER'] = '/data/job_docs'

os.makedirs('/data/attachments', exist_ok=True)
os.makedirs('/data/tmp', exist_ok=True)
# ============ SECURE FILE HANDLING (server generates every stored path) ============
import uuid
import zipfile

ALLOWED_RESUME_EXT = ('pdf', 'docx')
_UPLOAD_ID_RE = re.compile(r'^[0-9a-f]{32}$')


def _storage_roots():
    roots = [app.config['DOCUMENTS_FOLDER'], '/data/attachments', '/data/tmp']
    roots += [p.strip() for p in os.environ.get('EXTRA_STORAGE_ROOTS', '').split(',') if p.strip()]
    return [os.path.realpath(p) for p in roots]


def safe_stored_path(path):
    if not path:
        return None
    try:
        real = os.path.realpath(str(path))
    except (OSError, ValueError):
        return None
    for root in _storage_roots():
        if real.startswith(root + os.sep):
            return real if os.path.isfile(real) else None
    return None


def clean_display_name(name, default='resume'):
    name = os.path.basename(str(name or '').replace('\\', '/'))
    name = re.sub(r'[\x00-\x1f\x7f"<>|:*?]', '', name).strip()[:150]
    return name or default


def save_resume_upload(file_storage):
    ext = os.path.splitext(file_storage.filename or '')[1].lower().lstrip('.')
    if ext not in ALLOWED_RESUME_EXT:
        raise ValueError('Only PDF and DOCX resumes are supported')
    upload_id = uuid.uuid4().hex
    folder = app.config['DOCUMENTS_FOLDER']
    os.makedirs(folder, exist_ok=True)
    path = os.path.join(folder, f'{upload_id}.{ext}')
    file_storage.save(path)
    try:
        if ext == 'pdf':
            with open(path, 'rb') as fh:
                ok = b'%PDF-' in fh.read(1024)
        else:
            ok = zipfile.is_zipfile(path)
    except OSError:
        ok = False
    if not ok:
        try:
            os.remove(path)
        except OSError:
            pass
        raise ValueError('File content does not match its extension')
    return upload_id, ext, path


def resolve_resume_upload(upload_id):
    if not isinstance(upload_id, str) or not _UPLOAD_ID_RE.match(upload_id):
        return None
    for ext in ALLOWED_RESUME_EXT:
        p = os.path.join(app.config['DOCUMENTS_FOLDER'], f'{upload_id}.{ext}')
        if os.path.isfile(p):
            return p, ext
    return None

# ============ DATABASE SETUP ============
DB_PATH = '/data/shahnai.db'

def init_db():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    
    c.execute('''CREATE TABLE IF NOT EXISTS candidates (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        first_name TEXT, last_name TEXT, middle_name TEXT, phone TEXT, email TEXT,
        address TEXT, linkedin TEXT, other_social TEXT, current_role TEXT,
        current_ctc TEXT, expected_ctc TEXT,
        employment_status TEXT, notice_period_days INTEGER DEFAULT 0,
        work_experience TEXT, certifications TEXT, core_skills TEXT, education TEXT,
        notes TEXT,
        resume_text TEXT, resume_filename TEXT, match_score INTEGER DEFAULT 0,
        recommendation TEXT DEFAULT '', detailed_analysis TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        uploaded_by TEXT DEFAULT 'ShahnaIT',
        resume_file_path TEXT,
        resume_original_filename TEXT
    )''')
    
    c.execute('''CREATE TABLE IF NOT EXISTS candidate_documents (
        id INTEGER PRIMARY KEY AUTOINCREMENT, candidate_id INTEGER,
        filename TEXT, original_filename TEXT, file_path TEXT, file_type TEXT,
        is_resume BOOLEAN DEFAULT 0, uploaded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (candidate_id) REFERENCES candidates(id)
    )''')
    
    c.execute('''CREATE TABLE IF NOT EXISTS jobs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        title TEXT NOT NULL,
        company TEXT,
        description TEXT,
        roles_responsibilities TEXT,
        qualifications TEXT,
        required_skills TEXT,
        certifications_required TEXT,
        requirement_id TEXT,
        working_mode TEXT DEFAULT 'Not Specified',
        hybrid_days INTEGER DEFAULT 0,
        business_model TEXT DEFAULT 'Not Specified',
        payroll_company TEXT,
        client_name TEXT,
        end_client TEXT,
        years_of_experience INTEGER DEFAULT 0,
        budget TEXT,
        headcount INTEGER DEFAULT 1,
        is_active BOOLEAN DEFAULT 1,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )''')
    
    c.execute('''CREATE TABLE IF NOT EXISTS job_documents (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        job_id INTEGER,
        filename TEXT,
        original_filename TEXT,
        file_path TEXT,
        file_type TEXT,
        uploaded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (job_id) REFERENCES jobs(id)
    )''')
    
    c.execute('''CREATE TABLE IF NOT EXISTS candidate_notes (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        candidate_id INTEGER NOT NULL,
        note_text TEXT NOT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (candidate_id) REFERENCES candidates(id) ON DELETE CASCADE
    )''')

    c.execute('''CREATE TABLE IF NOT EXISTS invoices (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        invoice_number TEXT,
        onboarded_resource_id INTEGER,
        client_name TEXT,
        resource_name TEXT,
        amount REAL DEFAULT 0,
        gst_percent REAL DEFAULT 18,
        gst_amount REAL DEFAULT 0,
        total_amount REAL DEFAULT 0,
        invoice_date DATE,
        due_date DATE,
        description TEXT,
        status TEXT DEFAULT 'Draft',
        payment_date DATE,
        payment_amount REAL DEFAULT 0,
        notes TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (onboarded_resource_id) REFERENCES onboarded_resources(id)
    )''')
    
    c.execute('''CREATE TABLE IF NOT EXISTS interviews (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        candidate_id INTEGER,
        candidate_name TEXT,
        resource_owner TEXT,
        interview_date DATE,
        interview_time TIME,
        round TEXT DEFAULT 'L1',
        client_name TEXT,
        client_poc TEXT,
        requirement_id TEXT,
        verdict TEXT DEFAULT 'Scheduled',
        feedback TEXT,
        scheduled_by TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (candidate_id) REFERENCES candidates(id)
    )''')

    c.execute('''CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        email TEXT UNIQUE NOT NULL,
        password_hash TEXT NOT NULL,
        full_name TEXT,
        role TEXT DEFAULT 'recruiter',
        is_active BOOLEAN DEFAULT 1,
        last_login TIMESTAMP,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )''')
    
    # Create default admin if no users exist
    c.execute('SELECT COUNT(*) FROM users')
    if c.fetchone()[0] == 0:
        import hashlib
        default_password = hashlib.sha256('Ibaadrn@shahnait@301'.encode()).hexdigest()
        c.execute('INSERT INTO users (email, password_hash, full_name, role) VALUES (?, ?, ?, ?)',
                  ('ibaadrn@shahnait.com', default_password, 'Ibaad RN', 'admin'))
        print("✅ Default admin created: ibaadrn@shahnait.com")

        c.execute('''CREATE TABLE IF NOT EXISTS onboarded_resources (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        candidate_id INTEGER,
        client_name TEXT,
        doj DATE,
        contract_start DATE,
        contract_end DATE,
        resource_owner TEXT,
        work_location TEXT,
        monthly_salary REAL DEFAULT 0,
        billing_rate REAL DEFAULT 0,
        business_model TEXT DEFAULT 'C2C',
        requirement_id TEXT,
        requirement_name TEXT,
        po_number TEXT,
        sow_attached TEXT,
        status TEXT DEFAULT 'Active',
        notes TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (candidate_id) REFERENCES candidates(id)
    )''')

        c.execute('''CREATE TABLE IF NOT EXISTS invoices (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        invoice_number TEXT,
        onboarded_resource_id INTEGER,
        client_name TEXT,
        resource_name TEXT,
        amount REAL DEFAULT 0,
        gst_percent REAL DEFAULT 18,
        gst_amount REAL DEFAULT 0,
        total_amount REAL DEFAULT 0,
        invoice_date DATE,
        due_date DATE,
        description TEXT,
        status TEXT DEFAULT 'Draft',
        payment_date DATE,
        payment_amount REAL DEFAULT 0,
        notes TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (onboarded_resource_id) REFERENCES onboarded_resources(id)
    )''')

    c.execute('''CREATE TABLE IF NOT EXISTS company_settings (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        setting_key TEXT UNIQUE,
        setting_value TEXT
    )''')
    
    # Insert default empty settings if not exist
    c.execute("INSERT OR IGNORE INTO company_settings (setting_key, setting_value) VALUES ('bank_name', '')")
    c.execute("INSERT OR IGNORE INTO company_settings (setting_key, setting_value) VALUES ('account_no', '')")
    c.execute("INSERT OR IGNORE INTO company_settings (setting_key, setting_value) VALUES ('ifsc_code', '')")
    c.execute("INSERT OR IGNORE INTO company_settings (setting_key, setting_value) VALUES ('branch', '')")
    c.execute("INSERT OR IGNORE INTO company_settings (setting_key, setting_value) VALUES ('logo_path', '')")
    c.execute("INSERT OR IGNORE INTO company_settings (setting_key, setting_value) VALUES ('authorized_signatory', '')")

    c.execute('''CREATE TABLE IF NOT EXISTS uploaders (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT UNIQUE NOT NULL
    )''')
    
    c.execute('SELECT COUNT(*) FROM uploaders')
    if c.fetchone()[0] == 0:
        for name in ['Siraj', 'Ibaad', 'Saniya', 'Sumaiya', 'Muhiuddin']:
            c.execute('INSERT INTO uploaders (name) VALUES (?)', (name,))

        c.execute('''CREATE TABLE IF NOT EXISTS candidate_projects (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        candidate_id INTEGER,
        project_name TEXT NOT NULL,
        role TEXT,
        organization TEXT,
        start_date TEXT,
        end_date TEXT,
        description TEXT,
        tech_stack TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (candidate_id) REFERENCES candidates(id) ON DELETE CASCADE
    )''')
    
    c.execute('''CREATE TABLE IF NOT EXISTS candidate_education (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        candidate_id INTEGER,
        degree TEXT NOT NULL,
        institute TEXT NOT NULL,
        field_of_study TEXT,
        start_year TEXT,
        end_year TEXT,
        grade TEXT,
        location TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (candidate_id) REFERENCES candidates(id) ON DELETE CASCADE
    )''')
    
    conn.commit()
    conn.close()
    print("✅ Database initialized")

init_db()
# ============ STEP 1: DATABASE MIGRATION - ADD NEW COLUMNS ============
def migrate_database():
    """Add new columns for enhanced candidate profile"""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    
    # Get existing columns
    c.execute("PRAGMA table_info(candidates)")
    existing_columns = [col[1] for col in c.fetchall()]
    
    new_columns = {
        'designation': 'TEXT',
        'location': 'TEXT',
        'years_of_experience': 'TEXT',
        'proposed_client': 'TEXT',
        'proposed_requirement': 'TEXT',
        'stage': "TEXT DEFAULT 'new'",
        'attachments': 'TEXT',  # JSON array
        'analysis_summary': 'TEXT',
        'matched_jd': 'TEXT',
        'uploaded_by_name': 'TEXT DEFAULT \'ShahnaIT HR\''
    }
    
    for col_name, col_type in new_columns.items():
        if col_name not in existing_columns:
            try:
                c.execute(f"ALTER TABLE candidates ADD COLUMN {col_name} {col_type}")
                print(f"✅ Added column: {col_name}")
            except Exception as e:
                print(f"⚠️ Error adding {col_name}: {e}")
    
    conn.commit()
    conn.close()
    print("✅ Database migration complete!")

# Call migration at startup
migrate_database()
def ensure_schema():
    """Idempotent replacement for the old /fix-* schema routes. Safe to run on every start."""
    wanted = [
        ('jobs', 'max_salary', "TEXT DEFAULT ''"),
        ('jobs', 'office_location', "TEXT DEFAULT ''"),
        ('candidates', 'proposed_date', 'DATE'),
        ('candidates', 'relevant_experience', "TEXT DEFAULT '[]'"),
        ('candidates', 'pan_number', 'TEXT'),
        ('candidates', 'cgpa', 'TEXT'),
        ('candidates', 'pincode', 'TEXT'),
        # --- Master Reporting Engine: the 18 report columns that did not exist yet ---
        ('candidates', 'relevant_exp', "TEXT DEFAULT ''"),
        ('candidates', 'work_mode', "TEXT DEFAULT ''"),            # Onsite / Hybrid / Remote
        ('candidates', 'freelancing', "TEXT DEFAULT ''"),          # Yes / No
        ('candidates', 'engagement_type', "TEXT DEFAULT ''"),      # C2C / C2H / FTE
        ('candidates', 'last_working_day', "TEXT DEFAULT ''"),
        ('proposal_dispatch_log', 'tracker_json', "TEXT DEFAULT ''"),   # the proposal row(s) exactly as sent
        ('proposal_dispatch_log', 'submission_date', 'DATE'),
        ('onboarded_resources', 'client_gstin', "TEXT DEFAULT ''"),
        ('onboarded_resources', 'client_address', "TEXT DEFAULT ''"),
    ]
    conn = sqlite3.connect(DB_PATH)
    try:
        c = conn.cursor()
        for table, col, ddl in wanted:
            c.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name = ?", (table,))
            if not c.fetchone():
                continue
            c.execute(f"PRAGMA table_info({table})")
            if col not in {row[1] for row in c.fetchall()}:
                c.execute(f"ALTER TABLE {table} ADD COLUMN {col} {ddl}")
                print(f"Schema: added {table}.{col}")
        conn.commit()
    finally:
        conn.close()


ensure_schema()

def create_requirement_tables():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS requirements (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        requirement_id TEXT NOT NULL UNIQUE,
        title TEXT NOT NULL,
        client_name TEXT,
        description TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )''')
    conn.commit()
    conn.close()
    print("✅ Requirements table ready!")

create_requirement_tables()

# ============ GROQ API SETUP ============

# ============ GROQ API SETUP ============
GROQ_ENABLED = False
GROQ_API_KEY = os.getenv('GROQ_API_KEY')

if GROQ_API_KEY and GROQ_API_KEY.startswith('gsk_'):
    GROQ_ENABLED = True
    print("✅✅✅ Groq API configured")

# Model fallback chain - tries each in order until one works
GROQ_MODELS = [
    "meta-llama/llama-4-scout-17b-16e-instruct",
    "meta-llama/llama-4-maverick-17b-128e-instruct",
    "qwen/qwen3-32b",
    "openai/gpt-oss-120b",
    "openai/gpt-oss-20b",
]

def call_groq_api(prompt, max_tokens=2500):
    """Call Groq API with automatic model fallback"""
    if not GROQ_API_KEY:
        print("❌ Groq: No API key")
        return None
    
    url = "https://api.groq.com/openai/v1/chat/completions"
    headers = {"Authorization": f"Bearer {GROQ_API_KEY}", "Content-Type": "application/json"}
    
    last_error = None
    
    for model in GROQ_MODELS:
        payload = {
            "model": model,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 0.1,
            "max_tokens": max_tokens
        }
        
        try:
            response = requests.post(url, json=payload, headers=headers, timeout=45)
            
            if response.status_code == 200:
                msg = response.json()['choices'][0]['message']
                result = msg.get('content', '').strip()
                # Handle reasoning models that put output in 'reasoning'
                if not result and msg.get('reasoning'):
                    result = msg.get('reasoning', '').strip()
                result = result.strip()
                if result.startswith('```json'):
                    result = result[7:]
                if result.startswith('```'):
                    result = result[3:]
                if result.endswith('```'):
                    result = result[:-3]
                print(f"✅ Groq success with model: {model}")
                return result
            
            elif response.status_code == 404:
                print(f"⚠️ Model {model} not available, trying next...")
                last_error = f"{model}: model not found"
                continue
            
            elif response.status_code == 429:
                print(f"⚠️ Rate limited on {model}, trying next...")
                last_error = f"{model}: rate limit"
                continue
            
            else:
                print(f"⚠️ Model {model} failed with {response.status_code}: {response.text[:200]}")
                last_error = f"{model}: status {response.status_code}"
                continue
        
        except requests.exceptions.Timeout:
            print(f"⚠️ Timeout on {model}, trying next...")
            last_error = f"{model}: timeout"
            continue
        except Exception as e:
            print(f"⚠️ Exception on {model}: {type(e).__name__}: {e}")
            last_error = f"{model}: {str(e)}"
            continue
    
    print(f"❌ All Groq models failed. Last error: {last_error}")
    return None

def normalize_resume_text(text):
    """Clean up raw PDF/DOCX text - normalize whitespace, fix line breaks, remove garbage"""
    if not text:
        return ""
    
    # Remove excessive whitespace
    text = re.sub(r'\r\n', '\n', text)
    text = re.sub(r'\r', '\n', text)
    text = re.sub(r'[ \t]+', ' ', text)
    text = re.sub(r'\n\s*\n+', '\n', text)
    
    # Remove null bytes and control chars
    text = ''.join(ch for ch in text if ch == '\n' or ch == '\t' or ord(ch) >= 32)
    
    # Remove common PDF garbage
    text = re.sub(r'^\s*\d+\s*$', '', text, flags=re.MULTILINE)  # Standalone page numbers
    
    return text.strip()

SECTION_KEYWORDS = {
    'contact': ['contact', 'personal info', 'personal information'],
    'summary': ['professional summary', 'summary', 'objective', 'profile', 'about', 'executive summary'],
    'skills': ['skills', 'technical skills', 'core skills', 'competencies', 'expertise', 'key skills'],
    'experience': ['experience', 'work experience', 'professional experience', 'employment', 'career history'],
    'education': ['education', 'academic', 'qualifications', 'degree'],
    'certifications': ['certifications', 'certificates', 'credentials', 'licenses'],
    'projects': ['projects', 'portfolio', 'work samples'],
}

def detect_resume_sections(text):
    """Detect section boundaries in resume text"""
    if not text:
        return {}
    text_lines = text.split('\n')
    sections = {}
    
    for i, line in enumerate(text_lines):
        line_lower = line.lower().strip()
        if not line_lower or len(line_lower) > 60:
            continue
        for section_name, keywords in SECTION_KEYWORDS.items():
            if any(kw in line_lower for kw in keywords):
                start_pos = sum(len(l) + 1 for l in text_lines[:i])
                sections[section_name] = start_pos
                break
    
    sorted_sections = sorted(sections.items(), key=lambda x: x[1])
    ranges = {}
    for i, (name, start) in enumerate(sorted_sections):
        end = sorted_sections[i + 1][1] if i + 1 < len(sorted_sections) else len(text)
        ranges[name] = (start, end)
    
    return ranges

def extract_section_text(text, section_name):
    """Extract text belonging to a specific section"""
    sections = detect_resume_sections(text)
    if section_name not in sections:
        return ""
    start, end = sections[section_name]
    return text[start:end].strip()

def validate_field(field_name, value):
    """Validate extracted field. Returns (is_valid, confidence, warning)"""
    if value is None or value == "":
        return False, 0.0, "empty"
    
    value_str = str(value).strip()
    
    rules = {
        'first_name': {'min': 1, 'max': 50, 'pattern': r'^[A-Za-z\s\-\.\']+$', 'bad': ['@', '•', '|', 'Engineer', 'Manager', 'Developer']},
        'last_name': {'min': 1, 'max': 50, 'pattern': r'^[A-Za-z\s\-\.\']+$', 'bad': ['@', '•', '|']},
        'email': {'pattern': r'^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}$'},
        'phone': {'min': 10, 'max': 20, 'pattern': r'^[\d\s\+\-\(\)\.]{10,}$'},
        'summary': {'min': 20, 'max': 1000},
    }
    
    if field_name not in rules:
        return True, 0.9, ""
    
    rule = rules[field_name]
    confidence = 1.0
    
    if 'min' in rule and len(value_str) < rule['min']:
        return False, 0.3, "too short"
    if 'max' in rule and len(value_str) > rule['max']:
        return False, 0.3, "too long"
    if 'pattern' in rule and not re.match(rule['pattern'], value_str):
        return False, 0.4, "invalid format"
    if 'bad' in rule:
        for token in rule['bad']:
            if token.lower() in value_str.lower():
                return False, 0.5, f"contains '{token}'"
    
    return True, confidence, ""

def fix_misclassifications(data):
    """Detect and fix common misclassification errors"""
    fixes = []
    
    # Fix 1: Name stuck in summary field
    summary = str(data.get('summary', '') or '').strip()
    first_name = str(data.get('first_name', '') or '').strip()
    
    if summary and not first_name:
        if re.match(r'^[A-Z][a-z]+(\s+[A-Z][a-z]+){1,3}$', summary):
            parts = summary.split()
            data['first_name'] = parts[0]
            data['last_name'] = parts[-1]
            data['middle_name'] = ' '.join(parts[1:-1]) if len(parts) > 2 else ''
            data['summary'] = None
            fixes.append(f"Extracted name from summary: {summary}")
    
    # Fix 2: Contact info in summary field
    summary = str(data.get('summary', '') or '').strip()
    if summary and any(marker in summary for marker in ['@', '+91', 'Email:', 'Phone:', 'Mobile:']):
        data['summary'] = None
        fixes.append("Removed contact info from summary")
    
    # Fix 3: Years of experience unrealistic
    years = data.get('years_of_experience')
    if years:
        try:
            y = float(years)
            if y < 0 or y > 70:
                data['years_of_experience'] = 0
                fixes.append(f"Reset unrealistic years: {y}")
        except:
            data['years_of_experience'] = 0
            fixes.append("Reset non-numeric years")
    
    # Fix 4: Invalid email
    email = data.get('email')
    if email and ('@' not in str(email) or '.' not in str(email)):
        data['email'] = ''
        fixes.append(f"Removed invalid email: {email}")
    
    # Fix 5: Phone too short
    phone = data.get('phone')
    if phone:
        digits = ''.join(filter(str.isdigit, str(phone)))
        if len(digits) < 10:
            data['phone'] = ''
            fixes.append(f"Removed short phone: {phone}")
    
    # Fix 6: Name contains job title
    first_name = str(data.get('first_name', '') or '').strip()
    if first_name and any(title in first_name.lower() for title in ['engineer', 'manager', 'developer', 'analyst']):
        data['first_name'] = ''
        fixes.append(f"Removed job title from first_name: {first_name}")
    
    return data, fixes

def parse_resume_with_groq(resume_text):
    """Expert-level AI resume parser - extracts EVERY field with high accuracy"""
    if not resume_text or len(resume_text) < 50:
        return None
    
    cleaned_text = normalize_resume_text(resume_text)
    
    prompt = f"""You are the world's most accurate resume parser. Extract ALL details from this resume with 100% accuracy. Read carefully - especially dates, skills, and proper names.

Return ONLY valid JSON. No markdown, no explanations, no code fences.

{{
    "first_name": "Candidate's first name (proper case)",
    "last_name": "Candidate's last name (proper case)",
    "middle_name": "Middle name if present, else empty",
    "email": "Primary email address, else empty",
    "phone": "Primary phone (with country code if present), else empty",
    "address": "Full address if present, else empty",
    "location": "City, State (or City, Country)",
    "linkedin": "Full LinkedIn URL, else empty",
    "other_social": "GitHub/Portfolio/other URL, else empty",
    "current_role": "Most recent job title",
    "designation": "Current designation/position",
    "current_ctc": "Current CTC with currency (e.g., '15 LPA', '1200000 INR'), else empty",
    "expected_ctc": "Expected CTC, else empty",
    "years_of_experience": total years as number (0 if fresher),
    "notice_period_days": number of days (0 if not mentioned),
    "employment_status": "Employed / Unemployed / Student / Freelancer",
    
    "core_skills": ["every single technical skill mentioned - include programming languages, frameworks, databases, tools, cloud platforms, methodologies"],
    "relevant_experience": [{{"skill": "Python", "years": 5}}],
    
    "education": [
        {{"degree": "B.Tech Computer Science", "institute": "College name", "start_year": "2016", "end_year": "2020", "grade": "8.5 CGPA", "location": "City"}}
    ],
    
    "certifications": ["all certifications with full names"],
    
    "work_experience": [
        {{
            "company": "Full company name",
            "role": "Exact job title",
            "start_date": "Mon YYYY (e.g., Jan 2020)",
            "end_date": "Mon YYYY or Present",
            "duration": "Jan 2020 - Present",
            "location": "City, Country",
            "description": "Key responsibilities and achievements"
        }}
    ],
    
    "projects": [
        {{
            "project_name": "Project title",
            "role": "Your role in the project",
            "organization": "Company/Institution",
            "start_date": "Mon YYYY",
            "end_date": "Mon YYYY or Present",
            "description": "What the project did",
            "tech_stack": "Technologies used"
        }}
    ],
    
    "summary": "Professional summary/objective if present"
}}

CRITICAL RULES:
1. DATES: Extract actual months/years. Do not guess. If only year given, use "YYYY".
2. NAMES: Proper case (John Doe, not JOHN DOE). Take from top of resume.
3. PHONE: Include country code (+91, +1). Keep full number with spaces/dashes.
4. SKILLS: Extract EVERY skill mentioned anywhere in the resume. Include:
   - Programming languages: Python, Java, JavaScript, C++, C#, Go, Rust, etc.
   - Frameworks: React, Angular, Django, Flask, Spring Boot, etc.
   - Databases: MySQL, PostgreSQL, MongoDB, Redis, etc.
   - Cloud: AWS, Azure, GCP, etc.
   - DevOps: Docker, Kubernetes, Jenkins, Terraform, etc.
   - Data: Spark, Hadoop, Kafka, Airflow, etc.
   - ML/AI: TensorFlow, PyTorch, scikit-learn, NLP, etc.
   - SAP: All SAP modules (ABAP, FICO, MM, SD, HANA, etc.)
   - Salesforce: Apex, LWC, SOQL, etc.
   - Tools: Git, Jira, Figma, etc.
   - Methodologies: Agile, Scrum, Kanban, etc.
5. EXPERIENCE: List ALL companies with exact dates and full descriptions.
6. EDUCATION: List ALL degrees with institution, years, and grades.
7. WORK EXPERIENCE ORDER: Most recent first.
8. DO NOT INVENT any information. Use empty string "" or empty array [] for missing.
9. If a section has multiple entries, include ALL of them.
10. Verify email format. Verify phone is a phone number, not ID.
11. INDIAN NAMES: Handle these formats correctly:
    - With honorifics: "Dr. Rajesh Kumar" → first_name="Rajesh", last_name="Kumar"
    - With initials: "K. R. Narayanan" → first_name="K.R.", last_name="Narayanan"
    - Compound surnames: "Venkata Subramanian" → treat as single last name
    - All caps: "RAJESH KUMAR" → convert to proper case "Rajesh Kumar"
    - Regional names: Iyer, Reddy, Nair, Yadav, Sharma, Patel, Singh, etc.
12. INDIAN PHONE: Extract mobile starting with 6-9 (10 digits) with optional +91 prefix.
13. INDIAN EDUCATION: Extract CGPA (e.g., "8.4/10") or percentage (e.g., "65%") for education entries.
14. INDIAN ADDRESS: Include city, state, and PIN code (6-digit) if present.
15. INDIAN RESUME CONVENTIONS: Handle "Fresher" resumes (no work exp, focus on projects/internships), "Career Objective" sections, and CGPA-based education.
16. SECTION AWARENESS: Identify the section each piece of data belongs to FIRST.
    - Extract first_name from CONTACT section only (usually top of resume, before any headers)
    - Extract summary from PROFESSIONAL SUMMARY section only
    - Extract skills from SKILLS / TECHNICAL SKILLS section only
    - Extract work_experience from EXPERIENCE / WORK EXPERIENCE section only
    - Extract education from EDUCATION / ACADEMIC section only
    - Extract certifications from CERTIFICATIONS section only
    - Extract projects from PROJECTS section only
17. COMMON MISTAKES TO AVOID:
    - Do NOT put the candidate's name in the "summary" field
    - Do NOT put email/phone/LinkedIn in the "summary" field
    - Do NOT put company names in the "first_name" field
    - Do NOT put skill lists in the "summary" field
    - Do NOT skip the education section - it is ALWAYS present in most resumes
    - Do NOT skip designation/current_role - look for job titles near the top
18. NAME EXTRACTION RULE (CRITICAL):
    A person's name contains ONLY letters, spaces, dots, and hyphens.
    If the raw text has "John Doe +91 98765 43210", then:
      - first_name = "John"
      - last_name = "Doe"
      - phone = "+91 98765 43210"
    NEVER include digits, @, |, or / in first_name or last_name.
    If uncertain, extract only the first two purely alphabetic words as name.
19. VALIDATION:
    - first_name: actual person name (1-50 chars, letters only, no job titles)
    - email: must contain @ and .
    - phone: must have 10+ digits
    - years_of_experience: 0-70 range
    - summary: 20-1000 chars, no contact info, no honorifics
    - designation/current_role: MUST be extracted if any job title appears in resume
    - education: MUST include degree, institute, and years for EACH entry
20. FIELD LABEL STRIPPING (CRITICAL):
    Resumes often use labels like "Name:", "Email:", "Phone:", "Designation:".
    ALWAYS strip the label and its colon. Extract ONLY the value.
    Example: "Name: Pradesh B" → first_name="Pradesh", last_name="B" (NOT "Name:")
    Example: "Designation: SAP Consultant" → designation="SAP Consultant"
    Example: "Email: abc@xyz.com" → email="abc@xyz.com"
21. PROPER CASE FOR NAMES (CRITICAL):
    Always convert names to proper case:
    - "pradesh b" → "Pradesh B"
    - "PRADESH B" → "Pradesh B"
    - "john doe" → "John Doe"
    First letter of each word capitalized, rest lowercase..0

RESUME TEXT:
{cleaned_text[:8000]}
"""
    
    response = call_groq_api(prompt, max_tokens=4000)
    if response:
        try:
            response = response.strip()
            if response.startswith('```'):
                response = response.split('```')[1]
                if response.startswith('json'):
                    response = response[4:]
            response = response.strip()
            
            parsed = json.loads(response)
            return parsed
        except Exception as e:
            print(f"JSON parse error: {e}")
            print(f"Response: {response[:500]}")
            return None
    return None

def cross_validate_resume(ai_parsed, raw_text):
    """Cross-check AI output, fix misclassifications, validate fields"""
    if not ai_parsed:
        return ai_parsed
    
    # Fix misclassifications FIRST (name in summary, contact info, invalid data)
    ai_parsed, fixes = fix_misclassifications(ai_parsed)
    if fixes:
        print(f"🔧 Corrections made: {fixes}")
    
    # Validate each field against rules
    for field in ['first_name', 'last_name', 'email', 'phone', 'summary']:
        value = ai_parsed.get(field)
        if value:
            is_valid, confidence, warning = validate_field(field, value)
            if not is_valid:
                print(f"⚠️ Invalid {field}: {value} ({warning})")
                if field in ['email', 'phone']:
                    ai_parsed[field] = ''
                elif field == 'summary':
                    ai_parsed[field] = None
    
    # Verify email with regex
    regex_email = extract_email(raw_text)
    if regex_email and (not ai_parsed.get('email') or '@' not in ai_parsed.get('email', '')):
        ai_parsed['email'] = regex_email
    
    # Verify phone (Indian mobile first, then international)
    indian_mobile = extract_indian_mobile(raw_text)
    regex_phone = extract_phone(raw_text)
    current_phone = ai_parsed.get('phone', '')
    current_digits = ''.join(filter(str.isdigit, current_phone)) if current_phone else ''
    
    if len(current_digits) < 10:
        if indian_mobile:
            ai_parsed['phone'] = indian_mobile
        elif regex_phone:
            ai_parsed['phone'] = regex_phone
    
    # Verify name if missing
    if not ai_parsed.get('first_name'):
        first, last, middle = extract_name_from_text(raw_text)
        if first:
            ai_parsed['first_name'] = first
            ai_parsed['last_name'] = last
            ai_parsed['middle_name'] = middle
    
    # Strip Indian honorifics
    if ai_parsed.get('first_name'):
        ai_parsed['first_name'] = strip_indian_honorifics(ai_parsed['first_name'])
    if ai_parsed.get('last_name'):
        ai_parsed['last_name'] = strip_indian_honorifics(ai_parsed['last_name'])
    
    # Verify LinkedIn
    if not ai_parsed.get('linkedin'):
        li_match = re.search(r'(https?://[^\s]*linkedin[^\s]*)', raw_text, re.IGNORECASE)
        if li_match:
            ai_parsed['linkedin'] = li_match.group(1)
    
    # Verify skills if empty
    if not ai_parsed.get('core_skills') or len(ai_parsed.get('core_skills', [])) == 0:
        fallback = fallback_parse_resume(raw_text)
        if fallback.get('core_skills'):
            ai_parsed['core_skills'] = fallback['core_skills']
    
    # Verify all list fields
    for field in ['work_experience', 'certifications', 'education', 'projects']:
        if not isinstance(ai_parsed.get(field), list):
            ai_parsed[field] = []
    
    # India-specific fields
    pan = extract_pan(raw_text)
    if pan:
        ai_parsed['pan_number'] = pan
    
    cgpa = extract_cgpa_or_percentage(raw_text)
    if cgpa:
        ai_parsed['cgpa_or_percentage'] = cgpa
    
    pincode = extract_pincode(raw_text)
    if pincode and not ai_parsed.get('pincode'):
        ai_parsed['pincode'] = pincode
    
    return ai_parsed
def analyze_match_with_groq(resume_text, jd_text):
    """Analyze resume vs JD match with detailed scoring"""
    if not GROQ_ENABLED:
        return None
    prompt = f"""You are an expert recruitment analyst. Analyze this resume against the job description with extreme precision. Return ONLY valid JSON.

JOB DESCRIPTION:
{jd_text[:3000]}

RESUME:
{resume_text[:3500]}

Provide a detailed analysis. Be extremely critical and precise. Do not inflate scores.

Return EXACTLY this JSON format:
{{
    "match_score": 0-100 integer,
    "recommendation": "Shortlisted / Strong Match / Moderate Match / Low Match / Not Recommended",
    "category_scores": {{
        "skills_match": 0-100,
        "experience_match": 0-100,
        "education_match": 0-100,
        "certifications_match": 0-100,
        "overall_fit": 0-100
    }},
    "matching_skills": ["skill1", "skill2"],
    "missing_skills": ["skill1", "skill2"],
    "strengths": ["strength1", "strength2"],
    "weaknesses": ["weakness1", "weakness2"],
    "detailed_analysis": "Detailed paragraph explaining the match reasoning with specific examples",
    "pre_screening_questions": ["Q1", "Q2", "Q3"]
}}

Scoring Guidelines:
- 90-100: Perfect fit
- 70-89: Strong match
- 50-69: Moderate match
- 30-49: Weak match
- 0-29: No match

Be harsh and realistic."""
    response = call_groq_api(prompt, max_tokens=2000)
    if response:
        try:
            return json.loads(response)
        except:
            return None
    return None


def analyze_genuineness(resume_text, candidate_name=""):
    """Detect if a resume appears fake, AI-generated, or embellished"""
    if not GROQ_ENABLED:
        return None
    prompt = f"""You are an expert in detecting fake, AI-generated, or embellished resumes. Analyze this resume.

Check for:
1. AI-generated patterns (repetitive phrasing, overly perfect formatting, generic statements)
2. Inconsistencies in experience timeline
3. Unrealistic skill combinations for experience level
4. Vague or unverifiable claims
5. Keyword stuffing
6. Missing specific details real professionals would include
7. Unusual job hopping patterns

Return ONLY valid JSON:
{{
    "genuineness_score": 0-100 (100 = completely genuine),
    "ai_generated_probability": 0-100 (probability this was AI-written),
    "verdict": "Genuine / Possibly Embellished / Likely Fake / AI-Generated / Needs Verification",
    "red_flags": ["flag1", "flag2"],
    "positive_indicators": ["indicator1", "indicator2"],
    "detailed_analysis": "Paragraph explaining the reasoning",
    "suggested_verification_steps": ["step1", "step2"]
}}

CANDIDATE: {candidate_name}

RESUME:
{resume_text[:4000]}
"""
    response = call_groq_api(prompt, max_tokens=1500)
    if response:
        try:
            return json.loads(response)
        except:
            return None
    return None

# ============ RESUME PARSING HELPERS ============
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
    """Extract email with multiple pattern matching"""
    patterns = [
        r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b',
        r'[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}',
        r'Email\s*[:：]\s*([A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,})',
        r'E-mail\s*[:：]\s*([A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,})'
    ]
    
    for pattern in patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            # If it's a labeled pattern (Email:/E-mail:), return group 1
            if 'Email' in pattern or 'E-mail' in pattern:
                return match.group(1)
            return match.group(0)
    
    return ""

def extract_phone(text):
    """Extract phone with better pattern matching"""
    patterns = [
        r'\+\d{1,3}[-.\s]?\(?\d{2,4}\)?[-.\s]?\d{3,4}[-.\s]?\d{4}',
        r'\d{3}[-.\s]?\d{3}[-.\s]?\d{4}',
        r'\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}',
        r'Phone\s*[:：]\s*([+\d\s\-()]{10,})',
        r'Mobile\s*[:：]\s*([+\d\s\-()]{10,})',
        r'Contact\s*[:：]\s*([+\d\s\-()]{10,})'
    ]
    
    for pattern in patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            # If it's a labeled pattern (Phone:/Mobile:/Contact:), return group 1
            if any(x in pattern for x in ['Phone', 'Mobile', 'Contact']):
                phone = match.group(1)
            else:
                phone = match.group(0)
            # Clean up - keep only digits, +, -, (, )
            phone = re.sub(r'[^\d+\s\-()]', '', phone)
            return phone
    
    return ""

def extract_indian_mobile(text):
    """Extract Indian mobile (starts with 6-9, 10 digits)"""
    patterns = [
        r'(?:\+91[\-\s]?)?([6-9]\d{9})\b',
        r'(?:\+91[\-\s]?)?([6-9]\d{4}[\-\s]?\d{5})\b',
    ]
    for pattern in patterns:
        match = re.search(pattern, text)
        if match:
            return match.group(0).strip()
    return ""

def extract_pan(text):
    """Extract Indian PAN number"""
    match = re.search(r'\b[A-Z]{5}[0-9]{4}[A-Z]{1}\b', text)
    return match.group(0) if match else ""

def extract_aadhaar(text):
    """Extract Aadhaar (masked in output)"""
    match = re.search(r'\b\d{4}\s?\d{4}\s?\d{4}\b', text)
    return match.group(0) if match else ""

def extract_pincode(text):
    """Extract Indian PIN code"""
    match = re.search(r'\b[1-9][0-9]{5}\b', text)
    return match.group(0) if match else ""

def extract_cgpa_or_percentage(text):
    """Extract CGPA or percentage"""
    patterns = [
        (r'(\d+\.?\d*)\s*(?:CGPA|GPA)\s*(?:/\s*10)?', 'CGPA'),
        (r'(\d+\.?\d*)\s*%', 'Percentage'),
        (r'(\d+\.?\d*)\s*(?:/\s*4)\s*(?:CGPA|GPA)?', 'CGPA/4'),
    ]
    for pattern, kind in patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            return f"{match.group(1)} {kind}"
    return ""

def strip_indian_honorifics(name):
    """Remove Dr., Mr., Mrs., Ms., Shri, Smt., Prof., etc."""
    if not name:
        return ""
    honorifics = r'^(Dr\.?|Mr\.?|Mrs\.?|Ms\.?|Shri|Smt\.?|Prof\.?|Sri|Kum\.?|Er\.?|CA|Adv\.?)\s+'
    return re.sub(honorifics, '', name.strip(), flags=re.IGNORECASE).strip()

def extract_years_from_text(text, skill):
    patterns = [
        r'(\d+)\+?\s*years? of experience in ' + re.escape(skill),
        r'(\d+)\+?\s*years? in ' + re.escape(skill),
        r'(\d+)\+?\s*yrs? of experience with ' + re.escape(skill),
        r'(\d+)\+?\s*years?.*?' + re.escape(skill),
    ]
    for pattern in patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            return int(match.group(1))
    return 0

def extract_name_from_text(text):
    """Extract name intelligently - returns actual name, not job title"""
    lines = text.strip().split('\n')
    
    # Clean lines
    lines = [line.strip() for line in lines if line.strip()]
    
    # Common headers to skip (these are NOT names)
    common_headers = ['resume', 'curriculum vitae', 'cv', 'profile', 'summary', 
                      'objective', 'contact', 'education', 'experience', 'skills',
                      'software developer', 'engineer', 'manager', 'analyst', 
                      'consultant', 'architect', 'specialist', 'lead', 'senior']
    
    # Strategy 1: Check first 10 lines for a proper name
    for line in lines[:10]:
        line_lower = line.lower()
        
        # Skip if it's a common header or job title
        if any(header in line_lower for header in common_headers):
            continue
        
        # Skip if too short or too long
        if len(line) < 10 or len(line) > 50:
            continue
        
        # Skip if it contains email or URL
        if '@' in line or 'http' in line_lower or 'www.' in line_lower:
            continue
        
        # Skip if it contains phone number patterns
        if re.search(r'\d{3}[-.\s]?\d{3}[-.\s]?\d{4}', line):
            continue
        
        # Check if it looks like a proper name (at least 2 words, both capitalized)
        words = line.split()
        if len(words) >= 2:
            # Check if first and last words start with capital letters
            if words[0][0].isupper() and words[-1][0].isupper():
                # Make sure it's not all caps (could be company name)
                if not line.isupper():
                    # Split into parts and return as tuple
                    name_parts = line.split()
                    first_name = name_parts[0] if name_parts else ""
                    last_name = name_parts[-1] if len(name_parts) > 1 else ""
                    middle_name = " ".join(name_parts[1:-1]) if len(name_parts) > 2 else ""
                    return first_name, last_name, middle_name
        
        # If first word is capitalized and line has 2-4 words
        if len(words) in [2, 3, 4] and words[0][0].isupper():
            name_parts = line.split()
            first_name = name_parts[0] if name_parts else ""
            last_name = name_parts[-1] if len(name_parts) > 1 else ""
            middle_name = " ".join(name_parts[1:-1]) if len(name_parts) > 2 else ""
            return first_name, last_name, middle_name

        # Strategy 1.5: Indian name patterns
    # Handle "Dr. S. Rajesh Kumar" style names
    indian_name_pattern = r'^(?:(?:Dr\.?|Mr\.?|Mrs\.?|Ms\.?|Shri|Smt\.?|Prof\.?|Sri|Er\.?|CA|Adv\.?)\s+)?((?:[A-Z]\.\s*){1,3}[A-Z][a-z]+(?:\s+[A-Z][a-z]+){0,3})$'
    for line in lines[:10]:
        stripped = line.strip()
        match = re.match(indian_name_pattern, stripped)
        if match:
            name_clean = strip_indian_honorifics(stripped)
            parts = name_clean.split()
            if len(parts) >= 1:
                first = parts[0]
                last = parts[-1] if len(parts) > 1 else ''
                middle = ' '.join(parts[1:-1]) if len(parts) > 2 else ''
                return first, last, middle
    
    # Strategy 1.6: All caps Indian name (RAJESH KUMAR)
    for line in lines[:5]:
        stripped = line.strip()
        if re.match(r'^([A-Z]{2,}\s+){1,3}[A-Z]{2,}$', stripped):
            parts = stripped.split()
            if 2 <= len(parts) <= 4:
                return parts[0].title(), parts[-1].title(), ' '.join(p.title() for p in parts[1:-1])
    
    # Strategy 2: Use regex pattern for proper names
    name_pattern = r'^[A-Z][a-z]+(?:\s+[A-Z][a-z]+){1,3}$'
    for line in lines[:15]:
        # Remove punctuation and extra spaces
        cleaned = re.sub(r'[^\w\s]', '', line).strip()
        if re.match(name_pattern, cleaned):
            name_parts = cleaned.split()
            first_name = name_parts[0] if name_parts else ""
            last_name = name_parts[-1] if len(name_parts) > 1 else ""
            middle_name = " ".join(name_parts[1:-1]) if len(name_parts) > 2 else ""
            return first_name, last_name, middle_name
    
    # Strategy 3: Use spaCy NER if available
    if nlp:
        doc = nlp(text[:500])
        for ent in doc.ents:
            if ent.label_ == 'PERSON':
                # Make sure it's not a company or product
                if len(ent.text.split()) >= 2:
                    name_parts = ent.text.split()
                    first_name = name_parts[0] if name_parts else ""
                    last_name = name_parts[-1] if len(name_parts) > 1 else ""
                    middle_name = " ".join(name_parts[1:-1]) if len(name_parts) > 2 else ""
                    return first_name, last_name, middle_name
    
    # Strategy 4: Look for "Name:" or "Full Name:" prefix
    name_prefix_patterns = [
        r'Name\s*[:：]\s*([A-Z][a-z]+(?:\s+[A-Z][a-z]+)+)',
        r'Full Name\s*[:：]\s*([A-Z][a-z]+(?:\s+[A-Z][a-z]+)+)',
        r'Candidate Name\s*[:：]\s*([A-Z][a-z]+(?:\s+[A-Z][a-z]+)+)'
    ]
    for pattern in name_prefix_patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            name_parts = match.group(1).split()
            first_name = name_parts[0] if name_parts else ""
            last_name = name_parts[-1] if len(name_parts) > 1 else ""
            middle_name = " ".join(name_parts[1:-1]) if len(name_parts) > 2 else ""
            return first_name, last_name, middle_name

        # Strategy 5: Check first 3 lines for FirstName LastName pattern
    for line in lines[:3]:
        cleaned = re.sub(r'[^A-Za-z\s\.]', '', line).strip()
        parts = cleaned.split()
        if len(parts) >= 2 and all(p and p[0].isupper() for p in parts[:2]):
            return parts[0], parts[-1], ' '.join(parts[1:-1]) if len(parts) > 2 else ''
    
    # Fallback: return first line that's not a common header
    for line in lines[:5]:
        line_lower = line.lower()
        if line and len(line) < 50:
            if not any(header in line_lower for header in common_headers):
                if '@' not in line and not re.search(r'\d{3}[-.\s]?\d{3}[-.\s]?\d{4}', line):
                    name_parts = line.split()
                    first_name = name_parts[0] if name_parts else ""
                    last_name = name_parts[-1] if len(name_parts) > 1 else ""
                    middle_name = " ".join(name_parts[1:-1]) if len(name_parts) > 2 else ""
                    return first_name, last_name, middle_name
    
    return "", "", ""
    
def fallback_parse_resume(text):
    """Enhanced fallback parser - extracts maximum details from resume"""
    first_name, last_name, middle_name = extract_name_from_text(text)
    email = extract_email(text)
    phone = extract_phone(text)
    
    # Expanded skill list
    tech_skills = [
        'python', 'java', 'javascript', 'typescript', 'c', 'c++', 'c#', '.net', 'php', 'ruby', 'golang', 'go',
        'rust', 'scala', 'kotlin', 'swift', 'r', 'matlab', 'shell scripting', 'bash', 'powershell', 'vb.net',
        'html', 'css', 'sass', 'less', 'bootstrap', 'tailwind css', 'material ui', 'react', 'react native',
        'angular', 'vue.js', 'vue', 'svelte', 'next.js', 'nuxt', 'gatsby', 'jquery', 'redux', 'mobx',
        'webpack', 'babel', 'vite', 'graphql', 'rest api', 'soap', 'microservices', 'web services',
        'sql', 'mysql', 'postgresql', 'mongodb', 'oracle', 'sql server', 'sqlite', 'redis', 'elasticsearch',
        'cassandra', 'dynamodb', 'mariadb', 'firebase', 'snowflake', 'redshift', 'bigquery', 'teradata',
        'neo4j', 'prisma', 'sequelize', 'typeorm', 'hibernate',
        'aws', 'azure', 'gcp', 'google cloud', 'heroku', 'digitalocean', 'docker', 'kubernetes', 'openshift',
        'jenkins', 'gitlab ci', 'github actions', 'circleci', 'terraform', 'ansible', 'puppet', 'chef',
        'prometheus', 'grafana', 'datadog', 'splunk', 'elk stack', 'nginx', 'apache', 'tomcat', 'iis',
        'serverless', 'lambda', 'cloudformation', 'azure devops',
        'machine learning', 'deep learning', 'nlp', 'computer vision', 'data science', 'data engineering',
        'data analytics', 'tensorflow', 'pytorch', 'keras', 'scikit-learn', 'pandas', 'numpy', 'matplotlib',
        'seaborn', 'spark', 'hadoop', 'kafka', 'airflow', 'dbt', 'tableau', 'power bi', 'looker', 'qlik',
        'excel', 'vba', 'sap bo', 'ssis', 'ssrs', 'ssas', 'databricks', 'mlflow',
        'sap abap', 'sap fico', 'sap mm', 'sap sd', 'sap hana', 'sap bw', 'sap basis', 'sap crm',
        'sap s/4hana', 'sap pi/po', 'sap bpc', 'sap successfactors', 'sap ariba', 'sap cds',
        'sap bapi', 'sap idoc', 'sap smartforms', 'sap adobe forms', 'sap webdynpro', 'sap fiori',
        'sap ui5', 'sap odata', 'sap workflow', 'sap bopf', 'sap gateway',
        'salesforce', 'apex', 'visualforce', 'lightning', 'lwc', 'soql', 'sosl', 'sales cloud',
        'service cloud', 'marketing cloud', 'commerce cloud', 'community cloud', 'salesforce crm',
        'selenium', 'junit', 'testng', 'cucumber', 'jest', 'mocha', 'cypress', 'postman', 'jmeter',
        'loadrunner', 'appium', 'protractor', 'pytest', 'qa automation', 'manual testing',
        'git', 'github', 'gitlab', 'bitbucket', 'jira', 'confluence', 'slack', 'trello', 'asana',
        'figma', 'sketch', 'adobe xd', 'photoshop', 'illustrator', 'invision', 'zeplin',
        'linux', 'unix', 'windows', 'macos', 'android', 'ios', 'flutter', 'xamarin',
        'servicenow', 'workday', 'pega', 'appian', 'powerapps', 'sharepoint', 'dynamics 365',
        'mulesoft', 'dell boomi', 'informatica', 'talend', 'apache nifi',
        'blockchain', 'solidity', 'ethereum', 'hyperledger', 'iot', 'embedded systems',
        'agile', 'scrum', 'kanban', 'safe', 'waterfall', 'devops', 'ci/cd', 'sre'
    ]
    
    found_skills = []
    text_lower = text.lower()
    for skill in tech_skills:
        if skill in text_lower:
            years = extract_years_from_text(text, skill)
            found_skills.append({"skill": skill.title() if len(skill) <= 3 else skill, "years_of_experience": years})
    
    # Extract education
    education = []
    edu_patterns = [
        r'(b\.?tech|m\.?tech|b\.?e|m\.?e|bca|mca|bsc|msc|bba|mba|phd|diploma|bachelor|master)[^\n]*',
    ]
    for pattern in edu_patterns:
        matches = re.findall(pattern, text, re.IGNORECASE)
        for m in matches[:3]:
            education.append(m.strip())
    
    # Extract work experience
    work_exp = []
    exp_pattern = r'([A-Z][A-Za-z\s&.,]+)\s*[-–]\s*(?:Present|Current)'
    companies = re.findall(exp_pattern, text)
    for company in companies[:5]:
        work_exp.append({"company": company.strip(), "role": "", "duration": "", "description": ""})
    
    # Extract certifications
    certs = []
    cert_patterns = [
        r'(aws|azure|gcp|google|salesforce|pmp|scrum|safe|itil|six sigma|cissp|ceh|comptia|oracle|sap|csm|cka|ckad)[^\n]*certif[^\n]*',
        r'certif[^\n]*',
    ]
    for pattern in cert_patterns:
        matches = re.findall(pattern, text, re.IGNORECASE)
        for m in matches[:5]:
            certs.append(m.strip())
    
    # Extract LinkedIn
    linkedin = ''
    li_match = re.search(r'(https?://[^\s]*linkedin[^\s]*)', text, re.IGNORECASE)
    if li_match:
        linkedin = li_match.group(1)
    
    # Extract CTC
    current_ctc = ''
    ctc_match = re.search(r'(?:current\s*ctc|ctc)\s*[:-]\s*([\d.,]+\s*(?:lpa|lakh|lacs|l))', text, re.IGNORECASE)
    if ctc_match:
        current_ctc = ctc_match.group(1)
    
    # Extract total experience
    total_exp = 0
    exp_match = re.search(r'(\d+)\s*(?:\+|plus)?\s*years?\s*(?:of\s*)?(?:total\s*)?experience', text, re.IGNORECASE)
    if exp_match:
        total_exp = int(exp_match.group(1))
    
    return {
        'first_name': first_name,
        'last_name': last_name,
        'middle_name': middle_name,
        'phone': phone,
        'email': email,
        'address': "",
        'linkedin': linkedin,
        'other_social': "",
        'current_role': "",
        'designation': "",
        'current_ctc': current_ctc,
        'expected_ctc': "",
        'years_of_experience': total_exp,
        'notice_period_days': 0,
        'employment_status': "Employed",
        'core_skills': found_skills[:50],
        'relevant_experience': [],
        'education': education,
        'certifications': certs,
        'work_experience': work_exp,
        'summary': "",
        'resume_text': text[:6000],
        'ai_used': False
    }
def save_candidate_to_db(candidate_data, resume_path='', resume_original_name=''):
    skills = json.dumps(candidate_data.get('core_skills', []))
    work_exp = json.dumps(candidate_data.get('work_experience', []))
    certs = json.dumps(candidate_data.get('certifications', []))
    attachments = json.dumps(candidate_data.get('attachments', []))
    
    # Fix: Convert dict/list to JSON string for these fields
    education = candidate_data.get('education', '')
    if isinstance(education, (dict, list)):
        education = json.dumps(education)
    
    resume_text = candidate_data.get('resume_text', '')
    if isinstance(resume_text, (dict, list)):
        resume_text = json.dumps(resume_text)
    
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('''INSERT INTO candidates 
        (first_name, last_name, middle_name, phone, email, address, linkedin,
         current_role, current_ctc, expected_ctc, designation, location, years_of_experience,
         employment_status, notice_period_days, work_experience, certifications,
         core_skills, education, notes, resume_text, resume_filename, uploaded_by,
         resume_file_path, resume_original_filename,
         proposed_client, proposed_requirement, stage, attachments,
         analysis_summary, matched_jd, uploaded_by_name)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)''',
        (str(candidate_data.get('first_name') or ''),
         str(candidate_data.get('last_name') or ''),
         str(candidate_data.get('middle_name') or ''),
         str(candidate_data.get('phone') or ''),
         str(candidate_data.get('email') or ''),
         str(candidate_data.get('address') or ''),
         str(candidate_data.get('linkedin') or ''),
         str(candidate_data.get('current_role') or ''),
         str(candidate_data.get('current_ctc') or ''),
         str(candidate_data.get('expected_ctc') or ''),
         str(candidate_data.get('designation') or ''),
         str(candidate_data.get('location') or ''),
         str(candidate_data.get('years_of_experience') or ''),
         str(candidate_data.get('employment_status') or ''),
         candidate_data.get('notice_period_days', 0),
         work_exp, certs, skills,
         education,
         str(candidate_data.get('notes') or ''),
         resume_text,
         str(candidate_data.get('resume_filename') or ''),
         str(candidate_data.get('uploaded_by', 'ShahnaIT')),
         str(resume_path or ''),
         str(resume_original_name or ''),
         str(candidate_data.get('proposed_client') or ''),
         str(candidate_data.get('proposed_requirement') or ''),
         str(candidate_data.get('stage', 'new')),
         attachments,
         str(candidate_data.get('analysis_summary') or ''),
         str(candidate_data.get('matched_jd') or ''),
         str(candidate_data.get('uploaded_by_name', 'ShahnaIT HR'))))
    
    candidate_id = c.lastrowid

    # Save Indian-specific fields
    if candidate_data.get('pan_number'):
        try:
            c.execute('UPDATE candidates SET pan_number = ? WHERE id = ?', (candidate_data['pan_number'], candidate_id))
        except: pass
    if candidate_data.get('cgpa_or_percentage'):
        try:
            c.execute('UPDATE candidates SET cgpa = ? WHERE id = ?', (candidate_data['cgpa_or_percentage'], candidate_id))
        except: pass
    if candidate_data.get('pincode'):
        try:
            c.execute('UPDATE candidates SET pincode = ? WHERE id = ?', (candidate_data['pincode'], candidate_id))
        except: pass

    # Save relevant_experience
    rel_exp = candidate_data.get('relevant_experience', [])
    if isinstance(rel_exp, list) and rel_exp:
        c.execute('UPDATE candidates SET relevant_experience = ? WHERE id = ?',
                  (json.dumps(rel_exp), candidate_id))
    
    # Save projects
    projects = candidate_data.get('projects', [])
    if isinstance(projects, list) and projects:
        for proj in projects:
            if isinstance(proj, dict):
                c.execute('''INSERT INTO candidate_projects 
                    (candidate_id, project_name, role, organization, start_date, end_date, description, tech_stack)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)''',
                    (candidate_id,
                     str(proj.get('project_name') or ''),
                     str(proj.get('role') or ''),
                     str(proj.get('organization') or ''),
                     str(proj.get('start_date') or ''),
                     str(proj.get('end_date') or ''),
                     str(proj.get('description') or ''),
                     str(proj.get('tech_stack') or '')))
    
    # Save education entries
    edu_list = candidate_data.get('education', [])
    if isinstance(edu_list, list):
        for edu in edu_list:
            if isinstance(edu, dict):
                c.execute('''INSERT INTO candidate_education 
                    (candidate_id, degree, institute, field_of_study, start_year, end_year, grade, location)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)''',
                    (candidate_id,
                     str(edu.get('degree') or ''),
                     str(edu.get('institute') or edu.get('institution') or ''),
                     str(edu.get('field_of_study') or ''),
                     str(edu.get('start_year') or edu.get('year') or ''),
                     str(edu.get('end_year') or ''),
                     str(edu.get('grade') or edu.get('percentage') or ''),
                     str(edu.get('location') or '')))
    
    conn.commit()
    conn.close()
    return candidate_id
    # ============ ATTACHMENT UPLOAD ============
UPLOAD_FOLDER = '/data/attachments'
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

# ---- Attachment allowlist: PDF, DOCX, JPG, PNG only ----
import uuid
import zipfile

ALLOWED_ATTACHMENT_EXT = {'pdf', 'docx', 'jpg', 'jpeg', 'png'}
ATTACHMENT_MIME = {
    'pdf': 'application/pdf',
    'docx': 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
    'jpg': 'image/jpeg',
    'jpeg': 'image/jpeg',
    'png': 'image/png',
}
MAX_ATTACHMENT_BYTES = 10 * 1024 * 1024   # 10 MB per file


def _attachment_content_ok(ext, path):
    try:
        with open(path, 'rb') as fh:
            head = fh.read(1024)
        if ext == 'pdf':
            return b'%PDF-' in head
        if ext in ('jpg', 'jpeg'):
            return head.startswith(b'\xff\xd8\xff')
        if ext == 'png':
            return head.startswith(b'\x89PNG\r\n\x1a\n')
        if ext == 'docx':
            if not zipfile.is_zipfile(path):
                return False
            with zipfile.ZipFile(path) as z:
                return any(name.startswith('word/') for name in z.namelist())
    except (OSError, zipfile.BadZipFile):
        return False
    return False


def _candidate_attachment_dir(candidate_id):
    return os.path.join(UPLOAD_FOLDER, f"candidate_{candidate_id}")


def _resolve_attachment(candidate_id, filename):
    folder = os.path.realpath(_candidate_attachment_dir(candidate_id))
    real = os.path.realpath(os.path.join(folder, filename))
    if real.startswith(folder + os.sep) and os.path.isfile(real):
        return real
    return None


@app.route('/api/candidates/<int:candidate_id>/attachments', methods=['POST'])
@login_required()
def upload_candidate_attachment(candidate_id):
    try:
        if 'file' not in request.files:
            return jsonify({"success": False, "error": "No file provided"}), 400

        file = request.files['file']
        if file.filename == '':
            return jsonify({"success": False, "error": "No file selected"}), 400

        original = secure_filename(file.filename) or 'attachment'
        ext = os.path.splitext(original)[1].lower().lstrip('.')
        if ext not in ALLOWED_ATTACHMENT_EXT:
            return jsonify({"success": False, "error": "Only PDF, DOCX, JPG and PNG files are allowed"}), 400

        file.stream.seek(0, os.SEEK_END)
        size = file.stream.tell()
        file.stream.seek(0)
        if size > MAX_ATTACHMENT_BYTES:
            return jsonify({"success": False, "error": "File is too large (max 10 MB)"}), 413

        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        c = conn.cursor()
        c.execute('SELECT attachments FROM candidates WHERE id = ?', (candidate_id,))
        row = c.fetchone()
        if not row:
            conn.close()
            return jsonify({"success": False, "error": "Candidate not found"}), 404

        candidate_folder = _candidate_attachment_dir(candidate_id)
        os.makedirs(candidate_folder, exist_ok=True)

        stem = os.path.splitext(original)[0][:60] or 'attachment'
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        unique_filename = f"{stem}_{timestamp}_{uuid.uuid4().hex[:6]}.{ext}"
        file_path = os.path.join(candidate_folder, unique_filename)
        file.save(file_path)

        if not _attachment_content_ok(ext, file_path):
            os.remove(file_path)
            conn.close()
            return jsonify({"success": False, "error": "File content does not match its extension"}), 400

        attachments = []
        if row['attachments']:
            try:
                attachments = json.loads(row['attachments']) if isinstance(row['attachments'], str) else row['attachments']
            except Exception:
                attachments = []

        attachments.append({
            'filename': unique_filename,
            'original_name': original,
            'uploaded_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'size': os.path.getsize(file_path)
        })

        c.execute('UPDATE candidates SET attachments = ? WHERE id = ?',
                  (json.dumps(attachments), candidate_id))
        conn.commit()
        conn.close()

        return jsonify({
            "success": True,
            "message": "File uploaded",
            "attachments": attachments
        })
    except Exception:
        app.logger.exception('attachment upload failed')
        return jsonify({"success": False, "error": "Upload failed"}), 500


@app.route('/api/candidates/<int:candidate_id>/attachments/<filename>', methods=['GET'])
@login_required()
def download_attachment(candidate_id, filename):
    file_path = _resolve_attachment(candidate_id, filename)
    if not file_path:
        return jsonify({"error": "File not found"}), 404

    ext = os.path.splitext(file_path)[1].lower().lstrip('.')
    response = send_file(
        file_path,
        mimetype=ATTACHMENT_MIME.get(ext, 'application/octet-stream'),
        as_attachment=True,
        download_name=os.path.basename(file_path),
    )
    response.headers['X-Content-Type-Options'] = 'nosniff'
    response.headers['Content-Security-Policy'] = "default-src 'none'; sandbox"
    response.headers['Cache-Control'] = 'private, no-store'
    return response


@app.route('/api/candidates/<int:candidate_id>/attachments/<filename>', methods=['DELETE'])
@login_required()
def delete_attachment(candidate_id, filename):
    try:
        file_path = _resolve_attachment(candidate_id, filename)
        if file_path:
            os.remove(file_path)

        conn = sqlite3.connect(DB_PATH)
        try:
            c = conn.cursor()
            c.execute('SELECT attachments FROM candidates WHERE id = ?', (candidate_id,))
            row = c.fetchone()
            if row and row[0]:
                attachments = json.loads(row[0]) if isinstance(row[0], str) else row[0]
                attachments = [a for a in attachments if a.get('filename') != filename]
                c.execute('UPDATE candidates SET attachments = ? WHERE id = ?',
                          (json.dumps(attachments), candidate_id))
            conn.commit()
        finally:
            conn.close()

        return jsonify({"success": True, "message": "File deleted"})
    except Exception:
        app.logger.exception('attachment delete failed')
        return jsonify({"success": False, "error": "Delete failed"}), 500

@app.route('/api/requirements', methods=['GET'])
def get_requirements():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    c.execute('SELECT * FROM requirements ORDER BY id DESC')
    requirements = [dict(row) for row in c.fetchall()]
    conn.close()
    return jsonify(requirements)

# ============================================
# AUTH ROUTES
# ============================================

@app.route('/api/auth/login', methods=['POST'])
def login():
    data = request.get_json(silent=True) or {}
    email = str(data.get('email', '')).strip().lower()
    password = data.get('password', '')

    if not email or not password or not isinstance(password, str):
        return jsonify({'error': 'Email and password required'}), 400

    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    c.execute('SELECT * FROM users WHERE email = ? AND is_active = 1', (email,))
    user = c.fetchone()
    conn.close()

    if not user:
        verify_password(_DUMMY_PASSWORD_HASH, password)
        return jsonify({'error': 'Invalid email or password'}), 401

    valid, needs_upgrade = verify_password(user['password_hash'], password)
    if not valid:
        return jsonify({'error': 'Invalid email or password'}), 401

    session['user_id'] = user['id']
    session['role'] = user['role']
    session['user_name'] = user['full_name']

    conn = sqlite3.connect(DB_PATH)
    try:
        c = conn.cursor()
        if needs_upgrade:
            c.execute('UPDATE users SET password_hash = ?, last_login = CURRENT_TIMESTAMP WHERE id = ?',
                      (hash_password(password), user['id']))
        else:
            c.execute('UPDATE users SET last_login = CURRENT_TIMESTAMP WHERE id = ?', (user['id'],))
        conn.commit()
    finally:
        conn.close()

    return jsonify({
        'message': 'Login successful',
        'user': {
            'id': user['id'],
            'email': user['email'],
            'full_name': user['full_name'],
            'role': user['role']
        }
    })

@app.route('/api/auth/logout', methods=['POST'])
def logout():
    session.clear()
    return jsonify({'message': 'Logged out'})

@app.route('/api/auth/me', methods=['GET'])
def get_me():
    user = get_current_user()
    if not user:
        return jsonify({'error': 'Not logged in'}), 401
    return jsonify({'user': user})

@app.route('/api/auth/users', methods=['GET'])
@login_required('admin')
def get_users():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    c.execute('SELECT id, email, full_name, role, is_active, last_login, created_at FROM users ORDER BY id')
    users = [dict(row) for row in c.fetchall()]
    conn.close()
    return jsonify(users)

@app.route('/api/auth/users', methods=['POST'])
@login_required('admin')
def create_user():
    data = request.get_json(silent=True) or {}
    email = str(data.get('email', '')).strip().lower()
    password = data.get('password', '')
    full_name = data.get('full_name', '')
    role = data.get('role', 'recruiter')

    if not email or not password:
        return jsonify({'error': 'Email and password required'}), 400

    if role not in ['admin', 'manager', 'recruiter']:
        return jsonify({'error': 'Invalid role'}), 400

    problem = password_policy_error(password, email)
    if problem:
        return jsonify({'error': problem}), 400

    password_hash = hash_password(password)

    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    try:
        c.execute('INSERT INTO users (email, password_hash, full_name, role) VALUES (?, ?, ?, ?)',
                  (email, password_hash, full_name, role))
        conn.commit()
    except sqlite3.IntegrityError:
        conn.close()
        return jsonify({'error': 'Email already exists'}), 400
    conn.close()

    return jsonify({'message': 'User created'})
@app.route('/api/auth/users/<int:user_id>', methods=['PUT'])
@login_required('admin')
def update_user(user_id):
    data = request.get_json(silent=True) or {}

    if 'password' in data:
        problem = password_policy_error(data['password'])
        if problem:
            return jsonify({'error': problem}), 400

    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()

    if 'role' in data:
        c.execute('UPDATE users SET role = ? WHERE id = ?', (data['role'], user_id))
    if 'is_active' in data:
        c.execute('UPDATE users SET is_active = ? WHERE id = ?', (data['is_active'], user_id))
    if 'full_name' in data:
        c.execute('UPDATE users SET full_name = ? WHERE id = ?', (data['full_name'], user_id))
    if 'password' in data:
        c.execute('UPDATE users SET password_hash = ? WHERE id = ?', (hash_password(data['password']), user_id))

    conn.commit()
    conn.close()
    return jsonify({'message': 'User updated'})

@app.route('/api/candidates/check-duplicate', methods=['POST'])
@login_required()
def check_duplicate():
    data = request.json
    email = data.get('email', '').strip().lower()
    phone = data.get('phone', '').strip()
    
    if not email and not phone:
        return jsonify({'duplicate': False})
    
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    
    matches = []
    if email:
        c.execute("SELECT id, first_name, last_name, email, phone FROM candidates WHERE LOWER(email) = ?", (email,))
        matches.extend([dict(row) for row in c.fetchall()])
    
    if phone and not matches:
        c.execute("SELECT id, first_name, last_name, email, phone FROM candidates WHERE phone = ?", (phone,))
        matches.extend([dict(row) for row in c.fetchall()])
    
    conn.close()
    
    return jsonify({
        'duplicate': len(matches) > 0,
        'matches': matches,
        'matched_by': 'email' if email and any(m['email'] == email for m in matches) else 'phone' if matches else None
    })

@app.route('/api/jobs/parse-jd', methods=['POST'])
def parse_jd_file():
    """Parse uploaded JD file (PDF/DOCX)"""
    try:
        if 'file' not in request.files:
            return jsonify({"success": False, "error": "No file provided"}), 400
        
        file = request.files['file']
        if file.filename == '':
            return jsonify({"success": False, "error": "No file selected"}), 400
        
        filename = secure_filename(file.filename)
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(filepath)
        
        # Extract text based on file type
        text = ""
        if filename.endswith('.pdf'):
            pdf_reader = PyPDF2.PdfReader(filepath)
            for page in pdf_reader.pages:
                text += page.extract_text() or ""
        elif filename.endswith('.docx'):
            doc = docx.Document(filepath)
            for para in doc.paragraphs:
                text += para.text + "\n"
        else:
            os.remove(filepath)
            return jsonify({"success": False, "error": "Only PDF and DOCX supported"}), 400
        
        os.remove(filepath)
        
        if not text.strip():
            return jsonify({"success": False, "error": "Could not extract text"}), 400
        
        # Parse JD text
        parsed = parse_jd_text(text)
        
        return jsonify({"success": True, "text": text, "parsed": parsed})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

def parse_jd_with_groq(text):
    """Use AI to parse JD text into structured fields"""
    prompt = f"""Parse this job description. Extract ALL fields. Return ONLY valid JSON.

{{
    "title": "Job title",
    "company": "Company name if mentioned, else empty",
    "roles_responsibilities": "Key responsibilities as bullet points (use \\n for new lines)",
    "qualifications": "Required qualifications as bullet points",
    "required_skills": ["skill1", "skill2"],
    "certifications_required": ["cert1", "cert2"],
    "working_mode": "Remote / Hybrid / Onsite / Not Specified",
    "hybrid_days": number or 0,
    "business_model": "C2C / C2H / Permanent / Contract / Not Specified",
    "payroll_company": "Payroll company or empty",
    "client_name": "Client company or empty",
    "end_client": "End client or empty",
    "years_of_experience": number or 0,
    "budget": "Budget/salary or empty",
    "headcount": number or 1
}}

JOB DESCRIPTION:
{text[:4000]}
"""
    response = call_groq_api(prompt, max_tokens=1500)
    if response:
        try:
            return json.loads(response)
        except:
            return None
    return None


def parse_jd_text(text):
    """Extract key details from JD text - AI first, regex fallback"""
    
    # Try AI parsing first
    try:
        ai_result = parse_jd_with_groq(text)
        if ai_result and ai_result.get('title'):
            return {
                "title": ai_result.get('title', ''),
                "company": ai_result.get('company', ''),
                "roles_responsibilities": ai_result.get('roles_responsibilities', ''),
                "qualifications": ai_result.get('qualifications', ''),
                "required_skills": ai_result.get('required_skills', []),
                "certifications_required": ai_result.get('certifications_required', []),
                "working_mode": ai_result.get('working_mode', 'Not Specified'),
                "hybrid_days": ai_result.get('hybrid_days', 0),
                "business_model": ai_result.get('business_model', 'Not Specified'),
                "payroll_company": ai_result.get('payroll_company', ''),
                "client_name": ai_result.get('client_name', ''),
                "end_client": ai_result.get('end_client', ''),
                "years_of_experience": ai_result.get('years_of_experience', 0),
                "budget": ai_result.get('budget', ''),
                "headcount": ai_result.get('headcount', 1)
            }
    except Exception as e:
        print(f"AI JD parsing failed, using fallback: {e}")
    
    # Fallback: regex-based parsing
    import re
    result = {
        "title": "",
        "company": "",
        "roles_responsibilities": "",
        "qualifications": "",
        "required_skills": [],
        "certifications_required": [],
        "working_mode": "Not Specified",
        "hybrid_days": 0,
        "business_model": "Not Specified",
        "payroll_company": "",
        "client_name": "",
        "end_client": "",
        "years_of_experience": 0,
        "budget": "",
        "headcount": 1
    }
    
    lines = text.split('\n')
    text_lower = text.lower()
    
    # Title
    for line in lines[:15]:
        line = line.strip()
        if line and len(line) > 5 and not line.startswith('http') and not line.startswith('www'):
            skip_words = ['job description', 'jd', 'confidential', 'about us', 'company']
            if not any(line.lower().startswith(w) for w in skip_words):
                result["title"] = line[:200]
                break
    
    # Working mode
    if any(kw in text_lower for kw in ['work from home', 'remote', 'wfh', 'work remotely']):
        result["working_mode"] = "Remote"
    elif any(kw in text_lower for kw in ['hybrid']):
        result["working_mode"] = "Hybrid"
        days_match = re.search(r'(\d+)\s*day', text_lower)
        if days_match:
            result["hybrid_days"] = int(days_match.group(1))
    elif any(kw in text_lower for kw in ['work from office', 'wfo', 'onsite', 'on-site', 'in office']):
        result["working_mode"] = "Onsite"
    
    # Business model
    if any(kw in text_lower for kw in ['c2c', 'corp to corp', 'corp-to-corp']):
        result["business_model"] = "C2C"
    elif any(kw in text_lower for kw in ['c2h', 'contract to hire', 'contract-to-hire']):
        result["business_model"] = "C2H"
    elif any(kw in text_lower for kw in ['fte', 'full time', 'full-time', 'permanent']):
        result["business_model"] = "Permanent"
    elif any(kw in text_lower for kw in ['contract', 'contractor']):
        result["business_model"] = "Contract"
    
    # Years of experience
    exp_patterns = [
        r'(\d+)[\+-]?\s*(?:to\s*\d+)?\s*(?:years?|yrs?)\s*(?:of)?\s*experience',
        r'experience[:\s]*(\d+)[\+-]?\s*(?:to\s*\d+)?\s*(?:years?|yrs?)',
        r'(\d+)\+?\s*(?:years?|yrs?)(?:\s*experience)?',
        r'min(?:imum)?[:\s]*(\d+)\s*(?:years?|yrs?)',
    ]
    for pattern in exp_patterns:
        exp_match = re.search(pattern, text_lower)
        if exp_match:
            result["years_of_experience"] = int(exp_match.group(1))
            break
    
    # Budget
    budget_patterns = [
        r'(?:budget|salary|ctc|compensation)[:\s]*([\d,.]+)\s*(?:lakh|lpa|lacs|l|k|cr|crore)?',
        r'up\s*to\s*([\d,.]+)\s*(?:lakh|lpa|lacs|l|k|cr|crore)',
        r'([\d,.]+)\s*(?:lakh|lpa|lacs)\s*(?:per\s*annum)?',
    ]
    for pattern in budget_patterns:
        m = re.search(pattern, text_lower)
        if m:
            result["budget"] = m.group(0).strip()
            break
    
    # Headcount
    hc_match = re.search(r'(?:headcount|positions?|openings?|vacancies?)[:\s]*(\d+)', text_lower)
    if hc_match:
        result["headcount"] = int(hc_match.group(1))
    
    # Roles
    roles_start = ['responsibilities', 'role', 'what you will do', 'key responsibilities', 'job duties', 'the role', 'job summary']
    qual_start = ['qualification', 'requirement', 'what you need', 'what we are looking for', 'skills', 'education', 'certification', 'must have', 'required']
    
    in_roles = False
    roles_text = []
    for line in lines:
        lower = line.lower().strip()
        if not in_roles and any(kw in lower for kw in roles_start):
            in_roles = True
            if ':' in line:
                content = line.split(':', 1)[1].strip()
                if content:
                    roles_text.append(content)
            continue
        if in_roles:
            if any(kw in lower for kw in qual_start):
                in_roles = False
                continue
            cleaned = line.strip().lstrip('•-–*·◦▪▸►').strip()
            if cleaned:
                roles_text.append(cleaned)
    result["roles_responsibilities"] = '\n'.join(roles_text[:30])
    
    # Qualifications
    in_qual = False
    qual_text = []
    for line in lines:
        lower = line.lower().strip()
        if not in_qual and any(kw in lower for kw in ['qualification', 'requirement', 'what you need', 'what we are looking for', 'must have']):
            in_qual = True
            if ':' in line:
                content = line.split(':', 1)[1].strip()
                if content:
                    qual_text.append(content)
            continue
        if in_qual:
            if any(kw in lower for kw in ['responsibilities', 'about us', 'benefit', 'perks', 'preferred', 'nice to have', 'what we offer']):
                in_qual = False
                continue
            cleaned = line.strip().lstrip('•-–*·◦▪▸►').strip()
            if cleaned:
                qual_text.append(cleaned)
    result["qualifications"] = '\n'.join(qual_text[:25])
    
    # Skills
    tech_skills = [
        'python', 'java', 'javascript', 'typescript', 'react', 'angular', 'vue', 'svelte',
        'node.js', 'nodejs', 'node', 'express', 'django', 'flask', 'fastapi', 'spring', 'spring boot',
        'sql', 'mysql', 'postgresql', 'mongodb', 'oracle', 'nosql', 'redis', 'elasticsearch',
        'aws', 'azure', 'gcp', 'google cloud', 'docker', 'kubernetes', 'k8s', 'jenkins',
        'git', 'github', 'gitlab', 'bitbucket', 'linux', 'unix', 'bash',
        'salesforce', 'apex', 'visualforce', 'lwc', 'soql', 'sales cloud', 'service cloud',
        'tableau', 'powerbi', 'power bi', 'excel', 'looker', 'qlik',
        'tensorflow', 'pytorch', 'scikit-learn', 'nlp', 'machine learning', 'data science',
        'agile', 'scrum', 'kanban', 'jira', 'confluence',
        'api', 'rest', 'graphql', 'soap', 'microservices',
        'c++', 'c#', '.net', 'php', 'ruby', 'golang', 'go', 'rust', 'scala',
        'html', 'css', 'sass', 'bootstrap', 'tailwind', 'material ui',
        'redux', 'next.js', 'gatsby',
        'devops', 'ci/cd', 'terraform', 'ansible', 'puppet', 'chef',
        'prometheus', 'grafana', 'datadog', 'splunk', 'elk',
        'spark', 'hadoop', 'kafka', 'airflow', 'snowflake', 'databricks',
        'android', 'ios', 'swift', 'kotlin', 'flutter', 'react native',
        'figma', 'sketch', 'adobe', 'photoshop',
        'servicenow', 'sap', 'pega', 'appian', 'powerapps', 'sharepoint', 'dynamics', 'workday'
    ]
    found_skills = []
    for skill in tech_skills:
        if skill in text_lower:
            found_skills.append(skill)
        elif ' ' in skill and all(w in text_lower for w in skill.split()):
            found_skills.append(skill)
    result["required_skills"] = list(set(found_skills))
    
    # Certifications
    certs = [
        'aws certified', 'aws solution architect', 'aws developer',
        'azure certified', 'azure administrator', 'azure solutions architect',
        'gcp certified', 'google cloud certified',
        'pmp', 'prince2', 'scrum master', 'csm', 'psm', 'safe',
        'salesforce certified', 'salesforce administrator', 'salesforce developer',
        'comptia', 'cissp', 'ceh', 'security+', 'network+',
        'itil', 'itil v4', 'six sigma', 'lean six sigma',
        'pmi', 'pmi-acp', 'cka', 'ckad', 'cks',
        'togaf', 'cobit', 'iso', 'cisa', 'cism',
        'tableau certified', 'power bi certified',
        'oracle certified', 'sap certified'
    ]
    found_certs = []
    for cert in certs:
        if cert in text_lower:
            found_certs.append(cert)
    result["certifications_required"] = list(set(found_certs))
    
    # Client & Payroll
    for line in lines[:30]:
        lower = line.lower().strip()
        if 'end client' in lower:
            if ':' in line:
                result["end_client"] = line.split(':', 1)[1].strip()[:100]
        elif 'client' in lower and ':' in line:
            result["client_name"] = line.split(':', 1)[1].strip()[:100]
        if 'payroll' in lower and ':' in line:
            result["payroll_company"] = line.split(':', 1)[1].strip()[:100]
    
    return result
        # ============ HTML TEMPLATE ============

# ============ API ROUTES ============
@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/jobs', methods=['GET']) 
@login_required()
def get_jobs():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    c.execute('SELECT * FROM jobs ORDER BY created_at DESC')
    jobs = [dict(row) for row in c.fetchall()]
    conn.close()
    return jsonify(jobs)

@app.route('/api/jobs', methods=['POST']) 
@login_required('manager')
def create_job():
    data = request.json
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('''INSERT INTO jobs (
        title, company, description, roles_responsibilities, qualifications,
        required_skills, certifications_required, requirement_id,
        working_mode, hybrid_days, office_location, business_model,
        payroll_company, client_name, end_client,
        years_of_experience, budget, max_salary, headcount
    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)''',
    (
        data.get('title'),
        data.get('company'),
        data.get('description', ''),
        data.get('roles_responsibilities', ''),
        data.get('qualifications', ''),
        data.get('required_skills', ''),
        data.get('certifications_required', ''),
        data.get('requirement_id', ''),
        data.get('working_mode', 'Not Specified'),
        data.get('hybrid_days', 0),
        data.get('office_location', ''),
        data.get('business_model', 'Not Specified'),
        data.get('payroll_company', ''),
        data.get('client_name', data.get('company', '')),
        data.get('end_client', ''),
        data.get('years_of_experience', 0),
        data.get('budget', ''),
        data.get('max_salary', 0),
        data.get('headcount', 1)
    ))
    conn.commit()
    conn.close()

    user_name = session.get('user_name', 'Manager')
    user_role = session.get('role', '')
    if user_role == 'manager':
        notification = f"""🆕 <b>New Job Created</b>\n\n👤 <b>Created By:</b> {user_name}\n🔹 <b>Title:</b> {data.get('title', 'N/A')}\n🏢 <b>Company:</b> {data.get('company', 'N/A')}\n📋 <b>Job ID:</b> {data.get('requirement_id', 'N/A')}"""
        send_telegram_message(notification, to_admin=True)    
    return jsonify({'message': 'Job created'})
@app.route('/api/candidates/<int:candidate_id>/propose', methods=['PUT'])
@login_required()
def mark_proposed(candidate_id):
    data = request.json
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('UPDATE candidates SET proposed_date = ? WHERE id = ?', 
              (data.get('proposed_date'), candidate_id))
    conn.commit()
    conn.close()
    return jsonify({'message': 'Marked as proposed'})

# ============ PROJECTS API ============
# ============ PROPOSAL DISPATCH: resume (.docx) + tracker email ============
import io
import html as _html
import threading
import time
from email.message import EmailMessage
from email.utils import formataddr
from html.parser import HTMLParser

import docx as _docx
from docx.enum.table import WD_CELL_VERTICAL_ALIGNMENT as _VALIGN, WD_ROW_HEIGHT_RULE as _ROWRULE
from docx.enum.text import WD_ALIGN_PARAGRAPH as _ALIGN
from docx.oxml import OxmlElement as _OxmlElement
from docx.oxml.ns import qn as _qn
from docx.shared import Cm as _Cm, Pt as _Pt, RGBColor as _RGB

DISPATCH_FOOTER_TEXT = 'Proprietary & Confidential - An asset of ShahnaIT'
DISPATCH_MAX_BLANK_PROJECTS = 10
DISPATCH_MAX_PROJECTS = 30
DISPATCH_RATE_LIMIT = (15, 600)        # max 15 sends per user per 10 minutes (counted per worker process)
_DISPATCH_EMAIL_RE = re.compile(r'^[A-Za-z0-9._%+\-]+@[A-Za-z0-9\-]+(?:\.[A-Za-z0-9\-]+)*\.[A-Za-z]{2,}$')
_CONTACT_EMAIL_RE = re.compile(r'[A-Za-z0-9._%+\-]+@[A-Za-z0-9\-]+(?:\.[A-Za-z0-9\-]+)*\.[A-Za-z]{2,}')
_CONTACT_PHONE_RE = re.compile(
    r'(?<!\d)(?:\+\d{1,3}[\s\-]?\d[\d\s\-]{7,13}\d|(?:\+?\d{1,3}[\s\-]?)?[6-9]\d{4}[\s\-]?\d{5})(?!\d)')
_CONTACT_LABEL_RE = re.compile(r'(?im)\b(?:e-?mail(?:\s*id)?|phone|mobile|mob|contact(?:\s*no\.?)?|tel)\s*[:\-]?\s*$')


def _dispatch_scrub_contact(text):
    """Remove e-mail addresses and phone numbers from free text (used when 'Mask Contact Details' is on)."""
    text = _CONTACT_EMAIL_RE.sub('', str(text or ''))
    text = _CONTACT_PHONE_RE.sub('', text)
    text = _CONTACT_LABEL_RE.sub('', text)
    return re.sub(r'[ \t]{2,}', ' ', text).strip()


def _dispatch_error(message, status):
    return jsonify({'success': False, 'error': message}), status


# ---------------------------------------------------------------- abuse protection
_dispatch_hits = {}
_dispatch_lock = threading.Lock()


def _dispatch_rate_limited(user_id):
    limit, window = DISPATCH_RATE_LIMIT
    now = time.time()
    with _dispatch_lock:
        hits = [t for t in _dispatch_hits.get(user_id, []) if now - t < window]
        limited = len(hits) >= limit
        if not limited:
            hits.append(now)
        _dispatch_hits[user_id] = hits
        return limited


# ---------------------------------------------------------------- audit trail
def _ensure_dispatch_log_table():
    try:
        conn = sqlite3.connect(DB_PATH)
        try:
            conn.execute('''CREATE TABLE IF NOT EXISTS proposal_dispatch_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                candidate_id INTEGER, sent_by INTEGER, sent_by_name TEXT,
                recipient_email TEXT, subject TEXT, masked INTEGER, blank_projects INTEGER,
                status TEXT, error TEXT, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)''')
            conn.commit()
        finally:
            conn.close()
    except Exception as e:
        print(f"proposal_dispatch_log table not created: {e}")


_ensure_dispatch_log_table()
ensure_schema()      # adds the reporting columns to the existing proposal_dispatch_log table
try:
    _ix = sqlite3.connect(DB_PATH)
    _ix.execute('CREATE INDEX IF NOT EXISTS idx_dispatch_log_sub_date ON proposal_dispatch_log(submission_date)')
    _ix.commit()
    _ix.close()
except Exception as _e:
    print(f'dispatch log index not created: {_e}')


def _dispatch_log(candidate_id, recipient, subject, masked, blank_projects, status, error=''):
    """Record who sent which candidate to whom. Never raises."""
    try:
        conn = sqlite3.connect(DB_PATH)
        try:
            cur = conn.execute(
                '''INSERT INTO proposal_dispatch_log
                   (candidate_id, sent_by, sent_by_name, recipient_email, subject, masked, blank_projects, status, error)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)''',
                (candidate_id, session.get('user_id'), session.get('user_name') or '', recipient,
                 subject, 1 if masked else 0, blank_projects, status, str(error)[:300]))
            conn.commit()
            return cur.lastrowid
        finally:
            conn.close()
    except Exception as e:
        print(f"dispatch log failed: {e}")
        return None


# ---------------------------------------------------------------- tracker table: parse + re-render (never echo input)
class _TrackerTableParser(HTMLParser):
    """Reads UNTRUSTED table HTML into plain rows/cells. No tag, attribute or link from the input survives."""

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.rows = []
        self.saw_table = False
        self._row = None
        self._cell = None
        self._depth = 0
        self._skip = 0

    @staticmethod
    def _span(value):
        try:
            n = int(str(value).strip())
        except (TypeError, ValueError):
            return 1
        return n if 1 <= n <= 10 else 1

    def _close_cell(self):
        if self._cell is not None:
            if self._row is None:
                self._row = []
                self.rows.append(self._row)
            self._row.append(self._cell)
        self._cell = None

    def _newline(self):
        if self._cell is not None and self._cell['text'] and not self._cell['text'].endswith('\n'):
            self._cell['text'] += '\n'

    def handle_starttag(self, tag, attrs):
        if tag in ('script', 'style'):
            self._skip += 1
            return
        if self._skip:
            return
        if tag == 'table':
            self._depth += 1
            self.saw_table = True
            return
        if self._depth != 1:
            return                                   # ignore anything outside / nested deeper than the first table
        if tag == 'tr':
            self._close_cell()
            self._row = []
            self.rows.append(self._row)
        elif tag in ('td', 'th'):
            self._close_cell()
            a = dict(attrs)
            self._cell = {'th': tag == 'th', 'text': '',
                          'colspan': self._span(a.get('colspan')), 'rowspan': self._span(a.get('rowspan'))}
        elif tag in ('br', 'div', 'p'):
            self._newline()

    def handle_startendtag(self, tag, attrs):
        if tag == 'br' and not self._skip and self._depth == 1:
            self._newline()

    def handle_endtag(self, tag):
        if tag in ('script', 'style'):
            self._skip = max(0, self._skip - 1)
            return
        if self._skip:
            return
        if tag == 'table':
            if self._depth == 1:
                self._close_cell()
            self._depth = max(0, self._depth - 1)
        elif self._depth == 1:
            if tag in ('td', 'th'):
                self._close_cell()
            elif tag == 'tr':
                self._close_cell()
                self._row = None
            elif tag in ('div', 'p'):
                self._newline()

    def handle_data(self, data):
        if self._skip or self._depth != 1 or self._cell is None:
            return
        self._cell['text'] += re.sub(r'\s+', ' ', data)


def _dispatch_clean_tracker(raw, mask):
    """Return (safe_html, plain_text) for the tracker table, or raise ValueError."""
    raw = str(raw or '')
    if len(raw) > 200000:
        raise ValueError('The tracker table is too large')
    parser = _TrackerTableParser()
    try:
        parser.feed(raw)
        parser.close()
    except Exception:
        raise ValueError('The tracker table could not be read')
    rows = [r for r in parser.rows if r]
    if not parser.saw_table or not rows:
        raise ValueError('The tracker table is empty')
    if len(rows) > 200 or any(len(r) > 30 for r in rows):
        raise ValueError('The tracker table has too many rows or columns')

    cell_style = 'border:1px solid #9aa5a8;padding:6px 10px;text-align:left;vertical-align:top;'
    out = ['<table cellspacing="0" cellpadding="0" style="border-collapse:collapse;'
           'font-family:Arial,Helvetica,sans-serif;font-size:13px;color:#1f2d30;">']
    plain = []
    for row in rows:
        out.append('<tr>')
        plain_cells = []
        for cell in row:
            text = '\n'.join(line.strip() for line in cell['text'].split('\n')).strip()[:1000]
            if mask:
                text = _dispatch_scrub_contact(text)
            tag = 'th' if cell['th'] else 'td'
            style = cell_style + ('background:#e8eef0;font-weight:bold;' if cell['th'] else '')
            spans = ''.join(f' {k}="{cell[k]}"' for k in ('colspan', 'rowspan') if cell[k] > 1)
            body = '<br>'.join(_html.escape(line) for line in text.split('\n'))
            out.append(f'<{tag}{spans} style="{style}">{body}</{tag}>')
            plain_cells.append(text.replace('\n', ' '))
        out.append('</tr>')
        plain.append(' | '.join(plain_cells))
    out.append('</table>')
    return ''.join(out), '\n'.join(plain)


# ---------------------------------------------------------------- resume content helpers
_DISPATCH_STOP_HEADING = re.compile(
    r'^\s*(?:work\s+(?:experience|history)|professional\s+experience|experience|employment(?:\s+history)?|'
    r'education(?:al)?(?:\s+qualifications?)?|(?:technical\s+|key\s+|core\s+|functional\s+|soft\s+)?skills?|'
    r'projects?|certifications?|achievements?|awards?|personal\s+(?:details|information)|declaration|'
    r'references?|languages?|interests?|hobbies|summary|profile|objective)\s*:?\s*$', re.I)
_DISPATCH_BULLET_GLYPH = re.compile(r'^[\u2022\u25cf\u25aa\u25a0\u2023\u2043\-\*\u00b7\u27a2\u2713]+\s*')


def _dispatch_json_list(value):
    if isinstance(value, list):
        return value
    try:
        parsed = json.loads(value) if value else []
        return parsed if isinstance(parsed, list) else []
    except Exception:
        return []


def _dispatch_resume_section(text, heading_re, max_chars=1800):
    """Lines under a heading (e.g. 'Professional Summary') in the candidate's own resume text."""
    lines = [l.strip() for l in str(text or '').replace('\r', '').split('\n')]
    head = re.compile(r'^\s*(?:%s)\s*:?\s*$' % heading_re, re.I)
    for i, line in enumerate(lines):
        if head.match(line):
            out = []
            for nxt in lines[i + 1:i + 40]:
                if not nxt:
                    continue
                if _DISPATCH_STOP_HEADING.match(nxt) or (nxt.isupper() and len(nxt) < 40 and len(nxt.split()) <= 4):
                    break
                out.append(nxt)
                if sum(len(x) for x in out) > max_chars:
                    break
            if out:
                return out
    return []


def _dispatch_lines_to_bullets(lines, max_bullets=8, max_len=320, per_line=False):
    if per_line:                                                    # each non-empty line is its own bullet
        out = [_DISPATCH_BULLET_GLYPH.sub('', l).strip() for l in lines]
        return [b[:max_len] for b in out if b][:max_bullets]
    bullets, buf = [], ''
    for line in lines:
        starts_new = bool(_DISPATCH_BULLET_GLYPH.match(line))
        line = _DISPATCH_BULLET_GLYPH.sub('', line).strip()
        if not line:
            continue
        if starts_new and buf:
            bullets.append(buf)
            buf = line
        else:
            buf = (buf + ' ' + line).strip()
    if buf:
        bullets.append(buf)
    if len(bullets) == 1 and len(bullets[0]) > max_len:         # one long paragraph -> sentences
        bullets = [s.strip() for s in re.split(r'(?<=[.!?])\s+', bullets[0]) if s.strip()]
    return [b[:max_len] for b in bullets[:max_bullets]]


def _dispatch_candidate_content(cand, projects, mask):
    """Everything that goes into the resume, taken from the candidate's own data only.
    Internal fields (notes, analysis_summary, recommendation) are deliberately never used."""
    scrub = _dispatch_scrub_contact if mask else (lambda t: str(t or ''))
    name = ' '.join(p for p in [cand.get('first_name'), cand.get('middle_name'), cand.get('last_name')] if p).strip()
    role = cand.get('designation') or cand.get('current_role') or ''
    skills = [str(s).strip() for s in _dispatch_json_list(cand.get('core_skills')) if str(s).strip()]
    resume_text = cand.get('resume_text') or ''
    if not skills:
        skills = [s.strip() for s in re.split(r'[,|\u2022;]', ' '.join(_dispatch_resume_section(
            resume_text, r'(?:technical\s+|key\s+)?skills?|core\s+competenc(?:y|ies)'))) if s.strip()][:40]

    summary = _dispatch_lines_to_bullets(_dispatch_resume_section(
        resume_text, r'(?:professional\s+|career\s+|executive\s+)?(?:summary|profile|objective)|about\s+me'))
    if not summary:                                                 # generated from structured fields
        years = str(cand.get('years_of_experience') or '').strip()
        if role or years:
            summary.append(f"{role or 'Professional'}" + (f" with {years} years of total experience" if years else ''))
        if skills:
            summary.append('Hands-on experience with ' + ', '.join(skills[:8]))
        companies = []
        for w in _dispatch_json_list(cand.get('work_experience')):
            c = w.get('company') if isinstance(w, dict) else w
            if c and str(c).strip() and str(c).strip() not in companies:
                companies.append(str(c).strip())
        if companies:
            summary.append('Has worked with ' + ', '.join(companies[:4]))
        certs = [str(c).strip() for c in _dispatch_json_list(cand.get('certifications')) if str(c).strip()]
        if certs:
            summary.append('Certifications: ' + ', '.join(certs[:5]))

    functional = _dispatch_lines_to_bullets(_dispatch_resume_section(
        resume_text, r'(?:functional|soft|domain)\s+(?:skills?|expertise|knowledge)|functional\s+expertise'), max_bullets=12)

    proj_out = []
    for p in projects[:DISPATCH_MAX_PROJECTS]:
        pname = str(p.get('project_name') or '').strip()
        if p.get('organization'):
            pname = f"{pname} ({str(p['organization']).strip()})" if pname else str(p['organization']).strip()
        resp = [l for l in re.split(r'\r?\n', str(p.get('description') or '')) if l.strip()]
        resp = _dispatch_lines_to_bullets(resp, max_bullets=15, max_len=400, per_line=True)
        if p.get('role'):
            resp.insert(0, 'Role: ' + str(p['role']).strip())
        proj_out.append({'name': scrub(pname), 'env': scrub(p.get('tech_stack') or ''), 'resp': [scrub(r) for r in resp]})

    return {
        'name': scrub(name), 'role': scrub(role),
        'phone': '' if mask else str(cand.get('phone') or ''),
        'email': '' if mask else str(cand.get('email') or ''),
        'summary': [scrub(s) for s in summary], 'skills': [scrub(s) for s in skills],
        'functional': [scrub(s) for s in functional], 'projects': proj_out,
    }


# ---------------------------------------------------------------- .docx builder
def _dx_shade(cell, fill):
    tcPr = cell._tc.get_or_add_tcPr()
    shd = _OxmlElement('w:shd')
    shd.set(_qn('w:val'), 'clear')
    shd.set(_qn('w:color'), 'auto')
    shd.set(_qn('w:fill'), fill)
    tcPr.insert_element_before(shd, 'w:noWrap', 'w:tcMar', 'w:textDirection', 'w:tcFitText', 'w:vAlign', 'w:hideMark')


def _dx_heading(doc, text):
    p = doc.add_paragraph()
    p.paragraph_format.space_before = _Pt(12)
    p.paragraph_format.space_after = _Pt(4)
    p.paragraph_format.keep_with_next = True
    run = p.add_run(text)
    run.bold = True
    run.font.size = _Pt(13)
    run.font.color.rgb = _RGB(0x1F, 0x3A, 0x3F)
    pPr = p._p.get_or_add_pPr()
    borders = _OxmlElement('w:pBdr')
    bottom = _OxmlElement('w:bottom')
    for k, v in (('val', 'single'), ('sz', '8'), ('space', '1'), ('color', '1F3A3F')):
        bottom.set(_qn('w:' + k), v)
    borders.append(bottom)
    pPr.insert_element_before(borders, 'w:shd', 'w:tabs', 'w:suppressAutoHyphens', 'w:spacing', 'w:ind',
                              'w:contextualSpacing', 'w:jc', 'w:outlineLvl', 'w:rPr', 'w:sectPr', 'w:pPrChange')
    return p


def _dx_cell(cell, text='', bold=False, size=10, color=None, align=None, italic=False):
    cell.text = ''
    p = cell.paragraphs[0]
    p.paragraph_format.space_after = _Pt(2)
    if align is not None:
        p.alignment = align
    run = p.add_run(str(text))
    run.bold = bold
    run.italic = italic
    run.font.size = _Pt(size)
    if color:
        run.font.color.rgb = _RGB(*color)
    return p


def _dx_widths(table, widths):
    table.autofit = False
    for row in table.rows:
        for idx, w in enumerate(widths):
            row.cells[idx].width = w
    for idx, w in enumerate(widths):
        table.columns[idx].width = w


def _dx_bullets_in_cell(cell, lines):
    cell.text = ''
    first = True
    for line in lines:
        p = cell.paragraphs[0] if first else cell.add_paragraph()
        p.style = cell.part.document.styles['List Bullet']
        p.paragraph_format.space_after = _Pt(1)
        run = p.add_run(line)
        run.font.size = _Pt(10)
        first = False


def _dx_project_table(doc, name='', env='', resp_lines=None, blank=False):
    table = doc.add_table(rows=3, cols=2)
    table.style = 'Table Grid'
    _dx_widths(table, [_Cm(3.6), _Cm(13.8)])
    for i, label in enumerate(('Project Name', 'Environment', 'Responsibilities')):
        _dx_cell(table.cell(i, 0), label, bold=True)
        _dx_shade(table.cell(i, 0), 'EAF0F1')
    _dx_cell(table.cell(0, 1), name)
    _dx_cell(table.cell(1, 1), env)
    if resp_lines:
        _dx_bullets_in_cell(table.cell(2, 1), resp_lines)
    else:
        _dx_cell(table.cell(2, 1), '')
    if blank:                                                       # roomy boxes to fill in later in Word
        table.rows[2].height = _Cm(3.2)
        table.rows[2].height_rule = _ROWRULE.AT_LEAST
    for row in table.rows[:-1]:                                     # keep the whole project table on one page
        for cell in row.cells:
            for para in cell.paragraphs:
                para.paragraph_format.keep_with_next = True
    for row in table.rows:                                          # keep each row on one page
        trPr = row._tr.get_or_add_trPr()
        trPr.insert_element_before(_OxmlElement('w:cantSplit'), 'w:trHeight', 'w:tblHeader', 'w:tblCellSpacing',
                                   'w:jc', 'w:hidden', 'w:ins', 'w:del', 'w:trPrChange')
    spacer = doc.add_paragraph()                                    # required: Word merges tables with no paragraph between
    spacer.paragraph_format.space_before = _Pt(0)
    spacer.paragraph_format.space_after = _Pt(0)
    spacer.paragraph_format.line_spacing = _Pt(8)
    return table


def _dispatch_build_docx(cand, projects, mask, blank_projects):
    """Build the resume .docx and return its bytes."""
    c = _dispatch_candidate_content(cand, projects, mask)
    doc = _docx.Document()
    sec = doc.sections[0]
    sec.page_width, sec.page_height = _Cm(21.0), _Cm(29.7)
    sec.left_margin = sec.right_margin = _Cm(1.8)
    sec.top_margin, sec.bottom_margin = _Cm(1.6), _Cm(1.8)
    normal = doc.styles['Normal']
    normal.font.name = 'Calibri'
    normal.font.size = _Pt(10.5)
    normal.element.rPr.rFonts.set(_qn('w:eastAsia'), 'Calibri')

    # ---- Profile: photo placeholder + Name / Role / Phone / Email ----
    _dx_heading(doc, 'Profile')
    prof = doc.add_table(rows=4, cols=3)
    prof.style = 'Table Grid'
    _dx_widths(prof, [_Cm(3.6), _Cm(3.4), _Cm(10.4)])
    for r, (label, value) in enumerate((('Name', c['name']), ('Role', c['role']),
                                        ('Phone', c['phone']), ('Email', c['email']))):
        prof.rows[r].height = _Cm(1.0)
        prof.rows[r].height_rule = _ROWRULE.AT_LEAST
        _dx_cell(prof.cell(r, 1), label, bold=True)
        _dx_shade(prof.cell(r, 1), 'EAF0F1')
        _dx_cell(prof.cell(r, 2), value)                            # blank when contact details are masked
        prof.cell(r, 2).vertical_alignment = _VALIGN.CENTER
        prof.cell(r, 1).vertical_alignment = _VALIGN.CENTER
    photo = prof.cell(0, 0).merge(prof.cell(3, 0))
    _dx_cell(photo, 'PHOTO', bold=True, size=11, color=(0x8A, 0x99, 0x9C), align=_ALIGN.CENTER)
    hint = photo.add_paragraph()
    hint.alignment = _ALIGN.CENTER
    hr = hint.add_run('(paste photo here)')
    hr.font.size = _Pt(8)
    hr.font.color.rgb = _RGB(0x8A, 0x99, 0x9C)
    photo.vertical_alignment = _VALIGN.CENTER
    _dx_shade(photo, 'F4F6F6')

    # ---- Profile Summary ----
    _dx_heading(doc, 'Profile Summary')
    for line in (c['summary'] or ['']):
        doc.add_paragraph(line, style='List Bullet').paragraph_format.space_after = _Pt(2)

    # ---- Technical Skills / Functional Skills ----
    _dx_heading(doc, 'Technical Skills')
    if c['skills']:
        doc.add_paragraph(', '.join(c['skills']))
    else:
        doc.add_paragraph('', style='List Bullet')
    _dx_heading(doc, 'Functional Skills')
    for line in (c['functional'] or ['']):
        doc.add_paragraph(line, style='List Bullet').paragraph_format.space_after = _Pt(2)

    # ---- Projects: one bordered table per project, then any blank ones ----
    _dx_heading(doc, 'Projects')
    for p in c['projects']:
        _dx_project_table(doc, p['name'], p['env'], p['resp'])
    for _ in range(blank_projects):
        _dx_project_table(doc, blank=True)

    # ---- Footer ----
    footer = sec.footer
    footer.is_linked_to_previous = False
    fp = footer.paragraphs[0]
    fp.alignment = _ALIGN.CENTER
    fr = fp.add_run(DISPATCH_FOOTER_TEXT)
    fr.italic = True
    fr.font.size = _Pt(8.5)
    fr.font.color.rgb = _RGB(0x6B, 0x7C, 0x80)

    props = doc.core_properties
    props.author = 'ShahnaIT'
    props.last_modified_by = 'ShahnaIT'
    props.title = f"Profile - {c['name']}".strip(' -')
    props.comments = ''
    props.created = props.modified = datetime.now()

    buf = io.BytesIO()
    doc.save(buf)
    return buf.getvalue()


# ---------------------------------------------------------------- e-mail
def _dispatch_compose_email(sender, recipient, subject, table_html, table_plain, docx_bytes, filename, sender_name, reply_to):
    msg = EmailMessage()
    msg['From'] = formataddr(('ShahnaIT', sender))
    msg['To'] = recipient
    msg['Subject'] = subject
    if reply_to:
        msg['Reply-To'] = reply_to
    msg.set_content('Hello,\n\nPlease find the candidate profile details below. The detailed resume is attached.\n\n'
                    + table_plain + '\n\nRegards,\n' + (sender_name or 'ShahnaIT') + '\n\n' + DISPATCH_FOOTER_TEXT + '\n')
    msg.add_alternative(
        '<div style="font-family:Arial,Helvetica,sans-serif;font-size:14px;color:#1f2d30;">'
        '<p>Hello,</p><p>Please find the candidate profile details below. The detailed resume is attached.</p>'
        + table_html +
        '<p style="margin-top:18px;">Regards,<br>' + _html.escape(sender_name or 'ShahnaIT') + '<br>ShahnaIT</p>'
        '<p style="font-size:11px;color:#6b7c80;border-top:1px solid #d9cfb8;padding-top:8px;">'
        + _html.escape(DISPATCH_FOOTER_TEXT) + '</p></div>', subtype='html')
    msg.add_attachment(docx_bytes, maintype='application',
                       subtype='vnd.openxmlformats-officedocument.wordprocessingml.document', filename=filename)
    return msg


def _dispatch_send_email(msg, smtp_email=None, smtp_password=None):
    """Sends via the Resend HTTPS API (Railway blocks SMTP). Needs RESEND_API_KEY and RESEND_FROM_EMAIL."""
    import base64
    import resend
    resend.api_key = os.environ['RESEND_API_KEY']
    html_part, text_part = msg.get_body(('html',)), msg.get_body(('plain',))
    params = {
        'from': msg['From'],
        'to': [a.strip() for a in msg['To'].split(',') if a.strip()],
        'subject': msg['Subject'],
        'html': html_part.get_content() if html_part else None,
        'text': text_part.get_content() if text_part else None,
        'attachments': [{'filename': p.get_filename(), 'content': base64.b64encode(p.get_payload(decode=True)).decode()}
                        for p in msg.iter_attachments()],
    }
    if msg['Reply-To']:
        params['reply_to'] = msg['Reply-To']
    resend.Emails.send({k: v for k, v in params.items() if v})
    return {}                              # {} or {address: error} for refused recipients

DISPATCH_MAX_RECIPIENTS = 10

def _dispatch_parse_recipients(raw):
    """'a@x.com, b@y.com' -> (['a@x.com', 'b@y.com'], None) or ([], 'error message'). Commas or semicolons; duplicates dropped."""
    if isinstance(raw, (list, tuple)):
        raw = ','.join(str(x) for x in raw)
    raw = str(raw or '')
    if len(raw) > 2000:
        return [], 'The recipient list is too long'
    found, seen = [], set()
    for part in re.split(r'[,;]', raw):
        addr = part.strip()
        if not addr:
            continue
        if len(addr) > 254 or not _DISPATCH_EMAIL_RE.match(addr):
            return [], f'"{addr[:60]}" is not a valid email address'
        if addr.lower() not in seen:
            seen.add(addr.lower())
            found.append(addr)
    if not found:
        return [], 'Please enter at least one recipient email address'
    if len(found) > DISPATCH_MAX_RECIPIENTS:
        return [], f'You can send to at most {DISPATCH_MAX_RECIPIENTS} recipients at a time'
    return found, None


# ---------------------------------------------------------------- the route
# ---------------------------------------------------------------- the route
@app.route('/api/dispatch-proposal', methods=['POST'])
@login_required()
def dispatch_proposal():
    data = request.get_json(silent=True)
    if not isinstance(data, dict):
        return _dispatch_error('Invalid request', 400)

    # ---- validate input ----
    try:
        candidate_id = int(data.get('candidate_id'))
    except (TypeError, ValueError):
        return _dispatch_error('A valid candidate_id is required', 400)
        
    recipients, rec_error = _dispatch_parse_recipients(data.get('recipient_email'))
    
    if rec_error:
        return _dispatch_error(rec_error, 400)
    recipient = ', '.join(recipients)
    reply_to_raw = str(data.get('reply_to_email') or '').strip()
    if reply_to_raw and (len(reply_to_raw) > 254 or not _DISPATCH_EMAIL_RE.match(reply_to_raw)):
        return _dispatch_error('The Reply-To address is not a valid email address', 400)
    mask = data.get('mask_contact_details') in (True, 'true', 'True', 1, '1', 'on')
    try:
        blank_projects = int(data.get('add_blank_projects') or 0)
    except (TypeError, ValueError):
        blank_projects = -1
    if not 0 <= blank_projects <= DISPATCH_MAX_BLANK_PROJECTS:
        return _dispatch_error(f'Blank project boxes must be between 0 and {DISPATCH_MAX_BLANK_PROJECTS}', 400)
    subject = ' '.join(str(data.get('email_subject') or '').split())[:200]   # collapses CR/LF: no header injection
    try:
        table_html, table_plain = _dispatch_clean_tracker(data.get('table_html'), mask)
    except ValueError as e:
        return _dispatch_error(str(e), 400)

    smtp_email = (os.environ.get('RESEND_FROM_EMAIL') or '').strip()
    smtp_password = (os.environ.get('RESEND_API_KEY') or '').strip()
    if not smtp_email or not smtp_password:
        return _dispatch_error('Email is not configured on the server (RESEND_API_KEY / RESEND_FROM_EMAIL).', 503)
    if _dispatch_rate_limited(session.get('user_id')):
        return _dispatch_error('Too many proposals sent in a short time. Please wait a few minutes.', 429)

    # ---- load candidate (+ same ownership rule as editing) ----
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        row = conn.execute('SELECT * FROM candidates WHERE id = ?', (candidate_id,)).fetchone()
        if not row:
            return _dispatch_error('Candidate not found', 404)
        cand = dict(row)
        projects = [dict(r) for r in conn.execute(
            'SELECT * FROM candidate_projects WHERE candidate_id = ? ORDER BY id LIMIT ?',
            (candidate_id, DISPATCH_MAX_PROJECTS))]
    finally:
        conn.close()
    if session.get('role') != 'admin':
        user_name = session.get('user_name') or ''
        if not user_name or ((cand.get('uploaded_by_name') or '') != user_name and (cand.get('uploaded_by') or '') != user_name):
            return _dispatch_error('You can only dispatch your own candidates', 403)

    full_name = ' '.join(p for p in [cand.get('first_name'), cand.get('last_name')] if p).strip() or 'Candidate'
    if not subject:
        subject = f'Profile Proposal - {full_name}'[:200]

    try:
        docx_bytes = _dispatch_build_docx(cand, projects, mask, blank_projects)
    except Exception:
        app.logger.exception('proposal resume generation failed')
        _dispatch_log(candidate_id, recipient, subject, mask, blank_projects, 'failed', 'resume generation')
        return _dispatch_error('Could not generate the resume document', 500)

    filename = (secure_filename(f'{full_name}_Profile') or 'Profile') + '.docx'
    current = get_current_user() or {}
    msg = _dispatch_compose_email(smtp_email, recipient, subject, table_html, table_plain, docx_bytes, filename,
                                  session.get('user_name') or current.get('full_name') or '',
                                  reply_to_raw or (current.get('email') if _DISPATCH_EMAIL_RE.match(str(current.get('email') or '')) else ''))
    try:
        refused = _dispatch_send_email(msg, smtp_email, smtp_password) or {}
    except Exception as e:
        app.logger.exception('proposal dispatch: send failed')
        _dispatch_log(candidate_id, recipient, subject, mask, blank_projects, 'failed', type(e).__name__)
        return _dispatch_error('Could not send the email. Please try again.', 502)

    bad = ', '.join(sorted(refused)) if refused else ''
    log_id = _dispatch_log(candidate_id, recipient, subject, mask, blank_projects,
                           'partial' if refused else 'sent', f'refused: {bad}' if refused else '')
    _dispatch_record_tracker(log_id, candidate_id, _dispatch_tracker_rows(data.get('table_html')))   # feeds the Reports page
    if refused:
        return jsonify({'success': True, 'dispatch_id': log_id,
                        'message': f'Sent, but the mail server refused: {bad}'})
    count = len(recipients)
    return jsonify({'success': True, 'message': f'Proposal sent to {recipient}' if count <= 3 else f'Proposal sent to {count} recipients',
                    'dispatch_id': log_id})
# ============ MASTER REPORTING ENGINE: proposals -> JSON / Excel / PDF ============
# Paste this whole block into app.py directly AFTER the dispatch_proposal() route (before "@app.route('/api/candidates/<int:candidate_id>/projects'").
import io
import calendar
from datetime import date as _date, datetime as _datetime, timedelta as _timedelta, timezone as _timezone
from xml.sax.saxutils import escape as _xml_escape

IST = _timezone(_timedelta(hours=5, minutes=30))
REPORT_MAX_ROWS = 5000

REPORT_COLUMNS = [
    'Date of Submission', 'Candidate Name', 'Total Exp', 'Relevant Exp', 'Mobile No', 'Email ID',
    'Requirement (SIT-R-)', 'Client Name', 'HR who proposed', 'CCTC', 'ECTC', 'Location',
    'Onsite/Hybrid/Remote', 'Freelancing (Yes/No)', 'C2C/C2H/FTE', 'Last Working Day', 'Notice Period', 'Remarks',
]

# tracker header text (any spelling the user types) -> canonical column
_REPORT_ALIASES = {
    'dateofsubmission': 'Date of Submission', 'date': 'Date of Submission', 'submissiondate': 'Date of Submission',
    'candidatename': 'Candidate Name', 'name': 'Candidate Name',
    'totalexp': 'Total Exp', 'totalexperience': 'Total Exp', 'totalexpyrs': 'Total Exp',
    'relevantexp': 'Relevant Exp', 'relexp': 'Relevant Exp', 'relevantexperience': 'Relevant Exp',
    'mobileno': 'Mobile No', 'mobile': 'Mobile No', 'phone': 'Mobile No', 'contactno': 'Mobile No',
    'emailid': 'Email ID', 'email': 'Email ID',
    'requirementsitr': 'Requirement (SIT-R-)', 'requirement': 'Requirement (SIT-R-)', 'requirementid': 'Requirement (SIT-R-)',
    'clientname': 'Client Name', 'client': 'Client Name',
    'hrwhoproposed': 'HR who proposed', 'hr': 'HR who proposed', 'hrname': 'HR who proposed',
    'cctc': 'CCTC', 'currentctc': 'CCTC', 'ectc': 'ECTC', 'expectedctc': 'ECTC',
    'location': 'Location',
    'onsitehybridremote': 'Onsite/Hybrid/Remote', 'workmode': 'Onsite/Hybrid/Remote',
    'freelancingyesno': 'Freelancing (Yes/No)', 'freelancing': 'Freelancing (Yes/No)',
    'c2cc2hfte': 'C2C/C2H/FTE', 'engagementtype': 'C2C/C2H/FTE',
    'lastworkingday': 'Last Working Day', 'lwd': 'Last Working Day',
    'noticeperiod': 'Notice Period', 'notice': 'Notice Period',
    'remarks': 'Remarks', 'note': 'Remarks', 'notes': 'Remarks',
}


def _report_key(text):
    return re.sub(r'[^a-z0-9]', '', str(text or '').lower())


def _parse_any_date(text):
    """'01-Nov-2026', '2026-11-01', '01/11/2026', '1 Nov 2026' -> date, or None."""
    s = str(text or '').strip()
    for fmt in ('%d-%b-%Y', '%Y-%m-%d', '%d/%m/%Y', '%d-%m-%Y', '%d %b %Y', '%d %B %Y', '%d-%B-%Y', '%d.%m.%Y'):
        try:
            return _datetime.strptime(s, fmt).date()
        except ValueError:
            continue
    return None


def _dispatch_tracker_rows(raw):
    """Untrusted tracker HTML -> list of {canonical column: text} (first table; first row = headers).
    Columns the user renamed to something unknown are ignored, so the report always has the same 18 columns."""
    parser = _TrackerTableParser()
    try:
        parser.feed(str(raw or '')[:200000])
        parser.close()
    except Exception:
        return []
    rows = [r for r in parser.rows if r]
    if len(rows) < 2:
        return []
    heads = [_REPORT_ALIASES.get(_report_key(c['text'])) for c in rows[0]]
    out = []
    for r in rows[1:51]:
        rec = {}
        for h, cell in zip(heads, r):
            text = '\n'.join(x.strip() for x in cell['text'].split('\n')).strip()[:1000]
            if h and text and h not in rec:
                rec[h] = text
        if rec:
            out.append(rec)
    return out


def _dispatch_record_tracker(log_id, candidate_id, rows):
    """Store the proposal row(s) with the log entry, and remember the new candidate fields for next time. Never raises."""
    if not log_id or not rows:
        return
    try:
        sub = _parse_any_date(rows[0].get('Date of Submission')) or _datetime.now(IST).date()
        conn = sqlite3.connect(DB_PATH)
        try:
            conn.execute('UPDATE proposal_dispatch_log SET tracker_json = ?, submission_date = ? WHERE id = ?',
                         (json.dumps(rows, ensure_ascii=False), sub.isoformat(), log_id))
            remember = {'relevant_exp': 'Relevant Exp', 'work_mode': 'Onsite/Hybrid/Remote', 'freelancing': 'Freelancing (Yes/No)',
                        'engagement_type': 'C2C/C2H/FTE', 'last_working_day': 'Last Working Day'}
            for col, head in remember.items():
                if rows[0].get(head):
                    conn.execute(f'UPDATE candidates SET {col} = ? WHERE id = ?', (rows[0][head][:200], candidate_id))
            conn.commit()
        finally:
            conn.close()
    except Exception as e:
        print(f'dispatch tracker snapshot failed: {e}')


# ---------------------------------------------------------------- query
def _report_range(args):
    """range=day|week|month (+ date=YYYY-MM-DD anchor) or range=custom (+ start, end). Returns (start, end, label)."""
    today = _datetime.now(IST).date()
    kind = (args.get('range') or 'day').strip().lower()
    anchor = _parse_any_date(args.get('date')) or today
    if kind == 'custom':
        start = _parse_any_date(args.get('start')) or anchor
        end = _parse_any_date(args.get('end')) or start
        if end < start:
            start, end = end, start
        if (end - start).days > 366:
            raise ValueError('Custom range cannot be longer than one year')
    elif kind == 'week':
        start = anchor - _timedelta(days=anchor.weekday())
        end = start + _timedelta(days=6)
    elif kind == 'month':
        start = anchor.replace(day=1)
        end = anchor.replace(day=calendar.monthrange(anchor.year, anchor.month)[1])
    elif kind == 'day':
        start = end = anchor
    else:
        raise ValueError('range must be day, week, month or custom')
    label = start.strftime('%d %b %Y') if start == end else f"{start.strftime('%d %b %Y')} to {end.strftime('%d %b %Y')}"
    return start, end, label


def _ordinal_day(d):
    n = d.day
    suffix = 'th' if 10 <= n % 100 <= 20 else {1: 'st', 2: 'nd', 3: 'rd'}.get(n % 10, 'th')
    return f'{n:02d}{suffix}'


def _report_day_label(d):
    return f"{_ordinal_day(d)} {d.strftime('%b %Y')} ({d.strftime('%A')})"


def _fallback_row(r):
    """Row built from the candidate record - used for older log entries and for tracker cells left empty."""
    def years(v):
        s = str(v or '').strip()
        return s + ' yrs' if re.fullmatch(r'\d+(\.\d+)?', s) else s
    rel = ', '.join(f"{e['skill']} - {e['years']} yrs" if e.get('years') else e['skill']
                    for e in _dispatch_json_list(r['relevant_experience']) if isinstance(e, dict) and e.get('skill'))
    try:
        notice = f"{int(r['notice_period_days'])} days" if int(r['notice_period_days'] or 0) > 0 else ''
    except (TypeError, ValueError):
        notice = ''
    return {
        'Candidate Name': ' '.join(p for p in [r['first_name'], r['last_name']] if p).strip(),
        'Total Exp': years(r['years_of_experience']),
        'Relevant Exp': (r['relevant_exp'] or rel or ''),
        'Mobile No': r['phone'] or '', 'Email ID': r['email'] or '',
        'Requirement (SIT-R-)': r['proposed_requirement'] or '', 'Client Name': r['proposed_client'] or '',
        'HR who proposed': r['sent_by_name'] or '',
        'CCTC': r['current_ctc'] or '', 'ECTC': r['expected_ctc'] or '', 'Location': r['location'] or '',
        'Onsite/Hybrid/Remote': r['work_mode'] or '', 'Freelancing (Yes/No)': r['freelancing'] or '',
        'C2C/C2H/FTE': r['engagement_type'] or '', 'Last Working Day': r['last_working_day'] or '',
        'Notice Period': notice, 'Remarks': '',
    }


def _report_query(args, user_id, see_all):
    start, end, label = _report_range(args)
    hr_f = (args.get('hr') or '').strip().lower()
    client_f = (args.get('client') or '').strip().lower()
    skills = [s.strip().lower() for s in re.split(r'[,;]', args.get('skill') or '') if s.strip()]
    sql = '''SELECT l.id AS log_id, l.sent_by, l.sent_by_name, l.created_at, l.tracker_json,
                    COALESCE(l.submission_date, date(l.created_at, '+330 minutes')) AS sub_date,
                    c.first_name, c.last_name, c.phone, c.email, c.current_ctc, c.expected_ctc, c.location,
                    c.years_of_experience, c.relevant_experience, c.relevant_exp, c.notice_period_days,
                    c.proposed_client, c.proposed_requirement, c.work_mode, c.freelancing, c.engagement_type,
                    c.last_working_day, c.core_skills, c.designation
             FROM proposal_dispatch_log l LEFT JOIN candidates c ON c.id = l.candidate_id
             WHERE l.status IN ('sent', 'partial')
               AND COALESCE(l.submission_date, date(l.created_at, '+330 minutes')) BETWEEN ? AND ?'''
    params = [start.isoformat(), end.isoformat()]
    if not see_all:
        sql += ' AND l.sent_by = ?'
        params.append(user_id)
    sql += ' ORDER BY sub_date, l.id'
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        found = conn.execute(sql, params).fetchall()
    finally:
        conn.close()

    rows = []
    for r in found:
        d = _parse_any_date(r['sub_date']) or start
        base = _fallback_row(r)
        try:
            tracked = json.loads(r['tracker_json']) if r['tracker_json'] else []
        except Exception:
            tracked = []
        for rec in (tracked if isinstance(tracked, list) and tracked else [{}]):
            row = {col: (str(rec.get(col) or '').strip() or str(base.get(col) or '')) for col in REPORT_COLUMNS}
            row['Date of Submission'] = d.strftime('%d-%b-%Y')
            hay = ' '.join(str(x or '') for x in (r['core_skills'], r['relevant_experience'], r['designation'], row['Relevant Exp'])).lower()
            if hr_f and hr_f != row['HR who proposed'].lower():
                continue
            if client_f and client_f not in row['Client Name'].lower():
                continue
            if skills and not any(s in hay for s in skills):
                continue
            row['_date'] = d.isoformat()
            rows.append(row)
            if len(rows) >= REPORT_MAX_ROWS:
                return start, end, label, rows
    return start, end, label, rows


# ---------------------------------------------------------------- Excel (pandas + openpyxl), grouped by date
def _report_xlsx(rows, label):
    import pandas as pd
    from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
    from openpyxl.utils import get_column_letter

    buf = io.BytesIO()
    df = pd.DataFrame(rows, columns=REPORT_COLUMNS + ['_date']) if rows else pd.DataFrame(columns=REPORT_COLUMNS + ['_date'])
    n_cols = len(REPORT_COLUMNS)
    with pd.ExcelWriter(buf, engine='openpyxl') as xw:
        df[REPORT_COLUMNS].head(0).to_excel(xw, sheet_name='Proposals', index=False)        # header row
        ws = xw.sheets['Proposals']
        thin = Side(style='thin', color='B8C2CC')
        box = Border(left=thin, right=thin, top=thin, bottom=thin)
        for col in range(1, n_cols + 1):
            c = ws.cell(row=1, column=col)
            c.font = Font(bold=True, color='FFFFFF')
            c.fill = PatternFill('solid', fgColor='1B2A4A')
            c.alignment = Alignment(horizontal='center', vertical='center', wrap_text=True)
            c.border = box
        ws.row_dimensions[1].height = 30
        r = 2
        for d, grp in df.groupby('_date', sort=True):
            ws.cell(row=r, column=1, value=f"{_report_day_label(_date.fromisoformat(d))}  -  {len(grp)} proposal{'s' if len(grp) != 1 else ''}")
            ws.merge_cells(start_row=r, start_column=1, end_row=r, end_column=n_cols)
            band = ws.cell(row=r, column=1)
            band.font = Font(bold=True, color='1B2A4A')
            band.fill = PatternFill('solid', fgColor='E3EAF2')
            band.alignment = Alignment(vertical='center')
            ws.row_dimensions[r].height = 22
            r += 1
            grp[REPORT_COLUMNS].to_excel(xw, sheet_name='Proposals', index=False, header=False, startrow=r - 1)
            for rr in range(r, r + len(grp)):
                for col in range(1, n_cols + 1):
                    c = ws.cell(row=rr, column=col)
                    c.alignment = Alignment(vertical='top', wrap_text=True)
                    c.border = box
            r += len(grp)
        ws.cell(row=r + 1, column=1, value='Proprietary & Confidential - An asset of ShahnaIT').font = Font(italic=True, color='6B7C80', size=9)
        widths = [14, 22, 10, 22, 17, 26, 18, 20, 18, 10, 10, 16, 16, 14, 14, 14, 12, 30]
        for i, w in enumerate(widths, 1):
            ws.column_dimensions[get_column_letter(i)].width = w
        ws.freeze_panes = 'A2'
        ws.page_setup.orientation = 'landscape'          # prints on one page width
        ws.page_setup.fitToWidth = 1
        ws.page_setup.fitToHeight = 0
        ws.sheet_properties.pageSetUpPr.fitToPage = True
        ws.sheet_view.zoomScale = 90
        for row in ws.iter_rows():                                  # text that starts with "=" must never become a formula
            for c in row:
                if isinstance(c.value, str) and c.value.startswith('='):
                    c.data_type = 's'

        summary = pd.DataFrame({'Report': ['Period', 'Total proposals', 'Generated (IST)'],
                                'Value': [label, len(df), _datetime.now(IST).strftime('%d-%b-%Y %H:%M')]})
        summary.to_excel(xw, sheet_name='Summary', index=False)
        if len(df):
            by_date = df.groupby('_date').size().reset_index(name='Proposals').rename(columns={'_date': 'Date'})
            by_hr = df.groupby('HR who proposed').size().reset_index(name='Proposals').sort_values('Proposals', ascending=False)
            by_client = df.groupby('Client Name').size().reset_index(name='Proposals').sort_values('Proposals', ascending=False)
            by_date.to_excel(xw, sheet_name='Summary', index=False, startrow=6)
            by_hr.to_excel(xw, sheet_name='Summary', index=False, startrow=6, startcol=3)
            by_client.to_excel(xw, sheet_name='Summary', index=False, startrow=6, startcol=6)
        sw = xw.sheets['Summary']
        for i, w in enumerate([22, 26, 3, 24, 12, 3, 26, 12], 1):
            sw.column_dimensions[get_column_letter(i)].width = w
        for row in sw.iter_rows():
            for c in row:
                if isinstance(c.value, str) and c.value.startswith('='):
                    c.data_type = 's'
    buf.seek(0)
    return buf


# ---------------------------------------------------------------- PDF (reportlab), grouped by date
def _report_pdf(rows, label):
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import A3, landscape
    from reportlab.lib.styles import ParagraphStyle
    from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

    buf = io.BytesIO()
    footer = 'Proprietary & Confidential - An asset of ShahnaIT'

    def on_page(canvas, doc):
        canvas.saveState()
        canvas.setFont('Helvetica', 8)
        canvas.setFillColor(colors.HexColor('#6B7C80'))
        canvas.drawString(doc.leftMargin, 14, footer)
        canvas.drawRightString(doc.pagesize[0] - doc.rightMargin, 14, f'Page {doc.page}')
        canvas.restoreState()

    doc = SimpleDocTemplate(buf, pagesize=landscape(A3), leftMargin=20, rightMargin=20, topMargin=24, bottomMargin=30,
                            title='Proposal Report', author='ShahnaIT')
    navy = colors.HexColor('#1B2A4A')
    title = ParagraphStyle('t', fontName='Helvetica-Bold', fontSize=16, textColor=navy, leading=20)
    sub = ParagraphStyle('s', fontName='Helvetica', fontSize=9, textColor=colors.HexColor('#44546A'), leading=12)
    head = ParagraphStyle('h', fontName='Helvetica-Bold', fontSize=7, textColor=colors.white, leading=9, alignment=1)
    cell = ParagraphStyle('c', fontName='Helvetica', fontSize=6.8, leading=8.4)
    band = ParagraphStyle('b', fontName='Helvetica-Bold', fontSize=8.5, textColor=navy, leading=11)

    def p(text, style):
        return Paragraph(_xml_escape(str(text or '')).replace('\n', '<br/>'), style)

    n = len(REPORT_COLUMNS)
    weights = [1.0, 1.4, 0.7, 1.4, 1.1, 1.8, 1.2, 1.2, 1.2, 0.7, 0.7, 1.0, 1.2, 0.9, 1.0, 1.0, 0.8, 1.7]
    usable = landscape(A3)[0] - 40
    widths = [usable * w / sum(weights) for w in weights]

    data = [[p(c, head) for c in REPORT_COLUMNS]]
    style = [('BACKGROUND', (0, 0), (-1, 0), navy), ('VALIGN', (0, 0), (-1, -1), 'TOP'),
             ('GRID', (0, 0), (-1, -1), 0.4, colors.HexColor('#B8C2CC')),
             ('LEFTPADDING', (0, 0), (-1, -1), 3), ('RIGHTPADDING', (0, 0), (-1, -1), 3),
             ('TOPPADDING', (0, 0), (-1, -1), 3), ('BOTTOMPADDING', (0, 0), (-1, -1), 3)]
    last = None
    for row in rows:
        if row['_date'] != last:
            last = row['_date']
            count = sum(1 for x in rows if x['_date'] == last)
            data.append([p(f"{_report_day_label(_date.fromisoformat(last))}  -  {count} proposal{'s' if count != 1 else ''}", band)] + [''] * (n - 1))
            i = len(data) - 1
            style += [('SPAN', (0, i), (-1, i)), ('BACKGROUND', (0, i), (-1, i), colors.HexColor('#E3EAF2'))]
        data.append([p(row[c], cell) for c in REPORT_COLUMNS])
    if not rows:
        data.append([p('No proposals found for the selected filters.', cell)] + [''] * (n - 1))
        style.append(('SPAN', (0, 1), (-1, 1)))
    table = Table(data, colWidths=widths, repeatRows=1)
    table.setStyle(TableStyle(style))
    doc.build([Paragraph('Proposal Report', title),
               Paragraph(_xml_escape(f"{label}  |  {len(rows)} proposal{'s' if len(rows) != 1 else ''}  |  generated {_datetime.now(IST).strftime('%d-%b-%Y %H:%M')} IST"), sub),
               Spacer(1, 10), table], onFirstPage=on_page, onLaterPages=on_page)
    buf.seek(0)
    return buf


# ---------------------------------------------------------------- routes
@app.route('/api/reports/proposals', methods=['GET'])
@login_required()
def reports_proposals():
    """?range=day|week|month|custom &date=YYYY-MM-DD &start= &end= &hr= &skill= &client= &format=json|xlsx|pdf"""
    fmt = (request.args.get('format') or 'json').strip().lower()
    if fmt not in ('json', 'xlsx', 'pdf'):
        return jsonify({'error': 'format must be json, xlsx or pdf'}), 400
    see_all = (session.get('role') or '').lower() in ('admin', 'manager')       # recruiters only ever see their own proposals
    try:
        start, end, label, rows = _report_query(request.args, session.get('user_id'), see_all)
    except ValueError as e:
        return jsonify({'error': str(e)}), 400
    if fmt == 'json':
        resp = jsonify({'range': {'start': start.isoformat(), 'end': end.isoformat(), 'label': label},
                        'count': len(rows), 'columns': REPORT_COLUMNS, 'truncated': len(rows) >= REPORT_MAX_ROWS,
                        'rows': rows, 'groups': [{'date': d, 'label': _report_day_label(_date.fromisoformat(d)),
                                                  'count': sum(1 for x in rows if x['_date'] == d)}
                                                 for d in sorted({x['_date'] for x in rows})]})
    else:
        stem = f"Proposals_{start.isoformat()}" + ('' if start == end else f"_to_{end.isoformat()}")
        try:
            if fmt == 'xlsx':
                resp = send_file(_report_xlsx(rows, label), as_attachment=True, download_name=stem + '.xlsx',
                                 mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
            else:
                resp = send_file(_report_pdf(rows, label), as_attachment=True, download_name=stem + '.pdf', mimetype='application/pdf')
        except Exception:
            app.logger.exception('proposal report export failed')
            return jsonify({'error': 'Could not build the report file'}), 500
    resp.headers['Cache-Control'] = 'no-store'                                    # contains phone numbers / emails
    return resp


@app.route('/api/reports/filter-options', methods=['GET'])
@login_required()
def reports_filter_options():
    see_all = (session.get('role') or '').lower() in ('admin', 'manager')
    conn = sqlite3.connect(DB_PATH)
    try:
        hrs = [r[0] for r in conn.execute("SELECT DISTINCT sent_by_name FROM proposal_dispatch_log WHERE sent_by_name <> '' ORDER BY 1")] if see_all else []
        clients = [r[0] for r in conn.execute(
            """SELECT name FROM (SELECT client_name AS name FROM requirements UNION SELECT proposed_client FROM candidates)
               WHERE name IS NOT NULL AND TRIM(name) <> '' ORDER BY 1""")]
    finally:
        conn.close()
    return jsonify({'hr': hrs, 'clients': clients, 'see_all': see_all})


@app.route('/api/candidates/<int:candidate_id>/projects', methods=['GET'])
@login_required()
def get_candidate_projects(candidate_id):
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    c.execute('SELECT * FROM candidate_projects WHERE candidate_id = ? ORDER BY created_at DESC', (candidate_id,))
    projects = [dict(row) for row in c.fetchall()]
    conn.close()
    return jsonify(projects)

@app.route('/api/candidates/<int:candidate_id>/projects', methods=['POST'])
@login_required()
def add_candidate_project(candidate_id):
    data = request.json
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('''INSERT INTO candidate_projects (candidate_id, project_name, role, organization, start_date, end_date, description, tech_stack)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)''',
        (candidate_id, data.get('project_name'), data.get('role'), data.get('organization'),
         data.get('start_date'), data.get('end_date'), data.get('description'), data.get('tech_stack')))
    conn.commit()
    conn.close()
    return jsonify({'message': 'Project added'})

@app.route('/api/candidates/projects/<int:project_id>', methods=['PUT'])
@login_required()
def update_candidate_project(project_id):
    data = request.json
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('''UPDATE candidate_projects SET project_name=?, role=?, organization=?, start_date=?, end_date=?, description=?, tech_stack=? WHERE id=?''',
        (data.get('project_name'), data.get('role'), data.get('organization'),
         data.get('start_date'), data.get('end_date'), data.get('description'), data.get('tech_stack'), project_id))
    conn.commit()
    conn.close()
    return jsonify({'message': 'Project updated'})

@app.route('/api/candidates/projects/<int:project_id>', methods=['DELETE'])
@login_required()
def delete_candidate_project(project_id):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('DELETE FROM candidate_projects WHERE id = ?', (project_id,))
    conn.commit()
    conn.close()
    return jsonify({'message': 'Project deleted'})

# ============ EDUCATION API ============
@app.route('/api/candidates/<int:candidate_id>/education-entries', methods=['GET'])
@login_required()
def get_candidate_education(candidate_id):
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    c.execute('SELECT * FROM candidate_education WHERE candidate_id = ? ORDER BY start_year DESC', (candidate_id,))
    education = [dict(row) for row in c.fetchall()]
    conn.close()
    return jsonify(education)

@app.route('/api/candidates/<int:candidate_id>/education-entries', methods=['POST'])
@login_required()
def add_candidate_education(candidate_id):
    data = request.json
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('''INSERT INTO candidate_education (candidate_id, degree, institute, field_of_study, start_year, end_year, grade, location)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)''',
        (candidate_id, data.get('degree'), data.get('institute'), data.get('field_of_study'),
         data.get('start_year'), data.get('end_year'), data.get('grade'), data.get('location')))
    conn.commit()
    conn.close()
    return jsonify({'message': 'Education added'})

@app.route('/api/candidates/education/<int:edu_id>', methods=['PUT'])
@login_required()
def update_candidate_education(edu_id):
    data = request.json
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('''UPDATE candidate_education SET degree=?, institute=?, field_of_study=?, start_year=?, end_year=?, grade=?, location=? WHERE id=?''',
        (data.get('degree'), data.get('institute'), data.get('field_of_study'),
         data.get('start_year'), data.get('end_year'), data.get('grade'), data.get('location'), edu_id))
    conn.commit()
    conn.close()
    return jsonify({'message': 'Education updated'})

@app.route('/api/candidates/education/<int:edu_id>', methods=['DELETE'])
@login_required()
def delete_candidate_education(edu_id):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('DELETE FROM candidate_education WHERE id = ?', (edu_id,))
    conn.commit()
    conn.close()
    return jsonify({'message': 'Education deleted'})

@app.route('/api/candidates/<int:candidate_id>', methods=['PUT']) 
@login_required()
def update_candidate(candidate_id):
    try:
        data = request.json
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        
        # Check ownership - admin can edit all, others only own
        if session.get('role') != 'admin':
            c.execute('SELECT uploaded_by_name, uploaded_by FROM candidates WHERE id = ?', (candidate_id,))
            row = c.fetchone()
            user_name = session.get('user_name') or ''
            if not row or ((row[0] or '') != user_name and (row[1] or '') != user_name):
                conn.close()
                return jsonify({"success": False, "error": "You can only edit your own candidates"}), 403
        
        # Build dynamic update query
        allowed_fields = [
            'first_name', 'last_name', 'middle_name', 'phone', 'email', 'address', 'linkedin',
            'current_role', 'current_ctc', 'expected_ctc', 'designation', 'location', 'years_of_experience',
            'employment_status', 'notice_period_days', 'education', 'notes',
            'proposed_client', 'proposed_requirement', 'stage', 'analysis_summary', 'matched_jd', 'uploaded_by_name',
            'relevant_exp', 'work_mode', 'freelancing', 'engagement_type', 'last_working_day'
        ]
        
        json_fields = ['work_experience', 'certifications', 'core_skills', 'attachments']
        
        updates = []
        values = []
        
        for field in allowed_fields:
            if field in data:
                updates.append(f"{field} = ?")
                values.append(data[field])
        
        for field in json_fields:
            if field in data:
                updates.append(f"{field} = ?")
                values.append(json.dumps(data[field]))
        
        if not updates:
            return jsonify({"success": False, "error": "No fields to update"}), 400
        
        values.append(candidate_id)
        query = f"UPDATE candidates SET {', '.join(updates)} WHERE id = ?"
        
        c.execute(query, values)
        conn.commit()
        conn.close()
        
        return jsonify({"success": True, "message": "Candidate updated successfully"})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500
@app.route('/api/jobs/<int:job_id>', methods=['PUT']) 
@login_required('manager')
def update_job(job_id):
    data = request.json
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('''UPDATE jobs SET 
        title = ?, company = ?, description = ?,
        roles_responsibilities = ?, qualifications = ?,
        required_skills = ?, certifications_required = ?,
        working_mode = ?, hybrid_days = ?, office_location = ?, business_model = ?,
        payroll_company = ?, client_name = ?, end_client = ?,
        years_of_experience = ?, budget = ?, max_salary = ?, headcount = ?
    WHERE id = ?''', (
        data.get('title'),
        data.get('company'),
        data.get('description', ''),
        data.get('roles_responsibilities', ''),
        data.get('qualifications', ''),
        data.get('required_skills', ''),
        data.get('certifications_required', ''),
        data.get('working_mode', 'Not Specified'),
        data.get('hybrid_days', 0),
        data.get('office_location', ''),
        data.get('business_model', 'Not Specified'),
        data.get('payroll_company', ''),
        data.get('client_name', data.get('company', '')),
        data.get('end_client', ''),
        data.get('years_of_experience', 0),
        data.get('budget', ''),
        data.get('max_salary', 0),
        data.get('headcount', 1),
        job_id
    ))
    conn.commit()
    conn.close()
    
    # Send Telegram notification
    user_name = session.get('user_name', 'Manager')
    user_role = session.get('role', '')
    if user_role == 'manager':
        notification = f"""✏️ <b>Job Edited</b>\n\n👤 <b>Edited By:</b> {user_name}\n📋 <b>Job ID:</b> {job_id}\n🔹 <b>Title:</b> {data.get('title', 'N/A')}"""
        send_telegram_message(notification, to_admin=True)
    
    return jsonify({'message': 'Job updated'})

@app.route('/api/jobs/<int:job_id>', methods=['DELETE'])
@login_required('admin')
def delete_job(job_id):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('DELETE FROM jobs WHERE id = ?', (job_id,))
    conn.commit()
    conn.close()
    return jsonify({'message': 'Job deleted'})

@app.route('/api/jobs/<int:job_id>/toggle-active', methods=['PUT'])
@login_required('manager')
def toggle_job_active(job_id):
    data = request.json
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('UPDATE jobs SET is_active = ? WHERE id = ?', 
              (data.get('is_active', 0), job_id))
    conn.commit()
    conn.close()
    
    status = 'Closed' if data.get('is_active', 0) == 0 else 'Reopened'
    user_name = session.get('user_name', 'Manager')
        # Get job details
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('SELECT title, company, requirement_id FROM jobs WHERE id = ?', (job_id,))
    job = c.fetchone()
    conn.close()
    
    job_title = job[0] if job else 'N/A'
    job_company = job[1] if job else 'N/A'
    job_req_id = job[2] if job and job[2] else f'SIT-R-{str(job_id).zfill(3)}'
    
    notification = f"""🔄 <b>Job {status}</b>\n\n👤 <b>By:</b> {user_name}\n🔹 <b>Title:</b> {job_title}\n🏢 <b>Company:</b> {job_company}\n📋 <b>Job ID:</b> {job_req_id}"""
    send_telegram_message(notification, to_admin=True)
    
    return jsonify({'message': 'Job status updated'})

@app.route('/api/jobs/<int:job_id>/documents', methods=['GET'])
def get_job_documents(job_id):
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    c.execute('SELECT * FROM job_documents WHERE job_id = ? ORDER BY uploaded_at DESC', (job_id,))
    docs = [dict(row) for row in c.fetchall()]
    conn.close()
    return jsonify(docs)

@app.route('/api/jobs/upload-document', methods=['POST'])
def upload_job_document():
    job_id = request.form.get('job_id')
    if 'document' not in request.files:
        return jsonify({'error': 'No file'}), 400
    file = request.files['document']
    if file.filename == '':
        return jsonify({'error': 'No file'}), 400
    
    original_filename = file.filename
    filename = secure_filename(f"{job_id}_{datetime.now().timestamp()}_{file.filename}")
    filepath = os.path.join(app.config['JOB_DOCUMENTS_FOLDER'], filename)
    file.save(filepath)
    
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('INSERT INTO job_documents (job_id, filename, original_filename, file_path, file_type) VALUES (?, ?, ?, ?, ?)',
              (job_id, filename, original_filename, filepath, original_filename.split('.')[-1]))
    conn.commit()
    conn.close()
    return jsonify({'message': 'Document uploaded'})

@app.route('/api/jobs/documents/<int:doc_id>', methods=['DELETE'])
def delete_job_document(doc_id):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('SELECT file_path FROM job_documents WHERE id = ?', (doc_id,))
    row = c.fetchone()
    if row and os.path.exists(row[0]):
        os.remove(row[0])
    c.execute('DELETE FROM job_documents WHERE id = ?', (doc_id,))
    conn.commit()
    conn.close()
    return jsonify({'message': 'Document deleted'})

@app.route('/api/candidates', methods=['GET']) 
@login_required()
def get_candidates():
    try:
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        c = conn.cursor()
        c.execute('SELECT * FROM candidates ORDER BY created_at DESC')
        candidates = [dict(row) for row in c.fetchall()]
        conn.close()
        return jsonify(candidates)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/candidates', methods=['POST'])
@login_required()
def create_candidate():
    data = request.get_json(silent=True) or {}

    for key in ('permanent_file_path', 'file_path', 'resume_file_path', 'permanent_filename'):
        data.pop(key, None)

    resume_path, resume_ext, display_name = '', '', ''
    resolved = resolve_resume_upload(data.get('upload_id'))
    if resolved:
        resume_path, resume_ext = resolved
        display_name = clean_display_name(data.get('original_filename'), default=f'resume.{resume_ext}')
        if not display_name.lower().endswith('.' + resume_ext):
            display_name += '.' + resume_ext

    candidate_id = save_candidate_to_db(data, resume_path, display_name)

    if resume_path:
        conn = sqlite3.connect(DB_PATH)
        try:
            c = conn.cursor()
            c.execute('''INSERT INTO candidate_documents
                         (candidate_id, filename, original_filename, file_path, file_type, is_resume)
                         VALUES (?, ?, ?, ?, ?, ?)''',
                      (candidate_id, os.path.basename(resume_path), display_name, resume_path, resume_ext, 1))
            conn.commit()
        finally:
            conn.close()

    return jsonify({'message': 'Candidate saved', 'id': candidate_id})

# ============================================
# DELETE CANDIDATE ENDPOINT
# ============================================
@app.route('/api/candidates/<int:candidate_id>', methods=['DELETE'])
def delete_candidate(candidate_id):
    """Delete a candidate and their documents - only Siraj, Ibaad or Admin"""
    try:
        # Check if user is allowed to delete
        allowed_deleters = ['Siraj', 'Ibaad']
        user_name = session.get('user_name', '')
        user_role = session.get('role', '')
        
        if user_role != 'admin' and user_name not in allowed_deleters:
            return jsonify({'error': 'You are not authorized to delete candidates. Contact Siraj or Ibaad.'}), 403
        
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        
        # Get file paths to delete
        c.execute('SELECT file_path FROM candidate_documents WHERE candidate_id = ?', (candidate_id,))
        files = c.fetchall()
        for file in files:
            safe = safe_stored_path(file[0])
            if safe:
                os.remove(safe)
        
        # Delete candidate
        c.execute('DELETE FROM candidates WHERE id = ?', (candidate_id,))
        conn.commit()
        conn.close()
        
        return jsonify({'message': 'Candidate deleted successfully'}), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/candidates/<int:candidate_id>/documents', methods=['GET'])
def get_candidate_documents(candidate_id):
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    c.execute('SELECT * FROM candidate_documents WHERE candidate_id = ? ORDER BY is_resume DESC', (candidate_id,))
    docs = [dict(row) for row in c.fetchall()]
    conn.close()
    return jsonify(docs)

@app.route('/api/candidates/upload-document', methods=['POST'])
def upload_candidate_document():
    candidate_id = request.form.get('candidate_id')
    if 'document' not in request.files:
        return jsonify({'error': 'No file'}), 400
    file = request.files['document']
    if file.filename == '':
        return jsonify({'error': 'No file'}), 400
    
    original_filename = file.filename
    filename = secure_filename(f"{candidate_id}_{datetime.now().timestamp()}_{file.filename}")
    filepath = os.path.join(app.config['DOCUMENTS_FOLDER'], filename)
    file.save(filepath)
    
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('INSERT INTO candidate_documents (candidate_id, filename, original_filename, file_path, file_type, is_resume) VALUES (?, ?, ?, ?, ?, ?)',
              (candidate_id, filename, original_filename, filepath, original_filename.split('.')[-1], 0))
    conn.commit()
    conn.close()
    return jsonify({'message': 'Document uploaded'})

@app.route('/api/documents/<int:doc_id>/preview', methods=['GET'])
def preview_document(doc_id):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('SELECT * FROM candidate_documents WHERE id = ?', (doc_id,))
    doc = c.fetchone()
    conn.close()
    if doc and os.path.exists(doc[4]):
        file_path = doc[4]
        file_type = doc[5]
        
        if file_type == 'pdf':
            text = extract_text_from_pdf(file_path)
            return jsonify({'type': 'text', 'content': text[:2000]})
        elif file_type == 'docx':
            text = extract_text_from_docx(file_path)
            return jsonify({'type': 'text', 'content': text[:2000]})
        elif file_type in ['png', 'jpg', 'jpeg']:
            with open(file_path, 'rb') as f:
                img_data = base64.b64encode(f.read()).decode('utf-8')
                return jsonify({'type': 'image', 'content': img_data})
    
    return jsonify({'error': 'File not found'}), 404

@app.route('/api/parse-resume', methods=['POST'])
@login_required()
def parse_resume():
    file = request.files.get('resume')
    if not file or not file.filename:
        return jsonify({'error': 'No file'}), 400

    try:
        upload_id, ext, stored_path = save_resume_upload(file)
    except ValueError as e:
        return jsonify({'error': str(e)}), 400

    if ext == 'pdf':
        text = extract_text_from_pdf(stored_path)
    else:
        text = extract_text_from_docx(stored_path)

    if not text:
        os.remove(stored_path)
        return jsonify({'error': 'Could not extract text'}), 400

    ai_parsed = parse_resume_with_groq(text)

    if ai_parsed:
        parsed = cross_validate_resume(ai_parsed, text)
        parsed['resume_text'] = text[:8000]
        parsed['ai_used'] = True
        print(f"AI parsed: {parsed.get('first_name', '')} {parsed.get('last_name', '')} - {len(parsed.get('core_skills', []))} skills")
    else:
        parsed = fallback_parse_resume(text)
        parsed['resume_text'] = text[:8000]
        parsed['ai_used'] = False
        print(f"Fallback parsed: {parsed.get('first_name', '')} {parsed.get('last_name', '')}")

    parsed['upload_id'] = upload_id
    parsed['original_filename'] = clean_display_name(file.filename, default=f'resume.{ext}')
    return jsonify(parsed)

@app.route('/api/analyze-match', methods=['POST'])
def analyze_match():
    data = request.json
    resume_text = data.get('resume_text', '')
    jd_text = data.get('jd_text', '')
    candidate_id = data.get('candidate_id')
    candidate_name = data.get('candidate_name', '')
    job_title = data.get('job_title', '')
    
    if not resume_text or not jd_text:
        return jsonify({'error': 'Missing text'}), 400
    
    result = None
    
    # Try AI analysis first
    if GROQ_ENABLED:
        # Run match analysis
        match_result = analyze_match_with_groq(resume_text, jd_text)
        # Run genuineness check
        genuineness_result = analyze_genuineness(resume_text, candidate_name)
        
        if match_result:
            result = {
                'match_score': match_result.get('match_score', 0),
                'recommendation': match_result.get('recommendation', 'review'),
                'category_scores': match_result.get('category_scores', {}),
                'matching_skills': match_result.get('matching_skills', []),
                'missing_skills': match_result.get('missing_skills', []),
                'strengths': match_result.get('strengths', []),
                'weaknesses': match_result.get('weaknesses', []),
                'detailed_analysis': match_result.get('detailed_analysis', ''),
                'executive_summary': match_result.get('detailed_analysis', match_result.get('executive_summary', '')),
                'pre_screening_questions': match_result.get('pre_screening_questions', []),
                'ai_used': True
            }
            
            # Add genuineness data
            if genuineness_result:
                result['genuineness_score'] = genuineness_result.get('genuineness_score', 50)
                result['ai_generated_probability'] = genuineness_result.get('ai_generated_probability', 50)
                result['red_flags'] = genuineness_result.get('red_flags', [])
                result['genuineness_verdict'] = genuineness_result.get('verdict', '')
                result['genuineness_analysis'] = genuineness_result.get('detailed_analysis', '')
            
            # Add skill gap
            skill_gap = analyze_skill_gap(resume_text, jd_text)
            result['skill_gap'] = skill_gap
            
            # Generate interview questions
            missing_skills = skill_gap.get('missing_skills', [])
            interview_questions = generate_interview_questions(jd_text, resume_text, missing_skills)
            result['interview_questions'] = interview_questions
    
    # Fallback to local analysis if AI failed
    if not result:
        result = analyze_resume_locally(resume_text, jd_text)
        result['ai_used'] = False
        
        # Add skill gap
        skill_gap = analyze_skill_gap(resume_text, jd_text)
        result['skill_gap'] = skill_gap
        
        # Add interview questions
        missing_skills = skill_gap.get('missing_skills', [])
        interview_questions = generate_interview_questions(jd_text, resume_text, missing_skills)
        result['interview_questions'] = interview_questions
    
    # Save to database if candidate_id provided
    if result and candidate_id:
        detailed_json = json.dumps(result, indent=2)
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        c.execute('UPDATE candidates SET match_score = ?, recommendation = ?, detailed_analysis = ? WHERE id = ?',
                  (result.get('match_score', 0), result.get('recommendation', 'review'), detailed_json, candidate_id))
        conn.commit()
        conn.close()
    
    if result:
        return jsonify(result)
    
    return jsonify({'error': 'Analysis failed'}), 500

    return jsonify({'error': 'Analysis failed'}), 500

# ============================================
# INTERVIEW TRACKER ROUTES
# ============================================

@app.route('/api/interviews', methods=['GET']) 
@login_required()
def get_interviews():
    date_filter = request.args.get('date', '')
    round_filter = request.args.get('round', '')
    verdict_filter = request.args.get('verdict', '')
    
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    
    query = 'SELECT * FROM interviews WHERE 1=1'
    params = []
    
    if date_filter:
        query += ' AND interview_date = ?'
        params.append(date_filter)
    if round_filter:
        query += ' AND round = ?'
        params.append(round_filter)
    if verdict_filter:
        query += ' AND verdict = ?'
        params.append(verdict_filter)
    
    query += ' ORDER BY interview_date DESC, interview_time DESC'
    c.execute(query, params)
    interviews = [dict(row) for row in c.fetchall()]
    conn.close()
    return jsonify(interviews)

@app.route('/api/interviews', methods=['POST']) 
@login_required()
def create_interview():
    data = request.json
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('''INSERT INTO interviews 
        (candidate_id, candidate_name, resource_owner, interview_date, interview_time,
         round, client_name, client_poc, requirement_id, scheduled_by)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)''',
        (data.get('candidate_id'), data.get('candidate_name'), data.get('resource_owner'),
         data.get('interview_date'), data.get('interview_time'), data.get('round', 'L1'),
         data.get('client_name'), data.get('client_poc'), data.get('requirement_id'),
         data.get('scheduled_by', 'HR')))
    conn.commit()
    conn.close()

    # Send Telegram notification
    notification = f"""📅 <b>New Interview Scheduled</b>

👤 <b>Candidate:</b> {data.get('candidate_name')}
🎯 <b>Round:</b> {data.get('round')}
📅 <b>Date:</b> {data.get('interview_date')}
🕐 <b>Time:</b> {data.get('interview_time', 'TBD')}
🏢 <b>Client:</b> {data.get('client_name', 'N/A')}
👤 <b>Scheduled By:</b> {session.get('user_name', 'HR')}"""
    
    send_telegram_message(notification)
    
    return jsonify({'message': 'Interview scheduled'})

@app.route('/api/interviews/<int:interview_id>', methods=['PUT'])
def update_interview(interview_id):
    data = request.json
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('UPDATE interviews SET verdict = ?, feedback = ? WHERE id = ?',
              (data.get('verdict'), data.get('feedback', ''), interview_id))
    conn.commit()
    conn.close()
    
    # Send Telegram notification
    verdict = data.get('verdict', 'Scheduled')
    feedback = data.get('feedback', '')
    notification = f"""📊 <b>Interview Verdict Updated</b>

🎯 <b>Verdict:</b> {verdict}
💬 <b>Feedback:</b> {feedback if feedback else 'N/A'}
👤 <b>Updated By:</b> {session.get('user_name', 'HR')}"""
    
    send_telegram_message(notification)
    
    return jsonify({'message': 'Interview updated'})
@app.route('/api/interviews/<int:interview_id>/send-email', methods=['POST'])
def send_interview_email(interview_id):
    data = request.json
    email_type = data.get('type', 'invite')  # 'invite' or 'verdict'
    
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    c.execute('SELECT * FROM interviews WHERE id = ?', (interview_id,))
    interview = c.fetchone()
    
    if not interview:
        conn.close()
        return jsonify({'error': 'Interview not found'}), 404
    
    # Get candidate email
    c.execute('SELECT email, first_name, last_name FROM candidates WHERE id = ?', (interview['candidate_id'],))
    candidate = c.fetchone()
    conn.close()
    
    if not candidate or not candidate['email']:
        return jsonify({'error': 'Candidate email not found'}), 400
    
    candidate_name = f"{candidate['first_name'] or ''} {candidate['last_name'] or ''}".strip()
    
    if email_type == 'invite':
        subject = f"Interview Invitation - {interview['round']} Round | {interview['client_name'] or 'Client'}"
        body = f"""
        <div style="font-family:Arial,sans-serif;max-width:600px;margin:0 auto;padding:20px;">
            <h2 style="color:#1B2A4A;">📅 Interview Invitation</h2>
            <p>Dear <strong>{candidate_name}</strong>,</p>
            <p>Your interview has been scheduled. Here are the details:</p>
            <table style="width:100%;border-collapse:collapse;margin:20px 0;">
                <tr><td style="padding:8px;border:1px solid #ddd;background:#F5F5F5;"><strong>Date</strong></td><td style="padding:8px;border:1px solid #ddd;">{interview['interview_date']}</td></tr>
                <tr><td style="padding:8px;border:1px solid #ddd;background:#F5F5F5;"><strong>Time</strong></td><td style="padding:8px;border:1px solid #ddd;">{interview['interview_time'] or 'TBD'}</td></tr>
                <tr><td style="padding:8px;border:1px solid #ddd;background:#F5F5F5;"><strong>Round</strong></td><td style="padding:8px;border:1px solid #ddd;">{interview['round']}</td></tr>
                <tr><td style="padding:8px;border:1px solid #ddd;background:#F5F5F5;"><strong>Client</strong></td><td style="padding:8px;border:1px solid #ddd;">{interview['client_name'] or 'N/A'}</td></tr>
                <tr><td style="padding:8px;border:1px solid #ddd;background:#F5F5F5;"><strong>Requirement</strong></td><td style="padding:8px;border:1px solid #ddd;">{interview['requirement_id'] or 'N/A'}</td></tr>
            </table>
            <p>Please be available 5 minutes before the scheduled time.</p>
            <p>Best regards,<br><strong>ShahnaIT Recruitment Team</strong></p>
        </div>    
        """
    else:  # verdict
        verdict_emoji = {'Selected': '✅', 'Rejected': '❌', 'Hold': '⏸️', 'No Show': '🚫', 'Rescheduled': '🔄'}.get(interview['verdict'], '📋')
        subject = f"Interview Update - {interview['verdict']} | {interview['client_name'] or 'Client'}"
        body = f"""
        <div style="font-family:Arial,sans-serif;max-width:600px;margin:0 auto;padding:20px;">
            <h2 style="color:#1B2A4A;">{verdict_emoji} Interview Update</h2>
            <p>Dear <strong>{candidate_name}</strong>,</p>
            <p>Here is an update regarding your interview:</p>
            <table style="width:100%;border-collapse:collapse;margin:20px 0;">
                <tr><td style="padding:8px;border:1px solid #ddd;background:#F5F5F5;"><strong>Date</strong></td><td style="padding:8px;border:1px solid #ddd;">{interview['interview_date']}</td></tr>
                <tr><td style="padding:8px;border:1px solid #ddd;background:#F5F5F5;"><strong>Round</strong></td><td style="padding:8px;border:1px solid #ddd;">{interview['round']}</td></tr>
                <tr><td style="padding:8px;border:1px solid #ddd;background:#F5F5F5;"><strong>Verdict</strong></td><td style="padding:8px;border:1px solid #ddd;font-weight:bold;">{interview['verdict']}</td></tr>
                <tr><td style="padding:8px;border:1px solid #ddd;background:#F5F5F5;"><strong>Feedback</strong></td><td style="padding:8px;border:1px solid #ddd;">{interview['feedback'] or 'N/A'}</td></tr>
            </table>
            <p>Best regards,<br><strong>ShahnaIT Recruitment Team</strong></p>
        </div>
        """
    
    success = send_email(candidate['email'], subject, body)
    
    if success:
        # Log email in database
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        c.execute('''CREATE TABLE IF NOT EXISTS email_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            interview_id INTEGER,
            candidate_id INTEGER,
            email_type TEXT,
            sent_to TEXT,
            subject TEXT,
            sent_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )''')
        c.execute('INSERT INTO email_logs (interview_id, candidate_id, email_type, sent_to, subject) VALUES (?, ?, ?, ?, ?)',
                  (interview_id, interview['candidate_id'], email_type, candidate['email'], subject))
        conn.commit()
        conn.close()
        return jsonify({'message': 'Email sent successfully'})
    
    return jsonify({'error': 'Failed to send email'}), 500    


@app.route('/api/telegram/daily-digest', methods=['POST'])
@login_required('admin')
def send_daily_digest():
    today = datetime.now().strftime('%Y-%m-%d')
    
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    c.execute('SELECT * FROM interviews WHERE interview_date = ? ORDER BY interview_time', (today,))
    interviews = [dict(row) for row in c.fetchall()]
    conn.close()
    
    if not interviews:
        message = f"📅 <b>Daily Interview Digest - {today}</b>\n\n✅ No interviews scheduled today."
    else:
        message = f"📅 <b>Daily Interview Digest - {today}</b>\n\n"
        for i in interviews:
            message += f"🕐 {i['interview_time'] or 'TBD'} - {i['candidate_name']} ({i['round']}) - {i['client_name'] or 'N/A'}\n"
    
    send_telegram_message(message)
    return jsonify({'message': 'Digest sent'})

@app.route('/api/uploaders', methods=['GET'])
@login_required()
def get_uploaders():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('SELECT name FROM uploaders ORDER BY name')
    uploaders = [row[0] for row in c.fetchall()]
    conn.close()
    return jsonify(uploaders)

@app.route('/api/uploaders', methods=['POST'])
@login_required('admin')
def add_uploader():
    data = request.json
    name = data.get('name', '').strip()
    if not name:
        return jsonify({'error': 'Name required'}), 400
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    try:
        c.execute('INSERT INTO uploaders (name) VALUES (?)', (name,))
        conn.commit()
    except:
        conn.close()
        return jsonify({'error': 'Name already exists'}), 400
    conn.close()
    return jsonify({'message': 'Uploader added'})

@app.route('/api/uploaders/<name>', methods=['DELETE'])
@login_required('admin')
def delete_uploader(name):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('DELETE FROM uploaders WHERE name = ?', (name,))
    conn.commit()
    conn.close()
    return jsonify({'message': 'Uploader deleted'})
    
@app.route('/test-drive')
def test_drive():
    service_account_json = os.environ.get('GOOGLE_SERVICE_ACCOUNT', '')
    return jsonify({
        'has_key': bool(service_account_json),
        'length': len(service_account_json) if service_account_json else 0
    })

@app.route('/test-drive-list')
def test_drive_list():
    service_account_json = os.environ.get('GOOGLE_SERVICE_ACCOUNT', '')
    try:
        from google.oauth2 import service_account
        from googleapiclient.discovery import build
        import tempfile
        
        sa_data = json.loads(service_account_json)
        sa_file = tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False)
        json.dump(sa_data, sa_file)
        sa_file.close()
        
        creds = service_account.Credentials.from_service_account_file(
           sa_file.name, scopes=['https://www.googleapis.com/auth/drive'])
        drive_service = build('drive', 'v3', credentials=creds)
        
        results = drive_service.files().list(pageSize=20, fields="files(id, name, parents)").execute()
        files = results.get('files', [])
        
        os.unlink(sa_file.name)
        
        return jsonify({
            'file_count': len(files),
            'files': [{'name': f['name'], 'id': f['id']} for f in files]
        })
    except Exception as e:
        return jsonify({'error': str(e)})

@app.route('/api/admin/backup', methods=['POST'])
@login_required('admin')
def trigger_backup():
    try:
        result = perform_backup()
        return jsonify(result)
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/admin/backups', methods=['GET'])
@login_required('admin')
def list_backups():
    backup_dir = '/data/backups'
    os.makedirs(backup_dir, exist_ok=True)
    backups = []
    for f in sorted(os.listdir(backup_dir), reverse=True):
        if f.endswith('.db'):
            path = os.path.join(backup_dir, f)
            size = os.path.getsize(path)
            backups.append({
                'filename': f,
                'size': f'{size/1024/1024:.1f} MB' if size > 1024*1024 else f'{size/1024:.1f} KB',
                'date': f[:10]
            })
    return jsonify({'backups': backups})

def perform_backup():
    backup_dir = '/data/backups'
    os.makedirs(backup_dir, exist_ok=True)
    date_str = datetime.now().strftime('%Y-%m-%d_%H%M')
    backup_filename = f'shahnai_backup_{date_str}.db'
    backup_path = os.path.join(backup_dir, backup_filename)
    shutil.copy2(DB_PATH, backup_path)
    all_backups = sorted([f for f in os.listdir(backup_dir) if f.endswith('.db')])
    if len(all_backups) > 30:
        for old_file in all_backups[:-30]:
            os.remove(os.path.join(backup_dir, old_file))
    drive_result = upload_to_drive(backup_path, backup_filename)
    return {
        'success': True,
        'filename': backup_filename,
        'drive_upload': drive_result,
        'message': 'Backup created' + (' and uploaded to Drive' if drive_result else ' (local only)')
    }

def upload_to_drive(filepath, filename):
    service_account_json = os.environ.get('GOOGLE_SERVICE_ACCOUNT', '')
    folder_name = os.environ.get('GOOGLE_DRIVE_FOLDER', 'ShahnaIT-Backups')
    if not service_account_json:
        return False
    try:
        from google.oauth2 import service_account
        from googleapiclient.discovery import build
        from googleapiclient.http import MediaFileUpload
        import tempfile
        
        sa_data = json.loads(service_account_json)
        sa_file = tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False)
        json.dump(sa_data, sa_file)
        sa_file.close()
        
        creds = service_account.Credentials.from_service_account_file(
            sa_file.name, scopes=['https://www.googleapis.com/auth/drive'])
        drive_service = build('drive', 'v3', credentials=creds)
        
                # Use the shared folder in your Drive
        folder_id = '1yMZ4QmG_9PCdC4ulQtRXJsELmeAcwXeb'
        
        media = MediaFileUpload(filepath, mimetype='application/octet-stream', resumable=True)
        uploaded_file = drive_service.files().create(body={'name': filename, 'parents': [folder_id]}, media_body=media).execute()
        
        try:
            drive_service.permissions().create(
                fileId=uploaded_file['id'],
                body={'type': 'user', 'role': 'writer', 'emailAddress': 'ibaadrn@shahnait.com'},
                sendNotificationEmail=False
            ).execute()
            print(f"📧 Shared with ibaadrn@shahnait.com")
        except Exception as share_err:
            print(f"Share error: {share_err}")

        os.unlink(sa_file.name)        
        return True
    except Exception as e:
        error_msg = str(e)
        print(f"Drive error: {error_msg}")
        return error_msg

@app.route('/api/admin/backup/download/<filename>')
@login_required('admin')
def download_backup(filename):
    filepath = os.path.join('/data/backups', secure_filename(filename))
    if os.path.exists(filepath):
        return send_file(filepath, as_attachment=True, download_name=filename)
    return jsonify({'error': 'File not found'}), 404

@app.route('/api/admin/export-pdf', methods=['GET'])
@login_required('admin')
def export_pdf():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font('Times', 'B', 16)
    pdf.cell(0, 10, 'ShahnaIT Scout - Data Backup Report', ln=True, align='C')
    pdf.set_font('Times', '', 10)
    pdf.cell(0, 8, f'Generated: {datetime.now().strftime("%d %B %Y, %I:%M %p")}', ln=True, align='C')
    pdf.ln(5)
    
    pdf.set_font('Times', 'B', 13)
    pdf.cell(0, 8, 'Candidates', ln=True)
    pdf.set_font('Times', '', 9)
    c.execute('SELECT * FROM candidates ORDER BY id')
    for cand in c.fetchall():
        pdf.set_font('Times', 'B', 10)
        pdf.cell(0, 6, f"{cand['first_name'] or ''} {cand['last_name'] or ''} - SIT-C-{str(cand['id']).zfill(3)}", ln=True)
        pdf.set_font('Times', '', 9)
        pdf.cell(0, 5, f"Email: {cand['email'] or 'N/A'} | Phone: {cand['phone'] or 'N/A'} | Stage: {cand['stage'] or 'new'} | Match: {cand['match_score'] or 0}%", ln=True)
        pdf.ln(2)
    
    pdf.add_page()
    pdf.set_font('Times', 'B', 13)
    pdf.cell(0, 8, 'Jobs / Requirements', ln=True)
    pdf.set_font('Times', '', 9)
    c.execute('SELECT * FROM jobs ORDER BY id')
    for job in c.fetchall():
        pdf.set_font('Times', 'B', 10)
        pdf.cell(0, 6, f"{job['title'] or 'N/A'} - {job['requirement_id'] or 'SIT-R-'+str(job['id']).zfill(3)}", ln=True)
        pdf.set_font('Times', '', 9)
        pdf.cell(0, 5, f"Client: {job['client_name'] or job['company'] or 'N/A'}", ln=True)
        pdf.ln(2)
    
    pdf.ln(5)
    pdf.set_font('Times', 'B', 13)
    pdf.cell(0, 8, 'Interviews', ln=True)
    pdf.set_font('Times', '', 9)
    c.execute('SELECT * FROM interviews ORDER BY interview_date DESC')
    for iv in c.fetchall():
        pdf.set_font('Times', 'B', 10)
        pdf.cell(0, 6, f"{iv['candidate_name'] or 'N/A'} - {iv['round'] or 'N/A'} ({iv['interview_date']})", ln=True)
        pdf.set_font('Times', '', 9)
        pdf.cell(0, 5, f"Verdict: {iv['verdict'] or 'Scheduled'}", ln=True)
        pdf.ln(2)
    
    conn.close()
    
    pdf_path = '/data/backups/backup_report.pdf'
    pdf.output(pdf_path)
    return send_file(pdf_path, as_attachment=True, download_name=f'shahnai_report_{datetime.now().strftime("%Y%m%d")}.pdf')

@app.route('/api/daily-report', methods=['GET'])
@login_required()
def daily_report():
    date = request.args.get('date', datetime.now().strftime('%Y-%m-%d'))
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    
    c.execute('SELECT COUNT(*) as count FROM jobs WHERE is_active = 1')
    active_reqs = c.fetchone()['count']
    
    c.execute('SELECT id, title, company, requirement_id, created_at FROM jobs WHERE is_active = 1 ORDER BY created_at DESC')
    active_jobs = [dict(row) for row in c.fetchall()]
    
    c.execute('SELECT * FROM interviews WHERE interview_date = ? ORDER BY interview_time', (date,))
    interviews = [dict(row) for row in c.fetchall()]
    
    c.execute("SELECT id, first_name, last_name, email, uploaded_by_name, proposed_client, proposed_requirement, created_at, proposed_date FROM candidates WHERE date(proposed_date) = ? ORDER BY proposed_date DESC", (date,))
    candidates_added = [dict(row) for row in c.fetchall()]
    
    c.execute("SELECT * FROM interviews WHERE interview_date = ? AND verdict != 'Scheduled'", (date,))
    completed_interviews = [dict(row) for row in c.fetchall()]

    # Proposals by recruiter
    c.execute("""SELECT uploaded_by_name, COUNT(*) as count 
                 FROM candidates 
                 WHERE date(proposed_date) = ? AND uploaded_by_name IS NOT NULL
                 GROUP BY uploaded_by_name
                 ORDER BY count DESC""", (date,))
    proposals_by_recruiter = [dict(row) for row in c.fetchall()]
    
    conn.close()
    
    return jsonify({
        'date': date,
        'active_requirements': active_reqs,
        'active_jobs': active_jobs,
        'interviews_scheduled': len(interviews),
        'interviews': interviews,
        'interviews_completed': len(completed_interviews),
        'completed_interviews': completed_interviews,
        'candidates_added': len(candidates_added),
        'candidates': candidates_added,
        'proposals_by_recruiter': proposals_by_recruiter
    })

@app.route('/api/invoices/<int:invoice_id>/edit', methods=['PUT'])
@login_required('admin')
def edit_invoice(invoice_id):
    data = request.json
    
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    
    # Update invoice
    c.execute('''UPDATE invoices SET client_name=?, invoice_date=?, due_date=?, description=?, amount=?, gst_percent=? WHERE id=?''',
        (data.get('client_name'), data.get('invoice_date'), data.get('due_date'), 
         data.get('description'), data.get('amount'), data.get('gst_percent'), invoice_id))
    
    # Recalculate GST and total
    amount = data.get('amount', 0)
    gst = data.get('gst_percent', 18)
    gst_amount = round(amount * gst / 100, 2)
    total = amount + gst_amount
    c.execute('UPDATE invoices SET gst_amount=?, total_amount=? WHERE id=?', (gst_amount, total, invoice_id))
    
    # Update client GSTIN/address in onboarded resource
    c.execute('SELECT onboarded_resource_id FROM invoices WHERE id=?', (invoice_id,))
    row = c.fetchone()
    if row:
        c.execute('''UPDATE onboarded_resources SET client_gstin=?, client_address=? WHERE id=?''',
            (data.get('client_gstin', ''), data.get('client_address', ''), row[0]))
    
    # Save bank details to company settings
    for key, setting_key in [('bank_name','bank_name'), ('account_no','account_no'), ('ifsc_code','ifsc_code'), ('branch','branch')]:
        if data.get(key):
            c.execute('UPDATE company_settings SET setting_value=? WHERE setting_key=?', (data[key], setting_key))
    
    conn.commit()
    conn.close()
    return jsonify({'message': 'Invoice updated'})

@app.route('/api/expenses', methods=['GET'])
@login_required('admin')
def get_expenses():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    c.execute('SELECT * FROM expenses ORDER BY expense_date DESC')
    expenses = [dict(row) for row in c.fetchall()]
    conn.close()
    return jsonify(expenses)

@app.route('/api/expenses', methods=['POST'])
@login_required('admin')
def create_expense():
    data = request.form.to_dict() if request.form else request.json
    if not data:
        data = request.json
    
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('''INSERT INTO expenses (expense_date, category, description, amount, paid_by, vendor)
        VALUES (?, ?, ?, ?, ?, ?)''',
        (data.get('expense_date'), data.get('category'), data.get('description'),
         float(data.get('amount', 0)), data.get('paid_by'), data.get('vendor')))
    
    expense_id = c.lastrowid
    
    # Handle file upload
    if 'bill_file' in request.files:
        file = request.files['bill_file']
        if file.filename:
            doc_dir = f'/data/expense_docs/{expense_id}'
            os.makedirs(doc_dir, exist_ok=True)
            filename = secure_filename(f"{datetime.now().timestamp()}_{file.filename}")
            filepath = os.path.join(doc_dir, filename)
            file.save(filepath)
            c.execute('UPDATE expenses SET invoice_ref = ? WHERE id = ?', (filepath, expense_id))
    
    conn.commit()
    conn.close()
    return jsonify({'message': 'Expense added'})

@app.route('/api/expenses/<int:expense_id>/download-bill')
@login_required('admin')
def download_expense_bill(expense_id):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('SELECT invoice_ref FROM expenses WHERE id = ?', (expense_id,))
    row = c.fetchone()
    conn.close()
    if row and row[0] and os.path.exists(row[0]):
        return send_file(row[0], as_attachment=False)
    return jsonify({'error': 'File not found'}), 404

@app.route('/api/export-invoices', methods=['GET'])
@login_required('admin')
def export_invoices():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    c.execute('SELECT * FROM invoices ORDER BY created_at DESC')
    rows = c.fetchall()
    conn.close()
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(['Invoice No', 'Client', 'Resource', 'Amount', 'GST', 'Total', 'Date', 'Status'])
    for row in rows:
        writer.writerow([row['invoice_number'], row['client_name'], row['resource_name'], 
                         row['amount'], row['gst_amount'], row['total_amount'], row['invoice_date'], row['status']])
    output.seek(0)
    return Response(output.getvalue(), mimetype='text/csv', headers={'Content-Disposition': 'attachment; filename=invoices.csv'})

@app.route('/api/export-expenses', methods=['GET'])
@login_required('admin')
def export_expenses():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    c.execute('SELECT * FROM expenses ORDER BY expense_date DESC')
    rows = c.fetchall()
    conn.close()
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(['Date', 'Category', 'Description', 'Amount', 'Vendor', 'Paid By'])
    for row in rows:
        writer.writerow([row['expense_date'], row['category'], row['description'], 
                         row['amount'], row['vendor'], row['paid_by']])
    output.seek(0)
    return Response(output.getvalue(), mimetype='text/csv', headers={'Content-Disposition': 'attachment; filename=expenses.csv'})

@app.route('/api/export-interviews', methods=['GET'])
@login_required('admin')
def export_interviews():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    c.execute('SELECT * FROM interviews ORDER BY interview_date DESC')
    rows = c.fetchall()
    conn.close()
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(['Date', 'Time', 'Candidate', 'Round', 'Client', 'Verdict', 'Resource Owner'])
    for row in rows:
        writer.writerow([row['interview_date'], row['interview_time'], row['candidate_name'],
                         row['round'], row['client_name'], row['verdict'], row['resource_owner']])
    output.seek(0)
    return Response(output.getvalue(), mimetype='text/csv', headers={'Content-Disposition': 'attachment; filename=interviews.csv'})

@app.route('/api/export-finance-pdf', methods=['GET'])
@login_required('admin')
def export_finance_pdf():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    c.execute("SELECT * FROM onboarded_resources WHERE status = 'Active'")
    resources = [dict(row) for row in c.fetchall()]
    
    total_revenue = sum(r['billing_rate'] or 0 for r in resources)
    total_salary = sum(r['monthly_salary'] or 0 for r in resources)
    total_profit = total_revenue - total_salary
    
    c.execute('SELECT SUM(amount) as total FROM expenses')
    total_expenses = c.fetchone()['total'] or 0
    conn.close()
    
    net_profit = total_profit - total_expenses
    
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font('Times', 'B', 16)
    pdf.cell(0, 10, 'ShahnaIT LLP - Finance Report', ln=True, align='C')
    pdf.ln(5)
    pdf.set_font('Times', 'B', 12)
    pdf.cell(0, 8, 'Summary', ln=True)
    pdf.set_font('Times', '', 11)
    pdf.cell(0, 7, f'Total Monthly Revenue: Rs. {total_revenue:,.2f}', ln=True)
    pdf.cell(0, 7, f'Total Monthly Salary: Rs. {total_salary:,.2f}', ln=True)
    pdf.cell(0, 7, f'Gross Profit: Rs. {total_profit:,.2f}', ln=True)
    pdf.cell(0, 7, f'Total Expenses: Rs. {total_expenses:,.2f}', ln=True)
    pdf.cell(0, 7, f'Net Profit: Rs. {net_profit:,.2f}', ln=True)
    pdf.ln(8)
    
    pdf.set_font('Times', 'B', 12)
    pdf.cell(0, 8, 'Resource-wise Breakdown', ln=True)
    pdf.set_font('Times', '', 10)
    for r in resources:
        margin = ((r['billing_rate'] or 0) - (r['monthly_salary'] or 0)) / (r['billing_rate'] or 1) * 100
        pdf.cell(0, 6, f"{r.get('first_name','')} {r.get('last_name','')} - {r['client_name']} - Margin: {margin:.1f}%", ln=True)
    
    pdf_path = '/data/backups/finance_report.pdf'
    pdf.output(pdf_path)
    return send_file(pdf_path, as_attachment=True, download_name='finance_report.pdf')

@app.route('/debug-parse-full/<int:candidate_id>')
@login_required('admin')
def debug_parse_full(candidate_id):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('SELECT resume_text FROM candidates WHERE id = ?', (candidate_id,))
    row = c.fetchone()
    conn.close()
    
    if not row or not row[0]:
        return jsonify({'error': 'No resume text'})
    
    # Call AI directly
    cleaned_text = normalize_resume_text(row[0])
    
    # Raw response check
    prompt_test = f"""Extract education and designation from this resume. Return ONLY JSON with these fields:
{{"designation": "", "current_role": "", "education": [{{"degree": "", "institute": "", "start_year": "", "end_year": "", "grade": ""}}]}}

RESUME:
{cleaned_text[:3000]}"""
    
    raw = call_groq_api(prompt_test, max_tokens=1000)
    
    return jsonify({
        'resume_length': len(row[0]),
        'cleaned_preview': cleaned_text[:800],
        'ai_response': raw if raw else 'NULL'
    })

@app.route('/debug-groq-test')
@login_required('admin')
def debug_groq_test():
    test_prompt = "Return ONLY this JSON: {\"test\": \"success\"}"
    api_key = os.environ.get('GROQ_API_KEY', '')
    
    # Try direct request to see actual error
    try:
        url = "https://api.groq.com/openai/v1/chat/completions"
        headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
        payload = {
            "model": "openai/gpt-oss-120b",
            "messages": [{"role": "user", "content": test_prompt}],
            "temperature": 0.1,
            "max_tokens": 4000
        }
        response = requests.post(url, json=payload, headers=headers, timeout=45)
        return jsonify({
            'key_prefix': api_key[:10] if api_key else 'NONE',
            'status_code': response.status_code,
            'response_preview': response.text[:500]
        })
    except Exception as e:
        return jsonify({
            'key_prefix': api_key[:10] if api_key else 'NONE',
            'exception_type': type(e).__name__,
            'exception_message': str(e)
        })
    
@app.route('/debug-parse/<int:candidate_id>')
@login_required('admin')
def debug_parse(candidate_id):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('SELECT resume_text FROM candidates WHERE id = ?', (candidate_id,))
    row = c.fetchone()
    conn.close()
    
    if not row or not row[0]:
        return jsonify({'error': 'No resume text'})
    
    # Test normalize
    cleaned = normalize_resume_text(row[0])
    
    # Build the same prompt
    prompt_test = f"""Test prompt check. Resume first 500 chars:\n{cleaned[:500]}"""
    raw_response = call_groq_api(prompt_test, max_tokens=100)
    
    return jsonify({
        'resume_length': len(row[0]),
        'cleaned_length': len(cleaned),
        'first_500': cleaned[:500],
        'groq_test': raw_response[:200] if raw_response else 'NULL - Groq call failed'
    })

# ============================================
# ONBOARDED RESOURCES
# ============================================

@app.route('/api/onboarded', methods=['GET'])
@login_required()
def get_onboarded():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    c.execute('''SELECT o.*, c.first_name, c.last_name, c.email, c.phone 
                 FROM onboarded_resources o 
                 LEFT JOIN candidates c ON o.candidate_id = c.id 
                 ORDER BY o.id DESC''')
    resources = [dict(row) for row in c.fetchall()]
    conn.close()
    return jsonify(resources)

@app.route('/api/onboarded', methods=['POST'])
@login_required('manager')
def create_onboarded():
    data = request.form.to_dict() if request.form else request.json
    if not data:
        data = request.json
    
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('''INSERT INTO onboarded_resources 
        (candidate_id, client_name, doj, resource_owner, work_location,
         monthly_salary, billing_rate, business_model, requirement_id, requirement_name, po_number)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)''',
        (data.get('candidate_id'), data.get('client_name'), data.get('doj'),
         data.get('resource_owner'), data.get('work_location'),
         float(data.get('monthly_salary', 0)), float(data.get('billing_rate', 0)),
         data.get('business_model', 'C2C'), data.get('requirement_id', ''),
         data.get('requirement_name', ''), data.get('po_number', '')))
    
    resource_id = c.lastrowid
    
    if 'documents' in request.files:
        files = request.files.getlist('documents')
        doc_dir = f'/data/onboarded_docs/{resource_id}'
        os.makedirs(doc_dir, exist_ok=True)
        uploaded_files = []
        for file in files:
            if file.filename:
                filename = secure_filename(f"{datetime.now().timestamp()}_{file.filename}")
                filepath = os.path.join(doc_dir, filename)
                file.save(filepath)
                uploaded_files.append({'filename': filename, 'original_name': file.filename, 'path': filepath})
        if uploaded_files:
            c.execute('UPDATE onboarded_resources SET sow_attached = ? WHERE id = ?',
                      (json.dumps(uploaded_files), resource_id))
    
    conn.commit()
    conn.close()
    return jsonify({'message': 'Resource onboarded', 'id': resource_id})

@app.route('/api/client-analytics', methods=['GET'])
@login_required('admin')
def client_analytics():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    
    # Get all unique clients from jobs, candidates, interviews, onboarded
    clients = {}
    
    # From jobs
    c.execute("SELECT DISTINCT COALESCE(client_name, company, 'Unknown') as client FROM jobs WHERE client_name IS NOT NULL OR company IS NOT NULL")
    for row in c.fetchall():
        if row['client'] not in clients:
            clients[row['client']] = {'requirements': 0, 'proposals': 0, 'interviews': 0, 'closures': 0, 'revenue': 0}
    
    # From onboarded
    c.execute("SELECT DISTINCT client_name FROM onboarded_resources WHERE client_name IS NOT NULL")
    for row in c.fetchall():
        if row['client_name'] not in clients:
            clients[row['client_name']] = {'requirements': 0, 'proposals': 0, 'interviews': 0, 'closures': 0, 'revenue': 0}
    
    # Count requirements per client
    c.execute("SELECT COALESCE(client_name, company, 'Unknown') as client, COUNT(*) as count FROM jobs GROUP BY client")
    for row in c.fetchall():
        if row['client'] in clients:
            clients[row['client']]['requirements'] = row['count']
    
    # Count proposals per client
    c.execute("SELECT COALESCE(proposed_client, 'Unknown') as client, COUNT(*) as count FROM candidates WHERE proposed_client IS NOT NULL GROUP BY client")
    for row in c.fetchall():
        if row['client'] in clients:
            clients[row['client']]['proposals'] = row['count']
    
    # Count interviews per client
    c.execute("SELECT COALESCE(client_name, 'Unknown') as client, COUNT(*) as count FROM interviews GROUP BY client")
    for row in c.fetchall():
        if row['client'] in clients:
            clients[row['client']]['interviews'] = row['count']
    
    # Count closures + revenue per client
    c.execute("SELECT client_name, COUNT(*) as count, SUM(billing_rate) as revenue FROM onboarded_resources WHERE status = 'Active' GROUP BY client_name")
    for row in c.fetchall():
        if row['client_name'] in clients:
            clients[row['client_name']]['closures'] = row['count']
            clients[row['client_name']]['revenue'] = row['revenue'] or 0
    
    conn.close()
    
    # Convert to list
    client_list = []
    for name, data in clients.items():
        conversion = round((data['closures'] / data['proposals'] * 100)) if data['proposals'] > 0 else 0
        client_list.append({
            'name': name,
            'requirements': data['requirements'],
            'proposals': data['proposals'],
            'interviews': data['interviews'],
            'closures': data['closures'],
            'revenue': data['revenue'],
            'conversion': conversion
        })
    
    # Sort by revenue descending
    client_list.sort(key=lambda x: x['revenue'], reverse=True)
    
    return jsonify(client_list)

@app.route('/api/finance-dashboard', methods=['GET'])
@login_required('admin')
def finance_dashboard():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    
    # Get all active onboarded resources
    c.execute('''SELECT * FROM onboarded_resources WHERE status = 'Active' ORDER BY client_name''')
    resources = [dict(row) for row in c.fetchall()]
    
    total_revenue = sum(r['billing_rate'] or 0 for r in resources)
    total_salary = sum(r['monthly_salary'] or 0 for r in resources)
    total_profit = total_revenue - total_salary
    avg_margin = round((total_profit / total_revenue * 100)) if total_revenue > 0 else 0
    
    # Group by client
    clients = {}
    for r in resources:
        client = r['client_name'] or 'Unknown'
        if client not in clients:
            clients[client] = {'revenue': 0, 'salary': 0, 'count': 0, 'resources': []}
        clients[client]['revenue'] += r['billing_rate'] or 0
        clients[client]['salary'] += r['monthly_salary'] or 0
        clients[client]['count'] += 1
        clients[client]['resources'].append({
            'id': r['id'],
            'name': f"{r.get('first_name', '')} {r.get('last_name', '')}".strip() or 'N/A',
            'salary': r['monthly_salary'] or 0,
            'billing': r['billing_rate'] or 0,
            'margin': round(((r['billing_rate'] or 0) - (r['monthly_salary'] or 0)) / (r['billing_rate'] or 1) * 100)
        })
    
    conn.close()
    
    return jsonify({
        'total_revenue': total_revenue,
        'total_salary': total_salary,
        'total_profit': total_profit,
        'avg_margin': avg_margin,
        'active_resources': len(resources),
        'clients': clients
    })

@app.route('/api/onboarded/<int:resource_id>', methods=['PUT'])
@login_required('manager')
def update_onboarded(resource_id):
    data = request.form.to_dict() if request.form else request.json
    if not data:
        data = request.json
    
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('''UPDATE onboarded_resources SET 
        client_name=?, doj=?, resource_owner=?, work_location=?,
        monthly_salary=?, billing_rate=?, business_model=?,
        requirement_id=?, po_number=?, status=?
        WHERE id=?''',
        (data.get('client_name'), data.get('doj'),
         data.get('resource_owner'), data.get('work_location'),
         float(data.get('monthly_salary', 0)), float(data.get('billing_rate', 0)),
         data.get('business_model', 'C2C'), data.get('requirement_id', ''),
         data.get('po_number', ''), data.get('status', 'Active'), resource_id))
    
    if 'documents' in request.files:
        files = request.files.getlist('documents')
        doc_dir = f'/data/onboarded_docs/{resource_id}'
        os.makedirs(doc_dir, exist_ok=True)
        uploaded_files = []
        for file in files:
            if file.filename:
                filename = secure_filename(f"{datetime.now().timestamp()}_{file.filename}")
                filepath = os.path.join(doc_dir, filename)
                file.save(filepath)
                uploaded_files.append({'filename': filename, 'original_name': file.filename, 'path': filepath})
        if uploaded_files:
            c.execute('SELECT sow_attached FROM onboarded_resources WHERE id = ?', (resource_id,))
            row = c.fetchone()
            existing = json.loads(row[0]) if row and row[0] else []
            existing.extend(uploaded_files)
            c.execute('UPDATE onboarded_resources SET sow_attached = ? WHERE id = ?',
                      (json.dumps(existing), resource_id))
    
    conn.commit()
    conn.close()
    return jsonify({'message': 'Resource updated'})

# ============================================
# INVOICES
# ============================================

@app.route('/api/invoices', methods=['GET'])
@login_required('admin')
def get_invoices():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    c.execute('SELECT * FROM invoices ORDER BY created_at DESC')
    invoices = [dict(row) for row in c.fetchall()]
    conn.close()
    return jsonify(invoices)

@app.route('/api/invoices', methods=['POST'])
@login_required('admin')
def create_invoice():
    data = request.json
    resource_id = data.get('onboarded_resource_id')
    
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    
    # Get resource details
    c.execute('SELECT o.*, c.first_name, c.last_name FROM onboarded_resources o LEFT JOIN candidates c ON o.candidate_id = c.id WHERE o.id = ?', (resource_id,))
    resource = c.fetchone()
    
    if not resource:
        conn.close()
        return jsonify({'error': 'Resource not found'}), 404
    
    client = resource['client_name'] or 'Unknown'
    resource_name = f"{resource['first_name'] or ''} {resource['last_name'] or ''}".strip()
    amount = resource['billing_rate'] or 0
    gst = data.get('gst_percent', 18)
    gst_amount = round(amount * gst / 100, 2)
    total = amount + gst_amount
    
    # Generate invoice number
    c.execute('SELECT COUNT(*) as count FROM invoices')
    count = c.fetchone()['count'] + 1
    invoice_number = f"INV-{str(count).zfill(3)}"
    
    c.execute('''INSERT INTO invoices (invoice_number, onboarded_resource_id, client_name, resource_name, amount, gst_percent, gst_amount, total_amount, invoice_date, due_date, description, status)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)''',
        (invoice_number, resource_id, client, resource_name, amount, gst, gst_amount, total,
         data.get('invoice_date', datetime.now().strftime('%Y-%m-%d')),
         data.get('due_date', ''), data.get('description', ''), 'Draft'))
    
    conn.commit()
    conn.close()
    return jsonify({'message': 'Invoice created', 'invoice_number': invoice_number})

@app.route('/api/invoices/<int:invoice_id>', methods=['PUT'])
@login_required('admin')
def update_invoice(invoice_id):
    data = request.json
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('''UPDATE invoices SET status=?, payment_date=?, payment_amount=?, notes=? WHERE id=?''',
        (data.get('status'), data.get('payment_date'), data.get('payment_amount', 0), data.get('notes', ''), invoice_id))
    conn.commit()
    conn.close()
    return jsonify({'message': 'Invoice updated'})

@app.route('/api/company-settings', methods=['GET'])
@login_required('admin')
def get_company_settings():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('SELECT setting_key, setting_value FROM company_settings')
    settings = {row[0]: row[1] for row in c.fetchall()}
    conn.close()
    return jsonify(settings)

@app.route('/api/company-settings', methods=['POST'])
@login_required('admin')
def save_company_settings():
    data = request.json
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    for key, value in data.items():
        c.execute('UPDATE company_settings SET setting_value = ? WHERE setting_key = ?', (value, key))
    conn.commit()
    conn.close()
    return jsonify({'message': 'Settings saved'})

@app.route('/api/upload-logo', methods=['POST'])
@login_required('admin')
def upload_logo():
    if 'logo' not in request.files:
        return jsonify({'error': 'No file'}), 400
    file = request.files['logo']
    if file.filename == '':
        return jsonify({'error': 'No file'}), 400
    
    filename = secure_filename(f"logo_{datetime.now().timestamp()}.{file.filename.split('.')[-1]}")
    filepath = os.path.join('/data', filename)
    file.save(filepath)
    
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("UPDATE company_settings SET setting_value = ? WHERE setting_key = 'logo_path'", (filepath,))
    conn.commit()
    conn.close()
    
    return jsonify({'message': 'Logo uploaded', 'path': filepath})

@app.route('/api/invoices/<int:invoice_id>/pdf', methods=['GET'])

@app.route('/api/invoices/<int:invoice_id>/pdf', methods=['GET'])
@login_required('admin')
def invoice_pdf(invoice_id):
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    c.execute('SELECT * FROM invoices WHERE id = ?', (invoice_id,))
    invoice = c.fetchone()
    
    if not invoice:
        conn.close()
        return jsonify({'error': 'Invoice not found'}), 404
    
    conn.close()
    
    client_name = invoice['client_name'] or 'Client'
    resource_name = invoice['resource_name'] or 'N/A'
    amount = invoice['amount'] or 0
    gst_amount = invoice['gst_amount'] or 0
    total = invoice['total_amount'] or 0
    
    html = f'''<!DOCTYPE html>
<html><head><meta charset="UTF-8"><title>Invoice {invoice['invoice_number']}</title>
<style>
    body {{ font-family: 'Times New Roman', serif; max-width: 750px; margin: 0 auto; padding: 30px; color: #3D3D3D; background: #FFF; }}
    .header {{ text-align: center; border-bottom: 3px solid #0D9488; padding-bottom: 15px; margin-bottom: 20px; }}
    .header h1 {{ color: #1A237E; font-size: 26px; margin: 0; }}
    .header .address {{ font-size: 12px; color: #555; margin: 5px 0 0 0; line-height: 1.5; }}
    .company-details {{ font-size: 11px; color: #555; margin: 5px 0; }}
    .invoice-title {{ text-align: center; background: #F5F0E8; border: 2px solid #C9A96E; border-radius: 8px; padding: 12px; margin: 15px 0; }}
    .invoice-title h2 {{ color: #0D9488; font-size: 28px; margin: 0; }}
    .info-row {{ display: flex; justify-content: space-between; margin: 15px 0; }}
    .info-box {{ background: #F5F0E8; padding: 12px 16px; border-radius: 6px; border-left: 4px solid #0D9488; flex: 1; margin: 0 5px; }}
    .info-box .label {{ font-size: 11px; color: #666; text-transform: uppercase; }}
    .info-box .value {{ font-size: 14px; color: #1A237E; font-weight: 700; }}
    .bill-to {{ background: #F5F0E8; padding: 15px; border-radius: 6px; margin: 15px 0; border: 1px solid #C9A96E; }}
    .bill-to h3 {{ color: #0D9488; margin: 0 0 8px 0; font-size: 14px; }}
    table {{ width: 100%; border-collapse: collapse; margin: 15px 0; }}
    th {{ background: #0D9488; color: #FFF; padding: 10px; text-align: left; font-size: 13px; }}
    td {{ padding: 8px 10px; border-bottom: 1px solid #E2E0D8; font-size: 13px; }}
    .total-row td {{ font-weight: 700; color: #1A237E; font-size: 16px; border-top: 2px solid #0D9488; }}
    .bank-details {{ background: #F5F0E8; padding: 15px; border-radius: 6px; margin: 15px 0; font-size: 12px; }}
    .bank-details h3 {{ color: #0D9488; margin: 0 0 8px 0; }}
    .footer {{ text-align: center; font-size: 10px; color: #999; margin-top: 25px; }}
</style></head><body>
<div class="header">
    <h1>ShahnaIT LLP</h1>
    <div class="address">Ground Floor, 4-617/113, Mansabdar Layout<br>Near Jamiya Masjid, MB Nagar, Kalaburagi, Karnataka 585105</div>
    <div class="company-details">GSTIN: 29AFPFS9563L1ZS | PAN: AFPFS9563L | TAN: BLRS15532N | LLPIN: ACO-6604</div>
</div>
<div class="invoice-title"><h2>INVOICE</h2></div>
<div class="info-row">
    <div class="info-box"><div class="label">Invoice No</div><div class="value">{invoice['invoice_number']}</div></div>
    <div class="info-box"><div class="label">Date</div><div class="value">{invoice['invoice_date'] or 'N/A'}</div></div>
    <div class="info-box"><div class="label">Due Date</div><div class="value">{invoice['due_date'] or 'N/A'}</div></div>
</div>
<div class="bill-to">
    <h3>INVOICE TO</h3>
    <strong>{client_name}</strong><br>
    GSTIN: ______________________<br>
    Address: __________________________________________
</div>
<table>
    <tr><th>Description</th><th style="text-align:right;">Rate (₹)</th><th style="text-align:right;">Amount (₹)</th></tr>
    <tr><td>{invoice['description'] or 'Professional Services - ' + resource_name}</td><td style="text-align:right;">{amount:,.2f}</td><td style="text-align:right;">{amount:,.2f}</td></tr>
    <tr class="total-row"><td colspan="2" style="text-align:right;"><strong>Subtotal</strong></td><td style="text-align:right;">{amount:,.2f}</td></tr>
    <tr><td colspan="2" style="text-align:right;">GST ({invoice['gst_percent']}%)</td><td style="text-align:right;">{gst_amount:,.2f}</td></tr>
    <tr class="total-row"><td colspan="2" style="text-align:right;"><strong>Grand Total</strong></td><td style="text-align:right;font-size:18px;"><strong>₹ {total:,.2f}</strong></td></tr>
</table>
<div class="bank-details">
    <h3>Bank Details</h3>
    <strong>Account Name:</strong> ShahnaIT LLP<br>
    <strong>Bank:</strong> ______________________<br>
    <strong>Account No:</strong> ______________________<br>
    <strong>IFSC Code:</strong> ______________________<br>
    <strong>Branch:</strong> ______________________
</div>
<div class="footer">This is a computer generated invoice</div>
</body></html>'''
    
    return html

@app.route('/api/export-candidates', methods=['GET'])
@app.route('/api/export-candidates', methods=['GET'])
def export_candidates():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    c.execute('SELECT id, first_name, last_name, email, phone, current_role, match_score, created_at FROM candidates ORDER BY created_at DESC')
    rows = c.fetchall()
    conn.close()
    
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(['ID', 'First Name', 'Last Name', 'Email', 'Phone', 'Current Role', 'Match Score', 'Created Date'])
    for row in rows:
        writer.writerow([row['id'], row['first_name'] or '', row['last_name'] or '',
                         row['email'] or '', row['phone'] or '', row['current_role'] or '',
                         row['match_score'] or 0, row['created_at']])
    output.seek(0)
    return Response(output.getvalue(), mimetype='text/csv', headers={'Content-Disposition': 'attachment; filename=candidates.csv'})
@app.route('/api/batch-analyze', methods=['POST'])
def batch_analyze():
    data = request.json
    jd_text = data.get('jd_text', '')
    
    if not jd_text:
        return jsonify({'error': 'Missing job description'}), 400
    
    # Get all candidates
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    c.execute('SELECT id, first_name, last_name, email, resume_text FROM candidates ORDER BY created_at DESC')
    candidates = [dict(row) for row in c.fetchall()]
    conn.close()
    
    results = []
    for cand in candidates:
        name = (cand.get('first_name', '') + ' ' + cand.get('last_name', '')).strip() or 'Unknown'
        resume_text = cand.get('resume_text', '') or ''
        
        if not resume_text:
            results.append({
                'candidate_id': cand['id'],
                'name': name,
                'email': cand.get('email', ''),
                'match_score': 0,
                'recommendation': 'No resume text'
            })
            continue
        
        # Use the SAME analysis as single match
        result = analyze_resume_locally(resume_text, jd_text)
        
        # Calculate rank position
        rank = 0
        if len(results) > 0:
            # Add current score for comparison
            results.append({
                'candidate_id': cand['id'],
                'name': name,
                'email': cand.get('email', ''),
                'match_score': result.get('match_score', 0),
                'recommendation': result.get('recommendation', 'review'),
                'rank': 0  # Will be updated after sorting
            })
            continue
        
        # For the first candidate
        results.append({
            'candidate_id': cand['id'],
            'name': name,
            'email': cand.get('email', ''),
            'match_score': result.get('match_score', 0),
            'recommendation': result.get('recommendation', 'review'),
            'rank': 0  # Will be updated after sorting
        })
    
    # Sort by match score (highest first)
    results.sort(key=lambda x: x['match_score'], reverse=True)
    
    # Assign ranks
    for idx, result in enumerate(results):
        result['rank'] = idx + 1
        result['total_candidates'] = len(results)
    
    return jsonify(results)
    
# ========== NOTES API ROUTES ==========
@app.route('/api/candidates/<int:candidate_id>/notes', methods=['GET'])
def get_candidate_notes(candidate_id):
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    c.execute('SELECT id, note_text, created_at FROM candidate_notes WHERE candidate_id = ? ORDER BY created_at DESC', (candidate_id,))
    notes = [dict(row) for row in c.fetchall()]
    conn.close()
    return jsonify(notes)

@app.route('/api/candidates/<int:candidate_id>/notes', methods=['POST'])
def add_candidate_note(candidate_id):
    data = request.json
    note_text = data.get('note_text', '')
    if not note_text:
        return jsonify({'error': 'Note text required'}), 400
    
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('INSERT INTO candidate_notes (candidate_id, note_text) VALUES (?, ?)', (candidate_id, note_text))
    conn.commit()
    conn.close()
    return jsonify({'message': 'Note added'})

@app.route('/api/candidates/notes/<int:note_id>', methods=['DELETE'])
def delete_candidate_note(note_id):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('DELETE FROM candidate_notes WHERE id = ?', (note_id,))
    conn.commit()
    conn.close()
    return jsonify({'message': 'Note deleted'})

# ========== STATUS API ==========
@app.route('/api/candidates/<int:candidate_id>/status', methods=['PUT'])
def update_candidate_status(candidate_id):
    data = request.json
    new_status = data.get('employment_status', '')
    
    if not new_status:
        return jsonify({'error': 'Status required'}), 400
    
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('UPDATE candidates SET employment_status = ? WHERE id = ?', (new_status, candidate_id))
    conn.commit()
    conn.close()
    
    return jsonify({'message': 'Status updated', 'status': new_status})
# ========== PDF EXPORT ==========
# ============================================
# PDF EXPORT - CANDIDATE PROFILE
# ============================================
@app.route('/api/candidates/<int:candidate_id>/export-pdf')
def export_candidate_pdf(candidate_id):
    """Export candidate profile as PDF with full details"""
    try:
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        candidate = conn.execute('SELECT * FROM candidates WHERE id = ?', (candidate_id,)).fetchone()
        
        if not candidate:
            conn.close()
            return jsonify({'error': 'Candidate not found'}), 404
        
        candidate = dict(candidate)
        
        # Parse JSON fields
        skills = []
        try:
            raw_skills = candidate.get('core_skills', '[]')
            skills = json.loads(raw_skills) if isinstance(raw_skills, str) else raw_skills
        except: pass
        
        work_exp = []
        try:
            raw_work = candidate.get('work_experience', '[]')
            work_exp = json.loads(raw_work) if isinstance(raw_work, str) else raw_work
        except: pass
        
        notes = conn.execute(
            'SELECT note_text, created_at FROM candidate_notes WHERE candidate_id = ? ORDER BY created_at DESC',
            (candidate_id,)
        ).fetchall()
        conn.close()
        
        # Build full name
        full_name = f"{candidate.get('first_name', '')} {candidate.get('last_name', '')}".strip() or 'Unknown'
        candidate_id_display = f"SIT-C-{candidate['id']:03d}"
        
        # Create PDF
        buffer = io.BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=letter,
                               rightMargin=50, leftMargin=50,
                               topMargin=50, bottomMargin=50)
        
        styles = getSampleStyleSheet()
        title_style = ParagraphStyle('Title', parent=styles['Heading1'], fontSize=22, textColor=colors.HexColor('#1B2A4A'), spaceAfter=20, alignment=TA_CENTER)
        heading_style = ParagraphStyle('Heading', parent=styles['Heading2'], fontSize=14, textColor=colors.HexColor('#1B2A4A'), spaceAfter=10, spaceBefore=18)
        normal_style = styles['Normal']
        normal_style.fontSize = 10
        normal_style.fontName = 'Times-Roman'
        
        story = []
        
        # Header
        story.append(Paragraph(f"Candidate Profile", title_style))
        story.append(Paragraph(f"<b>{full_name}</b> | {candidate_id_display}", normal_style))
        story.append(Spacer(1, 15))
        
        # Basic Info
        story.append(Paragraph("Basic Information", heading_style))
        info_data = [
            ('Name', full_name),
            ('Candidate ID', candidate_id_display),
            ('Email', candidate.get('email', 'N/A')),
            ('Phone', candidate.get('phone', 'N/A')),
            ('Designation', candidate.get('designation') or candidate.get('current_role', 'N/A')),
            ('LinkedIn', candidate.get('linkedin', 'N/A')),
            ('Location', candidate.get('location') or candidate.get('address', 'N/A')),
            ('Experience', candidate.get('years_of_experience', 'N/A')),
            ('Current CTC', candidate.get('current_ctc', 'N/A')),
            ('Expected CTC', candidate.get('expected_ctc', 'N/A')),
            ('Stage', candidate.get('stage', 'new')),
            ('Status', candidate.get('employment_status', 'N/A')),
        ]
        for label, value in info_data:
            story.append(Paragraph(f"<b>{label}:</b> {value}", normal_style))
        story.append(Spacer(1, 10))
        
        # Skills
        story.append(Paragraph("Skills", heading_style))
        if skills:
            skill_text = ', '.join([s.get('skill', s) if isinstance(s, dict) else str(s) for s in skills])
            story.append(Paragraph(skill_text, normal_style))
        else:
            story.append(Paragraph("No skills listed", normal_style))
        story.append(Spacer(1, 10))
        
        # Match Score
        match_score = candidate.get('match_score', 0) or 0
        story.append(Paragraph("Match Score", heading_style))
        score_color = '#4caf50' if match_score >= 70 else '#ff9800' if match_score >= 40 else '#f44336'
        story.append(Paragraph(f'<font color="{score_color}" size="16"><b>{match_score}%</b></font>', normal_style))
        story.append(Spacer(1, 10))
        
        # Analysis Summary
        analysis = candidate.get('analysis_summary', '') or candidate.get('detailed_analysis', '')
        if analysis:
            story.append(Paragraph("AI Analysis", heading_style))
            story.append(Paragraph(str(analysis)[:1000], normal_style))
        story.append(Spacer(1, 10))
        
        # Notes
        story.append(Paragraph("Notes", heading_style))
        if notes:
            for note in notes:
                story.append(Paragraph(f"• {note['note_text'][:200]}", normal_style))
        else:
            story.append(Paragraph("No notes", normal_style))
        
        # Footer
        story.append(Spacer(1, 25))
        story.append(Paragraph(f"<i>Generated by ShahnaIT Scout | {datetime.now().strftime('%Y-%m-%d %H:%M')}</i>", normal_style))
        
        doc.build(story)
        buffer.seek(0)
        
        return send_file(buffer, as_attachment=True, download_name=f"{full_name}_profile.pdf", mimetype='application/pdf')
        
    except Exception as e:
        return jsonify({'error': f'PDF export failed: {str(e)}'}), 500
# ========== DASHBOARD API ==========
@app.route('/api/dashboard-data', methods=['GET'])
def get_dashboard_data():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    
    # Get all candidates
    c.execute('SELECT * FROM candidates ORDER BY created_at DESC')
    candidates = [dict(row) for row in c.fetchall()]
    
    # Total candidates
    total = len(candidates)
    
    # Match distribution
    match_distribution = {
        '0-20': 0,
        '21-40': 0,
        '41-60': 0,
        '61-80': 0,
        '81-100': 0
    }
    
    pipeline = {
    'new': 0,
    'proposed': 0,
    'screening': 0,
    'technical_l1': 0,
    'technical_l2': 0,
    'technical_l3': 0,
    'rejected': 0,
    'shortlisted': 0,
    'offer_letter_shared': 0,
    'onboarded': 0
}
    
    matched = 0
    hired = 0
    rejected = 0
    skills_count = {}
    trend_data = {}
    
    for candidate in candidates:
        # Match distribution
        score = candidate.get('match_score', 0)
        if score >= 80:
            match_distribution['81-100'] += 1
        elif score >= 60:
            match_distribution['61-80'] += 1
        elif score >= 40:
            match_distribution['41-60'] += 1
        elif score >= 20:
            match_distribution['21-40'] += 1
        else:
            match_distribution['0-20'] += 1
        
        # Pipeline
        # Pipeline
        status = candidate.get('stage', candidate.get('employment_status', 'new'))
        if status in pipeline:
            pipeline[status] += 1
        
        # Count matched (70%+)
        if score >= 70:
            matched += 1
        
        # Count hired/rejected
        if status == 'hired':
            hired += 1
        elif status == 'rejected':
            rejected += 1
        
        # Skills handle both string and object formats
        try:
            raw_skills = candidate.get('core_skills', '[]')
            skills = json.loads(raw_skills) if isinstance(raw_skills, str) else raw_skills
        except:
            skills = []
        
        if isinstance(skills, list):
            for skill in skills:
                if isinstance(skill, dict):
                    skill_name = skill.get('skill', '').strip()
                else:
                    skill_name = str(skill).strip()
                if skill_name:
                    skills_count[skill_name] = skills_count.get(skill_name, 0) + 1
        
        # Trend (by date)
        date = candidate.get('created_at', '')[:10]  # YYYY-MM-DD
        if date:
            trend_data[date] = trend_data.get(date, 0) + 1
    
    # Sort skills by count
    sorted_skills = sorted([{'skill': k, 'count': v} for k, v in skills_count.items()], key=lambda x: x['count'], reverse=True)
    
    # Sort trend dates
    sorted_dates = sorted(trend_data.keys())
    trend_labels = sorted_dates
    trend_values = [trend_data[d] for d in sorted_dates]
    
    conn.close()
    
    return jsonify({
        'total': total,
        'matched': matched,
        'hired': hired,
        'rejected': rejected,
        'matchDistribution': match_distribution,
        'pipeline': pipeline,
        'skills': sorted_skills,
        'trend': {
            'labels': trend_labels,
            'values': trend_values
        }
    })
@app.route('/api/test-pdf', methods=['GET'])
def test_pdf():
    try:
        import reportlab
        from reportlab.pdfgen import canvas
        import io
        return jsonify({
            'status': 'ok',
            'reportlab_version': reportlab.__version__,
            'canvas_available': 'yes'
        })
    except ImportError as e:
        return jsonify({'status': 'error', 'message': f'Import error: {str(e)}'}), 500
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500
@app.route('/api/candidates/<int:candidate_id>/download-resume')
def download_resume(candidate_id):
    """Download the original resume file for a candidate"""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('SELECT resume_file_path, resume_original_filename FROM candidates WHERE id = ?', (candidate_id,))
    row = c.fetchone()
    conn.close()
    
    file_path = safe_stored_path(row[0]) if row else None
    if not file_path:
        return jsonify({'error': 'Resume not found'}), 404
        
    original_filename = row[1] or 'resume.pdf'
    
    # Determine mimetype based on file extension
    if original_filename.endswith('.pdf'):
        mimetype = 'application/pdf'
    elif original_filename.endswith('.docx'):
        mimetype = 'application/vnd.openxmlformats-officedocument.wordprocessingml.document'
    elif original_filename.endswith('.doc'):
        mimetype = 'application/msword'
    else:
        mimetype = 'application/octet-stream'
    
    return send_file(
        file_path,
        as_attachment=True,
        download_name=original_filename,
        mimetype=mimetype
    )


@app.route('/api/candidates/<int:candidate_id>/view-resume')
def view_resume(candidate_id):
    """View the original resume file in the browser (PDF/DOCX)"""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('SELECT resume_file_path, resume_original_filename FROM candidates WHERE id = ?', (candidate_id,))
    row = c.fetchone()
    conn.close()
    
    file_path = safe_stored_path(row[0]) if row else None
    if not file_path:
        return jsonify({'error': 'Resume not found'}), 404
    original_filename = row[1] or 'resume.pdf'
    
    # Determine mimetype based on file extension
    if original_filename.endswith('.pdf'):
        mimetype = 'application/pdf'
    elif original_filename.endswith('.docx'):
        mimetype = 'application/vnd.openxmlformats-officedocument.wordprocessingml.document'
    elif original_filename.endswith('.doc'):
        mimetype = 'application/msword'
    else:
        mimetype = 'application/octet-stream'
    
    # Display in browser instead of downloading
    response = send_file(
        file_path,
        as_attachment=False,
        download_name=original_filename,
        mimetype=mimetype
    )
    
    # Force inline display for PDFs
    if original_filename.endswith('.pdf'):
        response.headers['Content-Disposition'] = f'inline; filename="{original_filename}"'
    
    return response

if __name__ == '__main__':
    app.run(host=os.environ.get('HOST', '127.0.0.1'), port=int(os.environ.get('PORT', 5000)), debug=False)


import threading
import time as time_module

def auto_daily_digest():
    while True:
        time_module.sleep(1800)  # check every 30 minutes
        now = datetime.now()
                # 9 AM IST = 3:30 AM UTC
        if now.hour == 3 and now.minute >= 30 and now.minute < 60:
            today = now.strftime('%Y-%m-%d')
            
            conn = sqlite3.connect(DB_PATH)
            conn.row_factory = sqlite3.Row
            c = conn.cursor()
            
            # Today's interviews
            c.execute('SELECT * FROM interviews WHERE interview_date = ? ORDER BY interview_time', (today,))
            interviews = [dict(row) for row in c.fetchall()]
            
            # Active requirements
            c.execute('SELECT id, title, company, requirement_id, working_mode, years_of_experience FROM jobs WHERE is_active = 1 ORDER BY created_at DESC')
            active_jobs = [dict(row) for row in c.fetchall()]
            
            # Yesterday's verdicts
            yesterday = (now - timedelta(days=1)).strftime('%Y-%m-%d')
            c.execute("SELECT * FROM interviews WHERE interview_date = ? AND verdict != 'Scheduled'", (yesterday,))
            yesterday_verdicts = [dict(row) for row in c.fetchall()]
            
            conn.close()
            
            message = f"📅 <b>SHAHNAIT SCOUT - DAILY UPDATE</b>\n"
            message += f"📆 {now.strftime('%A, %d %B %Y')}\n"
            message += "━━━━━━━━━━━━━━━━━━\n\n"
            
            # Interviews today
            if interviews:
                message += f"📋 <b>INTERVIEWS TODAY ({len(interviews)})</b>\n\n"
                for i in interviews:
                    message += f"🕐 <b>{i['interview_time'] or 'TBD'}</b>\n"
                    message += f"   👤 Candidate: {i['candidate_name']}\n"
                    message += f"   🎯 Round: {i['round']}\n"
                    message += f"   🏢 Client: {i['client_name'] or 'N/A'}\n"
                    message += f"   📋 Req: {i['requirement_id'] or 'N/A'}\n"
                    message += f"   👤 Owner: {i['resource_owner'] or 'N/A'}\n"
                    message += f"   📞 POC: {i['client_poc'] or 'N/A'}\n\n"
            else:
                message += "📋 <b>INTERVIEWS TODAY:</b>\n✅ No interviews scheduled\n\n"
            
            message += "━━━━━━━━━━━━━━━━━━\n\n"
            
            # Active requirements
            if active_jobs:
                message += f"📌 <b>ACTIVE REQUIREMENTS ({len(active_jobs)})</b>\n\n"
                for j in active_jobs[:10]:
                    req_id = j['requirement_id'] or f"SIT-R-{str(j['id']).zfill(3)}"
                    message += f"🔹 {j['title']} ({req_id})\n"
                    message += f"   🏢 {j['company'] or 'N/A'} | 📍 {j['working_mode'] or 'N/A'} | ⏳ {j['years_of_experience'] or 0}+ yrs\n\n"
                if len(active_jobs) > 10:
                    message += f"   ...and {len(active_jobs) - 10} more\n\n"
            else:
                message += "📌 <b>ACTIVE REQUIREMENTS:</b>\nNone\n\n"
            
            # Yesterday's verdicts
            if yesterday_verdicts:
                message += "━━━━━━━━━━━━━━━━━━\n\n"
                message += f"✅ <b>YESTERDAY'S VERDICTS ({len(yesterday_verdicts)})</b>\n\n"
                for v in yesterday_verdicts:
                    verdict_emoji = {'Selected': '✅', 'Rejected': '❌', 'Hold': '⏸️', 'No Show': '🚫', 'Rescheduled': '🔄'}.get(v['verdict'], '📋')
                    message += f"{verdict_emoji} {v['candidate_name']} - {v['round']} - {v['verdict']}\n"
            else:
                message += "━━━━━━━━━━━━━━━━━━\n\n"
                message += "✅ <b>YESTERDAY'S VERDICTS:</b>\nNone\n"
            
            message += "\n🔔 <i>Auto-generated by ShahnaIT Scout</i>"
            
            send_telegram_message(message)
            time_module.sleep(1800)

digest_thread = threading.Thread(target=auto_daily_digest, daemon=True)
digest_thread.start()
