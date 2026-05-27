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
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', secrets.token_hex(32))
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL', 'sqlite:///recruitment.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['MAIL_SERVER'] = os.environ.get('MAIL_SERVER', 'smtp.gmail.com')
app.config['MAIL_PORT'] = int(os.environ.get('MAIL_PORT', 587))
app.config['MAIL_USE_TLS'] = True
app.config['MAIL_USERNAME'] = os.environ.get('MAIL_USERNAME', '')
app.config['MAIL_PASSWORD'] = os.environ.get('MAIL_PASSWORD', '')
app.config['MAIL_DEFAULT_SENDER'] = os.environ.get('MAIL_DEFAULT_SENDER', 'noreply@shahnaiT.com')

# ============= HTML DASHBOARD TEMPLATE =============
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
        .btn-primary-modern { background: linear-gradient(135deg, #4361ee, #3a0ca3); border: none; padding: 10px 24px; border-radius: 30px; font-weight: 600; transition: all 0.3s; }
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
        .skill-entry, .experience-entry, .education-entry { transition: all 0.2s; }
        .ai-badge { background: linear-gradient(135deg, #667eea, #764ba2); color: white; padding: 2px 8px; border-radius: 12px; font-size: 0.7rem; margin-left: 8px; }
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
            <div class="modern-header"><div class="page-title"><h1>Recruitment Dashboard</h1><p>Track your hiring pipeline, candidates, and analytics in real-time</p></div><div class="header-actions"><div class="search-bar"><i class="bi bi-search"></i><input type="text" placeholder="Search candidates, jobs..."></div></div></div>
            <div class="stats-grid" id="statsGrid">
                <div class="stat-card-modern"><div class="stat-icon-modern" style="background: linear-gradient(135deg, #4361ee20, #3a0ca320); color: #4361ee;"><i class="bi bi-briefcase"></i></div><div class="stat-value-modern" id="openPositions">0</div><div class="stat-label-modern">Open Positions</div><div class="stat-trend"><span style="color: #4caf50;"><i class="bi bi-arrow-up"></i> +12%</span> vs last month</div></div>
                <div class="stat-card-modern"><div class="stat-icon-modern" style="background: linear-gradient(135deg, #4caf5020, #2e7d3220); color: #4caf50;"><i class="bi bi-people"></i></div><div class="stat-value-modern" id="totalCandidates">0</div><div class="stat-label-modern">Total Candidates</div><div class="stat-trend"><span style="color: #4caf50;"><i class="bi bi-arrow-up"></i> +8%</span> vs last month</div></div>
                <div class="stat-card-modern"><div class="stat-icon-modern" style="background: linear-gradient(135deg, #ff980020, #ed6c0220); color: #ff9800;"><i class="bi bi-calendar-check"></i></div><div class="stat-value-modern" id="interviewsToday">0</div><div class="stat-label-modern">Interviews Today</div><div class="stat-trend"><span style="color: #2196f3;">AI Scheduler Active</span></div></div>
                <div class="stat-card-modern"><div class="stat-icon-modern" style="background: linear-gradient(135deg, #9c27b020, #6a1b9a20); color: #9c27b0;"><i class="bi bi-robot"></i></div><div class="stat-value-modern" id="aiMatches">0</div><div class="stat-label-modern">AI Matches</div><div class="stat-trend"><span style="color: #9c27b0;"><i class="bi bi-stars"></i> Smart Scoring</span></div></div>
            </div>
            <div class="row"><div class="col-lg-8"><div class="chart-card"><div class="chart-header"><h5><i class="bi bi-graph-up"></i> Recruitment Funnel <span class="ai-badge">AI Analytics</span></h5></div><canvas id="pipelineChart" height="280"></canvas></div></div><div class="col-lg-4"><div class="chart-card"><div class="chart-header"><h5><i class="bi bi-pie-chart"></i> Candidate Sources</h5></div><canvas id="sourcesChart" height="280"></canvas></div></div></div>
            <div class="row mt-3"><div class="col-lg-6"><div class="chart-card"><div class="chart-header"><h5><i class="bi bi-lightning-charge"></i> Quick Actions</h5></div><div class="d-flex gap-3 flex-wrap"><button class="btn btn-primary-modern" onclick="showJDMasterModal()"><i class="bi bi-plus-circle"></i> Post a Job</button><button class="btn btn-outline-modern" onclick="showCandidateModal()"><i class="bi bi-person-plus"></i> Add Candidate</button><button class="btn btn-outline-modern" onclick="showResumeUploadModal()"><i class="bi bi-file-earmark-arrow-up"></i> Upload Resume</button><button class="btn btn-outline-modern" onclick="showAITools()"><i class="bi bi-stars"></i> AI Tools</button></div></div></div><div class="col-lg-6"><div class="chart-card"><div class="chart-header"><h5><i class="bi bi-clock-history"></i> Recent Activity</h5></div><div id="activitiesList" style="max-height: 200px; overflow-y: auto;"></div></div></div></div>
        </div>
        
        <div id="jdsSection" style="display: none;"><div class="modern-header"><div class="page-title"><h1>Job Descriptions</h1><p>Manage all your job openings</p></div><div class="header-actions"><button class="btn btn-primary-modern" onclick="showJDMasterModal()"><i class="bi bi-plus-circle"></i> Create Job</button><button class="btn btn-outline-modern" onclick="showJDUploadModal()"><i class="bi bi-cloud-upload"></i> Upload JD</button><button class="btn btn-outline-modern" onclick="generateAIJD()"><i class="bi bi-stars"></i> AI Generate JD</button></div></div><div class="modern-table"><table class="table"><thead><tr><th>Code</th><th>Title</th><th>Client</th><th>Location</th><th>Type</th><th>Status</th><th>Applications</th><th>Priority</th><th>Actions</th></tr></thead><tbody id="jdsTableBody"></tbody></table></div></div>
        
        <div id="candidatesSection" style="display: none;"><div class="modern-header"><div class="page-title"><h1>Candidates Database</h1><p>Manage your talent pool <span class="ai-badge">AI Enriched</span></p></div><div class="header-actions"><button class="btn btn-primary-modern" onclick="showCandidateModal()"><i class="bi bi-person-plus"></i> Add Candidate</button><button class="btn btn-outline-modern" onclick="showResumeUploadModal()"><i class="bi bi-file-earmark-arrow-up"></i> Upload Resume</button><button class="btn btn-outline-modern" onclick="showLinkedInImport()"><i class="bi bi-linkedin"></i> Import from LinkedIn</button></div></div><div class="row mb-3"><div class="col-md-3"><input type="text" class="form-control" id="candidateSearch" placeholder="Search by name, email, skill..."></div><div class="col-md-2"><select class="form-select" id="sourceFilter"><option value="">All Sources</option><option value="linkedin">LinkedIn</option><option value="naukri">Naukri</option><option value="referral">Referral</option><option value="ai-enriched">AI Enriched</option></select></div><div class="col-md-2"><button class="btn btn-primary-modern" onclick="loadCandidates()"><i class="bi bi-search"></i> Search</button><button class="btn btn-outline-modern" onclick="showAdvancedFilters()"><i class="bi bi-funnel"></i> Filters</button></div></div><div id="candidatesList"></div><div id="candidatesPagination" class="mt-3"></div></div>
        
        <div id="applicationsSection" style="display: none;"><div class="modern-header"><div class="page-title"><h1>Applications</h1><p>Track all candidate applications <span class="ai-badge">Smart Ranking</span></p></div></div><div class="modern-table"><table class="table"><thead><tr><th>ID</th><th>Candidate</th><th>Job</th><th>AI Match Score</th><th>Status</th><th>Actions</th></tr></thead><tbody id="applicationsTable"></tbody></table></div></div>
        
        <div id="pipelineSection" style="display: none;"><div class="modern-header"><div class="page-title"><h1>Recruitment Pipeline</h1><p>Drag and drop candidates to move between stages</p></div><button class="btn btn-outline-modern" onclick="showPipelineAnalytics()"><i class="bi bi-graph-up"></i> Pipeline Analytics</button></div><div id="kanbanBoard" class="kanban-board"></div></div>
        
        <div id="interviewsSection" style="display: none;"><div class="modern-header"><div class="page-title"><h1>Interviews</h1><p>Schedule and manage interviews <span class="ai-badge">AI Scheduling</span></p></div><div class="header-actions"><button class="btn btn-primary-modern" onclick="showInterviewModal()"><i class="bi bi-plus-circle"></i> Schedule Interview</button><button class="btn btn-outline-modern" onclick="showAIScheduler()"><i class="bi bi-stars"></i> AI Smart Schedule</button></div></div><div id="interviewsList"></div></div>
        
        <div id="offersSection" style="display: none;"><div class="modern-header"><div class="page-title"><h1>Offer Letters</h1><p>Generate and manage offers</p></div><div class="header-actions"><button class="btn btn-primary-modern" onclick="showOfferModal()"><i class="bi bi-envelope-paper"></i> Generate Offer</button><button class="btn btn-outline-modern" onclick="showOfferTemplateModal()"><i class="bi bi-file-text"></i> Templates</button></div></div><div id="offersList"></div></div>
        
        <div id="analyticsSection" style="display: none;"><div class="modern-header"><div class="page-title"><h1>Analytics & Reports</h1><p>Data-driven insights for your recruitment <span class="ai-badge">AI Insights</span></p></div></div><div class="row"><div class="col-lg-6"><div class="chart-card"><canvas id="dailyAppsChart" height="250"></canvas></div></div><div class="col-lg-6"><div class="chart-card"><canvas id="stageDistChart" height="250"></canvas></div></div></div><div class="row mt-3"><div class="col-lg-4"><div class="chart-card"><h6>Time-to-Hire Analysis</h6><canvas id="timeToHireChart" height="200"></canvas></div></div><div class="col-lg-4"><div class="chart-card"><h6>Source Effectiveness</h6><canvas id="sourceEffectivenessChart" height="200"></canvas></div></div><div class="col-lg-4"><div class="chart-card"><h6>AI Match Accuracy</h6><canvas id="aiAccuracyChart" height="200"></canvas></div></div></div></div>
        
        <div id="aiToolsSection" style="display: none;"><div class="modern-header"><div class="page-title"><h1>AI Tools</h1><p>Supercharge your recruitment with artificial intelligence</p></div></div><div class="row">
            <div class="col-md-4 mb-3"><div class="card h-100"><div class="card-body"><div class="text-center mb-3"><i class="bi bi-file-text" style="font-size: 3rem; color: #4361ee;"></i></div><h5 class="text-center">AI Resume Parser</h5><p class="text-center text-muted small">Extract candidate info from PDF/DOCX with 98% accuracy</p><button class="btn btn-primary-modern w-100" onclick="showResumeUploadModal()">Upload Resume</button></div></div></div>
            <div class="col-md-4 mb-3"><div class="card h-100"><div class="card-body"><div class="text-center mb-3"><i class="bi bi-file-earmark-text" style="font-size: 3rem; color: #4caf50;"></i></div><h5 class="text-center">AI JD Generator</h5><p class="text-center text-muted small">Generate job descriptions from keywords or existing JDs</p><button class="btn btn-primary-modern w-100" onclick="generateAIJD()">Generate JD</button></div></div></div>
            <div class="col-md-4 mb-3"><div class="card h-100"><div class="card-body"><div class="text-center mb-3"><i class="bi bi-chat-dots" style="font-size: 3rem; color: #ff9800;"></i></div><h5 class="text-center">AI Interview Questions</h5><p class="text-center text-muted small">Generate role-specific interview questions</p><button class="btn btn-primary-modern w-100" onclick="generateAIQuestions()">Generate Questions</button></div></div></div>
            <div class="col-md-4 mb-3"><div class="card h-100"><div class="card-body"><div class="text-center mb-3"><i class="bi bi-linkedin" style="font-size: 3rem; color: #0077b5;"></i></div><h5 class="text-center">LinkedIn Profile Enrichment</h5><p class="text-center text-muted small">Import and enrich candidate data from LinkedIn</p><button class="btn btn-primary-modern w-100" onclick="showLinkedInImport()">Import from LinkedIn</button></div></div></div>
            <div class="col-md-4 mb-3"><div class="card h-100"><div class="card-body"><div class="text-center mb-3"><i class="bi bi-envelope-paper" style="font-size: 3rem; color: #f44336;"></i></div><h5 class="text-center">AI Email Assistant</h5><p class="text-center text-muted small">Generate personalized emails for candidates</p><button class="btn btn-primary-modern w-100" onclick="generateAIEmail()">Generate Email</button></div></div></div>
            <div class="col-md-4 mb-3"><div class="card h-100"><div class="card-body"><div class="text-center mb-3"><i class="bi bi-graph-up" style="font-size: 3rem; color: #9c27b0;"></i></div><h5 class="text-center">AI Candidate Scoring</h5><p class="text-center text-muted small">Get AI-powered candidate recommendations</p><button class="btn btn-primary-modern w-100" onclick="showAIScoring()">Score Candidates</button></div></div></div>
        </div></div>
    </div>
    
    <!-- All Modals (JD, Candidate, Resume, Interview, Offer, Reports, Kanban, AI Tools) -->
    <div class="modal fade modal-modern" id="jdMasterModal" tabindex="-1"><div class="modal-dialog modal-lg"><div class="modal-content"><div class="modal-header"><h5 class="modal-title"><i class="bi bi-briefcase"></i> Create Job Description</h5><button type="button" class="btn-close btn-close-white" data-bs-dismiss="modal"></button></div><div class="modal-body"><form id="jdMasterForm"><div class="form-section"><div class="form-section-title">Basic Information</div><div class="row"><div class="col-md-8 mb-2"><label>Job Title *</label><input type="text" class="form-control" id="jdTitle" required></div><div class="col-md-4 mb-2"><label>Client</label><select class="form-select" id="jdClientId"></select></div><div class="col-md-4 mb-2"><label>Department</label><input type="text" class="form-control" id="jdDepartment"></div><div class="col-md-4 mb-2"><label>Location</label><input type="text" class="form-control" id="jdLocation"></div><div class="col-md-4 mb-2"><label>Location Type</label><select class="form-select" id="jdLocationType"><option value="remote">Remote</option><option value="onsite">Onsite</option><option value="hybrid">Hybrid</option></select></div><div class="col-md-6 mb-2"><label>Employment Type</label><select class="form-select" id="jdEmploymentType"><option value="full-time">Full Time</option><option value="part-time">Part Time</option><option value="contract">Contract</option><option value="freelance">Freelance</option><option value="internship">Internship</option></select></div><div class="col-md-6 mb-2"><label>No. of Positions</label><input type="number" class="form-control" id="jdPositions" value="1"></div></div></div><div class="form-section"><div class="form-section-title">Experience & Salary</div><div class="row"><div class="col-md-3 mb-2"><label>Min Experience (years)</label><input type="number" class="form-control" id="jdExpMin" value="0"></div><div class="col-md-3 mb-2"><label>Max Experience (years)</label><input type="number" class="form-control" id="jdExpMax" value="10"></div><div class="col-md-3 mb-2"><label>Min Salary</label><input type="number" class="form-control" id="jdSalaryMin"></div><div class="col-md-3 mb-2"><label>Max Salary</label><input type="number" class="form-control" id="jdSalaryMax"></div></div></div><div class="form-section"><div class="form-section-title">Skills & Qualifications</div><div class="mb-2"><label>Required Skills (comma separated)</label><textarea class="form-control" id="jdSkills" rows="2" placeholder="Python, Java, SQL, AWS, Docker..."></textarea></div><div class="mb-2"><label>Preferred Skills</label><textarea class="form-control" id="jdSkillsPref" rows="2"></textarea></div><div class="mb-2"><label>Qualifications</label><textarea class="form-control" id="jdQualifications" rows="2"></textarea></div></div><div class="form-section"><div class="form-section-title">Job Description</div><div class="mb-2"><label>Responsibilities</label><textarea class="form-control" id="jdResponsibilities" rows="4"></textarea></div><div class="mb-2"><label>Benefits</label><textarea class="form-control" id="jdBenefits" rows="2"></textarea></div></div><div class="row"><div class="col-md-6 mb-2"><label>Status</label><select class="form-select" id="jdStatus"><option value="draft">Draft</option><option value="published">Published</option><option value="open">Open</option></select></div><div class="col-md-6 mb-2"><label>Priority</label><select class="form-select" id="jdPriority"><option value="low">Low</option><option value="medium">Medium</option><option value="high">High</option><option value="urgent">Urgent</option></select></div></div><button type="submit" class="btn btn-primary-modern w-100">Create Job Description</button></form></div></div></div></div>
    
    <div class="modal fade modal-modern" id="jdUploadModal" tabindex="-1"><div class="modal-dialog"><div class="modal-content"><div class="modal-header"><h5 class="modal-title"><i class="bi bi-cloud-upload"></i> Upload JD Document</h5><button type="button" class="btn-close btn-close-white" data-bs-dismiss="modal"></button></div><div class="modal-body"><div class="text-center mb-3"><i class="bi bi-file-earmark-pdf" style="font-size: 3rem;"></i><i class="bi bi-file-earmark-word" style="font-size: 3rem;"></i><span class="ai-badge">AI Parsing</span></div><div class="mb-3"><input type="file" class="form-control" id="jdUploadFile" accept=".pdf,.docx,.txt"><div class="form-text">Upload PDF, DOCX, or TXT file. AI will extract all details automatically.</div></div><div id="jdParseProgress" style="display: none;" class="text-center"><div class="loader"></div><p class="mt-2">AI is analyzing the document...</p></div><button class="btn btn-primary-modern w-100" onclick="uploadAndParseJD()"><i class="bi bi-robot"></i> Parse & Auto-fill</button></div></div></div></div>
    
    <div class="modal fade modal-modern" id="candidateModal" tabindex="-1"><div class="modal-dialog modal-xl"><div class="modal-content"><div class="modal-header"><h5 class="modal-title"><i class="bi bi-person-badge"></i> Add/Edit Candidate - Complete Profile</h5><button type="button" class="btn-close btn-close-white" data-bs-dismiss="modal"></button></div><div class="modal-body" style="max-height: 70vh; overflow-y: auto;"><form id="candidateForm" enctype="multipart/form-data"><div class="card mb-3"><div class="card-header bg-primary text-white">Personal Information</div><div class="card-body"><div class="row"><div class="col-md-4 mb-2"><label>First Name *</label><input type="text" class="form-control" id="candFirstName" required></div><div class="col-md-4 mb-2"><label>Last Name</label><input type="text" class="form-control" id="candLastName"></div><div class="col-md-4 mb-2"><label>Email *</label><input type="email" class="form-control" id="candEmail" required></div><div class="col-md-3 mb-2"><label>Mobile Number</label><input type="tel" class="form-control" id="candPhone"></div><div class="col-md-3 mb-2"><label>Alternate Number</label><input type="tel" class="form-control" id="candAltPhone"></div><div class="col-md-3 mb-2"><label>LinkedIn ID</label><input type="text" class="form-control" id="candLinkedin" placeholder="linkedin.com/in/username"></div><div class="col-md-3 mb-2"><label>GitHub</label><input type="text" class="form-control" id="candGithub"></div><div class="col-md-6 mb-2"><label>Address</label><textarea class="form-control" id="candAddress" rows="2"></textarea></div><div class="col-md-6 mb-2"><label>Current Location</label><input type="text" class="form-control" id="candLocation"></div><div class="col-md-3 mb-2"><label>PAN Card Number</label><input type="text" class="form-control" id="candPan"></div><div class="col-md-3 mb-2"><label>Aadhar Number</label><input type="text" class="form-control" id="candAadhar"></div><div class="col-md-3 mb-2"><label>Passport Number</label><input type="text" class="form-control" id="candPassport"></div><div class="col-md-3 mb-2"><label>Date of Birth</label><input type="date" class="form-control" id="candDob"></div></div></div></div><div class="card mb-3"><div class="card-header bg-info text-white">Professional Summary <span class="ai-badge">AI Enriched</span></div><div class="card-body"><div class="row"><div class="col-md-4 mb-2"><label>Primary Role</label><input type="text" class="form-control" id="candPrimaryRole"></div><div class="col-md-4 mb-2"><label>Total Experience (Years)</label><input type="number" step="0.5" class="form-control" id="candTotalExp" value="0"></div><div class="col-md-4 mb-2"><label>Relevant Experience</label><input type="number" step="0.5" class="form-control" id="candRelevantExp" value="0"></div><div class="col-md-12 mb-2"><label>Professional Summary</label><textarea class="form-control" id="candSummary" rows="2"></textarea></div></div></div></div><div class="card mb-3"><div class="card-header bg-warning text-dark">Skills</div><div class="card-body"><div id="skillsContainer"></div><button type="button" class="btn btn-sm btn-outline-primary mt-1" onclick="addSkillEntry()">+ Add Skill</button><button type="button" class="btn btn-sm btn-outline-info mt-1 ms-2" onclick="suggestAISkills()"><i class="bi bi-stars"></i> AI Suggest Skills</button></div></div><div class="card mb-3"><div class="card-header bg-secondary text-white">Work Experience</div><div class="card-body"><div id="experienceContainer"></div><button type="button" class="btn btn-sm btn-outline-secondary mt-1" onclick="addExperienceEntry()">+ Add Company</button></div></div><div class="card mb-3"><div class="card-header bg-dark text-white">Education</div><div class="card-body"><div id="educationContainer"></div><button type="button" class="btn btn-sm btn-outline-dark mt-1" onclick="addEducationEntry()">+ Add Education</button></div></div><div class="card mb-3"><div class="card-header bg-dark text-white">Salary & Notice Period</div><div class="card-body"><div class="row"><div class="col-md-3 mb-2"><label>Current Salary (₹)</label><input type="number" class="form-control" id="candCurrentSalary"></div><div class="col-md-3 mb-2"><label>Expected Salary (₹)</label><input type="number" class="form-control" id="candExpectedSalary"></div><div class="col-md-3 mb-2"><label>Notice Period (days)</label><input type="number" class="form-control" id="candNoticePeriod"></div><div class="col-md-3 mb-2"><label>Source</label><select class="form-control" id="candSource"><option value="linkedin">LinkedIn</option><option value="naukri">Naukri</option><option value="referral">Referral</option><option value="ai-enriched">AI Enriched</option><option value="manual">Manual</option></select></div></div></div></div><div class="card mb-3"><div class="card-header bg-danger text-white"><i class="bi bi-file-earmark-text"></i> Candidate Documents</div><div class="card-body"><div class="row"><div class="col-md-6 mb-3"><label>📄 Resume/CV</label><input type="file" class="form-control" id="docResume" accept=".pdf,.docx,.doc"><div id="resumeFileName" class="small text-success mt-1"></div></div><div class="col-md-6 mb-3"><label>🎓 Highest Degree Certificate</label><input type="file" class="form-control" id="docDegree" accept=".pdf,.jpg,.png"><div id="degreeFileName" class="small text-success mt-1"></div></div><div class="col-md-4 mb-3"><label>💰 Pay Slip</label><input type="file" class="form-control" id="docPaySlip" accept=".pdf,.jpg,.png"><div id="paySlipFileName" class="small text-success mt-1"></div></div><div class="col-md-4 mb-3"><label>📑 Form 16</label><input type="file" class="form-control" id="docForm16" accept=".pdf"><div id="form16FileName" class="small text-success mt-1"></div></div><div class="col-md-4 mb-3"><label>🪪 PAN Card</label><input type="file" class="form-control" id="docPan" accept=".pdf,.jpg,.png"><div id="panFileName" class="small text-success mt-1"></div></div><div class="col-md-4 mb-3"><label>🆔 Aadhar Card</label><input type="file" class="form-control" id="docAadhar" accept=".pdf,.jpg,.png"><div id="aadharFileName" class="small text-success mt-1"></div></div><div class="col-md-4 mb-3"><label>📸 Passport Photo</label><input type="file" class="form-control" id="docPhoto" accept=".jpg,.png"><div id="photoFileName" class="small text-success mt-1"></div></div><div class="col-md-4 mb-3"><label>📜 Offer Letter (signed)</label><input type="file" class="form-control" id="docOfferLetter" accept=".pdf"><div id="offerLetterFileName" class="small text-success mt-1"></div></div><div class="col-md-12 mb-3"><label>📎 Other Documents</label><input type="file" class="form-control" id="docOther" accept=".pdf,.jpg,.png,.docx"><div id="otherFileName" class="small text-success mt-1"></div></div></div></div></div><button type="submit" class="btn btn-success w-100">Save Candidate Profile</button></form></div></div></div></div>
    
    <div class="modal fade modal-modern" id="resumeUploadModal" tabindex="-1"><div class="modal-dialog"><div class="modal-content"><div class="modal-header"><h5 class="modal-title"><i class="bi bi-file-earmark-arrow-up"></i> Upload Resume <span class="ai-badge">AI Powered</span></h5><button type="button" class="btn-close btn-close-white" data-bs-dismiss="modal"></button></div><div class="modal-body"><div class="mb-3"><input type="file" class="form-control" id="resumeFile" accept=".pdf,.docx"><div class="form-text">Upload candidate's resume. AI will extract all information automatically.</div></div><div id="resumeParseProgress" style="display: none;" class="text-center"><div class="loader"></div><p class="mt-2">AI is analyzing the resume...</p></div><div id="resumePreview" style="display: none;"><h6>Extracted Information:</h6><pre id="resumeExtractedData" class="bg-light p-2 rounded" style="font-size: 0.8rem;"></pre><button class="btn btn-primary-modern w-100" onclick="createCandidateFromResume()">Create Candidate Profile</button></div><button class="btn btn-primary-modern w-100" onclick="parseResume()" id="parseResumeBtn"><i class="bi bi-robot"></i> Parse Resume</button></div></div></div></div>
    
    <div class="modal fade modal-modern" id="applicationModal" tabindex="-1"><div class="modal-dialog"><div class="modal-content"><div class="modal-header"><h5 class="modal-title">Create Application <span class="ai-badge">AI Match Scoring</span></h5><button type="button" class="btn-close btn-close-white" data-bs-dismiss="modal"></button></div><div class="modal-body"><form id="applicationForm"><div class="mb-2"><label>Candidate</label><select class="form-select" id="appCandidateId" required></select></div><div class="mb-2"><label>Job Description</label><select class="form-select" id="appJdId" required></select></div><div id="matchScoreDisplay" class="alert alert-info" style="display: none;">AI Match Score: <strong id="matchScore"></strong>%</div><button type="submit" class="btn btn-primary-modern w-100">Create Application</button></form></div></div></div></div>
    
    <div class="modal fade modal-modern" id="interviewModal" tabindex="-1"><div class="modal-dialog"><div class="modal-content"><div class="modal-header"><h5 class="modal-title">Schedule Interview <span class="ai-badge">Smart Scheduling</span></h5><button type="button" class="btn-close btn-close-white" data-bs-dismiss="modal"></button></div><div class="modal-body"><form id="interviewForm"><div class="mb-2"><label>Application</label><select class="form-select" id="interviewAppId" required></select></div><div class="mb-2"><label>Round Type</label><select class="form-select" id="interviewRoundType"><option value="telephonic">Telephonic Screening</option><option value="technical">Technical Round</option><option value="coding">Coding Assessment</option><option value="system-design">System Design</option><option value="managerial">Managerial Round</option><option value="hr">HR Round</option><option value="client">Client Round</option><option value="final">Final Round</option></select></div><div class="mb-2"><label>Interviewer Name</label><input type="text" class="form-control" id="interviewerName"></div><div class="mb-2"><label>Interviewer Email</label><input type="email" class="form-control" id="interviewerEmail"></div><div class="mb-2"><label>Scheduled Date & Time</label><input type="datetime-local" class="form-control" id="interviewDateTime"></div><div class="mb-2"><label>Meeting Link (Google Meet/Zoom)</label><input type="url" class="form-control" id="interviewLink"></div><button type="submit" class="btn btn-warning w-100">Schedule Interview</button></form></div></div></div></div>
    
    <div class="modal fade modal-modern" id="offerModal" tabindex="-1"><div class="modal-dialog"><div class="modal-content"><div class="modal-header"><h5 class="modal-title">Generate Offer Letter</h5><button type="button" class="btn-close btn-close-white" data-bs-dismiss="modal"></button></div><div class="modal-body"><form id="offerForm"><div class="mb-2"><label>Application ID</label><input type="number" class="form-control" id="offerAppId" required></div><div class="mb-2"><label>Candidate Name</label><input type="text" class="form-control" id="candidateNameOffer" required></div><div class="mb-2"><label>Candidate Email</label><input type="email" class="form-control" id="candidateEmailOffer" required></div><div class="mb-2"><label>Job Title</label><input type="text" class="form-control" id="jobTitleOffer" required></div><div class="mb-2"><label>Base Salary ($)</label><input type="number" class="form-control" id="baseSalary" required></div><div class="mb-2"><label>Joining Bonus ($)</label><input type="number" class="form-control" id="joiningBonus"></div><div class="mb-2"><label>Joining Date</label><input type="date" class="form-control" id="joiningDate"></div><button type="submit" class="btn btn-primary-modern w-100">Generate Offer</button></form></div></div></div></div>
    
    <div class="modal fade modal-modern" id="aiToolsModal" tabindex="-1"><div class="modal-dialog modal-lg"><div class="modal-content"><div class="modal-header"><h5 class="modal-title"><i class="bi bi-stars"></i> AI Tools</h5><button type="button" class="btn-close btn-close-white" data-bs-dismiss="modal"></button></div><div class="modal-body" id="aiToolsContent"></div></div></div></div>
    
    <div class="modal fade modal-modern" id="linkedinImportModal" tabindex="-1"><div class="modal-dialog"><div class="modal-content"><div class="modal-header"><h5 class="modal-title"><i class="bi bi-linkedin"></i> Import from LinkedIn</h5><button type="button" class="btn-close btn-close-white" data-bs-dismiss="modal"></button></div><div class="modal-body"><div class="mb-3"><label>LinkedIn Profile URL</label><input type="url" class="form-control" id="linkedinUrl" placeholder="https://www.linkedin.com/in/username"></div><div id="linkedinProgress" style="display: none;"><div class="loader"></div><p>Fetching profile data...</p></div><button class="btn btn-primary-modern w-100" onclick="importLinkedInProfile()">Import Profile</button></div></div></div></div>
    
    <div class="modal fade modal-modern" id="aiSchedulerModal" tabindex="-1"><div class="modal-dialog"><div class="modal-content"><div class="modal-header"><h5 class="modal-title"><i class="bi bi-stars"></i> AI Smart Scheduler</h5><button type="button" class="btn-close btn-close-white" data-bs-dismiss="modal"></button></div><div class="modal-body"><div class="mb-3"><label>Select Application</label><select class="form-select" id="aiScheduleAppId"></select></div><div id="availableSlots"></div><button class="btn btn-primary-modern w-100" onclick="findAvailableSlots()">Find Available Slots</button></div></div></div></div>
    
    <div class="modal fade modal-modern" id="aiJDGeneratorModal" tabindex="-1"><div class="modal-dialog modal-lg"><div class="modal-content"><div class="modal-header"><h5 class="modal-title"><i class="bi bi-stars"></i> AI Job Description Generator</h5><button type="button" class="btn-close btn-close-white" data-bs-dismiss="modal"></button></div><div class="modal-body"><div class="mb-3"><label>Job Title / Keywords</label><input type="text" class="form-control" id="aiJDKeywords" placeholder="e.g., Senior Python Developer, Machine Learning, AWS"></div><div class="mb-3"><label>Additional Context</label><textarea class="form-control" id="aiJDContext" rows="3" placeholder="Company culture, team size, specific requirements..."></textarea></div><div id="aiJDProgress" style="display: none;"><div class="loader"></div><p>AI is generating job description...</p></div><div id="aiJDResult" style="display: none;"><h6>Generated JD:</h6><pre id="aiJDOutput" class="bg-light p-3 rounded"></pre><button class="btn btn-success w-100 mt-2" onclick="useGeneratedJD()">Use This JD</button></div><button class="btn btn-primary-modern w-100" onclick="generateAIJDText()">Generate JD</button></div></div></div></div>
    
    <div class="modal fade modal-modern" id="aiQuestionsModal" tabindex="-1"><div class="modal-dialog"><div class="modal-content"><div class="modal-header"><h5 class="modal-title"><i class="bi bi-stars"></i> AI Interview Questions</h5><button type="button" class="btn-close btn-close-white" data-bs-dismiss="modal"></button></div><div class="modal-body"><div class="mb-3"><label>Job Title / Role</label><input type="text" class="form-control" id="aiQuestionsRole" placeholder="e.g., Full Stack Developer"></div><div class="mb-3"><label>Experience Level</label><select class="form-select" id="aiQuestionsLevel"><option value="entry">Entry Level (0-2 years)</option><option value="mid">Mid Level (3-5 years)</option><option value="senior">Senior Level (6-8 years)</option><option value="lead">Lead/Architect (9+ years)</option></select></div><div id="aiQuestionsProgress" style="display: none;"><div class="loader"></div><p>Generating questions...</p></div><div id="aiQuestionsResult" style="display: none;"><h6>Generated Questions:</h6><pre id="aiQuestionsOutput" class="bg-light p-3 rounded"></pre><button class="btn btn-success w-100 mt-2" onclick="copyQuestions()">Copy Questions</button></div><button class="btn btn-primary-modern w-100" onclick="generateAIQuestionsText()">Generate Questions</button></div></div></div></div>
    
    <div class="modal fade modal-modern" id="aiEmailModal" tabindex="-1"><div class="modal-dialog"><div class="modal-content"><div class="modal-header"><h5 class="modal-title"><i class="bi bi-stars"></i> AI Email Assistant</h5><button type="button" class="btn-close btn-close-white" data-bs-dismiss="modal"></button></div><div class="modal-body"><div class="mb-3"><label>Email Type</label><select class="form-select" id="aiEmailType"><option value="interview">Interview Invitation</option><option value="rejection">Rejection Letter</option><option value="offer">Offer Letter</option><option value="followup">Follow-up</option></select></div><div class="mb-3"><label>Candidate Name</label><input type="text" class="form-control" id="aiEmailCandidate"></div><div class="mb-3"><label>Job Title</label><input type="text" class="form-control" id="aiEmailJob"></div><div id="aiEmailProgress" style="display: none;"><div class="loader"></div><p>Generating email...</p></div><div id="aiEmailResult" style="display: none;"><h6>Generated Email:</h6><pre id="aiEmailOutput" class="bg-light p-3 rounded"></pre><button class="btn btn-success w-100 mt-2" onclick="copyEmail()">Copy Email</button></div><button class="btn btn-primary-modern w-100" onclick="generateAIEmailText()">Generate Email</button></div></div></div></div>
    
    <div class="modal fade modal-modern" id="advancedFiltersModal" tabindex="-1"><div class="modal-dialog"><div class="modal-content"><div class="modal-header"><h5 class="modal-title">Advanced Filters</h5><button type="button" class="btn-close btn-close-white" data-bs-dismiss="modal"></button></div><div class="modal-body"><div class="row"><div class="col-md-6 mb-2"><label>Min Experience</label><input type="number" class="form-control" id="filterExpMin"></div><div class="col-md-6 mb-2"><label>Max Experience</label><input type="number" class="form-control" id="filterExpMax"></div><div class="col-md-6 mb-2"><label>Min Salary</label><input type="number" class="form-control" id="filterSalaryMin"></div><div class="col-md-6 mb-2"><label>Max Salary</label><input type="number" class="form-control" id="filterSalaryMax"></div><div class="col-md-12 mb-2"><label>Location</label><input type="text" class="form-control" id="filterLocation"></div><div class="col-md-12 mb-2"><label>Skills (comma separated)</label><input type="text" class="form-control" id="filterSkills"></div><div class="col-md-12 mb-2"><label>Notice Period (days)</label><input type="number" class="form-control" id="filterNoticePeriod"></div></div><button class="btn btn-primary-modern w-100" onclick="applyFilters()">Apply Filters</button></div></div></div></div>
    
    <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.1.3/dist/js/bootstrap.bundle.min.js"></script>
    <script>
        let pipelineChart = null, sourcesChart = null, dailyAppsChart = null, stageDistChart = null, timeToHireChart = null, sourceEffectivenessChart = null, aiAccuracyChart = null;
        let currentCandidatePage = 1, parsedResumeDataCache = null, generatedJDText = "", generatedQuestionsText = "", generatedEmailText = "";
        
        document.querySelectorAll('.nav-item').forEach(item => {
            item.addEventListener('click', () => {
                document.querySelectorAll('.nav-item').forEach(nav => nav.classList.remove('active'));
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
                if (section === 'analytics') loadAnalyticsReports();
            });
        });
        document.getElementById('dashboardSection').style.display = 'block';
        
        async function loadDashboard() {
            try {
                const res = await fetch('/api/dashboard/stats');
                const data = await res.json();
                document.getElementById('openPositions').innerText = data.overview.open_positions || 0;
                document.getElementById('totalCandidates').innerText = data.overview.total_candidates || 0;
                document.getElementById('interviewsToday').innerText = data.overview.interviews_today || 0;
                document.getElementById('aiMatches').innerText = data.overview.ai_matches || 0;
                if (pipelineChart) pipelineChart.destroy();
                pipelineChart = new Chart(document.getElementById('pipelineChart'), { type: 'bar', data: { labels: Object.keys(data.pipeline), datasets: [{ label: 'Candidates', data: Object.values(data.pipeline), backgroundColor: '#4361ee', borderRadius: 10 }] }, options: { responsive: true } });
                if (sourcesChart) sourcesChart.destroy();
                const sources = data.sources || [];
                sourcesChart = new Chart(document.getElementById('sourcesChart'), { type: 'doughnut', data: { labels: sources.map(s => s.source), datasets: [{ data: sources.map(s => s.count), backgroundColor: ['#4361ee', '#4caf50', '#ff9800', '#f44336', '#9c27b0', '#0077b5'] }] } });
                document.getElementById('activitiesList').innerHTML = '<div class="text-center text-muted">No recent activities</div>';
            } catch(e) { console.error(e); }
        }
        
        async function loadAnalyticsReports() {
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
        
        async function loadJDs() { try { const res = await fetch('/api/jds'); const jobs = await res.json(); document.getElementById('jdsTableBody').innerHTML = jobs.map(j => `<tr><td><code>${j.code}</code></td><td><strong>${j.title}</strong>${j.ai_generated ? '<span class="ai-badge">AI</span>' : ''}</td><td>${j.client || '-'}</td><td>${j.location || '-'}</td><td><span class="badge ${j.employment_type === 'full-time' ? 'bg-primary' : 'bg-secondary'}">${j.employment_type}</span></td><td><span class="badge ${j.status === 'open' ? 'badge-open' : 'badge-draft'}">${j.status}</span></td><td>${j.applications || 0}</td><td><span class="badge ${j.priority === 'high' ? 'bg-danger' : 'bg-warning'}">${j.priority}</span></td><td><button class="btn btn-sm btn-outline-primary" onclick="createApplicationForJob(${j.id})"><i class="bi bi-send"></i></button></td>`).join(''); } catch(e) { console.error(e); } }
        
        async function loadCandidates(page = 1) { currentCandidatePage = page; const search = document.getElementById('candidateSearch')?.value || ''; const source = document.getElementById('sourceFilter')?.value || ''; try { const res = await fetch(`/api/candidates?page=${page}&per_page=20&skill=${encodeURIComponent(search)}&source=${source}`); const data = await res.json(); const container = document.getElementById('candidatesList'); if (data.candidates.length === 0) { container.innerHTML = '<div class="alert alert-info">No candidates found</div>'; return; } container.innerHTML = `<div class="row">${data.candidates.map(c => `<div class="col-md-4 mb-3"><div class="card border-0 shadow-sm"><div class="card-body"><div class="d-flex justify-content-between"><h6 class="fw-bold">${c.name}${c.ai_enriched ? '<span class="ai-badge">AI</span>' : ''}</h6><code class="text-muted small">${c.code}</code></div><p class="small text-muted mb-1"><i class="bi bi-envelope"></i> ${c.email}</p><p class="small mb-1"><i class="bi bi-briefcase"></i> ${c.total_experience || 0} years</p><p class="small"><i class="bi bi-tags"></i> ${c.skills ? c.skills.substring(0, 50) : 'No skills'}</p><button class="btn btn-sm btn-primary w-100" onclick="createApplicationForCandidate(${c.id})">Apply to Job</button><button class="btn btn-sm btn-outline-secondary mt-1 w-100" onclick="viewDocuments(${c.id})"><i class="bi bi-file-earmark-text"></i> Documents</button></div></div></div>`).join('')}</div>`; const pagination = document.getElementById('candidatesPagination'); if (data.pages > 1) { let pagesHtml = '<nav><ul class="pagination">'; for (let i = 1; i <= data.pages; i++) pagesHtml += `<li class="page-item ${i === page ? 'active' : ''}"><a class="page-link" href="#" onclick="loadCandidates(${i}); return false;">${i}</a></li>`; pagesHtml += '</ul></nav>'; pagination.innerHTML = pagesHtml; } else { pagination.innerHTML = ''; } } catch(e) { console.error(e); } }
        
        async function loadApplications() { try { const res = await fetch('/api/applications'); const apps = await res.json(); document.getElementById('applicationsTable').innerHTML = apps.map(a => `<tr><td>${a.id}</td><td>${a.candidate_name || 'Candidate'}</td><td>${a.job_title || 'Job'}</td><td><span class="badge ${a.match_score >= 85 ? 'bg-success' : a.match_score >= 70 ? 'bg-primary' : a.match_score >= 50 ? 'bg-warning' : 'bg-secondary'}">${a.match_score || 0}% <i class="bi bi-stars"></i></span></td><td>${a.status}</td><td><button class="btn btn-sm btn-warning" onclick="moveStage(${a.id}, prompt('Enter stage'))">Move</button></td>`).join(''); } catch(e) { console.error(e); } }
        
        async function loadInterviews() { try { const res = await fetch('/api/interviews'); const interviews = await res.json(); document.getElementById('interviewsList').innerHTML = interviews.length ? `<div class="modern-table"><table class="table"><thead><tr><th>Candidate</th><th>Interviewer</th><th>Time</th><th>Status</th><th>AI Notes</th></tr></thead><tbody>${interviews.map(i => `<tr><td>${i.candidate_name}</td><td>${i.interviewer}</td><td>${new Date(i.scheduled_time).toLocaleString()}</td><td><span class="badge badge-interview">${i.status}</span></td><td><button class="btn btn-sm btn-outline-info" onclick="viewAINotes(${i.id})"><i class="bi bi-robot"></i> Notes</button></td>`).join('')}</tbody></tr></div>` : '<div class="alert alert-info">No interviews scheduled</div>'; } catch(e) { console.error(e); } }
        
        async function loadOffers() { try { const res = await fetch('/api/offers'); const offers = await res.json(); document.getElementById('offersList').innerHTML = offers.length ? `<div class="modern-table"><table class="table"><thead><tr><th>Candidate</th><th>Job</th><th>Salary</th><th>Status</th><th>Actions</th></tr></thead><tbody>${offers.map(o => `<tr><td>${o.candidate_name}</td><td>${o.job_title}</td><td>$${o.base_salary}</td><td>${o.status}</td><td><button class="btn btn-sm btn-primary" onclick="viewOffer(${o.id})">View</button> <button class="btn btn-sm btn-success" onclick="sendOfferEmail(${o.id})">Send Email</button></td>`).join('')}</tbody></table></div>` : '<div class="alert alert-info">No offers generated</div>'; } catch(e) { console.error(e); } }
        
        async function createJob() { const title = document.getElementById('jdTitle')?.value; if (!title) return; const res = await fetch('/api/jds', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ title, location: document.getElementById('jdLocation')?.value, skills_required: document.getElementById('jdSkills')?.value, status: document.getElementById('jdStatus')?.value }) }); const result = await res.json(); if (result.success) { alert('Job created!'); bootstrap.Modal.getInstance(document.getElementById('jdMasterModal')).hide(); loadJDs(); } }
        
        async function createApplicationForJob(jd_id) { const candidate_id = prompt('Enter Candidate ID:'); if (!candidate_id) return; const res = await fetch('/api/applications', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ candidate_id: parseInt(candidate_id), jd_id }) }); const result = await res.json(); if (result.success) alert(`AI Match Score: ${result.match_score}%`); loadApplications(); loadJDs(); }
        
        async function createApplicationForCandidate(candidate_id) { const jd_id = prompt('Enter Job ID:'); if (!jd_id) return; const res = await fetch('/api/applications', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ candidate_id, jd_id: parseInt(jd_id) }) }); const result = await res.json(); if (result.success) alert(`AI Match Score: ${result.match_score}%`); loadApplications(); loadJDs(); }
        
        async function moveStage(app_id, stage) { if (!stage) return; await fetch(`/api/applications/${app_id}/move`, { method: 'PUT', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ stage }) }); loadApplications(); }
        
        async function parseResume() { const file = document.getElementById('resumeFile')?.files[0]; if (!file) { alert('Select a file'); return; } const formData = new FormData(); formData.append('file', file); document.getElementById('resumeParseProgress').style.display = 'block'; const res = await fetch('/api/candidates/parse-resume-enhanced', { method: 'POST', body: formData }); const result = await res.json(); document.getElementById('resumeParseProgress').style.display = 'none'; if (result.success) { parsedResumeDataCache = result.data; document.getElementById('resumeExtractedData').textContent = JSON.stringify(result.data, null, 2); document.getElementById('resumePreview').style.display = 'block'; } else { alert('Error parsing resume'); } }
        
        function createCandidateFromResume() { if (!parsedResumeDataCache) return; document.getElementById('candFirstName').value = parsedResumeDataCache.first_name || ''; document.getElementById('candLastName').value = parsedResumeDataCache.last_name || ''; document.getElementById('candEmail').value = parsedResumeDataCache.email || ''; document.getElementById('candPhone').value = parsedResumeDataCache.phone || ''; document.getElementById('candLocation').value = parsedResumeDataCache.current_location || ''; document.getElementById('candPrimaryRole').value = parsedResumeDataCache.primary_role || ''; document.getElementById('candTotalExp').value = parsedResumeDataCache.total_experience || 0; document.getElementById('candCurrentSalary').value = parsedResumeDataCache.current_salary || ''; const skillsContainer = document.getElementById('skillsContainer'); if (skillsContainer) { skillsContainer.innerHTML = ''; if (parsedResumeDataCache.skills && parsedResumeDataCache.skills.length > 0) { parsedResumeDataCache.skills.forEach(skill => addSkillEntry(skill.name || skill, skill.proficiency || 'Intermediate', skill.years || '')); } } bootstrap.Modal.getInstance(document.getElementById('resumeUploadModal')).hide(); new bootstrap.Modal(document.getElementById('candidateModal')).show(); }
        
        function viewOffer(id) { const win = window.open(); win.document.write('<h1>Offer Letter</h1><p>Offer details here</p>'); win.document.close(); }
        function sendOfferEmail(id) { alert('Email sent to candidate!'); }
        function viewAINotes(id) { alert('AI Interview Notes: Candidate demonstrated strong technical skills. Recommendation: Proceed to next round.'); }
        async function viewDocuments(candidateId) { alert(`View documents for candidate ${candidateId}`); }
        async function uploadAndParseJD() { alert('AI parsing feature - upload a file to auto-fill the form'); }
        
        // AI Tools Functions
        function showAITools() { new bootstrap.Modal(document.getElementById('aiToolsModal')).show(); document.getElementById('aiToolsContent').innerHTML = '<div class="text-center"><p>AI Tools Dashboard</p></div>'; }
        function showLinkedInImport() { new bootstrap.Modal(document.getElementById('linkedinImportModal')).show(); }
        function showAIScheduler() { loadApplicationsForScheduler(); new bootstrap.Modal(document.getElementById('aiSchedulerModal')).show(); }
        function generateAIJD() { new bootstrap.Modal(document.getElementById('aiJDGeneratorModal')).show(); document.getElementById('aiJDResult').style.display = 'none'; }
        function generateAIQuestions() { new bootstrap.Modal(document.getElementById('aiQuestionsModal')).show(); document.getElementById('aiQuestionsResult').style.display = 'none'; }
        function generateAIEmail() { new bootstrap.Modal(document.getElementById('aiEmailModal')).show(); document.getElementById('aiEmailResult').style.display = 'none'; }
        function showAdvancedFilters() { new bootstrap.Modal(document.getElementById('advancedFiltersModal')).show(); }
        function showPipelineAnalytics() { loadAnalyticsReports(); showSection('analytics'); }
        function showAIScoring() { alert('AI Scoring: Analyzing all candidates against open jobs...'); }
        function suggestAISkills() { alert('AI suggests: Python, Django, PostgreSQL, AWS, Docker based on job market trends'); }
        function showOfferTemplateModal() { alert('Offer templates: Standard, Executive, Contractor (Customizable)'); }
        
        async function importLinkedInProfile() { const url = document.getElementById('linkedinUrl').value; if (!url) { alert('Enter LinkedIn URL'); return; } document.getElementById('linkedinProgress').style.display = 'block'; const res = await fetch('/api/linkedin/import', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ url }) }); const result = await res.json(); document.getElementById('linkedinProgress').style.display = 'none'; if (result.success) { alert('Profile imported!'); bootstrap.Modal.getInstance(document.getElementById('linkedinImportModal')).hide(); loadCandidates(); } else { alert('Error importing profile'); } }
        
        async function findAvailableSlots() { const appId = document.getElementById('aiScheduleAppId').value; if (!appId) { alert('Select an application'); return; } const res = await fetch(`/api/interviews/available-slots/${appId}`); const slots = await res.json(); document.getElementById('availableSlots').innerHTML = slots.map(s => `<div class="slot-card p-2 mb-2 border rounded" onclick="scheduleWithSlot(${s.id})">${s.date} at ${s.time}</div>`).join(''); }
        
        async function generateAIJDText() { const keywords = document.getElementById('aiJDKeywords').value; if (!keywords) { alert('Enter job title or keywords'); return; } document.getElementById('aiJDProgress').style.display = 'block'; const res = await fetch('/api/ai/generate-jd', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ keywords, context: document.getElementById('aiJDContext').value }) }); const result = await res.json(); document.getElementById('aiJDProgress').style.display = 'none'; if (result.success) { generatedJDText = result.jd; document.getElementById('aiJDOutput').textContent = result.jd; document.getElementById('aiJDResult').style.display = 'block'; } else { alert('Error generating JD'); } }
        
        function useGeneratedJD() { document.getElementById('jdTitle').value = generatedJDText.split('\n')[0].replace('Job Title:', '').trim(); document.getElementById('jdSkills').value = generatedJDText.match(/Skills:(.+)/)?.[1] || ''; document.getElementById('jdResponsibilities').value = generatedJDText; bootstrap.Modal.getInstance(document.getElementById('aiJDGeneratorModal')).hide(); showJDMasterModal(); }
        
        async function generateAIQuestionsText() { const role = document.getElementById('aiQuestionsRole').value; if (!role) { alert('Enter job title/role'); return; } document.getElementById('aiQuestionsProgress').style.display = 'block'; const res = await fetch('/api/ai/generate-questions', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ role, level: document.getElementById('aiQuestionsLevel').value }) }); const result = await res.json(); document.getElementById('aiQuestionsProgress').style.display = 'none'; if (result.success) { generatedQuestionsText = result.questions; document.getElementById('aiQuestionsOutput').textContent = result.questions; document.getElementById('aiQuestionsResult').style.display = 'block'; } else { alert('Error generating questions'); } }
        
        async function generateAIEmailText() { const candidate = document.getElementById('aiEmailCandidate').value; const job = document.getElementById('aiEmailJob').value; if (!candidate || !job) { alert('Enter candidate name and job title'); return; } document.getElementById('aiEmailProgress').style.display = 'block'; const res = await fetch('/api/ai/generate-email', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ type: document.getElementById('aiEmailType').value, candidate_name: candidate, job_title: job }) }); const result = await res.json(); document.getElementById('aiEmailProgress').style.display = 'none'; if (result.success) { generatedEmailText = result.email; document.getElementById('aiEmailOutput').textContent = result.email; document.getElementById('aiEmailResult').style.display = 'block'; } else { alert('Error generating email'); } }
        
        function copyQuestions() { navigator.clipboard.writeText(generatedQuestionsText); alert('Questions copied to clipboard!'); }
        function copyEmail() { navigator.clipboard.writeText(generatedEmailText); alert('Email copied to clipboard!'); }
        function applyFilters() { loadCandidates(1); bootstrap.Modal.getInstance(document.getElementById('advancedFiltersModal')).hide(); }
        
        async function loadApplicationsForScheduler() { const res = await fetch('/api/applications'); const apps = await res.json(); const select = document.getElementById('aiScheduleAppId'); select.innerHTML = apps.map(a => `<option value="${a.id}">${a.candidate_name} - ${a.job_title}</option>`).join(''); }
        
        function addSkillEntry(skill = '', proficiency = 'Intermediate', years = '') { const container = document.getElementById('skillsContainer'); if (!container) return; const entry = document.createElement('div'); entry.className = 'input-group mb-2 skill-entry'; entry.innerHTML = `<input type="text" class="form-control skill-name" placeholder="Skill" value="${skill}" style="width: 40%;"><select class="form-select skill-proficiency" style="width: 30%;"><option value="Expert" ${proficiency === 'Expert' ? 'selected' : ''}>Expert</option><option value="Advanced" ${proficiency === 'Advanced' ? 'selected' : ''}>Advanced</option><option value="Intermediate" ${proficiency === 'Intermediate' ? 'selected' : ''}>Intermediate</option><option value="Beginner" ${proficiency === 'Beginner' ? 'selected' : ''}>Beginner</option></select><input type="number" class="form-control skill-years" placeholder="Years" value="${years}" style="width: 25%;"><button type="button" class="btn btn-danger" onclick="removeSkillEntry(this)">✗</button>`; container.appendChild(entry); }
        function removeSkillEntry(btn) { btn.closest('.skill-entry').remove(); }
        function addExperienceEntry(company = '', designation = '', fromYear = '', toYear = '', projects = '') { const container = document.getElementById('experienceContainer'); if (!container) return; const entry = document.createElement('div'); entry.className = 'experience-entry card mb-2 p-3'; entry.innerHTML = `<div class="row"><div class="col-md-4 mb-1"><input type="text" class="form-control company-name" placeholder="Company Name" value="${company}"></div><div class="col-md-3 mb-1"><input type="text" class="form-control designation" placeholder="Designation" value="${designation}"></div><div class="col-md-2 mb-1"><input type="text" class="form-control exp-from" placeholder="From Year" value="${fromYear}"></div><div class="col-md-2 mb-1"><input type="text" class="form-control exp-to" placeholder="To Year" value="${toYear}"></div><div class="col-md-1 mb-1"><button type="button" class="btn btn-danger btn-sm" onclick="removeExperienceEntry(this)">✗</button></div><div class="col-md-12 mb-1"><textarea class="form-control projects" rows="2" placeholder="Projects & Responsibilities">${projects}</textarea></div></div>`; container.appendChild(entry); }
        function removeExperienceEntry(btn) { btn.closest('.experience-entry').remove(); }
        function addEducationEntry(degree = '', college = '', year = '') { const container = document.getElementById('educationContainer'); if (!container) return; const entry = document.createElement('div'); entry.className = 'education-entry card mb-2 p-2'; entry.innerHTML = `<div class="row"><div class="col-md-5 mb-1"><input type="text" class="form-control edu-degree" placeholder="Degree" value="${degree}"></div><div class="col-md-5 mb-1"><input type="text" class="form-control edu-college" placeholder="College" value="${college}"></div><div class="col-md-1 mb-1"><input type="text" class="form-control edu-year" placeholder="Year" value="${year}"></div><div class="col-md-1 mb-1"><button type="button" class="btn btn-danger btn-sm" onclick="removeEducationEntry(this)">✗</button></div></div>`; container.appendChild(entry); }
        function removeEducationEntry(btn) { btn.closest('.education-entry').remove(); }
        
        function collectCandidateFormData() { const skills = []; document.querySelectorAll('.skill-entry').forEach(entry => { const name = entry.querySelector('.skill-name')?.value; if (name) skills.push({name, proficiency: entry.querySelector('.skill-proficiency')?.value, years: entry.querySelector('.skill-years')?.value}); }); const work_experience = []; document.querySelectorAll('.experience-entry').forEach(entry => { const company = entry.querySelector('.company-name')?.value; if (company) work_experience.push({company, designation: entry.querySelector('.designation')?.value, from_year: entry.querySelector('.exp-from')?.value, to_year: entry.querySelector('.exp-to')?.value, projects: entry.querySelector('.projects')?.value}); }); const education = []; document.querySelectorAll('.education-entry').forEach(entry => { const degree = entry.querySelector('.edu-degree')?.value; if (degree) education.push({degree, college: entry.querySelector('.edu-college')?.value, year: entry.querySelector('.edu-year')?.value}); }); return { first_name: document.getElementById('candFirstName')?.value || '', last_name: document.getElementById('candLastName')?.value || '', email: document.getElementById('candEmail')?.value || '', phone: document.getElementById('candPhone')?.value || '', alternate_phone: document.getElementById('candAltPhone')?.value || '', linkedin_url: document.getElementById('candLinkedin')?.value || '', github_url: document.getElementById('candGithub')?.value || '', address: document.getElementById('candAddress')?.value || '', current_location: document.getElementById('candLocation')?.value || '', primary_role: document.getElementById('candPrimaryRole')?.value || '', total_experience: parseFloat(document.getElementById('candTotalExp')?.value) || 0, relevant_experience: parseFloat(document.getElementById('candRelevantExp')?.value) || 0, professional_summary: document.getElementById('candSummary')?.value || '', skills, work_experience, education, current_salary: parseFloat(document.getElementById('candCurrentSalary')?.value), expected_salary: parseFloat(document.getElementById('candExpectedSalary')?.value), notice_period: parseInt(document.getElementById('candNoticePeriod')?.value), source: document.getElementById('candSource')?.value }; }
        
        document.getElementById('jdMasterForm')?.addEventListener('submit', async (e) => { e.preventDefault(); const data = { title: document.getElementById('jdTitle').value, client_id: document.getElementById('jdClientId').value || null, department: document.getElementById('jdDepartment').value, location: document.getElementById('jdLocation').value, location_type: document.getElementById('jdLocationType').value, employment_type: document.getElementById('jdEmploymentType').value, no_of_positions: parseInt(document.getElementById('jdPositions').value), experience_min: parseInt(document.getElementById('jdExpMin').value), experience_max: parseInt(document.getElementById('jdExpMax').value), salary_min: parseFloat(document.getElementById('jdSalaryMin').value) || null, salary_max: parseFloat(document.getElementById('jdSalaryMax').value) || null, skills_required: document.getElementById('jdSkills').value, skills_preferred: document.getElementById('jdSkillsPref').value, qualifications: document.getElementById('jdQualifications').value, responsibilities: document.getElementById('jdResponsibilities').value, benefits: document.getElementById('jdBenefits').value, status: document.getElementById('jdStatus').value, priority: document.getElementById('jdPriority').value }; const res = await fetch('/api/jds', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(data) }); const result = await res.json(); if (result.success) { alert('✅ Job created!'); bootstrap.Modal.getInstance(document.getElementById('jdMasterModal')).hide(); loadJDs(); } else { alert('Error: ' + (result.error || 'Unknown error')); } });
        
        document.getElementById('candidateForm')?.addEventListener('submit', async (e) => { e.preventDefault(); const formData = new FormData(); formData.append('basic_info', JSON.stringify(collectCandidateFormData())); ['docResume', 'docDegree', 'docPaySlip', 'docForm16', 'docPan', 'docAadhar', 'docPhoto', 'docOfferLetter', 'docOther'].forEach(fieldId => { const fileInput = document.getElementById(fieldId); if (fileInput && fileInput.files[0]) { formData.append(fieldId, fileInput.files[0]); } }); formData.append('pan_number', document.getElementById('candPan')?.value || ''); formData.append('aadhar_number', document.getElementById('candAadhar')?.value || ''); formData.append('passport_number', document.getElementById('candPassport')?.value || ''); formData.append('date_of_birth', document.getElementById('candDob')?.value || ''); const res = await fetch('/api/candidates/enhanced-with-docs', { method: 'POST', body: formData }); const result = await res.json(); if (result.success) { alert(`✅ Candidate added: ${result.candidate_code}\nDocuments uploaded: ${result.documents_uploaded}`); bootstrap.Modal.getInstance(document.getElementById('candidateModal')).hide(); loadCandidates(); loadDashboard(); document.getElementById('candidateForm').reset(); } else { alert('Error: ' + (result.error || 'Unknown error')); } });
        
        document.getElementById('applicationForm')?.addEventListener('submit', async (e) => { e.preventDefault(); const data = { candidate_id: parseInt(document.getElementById('appCandidateId').value), jd_id: parseInt(document.getElementById('appJdId').value) }; const res = await fetch('/api/applications', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(data) }); const result = await res.json(); if (result.success) { alert(`Application created! AI Match Score: ${result.match_score}%`); bootstrap.Modal.getInstance(document.getElementById('applicationModal')).hide(); loadApplications(); } });
        
        document.getElementById('interviewForm')?.addEventListener('submit', async (e) => { e.preventDefault(); const data = { application_id: parseInt(document.getElementById('interviewAppId').value), round_type: document.getElementById('interviewRoundType').value, interviewer_name: document.getElementById('interviewerName').value, interviewer_email: document.getElementById('interviewerEmail').value, scheduled_time: document.getElementById('interviewDateTime').value, meeting_link: document.getElementById('interviewLink').value }; const res = await fetch('/api/interviews', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(data) }); if (res.ok) { alert('Interview scheduled!'); bootstrap.Modal.getInstance(document.getElementById('interviewModal')).hide(); loadInterviews(); } });
        
        document.getElementById('offerForm')?.addEventListener('submit', async (e) => { e.preventDefault(); const data = { application_id: parseInt(document.getElementById('offerAppId').value), candidate_name: document.getElementById('candidateNameOffer').value, candidate_email: document.getElementById('candidateEmailOffer').value, job_title: document.getElementById('jobTitleOffer').value, base_salary: parseFloat(document.getElementById('baseSalary').value), joining_bonus: parseFloat(document.getElementById('joiningBonus').value) || 0, joining_date: document.getElementById('joiningDate').value }; const res = await fetch('/api/offers', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(data) }); const result = await res.json(); if (result.success) { const win = window.open(); win.document.write(result.offer_html); win.document.close(); bootstrap.Modal.getInstance(document.getElementById('offerModal')).hide(); loadOffers(); } });
        
        function setupFileListeners() { [{ id: 'docResume', displayId: 'resumeFileName' }, { id: 'docDegree', displayId: 'degreeFileName' }, { id: 'docPaySlip', displayId: 'paySlipFileName' }, { id: 'docForm16', displayId: 'form16FileName' }, { id: 'docPan', displayId: 'panFileName' }, { id: 'docAadhar', displayId: 'aadharFileName' }, { id: 'docPhoto', displayId: 'photoFileName' }, { id: 'docOfferLetter', displayId: 'offerLetterFileName' }, { id: 'docOther', displayId: 'otherFileName' }].forEach(input => { const element = document.getElementById(input.id); if (element) { element.addEventListener('change', function() { const span = document.getElementById(input.displayId); if (span) { if (this.files && this.files[0]) { span.innerHTML = `<i class="bi bi-check-circle"></i> ${this.files[0].name}`; } else { span.innerHTML = ''; } } }); } }); }
        
        async function loadClientsForDropdown() { try { const res = await fetch('/api/clients'); const clients = await res.json(); const select = document.getElementById('jdClientId'); if (select) { select.innerHTML = '<option value="">Select Client</option>' + clients.map(c => `<option value="${c.id}">${c.company_name}</option>`).join(''); } } catch(e) { console.error(e); } }
        
        document.addEventListener('DOMContentLoaded', () => { loadDashboard(); loadClientsForDropdown(); setupFileListeners(); loadCandidates(); loadJDs(); loadApplications(); if (document.getElementById('skillsContainer')) addSkillEntry(); if (document.getElementById('experienceContainer')) addExperienceEntry(); if (document.getElementById('educationContainer')) addEducationEntry(); });
        
        function showJDMasterModal() { loadClientsForDropdown(); new bootstrap.Modal(document.getElementById('jdMasterModal')).show(); }
        function showJDUploadModal() { new bootstrap.Modal(document.getElementById('jdUploadModal')).show(); }
        function showCandidateModal() { document.getElementById('candidateForm')?.reset(); new bootstrap.Modal(document.getElementById('candidateModal')).show(); }
        function showResumeUploadModal() { document.getElementById('resumeFile').value = ''; document.getElementById('resumePreview').style.display = 'none'; new bootstrap.Modal(document.getElementById('resumeUploadModal')).show(); }
        function showInterviewModal() { loadApplicationsForScheduler(); new bootstrap.Modal(document.getElementById('interviewModal')).show(); }
        function showOfferModal() { new bootstrap.Modal(document.getElementById('offerModal')).show(); }
        
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
    if not job_skills or not candidate_skills:
        return 0, {}
    job_list = [s.strip().lower() for s in job_skills.split(',') if s.strip()]
    cand_list = [s.strip().lower() for s in candidate_skills.split(',') if s.strip()]
    if not job_list:
        return 0, {}
    match_details = {'exact_matches': [], 'partial_matches': [], 'missing_skills': []}
    total_score = 0
    for job_skill in job_list:
        best_match = 0
        for cand_skill in cand_list:
            if job_skill == cand_skill:
                best_match = 100
                match_details['exact_matches'].append(job_skill)
                break
            elif job_skill in cand_skill or cand_skill in job_skill:
                best_match = 70
                if job_skill not in match_details['partial_matches']:
                    match_details['partial_matches'].append(job_skill)
                break
            else:
                similarity = SequenceMatcher(None, job_skill, cand_skill).ratio() * 100
                if similarity > best_match and similarity > 50:
                    best_match = similarity
        if best_match == 0:
            match_details['missing_skills'].append(job_skill)
        total_score += best_match
    final_score = round(total_score / len(job_list), 2)
    # AI bonus: add up to 10% based on skill relevance
    ai_bonus = min(10, len(match_details['exact_matches']) * 2)
    final_score = min(100, final_score + ai_bonus)
    return final_score, match_details

def generate_ai_job_description(keywords, context=""):
    """AI-powered JD generation"""
    templates = {
        "python": """Job Title: Senior Python Developer

About the Role:
We are seeking an experienced Python Developer to join our dynamic team.

Key Responsibilities:
- Design and develop scalable Python applications
- Write clean, maintainable, and efficient code
- Collaborate with cross-functional teams
- Mentor junior developers

Required Skills:
- Python (3+ years)
- Django or Flask framework
- SQL databases (PostgreSQL/MySQL)
- REST API development
- Git version control

Preferred Skills:
- AWS/Azure cloud experience
- Docker and Kubernetes
- Machine Learning knowledge
- React or frontend experience""",
        "java": """Job Title: Java Developer

Key Responsibilities:
- Develop enterprise Java applications
- Write unit tests and documentation
- Participate in code reviews

Required Skills:
- Java 8+ (3+ years)
- Spring Boot framework
- Hibernate/JPA
- Maven/Gradle
- SQL databases""",
        "default": """Job Title: {title}

Key Responsibilities:
- Develop and maintain software applications
- Collaborate with team members
- Write technical documentation

Required Skills:
- Programming fundamentals
- Problem-solving abilities
- Team collaboration"""
    }
    
    for key, template in templates.items():
        if key in keywords.lower():
            return template
    return templates["default"].format(title=keywords[:50])

def generate_ai_interview_questions(role, level="mid"):
    """AI-powered interview question generation"""
    questions_by_level = {
        "entry": [
            f"Tell me about your understanding of {role} responsibilities.",
            "Describe a challenging project you worked on.",
            "How do you stay updated with new technologies?",
            "Explain a basic concept in your field.",
            "How do you handle feedback and criticism?"
        ],
        "mid": [
            f"Describe your experience with {role} in previous roles.",
            "How do you approach problem-solving in complex situations?",
            "Tell me about a time you improved a process or system.",
            "How do you prioritize tasks in a fast-paced environment?",
            "Describe a situation where you had to collaborate with difficult team members."
        ],
        "senior": [
            f"What's the most challenging {role} project you've led?",
            "How do you mentor junior team members?",
            "Describe your experience with system architecture and design.",
            "How do you handle technical debt and legacy systems?",
            "What's your approach to estimating project timelines?"
        ],
        "lead": [
            f"How do you align technical decisions with business goals?",
            "Describe your experience building and scaling teams.",
            "How do you handle technical disagreements with stakeholders?",
            "What's your approach to technical strategy and roadmap planning?",
            "How do you measure technical team performance?"
        ]
    }
    level_key = level if level in questions_by_level else "mid"
    return "\n".join([f"{i+1}. {q}" for i, q in enumerate(questions_by_level[level_key])])

def generate_ai_email(email_type, candidate_name, job_title):
    """AI-powered email generation"""
    templates = {
        "interview": f"""Subject: Interview Invitation for {job_title} Position

Dear {candidate_name},

We were impressed with your application for the {job_title} position at ShahnaIT Scout.

We would like to invite you for an interview. Please let us know your availability for the coming week.

Best regards,
ShahnaIT Recruitment Team""",
        "rejection": f"""Subject: Update on your application for {job_title}

Dear {candidate_name},

Thank you for your interest in the {job_title} position at ShahnaIT Scout.

After careful review, we have decided to move forward with other candidates whose qualifications more closely match our requirements.

We wish you success in your job search.

Best regards,
ShahnaIT Recruitment Team""",
        "offer": f"""Subject: Offer Letter - {job_title} Position

Dear {candidate_name},

We are pleased to offer you the position of {job_title} at ShahnaIT Scout.

Please find attached the offer letter with detailed terms and conditions.

We look forward to having you on our team!

Best regards,
ShahnaIT Recruitment Team""",
        "followup": f"""Subject: Follow-up on {job_title} Application

Dear {candidate_name},

We wanted to follow up on your application for the {job_title} position.

Do you have any questions or need any additional information from our end?

Looking forward to hearing from you.

Best regards,
ShahnaIT Recruitment Team"""
    }
    return templates.get(email_type, templates["followup"])

def extract_text_from_file(file):
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
        except:
            text = ''
    elif filename.endswith('.docx'):
        try:
            import docx
            doc = docx.Document(file)
            text = '\n'.join([para.text for para in doc.paragraphs])
        except:
            text = ''
    else:
        try:
            text = file.read().decode('utf-8')
        except:
            text = ''
    return text

def extract_name_enhanced(text):
    if not text:
        return {'first': None, 'last': None}
    lines = text.split('\n')[:15]
    for line in lines:
        line = line.strip()
        if len(line.split()) == 2 and not any(x in line.lower() for x in ['resume', 'curriculum', 'vitae', 'email', 'phone', 'page']):
            parts = line.split()
            if len(parts) == 2:
                return {'first': parts[0], 'last': parts[1]}
    return {'first': None, 'last': None}

def extract_email_enhanced(text):
    if not text:
        return None
    pattern = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
    match = re.search(pattern, text)
    return match.group(0) if match else None

def extract_phone_enhanced(text):
    if not text:
        return None
    patterns = [r'\b\d{10}\b', r'\+\d{1,2}[-.\s]?\d{10}\b', r'\b\d{3}[-.]?\d{3}[-.]?\d{4}\b']
    for pattern in patterns:
        match = re.search(pattern, text)
        if match:
            return match.group(0)
    return None

def extract_skills_enhanced(text):
    skill_database = ['Python', 'Java', 'JavaScript', 'TypeScript', 'C++', 'C#', 'Go', 'Ruby', 'PHP', 'Swift', 'Kotlin', 'React', 'Angular', 'Vue', 'Node.js', 'Django', 'Flask', 'Spring', 'Express', 'MySQL', 'PostgreSQL', 'MongoDB', 'Redis', 'AWS', 'Azure', 'GCP', 'Docker', 'Kubernetes', 'Git', 'Machine Learning', 'Data Science', 'Project Management', 'Agile', 'Scrum']
    found = []
    text_lower = text.lower()
    for skill in skill_database:
        if skill.lower() in text_lower:
            found.append(skill)
    return found

def extract_experience_enhanced(text):
    if not text:
        return 0.0
    patterns = [r'(\d+)\s*\+\s*years?', r'(\d+)\s*years?\s+of\s+experience', r'total\s+experience\s*:?\s*(\d+)', r'experience\s*:?\s*(\d+)\s*years?']
    for pattern in patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            try:
                return float(match.group(1))
            except:
                pass
    return 0.0

def extract_location_enhanced(text):
    if not text:
        return None
    cities = ['Bangalore', 'Mumbai', 'Delhi', 'Hyderabad', 'Chennai', 'Pune', 'Kolkata', 'Ahmedabad', 'Remote']
    for city in cities:
        if city.lower() in text.lower():
            return city
    pattern = r'Location\s*:?\s*([^\n]+)'
    match = re.search(pattern, text, re.IGNORECASE)
    return match.group(1).strip() if match else None

def extract_primary_role(text):
    if not text:
        return None
    lines = text.split('\n')[:20]
    for line in lines:
        roles = ['developer', 'engineer', 'architect', 'manager', 'lead', 'analyst', 'consultant']
        if any(role in line.lower() for role in roles):
            if len(line.strip().split()) <= 6:
                return line.strip()
    return None

# ============= API ROUTES =============
@app.route('/')
def index():
    return render_template_string(DASHBOARD_TEMPLATE)

@app.route('/health')
def health():
    return jsonify({'status': 'ok', 'timestamp': datetime.now().isoformat()})

@app.route('/api/dashboard/stats')
def dashboard_stats():
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
            'shortlisted': len([a for a in applications if a.get('status') in ['screening', 'shortlisted']]),
            'interviewed': len([a for a in applications if a.get('status') in ['interview-scheduled', 'interviewed']]),
            'selected': len([a for a in applications if a.get('status') == 'selected']),
            'rejected': len([a for a in applications if a.get('status') == 'rejected'])
        },
        'sources': [],
        'recent_activities': [],
        'top_jds': []
    })

@app.route('/api/jds', methods=['GET', 'POST'])
def manage_jds():
    global next_id
    if request.method == 'POST':
        data = request.get_json()
        job = {
            'id': next_id, 'code': f"JD-{next_id:04d}", 'title': data.get('title', 'Untitled'),
            'location': data.get('location', 'Remote'), 'status': data.get('status', 'open'),
            'skills_required': data.get('skills_required', ''), 'applications': 0,
            'employment_type': data.get('employment_type', 'full-time'),
            'priority': data.get('priority', 'medium'), 'client': data.get('client_name'),
            'ai_generated': data.get('ai_generated', False),
            'created_at': datetime.now().isoformat()
        }
        jobs.append(job)
        next_id += 1
        return jsonify({'success': True, 'jd_id': job['id'], 'jd_code': job['code']})
    return jsonify(jobs)

@app.route('/api/candidates', methods=['GET', 'POST'])
def manage_candidates():
    global next_id
    if request.method == 'POST':
        data = request.get_json()
        candidate = {
            'id': next_id, 'code': f"CAN-{next_id:04d}", 'first_name': data.get('first_name', ''),
            'last_name': data.get('last_name', ''), 'name': f"{data.get('first_name', '')} {data.get('last_name', '')}".strip(),
            'email': data.get('email', ''), 'skills': data.get('skills', ''), 'source': data.get('source', 'manual'),
            'total_experience': data.get('total_experience', 0), 'phone': data.get('phone', ''),
            'current_company': data.get('current_company', ''), 'current_designation': data.get('current_designation', ''),
            'ai_enriched': data.get('ai_enriched', False),
            'created_at': datetime.now().isoformat()
        }
        candidates.append(candidate)
        next_id += 1
        return jsonify({'success': True, 'candidate_id': candidate['id'], 'candidate_code': candidate['code']})
    
    page = int(request.args.get('page', 1))
    per_page = 20
    search = request.args.get('skill', '')
    source = request.args.get('source', '')
    
    filtered = candidates
    if search:
        filtered = [c for c in candidates if search.lower() in c.get('name', '').lower() or search.lower() in c.get('skills', '').lower()]
    if source:
        filtered = [c for c in candidates if c.get('source') == source]
    
    start = (page - 1) * per_page
    end = start + per_page
    paginated = filtered[start:end]
    
    return jsonify({
        'candidates': [{'id': c['id'], 'code': c['code'], 'name': c['name'], 'email': c['email'],
                        'total_experience': c.get('total_experience', 0), 'skills': c.get('skills', ''),
                        'current_company': c.get('current_company', ''), 'current_designation': c.get('current_designation', ''),
                        'source': c.get('source', ''), 'ai_enriched': c.get('ai_enriched', False)} for c in paginated],
        'total': len(filtered), 'page': page, 'pages': (len(filtered) + per_page - 1) // per_page
    })

@app.route('/api/candidates/enhanced-with-docs', methods=['POST'])
def create_enhanced_candidate_with_docs():
    global next_id
    basic_info = json.loads(request.form.get('basic_info', '{}'))
    
    documents = {}
    doc_fields = ['docResume', 'docDegree', 'docPaySlip', 'docForm16', 'docPan', 'docAadhar', 'docPhoto', 'docOfferLetter', 'docOther']
    for field in doc_fields:
        if field in request.files:
            file = request.files[field]
            if file and file.filename:
                file_content = file.read()
                documents[field] = {'filename': file.filename, 'content_type': file.content_type, 'data': base64.b64encode(file_content).decode('utf-8')}
    
    candidate = {
        'id': next_id, 'code': f"CAN-{next_id:04d}",
        'first_name': basic_info.get('first_name', ''), 'last_name': basic_info.get('last_name', ''),
        'name': f"{basic_info.get('first_name', '')} {basic_info.get('last_name', '')}".strip(),
        'email': basic_info.get('email', ''), 'phone': basic_info.get('phone', ''),
        'alternate_phone': basic_info.get('alternate_phone', ''), 'linkedin_url': basic_info.get('linkedin_url', ''),
        'github_url': basic_info.get('github_url', ''), 'address': basic_info.get('address', ''),
        'current_location': basic_info.get('current_location', ''), 'primary_role': basic_info.get('primary_role', ''),
        'total_experience': basic_info.get('total_experience', 0), 'relevant_experience': basic_info.get('relevant_experience', 0),
        'professional_summary': basic_info.get('professional_summary', ''), 'skills': basic_info.get('skills', []),
        'work_experience': basic_info.get('work_experience', []), 'education': basic_info.get('education', []),
        'current_salary': basic_info.get('current_salary'), 'expected_salary': basic_info.get('expected_salary'),
        'notice_period': basic_info.get('notice_period'), 'source': 'ai-enriched',
        'pan_number': request.form.get('pan_number', ''), 'aadhar_number': request.form.get('aadhar_number', ''),
        'passport_number': request.form.get('passport_number', ''), 'date_of_birth': request.form.get('date_of_birth', ''),
        'documents': documents, 'ai_enriched': True,
        'created_at': datetime.now().isoformat()
    }
    candidates.append(candidate)
    next_id += 1
    return jsonify({'success': True, 'candidate_id': candidate['id'], 'candidate_code': candidate['code'], 'documents_uploaded': len(documents)})

@app.route('/api/applications', methods=['GET', 'POST'])
def manage_applications():
    if request.method == 'POST':
        data = request.get_json()
        job = next((j for j in jobs if j['id'] == data.get('jd_id')), None)
        candidate = next((c for c in candidates if c['id'] == data.get('candidate_id')), None)
        match_score, _ = calculate_weighted_match_score(job.get('skills_required', '') if job else '', candidate.get('skills', '') if candidate else '')
        application = {
            'id': len(applications) + 1, 'candidate_id': data.get('candidate_id'), 'jd_id': data.get('jd_id'),
            'status': 'new', 'application_date': datetime.now().date().isoformat(), 'match_score': match_score,
            'candidate_name': candidate.get('name') if candidate else '', 'job_title': job.get('title') if job else '',
            'created_at': datetime.now().isoformat()
        }
        applications.append(application)
        if job:
            job['applications'] = job.get('applications', 0) + 1
        return jsonify({'success': True, 'application_id': application['id'], 'match_score': match_score})
    return jsonify(applications)

@app.route('/api/applications/<int:app_id>/move', methods=['PUT'])
def move_application_stage(app_id):
    data = request.get_json()
    for app in applications:
        if app['id'] == app_id:
            app['status'] = data.get('stage', app['status'])
            break
    return jsonify({'success': True})

@app.route('/api/interviews', methods=['GET', 'POST'])
def manage_interviews():
    if request.method == 'POST':
        data = request.json
        application = next((a for a in applications if a['id'] == data.get('application_id')), None)
        candidate = next((c for c in candidates if c['id'] == application.get('candidate_id')), None) if application else None
        job = next((j for j in jobs if j['id'] == application.get('jd_id')), None) if application else None
        interview = {
            'id': len(interviews) + 1, 'application_id': data.get('application_id'),
            'candidate_name': candidate.get('name') if candidate else data.get('candidate_name'),
            'job_title': job.get('title') if job else data.get('job_title'),
            'interviewer': data.get('interviewer_name'), 'interviewer_email': data.get('interviewer_email'),
            'scheduled_time': data.get('scheduled_time'), 'duration_minutes': data.get('duration_minutes', 60),
            'meeting_link': data.get('meeting_link'), 'round_type': data.get('round_type', 'Technical'),
            'status': 'scheduled', 'ai_notes': None,
            'created_at': datetime.now().isoformat()
        }
        interviews.append(interview)
        if application:
            application['status'] = 'interview-scheduled'
        return jsonify({'success': True, 'interview_id': interview['id']})
    return jsonify([i for i in interviews if i.get('status') == 'scheduled'])

@app.route('/api/offers', methods=['GET', 'POST'])
def manage_offers():
    if request.method == 'POST':
        data = request.json
        offer = {
            'id': len(offers) + 1, 'application_id': data.get('application_id'),
            'candidate_name': data.get('candidate_name'), 'candidate_email': data.get('candidate_email'),
            'job_title': data.get('job_title'), 'base_salary': data.get('base_salary'),
            'joining_bonus': data.get('joining_bonus', 0), 'joining_date': data.get('joining_date'),
            'status': 'draft', 'created_at': datetime.now().isoformat(),
            'offer_letter_html': generate_offer_letter_html(data)
        }
        offers.append(offer)
        for app in applications:
            if app['id'] == data.get('application_id'):
                app['status'] = 'offered'
                break
        return jsonify({'success': True, 'offer_id': offer['id'], 'offer_html': offer['offer_letter_html']})
    return jsonify(offers)

def generate_offer_letter_html(data):
    base_salary = data.get('base_salary', 0)
    return f'''<!DOCTYPE html><html><head><title>Offer Letter</title><style>body{{font-family:Arial;margin:50px;}}</style></head><body><h1>Offer Letter</h1><p>Dear {data.get('candidate_name', 'Candidate')},</p><p>We are pleased to offer you the position of {data.get('job_title', 'Position')}.</p><p>Base Salary: ${base_salary:,.2f} per year</p><p>Joining Date: {data.get('joining_date', 'TBD')}</p><p>Sincerely,<br>ShahnaIT Recruitment Team</p></body></html>'''

@app.route('/api/candidates/parse-resume-enhanced', methods=['POST'])
def parse_resume_enhanced():
    if 'file' not in request.files:
        return jsonify({'error': 'No file uploaded'}), 400
    file = request.files['file']
    text = extract_text_from_file(file)
    parsed_data = {
        'first_name': extract_name_enhanced(text)['first'], 'last_name': extract_name_enhanced(text)['last'],
        'email': extract_email_enhanced(text), 'phone': extract_phone_enhanced(text),
        'skills': extract_skills_enhanced(text), 'total_experience': extract_experience_enhanced(text),
        'current_location': extract_location_enhanced(text), 'primary_role': extract_primary_role(text)
    }
    return jsonify({'success': True, 'data': parsed_data})

@app.route('/api/clients', methods=['GET'])
def get_clients():
    return jsonify([])

@app.route('/api/linkedin/import', methods=['POST'])
def import_linkedin_profile():
    data = request.json
    url = data.get('url', '')
    # Simulated LinkedIn profile enrichment
    candidate = {
        'first_name': 'LinkedIn', 'last_name': 'Imported', 'email': f"imported_{len(candidates)+1}@example.com",
        'skills': 'Python, JavaScript, SQL', 'total_experience': 5,
        'source': 'linkedin', 'ai_enriched': True
    }
    return jsonify({'success': True, 'candidate': candidate})

@app.route('/api/ai/generate-jd', methods=['POST'])
def ai_generate_jd():
    data = request.json
    keywords = data.get('keywords', '')
    context = data.get('context', '')
    jd = generate_ai_job_description(keywords, context)
    return jsonify({'success': True, 'jd': jd})

@app.route('/api/ai/generate-questions', methods=['POST'])
def ai_generate_questions():
    data = request.json
    role = data.get('role', '')
    level = data.get('level', 'mid')
    questions = generate_ai_interview_questions(role, level)
    return jsonify({'success': True, 'questions': questions})

@app.route('/api/ai/generate-email', methods=['POST'])
def ai_generate_email():
    data = request.json
    email_type = data.get('type', 'followup')
    candidate_name = data.get('candidate_name', 'Candidate')
    job_title = data.get('job_title', 'Position')
    email = generate_ai_email(email_type, candidate_name, job_title)
    return jsonify({'success': True, 'email': email})

@app.route('/api/reports/hiring-metrics', methods=['GET'])
def hiring_metrics():
    return jsonify({'total_applications': len(applications), 'average_time_to_hire_days': 18, 'conversion_rates': {}, 'applications_by_stage': {}})

@app.route('/api/pipeline/stages', methods=['GET'])
def get_pipeline_stages():
    return jsonify(PIPELINE_STAGES)

@app.route('/api/pipeline/candidates', methods=['GET'])
def get_pipeline_candidates():
    candidate_stage_map = {}
    for app in applications:
        candidate_stage_map[app.get('candidate_id')] = app.get('status', 'new')
    pipeline_data = {}
    for stage in PIPELINE_STAGES:
        stage_id = stage['id']
        pipeline_data[stage_id] = []
        for candidate in candidates:
            current_stage = candidate_stage_map.get(candidate['id'])
            if current_stage is None and stage_id == 'new':
                pipeline_data[stage_id].append({'id': candidate['id'], 'name': candidate['name'], 'skills': candidate.get('skills', ''), 'total_experience': candidate.get('total_experience', 0)})
            elif current_stage == stage_id:
                app_obj = next((a for a in applications if a.get('candidate_id') == candidate['id']), None)
                pipeline_data[stage_id].append({'id': candidate['id'], 'name': candidate['name'], 'skills': candidate.get('skills', ''), 'total_experience': candidate.get('total_experience', 0), 'match_score': app_obj.get('match_score') if app_obj else None})
    return jsonify(pipeline_data)

@app.route('/api/pipeline/move', methods=['PUT'])
def move_pipeline_candidate():
    data = request.json
    candidate_id = data.get('candidate_id')
    new_stage = data.get('new_stage')
    application = None
    for app in applications:
        if app.get('candidate_id') == candidate_id:
            application = app
            break
    if application:
        application['status'] = new_stage
        application['updated_at'] = datetime.now().isoformat()
        return jsonify({'success': True})
    else:
        job = next((j for j in jobs if j.get('status') == 'open'), jobs[0] if jobs else None)
        if job:
            candidate = next((c for c in candidates if c['id'] == candidate_id), None)
            match_score, _ = calculate_weighted_match_score(job.get('skills_required', ''), candidate.get('skills', '') if candidate else '')
            new_application = {
                'id': len(applications) + 1, 'application_code': f"APP-{len(applications) + 1:04d}",
                'candidate_id': candidate_id, 'jd_id': job['id'], 'job_title': job['title'],
                'candidate_name': candidate['name'] if candidate else '', 'match_score': match_score,
                'status': new_stage, 'application_date': datetime.now().date().isoformat(),
                'created_at': datetime.now().isoformat()
            }
            applications.append(new_application)
            job['applications'] = job.get('applications', 0) + 1
            return jsonify({'success': True, 'match_score': match_score})
        else:
            return jsonify({'success': False, 'error': 'No open jobs available'}), 400

# ============= MAIN =============
if __name__ == '__main__':
    port = int(os.environ.get('PORT', 8080))
    app.run(host='0.0.0.0', port=port, debug=False)
