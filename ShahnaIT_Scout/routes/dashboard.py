# routes/dashboard.py
# Dashboard routes - stats, health checks

from flask import jsonify
from datetime import datetime

# Global references to data stores (will be set by main app)
jobs = []
candidates = []
applications = []
interviews = []
offers = []

def init_dashboard_routes(app, jobs_ref, candidates_ref, applications_ref, interviews_ref, offers_ref):
    """Initialize dashboard routes with references to data stores"""
    global jobs, candidates, applications, interviews, offers
    jobs = jobs_ref
    candidates = candidates_ref
    applications = applications_ref
    interviews = interviews_ref
    offers = offers_ref
    
    @app.route('/health')
    def health():
        """Health check endpoint"""
        return jsonify({
            'status': 'ok',
            'timestamp': datetime.now().isoformat(),
            'version': '2.0',
            'features': ['dashboard', 'jobs', 'candidates', 'applications', 'interviews', 'offers']
        })
    
    @app.route('/api/dashboard/stats')
    def dashboard_stats():
        """Get dashboard statistics"""
        total_apps = len(applications)
        ai_matches = sum(1 for a in applications if a.get('match_score', 0) >= 75)
        
        return jsonify({
            'overview': {
                'open_positions': len([j for j in jobs if j.get('status') == 'open']),
                'total_candidates': len(candidates),
                'total_applications': total_apps,
                'interviews_today': len([i for i in interviews if i.get('status') == 'scheduled']),
                'offers_accepted': len([o for o in offers if o.get('status') == 'accepted']),
                'ai_matches': ai_matches
            },
            'pipeline': {
                'new': len([a for a in applications if a.get('status') == 'new']),
                'screening': len([a for a in applications if a.get('status') in ['screening', 'shortlisted']]),
                'interview': len([a for a in applications if a.get('status') in ['interview-scheduled', 'interviewed']]),
                'offer': len([a for a in applications if a.get('status') in ['offered', 'offer-accepted']]),
                'hired': len([a for a in applications if a.get('status') == 'hired']),
                'rejected': len([a for a in applications if a.get('status') == 'rejected'])
            },
            'sources': [
                {'source': 'LinkedIn', 'count': len([c for c in candidates if c.get('source') == 'linkedin'])},
                {'source': 'Manual', 'count': len([c for c in candidates if c.get('source') == 'manual'])},
                {'source': 'CSV Import', 'count': len([c for c in candidates if c.get('source') == 'csv_import'])}
            ],
            'recent_activities': [],
            'top_jds': []
        })
