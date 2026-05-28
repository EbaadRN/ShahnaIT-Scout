# routes/ai_tools.py
# AI-powered tools routes (Gemini integration)

from flask import jsonify, request

# Global references
gemini_ai = None
resume_parser = None

def init_ai_tools_routes(app, gemini_ai_module, resume_parser_module):
    """Initialize AI tools routes with references"""
    global gemini_ai, resume_parser
    gemini_ai = gemini_ai_module
    resume_parser = resume_parser_module
    
    @app.route('/api/ai/generate-jd', methods=['POST'])
    def ai_generate_jd():
        """Generate job description using AI"""
        data = request.json
        keywords = data.get('keywords', '')
        context = data.get('context', '')
        
        if not keywords:
            return jsonify({'error': 'Keywords are required'}), 400
        
        jd = gemini_ai.generate_job_description(keywords, context)
        return jsonify({'success': True, 'jd': jd})
    
    @app.route('/api/ai/generate-questions', methods=['POST'])
    def ai_generate_questions():
        """Generate interview questions using AI"""
        data = request.json
        role = data.get('role', '')
        level = data.get('level', 'mid')
        
        if not role:
            return jsonify({'error': 'Role is required'}), 400
        
        questions = gemini_ai.generate_interview_questions(role, level)
        return jsonify({'success': True, 'questions': questions})
    
    @app.route('/api/ai/generate-email', methods=['POST'])
    def ai_generate_email():
        """Generate professional email using AI"""
        data = request.json
        email_type = data.get('type', 'followup')
        candidate_name = data.get('candidate_name', 'Candidate')
        job_title = data.get('job_title', 'the position')
        
        email = gemini_ai.generate_email(email_type, candidate_name, job_title)
        return jsonify({'success': True, 'email': email})
    
    @app.route('/api/ai/parse-resume', methods=['POST'])
    def ai_parse_resume():
        """Parse resume using AI"""
        if 'file' not in request.files:
            return jsonify({'error': 'No file uploaded'}), 400
        
        file = request.files['file']
        
        # Use AI parser if available, fallback to basic
        if gemini_ai.GEMINI_AVAILABLE:
            text = resume_parser.extract_text_from_resume(file)
            if text:
                ai_data = gemini_ai.parse_resume_with_ai(text)
                if ai_data:
                    return jsonify({'success': True, 'data': ai_data, 'ai_used': True})
        
        # Fallback to basic parsing
        parsed_data = resume_parser.parse_resume(file, use_ai=False, ai_parser=None)
        return jsonify({'success': True, 'data': parsed_data, 'ai_used': False})
    
    @app.route('/api/ai/status', methods=['GET'])
    def ai_status():
        """Check if AI services are available"""
        return jsonify({
            'gemini_available': gemini_ai.GEMINI_AVAILABLE,
            'api_key_configured': bool(gemini_ai.GEMINI_API_KEY) if hasattr(gemini_ai, 'GEMINI_API_KEY') else False
        })
