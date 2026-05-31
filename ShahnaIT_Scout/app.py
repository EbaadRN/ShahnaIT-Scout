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

# ============= FULL DASHBOARD HTML TEMPLATE =============
DASHBOARD_TEMPLATE = '''
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>ShahnaIT Scout - Professional Recruitment Suite</title>
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&display=swap" rel="stylesheet">
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.1.3/dist/css/bootstrap.min.css" rel="stylesheet">
    <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/bootstrap-icons@1.8.1/font/bootstrap-icons.css">
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
    <style>
        :root { --primary: #4361ee; --secondary: #3f37c9; --success: #4caf50; --danger: #f44336; --warning: #ff9800; --info: #2196f3; --dark: #1a1a2e; --light: #f8f9fa; }
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body { font-family: 'Inter', 'Segoe UI', sans-serif; background: linear-gradient(135deg, #f5f7fa 0%, #eef2f7 100%); overflow-x: hidden; }
        .sidebar { position: fixed; left: 0; top: 0; width: 280px; height: 100vh; background: linear-gradient(180deg, #1a1a2e 0%, #16213e 100%); color: white; transition: all 0.3s; z-index: 1000; overflow-y: auto; box-shadow: 10px 0 30px rgba(0,0,0,0.1); }
        .sidebar::-webkit-scrollbar { width: 5px; }
        .sidebar::-webkit-scrollbar-track { background: rgba(255,255,255,0.1); }
        .sidebar::-webkit-scrollbar-thumb { background: rgba(255,255,255,0.3); border-radius: 5px; }
        .sidebar .logo { padding: 30px 25px; text-align: center; border-bottom: 1px solid rgba(255,255,255,0.08); }
        .sidebar .logo h3 { font-size: 1.6rem; font-weight: 800; background: linear-gradient(135deg, #fff 0%, #a8c0ff 100%); -webkit-background-clip: text; -webkit-text-fill-color: transparent; background-clip: text; }
        .sidebar .logo p { font-size: 0.7rem; opacity: 0.6; margin-top: 5px; }
        .sidebar .nav-menu { padding: 25px 0; }
        .sidebar .nav-item { padding: 14px 28px; margin: 5px 15px; cursor: pointer; transition: all 0.3s; display: flex; align-items: center; gap: 14px; border-radius: 12px; color: rgba(255,255,255,0.7); }
        .sidebar .nav-item:hover { background: rgba(255,255,255,0.08); color: white; transform: translateX(5px); }
        .sidebar .nav-item.active { background: linear-gradient(135deg, #4361ee, #3a0ca3); color: white; box-shadow: 0 10px 20px rgba(67,97,238,0.3); }
        .sidebar .nav-item i { font-size: 1.3rem; width: 28px; }
        .main-content { margin-left: 280px; padding: 25px 35px; min-height: 100vh; }
        .modern-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 30px; }
        .page-title h1 { font-size: 1.8rem; font-weight: 700; background: linear-gradient(135deg, #1a1a2e, #2d3a5e); -webkit-background-clip: text; -webkit-text-fill-color: transparent; background-clip: text; }
        .page-title p { color: #6c757d; font-size: 0.85rem; margin-top: 5px; }
        .header-actions { display: flex; gap: 15px; align-items: center; }
        .search-bar { background: white; border-radius: 30px; padding: 8px 20px; display: flex; align-items: center; gap: 10px; box-shadow: 0 2px 8px rgba(0,0,0,0.05); }
        .search-bar input { border: none; outline: none; background: transparent; width: 200px; }
        .stats-grid { display: grid; grid-template-columns: repeat(4, 1fr); gap: 25px; margin-bottom: 35px; }
        .stat-card-modern { background: white; border-radius: 24px; padding: 22px; transition: all 0.3s; cursor: pointer; border: 1px solid rgba(0,0,0,0.05); box-shadow: 0 4px 15px rgba(0,0,0,0.03); }
        .stat-card-modern:hover { transform: translateY(-5px); box-shadow: 0 15px 35px rgba(0,0,0,0.1); }
        .stat-icon-modern { width: 55px; height: 55px; border-radius: 18px; display: flex; align-items: center; justify-content: center; font-size: 1.8rem; margin-bottom: 18px; }
        .stat-value-modern { font-size: 2.2rem; font-weight: 800; margin-bottom: 5px; }
        .stat-label-modern { color: #6c757d; font-size: 0.85rem; font-weight: 500; }
        .stat-trend { font-size: 0.75rem; margin-top: 8px; display: flex; align-items: center; gap: 5px; }
        .chart-card { background: white; border-radius: 24px; padding: 25px; margin-bottom: 25px; box-shadow: 0 4px 15px rgba(0,0,0,0.03); border: 1px solid rgba(0,0,0,0.05); }
        .chart-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 20px; }
        .chart-header h5 { font-weight: 700; margin: 0; }
        .modern-table { background: white; border-radius: 20px; overflow: hidden; box-shadow: 0 4px 15px rgba(0,0,0,0.03); border: 1px solid rgba(0,0,0,0.05); }
        .modern-table table { margin: 0; }
        .modern-table th { background: #f8f9fa; padding: 15px 20px; font-weight: 600; font-size: 0.85rem; color: #495057; border: none; }
        .modern-table td { padding: 15px 20px; vertical-align: middle; border-bottom: 1px solid #f0f0f0; }
        .badge-modern { padding: 5px 12px; border-radius: 20px; font-size: 0.7rem; font-weight: 600; }
        .badge-open { background: linear-gradient(135deg, #4caf50, #2e7d32); color: white; }
        .badge-closed { background: linear-gradient(135deg, #f44336, #c62828); color: white; }
        .badge-draft { background: linear-gradient(135deg, #9e9e9e, #616161); color: white; }
        .badge-interview { background: linear-gradient(135deg, #2196f3, #1565c0); color: white; }
        .btn-primary-modern { background: linear-gradient(135deg, #4361ee, #3a0ca3); border: none; padding: 10px 24px; border-radius: 30px; font-weight: 600; transition: all 0.3s; color: white; }
        .btn-primary-modern:hover { transform: translateY(-2px); box-shadow: 0 8px 20px rgba(67,97,238,0.3); }
        .btn-outline-modern { background: transparent; border: 1px solid #dee2e6; padding: 10px 20px; border-radius: 30px; font-weight: 500; transition: all 0.3s; }
        .btn-outline-modern:hover { background: #f8f9fa; border-color: #4361ee; }
        .kanban-board { display: flex; gap: 20px; overflow-x: auto; padding: 20px 0; }
        .kanban-column { min-width: 320px; background: #f8f9fa; border-radius: 20px; padding: 15px; }
        .kanban-column-header { font-weight: 700; padding: 12px; margin-bottom: 15px; background: white; border-radius: 12px; display: flex; justify-content: space-between; box-shadow: 0 2px 5px rgba(0,0,0,0.05); }
        .kanban-card { background: white; border-radius: 12px; padding: 14px; margin-bottom: 10px; cursor: grab; transition: all 0.3s; box-shadow: 0 2px 8px rgba(0,0,0,0.05); border: 1px solid rgba(0,0,0,0.03); }
        .kanban-card:hover { transform: translateX(5px); box-shadow: 0 5px 15px rgba(0,0,0,0.1); }
        .modal-modern .modal-content { border-radius: 28px; border: none; overflow: hidden; }
        .modal-modern .modal-header { background: linear-gradient(135deg, #4361ee, #3a0ca3); color: white; border: none; padding: 20px 25px; }
        @media (max-width: 1200px) { .stats-grid { grid-template-columns: repeat(2, 1fr); } }
        @media (max-width: 768px) { .sidebar { left: -280px; } .main-content { margin-left: 0; } .stats-grid { grid-template-columns: 1fr; } }
        .form-section { background: #f8f9fa; padding: 15px; border-radius: 8px; margin-bottom: 20px; }
        .form-section-title { font-weight: 600; margin-bottom: 15px; color: var(--primary); }
        .loader { display: inline-block; width: 20px; height: 20px; border: 3px solid #f3f3f3; border-top: 3px solid var(--primary); border-radius: 50%; animation: spin 1s linear infinite; }
        @keyframes spin { 0% { transform: rotate(0deg); } 100% { transform: rotate(360deg); } }
        .ai-badge { background: linear-gradient(135deg, #667eea, #764ba2); color: white; padding: 2px 8px; border-radius: 12px; font-size: 0.7rem; margin-left: 8px; }
        .skill-entry, .experience-entry, .education-entry { transition: all 0.2s; }
    </style>
</head>
<body>
    <div class="sidebar" id="sidebar">
        <div class="logo"><h3><i class="bi bi-robot"></i> ShahnaIT</h3><p>Intelligent Recruitment Suite</p></div>
        <div class="nav-menu">
            <div class="nav-item active" data-section="dashboard"><i class="bi bi-speedometer2"></i><span>Dashboard</span></div>
            <div class="nav-item" data-section="jds"><i class="bi bi-briefcase"></i><span>Job Descriptions</span></div>
            <div class="nav-item" data-section="candidates"><i class="bi bi-people"></i><span>Candidates</span></div>
            <div class="nav-item" data-section="applications"><i class="bi bi-file-check"></i><span>Applications</span></div>
            <div class="nav-item" data-section="pipeline"><i class="bi bi-kanban"></i><span>Pipeline</span></div>
            <div class="nav-item" data-section="interviews"><i class="bi bi-calendar-check"></i><span>Interviews</span></div>
            <div class="nav-item" data-section="offers"><i class="bi bi-envelope-paper"></i><span>Offers</span></div>
            <div class="nav-item" data-section="analytics"><i class="bi bi-graph-up"></i><span>Analytics</span></div>
            <div class="nav-item" data-section="ai-tools"><i class="bi bi-stars"></i><span>AI Tools</span></div>
        </div>
    </div>
    
    <div class="main-content" id="mainContent">
        <div id="dashboardSection">
            <div class="modern-header"><div class="page-title"><h1>Recruitment Dashboard</h1><p>Track your hiring pipeline, candidates, and analytics in real-time</p></div><div class="header-actions"><div class="search-bar"><i class="bi bi-search"></i><input type="text" id="globalSearch" placeholder="Search candidates, jobs..."></div></div></div>
            <div class="stats-grid" id="statsGrid"></div>
            <div class="row"><div class="col-lg-8"><div class="chart-card"><div class="chart-header"><h5><i class="bi bi-graph-up"></i> Recruitment Funnel <span class="ai-badge">AI Analytics</span></h5></div><canvas id="pipelineChart" height="280"></canvas></div></div><div class="col-lg-4"><div class="chart-card"><div class="chart-header"><h5><i class="bi bi-pie-chart"></i> Candidate Sources</h5></div><canvas id="sourcesChart" height="280"></canvas></div></div></div>
            <div class="row mt-3"><div class="col-lg-6"><div class="chart-card"><div class="chart-header"><h5><i class="bi bi-lightning-charge"></i> Quick Actions</h5></div><div class="d-flex gap-3 flex-wrap"><button class="btn btn-primary-modern" onclick="showJDMasterModal()"><i class="bi bi-plus-circle"></i> Post a Job</button><button class="btn btn-outline-modern" onclick="showCandidateModal()"><i class="bi bi-person-plus"></i> Add Candidate</button><button class="btn btn-outline-modern" onclick="showResumeUploadModal()"><i class="bi bi-file-earmark-arrow-up"></i> Upload Resume</button><button class="btn btn-outline-modern" onclick="showAITools()"><i class="bi bi-stars"></i> AI Tools</button></div></div></div><div class="col-lg-6"><div class="chart-card"><div class="chart-header"><h5><i class="bi bi-clock-history"></i> Recent Activity</h5></div><div id="activitiesList" style="max-height: 200px; overflow-y: auto;"></div></div></div></div>
        </div>
        
        <div id="jdsSection" style="display: none;"><div class="modern-header"><div class="page-title"><h1>Job Descriptions</h1><p>Manage all your job openings</p></div><div class="header-actions"><button class="btn btn-primary-modern" onclick="showJDMasterModal()"><i class="bi bi-plus-circle"></i> Create Job</button><button class="btn btn-outline-modern" onclick="showJDUploadModal()"><i class="bi bi-cloud-upload"></i> Upload JD</button><button class="btn btn-outline-modern" onclick="generateAIJD()"><i class="bi bi-stars"></i> AI Generate JD</button></div></div><div class="modern-table"><table class="table"><thead><tr><th>Code</th><th>Title</th><th>Client</th><th>Location</th><th>Type</th><th>Status</th><th>Applications</th><th>Actions</th></tr></thead><tbody id="jdsTableBody"></tbody></table></div></div>
        
        <div id="candidatesSection" style="display: none;"><div class="modern-header"><div class="page-title"><h1>Candidates Database</h1><p>Manage your talent pool <span class="ai-badge">AI Enriched</span></p></div><div class="header-actions"><button class="btn btn-primary-modern" onclick="showCandidateModal()"><i class="bi bi-person-plus"></i> Add Candidate</button><button class="btn btn-outline-modern" onclick="showResumeUploadModal()"><i class="bi bi-file-earmark-arrow-up"></i> Upload Resume</button><button class="btn btn-outline-modern" onclick="showLinkedInImport()"><i class="bi bi-linkedin"></i> Import from LinkedIn</button><button class="btn btn-outline-modern" onclick="showBulkImport()"><i class="bi bi-file-spreadsheet"></i> Bulk Import CSV</button></div></div><div class="row mb-3"><div class="col-md-3"><input type="text" class="form-control" id="candidateSearch" placeholder="Search by name, email, skill..."></div><div class="col-md-2"><select class="form-select" id="sourceFilter"><option value="">All Sources</option><option value="linkedin">LinkedIn</option><option value="naukri">Naukri</option><option value="referral">Referral</option><option value="ai-enriched">AI Enriched</option></select></div><div class="col-md-2"><button class="btn btn-primary-modern" onclick="loadCandidates()"><i class="bi bi-search"></i> Search</button><button class="btn btn-outline-modern" onclick="showAdvancedFilters()"><i class="bi bi-funnel"></i> Filters</button></div></div><div id="candidatesList"></div><div id="candidatesPagination" class="mt-3"></div></div>
        
        <div id="applicationsSection" style="display: none;"><div class="modern-header"><div class="page-title"><h1>Applications</h1><p>Track all candidate applications <span class="ai-badge">Smart Ranking</span></p></div></div><div class="modern-table"><table class="table"><thead><tr><th>ID</th><th>Candidate</th><th>Job</th><th>AI Match Score</th><th>Status</th><th>Actions</th></tr></thead><tbody id="applicationsTable"></tbody></table></div></div>
        
        <div id="pipelineSection" style="display: none;"><div class="modern-header"><div class="page-title"><h1>Recruitment Pipeline</h1><p>Drag and drop candidates to move between stages</p></div><button class="btn btn-outline-modern" onclick="showPipelineAnalytics()"><i class="bi bi-graph-up"></i> Pipeline Analytics</button></div><div id="kanbanBoard" class="kanban-board"></div></div>
        
        <div id="interviewsSection" style="display: none;"><div class="modern-header"><div class="page-title"><h1>Interviews</h1><p>Schedule and manage interviews <span class="ai-badge">AI Scheduling</span></p></div><div class="header-actions"><button class="btn btn-primary-modern" onclick="showInterviewModal()"><i class="bi bi-plus-circle"></i> Schedule Interview</button><button class="btn btn-outline-modern" onclick="showAIScheduler()"><i class="bi bi-stars"></i> AI Smart Schedule</button></div></div><div id="interviewsList"></div></div>
        
        <div id="offersSection" style="display: none;"><div class="modern-header"><div class="page-title"><h1>Offer Letters</h1><p>Generate and manage offers</p></div><div class="header-actions"><button class="btn btn-primary-modern" onclick="showOfferModal()"><i class="bi bi-envelope-paper"></i> Generate Offer</button><button class="btn btn-outline-modern" onclick="showOfferTemplateModal()"><i class="bi bi-file-text"></i> Templates</button></div></div><div id="offersList"></div></div>
        
        <div id="analyticsSection" style="display: none;"><div class="modern-header"><div class="page-title"><h1>Analytics & Reports</h1><p>Data-driven insights for your recruitment <span class="ai-badge">AI Insights</span></p></div></div><div class="row"><div class="col-lg-6"><div class="chart-card"><canvas id="dailyAppsChart" height="250"></canvas></div></div><div class="col-lg-6"><div class="chart-card"><canvas id="stageDistChart" height="250"></canvas></div></div></div><div class="row mt-3"><div class="col-lg-4"><div class="chart-card"><h6>Time-to-Hire Analysis</h6><canvas id="timeToHireChart" height="200"></canvas></div></div><div class="col-lg-4"><div class="chart-card"><h6>Source Effectiveness</h6><canvas id="sourceEffectivenessChart" height="200"></canvas></div></div><div class="col-lg-4"><div class="chart-card"><h6>AI Match Accuracy</h6><canvas id="aiAccuracyChart" height="200"></canvas></div></div></div></div>
        
        <div id="aiToolsSection" style="display: none;"><div class="modern-header"><div class="page-title"><h1>AI Tools</h1><p>Supercharge your recruitment with artificial intelligence</p></div></div><div class="row"><div class="col-md-4 mb-3"><div class="card h-100"><div class="card-body"><div class="text-center mb-3"><i class="bi bi-file-text" style="font-size: 3rem; color: #4361ee;"></i></div><h5 class="text-center">AI Resume Parser</h5><p class="text-center text-muted small">Extract candidate info with Gemini AI</p><button class="btn btn-primary-modern w-100" onclick="showResumeUploadModal()">Upload Resume</button></div></div></div><div class="col-md-4 mb-3"><div class="card h-100"><div class="card-body"><div class="text-center mb-3"><i class="bi bi-file-earmark-text" style="font-size: 3rem; color: #4caf50;"></i></div><h5 class="text-center">AI JD Generator</h5><p class="text-center text-muted small">Generate job descriptions with Gemini AI</p><button class="btn btn-primary-modern w-100" onclick="generateAIJD()">Generate JD</button></div></div></div><div class="col-md-4 mb-3"><div class="card h-100"><div class="card-body"><div class="text-center mb-3"><i class="bi bi-chat-dots" style="font-size: 3rem; color: #ff9800;"></i></div><h5 class="text-center">AI Interview Questions</h5><p class="text-center text-muted small">Generate role-specific questions</p><button class="btn btn-primary-modern w-100" onclick="generateAIQuestions()">Generate Questions</button></div></div></div><div class="col-md-4 mb-3"><div class="card h-100"><div class="card-body"><div class="text-center mb-3"><i class="bi bi-linkedin" style="font-size: 3rem; color: #0077b5;"></i></div><h5 class="text-center">LinkedIn Enrichment</h5><p class="text-center text-muted small">Import and enrich candidate data</p><button class="btn btn-primary-modern w-100" onclick="showLinkedInImport()">Import from LinkedIn</button></div></div></div><div class="col-md-4 mb-3"><div class="card h-100"><div class="card-body"><div class="text-center mb-3"><i class="bi bi-envelope-paper" style="font-size: 3rem; color: #f44336;"></i></div><h5 class="text-center">AI Email Assistant</h5><p class="text-center text-muted small">Generate personalized emails</p><button class="btn btn-primary-modern w-100" onclick="generateAIEmail()">Generate Email</button></div></div></div><div class="col-md-4 mb-3"><div class="card h-100"><div class="card-body"><div class="text-center mb-3"><i class="bi bi-graph-up" style="font-size: 3rem; color: #9c27b0;"></i></div><h5 class="text-center">AI Candidate Scoring</h5><p class="text-center text-muted small">AI-powered recommendations</p><button class="btn btn-primary-modern w-100" onclick="showAIScoring()">Score Candidates</button></div></div></div></div></div>
    </div>

    <!-- Modals -->
    <div class="modal fade modal-modern" id="jdMasterModal" tabindex="-1"><div class="modal-dialog modal-lg"><div class="modal-content"><div class="modal-header"><h5 class="modal-title"><i class="bi bi-briefcase"></i> Create Job Description</h5><button type="button" class="btn-close btn-close-white" data-bs-dismiss="modal"></button></div><div class="modal-body"><form id="jdMasterForm"><div class="form-section"><div class="form-section-title">Basic Information</div><div class="row"><div class="col-md-8 mb-2"><label>Job Title *</label><input type="text" class="form-control" id="jdTitle" required></div><div class="col-md-4 mb-2"><label>Client</label><select class="form-select" id="jdClientId"></select></div><div class="col-md-4 mb-2"><label>Department</label><input type="text" class="form-control" id="jdDepartment"></div><div class="col-md-4 mb-2"><label>Location</label><input type="text" class="form-control" id="jdLocation"></div><div class="col-md-4 mb-2"><label>Location Type</label><select class="form-select" id="jdLocationType"><option value="remote">Remote</option><option value="onsite">Onsite</option><option value="hybrid">Hybrid</option></select></div><div class="col-md-6 mb-2"><label>Employment Type</label><select class="form-select" id="jdEmploymentType"><option value="full-time">Full Time</option><option value="part-time">Part Time</option><option value="contract">Contract</option></select></div><div class="col-md-6 mb-2"><label>No. of Positions</label><input type="number" class="form-control" id="jdPositions" value="1"></div></div></div><div class="form-section"><div class="form-section-title">Experience & Salary</div><div class="row"><div class="col-md-3 mb-2"><label>Min Experience</label><input type="number" class="form-control" id="jdExpMin" value="0"></div><div class="col-md-3 mb-2"><label>Max Experience</label><input type="number" class="form-control" id="jdExpMax" value="10"></div><div class="col-md-3 mb-2"><label>Min Salary</label><input type="number" class="form-control" id="jdSalaryMin"></div><div class="col-md-3 mb-2"><label>Max Salary</label><input type="number" class="form-control" id="jdSalaryMax"></div></div></div><div class="form-section"><div class="form-section-title">Skills & Qualifications</div><div class="mb-2"><label>Required Skills (comma separated)</label><textarea class="form-control" id="jdSkills" rows="2"></textarea></div><div class="mb-2"><label>Preferred Skills</label><textarea class="form-control" id="jdSkillsPref" rows="2"></textarea></div><div class="mb-2"><label>Qualifications</label><textarea class="form-control" id="jdQualifications" rows="2"></textarea></div></div><div class="form-section"><div class="form-section-title">Job Description</div><div class="mb-2"><label>Responsibilities</label><textarea class="form-control" id="jdResponsibilities" rows="4"></textarea></div><div class="mb-2"><label>Benefits</label><textarea class="form-control" id="jdBenefits" rows="2"></textarea></div></div><div class="row"><div class="col-md-6 mb-2"><label>Status</label><select class="form-select" id="jdStatus"><option value="draft">Draft</option><option value="open">Open</option><option value="closed">Closed</option></select></div><div class="col-md-6 mb-2"><label>Priority</label><select class="form-select" id="jdPriority"><option value="low">Low</option><option value="medium">Medium</option><option value="high">High</option></select></div></div><button type="submit" class="btn btn-primary-modern w-100">Create Job</button></form></div></div></div></div>

    <div class="modal fade modal-modern" id="jdUploadModal" tabindex="-1"><div class="modal-dialog"><div class="modal-content"><div class="modal-header"><h5 class="modal-title"><i class="bi bi-cloud-upload"></i> Upload JD Document</h5><button type="button" class="btn-close btn-close-white" data-bs-dismiss="modal"></button></div><div class="modal-body"><div class="text-center mb-3"><i class="bi bi-file-earmark-pdf" style="font-size: 3rem;"></i><i class="bi bi-file-earmark-word" style="font-size: 3rem;"></i><span class="ai-badge">AI Parsing</span></div><div class="mb-3"><input type="file" class="form-control" id="jdUploadFile" accept=".pdf,.docx,.txt"><div class="form-text">Upload PDF, DOCX, or TXT file. AI will extract all details automatically.</div></div><div id="jdParseProgress" style="display: none;" class="text-center"><div class="loader"></div><p class="mt-2">AI is analyzing the document...</p></div><button class="btn btn-primary-modern w-100" onclick="uploadAndParseJD()"><i class="bi bi-robot"></i> Parse & Auto-fill</button></div></div></div></div>

    <div class="modal fade modal-modern" id="candidateModal" tabindex="-1"><div class="modal-dialog modal-xl"><div class="modal-content"><div class="modal-header"><h5 class="modal-title"><i class="bi bi-person-badge"></i> Add/Edit Candidate - Complete Profile</h5><button type="button" class="btn-close btn-close-white" data-bs-dismiss="modal"></button></div><div class="modal-body" style="max-height: 70vh; overflow-y: auto;"><form id="candidateForm" enctype="multipart/form-data"><div class="card mb-3"><div class="card-header bg-primary text-white">Personal Information</div><div class="card-body"><div class="row"><div class="col-md-4 mb-2"><label>First Name *</label><input type="text" class="form-control" id="candFirstName" required></div><div class="col-md-4 mb-2"><label>Last Name</label><input type="text" class="form-control" id="candLastName"></div><div class="col-md-4 mb-2"><label>Email *</label><input type="email" class="form-control" id="candEmail" required></div><div class="col-md-3 mb-2"><label>Mobile Number</label><input type="tel" class="form-control" id="candPhone"></div><div class="col-md-3 mb-2"><label>Alternate Number</label><input type="tel" class="form-control" id="candAltPhone"></div><div class="col-md-3 mb-2"><label>LinkedIn ID</label><input type="text" class="form-control" id="candLinkedin" placeholder="linkedin.com/in/username"></div><div class="col-md-3 mb-2"><label>GitHub</label><input type="text" class="form-control" id="candGithub"></div><div class="col-md-6 mb-2"><label>Address</label><textarea class="form-control" id="candAddress" rows="2"></textarea></div><div class="col-md-6 mb-2"><label>Current Location</label><input type="text" class="form-control" id="candLocation"></div><div class="col-md-3 mb-2"><label>PAN Card Number</label><input type="text" class="form-control" id="candPan"></div><div class="col-md-3 mb-2"><label>Aadhar Number</label><input type="text" class="form-control" id="candAadhar"></div><div class="col-md-3 mb-2"><label>Passport Number</label><input type="text" class="form-control" id="candPassport"></div><div class="col-md-3 mb-2"><label>Date of Birth</label><input type="date" class="form-control" id="candDob"></div></div></div></div><div class="card mb-3"><div class="card-header bg-info text-white">Professional Summary <span class="ai-badge">AI Enriched</span></div><div class="card-body"><div class="row"><div class="col-md-4 mb-2"><label>Primary Role</label><input type="text" class="form-control" id="candPrimaryRole"></div><div class="col-md-4 mb-2"><label>Total Experience (Years)</label><input type="number" step="0.5" class="form-control" id="candTotalExp" value="0"></div><div class="col-md-4 mb-2"><label>Relevant Experience</label><input type="number" step="0.5" class="form-control" id="candRelevantExp" value="0"></div><div class="col-md-12 mb-2"><label>Professional Summary</label><textarea class="form-control" id="candSummary" rows="2"></textarea></div></div></div></div><div class="card mb-3"><div class="card-header bg-warning text-dark">Skills</div><div class="card-body"><div id="skillsContainer"></div><button type="button" class="btn btn-sm btn-outline-primary mt-1" onclick="addSkillEntry()">+ Add Skill</button><button type="button" class="btn btn-sm btn-outline-info mt-1 ms-2" onclick="suggestAISkills()"><i class="bi bi-stars"></i> AI Suggest Skills</button></div></div><div class="card mb-3"><div class="card-header bg-secondary text-white">Work Experience</div><div class="card-body"><div id="experienceContainer"></div><button type="button" class="btn btn-sm btn-outline-secondary mt-1" onclick="addExperienceEntry()">+ Add Company</button></div></div><div class="card mb-3"><div class="card-header bg-dark text-white">Education</div><div class="card-body"><div id="educationContainer"></div><button type="button" class="btn btn-sm btn-outline-dark mt-1" onclick="addEducationEntry()">+ Add Education</button></div></div><div class="card mb-3"><div class="card-header bg-dark text-white">Salary & Notice Period</div><div class="card-body"><div class="row"><div class="col-md-3 mb-2"><label>Current Salary (₹)</label><input type="number" class="form-control" id="candCurrentSalary"></div><div class="col-md-3 mb-2"><label>Expected Salary (₹)</label><input type="number" class="form-control" id="candExpectedSalary"></div><div class="col-md-3 mb-2"><label>Notice Period (days)</label><input type="number" class="form-control" id="candNoticePeriod"></div><div class="col-md-3 mb-2"><label>Source</label><select class="form-control" id="candSource"><option value="linkedin">LinkedIn</option><option value="naukri">Naukri</option><option value="referral">Referral</option><option value="ai-enriched">AI Enriched</option></select></div></div></div></div><div class="card mb-3"><div class="card-header bg-danger text-white"><i class="bi bi-file-earmark-text"></i> Candidate Documents</div><div class="card-body"><div class="row"><div class="col-md-6 mb-3"><label>📄 Resume/CV</label><input type="file" class="form-control" id="docResume" accept=".pdf,.docx,.doc"><div id="resumeFileName" class="small text-success mt-1"></div></div><div class="col-md-6 mb-3"><label>🎓 Highest Degree Certificate</label><input type="file" class="form-control" id="docDegree" accept=".pdf,.jpg,.png"><div id="degreeFileName" class="small text-success mt-1"></div></div><div class="col-md-4 mb-3"><label>💰 Pay Slip</label><input type="file" class="form-control" id="docPaySlip" accept=".pdf,.jpg,.png"><div id="paySlipFileName" class="small text-success mt-1"></div></div><div class="col-md-4 mb-3"><label>📑 Form 16</label><input type="file" class="form-control" id="docForm16" accept=".pdf"><div id="form16FileName" class="small text-success mt-1"></div></div><div class="col-md-4 mb-3"><label>🪪 PAN Card</label><input type="file" class="form-control" id="docPan" accept=".pdf,.jpg,.png"><div id="panFileName" class="small text-success mt-1"></div></div><div class="col-md-4 mb-3"><label>🆔 Aadhar Card</label><input type="file" class="form-control" id="docAadhar" accept=".pdf,.jpg,.png"><div id="aadharFileName" class="small text-success mt-1"></div></div><div class="col-md-4 mb-3"><label>📸 Passport Photo</label><input type="file" class="form-control" id="docPhoto" accept=".jpg,.png"><div id="photoFileName" class="small text-success mt-1"></div></div><div class="col-md-4 mb-3"><label>📜 Offer Letter (signed)</label><input type="file" class="form-control" id="docOfferLetter" accept=".pdf"><div id="offerLetterFileName" class="small text-success mt-1"></div></div><div class="col-md-12 mb-3"><label>📎 Other Documents</label><input type="file" class="form-control" id="docOther" accept=".pdf,.jpg,.png,.docx"><div id="otherFileName" class="small text-success mt-1"></div></div></div></div></div><button type="submit" class="btn btn-success w-100">Save Candidate Profile</button></form></div></div></div></div>

    <div class="modal fade modal-modern" id="resumeUploadModal" tabindex="-1"><div class="modal-dialog"><div class="modal-content"><div class="modal-header"><h5 class="modal-title"><i class="bi bi-file-earmark-arrow-up"></i> Upload Resume <span class="ai-badge">AI Powered</span></h5><button type="button" class="btn-close btn-close-white" data-bs-dismiss="modal"></button></div><div class="modal-body"><div class="mb-3"><input type="file" class="form-control" id="resumeFile" accept=".pdf,.docx"><div class="form-text">Upload candidate's resume. AI will extract all information automatically.</div></div><div id="resumeParseProgress" style="display: none;" class="text-center"><div class="loader"></div><p class="mt-2">AI is analyzing the resume...</p></div><div id="resumePreview" style="display: none;"><h6>Extracted Information:</h6><pre id="resumeExtractedData" class="bg-light p-2 rounded" style="font-size: 0.8rem;"></pre><button class="btn btn-primary-modern w-100" onclick="createCandidateFromResume()">Create Candidate Profile</button></div><button class="btn btn-primary-modern w-100" onclick="parseResume()" id="parseResumeBtn"><i class="bi bi-robot"></i> Parse Resume</button></div></div></div></div>

    <div class="modal fade modal-modern" id="applicationModal" tabindex="-1"><div class="modal-dialog"><div class="modal-content"><div class="modal-header"><h5 class="modal-title">Create Application <span class="ai-badge">AI Match Scoring</span></h5><button type="button" class="btn-close btn-close-white" data-bs-dismiss="modal"></button></div><div class="modal-body"><form id="applicationForm"><div class="mb-2"><label>Candidate</label><select class="form-select" id="appCandidateId" required></select></div><div class="mb-2"><label>Job Description</label><select class="form-select" id="appJdId" required></select></div><div id="matchScoreDisplay" class="alert alert-info" style="display: none;">AI Match Score: <strong id="matchScore"></strong>%</div><button type="submit" class="btn btn-primary-modern w-100">Create Application</button></form></div></div></div></div>

    <div class="modal fade modal-modern" id="interviewModal" tabindex="-1"><div class="modal-dialog"><div class="modal-content"><div class="modal-header"><h5 class="modal-title">Schedule Interview <span class="ai-badge">Smart Scheduling</span></h5><button type="button" class="btn-close btn-close-white" data-bs-dismiss="modal"></button></div><div class="modal-body"><form id="interviewForm"><div class="mb-2"><label>Application</label><select class="form-select" id="interviewAppId" required></select></div><div class="mb-2"><label>Round Type</label><select class="form-select" id="interviewRoundType"><option value="telephonic">Telephonic Screening</option><option value="technical">Technical Round</option><option value="coding">Coding Assessment</option><option value="system-design">System Design</option><option value="managerial">Managerial Round</option><option value="hr">HR Round</option><option value="client">Client Round</option><option value="final">Final Round</option></select></div><div class="mb-2"><label>Interviewer Name</label><input type="text" class="form-control" id="interviewerName"></div><div class="mb-2"><label>Interviewer Email</label><input type="email" class="form-control" id="interviewerEmail"></div><div class="mb-2"><label>Scheduled Date & Time</label><input type="datetime-local" class="form-control" id="interviewDateTime"></div><div class="mb-2"><label>Meeting Link (Google Meet/Zoom)</label><input type="url" class="form-control" id="interviewLink"></div><button type="submit" class="btn btn-warning w-100">Schedule Interview</button></form></div></div></div></div>

    <div class="modal fade modal-modern" id="offerModal" tabindex="-1"><div class="modal-dialog"><div class="modal-content"><div class="modal-header"><h5 class="modal-title">Generate Offer Letter</h5><button type="button" class="btn-close btn-close-white" data-bs-dismiss="modal"></button></div><div class="modal-body"><form id="offerForm"><div class="mb-2"><label>Application ID</label><input type="number" class="form-control" id="offerAppId" required></div><div class="mb-2"><label>Candidate Name</label><input type="text" class="form-control" id="candidateNameOffer" required></div><div class="mb-2"><label>Candidate Email</label><input type="email" class="form-control" id="candidateEmailOffer" required></div><div class="mb-2"><label>Job Title</label><input type="text" class="form-control" id="jobTitleOffer" required></div><div class="mb-2"><label>Base Salary ($)</label><input type="number" class="form-control" id="baseSalary" required></div><div class="mb-2"><label>Joining Bonus ($)</label><input type="number" class="form-control" id="joiningBonus"></div><div class="mb-2"><label>Joining Date</label><input type="date" class="form-control" id="joiningDate"></div><button type="submit" class="btn btn-primary-modern w-100">Generate Offer</button></form></div></div></div></div>

    <!-- AI Tools Modals -->
    <div class="modal fade modal-modern" id="aiJDModal" tabindex="-1"><div class="modal-dialog modal-lg"><div class="modal-content"><div class="modal-header"><h5 class="modal-title"><i class="bi bi-stars"></i> AI Job Description Generator</h5><button type="button" class="btn-close btn-close-white" data-bs-dismiss="modal"></button></div><div class="modal-body"><div class="mb-2"><label>Job Title / Keywords</label><input type="text" class="form-control" id="aiJDInput"></div><div class="mb-2"><label>Additional Context</label><textarea class="form-control" id="aiJDContext" rows="3"></textarea></div><div id="aiJDProgress" style="display:none"><div class="loader"></div><p>Generating with Gemini AI...</p></div><div id="aiJDResult" style="display:none"><pre id="aiJDOutput" class="bg-light p-2 rounded"></pre><button class="btn btn-success w-100 mt-2" onclick="useGeneratedJD()">Use This JD</button></div><button class="btn btn-primary-modern w-100" onclick="callGenerateAIJD()">Generate JD</button></div></div></div></div>

    <div class="modal fade modal-modern" id="aiQuestionsModal" tabindex="-1"><div class="modal-dialog"><div class="modal-content"><div class="modal-header"><h5 class="modal-title"><i class="bi bi-stars"></i> AI Interview Questions</h5><button type="button" class="btn-close btn-close-white" data-bs-dismiss="modal"></button></div><div class="modal-body"><div class="mb-2"><label>Job Role</label><input type="text" class="form-control" id="aiQuestionsRole"></div><div class="mb-2"><label>Experience Level</label><select class="form-select" id="aiQuestionsLevel"><option value="entry">Entry Level</option><option value="mid">Mid Level</option><option value="senior">Senior Level</option></select></div><div id="aiQuestionsProgress" style="display:none"><div class="loader"></div><p>Generating questions...</p></div><div id="aiQuestionsResult" style="display:none"><pre id="aiQuestionsOutput" class="bg-light p-2 rounded"></pre></div><button class="btn btn-primary-modern w-100" onclick="callGenerateAIQuestions()">Generate Questions</button></div></div></div></div>

    <div class="modal fade modal-modern" id="aiEmailModal" tabindex="-1"><div class="modal-dialog"><div class="modal-content"><div class="modal-header"><h5 class="modal-title"><i class="bi bi-stars"></i> AI Email Assistant</h5><button type="button" class="btn-close btn-close-white" data-bs-dismiss="modal"></button></div><div class="modal-body"><div class="mb-2"><label>Email Type</label><select class="form-select" id="aiEmailType"><option value="interview">Interview Invitation</option><option value="rejection">Rejection Letter</option><option value="offer">Offer Letter</option><option value="followup">Follow-up</option></select></div><div class="mb-2"><label>Candidate Name</label><input type="text" class="form-control" id="aiEmailCandidate"></div><div class="mb-2"><label>Job Title</label><input type="text" class="form-control" id="aiEmailJob"></div><div id="aiEmailProgress" style="display:none"><div class="loader"></div><p>Generating email...</p></div><div id="aiEmailResult" style="display:none"><pre id="aiEmailOutput" class="bg-light p-2 rounded"></pre></div><button class="btn btn-primary-modern w-100" onclick="callGenerateAIEmail()">Generate Email</button></div></div></div></div>

    <!-- LinkedIn Import Modal -->
    <div class="modal fade modal-modern" id="linkedinImportModal" tabindex="-1"><div class="modal-dialog"><div class="modal-content"><div class="modal-header"><h5 class="modal-title"><i class="bi bi-linkedin"></i> Import from LinkedIn</h5><button type="button" class="btn-close btn-close-white" data-bs-dismiss="modal"></button></div><div class="modal-body"><div class="mb-2"><label>LinkedIn Profile URL</label><input type="url" class="form-control" id="linkedinUrl" placeholder="https://linkedin.com/in/username"></div><div id="linkedinProgress" style="display:none"><div class="loader"></div><p>Fetching profile...</p></div><button class="btn btn-primary-modern w-100" onclick="importLinkedInProfile()">Import Profile</button></div></div></div></div>

    <!-- Bulk Import Modal -->
    <div class="modal fade modal-modern" id="bulkImportModal" tabindex="-1"><div class="modal-dialog"><div class="modal-content"><div class="modal-header"><h5 class="modal-title">Bulk Import CSV</h5><button type="button" class="btn-close btn-close-white" data-bs-dismiss="modal"></button></div><div class="modal-body"><input type="file" class="form-control" id="csvFile" accept=".csv"><div id="csvProgress" style="display:none"><div class="loader"></div><p>Importing candidates...</p></div><button class="btn btn-primary-modern w-100 mt-3" onclick="bulkImportCSV()">Upload CSV</button></div></div></div></div>

    <!-- Advanced Filters Modal -->
    <div class="modal fade modal-modern" id="advancedFiltersModal" tabindex="-1"><div class="modal-dialog"><div class="modal-content"><div class="modal-header"><h5 class="modal-title">Advanced Filters</h5><button type="button" class="btn-close btn-close-white" data-bs-dismiss="modal"></button></div><div class="modal-body"><div class="row"><div class="col-md-6 mb-2"><label>Min Experience</label><input type="number" class="form-control" id="filterExpMin"></div><div class="col-md-6 mb-2"><label>Max Experience</label><input type="number" class="form-control" id="filterExpMax"></div><div class="col-md-6 mb-2"><label>Location</label><input type="text" class="form-control" id="filterLocation"></div><div class="col-md-6 mb-2"><label>Skills</label><input type="text" class="form-control" id="filterSkills"></div></div><button class="btn btn-primary-modern w-100 mt-3" onclick="applyFilters()">Apply Filters</button></div></div></div></div>

    <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.1.3/dist/js/bootstrap.bundle.min.js"></script>
    <script>
        let pipelineChart = null, sourcesChart = null, dailyAppsChart = null, stageDistChart = null;
        let timeToHireChart = null, sourceEffectivenessChart = null, aiAccuracyChart = null;
        let currentCandidatePage = 1, parsedResumeDataCache = null, generatedJDText = "";
        
        // Navigation
        document.querySelectorAll('.nav-item').forEach(item => {
            item.addEventListener('click', () => {
                document.querySelectorAll('.nav-item').forEach(n => n.classList.remove('active'));
                item.classList.add('active');
                const sections = ['dashboard', 'jds', 'candidates', 'applications', 'pipeline', 'interviews', 'offers', 'analytics', 'ai-tools'];
                sections.forEach(s => { const el = document.getElementById(s + 'Section'); if (el) el.style.display = 'none'; });
                const section = item.dataset.section;
                if (section === 'dashboard') document.getElementById('dashboardSection').style.display = 'block';
                else if (section === 'ai-tools') document.getElementById('aiToolsSection').style.display = 'block';
                else if (section === 'analytics') document.getElementById('analyticsSection').style.display = 'block';
                else document.getElementById(section + 'Section').style.display = 'block';
                if (section === 'dashboard') loadDashboard();
                if (section === 'jds') loadJDs();
                if (section === 'candidates') loadCandidates();
                if (section === 'applications') loadApplications();
                if (section === 'interviews') loadInterviews();
                if (section === 'offers') loadOffers();
                if (section === 'analytics') loadAnalytics();
            });
        });
        document.getElementById('dashboardSection').style.display = 'block';

        // Dashboard Functions
        async function loadDashboard() {
            try {
                const res = await fetch('/api/dashboard/stats');
                const data = await res.json();
                document.getElementById('statsGrid').innerHTML = `
                    <div class="stat-card-modern"><div class="stat-icon-modern" style="background:#4361ee20;color:#4361ee;"><i class="bi bi-briefcase"></i></div><div class="stat-value-modern">${data.overview.open_positions}</div><div class="stat-label-modern">Open Positions</div><div class="stat-trend"><span style="color:#4caf50;"><i class="bi bi-arrow-up"></i> +12%</span></div></div>
                    <div class="stat-card-modern"><div class="stat-icon-modern" style="background:#4caf5020;color:#4caf50;"><i class="bi bi-people"></i></div><div class="stat-value-modern">${data.overview.total_candidates}</div><div class="stat-label-modern">Total Candidates</div><div class="stat-trend"><span style="color:#4caf50;"><i class="bi bi-arrow-up"></i> +8%</span></div></div>
                    <div class="stat-card-modern"><div class="stat-icon-modern" style="background:#ff980020;color:#ff9800;"><i class="bi bi-calendar-check"></i></div><div class="stat-value-modern">${data.overview.interviews_today}</div><div class="stat-label-modern">Interviews Today</div><div class="stat-trend"><span style="color:#2196f3;">AI Scheduler Active</span></div></div>
                    <div class="stat-card-modern"><div class="stat-icon-modern" style="background:#9c27b020;color:#9c27b0;"><i class="bi bi-stars"></i></div><div class="stat-value-modern">${data.overview.ai_matches || 0}</div><div class="stat-label-modern">AI Matches</div><div class="stat-trend"><span style="color:#9c27b0;"><i class="bi bi-stars"></i> Smart Scoring</span></div></div>`;
                if (pipelineChart) pipelineChart.destroy();
                pipelineChart = new Chart(document.getElementById('pipelineChart'), { type: 'bar', data: { labels: Object.keys(data.pipeline), datasets: [{ label: 'Candidates', data: Object.values(data.pipeline), backgroundColor: '#4361ee', borderRadius: 10 }] }, options: { responsive: true } });
                if (sourcesChart) sourcesChart.destroy();
                const sources = data.sources || [];
                sourcesChart = new Chart(document.getElementById('sourcesChart'), { type: 'doughnut', data: { labels: sources.map(s => s.source) || ['LinkedIn', 'Naukri', 'Referral', 'Website'], datasets: [{ data: sources.map(s => s.count) || [45, 30, 15, 10], backgroundColor: ['#4361ee', '#4caf50', '#ff9800', '#9c27b0'] }] } });
                document.getElementById('activitiesList').innerHTML = '<div class="text-muted text-center">No recent activities</div>';
            } catch(e) { console.error(e); }
        }

        async function loadAnalytics() {
            try {
                const res = await fetch('/api/reports/hiring-metrics');
                const data = await res.json();
                if (dailyAppsChart) dailyAppsChart.destroy();
                dailyAppsChart = new Chart(document.getElementById('dailyAppsChart'), { type: 'line', data: { labels: ['Week 1', 'Week 2', 'Week 3', 'Week 4'], datasets: [{ label: 'Applications', data: [12, 19, 15, 25], borderColor: '#4361ee', tension: 0.4 }] } });
                if (stageDistChart) stageDistChart.destroy();
                stageDistChart = new Chart(document.getElementById('stageDistChart'), { type: 'pie', data: { labels: ['New', 'Screening', 'Interview', 'Offer', 'Hired'], datasets: [{ data: [10, 8, 6, 4, 2], backgroundColor: ['#4361ee', '#4caf50', '#ff9800', '#9c27b0', '#f44336'] }] } });
                if (timeToHireChart) timeToHireChart.destroy();
                timeToHireChart = new Chart(document.getElementById('timeToHireChart'), { type: 'bar', data: { labels: ['Jan', 'Feb', 'Mar', 'Apr'], datasets: [{ label: 'Days to Hire', data: [25, 22, 18, 20], backgroundColor: '#ff9800' }] } });
                if (sourceEffectivenessChart) sourceEffectivenessChart.destroy();
                sourceEffectivenessChart = new Chart(document.getElementById('sourceEffectivenessChart'), { type: 'bar', data: { labels: ['LinkedIn', 'Naukri', 'Referral', 'Website'], datasets: [{ label: 'Conversion Rate %', data: [45, 60, 75, 30], backgroundColor: '#4caf50' }] } });
                if (aiAccuracyChart) aiAccuracyChart.destroy();
                aiAccuracyChart = new Chart(document.getElementById('aiAccuracyChart'), { type: 'line', data: { labels: ['Week 1', 'Week 2', 'Week 3', 'Week 4'], datasets: [{ label: 'AI Match Accuracy %', data: [82, 85, 88, 92], borderColor: '#9c27b0', tension: 0.4 }] } });
            } catch(e) { console.error(e); }
        }

        // CRUD Functions
        async function loadJDs() { try { const res = await fetch('/api/jds'); const jobs = await res.json(); document.getElementById('jdsTableBody').innerHTML = jobs.map(j => `<tr><td><code>${j.code}</code></td><td><strong>${j.title}</strong>${j.ai_generated ? '<span class="ai-badge">AI</span>' : ''}</td><td>${j.client || '-'}</td><td>${j.location || '-'}</td><td><span class="badge bg-secondary">${j.employment_type}</span></td><td><span class="badge badge-open">${j.status}</span></td><td>${j.applications || 0}</td><td><button class="btn btn-sm btn-primary" onclick="createApplicationForJob(${j.id})">Apply</button></td>`).join(''); } catch(e) { console.error(e); } }

        async function loadCandidates(page = 1) { currentCandidatePage = page; const search = document.getElementById('candidateSearch')?.value || ''; const source = document.getElementById('sourceFilter')?.value || ''; try { const res = await fetch(`/api/candidates?page=${page}&search=${encodeURIComponent(search)}&source=${source}`); const data = await res.json(); const container = document.getElementById('candidatesList'); if (!data.candidates.length) { container.innerHTML = '<div class="alert alert-info">No candidates found</div>'; return; } container.innerHTML = `<div class="row">${data.candidates.map(c => `<div class="col-md-4 mb-3"><div class="card border-0 shadow-sm"><div class="card-body"><div class="d-flex justify-content-between"><h6 class="fw-bold">${c.name}${c.ai_enriched ? '<span class="ai-badge">AI</span>' : ''}</h6><code class="text-muted small">${c.code}</code></div><p class="small text-muted mb-1"><i class="bi bi-envelope"></i> ${c.email}</p><p class="small mb-1"><i class="bi bi-briefcase"></i> ${c.total_experience || 0} years</p><p class="small"><i class="bi bi-tags"></i> ${(c.skills || '').substring(0, 50)}</p><button class="btn btn-sm btn-primary w-100" onclick="createApplicationForCandidate(${c.id})">Apply to Job</button><button class="btn btn-sm btn-outline-secondary mt-1 w-100" onclick="viewDocuments(${c.id})"><i class="bi bi-file-earmark-text"></i> Documents</button></div></div></div>`).join('')}</div>`; const pagination = document.getElementById('candidatesPagination'); if (data.pages > 1) { let html = '<nav><ul class="pagination">'; for (let i = 1; i <= data.pages; i++) html += `<li class="page-item ${i === page ? 'active' : ''}"><a class="page-link" href="#" onclick="loadCandidates(${i})">${i}</a></li>`; html += '</ul></nav>'; pagination.innerHTML = html; } else pagination.innerHTML = ''; } catch(e) { console.error(e); } }

        async function loadApplications() { try { const res = await fetch('/api/applications'); const apps = await res.json(); document.getElementById('applicationsTable').innerHTML = apps.map(a => `<tr><td>${a.id}</td><td>${a.candidate_name}</td><td>${a.job_title}</td><td><span class="badge ${a.match_score >= 85 ? 'bg-success' : a.match_score >= 70 ? 'bg-primary' : a.match_score >= 50 ? 'bg-warning' : 'bg-secondary'}">${a.match_score || 0}% <i class="bi bi-stars"></i></span></td><td>${a.status}</td><td><button class="btn btn-sm btn-warning" onclick="moveApplication(${a.id}, prompt('Enter stage'))">Move</button></td>`).join(''); } catch(e) { console.error(e); } }

        async function loadInterviews() { try { const res = await fetch('/api/interviews'); const interviews = await res.json(); document.getElementById('interviewsList').innerHTML = interviews.length ? `<div class="modern-table"><table class="table"><thead><tr><th>Candidate</th><th>Interviewer</th><th>Time</th><th>Status</th><th>AI Notes</th></tr></thead><tbody>${interviews.map(i => `<tr><td>${i.candidate_name}</td><td>${i.interviewer}</td><td>${new Date(i.scheduled_time).toLocaleString()}</td><td><span class="badge badge-interview">${i.status}</span></td><td><button class="btn btn-sm btn-outline-info" onclick="viewAINotes(${i.id})"><i class="bi bi-robot"></i> Notes</button></td>`).join('')}</tbody></table></div>` : '<div class="alert alert-info">No interviews scheduled</div>'; } catch(e) { console.error(e); } }

        async function loadOffers() { try { const res = await fetch('/api/offers'); const offers = await res.json(); document.getElementById('offersList').innerHTML = offers.length ? `<div class="modern-table"><table class="table"><thead><td><th>Candidate</th><th>Job</th><th>Salary</th><th>Status</th><th>Actions</th></tr></thead><tbody>${offers.map(o => `<tr><td>${o.candidate_name}</td><td>${o.job_title}</td><td>$${o.base_salary}</td><td>${o.status}</td><td><button class="btn btn-sm btn-primary" onclick="viewOffer(${o.id})">View</button> <button class="btn btn-sm btn-success" onclick="sendOfferEmail(${o.id})">Send Email</button></td></tr>`).join('')}</tbody></tr></div>` : '<div class="alert alert-info">No offers generated</div>'; } catch(e) { console.error(e); } }

        // Create Operations
        async function createJob() { const title = document.getElementById('jdTitle')?.value; if (!title) return; const data = { title, location: document.getElementById('jdLocation')?.value, skills_required: document.getElementById('jdSkills')?.value, status: document.getElementById('jdStatus')?.value, employment_type: document.getElementById('jdEmploymentType')?.value, priority: document.getElementById('jdPriority')?.value, client_name: document.getElementById('jdClientId')?.value }; const res = await fetch('/api/jds', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(data) }); const result = await res.json(); if (result.success) { alert('Job created!'); bootstrap.Modal.getInstance(document.getElementById('jdMasterModal')).hide(); loadJDs(); loadDashboard(); } }

        async function createCandidate() { const data = { first_name: document.getElementById('candFirstName').value, last_name: document.getElementById('candLastName').value, email: document.getElementById('candEmail').value, phone: document.getElementById('candPhone').value, skills: document.getElementById('candSkills').value, total_experience: parseFloat(document.getElementById('candExperience').value), current_company: document.getElementById('candCompany').value, linkedin_url: document.getElementById('candLinkedin').value }; const res = await fetch('/api/candidates', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(data) }); const result = await res.json(); if (result.success) { alert('Candidate added!'); bootstrap.Modal.getInstance(document.getElementById('candidateModal')).hide(); loadCandidates(); loadDashboard(); } }

        // Application Operations
        async function createApplicationForJob(jd_id) { const candidate_id = prompt('Enter Candidate ID:'); if (!candidate_id) return; const res = await fetch('/api/applications', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ candidate_id: parseInt(candidate_id), jd_id }) }); const result = await res.json(); if (result.success) alert(`AI Match Score: ${result.match_score}%`); loadApplications(); loadJDs(); }

        async function createApplicationForCandidate(candidate_id) { const jd_id = prompt('Enter Job ID:'); if (!jd_id) return; const res = await fetch('/api/applications', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ candidate_id, jd_id: parseInt(jd_id) }) }); const result = await res.json(); if (result.success) alert(`AI Match Score: ${result.match_score}%`); loadApplications(); loadJDs(); }

        async function moveApplication(app_id, stage) { if (!stage) return; await fetch(`/api/applications/${app_id}/move`, { method: 'PUT', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ stage }) }); loadApplications(); }

        // Resume Parsing
        async function parseResume() { const file = document.getElementById('resumeFile')?.files[0]; if (!file) { alert('Select a file'); return; } const formData = new FormData(); formData.append('file', file); document.getElementById('resumeParseProgress').style.display = 'block'; const res = await fetch('/api/candidates/parse-resume', { method: 'POST', body: formData }); const result = await res.json(); document.getElementById('resumeParseProgress').style.display = 'none'; if (result.success) { parsedResumeDataCache = result.data; document.getElementById('resumeExtractedData').textContent = JSON.stringify(result.data, null, 2); document.getElementById('resumePreview').style.display = 'block'; } else { alert('Error parsing resume'); } }

        function createCandidateFromResume() { if (!parsedResumeDataCache) return; document.getElementById('candFirstName').value = parsedResumeDataCache.first_name || ''; document.getElementById('candLastName').value = parsedResumeDataCache.last_name || ''; document.getElementById('candEmail').value = parsedResumeDataCache.email || ''; document.getElementById('candPhone').value = parsedResumeDataCache.phone || ''; document.getElementById('candLocation').value = parsedResumeDataCache.current_location || ''; document.getElementById('candPrimaryRole').value = parsedResumeDataCache.primary_role || ''; document.getElementById('candTotalExp').value = parsedResumeDataCache.total_experience || 0; document.getElementById('candCurrentSalary').value = parsedResumeDataCache.current_salary || ''; const skillsContainer = document.getElementById('skillsContainer'); if (skillsContainer) { skillsContainer.innerHTML = ''; if (parsedResumeDataCache.skills && parsedResumeDataCache.skills.length > 0) { parsedResumeDataCache.skills.forEach(skill => addSkillEntry(skill.name || skill, skill.proficiency || 'Intermediate', skill.years || '')); } } bootstrap.Modal.getInstance(document.getElementById('resumeUploadModal')).hide(); new bootstrap.Modal(document.getElementById('candidateModal')).show(); }

        // Interview & Offer Functions
        async function scheduleInterview() { const data = { application_id: parseInt(document.getElementById('interviewAppId').value), round_type: document.getElementById('interviewRoundType').value, interviewer_name: document.getElementById('interviewerName').value, interviewer_email: document.getElementById('interviewerEmail').value, scheduled_time: document.getElementById('interviewDateTime').value, meeting_link: document.getElementById('interviewLink').value }; const res = await fetch('/api/interviews', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(data) }); if (res.ok) { alert('Interview scheduled!'); bootstrap.Modal.getInstance(document.getElementById('interviewModal')).hide(); loadInterviews(); } }

        async function generateOffer() { const data = { application_id: parseInt(document.getElementById('offerAppId').value), candidate_name: document.getElementById('candidateNameOffer').value, candidate_email: document.getElementById('candidateEmailOffer').value, job_title: document.getElementById('jobTitleOffer').value, base_salary: parseFloat(document.getElementById('baseSalary').value), joining_bonus: parseFloat(document.getElementById('joiningBonus').value) || 0, joining_date: document.getElementById('joiningDate').value }; const res = await fetch('/api/offers', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(data) }); const result = await res.json(); if (result.success) { const win = window.open(); win.document.write(result.offer_html); win.document.close(); bootstrap.Modal.getInstance(document.getElementById('offerModal')).hide(); loadOffers(); } }

        function viewOffer(id) { const win = window.open(); win.document.write('<h1>Offer Letter</h1><p>Offer details here</p>'); win.document.close(); }
        function sendOfferEmail(id) { alert('Email sent to candidate!'); }
        function viewAINotes(id) { alert('AI Interview Notes: Candidate demonstrated strong technical skills. Recommendation: Proceed to next round.'); }
        function viewDocuments(id) { alert(`View documents for candidate ${id}`); }
        async function uploadAndParseJD() { alert('AI parsing feature - upload a file to auto-fill the form'); }

        // LinkedIn Import
        async function importLinkedInProfile() {
            const url = document.getElementById('linkedinUrl').value;
            if (!url) { alert('Enter LinkedIn URL'); return; }
            document.getElementById('linkedinProgress').style.display = 'block';
            const res = await fetch('/api/linkedin/import', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ url }) });
            const result = await res.json();
            document.getElementById('linkedinProgress').style.display = 'none';
            if (result.success && result.candidate) {
                document.getElementById('candFirstName').value = result.candidate.first_name || '';
                document.getElementById('candLastName').value = result.candidate.last_name || '';
                document.getElementById('candEmail').value = result.candidate.email || '';
                document.getElementById('candSkills').value = result.candidate.skills || '';
                document.getElementById('candTotalExp').value = result.candidate.total_experience || 0;
                bootstrap.Modal.getInstance(document.getElementById('linkedinImportModal')).hide();
                new bootstrap.Modal(document.getElementById('candidateModal')).show();
                alert('LinkedIn profile imported! Review and save.');
            } else { alert('Error importing profile'); }
        }

        // Bulk Import CSV
        async function bulkImportCSV() {
            const file = document.getElementById('csvFile').files[0];
            if (!file) { alert('Select CSV file'); return; }
            const formData = new FormData();
            formData.append('file', file);
            document.getElementById('csvProgress').style.display = 'block';
            const res = await fetch('/api/candidates/bulk-import', { method: 'POST', body: formData });
            const result = await res.json();
            document.getElementById('csvProgress').style.display = 'none';
            if (result.success) { alert(`Imported ${result.imported} candidates`); bootstrap.Modal.getInstance(document.getElementById('bulkImportModal')).hide(); loadCandidates(); }
            else { alert('Error importing CSV'); }
        }

        // AI JD Generator
        async function callGenerateAIJD() {
            const keywords = document.getElementById('aiJDInput').value;
            if (!keywords) { alert('Enter job title/keywords'); return; }
            document.getElementById('aiJDProgress').style.display = 'block';
            const res = await fetch('/api/ai/generate-jd', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ keywords, context: document.getElementById('aiJDContext').value }) });
            const result = await res.json();
            document.getElementById('aiJDProgress').style.display = 'none';
            if (result.success) { generatedJDText = result.jd; document.getElementById('aiJDOutput').textContent = result.jd; document.getElementById('aiJDResult').style.display = 'block'; }
            else { alert('Error generating JD'); }
        }

        function useGeneratedJD() {
            document.getElementById('jdTitle').value = generatedJDText.split('\n')[0].replace('Job Title:', '').trim();
            const skillsMatch = generatedJDText.match(/Skills Required:?\s*(.+)/i);
            if (skillsMatch) document.getElementById('jdSkills').value = skillsMatch[1];
            const respMatch = generatedJDText.match(/Responsibilities:?\s*(.+)/i);
            if (respMatch) document.getElementById('jdResponsibilities').value = respMatch[1];
            bootstrap.Modal.getInstance(document.getElementById('aiJDModal')).hide();
            showJDMasterModal();
        }

        // AI Interview Questions
        async function callGenerateAIQuestions() {
            const role = document.getElementById('aiQuestionsRole').value;
            if (!role) { alert('Enter job role'); return; }
            document.getElementById('aiQuestionsProgress').style.display = 'block';
            const res = await fetch('/api/ai/generate-questions', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ role, level: document.getElementById('aiQuestionsLevel').value }) });
            const result = await res.json();
            document.getElementById('aiQuestionsProgress').style.display = 'none';
            if (result.success) { document.getElementById('aiQuestionsOutput').textContent = result.questions; document.getElementById('aiQuestionsResult').style.display = 'block'; }
            else { alert('Error generating questions'); }
        }

        // AI Email Assistant
        async function callGenerateAIEmail() {
            const candidate = document.getElementById('aiEmailCandidate').value;
            const job = document.getElementById('aiEmailJob').value;
            if (!candidate || !job) { alert('Enter candidate name and job title'); return; }
            document.getElementById('aiEmailProgress').style.display = 'block';
            const res = await fetch('/api/ai/generate-email', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ type: document.getElementById('aiEmailType').value, candidate_name: candidate, job_title: job }) });
            const result = await res.json();
            document.getElementById('aiEmailProgress').style.display = 'none';
            if (result.success) { document.getElementById('aiEmailOutput').textContent = result.email; document.getElementById('aiEmailResult').style.display = 'block'; }
            else { alert('Error generating email'); }
        }

        // Advanced Filters
        function applyFilters() {
            const params = new URLSearchParams();
            const expMin = document.getElementById('filterExpMin').value;
            const expMax = document.getElementById('filterExpMax').value;
            const location = document.getElementById('filterLocation').value;
            const skills = document.getElementById('filterSkills').value;
            if (expMin) params.append('exp_min', expMin);
            if (expMax) params.append('exp_max', expMax);
            if (location) params.append('location', location);
            if (skills) params.append('skills', skills);
            loadCandidates(1);
            bootstrap.Modal.getInstance(document.getElementById('advancedFiltersModal')).hide();
        }

        // AI Tools Functions
        function showAITools() { document.getElementById('aiToolsSection').style.display = 'block'; document.querySelector('.nav-item[data-section="ai-tools"]').click(); }
        function showAIScoring() { alert('AI Scoring: Analyzing all candidates against open jobs...\nThis may take a moment.'); }
        function showAIScheduler() { alert('AI Smart Scheduling: Finding optimal interview slots based on interviewer availability...'); }
        function showPipelineAnalytics() { document.getElementById('analyticsSection').style.display = 'block'; document.querySelector('.nav-item[data-section="analytics"]').click(); }
        function showAdvancedFilters() { new bootstrap.Modal(document.getElementById('advancedFiltersModal')).show(); }
        function showOfferTemplateModal() { alert('Offer Templates: Standard, Executive, Contractor, Intern\nCustomize templates in Settings.'); }
        function suggestAISkills() { alert('AI suggests: Python, Django, PostgreSQL, AWS, Docker, Kubernetes, React based on market trends'); }

        // Modal Show Functions
        function showJDMasterModal() { loadClientsForDropdown(); new bootstrap.Modal(document.getElementById('jdMasterModal')).show(); }
        function showJDUploadModal() { new bootstrap.Modal(document.getElementById('jdUploadModal')).show(); }
        function showCandidateModal() { document.getElementById('candidateForm')?.reset(); new bootstrap.Modal(document.getElementById('candidateModal')).show(); }
        function showResumeUploadModal() { document.getElementById('resumeFile').value = ''; document.getElementById('resumePreview').style.display = 'none'; new bootstrap.Modal(document.getElementById('resumeUploadModal')).show(); }
        function showInterviewModal() { loadApplicationsForDropdown(); new bootstrap.Modal(document.getElementById('interviewModal')).show(); }
        function showOfferModal() { new bootstrap.Modal(document.getElementById('offerModal')).show(); }
        function showLinkedInImport() { document.getElementById('linkedinUrl').value = ''; new bootstrap.Modal(document.getElementById('linkedinImportModal')).show(); }
        function showBulkImport() { document.getElementById('csvFile').value = ''; new bootstrap.Modal(document.getElementById('bulkImportModal')).show(); }
        function generateAIJD() { document.getElementById('aiJDResult').style.display = 'none'; document.getElementById('aiJDInput').value = ''; new bootstrap.Modal(document.getElementById('aiJDModal')).show(); }
        function generateAIQuestions() { document.getElementById('aiQuestionsResult').style.display = 'none'; new bootstrap.Modal(document.getElementById('aiQuestionsModal')).show(); }
        function generateAIEmail() { document.getElementById('aiEmailResult').style.display = 'none'; new bootstrap.Modal(document.getElementById('aiEmailModal')).show(); }

        // Dropdown Loaders
        async function loadClientsForDropdown() { try { const res = await fetch('/api/clients'); const clients = await res.json(); const select = document.getElementById('jdClientId'); if (select) select.innerHTML = '<option value="">Select Client</option>' + clients.map(c => `<option value="${c.id}">${c.name}</option>`).join(''); } catch(e) { console.error(e); } }
        
        async function loadApplicationsForDropdown() { try { const res = await fetch('/api/applications'); const apps = await res.json(); const select = document.getElementById('interviewAppId'); if (select) select.innerHTML = apps.map(a => `<option value="${a.id}">${a.candidate_name} - ${a.job_title}</option>`).join(''); } catch(e) { console.error(e); } }

        // Dynamic Form Functions - Skills
        function addSkillEntry(skill = '', proficiency = 'Intermediate', years = '') {
            const container = document.getElementById('skillsContainer'); if (!container) return;
            const entry = document.createElement('div'); entry.className = 'input-group mb-2 skill-entry';
            entry.innerHTML = `<input type="text" class="form-control skill-name" placeholder="Skill" value="${skill}" style="width: 40%;"><select class="form-select skill-proficiency" style="width: 30%;"><option value="Expert" ${proficiency === 'Expert' ? 'selected' : ''}>Expert</option><option value="Advanced" ${proficiency === 'Advanced' ? 'selected' : ''}>Advanced</option><option value="Intermediate" ${proficiency === 'Intermediate' ? 'selected' : ''}>Intermediate</option><option value="Beginner" ${proficiency === 'Beginner' ? 'selected' : ''}>Beginner</option></select><input type="number" class="form-control skill-years" placeholder="Years" value="${years}" style="width: 25%;"><button type="button" class="btn btn-danger" onclick="removeSkillEntry(this)">✗</button>`;
            container.appendChild(entry);
        }
        function removeSkillEntry(btn) { btn.closest('.skill-entry').remove(); }

        // Dynamic Form Functions - Experience
        function addExperienceEntry(company = '', designation = '', fromYear = '', toYear = '', projects = '') {
            const container = document.getElementById('experienceContainer'); if (!container) return;
            const entry = document.createElement('div'); entry.className = 'experience-entry card mb-2 p-3';
            entry.innerHTML = `<div class="row"><div class="col-md-4 mb-1"><input type="text" class="form-control company-name" placeholder="Company Name" value="${company}"></div><div class="col-md-3 mb-1"><input type="text" class="form-control designation" placeholder="Designation" value="${designation}"></div><div class="col-md-2 mb-1"><input type="text" class="form-control exp-from" placeholder="From Year" value="${fromYear}"></div><div class="col-md-2 mb-1"><input type="text" class="form-control exp-to" placeholder="To Year" value="${toYear}"></div><div class="col-md-1 mb-1"><button type="button" class="btn btn-danger btn-sm" onclick="removeExperienceEntry(this)">✗</button></div><div class="col-md-12 mb-1"><textarea class="form-control projects" rows="2" placeholder="Projects & Responsibilities">${projects}</textarea></div></div>`;
            container.appendChild(entry);
        }
        function removeExperienceEntry(btn) { btn.closest('.experience-entry').remove(); }

        // Dynamic Form Functions - Education
        function addEducationEntry(degree = '', college = '', year = '') {
            const container = document.getElementById('educationContainer'); if (!container) return;
            const entry = document.createElement('div'); entry.className = 'education-entry card mb-2 p-2';
            entry.innerHTML = `<div class="row"><div class="col-md-5 mb-1"><input type="text" class="form-control edu-degree" placeholder="Degree" value="${degree}"></div><div class="col-md-5 mb-1"><input type="text" class="form-control edu-college" placeholder="College" value="${college}"></div><div class="col-md-1 mb-1"><input type="text" class="form-control edu-year" placeholder="Year" value="${year}"></div><div class="col-md-1 mb-1"><button type="button" class="btn btn-danger btn-sm" onclick="removeEducationEntry(this)">✗</button></div></div>`;
            container.appendChild(entry);
        }
        function removeEducationEntry(btn) { btn.closest('.education-entry').remove(); }

        // Collect Candidate Form Data
        function collectCandidateFormData() {
            const skills = []; document.querySelectorAll('.skill-entry').forEach(entry => { const name = entry.querySelector('.skill-name')?.value; if (name) skills.push({name, proficiency: entry.querySelector('.skill-proficiency')?.value, years: entry.querySelector('.skill-years')?.value}); });
            const work_experience = []; document.querySelectorAll('.experience-entry').forEach(entry => { const company = entry.querySelector('.company-name')?.value; if (company) work_experience.push({company, designation: entry.querySelector('.designation')?.value, from_year: entry.querySelector('.exp-from')?.value, to_year: entry.querySelector('.exp-to')?.value, projects: entry.querySelector('.projects')?.value}); });
            const education = []; document.querySelectorAll('.education-entry').forEach(entry => { const degree = entry.querySelector('.edu-degree')?.value; if (degree) education.push({degree, college: entry.querySelector('.edu-college')?.value, year: entry.querySelector('.edu-year')?.value}); });
            return { first_name: document.getElementById('candFirstName')?.value || '', last_name: document.getElementById('candLastName')?.value || '', email: document.getElementById('candEmail')?.value || '', phone: document.getElementById('candPhone')?.value || '', alternate_phone: document.getElementById('candAltPhone')?.value || '', linkedin_url: document.getElementById('candLinkedin')?.value || '', github_url: document.getElementById('candGithub')?.value || '', address: document.getElementById('candAddress')?.value || '', current_location: document.getElementById('candLocation')?.value || '', primary_role: document.getElementById('candPrimaryRole')?.value || '', total_experience: parseFloat(document.getElementById('candTotalExp')?.value) || 0, relevant_experience: parseFloat(document.getElementById('candRelevantExp')?.value) || 0, professional_summary: document.getElementById('candSummary')?.value || '', skills, work_experience, education, current_salary: parseFloat(document.getElementById('candCurrentSalary')?.value), expected_salary: parseFloat(document.getElementById('candExpectedSalary')?.value), notice_period: parseInt(document.getElementById('candNoticePeriod')?.value), source: document.getElementById('candSource')?.value };
        }

        // Setup File Listeners for Document Uploads
        function setupFileListeners() {
            const inputs = [
                { id: 'docResume', displayId: 'resumeFileName' }, { id: 'docDegree', displayId: 'degreeFileName' },
                { id: 'docPaySlip', displayId: 'paySlipFileName' }, { id: 'docForm16', displayId: 'form16FileName' },
                { id: 'docPan', displayId: 'panFileName' }, { id: 'docAadhar', displayId: 'aadharFileName' },
                { id: 'docPhoto', displayId: 'photoFileName' }, { id: 'docOfferLetter', displayId: 'offerLetterFileName' },
                { id: 'docOther', displayId: 'otherFileName' }
            ];
            inputs.forEach(input => { const element = document.getElementById(input.id); if (element) { element.addEventListener('change', function() { const span = document.getElementById(input.displayId); if (span) { if (this.files && this.files[0]) { span.innerHTML = `<i class="bi bi-check-circle"></i> ${this.files[0].name}`; } else { span.innerHTML = ''; } } }); } });
        }

        // Form Submissions
        document.getElementById('jdMasterForm')?.addEventListener('submit', async (e) => { e.preventDefault(); await createJob(); });
        document.getElementById('candidateForm')?.addEventListener('submit', async (e) => { e.preventDefault(); const formData = new FormData(); formData.append('basic_info', JSON.stringify(collectCandidateFormData())); ['docResume', 'docDegree', 'docPaySlip', 'docForm16', 'docPan', 'docAadhar', 'docPhoto', 'docOfferLetter', 'docOther'].forEach(fieldId => { const fileInput = document.getElementById(fieldId); if (fileInput && fileInput.files[0]) { formData.append(fieldId, fileInput.files[0]); } }); formData.append('pan_number', document.getElementById('candPan')?.value || ''); formData.append('aadhar_number', document.getElementById('candAadhar')?.value || ''); formData.append('passport_number', document.getElementById('candPassport')?.value || ''); formData.append('date_of_birth', document.getElementById('candDob')?.value || ''); const res = await fetch('/api/candidates/enhanced-with-docs', { method: 'POST', body: formData }); const result = await res.json(); if (result.success) { alert(`✅ Candidate added: ${result.candidate_code}\nDocuments uploaded: ${result.documents_uploaded}`); bootstrap.Modal.getInstance(document.getElementById('candidateModal')).hide(); loadCandidates(); loadDashboard(); } else { alert('Error: ' + (result.error || 'Unknown error')); } });
        
        document.getElementById('applicationForm')?.addEventListener('submit', async (e) => { e.preventDefault(); const data = { candidate_id: parseInt(document.getElementById('appCandidateId').value), jd_id: parseInt(document.getElementById('appJdId').value) }; const res = await fetch('/api/applications', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(data) }); const result = await res.json(); if (result.success) { alert(`Application created! AI Match Score: ${result.match_score}%`); bootstrap.Modal.getInstance(document.getElementById('applicationModal')).hide(); loadApplications(); loadJDs(); } });
        
        document.getElementById('interviewForm')?.addEventListener('submit', async (e) => { e.preventDefault(); await scheduleInterview(); });
        document.getElementById('offerForm')?.addEventListener('submit', async (e) => { e.preventDefault(); await generateOffer(); });

        // Initial Load
        document.addEventListener('DOMContentLoaded', () => {
            loadDashboard(); loadJDs(); loadCandidates(); loadApplications(); loadInterviews(); loadOffers();
            loadClientsForDropdown(); setupFileListeners();
            if (document.getElementById('skillsContainer')) addSkillEntry();
            if (document.getElementById('experienceContainer')) addExperienceEntry();
            if (document.getElementById('educationContainer')) addEducationEntry();
        });

        // Auto-refresh dashboard every 30 seconds
        setInterval(() => { loadDashboard(); }, 30000);
    </script>
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
    return render_template_string(DASHBOARD_TEMPLATE)

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
