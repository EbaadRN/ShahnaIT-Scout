# services/resume_parser.py
# Extract data from resumes (PDF, DOCX, TXT)

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
    """Extract text from any supported file type"""
    filename = file.filename.lower()
    
    if filename.endswith('.pdf'):
        return extract_text_from_pdf(file)
    elif filename.endswith('.docx'):
        return extract_text_from_docx(file)
    else:
        return extract_text_from_txt(file)

def extract_name(text):
    """Extract candidate name from resume text"""
    lines = text.split('\n')[:15]
    for line in lines:
        line = line.strip()
        if len(line.split()) == 2 and not any(x in line.lower() for x in ['resume', 'email', 'phone']):
            parts = line.split()
            if len(parts) == 2 and parts[0][0].isupper() and parts[1][0].isupper():
                return parts[0], parts[1]
    
    name_match = re.search(r'Name[:\s]+([A-Z][a-z]+)\s+([A-Z][a-z]+)', text, re.IGNORECASE)
    if name_match:
        return name_match.group(1), name_match.group(2)
    
    return None, None

def extract_email(text):
    """Extract email address"""
    pattern = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
    match = re.search(pattern, text)
    return match.group(0) if match else None

def extract_phone(text):
    """Extract phone number"""
    patterns = [
        r'\b\d{10}\b',
        r'\+\d{1,2}[-.\s]?\d{10}\b',
        r'\b\d{3}[-.]?\d{3}[-.]?\d{4}\b'
    ]
    for pattern in patterns:
        match = re.search(pattern, text)
        if match:
            return match.group(0)
    return None

def extract_skills(text):
    """Extract technical skills from resume"""
    skill_database = [
        'Python', 'Java', 'JavaScript', 'React', 'Angular', 'Vue', 'Node.js',
        'Django', 'Flask', 'Spring', 'AWS', 'Azure', 'GCP', 'Docker', 'Kubernetes',
        'MySQL', 'PostgreSQL', 'MongoDB', 'Git', 'Machine Learning', 'Data Science',
        'Project Management', 'Agile', 'Scrum', 'Leadership', 'Communication'
    ]
    found = []
    text_lower = text.lower()
    for skill in skill_database:
        if skill.lower() in text_lower:
            found.append(skill)
    return found

def extract_experience(text):
    """Extract years of experience"""
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

def extract_location(text):
    """Extract location from resume"""
    cities = ['Bangalore', 'Mumbai', 'Delhi', 'Hyderabad', 'Chennai', 'Pune', 
              'Kolkata', 'Ahmedabad', 'Remote', 'Gurgaon', 'Noida']
    for city in cities:
        if city.lower() in text.lower():
            return city
    
    pattern = r'Location\s*:?\s*([^\n]+)'
    match = re.search(pattern, text, re.IGNORECASE)
    return match.group(1).strip() if match else None

def extract_designation(text):
    """Extract current designation/job title"""
    lines = text.split('\n')[:20]
    titles = ['Developer', 'Engineer', 'Manager', 'Lead', 'Architect', 
              'Analyst', 'Consultant', 'Specialist']
    for line in lines:
        for title in titles:
            if title.lower() in line.lower():
                words = line.strip().split()
                if len(words) <= 6:
                    return line.strip()
                for i, word in enumerate(words):
                    if title.lower() in word.lower():
                        start = max(0, i - 2)
                        end = min(len(words), i + 3)
                        return ' '.join(words[start:end])
    return None

def parse_resume(file, use_ai=True, ai_parser=None):
    """Main function to parse resume and extract all data"""
    # Extract text from file
    text = extract_text_from_resume(file)
    
    if not text:
        return None
    
    # Try AI parsing first if available
    if use_ai and ai_parser:
        ai_data = ai_parser(text)
        if ai_data:
            return ai_data
    
    # Fallback to basic extraction
    first_name, last_name = extract_name(text)
    
    return {
        'first_name': first_name,
        'last_name': last_name,
        'email': extract_email(text),
        'phone': extract_phone(text),
        'skills': extract_skills(text),
        'total_experience': extract_experience(text),
        'current_location': extract_location(text),
        'current_designation': extract_designation(text),
        'resume_text_preview': text[:500] + '...' if len(text) > 500 else text
    }
