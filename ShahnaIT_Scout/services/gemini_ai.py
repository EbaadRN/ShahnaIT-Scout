import os
import json
import re

GEMINI_AVAILABLE = False
gemini_model = None

try:
    import google.generativeai as genai
    GEMINI_API_KEY = os.environ.get('GEMINI_API_KEY', '')
    if GEMINI_API_KEY:
        genai.configure(api_key=GEMINI_API_KEY)
        gemini_model = genai.GenerativeModel('gemini-pro')
        GEMINI_AVAILABLE = True
        print("Gemini AI initialized")
    else:
        print("Gemini AI: No API key")
except Exception as e:
    print(f"Gemini AI error: {e}")

def is_available():
    return GEMINI_AVAILABLE

def parse_resume_with_gemini(resume_text):
    if not GEMINI_AVAILABLE:
        return None
    try:
        prompt = 'Extract from resume. Return JSON only. Keys: first_name, last_name, email, phone, address, linkedin_url, current_role, notice_period, employment_status, work_history (array with company,role,duration_from,duration_to), certifications (array), top_skills (array of 5). Use null if missing. Resume: ' + resume_text[:3000]
        response = gemini_model.generate_content(prompt)
        text = response.text
        text = text.replace('```json', '').replace('```', '').strip()
        return json.loads(text)
    except Exception as e:
        print(f"Parse error: {e}")
        return None

def parse_jd_with_gemini(jd_text):
    if not GEMINI_AVAILABLE:
        return None
    try:
        prompt = 'Extract from job description. Return JSON only. Keys: job_title, experience_min, experience_max, budget_min, budget_max, work_location, work_location_city, responsibilities (array), mandatory_skills (array), preferred_skills (array), good_to_have_skills (array), education_qualification, work_timings, number_of_openings. Use null if missing. JD: ' + jd_text[:3000]
        response = gemini_model.generate_content(prompt)
        text = response.text
        text = text.replace('```json', '').replace('```', '').strip()
        return json.loads(text)
    except Exception as e:
        print(f"JD error: {e}")
        return None

def analyze_profile_with_gemini(candidate_data, job_data):
    if not GEMINI_AVAILABLE:
        return None
    try:
        candidate_str = json.dumps(candidate_data)
        job_str = json.dumps(job_data)
        prompt = 'Analyze candidate against job. Return JSON only. Keys: relevance_score, relevance_reason, genuineness_score, genuineness_reason, strengths (array), weaknesses (array), recommendation. Candidate: ' + candidate_str + ' Job: ' + job_str
        response = gemini_model.generate_content(prompt)
        text = response.text
        text = text.replace('```json', '').replace('```', '').strip()
        return json.loads(text)
    except Exception as e:
        print(f"Analysis error: {e}")
        return None
