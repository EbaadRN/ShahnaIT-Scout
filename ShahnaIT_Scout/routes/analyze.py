# routes/analyze.py
import json
from flask import Blueprint, request, jsonify
from services.groq_service import analyze_match_with_groq, GROQ_ENABLED
from models.database import update_candidate_match

analyze_bp = Blueprint('analyze', __name__)

@analyze_bp.route('/analyze-match', methods=['POST'])
def analyze():
    data = request.json
    resume_text = data.get('resume_text', '')
    jd_text = data.get('jd_text', '')
    candidate_id = data.get('candidate_id')
    
    if not resume_text or not jd_text:
        return jsonify({'error': 'Missing text'}), 400
    
    if not GROQ_ENABLED:
        return jsonify({'error': 'Groq API not configured'}), 503
    
    result = analyze_match_with_groq(resume_text, jd_text)
    
    if result and candidate_id:
        detailed_json = json.dumps(result, indent=2)
        update_candidate_match(candidate_id, result.get('match_score', 0), 
                              result.get('recommendation', 'review'), detailed_json)
        return jsonify(result)
    elif result:
        return jsonify(result)
    
    return jsonify({'error': 'Analysis failed'}), 500
