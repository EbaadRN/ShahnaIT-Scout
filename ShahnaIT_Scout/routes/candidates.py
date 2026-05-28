# routes/candidates.py
# Candidate management routes

from flask import jsonify, request
from datetime import datetime
import json
import base64
import csv
import io

# Global references
candidates = []
next_id = 1
applications = []

def init_candidates_routes(app, candidates_ref, next_id_ref, applications_ref, resume_parser, matching_engine):
    """Initialize candidates routes with references to data stores"""
    global candidates, next_id, applications
    candidates = candidates_ref
    next_id = next_id_ref
    applications = applications_ref
    
    def generate_candidate_code():
        global next_id
        code = f"CAN-{next_id:04d}"
        next_id += 1
        return code
    
    @app.route('/api/candidates', methods=['GET', 'POST'])
    def manage_candidates():
        global candidates, next_id
        
        if request.method == 'POST':
            data = request.get_json()
            
            # Check for duplicate email
            existing = next((c for c in candidates if c.get('email') == data.get('email')), None)
            if existing:
                return jsonify({'error': 'Candidate already exists', 'candidate_id': existing['id']}), 409
            
            candidate = {
                'id': len(candidates) + 1,
                'code': generate_candidate_code(),
                'first_name': data.get('first_name', ''),
                'last_name': data.get('last_name', ''),
                'name': f"{data.get('first_name', '')} {data.get('last_name', '')}".strip(),
                'email': data.get('email', ''),
                'phone': data.get('phone', ''),
                'skills': data.get('skills', ''),
                'current_company': data.get('current_company', ''),
                'current_designation': data.get('current_designation', ''),
                'total_experience': data.get('total_experience', 0),
                'current_location': data.get('current_location', ''),
                'source': data.get('source', 'manual'),
                'created_at': datetime.now().isoformat()
            }
            candidates.append(candidate)
            return jsonify({'success': True, 'candidate_id': candidate['id'], 'candidate_code': candidate['code']})
        
        # GET request with pagination
        page = int(request.args.get('page', 1))
        per_page = int(request.args.get('per_page', 20))
        search = request.args.get('search', '')
        source = request.args.get('source', '')
        
        filtered = candidates.copy()
        
        if search:
            filtered = [c for c in filtered if search.lower() in c.get('name', '').lower() or search.lower() in c.get('email', '').lower() or search.lower() in c.get('skills', '').lower()]
        if source:
            filtered = [c for c in filtered if c.get('source') == source]
        
        start = (page - 1) * per_page
        end = start + per_page
        paginated = filtered[start:end]
        
        return jsonify({
            'candidates': paginated,
            'total': len(filtered),
            'page': page,
            'pages': (len(filtered) + per_page - 1) // per_page
        })
    
    @app.route('/api/candidates/parse-resume', methods=['POST'])
    def parse_resume():
        """Parse uploaded resume file"""
        if 'file' not in request.files:
            return jsonify({'error': 'No file uploaded'}), 400
        
        file = request.files['file']
        parsed_data = resume_parser.parse_resume(file, use_ai=True, ai_parser=None)
        
        if parsed_data:
            return jsonify({'success': True, 'data': parsed_data})
        return jsonify({'error': 'Could not parse resume'}), 400
    
    @app.route('/api/candidates/bulk-import', methods=['POST'])
    def bulk_import_candidates():
        """Import candidates from CSV file"""
        if 'file' not in request.files:
            return jsonify({'error': 'No file uploaded'}), 400
        
        global next_id
        file = request.files['file']
        
        try:
            content = file.read().decode('utf-8')
            csv_reader = csv.DictReader(io.StringIO(content))
        except Exception as e:
            return jsonify({'error': f'Invalid CSV: {str(e)}'}), 400
        
        imported = 0
        for row in csv_reader:
            name = row.get('Name', row.get('name', '')).strip()
            first_name = name.split()[0] if name else ''
            last_name = ' '.join(name.split()[1:]) if len(name.split()) > 1 else ''
            
            candidate = {
                'id': len(candidates) + 1,
                'code': generate_candidate_code(),
                'first_name': first_name,
                'last_name': last_name,
                'name': name,
                'email': row.get('Email', row.get('email', '')),
                'phone': row.get('Phone', row.get('phone', '')),
                'skills': row.get('Skills', row.get('skills', '')),
                'source': 'csv_import',
                'created_at': datetime.now().isoformat()
            }
            candidates.append(candidate)
            imported += 1
        
        return jsonify({'success': True, 'imported': imported})
    
    @app.route('/api/candidates/<int:candidate_id>/match/<int:jd_id>', methods=['GET'])
    def get_candidate_job_match(candidate_id, jd_id):
        """Get match score between candidate and job"""
        global candidates, jobs
        
        candidate = next((c for c in candidates if c['id'] == candidate_id), None)
        job = next((j for j in jobs if j['id'] == jd_id), None)
        
        if not candidate or not job:
            return jsonify({'error': 'Candidate or job not found'}), 404
        
        score, details = matching_engine.calculate_match_score(
            job.get('skills_required', ''),
            candidate.get('skills', '')
        )
        
        return jsonify({
            'candidate_id': candidate_id,
            'candidate_name': candidate.get('name'),
            'job_id': jd_id,
            'job_title': job.get('title'),
            'match_score': score,
            'match_details': details
        })
