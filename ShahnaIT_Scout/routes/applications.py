# routes/applications.py
# Application management routes

from flask import jsonify, request
from datetime import datetime

# Global references
applications = []
jobs = []
candidates = []

def init_applications_routes(app, applications_ref, jobs_ref, candidates_ref, matching_engine, email_service):
    """Initialize applications routes with references to data stores"""
    global applications, jobs, candidates
    applications = applications_ref
    jobs = jobs_ref
    candidates = candidates_ref
    
    def generate_application_code():
        return f"APP-{len(applications) + 1:04d}"
    
    @app.route('/api/applications', methods=['GET', 'POST'])
    def manage_applications():
        global applications
        
        if request.method == 'POST':
            data = request.get_json()
            job = next((j for j in jobs if j['id'] == data.get('jd_id')), None)
            candidate = next((c for c in candidates if c['id'] == data.get('candidate_id')), None)
            
            if not job or not candidate:
                return jsonify({'error': 'Job or candidate not found'}), 404
            
            # Calculate match score
            match_score, match_details = matching_engine.calculate_match_score(
                job.get('skills_required', ''),
                candidate.get('skills', '')
            )
            
            application = {
                'id': len(applications) + 1,
                'application_code': generate_application_code(),
                'candidate_id': data.get('candidate_id'),
                'jd_id': data.get('jd_id'),
                'candidate_name': candidate.get('name'),
                'job_title': job.get('title'),
                'match_score': match_score,
                'match_details': match_details,
                'status': 'new',
                'application_date': datetime.now().date().isoformat(),
                'created_at': datetime.now().isoformat(),
                'updated_at': datetime.now().isoformat()
            }
            applications.append(application)
            
            # Update job application count
            job['applications'] = job.get('applications', 0) + 1
            
            # Send email notification
            email_service.send_application_received_email(
                candidate.get('name'),
                candidate.get('email'),
                job.get('title'),
                match_score
            )
            
            return jsonify({
                'success': True,
                'application_id': application['id'],
                'match_score': match_score,
                'match_details': match_details
            })
        
        # GET request
        return jsonify(applications)
    
    @app.route('/api/applications/<int:app_id>/status', methods=['PUT'])
    def update_application_status(app_id):
        """Update application status (move through pipeline)"""
        data = request.get_json()
        new_status = data.get('status')
        
        for app in applications:
            if app['id'] == app_id:
                old_status = app['status']
                app['status'] = new_status
                app['updated_at'] = datetime.now().isoformat()
                
                # Send email notification on status change
                candidate = next((c for c in candidates if c['id'] == app.get('candidate_id')), None)
                if candidate and new_status in ['shortlisted', 'rejected', 'selected']:
                    email_service.send_status_update_email(
                        candidate.get('name'),
                        candidate.get('email'),
                        app.get('job_title'),
                        new_status
                    )
                
                return jsonify({'success': True, 'message': f'Status changed from {old_status} to {new_status}'})
        
        return jsonify({'error': 'Application not found'}), 404
