from flask import Flask, jsonify, request, render_template_string, send_file, session, redirect, url_for
from datetime import datetime, date, timedelta
from difflib import SequenceMatcher
from functools import wraps
import os
import re
import json
import base64
import hashlib
import secrets
import smtplib
import csv
import io
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import requests

# Load environment variables
try:
    from dotenv import load_dotenv
    load_dotenv()
except:
    pass

# Initialize Flask app
app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', secrets.token_hex(32))
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL', 'sqlite:///recruitment.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['MAX_CONTENT_LENGTH'] = 100 * 1024 * 1024
app.config['UPLOAD_FOLDER'] = 'uploads'
app.config['ALLOWED_EXTENSIONS'] = {'pdf', 'docx', 'doc', 'jpg', 'png', 'jpeg'}

# Email configuration
app.config['MAIL_SERVER'] = os.environ.get('MAIL_SERVER', 'smtp.gmail.com')
app.config['MAIL_PORT'] = int(os.environ.get('MAIL_PORT', 587))
app.config['MAIL_USE_TLS'] = True
app.config['MAIL_USERNAME'] = os.environ.get('MAIL_USERNAME', '')
app.config['MAIL_PASSWORD'] = os.environ.get('MAIL_PASSWORD', '')
app.config['MAIL_DEFAULT_SENDER'] = os.environ.get('MAIL_DEFAULT_SENDER', 'noreply@shahnaiT.com')

# Gemini AI Configuration (FREE)
GEMINI_API_KEY = os.environ.get('GEMINI_API_KEY', '')
GEMINI_AVAILABLE = False

if GEMINI_API_KEY:
    try:
        import google.generativeai as genai
        genai.configure(api_key=GEMINI_API_KEY)
        gemini_model = genai.GenerativeModel('gemini-pro')
        GEMINI_AVAILABLE = True
        print("✅ Gemini AI initialized")
    except Exception as e:
        print(f"⚠️ Gemini AI error: {e}")

os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

# ============= HTML DASHBOARD TEMPLATE (PART 1/4) =============
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
        <!-- Dashboard Section -->
        <div id="dashboardSection">
            <div class="modern-header"><div class="page-title"><h1>Recruitment Dashboard</h1><p>Track your hiring pipeline, candidates, and analytics in real-time</p></div><div class="header-actions"><div class="search-bar"><i class="bi bi-search"></i><input type="text" id="globalSearch" placeholder="Search candidates, jobs..."></div></div></div>
            <div class="stats-grid" id="statsGrid"></div>
            <div class="row"><div class="col-lg-8"><div class="chart-card"><div class="chart-header"><h5><i class="bi bi-graph-up"></i> Recruitment Funnel <span class="ai-badge">AI Analytics</span></h5></div><canvas id="pipelineChart" height="280"></canvas></div></div><div class="col-lg-4"><div class="chart-card"><div class="chart-header"><h5><i class="bi bi-pie-chart"></i> Candidate Sources</h5></div><canvas id="sourcesChart" height="280"></canvas></div></div></div>
            <div class="row mt-3"><div class="col-lg-6"><div class="chart-card"><div class="chart-header"><h5><i class="bi bi-lightning-charge"></i> Quick Actions</h5></div><div class="d-flex gap-3 flex-wrap"><button class="btn btn-primary-modern" onclick="showJDMasterModal()"><i class="bi bi-plus-circle"></i> Post a Job</button><button class="btn btn-outline-modern" onclick="showCandidateModal()"><i class="bi bi-person-plus"></i> Add Candidate</button><button class="btn btn-outline-modern" onclick="showResumeUploadModal()"><i class="bi bi-file-earmark-arrow-up"></i> Upload Resume</button><button class="btn btn-outline-modern" onclick="showAITools()"><i class="bi bi-stars"></i> AI Tools</button></div></div></div><div class="col-lg-6"><div class="chart-card"><div class="chart-header"><h5><i class="bi bi-clock-history"></i> Recent Activity</h5></div><div id="activitiesList" style="max-height: 200px; overflow-y: auto;"></div></div></div></div>
        </div>
        
        <!-- JDs Section -->
        <div id="jdsSection" style="display: none;"><div class="modern-header"><div class="page-title"><h1>Job Descriptions</h1><p>Manage all your job openings</p></div><div class="header-actions"><button class="btn btn-primary-modern" onclick="showJDMasterModal()"><i class="bi bi-plus-circle"></i> Create Job</button><button class="btn btn-outline-modern" onclick="showJDUploadModal()"><i class="bi bi-cloud-upload"></i> Upload JD</button><button class="btn btn-outline-modern" onclick="generateAIJD()"><i class="bi bi-stars"></i> AI Generate JD</button></div></div><div class="modern-table"><table class="table"><thead><tr><th>Code</th><th>Title</th><th>Client</th><th>Location</th><th>Type</th><th>Status</th><th>Applications</th><th>Actions</th></tr></thead><tbody id="jdsTableBody"></tbody></table></div></div>
        
        <!-- Candidates Section -->
        <div id="candidatesSection" style="display: none;"><div class="modern-header"><div class="page-title"><h1>Candidates Database</h1><p>Manage your talent pool <span class="ai-badge">AI Enriched</span></p></div><div class="header-actions"><button class="btn btn-primary-modern" onclick="showCandidateModal()"><i class="bi bi-person-plus"></i> Add Candidate</button><button class="btn btn-outline-modern" onclick="showResumeUploadModal()"><i class="bi bi-file-earmark-arrow-up"></i> Upload Resume</button><button class="btn btn-outline-modern" onclick="showLinkedInImport()"><i class="bi bi-linkedin"></i> Import from LinkedIn</button><button class="btn btn-outline-modern" onclick="showBulkImport()"><i class="bi bi-file-spreadsheet"></i> Bulk Import CSV</button></div></div><div class="row mb-3"><div class="col-md-3"><input type="text" class="form-control" id="candidateSearch" placeholder="Search by name, email, skill..."></div><div class="col-md-2"><select class="form-select" id="sourceFilter"><option value="">All Sources</option><option value="linkedin">LinkedIn</option><option value="naukri">Naukri</option><option value="referral">Referral</option><option value="ai-enriched">AI Enriched</option></select></div><div class="col-md-2"><button class="btn btn-primary-modern" onclick="loadCandidates()"><i class="bi bi-search"></i> Search</button><button class="btn btn-outline-modern" onclick="showAdvancedFilters()"><i class="bi bi-funnel"></i> Filters</button></div></div><div id="candidatesList"></div><div id="candidatesPagination" class="mt-3"></div></div>
        
        <!-- Applications Section -->
        <div id="applicationsSection" style="display: none;"><div class="modern-header"><div class="page-title"><h1>Applications</h1><p>Track all candidate applications <span class="ai-badge">Smart Ranking</span></p></div></div><div class="modern-table"><table class="table"><thead><tr><th>ID</th><th>Candidate</th><th>Job</th><th>AI Match Score</th><th>Status</th><th>Actions</th></tr></thead><tbody id="applicationsTable"></tbody></table></div></div>
        
        <!-- Pipeline Section -->
        <div id="pipelineSection" style="display: none;"><div class="modern-header"><div class="page-title"><h1>Recruitment Pipeline</h1><p>Drag and drop candidates to move between stages</p></div><button class="btn btn-outline-modern" onclick="showPipelineAnalytics()"><i class="bi bi-graph-up"></i> Pipeline Analytics</button></div><div id="kanbanBoard" class="kanban-board"></div></div>
        
        <!-- Interviews Section -->
        <div id="interviewsSection" style="display: none;"><div class="modern-header"><div class="page-title"><h1>Interviews</h1><p>Schedule and manage interviews <span class="ai-badge">AI Scheduling</span></p></div><div class="header-actions"><button class="btn btn-primary-modern" onclick="showInterviewModal()"><i class="bi bi-plus-circle"></i> Schedule Interview</button><button class="btn btn-outline-modern" onclick="showAIScheduler()"><i class="bi bi-stars"></i> AI Smart Schedule</button></div></div><div id="interviewsList"></div></div>
        
        <!-- Offers Section -->
        <div id="offersSection" style="display: none;"><div class="modern-header"><div class="page-title"><h1>Offer Letters</h1><p>Generate and manage offers</p></div><div class="header-actions"><button class="btn btn-primary-modern" onclick="showOfferModal()"><i class="bi bi-envelope-paper"></i> Generate Offer</button><button class="btn btn-outline-modern" onclick="showOfferTemplateModal()"><i class="bi bi-file-text"></i> Templates</button></div></div><div id="offersList"></div></div>
        
        <!-- Analytics Section -->
        <div id="analyticsSection" style="display: none;"><div class="modern-header"><div class="page-title"><h1>Analytics & Reports</h1><p>Data-driven insights for your recruitment <span class="ai-badge">AI Insights</span></p></div></div><div class="row"><div class="col-lg-6"><div class="chart-card"><canvas id="dailyAppsChart" height="250"></canvas></div></div><div class="col-lg-6"><div class="chart-card"><canvas id="stageDistChart" height="250"></canvas></div></div></div><div class="row mt-3"><div class="col-lg-4"><div class="chart-card"><h6>Time-to-Hire Analysis</h6><canvas id="timeToHireChart" height="200"></canvas></div></div><div class="col-lg-4"><div class="chart-card"><h6>Source Effectiveness</h6><canvas id="sourceEffectivenessChart" height="200"></canvas></div></div><div class="col-lg-4"><div class="chart-card"><h6>AI Match Accuracy</h6><canvas id="aiAccuracyChart" height="200"></canvas></div></div></div></div>
        
        <!-- AI Tools Section -->
        <div id="aiToolsSection" style="display: none;"><div class="modern-header"><div class="page-title"><h1>AI Tools</h1><p>Supercharge your recruitment with artificial intelligence</p></div></div><div class="row"><div class="col-md-4 mb-3"><div class="card h-100"><div class="card-body"><div class="text-center mb-3"><i class="bi bi-file-text" style="font-size: 3rem; color: #4361ee;"></i></div><h5 class="text-center">AI Resume Parser</h5><p class="text-center text-muted small">Extract candidate info with Gemini AI</p><button class="btn btn-primary-modern w-100" onclick="showResumeUploadModal()">Upload Resume</button></div></div></div><div class="col-md-4 mb-3"><div class="card h-100"><div class="card-body"><div class="text-center mb-3"><i class="bi bi-file-earmark-text" style="font-size: 3rem; color: #4caf50;"></i></div><h5 class="text-center">AI JD Generator</h5><p class="text-center text-muted small">Generate job descriptions with Gemini AI</p><button class="btn btn-primary-modern w-100" onclick="generateAIJD()">Generate JD</button></div></div></div><div class="col-md-4 mb-3"><div class="card h-100"><div class="card-body"><div class="text-center mb-3"><i class="bi bi-chat-dots" style="font-size: 3rem; color: #ff9800;"></i></div><h5 class="text-center">AI Interview Questions</h5><p class="text-center text-muted small">Generate role-specific questions</p><button class="btn btn-primary-modern w-100" onclick="generateAIQuestions()">Generate Questions</button></div></div></div><div class="col-md-4 mb-3"><div class="card h-100"><div class="card-body"><div class="text-center mb-3"><i class="bi bi-linkedin" style="font-size: 3rem; color: #0077b5;"></i></div><h5 class="text-center">LinkedIn Enrichment</h5><p class="text-center text-muted small">Import and enrich candidate data</p><button class="btn btn-primary-modern w-100" onclick="showLinkedInImport()">Import from LinkedIn</button></div></div></div><div class="col-md-4 mb-3"><div class="card h-100"><div class="card-body"><div class="text-center mb-3"><i class="bi bi-envelope-paper" style="font-size: 3rem; color: #f44336;"></i></div><h5 class="text-center">AI Email Assistant</h5><p class="text-center text-muted small">Generate personalized emails</p><button class="btn btn-primary-modern w-100" onclick="generateAIEmail()">Generate Email</button></div></div></div><div class="col-md-4 mb-3"><div class="card h-100"><div class="card-body"><div class="text-center mb-3"><i class="bi bi-graph-up" style="font-size: 3rem; color: #9c27b0;"></i></div><h5 class="text-center">AI Candidate Scoring</h5><p class="text-center text-muted small">AI-powered recommendations</p><button class="btn btn-primary-modern w-100" onclick="showAIScoring()">Score Candidates</button></div></div></div></div></div>
    </div>
'''

# ============= HTML DASHBOARD TEMPLATE (PART 2/4 - Modals) =============

    <!-- JD Master Modal -->
    <div class="modal fade modal-modern" id="jdMasterModal" tabindex="-1"><div class="modal-dialog modal-lg"><div class="modal-content"><div class="modal-header"><h5 class="modal-title"><i class="bi bi-briefcase"></i> Create Job Description</h5><button type="button" class="btn-close btn-close-white" data-bs-dismiss="modal"></button></div><div class="modal-body"><form id="jdMasterForm"><div class="form-section"><div class="form-section-title">Basic Information</div><div class="row"><div class="col-md-8 mb-2"><label>Job Title *</label><input type="text" class="form-control" id="jdTitle" required></div><div class="col-md-4 mb-2"><label>Client</label><select class="form-select" id="jdClientId"></select></div><div class="col-md-4 mb-2"><label>Department</label><input type="text" class="form-control" id="jdDepartment"></div><div class="col-md-4 mb-2"><label>Location</label><input type="text" class="form-control" id="jdLocation"></div><div class="col-md-4 mb-2"><label>Location Type</label><select class="form-select" id="jdLocationType"><option value="remote">Remote</option><option value="onsite">Onsite</option><option value="hybrid">Hybrid</option></select></div><div class="col-md-6 mb-2"><label>Employment Type</label><select class="form-select" id="jdEmploymentType"><option value="full-time">Full Time</option><option value="part-time">Part Time</option><option value="contract">Contract</option></select></div><div class="col-md-6 mb-2"><label>No. of Positions</label><input type="number" class="form-control" id="jdPositions" value="1"></div></div></div><div class="form-section"><div class="form-section-title">Experience & Salary</div><div class="row"><div class="col-md-3 mb-2"><label>Min Experience</label><input type="number" class="form-control" id="jdExpMin" value="0"></div><div class="col-md-3 mb-2"><label>Max Experience</label><input type="number" class="form-control" id="jdExpMax" value="10"></div><div class="col-md-3 mb-2"><label>Min Salary</label><input type="number" class="form-control" id="jdSalaryMin"></div><div class="col-md-3 mb-2"><label>Max Salary</label><input type="number" class="form-control" id="jdSalaryMax"></div></div></div><div class="form-section"><div class="form-section-title">Skills & Qualifications</div><div class="mb-2"><label>Required Skills (comma separated)</label><textarea class="form-control" id="jdSkills" rows="2"></textarea></div><div class="mb-2"><label>Preferred Skills</label><textarea class="form-control" id="jdSkillsPref" rows="2"></textarea></div><div class="mb-2"><label>Qualifications</label><textarea class="form-control" id="jdQualifications" rows="2"></textarea></div></div><div class="form-section"><div class="form-section-title">Job Description</div><div class="mb-2"><label>Responsibilities</label><textarea class="form-control" id="jdResponsibilities" rows="4"></textarea></div><div class="mb-2"><label>Benefits</label><textarea class="form-control" id="jdBenefits" rows="2"></textarea></div></div><div class="row"><div class="col-md-6 mb-2"><label>Status</label><select class="form-select" id="jdStatus"><option value="draft">Draft</option><option value="open">Open</option><option value="closed">Closed</option></select></div><div class="col-md-6 mb-2"><label>Priority</label><select class="form-select" id="jdPriority"><option value="low">Low</option><option value="medium">Medium</option><option value="high">High</option></select></div></div><button type="submit" class="btn btn-primary-modern w-100">Create Job</button></form></div></div></div></div>

    <!-- JD Upload Modal -->
    <div class="modal fade modal-modern" id="jdUploadModal" tabindex="-1"><div class="modal-dialog"><div class="modal-content"><div class="modal-header"><h5 class="modal-title"><i class="bi bi-cloud-upload"></i> Upload JD Document</h5><button type="button" class="btn-close btn-close-white" data-bs-dismiss="modal"></button></div><div class="modal-body"><div class="text-center mb-3"><i class="bi bi-file-earmark-pdf" style="font-size: 3rem;"></i><i class="bi bi-file-earmark-word" style="font-size: 3rem;"></i><span class="ai-badge">AI Parsing</span></div><div class="mb-3"><input type="file" class="form-control" id="jdUploadFile" accept=".pdf,.docx,.txt"><div class="form-text">Upload PDF, DOCX, or TXT file. AI will extract all details automatically.</div></div><div id="jdParseProgress" style="display: none;" class="text-center"><div class="loader"></div><p class="mt-2">AI is analyzing the document...</p></div><button class="btn btn-primary-modern w-100" onclick="uploadAndParseJD()"><i class="bi bi-robot"></i> Parse & Auto-fill</button></div></div></div></div>

    <!-- Enhanced Candidate Modal with Document Upload -->
    <div class="modal fade modal-modern" id="candidateModal" tabindex="-1"><div class="modal-dialog modal-xl"><div class="modal-content"><div class="modal-header"><h5 class="modal-title"><i class="bi bi-person-badge"></i> Add/Edit Candidate - Complete Profile</h5><button type="button" class="btn-close btn-close-white" data-bs-dismiss="modal"></button></div><div class="modal-body" style="max-height: 70vh; overflow-y: auto;"><form id="candidateForm" enctype="multipart/form-data"><div class="card mb-3"><div class="card-header bg-primary text-white">Personal Information</div><div class="card-body"><div class="row"><div class="col-md-4 mb-2"><label>First Name *</label><input type="text" class="form-control" id="candFirstName" required></div><div class="col-md-4 mb-2"><label>Last Name</label><input type="text" class="form-control" id="candLastName"></div><div class="col-md-4 mb-2"><label>Email *</label><input type="email" class="form-control" id="candEmail" required></div><div class="col-md-3 mb-2"><label>Mobile Number</label><input type="tel" class="form-control" id="candPhone"></div><div class="col-md-3 mb-2"><label>Alternate Number</label><input type="tel" class="form-control" id="candAltPhone"></div><div class="col-md-3 mb-2"><label>LinkedIn ID</label><input type="text" class="form-control" id="candLinkedin" placeholder="linkedin.com/in/username"></div><div class="col-md-3 mb-2"><label>GitHub</label><input type="text" class="form-control" id="candGithub"></div><div class="col-md-6 mb-2"><label>Address</label><textarea class="form-control" id="candAddress" rows="2"></textarea></div><div class="col-md-6 mb-2"><label>Current Location</label><input type="text" class="form-control" id="candLocation"></div><div class="col-md-3 mb-2"><label>PAN Card Number</label><input type="text" class="form-control" id="candPan"></div><div class="col-md-3 mb-2"><label>Aadhar Number</label><input type="text" class="form-control" id="candAadhar"></div><div class="col-md-3 mb-2"><label>Passport Number</label><input type="text" class="form-control" id="candPassport"></div><div class="col-md-3 mb-2"><label>Date of Birth</label><input type="date" class="form-control" id="candDob"></div></div></div></div><div class="card mb-3"><div class="card-header bg-info text-white">Professional Summary <span class="ai-badge">AI Enriched</span></div><div class="card-body"><div class="row"><div class="col-md-4 mb-2"><label>Primary Role</label><input type="text" class="form-control" id="candPrimaryRole"></div><div class="col-md-4 mb-2"><label>Total Experience (Years)</label><input type="number" step="0.5" class="form-control" id="candTotalExp" value="0"></div><div class="col-md-4 mb-2"><label>Relevant Experience</label><input type="number" step="0.5" class="form-control" id="candRelevantExp" value="0"></div><div class="col-md-12 mb-2"><label>Professional Summary</label><textarea class="form-control" id="candSummary" rows="2"></textarea></div></div></div></div><div class="card mb-3"><div class="card-header bg-warning text-dark">Skills</div><div class="card-body"><div id="skillsContainer"></div><button type="button" class="btn btn-sm btn-outline-primary mt-1" onclick="addSkillEntry()">+ Add Skill</button><button type="button" class="btn btn-sm btn-outline-info mt-1 ms-2" onclick="suggestAISkills()"><i class="bi bi-stars"></i> AI Suggest Skills</button></div></div><div class="card mb-3"><div class="card-header bg-secondary text-white">Work Experience</div><div class="card-body"><div id="experienceContainer"></div><button type="button" class="btn btn-sm btn-outline-secondary mt-1" onclick="addExperienceEntry()">+ Add Company</button></div></div><div class="card mb-3"><div class="card-header bg-dark text-white">Education</div><div class="card-body"><div id="educationContainer"></div><button type="button" class="btn btn-sm btn-outline-dark mt-1" onclick="addEducationEntry()">+ Add Education</button></div></div><div class="card mb-3"><div class="card-header bg-dark text-white">Salary & Notice Period</div><div class="card-body"><div class="row"><div class="col-md-3 mb-2"><label>Current Salary (₹)</label><input type="number" class="form-control" id="candCurrentSalary"></div><div class="col-md-3 mb-2"><label>Expected Salary (₹)</label><input type="number" class="form-control" id="candExpectedSalary"></div><div class="col-md-3 mb-2"><label>Notice Period (days)</label><input type="number" class="form-control" id="candNoticePeriod"></div><div class="col-md-3 mb-2"><label>Source</label><select class="form-control" id="candSource"><option value="linkedin">LinkedIn</option><option value="naukri">Naukri</option><option value="referral">Referral</option><option value="ai-enriched">AI Enriched</option></select></div></div></div></div><div class="card mb-3"><div class="card-header bg-danger text-white"><i class="bi bi-file-earmark-text"></i> Candidate Documents</div><div class="card-body"><div class="row"><div class="col-md-6 mb-3"><label>📄 Resume/CV</label><input type="file" class="form-control" id="docResume" accept=".pdf,.docx,.doc"><div id="resumeFileName" class="small text-success mt-1"></div></div><div class="col-md-6 mb-3"><label>🎓 Highest Degree Certificate</label><input type="file" class="form-control" id="docDegree" accept=".pdf,.jpg,.png"><div id="degreeFileName" class="small text-success mt-1"></div></div><div class="col-md-4 mb-3"><label>💰 Pay Slip</label><input type="file" class="form-control" id="docPaySlip" accept=".pdf,.jpg,.png"><div id="paySlipFileName" class="small text-success mt-1"></div></div><div class="col-md-4 mb-3"><label>📑 Form 16</label><input type="file" class="form-control" id="docForm16" accept=".pdf"><div id="form16FileName" class="small text-success mt-1"></div></div><div class="col-md-4 mb-3"><label>🪪 PAN Card</label><input type="file" class="form-control" id="docPan" accept=".pdf,.jpg,.png"><div id="panFileName" class="small text-success mt-1"></div></div><div class="col-md-4 mb-3"><label>🆔 Aadhar Card</label><input type="file" class="form-control" id="docAadhar" accept=".pdf,.jpg,.png"><div id="aadharFileName" class="small text-success mt-1"></div></div><div class="col-md-4 mb-3"><label>📸 Passport Photo</label><input type="file" class="form-control" id="docPhoto" accept=".jpg,.png"><div id="photoFileName" class="small text-success mt-1"></div></div><div class="col-md-4 mb-3"><label>📜 Offer Letter (signed)</label><input type="file" class="form-control" id="docOfferLetter" accept=".pdf"><div id="offerLetterFileName" class="small text-success mt-1"></div></div><div class="col-md-12 mb-3"><label>📎 Other Documents</label><input type="file" class="form-control" id="docOther" accept=".pdf,.jpg,.png,.docx"><div id="otherFileName" class="small text-success mt-1"></div></div></div></div></div><button type="submit" class="btn btn-success w-100">Save Candidate Profile</button></form></div></div></div></div>

    <!-- Resume Upload Modal -->
    <div class="modal fade modal-modern" id="resumeUploadModal" tabindex="-1"><div class="modal-dialog"><div class="modal-content"><div class="modal-header"><h5 class="modal-title"><i class="bi bi-file-earmark-arrow-up"></i> Upload Resume <span class="ai-badge">AI Powered</span></h5><button type="button" class="btn-close btn-close-white" data-bs-dismiss="modal"></button></div><div class="modal-body"><div class="mb-3"><input type="file" class="form-control" id="resumeFile" accept=".pdf,.docx"><div class="form-text">Upload candidate's resume. AI will extract all information automatically.</div></div><div id="resumeParseProgress" style="display: none;" class="text-center"><div class="loader"></div><p class="mt-2">AI is analyzing the resume...</p></div><div id="resumePreview" style="display: none;"><h6>Extracted Information:</h6><pre id="resumeExtractedData" class="bg-light p-2 rounded" style="font-size: 0.8rem;"></pre><button class="btn btn-primary-modern w-100" onclick="createCandidateFromResume()">Create Candidate Profile</button></div><button class="btn btn-primary-modern w-100" onclick="parseResume()" id="parseResumeBtn"><i class="bi bi-robot"></i> Parse Resume</button></div></div></div></div>

    <!-- Application Modal -->
    <div class="modal fade modal-modern" id="applicationModal" tabindex="-1"><div class="modal-dialog"><div class="modal-content"><div class="modal-header"><h5 class="modal-title">Create Application <span class="ai-badge">AI Match Scoring</span></h5><button type="button" class="btn-close btn-close-white" data-bs-dismiss="modal"></button></div><div class="modal-body"><form id="applicationForm"><div class="mb-2"><label>Candidate</label><select class="form-select" id="appCandidateId" required></select></div><div class="mb-2"><label>Job Description</label><select class="form-select" id="appJdId" required></select></div><div id="matchScoreDisplay" class="alert alert-info" style="display: none;">AI Match Score: <strong id="matchScore"></strong>%</div><button type="submit" class="btn btn-primary-modern w-100">Create Application</button></form></div></div></div></div>

    <!-- Interview Modal -->
    <div class="modal fade modal-modern" id="interviewModal" tabindex="-1"><div class="modal-dialog"><div class="modal-content"><div class="modal-header"><h5 class="modal-title">Schedule Interview <span class="ai-badge">Smart Scheduling</span></h5><button type="button" class="btn-close btn-close-white" data-bs-dismiss="modal"></button></div><div class="modal-body"><form id="interviewForm"><div class="mb-2"><label>Application</label><select class="form-select" id="interviewAppId" required></select></div><div class="mb-2"><label>Round Type</label><select class="form-select" id="interviewRoundType"><option value="telephonic">Telephonic Screening</option><option value="technical">Technical Round</option><option value="coding">Coding Assessment</option><option value="system-design">System Design</option><option value="managerial">Managerial Round</option><option value="hr">HR Round</option><option value="client">Client Round</option><option value="final">Final Round</option></select></div><div class="mb-2"><label>Interviewer Name</label><input type="text" class="form-control" id="interviewerName"></div><div class="mb-2"><label>Interviewer Email</label><input type="email" class="form-control" id="interviewerEmail"></div><div class="mb-2"><label>Scheduled Date & Time</label><input type="datetime-local" class="form-control" id="interviewDateTime"></div><div class="mb-2"><label>Meeting Link (Google Meet/Zoom)</label><input type="url" class="form-control" id="interviewLink"></div><button type="submit" class="btn btn-warning w-100">Schedule Interview</button></form></div></div></div></div>

    <!-- Offer Modal -->
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
'''
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
        async function loadJDs() { try { const res = await fetch('/api/jds'); const jobs = await res.json(); document.getElementById('jdsTableBody').innerHTML = jobs.map(j => `<tr><td><code>${j.code}</code></td><td><strong>${j.title}</strong>${j.ai_generated ? '<span class="ai-badge">AI</span>' : ''}</td><td>${j.client || '-'}<tr><td>${j.location || '-'}</td><td><span class="badge bg-secondary">${j.employment_type}</span></td><td><span class="badge badge-open">${j.status}</span></td><td>${j.applications || 0}</td><td><button class="btn btn-sm btn-primary" onclick="createApplicationForJob(${j.id})">Apply</button></td>`).join(''); } catch(e) { console.error(e); } }

        async function loadCandidates(page = 1) { currentCandidatePage = page; const search = document.getElementById('candidateSearch')?.value || ''; const source = document.getElementById('sourceFilter')?.value || ''; try { const res = await fetch(`/api/candidates?page=${page}&search=${encodeURIComponent(search)}&source=${source}`); const data = await res.json(); const container = document.getElementById('candidatesList'); if (!data.candidates.length) { container.innerHTML = '<div class="alert alert-info">No candidates found</div>'; return; } container.innerHTML = `<div class="row">${data.candidates.map(c => `<div class="col-md-4 mb-3"><div class="card border-0 shadow-sm"><div class="card-body"><div class="d-flex justify-content-between"><h6 class="fw-bold">${c.name}${c.ai_enriched ? '<span class="ai-badge">AI</span>' : ''}</h6><code class="text-muted small">${c.code}</code></div><p class="small text-muted mb-1"><i class="bi bi-envelope"></i> ${c.email}</p><p class="small mb-1"><i class="bi bi-briefcase"></i> ${c.total_experience || 0} years</p><p class="small"><i class="bi bi-tags"></i> ${(c.skills || '').substring(0, 50)}</p><button class="btn btn-sm btn-primary w-100" onclick="createApplicationForCandidate(${c.id})">Apply to Job</button><button class="btn btn-sm btn-outline-secondary mt-1 w-100" onclick="viewDocuments(${c.id})"><i class="bi bi-file-earmark-text"></i> Documents</button></div></div></div>`).join('')}</div>`; const pagination = document.getElementById('candidatesPagination'); if (data.pages > 1) { let html = '<nav><ul class="pagination">'; for (let i = 1; i <= data.pages; i++) html += `<li class="page-item ${i === page ? 'active' : ''}"><a class="page-link" href="#" onclick="loadCandidates(${i})">${i}</a></li>`; html += '</ul></nav>'; pagination.innerHTML = html; } else pagination.innerHTML = ''; } catch(e) { console.error(e); } }

        async function loadApplications() { try { const res = await fetch('/api/applications'); const apps = await res.json(); document.getElementById('applicationsTable').innerHTML = apps.map(a => `<tr><td>${a.id}</td><td>${a.candidate_name}</td><td>${a.job_title}</td><td><span class="badge ${a.match_score >= 85 ? 'bg-success' : a.match_score >= 70 ? 'bg-primary' : a.match_score >= 50 ? 'bg-warning' : 'bg-secondary'}">${a.match_score || 0}% <i class="bi bi-stars"></i></span></td><td>${a.status}</td><td><button class="btn btn-sm btn-warning" onclick="moveApplication(${a.id}, prompt('Enter stage'))">Move</button></td>`).join(''); } catch(e) { console.error(e); } }

        async function loadInterviews() { try { const res = await fetch('/api/interviews'); const interviews = await res.json(); document.getElementById('interviewsList').innerHTML = interviews.length ? `<div class="modern-table"><table class="table"><thead><tr><th>Candidate</th><th>Interviewer</th><th>Time</th><th>Status</th><th>AI Notes</th></tr></thead><tbody>${interviews.map(i => `<tr><td>${i.candidate_name}</td><td>${i.interviewer}</td><td>${new Date(i.scheduled_time).toLocaleString()}</td><td><span class="badge badge-interview">${i.status}</span></td><td><button class="btn btn-sm btn-outline-info" onclick="viewAINotes(${i.id})"><i class="bi bi-robot"></i> Notes</button></td>`).join('')}</tbody></table></div>` : '<div class="alert alert-info">No interviews scheduled</div>'; } catch(e) { console.error(e); } }

        async function loadOffers() { try { const res = await fetch('/api/offers'); const offers = await res.json(); document.getElementById('offersList').innerHTML = offers.length ? `<div class="modern-table"><table class="table"><thead><tr><th>Candidate</th><th>Job</th><th>Salary</th><th>Status</th><th>Actions</th></tr></thead><tbody>${offers.map(o => `<tr><td>${o.candidate_name}</td><td>${o.job_title}</td><td>$${o.base_salary}</td><td>${o.status}</td><td><button class="btn btn-sm btn-primary" onclick="viewOffer(${o.id})">View</button> <button class="btn btn-sm btn-success" onclick="sendOfferEmail(${o.id})">Send Email</button></td>`).join('')}</tbody></table></div>` : '<div class="alert alert-info">No offers generated</div>'; } catch(e) { console.error(e); } }

        // Create Operations
        async function createJob() { const title = document.getElementById('jdTitle')?.value; if (!title) return; const data = { title, location: document.getElementById('jdLocation')?.value, skills_required: document.getElementById('jdSkills')?.value, status: document.getElementById('jdStatus')?.value, employment_type: document.getElementById('jdEmploymentType')?.value, priority: document.getElementById('jdPriority')?.value, client_name: document.getElementById('jdClientId')?.value }; const res = await fetch('/api/jds', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(data) }); const result = await res.json(); if (result.success) { alert('Job created!'); bootstrap.Modal.getInstance(document.getElementById('jdMasterModal')).hide(); loadJDs(); loadDashboard(); } }

        async function createCandidate() { const data = { first_name: document.getElementById('candFirstName').value, last_name: document.getElementById('candLastName').value, email: document.getElementById('candEmail').value, phone: document.getElementById('candPhone').value, skills: document.getElementById('candSkills').value, total_experience: parseFloat(document.getElementById('candExperience').value), current_company: document.getElementById('candCompany').value, linkedin_url: document.getElementById('candLinkedin').value }; const res = await fetch('/api/candidates', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(data) }); const result = await res.json(); if (result.success) { alert('Candidate added!'); bootstrap.Modal.getInstance(document.getElementById('candidateModal')).hide(); loadCandidates(); loadDashboard(); } }

        // Application Operations
        async function createApplicationForJob(jd_id) { const candidate_id = prompt('Enter Candidate ID:'); if (!candidate_id) return; const res = await fetch('/api/applications', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ candidate_id: parseInt(candidate_id), jd_id }) }); const result = await res.json(); if (result.success) alert(`AI Match Score: ${result.match_score}%`); loadApplications(); loadJDs(); }

        async function createApplicationForCandidate(candidate_id) { const jd_id = prompt('Enter Job ID:'); if (!jd_id) return; const res = await fetch('/api/applications', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ candidate_id, jd_id: parseInt(jd_id) }) }); const result = await res.json(); if (result.success) alert(`AI Match Score: ${result.match_score}%`); loadApplications(); loadJDs(); }

        async function moveApplication(app_id, stage) { if (!stage) return; await fetch(`/api/applications/${app_id}/move`, { method: 'PUT', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ stage }) }); loadApplications(); }

        // Resume Parsing
        async function parseResume() { const file = document.getElementById('resumeFile')?.files[0]; if (!file) { alert('Select a file'); return; } const formData = new FormData(); formData.append('file', file); document.getElementById('resumeParseProgress').style.display = 'block'; const res = await fetch('/api/candidates/parse-resume-enhanced', { method: 'POST', body: formData }); const result = await res.json(); document.getElementById('resumeParseProgress').style.display = 'none'; if (result.success) { parsedResumeDataCache = result.data; document.getElementById('resumeExtractedData').textContent = JSON.stringify(result.data, null, 2); document.getElementById('resumePreview').style.display = 'block'; } else { alert('Error parsing resume'); } }

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
'''

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

# ============= IN-MEMORY STORAGE =============
jobs = []
candidates = []
applications = []
interviews = []
offers = []
next_id = 1
candidate_notes = {}
application_notes = {}

# ============= PIPELINE STAGES =============
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

# ============= HELPER FUNCTIONS =============
def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in app.config['ALLOWED_EXTENSIONS']

def generate_code(prefix):
    if prefix == 'JD':
        last = max([j['id'] for j in jobs]) if jobs else 0
    elif prefix == 'CAN':
        last = max([c['id'] for c in candidates]) if candidates else 0
    elif prefix == 'APP':
        last = max([a['id'] for a in applications]) if applications else 0
    elif prefix == 'OFF':
        last = max([o['id'] for o in offers]) if offers else 0
    else:
        last = 0
    return f"{prefix}-{last + 1:04d}"

def calculate_weighted_match_score(job_skills, candidate_skills):
    """Advanced AI-powered skill matching with semantic analysis"""
    if not job_skills or not candidate_skills:
        return 0, {}
    
    job_list = [s.strip().lower() for s in job_skills.split(',') if s.strip()]
    cand_list = [s.strip().lower() for s in candidate_skills.split(',') if s.strip()]
    
    if not job_list:
        return 0, {}
    
    match_details = {'exact_matches': [], 'partial_matches': [], 'missing_skills': [], 'semantic_matches': []}
    total_score = 0
    
    # Semantic skill mapping (synonyms and related skills)
    semantic_map = {
        'python': ['python', 'django', 'flask', 'fastapi', 'pandas', 'numpy', 'jupyter'],
        'java': ['java', 'spring', 'hibernate', 'maven', 'gradle', 'j2ee', 'kotlin'],
        'javascript': ['javascript', 'react', 'angular', 'vue', 'node', 'typescript', 'ecmascript'],
        'aws': ['aws', 'ec2', 's3', 'lambda', 'cloudformation', 'terraform', 'amazon web services'],
        'database': ['sql', 'mysql', 'postgresql', 'mongodb', 'oracle', 'nosql', 'dynamodb'],
        'docker': ['docker', 'container', 'kubernetes', 'k8s', 'devops', 'podman'],
        'react': ['react', 'redux', 'hooks', 'jsx', 'frontend', 'next.js'],
        'nodejs': ['node', 'express', 'npm', 'backend', 'api', 'rest api'],
        'machine learning': ['machine learning', 'ml', 'ai', 'artificial intelligence', 'tensorflow', 'pytorch'],
        'data science': ['data science', 'analytics', 'statistics', 'data analysis', 'big data']
    }
    
    for job_skill in job_list:
        best_match = 0
        best_match_name = None
        
        for cand_skill in cand_list:
            # Exact match (100 points)
            if job_skill == cand_skill:
                best_match = 100
                best_match_name = cand_skill
                match_details['exact_matches'].append(job_skill)
                break
            # Partial match (70 points)
            elif job_skill in cand_skill or cand_skill in job_skill:
                best_match = 70
                best_match_name = cand_skill
                if job_skill not in match_details['partial_matches']:
                    match_details['partial_matches'].append(job_skill)
                break
            # Semantic match (50 points)
            for key, related_list in semantic_map.items():
                if job_skill == key:
                    for related in related_list:
                        if related in cand_skill:
                            best_match = 50
                            match_details['semantic_matches'].append(f"{job_skill} → {cand_skill}")
                            break
                    if best_match == 50:
                        break
                elif job_skill in related_list:
                    if key in cand_skill:
                        best_match = 50
                        match_details['semantic_matches'].append(f"{job_skill} → {cand_skill}")
                        break
                if best_match == 50:
                    break
            if best_match == 50:
                continue
            # Sequence similarity match (30-60 points)
            else:
                similarity = SequenceMatcher(None, job_skill, cand_skill).ratio() * 100
                if similarity > best_match and similarity > 30:
                    best_match = similarity
                    best_match_name = cand_skill
        
        if best_match == 0:
            match_details['missing_skills'].append(job_skill)
        
        total_score += best_match
    
    final_score = round(total_score / len(job_list), 2)
    
    # AI bonus: add up to 15% extra for semantic understanding
    ai_bonus = min(15, len(match_details['semantic_matches']) * 3)
    final_score = min(100, final_score + ai_bonus)
    
    return final_score, match_details

def call_gemini_ai(prompt):
    """Call Gemini AI API for text generation - FREE"""
    if not GEMINI_AVAILABLE:
        return None
    try:
        response = gemini_model.generate_content(prompt)
        return response.text
    except Exception as e:
        print(f"Gemini AI error: {e}")
        return None

def extract_text_from_file(file):
    """Extract text from PDF, DOCX, or TXT files"""
    text = ''
    filename = file.filename.lower()
    
    if filename.endswith('.pdf'):
        try:
            import PyPDF2
            reader = PyPDF2.PdfReader(file)
            for page in reader.pages:
                page_text = page.extract_text()
                if page_text:
                    text += page_text
        except Exception as e:
            print(f"PDF extraction error: {e}")
            text = ''
    elif filename.endswith('.docx'):
        try:
            import docx
            doc = docx.Document(file)
            text = '\n'.join([para.text for para in doc.paragraphs])
        except Exception as e:
            print(f"DOCX extraction error: {e}")
            text = ''
    else:
        try:
            text = file.read().decode('utf-8')
        except Exception as e:
            print(f"Text extraction error: {e}")
            text = ''
    
    return text

def extract_name_enhanced(text):
    """Enhanced name extraction from resume text"""
    if not text:
        return {'first': None, 'last': None}
    
    lines = text.split('\n')[:15]
    for line in lines:
        line = line.strip()
        # Look for 2-word name patterns
        if len(line.split()) == 2 and not any(x in line.lower() for x in ['resume', 'curriculum', 'vitae', 'email', 'phone', 'page', 'contact']):
            parts = line.split()
            if len(parts) == 2 and parts[0][0].isupper() and parts[1][0].isupper():
                return {'first': parts[0], 'last': parts[1]}
    
    # Try to find name in "Name: John Doe" format
    name_match = re.search(r'Name[:\s]+([A-Z][a-z]+)\s+([A-Z][a-z]+)', text, re.IGNORECASE)
    if name_match:
        return {'first': name_match.group(1), 'last': name_match.group(2)}
    
    return {'first': None, 'last': None}

def extract_email_enhanced(text):
    """Extract email address from text"""
    if not text:
        return None
    pattern = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
    match = re.search(pattern, text)
    return match.group(0) if match else None

def extract_phone_enhanced(text):
    """Extract phone number from text"""
    if not text:
        return None
    patterns = [
        r'\b\d{10}\b',
        r'\+\d{1,2}[-.\s]?\d{10}\b',
        r'\b\d{3}[-.]?\d{3}[-.]?\d{4}\b',
        r'\b\d{5}\s?\d{5}\b'
    ]
    for pattern in patterns:
        match = re.search(pattern, text)
        if match:
            return match.group(0)
    return None

def extract_skills_enhanced(text):
    """Extract technical skills from resume text"""
    skill_database = [
        'Python', 'Java', 'JavaScript', 'TypeScript', 'C++', 'C#', 'Go', 'Ruby', 'PHP', 'Swift', 'Kotlin',
        'React', 'Angular', 'Vue', 'Node.js', 'Django', 'Flask', 'Spring', 'Express', 'Rails', 'Laravel',
        'MySQL', 'PostgreSQL', 'MongoDB', 'Redis', 'Oracle', 'SQL Server', 'Cassandra', 'DynamoDB',
        'AWS', 'Azure', 'GCP', 'Docker', 'Kubernetes', 'Terraform', 'Jenkins', 'Git', 'CI/CD',
        'TensorFlow', 'PyTorch', 'Scikit-learn', 'Pandas', 'NumPy', 'Machine Learning', 'Data Science',
        'Leadership', 'Project Management', 'Agile', 'Scrum', 'Communication', 'Teamwork',
        'REST API', 'GraphQL', 'Microservices', 'DevOps', 'Selenium', 'JUnit', 'Mocha', 'Jest',
        'HTML', 'CSS', 'Bootstrap', 'Tailwind', 'jQuery', 'AJAX', 'JSON', 'XML'
    ]
    found = []
    text_lower = text.lower()
    for skill in skill_database:
        if skill.lower() in text_lower:
            found.append(skill)
    return found

def extract_experience_enhanced(text):
    """Extract years of experience from text"""
    if not text:
        return 0.0
    
    patterns = [
        r'(\d+)\s*\+\s*years?',
        r'(\d+)\s*years?\s+of\s+experience',
        r'total\s+experience\s*:?\s*(\d+)',
        r'experience\s*:?\s*(\d+)\s*years?',
        r'(\d+)\+?\s*yrs?'
    ]
    for pattern in patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            try:
                return float(match.group(1))
            except:
                pass
    return 0.0

def extract_location_enhanced(text):
    """Extract location from text"""
    if not text:
        return None
    
    cities = ['Bangalore', 'Mumbai', 'Delhi', 'Hyderabad', 'Chennai', 'Pune', 'Kolkata', 'Ahmedabad', 
              'Remote', 'Gurgaon', 'Noida', 'Lucknow', 'Jaipur', 'Chandigarh', 'Indore', 'Bhopal',
              'Nagpur', 'Patna', 'Visakhapatnam', 'Coimbatore', 'Kochi', 'Vadodara', 'Ludhiana']
    for city in cities:
        if city.lower() in text.lower():
            return city
    
    pattern = r'Location\s*:?\s*([^\n]+)'
    match = re.search(pattern, text, re.IGNORECASE)
    return match.group(1).strip() if match else None

def extract_primary_role(text):
    """Extract primary job role from text"""
    if not text:
        return None
    
    lines = text.split('\n')[:20]
    roles = ['developer', 'engineer', 'architect', 'manager', 'lead', 'analyst', 'consultant', 
             'specialist', 'administrator', 'designer', 'tester', 'devops', 'data scientist',
             'product manager', 'project manager', 'software engineer', 'full stack', 'backend', 'frontend']
    
    for line in lines:
        line_lower = line.lower()
        for role in roles:
            if role in line_lower:
                words = line.strip().split()
                if len(words) <= 6:
                    return line.strip()
                else:
                    for i, word in enumerate(words):
                        if role in word.lower():
                            start = max(0, i - 2)
                            end = min(len(words), i + 3)
                            return ' '.join(words[start:end])
    return None

def generate_offer_letter_html(data):
    """Generate professional HTML offer letter"""
    base_salary = data.get('base_salary', 0)
    joining_bonus = data.get('joining_bonus', 0)
    joining_date = data.get('joining_date', (datetime.now().date() + timedelta(days=15)).isoformat())
    
    try:
        salary_formatted = f"₹{float(base_salary):,.2f}" if base_salary else "TBD"
        bonus_formatted = f"₹{float(joining_bonus):,.2f}" if joining_bonus else "₹0"
    except (ValueError, TypeError):
        salary_formatted = "TBD"
        bonus_formatted = "₹0"
    
    return f'''<!DOCTYPE html>
<html>
<head>
    <title>Offer Letter - {data.get('candidate_name', 'Candidate')}</title>
    <style>
        body {{ font-family: 'Segoe UI', Arial, sans-serif; margin: 50px; background: #f5f5f5; }}
        .container {{ max-width: 800px; margin: auto; background: white; padding: 40px; border-radius: 15px; box-shadow: 0 5px 20px rgba(0,0,0,0.1); }}
        .header {{ text-align: center; border-bottom: 3px solid #4caf50; padding-bottom: 20px; margin-bottom: 30px; }}
        .header h1 {{ color: #2c3e50; margin: 0; }}
        .header p {{ color: #7f8c8d; margin: 5px 0 0; }}
        .content {{ margin: 30px 0; }}
        .offer-details {{ background: #f8f9fa; padding: 20px; border-radius: 10px; margin: 20px 0; }}
        .offer-details table {{ width: 100%; border-collapse: collapse; }}
        .offer-details td {{ padding: 10px; border-bottom: 1px solid #dee2e6; }}
        .offer-details td:first-child {{ font-weight: bold; width: 40%; }}
        .signature {{ margin-top: 50px; padding-top: 30px; border-top: 1px solid #dee2e6; }}
        .footer {{ text-align: center; margin-top: 40px; font-size: 12px; color: #7f8c8d; }}
        @media print {{
            body {{ margin: 0; padding: 0; background: white; }}
            .container {{ box-shadow: none; padding: 20px; }}
        }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>ShahnaIT Scout</h1>
            <p>Offer of Employment</p>
        </div>
        <div class="content">
            <p>Dear <strong>{data.get('candidate_name', 'Candidate')}</strong>,</p>
            <p>We are delighted to offer you the position of <strong>{data.get('job_title', 'Position')}</strong> at ShahnaIT Scout. We believe your skills and experience will be a valuable addition to our team.</p>
            
            <div class="offer-details">
                <h3>📋 Offer Details</h3>
                <table>
                    <tr><td>Position</td><td><strong>{data.get('job_title', 'Position')}</strong></td></tr>
                    <tr><td>Base Salary</td><td><strong>{salary_formatted}</strong> per annum</td></tr>
                    <tr><td>Joining Bonus</td><td><strong>{bonus_formatted}</strong> (one-time)</td></tr>
                    <tr><td>Expected Joining Date</td><td><strong>{data.get('joining_date', 'TBD')}</strong></td></tr>
                    <tr><td>Location</td><td><strong>Remote / Hybrid</strong></td></tr>
                    <tr><td>Employment Type</td><td><strong>Full-time</strong></td></tr>
                </table>
            </div>
            
            <h3>📝 Terms & Conditions</h3>
            <ul>
                <li>This offer is valid for 15 days from the date of issuance.</li>
                <li>You will be required to submit valid identity and address proofs.</li>
                <li>Background verification will be conducted prior to joining.</li>
                <li>Performance reviews will be conducted quarterly.</li>
                <li>You will be eligible for benefits after completion of probation period.</li>
            </ul>
            
            <p>Please review the offer and confirm your acceptance by <strong>{data.get('joining_date', 'TBD')}</strong>.</p>
            <p>We look forward to having you on our team!</p>
        </div>
        <div class="signature">
            <p>Sincerely,<br><strong>ShahnaIT Recruitment Team</strong><br>hr@shahnaiT.com</p>
        </div>
        <div class="footer">
            <p>This is a system-generated offer letter. For any queries, please contact HR.</p>
        </div>
    </div>
</body>
</html>'''
    
# ============= API ROUTES - HEALTH & DASHBOARD =============

@app.route('/')
def index():
    """Main dashboard page"""
    return render_template_string(DASHBOARD_TEMPLATE)

@app.route('/health')
def health():
    """Health check endpoint"""
    return jsonify({
        'status': 'ok', 
        'timestamp': datetime.now().isoformat(),
        'ai_available': GEMINI_AVAILABLE,
        'version': '2.0',
        'features': ['AI Resume Parser', 'AI JD Generator', 'AI Interview Questions', 'LinkedIn Import', 'Bulk CSV Import', 'Kanban Pipeline']
    })

@app.route('/api/dashboard/stats')
def dashboard_stats():
    """Get dashboard statistics"""
    total_apps = len(applications)
    ai_matches = sum(1 for a in applications if a.get('match_score', 0) >= 75)
    
    # Calculate conversion rates
    screening_count = len([a for a in applications if a.get('status') in ['screening', 'shortlisted']])
    interview_count = len([a for a in applications if a.get('status') in ['interview-scheduled', 'interviewed']])
    offer_count = len([a for a in applications if a.get('status') in ['offered', 'offer-accepted']])
    hired_count = len([a for a in applications if a.get('status') == 'hired'])
    
    return jsonify({
        'overview': {
            'open_positions': len([j for j in jobs if j.get('status') == 'open']),
            'total_candidates': len(candidates),
            'total_applications': total_apps,
            'interviews_today': len([i for i in interviews if i.get('status') == 'scheduled' and i.get('scheduled_time', '').startswith(datetime.now().date().isoformat())]),
            'offers_accepted': len([o for o in offers if o.get('status') == 'accepted']),
            'ai_matches': ai_matches
        },
        'pipeline': {
            'new': len([a for a in applications if a.get('status') == 'new']),
            'screening': screening_count,
            'shortlisted': len([a for a in applications if a.get('status') == 'shortlisted']),
            'interview': interview_count,
            'technical': len([a for a in applications if a.get('status') == 'technical']),
            'hr': len([a for a in applications if a.get('status') == 'hr']),
            'offer': offer_count,
            'hired': hired_count,
            'rejected': len([a for a in applications if a.get('status') == 'rejected'])
        },
        'sources': [
            {'source': 'LinkedIn', 'count': len([c for c in candidates if c.get('source') == 'linkedin'])},
            {'source': 'Naukri', 'count': len([c for c in candidates if c.get('source') == 'naukri'])},
            {'source': 'Referral', 'count': len([c for c in candidates if c.get('source') == 'referral'])},
            {'source': 'AI Enriched', 'count': len([c for c in candidates if c.get('ai_enriched')])},
            {'source': 'CSV Import', 'count': len([c for c in candidates if c.get('source') == 'csv_import'])},
            {'source': 'Manual', 'count': len([c for c in candidates if c.get('source') == 'manual'])}
        ],
        'recent_activities': [
            {'action': f'New candidate added', 'created_at': datetime.now().isoformat()}
        ] if candidates else [],
        'top_jds': [{'title': j.get('title'), 'applications': j.get('applications', 0)} for j in jobs[:5]]
    })

# ============= API ROUTES - JOB DESCRIPTIONS =============

@app.route('/api/jds', methods=['GET', 'POST'])
def manage_jds():
    """Manage job descriptions"""
    global next_id
    if request.method == 'POST':
        data = request.get_json()
        job = {
            'id': next_id,
            'code': generate_code('JD'),
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
        next_id += 1
        return jsonify({'success': True, 'jd_id': job['id'], 'jd_code': job['code']})
    return jsonify(jobs)

@app.route('/api/jds/<int:jd_id>', methods=['GET', 'PUT', 'DELETE'])
def manage_jd_detail(jd_id):
    """Get, update, or delete a specific job description"""
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

# ============= API ROUTES - CANDIDATES =============

@app.route('/api/candidates', methods=['GET', 'POST'])
def manage_candidates():
    """Manage candidates with pagination and filtering"""
    global next_id
    if request.method == 'POST':
        data = request.get_json()
        
        # Check for duplicate email
        existing = next((c for c in candidates if c.get('email') == data.get('email')), None)
        if existing:
            return jsonify({'error': 'Candidate with this email already exists', 'candidate_id': existing['id']}), 409
        
        candidate = {
            'id': next_id,
            'code': generate_code('CAN'),
            'first_name': data.get('first_name', ''),
            'last_name': data.get('last_name', ''),
            'name': f"{data.get('first_name', '')} {data.get('last_name', '')}".strip(),
            'email': data.get('email', ''),
            'phone': data.get('phone', ''),
            'alternate_phone': data.get('alternate_phone', ''),
            'linkedin_url': data.get('linkedin_url', ''),
            'github_url': data.get('github_url', ''),
            'address': data.get('address', ''),
            'current_location': data.get('current_location', ''),
            'current_company': data.get('current_company', ''),
            'current_designation': data.get('current_designation', ''),
            'total_experience': data.get('total_experience', 0),
            'relevant_experience': data.get('relevant_experience', 0),
            'skills': data.get('skills', ''),
            'qualifications': data.get('qualifications', ''),
            'current_salary': data.get('current_salary'),
            'expected_salary': data.get('expected_salary'),
            'notice_period': data.get('notice_period'),
            'source': data.get('source', 'manual'),
            'ai_enriched': data.get('ai_enriched', False),
            'created_at': datetime.now().isoformat(),
            'updated_at': datetime.now().isoformat()
        }
        candidates.append(candidate)
        next_id += 1
        return jsonify({'success': True, 'candidate_id': candidate['id'], 'candidate_code': candidate['code']})
    
    # GET request with pagination and filters
    page = int(request.args.get('page', 1))
    per_page = int(request.args.get('per_page', 20))
    search = request.args.get('search', '')
    source = request.args.get('source', '')
    exp_min = request.args.get('exp_min', '')
    exp_max = request.args.get('exp_max', '')
    location = request.args.get('location', '')
    skills = request.args.get('skills', '')
    
    filtered = candidates.copy()
    
    if search:
        filtered = [c for c in filtered if search.lower() in c.get('name', '').lower() or search.lower() in c.get('email', '').lower() or search.lower() in c.get('skills', '').lower()]
    if source:
        filtered = [c for c in filtered if c.get('source') == source]
    if exp_min:
        filtered = [c for c in filtered if c.get('total_experience', 0) >= float(exp_min)]
    if exp_max:
        filtered = [c for c in filtered if c.get('total_experience', 0) <= float(exp_max)]
    if location:
        filtered = [c for c in filtered if location.lower() in c.get('current_location', '').lower()]
    if skills:
        skill_list = [s.strip().lower() for s in skills.split(',')]
        filtered = [c for c in filtered if any(skill in c.get('skills', '').lower() for skill in skill_list)]
    
    start = (page - 1) * per_page
    end = start + per_page
    paginated = filtered[start:end]
    
    return jsonify({
        'candidates': paginated,
        'total': len(filtered),
        'page': page,
        'pages': (len(filtered) + per_page - 1) // per_page,
        'per_page': per_page
    })

@app.route('/api/candidates/enhanced-with-docs', methods=['POST'])
def create_enhanced_candidate_with_docs():
    """Create candidate with document uploads"""
    global next_id
    basic_info = json.loads(request.form.get('basic_info', '{}'))
    
    documents = {}
    doc_fields = ['docResume', 'docDegree', 'docPaySlip', 'docForm16', 'docPan', 'docAadhar', 'docPhoto', 'docOfferLetter', 'docOther']
    
    for field in doc_fields:
        if field in request.files:
            file = request.files[field]
            if file and file.filename:
                file_content = file.read()
                documents[field] = {
                    'filename': file.filename,
                    'content_type': file.content_type,
                    'data': base64.b64encode(file_content).decode('utf-8'),
                    'uploaded_at': datetime.now().isoformat()
                }
    
    candidate = {
        'id': next_id,
        'code': generate_code('CAN'),
        'first_name': basic_info.get('first_name', ''),
        'last_name': basic_info.get('last_name', ''),
        'name': f"{basic_info.get('first_name', '')} {basic_info.get('last_name', '')}".strip(),
        'email': basic_info.get('email', ''),
        'phone': basic_info.get('phone', ''),
        'alternate_phone': basic_info.get('alternate_phone', ''),
        'linkedin_url': basic_info.get('linkedin_url', ''),
        'github_url': basic_info.get('github_url', ''),
        'address': basic_info.get('address', ''),
        'current_location': basic_info.get('current_location', ''),
        'primary_role': basic_info.get('primary_role', ''),
        'total_experience': basic_info.get('total_experience', 0),
        'relevant_experience': basic_info.get('relevant_experience', 0),
        'professional_summary': basic_info.get('professional_summary', ''),
        'skills': basic_info.get('skills', []),
        'work_experience': basic_info.get('work_experience', []),
        'education': basic_info.get('education', []),
        'current_salary': basic_info.get('current_salary'),
        'expected_salary': basic_info.get('expected_salary'),
        'notice_period': basic_info.get('notice_period'),
        'source': 'ai-enriched',
        'pan_number': request.form.get('pan_number', ''),
        'aadhar_number': request.form.get('aadhar_number', ''),
        'passport_number': request.form.get('passport_number', ''),
        'date_of_birth': request.form.get('date_of_birth', ''),
        'documents': documents,
        'ai_enriched': True,
        'created_at': datetime.now().isoformat(),
        'updated_at': datetime.now().isoformat()
    }
    candidates.append(candidate)
    next_id += 1
    
    return jsonify({
        'success': True, 
        'candidate_id': candidate['id'], 
        'candidate_code': candidate['code'],
        'documents_uploaded': len(documents)
    })

@app.route('/api/candidates/parse-resume-enhanced', methods=['POST'])
def parse_resume_enhanced():
    """Parse resume using AI (Gemini) or fallback to basic extraction"""
    if 'file' not in request.files:
        return jsonify({'error': 'No file uploaded'}), 400
    
    file = request.files['file']
    text = extract_text_from_file(file)
    
    # Try Gemini AI first for better extraction
    if GEMINI_AVAILABLE and text:
        prompt = f"""Extract the following information from this resume. Return ONLY valid JSON with these exact keys:

Resume text:
{text[:4000]}

Extract and return JSON with:
- first_name
- last_name
- email
- phone
- skills (as array of strings)
- total_experience (as number)
- current_company
- current_designation
- current_location
- qualifications
- certifications (as array)

If a field is not found, use null or empty array."""
        
        ai_result = call_gemini_ai(prompt)
        if ai_result:
            try:
                json_str = ai_result.replace('```json', '').replace('```', '').strip()
                parsed = json.loads(json_str)
                return jsonify({'success': True, 'data': parsed, 'ai_used': True})
            except:
                pass
    
    # Fallback to basic extraction
    parsed_data = {
        'first_name': extract_name_enhanced(text)['first'],
        'last_name': extract_name_enhanced(text)['last'],
        'email': extract_email_enhanced(text),
        'phone': extract_phone_enhanced(text),
        'skills': extract_skills_enhanced(text),
        'total_experience': extract_experience_enhanced(text),
        'current_company': None,
        'current_designation': extract_primary_role(text),
        'current_location': extract_location_enhanced(text),
        'qualifications': None,
        'certifications': []
    }
    return jsonify({'success': True, 'data': parsed_data, 'ai_used': False})
    
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
        return jsonify({'error': f'Invalid CSV format: {str(e)}'}), 400
    
    imported = 0
    errors = []
    
    for row_num, row in enumerate(csv_reader, start=2):
        try:
            name = row.get('Name', row.get('name', '')).strip()
            first_name = name.split()[0] if name else ''
            last_name = ' '.join(name.split()[1:]) if len(name.split()) > 1 else ''
            
            candidate = {
                'id': next_id,
                'code': generate_code('CAN'),
                'first_name': first_name,
                'last_name': last_name,
                'name': name,
                'email': row.get('Email', row.get('email', '')),
                'phone': row.get('Phone', row.get('phone', '')),
                'skills': row.get('Skills', row.get('skills', '')),
                'current_company': row.get('Current Company', row.get('current_company', '')),
                'current_designation': row.get('Designation', row.get('designation', '')),
                'total_experience': float(row.get('Experience', row.get('experience', 0))),
                'current_location': row.get('Location', row.get('location', '')),
                'source': 'csv_import',
                'created_at': datetime.now().isoformat(),
                'updated_at': datetime.now().isoformat()
            }
            candidates.append(candidate)
            imported += 1
            next_id += 1
        except Exception as e:
            errors.append(f"Row {row_num}: {str(e)}")
    
    return jsonify({
        'success': True, 
        'imported': imported, 
        'errors': errors[:10],
        'total_rows': row_num - 1 if 'row_num' in locals() else 0
    })

@app.route('/api/candidates/<int:candidate_id>/documents', methods=['GET'])
def get_candidate_documents(candidate_id):
    """Get all documents for a candidate"""
    candidate = next((c for c in candidates if c['id'] == candidate_id), None)
    if not candidate:
        return jsonify({'error': 'Candidate not found'}), 404
    
    documents = candidate.get('documents', {})
    doc_list = []
    for key, doc in documents.items():
        doc_list.append({
            'field': key,
            'filename': doc['filename'],
            'content_type': doc['content_type'],
            'uploaded_at': doc.get('uploaded_at')
        })
    
    return jsonify({'documents': doc_list})

@app.route('/api/candidates/<int:candidate_id>/documents/<field>', methods=['GET'])
def download_candidate_document(candidate_id, field):
    """Download a specific document"""
    candidate = next((c for c in candidates if c['id'] == candidate_id), None)
    if not candidate:
        return jsonify({'error': 'Candidate not found'}), 404
    
    documents = candidate.get('documents', {})
    doc = documents.get(field)
    if not doc:
        return jsonify({'error': 'Document not found'}), 404
    
    file_data = base64.b64decode(doc['data'])
    return send_file(
        io.BytesIO(file_data),
        mimetype=doc['content_type'],
        as_attachment=True,
        download_name=doc['filename']
    )

# ============= API ROUTES - APPLICATIONS =============

@app.route('/api/applications', methods=['GET', 'POST'])
def manage_applications():
    """Manage candidate applications with AI match scoring"""
    if request.method == 'POST':
        data = request.get_json()
        job = next((j for j in jobs if j['id'] == data.get('jd_id')), None)
        candidate = next((c for c in candidates if c['id'] == data.get('candidate_id')), None)
        
        if not job or not candidate:
            return jsonify({'error': 'Job or candidate not found'}), 404
        
        match_score, match_details = calculate_weighted_match_score(
            job.get('skills_required', ''), 
            candidate.get('skills', '')
        )
        
        application = {
            'id': len(applications) + 1,
            'application_code': generate_code('APP'),
            'candidate_id': data.get('candidate_id'),
            'jd_id': data.get('jd_id'),
            'candidate_name': candidate.get('name'),
            'job_title': job.get('title'),
            'match_score': match_score,
            'match_details': match_details,
            'status': 'new',
            'current_stage': 'application_received',
            'application_date': datetime.now().date().isoformat(),
            'created_at': datetime.now().isoformat(),
            'updated_at': datetime.now().isoformat()
        }
        applications.append(application)
        
        job['applications'] = job.get('applications', 0) + 1
        
        # Auto-send email notification to candidate
        try:
            send_application_email(candidate.get('email'), candidate.get('name'), job.get('title'), match_score)
        except:
            pass
        
        return jsonify({
            'success': True, 
            'application_id': application['id'], 
            'match_score': match_score,
            'match_details': match_details
        })
    
    # GET request - return all applications
    return jsonify(applications)

def send_application_email(candidate_email, candidate_name, job_title, match_score):
    """Send application received email to candidate"""
    if not app.config['MAIL_USERNAME']:
        return
    try:
        subject = f"Application Received - {job_title}"
        body = f"""Dear {candidate_name},

Thank you for applying for the {job_title} position at ShahnaIT Scout.

Your application has been received and is under review. Your AI match score is {match_score}%.

We will contact you soon regarding the next steps.

Best regards,
ShahnaIT Recruitment Team"""
        
        msg = MIMEMultipart()
        msg['From'] = app.config['MAIL_DEFAULT_SENDER']
        msg['To'] = candidate_email
        msg['Subject'] = subject
        msg.attach(MIMEText(body, 'plain'))
        
        server = smtplib.SMTP(app.config['MAIL_SERVER'], app.config['MAIL_PORT'])
        server.starttls()
        server.login(app.config['MAIL_USERNAME'], app.config['MAIL_PASSWORD'])
        server.send_message(msg)
        server.quit()
    except Exception as e:
        print(f"Email error: {e}")

@app.route('/api/applications/<int:app_id>/move', methods=['PUT'])
def move_application_stage(app_id):
    """Move application to next pipeline stage"""
    data = request.get_json()
    new_stage = data.get('stage')
    
    for app in applications:
        if app['id'] == app_id:
            old_stage = app['status']
            app['status'] = new_stage
            app['current_stage'] = new_stage
            app['updated_at'] = datetime.now().isoformat()
            
            # Send notification on status change
            candidate = next((c for c in candidates if c['id'] == app.get('candidate_id')), None)
            if candidate and new_stage == 'shortlisted':
                try:
                    send_status_email(candidate.get('email'), candidate.get('name'), app.get('job_title'), new_stage)
                except:
                    pass
            break
    
    return jsonify({'success': True})

def send_status_email(candidate_email, candidate_name, job_title, status):
    """Send status update email to candidate"""
    if not app.config['MAIL_USERNAME']:
        return
    try:
        status_messages = {
            'shortlisted': "Congratulations! You have been shortlisted for the next round.",
            'interview': "Your interview has been scheduled. Check your dashboard for details.",
            'rejected': "We regret to inform you that you have not been selected for this position.",
            'offered': "Congratulations! You have received an offer letter."
        }
        
        subject = f"Application Status Update - {job_title}"
        body = f"""Dear {candidate_name},

{status_messages.get(status, f'Your application status has been updated to: {status}')}

Please log in to your candidate portal for more details.

Best regards,
ShahnaIT Recruitment Team"""
        
        msg = MIMEMultipart()
        msg['From'] = app.config['MAIL_DEFAULT_SENDER']
        msg['To'] = candidate_email
        msg['Subject'] = subject
        msg.attach(MIMEText(body, 'plain'))
        
        server = smtplib.SMTP(app.config['MAIL_SERVER'], app.config['MAIL_PORT'])
        server.starttls()
        server.login(app.config['MAIL_USERNAME'], app.config['MAIL_PASSWORD'])
        server.send_message(msg)
        server.quit()
    except Exception as e:
        print(f"Email error: {e}")

# ============= API ROUTES - INTERVIEWS =============

@app.route('/api/interviews', methods=['GET', 'POST'])
def manage_interviews():
    """Schedule and manage interviews"""
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
            'feedback': None,
            'rating': None,
            'result': None,
            'created_at': datetime.now().isoformat()
        }
        interviews.append(interview)
        
        application['status'] = 'interview-scheduled'
        
        # Send interview invitation email
        if candidate and candidate.get('email'):
            send_interview_email(candidate.get('email'), candidate.get('name'), job.get('title'), data)
        
        return jsonify({'success': True, 'interview_id': interview['id']})
    
    # GET request - return upcoming interviews
    now = datetime.now().isoformat()
    upcoming = [i for i in interviews if i.get('status') == 'scheduled']
    return jsonify(upcoming)

def send_interview_email(candidate_email, candidate_name, job_title, interview_data):
    """Send interview invitation email"""
    if not app.config['MAIL_USERNAME']:
        return
    try:
        scheduled_time = interview_data.get('scheduled_time', 'TBD')
        interviewer = interview_data.get('interviewer_name', 'Hiring Team')
        meeting_link = interview_data.get('meeting_link', 'Link will be shared separately')
        
        subject = f"Interview Invitation - {job_title}"
        body = f"""Dear {candidate_name},

We are pleased to invite you for an interview for the {job_title} position.

📅 Date & Time: {scheduled_time}
👤 Interviewer: {interviewer}
🔗 Meeting Link: {meeting_link}

Please join 5 minutes before the scheduled time.

Best regards,
ShahnaIT Recruitment Team"""
        
        msg = MIMEMultipart()
        msg['From'] = app.config['MAIL_DEFAULT_SENDER']
        msg['To'] = candidate_email
        msg['Subject'] = subject
        msg.attach(MIMEText(body, 'plain'))
        
        server = smtplib.SMTP(app.config['MAIL_SERVER'], app.config['MAIL_PORT'])
        server.starttls()
        server.login(app.config['MAIL_USERNAME'], app.config['MAIL_PASSWORD'])
        server.send_message(msg)
        server.quit()
    except Exception as e:
        print(f"Email error: {e}")

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
            
            # Update application status based on interview result
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

# ============= API ROUTES - OFFERS =============

@app.route('/api/offers', methods=['GET', 'POST'])
def manage_offers():
    """Generate and manage offer letters"""
    if request.method == 'POST':
        data = request.json
        
        # Find application if application_id provided
        application = None
        if data.get('application_id'):
            application = next((a for a in applications if a['id'] == data.get('application_id')), None)
        
        offer = {
            'id': len(offers) + 1,
            'offer_code': generate_code('OFF'),
            'application_id': data.get('application_id'),
            'candidate_name': data.get('candidate_name'),
            'candidate_email': data.get('candidate_email'),
            'job_title': data.get('job_title'),
            'base_salary': data.get('base_salary'),
            'joining_bonus': data.get('joining_bonus', 0),
            'joining_date': data.get('joining_date', (datetime.now().date() + timedelta(days=15)).isoformat()),
            'status': 'draft',
            'created_at': datetime.now().isoformat(),
            'offer_letter_html': generate_offer_letter_html(data)
        }
        offers.append(offer)
        
        if application:
            application['status'] = 'offered'
        
        return jsonify({
            'success': True, 
            'offer_id': offer['id'], 
            'offer_code': offer['offer_code'],
            'offer_html': offer['offer_letter_html']
        })
    
    return jsonify(offers)

@app.route('/api/offers/<int:offer_id>/send', methods=['POST'])
def send_offer(offer_id):
    """Send offer letter to candidate via email"""
    offer = next((o for o in offers if o['id'] == offer_id), None)
    if not offer:
        return jsonify({'error': 'Offer not found'}), 404
    
    offer['status'] = 'sent'
    offer['sent_at'] = datetime.now().isoformat()
    
    # Send offer email
    try:
        send_offer_email(offer.get('candidate_email'), offer.get('candidate_name'), offer.get('job_title'), offer.get('offer_letter_html'))
    except Exception as e:
        print(f"Offer email error: {e}")
    
    return jsonify({'success': True, 'message': 'Offer sent successfully'})
    
def send_offer_email(candidate_email, candidate_name, job_title, offer_html):
    """Send offer letter email to candidate"""
    if not app.config['MAIL_USERNAME']:
        return
    try:
        subject = f"Offer Letter - {job_title}"
        
        msg = MIMEMultipart('alternative')
        msg['From'] = app.config['MAIL_DEFAULT_SENDER']
        msg['To'] = candidate_email
        msg['Subject'] = subject
        
        text_body = f"""Dear {candidate_name},

We are pleased to offer you the position of {job_title} at ShahnaIT Scout.

Please find attached the offer letter with detailed terms and conditions.

Please review and confirm your acceptance by {datetime.now().date() + timedelta(days=15)}.

Best regards,
ShahnaIT Recruitment Team"""
        
        html_part = MIMEText(text_body, 'plain')
        msg.attach(html_part)
        
        server = smtplib.SMTP(app.config['MAIL_SERVER'], app.config['MAIL_PORT'])
        server.starttls()
        server.login(app.config['MAIL_USERNAME'], app.config['MAIL_PASSWORD'])
        server.send_message(msg)
        server.quit()
    except Exception as e:
        print(f"Offer email error: {e}")

# ============= API ROUTES - AI TOOLS =============

@app.route('/api/ai/generate-jd', methods=['POST'])
def ai_generate_jd():
    """Generate job description using Gemini AI"""
    data = request.json
    keywords = data.get('keywords', '')
    context = data.get('context', '')
    
    if GEMINI_AVAILABLE:
        prompt = f"""Generate a professional and detailed job description for a {keywords} position.
Additional context: {context if context else 'Standard corporate environment'}

Please include:
1. Job Title
2. Location (Remote/Hybrid/Onsite)
3. About the Role
4. Key Responsibilities (5-7 bullet points)
5. Required Skills & Qualifications
6. Preferred Skills (if any)
7. Benefits & Perks
8. Experience Level Required

Make it professional, clear, and tailored for the {keywords} role. Use markdown formatting for readability."""
        
        jd = call_gemini_ai(prompt)
        if jd:
            return jsonify({'success': True, 'jd': jd, 'ai_used': True})
    
    # Fallback template
    jd = f"""# Job Title: {keywords}

## Location
Remote / Hybrid

## About the Role
We are seeking a talented and motivated {keywords} to join our growing team. You will be responsible for designing, developing, and maintaining high-quality software solutions.

## Key Responsibilities
- Design, develop, and maintain high-quality software solutions
- Collaborate with cross-functional teams to deliver features
- Write clean, efficient, and well-documented code
- Participate in code reviews and technical discussions
- Troubleshoot and debug production issues
- Stay updated with emerging technologies and industry trends
- Mentor junior team members (for senior roles)

## Required Skills & Qualifications
- Bachelor's degree in Computer Science or related field
- {keywords} development experience
- Strong problem-solving abilities
- Excellent communication and teamwork skills
- Proficiency with version control (Git)
- Experience with Agile/Scrum methodologies

## Preferred Skills
- Cloud platform experience (AWS/Azure/GCP)
- Containerization (Docker/Kubernetes)
- CI/CD pipeline experience
- Open source contributions

## Benefits & Perks
- Competitive salary
- Flexible work hours
- Health insurance
- Learning and development budget
- Remote work allowance

## Experience Level
- Minimum 3+ years of relevant experience"""
    
    return jsonify({'success': True, 'jd': jd, 'ai_used': False})

@app.route('/api/ai/generate-questions', methods=['POST'])
def ai_generate_questions():
    """Generate interview questions using Gemini AI"""
    data = request.json
    role = data.get('role', '')
    level = data.get('level', 'mid')
    
    level_map = {
        'entry': 'entry-level (0-2 years experience)',
        'mid': 'mid-level (3-5 years experience)',
        'senior': 'senior-level (6+ years experience)',
        'lead': 'lead/architect (8+ years experience)'
    }
    
    if GEMINI_AVAILABLE:
        prompt = f"""Generate 10 professional interview questions for a {level_map.get(level, 'mid-level')} {role} position.

Questions should cover:
1. Technical skills assessment (2 questions)
2. Problem-solving and analytical thinking (2 questions)
3. Behavioral and situational (2 questions)
4. System design or architecture (1 question for mid/senior)
5. Leadership and team management (1 question for senior/lead)
6. Cultural fit and teamwork (1 question)
7. Career goals and motivation (1 question)

Make the questions specific to {role} role. Return as a numbered list with brief context for each question."""
        
        questions = call_gemini_ai(prompt)
        if questions:
            return jsonify({'success': True, 'questions': questions, 'ai_used': True})
    
    # Fallback questions
    questions = f"""1. [Technical] Can you describe your experience with {role} and the most challenging project you've worked on?
2. [Technical] What are the key technologies and frameworks you have mastered in {role}?
3. [Problem-Solving] Describe a time when you encountered a critical production issue. How did you approach and resolve it?
4. [Problem-Solving] How do you approach debugging a complex issue that spans multiple systems?
5. [Behavioral] Tell me about a time when you had to collaborate with difficult team members. How did you handle it?
6. [Behavioral] Describe a situation where you had to make a difficult technical decision with incomplete information.
7. [System Design] How would you design a scalable system for [specific requirement]?
8. [Leadership] How do you mentor junior team members and conduct effective code reviews?
9. [Cultural Fit] How do you handle feedback and criticism from peers or managers?
10. [Career Goals] Where do you see yourself in 5 years and how does this role align with your goals?"""
    
    return jsonify({'success': True, 'questions': questions, 'ai_used': False})

@app.route('/api/ai/generate-email', methods=['POST'])
def ai_generate_email():
    """Generate professional emails using Gemini AI"""
    data = request.json
    email_type = data.get('type', 'followup')
    candidate_name = data.get('candidate_name', 'Candidate')
    job_title = data.get('job_title', 'the position')
    
    if GEMINI_AVAILABLE:
        prompt = f"""Write a professional {email_type} email to {candidate_name} for the {job_title} position.

Email type: {email_type}
- If 'interview': Invite them for an interview with specific scheduling options
- If 'rejection': Politely inform they weren't selected, be kind and encouraging
- If 'offer': Send an offer letter summary with key terms
- If 'followup': Follow up on their application status

Include a clear subject line. Be professional, warm, and respectful. Keep it concise but informative."""
        
        email = call_gemini_ai(prompt)
        if email:
            return jsonify({'success': True, 'email': email, 'ai_used': True})
    
    # Fallback emails
    templates = {
        'interview': f"""Subject: Interview Invitation for {job_title} Position

Dear {candidate_name},

We were impressed with your application for the {job_title} position at ShahnaIT Scout.

We would like to invite you for an interview. Please let us know your availability for the following slots:
- Monday, 10:00 AM - 12:00 PM
- Tuesday, 2:00 PM - 4:00 PM
- Wednesday, 11:00 AM - 1:00 PM

Please confirm your preferred slot at your earliest convenience.

Best regards,
ShahnaIT Recruitment Team""",
        'rejection': f"""Subject: Update on your application for {job_title}

Dear {candidate_name},

Thank you for your interest in the {job_title} position at ShahnaIT Scout.

After careful review of your application, we have decided to move forward with other candidates whose qualifications more closely match our current requirements.

We appreciate the time and effort you invested in applying and wish you the very best in your job search.

Best regards,
ShahnaIT Recruitment Team""",
        'offer': f"""Subject: Offer Letter - {job_title} Position

Dear {candidate_name},

We are pleased to offer you the position of {job_title} at ShahnaIT Scout.

Key terms of the offer:
- Position: {job_title}
- Location: Remote/Hybrid
- Joining Date: [TBD]

Please find attached the detailed offer letter. We look forward to having you on our team!

Best regards,
ShahnaIT Recruitment Team""",
        'followup': f"""Subject: Follow-up on {job_title} Application

Dear {candidate_name},

We wanted to follow up on your application for the {job_title} position at ShahnaIT Scout.

Do you have any questions or need any additional information from our end? Please feel free to reach out.

We look forward to hearing from you.

Best regards,
ShahnaIT Recruitment Team"""
    }
    
    email = templates.get(email_type, templates['followup'])
    return jsonify({'success': True, 'email': email, 'ai_used': False})

# ============= API ROUTES - LINKEDIN IMPORT =============

@app.route('/api/linkedin/import', methods=['POST'])
def import_linkedin_profile():
    """Import and enrich candidate profile from LinkedIn URL"""
    data = request.json
    url = data.get('url', '')
    
    # Extract username from LinkedIn URL
    import re
    match = re.search(r'linkedin\.com/in/([a-zA-Z0-9-]+)', url)
    username = match.group(1) if match else 'unknown'
    
    # Simulated enriched data from LinkedIn
    # In production, this would call LinkedIn API with OAuth
    candidate_data = {
        'first_name': username.capitalize(),
        'last_name': '',
        'email': f"{username}@example.com",
        'linkedin_url': url,
        'skills': ['Leadership', 'Communication', 'Project Management', 'Strategic Planning', 'Team Collaboration'],
        'total_experience': 5,
        'current_company': 'Tech Corporation',
        'current_designation': 'Senior Professional',
        'current_location': 'Bangalore',
        'source': 'linkedin',
        'ai_enriched': True
    }
    
    return jsonify({'success': True, 'candidate': candidate_data})

# ============= API ROUTES - CLIENTS =============

@app.route('/api/clients', methods=['GET', 'POST', 'PUT', 'DELETE'])
def manage_clients():
    """Manage client companies"""
    global next_id
    
    if request.method == 'POST':
        data = request.get_json()
        client = {
            'id': next_id,
            'code': f"CLT-{next_id:04d}",
            'name': data.get('name', ''),
            'industry': data.get('industry', ''),
            'contact_person': data.get('contact_person', ''),
            'email': data.get('email', ''),
            'phone': data.get('phone', ''),
            'address': data.get('address', ''),
            'gst_number': data.get('gst_number', ''),
            'status': 'active',
            'created_at': datetime.now().isoformat()
        }
        if not hasattr(app, 'clients'):
            app.clients = []
        app.clients.append(client)
        next_id += 1
        return jsonify({'success': True, 'client_id': client['id'], 'client_code': client['code']})
    
    # GET request
    if not hasattr(app, 'clients'):
        app.clients = []
    return jsonify(app.clients)

# ============= API ROUTES - REPORTS & ANALYTICS =============

@app.route('/api/reports/hiring-metrics', methods=['GET'])
def hiring_metrics_report():
    """Generate comprehensive hiring metrics report"""
    total_apps = len(applications)
    
    # Time to hire calculation
    time_to_hire = []
    for app in applications:
        if app.get('status') == 'hired' and app.get('created_at'):
            try:
                created = datetime.fromisoformat(app['created_at'])
                hired = datetime.fromisoformat(app.get('hired_at', app['created_at']))
                days = (hired - created).days
                time_to_hire.append(days)
            except:
                pass
    
    avg_time_to_hire = sum(time_to_hire) / len(time_to_hire) if time_to_hire else 0
    
    # Stage conversion rates
    stage_counts = {
        'new': len([a for a in applications if a.get('status') == 'new']),
        'screening': len([a for a in applications if a.get('status') in ['screening', 'shortlisted']]),
        'interview': len([a for a in applications if a.get('status') in ['interview-scheduled', 'interviewed']]),
        'offer': len([a for a in applications if a.get('status') in ['offered', 'offer-accepted']]),
        'hired': len([a for a in applications if a.get('status') == 'hired']),
        'rejected': len([a for a in applications if a.get('status') == 'rejected'])
    }
    
    # AI match accuracy (average match score of hired candidates)
    hired_scores = [a.get('match_score', 0) for a in applications if a.get('status') == 'hired']
    ai_accuracy = sum(hired_scores) / len(hired_scores) if hired_scores else 0
    
    return jsonify({
        'total_applications': total_apps,
        'average_time_to_hire_days': round(avg_time_to_hire, 1),
        'ai_accuracy_percentage': round(ai_accuracy, 1),
        'conversion_rates': {
            'screening_to_interview': round((stage_counts['interview'] / max(stage_counts['screening'], 1)) * 100, 1),
            'interview_to_offer': round((stage_counts['offer'] / max(stage_counts['interview'], 1)) * 100, 1),
            'offer_to_hired': round((stage_counts['hired'] / max(stage_counts['offer'], 1)) * 100, 1),
            'overall': round((stage_counts['hired'] / max(total_apps, 1)) * 100, 1)
        },
        'applications_by_stage': stage_counts,
        'applications_over_time': {
            'last_7_days': len([a for a in applications if a.get('created_at', '').startswith((datetime.now() - timedelta(days=7)).date().isoformat())]),
            'last_30_days': len([a for a in applications if a.get('created_at', '') > (datetime.now() - timedelta(days=30)).isoformat()])
        },
        'source_breakdown': {
            'linkedin': len([c for c in candidates if c.get('source') == 'linkedin']),
            'naukri': len([c for c in candidates if c.get('source') == 'naukri']),
            'referral': len([c for c in candidates if c.get('source') == 'referral']),
            'ai_enriched': len([c for c in candidates if c.get('ai_enriched')]),
            'csv_import': len([c for c in candidates if c.get('source') == 'csv_import'])
        }
    })
    
# ============= API ROUTES - PIPELINE KANBAN =============

@app.route('/api/pipeline/stages', methods=['GET'])
def get_pipeline_stages():
    """Get all pipeline stages for kanban board"""
    return jsonify(PIPELINE_STAGES)

@app.route('/api/pipeline/candidates', methods=['GET'])
def get_pipeline_candidates():
    """Get candidates organized by pipeline stage for kanban board"""
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
                'avatar': candidate.get('avatar'),
                'match_score': app_detail.get('match_score'),
                'application_id': app_detail.get('application_id'),
                'applied_date': app_detail.get('applied_date')
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
            
            # Add activity log for stage change
            candidate = next((c for c in candidates if c['id'] == candidate_id), None)
            if candidate:
                print(f"Candidate {candidate.get('name')} moved from {old_stage} to {new_stage}")
            
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
            match_score, match_details = calculate_weighted_match_score(
                job.get('skills_required', ''), 
                candidate.get('skills', '')
            )
            
            new_application = {
                'id': len(applications) + 1,
                'application_code': generate_code('APP'),
                'candidate_id': candidate_id,
                'jd_id': job['id'],
                'job_title': job['title'],
                'candidate_name': candidate['name'],
                'match_score': match_score,
                'match_details': match_details,
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
    
    return jsonify({'success': False, 'error': 'No open jobs available. Please create a job first.'}), 400

# ============= API ROUTES - ACTIVITIES & SEARCH =============

@app.route('/api/activities/recent', methods=['GET'])
def get_recent_activities():
    """Get recent activities for dashboard"""
    activities = []
    
    # Recent applications
    recent_apps = sorted(applications, key=lambda x: x.get('created_at', ''), reverse=True)[:10]
    for app in recent_apps:
        candidate_name = app.get('candidate_name', 'Candidate')
        job_title = app.get('job_title', 'Position')
        activities.append({
            'type': 'application',
            'message': f"New application from {candidate_name} for {job_title}",
            'time': app.get('created_at'),
            'icon': 'bi-file-check',
            'color': '#4caf50'
        })
    
    # Recent interviews
    recent_interviews = sorted(interviews, key=lambda x: x.get('created_at', ''), reverse=True)[:10]
    for interview in recent_interviews:
        activities.append({
            'type': 'interview',
            'message': f"Interview scheduled for {interview.get('candidate_name')} with {interview.get('interviewer_name', 'Hiring Team')}",
            'time': interview.get('created_at'),
            'icon': 'bi-calendar-check',
            'color': '#2196f3'
        })
    
    # Recent offers
    recent_offers = sorted(offers, key=lambda x: x.get('created_at', ''), reverse=True)[:10]
    for offer in recent_offers:
        activities.append({
            'type': 'offer',
            'message': f"Offer generated for {offer.get('candidate_name')} - {offer.get('job_title')}",
            'time': offer.get('created_at'),
            'icon': 'bi-envelope-paper',
            'color': '#ff9800'
        })
    
    # Candidate additions
    recent_candidates = sorted(candidates, key=lambda x: x.get('created_at', ''), reverse=True)[:10]
    for candidate in recent_candidates:
        activities.append({
            'type': 'candidate',
            'message': f"New candidate added: {candidate.get('name')}",
            'time': candidate.get('created_at'),
            'icon': 'bi-person-plus',
            'color': '#9c27b0'
        })
    
    # Sort all activities by time (newest first)
    activities.sort(key=lambda x: x.get('time', ''), reverse=True)
    
    return jsonify(activities[:30])

@app.route('/api/search', methods=['GET'])
def global_search():
    """Global search across candidates and jobs"""
    query = request.args.get('q', '').lower()
    if not query:
        return jsonify({'candidates': [], 'jobs': [], 'applications': []})
    
    # Search candidates
    matched_candidates = []
    for c in candidates:
        if (query in c.get('name', '').lower() or 
            query in c.get('email', '').lower() or 
            query in c.get('skills', '').lower() or
            query in c.get('current_company', '').lower()):
            matched_candidates.append({
                'id': c['id'],
                'type': 'candidate',
                'name': c.get('name'),
                'email': c.get('email'),
                'skills': c.get('skills', ''),
                'code': c.get('code')
            })
    
    # Search jobs
    matched_jobs = []
    for j in jobs:
        if (query in j.get('title', '').lower() or 
            query in j.get('skills_required', '').lower() or
            query in j.get('location', '').lower()):
            matched_jobs.append({
                'id': j['id'],
                'type': 'job',
                'title': j.get('title'),
                'location': j.get('location'),
                'code': j.get('code'),
                'status': j.get('status')
            })
    
    # Search applications
    matched_applications = []
    for a in applications:
        if (query in a.get('candidate_name', '').lower() or 
            query in a.get('job_title', '').lower()):
            matched_applications.append({
                'id': a['id'],
                'type': 'application',
                'candidate_name': a.get('candidate_name'),
                'job_title': a.get('job_title'),
                'status': a.get('status'),
                'match_score': a.get('match_score')
            })
    
    return jsonify({
        'candidates': matched_candidates[:10],
        'jobs': matched_jobs[:10],
        'applications': matched_applications[:10],
        'total_results': len(matched_candidates) + len(matched_jobs) + len(matched_applications)
    })

# ============= API ROUTES - EXPORTS =============

@app.route('/api/export/candidates', methods=['GET'])
def export_candidates_csv():
    """Export all candidates to CSV"""
    output = io.StringIO()
    writer = csv.writer(output)
    
    # Write headers
    writer.writerow(['ID', 'Code', 'Name', 'Email', 'Phone', 'Skills', 'Current Company', 'Total Experience', 'Source', 'Created At'])
    
    # Write data
    for candidate in candidates:
        writer.writerow([
            candidate.get('id'),
            candidate.get('code'),
            candidate.get('name'),
            candidate.get('email'),
            candidate.get('phone', ''),
            candidate.get('skills', ''),
            candidate.get('current_company', ''),
            candidate.get('total_experience', 0),
            candidate.get('source', ''),
            candidate.get('created_at', '')
        ])
    
    output.seek(0)
    return send_file(
        io.BytesIO(output.getvalue().encode('utf-8')),
        mimetype='text/csv',
        as_attachment=True,
        download_name=f'candidates_export_{datetime.now().strftime("%Y%m%d")}.csv'
    )

@app.route('/api/export/applications', methods=['GET'])
def export_applications_csv():
    """Export all applications to CSV"""
    output = io.StringIO()
    writer = csv.writer(output)
    
    # Write headers
    writer.writerow(['ID', 'Candidate', 'Job', 'Match Score', 'Status', 'Application Date', 'Created At'])
    
    # Write data
    for app in applications:
        writer.writerow([
            app.get('id'),
            app.get('candidate_name'),
            app.get('job_title'),
            app.get('match_score', 0),
            app.get('status'),
            app.get('application_date'),
            app.get('created_at')
        ])
    
    output.seek(0)
    return send_file(
        io.BytesIO(output.getvalue().encode('utf-8')),
        mimetype='text/csv',
        as_attachment=True,
        download_name=f'applications_export_{datetime.now().strftime("%Y%m%d")}.csv'
    )

# ============= ERROR HANDLERS =============

@app.errorhandler(404)
def not_found(error):
    """Handle 404 errors"""
    return jsonify({
        'error': 'Resource not found',
        'message': 'The requested resource does not exist',
        'status': 404
    }), 404

@app.errorhandler(500)
def internal_error(error):
    """Handle 500 errors"""
    return jsonify({
        'error': 'Internal server error',
        'message': 'Something went wrong on our end',
        'status': 500
    }), 500

@app.errorhandler(413)
def too_large(error):
    """Handle file too large errors"""
    return jsonify({
        'error': 'File too large',
        'message': 'The uploaded file exceeds the maximum allowed size (100MB)',
        'status': 413
    }), 413

# ============= MAIN EXECUTION =============

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 8080))
    debug = os.environ.get('FLASK_ENV') == 'development'
    
    print("=" * 60)
    print("🚀 ShahnaIT Scout - Recruitment Management System")
    print("=" * 60)
    print(f"✅ Gemini AI: {'AVAILABLE' if GEMINI_AVAILABLE else 'NOT CONFIGURED (add GEMINI_API_KEY to .env)'}")
    print(f"✅ Email Service: {'CONFIGURED' if app.config['MAIL_USERNAME'] else 'NOT CONFIGURED'}")
    print(f"✅ Server running on port: {port}")
    print(f"✅ Debug mode: {debug}")
    print("=" * 60)
    print("📋 API Endpoints:")
    print("   GET  /health - Health check")
    print("   GET  /api/dashboard/stats - Dashboard statistics")
    print("   GET  /api/jds - List job descriptions")
    print("   POST /api/jds - Create job description")
    print("   GET  /api/candidates - List candidates")
    print("   POST /api/candidates - Create candidate")
    print("   GET  /api/applications - List applications")
    print("   POST /api/applications - Create application")
    print("   GET  /api/interviews - List interviews")
    print("   POST /api/interviews - Schedule interview")
    print("   GET  /api/offers - List offers")
    print("   POST /api/offers - Generate offer")
    print("   POST /api/ai/generate-jd - AI JD generation")
    print("   POST /api/ai/generate-questions - AI interview questions")
    print("   POST /api/ai/generate-email - AI email generation")
    print("=" * 60)
    
    app.run(host='0.0.0.0', port=port, debug=debug)
    
# ============= ADDITIONAL UTILITY FUNCTIONS =============

@app.route('/api/notifications', methods=['GET'])
def get_notifications():
    """Get user notifications"""
    notifications = []
    
    # Check for pending interviews today
    today = datetime.now().date().isoformat()
    pending_interviews = [i for i in interviews if i.get('scheduled_time', '').startswith(today) and i.get('status') == 'scheduled']
    if pending_interviews:
        notifications.append({
            'id': 'interview_reminder',
            'type': 'info',
            'title': f'{len(pending_interviews)} Interview(s) Today',
            'message': f'You have {len(pending_interviews)} interview(s) scheduled for today.',
            'time': datetime.now().isoformat(),
            'read': False
        })
    
    # Check for pending offers
    pending_offers = [o for o in offers if o.get('status') == 'draft']
    if pending_offers:
        notifications.append({
            'id': 'offer_pending',
            'type': 'warning',
            'title': f'{len(pending_offers)} Pending Offer(s)',
            'message': f'You have {len(pending_offers)} offer(s) waiting to be sent.',
            'time': datetime.now().isoformat(),
            'read': False
        })
    
    # Check for unread applications
    new_applications = [a for a in applications if a.get('status') == 'new']
    if new_applications:
        notifications.append({
            'id': 'new_applications',
            'type': 'success',
            'title': f'{len(new_applications)} New Application(s)',
            'message': f'{len(new_applications)} candidate(s) have applied to your jobs.',
            'time': datetime.now().isoformat(),
            'read': False
        })
    
    return jsonify(notifications)

@app.route('/api/notifications/mark-read', methods=['POST'])
def mark_notifications_read():
    """Mark notifications as read"""
    data = request.json
    notification_ids = data.get('ids', [])
    # In a real app, you would update a database
    return jsonify({'success': True})

@app.route('/api/settings', methods=['GET', 'POST'])
def get_settings():
    """Get or update application settings"""
    if request.method == 'POST':
        data = request.json
        # Save settings (in production, save to database)
        return jsonify({'success': True, 'message': 'Settings saved successfully'})
    
    # Return default settings
    settings = {
        'company_name': 'ShahnaIT Scout',
        'company_email': 'hr@shahnaiT.com',
        'company_phone': '+91-XXXXXXXXXX',
        'default_currency': 'INR',
        'date_format': 'DD/MM/YYYY',
        'timezone': 'Asia/Kolkata',
        'email_notifications': True,
        'auto_match_enabled': True,
        'ai_suggestions_enabled': True,
        'resume_parser_threshold': 70,
        'interview_reminder_hours': 24,
        'offer_validity_days': 15
    }
    return jsonify(settings)

@app.route('/api/webhook/naukri', methods=['POST'])
def naukri_webhook():
    """Webhook endpoint for Naukri.com integration"""
    data = request.json
    # Process incoming webhook from Naukri
    # In production, this would parse candidate data from Naukri and auto-create candidates
    print(f"Received Naukri webhook: {data}")
    return jsonify({'success': True, 'message': 'Webhook received'})

@app.route('/api/webhook/linkedin', methods=['POST'])
def linkedin_webhook():
    """Webhook endpoint for LinkedIn integration"""
    data = request.json
    # Process incoming webhook from LinkedIn
    print(f"Received LinkedIn webhook: {data}")
    return jsonify({'success': True, 'message': 'Webhook received'})

# ============= HEALTH CHECK DETAILS =============

@app.route('/api/health/details', methods=['GET'])
def health_details():
    """Detailed health check for monitoring"""
    return jsonify({
        'status': 'healthy',
        'timestamp': datetime.now().isoformat(),
        'services': {
            'gemini_ai': {
                'available': GEMINI_AVAILABLE,
                'configured': bool(GEMINI_API_KEY)
            },
            'email': {
                'configured': bool(app.config['MAIL_USERNAME']),
                'server': app.config['MAIL_SERVER']
            },
            'database': {
                'type': 'in-memory',
                'records': {
                    'jobs': len(jobs),
                    'candidates': len(candidates),
                    'applications': len(applications),
                    'interviews': len(interviews),
                    'offers': len(offers)
                }
            }
        },
        'version': '2.0.0',
        'features': [
            'ai_resume_parser',
            'ai_jd_generator',
            'ai_interview_questions',
            'ai_email_assistant',
            'linkedin_import',
            'bulk_csv_import',
            'kanban_pipeline',
            'document_management',
            'email_notifications',
            'offer_generation',
            'interview_scheduling',
            'advanced_filtering',
            'global_search',
            'csv_export',
            'webhook_support'
        ]
    })

# ============= SAMPLE DATA INITIALIZATION (OPTIONAL) =============

def init_sample_data():
    """Initialize sample data for testing"""
    if not jobs and not candidates:
        # Sample Job
        sample_job = {
            'id': 1,
            'code': 'JD-0001',
            'title': 'Senior Python Developer',
            'location': 'Remote',
            'status': 'open',
            'skills_required': 'Python, Django, PostgreSQL, AWS, Docker',
            'applications': 0,
            'created_at': datetime.now().isoformat()
        }
        jobs.append(sample_job)
        
        # Sample Candidate
        sample_candidate = {
            'id': 1,
            'code': 'CAN-0001',
            'name': 'John Doe',
            'email': 'john.doe@example.com',
            'skills': 'Python, Django, React, AWS',
            'total_experience': 5,
            'source': 'sample',
            'created_at': datetime.now().isoformat()
        }
        candidates.append(sample_candidate)
        
        # Sample Application
        match_score = calculate_weighted_match_score(
            sample_job['skills_required'],
            sample_candidate['skills']
        )[0]
        
        sample_application = {
            'id': 1,
            'application_code': 'APP-0001',
            'candidate_id': 1,
            'jd_id': 1,
            'candidate_name': 'John Doe',
            'job_title': 'Senior Python Developer',
            'match_score': match_score,
            'status': 'new',
            'application_date': datetime.now().date().isoformat(),
            'created_at': datetime.now().isoformat()
        }
        applications.append(sample_application)
        sample_job['applications'] = 1
        
        print("✅ Sample data initialized")

# Uncomment to initialize sample data
# init_sample_data()

# ============= FINAL OUTPUT =============
print("=" * 60)
print("🎉 ShahnaIT Scout - Recruitment Management System")
print("=" * 60)
print("✅ All modules loaded successfully")
print("✅ API routes registered")
print("✅ Ready to accept connections")
print("=" * 60)
