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
        .spinner { border: 3px solid #f3f3f3; border-top: 3px solid #1A4D4A; border-radius: 50%; width: 30px; height: 30px; animation: spin 1s linear infinite; margin: 10px auto; }
        @keyframes spin { 0% { transform: rotate(0deg); } 100% { transform: rotate(360deg); } }
        .flex { display: flex; gap: 10px; flex-wrap: wrap; }
        .flex-1 { flex: 1; }
        .modal { display: none; position: fixed; z-index: 1000; left: 0; top: 0; width: 100%; height: 100%; background: rgba(0,0,0,0.5); }
        .modal-content { background: #F5F0E8; margin: 50px auto; border-radius: 10px; max-width: 700px; width: 90%; }
        .modal-header { background: #1A4D4A; color: white; padding: 15px; border-radius: 10px 10px 0 0; display: flex; justify-content: space-between; }
        .close { cursor: pointer; font-size: 24px; }
        .detail-row { margin-bottom: 10px; display: flex; border-bottom: 1px solid #ddd; padding-bottom: 5px; }
        .detail-label { width: 130px; font-weight: bold; }
        .detail-value { flex: 1; }
    </style>
</head>
<body>
<div style="max-width: 1200px; margin: 0 auto;">
    <div class="header">
        <h1>🎯 ShahnaIT Scout</h1>
        <p>AI-Powered Recruitment Platform</p>
    </div>
    
    <div style="text-align: center; margin: 20px 0;">
        <button class="tab-btn active" onclick="loadJobs()">📋 Jobs</button>
        <button class="tab-btn" onclick="loadCandidates()">👥 Candidates</button>
        <button class="tab-btn" onclick="alert('Upload functionality')">📤 Upload Resume</button>
    </div>
    
    <div id="content"></div>
</div>

<script>
    function loadJobs() {
        fetch('/api/jobs')
            .then(r => r.json())
            .then(jobs => {
                document.getElementById('content').innerHTML = jobs.length > 0 
                    ? '<div class="card">' + jobs.map(j => `<h3>${j.title}</h3>`).join('') + '</div>'
                    : '<div class="card">No jobs found</div>';
            });
    }
    
    function loadCandidates() {
        fetch('/api/candidates')
            .then(r => r.json())
            .then(candidates => {
                document.getElementById('content').innerHTML = candidates.length > 0 
                    ? '<div class="card">' + candidates.map(c => `<h3>${c.first_name} ${c.last_name}</h3>`).join('') + '</div>'
                    : '<div class="card">No candidates found</div>';
            });
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
    return jsonify({'message': 'Candidate saved', 'id': candidate_id})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
