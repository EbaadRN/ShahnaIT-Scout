# routes/interviews.py
# Interview scheduling routes

from flask import jsonify, request
from datetime import datetime

# Global references
interviews = []
applications = []
candidates = []
jobs = []

def init_interviews_routes(app, interviews_ref, applications_ref, candidates_ref, jobs_ref, email_service):
    """Initialize interviews routes with references to data stores"""
    global interviews, applications, candidates, jobs
    interviews = interviews_ref
    applications = applications_ref
    candidates = candidates_ref
    jobs = jobs_ref
    
    @app.route('/api/interviews', methods=['GET', 'POST'])
    def manage_interviews():
        global interviews
        
        if request.method == 'POST':
            data = request.get_json()
            application = next((a for a in applications if a['id'] == data.get('application_id')), None)
            
            if not application:
                return jsonify({'error': 'Application not found'}), 404
            
            candidate = next((c for c in candidates if c['id'] == application.get('candidate_id')), None)
            job = next((j for j in jobs if j['id'] == application.get('jd_id')), None)
            
            interview = {
                'id': len(interviews) + 1,
                'application_id': data.get('application_id'),
                'candidate_name': candidate.get('name') if candidate else data.get('candidate_name'),
                'job_title': job.get('title') if job else data.get('job_title'),
                'round_number': data.get('round_number', 1),
                'round_type': data.get('round_type', 'Technical'),
                'interviewer_name': data.get('interviewer_name'),
                'interviewer_email': data.get('interviewer_email'),
                'scheduled_time': data.get('scheduled_time'),
                'duration_minutes': data.get('duration_minutes', 60),
                'meeting_link': data.get('meeting_link'),
                'status': 'scheduled',
                'created_at': datetime.now().isoformat()
            }
            interviews.append(interview)
            
            # Update application status
            application['status'] = 'interview-scheduled'
            
            # Send interview invitation email
            if candidate and candidate.get('email'):
                email_service.send_interview_invite_email(
                    candidate.get('name'),
                    candidate.get('email'),
                    job.get('title') if job else 'the position',
                    data.get('interviewer_name', 'Hiring Team'),
                    data.get('scheduled_time', 'TBD'),
                    data.get('meeting_link', 'Link will be shared')
                )
            
            return jsonify({'success': True, 'interview_id': interview['id']})
        
        # GET request - return upcoming interviews
        upcoming = [i for i in interviews if i.get('status') == 'scheduled']
        return jsonify(upcoming)
    
    @app.route('/api/interviews/<int:interview_id>/complete', methods=['PUT'])
    def complete_interview(interview_id):
        """Mark interview as completed with feedback"""
        data = request.json
        
        for interview in interviews:
            if interview['id'] == interview_id:
                interview['status'] = 'completed'
                interview['feedback'] = data.get('feedback')
                interview['rating'] = data.get('rating')
                interview['result'] = data.get('result')
                interview['completed_at'] = datetime.now().isoformat()
                
                # Update application based on result
                if interview.get('application_id'):
                    for app in applications:
                        if app['id'] == interview['application_id']:
                            if data.get('result') == 'pass':
                                app['status'] = 'interviewed'
                            else:
                                app['status'] = 'rejected'
                            break
                break
        
        return jsonify({'success': True})
    
    @app.route('/api/interviews/upcoming', methods=['GET'])
    def get_upcoming_interviews():
        """Get interviews scheduled for today and tomorrow"""
        today = datetime.now().date().isoformat()
        upcoming = [i for i in interviews if i.get('scheduled_time', '').startswith(today) and i.get('status') == 'scheduled']
        return jsonify(upcoming)
