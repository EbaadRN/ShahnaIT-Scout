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
from datetime import datetime
import traceback

# ============================================
# FLASK & WEB FRAMEWORK
# ============================================
from flask import Flask, render_template_string, request, jsonify, send_file, Response
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
            server.send_message(msg)
        return True
    except Exception as e:
        print(f"Email error: {e}")
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
app.secret_key = os.environ.get('SECRET_KEY', 'shahnait-scout-secret-key-change-in-production')
CORS(app, supports_credentials=True)

# ============================================
# AUTHENTICATION
# ============================================
import hashlib
from functools import wraps
from flask import session, redirect, url_for

def login_required(role=None):
    """Decorator to require login and optional role"""
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if 'user_id' not in session:
                return jsonify({'error': 'Unauthorized', 'redirect': '/login'}), 401
            if role and session.get('role') != role and session.get('role') != 'admin':
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

# Configuration
app.config['MAX_CONTENT_LENGTH'] = 50 * 1024 * 1024
app.config['UPLOAD_FOLDER'] = '/data/tmp'
app.config['DOCUMENTS_FOLDER'] = '/data/candidate_docs'
app.config['JOB_DOCUMENTS_FOLDER'] = '/data/job_docs'

os.makedirs('/data/attachments', exist_ok=True)
os.makedirs('/data/tmp', exist_ok=True)

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
            result = response.json()['choices'][0]['message']['content']
            result = result.strip()
            if result.startswith('```json'):
                result = result[7:]
            if result.startswith('```'):
                result = result[3:]
            if result.endswith('```'):
                result = result[:-3]
            return result
        return None
    except Exception as e:
        print(f"Groq error: {e}")
        return None

def parse_resume_with_groq(resume_text):
    """Parse resume text into structured candidate fields using AI"""
    prompt = f"""You are an expert resume parser. Extract ALL fields from this resume precisely. Return ONLY valid JSON, no explanations.

{{
    "first_name": "First name",
    "last_name": "Last name", 
    "middle_name": "",
    "phone": "phone number or empty",
    "email": "email or empty",
    "address": "full address or empty",
    "linkedin": "LinkedIn URL or empty",
    "current_role": "Current job title",
    "designation": "Most recent designation",
    "location": "City, State",
    "current_ctc": "Current CTC if mentioned else empty",
    "expected_ctc": "Expected CTC if mentioned else empty",
    "years_of_experience": number,
    "notice_period_days": number (30/60/90, 0 if not mentioned),
    "employment_status": "Employed / Unemployed / Not Specified",
    "core_skills": ["skill1", "skill2"],
    "education": "Highest education",
    "certifications": ["cert1", "cert2"],
    "work_experience": [
        {{"company": "name", "role": "title", "duration": "Jan 2020 - Present", "description": "key work"}}
    ],
    "summary": "2-line professional summary"
}}

RESUME:
{resume_text[:5000]}
"""
    response = call_groq_api(prompt, max_tokens=2500)
    if response:
        try:
            return json.loads(response)
        except:
            return None
    return None

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
    first_name, last_name, middle_name = extract_name_from_text(text)
    email = extract_email(text)
    phone = extract_phone(text)
    
    common_skills = [
        'Python', 'Java', 'JavaScript', 'React', 'Angular', 'Node.js', 'SQL', 'AWS', 
        'Docker', 'Kubernetes', 'Git', 'Azure', 'Salesforce', 'Power Apps', 'Entra ID'
    ]
    found_skills = []
    for skill in common_skills:
        if skill.lower() in text.lower():
            years = extract_years_from_text(text, skill)
            found_skills.append({"skill": skill, "years_of_experience": years})
    
    return {
        'first_name': first_name,
        'last_name': last_name,
        'middle_name': middle_name,
        'phone': phone,
        'email': email,
        'address': "",
        'linkedin': "",
        'current_role': "",
        'current_ctc': "",
        'expected_ctc': "",
        'employment_status': "working",
        'notice_period_days': 0,
        'work_experience': [],
        'certifications': [],
        'core_skills': found_skills[:5],
        'education': "",
        'resume_text': text[:3000],
        'ai_used': False
    }

def save_candidate_to_db(candidate_data):
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
         str(candidate_data.get('permanent_file_path') or ''),
         str(candidate_data.get('original_filename') or ''),
         str(candidate_data.get('proposed_client') or ''),
         str(candidate_data.get('proposed_requirement') or ''),
         str(candidate_data.get('stage', 'new')),
         attachments,
         str(candidate_data.get('analysis_summary') or ''),
         str(candidate_data.get('matched_jd') or ''),
         str(candidate_data.get('uploaded_by_name', 'ShahnaIT HR'))))
    
    candidate_id = c.lastrowid
    conn.commit()
    conn.close()
    return candidate_id
    # ============ ATTACHMENT UPLOAD ============
UPLOAD_FOLDER = '/data/attachments'
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

@app.route('/api/candidates/<int:candidate_id>/attachments', methods=['POST'])
def upload_candidate_attachment(candidate_id):
    """Upload attachment for a candidate"""
    try:
        if 'file' not in request.files:
            return jsonify({"success": False, "error": "No file provided"}), 400
        
        file = request.files['file']
        if file.filename == '':
            return jsonify({"success": False, "error": "No file selected"}), 400
        
        # Create candidate folder
        candidate_folder = os.path.join(UPLOAD_FOLDER, f"candidate_{candidate_id}")
        if not os.path.exists(candidate_folder):
            os.makedirs(candidate_folder)
        
        # Secure filename and save
        filename = secure_filename(file.filename)
        # Add timestamp to avoid duplicates
        name, ext = os.path.splitext(filename)
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        unique_filename = f"{name}_{timestamp}{ext}"
        file_path = os.path.join(candidate_folder, unique_filename)
        file.save(file_path)
        
        # Get existing attachments
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        c = conn.cursor()
        c.execute('SELECT attachments FROM candidates WHERE id = ?', (candidate_id,))
        row = c.fetchone()
        
        attachments = []
        if row and row['attachments']:
            try:
                attachments = json.loads(row['attachments']) if isinstance(row['attachments'], str) else row['attachments']
            except:
                attachments = []
        
        # Add new attachment
        attachments.append({
            'filename': unique_filename,
            'original_name': filename,
            'path': file_path,
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
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

@app.route('/api/candidates/<int:candidate_id>/attachments/<filename>', methods=['GET'])
def download_attachment(candidate_id, filename):
    """Download or view a candidate attachment"""
    candidate_folder = os.path.join(UPLOAD_FOLDER, f"candidate_{candidate_id}")
    file_path = os.path.join(candidate_folder, filename)
    
    if os.path.exists(file_path):
        # If ?view=1 is in URL, open in browser instead of downloading
        view_mode = request.args.get('view', '0')
        if view_mode == '1':
            return send_file(file_path)
        return send_file(file_path, as_attachment=True, download_name=filename)
    return jsonify({"error": "File not found"}), 404

@app.route('/api/candidates/<int:candidate_id>/attachments/<filename>', methods=['DELETE'])
def delete_attachment(candidate_id, filename):
    """Delete a candidate attachment"""
    try:
        candidate_folder = os.path.join(UPLOAD_FOLDER, f"candidate_{candidate_id}")
        file_path = os.path.join(candidate_folder, filename)
        
        # Delete file
        if os.path.exists(file_path):
            os.remove(file_path)
        
        # Update database
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        c.execute('SELECT attachments FROM candidates WHERE id = ?', (candidate_id,))
        row = c.fetchone()
        
        if row and row[0]:
            attachments = json.loads(row[0]) if isinstance(row[0], str) else row[0]
            attachments = [a for a in attachments if a.get('filename') != filename]
            c.execute('UPDATE candidates SET attachments = ? WHERE id = ?', 
                      (json.dumps(attachments), candidate_id))
        
        conn.commit()
        conn.close()
        
        return jsonify({"success": True, "message": "File deleted"})
    except Exception as e:
       return jsonify({"success": False, "error": str(e)}), 500

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
    data = request.json
    email = data.get('email', '').strip().lower()
    password = data.get('password', '')
    
    if not email or not password:
        return jsonify({'error': 'Email and password required'}), 400
    
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    c.execute('SELECT * FROM users WHERE email = ? AND is_active = 1', (email,))
    user = c.fetchone()
    conn.close()
    
    if not user:
        return jsonify({'error': 'Invalid email or password'}), 401
    
    password_hash = hashlib.sha256(password.encode()).hexdigest()
    if password_hash != user['password_hash']:
        return jsonify({'error': 'Invalid email or password'}), 401
    
    session['user_id'] = user['id']
    session['role'] = user['role']
    session['user_name'] = user['full_name']
    
    # Update last login
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('UPDATE users SET last_login = CURRENT_TIMESTAMP WHERE id = ?', (user['id'],))
    conn.commit()
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
    data = request.json
    email = data.get('email', '').strip().lower()
    password = data.get('password', '')
    full_name = data.get('full_name', '')
    role = data.get('role', 'recruiter')
    
    if not email or not password:
        return jsonify({'error': 'Email and password required'}), 400
    
    if role not in ['admin', 'manager', 'recruiter']:
        return jsonify({'error': 'Invalid role'}), 400
    
    password_hash = hashlib.sha256(password.encode()).hexdigest()
    
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
    data = request.json
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    
    if 'role' in data:
        c.execute('UPDATE users SET role = ? WHERE id = ?', (data['role'], user_id))
    if 'is_active' in data:
        c.execute('UPDATE users SET is_active = ? WHERE id = ?', (data['is_active'], user_id))
    if 'full_name' in data:
        c.execute('UPDATE users SET full_name = ? WHERE id = ?', (data['full_name'], user_id))
    if 'password' in data:
        password_hash = hashlib.sha256(data['password'].encode()).hexdigest()
        c.execute('UPDATE users SET password_hash = ? WHERE id = ?', (password_hash, user_id))
    
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
HTML_TEMPLATE = '''
<!DOCTYPE html>
<html>
<head>
    <title>ShahnaIT Scout</title>
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
    <!-- Font Awesome Icons -->
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css">
   <style>
    /* ============================================
       WHITE & NAVY BLUE THEME - SHAHNAIT SCOUT
       High Visibility - Clear Text - Prominent Boxes
       ============================================ */
    
    :root {
        /* Navy Blue Primary Palette */
        --color-primary: #1B2A4A;
        --color-primary-dark: #0F1D33;
        --color-primary-light: #2C4270;
        --color-primary-bg: #F0F4FA;
        --color-accent: #3B5998;
        --color-accent-light: #E8EDF5;
        
        /* Surface Colors */
        --color-white: #FFFFFF;
        --color-off-white: #F5F7FA;
        --color-card-bg: #FFFFFF;
        
        /* Text Colors - High Contrast */
        --color-text-primary: #0F1D33;
        --color-text-secondary: #2C3E5A;
        --color-text-tertiary: #5A6F8A;
        --color-text-on-dark: #FFFFFF;
        --color-text-on-primary: #FFFFFF;
        
        /* Border Colors - Prominent */
        --color-border: #D0D8E4;
        --color-border-light: #E2E8F0;
        --color-border-strong: #A0B0C8;
        
        /* Status Colors */
        --color-success: #0D7B4A;
        --color-success-bg: #E6F4ED;
        --color-warning: #B85C00;
        --color-warning-bg: #FFF4E8;
        --color-error: #C42020;
        --color-error-bg: #FDEAEA;
        --color-info: #1B5F8C;
        --color-info-bg: #E8F2FA;
        
        /* Shadows - More Prominent */
        --shadow-sm: 0 1px 3px rgba(15, 29, 51, 0.08);
        --shadow-md: 0 4px 12px rgba(15, 29, 51, 0.1);
        --shadow-lg: 0 8px 24px rgba(15, 29, 51, 0.12);
        --shadow-xl: 0 12px 36px rgba(15, 29, 51, 0.15);
        
        /* Spacing */
        --radius-sm: 6px;
        --radius-md: 10px;
        --radius-lg: 14px;
        --radius-xl: 18px;
    }

    /* ===== BASE ===== */
    body {
        font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
        background: #F2F5F9;
        color: var(--color-text-primary);
        margin: 0;
        padding: 20px;
        line-height: 1.6;
        font-size: 15px;
        -webkit-font-smoothing: antialiased;
        -moz-osx-font-smoothing: grayscale;
    }

    /* ===== HEADER - Navy Blue ===== */
    .header {
        background: linear-gradient(135deg, var(--color-primary-dark) 0%, var(--color-primary) 40%, var(--color-accent) 100%);
        color: var(--color-text-on-dark);
        padding: 28px 32px;
        border-radius: var(--radius-xl);
        margin-bottom: 24px;
        box-shadow: var(--shadow-lg);
        border: 2px solid var(--color-primary-dark);
    }
    .header h1 { 
        margin: 0; 
        font-size: 30px; 
        font-weight: 800; 
        letter-spacing: -0.5px;
        color: #FFFFFF;
        text-shadow: 0 1px 2px rgba(0,0,0,0.1);
    }
    .header p { 
        margin: 6px 0 0 0; 
        opacity: 0.95; 
        font-size: 15px; 
        font-weight: 500;
        color: #D0DAEC;
    }

    /* ===== BUTTONS ===== */
    button, .btn {
        background: var(--color-primary);
        color: var(--color-text-on-primary);
        border: 2px solid var(--color-primary-dark);
        padding: 10px 22px;
        margin: 5px;
        cursor: pointer;
        border-radius: var(--radius-md);
        font-weight: 700;
        font-size: 14px;
        transition: all 0.2s ease;
        letter-spacing: 0.2px;
    }
    button:hover, .btn:hover {
        background: var(--color-primary-dark);
        border-color: var(--color-primary-dark);
        transform: translateY(-2px);
        box-shadow: var(--shadow-md);
    }
    button:active, .btn:active {
        transform: translateY(0);
        box-shadow: var(--shadow-sm);
    }
    
    .btn-primary { 
        background: var(--color-primary); 
        color: #FFFFFF; 
        border-color: var(--color-primary-dark);
        font-weight: 700;
    }
    .btn-primary:hover { 
        background: var(--color-primary-dark);
        border-color: #0A1525;
    }
    
    .btn-secondary {
        background: var(--color-white);
        color: var(--color-text-primary);
        border: 2px solid var(--color-border-strong);
        font-weight: 600;
    }
    .btn-secondary:hover { 
        background: var(--color-off-white); 
        border-color: var(--color-primary);
        color: var(--color-primary);
    }
    
    .btn-danger { 
        background: var(--color-error); 
        color: #FFFFFF; 
        border-color: #A01A1A;
        font-weight: 700;
    }
    .btn-danger:hover { 
        background: #A01A1A; 
        border-color: #801515;
    }
    
    .btn-edit {
        background: var(--color-accent-light);
        color: var(--color-primary);
        border: 2px solid var(--color-border);
        font-weight: 600;
    }
    .btn-edit:hover { 
        background: var(--color-primary); 
        color: #FFFFFF;
        border-color: var(--color-primary-dark);
    }

    /* ===== TABS ===== */
    .tab-btn {
        background: transparent;
        color: var(--color-text-secondary);
        border: none;
        padding: 13px 22px;
        margin: 0;
        cursor: pointer;
        font-size: 14px;
        font-weight: 600;
        border-left: 4px solid transparent;
        transition: all 0.2s ease;
        width: 100%;
        text-align: left;
        letter-spacing: 0.2px;
    }
    .tab-btn:hover {
        background: var(--color-accent-light);
        color: var(--color-text-primary);
    }
    .tab-btn.active {
        background: var(--color-accent-light);
        border-left: 4px solid var(--color-primary);
        color: var(--color-primary);
        font-weight: 700;
    }

    /* ===== CARDS - Prominent Borders ===== */
    .card {
        background: var(--color-white);
        padding: 20px 22px;
        margin: 12px 0;
        border-radius: var(--radius-lg);
        border: 2px solid var(--color-border);
        border-left: 5px solid var(--color-primary);
        cursor: pointer;
        transition: all 0.25s ease;
        box-shadow: var(--shadow-sm);
    }
    .card:hover {
        transform: translateY(-3px);
        box-shadow: var(--shadow-lg);
        border-color: var(--color-primary);
        border-left-width: 5px;
    }
    .card.no-click { 
        cursor: default; 
        border-left: 5px solid var(--color-border);
    }
    .card.no-click:hover { 
        transform: none; 
        box-shadow: var(--shadow-sm); 
        border-color: var(--color-border);
    }

    /* ===== CANDIDATE CARDS - Prominent ===== */
    .candidate-card {
        background: var(--color-white);
        border-radius: var(--radius-lg);
        box-shadow: var(--shadow-md);
        margin-bottom: 18px;
        overflow: hidden;
        transition: all 0.3s ease;
        border: 2px solid var(--color-border);
        cursor: pointer;
    }
    .candidate-card:hover {
        box-shadow: var(--shadow-xl);
        transform: translateY(-4px);
        border-color: var(--color-primary);
    }
    
    .card-header {
        padding: 18px 22px;
        display: flex;
        align-items: center;
        gap: 15px;
        background: var(--color-off-white);
        border-bottom: 2px solid var(--color-border);
    }
    
    .candidate-avatar {
        position: relative;
        width: 54px;
        height: 54px;
        border-radius: 50%;
        background: linear-gradient(135deg, var(--color-primary) 0%, var(--color-accent) 100%);
        display: flex;
        align-items: center;
        justify-content: center;
        color: #FFFFFF;
        font-weight: 800;
        font-size: 22px;
        flex-shrink: 0;
        border: 3px solid var(--color-primary-dark);
        box-shadow: var(--shadow-sm);
    }
    
    .avatar-text { text-transform: uppercase; }
    
    .score-badge {
        position: absolute;
        bottom: -5px;
        right: -5px;
        font-size: 11px;
        font-weight: 800;
        color: #FFFFFF;
        padding: 3px 9px;
        border-radius: 20px;
        min-width: 32px;
        text-align: center;
        border: 2px solid #FFFFFF;
        box-shadow: var(--shadow-sm);
    }
    
    .candidate-title { flex: 1; }
    .candidate-name {
        margin: 0;
        font-size: 17px;
        font-weight: 700;
        color: var(--color-text-primary);
        letter-spacing: -0.3px;
    }
    .candidate-email {
        font-size: 13px;
        color: var(--color-text-secondary);
        display: block;
        margin-top: 3px;
        font-weight: 500;
    }
    
    .btn-expand {
        background: none;
        border: 2px solid var(--color-border);
        color: var(--color-text-secondary);
        cursor: pointer;
        padding: 8px;
        font-size: 16px;
        transition: all 0.3s ease;
        border-radius: 50%;
        width: 36px;
        height: 36px;
        display: flex;
        align-items: center;
        justify-content: center;
    }
    .btn-expand:hover { 
        background: var(--color-primary); 
        color: #FFFFFF;
        border-color: var(--color-primary);
    }
    .btn-expand.expanded { 
        transform: rotate(180deg); 
        background: var(--color-accent-light);
        border-color: var(--color-primary);
        color: var(--color-primary);
    }
    
    .card-body { 
        padding: 0 22px 18px 22px; 
        background: var(--color-white);
    }
    
    .candidate-skills {
        display: flex;
        flex-wrap: wrap;
        gap: 7px;
        margin: 14px 0 12px 0;
    }
    .skill-tag {
        background: var(--color-accent-light);
        color: var(--color-primary);
        padding: 5px 14px;
        border-radius: 20px;
        font-size: 12px;
        font-weight: 700;
        display: inline-block;
        border: 1.5px solid var(--color-border);
        letter-spacing: 0.2px;
    }
    .skill-tag.more {
        background: var(--color-border-light);
        color: var(--color-text-secondary);
        font-weight: 700;
        border-color: var(--color-border);
    }
    .no-skills { 
        color: var(--color-text-tertiary); 
        font-size: 13px; 
        font-style: italic; 
        font-weight: 500;
    }
    
    .candidate-meta {
        display: flex;
        flex-wrap: wrap;
        gap: 14px;
        align-items: center;
        margin-bottom: 14px;
    }
    .meta-item {
        font-size: 13px;
        color: var(--color-text-secondary);
        display: flex;
        align-items: center;
        gap: 5px;
        font-weight: 500;
    }
    
    /* Status Badges - High Visibility */
    .status-badge {
        padding: 5px 14px;
        border-radius: 20px;
        font-size: 12px;
        font-weight: 700;
        border: 2px solid transparent;
        letter-spacing: 0.3px;
    }
    .status-new { background: #E8F2FA; color: #1B5F8C; border-color: #B8D4F0; }
    .status-screening { background: #FFF4E8; color: #B85C00; border-color: #F0C898; }
    .status-interview { background: #FDEAEA; color: #C42020; border-color: #F0B8B8; }
    .status-offer { background: #E6F4ED; color: #0D7B4A; border-color: #B8E0CC; }
    .status-hired { background: #E6F4ED; color: #0A5C35; border-color: #90D4B0; font-weight: 800; }
    .status-rejected { background: #FDEAEA; color: #A01A1A; border-color: #F0A0A0; font-weight: 800; }
    
    .card-actions {
        display: flex;
        gap: 8px;
        flex-wrap: wrap;
        margin-top: 6px;
    }

    /* ===== DASHBOARD STATS - Prominent Boxes ===== */
    .dashboard-stats {
        display: grid;
        grid-template-columns: repeat(auto-fit, minmax(210px, 1fr));
        gap: 18px;
        margin-bottom: 24px;
    }
    .stat-card {
        background: var(--color-white);
        border-radius: var(--radius-lg);
        padding: 20px 22px;
        box-shadow: var(--shadow-md);
        display: flex;
        align-items: center;
        gap: 16px;
        transition: all 0.25s ease;
        cursor: pointer;
        border: 2px solid var(--color-border);
        border-left: 5px solid var(--color-primary);
    }
    .stat-card:hover {
        transform: translateY(-4px);
        box-shadow: var(--shadow-xl);
        border-color: var(--color-primary);
    }
    .stat-icon {
        width: 52px;
        height: 52px;
        border-radius: var(--radius-md);
        display: flex;
        align-items: center;
        justify-content: center;
        color: #FFFFFF;
        font-size: 22px;
        flex-shrink: 0;
        box-shadow: var(--shadow-sm);
    }
    .stat-info h3 {
        margin: 0;
        font-size: 26px;
        color: var(--color-text-primary);
        font-weight: 800;
        letter-spacing: -0.5px;
    }
    .stat-info p { 
        margin: 2px 0 0 0; 
        font-size: 13px; 
        color: var(--color-text-secondary); 
        font-weight: 600;
    }
    .stat-change {
        font-size: 12px;
        padding: 5px 12px;
        border-radius: 20px;
        font-weight: 700;
        flex-shrink: 0;
        border: 1.5px solid transparent;
    }
    .stat-change.positive { background: var(--color-success-bg); color: var(--color-success); border-color: #B8E0CC; }
    .stat-change.negative { background: var(--color-error-bg); color: var(--color-error); border-color: #F0B8B8; }
    .stat-change.neutral { background: var(--color-off-white); color: var(--color-text-secondary); border-color: var(--color-border); }

        /* ===== MATCH SCORES ===== */
    .match-high { 
        background: #10B981; 
        color: #FFFFFF; 
        padding: 6px 18px; 
        border-radius: 20px; 
        display: inline-block; 
        font-weight: 800; 
        font-size: 17px; 
        border: 2px solid #059669;
        text-shadow: 0 1px 2px rgba(0,0,0,0.2);
    }
    .match-medium { 
        background: #F59E0B; 
        color: #1A1A1A; 
        padding: 6px 18px; 
        border-radius: 20px; 
        display: inline-block; 
        font-weight: 800; 
        font-size: 17px; 
        border: 2px solid #D97706;
    }
    .match-low { 
        background: #EF4444; 
        color: #FFFFFF; 
        padding: 6px 18px; 
        border-radius: 20px; 
        display: inline-block; 
        font-weight: 800; 
        font-size: 17px; 
        border: 2px solid #DC2626;
        text-shadow: 0 1px 2px rgba(0,0,0,0.2);
    }

    /* ===== ALERTS ===== */
    .alert-success { 
        background: var(--color-success); 
        color: #FFFFFF; 
        padding: 14px 18px; 
        border-radius: var(--radius-md); 
        margin: 10px 0; 
        font-weight: 600;
        border: 2px solid #0A5C35;
    }
    .alert-error { 
        background: var(--color-error); 
        color: #FFFFFF; 
        padding: 14px 18px; 
        border-radius: var(--radius-md); 
        margin: 10px 0; 
        font-weight: 600;
        border: 2px solid #801515;
    }

    /* ===== MODALS ===== */
    .modal {
        display: none;
        position: fixed;
        z-index: 1000;
        left: 0;
        top: 0;
        width: 100%;
        height: 100%;
        background: rgba(15, 29, 51, 0.7);
        backdrop-filter: blur(6px);
    }
    .modal-content {
    background: var(--color-white);
    margin: 30px auto;
    border-radius: var(--radius-xl);
    max-width: 1000px;
    width: 95%;
    box-shadow: var(--shadow-xl);
    border: 2px solid var(--color-border-strong);
    overflow: hidden;
}
    .modal-header {
        background: linear-gradient(135deg, var(--color-primary-dark) 0%, var(--color-primary) 100%);
        color: #FFFFFF;
        padding: 18px 22px;
        border-radius: var(--radius-xl) var(--radius-xl) 0 0;
        display: flex;
        justify-content: space-between;
        align-items: center;
        border-bottom: 2px solid var(--color-primary-dark);
    }
    .modal-header h2 { 
        margin: 0; 
        font-weight: 700; 
        font-size: 20px;
        letter-spacing: -0.3px;
    }
    .modal-body { 
    padding: 0; 
    max-height: 70vh; 
    overflow-y: auto; 
    background: var(--color-white);
}
    .close { 
        cursor: pointer; 
        font-size: 30px; 
        font-weight: 400; 
        opacity: 0.9; 
        transition: opacity 0.2s; 
        color: #FFFFFF;
    }
    .close:hover { opacity: 1; }

    /* ===== INPUTS ===== */
    input, select, textarea {
        width: 100%;
        padding: 10px 14px;
        margin: 5px 0;
        border: 2px solid var(--color-border);
        border-radius: var(--radius-md);
        font-size: 14px;
        transition: all 0.2s;
        background: var(--color-white);
        color: var(--color-text-primary);
        font-weight: 500;
    }
    input:focus, select:focus, textarea:focus {
        outline: none;
        border-color: var(--color-primary);
        box-shadow: 0 0 0 4px rgba(27, 42, 74, 0.1);
        background: #FAFBFC;
    }
    input::placeholder, textarea::placeholder {
        color: var(--color-text-tertiary);
        font-weight: 400;
    }

    /* ===== FILTER BAR ===== */
    .filter-bar {
        background: var(--color-white);
        padding: 14px 18px;
        border-radius: var(--radius-lg);
        margin-bottom: 18px;
        display: flex;
        gap: 12px;
        flex-wrap: wrap;
        box-shadow: var(--shadow-md);
        border: 2px solid var(--color-border);
    }
    .filter-bar input, .filter-bar select { 
        width: auto; 
        flex: 1; 
        min-width: 140px; 
    }

    /* ===== DETAIL ROWS ===== */
    .detail-row {
        margin-bottom: 12px;
        display: flex;
        border-bottom: 2px solid var(--color-border-light);
        padding-bottom: 6px;
    }
    .detail-label { 
        width: 140px; 
        font-weight: 700; 
        color: var(--color-text-secondary); 
        font-size: 14px;
    }
    .detail-value { 
        flex: 1; 
        color: var(--color-text-primary); 
        font-weight: 500;
    }

    /* ===== COMPANY ITEMS ===== */
    .company-item {
        background: var(--color-off-white);
        padding: 10px 14px;
        margin-bottom: 6px;
        border-radius: var(--radius-md);
        border-left: 4px solid var(--color-primary);
        font-weight: 500;
        border: 1.5px solid var(--color-border-light);
        border-left: 4px solid var(--color-primary);
    }

    /* ===== FILE LIST ===== */
    .file-list { 
        background: var(--color-off-white); 
        border-radius: var(--radius-md); 
        padding: 12px; 
        margin-top: 10px; 
        max-height: 150px; 
        overflow-y: auto; 
        border: 2px solid var(--color-border);
    }
    .file-list-item { 
        padding: 6px 10px; 
        border-bottom: 1.5px solid var(--color-border-light); 
        font-size: 13px; 
        display: flex; 
        justify-content: space-between; 
        align-items: center; 
        font-weight: 500;
    }
    .remove-file { 
        color: var(--color-error); 
        cursor: pointer; 
        margin-left: 10px; 
        font-weight: 700; 
    }

    /* ===== PROGRESS BAR ===== */
    .progress-bar { 
        background: var(--color-border-light); 
        border-radius: 10px; 
        height: 16px; 
        margin: 10px 0; 
        overflow: hidden; 
        border: 1px solid var(--color-border);
    }
    .progress-fill { 
        background: linear-gradient(90deg, var(--color-primary), var(--color-accent));
        width: 0%; 
        height: 100%; 
        transition: width 0.3s ease; 
    }

    /* ===== SPINNER ===== */
    .spinner {
        border: 3px solid var(--color-border-light);
        border-top: 3px solid var(--color-primary);
        border-radius: 50%;
        width: 32px;
        height: 32px;
        animation: spin 1s linear infinite;
        margin: 12px auto;
    }
    @keyframes spin { 0% { transform: rotate(0deg); } 100% { transform: rotate(360deg); } }

    /* ===== DOC LINK ===== */
    .doc-link { 
        cursor: pointer; 
        color: var(--color-primary); 
        text-decoration: underline; 
        font-weight: 600;
        text-underline-offset: 3px;
    }
    .doc-link:hover { 
        color: var(--color-accent);
    }

    /* ===== SIDEBAR ===== */
    .sidebar {
        width: 230px;
        background: var(--color-white);
        border-radius: var(--radius-lg);
        padding: 20px 0;
        flex-shrink: 0;
        box-shadow: var(--shadow-md);
        transition: all 0.3s ease;
        border: 2px solid var(--color-border);
    }
    .sidebar-container {
        display: flex;
        gap: 22px;
        align-items: flex-start;
        margin-bottom: 22px;
    }

    /* ===== TOAST ===== */
    .toast-container {
        position: fixed;
        top: 20px;
        right: 20px;
        z-index: 9999;
        display: flex;
        flex-direction: column;
        gap: 12px;
        max-width: 360px;
        width: 100%;
    }
    .toast {
        padding: 16px 22px;
        border-radius: var(--radius-lg);
        color: #FFFFFF;
        font-size: 14px;
        font-weight: 600;
        box-shadow: var(--shadow-lg);
        transform: translateX(400px);
        animation: slideIn 0.5s forwards;
        display: flex;
        align-items: center;
        gap: 10px;
        border: 2px solid rgba(255,255,255,0.2);
    }
    .toast-success { background: var(--color-success); border-left: 5px solid #0A5C35; }
    .toast-error { background: var(--color-error); border-left: 5px solid #801515; }
    .toast-warning { background: var(--color-warning); border-left: 5px solid #8C4400; }
    .toast-info { background: var(--color-primary); border-left: 5px solid var(--color-primary-dark); }
    .toast-icon { font-size: 22px; }
    .toast-message { flex: 1; }
    .toast-close { 
        cursor: pointer; 
        font-size: 18px; 
        opacity: 0.8; 
        transition: opacity 0.3s; 
        background: none; 
        border: none; 
        color: #FFFFFF; 
        font-weight: 700;
    }
    .toast-close:hover { opacity: 1; }
    @keyframes slideIn { to { transform: translateX(0); } }
    @keyframes slideOut { to { transform: translateX(400px); opacity: 0; } }
    .toast-hidden { animation: slideOut 0.5s forwards; }

    /* ============================================
       DARK MODE - High Contrast Navy
       ============================================ */
    body.dark-mode { 
        background: #0A0F1A; 
        color: #E8ECF2; 
    }
    
    body.dark-mode .header { 
        background: linear-gradient(135deg, #0F1D33 0%, #1B2A4A 50%, #2C4270 100%);
        border-color: #1B2A4A;
    }
    body.dark-mode .header h1 { color: #FFFFFF; }
    body.dark-mode .header p { color: #B8C8E0; }
    
    /* Dark Mode Cards */
    body.dark-mode .card { 
        background: #131C2E; 
        border-color: #2A3A5C;
        border-left: 5px solid var(--color-accent);
        box-shadow: 0 2px 8px rgba(0,0,0,0.3);
    }
    body.dark-mode .card:hover {
        border-color: #3B5998;
        box-shadow: 0 6px 20px rgba(0,0,0,0.4);
    }
    body.dark-mode .card.no-click { 
        background: #131C2E; 
        border-left-color: #2A3A5C;
    }
    
    body.dark-mode .candidate-card { 
        background: #131C2E; 
        border-color: #2A3A5C;
        box-shadow: 0 2px 8px rgba(0,0,0,0.3);
    }
    body.dark-mode .candidate-card:hover { 
        border-color: #3B5998;
        box-shadow: 0 6px 20px rgba(0,0,0,0.4);
    }
    body.dark-mode .card-header { 
        background: #0F1829; 
        border-bottom-color: #2A3A5C; 
    }
    body.dark-mode .card-body {
        background: #131C2E;
    }
    body.dark-mode .candidate-name { 
        color: #FFFFFF; 
        font-weight: 700;
    }
    body.dark-mode .candidate-email { 
        color: #A8B8D4; 
        font-weight: 500;
    }
    
    /* Dark Mode Stats */
    body.dark-mode .stat-card { 
        background: #131C2E; 
        border-color: #2A3A5C;
        border-left: 5px solid var(--color-accent);
    }
    body.dark-mode .stat-info h3 { 
        color: #FFFFFF; 
        font-weight: 800;
    }
    body.dark-mode .stat-info p { 
        color: #A8B8D4; 
        font-weight: 500;
    }
    
    /* Dark Mode Modal */
    body.dark-mode .modal-content { 
        background: #131C2E; 
        border-color: #2A3A5C;
    }
    body.dark-mode .modal-body {
        background: #131C2E;
        color: #E8ECF2;
    }
    body.dark-mode .modal-header { 
        background: linear-gradient(135deg, #0F1D33 0%, #1B2A4A 100%);
        border-bottom-color: #1B2A4A;
    }
    
    /* Dark Mode Detail Rows */
    body.dark-mode .detail-row { 
        border-bottom-color: #2A3A5C; 
    }
    body.dark-mode .detail-label {
        color: #A8B8D4;
    }
    body.dark-mode .detail-value {
        color: #E8ECF2;
    }
    
    /* Dark Mode Components */
    body.dark-mode .company-item { 
        background: #0F1829; 
        border-left-color: var(--color-accent);
        border-color: #2A3A5C;
        color: #E8ECF2;
    }
    body.dark-mode .file-list { 
        background: #0F1829;
        border-color: #2A3A5C;
    }
    body.dark-mode .file-list-item { 
        border-bottom-color: #2A3A5C; 
        color: #E8ECF2;
    }
    body.dark-mode .filter-bar { 
        background: #131C2E;
        border-color: #2A3A5C;
    }
    body.dark-mode .sidebar { 
        background: #131C2E; 
        border-color: #2A3A5C;
        box-shadow: 0 2px 10px rgba(0,0,0,0.4); 
    }
    
    /* Dark Mode Tabs */
    body.dark-mode .tab-btn { 
        color: #A8B8D4; 
    }
    body.dark-mode .tab-btn:hover { 
        background: rgba(59, 89, 152, 0.15); 
        color: #D0DAEC; 
    }
    body.dark-mode .tab-btn.active { 
        background: rgba(59, 89, 152, 0.25); 
        color: #8AACF0; 
        font-weight: 700;
    }
    
    /* Dark Mode Inputs */
    body.dark-mode input, 
    body.dark-mode select, 
    body.dark-mode textarea { 
        background: #0F1829; 
        color: #E8ECF2; 
        border-color: #2A3A5C; 
    }
    body.dark-mode input:focus, 
    body.dark-mode select:focus, 
    body.dark-mode textarea:focus {
        border-color: #3B5998;
        box-shadow: 0 0 0 4px rgba(59, 89, 152, 0.2);
        background: #0F1A2E;
    }
    body.dark-mode input::placeholder, 
    body.dark-mode textarea::placeholder { 
        color: #5A6F8A; 
    }
    
    /* Dark Mode Tags & Badges */
    body.dark-mode .skill-tag { 
        background: #0F1829; 
        color: #8AACF0; 
        border-color: #2A3A5C;
        font-weight: 700;
    }
    body.dark-mode .skill-tag.more {
        background: #1A2740;
        color: #A8B8D4;
        border-color: #2A3A5C;
    }
    
    /* Dark Mode Buttons */
    body.dark-mode .btn-secondary { 
        background: #1A2740; 
        color: #E8ECF2; 
        border-color: #2A3A5C; 
    }
    body.dark-mode .btn-secondary:hover { 
        background: #2A3A5C; 
        border-color: #3B5998;
        color: #FFFFFF;
    }
    body.dark-mode .btn-expand { 
        border-color: #2A3A5C;
        color: #A8B8D4;
    }
    body.dark-mode .btn-expand:hover { 
        background: #3B5998; 
        color: #FFFFFF;
        border-color: #3B5998;
    }
    body.dark-mode .btn-expand.expanded {
        background: rgba(59, 89, 152, 0.3);
        border-color: #3B5998;
        color: #8AACF0;
    }
    
    /* Dark Mode Status Badges */
    body.dark-mode .status-new { background: #0F2035; color: #6AACF0; border-color: #1B3A5C; }
    body.dark-mode .status-screening { background: #2A1A0A; color: #F0A050; border-color: #5C3A1A; }
    body.dark-mode .status-interview { background: #2A0F0F; color: #F06060; border-color: #5C1F1F; }
    body.dark-mode .status-offer { background: #0A1F14; color: #50D080; border-color: #1A4A2A; }
    body.dark-mode .status-hired { background: #0A1F14; color: #40E070; border-color: #1A5C2A; }
    body.dark-mode .status-rejected { background: #2A0F0F; color: #F04040; border-color: #5C1F1F; }
    
    /* Dark Mode Misc */
    body.dark-mode .stat-change.positive { background: #0A1F14; color: #50D080; border-color: #1A4A2A; }
    body.dark-mode .stat-change.negative { background: #2A0F0F; color: #F06060; border-color: #5C1F1F; }
    body.dark-mode .stat-change.neutral { background: #1A2740; color: #A8B8D4; border-color: #2A3A5C; }
    body.dark-mode .toast-success { background: #0A5C35; }
    body.dark-mode .toast-error { background: #801515; }
    body.dark-mode .toast-warning { background: #8C4400; }
    body.dark-mode .btn-secondary { background: #1A2740; color: #D0DAEC; border-color: #2A3A5C; }
    body.dark-mode .btn-secondary:hover { background: #2A3A5C; color: #FFFFFF; }
    body.dark-mode .toast-info { background: #1B2A4A; }
    /* Dark Mode Dashboard Stats */
body.dark-mode .stat-card { background: #131C2E; border-color: #2A3A5C; border-left: 5px solid #3B5998; }
body.dark-mode .stat-info h3 { color: #FFFFFF; font-weight: 800; }
body.dark-mode .stat-info p { color: #A8B8D4; }

/* Dark Mode Dashboard Panels */
body.dark-mode .card.no-click { background: #131C2E; border-color: #2A3A5C; }
body.dark-mode .card.no-click h3 { color: #E8ECF2; }
body.dark-mode .card.no-click h4 { color: #D0DAEC; }
body.dark-mode #skillsCloud span { background: #1A2740 !important; color: #A8B8D4 !important; border-color: #2A3A5C !important; }
body.dark-mode canvas { filter: brightness(0.9); }

/* Dark Mode Forms */
body.dark-mode .form-group label { color: #A8B8D4 !important; font-weight: 600; }
body.dark-mode .form-input, body.dark-mode input, body.dark-mode select, body.dark-mode textarea { background: #0F1829 !important; color: #E8ECF2 !important; border-color: #2A3A5C !important; }
body.dark-mode .form-input:focus { border-color: #3B5998 !important; box-shadow: 0 0 0 3px rgba(59,89,152,0.2) !important; }
body.dark-mode input::placeholder, body.dark-mode textarea::placeholder { color: #5A6F8A !important; }

/* Dark Mode Modal */
body.dark-mode .modal-section { background: #0F1829 !important; border-color: #2A3A5C !important; }
body.dark-mode .modal-section-title { color: #E8ECF2 !important; border-bottom-color: #2A3A5C !important; }

/* Dark Mode Filter Bar */
body.dark-mode .filter-bar { background: #131C2E; border-color: #2A3A5C; }
body.dark-mode #simple-total, body.dark-mode #simple-hired, body.dark-mode #simple-pending, body.dark-mode #simple-rejected, body.dark-mode #simple-avg { color: #E8ECF2 !important; }
body.dark-mode #candidateStats { color: #A8B8D4 !important; }

/* Dark Mode Cards */
body.dark-mode .company-item { background: #0F1829; border-color: #2A3A5C; color: #E8ECF2; }
body.dark-mode .file-list { background: #0F1829; border-color: #2A3A5C; }
body.dark-mode .file-list-item { border-bottom-color: #2A3A5C; color: #E8ECF2; }
body.dark-mode .progress-bar { background: #1A2740; border-color: #2A3A5C; }
body.dark-mode .detail-label { color: #A8B8D4; }
body.dark-mode .detail-value { color: #E8ECF2; }
body.dark-mode .detail-row { border-bottom-color: #2A3A5C; }

/* Dark Mode Alerts */
body.dark-mode .alert-success { background: #0A3D1F; border-color: #0A5C35; color: #D0F0D8; }
body.dark-mode .alert-error { background: #3D0A0A; border-color: #801515; color: #F0D0D0; }
body.dark-mode .no-skills { color: #5A6F8A; }
body.dark-mode .doc-link { color: #8AACF0; }
body.dark-mode .doc-link:hover { color: #B0C8F8; }

/* Dark Mode Text Visibility - Force light text everywhere */
body.dark-mode p, body.dark-mode span, body.dark-mode div, body.dark-mode small, body.dark-mode strong { color: #D0DAEC; }
body.dark-mode h1, body.dark-mode h2, body.dark-mode h3, body.dark-mode h4 { color: #E8ECF2; }
body.dark-mode label { color: #A8B8D4; }
body.dark-mode [style*="color:#555"], body.dark-mode [style*="color:#666"], body.dark-mode [style*="color:#333"], body.dark-mode [style*="color: #555"], body.dark-mode [style*="color: #666"], body.dark-mode [style*="color: #333"] { color: #A8B8D4 !important; }
body.dark-mode [style*="color:#777"], body.dark-mode [style*="color: #777"] { color: #8A9BB5 !important; }
body.dark-mode [style*="color:#999"], body.dark-mode [style*="color: #999"] { color: #6A7A95 !important; }
body.dark-mode .match-high { color: #FFFFFF !important; }
body.dark-mode .match-low { color: #FFFFFF !important; }

    /* ===== RESPONSIVE ===== */
    @media screen and (max-width: 768px) {
    body {
        padding: 0;
        font-size: 15px;
        background: #F2F5F9;
    }
    
    .header {
        padding: 14px 16px;
        border-radius: 0;
        position: sticky;
        top: 0;
        z-index: 100;
    }
    .header h1 { font-size: 20px; }
    .header p { font-size: 12px; display: none; }
    
    /* Mobile Menu Button */
    .mobile-menu-btn { 
        display: block !important;
        position: fixed;
        top: 8px;
        left: 8px;
        z-index: 1001;
        background: #1B2A4A;
        color: #fff;
        border: none;
        padding: 10px 12px;
        border-radius: 8px;
        font-size: 20px;
        width: 44px;
        height: 44px;
        text-align: center;
        line-height: 1;
    }
    
    /* Sidebar - Slide from left */
        .sidebar-container { 
        display: block !important;
        flex-direction: column !important;
        gap: 0; 
        position: relative;
    }
    .sidebar { 
        position: fixed;
        top: 0;
        left: -280px;
        width: 260px !important;
        height: 100vh;
        z-index: 1000;
        overflow-y: auto;
        border-radius: 0 !important;
        box-shadow: 0 0 40px rgba(0,0,0,0.4);
        transition: left 0.3s ease;
        padding-top: 60px;
    }
    .sidebar.open { left: 0; }
    
    /* Overlay when sidebar is open */
    .sidebar-overlay {
        display: none;
        position: fixed;
        top: 0;
        left: 0;
        width: 100%;
        height: 100%;
        background: rgba(0,0,0,0.5);
        z-index: 999;
    }
    .sidebar-overlay.active { display: block; }
    
    /* Content area - full width */
        .content-area {
        width: 100% !important;
        flex: none !important;
        min-width: 100% !important;
        margin-top: 60px !important;
        margin-left: 0 !important;
        padding: 8px !important;
        overflow-x: hidden !important;
    }
    
    /* Bigger touch-friendly inputs */
    input, select, textarea {
        font-size: 16px !important;
        padding: 12px 10px !important;
    }
    .form-input { font-size: 16px !important; padding: 12px 10px !important; }
    
    /* Bigger buttons */
    button, .btn {
        font-size: 15px !important;
        padding: 12px 18px !important;
        margin: 4px;
    }
    .btn-sm { padding: 8px 14px !important; font-size: 13px !important; }
    
    /* Cards - full width */
    .card { 
        padding: 14px; 
        margin: 8px 0;
        border-radius: 10px;
    }
    .card h3 { font-size: 16px !important; }
    .card h4 { font-size: 14px !important; }
    
    /* Candidate cards */
    .candidate-card { margin-bottom: 10px; }
    .card-header { padding: 12px 14px; }
    .candidate-name { font-size: 15px !important; }
    .candidate-email { font-size: 12px !important; }
    .candidate-avatar { width: 40px; height: 40px; font-size: 18px; }
    .candidate-skills .skill-tag { font-size: 11px !important; padding: 4px 10px !important; }
    .candidate-meta { flex-direction: column; gap: 4px; }
    .candidate-meta .meta-item { font-size: 12px !important; }
    .card-actions { flex-direction: row; flex-wrap: wrap; gap: 4px; }
    .card-actions button { flex: 1; min-width: 80px; font-size: 12px !important; padding: 8px !important; }
    
    /* Dashboard */
    .dashboard-stats { grid-template-columns: 1fr 1fr; gap: 8px; }
    .stat-card { padding: 12px; }
    .stat-info h3 { font-size: 20px !important; }
    
    /* Filters */
    .filter-bar { 
        flex-direction: column; 
        gap: 6px;
        padding: 10px;
    }
    .filter-bar input, .filter-bar select { width: 100%; }
    
    /* Modals - full screen */
    .modal-content {
        width: 100% !important;
        max-width: 100% !important;
        margin: 0 !important;
        border-radius: 0 !important;
        height: 100vh;
        max-height: 100vh;
    }
    .modal-body { max-height: calc(100vh - 60px) !important; }
    .modal-grid { grid-template-columns: 1fr; padding: 8px; }
    .modal-header { padding: 12px 16px; }
    .modal-header h2 { font-size: 17px; }
    .form-row { grid-template-columns: 1fr; gap: 4px; }
    .modal-section { margin-bottom: 8px; padding: 10px; }
    
    /* Kanban - vertical stack */
    #kanbanBoard {
        flex-direction: column !important;
        gap: 8px;
    }
    #kanbanBoard > div {
        min-width: 100% !important;
        max-width: 100% !important;
        min-height: auto !important;
    }
    
    /* Jobs/Candidate lists */
    #jobsList .card, #candidatesList .card {
        padding: 12px;
    }
    
    /* Toast */
    .toast-container {
        left: 8px;
        right: 8px;
        top: 60px;
        max-width: 100%;
    }
    .toast { font-size: 14px; padding: 12px 14px; }
    
    /* Pipeline stats */
    [style*="grid-template-columns: repeat(6, 1fr)"] {
        grid-template-columns: repeat(3, 1fr) !important;
        gap: 4px !important;
    }
    
    /* Hide dark mode toggle on mobile header */
    .dark-mode-toggle { font-size: 14px; padding: 8px 12px; }
    
    /* Scrollable panels */
    #reportsPanel, #dashboardPanel, #jobsPanel, #candidatesPanel, 
    #interviewsPanel, #analyzePanel, #kanbanPanel, #onboardedPanel, 
    #usersPanel, #uploadPanel, #createJobPanel {
        overflow-x: hidden;
        padding: 0;
    }
}
    /* ===== MODAL FORM LAYOUT ===== */
.modal-section { margin-bottom: 14px; background: #FAFBFC; border: 2px solid #E2E8F0; border-radius: 10px; padding: 14px; min-height: 100px; max-height: 250px; overflow-y: auto; }
.modal-section-title { font-size: 14px; font-weight: 700; color: #1B2A4A; margin: 0 0 10px 0; padding-bottom: 8px; border-bottom: 2px solid #E2E8F0; }
.form-row {
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 8px;
    margin-bottom: 6px;
}
.form-group { display: flex; flex-direction: column; }
.form-group label { font-size: 12px; font-weight: 600; color: #2C3E5A; margin-bottom: 3px; }
.form-input { width: 100%; padding: 8px 10px; border: 2px solid #D0D8E4; border-radius: 6px; font-size: 13px; background: #FFFFFF; color: #0F1D33; box-sizing: border-box; }
.form-input:focus { border-color: #1B2A4A; outline: none; box-shadow: 0 0 0 3px rgba(27,42,74,0.1); }
.modal-grid {
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 16px;
    padding: 16px;
}
.modal-grid > div {
    min-width: 0;
    overflow: hidden;
}
.modal-grid > div { display: flex; flex-direction: column; }
#skillsContainer, #workHistoryContainer, #certificationsContainer, #attachmentsList { min-height: 36px; max-height: 130px; overflow-y: auto; }
body.dark-mode .modal-section { background: #0F1829; border-color: #2A3A5C; }
body.dark-mode .modal-section-title { color: #E8ECF2; border-bottom-color: #2A3A5C; }
body.dark-mode .form-group label { color: #A8B8D4; }
body.dark-mode .form-input { background: #0F1829; color: #E8ECF2; border-color: #2A3A5C; }
@media screen and (max-width: 600px) { .form-row { grid-template-columns: 1fr; } }
@media screen and (max-width: 900px) { .modal-grid { grid-template-columns: 1fr; } }

/* Sidebar Dropdown Groups */
.sidebar-group { border-bottom: 1px solid rgba(255,255,255,0.08); }
.sidebar-group-header {
    padding: 12px 20px;
    cursor: pointer;
    display: flex;
    justify-content: space-between;
    align-items: center;
    color: #FFFFFF;
    font-size: 13px;
    font-weight: 700;
    letter-spacing: 0.5px;
    transition: all 0.2s;
}
.sidebar-group-header:hover { background: rgba(255,255,255,0.1); }
.sidebar-group-header i { font-size: 10px; transition: transform 0.3s; color: rgba(255,255,255,0.6); }
.sidebar-group-header.open i { transform: rotate(180deg); }
.sidebar-group-items { display: none; }
.sidebar-group-items.open { display: block; }
.sidebar-group-items .tab-btn { 
    padding-left: 35px !important; 
    font-size: 13px !important; 
    color: #D0DAEC !important;
}
.sidebar-group-items .tab-btn:hover { color: #E0E8F0 !important; background: rgba(255,255,255,0.08); }
.sidebar-group-items .tab-btn.active { color: #D0DAEC !important; background: rgba(255,255,255,0.05); }

/* Dark Mode Sidebar Groups */
body.dark-mode .sidebar-group-header { color: #C9A96E; }
body.dark-mode .sidebar-group-header:hover { background: rgba(255,255,255,0.05); }
body.dark-mode .sidebar-group-header i { color: rgba(201,169,110,0.5); }
body.dark-mode .sidebar-group-items .tab-btn { color: #A8B8D4 !important; }
body.dark-mode .sidebar-group-items .tab-btn:hover { color: #FFFFFF !important; }
body.dark-mode .sidebar-group-items .tab-btn.active { color: #C9A96E !important; }
</style>
    
</head>
<body>

<!-- LOGIN OVERLAY -->
<div id="loginOverlay" style="display:flex;position:fixed;top:0;left:0;width:100%;height:100%;background:#1B2A4A;z-index:9999;align-items:center;justify-content:center;">
    <div style="background:#FFFFFF;padding:40px;border-radius:16px;width:100%;max-width:420px;box-shadow:0 20px 60px rgba(0,0,0,0.3);">
        <div style="text-align:center;margin-bottom:30px;">
            <h1 style="color:#1B2A4A;margin:0;font-size:28px;">🔍 ShahnaIT Scout</h1>
            <p style="color:#64748B;margin:8px 0 0 0;">AI-Powered Recruitment Platform</p>
        </div>
        <div id="loginError" style="display:none;background:#FEE2E2;color:#991B1B;padding:10px 14px;border-radius:8px;margin-bottom:16px;font-size:13px;"></div>
        <form id="loginForm" onsubmit="handleLogin(event)">
            <div class="form-group"><label>Email</label><input type="email" id="loginEmail" class="form-input" placeholder="ibaadrn@shahnait.com" required></div>
            <div class="form-group"><label>Password</label><input type="password" id="loginPassword" class="form-input" placeholder="Enter password" required></div>
            <button type="submit" class="btn btn-primary" style="width:100%;padding:14px;font-size:16px;">🔐 Login</button>
        </form>
        <p style="text-align:center;margin-top:16px;font-size:12px;color:#94A3B8;">Default: ibaadrn@shahnait.com</p>
    </div>
</div>

<!-- Toast Container -->
<div id="toastContainer" class="toast-container"></div>
<div style="max-width: 1200px; margin: 0 auto;">
    <div class="header">
    <div style="display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap;">
        <div>
            <h1>🎯 ShahnaIT Scout</h1>
            <p>AI-Powered Recruitment Platform</p>
        </div>
        <button class="dark-mode-toggle" onclick="toggleDarkMode()" title="Toggle Dark Mode">🌙</button>
    </div>
</div>

   <div class="sidebar-overlay" id="sidebarOverlay" onclick="toggleSidebar()"></div>
   <div class="sidebar-container" style="display: flex; gap: 20px; align-items: flex-start; margin-bottom: 20px;">
    <!-- Mobile Menu Button -->
    <button class="mobile-menu-btn" onclick="toggleSidebar()">☰ Menu</button>
    
    <!-- Sidebar -->
    <div class="sidebar" id="sidebar" style="width: 220px; background: #1A4D4A; border-radius: 12px; padding: 20px 0; flex-shrink: 0; box-shadow: 0 2px 10px rgba(0,0,0,0.1);">
        <div style="padding: 0 20px 15px 20px; border-bottom: 1px solid rgba(255,255,255,0.1); margin-bottom: 10px;">
            <div style="color: #C9A96E; font-size: 11px; text-transform: uppercase; letter-spacing: 1px; font-weight: bold;">Menu</div>
        </div>
                <!-- User Info -->
        <div style="padding:10px 20px 12px 20px;border-bottom:1px solid rgba(255,255,255,0.1);margin-bottom:6px;">
            <div style="display:flex;align-items:center;gap:10px;">
                <div style="width:34px;height:34px;border-radius:50%;background:rgba(255,255,255,0.2);display:flex;align-items:center;justify-content:center;font-size:15px;flex-shrink:0;">👤</div>
                <div style="flex:1;min-width:0;">
                    <div id="userDisplayName" style="color:#FFFFFF;font-size:13px;font-weight:600;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;">---</div>
                    <div id="userDisplayRole" style="color:rgba(255,255,255,0.5);font-size:10px;">---</div>
                </div>
                <button onclick="logout()" style="background:rgba(255,255,255,0.1);border:none;color:#fff;padding:5px 8px;border-radius:4px;cursor:pointer;font-size:11px;flex-shrink:0;" title="Logout">🚪</button>
            </div>
        </div>

        <!-- 📋 Jobs -->
        <div class="sidebar-group">
            <div class="sidebar-group-header" onclick="toggleSidebarGroup(this)">
                <span>📋 Jobs</span><i class="fas fa-chevron-down"></i>
            </div>
            <div class="sidebar-group-items">
                <button class="tab-btn active" id="tabJobs">📋 View Jobs</button>
                <button class="tab-btn" id="tabCreateJob">➕ Create Job</button>
            </div>
        </div>

        <!-- 👥 Candidates -->
        <div class="sidebar-group">
            <div class="sidebar-group-header" onclick="toggleSidebarGroup(this)">
                <span>👥 Candidates</span><i class="fas fa-chevron-down"></i>
            </div>
            <div class="sidebar-group-items">
                <button class="tab-btn" id="tabCandidates">👥 View Candidates</button>
                <button class="tab-btn" id="tabUpload">📄 Upload Resume</button>
            </div>
        </div>

        <!-- 📊 Insights -->
        <div class="sidebar-group">
            <div class="sidebar-group-header" onclick="toggleSidebarGroup(this)">
                <span>📊 Insights</span><i class="fas fa-chevron-down"></i>
            </div>
            <div class="sidebar-group-items">
                <button class="tab-btn" id="tabAnalyze">🔍 Analyze Match</button>
                <button class="tab-btn" id="tabDashboard">📊 Dashboard</button>
                <button class="tab-btn" id="tabKanban">📋 Kanban Board</button>
                <button class="tab-btn" id="tabReports">📈 Daily Report</button>
            </div>
        </div>

        <!-- 📅 Operations -->
        <div class="sidebar-group">
            <div class="sidebar-group-header" onclick="toggleSidebarGroup(this)">
                <span>📅 Operations</span><i class="fas fa-chevron-down"></i>
            </div>
            <div class="sidebar-group-items">
                <button class="tab-btn" id="tabInterviews">📅 Interviews</button>
            </div>
        </div>

        <!-- 💼 Management (Admin Only) -->
        <div class="sidebar-group admin-only" style="display:none;">
            <div class="sidebar-group-header" onclick="toggleSidebarGroup(this)">
                <span>💼 Management</span><i class="fas fa-chevron-down"></i>
            </div>
            <div class="sidebar-group-items">
                <button class="tab-btn" id="tabOnboarded">💼 Onboarded</button>
            </div>
        </div>

        <!-- 💰 Finance (Admin Only) -->
        <div class="sidebar-group admin-only" style="display:none;">
            <div class="sidebar-group-header" onclick="toggleSidebarGroup(this)">
                <span>💰 Finance</span><i class="fas fa-chevron-down"></i>
            </div>
            <div class="sidebar-group-items">
                <button class="tab-btn" id="tabFinance">📊 Finance Dashboard</button>
                <button class="tab-btn" onclick="toastInfo('Coming Soon')">🧾 Invoices</button>
                <button class="tab-btn" onclick="toastInfo('Coming Soon')">💸 Expenses</button>
            </div>
        </div>

        <!-- 📈 Reports (Admin Only) -->
        <div class="sidebar-group admin-only" style="display:none;">
            <div class="sidebar-group-header" onclick="toggleSidebarGroup(this)">
                <span>📈 Reports</span><i class="fas fa-chevron-down"></i>
            </div>
            <div class="sidebar-group-items">
                <button class="tab-btn" onclick="toastInfo('Coming Soon')">📄 Reports & Exports</button>
            </div>
        </div>

        <!-- ⚙️ Admin -->
        <div class="sidebar-group admin-only" style="display:none;">
            <div class="sidebar-group-header" onclick="toggleSidebarGroup(this)">
                <span>⚙️ Admin</span><i class="fas fa-chevron-down"></i>
            </div>
            <div class="sidebar-group-items">
                <button class="tab-btn" id="tabUsers">👥 Users</button>
            </div>
        </div>
    </div>
    
    <!-- Content Area -->
    <div class="content-area" style="flex: 1; min-width: 0;">
        <!-- Panel content goes here -->
    
    <div id="jobsPanel"><div id="jobsList"></div></div>
    <div id="candidatesPanel" style="display:none;">
    <!-- Static Dashboard Header - Stays at top while scrolling -->
    <div style="position: sticky; top: 0; background: #F5F0E8; z-index: 10; padding-bottom: 10px;">
        <div style="display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 10px;">
            <div>
                <span style="font-size: 20px; font-weight: bold;">👥 Candidate Inventory</span>
                <span id="candidateStats" style="font-size: 13px; color: #666; margin-left: 15px;"></span>
            </div>
            <div style="display: flex; gap: 8px;">
                <button id="exportBtn" class="btn" style="background: #1A4D4A;">📥 Export CSV</button>
                <button id="toggleViewBtn" class="btn" style="background: #6B7B7B;">📊 Grid/List</button>
            </div>
        </div>
                <!-- Simple Stats Bar -->
        <div style="display: flex; gap: 20px; flex-wrap: wrap; margin: 10px 0 15px 0; background: white; padding: 12px 20px; border-radius: 8px; box-shadow: 0 1px 3px rgba(0,0,0,0.05);">
            <div style="display: flex; align-items: center; gap: 6px;">
                <span style="font-weight: bold; color: #1A4D4A;">👥 Total:</span>
                <span id="simple-total" style="font-weight: bold; color: #1A4D4A; font-size: 16px;">0</span>
            </div>
            <div style="display: flex; align-items: center; gap: 6px;">
                <span style="font-weight: bold; color: #4CAF50;">✅ Hired:</span>
                <span id="simple-hired" style="font-weight: bold; color: #4CAF50; font-size: 16px;">0</span>
            </div>
            <div style="display: flex; align-items: center; gap: 6px;">
                <span style="font-weight: bold; color: #FF9800;">🟡 Pending:</span>
                <span id="simple-pending" style="font-weight: bold; color: #FF9800; font-size: 16px;">0</span>
            </div>
            <div style="display: flex; align-items: center; gap: 6px;">
                <span style="font-weight: bold; color: #F44336;">❌ Rejected:</span>
                <span id="simple-rejected" style="font-weight: bold; color: #F44336; font-size: 16px;">0</span>
            </div>
            <div style="display: flex; align-items: center; gap: 6px; margin-left: auto;">
                <span style="font-weight: bold; color: #1A4D4A;">📊 Avg Score:</span>
                <span id="simple-avg" style="font-weight: bold; color: #1A4D4A; font-size: 16px;">0%</span>
            </div>
        </div>
        
        <!-- Pipeline Stats -->
        <div style="display: grid; grid-template-columns: repeat(6, 1fr); gap: 8px; margin: 12px 0;">
            <div id="stat-new" style="background: #2196F3; color: white; padding: 10px; border-radius: 8px; text-align: center; cursor: pointer;">
                <div style="font-size: 20px; font-weight: bold;" id="stat-new-count">0</div>
                <div style="font-size: 11px;">📥 New</div>
            </div>
            <div id="stat-screening" style="background: #FF9800; color: white; padding: 10px; border-radius: 8px; text-align: center; cursor: pointer;">
                <div style="font-size: 20px; font-weight: bold;" id="stat-screening-count">0</div>
                <div style="font-size: 11px;">🔍 Screening</div>
            </div>
            <div id="stat-interview" style="background: #FF5722; color: white; padding: 10px; border-radius: 8px; text-align: center; cursor: pointer;">
                <div style="font-size: 20px; font-weight: bold;" id="stat-interview-count">0</div>
                <div style="font-size: 11px;">🎤 Interview</div>
            </div>
            <div id="stat-offer" style="background: #9C27B0; color: white; padding: 10px; border-radius: 8px; text-align: center; cursor: pointer;">
                <div style="font-size: 20px; font-weight: bold;" id="stat-offer-count">0</div>
                <div style="font-size: 11px;">💼 Offer</div>
            </div>
            <div id="stat-hired" style="background: #4CAF50; color: white; padding: 10px; border-radius: 8px; text-align: center; cursor: pointer;">
                <div style="font-size: 20px; font-weight: bold;" id="stat-hired-count">0</div>
                <div style="font-size: 11px;">✅ Hired</div>
            </div>
            <div id="stat-rejected" style="background: #F44336; color: white; padding: 10px; border-radius: 8px; text-align: center; cursor: pointer;">
                <div style="font-size: 20px; font-weight: bold;" id="stat-rejected-count">0</div>
                <div style="font-size: 11px;">❌ Rejected</div>
            </div>
        </div>
        
        <!-- Advanced Filters -->
      <!-- Advanced Filters -->
<div style="background: white; padding: 12px; border-radius: 8px; margin-bottom: 12px; box-shadow: 0 1px 3px rgba(0,0,0,0.1);">
    <div style="display: flex; gap: 10px; flex-wrap: wrap; align-items: center;">
        <!-- Search Box -->
        <input type="text" id="searchBox" placeholder="🔍 Search name, email, skills..." style="flex: 2; min-width: 150px; padding: 8px; border: 1px solid #ccc; border-radius: 5px;">
        
<!-- Status Filter -->
<select id="statusFilter" style="padding: 8px; border: 2px solid #D0D8E4; border-radius: 8px; font-weight:500;">
    <option value="all">📋 All Status</option>
    <option value="new">🆕 New</option>
    <option value="proposed">📋 Proposed</option>
    <option value="screening">🔍 Screening</option>
    <option value="technical_l1">💻 Technical L1</option>
    <option value="technical_l2">💻 Technical L2</option>
    <option value="technical_l3">💻 Technical L3</option>
    <option value="rejected">❌ Rejected</option>
    <option value="shortlisted">⭐ Shortlisted</option>
    <option value="offer_letter_shared">📄 Offer Shared</option>
    <option value="onboarded">✅ Onboarded</option>
</select>
       
        <!-- Score Filter -->
        <select id="scoreFilter" style="padding: 8px; border: 1px solid #ccc; border-radius: 5px;">
            <option value="all">All Scores</option>
            <option value="high">High (70%+)</option>
            <option value="medium">Medium (40-69%)</option>
            <option value="low">Low (<40%)</option>
        </select>
        
        <!-- Uploader Filter -->
        <input type="text" id="uploadedByFilter" placeholder="👤 Uploaded by..." style="min-width: 120px; padding: 8px; border: 1px solid #ccc; border-radius: 5px;">
        
        <!-- Sort By -->
        <select id="sortBy" style="padding: 8px; border: 1px solid #ccc; border-radius: 5px;">
            <option value="score">Sort by Match Score</option>
            <option value="name">Sort by Name</option>
            <option value="date">Sort by Date Added</option>
            <option value="status">Sort by Status</option>
            <option value="uploader">Sort by Uploader</option>
        </select>
        
        <!-- Clear Filters Button -->
        <button id="clearFiltersBtn" class="btn" style="background: #6B7B7B; padding: 8px 16px; border: none; border-radius: 5px; color: white; cursor: pointer;">Clear Filters</button>
      </div>
   </div>
</div>
    
    <!-- Candidates List - Updated with new card structure -->
<div id="candidatesList" style="min-height: 400px;"></div>
    
    <!-- Pagination -->
    <div id="pagination" style="display: flex; justify-content: space-between; align-items: center; margin-top: 15px; flex-wrap: wrap; gap: 10px;">
        <span id="paginationInfo" style="font-size: 13px; color: #666;"></span>
        <div style="display: flex; gap: 5px; flex-wrap: wrap;" id="paginationControls"></div>
    </div>
    
    <!-- Uploader Stats (Bar Chart) -->
    <div id="uploaderStats" style="background: white; padding: 15px; border-radius: 8px; margin-top: 20px; box-shadow: 0 1px 3px rgba(0,0,0,0.1);">
        <h4 style="margin: 0 0 10px 0;">👤 Uploader Stats</h4>
        <div id="uploaderChart" style="display: flex; flex-direction: column; gap: 6px;"></div>
    </div>
</div>    
    <div id="uploadPanel" style="display:none;">
        <div class="card no-click">
            <h3>📄 Single Resume Upload</h3>
            <input type="file" id="resumeFile" accept=".pdf,.docx">
            <button id="parseBtn">🔍 Parse & Save</button>
            <div id="parseResult"></div>
        </div>
        
        <div class="card no-click" style="margin-top: 20px;">
            <h3>📚 Bulk Resume Upload (Select Multiple Files)</h3>
            <p>Hold Ctrl (or Cmd on Mac) to select multiple PDF/DOCX files</p>
            <input type="file" id="multiResumeFiles" multiple accept=".pdf,.docx">
            <div id="selectedFilesList" class="file-list" style="display:none;"></div>
            <button id="bulkUploadBtn" class="btn">🚀 Upload & Parse All</button>
            <div id="bulkUploadResult"></div>
        </div>
    </div>

<div id="createJobPanel" style="display:none;">
    <div class="card no-click">
        <h3>➕ Create Job / Requirement</h3>
        
        <!-- Upload JD File -->
        <div style="background:#F0F4FA;padding:14px;border-radius:8px;margin-bottom:14px;border:2px dashed #D0D8E4;">
            <strong>📄 Upload JD File (PDF/DOCX)</strong>
            <div style="display:flex;gap:8px;margin-top:8px;">
                <input type="file" id="jdFileInput" accept=".pdf,.docx" style="flex:1;">
                <button id="parseJDBtn" class="btn btn-secondary" style="white-space:nowrap;">🔍 Parse JD</button>
            </div>
            <div id="jdParseStatus" style="margin-top:6px;font-size:12px;"></div>
        </div>
        
        <div style="text-align:center;margin:10px 0;color:#94A3B8;">— OR enter manually —</div>
        
        <!-- Row 1: Title & Client -->
        <div style="display:grid;grid-template-columns:1fr 1fr;gap:12px;">
            <div class="form-group"><label>Requirement Title *</label><input type="text" id="jobTitle" class="form-input" placeholder="e.g. Senior Python Developer"></div>
            <div class="form-group"><label>Client / Company</label><input type="text" id="jobCompany" class="form-input" placeholder="e.g. TCS"></div>
        </div>
        
        <!-- Row 2: Working Mode & Business Model -->
        <div style="display:grid;grid-template-columns:1fr 1fr;gap:12px;">
            <div class="form-group">
                <label>Working Mode</label>
                <select id="jobWorkingMode" class="form-input">
                    <option value="Not Specified">Not Specified</option>
                    <option value="Remote">Remote</option>
                    <option value="Hybrid">Hybrid</option>
                    <option value="Onsite">Onsite</option>
                </select>
            </div>
            <div class="form-group">
                <label>Business Model</label>
                <select id="jobBusinessModel" class="form-input">
                    <option value="Not Specified">Not Specified</option>
                    <option value="C2C">C2C</option>
                    <option value="C2H">C2H</option>
                    <option value="Permanent">Permanent</option>
                    <option value="Contract">Contract</option>
                </select>
            </div>
        </div>
        
        <!-- Hybrid Days (shown conditionally) -->
        <div class="form-group" id="hybridDaysGroup" style="display:none;">
            <label>Hybrid Days (per week)</label>
            <input type="number" id="jobHybridDays" class="form-input" value="0" min="0" max="7">
        </div>
        
        <!-- Row 3: Payroll & End Client -->
        <div style="display:grid;grid-template-columns:1fr 1fr;gap:12px;">
            <div class="form-group"><label>Payroll Company</label><input type="text" id="jobPayroll" class="form-input" placeholder="e.g. Randstad"></div>
            <div class="form-group"><label>End Client</label><input type="text" id="jobEndClient" class="form-input" placeholder="e.g. Microsoft"></div>
        </div>
        
        <!-- Row 4: Experience, Budget, Headcount -->
        <div style="display:grid;grid-template-columns:1fr 1fr 1fr;gap:12px;">
            <div class="form-group"><label>Years of Experience</label><input type="number" id="jobExperience" class="form-input" value="0" min="0"></div>
            <div class="form-group"><label>Budget</label><input type="text" id="jobBudget" class="form-input" placeholder="e.g. 15-20 LPA"></div>
            <div class="form-group"><label>Headcount</label><input type="number" id="jobHeadcount" class="form-input" value="1" min="1"></div>
        </div>
        
        <!-- Roles & Responsibilities -->
        <div class="form-group"><label>Roles & Responsibilities</label><textarea id="jobRoles" class="form-input" rows="4" placeholder="Key responsibilities..."></textarea></div>
        
        <!-- Row 5: Qualifications & Certifications -->
        <div style="display:grid;grid-template-columns:1fr 1fr;gap:12px;">
            <div class="form-group"><label>Qualifications</label><textarea id="jobQualifications" class="form-input" rows="3" placeholder="Required qualifications..."></textarea></div>
            <div class="form-group"><label>Certifications Required</label><input type="text" id="jobCertifications" class="form-input" placeholder="e.g. AWS Certified, PMP..."></div>
        </div>
        
        <!-- Skills & Description -->
        <div class="form-group"><label>Required Skills (comma separated)</label><input type="text" id="jobSkills" class="form-input" placeholder="Python, AWS, Docker..."></div>
        <div class="form-group"><label>Job Description</label><textarea id="jobDesc" class="form-input" rows="3" placeholder="Full job description..."></textarea></div>
        
                      <button id="createJobBtn" class="btn btn-primary">💾 Create Requirement</button>
    </div>
</div>   <!-- This closes createJobPanel -->


<div id="interviewsPanel" style="display:none;">
    <div class="card no-click">
        <h3>📅 Interview Tracker</h3>
        <div style="background:#F0F4FA;padding:14px;border-radius:8px;margin-bottom:14px;border:2px dashed #D0D8E4;">
            <strong>➕ Schedule Interview</strong>
            <div style="display:grid;grid-template-columns:1fr 1fr 1fr;gap:10px;margin-top:10px;">
                <div><label style="font-size:12px;">Candidate ID</label><div style="display:flex;align-items:center;background:#fff;border:1px solid #D0D8E4;border-radius:6px;"><span style="padding:8px 4px 8px 10px;color:#1B2A4A;font-weight:bold;font-size:14px;">SIT-C-</span><input type="text" id="intCandidateSearch" class="form-input" placeholder="001" style="border:none;flex:1;" oninput="searchInterviewCandidate()" list="intCandidateList"></div><datalist id="intCandidateList"></datalist></div>
                <div><label style="font-size:12px;">Date</label><input type="date" id="intDate" class="form-input"></div>
                <div><label style="font-size:12px;">Time</label><input type="time" id="intTime" class="form-input"></div>
            </div>
            <div style="display:grid;grid-template-columns:1fr 1fr 1fr;gap:10px;margin-top:10px;">
                <div><label style="font-size:12px;">Round</label><select id="intRound" class="form-input"><option value="L1">L1 - Technical</option><option value="L2">L2 - Technical</option><option value="L3">L3 - Architect</option><option value="Managerial">Managerial</option><option value="HR">HR Discussion</option><option value="Client">Client Round</option></select></div>
                <div><label style="font-size:12px;">Resource Owner</label><input type="text" id="intOwner" class="form-input" placeholder="HR Name"></div>
                <div><label style="font-size:12px;">Client Name</label><input type="text" id="intClient" class="form-input" placeholder="Client"></div>
            </div>
            <div style="display:grid;grid-template-columns:1fr 1fr;gap:10px;margin-top:10px;">
                <div><label style="font-size:12px;">Client POC</label><input type="text" id="intPOC" class="form-input" placeholder="Client Contact Person"></div>
                <div><label style="font-size:12px;">Requirement ID</label><div style="display:flex;align-items:center;background:#fff;border:1px solid #D0D8E4;border-radius:6px;"><span style="padding:8px 4px 8px 10px;color:#1B2A4A;font-weight:bold;font-size:13px;">SIT-R-</span><input type="text" id="intRequirement" class="form-input" placeholder="001" style="border:none;flex:1;" list="intReqList"></div><datalist id="intReqList"></datalist></div>
            </div>
            <button id="scheduleInterviewBtn" class="btn btn-primary" style="margin-top:12px;">📅 Schedule Interview</button>
        </div>
        <div style="display:flex;gap:10px;flex-wrap:wrap;margin-bottom:14px;align-items:center;">
            <input type="date" id="intFilterDate" class="form-input" style="width:160px;" onchange="loadInterviews()">
            <select id="intFilterRound" class="form-input" style="width:150px;" onchange="loadInterviews()">
                <option value="">All Rounds</option><option value="L1">L1</option><option value="L2">L2</option><option value="L3">L3</option><option value="Managerial">Managerial</option><option value="HR">HR</option><option value="Client">Client</option>
            </select>
            <select id="intFilterVerdict" class="form-input" style="width:150px;" onchange="loadInterviews()">
                <option value="">All Verdicts</option><option value="Scheduled">Scheduled</option><option value="Selected">Selected</option><option value="Rejected">Rejected</option><option value="Hold">On Hold</option><option value="No Show">No Show</option><option value="Rescheduled">Rescheduled</option>
            </select>
            <button class="btn btn-secondary" onclick="document.getElementById('intFilterDate').value='';document.getElementById('intFilterRound').value='';document.getElementById('intFilterVerdict').value='';loadInterviews();">🔄 Clear Filters</button>
        </div>
        <div id="interviewsList"></div>
    </div>
</div>

<div id="analyzePanel" style="display:none;">
    <div class="card no-click">
        <h3>🔍 AI Match Analysis - Single Candidate</h3>
        <div class="flex">
            <div class="flex-1"><select id="jobSelect"></select></div>
            <div class="flex-1"><select id="candidateSelect"></select></div>
        </div>
        <button id="analyzeBtn">🤖 Run Analysis</button>
        <div id="analysisResult"></div>
    </div>
    
    <div class="card no-click" style="margin-top: 20px;">
        <h3>📊 Match JD Against ALL Candidates</h3>
        <p>Select a Job to see how ALL candidates match (even 1% matches)</p>
        <div class="flex">
            <div class="flex-1"><select id="batchJobSelect"></select></div>
        </div>
        <button id="batchAnalyzeBtn">🎯 Match Against All Candidates</button>
        <div id="batchAnalysisResult"></div>
    </div>
</div>
</div>
    <!-- Dashboard Panel -->
    <div id="dashboardPanel" style="display:none;">
        <div class="card no-click">
        <div style="display:flex;gap:8px;margin-bottom:10px;">
    <button class="btn btn-sm btn-secondary" onclick="triggerBackup()">💾 Backup Now</button>
    <button class="btn btn-sm btn-secondary" onclick="window.open('/api/admin/export-pdf')">📄 Export PDF Report</button>
    <button class="btn btn-sm btn-secondary" onclick="listBackups()">📂 View Backups</button>
</div>
<div id="backupStatus" style="font-size:12px;margin-bottom:10px;"></div>
            <h3>📊 Recruitment Dashboard</h3>
            <div style="display:flex;gap:8px;margin-bottom:10px;">
    <button class="btn btn-sm btn-secondary" onclick="window.open('/api/admin/export-pdf')">📄 Export PDF Report</button>
</div>
            <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(150px, 1fr)); gap: 15px; margin-bottom: 20px;">
                <div style="background: #1A4D4A; color: white; padding: 15px; border-radius: 10px; text-align: center;">
                    <div style="font-size: 28px; font-weight: bold;" id="totalCandidates">0</div>
                    <div style="font-size: 12px;">Total Candidates</div>
                </div>
                <div style="background: #1B6B2E; color: white; padding: 15px; border-radius: 10px; text-align: center;">
                    <div style="font-size: 28px; font-weight: bold;" id="matchedCandidates">0</div>
                    <div style="font-size: 12px;">Matched (70%+)</div>
                </div>
                <div style="background: #2196F3; color: white; padding: 15px; border-radius: 10px; text-align: center;">
                    <div style="font-size: 28px; font-weight: bold;" id="hiredCandidates">0</div>
                    <div style="font-size: 12px;">Hired</div>
                </div>
                <div style="background: #F44336; color: white; padding: 15px; border-radius: 10px; text-align: center;">
                    <div style="font-size: 28px; font-weight: bold;" id="rejectedCandidates">0</div>
                    <div style="font-size: 12px;">Rejected</div>
                </div>
            </div>
            <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 20px;">
                <div style="background: white; padding: 15px; border-radius: 8px;">
                    <h4>Match Score Distribution</h4>
                    <canvas id="matchChart" height="200"></canvas>
                </div>
                <div style="background: white; padding: 15px; border-radius: 8px;">
                    <h4>Pipeline Funnel</h4>
                    <canvas id="pipelineChart" height="200"></canvas>
                </div>
            </div>
            <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 20px; margin-top: 20px;">
                <div style="background: white; padding: 15px; border-radius: 8px;">
                    <h4>Top Skills</h4>
                    <div id="skillsCloud" style="min-height: 100px; display: flex; flex-wrap: wrap; gap: 8px; align-items: center;"></div>
                </div>
                <div style="background: white; padding: 15px; border-radius: 8px;">
                    <h4>Candidates Over Time</h4>
                    <canvas id="trendChart" height="200"></canvas>
                </div>
                      </div>
        </div>
    </div>

<div id="reportsPanel" style="display:none;">
    <div class="card no-click" style="max-width:100%;">
        <h3>📈 Daily Activity Report</h3>
        <div style="display:flex;gap:10px;align-items:center;margin-bottom:15px;">
            <input type="date" id="reportDate" class="form-input" style="width:200px;" onchange="loadDailyReport()">
            <button class="btn btn-secondary" onclick="document.getElementById('reportDate').value = new Date().toISOString().split('T')[0]; loadDailyReport();">📅 Today</button>
        </div>
        <div id="dailyReportContent"></div>
    </div>
</div>
<div id="kanbanPanel" style="display:none;">
    <div class="card no-click">
        <h3>📋 Kanban Board</h3>
        <div id="kanbanBoard" style="display:flex;flex-direction:row;gap:10px;overflow-x:auto;padding:10px 0;max-height:70vh;"></div>
    </div>
</div>

<div id="onboardedPanel" style="display:none;">
    <div class="card no-click">
        <h3>💰 Finance Dashboard</h3>
        
        <!-- Summary Cards -->
        <div style="display:grid;grid-template-columns:repeat(auto-fit,minmax(180px,1fr));gap:15px;margin-bottom:20px;">
            <div style="background:linear-gradient(135deg,#1B5E20,#43A047);color:#fff;padding:20px;border-radius:12px;text-align:center;box-shadow:0 4px 15px rgba(0,0,0,0.1);">
                <div style="font-size:28px;font-weight:700;" id="finTotalRevenue">₹0</div>
                <div style="font-size:12px;text-transform:uppercase;opacity:0.9;">Total Monthly Revenue</div>
            </div>
            <div style="background:linear-gradient(135deg,#0D47A1,#1E88E5);color:#fff;padding:20px;border-radius:12px;text-align:center;box-shadow:0 4px 15px rgba(0,0,0,0.1);">
                <div style="font-size:28px;font-weight:700;" id="finTotalSalary">₹0</div>
                <div style="font-size:12px;text-transform:uppercase;opacity:0.9;">Total Monthly Salary</div>
            </div>
            <div style="background:linear-gradient(135deg,#E65100,#F57C00);color:#fff;padding:20px;border-radius:12px;text-align:center;box-shadow:0 4px 15px rgba(0,0,0,0.1);">
                <div style="font-size:28px;font-weight:700;" id="finTotalProfit">₹0</div>
                <div style="font-size:12px;text-transform:uppercase;opacity:0.9;">Monthly Profit</div>
            </div>
            <div style="background:linear-gradient(135deg,#4A148C,#7B1FA2);color:#fff;padding:20px;border-radius:12px;text-align:center;box-shadow:0 4px 15px rgba(0,0,0,0.1);">
                <div style="font-size:28px;font-weight:700;" id="finAvgMargin">0%</div>
                <div style="font-size:12px;text-transform:uppercase;opacity:0.9;">Avg Profit Margin</div>
            </div>
            <div style="background:linear-gradient(135deg,#004D40,#00796B);color:#fff;padding:20px;border-radius:12px;text-align:center;box-shadow:0 4px 15px rgba(0,0,0,0.1);">
                <div style="font-size:28px;font-weight:700;" id="finActiveResources">0</div>
                <div style="font-size:12px;text-transform:uppercase;opacity:0.9;">Active Resources</div>
            </div>
        </div>
        
        </div>
</div>
</div>   <!-- closes the previous panel -->

<div id="financePanel" style="display:none;">
    <div class="card no-click">
        <h3>💰 Finance Dashboard</h3>
        <!-- Summary Cards -->
        <div style="display:grid;grid-template-columns:repeat(auto-fit,minmax(180px,1fr));gap:15px;margin-bottom:20px;">
            <div style="background:linear-gradient(135deg,#1B5E20,#43A047);color:#fff;padding:20px;border-radius:12px;text-align:center;box-shadow:0 4px 15px rgba(0,0,0,0.1);">
                <div style="font-size:28px;font-weight:700;" id="finTotalRevenue">₹0</div>
                <div style="font-size:12px;text-transform:uppercase;opacity:0.9;">Total Monthly Revenue</div>
            </div>
            <div style="background:linear-gradient(135deg,#0D47A1,#1E88E5);color:#fff;padding:20px;border-radius:12px;text-align:center;box-shadow:0 4px 15px rgba(0,0,0,0.1);">
                <div style="font-size:28px;font-weight:700;" id="finTotalSalary">₹0</div>
                <div style="font-size:12px;text-transform:uppercase;opacity:0.9;">Total Monthly Salary</div>
            </div>
            <div style="background:linear-gradient(135deg,#E65100,#F57C00);color:#fff;padding:20px;border-radius:12px;text-align:center;box-shadow:0 4px 15px rgba(0,0,0,0.1);">
                <div style="font-size:28px;font-weight:700;" id="finTotalProfit">₹0</div>
                <div style="font-size:12px;text-transform:uppercase;opacity:0.9;">Monthly Profit</div>
            </div>
            <div style="background:linear-gradient(135deg,#4A148C,#7B1FA2);color:#fff;padding:20px;border-radius:12px;text-align:center;box-shadow:0 4px 15px rgba(0,0,0,0.1);">
                <div style="font-size:28px;font-weight:700;" id="finAvgMargin">0%</div>
                <div style="font-size:12px;text-transform:uppercase;opacity:0.9;">Avg Profit Margin</div>
            </div>
            <div style="background:linear-gradient(135deg,#004D40,#00796B);color:#fff;padding:20px;border-radius:12px;text-align:center;box-shadow:0 4px 15px rgba(0,0,0,0.1);">
                <div style="font-size:28px;font-weight:700;" id="finActiveResources">0</div>
                <div style="font-size:12px;text-transform:uppercase;opacity:0.9;">Active Resources</div>
            </div>
        </div>
        <div id="financeBreakdown"></div>
    </div>
</div>

<div id="onboardedPanel" style="display:none;">
    <div class="card no-click">
        <h3>💼 Onboarded Resources</h3>
        <div style="background:#F0F4FA;padding:14px;border-radius:8px;margin-bottom:14px;border:2px dashed #D0D8E4;">
            <strong>➕ Onboard New Resource</strong>
            <div style="display:grid;grid-template-columns:1fr 1fr 1fr;gap:10px;margin-top:10px;">
                <div><label style="font-size:12px;">Candidate</label><div style="display:flex;align-items:center;background:#fff;border:1px solid #D0D8E4;border-radius:6px;"><span style="padding:8px 4px 8px 10px;color:#1B2A4A;font-weight:bold;font-size:14px;">SIT-C-</span><input type="text" id="onbCandidate" class="form-input" placeholder="001" style="border:none;flex:1;" list="onbCandidateList" oninput="searchOnbCandidate()"></div><datalist id="onbCandidateList"></datalist></div>
                <div><label style="font-size:12px;">Client</label><input type="text" id="onbClient" class="form-input" placeholder="Client name"></div>
                <div><label style="font-size:12px;">DOJ</label><input type="date" id="onbDOJ" class="form-input"></div>
            </div>
            <div style="display:grid;grid-template-columns:1fr 1fr 1fr;gap:10px;margin-top:10px;">
                <div><label style="font-size:12px;">Monthly Salary (₹)</label><input type="number" id="onbSalary" class="form-input" placeholder="50000"></div>
                <div><label style="font-size:12px;">Billing Rate (₹)</label><input type="number" id="onbBilling" class="form-input" placeholder="75000"></div>
                <div><label style="font-size:12px;">Resource Owner</label><input type="text" id="onbOwner" class="form-input" placeholder="HR Name"></div>
            </div>
            <div style="display:grid;grid-template-columns:1fr 1fr;gap:10px;margin-top:10px;">
                <div><label style="font-size:12px;">Work Location</label><input type="text" id="onbLocation" class="form-input" placeholder="Remote/Hybrid/Onsite"></div>
                <div><label style="font-size:12px;">Business Model</label><select id="onbModel" class="form-input"><option value="C2C">C2C</option><option value="C2H">C2H</option><option value="FTE">FTE</option><option value="Fixed Price">Fixed Price</option></select></div>
            </div>
            <div style="display:grid;grid-template-columns:1fr 1fr;gap:10px;margin-top:10px;">
                <div><label style="font-size:12px;">Requirement ID</label><div style="display:flex;align-items:center;background:#fff;border:1px solid #D0D8E4;border-radius:6px;"><span style="padding:8px 4px 8px 10px;color:#1B2A4A;font-weight:bold;font-size:13px;">SIT-R-</span><input type="text" id="onbRequirementId" class="form-input" placeholder="001" style="border:none;flex:1;" list="onbReqList" oninput="searchOnbRequirement()"></div><datalist id="onbReqList"></datalist></div>
                <div><label style="font-size:12px;">PO Number</label><input type="text" id="onbPO" class="form-input" placeholder="PO-001"></div>
            </div>
            <div style="margin-top:10px;"><label style="font-size:12px;">Attach Documents (PO/SOW/Offer Letter)</label><input type="file" id="onbDocuments" multiple accept=".pdf,.docx,.doc" style="font-size:12px;"></div>
            <button id="onboardBtn" class="btn btn-primary" style="margin-top:12px;">💼 Onboard Resource</button>
        </div>
        <div id="onboardedList"></div>
    </div>
</div>

<div id="usersPanel" style="display:none;">
    <div class="card no-click">
        <h3>👥 User Management</h3>
        <div style="background:#F0F4FA;padding:14px;border-radius:8px;margin-bottom:14px;border:2px dashed #D0D8E4;">
            <strong>➕ Add New User</strong>
            <div style="display:grid;grid-template-columns:1fr 1fr 1fr 1fr;gap:10px;margin-top:10px;">
                <div><label style="font-size:12px;">Full Name</label><input type="text" id="newUserName" class="form-input" placeholder="John Doe"></div>
                <div><label style="font-size:12px;">Email</label><input type="email" id="newUserEmail" class="form-input" placeholder="john@shahnait.com"></div>
                <div><label style="font-size:12px;">Password</label><input type="password" id="newUserPassword" class="form-input" placeholder="Min 6 characters"></div>
                <div><label style="font-size:12px;">Role</label><select id="newUserRole" class="form-input"><option value="admin">Admin</option><option value="manager">Manager</option><option value="recruiter">Recruiter</option></select></div>
            </div>
            <button id="addUserBtn" class="btn btn-primary" style="margin-top:12px;">➕ Add User</button>
            <div id="addUserStatus" style="margin-top:6px;font-size:12px;"></div>
        </div>
        <div id="usersList"></div>
    </div>
</div>


<!-- ============================================ -->
<!-- MODALS - SHAHNAIT SCOUT                     -->
<!-- ============================================ -->

<!-- CANDIDATE PROFILE MODAL -->
<div id="candidateModal" class="modal">
    <div class="modal-content modal-xl">
        <div class="modal-header">
            <h2 id="modalCandidateName">Candidate Profile</h2>
            <div style="display:flex;align-items:center;gap:15px;">
                <span id="modalHRName" style="font-size:13px;opacity:0.9;"></span>
                <span class="close" onclick="closeModal()">&times;</span>
            </div>
        </div>
        <div class="modal-body" id="modalBody" style="padding:0;">
            <!-- AI Summary Section -->
            <div id="aiSummarySection" style="display:none;background:#F0F4FA;padding:14px 20px;border-bottom:2px solid #D0D8E4;margin:0;">
                <div style="display:flex;align-items:center;gap:8px;margin-bottom:6px;">
                    <i class="fas fa-robot" style="color:#1B2A4A;font-size:16px;"></i>
                    <strong style="color:#1B2A4A;">AI Analysis Summary</strong>
                    <span id="aiMatchedJD" style="font-size:12px;background:#1B2A4A;color:#fff;padding:2px 10px;border-radius:12px;"></span>
                </div>
                <p id="aiSummaryText" style="margin:4px 0 0 0;font-size:14px;color:#0F1D33;line-height:1.7;max-height:300px;overflow-y:auto;white-space:pre-wrap;padding:8px 12px;background:#FFFFFF;border-radius:6px;border:1px solid #D0D8E4;"></p>
            </div>
            
            <!-- Main Content Grid -->
<!-- Main Content -->
<div style="display:grid;grid-template-columns:1fr 1fr;gap:16px;padding:16px;">
    
    <!-- LEFT COLUMN -->
    <div style="min-width:0;">
        <!-- Basic Info -->
        <div class="modal-section">
            <h3 class="modal-section-title"><i class="fas fa-user"></i> Basic Information</h3>
            <div class="form-row">
                <div class="form-group"><label>First Name</label><input type="text" id="edit_first_name" class="form-input"></div>
                <div class="form-group"><label>Last Name</label><input type="text" id="edit_last_name" class="form-input"></div>
            </div>
            <div class="form-row">
                <div class="form-group"><label>Email ID</label><input type="email" id="edit_email" class="form-input"></div>
                <div class="form-group"><label>Phone Number</label><input type="text" id="edit_phone" class="form-input"></div>
            </div>
            <div class="form-row">
                <div class="form-group"><label>Designation</label><input type="text" id="edit_designation" class="form-input"></div>
                <div class="form-group"><label>LinkedIn</label><input type="text" id="edit_linkedin" class="form-input"></div>
            </div>
            <div class="form-row">
                <div class="form-group"><label>Location</label><input type="text" id="edit_location" class="form-input"></div>
                <div class="form-group"><label>Years of Experience</label><input type="text" id="edit_years_exp" class="form-input"></div>
            </div>
        </div>
        
        <!-- Compensation -->
        <div class="modal-section">
            <h3 class="modal-section-title"><i class="fas fa-money-bill-wave"></i> Compensation</h3>
            <div class="form-row">
                <div class="form-group"><label>Current CTC</label><input type="text" id="edit_current_ctc" class="form-input"></div>
                <div class="form-group"><label>Expected CTC</label><input type="text" id="edit_expected_ctc" class="form-input"></div>
            </div>
        </div>
        
        <!-- Skills -->
        <div class="modal-section">
            <h3 class="modal-section-title"><i class="fas fa-code"></i> Skill Sets</h3>
            <div id="skillsContainer" style="display:flex;flex-wrap:wrap;gap:6px;min-height:30px;"></div>
            <div style="display:flex;gap:6px;margin-top:8px;">
                <input type="text" id="newSkillInput" class="form-input" placeholder="Add skill..." style="flex:1;">
                <button class="btn btn-sm" onclick="addSkillToCandidate()">+</button>
            </div>
        </div>
    </div>
    
    <!-- RIGHT COLUMN -->
    <div style="min-width:0;">
        <!-- Proposed Info -->
        <div class="modal-section">
            <h3 class="modal-section-title"><i class="fas fa-building"></i> Proposed To</h3>
            <div class="form-row">
                <div class="form-group">
                    <label>Client</label>
                    <div style="display:flex;gap:4px;align-items:center;">
                        <select id="edit_proposed_client" class="form-input" style="flex:1;min-width:0;" onchange="loadRequirementsForClient()">
                            <option value="">-- Select Client --</option>
                        </select>
                        <button class="btn btn-sm" onclick="addNewClient()" style="white-space:nowrap;padding:8px 10px;flex-shrink:0;">+</button>
                    </div>
                </div>
                <div class="form-group">
                    <label>Requirement</label>
                    <div style="display:flex;gap:4px;align-items:center;">
                        <input type="text" id="edit_proposed_requirement" class="form-input" style="flex:1;min-width:0;" list="requirementList" placeholder="Search SIT-R-XXX..." oninput="filterRequirementDropdown()" autocomplete="off">
                        <datalist id="requirementList"></datalist>
                        <button class="btn btn-sm" onclick="addNewRequirement()" style="white-space:nowrap;padding:8px 10px;flex-shrink:0;">+</button>
                    </div>
                </div>
            </div>
        </div>
        
        <!-- Candidate Stage -->
        <div class="modal-section">
            <h3 class="modal-section-title"><i class="fas fa-flag-checkered"></i> Candidate Stage</h3>
            <select id="edit_stage" class="form-input" onchange="updateStageColor()">
                <option value="new">🆕 New</option>
                <option value="proposed">📋 Proposed</option>
                <option value="screening">🔍 Screening</option>
                <option value="technical_l1">💻 Technical L1</option>
                <option value="technical_l2">💻 Technical L2</option>
                <option value="technical_l3">💻 Technical L3</option>
                <option value="rejected">❌ Rejected</option>
                <option value="shortlisted">⭐ Shortlisted</option>
                <option value="offer_letter_shared">📄 Offer Shared</option>
                <option value="onboarded">✅ Onboarded</option>
            </select>
            <div id="stageColorBar" style="height:6px;border-radius:3px;margin-top:6px;"></div>
        </div>
        
        <!-- Work History -->
        <div class="modal-section">
            <h3 class="modal-section-title"><i class="fas fa-briefcase"></i> Work History</h3>
            <div id="workHistoryContainer"></div>
            <button class="btn btn-sm btn-secondary" onclick="addWorkEntry()" style="margin-top:6px;">+ Add</button>
        </div>
        
        <!-- Certifications -->
        <div class="modal-section">
            <h3 class="modal-section-title"><i class="fas fa-certificate"></i> Certifications</h3>
            <div id="certificationsContainer"></div>
            <button class="btn btn-sm btn-secondary" onclick="addCertification()" style="margin-top:6px;">+ Add</button>
        </div>
        
        <!-- Attachments -->
        <div class="modal-section">
            <h3 class="modal-section-title"><i class="fas fa-paperclip"></i> Attachments</h3>
            <div id="attachmentsList" style="margin-bottom:8px;"></div>
            <input type="file" id="attachmentFileInput" multiple style="display:none;" onchange="uploadAttachments()">
            <button class="btn btn-sm btn-secondary" onclick="document.getElementById('attachmentFileInput').click()">📎 Attach Files</button>
        </div>
    </div>
</div>
            <!-- FULL WIDTH: Resume Section -->
            <div style="padding:0 20px 20px 20px;">
                <div class="modal-section">
                    <h3 class="modal-section-title"><i class="fas fa-file-alt"></i> Resume</h3>
                    <div style="display:flex;gap:8px;flex-wrap:wrap;margin-bottom:10px;">
                        <button class="btn btn-sm" onclick="viewOriginalResume(currentCandidateId)"><i class="fas fa-external-link-alt"></i> View Original Resume</button>
                        <button class="btn btn-sm btn-secondary" onclick="downloadOriginalResume(currentCandidateId)"><i class="fas fa-download"></i> Download Resume</button>
                        <button class="btn btn-sm btn-secondary" onclick="copyResumeText()"><i class="fas fa-copy"></i> Copy Text</button>
                    </div>
                    <div id="resumeFullText" style="background:#F5F7FA;border:2px solid #D0D8E4;border-radius:8px;padding:16px;max-height:400px;overflow-y:auto;font-size:13px;line-height:1.6;white-space:pre-wrap;color:#0F1D33;font-family:'Times New Roman',serif;"></div>
                </div>
                
                <!-- Notes -->
                <div class="modal-section">
                    <h3 class="modal-section-title"><i class="fas fa-sticky-note"></i> Notes</h3>
                    <textarea id="edit_notes" class="form-input" rows="3" placeholder="Add notes about this candidate..."></textarea>
                </div>
                
                <!-- Action Buttons -->
                <div style="display:flex;gap:10px;flex-wrap:wrap;margin-top:10px;padding-top:15px;border-top:2px solid #E2E8F0;">
                    <button class="btn btn-primary" onclick="saveCandidateChanges()"><i class="fas fa-save"></i> Save Changes</button>
                    <button class="btn btn-secondary" onclick="generateCandidatePDF()"><i class="fas fa-file-pdf"></i> Generate PDF Report</button>
                    <button class="btn btn-secondary" onclick="runAIAnalysis()"><i class="fas fa-robot"></i> Run AI Analysis</button>
                    <button class="btn btn-danger" onclick="closeModal()" style="margin-left:auto;">Close</button>
                </div>
            </div>
        </div>
    </div>
</div>

<!-- EDIT JOB MODAL -->
<div id="editJobModal" class="modal">
    <div class="modal-content">
        <div class="modal-header"><h2>✏️ Edit Job</h2><span class="close" onclick="closeEditJobModal()">&times;</span></div>
        <div class="modal-body" id="editJobModalBody"></div>
    </div>
</div>

<!-- PREVIEW MODAL -->
<div id="previewModal" class="modal">
    <div class="modal-content modal-xl">
        <div class="modal-header"><h2>Preview</h2><span class="close" onclick="closePreviewModal()">&times;</span></div>
        <div class="modal-body" id="previewBody"></div>
    </div>
</div>

<script>
// ============================================
// AUTHENTICATION
// ============================================
let currentUser = null;

async function checkAuth() {
    try {
        const res = await fetch('/api/auth/me');
        if (res.ok) {
            const data = await res.json();
            currentUser = data.user;
            document.getElementById('loginOverlay').style.display = 'none';
            document.getElementById('userDisplayName').textContent = currentUser.full_name || currentUser.email;
            document.getElementById('userDisplayRole').textContent = currentUser.role.toUpperCase();
            
            // Hide Users tab for non-admins
            const tabUsers = document.getElementById('tabUsers');
            if (tabUsers && currentUser.role !== 'admin') {
                tabUsers.style.display = 'none';
            }
            
                        loadDashboard();
            if (currentUser.role === 'admin') {
                document.querySelectorAll('.admin-only').forEach(el => el.style.display = 'block');
            }
        }
    } catch(e) {
        console.log('Not logged in');
    }
}

async function handleLogin(e) {
    e.preventDefault();
    const email = document.getElementById('loginEmail').value;
    const password = document.getElementById('loginPassword').value;
    const errorDiv = document.getElementById('loginError');
    errorDiv.style.display = 'none';
    try {
        const res = await fetch('/api/auth/login', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({ email, password })
        });
        const data = await res.json();
        if (res.ok) {
            currentUser = data.user;
            document.getElementById('loginOverlay').style.display = 'none';
            document.getElementById('userDisplayName').textContent = currentUser.full_name || currentUser.email;
                       document.getElementById('userDisplayRole').textContent = currentUser.role.toUpperCase();
            
            // Hide Users tab for non-admins
            const tabUsers = document.getElementById('tabUsers');
            if (tabUsers && currentUser.role !== 'admin') {
                tabUsers.style.display = 'none';
            }
            
                        loadDashboard();
            if (currentUser.role === 'admin') {
                document.querySelectorAll('.admin-only').forEach(el => el.style.display = 'block');
            }
            toastSuccess('Welcome, ' + currentUser.full_name + '!');
        } else {
            errorDiv.textContent = data.error || 'Login failed';
            errorDiv.style.display = 'block';
        }
    } catch(e) {
        errorDiv.textContent = 'Network error. Please try again.';
        errorDiv.style.display = 'block';
    }
}

async function logout() {
    await fetch('/api/auth/logout', { method: 'POST' });
    currentUser = null;
    document.getElementById('loginOverlay').style.display = 'flex';
    document.getElementById('loginEmail').value = '';
    document.getElementById('loginPassword').value = '';
}

checkAuth();

    let allJobs = [], allCandidates = [], currentCandidateId = null;
    let currentCandidateData = null;
    let selectedBulkFiles = [];
    console.log('✅ App initialized');
console.log('✅ loadNotes:', typeof loadNotes);
console.log('✅ addNote:', typeof addNote);
console.log('✅ deleteNote:', typeof deleteNote);
console.log('✅ viewCandidate:', typeof viewCandidate);
console.log('✅ viewOriginalResume:', typeof viewOriginalResume);
// ============================================
// SIDEBAR TOGGLE FOR MOBILE
// ============================================
function toggleSidebar() {
    const sidebar = document.getElementById('sidebar');
    const overlay = document.getElementById('sidebarOverlay');
    
    if (window.innerWidth <= 768) {
        if (sidebar.style.position !== 'fixed') {
            sidebar.style.position = 'fixed';
            sidebar.style.top = '0';
            sidebar.style.left = '-280px';
            sidebar.style.width = '260px';
            sidebar.style.height = '100vh';
            sidebar.style.zIndex = '1000';
            sidebar.style.paddingTop = '60px';
            sidebar.style.transition = 'left 0.3s ease';
        }
        sidebar.classList.toggle('open');
        sidebar.style.left = sidebar.classList.contains('open') ? '0' : '-280px';
    } else {
        sidebar.classList.toggle('open');
    }
    
    if (overlay) overlay.classList.toggle('active');
}

function toggleSidebarGroup(header) {
    header.classList.toggle('open');
    const items = header.nextElementSibling;
    items.classList.toggle('open');
}

// Close sidebar when clicking outside (on mobile)
document.addEventListener('click', function(event) {
    const sidebar = document.getElementById('sidebar');
    const menuBtn = document.querySelector('.mobile-menu-btn');
    
    if (window.innerWidth <= 768) {
        if (sidebar && !sidebar.contains(event.target) && menuBtn && !menuBtn.contains(event.target)) {
            sidebar.classList.remove('open');
        }
    }
});

// Close sidebar when a tab is clicked (on mobile)
document.querySelectorAll('.tab-btn').forEach(function(btn) {
    btn.addEventListener('click', function() {
        if (window.innerWidth <= 768) {
            const sidebar = document.getElementById('sidebar');
            if (sidebar) {
                sidebar.classList.remove('open');
            }
        }
    });
});
// ============================================
// VIEW CANDIDATE - FULL MODAL VERSION
// ============================================
window.viewCandidate = function(id) {
    console.log('Opening candidate:', id);
    currentCandidateId = id;
    
    const candidate = allCandidates.find(c => c.id == id);
    if (!candidate) {
        toastError('Candidate not found');
        return;
    }
    
    currentCandidateData = candidate;
    
    // Set HR name in header
    document.getElementById('modalHRName').innerHTML = 
    '<span style="background:#fff;color:#1B2A4A;padding:3px 12px;border-radius:14px;font-weight:700;font-size:13px;margin-right:12px;">SIT-C-' + String(candidate.id).padStart(3,'0') + '</span>' +
    '<i class="fas fa-user-circle"></i> Uploaded by: ' + escapeHtml(String(candidate.uploaded_by_name || 'ShahnaIT HR'));
    document.getElementById('modalCandidateName').textContent = (candidate.first_name || '') + ' ' + (candidate.last_name || '');
    
    // AI Summary
    if (candidate.analysis_summary) {
        document.getElementById('aiSummarySection').style.display = 'block';
        document.getElementById('aiSummaryText').textContent = candidate.analysis_summary;
        document.getElementById('aiMatchedJD').textContent = candidate.matched_jd || 'Analysis';
    } else {
        document.getElementById('aiSummarySection').style.display = 'none';
    }
    
    // Basic Info
    document.getElementById('edit_first_name').value = candidate.first_name || '';
    document.getElementById('edit_last_name').value = candidate.last_name || '';
    document.getElementById('edit_email').value = candidate.email || '';
    document.getElementById('edit_phone').value = candidate.phone || '';
    document.getElementById('edit_designation').value = candidate.designation || candidate.current_role || '';
    document.getElementById('edit_linkedin').value = candidate.linkedin || '';
    document.getElementById('edit_location').value = candidate.location || candidate.address || '';
    document.getElementById('edit_years_exp').value = candidate.years_of_experience || '';
    
    // Compensation
    document.getElementById('edit_current_ctc').value = candidate.current_ctc || '';
    document.getElementById('edit_expected_ctc').value = candidate.expected_ctc || '';
    
    // Proposed
    document.getElementById('edit_proposed_client').value = candidate.proposed_client || '';
    // Requirement will be set by loadRequirementsForClient(), just store the ID
    document.getElementById('edit_proposed_requirement').value = candidate.proposed_requirement || '';
    document.getElementById('edit_proposed_requirement').setAttribute('data-saved-id', candidate.proposed_requirement || '');
    // Stage
    document.getElementById('edit_stage').value = candidate.stage || 'new';
    updateStageColor();
    
    // Skills
    renderSkills(candidate.core_skills);
    
    // Work History
    renderWorkHistory(candidate.work_experience);
    
    // Certifications
    renderCertifications(candidate.certifications);
    
    // Attachments
    renderAttachments(candidate.attachments);
    
    // Resume - FULL TEXT, NO TRUNCATION
    const resumeText = candidate.resume_text || '';
    document.getElementById('resumeFullText').textContent = resumeText;
    
    // Notes
    document.getElementById('edit_notes').value = candidate.notes || '';
    
    // Show modal
    document.getElementById('candidateModal').style.display = 'block';
};

// ============================================
// HELPER FUNCTIONS
// ============================================
function escapeHtml(str) {
    str = String(str || '');
    const div = document.createElement('div');
    div.textContent = str;
    return div.innerHTML;
}

function renderSkills(skillsData) {
    const container = document.getElementById('skillsContainer');
    container.innerHTML = '';
    let skills = [];
try {
    if (skillsData) {
        skills = typeof skillsData === 'string' ? JSON.parse(skillsData) : skillsData;
    }
} catch(e) { skills = []; }
if (!Array.isArray(skills)) skills = [];
    
    if (!Array.isArray(skills) || skills.length === 0) {
        container.innerHTML = '<span style="color:#94A3B8;font-size:13px;">No skills added</span>';
        return;
    }
    
    skills.forEach((skill, index) => {
        const tag = document.createElement('span');
        tag.className = 'skill-tag editable-skill';
        tag.innerHTML = escapeHtml(String(typeof skill === 'object' ? (skill.skill || skill.name || '') : skill)) + ' <i class="fas fa-times" style="cursor:pointer;margin-left:4px;font-size:10px;" onclick="removeSkill(' + index + ')"></i>';
        container.appendChild(tag);
    });
}

function renderWorkHistory(workData) {
    const container = document.getElementById('workHistoryContainer');
    container.innerHTML = '';
    let work = [];
    try {
        work = typeof workData === 'string' ? JSON.parse(workData) : (workData || []);
    } catch(e) { work = []; }
    
    if (!Array.isArray(work) || work.length === 0) {
        container.innerHTML = '<span style="color:#94A3B8;font-size:13px;">No work history</span>';
        return;
    }
    
    work.forEach((w, index) => {
        const div = document.createElement('div');
        div.className = 'company-item';
        div.style.cssText = 'display:flex;justify-content:space-between;align-items:center;margin-bottom:4px;';
        div.innerHTML = '<span><strong>' + escapeHtml(String(w.company || w || '')) + '</strong></span>' +
            '<i class="fas fa-times" style="cursor:pointer;color:#C42020;font-size:12px;" onclick="removeWorkEntry(' + index + ')"></i>';
        container.appendChild(div);
    });
}

function renderCertifications(certsData) {
    const container = document.getElementById('certificationsContainer');
    container.innerHTML = '';
    let certs = [];
    try {
        certs = typeof certsData === 'string' ? JSON.parse(certsData) : (certsData || []);
    } catch(e) { certs = []; }
    
    if (!Array.isArray(certs) || certs.length === 0) {
        container.innerHTML = '<span style="color:#94A3B8;font-size:13px;">No certifications</span>';
        return;
    }
    
    certs.forEach((cert, index) => {
        const div = document.createElement('div');
        div.className = 'company-item';
        div.style.cssText = 'display:flex;justify-content:space-between;align-items:center;margin-bottom:4px;';
        div.innerHTML = '<span>📜 ' + escapeHtml(String(cert)) + '</span>' +
            '<i class="fas fa-times" style="cursor:pointer;color:#C42020;font-size:12px;" onclick="removeCertification(' + index + ')"></i>';
        container.appendChild(div);
    });
}
function renderAttachments(attachmentsData) {
    const container = document.getElementById('attachmentsList');
    if (!container) return;
    container.innerHTML = '';
    
    let attachments = [];
    try {
        attachments = typeof attachmentsData === 'string' ? JSON.parse(attachmentsData) : (attachmentsData || []);
    } catch(e) { attachments = []; }
    
    if (!Array.isArray(attachments) || attachments.length === 0) {
        container.innerHTML = '<span style="color:#94A3B8;font-size:13px;">No attachments</span>';
        return;
    }
    
    attachments.forEach((att, index) => {
        const filename = att.filename || att.original_name || att;
        const div = document.createElement('div');
        div.style.cssText = 'display:flex;justify-content:space-between;align-items:center;padding:6px 0;font-size:13px;border-bottom:1px solid #E2E8F0;';
        div.innerHTML = '<span>📎 ' + escapeHtml(String(filename)) + '</span>' +
            '<div style="display:flex;gap:8px;">' +
'<i class="fas fa-eye" style="cursor:pointer;color:#2C7A4A;" onclick="viewAttachment(&quot;' + escapeHtml(String(filename)) + '&quot;)" title="View"></i>' +
'<i class="fas fa-download" style="cursor:pointer;color:#1B2A4A;" onclick="downloadAttachment(&quot;' + escapeHtml(String(filename)) + '&quot;)" title="Download"></i>' +
'<i class="fas fa-trash" style="cursor:pointer;color:#C42020;" onclick="deleteAttachment(&quot;' + escapeHtml(String(filename)) + '&quot;)" title="Delete"></i>' +
            '</div>';
        container.appendChild(div);
    });
}

function downloadAttachment(filename) {
    if (!currentCandidateId) return;
    window.open('/api/candidates/' + currentCandidateId + '/attachments/' + filename, '_blank');
}

function viewAttachment(filename) {
    if (!currentCandidateId) return;
    window.open('/api/candidates/' + currentCandidateId + '/attachments/' + filename + '?view=1', '_blank');
}

async function deleteAttachment(filename) {
    if (!currentCandidateId) return;
    if (!confirm('Delete "' + filename + '"?')) return;
    
    try {
        const res = await fetch('/api/candidates/' + currentCandidateId + '/attachments/' + filename, {
            method: 'DELETE'
        });
        const result = await res.json();
        
        if (result.success) {
            toastSuccess('File deleted');
            const candidateRes = await fetch('/api/candidates/' + currentCandidateId);
            const candidate = await candidateRes.json();
            currentCandidateData = candidate;
            renderAttachments(candidate.attachments);
        } else {
            toastError('Failed to delete');
        }
    } catch(e) {
        toastError('Error: ' + e.message);
    }
}

function updateStageColor() {
    const stage = document.getElementById('edit_stage').value;
    const colorBar = document.getElementById('stageColorBar');
    const colors = {
        'new': '#1B5F8C',
        'proposed': '#6B4CB8',
        'screening': '#B85C00',
        'technical_l1': '#0D7B4A',
        'technical_l2': '#0D7B4A',
        'technical_l3': '#0A5C35',
        'rejected': '#C42020',
        'shortlisted': '#D4A800',
        'offer_letter_shared': '#2C7A4A',
        'onboarded': '#1B5F8C'
    };
    colorBar.style.background = colors[stage] || '#1B2A4A';
}

// Skill Management
function addSkillToCandidate() {
    const input = document.getElementById('newSkillInput');
    const skill = input.value.trim();
    if (!skill) return;
    
let skills = [];
try {
    skills = typeof currentCandidateData.core_skills === 'string' ? JSON.parse(currentCandidateData.core_skills) : (currentCandidateData.core_skills || []);
} catch(e) { skills = []; }
if (!Array.isArray(skills)) skills = [];

skills.push(skill);
    currentCandidateData.core_skills = skills;
    renderSkills(skills);
    input.value = '';
}

function removeSkill(index) {
let skills = [];
try {
    skills = typeof currentCandidateData.core_skills === 'string' ? JSON.parse(currentCandidateData.core_skills) : (currentCandidateData.core_skills || []);
} catch(e) { skills = []; }
if (!Array.isArray(skills)) skills = [];
skills.splice(index, 1);
    currentCandidateData.core_skills = skills;
    renderSkills(skills);
}

function addWorkEntry() {
    const company = prompt('Enter company name:');
    if (!company) return;
let work = [];
try {
    work = typeof currentCandidateData.work_experience === 'string' ? JSON.parse(currentCandidateData.work_experience) : (currentCandidateData.work_experience || []);
} catch(e) { work = []; }
if (!Array.isArray(work)) work = [];
work.push({company: company});
    currentCandidateData.work_experience = work;
    renderWorkHistory(work);
}

function removeWorkEntry(index) {
    let work = [];
    try {
        work = typeof currentCandidateData.work_experience === 'string' ? JSON.parse(currentCandidateData.work_experience) : (currentCandidateData.work_experience || []);
    } catch(e) { work = []; }
    work.splice(index, 1);
    currentCandidateData.work_experience = work;
    renderWorkHistory(work);
}

function addCertification() {
    const cert = prompt('Enter certification name:');
    if (!cert) return;
let certs = [];
try {
    certs = typeof currentCandidateData.certifications === 'string' ? JSON.parse(currentCandidateData.certifications) : (currentCandidateData.certifications || []);
} catch(e) { certs = []; }
if (!Array.isArray(certs)) certs = [];
certs.push(cert);
    currentCandidateData.certifications = certs;
    renderCertifications(certs);
}

function removeCertification(index) {
    let certs = [];
    try {
        certs = typeof currentCandidateData.certifications === 'string' ? JSON.parse(currentCandidateData.certifications) : (currentCandidateData.certifications || []);
    } catch(e) { certs = []; }
    certs.splice(index, 1);
    currentCandidateData.certifications = certs;
    renderCertifications(certs);
}

function removeAttachment(index) {
    let attachments = [];
    try {
        attachments = typeof currentCandidateData.attachments === 'string' ? JSON.parse(currentCandidateData.attachments) : (currentCandidateData.attachments || []);
    } catch(e) { attachments = []; }
    attachments.splice(index, 1);
    currentCandidateData.attachments = attachments;
    renderAttachments(attachments);
}

async function uploadAttachments() {
    const fileInput = document.getElementById('attachmentFileInput');
    if (!fileInput || !fileInput.files || fileInput.files.length === 0) {
        toastError('Please select files first');
        return;
    }
    
    const files = fileInput.files;
    let successCount = 0;
    let failCount = 0;
    
    for (let i = 0; i < files.length; i++) {
        const file = files[i];
        const formData = new FormData();
        formData.append('file', file);
        
        try {
            const res = await fetch('/api/candidates/' + currentCandidateId + '/attachments', {
                method: 'POST',
                body: formData
            });
            const result = await res.json();
            
            if (result.success) {
                successCount++;
                // Update attachments in current data
                currentCandidateData.attachments = result.attachments;
            } else {
                failCount++;
            }
        } catch(e) {
            failCount++;
        }
    }
    
    // Refresh the attachments list
    renderAttachments(currentCandidateData.attachments);
    
    // Reset file input
    fileInput.value = '';
    
    if (successCount > 0) {
        toastSuccess(successCount + ' file(s) uploaded!');
    }
    if (failCount > 0) {
        toastError(failCount + ' file(s) failed');
    }
}

// Save Changes
async function saveCandidateChanges() {
    if (!currentCandidateId) return;
    
    const data = {
        first_name: document.getElementById('edit_first_name').value,
        last_name: document.getElementById('edit_last_name').value,
        email: document.getElementById('edit_email').value,
        phone: document.getElementById('edit_phone').value,
        designation: document.getElementById('edit_designation').value,
        linkedin: document.getElementById('edit_linkedin').value,
        location: document.getElementById('edit_location').value,
        years_of_experience: document.getElementById('edit_years_exp').value,
        current_ctc: document.getElementById('edit_current_ctc').value,
        expected_ctc: document.getElementById('edit_expected_ctc').value,
        proposed_client: document.getElementById('edit_proposed_client').value,
        proposed_requirement: (document.getElementById('edit_proposed_requirement').value || '').split(' - ')[0].trim(),
        stage: document.getElementById('edit_stage').value,
        notes: document.getElementById('edit_notes').value,
        core_skills: currentCandidateData.core_skills,
        work_experience: currentCandidateData.work_experience,
        certifications: currentCandidateData.certifications,
        attachments: currentCandidateData.attachments
    };
    
    try {
        const response = await fetch('/api/candidates/' + currentCandidateId, {
            method: 'PUT',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify(data)
        });
        const result = await response.json();
        if (result.success) {
            toastSuccess('Candidate updated successfully!');
            closeModal();
            loadCandidates();
        } else {
            toastError(result.error || 'Update failed');
        }
    } catch(e) {
        toastError('Error: ' + e.message);
    }
}

// PDF Generation
function generateCandidatePDF() {
    const candidate = currentCandidateData;
    if (!candidate) return;
    
    let html = '<html><head><meta charset="UTF-8"><style>';
    html += 'body{font-family:"Times New Roman",serif;font-size:12pt;color:#000;padding:40px;line-height:1.6;}';
    html += 'h1{font-size:20pt;color:#1B2A4A;border-bottom:2px solid #1B2A4A;padding-bottom:10px;}';
    html += 'h2{font-size:14pt;color:#1B2A4A;margin-top:20px;}';
    html += 'table{width:100%;border-collapse:collapse;margin:10px 0;}';
    html += 'td{padding:6px 10px;border:1px solid #ccc;}';
    html += 'td:first-child{font-weight:bold;background:#f5f5f5;width:30%;}';
    html += '.skill-tag{display:inline-block;background:#E8EDF5;color:#1B2A4A;padding:3px 10px;margin:3px;border-radius:12px;font-size:10pt;}';
    html += '.section{margin:15px 0;}';
    html += '</style></head><body>';
    
    html += '<h1>Candidate Profile: ' + escapeHtml(String(candidate.first_name + ' ' + candidate.last_name)) + '</h1>';
    
    html += '<h2>Basic Information</h2><table>';
    html += '<tr><td>Name</td><td>' + escapeHtml(String(candidate.first_name + ' ' + candidate.last_name)) + '</td></tr>';
    html += '<tr><td>Email</td><td>' + escapeHtml(String(candidate.email || 'N/A')) + '</td></tr>';
    html += '<tr><td>Phone</td><td>' + escapeHtml(String(candidate.phone || 'N/A')) + '</td></tr>';
    html += '<tr><td>Designation</td><td>' + escapeHtml(String(candidate.designation || candidate.current_role || 'N/A')) + '</td></tr>';
    html += '<tr><td>LinkedIn</td><td>' + escapeHtml(String(candidate.linkedin || 'N/A')) + '</td></tr>';
    html += '<tr><td>Location</td><td>' + escapeHtml(String(candidate.location || candidate.address || 'N/A')) + '</td></tr>';
    html += '<tr><td>Experience</td><td>' + escapeHtml(String(candidate.years_of_experience || 'N/A')) + '</td></tr>';
    html += '<tr><td>Current CTC</td><td>' + escapeHtml(String(candidate.current_ctc || 'N/A')) + '</td></tr>';
    html += '<tr><td>Expected CTC</td><td>' + escapeHtml(String(candidate.expected_ctc || 'N/A')) + '</td></tr>';
    html += '<tr><td>Stage</td><td>' + escapeHtml(String(candidate.stage || 'new')) + '</td></tr>';
    html += '</table>';
    
    // Skills
    let skills = [];
    try { skills = typeof candidate.core_skills === 'string' ? JSON.parse(candidate.core_skills) : (candidate.core_skills || []); } catch(e) {}
    if (skills.length > 0) {
        html += '<h2>Skills</h2><div>';
        skills.forEach(s => { html += '<span class="skill-tag">' + escapeHtml(String(s)) + '</span>'; });
        html += '</div>';
    }
    
    html += '<h2>Notes</h2><p>' + escapeHtml(String(candidate.notes || 'No notes')) + '</p>';
    html += '<p style="margin-top:30px;font-size:9pt;color:#666;">Generated by ShahnaIT Scout</p>';
    html += '</body></html>';
    
    const blob = new Blob([html], {type: 'text/html'});
    const url = URL.createObjectURL(blob);
    window.open(url, '_blank');
    toastSuccess('PDF report opened in new tab. Use Ctrl+P to save as PDF.');
}

async function runAIAnalysis() {
    if (!currentCandidateId || !currentCandidateData) {
        toastError('No candidate selected');
        return;
    }
    
    const requirementId = (document.getElementById('edit_proposed_requirement').value || '').split(' - ')[0].trim();
    if (!requirementId) {
        toastError('Please select a Requirement/Job ID first');
        return;
    }
    
    try {
        const reqRes = await fetch('/api/requirements');
        const requirements = await reqRes.json();
        const selectedReq = requirements.find(r => r.requirement_id === requirementId);
        
        if (!selectedReq) {
            toastError('Requirement not found');
            return;
        }
        
        const jobsRes = await fetch('/api/jobs');
        const jobs = await jobsRes.json();
        const job = jobs.find(j => (j.requirement_id === requirementId || j.title === selectedReq.title));
        
        const jdText = (job ? job.description : '') || selectedReq.title || '';
        const resumeText = currentCandidateData.resume_text || '';
        
        if (!resumeText) {
            toastError('No resume text available');
            return;
        }
        
        toastInfo('Running AI Analysis...');
        
        const analysisRes = await fetch('/api/analyze-match', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
body: JSON.stringify({
    resume_text: resumeText,
    jd_text: jdText,
    candidate_id: currentCandidateId,
    candidate_name: (currentCandidateData.first_name || '') + ' ' + (currentCandidateData.last_name || ''),
    job_title: job ? job.title : ''
})
        });
        
        const result = await analysisRes.json();
        
        if (result.match_score !== undefined) {
            document.getElementById('aiSummarySection').style.display = 'block';
            const summaryText = result.detailed_analysis || result.executive_summary || 'Analysis complete'; document.getElementById('aiSummaryText').textContent = summaryText;
            document.getElementById('aiMatchedJD').textContent = requirementId;
            
            currentCandidateData.analysis_summary = result.executive_summary;
            currentCandidateData.match_score = result.match_score;
            currentCandidateData.matched_jd = requirementId;
            
            await fetch('/api/candidates/' + currentCandidateId, {
                method: 'PUT',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({
                    analysis_summary: result.executive_summary,
                    match_score: result.match_score,
                    matched_jd: requirementId,
                    proposed_requirement: requirementId
                })
            });
            
            toastSuccess('Analysis complete! Match: ' + result.match_score + '%');
            closeModal();
            loadCandidates();
        } else {
            toastError('Analysis failed');
        }
    } catch(e) {
        toastError('Error: ' + e.message);
    }
}

function copyResumeText() {
    const text = document.getElementById('resumeFullText').textContent;
    navigator.clipboard.writeText(text).then(() => {
        toastSuccess('Resume text copied!');
    }).catch(() => {
        toastError('Failed to copy');
    });
}

function downloadOriginalResume(candidateId) {
    if (!candidateId) return;
    window.open('/api/candidates/' + candidateId + '/download-resume', '_blank');
}

function closeModal() {
    document.getElementById('candidateModal').style.display = 'none';
    currentCandidateId = null;
    currentCandidateData = null;
}

console.log('✅ viewCandidate (full modal) defined');
console.log('✅ Stage colors:', typeof updateStageColor);
console.log('✅ Skills renderer:', typeof renderSkills);
// LOAD CANDIDATES
// ============================================
async function loadCandidates() {
    try {
        const res = await fetch('/api/candidates');
        const data = await res.json();
        allCandidates = data;
        console.log('✅ Loaded ' + allCandidates.length + ' candidates');
        
        // Update the candidate cards with IDs
        document.querySelectorAll('.candidate-card').forEach(function(card) {
            const id = card.getAttribute('data-id');
            if (id) {
               if (card) card.onclick = function() {
                    viewCandidate(parseInt(id));
                };
            }
        });
    } catch (e) {
        console.error('Error loading candidates:', e);
    }
}
console.log('✅ loadCandidates defined');

// Call loadCandidates when page loads
loadCandidates();

// Open first sidebar group by default
document.querySelector('.sidebar-group-header').classList.add('open');
document.querySelector('.sidebar-group-items').classList.add('open');
// ============================================
    // DARK MODE
    // ============================================
    function toggleDarkMode() {
        const body = document.body;
        const toggle = document.querySelector('.dark-mode-toggle');
        
        body.classList.toggle('dark-mode');
        
        // Save preference
        if (body.classList.contains('dark-mode')) {
            localStorage.setItem('darkMode', 'enabled');
            if (toggle) toggle.textContent = '☀️';
        } else {
            localStorage.setItem('darkMode', 'disabled');
            if (toggle) toggle.textContent = '🌙';
        }
    }

    // Load saved preference on page load
    function loadDarkModePreference() {
        const darkMode = localStorage.getItem('darkMode');
        const toggle = document.querySelector('.dark-mode-toggle');
        
        if (darkMode === 'enabled') {
            document.body.classList.add('dark-mode');
            if (toggle) toggle.textContent = '☀️';
        }
    }

    // Call on page load
    loadDarkModePreference();

    // ============================================
    // TOAST NOTIFICATIONS
    // ============================================
    function showToast(message, type = 'info', duration = 4000) {
        const container = document.getElementById('toastContainer');
        
        const icons = {
            success: '✅',
            error: '❌',
            warning: '⚠️',
            info: 'ℹ️'
        };
        
        const toast = document.createElement('div');
        toast.className = `toast toast-${type}`;
        toast.innerHTML = `
            <span class="toast-icon">${icons[type] || 'ℹ️'}</span>
            <span class="toast-message">${message}</span>
            <button class="toast-close" onclick="this.parentElement.remove()">✕</button>`;
        
        container.appendChild(toast);
        
        setTimeout(() => {
            if (toast.parentElement) {
                toast.classList.add('toast-hidden');
                setTimeout(() => toast.remove(), 500);
            }
        }, duration);
        
        toast.addEventListener('click', function(e) {
            if (e.target.tagName !== 'BUTTON') {
                this.classList.add('toast-hidden');
                setTimeout(() => this.remove(), 500);
            }
        });
    }

    // Shortcut functions
    function toastSuccess(msg) { showToast(msg, 'success'); }
    function toastError(msg) { showToast(msg, 'error'); }
    function toastWarning(msg) { showToast(msg, 'warning'); }
    function toastInfo(msg) { showToast(msg, 'info'); }

    
    // Tab switching
    const tabJobs = document.getElementById('tabJobs'); if (tabJobs) tabJobs.onclick = function() { showPanel('jobs'); loadJobs(); };
    const tabCandidates = document.getElementById('tabCandidates'); if (tabCandidates) tabCandidates.onclick = function() { showPanel('candidates'); loadCandidates(); };
    const tabUpload = document.getElementById('tabUpload'); if (tabUpload) tabUpload.onclick = function() { showPanel('upload'); };
    const tabCreateJob = document.getElementById('tabCreateJob'); if (tabCreateJob) tabCreateJob.onclick = function() { showPanel('createJob'); };     const tabInterviews = document.getElementById('tabInterviews'); if (tabInterviews) tabInterviews.onclick = function() { showPanel('interviews'); loadInterviews(); };
    const tabAnalyze = document.getElementById('tabAnalyze'); if (tabAnalyze) tabAnalyze.onclick = function() { showPanel('analyze'); loadJobs(); loadCandidates(); };
    const tabDashboard = document.getElementById('tabDashboard'); const tabKanban = document.getElementById('tabKanban'); const tabReports = document.getElementById('tabReports'); if (tabReports) tabReports.onclick = function() { showPanel('reports'); document.getElementById('reportDate').value = new Date().toISOString().split('T')[0]; loadDailyReport(); }; if (tabKanban) tabKanban.onclick = function() { showPanel('kanban'); loadKanban(); }; if (tabDashboard) tabDashboard.onclick = function() { showPanel('dashboard'); loadDashboard(); };
    const tabUsers = document.getElementById('tabUsers'); if (tabUsers) tabUsers.onclick = function() { showPanel('users'); loadUsers(); };
    const tabOnboarded = document.getElementById('tabOnboarded'); const tabFinance = document.getElementById('tabFinance'); if (tabFinance) tabFinance.onclick = function() { showPanel('finance'); loadFinance(); }; if (tabOnboarded) tabOnboarded.onclick = function() { showPanel('onboarded'); loadOnboarded(); };
    
   function showPanel(panel) {
    const allPanels = ['jobsPanel', 'candidatesPanel', 'uploadPanel', 'createJobPanel', 'interviewsPanel', 'analyzePanel', 'dashboardPanel', 'kanbanPanel', 'reportsPanel', 'usersPanel', 'onboardedPanel', 'financePanel'];
    allPanels.forEach(id => {
        const el = document.getElementById(id);
        if (el) el.style.display = 'none';
    });
    
    const target = document.getElementById(panel + 'Panel');
    if (target) target.style.display = 'block';
    
    document.querySelectorAll('.tab-btn').forEach(btn => btn.classList.remove('active'));
     const tabMap = {
        'jobs': 'tabJobs', 'candidates': 'tabCandidates', 'upload': 'tabUpload',
        'createJob': 'tabCreateJob', 'analyze': 'tabAnalyze', 'dashboard': 'tabDashboard',
        'interviews': 'tabInterviews', 'kanban': 'tabKanban', 'reports': 'tabReports',
        'users': 'tabUsers', 'onboarded': 'tabOnboarded', 'finance': 'tabFinance'
    };
    const tab = document.getElementById(tabMap[panel]);
    if (tab) tab.classList.add('active');
}
// ============================================
// INTERVIEW TRACKER FUNCTIONS
// ============================================

async function loadInterviews() {
    const dateFilter = document.getElementById('intFilterDate').value || '';
    const roundFilter = document.getElementById('intFilterRound').value || '';
    const verdictFilter = document.getElementById('intFilterVerdict').value || '';
    
    let url = '/api/interviews?';
    if (dateFilter) url += 'date=' + dateFilter + '&';
    if (roundFilter) url += 'round=' + roundFilter + '&';
    if (verdictFilter) url += 'verdict=' + verdictFilter + '&';
    
    const res = await fetch(url);
    const interviews = await res.json();
    const container = document.getElementById('interviewsList');
    
    if (!interviews.length) {
        container.innerHTML = '<div class="card no-click" style="text-align:center;padding:40px;color:#94A3B8;">📅 No interviews found</div>';
        return;
    }
    
    container.innerHTML = interviews.map(i => {
        const verdictColors = {
            'Scheduled': '#2196F3', 'Selected': '#4CAF50', 'Rejected': '#F44336',
            'Hold': '#FF9800', 'No Show': '#9E9E9E', 'Rescheduled': '#9C27B0'
        };
        const verdictColor = verdictColors[i.verdict] || '#2196F3';
        
        return `<div class="card" style="margin-bottom:10px;">
            <div style="display:flex;justify-content:space-between;align-items:start;flex-wrap:wrap;gap:10px;">
                <div style="flex:1;min-width:200px;">
                    <h4 style="margin:0 0 5px 0;">
                        <a href="javascript:void(0)" onclick="viewCandidate(${i.candidate_id})" style="color:#1B2A4A;text-decoration:underline;">${escapeHtml(i.candidate_name || 'Unknown')}</a>
                    </h4>
                    <div style="display:flex;gap:10px;flex-wrap:wrap;font-size:13px;color:#555;">
                        <span>📅 ${i.interview_date} ${i.interview_time || ''}</span>
                        <span style="background:#E3F2FD;padding:2px 10px;border-radius:12px;">🎯 ${escapeHtml(i.round)}</span>
                        ${i.client_name ? `<span>🏢 ${escapeHtml(i.client_name)}</span>` : ''}
                        ${i.requirement_id ? `<span>📋 ${escapeHtml(i.requirement_id)}</span>` : ''}
                    </div>
                    <div style="margin-top:8px;font-size:12px;color:#777;">
                        ${i.resource_owner ? `👤 Owner: ${escapeHtml(i.resource_owner)}` : ''}
                        ${i.client_poc ? ` | 📞 POC: ${escapeHtml(i.client_poc)}` : ''}
                    </div>
                </div>
                <div style="text-align:right;">
                    <select onchange="updateInterviewVerdict(${i.id}, this.value)" style="background:${verdictColor};color:#fff;border:none;padding:6px 12px;border-radius:16px;font-weight:bold;cursor:pointer;font-size:13px;">
                        <option value="Scheduled" ${i.verdict==='Scheduled'?'selected':''}>📋 Scheduled</option>
                        <option value="Selected" ${i.verdict==='Selected'?'selected':''}>✅ Selected</option>
                        <option value="Rejected" ${i.verdict==='Rejected'?'selected':''}>❌ Rejected</option>
                        <option value="Hold" ${i.verdict==='Hold'?'selected':''}>⏸️ Hold</option>
                        <option value="No Show" ${i.verdict==='No Show'?'selected':''}>🚫 No Show</option>
                        <option value="Rescheduled" ${i.verdict==='Rescheduled'?'selected':''}>🔄 Rescheduled</option>
                    </select>
                </div>
            </div>
           ${i.feedback ? `<div style="margin-top:8px;padding:8px;background:#F5F5F5;border-radius:6px;font-size:13px;color:#555;">💬 ${escapeHtml(i.feedback)}</div>` : ''}
            <div style="margin-top:8px;display:flex;gap:6px;">
                <button class="btn btn-sm" onclick="sendInterviewEmail(${i.id}, 'invite')" style="font-size:11px;padding:4px 10px;">📧 Send Invite</button>
                ${i.verdict !== 'Scheduled' ? `<button class="btn btn-sm btn-secondary" onclick="sendInterviewEmail(${i.id}, 'verdict')" style="font-size:11px;padding:4px 10px;">📨 Send Verdict</button>` : ''}
            </div>
        </div>`;
    }).join('');
    
    const reqList = document.getElementById('intReqList');
    if (reqList && allJobs.length) {
        reqList.innerHTML = allJobs.map(j => `<option value="${escapeHtml(j.requirement_id || 'SIT-R-' + String(j.id).padStart(3,'0'))}">`).join('');
    }
}

function searchInterviewCandidate() {
    const search = document.getElementById('intCandidateSearch').value.toLowerCase();
    const list = document.getElementById('intCandidateList');
    if (!search || search.length < 2) { list.innerHTML = ''; return; }
    const matches = allCandidates.filter(c => 
        (c.first_name + ' ' + c.last_name).toLowerCase().includes(search) ||
        ('SIT-C-' + String(c.id).padStart(3,'0')).includes(search)
    );
    list.innerHTML = matches.map(c => 
        `<option value="${escapeHtml('SIT-C-' + String(c.id).padStart(3,'0') + ' - ' + (c.first_name||'') + ' ' + (c.last_name||''))}">`
    ).join('');
}

async function scheduleInterview() {
    const candidateVal = document.getElementById('intCandidateSearch').value;
    const candidateId = candidateVal.split(' - ')[0].replace('SIT-C-', '').trim();
    
    if (!candidateId) { toastError('Please select a candidate'); return; }
    
    const data = {
        candidate_id: parseInt(candidateId),
        candidate_name: candidateVal.split(' - ').slice(1).join(' - ').trim(),
        interview_date: document.getElementById('intDate').value,
        interview_time: document.getElementById('intTime').value,
        round: document.getElementById('intRound').value,
        resource_owner: document.getElementById('intOwner').value,
        client_name: document.getElementById('intClient').value,
        client_poc: document.getElementById('intPOC').value,
        requirement_id: document.getElementById('intRequirement').value,
        scheduled_by: 'HR'
    };
    
    if (!data.interview_date) { toastError('Please select a date'); return; }
    
    const res = await fetch('/api/interviews', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify(data)
    });
    
    if (res.ok) {
        toastSuccess('Interview scheduled!');
        document.getElementById('intCandidateSearch').value = '';
        document.getElementById('intDate').value = '';
        document.getElementById('intTime').value = '';
        document.getElementById('intOwner').value = '';
        document.getElementById('intClient').value = '';
        document.getElementById('intPOC').value = '';
        document.getElementById('intRequirement').value = '';
        loadInterviews();
    } else {
        toastError('Failed to schedule interview');
    }
}

async function sendInterviewEmail(interviewId, type) {
    if (!confirm('Send ' + (type === 'invite' ? 'interview invite' : 'verdict update') + ' email to candidate?')) return;
    
    const res = await fetch('/api/interviews/' + interviewId + '/send-email', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({ type: type })
    });
    
    if (res.ok) {
        toastSuccess('Email sent!');
    } else {
        const result = await res.json();
        toastError(result.error || 'Failed to send email');
    }
}

async function updateInterviewVerdict(interviewId, verdict) {
    const feedback = prompt('Add feedback (optional):', '');
    const res = await fetch('/api/interviews/' + interviewId, {
        method: 'PUT',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({ verdict: verdict, feedback: feedback || '' })
    });
    if (res.ok) {
        toastSuccess('Verdict updated!');
        loadInterviews();
    } else {
        toastError('Failed to update verdict');
    }
}

// Schedule button handler
document.addEventListener('DOMContentLoaded', function() {
       const scheduleInterviewBtn = document.getElementById('scheduleInterviewBtn');
    if (scheduleInterviewBtn) scheduleInterviewBtn.onclick = scheduleInterview;
        
    // Onboard button
    const onboardBtn = document.getElementById('onboardBtn');
    if (onboardBtn) onboardBtn.onclick = async function() {
        const candidateVal = document.getElementById('onbCandidate').value;
        const candidateId = candidateVal.split(' - ')[0].trim();
        if (!candidateId) { toastError('Select a candidate'); return; }
        
        const reqId = document.getElementById('onbRequirementId').value.trim();
        const reqName = document.getElementById('onbRequirementId').value.includes(' - ') ? 
            document.getElementById('onbRequirementId').value.split(' - ')[1].trim() : '';
        
        const data = {
            candidate_id: parseInt(candidateId),
            client_name: document.getElementById('onbClient').value,
            doj: document.getElementById('onbDOJ').value,
            resource_owner: document.getElementById('onbOwner').value,
            work_location: document.getElementById('onbLocation').value,
            monthly_salary: parseFloat(document.getElementById('onbSalary').value) || 0,
            billing_rate: parseFloat(document.getElementById('onbBilling').value) || 0,
            business_model: document.getElementById('onbModel').value,
            requirement_id: reqId ? 'SIT-R-' + reqId : '',
            requirement_name: reqName,
            po_number: document.getElementById('onbPO').value
        };
        
        if (!data.client_name || !data.doj) { toastError('Client and DOJ required'); return; }
        
        const formData = new FormData();
        Object.keys(data).forEach(key => formData.append(key, data[key]));
        const docFiles = document.getElementById('onbDocuments').files;
        for (let i = 0; i < docFiles.length; i++) {
            formData.append('documents', docFiles[i]);
        }

        console.log('Files count:', document.getElementById('onbDocuments').files.length);
        
        const res = await fetch('/api/onboarded', { method: 'POST', body: formData });
        if (res.ok) {
            toastSuccess('Resource onboarded!');
            document.getElementById('onbCandidate').value = '';
            document.getElementById('onbClient').value = '';
            document.getElementById('onbDOJ').value = '';
            document.getElementById('onbSalary').value = '';
            document.getElementById('onbBilling').value = '';
            document.getElementById('onbOwner').value = '';
            document.getElementById('onbLocation').value = '';
            document.getElementById('onbPO').value = '';
            loadOnboarded();
        } else {
            toastError('Failed to onboard');
        }
    };
});

async function toggleJobActive(jobId) {
    const job = allJobs.find(j => j.id == jobId);
    const newStatus = (job.is_active !== false) ? 0 : 1;
    const res = await fetch('/api/jobs/' + jobId + '/toggle-active', {
        method: 'PUT',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({ is_active: newStatus })
    });
    if (res.ok) {
        toastSuccess(newStatus ? 'Requirement reopened!' : 'Requirement closed!');
        loadJobs();
    } else {
        toastError('Failed to update');
    }
}

async function loadJobs() {
    const res = await fetch('/api/jobs');
    allJobs = await res.json();
    const container = document.getElementById('jobsList');
    if(!allJobs.length) { container.innerHTML = '<div class="card no-click">No jobs yet</div>'; return; }
    
    container.innerHTML = allJobs.map(j => {
    const requirementId = j.requirement_id || ('SIT-R-' + String(j.id).padStart(3,'0'));
    
    // Build info badges
    let badges = '';
    if (j.working_mode && j.working_mode !== 'Not Specified') {
        const modeColors = { 'Remote': '#10B981', 'Hybrid': '#F59E0B', 'Onsite': '#EF4444' };
        const color = modeColors[j.working_mode] || '#6B7280';
        badges += `<span style="background:${color};color:#fff;padding:2px 8px;border-radius:10px;font-size:11px;margin-right:4px;">${escapeHtml(j.working_mode)}${j.working_mode === 'Hybrid' && j.hybrid_days ? ' (' + j.hybrid_days + 'd)' : ''}</span>`;
    }
    if (j.business_model && j.business_model !== 'Not Specified') {
        badges += `<span style="background:#6366F1;color:#fff;padding:2px 8px;border-radius:10px;font-size:11px;margin-right:4px;">${escapeHtml(j.business_model)}</span>`;
    }
    if (j.years_of_experience) {
        badges += `<span style="background:#8B5CF6;color:#fff;padding:2px 8px;border-radius:10px;font-size:11px;margin-right:4px;">${j.years_of_experience}+ Yrs</span>`;
    }
    if (j.budget) {
        badges += `<span style="background:#EC4899;color:#fff;padding:2px 8px;border-radius:10px;font-size:11px;margin-right:4px;">💰 ${escapeHtml(j.budget)}</span>`;
    }
    if (j.headcount && j.headcount > 1) {
        badges += `<span style="background:#14B8A6;color:#fff;padding:2px 8px;border-radius:10px;font-size:11px;">👥 ${j.headcount}</span>`;
    }
    
    return `<div class="card" style="cursor:pointer;">
        <div onclick="viewCandidatesForRequirement('${escapeHtml(requirementId)}')" style="flex:1;">
            <h3>${escapeHtml(j.title)} <span style="font-size:12px;background:#1B2A4A;color:#fff;padding:2px 8px;border-radius:10px;">${escapeHtml(requirementId)}</span></h3>
            ${j.company ? `<p>🏢 ${escapeHtml(j.company)}</p>` : ''}
            ${j.end_client ? `<p style="font-size:13px;">🎯 End Client: ${escapeHtml(j.end_client)}</p>` : ''}
            ${j.payroll_company ? `<p style="font-size:13px;">💼 Payroll: ${escapeHtml(j.payroll_company)}</p>` : ''}
            ${badges ? `<div style="margin:8px 0;">${badges}</div>` : ''}
            <small>📅 ${new Date(j.created_at).toLocaleDateString()}</small>
        </div>
        <button class="btn btn-sm btn-secondary" onclick="event.stopPropagation(); editJob(${j.id})" style="margin-top:8px;">✏️ Edit</button> <button class="btn btn-sm" onclick="event.stopPropagation(); toggleJobActive(${j.id})" style="margin-top:8px;background:${j.is_active ? '#EF4444' : '#10B981'};">${j.is_active !== false ? '🔒 Close' : '🔓 Reopen'}</button>
        <button class="btn btn-sm" onclick="event.stopPropagation(); viewCandidatesForRequirement('${escapeHtml(requirementId)}')" style="margin-top:8px;">👥 View Candidates</button>
    </div>`;
}).join('');
    
    document.getElementById('jobSelect').innerHTML = '<option value="">-- Select Job --</option>' + allJobs.map(j => `<option value="${j.id}">${escapeHtml(j.title)}</option>`).join('');
    document.getElementById('batchJobSelect').innerHTML = '<option value="">-- Select Job --</option>' + allJobs.map(j => `<option value="${j.id}">${escapeHtml(j.title)}</option>`).join('');
}
async function viewCandidatesForRequirement(requirementId) {
    // Filter candidates by this requirement
    const matched = allCandidates.filter(c => {
        return c.proposed_requirement === requirementId;
    });
    
    if (matched.length === 0) {
        toastInfo('No candidates linked to ' + requirementId);
        return;
    }
    
    // Switch to candidates panel
    showPanel('candidates');
    
    // Set the requirement as a filter
    // Display only matched candidates
    renderCandidates(matched);
    
    // Show count
    toastSuccess('Found ' + matched.length + ' candidate(s) for ' + requirementId);
}
   
   async function loadCandidates() {
    const res = await fetch('/api/candidates');
    allCandidates = await res.json();
    filterCandidates();
    // updatePipelineStats();  // ← REMOVED - function doesn't exist
    renderUploaderStats();
    document.getElementById('candidateSelect').innerHTML = '<option value="">-- Select Candidate --</option>' + allCandidates.map(c => `<option value="${c.id}">${escapeHtml(c.first_name + ' ' + c.last_name || 'Unknown')}</option>`).join('');
  refreshDashboard();
}
// ============================================
// UPDATE DASHBOARD STATISTICS
// ============================================
function updateDashboardStats() {
    const candidates = allCandidates || [];
    const total = candidates.length;
    
    // Calculate average match score
    let totalScore = 0;
    let scoredCount = 0;
    candidates.forEach(c => {
        const score = c.match_score || 0;
        if (score > 0) {
            totalScore += score;
            scoredCount++;
        }
    });
    const avgScore = scoredCount > 0 ? Math.round(totalScore / scoredCount) : 0;
    
    // Count hired and rejected
    const hired = candidates.filter(c => c.employment_status === 'hired').length;
    const rejected = candidates.filter(c => c.employment_status === 'rejected').length;
    const pending = candidates.filter(c => 
        c.employment_status === 'new' || 
        c.employment_status === 'screening' || 
        c.employment_status === 'interview' ||
        c.employment_status === 'offer' ||
        !c.employment_status
    ).length;
    
    // Update SIMPLE stat cards (the ones that exist)
    const totalEl = document.getElementById('simple-total');
    const avgEl = document.getElementById('simple-avg');
    const hiredEl = document.getElementById('simple-hired');
    const rejectedEl = document.getElementById('simple-rejected');
    const pendingEl = document.getElementById('simple-pending');
    
    if (totalEl) totalEl.textContent = total;
    if (avgEl) avgEl.textContent = avgScore + '%';
    if (hiredEl) hiredEl.textContent = hired;
    if (rejectedEl) rejectedEl.textContent = rejected;
    if (pendingEl) pendingEl.textContent = pending;
}

// ============================================
// RENDER MATCH SCORE CHART
// ============================================
function renderChart() {
    const chart = document.getElementById('score-chart');
    if (!chart) return;
    
    const candidates = allCandidates || [];
    const scores = [];
    
    // Collect all match scores
    candidates.forEach(c => {
        const score = c.match_score || 0;
        if (score > 0) scores.push(score);
    });
    
    if (scores.length === 0) {
        chart.innerHTML = '<p style="text-align: center; color: #999; width: 100%;">No data to display</p>';
        return;
    }
    
    // Group scores into ranges
    const ranges = {
        '0-20': 0,
        '21-40': 0,
        '41-60': 0,
        '61-80': 0,
        '81-100': 0
    };
    
    scores.forEach(score => {
        if (score <= 20) ranges['0-20']++;
        else if (score <= 40) ranges['21-40']++;
        else if (score <= 60) ranges['41-60']++;
        else if (score <= 80) ranges['61-80']++;
        else ranges['81-100']++;
    });
    
    const max = Math.max(...Object.values(ranges), 1);
    const colors = ['#f44336', '#ff9800', '#ffc107', '#4caf50', '#2196f3'];
    const labels = ['0-20%', '21-40%', '41-60%', '61-80%', '81-100%'];
    
    let html = '';
    let index = 0;
    for (const [range, count] of Object.entries(ranges)) {
        const height = Math.max((count / max) * 100, 5); // Minimum 5% height for visibility
        const color = colors[index];
        html += `
            <div style="flex: 1; display: flex; flex-direction: column; align-items: center; gap: 5px;">
                <div class="bar" style="width: 100%; max-width: 40px; border-radius: 4px 4px 0 0; height: ${height}%; background: ${color}; transition: height 0.5s ease; min-height: 5px;"></div>
                <span class="bar-label" style="font-size: 11px; color: #666;">${labels[index]}</span>
                <span class="bar-label" style="font-size: 10px; font-weight: 600; color: #333;">${count}</span>
            </div>
        `;
        index++;
    }
    
    chart.innerHTML = html;
}

// ============================================
// REFRESH DASHBOARD (called from page load)
// ============================================
function refreshDashboard() {
    updateDashboardStats();
    renderChart();
}
    
    // ============================================
// FILTER CANDIDATES - ENHANCED VERSION
// ============================================
function filterCandidates() {
    const searchTerm = document.getElementById('searchBox').value.toLowerCase();
    const statusFilter = document.getElementById('statusFilter').value;
    const scoreFilter = document.getElementById('scoreFilter').value;
    const uploaderFilter = document.getElementById('uploadedByFilter').value.toLowerCase();
    const sortBy = document.getElementById('sortBy').value;
    
    let filtered = allCandidates;
    
    // 1. Search filter - name, email, phone, skills
    if (searchTerm) {
        filtered = filtered.filter(c => {
            const name = ((c.first_name || '') + ' ' + (c.last_name || '')).toLowerCase().trim();
            const email = (c.email || '').toLowerCase();
            const phone = (c.phone || '').toLowerCase();
            let skills = '';
            if (c.core_skills) {
                try {
                    const parsedSkills = JSON.parse(c.core_skills);
                    skills = parsedSkills.map(s => (s.skill || '').toLowerCase()).join(' ');
                } catch(e) {
                    skills = '';
                }
            }
            return name.includes(searchTerm) || 
                   email.includes(searchTerm) || 
                   phone.includes(searchTerm) || 
                   skills.includes(searchTerm);
        });
    }
    
    // 2. Status filter
    if (statusFilter !== 'all') {
        filtered = filtered.filter(c => (c.stage || c.employment_status || 'new') === statusFilter);
    }
    
    // 3. Score filter
    if (scoreFilter === 'high') {
        filtered = filtered.filter(c => (c.match_score || 0) >= 70);
    } else if (scoreFilter === 'medium') {
        filtered = filtered.filter(c => (c.match_score || 0) >= 40 && (c.match_score || 0) < 70);
    } else if (scoreFilter === 'low') {
        filtered = filtered.filter(c => (c.match_score || 0) < 40);
    }
    
    // 4. Uploader filter
    if (uploaderFilter) {
        filtered = filtered.filter(c => (c.uploaded_by || 'ShahnaIT').toLowerCase().includes(uploaderFilter));
    }
    
    // 5. Sorting
    if (sortBy === 'score') {
        filtered.sort((a, b) => (b.match_score || 0) - (a.match_score || 0));
    } else if (sortBy === 'name') {
        filtered.sort((a, b) => ((a.first_name || '') + ' ' + (a.last_name || '')).localeCompare((b.first_name || '') + ' ' + (b.last_name || '')));
    } else if (sortBy === 'date') {
        filtered.sort((a, b) => new Date(b.created_at) - new Date(a.created_at));
    } else if (sortBy === 'status') {
        filtered.sort((a, b) => (a.stage || a.employment_status || '').localeCompare(b.stage || b.employment_status || ''));
    } else if (sortBy === 'uploader') {
        filtered.sort((a, b) => (a.uploaded_by || 'ShahnaIT').localeCompare(b.uploaded_by || 'ShahnaIT'));
    }
    
    // 6. Render the filtered candidates
    renderCandidates(filtered);
    
    // 7. Update dashboard stats based on filtered results
    updateFilteredStats(filtered);
}
// ============================================
// UPDATE STATS BASED ON FILTERED RESULTS
// ============================================
function updateFilteredStats(filteredCandidates) {
    const total = filteredCandidates.length;
    
    // Calculate average match score for filtered results
    let totalScore = 0;
    let scoredCount = 0;
    filteredCandidates.forEach(c => {
        const score = c.match_score || 0;
        if (score > 0) {
            totalScore += score;
            scoredCount++;
        }
    });
    const avgScore = scoredCount > 0 ? Math.round(totalScore / scoredCount) : 0;
    
    // Count shortlisted in filtered results
    const shortlisted = filteredCandidates.filter(c => 
        c.employment_status === 'hired' || 
        c.employment_status === 'offer' || 
        c.employment_status === 'shortlisted'
    ).length;
    
    // Count pending review in filtered results
    const pendingReview = filteredCandidates.filter(c => 
        c.employment_status === 'new' || 
        c.employment_status === 'screening' || 
        c.employment_status === 'interview' ||
        !c.employment_status
    ).length;
    
    // Update the SIMPLE stat cards (not the old ones)
    const totalEl = document.getElementById('simple-total');
    const avgEl = document.getElementById('simple-avg');
    const hiredEl = document.getElementById('simple-hired');
    const rejectedEl = document.getElementById('simple-rejected');
    const pendingEl = document.getElementById('simple-pending');
    
    if (totalEl) totalEl.textContent = total;
    if (avgEl) avgEl.textContent = avgScore + '%';
    if (hiredEl) hiredEl.textContent = shortlisted;
    if (pendingEl) pendingEl.textContent = pendingReview;
    if (rejectedEl) rejectedEl.textContent = filteredCandidates.filter(c => c.employment_status === 'rejected').length;
    
    // Re-render the chart with filtered data
    renderFilteredChart(filteredCandidates);
}
// ============================================
// RENDER CHART WITH FILTERED DATA
// ============================================
function renderFilteredChart(filteredCandidates) {
    const chart = document.getElementById('score-chart');
    if (!chart) return;
    
    const scores = [];
    
    // Collect all match scores from filtered candidates
    filteredCandidates.forEach(c => {
        const score = c.match_score || 0;
        if (score > 0) scores.push(score);
    });
    
    if (scores.length === 0) {
        chart.innerHTML = '<p style="text-align: center; color: #999; width: 100%;">No data to display</p>';
        return;
    }
    
    // Group scores into ranges
    const ranges = {
        '0-20': 0,
        '21-40': 0,
        '41-60': 0,
        '61-80': 0,
        '81-100': 0
    };
    
    scores.forEach(score => {
        if (score <= 20) ranges['0-20']++;
        else if (score <= 40) ranges['21-40']++;
        else if (score <= 60) ranges['41-60']++;
        else if (score <= 80) ranges['61-80']++;
        else ranges['81-100']++;
    });
    
    const max = Math.max(...Object.values(ranges), 1);
    const colors = ['#f44336', '#ff9800', '#ffc107', '#4caf50', '#2196f3'];
    const labels = ['0-20%', '21-40%', '41-60%', '61-80%', '81-100%'];
    
    let html = '';
    let index = 0;
    for (const [range, count] of Object.entries(ranges)) {
        const height = Math.max((count / max) * 100, 5);
        const color = colors[index];
        html += `
            <div style="flex: 1; display: flex; flex-direction: column; align-items: center; gap: 5px;">
                <div class="bar" style="width: 100%; max-width: 40px; border-radius: 4px 4px 0 0; height: ${height}%; background: ${color}; transition: height 0.5s ease; min-height: 5px;"></div>
                <span class="bar-label" style="font-size: 11px; color: #666;">${labels[index]}</span>
                <span class="bar-label" style="font-size: 10px; font-weight: 600; color: #333;">${count}</span>
            </div>
        `;
        index++;
    }
    
    chart.innerHTML = html;
}
    
   // ============================================
// RENDER CANDIDATE CARDS - IMPROVED VERSION
// ============================================
function renderCandidates(candidates) {
    const container = document.getElementById('candidatesList');
    if(!candidates.length) { 
        container.innerHTML = '<div class="card no-click" style="text-align: center; padding: 40px; color: #666;">🔍 No candidates found</div>'; 
        return; 
    }
    
    container.innerHTML = candidates.map(c => {
        const name = (c.first_name + ' ' + c.last_name).trim() || 'Unknown';
        let skills = [];
try {
    if (c.core_skills) {
        skills = typeof c.core_skills === 'string' ? JSON.parse(c.core_skills) : c.core_skills;
    }
} catch(e) { skills = []; }
if (!Array.isArray(skills)) skills = [];
        const matchScore = c.match_score || 0;
        const matchClass = matchScore >= 70 ? 'match-high' : (matchScore >= 40 ? 'match-medium' : 'match-low');
        const status = c.stage || c.employment_status || 'new';
        
        // Status colors
        const statusColors = {
            'new': '#2196F3',
            'screening': '#FF9800',
            'interview': '#FF5722',
            'offer': '#9C27B0',
            'hired': '#4CAF50',
            'rejected': '#F44336'
        };
        const statusLabels = {
            'new': '🟢 New',
            'screening': '🔵 Screening',
            'interview': '🟠 Interview',
            'offer': '🟣 Offer',
            'hired': '✅ Hired',
            'rejected': '❌ Rejected'
        };
        const uploadedBy = c.uploaded_by || 'ShahnaIT';
        
        return `
        <div class="candidate-card" data-id="${c.id}" onclick="viewCandidate(${c.id})">
            <div class="card-header">
                <div class="candidate-avatar">
                    <span class="avatar-text">${escapeHtml(name.charAt(0) || '?')}</span>
                    ${matchScore > 0 ? `<div class="score-badge" style="background: ${matchScore >= 70 ? '#4caf50' : (matchScore >= 40 ? '#ff9800' : '#f44336')}">${matchScore}%</div>` : ''}
                </div>
                <div class="candidate-title">
                    <h3 class="candidate-name">👤 ${escapeHtml(name)}</h3>
                    <span class="candidate-email">${c.email ? '📧 ' + escapeHtml(c.email) : ''}</span>
                </div>
                <button class="btn-expand" onclick="event.stopPropagation(); toggleCandidateDetails(${c.id})">
                    <i class="fas fa-chevron-down"></i>
                </button>
            </div>
            
            <div class="card-body">
                <div class="candidate-skills">
                    ${skills.length > 0 ? skills.slice(0,5).map(s => 
    `<span class="skill-tag">${escapeHtml(typeof s === 'object' ? (s.skill || s.name || '') : s)}</span>`
                    ).join('') : '<span class="no-skills">No skills listed</span>'}
                    ${skills.length > 5 ? `<span class="skill-tag more">+${skills.length - 5}</span>` : ''}
                </div>
                
                <div class="candidate-meta">
                    <span class="meta-item">
                        <i class="fas fa-phone"></i> ${c.phone || 'N/A'}
                    </span>
                    <span class="meta-item">
                        <i class="fas fa-calendar"></i> ${c.created_at ? new Date(c.created_at).toLocaleDateString() : 'N/A'}
                    </span>
                    <span class="status-badge status-${status}" style="background: ${statusColors[status]}22; color: ${statusColors[status]};">
                        ${statusLabels[status] || status}
                    </span>
                    <span class="meta-item" style="font-size: 11px; color: #999;">
                        👤 ${escapeHtml(uploadedBy)}
                    </span>
                </div>
                
                <div class="card-actions">
                    <button class="btn-primary" onclick="event.stopPropagation(); viewCandidate(${c.id})">
                        <i class="fas fa-eye"></i> View Details
                    </button>
                    <button class="btn-secondary" onclick="event.stopPropagation(); exportPDF(${c.id}, event)">
                        <i class="fas fa-file-pdf"></i> Export PDF
                    </button>
                    <button class="btn-danger" onclick="event.stopPropagation(); deleteCandidate(${c.id})">
                        <i class="fas fa-trash"></i>
                    </button>
                </div>
            </div>
            
            <!-- Expanded Details -->
            <div class="card-details" id="details-${c.id}" style="display: none;">
                <div class="details-section">
                    <h4>📊 AI Analysis</h4>
                    <p>${c.detailed_analysis ? 'Analysis available' : 'No analysis available'}</p>
                </div>
                <div class="details-section">
                    <h4>📝 Notes</h4>
                    <div class="notes-container" id="notes-${c.id}">
                        <p style="color: #999; font-style: italic;">Loading notes...</p>
                    </div>
                    <input type="text" class="note-input" placeholder="Add a note..." 
                           onkeypress="if(event.key==='Enter') addNote(${c.id}, this.value)">
                </div>
            </div>
        </div>`;
    }).join('');
}
// ============================================
// TOGGLE CANDIDATE DETAILS
// ============================================
function toggleCandidateDetails(id) {
    const details = document.getElementById(`details-${id}`);
    if (!details) return;
    
    if (details.style.display === 'none') {
        details.style.display = 'block';
        // Load notes when expanded
        loadNotes(id);
    } else {
        details.style.display = 'none';
    }
}

// ============================================
// LOAD NOTES FOR CANDIDATE
// ============================================
async function loadNotes(candidateId) {
    const container = document.getElementById(`notes-${candidateId}`);
    if (!container) return;
    
    try {
        const res = await fetch(`/api/candidates/${candidateId}/notes`);
        const notes = await res.json();
        
        if (notes.length === 0) {
            container.innerHTML = '<p style="color: #999; font-style: italic; margin: 5px 0;">No notes yet. Add one above.</p>';
            return;
        }
        
        let html = '';
        notes.forEach(note => {
            const date = new Date(note.created_at).toLocaleString();
            html += `
                <div style="background: #F9F6F0; padding: 8px; border-radius: 6px; margin-bottom: 6px; border-left: 3px solid #1A4D4A;">
                    <div style="display: flex; justify-content: space-between; align-items: flex-start;">
                        <div style="flex: 1; font-size: 13px;">${escapeHtml(note.note_text)}</div>
                        <button class="btn" style="background: #B22222; padding: 2px 8px; font-size: 10px; margin-left: 8px; border: none; border-radius: 4px; color: white; cursor: pointer;" onclick="deleteNote(${note.id}, ${candidateId})">✕</button>
                    </div>
                    <small style="color: #666; font-size: 10px;">📅 ${date}</small>
                </div>
            `;
        });
        container.innerHTML = html;
    } catch(e) {
        container.innerHTML = '<p style="color: #B22222;">Failed to load notes</p>';
    }
}

// ============================================
// ADD NOTE
// ============================================
async function addNote(candidateId, inputElement) {
    const noteText = inputElement.trim();
    if (!noteText) { toastWarning('Please enter a note'); return; }
    
    try {
        const res = await fetch(`/api/candidates/${candidateId}/notes`, {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({ note_text: noteText })
        });
        
        if (res.ok) {
            // Clear input
            const inputField = document.querySelector(`#details-${candidateId} .note-input`);
            if (inputField) inputField.value = '';
            loadNotes(candidateId);
            toastSuccess('Note added!');
        } else {
            toastError('Failed to add note');
        }
    } catch(e) {
        toastError('Error adding note');
    }
}

// ============================================
// DELETE NOTE
// ============================================
async function deleteNote(noteId, candidateId) {
    if (!confirm('Delete this note?')) return;
    
    try {
        const res = await fetch(`/api/candidates/notes/${noteId}`, {
            method: 'DELETE'
        });
        
        if (res.ok) {
            loadNotes(candidateId);
            toastSuccess('Note deleted');
        } else {
            toastError('Failed to delete note');
        }
    } catch(e) {
        toastError('Error deleting note');
    }
}

// ============================================
// DELETE CANDIDATE
// ============================================
async function deleteCandidate(candidateId) {
    if (!confirm('Delete this candidate?')) return;
    
    try {
        const res = await fetch(`/api/candidates/${candidateId}`, {
            method: 'DELETE'
        });
        
        if (res.ok) {
            toastSuccess('Candidate deleted');
            loadCandidates();
        } else {
            toastError('Failed to delete candidate');
        }
    } catch(e) {
        toastError('Error deleting candidate');
    }
}
    
   // ============================================
// EVENT LISTENERS FOR FILTERS
// ============================================
// Search input - real-time filtering
document.getElementById('searchBox').addEventListener('input', filterCandidates);

// Status filter
document.getElementById('statusFilter').addEventListener('change', filterCandidates);

// Score filter
document.getElementById('scoreFilter').addEventListener('change', filterCandidates);

// Uploader filter
document.getElementById('uploadedByFilter').addEventListener('input', filterCandidates);

// Sort by
document.getElementById('sortBy').addEventListener('change', filterCandidates);

// Clear all filters
document.getElementById('clearFiltersBtn').addEventListener('click', function() {
    document.getElementById('searchBox').value = '';
    document.getElementById('statusFilter').value = 'all';
    document.getElementById('scoreFilter').value = 'all';
    document.getElementById('uploadedByFilter').value = '';
    document.getElementById('sortBy').value = 'score';
    filterCandidates();
    
    // Show success message
    toastSuccess('Filters cleared!');
});
    
   // Edit Job
    window.editJob = async function(id) {
        const job = allJobs.find(j => j.id == id);
        const docRes = await fetch(`/api/jobs/${id}/documents`);
        const documents = await docRes.json();
        let docsHtml = '';
        if (documents.length > 0) {
            docsHtml = '<h4>Attached Documents</h4><div class="file-list">';
            documents.forEach(doc => { docsHtml += `<div class="file-list-item">📄 ${escapeHtml(doc.original_filename)} <span class="remove-file" onclick="deleteJobDocument(${doc.id}, ${id})">✕ Remove</span></div>`; });
            docsHtml += '</div>';
        }
        
        const workingModeOptions = ['Not Specified', 'Remote', 'Hybrid', 'Onsite']
            .map(m => `<option value="${m}" ${(job.working_mode || 'Not Specified') === m ? 'selected' : ''}>${m}</option>`).join('');
        const businessModelOptions = ['Not Specified', 'C2C', 'C2H', 'Permanent', 'Contract']
            .map(m => `<option value="${m}" ${(job.business_model || 'Not Specified') === m ? 'selected' : ''}>${m}</option>`).join('');
        
        document.getElementById('editJobModalBody').innerHTML = `<form id="editJobForm">
            <div style="display:grid;grid-template-columns:1fr 1fr;gap:12px;">
                <div class="form-group"><label>Job Title</label><input type="text" id="editJobTitle" class="form-input" value="${escapeHtml(job.title || '')}"></div>
                <div class="form-group"><label>Company</label><input type="text" id="editJobCompany" class="form-input" value="${escapeHtml(job.company || '')}"></div>
            </div>
            <div style="display:grid;grid-template-columns:1fr 1fr;gap:12px;">
                <div class="form-group">
                    <label>Working Mode</label>
                    <select id="editJobWorkingMode" class="form-input">${workingModeOptions}</select>
                </div>
                <div class="form-group">
                    <label>Business Model</label>
                    <select id="editJobBusinessModel" class="form-input">${businessModelOptions}</select>
                </div>
            </div>
            <div class="form-group" id="editHybridDaysGroup" style="display:${(job.working_mode === 'Hybrid') ? 'block' : 'none'};">
                <label>Hybrid Days (per week)</label>
                <input type="number" id="editJobHybridDays" class="form-input" value="${job.hybrid_days || 0}" min="0" max="7">
            </div>
            <div style="display:grid;grid-template-columns:1fr 1fr;gap:12px;">
                <div class="form-group"><label>Payroll Company</label><input type="text" id="editJobPayroll" class="form-input" value="${escapeHtml(job.payroll_company || '')}"></div>
                <div class="form-group"><label>End Client</label><input type="text" id="editJobEndClient" class="form-input" value="${escapeHtml(job.end_client || '')}"></div>
            </div>
            <div style="display:grid;grid-template-columns:1fr 1fr 1fr;gap:12px;">
                <div class="form-group"><label>Years of Experience</label><input type="number" id="editJobExperience" class="form-input" value="${job.years_of_experience || 0}" min="0"></div>
                <div class="form-group"><label>Budget</label><input type="text" id="editJobBudget" class="form-input" value="${escapeHtml(job.budget || '')}"></div>
                <div class="form-group"><label>Headcount</label><input type="number" id="editJobHeadcount" class="form-input" value="${job.headcount || 1}" min="1"></div>
            </div>
            <div class="form-group"><label>Roles & Responsibilities</label><textarea id="editJobRoles" class="form-input" rows="4">${escapeHtml(job.roles_responsibilities || '')}</textarea></div>
            <div style="display:grid;grid-template-columns:1fr 1fr;gap:12px;">
                <div class="form-group"><label>Qualifications</label><textarea id="editJobQualifications" class="form-input" rows="3">${escapeHtml(job.qualifications || '')}</textarea></div>
                <div class="form-group"><label>Certifications Required</label><input type="text" id="editJobCertifications" class="form-input" value="${escapeHtml(job.certifications_required || '')}"></div>
            </div>
            <div class="form-group"><label>Required Skills</label><input type="text" id="editJobSkills" class="form-input" value="${escapeHtml(job.required_skills || '')}"></div>
            <div class="form-group"><label>Description</label><textarea id="editJobDesc" class="form-input" rows="5">${escapeHtml(job.description || '')}</textarea></div>
            <h4>Attach Document</h4><input type="file" id="jobDocFile"><button type="button" id="uploadJobDocBtn" class="btn btn-secondary">Upload</button><div id="jobDocUploadStatus"></div>${docsHtml}
            <div style="margin-top:20px;"><button type="submit" class="btn">Save</button><button type="button" class="btn btn-secondary" onclick="closeEditJobModal()">Cancel</button></div>
        </form>`;
        
        document.getElementById('editJobModal').style.display = 'block';
        
        // Show/hide hybrid days
        const editWorkingMode = document.getElementById('editJobWorkingMode');
        const editHybridGroup = document.getElementById('editHybridDaysGroup');
        if (editWorkingMode && editHybridGroup) {
            editWorkingMode.addEventListener('change', function() {
                editHybridGroup.style.display = this.value === 'Hybrid' ? 'block' : 'none';
            });
        }
        
        const uploadJobDocBtn = document.getElementById('uploadJobDocBtn');
        if (uploadJobDocBtn) uploadJobDocBtn.onclick = async function() {
            const file = document.getElementById('jobDocFile').files[0];
            if (!file) return;
            const fd = new FormData(); fd.append('document', file); fd.append('job_id', id);
            document.getElementById('jobDocUploadStatus').innerHTML = '<div class="spinner"></div>';
            const res = await fetch('/api/jobs/upload-document', { method: 'POST', body: fd });
            if (res.ok) { toastSuccess('Uploaded!'); editJob(id); }
            document.getElementById('jobDocUploadStatus').innerHTML = '';
        };
        
        document.getElementById('editJobForm').onsubmit = async (e) => {
            e.preventDefault();
            const data = {
                title: document.getElementById('editJobTitle').value,
                company: document.getElementById('editJobCompany').value,
                working_mode: document.getElementById('editJobWorkingMode').value,
                hybrid_days: parseInt(document.getElementById('editJobHybridDays').value) || 0,
                business_model: document.getElementById('editJobBusinessModel').value,
                payroll_company: document.getElementById('editJobPayroll').value,
                end_client: document.getElementById('editJobEndClient').value,
                years_of_experience: parseInt(document.getElementById('editJobExperience').value) || 0,
                budget: document.getElementById('editJobBudget').value,
                headcount: parseInt(document.getElementById('editJobHeadcount').value) || 1,
                roles_responsibilities: document.getElementById('editJobRoles').value,
                qualifications: document.getElementById('editJobQualifications').value,
                certifications_required: document.getElementById('editJobCertifications').value,
                required_skills: document.getElementById('editJobSkills').value,
                description: document.getElementById('editJobDesc').value
            };
            const res = await fetch(`/api/jobs/${id}`, { method: 'PUT', headers: {'Content-Type':'application/json'}, body: JSON.stringify(data) });
            if (res.ok) { toastSuccess('Job updated!'); closeEditJobModal(); loadJobs(); }
        };
    };

    
    window.deleteJobDocument = async function(docId, jobId) {
        if (confirm('Delete?')) { await fetch(`/api/jobs/documents/${docId}`, { method: 'DELETE' }); editJob(jobId); }
    };
    function closeEditJobModal() { document.getElementById('editJobModal').style.display = 'none'; }
    window.closeEditJobModal = closeEditJobModal;
    
   window.previewDocument = async function(docId) {
    try {
        const res = await fetch(`/api/documents/${docId}/preview`);
        const data = await res.json();

        if (data.error) {
            toastError(data.error);
            return;
        }

        if (data.type === 'image') {
            document.getElementById('previewBody').innerHTML = `
                <img src="data:image/png;base64,${data.content}" style="max-width:100%; border-radius: 8px;">
                <div style="margin-top: 15px; text-align: center;">
                    <button onclick="copyPreviewText()" style="background: #C9A96E; color: white; border: none; padding: 8px 20px; border-radius: 6px; cursor: pointer; font-size: 14px;">
                        📋 Copy Image Description
                    </button>
                </div>
            `;
        } else {
            document.getElementById('previewBody').innerHTML = `
                <div style="white-space:pre-wrap; background: #f9f6f0; padding: 15px; border-radius: 8px; max-height: 500px; overflow-y: auto; user-select: text; cursor: text; font-family: 'Courier New', monospace; font-size: 13px; line-height: 1.6; border: 1px solid #e0e0e0;">
                    ${escapeHtml(data.content)}
                </div>
                <div style="margin-top: 15px; display: flex; gap: 10px; flex-wrap: wrap; justify-content: center;">
                    <button onclick="copyPreviewText()" style="background: #C9A96E; color: white; border: none; padding: 8px 20px; border-radius: 6px; cursor: pointer; font-size: 14px;">
                        📋 Copy All Text
                    </button>
                    <button onclick="window.print()" style="background: #1A4D4A; color: white; border: none; padding: 8px 20px; border-radius: 6px; cursor: pointer; font-size: 14px;">
                        🖨️ Print
                    </button>
                </div>
            `;
        }
        document.getElementById('previewModal').style.display = 'block';
    } catch (e) {
        toastError('Error loading preview');
        console.error('Preview error:', e);
    }
};
// ============================================
// VIEW ORIGINAL RESUME (Opens in new tab)
// ============================================
function viewOriginalResume(candidateId) {
    // Get the resume URL
    const url = `/api/candidates/${candidateId}/view-resume`;
    
    // Open in new tab
    window.open(url, '_blank');
}

// ============================================
// COPY RESUME TEXT TO CLIPBOARD
// ============================================
async function copyResumeText(candidateId) {
    try {
        const container = document.getElementById(`resume-text-${candidateId}`);
        if (!container) {
            toastError('Resume text not found');
            return;
        }
        
        const text = container.textContent;
        
        // Check if there's actual text
        if (!text || text.trim() === '' || text.includes('No resume text available')) {
            toastWarning('No resume text to copy');
            return;
        }
        
        // Try using the Clipboard API
        try {
            await navigator.clipboard.writeText(text);
            toastSuccess('Resume text copied to clipboard!');
            return;
        } catch (e) {
            // Fallback: use the old method
            const textarea = document.createElement('textarea');
            textarea.value = text;
            textarea.style.position = 'fixed';
            textarea.style.opacity = '0';
            textarea.style.left = '-9999px';
            document.body.appendChild(textarea);
            textarea.select();
            document.execCommand('copy');
            document.body.removeChild(textarea);
            toastSuccess('Resume text copied to clipboard!');
        }
    } catch (e) {
        toastError('Failed to copy text');
        console.error('Copy error:', e);
    }
}

// ============================================
// COPY PREVIEW TEXT
// ============================================
function copyPreviewText() {
    const previewBody = document.getElementById('previewBody');
    if (!previewBody) {
        toastError('Preview not found');
        return;
    }
    
    const textDiv = previewBody.querySelector('div');
    if (!textDiv) {
        toastError('No text to copy');
        return;
    }
    
    const text = textDiv.textContent;
    
    // Try using the Clipboard API
    navigator.clipboard.writeText(text).then(() => {
        toastSuccess('Preview text copied!');
    }).catch(() => {
        // Fallback
        const textarea = document.createElement('textarea');
        textarea.value = text;
        document.body.appendChild(textarea);
        textarea.select();
        document.execCommand('copy');
        document.body.removeChild(textarea);
        toastSuccess('Preview text copied!');
    });
}
    function closeEditModal() { document.getElementById('editModal').style.display = 'none'; }
    window.closeEditModal = closeEditModal;
    function closeDocModal() { document.getElementById('docModal').style.display = 'none'; }
    window.closeDocModal = closeDocModal;
    
    window.openEditModal = async function(id) {
        const c = allCandidates.find(c => c.id == id);
        const skillsStr = c.core_skills ? JSON.parse(c.core_skills).map(s => s.skill).join(', ') : '';
        const certsStr = c.certifications ? JSON.parse(c.certifications).join(', ') : '';
        document.getElementById('editModalBody').innerHTML = `<form id="editForm"><div class="flex"><div class="flex-1"><label>First Name</label><input type="text" id="editFirst" value="${escapeHtml(c.first_name||'')}"></div><div class="flex-1"><label>Middle</label><input type="text" id="editMiddle" value="${escapeHtml(c.middle_name||'')}"></div><div class="flex-1"><label>Last</label><input type="text" id="editLast" value="${escapeHtml(c.last_name||'')}"></div></div><div class="flex"><div class="flex-1"><label>Email</label><input type="email" id="editEmail" value="${escapeHtml(c.email||'')}"></div><div class="flex-1"><label>Phone</label><input type="text" id="editPhone" value="${escapeHtml(c.phone||'')}"></div></div><div class="flex"><div class="flex-1"><label>Current CTC</label><input type="text" id="editCurrentCTC" value="${escapeHtml(c.current_ctc||'')}"></div><div class="flex-1"><label>Expected CTC</label><input type="text" id="editExpectedCTC" value="${escapeHtml(c.expected_ctc||'')}"></div></div><label>Address</label><input type="text" id="editAddress" value="${escapeHtml(c.address||'')}"><label>LinkedIn</label><input type="text" id="editLinkedin" value="${escapeHtml(c.linkedin||'')}"><label>Current Role</label><input type="text" id="editRole" value="${escapeHtml(c.current_role||'')}"><div class="flex"><div class="flex-1"><label>Status</label><select id="editStatus"><option value="working" ${c.employment_status==='working'?'selected':''}>Working</option><option value="bench" ${c.employment_status==='bench'?'selected':''}>Bench</option><option value="notice_period" ${c.employment_status==='notice_period'?'selected':''}>Notice</option></select></div><div class="flex-1"><label>Notice Days</label><input type="number" id="editNoticeDays" value="${c.notice_period_days||0}"></div></div><label>Education</label><textarea id="editEducation" rows="2">${escapeHtml(c.education||'')}</textarea><label>📝 Notes</label><textarea id="editNotes" rows="3" style="background: #FFF8E1; border-left: 4px solid #C9A96E; padding: 10px;">${escapeHtml(c.notes||'')}</textarea><label>Skills (comma)</label><input type="text" id="editSkills" value="${escapeHtml(skillsStr)}"><label>Certifications (comma)</label><input type="text" id="editCerts" value="${escapeHtml(certsStr)}"><div style="margin-top:20px;"><button type="submit" class="btn">Save</button><button type="button" class="btn btn-secondary" onclick="closeEditModal()">Cancel</button></div></form>`;
        document.getElementById('editModal').style.display = 'block';
        document.getElementById('editForm').onsubmit = async (e) => {
            e.preventDefault();
            const skillsArray = document.getElementById('editSkills').value.split(',').map(s => ({skill: s.trim(), years_of_experience: 0})).filter(s => s.skill);
            const certsArray = document.getElementById('editCerts').value.split(',').map(c => c.trim()).filter(c => c);
            const data = {
                first_name: document.getElementById('editFirst').value, middle_name: document.getElementById('editMiddle').value, last_name: document.getElementById('editLast').value,
                email: document.getElementById('editEmail').value, phone: document.getElementById('editPhone').value,
                current_ctc: document.getElementById('editCurrentCTC').value, expected_ctc: document.getElementById('editExpectedCTC').value,
                address: document.getElementById('editAddress').value, linkedin: document.getElementById('editLinkedin').value,
                current_role: document.getElementById('editRole').value, employment_status: document.getElementById('editStatus').value,
                notice_period_days: parseInt(document.getElementById('editNoticeDays').value) || 0, education: document.getElementById('editEducation').value,
                notes: document.getElementById('editNotes').value, core_skills: JSON.stringify(skillsArray), certifications: JSON.stringify(certsArray)
            };
            const res = await fetch(`/api/candidates/${id}`, { method: 'PUT', headers: {'Content-Type':'application/json'}, body: JSON.stringify(data) });
           if (res.ok) { toastSuccess('Updated!'); closeEditModal(); loadCandidates(); viewCandidate(id); }
        };
    };
    
    // Document upload - with null checks
window.openDocModal = function(id) { 
    currentCandidateId = id; 
    const docModal = document.getElementById('docModal');
    if (docModal) docModal.style.display = 'block'; 
};

const uploadDocBtn = document.getElementById('uploadDocBtn');
if (uploadDocBtn) {
    if (uploadDocBtn) uploadDocBtn.onclick = async function() {
        const docFile = document.getElementById('docFile');
        if (!docFile) return;
        const file = docFile.files[0];
        if (!file || !currentCandidateId) return;
        const fd = new FormData(); 
        fd.append('document', file); 
        fd.append('candidate_id', currentCandidateId);
        const docUploadStatus = document.getElementById('docUploadStatus');
        if (docUploadStatus) docUploadStatus.innerHTML = '<div class="spinner"></div>';
        const res = await fetch('/api/candidates/upload-document', { method: 'POST', body: fd });
        if (res.ok) { 
            toastSuccess('Uploaded!'); 
            const closeDocModal = window.closeDocModal;
            if (closeDocModal) closeDocModal(); 
            viewCandidate(currentCandidateId); 
        }
        if (docUploadStatus) docUploadStatus.innerHTML = '';
    };
}
    
    const exportBtn = document.getElementById('exportBtn');
if (exportBtn) exportBtn.onclick = () => window.location.href = '/api/export-candidates';
    
    const parseBtn = document.getElementById('parseBtn');
if (parseBtn) parseBtn.onclick = async function() {
        const file = document.getElementById('resumeFile').files[0];
        if(!file) return;
        const fd = new FormData(); fd.append('resume', file);
        const div = document.getElementById('parseResult');
        div.innerHTML = '<div class="spinner"></div><p>Parsing...</p>';
        const res = await fetch('/api/parse-resume', { method: 'POST', body: fd });
        const result = await res.json();
        if(result.error) { div.innerHTML = `<div class="alert-error">${result.error}</div>`; return; }
        div.innerHTML = `<div class="alert-success"><h4>✅ Parsed</h4><p><strong>Name:</strong> ${escapeHtml(result.first_name||'')} ${escapeHtml(result.last_name||'')}</p><p><strong>Email:</strong> ${escapeHtml(result.email||'')}</p><p><strong>Phone:</strong> ${escapeHtml(result.phone||'')}</p><p><strong>Skills:</strong> ${result.core_skills ? result.core_skills.map(s => `<span class="skill-tag">${escapeHtml(typeof s === 'object' ? (s.skill || s.name || '') : s)}</span>`).join('') : 'None'}</p><button id="saveBtn">💾 Save</button></div>`;
                             const saveBtn = document.getElementById('saveBtn'); if (saveBtn) saveBtn.onclick = async function() {
            // Check for duplicates first
            const dupRes = await fetch('/api/candidates/check-duplicate', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({ email: result.email, phone: result.phone })
            });
            const dupData = await dupRes.json();
            
            if (dupData.duplicate) {
                const dupNames = dupData.matches.map(m => `${m.first_name} ${m.last_name} (${m.email || m.phone})`).join(', ');
                const skip = confirm(`⚠️ Possible duplicate found!\n\nExisting candidate(s): ${dupNames}\n\nMatched by: ${dupData.matched_by}\n\nClick OK to save anyway, Cancel to skip.`);
                if (!skip) { toastInfo('Skipped duplicate'); return; }
            }
            
            // Ask for uploader name
            const uploaded_by = prompt('Enter your name (for tracking):', 'HR Team');
            result.uploaded_by = uploaded_by || 'ShahnaIT';
            
            const saveRes = await fetch('/api/candidates', { 
                method: 'POST', 
                headers: {'Content-Type': 'application/json'}, 
                body: JSON.stringify(result) 
            });
            if(saveRes.ok) { 
                toastSuccess('Saved! Resume auto-attached!'); 
                div.innerHTML = ''; 
                document.getElementById('resumeFile').value = ''; 
                loadCandidates(); 
                showPanel('candidates'); 
            }
            else alert('Error');
        };
    };
    
   const parseJDBtn = document.getElementById('parseJDBtn');
if (parseJDBtn) parseJDBtn.onclick = async function() {
    const fileInput = document.getElementById('jdFileInput');
    const file = fileInput.files[0];
    if (!file) { toastError('Please select a file'); return; }
    
    const status = document.getElementById('jdParseStatus');
    status.innerHTML = '<div class="spinner"></div> Parsing...';
    
    const fd = new FormData();
    fd.append('file', file);
    
    try {
        const res = await fetch('/api/jobs/parse-jd', { method: 'POST', body: fd });
        const result = await res.json();
        
        if (result.success && result.parsed) {
            const p = result.parsed;
            document.getElementById('jobTitle').value = p.title || '';
            document.getElementById('jobRoles').value = p.roles_responsibilities || '';
            document.getElementById('jobQualifications').value = p.qualifications || '';
            document.getElementById('jobSkills').value = (p.required_skills || []).join(', ');
            document.getElementById('jobDesc').value = result.text || '';
            status.innerHTML = '✅ JD parsed successfully!';
            toastSuccess('JD parsed!');
        } else {
            status.innerHTML = '❌ ' + (result.error || 'Parse failed');
        }
    } catch(e) {
        status.innerHTML = '❌ Error: ' + e.message;
    }
};

// Create job button
// Show/hide hybrid days based on working mode
const jobWorkingMode = document.getElementById('jobWorkingMode');
const hybridDaysGroup = document.getElementById('hybridDaysGroup');
if (jobWorkingMode && hybridDaysGroup) {
    jobWorkingMode.addEventListener('change', function() {
        hybridDaysGroup.style.display = this.value === 'Hybrid' ? 'block' : 'none';
    });
}

// Create job button
const createJobBtn = document.getElementById('createJobBtn');
if (createJobBtn) createJobBtn.onclick = async function() {
    const data = {
        title: document.getElementById('jobTitle').value,
        company: document.getElementById('jobCompany').value,
        working_mode: document.getElementById('jobWorkingMode').value,
        hybrid_days: parseInt(document.getElementById('jobHybridDays').value) || 0,
        business_model: document.getElementById('jobBusinessModel').value,
        payroll_company: document.getElementById('jobPayroll').value,
        end_client: document.getElementById('jobEndClient').value,
        years_of_experience: parseInt(document.getElementById('jobExperience').value) || 0,
        budget: document.getElementById('jobBudget').value,
        headcount: parseInt(document.getElementById('jobHeadcount').value) || 1,
        roles_responsibilities: document.getElementById('jobRoles').value,
        qualifications: document.getElementById('jobQualifications').value,
        certifications_required: document.getElementById('jobCertifications').value,
        required_skills: document.getElementById('jobSkills').value,
        description: document.getElementById('jobDesc').value
    };
    
    if (!data.title) { toastError('Title is required'); return; }
    
    const res = await fetch('/api/jobs', { 
        method: 'POST', 
        headers: {'Content-Type':'application/json'}, 
        body: JSON.stringify(data) 
    });
    
    if (res.ok) { 
        toastSuccess('Requirement created!'); 
        document.getElementById('jobTitle').value = '';
        document.getElementById('jobCompany').value = '';
        document.getElementById('jobWorkingMode').value = 'Not Specified';
        document.getElementById('jobHybridDays').value = '0';
        document.getElementById('jobBusinessModel').value = 'Not Specified';
        document.getElementById('jobPayroll').value = '';
        document.getElementById('jobEndClient').value = '';
        document.getElementById('jobExperience').value = '0';
        document.getElementById('jobBudget').value = '';
        document.getElementById('jobHeadcount').value = '1';
        document.getElementById('jobRoles').value = '';
        document.getElementById('jobQualifications').value = '';
        document.getElementById('jobCertifications').value = '';
        document.getElementById('jobSkills').value = '';
        document.getElementById('jobDesc').value = '';
        if (hybridDaysGroup) hybridDaysGroup.style.display = 'none';
        showPanel('jobs'); 
        loadJobs(); 
    } else { 
        toastError('Error creating requirement'); 
    }
};
    
    const analyzeBtn = document.getElementById('analyzeBtn'); if (analyzeBtn) analyzeBtn.onclick = async function() {
    const jobId = document.getElementById('jobSelect').value;
    const candidateId = document.getElementById('candidateSelect').value;
    if(!jobId || !candidateId) return;
    const job = allJobs.find(j => j.id == jobId);
    const cand = allCandidates.find(c => c.id == candidateId);
    const div = document.getElementById('analysisResult');
    div.innerHTML = '<div class="spinner"></div><p>🤖 Analyzing with AI...</p>';
    const res = await fetch('/api/analyze-match', { 
        method: 'POST', 
        headers: {'Content-Type':'application/json'}, 
        body: JSON.stringify({ 
            job_id: jobId, 
            candidate_id: candidateId, 
            jd_text: job.description || '', 
            resume_text: cand.resume_text || '' 
        }) 
    });
    const result = await res.json();
    if(result.error) { div.innerHTML = `<div class="alert-error">${result.error}</div>`; return; }
    
    const matchClass = result.match_score >= 70 ? 'match-high' : (result.match_score >= 40 ? 'match-medium' : 'match-low');
    
    // Build category scores display
    let categoryHtml = '';
    if (result.category_scores) {
        const cats = result.category_scores;
       categoryHtml = `
    <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 10px; margin: 10px 0;">
        <div style="background: #FFFFFF; padding: 12px 16px; border-radius: 8px; border: 1px solid #E0E0E0; border-left: 4px solid ${cats.skills_match >= 70 ? '#1A237E' : (cats.skills_match >= 40 ? '#283593' : '#B71C1C')};">
            <div style="font-size: 11px; color: #666;">Skills</div>
            <div style="font-size: 20px; font-weight: bold; color: #1A237E;">${cats.skills_match || 0}%</div>
        </div>
        <div style="background: #FFFFFF; padding: 12px 16px; border-radius: 8px; border: 1px solid #E0E0E0; border-left: 4px solid ${cats.experience_match >= 70 ? '#1A237E' : (cats.experience_match >= 40 ? '#283593' : '#B71C1C')};">
            <div style="font-size: 11px; color: #666;">Experience</div>
            <div style="font-size: 20px; font-weight: bold; color: #1A237E;">${cats.experience_match || 0}%</div>
        </div>
        <div style="background: #FFFFFF; padding: 12px 16px; border-radius: 8px; border: 1px solid #E0E0E0; border-left: 4px solid ${cats.education_match >= 70 ? '#1A237E' : (cats.education_match >= 40 ? '#283593' : '#B71C1C')};">
            <div style="font-size: 11px; color: #666;">Education</div>
            <div style="font-size: 20px; font-weight: bold; color: #1A237E;">${cats.education_match || 0}%</div>
        </div>
        <div style="background: #FFFFFF; padding: 12px 16px; border-radius: 8px; border: 1px solid #E0E0E0; border-left: 4px solid ${cats.certifications_match >= 70 ? '#1A237E' : (cats.certifications_match >= 40 ? '#283593' : '#B71C1C')};">
            <div style="font-size: 11px; color: #666;">Certifications</div>
            <div style="font-size: 20px; font-weight: bold; color: #1A237E;">${cats.certifications_match || 0}%</div>
        </div>
    </div>
`;
    }
    
    // Build skills display
    let skillsHtml = '';
        // Build genuineness display
    let genuinenessHtml = '';
    if (result.genuineness_score !== undefined) {
        const genClass = result.genuineness_score >= 70 ? 'match-high' : (result.genuineness_score >= 40 ? 'match-medium' : 'match-low');
        const aiClass = result.ai_generated_probability <= 30 ? 'match-high' : (result.ai_generated_probability <= 60 ? 'match-medium' : 'match-low');
        genuinenessHtml = `
            <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 10px; margin: 10px 0;">
                <div style="background: #FFFFFF; padding: 12px 16px; border-radius: 8px; border: 1px solid #E0E0E0; text-align: center;">
                    <div style="font-size: 11px; color: #666;">🔍 Authenticity</div>
                    <div style="font-size: 22px; font-weight: bold; margin-top: 4px;" class="${genClass}">${result.genuineness_score}%</div>
                </div>
                <div style="background: #FFFFFF; padding: 12px 16px; border-radius: 8px; border: 1px solid #E0E0E0; text-align: center;">
                    <div style="font-size: 11px; color: #666;">🤖 AI Probability</div>
                    <div style="font-size: 22px; font-weight: bold; margin-top: 4px;" class="${aiClass}">${result.ai_generated_probability}%</div>
                </div>
            </div>
        `;
        
        if (result.red_flags && result.red_flags.length > 0) {
            genuinenessHtml += `<div style="margin: 10px 0; padding: 12px; background: #F5F5F5; border-radius: 8px; border-left: 4px solid #B71C1C;">
                <strong style="color: #B71C1C; font-size: 14px;">🚨 Red Flags:</strong>
                <ul style="margin: 6px 0 0 0; padding-left: 20px; color: #B71C1C; font-size: 13px;">
                    ${result.red_flags.map(flag => `<li style="margin-bottom: 4px;">${escapeHtml(flag)}</li>`).join('')}
                </ul>
            </div>`;
        }
    }
 if (result.matching_skills && result.matching_skills.length > 0) {
    skillsHtml += `<div style="margin: 10px 0; padding: 12px; background: #F5F5F5; border-radius: 8px; border-left: 4px solid #1A237E;">
        <strong style="color: #1A237E; font-size: 14px;">✅ Matching Skills:</strong>
        <div style="margin-top: 6px; display: flex; flex-wrap: wrap; gap: 6px;">
            ${result.matching_skills.map(s => `<span style="background: #1A237E; color: #FFFFFF; padding: 4px 14px; border-radius: 20px; font-size: 13px; font-weight: 500; display: inline-block;">${escapeHtml(s)}</span>`).join('')}
        </div>
    </div>`;
}
if (result.missing_skills && result.missing_skills.length > 0) {
    skillsHtml += `<div style="margin: 10px 0; padding: 12px; background: #F5F5F5; border-radius: 8px; border-left: 4px solid #B71C1C;">
        <strong style="color: #B71C1C; font-size: 14px;">❌ Missing Skills:</strong>
        <div style="margin-top: 6px; display: flex; flex-wrap: wrap; gap: 6px;">
            ${result.missing_skills.map(s => `<span style="background: #B71C1C; color: #FFFFFF; padding: 4px 14px; border-radius: 20px; font-size: 13px; font-weight: 500; display: inline-block;">${escapeHtml(s)}</span>`).join('')}
        </div>
    </div>`;
}
    
    // Build strengths/weaknesses
    let swotHtml = '';
    if (result.strengths && result.strengths.length > 0) {
 if (result.strengths && result.strengths.length > 0) {
    swotHtml += `<div style="margin: 10px 0; padding: 12px; background: #F5F5F5; border-radius: 8px; border-left: 4px solid #1A237E;">
        <strong style="color: #1A237E; font-size: 14px;">💪 Strengths:</strong>
        <div style="margin-top: 6px; display: flex; flex-wrap: wrap; gap: 6px;">
            ${result.strengths.map(s => `<span style="background: #1A237E; color: #FFFFFF; padding: 4px 14px; border-radius: 20px; font-size: 13px; font-weight: 500; display: inline-block;">${escapeHtml(s)}</span>`).join('')}
        </div>
    </div>`;
}
if (result.weaknesses && result.weaknesses.length > 0) {
    swotHtml += `<div style="margin: 10px 0; padding: 12px; background: #F5F5F5; border-radius: 8px; border-left: 4px solid #B71C1C;">
        <strong style="color: #B71C1C; font-size: 14px;">⚠️ Weaknesses:</strong>
        <div style="margin-top: 6px; display: flex; flex-wrap: wrap; gap: 6px;">
            ${result.weaknesses.map(s => `<span style="background: #B71C1C; color: #FFFFFF; padding: 4px 14px; border-radius: 20px; font-size: 13px; font-weight: 500; display: inline-block;">${escapeHtml(s)}</span>`).join('')}
        </div>
    </div>`;
}
            }
    
    // Build questions
    let questionsHtml = '';
    if (result.pre_screening_questions && result.pre_screening_questions.length > 0) {
        questionsHtml = `<div style="margin-top: 10px;"><strong>📋 Pre-screening Questions:</strong><ul style="margin: 5px 0; padding-left: 20px;">`;
        result.pre_screening_questions.forEach(q => {
            questionsHtml += `<li>${escapeHtml(q)}</li>`;
        });
        questionsHtml += `</ul></div>`;
    }
    
    div.innerHTML = `
        <div class="alert-success" style="padding: 15px;">
            <h4>📊 Analysis Complete</h4>
            <div style="display: flex; align-items: center; gap: 20px; margin: 10px 0;">
                <div style="text-align: center;">
                    <div style="font-size: 36px; font-weight: bold;" class="${matchClass}">${result.match_score || 0}%</div>
                    <div style="font-size: 12px; color: #666;">Match Score</div>
                </div>
                <div>
                    <div><strong>Recommendation:</strong> <span style="text-transform: uppercase; font-weight: bold;">${result.recommendation || 'Review'}</span></div>
                    <div style="font-size: 14px; color: #1A1A2E; margin-top: 8px; line-height: 1.7; background: #FFFFFF; padding: 12px 16px; border-radius: 8px; border: 1px solid #D0D8E4; max-height: 250px; overflow-y: auto; white-space: pre-wrap;">${result.detailed_analysis || result.executive_summary ? escapeHtml(result.detailed_analysis || result.executive_summary) : '<em style="color:#999;">No detailed analysis available</em>'}</div>
                </div>
            </div>
            ${categoryHtml}
            ${genuinenessHtml}
            ${skillsHtml}
            ${swotHtml}
            ${questionsHtml}
            
            <!-- INTERVIEW QUESTIONS -->
        ${result.interview_questions ? `
        <div style="margin-top: 15px; padding: 15px; background: #E3F2FD; border-radius: 8px; border-left: 4px solid #1A4D4A;">
            <h4 style="margin: 0 0 10px 0; color: #1A4D4A;">🎤 Interview Questions</h4>
            
            ${result.interview_questions.technical.length > 0 ? `
            <div style="margin: 8px 0;">
                <strong style="color: #1A4D4A;">💻 Technical Questions:</strong>
                <ul style="margin: 5px 0; padding-left: 20px;">
                    ${result.interview_questions.technical.map(q => `<li style="margin-bottom: 4px; color: #333;">${escapeHtml(q)}</li>`).join('')}
                </ul>
            </div>` : ''}
            
            ${result.interview_questions.skill_check.length > 0 ? `
            <div style="margin: 8px 0;">
                <strong style="color: #1A4D4A;">🔍 Skill Check Questions:</strong>
                <ul style="margin: 5px 0; padding-left: 20px;">
                    ${result.interview_questions.skill_check.map(q => `<li style="margin-bottom: 4px; color: #333;">${escapeHtml(q)}</li>`).join('')}
                </ul>
            </div>` : ''}
            
            ${result.interview_questions.behavioral.length > 0 ? `
            <div style="margin: 8px 0;">
                <strong style="color: #1A4D4A;">🧠 Behavioral Questions:</strong>
                <ul style="margin: 5px 0; padding-left: 20px;">
                    ${result.interview_questions.behavioral.map(q => `<li style="margin-bottom: 4px; color: #333;">${escapeHtml(q)}</li>`).join('')}
                </ul>
            </div>` : ''}
        </div>` : ''}
                    // Add Skill Gap Analysis
        ${result.skill_gap ? `
        <div style="margin-top: 15px; padding: 15px; background: #F9F6F0; border-radius: 8px; border-left: 4px solid #C9A96E;">
            <h4 style="margin: 0 0 10px 0; color: #1A4D4A;">📊 Skill Gap Analysis</h4>
            
            <div style="display: flex; gap: 20px; flex-wrap: wrap; margin-bottom: 10px;">
                <div style="background: #E8F5E9; padding: 6px 14px; border-radius: 20px;">
                    <strong style="color: #1B5E20;">✅ Matching:</strong> 
                    <span style="color: #1B5E20; font-weight: bold;">${result.skill_gap.matching_skills.length}</span>
                </div>
                <div style="background: #FFEBEE; padding: 6px 14px; border-radius: 20px;">
                    <strong style="color: #B71C1C;">❌ Missing:</strong> 
                    <span style="color: #B71C1C; font-weight: bold;">${result.skill_gap.missing_skills.length}</span>
                </div>
                <div style="background: #FFF3E0; padding: 6px 14px; border-radius: 20px;">
                    <strong style="color: #E65100;">📊 Gap:</strong> 
                    <span style="color: #E65100; font-weight: bold;">${result.skill_gap.gap_percentage}%</span>
                </div>
            </div>
            
            ${result.skill_gap.matching_skills.length > 0 ? `
            <div style="margin: 10px 0;">
                <strong style="color: #1A4D4A;">✅ Matching Skills:</strong>
                <div style="display: flex; flex-wrap: wrap; gap: 5px; margin-top: 5px;">
                    ${result.skill_gap.matching_skills.map(s => `<span style="background: #1B6B2E; color: #FFFFFF; padding: 4px 14px; border-radius: 20px; font-size: 12px; font-weight: 500; display: inline-block;">${escapeHtml(s)}</span>`).join('')}
                </div>
            </div>` : ''}
            
            ${result.skill_gap.missing_skills.length > 0 ? `
            <div style="margin: 10px 0;">
                <strong style="color: #1A4D4A;">❌ Missing Skills:</strong>
                <div style="display: flex; flex-wrap: wrap; gap: 5px; margin-top: 5px;">
                    ${result.skill_gap.missing_skills.map(s => `<span style="background: #B71C1C; color: #FFFFFF; padding: 4px 14px; border-radius: 20px; font-size: 12px; font-weight: 500; display: inline-block;">${escapeHtml(s)}</span>`).join('')}
                </div>
            </div>` : ''}
            
            ${result.skill_gap.learning_path.length > 0 ? `
            <div style="margin-top: 10px; background: #FFFFFF; padding: 12px; border-radius: 8px; border: 1px solid #E8E0D8;">
                <strong style="color: #1A4D4A;">📚 Learning Path:</strong>
                <ul style="margin: 8px 0 0 0; padding-left: 20px; list-style-type: none;">
                    ${result.skill_gap.learning_path.map(item => `
                        <li style="margin-bottom: 10px; padding: 10px; background: #F9F6F0; border-radius: 6px; border-left: 3px solid #C9A96E;">
                            <strong style="color: #1A4D4A;">${escapeHtml(item.skill)}</strong>
                            <span style="background: #FFF3E0; color: #E65100; padding: 2px 10px; border-radius: 12px; font-size: 11px; margin-left: 8px;">${item.estimated_hours} hours</span>
                            <ul style="margin: 5px 0 0 0; padding-left: 20px; font-size: 12px; color: #555;">
                                ${item.resources.map(r => `<li style="margin-bottom: 3px; color: #555;">${escapeHtml(r)}</li>`).join('')}
                            </ul>
                        </li>
                    `).join('')}
                </ul>
            </div>` : ''}
        </div>` : ''}
            <small style="display: block; margin-top: 10px;">✅ Analysis saved to candidate record</small>
        </div>
    `;
    loadCandidates();
};
    
    // ========== BULK RESUME UPLOAD ==========
    document.getElementById('multiResumeFiles').addEventListener('change', function(e) {
        selectedBulkFiles = Array.from(e.target.files);
        const fileListDiv = document.getElementById('selectedFilesList');
        if (selectedBulkFiles.length > 0) {
            let html = '<strong>Selected files (' + selectedBulkFiles.length + '):</strong><br>';
            selectedBulkFiles.forEach((file, index) => {
                html += `<div class="file-list-item">📄 ${escapeHtml(file.name)} (${(file.size / 1024).toFixed(1)} KB)<span class="remove-file" onclick="removeBulkFile(${index})">✕ Remove</span></div>`;
            });
            fileListDiv.innerHTML = html;
            fileListDiv.style.display = 'block';
        } else {
            fileListDiv.style.display = 'none';
        }
    });
    
    window.removeBulkFile = function(index) {
        selectedBulkFiles.splice(index, 1);
        const dataTransfer = new DataTransfer();
        selectedBulkFiles.forEach(file => dataTransfer.items.add(file));
        document.getElementById('multiResumeFiles').files = dataTransfer.files;
        
        const fileListDiv = document.getElementById('selectedFilesList');
        if (selectedBulkFiles.length > 0) {
            let html = '<strong>Selected files (' + selectedBulkFiles.length + '):</strong><br>';
            selectedBulkFiles.forEach((file, idx) => {
                html += `<div class="file-list-item">📄 ${escapeHtml(file.name)} (${(file.size / 1024).toFixed(1)} KB)<span class="remove-file" onclick="removeBulkFile(${idx})">✕ Remove</span></div>`;
            });
            fileListDiv.innerHTML = html;
            fileListDiv.style.display = 'block';
        } else {
            fileListDiv.style.display = 'none';
        }
    };
    
    const bulkUploadBtn = document.getElementById('bulkUploadBtn'); if (bulkUploadBtn) bulkUploadBtn.onclick = async function() {
        if (selectedBulkFiles.length === 0) { toastWarning('Please select files first'); return; }
        
        const div = document.getElementById('bulkUploadResult');
        div.innerHTML = '<div class="spinner"></div><p>📚 Processing ' + selectedBulkFiles.length + ' files...</p>';
        
        let successCount = 0;
        let failCount = 0;
        let errors = [];
        
        for (let i = 0; i < selectedBulkFiles.length; i++) {
            const file = selectedBulkFiles[i];
            const fd = new FormData();
            fd.append('resume', file);
            
            const percent = Math.round((i / selectedBulkFiles.length) * 100);
            div.innerHTML = `<div class="progress-bar"><div class="progress-fill" style="width: ${percent}%"></div></div>
    <div style="max-height: 300px; overflow-y: auto; margin-top: 10px;">
    <div><strong>📄 ${i+1} of ${selectedBulkFiles.length}:</strong> ${escapeHtml(file.name)}</div>
    <div id="liveStatus${i}" style="font-size: 13px; margin-left: 20px; margin-bottom: 10px;">⏳ Parsing...</div>
    </div>`;
            
            try {
                const res = await fetch('/api/parse-resume', { method: 'POST', body: fd });
                const result = await res.json();
document.getElementById(`liveStatus${i}`).innerHTML = result.error ? '❌ Parse failed: ' + escapeHtml(result.error) : '✅ Parsed successfully, saving...';
                
                 if (result.error) {
                    failCount++;
                    errors.push(`${file.name}: ${result.error}`);
                    document.getElementById(`liveStatus${i}`).innerHTML = '❌ Parse failed: ' + escapeHtml(result.error);
                } else {
                    // Check duplicate
                    const dupRes = await fetch('/api/candidates/check-duplicate', {
                        method: 'POST',
                        headers: {'Content-Type': 'application/json'},
                        body: JSON.stringify({ email: result.email, phone: result.phone })
                    });
                    const dupData = await dupRes.json();
                    
                    if (dupData.duplicate) {
                        document.getElementById(`liveStatus${i}`).innerHTML = '⚠️ Duplicate skipped (matched by ' + dupData.matched_by + ')';
                        failCount++;
                        errors.push(`${file.name}: Duplicate - ${dupData.matches[0].first_name} ${dupData.matches[0].last_name}`);
                        continue; // Skip saving, move to next file
                    }
                    
                    // Save candidate
                    const saveRes = await fetch('/api/candidates', { 
                        method: 'POST', 
                        headers: {'Content-Type': 'application/json'}, 
                        body: JSON.stringify(result) 
                    });
                    document.getElementById(`liveStatus${i}`).innerHTML = saveRes.ok ? '✅ Saved! Resume auto-attached.' : '❌ Save failed';
                    if (saveRes.ok) {
                        successCount++;
                    } else {
                        failCount++;
                        errors.push(`${file.name}: Save failed`);
                    }
                }
                        } catch(e) {
                failCount++;
                errors.push(`${file.name}: ${e.message}`);
                document.getElementById(`liveStatus${i}`).innerHTML = `❌ Error: ${escapeHtml(e.message)}`;
            }
        }
        
        let resultHtml = `<div class="alert-success"><h4>✅ Bulk Upload Complete!</h4>`;
        resultHtml += `<p><strong>Total files:</strong> ${selectedBulkFiles.length}</p>`;
        resultHtml += `<p><strong>Successfully saved:</strong> ${successCount}</p>`;
        resultHtml += `<p><strong>Failed:</strong> ${failCount}</p>`;
        
        if (errors.length > 0 && errors.length <= 10) {
            resultHtml += `<div style="margin-top: 10px;"><strong>⚠️ Errors:</strong><ul>`;
            errors.forEach(err => { resultHtml += `<li>${escapeHtml(err)}</li>`; });
            resultHtml += `</ul></div>`;
        } else if (errors.length > 10) {
            resultHtml += `<p><strong>⚠️ ${errors.length} errors occurred. Check console for details.</strong></p>`;
        }
        
        resultHtml += `<button class="btn" onclick="document.getElementById('tabCandidates').click()" style="margin-top: 15px;">View All Candidates</button></div>`;
        div.innerHTML = resultHtml;
        
        // Clear selection
        selectedBulkFiles = [];
        document.getElementById('multiResumeFiles').value = '';
        document.getElementById('selectedFilesList').style.display = 'none';
        
        loadCandidates();
    };

        // ========== BATCH ANALYZE - Match JD Against ALL Candidates ==========
       const batchAnalyzeBtn = document.getElementById('batchAnalyzeBtn'); if (batchAnalyzeBtn) batchAnalyzeBtn.onclick = async function() {
        const jobId = document.getElementById('batchJobSelect').value;
       if (!jobId) { toastWarning('Please select a Job'); return; }
        
        const job = allJobs.find(j => j.id == jobId);
        if (!job) { toastWarning('Job not found'); return; }
        
        const div = document.getElementById('batchAnalysisResult');
        div.innerHTML = '<div class="spinner"></div><p>📊 Analyzing ' + allCandidates.length + ' candidates with enhanced matching...</p>';
        
        try {
            const res = await fetch('/api/batch-analyze', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({ jd_text: job.description || '' })
            });
            const results = await res.json();
            
            if (results.error) {
                div.innerHTML = `<div class="alert-error">${results.error}</div>`;
                return;
            }
            
            // Count candidates with meaningful match (>0%)
            const meaningfulMatches = results.filter(r => r.match_score > 0).length;
            
            let html = `<div class="alert-success" style="padding: 15px;"><h4>📊 Batch Analysis Complete</h4>`;
            html += `<div style="display: flex; gap: 20px; flex-wrap: wrap; margin: 10px 0;">`;
            html += `<div><strong>Job:</strong> ${escapeHtml(job.title)}</div>`;
            html += `<div><strong>Total Candidates:</strong> ${results.length}</div>`;
            html += `<div><strong>Candidates with any match (>0%):</strong> ${meaningfulMatches}</div>`;
            html += `</div><hr><div style="max-height: 500px; overflow-y: auto;">`;
            
            if (results.length === 0) {
                html += `<p style="color: #666; font-style: italic;">No candidates found in database.</p>`;
            } else {
               results.forEach((r, index) => {
    const matchClass = r.match_score >= 70 ? 'match-high' : (r.match_score >= 40 ? 'match-medium' : 'match-low');
    const nameDisplay = r.name && r.name !== 'Unknown' ? r.name : 'Unknown Candidate';
    
    // Medal emoji based on rank
    let medal = '';
    if (r.rank === 1) medal = '🥇';
    else if (r.rank === 2) medal = '🥈';
    else if (r.rank === 3) medal = '🥉';
    
    // Top 3 background highlight
    let bgStyle = '';
    if (r.rank === 1) bgStyle = 'background: linear-gradient(135deg, #FFF9C4 0%, #FFF176 100%); border-left: 4px solid #FFD700;';
    else if (r.rank === 2) bgStyle = 'background: linear-gradient(135deg, #E8F5E9 0%, #C8E6C9 100%); border-left: 4px solid #C0C0C0;';
    else if (r.rank === 3) bgStyle = 'background: linear-gradient(135deg, #FFF3E0 0%, #FFE0B2 100%); border-left: 4px solid #CD7F32;';
    
    html += `<div class="card" style="cursor: pointer; margin: 8px 0; padding: 12px; border-left: 4px solid ${r.match_score >= 70 ? '#1B6B2E' : (r.match_score >= 40 ? '#CC5500' : '#B22222')}; ${bgStyle}">
        <div style="display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 10px;">
            <div onclick="viewCandidate(${r.candidate_id})" style="flex: 1; cursor: pointer;">
                <div style="display: flex; align-items: center; gap: 10px;">
                    <span style="font-weight: bold; color: #666; font-size: 16px; min-width: 40px;">${medal} #${r.rank}</span>
                    <span style="font-size: 16px; font-weight: bold;">👤 ${escapeHtml(nameDisplay)}</span>
                    ${r.rank <= 3 ? `<span style="background: #FFD700; color: #000; padding: 2px 12px; border-radius: 12px; font-size: 10px; font-weight: bold;">TOP ${r.rank}</span>` : ''}
                </div>
                ${r.email ? `<div style="font-size: 12px; color: #666; margin-top: 2px;">📧 ${escapeHtml(r.email)}</div>` : ''}
                ${r.tech_found && r.tech_found.length > 0 ? `<div style="font-size: 11px; color: #555; margin-top: 4px;">🔧 ${r.tech_found.map(t => `<span style="background: #E8F5E9; padding: 1px 8px; border-radius: 10px; margin: 2px; display: inline-block;">${escapeHtml(t)}</span>`).join(' ')}</div>` : ''}
                <div style="font-size: 11px; color: #999; margin-top: 4px;">
                    ${r.rank} of ${r.total_candidates} candidates
                </div>
            </div>
            <div style="text-align: right; min-width: 80px;">
                <div><span class="${matchClass}" style="font-size: 18px; padding: 4px 14px;">${r.match_score}%</span></div>
                <div style="font-size: 11px; margin-top: 2px; color: ${r.recommendation === 'hire' ? '#1B6B2E' : (r.recommendation === 'interview' ? '#CC5500' : '#B22222')};">
                    ${r.recommendation || 'Review'}
                </div>
                <button class="btn" style="background: #C9A96E; color: white; padding: 2px 10px; font-size: 10px; margin-top: 4px; border: none; border-radius: 4px; cursor: pointer;" onclick="event.stopPropagation(); runDeepAnalysis(${r.candidate_id}, '${escapeHtml(job.title)}')">🔍 AI Deep Dive</button>
            </div>
        </div>
    </div>`;
});
            }
            
            html += `</div>
                <div style="margin-top: 15px; display: flex; gap: 10px; flex-wrap: wrap;">
                    <button class="btn" onclick="document.getElementById('tabCandidates').click()" style="margin-top:0;">👥 View All Candidates</button>
                    <button class="btn" onclick="document.getElementById('tabAnalyze').click(); loadJobs(); loadCandidates();" style="background: #C9A96E; margin-top:0;">🔍 Go to Single Analysis</button>
                </div>
            </div>`;
            div.innerHTML = html;
            
        } catch(e) {
            console.error('Batch analysis error:', e);
            div.innerHTML = '<div class="alert-error">❌ Analysis failed. Please try again.</div>';
        }
    };
      
           // ========== EXPORT PDF ==========
    window.exportPDF = async function(candidateId, event) {
        const btn = event.target;
        btn.textContent = '⏳ Generating...';
        btn.disabled = true;
        
        try {
            const res = await fetch(`/api/candidates/${candidateId}/export-pdf`);
            if (res.ok) {
                const blob = await res.blob();
                const url = window.URL.createObjectURL(blob);
                const a = document.createElement('a');
                a.href = url;
                
                // Get candidate name for filename
                const c = allCandidates.find(c => c.id == candidateId);
                const name = ((c.first_name || '') + '_' + (c.last_name || '')).trim() || 'candidate';
                a.download = `${name}_profile.pdf`;
                document.body.appendChild(a);
                a.click();
                a.remove();
                window.URL.revokeObjectURL(url);
            } else {
                toastError('Failed to generate PDF');
            }
        } catch(e) {
            toastError('Error generating PDF');
        } finally {
            btn.textContent = '📄 Export PDF';
            btn.disabled = false;
        }
    };
        // ========== STATUS MANAGEMENT ==========
    function getStatusColor(status) {
        const colors = {
            'new': '#2196F3',
            'screening': '#FF9800',
            'interview': '#FF5722',
            'offer': '#9C27B0',
            'hired': '#4CAF50',
            'rejected': '#F44336'
        };
        return colors[status] || '#666';
    }
    
    window.updateStatus = async function(candidateId, newStatus) {
        try {
            const res = await fetch(`/api/candidates/${candidateId}/status`, {
                method: 'PUT',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({ employment_status: newStatus })
            });
            
            if (res.ok) {
                // Update the dropdown background color
                const dropdown = document.getElementById(`candidateStatus-${candidateId}`);
                if (dropdown) {
                    dropdown.style.background = getStatusColor(newStatus);
                }
                // Reload candidates list to reflect changes
                loadCandidates();
            } else {
                toastError('Failed to update status');
                // Reload to revert dropdown
                loadCandidates();
            }
        } catch(e) {
            toastError('Error updating status');
            loadCandidates();
        }
    };
        // ========== DASHBOARD ==========
    let matchChartInstance = null;
    let pipelineChartInstance = null;
    let trendChartInstance = null;

// ============================================
// USER MANAGEMENT
// ============================================

async function loadUsers() {
    try {
        const res = await fetch('/api/auth/users');
        if (!res.ok) { toastError('Admin access required'); return; }
        const users = await res.json();
        const container = document.getElementById('usersList');
        if (!users.length) {
            container.innerHTML = '<div class="card no-click" style="text-align:center;padding:30px;">No users found</div>';
            return;
        }
        container.innerHTML = users.map(u => `
            <div class="card" style="margin-bottom:8px;">
                <div style="display:flex;justify-content:space-between;align-items:center;flex-wrap:wrap;gap:10px;">
                    <div style="flex:1;min-width:200px;">
                        <strong>${escapeHtml(u.full_name)}</strong>
                        <span style="font-size:12px;color:#666;margin-left:8px;">${escapeHtml(u.email)}</span>
                        <span style="background:${u.role==='admin'?'#1B2A4A':u.role==='manager'?'#0D7B4A':'#6366F1'};color:#fff;padding:2px 10px;border-radius:12px;font-size:11px;margin-left:8px;">${u.role.toUpperCase()}</span>
                        ${!u.is_active ? '<span style="background:#EF4444;color:#fff;padding:2px 10px;border-radius:12px;font-size:11px;margin-left:8px;">Disabled</span>' : ''}
                    </div>
                    <div style="display:flex;gap:6px;align-items:center;">
                        <select onchange="updateUserRole(${u.id}, this.value)" style="font-size:12px;padding:4px 8px;border-radius:6px;border:1px solid #D0D8E4;">
                            <option value="admin" ${u.role==='admin'?'selected':''}>Admin</option>
                            <option value="manager" ${u.role==='manager'?'selected':''}>Manager</option>
                            <option value="recruiter" ${u.role==='recruiter'?'selected':''}>Recruiter</option>
                        </select>
                        <button class="btn btn-sm ${u.is_active ? 'btn-danger' : 'btn-secondary'}" onclick="toggleUserStatus(${u.id}, ${u.is_active ? 'false' : 'true'})" style="font-size:11px;padding:4px 10px;">
                            ${u.is_active ? '🚫 Disable' : '✅ Enable'}
                        </button>
                    </div>
                </div>
            </div>
        `).join('');
    } catch(e) {
        toastError('Failed to load users');
    }
}

async function updateUserRole(userId, role) {
    const res = await fetch('/api/auth/users/' + userId, {
        method: 'PUT', headers: {'Content-Type': 'application/json'}, body: JSON.stringify({ role: role })
    });
    if (res.ok) { toastSuccess('Role updated'); loadUsers(); } else { toastError('Failed to update role'); }
}

async function toggleUserStatus(userId, isActive) {
    const res = await fetch('/api/auth/users/' + userId, {
        method: 'PUT', headers: {'Content-Type': 'application/json'}, body: JSON.stringify({ is_active: isActive })
    });
    if (res.ok) { toastSuccess(isActive ? 'User enabled' : 'User disabled'); loadUsers(); } else { toastError('Failed to update user'); }
}

document.addEventListener('DOMContentLoaded', function() {
    const addUserBtn = document.getElementById('addUserBtn');
    if (addUserBtn) addUserBtn.onclick = async function() {
        const full_name = document.getElementById('newUserName').value;
        const email = document.getElementById('newUserEmail').value;
        const password = document.getElementById('newUserPassword').value;
        const role = document.getElementById('newUserRole').value;
        const statusDiv = document.getElementById('addUserStatus');
        if (!full_name || !email || !password) { statusDiv.innerHTML = '<span style="color:#EF4444;">All fields required</span>'; return; }
        statusDiv.innerHTML = '<span style="color:#6366F1;">Creating...</span>';
        const res = await fetch('/api/auth/users', {
            method: 'POST', headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({ full_name, email, password, role })
        });
        if (res.ok) {
            statusDiv.innerHTML = '<span style="color:#10B981;">✅ User created!</span>';
            document.getElementById('newUserName').value = '';
            document.getElementById('newUserEmail').value = '';
            document.getElementById('newUserPassword').value = '';
            loadUsers();
        } else {
            const data = await res.json();
            statusDiv.innerHTML = '<span style="color:#EF4444;">' + (data.error || 'Failed') + '</span>';
        }
    };
});

async function triggerBackup() {
    const div = document.getElementById('backupStatus');
    div.innerHTML = '<span style="color:#6366F1;">⏳ Creating backup...</span>';
    try {
        const res = await fetch('/api/admin/backup', { method: 'POST' });
        const data = await res.json();
        if (data.success) {
            const driveMsg = data.drive_upload ? '✅ Uploaded to Google Drive' : '⚠️ Local only';
            div.innerHTML = `<span style="color:#10B981;">✅ Backup saved: ${data.filename}</span><br><span>${driveMsg}</span>`;
        } else {
            div.innerHTML = `<span style="color:#EF4444;">❌ ${data.error}</span>`;
        }
    } catch(e) {
        div.innerHTML = '<span style="color:#EF4444;">❌ Backup failed</span>';
    }
}

async function listBackups() {
    const div = document.getElementById('backupStatus');
    try {
        const res = await fetch('/api/admin/backups');
        const data = await res.json();
        if (data.backups && data.backups.length > 0) {
            div.innerHTML = '<strong>📂 Backups:</strong><br>' + data.backups.slice(0,10).map(b => 
                `<a href="/api/admin/backup/download/${b.filename}" style="color:#1B2A4A;">📥 ${b.filename}</a> (${b.size})`
            ).join('<br>');
        } else {
            div.innerHTML = '<span style="color:#666;">No backups found</span>';
        }
    } catch(e) {
        div.innerHTML = '<span style="color:#EF4444;">Failed to load backups</span>';
    }
}
    
    async function loadDashboard() {
        try {
            const res = await fetch('/api/dashboard-data');
            const data = await res.json();
            
            // Update stats cards
            document.getElementById('totalCandidates').textContent = data.total || 0;
            document.getElementById('matchedCandidates').textContent = data.matched || 0;
            document.getElementById('hiredCandidates').textContent = data.hired || 0;
            document.getElementById('rejectedCandidates').textContent = data.rejected || 0;
            
            // Render match score chart
            renderMatchChart(data.matchDistribution || {});
            
            // Render pipeline chart
            renderPipelineChart(data.pipeline || {});
            
            // Render skills cloud
            renderSkillsCloud(data.skills || []);
            
            // Render trend chart
            renderTrendChart(data.trend || {});
            
        } catch(e) {
            console.error('Dashboard error:', e);
        }
    }
    
    function renderMatchChart(distribution) {
        const ctx = document.getElementById('matchChart').getContext('2d');
        const labels = ['0-20%', '21-40%', '41-60%', '61-80%', '81-100%'];
        const values = [
            distribution['0-20'] || 0,
            distribution['21-40'] || 0,
            distribution['41-60'] || 0,
            distribution['61-80'] || 0,
            distribution['81-100'] || 0
        ];
        const colors = ['#F44336', '#FF9800', '#FFC107', '#4CAF50', '#1B6B2E'];
        
        if (matchChartInstance) {
            matchChartInstance.destroy();
        }
        
        matchChartInstance = new Chart(ctx, {
            type: 'bar',
            data: {
                labels: labels,
                datasets: [{
                    label: 'Candidates',
                    data: values,
                    backgroundColor: colors,
                    borderColor: colors.map(c => c),
                    borderWidth: 1
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: true,
                plugins: {
                    legend: { display: false }
                },
                scales: {
                    y: {
                        beginAtZero: true,
                        ticks: { stepSize: 1 }
                    }
                }
            }
        });
    }
    
function renderPipelineChart(pipeline) {
    const canvas = document.getElementById('pipelineChart');
    if (!canvas) return;
    const ctx = canvas.getContext('2d');
    
    const labels = ['New', 'Proposed', 'Screening', 'Tech L1', 'Tech L2', 'Tech L3', 'Rejected', 'Shortlisted', 'Offer Shared', 'Onboarded'];
    const values = [
        pipeline.new || 0,
        pipeline.proposed || 0,
        pipeline.screening || 0,
        pipeline.technical_l1 || 0,
        pipeline.technical_l2 || 0,
        pipeline.technical_l3 || 0,
        pipeline.rejected || 0,
        pipeline.shortlisted || 0,
        pipeline.offer_letter_shared || 0,
        pipeline.onboarded || 0
    ];
    const colors = [
        '#1B5F8C',  // New - Blue
        '#6B4CB8',  // Proposed - Purple
        '#B85C00',  // Screening - Orange
        '#0D7B4A',  // Tech L1 - Green
        '#0D7B4A',  // Tech L2 - Green
        '#0A5C35',  // Tech L3 - Dark Green
        '#C42020',  // Rejected - Red
        '#D4A800',  // Shortlisted - Gold
        '#2C7A4A',  // Offer Shared - Green
        '#1B5F8C'   // Onboarded - Blue
    ];
    
    if (pipelineChartInstance) pipelineChartInstance.destroy();
    
    pipelineChartInstance = new Chart(ctx, {
        type: 'doughnut',
        data: { 
            labels: labels, 
            datasets: [{ 
                data: values, 
                backgroundColor: colors, 
                borderColor: '#fff', 
                borderWidth: 2 
            }] 
        },
        options: { 
            responsive: true, 
            maintainAspectRatio: true, 
            plugins: { 
                legend: { 
                    position: 'right', 
                    labels: { boxWidth: 12, font: { size: 10 } } 
                } 
            } 
        }
    });
}
    
    function renderSkillsCloud(skills) {
    const container = document.getElementById('skillsCloud');
    if (!container) return;
    if (!skills || skills.length === 0) { 
        container.innerHTML = '<p style="color: #999; font-style: italic;">No skills data available</p>'; 
        return; 
    }
    
    const normalizedSkills = skills.map(s => 
        typeof s === 'object' ? {skill: s.skill || s.name || '', count: s.count || 1} : {skill: String(s), count: 1}
    );
    const topSkills = normalizedSkills.slice(0, 15);
    const maxCount = topSkills[0]?.count || 1;
    
    container.innerHTML = topSkills.map(s => {
        const size = 10 + (s.count / maxCount) * 8;
        return '<span style="font-size:' + size + 'px; color:#1A4D4A; background:#F5F0E8; padding:4px 12px; border-radius:20px; border:1px solid #ddd; opacity:' + (0.6 + (s.count / maxCount) * 0.4) + ';">' + escapeHtml(s.skill) + '</span>';
    }).join('');
}
    
    function renderTrendChart(trend) {
        const ctx = document.getElementById('trendChart').getContext('2d');
        const labels = trend.labels || [];
        const values = trend.values || [];
        
        if (trendChartInstance) {
            trendChartInstance.destroy();
        }
        
        if (labels.length === 0) {
            trendChartInstance = null;
            return;
        }
        
        trendChartInstance = new Chart(ctx, {
            type: 'line',
            data: {
                labels: labels,
                datasets: [{
                    label: 'Candidates Added',
                    data: values,
                    borderColor: '#1A4D4A',
                    backgroundColor: 'rgba(26, 77, 74, 0.1)',
                    fill: true,
                    tension: 0.3,
                    pointBackgroundColor: '#1A4D4A'
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: true,
                plugins: {
                    legend: { display: false }
                },
                scales: {
                    y: {
                        beginAtZero: true,
                        ticks: { stepSize: 1 }
                    }
                }
            }
        });
    }

    // ========== DASHBOARD ==========
// ============================================
// KANBAN BOARD
// ============================================

const kanbanStages = [
    { id: 'new', name: 'New', color: '#2196F3', emoji: '🆕' },
    { id: 'proposed', name: 'Proposed', color: '#6B4CB8', emoji: '📋' },
    { id: 'screening', name: 'Screening', color: '#FF9800', emoji: '🔍' },
    { id: 'technical_l1', name: 'L1 Tech', color: '#0D7B4A', emoji: '💻' },
    { id: 'technical_l2', name: 'L2 Tech', color: '#0D7B4A', emoji: '💻' },
    { id: 'technical_l3', name: 'L3 Tech', color: '#0A5C35', emoji: '💻' },
    { id: 'shortlisted', name: 'Shortlisted', color: '#D4A800', emoji: '⭐' },
    { id: 'offer_letter_shared', name: 'Offer', color: '#2C7A4A', emoji: '📄' },
    { id: 'onboarded', name: 'Onboarded', color: '#1B5F8C', emoji: '✅' },
    { id: 'rejected', name: 'Rejected', color: '#C42020', emoji: '❌' }
];

function searchOnbCandidate() {
    const search = document.getElementById('onbCandidate').value.toLowerCase();
    const list = document.getElementById('onbCandidateList');
    if (!search || search.length < 1) { list.innerHTML = ''; return; }
    const matches = allCandidates.filter(c => 
        (c.first_name + ' ' + c.last_name).toLowerCase().includes(search) ||
        String(c.id).padStart(3,'0').includes(search)
    );
    list.innerHTML = matches.map(c => 
        `<option value="${String(c.id).padStart(3,'0')} - ${escapeHtml((c.first_name||'') + ' ' + (c.last_name||''))}">`
    ).join('');
}

function searchOnbRequirement() {
    const search = document.getElementById('onbRequirementId').value.toLowerCase();
    const list = document.getElementById('onbReqList');
    if (!search || search.length < 1) { list.innerHTML = ''; return; }
    const matches = allJobs.filter(j => 
        (j.requirement_id || '').toLowerCase().includes(search) ||
        (j.title || '').toLowerCase().includes(search)
    );
    list.innerHTML = matches.map(j => 
        `<option value="${(j.requirement_id || 'SIT-R-'+String(j.id).padStart(3,'0')).replace('SIT-R-','')} - ${escapeHtml(j.title || '')}">`
    ).join('');
}

async function editOnboarded(id) {
    const res = await fetch('/api/onboarded');
    const resources = await res.json();
    const r = resources.find(r => r.id == id);
    if (!r) return;
    
    const modal = document.createElement('div');
    modal.style.cssText = 'position:fixed;top:0;left:0;width:100%;height:100%;background:rgba(0,0,0,0.5);z-index:9999;display:flex;align-items:center;justify-content:center;';
    modal.innerHTML = `<div style="background:#fff;padding:25px;border-radius:12px;width:90%;max-width:500px;max-height:80vh;overflow-y:auto;">
        <h3>✏️ Edit Onboarded Resource</h3>
        <label>Client</label><input id="editOnbClient" class="form-input" value="${escapeHtml(r.client_name||'')}">
        <label>DOJ</label><input id="editOnbDOJ" type="date" class="form-input" value="${r.doj||''}">
        <label>Resource Owner</label><input id="editOnbOwner" class="form-input" value="${escapeHtml(r.resource_owner||'')}">
        <label>Work Location</label><input id="editOnbLocation" class="form-input" value="${escapeHtml(r.work_location||'')}">
        <label>Monthly Salary (₹)</label><input id="editOnbSalary" type="number" class="form-input" value="${r.monthly_salary||0}">
        <label>Billing Rate (₹)</label><input id="editOnbBilling" type="number" class="form-input" value="${r.billing_rate||0}">
        <label>Business Model</label><select id="editOnbModel" class="form-input">
            <option value="C2C" ${r.business_model==='C2C'?'selected':''}>C2C</option>
            <option value="C2H" ${r.business_model==='C2H'?'selected':''}>C2H</option>
            <option value="FTE" ${r.business_model==='FTE'?'selected':''}>FTE</option>
            <option value="Fixed Price" ${r.business_model==='Fixed Price'?'selected':''}>Fixed Price</option>
        </select>
        <label>Requirement ID</label><input id="editOnbReq" class="form-input" value="${escapeHtml(r.requirement_id||'')}">
        <label>PO Number</label><input id="editOnbPO" class="form-input" value="${escapeHtml(r.po_number||'')}">
        <label>Status</label><select id="editOnbStatus" class="form-input">
            <option value="Active" ${r.status==='Active'?'selected':''}>Active</option>
            <option value="Completed" ${r.status==='Completed'?'selected':''}>Completed</option>
            <option value="Terminated" ${r.status==='Terminated'?'selected':''}>Terminated</option>
        </select>
                <label>Attach Documents</label><input type="file" id="editOnbDocs" multiple accept=".pdf,.docx,.doc" style="font-size:12px;">
        <div style="margin-top:15px;display:flex;gap:10px;">
            <button id="saveOnbEdit" class="btn btn-primary">💾 Save</button>
            <button id="cancelOnbEdit" class="btn btn-secondary">Cancel</button>
        </div>
    </div>`;
    document.body.appendChild(modal);
    
    document.getElementById('cancelOnbEdit').onclick = () => modal.remove();
        document.getElementById('saveOnbEdit').onclick = async () => {
        const formData = new FormData();
        formData.append('client_name', document.getElementById('editOnbClient').value);
        formData.append('doj', document.getElementById('editOnbDOJ').value);
        formData.append('resource_owner', document.getElementById('editOnbOwner').value);
        formData.append('work_location', document.getElementById('editOnbLocation').value);
        formData.append('monthly_salary', document.getElementById('editOnbSalary').value);
        formData.append('billing_rate', document.getElementById('editOnbBilling').value);
        formData.append('business_model', document.getElementById('editOnbModel').value);
        formData.append('requirement_id', document.getElementById('editOnbReq').value);
        formData.append('po_number', document.getElementById('editOnbPO').value);
        formData.append('status', document.getElementById('editOnbStatus').value);
        
        const docFiles = document.getElementById('editOnbDocs').files;
        for (let i = 0; i < docFiles.length; i++) {
            formData.append('documents', docFiles[i]);
        }
        
        const updateRes = await fetch('/api/onboarded/' + id, {
            method: 'PUT',
            body: formData
        });
        if (updateRes.ok) {
            toastSuccess('Updated!');
            modal.remove();
            loadOnboarded();
        } else {
            toastError('Failed to update');
        }
    };
}
async function loadFinance() {
    const res = await fetch('/api/finance-dashboard');
    const data = await res.json();
    
    document.getElementById('finTotalRevenue').textContent = '₹' + (data.total_revenue || 0).toLocaleString();
    document.getElementById('finTotalSalary').textContent = '₹' + (data.total_salary || 0).toLocaleString();
    document.getElementById('finTotalProfit').textContent = '₹' + (data.total_profit || 0).toLocaleString();
    document.getElementById('finAvgMargin').textContent = (data.avg_margin || 0) + '%';
    document.getElementById('finActiveResources').textContent = data.active_resources || 0;
    
    let html = '<h4>📊 Client-wise Breakdown</h4>';
    const clients = data.clients || {};
    
    for (const [client, info] of Object.entries(clients)) {
        const profit = info.revenue - info.salary;
        const margin = info.revenue > 0 ? Math.round((profit / info.revenue) * 100) : 0;
        html += `<div class="card" style="margin:8px 0;">
            <h4>🏢 ${escapeHtml(client)} <span style="font-size:12px;color:#666;">(${info.count} resources)</span></h4>
            <div style="display:flex;gap:20px;flex-wrap:wrap;font-size:13px;">
                <span>💰 Revenue: <strong>₹${info.revenue.toLocaleString()}</strong></span>
                <span>💸 Salary: <strong>₹${info.salary.toLocaleString()}</strong></span>
                <span style="color:${margin>=30?'#10B981':margin>=15?'#F59E0B':'#EF4444'};font-weight:bold;">📊 Margin: ${margin}% (₹${profit.toLocaleString()})</span>
            </div>
            <div style="margin-top:8px;font-size:12px;">`;
        info.resources.forEach(r => {
            html += `<div style="padding:2px 0;">👤 ${escapeHtml(r.name)} - Salary: ₹${r.salary.toLocaleString()} | Billing: ₹${r.billing.toLocaleString()} | Margin: ${r.margin}%</div>`;
        });
        html += `</div></div>`;
    }
    
    document.getElementById('financeBreakdown').innerHTML = html || '<p style="color:#999;">No active resources</p>';
}
async function loadOnboarded() {
    const res = await fetch('/api/onboarded');
    const resources = await res.json();
    const container = document.getElementById('onboardedList');
    if (!resources.length) {
        container.innerHTML = '<div class="card no-click" style="text-align:center;padding:40px;">No onboarded resources</div>';
        return;
    }
    container.innerHTML = resources.map(r => {
        const revenue = (r.billing_rate || 0) - (r.monthly_salary || 0);
        const margin = r.billing_rate ? Math.round((revenue / r.billing_rate) * 100) : 0;
        return `<div class="card" style="margin-bottom:8px;">
            <div style="display:flex;justify-content:space-between;align-items:start;flex-wrap:wrap;gap:10px;">
                <div style="flex:1;"><h4 style="margin:0;"><strong style="color:#1B2A4A;">${escapeHtml(r.first_name||'')} ${escapeHtml(r.last_name||'')}</strong></h4>
                <div style="font-size:13px;color:#555;">🏢 ${escapeHtml(r.client_name||'N/A')} | 📅 DOJ: ${r.doj||'N/A'}</div>
                <div style="font-size:12px;color:#777;">👤 ${escapeHtml(r.resource_owner||'N/A')} | 📍 ${escapeHtml(r.work_location||'N/A')}</div></div>
                <div style="text-align:right;"><div>💰 Salary: ₹${(r.monthly_salary||0).toLocaleString()}</div>
                <div>📊 Billing: ₹${(r.billing_rate||0).toLocaleString()}</div>
                <div style="font-weight:bold;color:${margin>=30?'#10B981':margin>=15?'#F59E0B':'#EF4444'};">Margin: ${margin}% (₹${revenue.toLocaleString()}/mo)</div> <button class="btn btn-sm" onclick="event.stopPropagation(); editOnboarded(${r.id})" style="margin-top:4px;">✏️ Edit</button></div>
            </div></div>`;
    }).join('');
}

async function loadDailyReport() {
    const date = document.getElementById('reportDate').value || new Date().toISOString().split('T')[0];
    const container = document.getElementById('dailyReportContent');
    container.innerHTML = '<div class="spinner"></div>';
    
    const res = await fetch('/api/daily-report?date=' + date);
    const data = await res.json();
    
    let html = `<h4>📅 Report for ${data.date}</h4>`;
    
    // Active Requirements
    html += `<div class="card" style="margin:10px 0;"><h4>📋 Active Requirements: ${data.active_requirements}</h4>`;
    if (data.active_jobs.length === 0) {
        html += '<p style="color:#999;">No active requirements</p>';
    } else {
        data.active_jobs.forEach(j => {
            html += `<div style="font-size:13px;padding:4px 0;">
                🔹 <a href="javascript:void(0)" onclick="showPanel('jobs'); setTimeout(() => loadJobs(), 300);" style="color:#1B2A4A;text-decoration:underline;">
                    ${escapeHtml(j.title)} - ${escapeHtml(j.requirement_id || 'SIT-R-'+String(j.id).padStart(3,'0'))}
                </a> (${escapeHtml(j.company||'N/A')})
            </div>`;
        });
    }
    html += `</div>`;
    
    // Proposals Sent
    html += `<div class="card" style="margin:10px 0;"><h4>📤 Profiles Proposed: ${data.candidates_added}</h4>`;
    if (data.candidates.length === 0) {
        html += '<p style="color:#999;">No profiles proposed on this date</p>';
    } else {
        data.candidates.forEach(c => {
            html += `<div style="font-size:13px;padding:4px 0;border-bottom:1px solid #eee;">
                👤 <a href="javascript:void(0)" onclick="viewCandidate(${c.id})" style="color:#1B2A4A;text-decoration:underline;font-weight:bold;">
                    ${escapeHtml(c.first_name||'')} ${escapeHtml(c.last_name||'')}
                </a>
                | 🏢 ${escapeHtml(c.proposed_client||'N/A')} 
                | 📋 ${escapeHtml(c.proposed_requirement||'N/A')}
                | 👤 HR: ${escapeHtml(c.uploaded_by_name||'N/A')}
            </div>`;
        });
    }
    html += `</div>`;
    
    // Interviews Scheduled
    html += `<div class="card" style="margin:10px 0;"><h4>📅 Interviews Scheduled: ${data.interviews_scheduled}</h4>`;
    if (data.interviews.length === 0) {
        html += '<p style="color:#999;">No interviews scheduled on this date</p>';
    } else {
        data.interviews.forEach(i => {
            html += `<div style="font-size:13px;padding:4px 0;border-bottom:1px solid #eee;">
                🕐 ${i.interview_time||'TBD'} - 
                <a href="javascript:void(0)" onclick="showPanel('interviews'); document.getElementById('intFilterDate').value='${i.interview_date}'; loadInterviews();" style="color:#1B2A4A;text-decoration:underline;font-weight:bold;">
                    ${escapeHtml(i.candidate_name)}
                </a> 
                (${escapeHtml(i.round)}) - 🏢 ${escapeHtml(i.client_name||'N/A')}
            </div>`;
        });
    }
    html += `</div>`;
    
    // Interviews Completed
    html += `<div class="card" style="margin:10px 0;"><h4>✅ Interviews Completed: ${data.interviews_completed}</h4>`;
    if (data.completed_interviews.length === 0) {
        html += '<p style="color:#999;">No interviews completed on this date</p>';
    } else {
        data.completed_interviews.forEach(i => {
            html += `<div style="font-size:13px;padding:4px 0;border-bottom:1px solid #eee;">
                ${i.verdict} - 
                <a href="javascript:void(0)" onclick="showPanel('interviews'); document.getElementById('intFilterDate').value='${i.interview_date}'; loadInterviews();" style="color:#1B2A4A;text-decoration:underline;font-weight:bold;">
                    ${escapeHtml(i.candidate_name)}
                </a> 
                (${escapeHtml(i.round)}) - 🏢 ${escapeHtml(i.client_name||'N/A')}
            </div>`;
        });
    }
    html += `</div>`;
    
    container.innerHTML = html;
}
async function loadKanban() {
    const res = await fetch('/api/candidates');
    const candidates = await res.json();
    const board = document.getElementById('kanbanBoard');
    
    board.innerHTML = kanbanStages.map(stage => {
        const stageCandidates = candidates.filter(c => (c.stage || 'new') === stage.id);
        return `
            <div style="background:#F5F7FA;border-radius:10px;min-height:150px;min-width:200px;max-width:240px;display:flex;flex-direction:column;flex-shrink:0;">
                <div style="background:${stage.color};color:#fff;padding:10px 14px;border-radius:10px 10px 0 0;font-weight:bold;font-size:13px;display:flex;justify-content:space-between;">
                    <span>${stage.emoji} ${stage.name}</span>
                    <span style="background:rgba(255,255,255,0.3);padding:2px 8px;border-radius:10px;font-size:11px;">${stageCandidates.length}</span>
                </div>
                <div style="padding:8px;flex:1;min-height:100px;" 
                     ondragover="event.preventDefault()" 
                     ondrop="dropCandidate(event, '${stage.id}')">
                    ${stageCandidates.map(c => `
                                                <div draggable="true" 
                             ondragstart="dragCandidate(event, ${c.id})" 
                             onclick="viewCandidate(${c.id})"
                             style="background:#fff;padding:8px;margin-bottom:5px;border-radius:6px;border-left:3px solid ${stage.color};cursor:pointer;font-size:11px;box-shadow:0 1px 2px rgba(0,0,0,0.08);">
                            <strong style="font-size:11px;">${escapeHtml(c.first_name || '')} ${escapeHtml(c.last_name || '')}</strong>
                            <div style="color:#666;font-size:10px;">${escapeHtml(c.designation || c.current_role || '')}</div>
                            ${c.match_score ? `<span style="background:${c.match_score>=70?'#10B981':c.match_score>=40?'#F59E0B':'#EF4444'};color:#fff;padding:1px 6px;border-radius:8px;font-size:10px;">${c.match_score}%</span>` : ''}
                        </div>
                    `).join('')}
                    ${stageCandidates.length === 0 ? '<div style="color:#bbb;font-size:11px;text-align:center;padding:20px;">Drop here</div>' : ''}
                </div>
            </div>
        `;
    }).join('');
}

let draggedCandidateId = null;

function dragCandidate(event, candidateId) {
    draggedCandidateId = candidateId;
    event.dataTransfer.effectAllowed = 'move';
}

async function dropCandidate(event, stage) {
    event.preventDefault();
    if (!draggedCandidateId) return;
    
    await fetch('/api/candidates/' + draggedCandidateId, {
        method: 'PUT',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({ stage: stage })
    });
    
    draggedCandidateId = null;
    loadKanban();
    toastSuccess('Stage updated!');
}
    
    function renderMatchChart(distribution) {
        const canvas = document.getElementById('matchChart');
        if (!canvas) return;
        const ctx = canvas.getContext('2d');
        const labels = ['0-20%', '21-40%', '41-60%', '61-80%', '81-100%'];
        const values = [
            distribution['0-20'] || 0,
            distribution['21-40'] || 0,
            distribution['41-60'] || 0,
            distribution['61-80'] || 0,
            distribution['81-100'] || 0
        ];
        const colors = ['#F44336', '#FF9800', '#FFC107', '#4CAF50', '#1B6B2E'];
        
        if (matchChartInstance) matchChartInstance.destroy();
        matchChartInstance = new Chart(ctx, {
            type: 'bar',
            data: { labels: labels, datasets: [{ label: 'Candidates', data: values, backgroundColor: colors, borderColor: colors, borderWidth: 1 }] },
            options: { responsive: true, maintainAspectRatio: true, plugins: { legend: { display: false } }, scales: { y: { beginAtZero: true, ticks: { stepSize: 1 } } } }
        });
    }
    
    function renderPipelineChart(pipeline) {
        const canvas = document.getElementById('pipelineChart');
        if (!canvas) return;
        const ctx = canvas.getContext('2d');
        const labels = ['New', 'Screening', 'Interview', 'Offer', 'Hired', 'Rejected'];
        const values = [pipeline.new||0, pipeline.screening||0, pipeline.interview||0, pipeline.offer||0, pipeline.hired||0, pipeline.rejected||0];
        const colors = ['#2196F3', '#FF9800', '#FF5722', '#9C27B0', '#4CAF50', '#F44336'];
        if (values.every(v => v === 0)) return;
        if (pipelineChartInstance) pipelineChartInstance.destroy();
        pipelineChartInstance = new Chart(ctx, {
            type: 'doughnut',
            data: { labels: labels, datasets: [{ data: values, backgroundColor: colors, borderColor: '#fff', borderWidth: 2 }] },
            options: { responsive: true, maintainAspectRatio: true, plugins: { legend: { position: 'right', labels: { boxWidth: 12, font: { size: 10 } } } } }
        });
    }
    
   function renderSkillsCloud(skills) {
    const container = document.getElementById('skillsCloud');
    if (!container) return;
    if (!skills || skills.length === 0) { 
        container.innerHTML = '<p style="color: #999; font-style: italic;">No skills data available</p>'; 
        return; 
    }
    
    const normalizedSkills = skills.map(s => 
        typeof s === 'object' ? {skill: s.skill || s.name || '', count: s.count || 1} : {skill: String(s), count: 1}
    );
    const topSkills = normalizedSkills.slice(0, 15);
    const maxCount = topSkills[0]?.count || 1;
    
    container.innerHTML = topSkills.map(s => {
        const size = 12 + (s.count / maxCount) * 20;
        return '<span style="font-size:' + size + 'px; color:#1A4D4A; background:#F5F0E8; padding:4px 12px; border-radius:20px; border:1px solid #ddd; opacity:' + (0.6 + (s.count / maxCount) * 0.4) + ';">' + escapeHtml(s.skill) + '</span>';
    }).join('');
}
    
    function renderTrendChart(trend) {
        const canvas = document.getElementById('trendChart');
        if (!canvas) return;
        const ctx = canvas.getContext('2d');
        const labels = trend.labels || [];
        const values = trend.values || [];
        if (trendChartInstance) trendChartInstance.destroy();
        if (labels.length === 0) return;
        trendChartInstance = new Chart(ctx, {
            type: 'line',
            data: { labels: labels, datasets: [{ label: 'Candidates Added', data: values, borderColor: '#1A4D4A', backgroundColor: 'rgba(26,77,74,0.1)', fill: true, tension: 0.3, pointBackgroundColor: '#1A4D4A' }] },
            options: { responsive: true, maintainAspectRatio: true, plugins: { legend: { display: false } }, scales: { y: { beginAtZero: true, ticks: { stepSize: 1 } } } }
        });
    }
    // ========== AI DEEP DIVE FROM BATCH RESULTS ==========
    window.runDeepAnalysis = async function(candidateId, jobTitle) {
        // Find the job by title
        const job = allJobs.find(j => j.title === jobTitle);
        if (!job) { 
            toastError('Job not found. Please select from Analyze tab.');
            return; 
        }
        
        const cand = allCandidates.find(c => c.id == candidateId);
        if (!cand) { 
            toastError('Candidate not found.');
            return; 
        }
        
        // Switch to analyze tab
        showPanel('analyze');
        
        // Wait for panel to show
        setTimeout(() => {
            // Set the job and candidate in the dropdowns
            document.getElementById('jobSelect').value = job.id;
            document.getElementById('candidateSelect').value = candidateId;
            
            // Trigger the analysis
            document.getElementById('analyzeBtn').click();
            
            // Scroll to analysis result after a delay
            setTimeout(() => {
                const resultDiv = document.getElementById('analysisResult');
                if (resultDiv) {
                    resultDiv.scrollIntoView({ behavior: 'smooth', block: 'start' });
                }
            }, 500);
        }, 300);
    };
    
    function updateStats() {
        const total = allCandidates.length;
        const matched = allCandidates.filter(c => (c.match_score || 0) >= 70).length;
        const hired = allCandidates.filter(c => c.employment_status === 'hired').length;
        const rejected = allCandidates.filter(c => c.employment_status === 'rejected').length;
        const screening = allCandidates.filter(c => c.employment_status === 'screening').length;
        const interview = allCandidates.filter(c => c.employment_status === 'interview').length;
        const offer = allCandidates.filter(c => c.employment_status === 'offer').length;
        const newCount = allCandidates.filter(c => c.employment_status === 'new' || !c.employment_status).length;
        
        document.getElementById('candidateStats').textContent = `📊 ${total} total  |  🎯 ${matched} matched  |  ✅ ${hired} hired  |  ❌ ${rejected} rejected`;
        
        // Update pipeline stats
        document.getElementById('stat-new-count').textContent = newCount;
        document.getElementById('stat-screening-count').textContent = screening;
        document.getElementById('stat-interview-count').textContent = interview;
        document.getElementById('stat-offer-count').textContent = offer;
        document.getElementById('stat-hired-count').textContent = hired;
        document.getElementById('stat-rejected-count').textContent = rejected;
        
        // Uploader stats
        renderUploaderStats();
    }

    function renderUploaderStats() {
        const uploaderMap = {};
        allCandidates.forEach(c => {
            const uploader = c.uploaded_by || 'ShahnaIT';
            uploaderMap[uploader] = (uploaderMap[uploader] || 0) + 1;
        });
        
        const sorted = Object.entries(uploaderMap).sort((a, b) => b[1] - a[1]);
        const maxCount = sorted.length > 0 ? sorted[0][1] : 1;
        const total = allCandidates.length;
        
        const container = document.getElementById('uploaderChart');
        if (sorted.length === 0) {
            container.innerHTML = '<p style="color: #999; font-style: italic;">No candidates uploaded yet</p>';
            return;
        }
        
        container.innerHTML = sorted.map(([name, count]) => {
            const percentage = total > 0 ? Math.round((count / total) * 100) : 0;
            const barWidth = Math.max(5, Math.round((count / maxCount) * 100));
            return `
                <div style="display: flex; align-items: center; gap: 10px;">
                    <span style="min-width: 120px; font-size: 13px; font-weight: 500;">👤 ${escapeHtml(name)}</span>
                    <div style="flex: 1; background: #F0F0F0; border-radius: 10px; height: 22px; overflow: hidden;">
                        <div style="background: linear-gradient(90deg, #1A4D4A, #2A6B67); height: 100%; width: ${barWidth}%; border-radius: 10px; transition: width 0.5s; display: flex; align-items: center; justify-content: flex-end; padding-right: 8px; color: white; font-size: 11px; font-weight: bold;">${count}</div>
                    </div>
                    <span style="min-width: 60px; font-size: 13px; color: #666; text-align: right;">${percentage}%</span>
                </div>
            `;
        }).join('');
    }
    function escapeHtml(str) { 
    if (!str) return ''; 
    // Convert to string if it's not already
    str = String(str);
    return str.replace(/[&<>]/g, function(m) { 
        if(m==='&') return '&amp;'; 
        if(m==='<') return '&lt;'; 
        if(m==='>') return '&gt;'; 
        return m; 
    }); 
}
      
</script>
</body>
</html>
'''

# ============ API ROUTES ============
@app.route('/')
def index():
    return HTML_TEMPLATE

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
        working_mode, hybrid_days, business_model,
        payroll_company, client_name, end_client,
        years_of_experience, budget, headcount
    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)''',
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
        data.get('business_model', 'Not Specified'),
        data.get('payroll_company', ''),
        data.get('client_name', data.get('company', '')),
        data.get('end_client', ''),
        data.get('years_of_experience', 0),
        data.get('budget', ''),
        data.get('headcount', 1)
    ))
    conn.commit()
    conn.close()
    return jsonify({'message': 'Job created'})

@app.route('/api/candidates/<int:candidate_id>', methods=['PUT']) 
@login_required()
def update_candidate(candidate_id):
    try:
        data = request.json
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        
        # Check ownership - admin can edit all, others only own
        if session.get('role') != 'admin':
            c.execute('SELECT uploaded_by_name FROM candidates WHERE id = ?', (candidate_id,))
            row = c.fetchone()
            if not row or (row[0] or '') != (session.get('user_name') or ''):
                conn.close()
                return jsonify({"success": False, "error": "You can only edit your own candidates"}), 403
        
        # Build dynamic update query
        allowed_fields = [
            'first_name', 'last_name', 'middle_name', 'phone', 'email', 'address', 'linkedin',
            'current_role', 'current_ctc', 'expected_ctc', 'designation', 'location', 'years_of_experience',
            'employment_status', 'notice_period_days', 'education', 'notes',
            'proposed_client', 'proposed_requirement', 'stage', 'analysis_summary', 'matched_jd', 'uploaded_by_name'
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
        working_mode = ?, hybrid_days = ?, business_model = ?,
        payroll_company = ?, client_name = ?, end_client = ?,
        years_of_experience = ?, budget = ?, headcount = ?
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
        data.get('business_model', 'Not Specified'),
        data.get('payroll_company', ''),
        data.get('client_name', data.get('company', '')),
        data.get('end_client', ''),
        data.get('years_of_experience', 0),
        data.get('budget', ''),
        data.get('headcount', 1),
        job_id
    ))
    conn.commit()
    conn.close()
    return jsonify({'message': 'Job updated'})

@app.route('/api/jobs/<int:job_id>/toggle-active', methods=['PUT'])
@login_required('admin')
def toggle_job_active(job_id):
    data = request.json
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('UPDATE jobs SET is_active = ? WHERE id = ?', 
              (data.get('is_active', 0), job_id))
    conn.commit()
    conn.close()
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
    data = request.json
    candidate_id = save_candidate_to_db(data)
    
    # Handle resume file - using permanent_file_path from parse-resume
    file_path = data.get('permanent_file_path')
    original_filename = data.get('original_filename')
    permanent_filename = data.get('permanent_filename')
    
    if file_path and os.path.exists(file_path):
        # File is already saved in permanent location by parse-resume
        # Just record it in the database
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        c.execute('''UPDATE candidates SET 
            resume_file_path = ?,
            resume_original_filename = ?
            WHERE id = ?''',
            (file_path, original_filename, candidate_id))
        conn.commit()
        conn.close()
        
        # Also add to candidate_documents for document management
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        c.execute('INSERT INTO candidate_documents (candidate_id, filename, original_filename, file_path, file_type, is_resume) VALUES (?, ?, ?, ?, ?, ?)',
                  (candidate_id, permanent_filename, original_filename, file_path, original_filename.split('.')[-1], 1))
        conn.commit()
        conn.close()
    
    return jsonify({'message': 'Candidate saved', 'id': candidate_id})

# ============================================
# DELETE CANDIDATE ENDPOINT
# ============================================
@app.route('/api/candidates/<int:candidate_id>', methods=['DELETE'])
def delete_candidate(candidate_id):
    """Delete a candidate and their documents"""
    try:
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        
        # Get file paths to delete
        c.execute('SELECT file_path FROM candidate_documents WHERE candidate_id = ?', (candidate_id,))
        files = c.fetchall()
        for file in files:
            if os.path.exists(file[0]):
                os.remove(file[0])
        
        # Delete candidate (cascade will delete notes and documents)
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
def parse_resume():
    if 'resume' not in request.files:
        return jsonify({'error': 'No file'}), 400
    file = request.files['resume']
    if file.filename == '':
        return jsonify({'error': 'No file'}), 400
    
    filename = secure_filename(file.filename)
    original_filename = file.filename
    temp_filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
    file.save(temp_filepath)
    
    # Extract text for parsing
    if filename.endswith('.pdf'):
        text = extract_text_from_pdf(temp_filepath)
    else:
        text = extract_text_from_docx(temp_filepath)
    
    if not text:
        os.remove(temp_filepath)
        return jsonify({'error': 'Could not extract text'}), 400
    
    # Try Groq first, then fallback
    parsed = parse_resume_with_groq(text)
    if parsed and parsed.get('first_name'):
        parsed['resume_text'] = text[:5000]  # Store for search (increased from 3000)
        parsed['ai_used'] = True
    else:
        parsed = fallback_parse_resume(text)
        parsed['resume_text'] = text[:5000]  # Store for search (increased from 3000)
        parsed['ai_used'] = False
    
    # Store the original file path for later download
    parsed['file_path'] = temp_filepath
    parsed['original_filename'] = original_filename
    
       # Save to permanent location
    permanent_filename = secure_filename(f"{datetime.now().timestamp()}_{original_filename}")
    permanent_path = os.path.join(app.config['DOCUMENTS_FOLDER'], permanent_filename)
    os.makedirs(os.path.dirname(permanent_path), exist_ok=True)
    shutil.move(temp_filepath, permanent_path)
    parsed['permanent_file_path'] = permanent_path
    parsed['permanent_filename'] = permanent_filename
    
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
    
    c.execute("SELECT id, first_name, last_name, email, uploaded_by_name, proposed_client, proposed_requirement, created_at FROM candidates WHERE date(created_at) = ? ORDER BY created_at DESC", (date,))
    candidates_added = [dict(row) for row in c.fetchall()]
    
    c.execute("SELECT * FROM interviews WHERE interview_date = ? AND verdict != 'Scheduled'", (date,))
    completed_interviews = [dict(row) for row in c.fetchall()]
    
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
        'candidates': candidates_added
    })


@app.route('/fix-jobs-active')
def fix_jobs_active():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    try:
        c.execute("ALTER TABLE jobs ADD COLUMN is_active BOOLEAN DEFAULT 1")
    except:
        pass
    conn.commit()
    conn.close()
    return 'Jobs table fixed!'

@app.route('/fix-onboarded-table')
def fix_onboarded_table():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
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
    conn.commit()
    conn.close()
    return 'Onboarded table created!'

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
    
    if not row or not row[0] or not os.path.exists(row[0]):
        return jsonify({'error': 'Resume not found'}), 404
    
    file_path = row[0]
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
    
    if not row or not row[0] or not os.path.exists(row[0]):
        return jsonify({'error': 'Resume not found'}), 404
    
    file_path = row[0]
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

@app.route('/api/debug-db')
def debug_db():
    try:
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        c.execute("SELECT COUNT(*) FROM candidates")
        candidate_count = c.fetchone()[0]
        c.execute("SELECT COUNT(*) FROM jobs")
        job_count = c.fetchone()[0]
        c.execute("PRAGMA table_info(candidates)")
        columns = [col[1] for col in c.fetchall()]
        conn.close()
        return jsonify({
            'db_path': DB_PATH,
            'candidate_count': candidate_count,
            'job_count': job_count,
            'columns': columns
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
