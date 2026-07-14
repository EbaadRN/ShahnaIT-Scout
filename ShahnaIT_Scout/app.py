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
CORS(app)

# Configuration
app.config['MAX_CONTENT_LENGTH'] = 50 * 1024 * 1024
app.config['UPLOAD_FOLDER'] = '/tmp'
app.config['DOCUMENTS_FOLDER'] = '/tmp/candidate_docs'
app.config['JOB_DOCUMENTS_FOLDER'] = '/tmp/job_docs'

os.makedirs(app.config['DOCUMENTS_FOLDER'], exist_ok=True)
os.makedirs(app.config['JOB_DOCUMENTS_FOLDER'], exist_ok=True)

# ============ DATABASE SETUP ============
DB_PATH = 'shahnai.db'

def init_db():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    
    c.execute('DROP TABLE IF EXISTS candidates')
    c.execute('''CREATE TABLE candidates (
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
        uploaded_by TEXT DEFAULT 'ShahnaIT'
    )''')
    
    c.execute('DROP TABLE IF EXISTS candidate_documents')
    c.execute('''CREATE TABLE candidate_documents (
        id INTEGER PRIMARY KEY AUTOINCREMENT, candidate_id INTEGER,
        filename TEXT, original_filename TEXT, file_path TEXT, file_type TEXT,
        is_resume BOOLEAN DEFAULT 0, uploaded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (candidate_id) REFERENCES candidates(id)
    )''')
    
    c.execute('DROP TABLE IF EXISTS jobs')
    c.execute('''CREATE TABLE jobs (
        id INTEGER PRIMARY KEY AUTOINCREMENT, title TEXT NOT NULL,
        company TEXT, description TEXT, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
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
   # Add resume file storage columns if they don't exist
    c.execute("PRAGMA table_info(candidates)")
    columns = [col[1] for col in c.fetchall()]
    
    if 'resume_file_path' not in columns:
        c.execute('ALTER TABLE candidates ADD COLUMN resume_file_path TEXT')
        print("✅ Added resume_file_path column")
    
    if 'resume_original_filename' not in columns:
        c.execute('ALTER TABLE candidates ADD COLUMN resume_original_filename TEXT')
        print("✅ Added resume_original_filename column")
    
    conn.commit()
    conn.close()
    print("✅ Database initialized")

init_db()

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
    prompt = f"""Parse this resume. Extract years of experience for each skill. Return ONLY valid JSON.

RESUME: {resume_text[:3500]}

Return: {{
    "first_name": "",
    "last_name": "",
    "middle_name": "",
    "phone": "",
    "email": "",
    "address": "",
    "linkedin": "",
    "current_role": "",
    "current_ctc": "",
    "expected_ctc": "",
    "employment_status": "working",
    "notice_period_days": 0,
    "work_experience": [],
    "certifications": [],
    "core_skills": [],
    "education": ""
}}"""
    response = call_groq_api(prompt, max_tokens=2500)
    if response:
        try:
            return json.loads(response)
        except:
            return None
    return None

def analyze_match_with_groq(resume_text, jd_text):
    if not GROQ_ENABLED:
        return None
    prompt = f"""You are an expert recruitment analyst. Analyze this resume against the job description with extreme precision. Return ONLY valid JSON.

JOB DESCRIPTION:
{jd_text[:3000]}

RESUME:
{resume_text[:3500]}

Provide a detailed analysis with the following structure. Be extremely critical and precise.

Return EXACTLY this JSON format:
{{
    "match_score": 0-100 integer,
    "recommendation": "hire" or "interview" or "reject",
    "category_scores": {{
        "skills_match": 0-100,
        "experience_match": 0-100,
        "education_match": 0-100,
        "certifications_match": 0-100
    }},
    "matching_skills": ["skill1", "skill2"],
    "missing_skills": ["skill1", "skill2"],
    "strengths": ["strength1", "strength2"],
    "weaknesses": ["weakness1", "weakness2"],
    "executive_summary": "2-3 sentence summary",
    "pre_screening_questions": ["Q1", "Q2", "Q3"]
}}

Scoring Guidelines:
- 90-100: Perfect fit, hire immediately
- 70-89: Strong match, schedule interview
- 50-69: Partial match, consider for interview
- 30-49: Weak match, reject
- 0-29: No match, reject

Be harsh and realistic. Do not inflate scores."""
    response = call_groq_api(prompt, max_tokens=2000)
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
    
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('''INSERT INTO candidates 
        (first_name, last_name, middle_name, phone, email, address, linkedin,
         current_role, current_ctc, expected_ctc,
         employment_status, notice_period_days, work_experience, certifications,
         core_skills, education, notes, resume_text, resume_filename, uploaded_by,
         resume_file_path, resume_original_filename)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)''',
        (candidate_data.get('first_name'), candidate_data.get('last_name'), candidate_data.get('middle_name'),
         candidate_data.get('phone'), candidate_data.get('email'), candidate_data.get('address'), candidate_data.get('linkedin'),
         candidate_data.get('current_role'), candidate_data.get('current_ctc'), candidate_data.get('expected_ctc'),
         candidate_data.get('employment_status'), candidate_data.get('notice_period_days', 0),
         work_exp, certs, skills, candidate_data.get('education'), candidate_data.get('notes'), 
         candidate_data.get('resume_text'), candidate_data.get('resume_filename'),
         candidate_data.get('uploaded_by', 'ShahnaIT'),
         candidate_data.get('permanent_file_path'), candidate_data.get('original_filename')))
    
    candidate_id = c.lastrowid
    conn.commit()
    conn.close()
    return candidate_id
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
        body { font-family: Arial; background: #F5F0E8; margin: 0; padding: 20px; }
        .header { background: #1A4D4A; color: white; padding: 20px; border-radius: 10px; margin-bottom: 20px; }
        button, .btn { background: #1A4D4A; color: white; border: none; padding: 10px 20px; margin: 5px; cursor: pointer; border-radius: 8px; }
        button:hover, .btn:hover { background: #2A6B67; }
        .tab-btn { background: white; color: #1A4D4A; border: 1px solid #1A4D4A; padding: 10px 20px; margin: 5px; cursor: pointer; border-radius: 8px; }
        .tab-btn.active { background: #1A4D4A; color: white; }
        .card { background: white; padding: 15px; margin: 10px 0; border-radius: 8px; border-left: 4px solid #1A4D4A; cursor: pointer; transition: transform 0.2s; }
        .card:hover { transform: translateY(-2px); box-shadow: 0 2px 8px rgba(0,0,0,0.1); }
        .card.no-click { cursor: default; }
        input, select, textarea { width: 100%; padding: 8px; margin: 5px 0; border: 1px solid #ccc; border-radius: 5px; }
       .skill-tag { background: #F5F0E8; padding: 3px 8px; border-radius: 15px; display: inline-block; margin: 2px; color: #1A4D4A; font-weight: 500; }
       .skill-with-years { background: #E8F5E9; padding: 3px 8px; border-radius: 15px; display: inline-block; margin: 2px; color: #1B5E20; font-weight: 500; }
        .match-high { background: #1A237E; color: #FFFFFF; padding: 4px 14px; border-radius: 20px; display: inline-block; font-weight: bold; font-size: 16px; }
        .match-medium { background: #283593; color: #FFFFFF; padding: 4px 14px; border-radius: 20px; display: inline-block; font-weight: bold; font-size: 16px; }
        .match-low { background: #B71C1C; color: #FFFFFF; padding: 4px 14px; border-radius: 20px; display: inline-block; font-weight: bold; font-size: 16px; }
        .alert-success { background: #1B6B2E; color: white; padding: 10px; border-radius: 8px; margin: 10px 0; }
        .alert-error { background: #B22222; color: white; padding: 10px; border-radius: 8px; margin: 10px 0; }
        /* ============================================
   CANDIDATE CARDS - NEW STYLES
   ============================================ */
.candidate-card {
    background: white;
    border-radius: 12px;
    box-shadow: 0 2px 10px rgba(0,0,0,0.05);
    margin-bottom: 16px;
    overflow: hidden;
    transition: all 0.3s ease;
    border: 1px solid #e0e0e0;
    cursor: default;
}

.candidate-card:hover {
    box-shadow: 0 5px 25px rgba(0,0,0,0.1);
    transform: translateY(-2px);
}

.card-header {
    padding: 16px 20px;
    display: flex;
    align-items: center;
    gap: 15px;
    cursor: pointer;
    background: #fafafa;
    border-bottom: 1px solid #f0f0f0;
}

.candidate-avatar {
    position: relative;
    width: 50px;
    height: 50px;
    border-radius: 50%;
    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
    display: flex;
    align-items: center;
    justify-content: center;
    color: white;
    font-weight: bold;
    font-size: 20px;
    flex-shrink: 0;
}

.avatar-text {
    text-transform: uppercase;
}

.score-badge {
    position: absolute;
    bottom: -5px;
    right: -5px;
    font-size: 10px;
    font-weight: 700;
    color: white;
    padding: 2px 8px;
    border-radius: 20px;
    min-width: 30px;
    text-align: center;
}

.candidate-title {
    flex: 1;
}

.candidate-name {
    margin: 0;
    font-size: 16px;
    font-weight: 600;
    color: #1A4D4A;
}

.candidate-email {
    font-size: 13px;
    color: #666;
    display: block;
    margin-top: 2px;
}

.btn-expand {
    background: none;
    border: none;
    color: #999;
    cursor: pointer;
    padding: 8px;
    font-size: 16px;
    transition: transform 0.3s ease;
    border-radius: 50%;
}

.btn-expand:hover {
    background: #f0f0f0;
    color: #1A4D4A;
}

.btn-expand.expanded {
    transform: rotate(180deg);
}

.card-body {
    padding: 0 20px 16px 20px;
}

.candidate-skills {
    display: flex;
    flex-wrap: wrap;
    gap: 6px;
    margin: 12px 0 10px 0;
}

.skill-tag {
    background: #F5F0E8;
    color: #1A4D4A;
    padding: 4px 12px;
    border-radius: 20px;
    font-size: 12px;
    font-weight: 500;
    display: inline-block;
}

.skill-tag.more {
    background: #e0e0e0;
    color: #666;
    font-weight: 600;
}

.no-skills {
    color: #999;
    font-size: 13px;
    font-style: italic;
}

.candidate-meta {
    display: flex;
    flex-wrap: wrap;
    gap: 12px;
    align-items: center;
    margin-bottom: 12px;
}

.meta-item {
    font-size: 13px;
    color: #666;
    display: flex;
    align-items: center;
    gap: 5px;
}

.meta-item i {
    font-size: 13px;
    opacity: 0.7;
}

.status-badge {
    padding: 4px 12px;
    border-radius: 20px;
    font-size: 12px;
    font-weight: 600;
    border: 1px solid transparent;
}

.card-actions {
    display: flex;
    gap: 8px;
    flex-wrap: wrap;
    margin-top: 4px;
}

.btn-primary, .btn-secondary, .btn-danger {
    padding: 6px 14px;
    border: none;
    border-radius: 6px;
    cursor: pointer;
    font-size: 12px;
    display: flex;
    align-items: center;
    gap: 5px;
    transition: all 0.3s ease;
    font-weight: 500;
}

.btn-primary {
    background: #1A4D4A;
    color: white;
}

.btn-primary:hover {
    background: #2A6B67;
    transform: translateY(-2px);
    box-shadow: 0 4px 12px rgba(26, 77, 74, 0.3);
}

.btn-secondary {
    background: #e0e0e0;
    color: #333;
}

.btn-secondary:hover {
    background: #d0d0d0;
    transform: translateY(-2px);
}

.btn-danger {
    background: #ff5252;
    color: white;
}

.btn-danger:hover {
    background: #ff1744;
    transform: translateY(-2px);
    box-shadow: 0 4px 12px rgba(255, 23, 68, 0.3);
}

.card-details {
    padding: 16px 20px 20px 20px;
    background: #f9f9f9;
    border-top: 1px solid #e0e0e0;
}

.details-section {
    margin-bottom: 15px;
}

.details-section h4 {
    margin: 0 0 8px 0;
    color: #1A4D4A;
    font-size: 14px;
    font-weight: 600;
}

.details-section p {
    margin: 0;
    font-size: 13px;
    color: #555;
    line-height: 1.5;
}

.notes-container {
    max-height: 150px;
    overflow-y: auto;
    margin-bottom: 8px;
}

.notes-container::-webkit-scrollbar {
    width: 4px;
}

.notes-container::-webkit-scrollbar-thumb {
    background: #ccc;
    border-radius: 4px;
}

.notes-container::-webkit-scrollbar-track {
    background: #f0f0f0;
}

.note-input {
    width: 100%;
    padding: 8px 12px;
    border: 1px solid #ddd;
    border-radius: 6px;
    font-size: 13px;
    transition: border-color 0.3s;
    box-sizing: border-box;
}

.note-input:focus {
    outline: none;
    border-color: #1A4D4A;
}

/* Dark mode overrides */
body.dark-mode .candidate-card {
    background: #2d2d44;
    border-color: #444466;
}

body.dark-mode .card-header {
    background: #25253a;
    border-bottom-color: #3d3d55;
}

body.dark-mode .candidate-name {
    color: #e0e0e0;
}

body.dark-mode .candidate-email {
    color: #999;
}

body.dark-mode .card-details {
    background: #25253a;
    border-top-color: #444466;
}

body.dark-mode .details-section h4 {
    color: #C9A96E;
}

body.dark-mode .details-section p {
    color: #bbb;
}

body.dark-mode .note-input {
    background: #3d3d55;
    color: #e0e0e0;
    border-color: #555577;
}

body.dark-mode .note-input:focus {
    border-color: #C9A96E;
}

body.dark-mode .notes-container::-webkit-scrollbar-thumb {
    background: #555577;
}

body.dark-mode .notes-container::-webkit-scrollbar-track {
    background: #3d3d55;
}

body.dark-mode .btn-secondary {
    background: #444466;
    color: #e0e0e0;
}

body.dark-mode .btn-secondary:hover {
    background: #555577;
}

body.dark-mode .btn-expand:hover {
    background: #3d3d55;
    color: #C9A96E;
}

body.dark-mode .skill-tag {
    background: #3d3d55;
    color: #e0e0e0;
}

body.dark-mode .skill-tag.more {
    background: #444466;
    color: #aaa;
}

body.dark-mode .status-badge {
    border-color: rgba(255,255,255,0.1);
}

body.dark-mode .meta-item {
    color: #999;
}
        .spinner { border: 3px solid #f3f3f3; border-top: 3px solid #1A4D4A; border-radius: 50%; width: 30px; height: 30px; animation: spin 1s linear infinite; margin: 10px auto; }
        @keyframes spin { 0% { transform: rotate(0deg); } 100% { transform: rotate(360deg); } }
        .flex { display: flex; gap: 10px; flex-wrap: wrap; }
        .flex-1 { flex: 1; }
        .filter-bar { background: white; padding: 10px; border-radius: 8px; margin-bottom: 15px; display: flex; gap: 10px; flex-wrap: wrap; }
        .filter-bar input, .filter-bar select { width: auto; flex: 1; }
        
        .modal { display: none; position: fixed; z-index: 1000; left: 0; top: 0; width: 100%; height: 100%; background: rgba(0,0,0,0.5); }
        .modal-content { background: #F5F0E8; margin: 50px auto; border-radius: 10px; max-width: 700px; width: 90%; }
        .modal-header { background: #1A4D4A; color: white; padding: 15px; border-radius: 10px 10px 0 0; display: flex; justify-content: space-between; }
        .modal-body { padding: 20px; max-height: 60vh; overflow-y: auto; }
        .close { cursor: pointer; font-size: 24px; }
        .detail-row { margin-bottom: 10px; display: flex; border-bottom: 1px solid #ddd; padding-bottom: 5px; }
        .detail-label { width: 130px; font-weight: bold; }
        .detail-value { flex: 1; }
        .company-item { background: #F9F6F0; padding: 8px; margin-bottom: 5px; border-radius: 5px; border-left: 3px solid #1A4D4A; }
        .btn-edit { background: #C9A96E; }
        .btn-secondary { background: #6B7B7B; }
        .doc-link { cursor: pointer; color: #1A4D4A; text-decoration: underline; }
        .file-list { background: #F9F6F0; border-radius: 8px; padding: 10px; margin-top: 10px; max-height: 150px; overflow-y: auto; }
        .file-list-item { padding: 5px; border-bottom: 1px solid #ddd; font-size: 12px; display: flex; justify-content: space-between; }
        .remove-file { color: #B22222; cursor: pointer; margin-left: 10px; }
        .progress-bar { background: #ddd; border-radius: 10px; height: 15px; margin: 10px 0; overflow: hidden; }
        .progress-fill { background: #1B6B2E; width: 0%; height: 100%; transition: width 0.3s; }
        /* Sidebar navigation styles */
.tab-btn.active {
    background: rgba(255,255,255,0.12) !important;
    border-left: 3px solid #C9A96E !important;
    color: #C9A96E !important;
}
.tab-btn:hover {
    background: rgba(255,255,255,0.08) !important;
}
/* ========== MOBILE RESPONSIVE ========== */
/* Hamburger menu button - hidden on desktop */
.mobile-menu-btn {
    display: none;
    background: #1A4D4A;
    color: white;
    border: none;
    padding: 12px 16px;
    font-size: 24px;
    cursor: pointer;
    border-radius: 8px;
    width: 100%;
    text-align: left;
    margin-bottom: 10px;
}

/* Sidebar - visible on desktop */
.sidebar {
    width: 220px;
    background: #1A4D4A;
    border-radius: 12px;
    padding: 20px 0;
    flex-shrink: 0;
    box-shadow: 0 2px 10px rgba(0,0,0,0.1);
    transition: all 0.3s ease;
}

/* Content area - fills remaining space */
.content-area {
    flex: 1;
    min-width: 0;
}

<style>
    body { font-family: Arial; background: #F5F0E8; margin: 0; padding: 20px; }
    /* ... all your existing CSS ... */
    .progress-fill { background: #1B6B2E; width: 0%; height: 100%; transition: width 0.3s; }
    
    /* Sidebar container */
    .sidebar-container {
        display: flex;
        gap: 20px;
        align-items: flex-start;
        margin-bottom: 20px;
    }

    /* ===== MOBILE STYLES ===== */
    @media screen and (max-width: 768px) {
        .sidebar-container {
            flex-direction: column;
            gap: 10px;
        }
        
        .mobile-menu-btn {
            display: block;
        }
        
        .sidebar {
            width: 100%;
            display: none;
            border-radius: 8px;
        }
        
        .sidebar.open {
            display: block;
        }
        
        .tab-btn {
            padding: 14px 20px !important;
            font-size: 15px !important;
        }
    }
/* ========== TOAST NOTIFICATIONS ========== */
.toast-container {
    position: fixed;
    top: 20px;
    right: 20px;
    z-index: 9999;
    display: flex;
    flex-direction: column;
    gap: 10px;
    max-width: 350px;
    width: 100%;
}

.toast {
    padding: 15px 20px;
    border-radius: 10px;
    color: white;
    font-size: 14px;
    font-weight: 500;
    box-shadow: 0 4px 15px rgba(0,0,0,0.2);
    transform: translateX(400px);
    animation: slideIn 0.5s forwards;
    display: flex;
    align-items: center;
    gap: 10px;
}

.toast-success {
    background: #1B6B2E;
    border-left: 4px solid #4CAF50;
}

.toast-error {
    background: #B22222;
    border-left: 4px solid #F44336;
}

.toast-warning {
    background: #CC5500;
    border-left: 4px solid #FF9800;
}

.toast-info {
    background: #1A4D4A;
    border-left: 4px solid #2196F3;
}

.toast-icon {
    font-size: 20px;
}

.toast-message {
    flex: 1;
}

.toast-close {
    cursor: pointer;
    font-size: 18px;
    opacity: 0.7;
    transition: opacity 0.3s;
    background: none;
    border: none;
    color: white;
}

.toast-close:hover {
    opacity: 1;
}

@keyframes slideIn {
    to {
        transform: translateX(0);
    }
}

@keyframes slideOut {
    to {
        transform: translateX(400px);
        opacity: 0;
    }
}

.toast-hidden {
    animation: slideOut 0.5s forwards;
}

@media (max-width: 480px) {
    .toast-container {
        top: 10px;
        right: 10px;
        max-width: calc(100% - 20px);
    }
}
/* ========== DARK MODE ========== */
body.dark-mode {
    background: #1a1a2e;
    color: #e0e0e0;
}

body.dark-mode .header {
    background: #16213e;
    color: #e0e0e0;
}

body.dark-mode .card {
    background: #2d2d44;
    border-left: 4px solid #C9A96E;
    color: #e0e0e0;
}

body.dark-mode .card.no-click {
    background: #2d2d44;
}

body.dark-mode .tab-btn {
    background: #2d2d44;
    color: #e0e0e0;
    border: 1px solid #444466;
}

body.dark-mode .tab-btn.active {
    background: #1A4D4A;
    color: white;
}

body.dark-mode input, 
body.dark-mode select, 
body.dark-mode textarea {
    background: #2d2d44;
    color: #e0e0e0;
    border: 1px solid #444466;
}

body.dark-mode input::placeholder,
body.dark-mode textarea::placeholder {
    color: #888899;
}

body.dark-mode .modal-content {
    background: #1a1a2e;
    color: #e0e0e0;
}

body.dark-mode .modal-header {
    background: #16213e;
}

body.dark-mode .detail-row {
    border-bottom: 1px solid #444466;
}

body.dark-mode .company-item {
    background: #2d2d44;
    border-left: 3px solid #C9A96E;
}

body.dark-mode .file-list {
    background: #2d2d44;
}

body.dark-mode .file-list-item {
    border-bottom: 1px solid #444466;
}

body.dark-mode .filter-bar {
    background: #2d2d44;
}

body.dark-mode .skill-tag {
    background: #3d3d55;
    color: #e0e0e0;
}

body.dark-mode .skill-with-years {
    background: #1a3d2e;
    color: #8bc34a;
}

body.dark-mode .alert-success {
    background: #1a3d2e;
    color: #e0e0e0;
}

body.dark-mode .alert-error {
    background: #3d1a1a;
    color: #e0e0e0;
}

body.dark-mode #uploaderStats {
    background: #2d2d44;
    color: #e0e0e0;
}

body.dark-mode .toast {
    background: #2d2d44 !important;
    color: #e0e0e0 !important;
}

body.dark-mode .toast-success {
    background: #1a4d2e !important;
    border-left: 4px solid #4CAF50 !important;
}

body.dark-mode .toast-error {
    background: #4d1a1a !important;
    border-left: 4px solid #F44336 !important;
}

body.dark-mode .toast-warning {
    background: #4d3a1a !important;
    border-left: 4px solid #FF9800 !important;
}

body.dark-mode .toast-info {
    background: #1a3d4d !important;
    border-left: 4px solid #2196F3 !important;
}

/* Dark mode toggle button */
.dark-mode-toggle {
    background: none;
    border: none;
    font-size: 24px;
    cursor: pointer;
    padding: 5px 10px;
    border-radius: 8px;
    transition: all 0.3s;
}

.dark-mode-toggle:hover {
    transform: scale(1.1);
}

body.dark-mode .dark-mode-toggle {
    color: #FFD700;
}
/* ========== RESPONSIVE DESIGN ========== */

/* ===== TABLET (600px - 1024px) ===== */
@media screen and (min-width: 600px) and (max-width: 1024px) {
    /* Sidebar: Show icons only */
    .sidebar {
        width: 80px !important;
        padding: 15px 0 !important;
    }
    
    .sidebar .menu-label {
        display: none;
    }
    
    .sidebar .tab-btn {
        padding: 12px !important;
        text-align: center !important;
        font-size: 12px !important;
    }
    
    .sidebar .tab-btn span {
        display: none;
    }
    
    .sidebar .tab-btn::before {
        font-size: 20px;
    }
    
    /* Cards: 2 columns */
    #candidatesList {
        display: grid;
        grid-template-columns: 1fr 1fr;
        gap: 10px;
    }
    
    #candidatesList .card {
        margin: 0 !important;
    }
    
    /* Dashboard: 2 columns */
    .dashboard-grid {
        grid-template-columns: 1fr 1fr !important;
    }
    
    /* Stats: 3 columns */
    .stats-grid {
        grid-template-columns: repeat(3, 1fr) !important;
    }
}

/* ===== MOBILE (360px - 599px) ===== */
@media screen and (max-width: 599px) {
    /* Body padding */
    body {
        padding: 10px !important;
    }
    
    /* Header */
    .header {
        padding: 15px !important;
    }
    
    .header h1 {
        font-size: 18px !important;
    }
    
    .header p {
        font-size: 12px !important;
    }
    
    .dark-mode-toggle {
        font-size: 20px !important;
        padding: 8px 12px !important;
    }
    
    /* Sidebar - Full width hamburger */
    .sidebar-container {
        flex-direction: column !important;
        gap: 10px !important;
    }
    
    .mobile-menu-btn {
        display: block !important;
        width: 100%;
        background: #1A4D4A;
        color: white;
        border: none;
        padding: 12px 16px;
        font-size: 20px;
        text-align: left;
        border-radius: 8px;
        cursor: pointer;
    }
    
    .sidebar {
        width: 100% !important;
        display: none;
        border-radius: 8px !important;
        padding: 10px 0 !important;
    }
    
    .sidebar.open {
        display: block !important;
    }
    
    .sidebar .tab-btn {
        padding: 14px 20px !important;
        font-size: 15px !important;
        width: 100% !important;
        text-align: left !important;
        border-left: 3px solid transparent !important;
    }
    
    .sidebar .tab-btn.active {
        border-left: 3px solid #C9A96E !important;
    }
    
    /* Content area - full width */
    .content-area {
        width: 100% !important;
        min-width: 0 !important;
    }
    
    /* Cards - full width, single column */
    #candidatesList {
        display: flex;
        flex-direction: column;
        gap: 10px;
    }
    
    #candidatesList .card {
        margin: 0 !important;
        padding: 12px 14px !important;
    }
    
    .card h3 {
        font-size: 15px !important;
    }
    
    /* Filter bar - stack vertically */
    .filter-bar {
        flex-direction: column !important;
        gap: 8px !important;
        padding: 12px !important;
    }
    
    .filter-bar input,
    .filter-bar select,
    .filter-bar button {
        width: 100% !important;
        min-width: 100% !important;
        padding: 10px !important;
        font-size: 14px !important;
    }
    
    #searchBox {
        min-width: 100% !important;
    }
    
    /* Pipeline stats - 3 columns */
    .pipeline-stats {
        display: grid !important;
        grid-template-columns: repeat(3, 1fr) !important;
        gap: 6px !important;
    }
    
    .pipeline-stats > div {
        padding: 8px !important;
    }
    
    .pipeline-stats > div div:first-child {
        font-size: 16px !important;
    }
    .pipeline-stats > div div:last-child {
        font-size: 9px !important;
    }
    
    /* Stats in dashboard - 2 columns */
    .dashboard-stats {
        grid-template-columns: 1fr 1fr !important;
        gap: 10px !important;
    }
    
    .dashboard-stats > div {
        padding: 12px !important;
    }
    
    .dashboard-stats > div div:first-child {
        font-size: 22px !important;
    }
    
    /* Dashboard charts - single column */
    .dashboard-charts {
        grid-template-columns: 1fr !important;
        gap: 15px !important;
    }
    
    .dashboard-charts > div {
        padding: 12px !important;
    }
    
    /* Modals - full screen */
    .modal-content {
        margin: 10px auto !important;
        max-width: 95% !important;
        width: 95% !important;
    }
    
    .modal-header h2 {
        font-size: 18px !important;
    }
    
    .modal-body {
        padding: 15px !important;
        max-height: 70vh !important;
    }
    
    /* Detail rows - stack labels */
    .detail-row {
        flex-direction: column !important;
        gap: 2px !important;
    }
    
    .detail-label {
        width: 100% !important;
        font-weight: bold;
        font-size: 12px !important;
        color: #666;
    }
    
    .detail-value {
        font-size: 14px !important;
    }
    
    /* Buttons - touch friendly */
    button, .btn {
        padding: 12px 18px !important;
        font-size: 14px !important;
        min-height: 44px !important;
        min-width: 44px !important;
    }
    
    /* Tabs */
    .tab-btn {
        padding: 12px 16px !important;
        font-size: 14px !important;
    }
    
    /* Upload area */
    .upload-area {
        padding: 15px !important;
    }
    
    .upload-area input[type="file"] {
        padding: 10px !important;
    }
    
    /* Pagination */
    #pagination {
        flex-direction: column !important;
        gap: 8px !important;
        align-items: center !important;
    }
    
    #paginationControls {
        justify-content: center !important;
    }
    
    #paginationControls .btn {
        padding: 8px 14px !important;
        font-size: 13px !important;
        min-height: 40px !important;
        min-width: 40px !important;
    }
    
    /* Uploader stats */
    #uploaderStats {
        padding: 12px !important;
    }
    
    #uploaderStats h4 {
        font-size: 14px !important;
    }
    
    #uploaderChart > div {
        flex-direction: column !important;
        align-items: flex-start !important;
        gap: 4px !important;
    }
    
    #uploaderChart > div span:first-child {
        min-width: 100% !important;
        font-size: 12px !important;
    }
    
    #uploaderChart > div > div {
        width: 100% !important;
        height: 18px !important;
    }
    
    #uploaderChart > div span:last-child {
        min-width: 100% !important;
        text-align: left !important;
        font-size: 11px !important;
    }
    
    /* Skills cloud */
    #skillsCloud span {
        font-size: 12px !important;
        padding: 3px 10px !important;
    }
    
    /* Toast notifications - full width */
    .toast-container {
        top: 10px !important;
        right: 10px !important;
        max-width: calc(100% - 20px) !important;
    }
    
    .toast {
        font-size: 13px !important;
        padding: 12px 16px !important;
    }
}

/* ===== VERY SMALL PHONES (320px - 359px) ===== */
@media screen and (max-width: 359px) {
    .header h1 {
        font-size: 16px !important;
    }
    
    .pipeline-stats {
        grid-template-columns: repeat(2, 1fr) !important;
    }
    
    .dashboard-stats {
        grid-template-columns: 1fr !important;
    }
    
    .card h3 {
        font-size: 13px !important;
    }
    
    button, .btn {
        font-size: 12px !important;
        padding: 10px 14px !important;
    }
}
/* ============================================
   RESUME TEXT VIEWER STYLES
   ============================================ */
#resume-text-container {
    background: #f9f6f0;
    border-radius: 8px;
    padding: 12px;
    max-height: 300px;
    overflow-y: auto;
    border: 1px solid #e0e0e0;
    white-space: pre-wrap;
    font-family: 'Courier New', monospace;
    font-size: 13px;
    line-height: 1.6;
    user-select: text;
    cursor: text;
}

/* Scrollbar styling for resume text */
#resume-text-container::-webkit-scrollbar {
    width: 6px;
}

#resume-text-container::-webkit-scrollbar-track {
    background: #f0f0f0;
    border-radius: 4px;
}

#resume-text-container::-webkit-scrollbar-thumb {
    background: #ccc;
    border-radius: 4px;
}

#resume-text-container::-webkit-scrollbar-thumb:hover {
    background: #aaa;
}

/* Preview modal text styles */
#previewBody div {
    white-space: pre-wrap;
    background: #f9f6f0;
    padding: 15px;
    border-radius: 8px;
    max-height: 500px;
    overflow-y: auto;
    user-select: text;
    cursor: text;
    font-family: 'Courier New', monospace;
    font-size: 13px;
    line-height: 1.6;
    border: 1px solid #e0e0e0;
}

/* Preview modal scrollbar */
#previewBody div::-webkit-scrollbar {
    width: 6px;
}

#previewBody div::-webkit-scrollbar-track {
    background: #f0f0f0;
    border-radius: 4px;
}

#previewBody div::-webkit-scrollbar-thumb {
    background: #ccc;
    border-radius: 4px;
}

#previewBody div::-webkit-scrollbar-thumb:hover {
    background: #aaa;
}

/* Button styles for preview modal */
#previewBody button {
    transition: all 0.2s;
}

#previewBody button:hover {
    transform: translateY(-2px);
    box-shadow: 0 4px 12px rgba(0,0,0,0.15);
}

/* ============================================
   DARK MODE - RESUME TEXT VIEWER
   ============================================ */
body.dark-mode #resume-text-container {
    background: #2d2d44;
    border-color: #444466;
    color: #e0e0e0;
}

body.dark-mode #resume-text-container::-webkit-scrollbar-track {
    background: #3d3d55;
}

body.dark-mode #resume-text-container::-webkit-scrollbar-thumb {
    background: #555577;
}

body.dark-mode #resume-text-container::-webkit-scrollbar-thumb:hover {
    background: #666688;
}

body.dark-mode #previewBody div {
    background: #2d2d44;
    border-color: #444466;
    color: #e0e0e0;
}

body.dark-mode #previewBody div::-webkit-scrollbar-track {
    background: #3d3d55;
}

body.dark-mode #previewBody div::-webkit-scrollbar-thumb {
    background: #555577;
}

body.dark-mode #previewBody div::-webkit-scrollbar-thumb:hover {
    background: #666688;
}

/* ============================================
   RESUME SECTION IN CANDIDATE VIEW
   ============================================ */
.resume-section {
    margin-top: 10px;
}

.resume-section .btn-group {
    display: flex;
    gap: 10px;
    flex-wrap: wrap;
    align-items: center;
    margin-bottom: 10px;
}

.resume-section .btn-group button {
    padding: 6px 14px;
    border: none;
    border-radius: 6px;
    cursor: pointer;
    font-size: 12px;
    transition: all 0.2s;
}

.resume-section .btn-group button:hover {
    transform: translateY(-2px);
    box-shadow: 0 4px 12px rgba(0,0,0,0.15);
}

.resume-section .btn-download {
    background: #1A4D4A;
    color: white;
}

.resume-section .btn-download:hover {
    background: #2A6B67;
}

.resume-section .btn-copy {
    background: #C9A96E;
    color: white;
}

.resume-section .btn-copy:hover {
    background: #B8985E;
}

.resume-section .resume-text-box {
    background: #f9f6f0;
    border-radius: 8px;
    padding: 12px;
    max-height: 300px;
    overflow-y: auto;
    border: 1px solid #e0e0e0;
    white-space: pre-wrap;
    font-family: 'Courier New', monospace;
    font-size: 13px;
    line-height: 1.6;
    user-select: text;
    cursor: text;
}

.resume-section .resume-text-box::-webkit-scrollbar {
    width: 6px;
}

.resume-section .resume-text-box::-webkit-scrollbar-track {
    background: #f0f0f0;
    border-radius: 4px;
}

.resume-section .resume-text-box::-webkit-scrollbar-thumb {
    background: #ccc;
    border-radius: 4px;
}

.resume-section .resume-text-box::-webkit-scrollbar-thumb:hover {
    background: #aaa;
}

body.dark-mode .resume-section .resume-text-box {
    background: #2d2d44;
    border-color: #444466;
    color: #e0e0e0;
}

body.dark-mode .resume-section .resume-text-box::-webkit-scrollbar-track {
    background: #3d3d55;
}

body.dark-mode .resume-section .resume-text-box::-webkit-scrollbar-thumb {
    background: #555577;
}
</style>
</head>
<body>
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
    
   <div class="sidebar-container" style="display: flex; gap: 20px; align-items: flex-start; margin-bottom: 20px;">
    <!-- Mobile Menu Button -->
    <button class="mobile-menu-btn" onclick="toggleSidebar()">☰ Menu</button>
    
    <!-- Sidebar -->
    <div class="sidebar" id="sidebar" style="width: 220px; background: #1A4D4A; border-radius: 12px; padding: 20px 0; flex-shrink: 0; box-shadow: 0 2px 10px rgba(0,0,0,0.1);">
        <div style="padding: 0 20px 15px 20px; border-bottom: 1px solid rgba(255,255,255,0.1); margin-bottom: 10px;">
            <div style="color: #C9A96E; font-size: 11px; text-transform: uppercase; letter-spacing: 1px; font-weight: bold;">Menu</div>
        </div>
        <button class="tab-btn active" id="tabJobs" style="display: block; width: 100%; text-align: left; background: transparent; color: #FFFFFF; border: none; padding: 12px 20px; margin: 0; border-radius: 0; border-left: 3px solid transparent; cursor: pointer; font-size: 14px; transition: all 0.2s;">📋 Jobs</button>
        <button class="tab-btn" id="tabCandidates" style="display: block; width: 100%; text-align: left; background: transparent; color: #FFFFFF; border: none; padding: 12px 20px; margin: 0; border-radius: 0; border-left: 3px solid transparent; cursor: pointer; font-size: 14px; transition: all 0.2s;">👥 Candidates</button>
        <button class="tab-btn" id="tabUpload" style="display: block; width: 100%; text-align: left; background: transparent; color: #FFFFFF; border: none; padding: 12px 20px; margin: 0; border-radius: 0; border-left: 3px solid transparent; cursor: pointer; font-size: 14px; transition: all 0.2s;">📄 Upload Resume</button>
        <button class="tab-btn" id="tabCreateJob" style="display: block; width: 100%; text-align: left; background: transparent; color: #FFFFFF; border: none; padding: 12px 20px; margin: 0; border-radius: 0; border-left: 3px solid transparent; cursor: pointer; font-size: 14px; transition: all 0.2s;">➕ Create Job</button>
        <button class="tab-btn" id="tabAnalyze" style="display: block; width: 100%; text-align: left; background: transparent; color: #FFFFFF; border: none; padding: 12px 20px; margin: 0; border-radius: 0; border-left: 3px solid transparent; cursor: pointer; font-size: 14px; transition: all 0.2s;">🔍 Analyze Match</button>
        <button class="tab-btn" id="tabDashboard" style="display: block; width: 100%; text-align: left; background: transparent; color: #FFFFFF; border: none; padding: 12px 20px; margin: 0; border-radius: 0; border-left: 3px solid transparent; cursor: pointer; font-size: 14px; transition: all 0.2s;">📊 Dashboard</button>
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
        <select id="statusFilter" style="padding: 8px; border: 1px solid #ccc; border-radius: 5px;">
            <option value="all">All Status</option>
            <option value="new">🟢 New</option>
            <option value="screening">🔵 Screening</option>
            <option value="interview">🟠 Interview</option>
            <option value="offer">🟣 Offer</option>
            <option value="hired">✅ Hired</option>
            <option value="rejected">❌ Rejected</option>
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
    
    <div id="createJobPanel" style="display:none;"><div class="card no-click"><h3>➕ Create Job</h3><input type="text" id="jobTitle" placeholder="Job Title *"><input type="text" id="jobCompany" placeholder="Company"><textarea id="jobDesc" rows="4" placeholder="Job Description"></textarea><button id="createJobBtn">Create Job</button></div></div>
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
            <h3>📊 Recruitment Dashboard</h3>
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

<!-- Modals -->
<div id="candidateModal" class="modal"><div class="modal-content"><div class="modal-header"><h2>Candidate Profile</h2><span class="close" onclick="closeModal()">&times;</span></div><div class="modal-body" id="modalBody"></div></div></div>
<div id="editModal" class="modal"><div class="modal-content"><div class="modal-header"><h2>✏️ Edit Candidate</h2><span class="close" onclick="closeEditModal()">&times;</span></div><div class="modal-body" id="editModalBody"></div></div></div>
<div id="docModal" class="modal"><div class="modal-content"><div class="modal-header"><h2>📎 Add Document</h2><span class="close" onclick="closeDocModal()">&times;</span></div><div class="modal-body"><input type="file" id="docFile"><button id="uploadDocBtn" class="btn">Upload</button><div id="docUploadStatus"></div></div></div></div>
<div id="previewModal" class="modal"><div class="modal-content"><div class="modal-header"><h2>Preview</h2><span class="close" onclick="closePreviewModal()">&times;</span></div><div class="modal-body" id="previewBody"></div></div></div>
<div id="editJobModal" class="modal"><div class="modal-content"><div class="modal-header"><h2>✏️ Edit Job</h2><span class="close" onclick="closeEditJobModal()">&times;</span></div><div class="modal-body" id="editJobModalBody"></div></div></div>

<script>
    let allJobs = [], allCandidates = [], currentCandidateId = null;
    let selectedBulkFiles = [];
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
            <button class="toast-close" onclick="this.parentElement.remove()">✕</button>
        `;
        
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
    document.getElementById('tabJobs').onclick = function() { showPanel('jobs'); loadJobs(); };
    document.getElementById('tabCandidates').onclick = function() { showPanel('candidates'); loadCandidates(); };
    document.getElementById('tabUpload').onclick = function() { showPanel('upload'); };
    document.getElementById('tabCreateJob').onclick = function() { showPanel('createJob'); };
    document.getElementById('tabAnalyze').onclick = function() { showPanel('analyze'); loadJobs(); loadCandidates(); };
    document.getElementById('tabDashboard').onclick = function() { showPanel('dashboard'); loadDashboard(); };
    
    function showPanel(panel) {
    document.getElementById('jobsPanel').style.display = 'none';
    document.getElementById('candidatesPanel').style.display = 'none';
    document.getElementById('uploadPanel').style.display = 'none';
    document.getElementById('createJobPanel').style.display = 'none';
    document.getElementById('analyzePanel').style.display = 'none';
    document.getElementById('dashboardPanel').style.display = 'none';
    document.getElementById(panel + 'Panel').style.display = 'block';
    document.querySelectorAll('.tab-btn').forEach(btn => btn.classList.remove('active'));
    if(panel === 'jobs') document.getElementById('tabJobs').classList.add('active');
    if(panel === 'candidates') document.getElementById('tabCandidates').classList.add('active');
    if(panel === 'upload') document.getElementById('tabUpload').classList.add('active');
    if(panel === 'createJob') document.getElementById('tabCreateJob').classList.add('active');
    if(panel === 'analyze') document.getElementById('tabAnalyze').classList.add('active');
    if(panel === 'dashboard') document.getElementById('tabDashboard').classList.add('active');
}
    
    async function loadJobs() {
        const res = await fetch('/api/jobs');
        allJobs = await res.json();
        const container = document.getElementById('jobsList');
        if(!allJobs.length) { container.innerHTML = '<div class="card no-click">No jobs yet</div>'; return; }
        container.innerHTML = allJobs.map(j => `<div class="card" onclick="editJob(${j.id})"><h3>${escapeHtml(j.title)}</h3>${j.company ? `<p>🏢 ${escapeHtml(j.company)}</p>` : ''}<small>${new Date(j.created_at).toLocaleDateString()}</small></div>`).join('');
        document.getElementById('jobSelect').innerHTML = '<option value="">-- Select Job --</option>' + allJobs.map(j => `<option value="${j.id}">${escapeHtml(j.title)}</option>`).join('');
        document.getElementById('batchJobSelect').innerHTML = '<option value="">-- Select Job --</option>' + allJobs.map(j => `<option value="${j.id}">${escapeHtml(j.title)}</option>`).join('');
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
        filtered = filtered.filter(c => (c.employment_status || 'new') === statusFilter);
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
        filtered.sort((a, b) => (a.employment_status || '').localeCompare(b.employment_status || ''));
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
        const skills = c.core_skills ? JSON.parse(c.core_skills) : [];
        const matchScore = c.match_score || 0;
        const matchClass = matchScore >= 70 ? 'match-high' : (matchScore >= 40 ? 'match-medium' : 'match-low');
        const status = c.employment_status || 'new';
        
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
                        `<span class="skill-tag">${escapeHtml(s.skill)}</span>`
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
        document.getElementById('editJobModalBody').innerHTML = `<form id="editJobForm"><label>Job Title</label><input type="text" id="editJobTitle" value="${escapeHtml(job.title || '')}"><label>Company</label><input type="text" id="editJobCompany" value="${escapeHtml(job.company || '')}"><label>Description</label><textarea id="editJobDesc" rows="5">${escapeHtml(job.description || '')}</textarea><h4>Attach Document</h4><input type="file" id="jobDocFile"><button type="button" id="uploadJobDocBtn" class="btn btn-secondary">Upload</button><div id="jobDocUploadStatus"></div>${docsHtml}<div style="margin-top:20px;"><button type="submit" class="btn">Save</button><button type="button" class="btn btn-secondary" onclick="closeEditJobModal()">Cancel</button></div></form>`;
        document.getElementById('editJobModal').style.display = 'block';
        document.getElementById('uploadJobDocBtn').onclick = async function() {
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
            const data = { title: document.getElementById('editJobTitle').value, company: document.getElementById('editJobCompany').value, description: document.getElementById('editJobDesc').value };
            const res = await fetch(`/api/jobs/${id}`, { method: 'PUT', headers: {'Content-Type':'application/json'}, body: JSON.stringify(data) });
            if (res.ok) { toastSuccess('Job updated!'); closeEditJobModal(); loadJobs(); }
        };
    };
    
    window.deleteJobDocument = async function(docId, jobId) {
        if (confirm('Delete?')) { await fetch(`/api/jobs/documents/${docId}`, { method: 'DELETE' }); editJob(jobId); }
    };
    function closeEditJobModal() { document.getElementById('editJobModal').style.display = 'none'; }
    window.closeEditJobModal = closeEditJobModal;
    
    // View Candidate
           window.viewCandidate = async function(id) {
        currentCandidateId = id;
        const c = allCandidates.find(c => c.id == id);
        const skills = c.core_skills ? JSON.parse(c.core_skills) : [];
        const certs = c.certifications ? JSON.parse(c.certifications) : [];
        const workExp = c.work_experience ? JSON.parse(c.work_experience) : [];
        const docRes = await fetch(`/api/candidates/${id}/documents`);
        const documents = await docRes.json();
        const resumeDoc = documents.find(d => d.is_resume === 1);
        const otherDocs = documents.filter(d => !d.is_resume);
        
        document.getElementById('modalBody').innerHTML = `
            <div style="display:flex; gap:10px; justify-content:flex-end; margin-bottom:15px;">
                <button class="btn btn-edit" onclick="openEditModal(${c.id})">✏️ Edit</button>
                <button class="btn btn-secondary" onclick="openDocModal(${c.id})">📎 Add Document</button>
                <button class="btn btn-secondary" onclick="copyAllDetails()">📋 Copy</button>
                <button class="btn" style="background: #C9A96E; color: white;" onclick="exportPDF(${c.id}, event)">📄 Export PDF</button>
            </div>
            <div class="detail-row"><div class="detail-label">Name:</div><div class="detail-value">${escapeHtml((c.first_name||'') + ' ' + (c.last_name||''))}</div></div>
            <div class="detail-row"><div class="detail-label">Phone:</div><div class="detail-value">${escapeHtml(c.phone || 'N/A')}</div></div>
            <div class="detail-row"><div class="detail-label">Email:</div><div class="detail-value">${escapeHtml(c.email || 'N/A')}</div></div>
            <div class="detail-row"><div class="detail-label">Role:</div><div class="detail-value">${escapeHtml(c.current_role || 'N/A')}</div></div>
            <div class="detail-row"><div class="detail-label">CTC:</div><div class="detail-value">Current: ${escapeHtml(c.current_ctc || 'N/A')} | Expected: ${escapeHtml(c.expected_ctc || 'N/A')}</div></div>
            <div class="detail-row"><div class="detail-label">Status:</div><div class="detail-value">
                <select id="candidateStatus-${c.id}" onchange="updateStatus(${c.id}, this.value)" style="padding: 4px 8px; border-radius: 5px; border: 1px solid #ccc;">
                    <option value="new" ${c.employment_status === 'new' ? 'selected' : ''}>🟢 New</option>
                    <option value="screening" ${c.employment_status === 'screening' ? 'selected' : ''}>🔵 Screening</option>
                    <option value="interview" ${c.employment_status === 'interview' ? 'selected' : ''}>🟠 Interview</option>
                    <option value="offer" ${c.employment_status === 'offer' ? 'selected' : ''}>🟣 Offer</option>
                    <option value="hired" ${c.employment_status === 'hired' ? 'selected' : ''}>✅ Hired</option>
                    <option value="rejected" ${c.employment_status === 'rejected' ? 'selected' : ''}>❌ Rejected</option>
                </select>
                ${c.notice_period_days ? ` (${c.notice_period_days} days notice)` : ''}
            </div></div>
            <h4>Work Experience</h4>
            ${workExp.map(w => `<div class="company-item"><strong>${escapeHtml(w.company)}</strong> — ${escapeHtml(w.role)}<br><small>${escapeHtml(w.start_date||'')} - ${escapeHtml(w.end_date||'Present')}</small></div>`).join('') || '<p>None</p>'}
            <h4>Skills</h4>
            ${skills.map(s => `<span class="skill-with-years">${escapeHtml(s.skill)} (${s.years_of_experience||0}y)</span>`).join('') || '<p>None</p>'}
            <h4>Certifications</h4>
            ${certs.map(cert => `<div>📜 ${escapeHtml(cert)}</div>`).join('') || '<p>None</p>'}
            <h4>📄 Resume</h4>
            ${resumeDoc ? `
    <div style="display: flex; gap: 10px; flex-wrap: wrap; align-items: center; margin-bottom: 10px;">
        <span class="doc-link" onclick="previewDocument(${resumeDoc.id})">📄 ${escapeHtml(resumeDoc.original_filename)}</span>
        <span style="background:#1B6B2E;color:white;padding:2px 8px;border-radius:12px;font-size:10px;">Original</span>
        <button onclick="viewOriginalResume(${c.id})" style="background: #9C27B0; color: white; border: none; padding: 4px 12px; border-radius: 4px; cursor: pointer; font-size: 12px;">
            👁️ View Original
        </button>
        <button onclick="downloadResume(${c.id})" style="background: #1A4D4A; color: white; border: none; padding: 4px 12px; border-radius: 4px; cursor: pointer; font-size: 12px;">
            ⬇️ Download Original
        </button>
        <button onclick="copyResumeText(${c.id})" style="background: #C9A96E; color: white; border: none; padding: 4px 12px; border-radius: 4px; cursor: pointer; font-size: 12px;">
            📋 Copy Resume Text
        </button>
    </div>
    <div id="resume-text-${c.id}" style="background: #f9f6f0; border-radius: 8px; padding: 12px; max-height: 300px; overflow-y: auto; border: 1px solid #e0e0e0; white-space: pre-wrap; font-family: monospace; font-size: 13px; line-height: 1.6; user-select: text; cursor: text;">
        ${c.resume_text ? escapeHtml(c.resume_text) : 'No resume text available'}
    </div>
    ${c.resume_text && c.resume_text.length > 5000 ? `<p style="font-size: 12px; color: #999; margin-top: 5px;">📌 Resume is long. Click "View Original" to see the formatted version.</p>` : ''}
` : '<p>No resume uploaded</p>'}
            <h4>Other Documents</h4>
            ${otherDocs.map(d => `<div><span class="doc-link" onclick="previewDocument(${d.id})">📄 ${escapeHtml(d.original_filename)}</span></div>`).join('') || '<p>None</p>'}
            <h4>📝 Notes</h4>
            <div id="notes-${c.id}" style="max-height: 200px; overflow-y: auto; margin-bottom: 10px;">
                <div class="spinner" style="width: 20px; height: 20px;"></div>
            </div>
            <div style="display: flex; gap: 8px; margin-top: 5px;">
                <input type="text" id="newNote-${c.id}" placeholder="Add a note..." style="flex: 1; padding: 6px;">
                <button class="btn btn-secondary" style="padding: 6px 12px;" onclick="addNote(${c.id})">➕ Add</button>
            </div>
            <button class="btn" onclick="closeModal()">Close</button>
        `;
        loadNotes(c.id);
        document.getElementById('candidateModal').style.display = 'block';
    };
    
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
    function closePreviewModal() { document.getElementById('previewModal').style.display = 'none'; }
    window.closePreviewModal = closePreviewModal;
    
    window.copyAllDetails = function() {
        let text = '';
        document.querySelectorAll('#modalBody .detail-row, #modalBody .company-item, #modalBody .skill-with-years').forEach(el => text += el.innerText + '\\n');
        navigator.clipboard.writeText(text);
toastSuccess('Copied!');
    };
    
    function closeModal() { document.getElementById('candidateModal').style.display = 'none'; }
    window.closeModal = closeModal;
    // ============================================
// DOWNLOAD ORIGINAL RESUME
// ============================================
async function downloadResume(candidateId) {
    try {
        const res = await fetch(`/api/candidates/${candidateId}/download-resume`);
        if (res.ok) {
            const blob = await res.blob();
            const url = window.URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            
            // Get filename from content-disposition or use default
            const disposition = res.headers.get('content-disposition');
            let filename = 'resume.pdf';
            if (disposition) {
               const parts = disposition.split(';');
for (let part of parts) {
    if (part.trim().startsWith('filename=')) {
        filename = part.trim().substring(9).replace(/['"]/g, '');
        break;
    }
}
                if (match) filename = match[1].replace(/['"]/g, '');
            }
            a.download = filename;
            document.body.appendChild(a);
            a.click();
            a.remove();
            window.URL.revokeObjectURL(url);
            toastSuccess('Resume downloaded!');
        } else {
            toastError('Resume not found');
        }
    } catch(e) {
        toastError('Error downloading resume');
        console.error('Download error:', e);
    }
}
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
    
    window.openDocModal = function(id) { currentCandidateId = id; document.getElementById('docModal').style.display = 'block'; };
    document.getElementById('uploadDocBtn').onclick = async function() {
        const file = document.getElementById('docFile').files[0];
        if (!file || !currentCandidateId) return;
        const fd = new FormData(); fd.append('document', file); fd.append('candidate_id', currentCandidateId);
        document.getElementById('docUploadStatus').innerHTML = '<div class="spinner"></div>';
        const res = await fetch('/api/candidates/upload-document', { method: 'POST', body: fd });
       if (res.ok) { toastSuccess('Uploaded!'); closeDocModal(); viewCandidate(currentCandidateId); }
        document.getElementById('docUploadStatus').innerHTML = '';
    };
    
    document.getElementById('exportBtn').onclick = () => window.location.href = '/api/export-candidates';
    
    document.getElementById('parseBtn').onclick = async function() {
        const file = document.getElementById('resumeFile').files[0];
        if(!file) return;
        const fd = new FormData(); fd.append('resume', file);
        const div = document.getElementById('parseResult');
        div.innerHTML = '<div class="spinner"></div><p>Parsing...</p>';
        const res = await fetch('/api/parse-resume', { method: 'POST', body: fd });
        const result = await res.json();
        if(result.error) { div.innerHTML = `<div class="alert-error">${result.error}</div>`; return; }
        div.innerHTML = `<div class="alert-success"><h4>✅ Parsed</h4><p><strong>Name:</strong> ${escapeHtml(result.first_name||'')} ${escapeHtml(result.last_name||'')}</p><p><strong>Email:</strong> ${escapeHtml(result.email||'')}</p><p><strong>Phone:</strong> ${escapeHtml(result.phone||'')}</p><p><strong>Skills:</strong> ${result.core_skills ? result.core_skills.map(s => `<span class="skill-tag">${escapeHtml(s.skill)}</span>`).join('') : 'None'}</p><button id="saveBtn">💾 Save</button></div>`;
               document.getElementById('saveBtn').onclick = async function() {
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
    
    document.getElementById('createJobBtn').onclick = async function() {
        const data = { title: document.getElementById('jobTitle').value, company: document.getElementById('jobCompany').value, description: document.getElementById('jobDesc').value };
        if(!data.title) return;
        const res = await fetch('/api/jobs', { method: 'POST', headers: {'Content-Type':'application/json'}, body: JSON.stringify(data) });
        if(res.ok) { toastSuccess('Job created!'); document.getElementById('jobTitle').value = ''; document.getElementById('jobCompany').value = ''; document.getElementById('jobDesc').value = ''; showPanel('jobs'); loadJobs(); }
        else alert('Error');
    };
    
    document.getElementById('analyzeBtn').onclick = async function() {
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
                    <div style="font-size: 13px; color: #555; margin-top: 5px;">${result.executive_summary ? escapeHtml(result.executive_summary) : ''}</div>
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
    
    document.getElementById('bulkUploadBtn').onclick = async function() {
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
                } else {
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
       document.getElementById('batchAnalyzeBtn').onclick = async function() {
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
        const ctx = document.getElementById('pipelineChart').getContext('2d');
        const labels = ['New', 'Screening', 'Interview', 'Offer', 'Hired', 'Rejected'];
        const values = [
            pipeline.new || 0,
            pipeline.screening || 0,
            pipeline.interview || 0,
            pipeline.offer || 0,
            pipeline.hired || 0,
            pipeline.rejected || 0
        ];
        const colors = ['#2196F3', '#FF9800', '#FF5722', '#9C27B0', '#4CAF50', '#F44336'];
        
        if (pipelineChartInstance) {
            pipelineChartInstance.destroy();
        }
        
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
        if (!skills || skills.length === 0) {
            container.innerHTML = '<p style="color: #999; font-style: italic;">No skills data available</p>';
            return;
        }
        
        // Take top 15 skills
        const topSkills = skills.slice(0, 15);
        const maxCount = topSkills[0]?.count || 1;
        
        container.innerHTML = topSkills.map(s => {
            const size = 12 + (s.count / maxCount) * 20; // 12-32px
            const opacity = 0.6 + (s.count / maxCount) * 0.4;
            return `<span style="
                font-size: ${size}px;
                color: #1A4D4A;
                background: #F5F0E8;
                padding: 4px 12px;
                border-radius: 20px;
                border: 1px solid #ddd;
                opacity: ${opacity};
                font-weight: ${s.count > maxCount/2 ? 'bold' : 'normal'};
            ">${escapeHtml(s.skill)} (${s.count})</span>`;
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
    
    async function loadDashboard() {
        try {
            const res = await fetch('/api/dashboard-data');
            const data = await res.json();
            
            document.getElementById('totalCandidates').textContent = data.total || 0;
            document.getElementById('matchedCandidates').textContent = data.matched || 0;
            document.getElementById('hiredCandidates').textContent = data.hired || 0;
            document.getElementById('rejectedCandidates').textContent = data.rejected || 0;
            
            renderMatchChart(data.matchDistribution || {});
            renderPipelineChart(data.pipeline || {});
            renderSkillsCloud(data.skills || []);
            renderTrendChart(data.trend || {});
        } catch(e) {
            console.error('Dashboard error:', e);
        }
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
        if (!skills || skills.length === 0) { container.innerHTML = '<p style="color: #999; font-style: italic;">No skills data available</p>'; return; }
        const topSkills = skills.slice(0, 15);
        const maxCount = topSkills[0]?.count || 1;
        container.innerHTML = topSkills.map(s => {
            const size = 12 + (s.count / maxCount) * 20;
            return `<span style="font-size:${size}px; color:#1A4D4A; background:#F5F0E8; padding:4px 12px; border-radius:20px; border:1px solid #ddd; opacity:${0.6+(s.count/maxCount)*0.4};">${escapeHtml(s.skill)}</span>`;
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
    // ========== MOBILE SIDEBAR TOGGLE ==========
function toggleSidebar() {
    const sidebar = document.getElementById('sidebar');
    sidebar.classList.toggle('open');
}

// Close sidebar when a tab is clicked (on mobile)
document.querySelectorAll('.tab-btn').forEach(btn => {
    btn.addEventListener('click', function() {
        // Close sidebar on mobile after clicking
        if (window.innerWidth <= 768) {
            const sidebar = document.getElementById('sidebar');
            sidebar.classList.remove('open');
        }
    });
});
    
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
def get_jobs():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    c.execute('SELECT * FROM jobs ORDER BY created_at DESC')
    jobs = [dict(row) for row in c.fetchall()]
    conn.close()
    return jsonify(jobs)

@app.route('/api/jobs', methods=['POST'])
def create_job():
    data = request.json
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('INSERT INTO jobs (title, company, description) VALUES (?, ?, ?)',
              (data.get('title'), data.get('company'), data.get('description', '')))
    conn.commit()
    conn.close()
    return jsonify({'message': 'Job created'})

@app.route('/api/jobs/<int:job_id>', methods=['PUT'])
def update_job(job_id):
    data = request.json
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('UPDATE jobs SET title = ?, company = ?, description = ? WHERE id = ?',
              (data.get('title'), data.get('company'), data.get('description', ''), job_id))
    conn.commit()
    conn.close()
    return jsonify({'message': 'Job updated'})

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

@app.route('/api/candidates/<int:candidate_id>', methods=['PUT'])
def update_candidate(candidate_id):
    data = request.json
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('''UPDATE candidates SET 
        first_name=?, middle_name=?, last_name=?, email=?, phone=?, address=?, linkedin=?,
        current_role=?, current_ctc=?, expected_ctc=?,
        employment_status=?, notice_period_days=?, education=?,
        core_skills=?, certifications=?
        WHERE id=?''',
        (data.get('first_name'), data.get('middle_name'), data.get('last_name'),
         data.get('email'), data.get('phone'), data.get('address'), data.get('linkedin'),
         data.get('current_role'), data.get('current_ctc'), data.get('expected_ctc'),
         data.get('employment_status'), data.get('notice_period_days', 0),
         data.get('education'), data.get('core_skills'), data.get('certifications'), candidate_id))
    conn.commit()
    conn.close()
    return jsonify({'message': 'Candidate updated'})
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
    
    if not resume_text or not jd_text:
        return jsonify({'error': 'Missing text'}), 400
    
       # Use LOCAL open-source analysis (no API key needed!)
    result = analyze_resume_locally(resume_text, jd_text)
    
    # ADD SKILL GAP ANALYSIS
    skill_gap = analyze_skill_gap(resume_text, jd_text)
    result['skill_gap'] = skill_gap
    
    # ADD INTERVIEW QUESTIONS
    missing_skills = skill_gap.get('missing_skills', [])
    interview_questions = generate_interview_questions(jd_text, resume_text, missing_skills)
    result['interview_questions'] = interview_questions
    
    if result and candidate_id:
        detailed_json = json.dumps(result, indent=2)
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        c.execute('UPDATE candidates SET match_score = ?, recommendation = ?, detailed_analysis = ? WHERE id = ?',
                  (result.get('match_score', 0), result.get('recommendation', 'review'), detailed_json, candidate_id))
        conn.commit()
        conn.close()
        return jsonify(result)
    elif result:
        return jsonify(result)
    
    return jsonify({'error': 'Analysis failed'}), 500
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
        # Get candidate from database
        conn = get_db_connection()
        candidate = conn.execute('SELECT * FROM candidates WHERE id = ?', (candidate_id,)).fetchone()
        
        if not candidate:
            conn.close()
            return jsonify({'error': 'Candidate not found'}), 404
        
        # Get notes for this candidate
        notes = conn.execute(
            'SELECT note, created_at FROM candidate_notes WHERE candidate_id = ? ORDER BY created_at DESC',
            (candidate_id,)
        ).fetchall()
        conn.close()
        
        # Create PDF in memory
        buffer = io.BytesIO()
        
        # Use SimpleDocTemplate for better formatting
        doc = SimpleDocTemplate(buffer, pagesize=letter,
                               rightMargin=72, leftMargin=72,
                               topMargin=72, bottomMargin=72)
        
        # Styles
        styles = getSampleStyleSheet()
        title_style = ParagraphStyle(
            'CustomTitle',
            parent=styles['Heading1'],
            fontSize=24,
            textColor=colors.HexColor('#1a237e'),
            spaceAfter=30,
            alignment=TA_CENTER
        )
        heading_style = ParagraphStyle(
            'CustomHeading',
            parent=styles['Heading2'],
            fontSize=16,
            textColor=colors.HexColor('#0d47a1'),
            spaceAfter=12,
            spaceBefore=20
        )
        normal_style = styles['Normal']
        normal_style.fontSize = 11
        normal_style.spaceAfter = 6
        
        # Build content
        story = []
        
        # Title
        story.append(Paragraph(f"👤 Candidate Profile: {candidate['name']}", title_style))
        story.append(Spacer(1, 12))
        
        # Personal Information
        story.append(Paragraph("📋 Personal Information", heading_style))
        story.append(Paragraph(f"<b>Name:</b> {candidate['name']}", normal_style))
        story.append(Paragraph(f"<b>Email:</b> {candidate['email']}", normal_style))
        story.append(Paragraph(f"<b>Phone:</b> {candidate.get('phone', 'N/A')}", normal_style))
        story.append(Paragraph(f"<b>Status:</b> {candidate.get('status', 'New')}", normal_style))
        story.append(Paragraph(f"<b>Uploaded:</b> {candidate.get('uploaded_at', 'N/A')}", normal_style))
        story.append(Spacer(1, 12))
        
        # Skills
        skills = candidate.get('skills', 'N/A')
        story.append(Paragraph("🛠️ Skills", heading_style))
        if skills and skills != 'N/A':
            skill_list = skills.split(',') if isinstance(skills, str) else skills
            for skill in skill_list[:10]:  # Show top 10 skills
                story.append(Paragraph(f"• {skill.strip()}", normal_style))
        else:
            story.append(Paragraph("No skills listed", normal_style))
        story.append(Spacer(1, 12))
        
        # Match Score
        match_score = candidate.get('match_score', 0)
        story.append(Paragraph("🎯 Match Score", heading_style))
        score_color = '#4caf50' if match_score >= 70 else '#ff9800' if match_score >= 40 else '#f44336'
        story.append(Paragraph(
            f'<font color="{score_color}" size="18"><b>{match_score}%</b></font>',
            normal_style
        ))
        story.append(Spacer(1, 12))
        
        # Analysis
        analysis = candidate.get('analysis', '')
        if analysis:
            story.append(Paragraph("📊 AI Analysis", heading_style))
            try:
                # Parse analysis if it's JSON
                if isinstance(analysis, str):
                    analysis_data = json.loads(analysis)
                    if isinstance(analysis_data, dict):
                        # Summary
                        if 'summary' in analysis_data:
                            story.append(Paragraph(f"<b>Summary:</b> {analysis_data['summary']}", normal_style))
                        # Strengths
                        if 'strengths' in analysis_data and analysis_data['strengths']:
                            story.append(Paragraph("<b>Strengths:</b>", normal_style))
                            for strength in analysis_data['strengths'][:5]:
                                story.append(Paragraph(f"✓ {strength}", normal_style))
                        # Weaknesses
                        if 'weaknesses' in analysis_data and analysis_data['weaknesses']:
                            story.append(Paragraph("<b>Areas for Improvement:</b>", normal_style))
                            for weakness in analysis_data['weaknesses'][:5]:
                                story.append(Paragraph(f"○ {weakness}", normal_style))
                    else:
                        story.append(Paragraph(str(analysis)[:500], normal_style))
                else:
                    story.append(Paragraph(str(analysis)[:500], normal_style))
            except:
                story.append(Paragraph(str(analysis)[:500], normal_style))
        story.append(Spacer(1, 12))
        
        # Notes
        story.append(Paragraph("📝 Notes", heading_style))
        if notes:
            for note in notes:
                note_text = note['note'][:200]
                if len(note['note']) > 200:
                    note_text += '...'
                story.append(Paragraph(f"• {note_text}", normal_style))
                story.append(Paragraph(
                    f"<i style='color: #666;'>{note['created_at']}</i>",
                    normal_style
                ))
                story.append(Spacer(1, 6))
        else:
            story.append(Paragraph("No notes available", normal_style))
        
        # Footer
        story.append(Spacer(1, 30))
        story.append(Paragraph(
            f"<i style='color: #999; font-size: 8pt;'>Generated by ShahnaIT Scout on {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</i>",
            normal_style
        ))
        
        # Build PDF
        doc.build(story)
        buffer.seek(0)
        
        # Send file
        return send_file(
            buffer,
            as_attachment=True,
            download_name=f"{candidate['name']}_profile.pdf",
            mimetype='application/pdf'
        )
        
    except Exception as e:
        app.logger.error(f"PDF Export Error: {str(e)}")
        app.logger.error(traceback.format_exc())
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
    
    # Pipeline counts
    pipeline = {
        'new': 0,
        'screening': 0,
        'interview': 0,
        'offer': 0,
        'hired': 0,
        'rejected': 0
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
        status = candidate.get('employment_status', 'new')
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
        
        # Skills
        skills = json.loads(candidate.get('core_skills', '[]'))
        for skill in skills:
            skill_name = skill.get('skill', '').strip()
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
    return send_file(
        file_path,
        as_attachment=False,
        download_name=original_filename,
        mimetype=mimetype
    )
@app.route('/api/check-resume/<int:candidate_id>')
def check_resume(candidate_id):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('SELECT resume_file_path, resume_original_filename FROM candidates WHERE id = ?', (candidate_id,))
    row = c.fetchone()
    conn.close()
    
    if row:
        return jsonify({
            'file_path': row[0],
            'filename': row[1],
            'exists': os.path.exists(row[0]) if row[0] else False
        })
    return jsonify({'error': 'Candidate not found'}), 404

# ============================================
# ✅ CORRECT: No indentation before @app.route
# ============================================
@app.route('/api/debug-db')
def debug_db():
    try:
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        c.execute("PRAGMA table_info(candidates)")
        columns = c.fetchall()
        conn.close()
        return jsonify({
            'columns': [col[1] for col in columns],
            'has_resume_file_path': 'resume_file_path' in [col[1] for col in columns],
            'has_resume_original_filename': 'resume_original_filename' in [col[1] for col in columns]
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
