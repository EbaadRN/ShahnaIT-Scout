# services/linkedin_service.py
# LinkedIn profile import and enrichment

import re

def extract_linkedin_username(url):
    """Extract username from LinkedIn profile URL"""
    patterns = [
        r'linkedin\.com/in/([a-zA-Z0-9-]+)',
        r'linkedin\.com/pub/([a-zA-Z0-9-]+)'
    ]
    
    for pattern in patterns:
        match = re.search(pattern, url, re.IGNORECASE)
        if match:
            return match.group(1)
    
    return None


def enrich_from_linkedin(url):
    """
    Enrich candidate data from LinkedIn profile.
    Note: In production, this would call LinkedIn API with OAuth.
    For now, returns simulated data.
    """
    username = extract_linkedin_username(url)
    
    if not username:
        return None
    
    # Simulated enrichment data
    # In production, replace with actual LinkedIn API call
    simulated_data = {
        'first_name': username.capitalize(),
        'last_name': '',
        'email': f"{username}@example.com",
        'linkedin_url': url,
        'skills': ['Leadership', 'Communication', 'Project Management', 'Strategic Planning'],
        'total_experience': 5,
        'current_company': 'Tech Corporation',
        'current_designation': 'Senior Professional',
        'current_location': 'Bangalore',
        'source': 'linkedin',
        'ai_enriched': True
    }
    
    return simulated_data


def validate_linkedin_url(url):
    """Check if a URL is a valid LinkedIn profile URL"""
    if not url:
        return False
    
    patterns = [
        r'^https?:\/\/(www\.)?linkedin\.com\/in\/[a-zA-Z0-9-]+',
        r'^https?:\/\/(www\.)?linkedin\.com\/pub\/[a-zA-Z0-9-]+'
    ]
    
    for pattern in patterns:
        if re.match(pattern, url, re.IGNORECASE):
            return True
    
    return False


def get_profile_preview(username):
    """Get a preview of LinkedIn profile data (simulated)"""
    return {
        'username': username,
        'profile_url': f"https://linkedin.com/in/{username}",
        'exists': True,
        'public_profile': True
    }
