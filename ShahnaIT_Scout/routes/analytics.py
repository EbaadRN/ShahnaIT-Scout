# routes/analytics.py
# Analytics and reporting routes

from flask import jsonify
from datetime import datetime, timedelta

# Global references
applications = []
candidates = []
jobs = []

def init_analytics_routes(app, applications_ref, candidates_ref, jobs_ref):
    """Initialize analytics routes with references to data stores"""
    global applications, candidates, jobs
    applications = applications_ref
    candidates = candidates_ref
    jobs = jobs_ref
    
    @app.route('/api/reports/hiring-metrics', methods=['GET'])
    def hiring_metrics():
        """Generate hiring metrics report"""
        total_apps = len(applications)
        
        # Stage counts
        stage_counts = {
            'new': len([a for a in applications if a.get('status') == 'new']),
            'screening': len([a for a in applications if a.get('status') in ['screening', 'shortlisted']]),
            'interview': len([a for a in applications if a.get('status') in ['interview-scheduled', 'interviewed']]),
            'offer': len([a for a in applications if a.get('status') in ['offered', 'offer-accepted']]),
            'hired': len([a for a in applications if a.get('status') == 'hired']),
            'rejected': len([a for a in applications if a.get('status') == 'rejected'])
        }
        
        # Calculate conversion rates
        conversion_rates = {
            'application_to_screening': round((stage_counts['screening'] / max(total_apps, 1)) * 100, 1),
            'screening_to_interview': round((stage_counts['interview'] / max(stage_counts['screening'], 1)) * 100, 1),
            'interview_to_offer': round((stage_counts['offer'] / max(stage_counts['interview'], 1)) * 100, 1),
            'offer_to_hired': round((stage_counts['hired'] / max(stage_counts['offer'], 1)) * 100, 1)
        }
        
        # Source breakdown
        source_stats = {}
        for candidate in candidates:
            source = candidate.get('source', 'unknown')
            source_stats[source] = source_stats.get(source, 0) + 1
        
        return jsonify({
            'total_applications': total_apps,
            'total_candidates': len(candidates),
            'open_positions': len([j for j in jobs if j.get('status') == 'open']),
            'stage_counts': stage_counts,
            'conversion_rates': conversion_rates,
            'source_breakdown': source_stats,
            'average_match_score': 75  # Placeholder
        })
    
    @app.route('/api/reports/job-analytics/<int:jd_id>', methods=['GET'])
    def job_analytics(jd_id):
        """Get analytics for a specific job"""
        job = next((j for j in jobs if j['id'] == jd_id), None)
        if not job:
            return jsonify({'error': 'Job not found'}), 404
        
        job_apps = [a for a in applications if a.get('jd_id') == jd_id]
        
        return jsonify({
            'job_title': job.get('title'),
            'total_applications': len(job_apps),
            'average_match_score': sum([a.get('match_score', 0) for a in job_apps]) / max(len(job_apps), 1),
            'applications_by_status': {
                'new': len([a for a in job_apps if a.get('status') == 'new']),
                'shortlisted': len([a for a in job_apps if a.get('status') == 'shortlisted']),
                'interviewed': len([a for a in job_apps if a.get('status') in ['interview-scheduled', 'interviewed']]),
                'rejected': len([a for a in job_apps if a.get('status') == 'rejected'])
            }
        })
