# services/gemini_ai.py
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
        print("✅ Gemini AI initialized")
    else:
        print("⚠️ Gemini AI: No API key found")
except ImportError:
    print("⚠️ Gemini AI: google-generativeai not installed")
except Exception as e:
    print(f"⚠️ Gemini AI error: {e}")

def is_available():
    return GEMINI_AVAILABLE

def parse_resume_with_gemini(resume_text):
    if not GEMINI_AVAILABLE:
        return None
    try:
        prompt = f"""Extract information from this resume. Return ONLY valid JSON.

Resume text:
{resume_text[:3500]}

Return JSON with these exact keys:
- first_name
- last_name
- email
- phone
- address
- linkedin_url
- current_role
- notice_period (number of days, or null)
- employment_status (working/bench/notice_period)
- work_history (array of objects with: company, role, duration_from, duration_to)
- certifications (array of strings)
- top_skills (array of 5 strings, each as "skill: years")

Use null or empty array if information not found."""
        
        response = gemini_model.generate_content(prompt)
        json_str = response.text.replace('```json', '').replace('```', '').strip()
        return json.loads(json_str)
    except Exception as e:
        print(f"Gemini parsing error: {e}")
        return None

def parse_jd_with_gemini(jd_text):
    if not GEMINI_AVAILABLE:
        return None
    try:
        prompt = f"""Extract information from this job description. Return ONLY valid JSON.

JD text:
{jd_text[:3500]}

Return JSON with these exact keys:
- job_title
- experience_min (number)
- experience_max (number)
- budget_min (number, or null)
- budget_max (number, or null)
- work_location (Remote/Hybrid/Onsite)
- work_location_city
- responsibilities (array of strings)
- mandatory_skills (array of strings)
- preferred_skills (array of strings)
- good_to_have_skills (array of strings)
- education_qualification
- work_timings
- number_of_openings (number)

Use null or empty array if not found."""
        
        response = gemini_model.generate_content(prompt)
        json_str = response.text.replace('```json', '').replace('```', '').strip()
        return json.loads(json_str)
    except Exception as e:
        print(f"Gemini JD error: {e}")
        return None

def analyze_profile_with_gemini(candidate_data, job_data):
    if not GEMINI_AVAILABLE:
        return None
    try:
        prompt = f"""Analyze this candidate against the job requirement. Return ONLY valid JSON.

CANDIDATE:
- Name: {candidate_data.get('name', '')}
- Current Role: {candidate_data.get('current_role', '')}
- Skills: {candidate_data.get('skills', '')}
- Experience: {candidate_data.get('total_experience', 0)} years
- Work History: {candidate_data.get('work_history', [])}

JOB:
- Title: {job_data.get('title', '')}
- Required Skills: {job_data.get('skills_required', '')}
- Experience Needed: {job_data.get('experience_min', 0)}-{job_data.get('experience_max', 10)} years

Return JSON:
{{
    "relevance_score": 0-100,
    "relevance_reason": "brief explanation",
    "genuineness_score": 0-100,
    "genuineness_reason": "brief explanation",
    "strengths": ["strength1", "strength2"],
    "weaknesses": ["weakness1", "weakness2"],
    "recommendation": "Hire/Interview/Reject"
}}"""
        
        response = gemini_model.generate_content(prompt)
        json_str = response.text.replace('```json', '').replace('```', '').strip()
        return json.loads(json_str)
    except Exception as e:
        print(f"Analysis error: {e}")
        return None
