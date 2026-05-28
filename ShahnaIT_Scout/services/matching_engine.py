# services/matching_engine.py
# AI-powered candidate-job matching

from difflib import SequenceMatcher

# Skill synonyms for semantic matching
SKILL_SYNONYMS = {
    'python': ['python', 'django', 'flask', 'fastapi', 'pandas', 'numpy'],
    'java': ['java', 'spring', 'hibernate', 'maven', 'gradle'],
    'javascript': ['javascript', 'react', 'angular', 'vue', 'node', 'typescript'],
    'aws': ['aws', 'ec2', 's3', 'lambda', 'cloudformation', 'terraform'],
    'database': ['sql', 'mysql', 'postgresql', 'mongodb', 'oracle', 'nosql'],
    'docker': ['docker', 'container', 'kubernetes', 'k8s', 'devops'],
    'react': ['react', 'redux', 'hooks', 'jsx', 'frontend'],
    'nodejs': ['node', 'express', 'npm', 'backend', 'api'],
    'machine learning': ['machine learning', 'ml', 'ai', 'tensorflow', 'pytorch'],
    'data science': ['data science', 'analytics', 'statistics', 'big data']
}


def calculate_match_score(job_skills, candidate_skills):
    """
    Calculate match percentage between job requirements and candidate skills
    Returns: (match_score, match_details)
    """
    if not job_skills or not candidate_skills:
        return 0, {'exact_matches': [], 'partial_matches': [], 'missing_skills': [], 'semantic_matches': []}
    
    # Parse skills into lists
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
        best_match_name = None
        
        for cand_skill in cand_list:
            # Exact match (100 points)
            if job_skill == cand_skill:
                best_match = 100
                best_match_name = cand_skill
                match_details['exact_matches'].append(job_skill)
                break
            
            # Partial match (70 points)
            elif job_skill in cand_skill or cand_skill in job_skill:
                best_match = 70
                best_match_name = cand_skill
                if job_skill not in match_details['partial_matches']:
                    match_details['partial_matches'].append(job_skill)
                break
            
            # Semantic match (50 points)
            else:
                semantic_score = check_semantic_match(job_skill, cand_skill)
                if semantic_score > best_match and semantic_score > 40:
                    best_match = semantic_score
                    best_match_name = cand_skill
                    match_details['semantic_matches'].append(f"{job_skill} → {cand_skill}")
                
                # Sequence similarity (30-60 points)
                else:
                    similarity = SequenceMatcher(None, job_skill, cand_skill).ratio() * 100
                    if similarity > best_match and similarity > 30:
                        best_match = similarity
                        best_match_name = cand_skill
        
        if best_match == 0:
            match_details['missing_skills'].append(job_skill)
        
        total_score += best_match
    
    # Calculate final score
    final_score = round(total_score / len(job_list), 2)
    
    # AI bonus: add up to 10% for semantic matches
    ai_bonus = min(10, len(match_details['semantic_matches']) * 2)
    final_score = min(100, final_score + ai_bonus)
    
    return final_score, match_details


def check_semantic_match(job_skill, cand_skill):
    """Check if two skills are semantically related"""
    for key, synonyms in SKILL_SYNONYMS.items():
        if job_skill == key:
            if cand_skill in synonyms:
                return 50
        elif job_skill in synonyms:
            if cand_skill == key or cand_skill in synonyms:
                return 50
    return 0


def get_match_summary(match_score, match_details):
    """Generate a human-readable summary of the match"""
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
    
    summary = {
        'level': level,
        'color': color,
        'score': match_score,
        'exact_matches': len(match_details.get('exact_matches', [])),
        'partial_matches': len(match_details.get('partial_matches', [])),
        'semantic_matches': len(match_details.get('semantic_matches', [])),
        'missing_skills': match_details.get('missing_skills', [])[:5]
    }
    
    return summary


def rank_candidates(job_skills, candidates_list):
    """Rank candidates by match score for a given job"""
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
    
    # Sort by score descending
    ranked.sort(key=lambda x: x['match_score'], reverse=True)
    
    return ranked


def suggest_skills_for_candidate(candidate_skills, target_job_skills):
    """Suggest skills a candidate should learn to improve match score"""
    if not candidate_skills or not target_job_skills:
        return []
    
    cand_list = [s.strip().lower() for s in candidate_skills.split(',') if s.strip()]
    job_list = [s.strip().lower() for s in target_job_skills.split(',') if s.strip()]
    
    missing = [s for s in job_list if s not in cand_list]
    
    # Check for semantic matches to suggest related skills
    suggestions = []
    for skill in missing:
        for key, synonyms in SKILL_SYNONYMS.items():
            if skill == key:
                suggestions.append(f"Learn {skill} or related: {', '.join(synonyms[:3])}")
                break
            elif skill in synonyms:
                suggestions.append(f"Consider learning {key} (related to {skill})")
                break
        else:
            suggestions.append(f"Add {skill} to your skillset")
    
    return suggestions[:5]
