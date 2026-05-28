# routes/jobs.py
# Job description routes - CRUD operations

from flask import jsonify, request
from datetime import datetime

# Global references
jobs = []
next_id = 1

def init_jobs_routes(app, jobs_ref, next_id_ref):
    """Initialize jobs routes with references to data stores"""
    global jobs, next_id
    jobs = jobs_ref
    next_id = next_id_ref
    
    def generate_job_code():
        global next_id
        code = f"JD-{next_id:04d}"
        next_id += 1
        return code
    
    @app.route('/api/jds', methods=['GET', 'POST'])
    def manage_jds():
        global jobs, next_id
        
        if request.method == 'POST':
            data = request.get_json()
            
            job = {
                'id': len(jobs) + 1,
                'code': generate_job_code(),
                'title': data.get('title', 'Untitled'),
                'location': data.get('location', 'Remote'),
                'location_type': data.get('location_type', 'remote'),
                'employment_type': data.get('employment_type', 'full-time'),
                'status': data.get('status', 'open'),
                'priority': data.get('priority', 'medium'),
                'skills_required': data.get('skills_required', ''),
                'skills_preferred': data.get('skills_preferred', ''),
                'qualifications': data.get('qualifications', ''),
                'responsibilities': data.get('responsibilities', ''),
                'benefits': data.get('benefits', ''),
                'experience_min': data.get('experience_min', 0),
                'experience_max': data.get('experience_max', 10),
                'salary_min': data.get('salary_min'),
                'salary_max': data.get('salary_max'),
                'no_of_positions': data.get('no_of_positions', 1),
                'client': data.get('client_name'),
                'department': data.get('department'),
                'ai_generated': data.get('ai_generated', False),
                'applications': 0,
                'created_at': datetime.now().isoformat(),
                'updated_at': datetime.now().isoformat()
            }
            jobs.append(job)
            return jsonify({'success': True, 'jd_id': job['id'], 'jd_code': job['code']})
        
        # GET request
        return jsonify(jobs)
    
    @app.route('/api/jds/<int:jd_id>', methods=['GET', 'PUT', 'DELETE'])
    def manage_jd_detail(jd_id):
        global jobs
        
        job = next((j for j in jobs if j['id'] == jd_id), None)
        if not job:
            return jsonify({'error': 'Job not found'}), 404
        
        if request.method == 'GET':
            return jsonify(job)
        
        elif request.method == 'PUT':
            data = request.get_json()
            job.update({
                'title': data.get('title', job['title']),
                'location': data.get('location', job['location']),
                'status': data.get('status', job['status']),
                'skills_required': data.get('skills_required', job['skills_required']),
                'updated_at': datetime.now().isoformat()
            })
            return jsonify({'success': True})
        
        elif request.method == 'DELETE':
            jobs.remove(job)
            return jsonify({'success': True})
