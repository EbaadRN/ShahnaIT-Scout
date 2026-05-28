# app.py - Main Application File
# ShahnaIT Scout - Recruitment Management System

from flask import Flask, render_template_string
import os

# Initialize Flask app
app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'dev-secret-key')
app.config['MAX_CONTENT_LENGTH'] = 100 * 1024 * 1024  # 100MB

# Import all services
from services import gemini_ai, resume_parser, email_service, matching_engine, linkedin_service

# Import all route modules
from routes import dashboard, jobs, candidates, applications, interviews, offers, analytics, pipeline, ai_tools

# ============= HTML DASHBOARD TEMPLATE =============
# You already have this in your existing app.py
# For now, load a simple version - you can replace with your full template later

DASHBOARD_TEMPLATE = '''
<!DOCTYPE html>
<html>
<head>
    <title>ShahnaIT Scout</title>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.1.3/dist/css/bootstrap.min.css" rel="stylesheet">
    <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/bootstrap-icons@1.8.1/font/bootstrap-icons.css">
</head>
<body>
    <nav class="navbar navbar-dark bg-dark">
        <div class="container-fluid">
            <span class="navbar-brand"><i class="bi bi-robot"></i> ShahnaIT Scout - Recruitment System</span>
        </div>
    </nav>
    <div class="container mt-4">
        <div class="alert alert-success">
            <h4>✅ Recruitment System is Running!</h4>
            <p>Your modular recruitment system is successfully deployed.</p>
            <hr>
            <h5>Available Features:</h5>
            <ul>
                <li>Job Description Management</li>
                <li>Candidate Database</li>
                <li>Application Tracking with AI Matching</li>
                <li>Interview Scheduling</li>
                <li>Offer Letter Generation</li>
                <li>Kanban Pipeline</li>
                <li>AI Tools (Resume Parsing, JD Generation, etc.)</li>
            </ul>
            <p><strong>API Status:</strong> 
                <span class="badge bg-success">Gemini AI: {{ "Available" if gemini_available else "Not Configured" }}</span>
                <span class="badge bg-info">Email: {{ "Configured" if email_configured else "Not Configured" }}</span>
            </p>
        </div>
        
        <div class="row mt-4">
            <div class="col-md-4">
                <div class="card">
                    <div class="card-body text-center">
                        <h3>📋</h3>
                        <h5>Jobs</h5>
                        <button class="btn btn-primary" onclick="location.href='/api/jds'">View Jobs API</button>
                    </div>
                </div>
            </div>
            <div class="col-md-4">
                <div class="card">
                    <div class="card-body text-center">
                        <h3>👥</h3>
                        <h5>Candidates</h5>
                        <button class="btn btn-success" onclick="location.href='/api/candidates'">View Candidates API</button>
                    </div>
                </div>
            </div>
            <div class="col-md-4">
                <div class="card">
                    <div class="card-body text-center">
                        <h3>📄</h3>
                        <h5>Applications</h5>
                        <button class="btn btn-info" onclick="location.href='/api/applications'">View Applications API</button>
                    </div>
                </div>
            </div>
        </div>
    </div>
    <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.1.3/dist/js/bootstrap.bundle.min.js"></script>
</body>
</html>
'''

# ============= DATA STORES =============
jobs = []
candidates = []
applications = []
interviews = []
offers = []
next_id = 1

# ============= INITIALIZE ROUTES =============

# Dashboard routes
dashboard.init_dashboard_routes(app, jobs, candidates, applications, interviews, offers)

# Jobs routes
jobs.init_jobs_routes(app, jobs, next_id)

# Candidates routes
candidates.init_candidates_routes(app, candidates, next_id, applications, resume_parser, matching_engine)

# Applications routes
applications.init_applications_routes(app, applications, jobs, candidates, matching_engine, email_service)

# Interviews routes
interviews.init_interviews_routes(app, interviews, applications, candidates, jobs, email_service)

# Offers routes
offers.init_offers_routes(app, offers, applications, candidates, email_service)

# Analytics routes
analytics.init_analytics_routes(app, applications, candidates, jobs)

# Pipeline routes
pipeline.init_pipeline_routes(app, applications, candidates, jobs, matching_engine)

# AI Tools routes
ai_tools.init_ai_tools_routes(app, gemini_ai, resume_parser)

# ============= MAIN ROUTE =============
@app.route('/')
def index():
    """Main dashboard page"""
    gemini_available = gemini_ai.GEMINI_AVAILABLE
    email_configured = email_service.EMAIL_CONFIGURED
    return render_template_string(DASHBOARD_TEMPLATE, 
                                  gemini_available=gemini_available,
                                  email_configured=email_configured)

# ============= HEALTH CHECK =============
@app.route('/health')
def health():
    from flask import jsonify
    from datetime import datetime
    return jsonify({
        'status': 'ok',
        'timestamp': datetime.now().isoformat(),
        'services': {
            'gemini_ai': gemini_ai.GEMINI_AVAILABLE,
            'email': email_service.EMAIL_CONFIGURED
        }
    })

# ============= MAIN =============
if __name__ == '__main__':
    port = int(os.environ.get('PORT', 8080))
    print("=" * 50)
    print("🚀 ShahnaIT Scout - Recruitment System")
    print("=" * 50)
    print(f"✅ Gemini AI: {'AVAILABLE' if gemini_ai.GEMINI_AVAILABLE else 'NOT CONFIGURED'}")
    print(f"✅ Email: {'CONFIGURED' if email_service.EMAIL_CONFIGURED else 'NOT CONFIGURED'}")
    print(f"✅ Server running on port: {port}")
    print("=" * 50)
    app.run(host='0.0.0.0', port=port, debug=False)
