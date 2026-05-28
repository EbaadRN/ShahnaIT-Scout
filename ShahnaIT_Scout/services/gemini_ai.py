# services/gemini_ai.py
# Handles all Gemini AI interactions (FREE)

import os
import re
import json

# Gemini AI setup
GEMINI_AVAILABLE = False
gemini_model = None

try:
    import google.generativeai as genai
    
    GEMINI_API_KEY = os.environ.get('GEMINI_API_KEY', '')
    if GEMINI_API_KEY:
        genai.configure(api_key=GEMINI_API_KEY)
        gemini_model = genai.GenerativeModel('gemini-pro')
        GEMINI_AVAILABLE = True
        print("✅ Gemini AI initialized successfully")
    else:
        print("⚠️ GEMINI_API_KEY not found. AI features disabled.")
except ImportError:
    print("⚠️ google-generativeai not installed. Install with: pip install google-generativeai")
except Exception as e:
    print(f"⚠️ Gemini AI initialization failed: {e}")


def call_gemini(prompt):
    """Call Gemini AI API for text generation"""
    if not GEMINI_AVAILABLE:
        return None
    
    try:
        response = gemini_model.generate_content(prompt)
        return response.text
    except Exception as e:
        print(f"Gemini AI error: {e}")
        return None


def generate_job_description(keywords, context=""):
    """Generate job description using AI"""
    prompt = f"""Generate a professional job description for a {keywords} position.
{context if context else ''}

Include:
- Job Title
- Location
- Key Responsibilities (5-7 points)
- Required Skills
- Qualifications
- Benefits

Make it detailed and professional."""
    
    result = call_gemini(prompt)
    if result:
        return result
    
    # Fallback template
    return f"""Job Title: {keywords}

Location: Remote/Hybrid

Key Responsibilities:
- Develop and maintain software applications
- Collaborate with cross-functional teams
- Write clean, efficient code
- Participate in code reviews
- Troubleshoot and debug issues

Required Skills:
- {keywords} experience
- Strong problem-solving abilities
- Excellent communication skills

Qualifications:
- Bachelor's degree in Computer Science or related field
- 3+ years of relevant experience"""


def generate_interview_questions(role, level="mid"):
    """Generate interview questions using AI"""
    level_map = {
        'entry': 'entry-level (0-2 years)',
        'mid': 'mid-level (3-5 years)',
        'senior': 'senior-level (6+ years)'
    }
    
    prompt = f"""Generate 8 interview questions for a {level_map.get(level, 'mid-level')} {role} position.
Cover technical skills, problem-solving, behavioral, and cultural fit.
Return as a numbered list."""
    
    result = call_gemini(prompt)
    if result:
        return result
    
    # Fallback questions
    return f"""1. Tell me about your experience with {role}.
2. Describe a challenging project you worked on.
3. How do you stay updated with industry trends?
4. Describe a time you had to solve a complex problem.
5. How do you handle feedback and criticism?
6. Tell me about a time you collaborated with difficult team members.
7. Where do you see yourself in 5 years?
8. Why do you want to work with us?"""


def generate_email(email_type, candidate_name, job_title):
    """Generate professional email using AI"""
    prompt = f"""Write a professional {email_type} email to {candidate_name} for the {job_title} position.
Be polite and professional. Include subject line."""
    
    result = call_gemini(prompt)
    if result:
        return result
    
    # Fallback emails
    templates = {
        'interview': f"Subject: Interview Invitation - {job_title}\n\nDear {candidate_name},\n\nWe are pleased to invite you for an interview for the {job_title} position. Please let us know your availability.\n\nBest regards,\nRecruitment Team",
        'rejection': f"Subject: Update on your application - {job_title}\n\nDear {candidate_name},\n\nThank you for your interest. We have decided to move forward with other candidates.\n\nBest regards,\nRecruitment Team",
        'offer': f"Subject: Offer Letter - {job_title}\n\nDear {candidate_name},\n\nWe are pleased to offer you the {job_title} position. Please review the attached offer letter.\n\nBest regards,\nRecruitment Team",
        'followup': f"Subject: Follow-up on your application\n\nDear {candidate_name},\n\nWe wanted to follow up on your application for the {job_title} position. Do you have any questions?\n\nBest regards,\nRecruitment Team"
    }
    return templates.get(email_type, templates['followup'])


def parse_resume_with_ai(resume_text):
    """Parse resume using AI to extract structured data"""
    prompt = f"""Extract the following information from this resume. Return ONLY valid JSON:

Resume text:
{resume_text[:4000]}

Extract and return JSON with:
- first_name
- last_name
- email
- phone
- skills (as array)
- total_experience (as number)
- current_company
- current_designation
- current_location

If a field is not found, use null or empty array."""
    
    result = call_gemini(prompt)
    if result:
        try:
            json_str = re.sub(r'```json\n?|```\n?', '', result)
            return json.loads(json_str)
        except:
            pass
    return None
