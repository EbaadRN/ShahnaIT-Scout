# routes/pipeline.py
# Kanban pipeline routes

from flask import jsonify, request
from datetime import datetime

# Global references
applications = []
candidates = []
jobs = []

# Pipeline stages
PIPELINE_STAGES = [
    {'id': 'new', 'name': '📋 New', 'color': '#6c757d', 'order': 1},
    {'id': 'screening', 'name': '🔍 Screening', 'color': '#17a2b8', 'order': 2},
    {'id': 'shortlisted', 'name': '⭐ Shortlisted', 'color': '#28a745', 'order': 3},
    {'id': 'interview', 'name': '🎯 Interview', 'color': '#007bff', 'order': 4},
    {'id': 'technical', 'name': '💻 Technical', 'color': '#fd7e14', 'order': 5},
    {'id': 'hr', 'name': '🤝 HR Round', 'color': '#6f42c1', 'order': 6},
    {'id': 'offer', 'name': '📄 Offer', 'color': '#20c997', 'order': 7},
    {'id': 'hired', 'name': '✅ Hired', 'color': '#28a745', 'order': 8},
    {'id': 'rejected', 'name': '❌ Rejected', 'color': '#dc3545', 'order': 9}
]

def init_pipeline_routes(app, applications_ref, candidates_ref, jobs_ref, matching_engine):
    """Initialize pipeline routes with references to data stores"""
    global applications, candidates, jobs
    applications = applications_ref
    candidates = candidates_ref
    jobs = jobs_ref
    
    @app.route('/api/pipeline/stages', methods=['GET'])
    def get_pipeline_stages():
        """Get all pipeline stages for kanban board"""
        return jsonify(PIPELINE_STAGES)
    
    @app.route('/api/pipeline/candidates', methods=['GET'])
    def get_pipeline_candidates():
        """Get candidates organized by pipeline stage"""
        candidate_stage_map = {}
        application_details = {}
        
        for app in applications:
            candidate_id = app.get('candidate_id')
            candidate_stage_map[candidate_id] = app.get('status', 'new')
            application_details[candidate_id] = {
                'application_id': app.get('id'),
                'match_score': app.get('match_score'),
                'applied_date': app.get('application_date')
            }
        
        pipeline_data = {}
        for stage in PIPELINE_STAGES:
            stage_id = stage['id']
            pipeline_data[stage_id] = []
            
            for candidate in candidates:
                current_stage = candidate_stage_map.get(candidate['id'])
                app_detail = application_details.get(candidate['id'], {})
                
                candidate_info = {
                    'id': candidate['id'],
                    'code': candidate.get('code'),
                    'name': candidate.get('name'),
                    'email': candidate.get('email'),
                    'skills': candidate.get('skills', ''),
                    'current_company': candidate.get('current_company', ''),
                    'current_designation': candidate.get('current_designation', ''),
                    'total_experience': candidate.get('total_experience', 0),
                    'match_score': app_detail.get('match_score'),
                    'application_id': app_detail.get('application_id')
                }
                
                if current_stage is None and stage_id == 'new':
                    pipeline_data[stage_id].append(candidate_info)
                elif current_stage == stage_id:
                    pipeline_data[stage_id].append(candidate_info)
        
        return jsonify(pipeline_data)
    
    @app.route('/api/pipeline/move', methods=['PUT'])
    def move_pipeline_candidate():
        """Move a candidate to a different pipeline stage"""
        data = request.json
        candidate_id = data.get('candidate_id')
        new_stage = data.get('new_stage')
        jd_id = data.get('jd_id')
        
        # Find existing application
        for app in applications:
            if app.get('candidate_id') == candidate_id:
                old_stage = app['status']
                app['status'] = new_stage
                app['updated_at'] = datetime.now().isoformat()
                return jsonify({
                    'success': True,
                    'message': f'Moved from {old_stage} to {new_stage}',
                    'old_stage': old_stage,
                    'new_stage': new_stage
                })
        
        # Create new application if none exists
        job = None
        if jd_id:
            job = next((j for j in jobs if j['id'] == jd_id), None)
        if not job:
            job = next((j for j in jobs if j.get('status') == 'open'), jobs[0] if jobs else None)
        
        if job:
            candidate = next((c for c in candidates if c['id'] == candidate_id), None)
            if candidate:
                match_score, _ = matching_engine.calculate_match_score(
                    job.get('skills_required', ''),
                    candidate.get('skills', '')
                )
                
                new_application = {
                    'id': len(applications) + 1,
                    'application_code': f"APP-{len(applications) + 1:04d}",
                    'candidate_id': candidate_id,
                    'jd_id': job['id'],
                    'job_title': job['title'],
                    'candidate_name': candidate['name'],
                    'match_score': match_score,
                    'status': new_stage,
                    'application_date': datetime.now().date().isoformat(),
                    'created_at': datetime.now().isoformat(),
                    'updated_at': datetime.now().isoformat()
                }
                applications.append(new_application)
                job['applications'] = job.get('applications', 0) + 1
                
                return jsonify({
                    'success': True,
                    'message': f'Candidate moved to {new_stage}',
                    'new_stage': new_stage,
                    'match_score': match_score
                })
        
        return jsonify({'success': False, 'error': 'No open jobs available'}), 400
