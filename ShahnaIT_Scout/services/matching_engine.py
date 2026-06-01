# services/matching_engine.py
from difflib import SequenceMatcher

# Skill synonyms for semantic matching
SKILL_SYNONYMS = {
    'python': ['python', 'django', 'flask', 'fastapi', 'pandas', 'numpy', 'jupyter'],
    'java': ['java', 'spring', 'hibernate', 'maven', 'gradle', 'j2ee', 'kotlin'],
    'javascript': ['javascript', 'react', 'angular', 'vue', 'node', 'typescript', 'ecmascript'],
    'aws': ['aws', 'ec2', 's3', 'lambda', 'cloudformation', 'terraform', 'amazon web services'],
    'database': ['sql', 'mysql', 'postgresql', 'mongodb', 'oracle', 'nosql', 'dynamodb'],
    'docker': ['docker', 'container', 'kubernetes', 'k8s', 'devops', 'podman'],
    'react': ['react', 'redux', 'hooks', 'jsx', 'frontend', 'next.js'],
    'nodejs': ['node', 'express', 'npm', 'backend', 'api', 'rest api'],
    'machine learning': ['machine learning', 'ml', 'ai', 'artificial intelligence', 'tensorflow', 'pytorch'],
    'data science': ['data science', 'analytics', 'statistics', 'data analysis', 'big data']
}

def calculate_match_score(job_skills, candidate_skills):
    if not job_skills or not candidate_skills:
        return 0, {'exact_matches': [], 'partial_matches': [], 'missing_skills': [], 'semantic_matches': []}
    
    job_list = [s.strip().lower() for s in job_skills.split(',') if s.strip()]
    cand_list = [s.strip().lower() for s in candidate_skills.split(',') if s.strip()]
    
    if not job_list:
        return 0, {'exact_matches': [], 'partial_matches': [], 'missing_skills': job_list, 'semantic_matches': []}
    
    match_details = {
        'exact_matches': [],
        'partial_matches': [],
        'missing_skills': [],
        'semantic_matches': []
    }
    
    total_score = 0
    
    for job_skill in job_list:
        best_match = 0
        
        for cand_skill in cand_list:
            if job_skill == cand_skill:
                best_match = 100
                match_details['exact_matches'].append(job_skill)
                break
            elif job_skill in cand_skill or cand_skill in job_skill:
                best_match = 70
                if job_skill not in match_details['partial_matches']:
                    match_details['partial_matches'].append(job_skill)
                break
            else:
                semantic_score = check_semantic_match(job_skill, cand_skill)
                if semantic_score > best_match and semantic_score > 40:
                    best_match = semantic_score
                    match_details['semantic_matches'].append(f"{job_skill} to {cand_skill}")
                else:
                    similarity = SequenceMatcher(None, job_skill, cand_skill).ratio() * 100
                    if similarity > best_match and similarity > 30:
                        best_match = similarity
        
        if best_match == 0:
            match_details['missing_skills'].append(job_skill)
        
        total_score += best_match
    
    final_score = round(total_score / len(job_list), 2)
    ai_bonus = min(10, len(match_details['semantic_matches']) * 2)
    final_score = min(100, final_score + ai_bonus)
    
    return final_score, match_details

def check_semantic_match(job_skill, cand_skill):
    for key, synonyms in SKILL_SYNONYMS.items():
        if job_skill == key:
            if cand_skill in synonyms:
                return 50
        elif job_skill in synonyms:
            if cand_skill == key or cand_skill in synonyms:
                return 50
    return 0

def get_match_summary(match_score, match_details):
    if match_score >= 85:
        level = "Excellent Match"
        color = "success"
    elif match_score >= 70:
        level = "Good Match"
        color = "primary"
    elif match_score >= 50:
        level = "Potential Match"
        color = "warning"
    else:
        level = "Low Match"
        color = "secondary"
    
    return {
        'level': level,
        'color': color,
        'score': match_score,
        'exact_matches': len(match_details.get('exact_matches', [])),
        'partial_matches': len(match_details.get('partial_matches', [])),
        'semantic_matches': len(match_details.get('semantic_matches', [])),
        'missing_skills': match_details.get('missing_skills', [])[:5]
    }

def rank_candidates(job_skills, candidates_list):
    ranked = []
    for candidate in candidates_list:
        candidate_skills = candidate.get('skills', '')
        score, details = calculate_match_score(job_skills, candidate_skills)
        ranked.append({
            'candidate_id': candidate.get('id'),
            'candidate_name': candidate.get('name'),
            'candidate_email': candidate.get('email'),
            'match_score': score,
            'match_summary': get_match_summary(score, details)
        })
    ranked.sort(key=lambda x: x['match_score'], reverse=True)
    return ranked

def suggest_skills(candidate_skills, target_job_skills):
    if not candidate_skills or not target_job_skills:
        return []
    
    cand_list = [s.strip().lower() for s in candidate_skills.split(',') if s.strip()]
    job_list = [s.strip().lower() for s in target_job_skills.split(',') if s.strip()]
    missing = [s for s in job_list if s not in cand_list]
    
    suggestions = []
    for skill in missing:
        found = False
        for key, synonyms in SKILL_SYNONYMS.items():
            if skill == key:
                suggestions.append(f"Learn {skill} or related: {', '.join(synonyms[:3])}")
                found = True
                break
            elif skill in synonyms:
                suggestions.append(f"Consider learning {key} (related to {skill})")
                found = True
                break
        if not found:
            suggestions.append(f"Add {skill} to your skillset")
    
    return suggestions[:5]
