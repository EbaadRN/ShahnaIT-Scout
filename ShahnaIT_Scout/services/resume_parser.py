# services/resume_parser.py
import re
import PyPDF2
import docx

def extract_text_from_pdf(file):
    """Extract text from PDF file"""
    text = ""
    try:
        reader = PyPDF2.PdfReader(file)
        for page in reader.pages:
            page_text = page.extract_text()
            if page_text:
                text += page_text + "\n"
    except Exception as e:
        print(f"PDF extraction error: {e}")
    return text

def extract_text_from_docx(file):
    """Extract text from DOCX file"""
    text = ""
    try:
        doc = docx.Document(file)
        for para in doc.paragraphs:
            text += para.text + "\n"
    except Exception as e:
        print(f"DOCX extraction error: {e}")
    return text

def extract_text_from_txt(file):
    """Extract text from TXT file"""
    try:
        return file.read().decode('utf-8')
    except Exception as e:
        print(f"TXT extraction error: {e}")
        return ""

def extract_text_from_resume(file):
    """Extract text from any supported resume file"""
    filename = file.filename.lower()
    file.seek(0)
    
    if filename.endswith('.pdf'):
        return extract_text_from_pdf(file)
    elif filename.endswith('.docx'):
        return extract_text_from_docx(file)
    else:
        return extract_text_from_txt(file)

def extract_name_basic(text):
    """Extract candidate name from resume text (basic fallback)"""
    lines = text.split('\n')
    for line in lines[:10]:
        line = line.strip()
        if line and not any(x in line.lower() for x in ['resume', 'curriculum', 'email', 'phone', 'page']):
            parts = line.split()
            if len(parts) >= 2 and parts[0][0].isupper() and parts[1][0].isupper():
                return parts[0], parts[1] if len(parts) > 1 else ''
    return '', ''

def extract_email_basic(text):
    """Extract email address from text"""
    pattern = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
    match = re.search(pattern, text)
    return match.group(0) if match else ''

def extract_phone_basic(text):
    """Extract phone number from text"""
    patterns = [
        r'\b\d{10}\b',
        r'\+\d{1,2}[-.\s]?\d{10}\b',
        r'\b\d{3}[-.]?\d{3}[-.]?\d{4}\b'
    ]
    for pattern in patterns:
        match = re.search(pattern, text)
        if match:
            return match.group(0)
    return ''

def extract_skills_basic(text):
    """Extract technical skills from text"""
    skill_database = [
        'Python', 'Java', 'JavaScript', 'TypeScript', 'C++', 'C#', 'Go', 'Ruby', 'PHP', 'Swift', 'Kotlin',
        'React', 'Angular', 'Vue', 'Node.js', 'Django', 'Flask', 'Spring', 'Express', 'Rails', 'Laravel',
        'MySQL', 'PostgreSQL', 'MongoDB', 'Redis', 'Oracle', 'SQL Server', 'Cassandra', 'DynamoDB',
        'AWS', 'Azure', 'GCP', 'Docker', 'Kubernetes', 'Terraform', 'Jenkins', 'Git', 'CI/CD',
        'TensorFlow', 'PyTorch', 'Scikit-learn', 'Pandas', 'NumPy', 'Machine Learning', 'Data Science',
        'Leadership', 'Project Management', 'Agile', 'Scrum', 'Communication', 'Teamwork'
    ]
    found = []
    text_lower = text.lower()
    for skill in skill_database:
        if skill.lower() in text_lower:
            found.append(skill)
    return found

def extract_current_role_basic(text):
    """Extract current job role from text"""
    lines = text.split('\n')
    role_keywords = ['developer', 'engineer', 'manager', 'lead', 'architect', 'analyst', 
                     'consultant', 'specialist', 'administrator', 'designer']
    for line in lines[:20]:
        line_lower = line.lower()
        for role in role_keywords:
            if role in line_lower:
                words = line.strip().split()
                if len(words) <= 8:
                    return line.strip()
                for i, word in enumerate(words):
                    if role in word.lower():
                        start = max(0, i - 2)
                        end = min(len(words), i + 3)
                        return ' '.join(words[start:end])
    return ''

def extract_experience_basic(text):
    """Extract total years of experience"""
    patterns = [
        r'(\d+)\s*\+\s*years?',
        r'(\d+)\s*years?\s+of\s+experience',
        r'total\s+experience\s*:?\s*(\d+)',
        r'experience\s*:?\s*(\d+)\s*years?'
    ]
    for pattern in patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            try:
                return float(match.group(1))
            except:
                pass
    return 0

def extract_location_basic(text):
    """Extract location from text"""
    cities = ['Bangalore', 'Mumbai', 'Delhi', 'Hyderabad', 'Chennai', 'Pune', 'Kolkata', 
              'Ahmedabad', 'Remote', 'Gurgaon', 'Noida', 'Lucknow', 'Jaipur', 'Indore']
    for city in cities:
        if city.lower() in text.lower():
            return city
    pattern = r'Location\s*:?\s*([^\n]+)'
    match = re.search(pattern, text, re.IGNORECASE)
    return match.group(1).strip() if match else ''

def parse_resume_basic(file):
    """Complete basic resume parsing (fallback when AI is unavailable)"""
    text = extract_text_from_resume(file)
    
    if not text:
        return None
    
    first_name, last_name = extract_name_basic(text)
    
    return {
        'first_name': first_name,
        'last_name': last_name,
        'email': extract_email_basic(text),
        'phone': extract_phone_basic(text),
        'address': '',
        'linkedin_url': '',
        'current_role': extract_current_role_basic(text),
        'notice_period': None,
        'employment_status': '',
        'work_history': [],
        'certifications': [],
        'top_skills': extract_skills_basic(text)[:5],
        'total_experience': extract_experience_basic(text),
        'current_location': extract_location_basic(text)
    }
