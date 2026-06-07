# app.py - DEBUG VERSION
import os
from flask import Flask, render_template_string
from flask_cors import CORS
from routes.candidates import candidates_bp
from routes.jobs import jobs_bp
from routes.analyze import analyze_bp
from routes.export import export_bp
from routes.documents import documents_bp
from models.database import init_db

app = Flask(__name__)
CORS(app)

# Initialize database
init_db()

# Create documents folder if not exists
os.makedirs('/tmp/candidate_docs', exist_ok=True)

# Register all blueprints
app.register_blueprint(candidates_bp, url_prefix='/api')
app.register_blueprint(jobs_bp, url_prefix='/api')
app.register_blueprint(analyze_bp, url_prefix='/api')
app.register_blueprint(export_bp, url_prefix='/api')
app.register_blueprint(documents_bp, url_prefix='/api')

# DEBUG HTML - Will show if buttons are found
HTML_TEMPLATE = '''
<!DOCTYPE html>
<html>
<head>
    <title>ShahnaIT Scout - Debug</title>
    <style>
        body { font-family: Arial; background: #F5F0E8; padding: 20px; }
        .header { background: #1A4D4A; color: white; padding: 20px; border-radius: 12px; }
        button { background: #1A4D4A; color: white; border: none; padding: 10px 20px; margin: 5px; cursor: pointer; border-radius: 8px; }
        button:hover { background: #2A6B67; }
        .card { background: white; padding: 15px; margin: 10px 0; border-radius: 8px; }
        .debug { background: #FFFFCC; padding: 10px; margin: 10px 0; font-family: monospace; }
        .green { background: #1B6B2E; color: white; padding: 5px 10px; border-radius: 5px; }
        .red { background: #B22222; color: white; padding: 5px 10px; border-radius: 5px; }
    </style>
</head>
<body>
<div style="max-width: 1000px; margin: 0 auto;">
    <div class="header">
        <h1>🎯 ShahnaIT Scout - Debug Mode</h1>
        <p>Testing button functionality</p>
    </div>
    
    <div class="debug">
        <h3>🔧 Debug Info:</h3>
        <p id="debugStatus">Checking buttons...</p>
    </div>
    
    <div class="tabs" style="display: flex; gap: 5px; margin: 20px 0; flex-wrap: wrap;">
        <button id="testBtn1">📋 Test Button 1</button>
        <button id="testBtn2">👥 Test Button 2</button>
        <button id="testBtn3">📄 Test Button 3</button>
    </div>
    
    <div id="result" class="card">
        Click a button above to test
    </div>
    
    <hr style="margin: 20px 0;">
    
    <h2>Original Features (Will work after debug)</h2>
    <div class="tabs" style="display: flex; gap: 5px; margin: 20px 0; flex-wrap: wrap;">
        <button id="jobsBtn">📋 Jobs</button>
        <button id="candidatesBtn">👥 Candidates</button>
        <button id="uploadBtn">📄 Upload Resume</button>
        <button id="createJobBtn">➕ Create Job</button>
        <button id="analyzeBtn">🔍 Analyze Match</button>
    </div>
    
    <div id="jobsPanel" style="display:none;"><div id="jobsList" class="card">Loading jobs...</div></div>
    <div id="candidatesPanel" style="display:none;"><div id="candidatesList" class="card">Loading candidates...</div></div>
    <div id="uploadPanel" style="display:none;">
        <div class="card">
            <input type="file" id="resumeFile" accept=".pdf,.docx">
            <button id="parseResumeBtn">Parse Resume</button>
            <div id="parseResult"></div>
        </div>
    </div>
    <div id="createJobPanel" style="display:none;">
        <div class="card">
            <input type="text" id="jobTitle" placeholder="Job Title">
            <button id="createJobSubmitBtn">Create Job</button>
        </div>
    </div>
    <div id="analyzePanel" style="display:none;">
        <div class="card">
            <select id="jobSelect"><option>Loading jobs...</option></select>
            <select id="candidateSelect"><option>Loading candidates...</option></select>
            <button id="runAnalysisBtn">Run Analysis</button>
            <div id="analysisResult"></div>
        </div>
    </div>
</div>

<script>
    // Debug function to log button clicks
    function log(message, isSuccess = true) {
        const debugDiv = document.getElementById('debugStatus');
        const resultDiv = document.getElementById('result');
        const timestamp = new Date().toLocaleTimeString();
        debugDiv.innerHTML += `<br>${timestamp}: ${message}`;
        resultDiv.innerHTML = `<span class="${isSuccess ? 'green' : 'red'}">${timestamp}: ${message}</span>`;
        console.log(message);
    }
    
    // Test Button 1
    document.getElementById('testBtn1').onclick = function() {
        log('✅ Test Button 1 CLICKED successfully!', true);
    };
    
    // Test Button 2
    document.getElementById('testBtn2').onclick = function() {
        log('✅ Test Button 2 CLICKED successfully!', true);
    };
    
    // Test Button 3
    document.getElementById('testBtn3').onclick = function() {
        log('✅ Test Button 3 CLICKED successfully!', true);
    };
    
    // Check if all buttons are found
    log('Checking buttons...');
    
    const testBtn1 = document.getElementById('testBtn1');
    const testBtn2 = document.getElementById('testBtn2');
    const testBtn3 = document.getElementById('testBtn3');
    
    if (testBtn1) log('✅ testBtn1 found', true);
    else log('❌ testBtn1 NOT found', false);
    
    if (testBtn2) log('✅ testBtn2 found', true);
    else log('❌ testBtn2 NOT found', false);
    
    if (testBtn3) log('✅ testBtn3 found', true);
    else log('❌ testBtn3 NOT found', false);
    
    // Original feature buttons
    const jobsBtn = document.getElementById('jobsBtn');
    const candidatesBtn = document.getElementById('candidatesBtn');
    const uploadBtn = document.getElementById('uploadBtn');
    const createJobBtn = document.getElementById('createJobBtn');
    const analyzeBtn = document.getElementById('analyzeBtn');
    
    if (jobsBtn) log('✅ jobsBtn found', true);
    else log('❌ jobsBtn NOT found', false);
    
    // Simple panel switching
    let currentPanel = 'jobs';
    
    function showPanel(panel) {
        document.getElementById('jobsPanel').style.display = 'none';
        document.getElementById('candidatesPanel').style.display = 'none';
        document.getElementById('uploadPanel').style.display = 'none';
        document.getElementById('createJobPanel').style.display = 'none';
        document.getElementById('analyzePanel').style.display = 'none';
        document.getElementById(panel + 'Panel').style.display = 'block';
        log(`Switched to ${panel} panel`);
    }
    
    if (jobsBtn) {
        jobsBtn.onclick = function() { 
            log('Jobs button clicked');
            showPanel('jobs');
            loadJobs();
        };
    }
    
    if (candidatesBtn) {
        candidatesBtn.onclick = function() { 
            log('Candidates button clicked');
            showPanel('candidates');
            loadCandidates();
        };
    }
    
    if (uploadBtn) {
        uploadBtn.onclick = function() { 
            log('Upload button clicked');
            showPanel('upload');
        };
    }
    
    if (createJobBtn) {
        createJobBtn.onclick = function() { 
            log('Create Job button clicked');
            showPanel('createJob');
        };
    }
    
    if (analyzeBtn) {
        analyzeBtn.onclick = function() { 
            log('Analyze button clicked');
            showPanel('analyze');
            loadJobs();
            loadCandidates();
        };
    }
    
    async function loadJobs() {
        log('Loading jobs...');
        try {
            const res = await fetch('/api/jobs');
            const jobs = await res.json();
            const container = document.getElementById('jobsList');
            if (jobs.length === 0) {
                container.innerHTML = '<div class="card">No jobs yet</div>';
            } else {
                container.innerHTML = jobs.map(j => `<div class="card"><h3>${escapeHtml(j.title)}</h3></div>`).join('');
            }
            const jobSelect = document.getElementById('jobSelect');
            if (jobSelect) {
                jobSelect.innerHTML = '<option value="">-- Select Job --</option>' + jobs.map(j => `<option value="${j.id}">${escapeHtml(j.title)}</option>`).join('');
            }
            log(`Loaded ${jobs.length} jobs`);
        } catch(e) {
            log(`Error loading jobs: ${e.message}`, false);
        }
    }
    
    async function loadCandidates() {
        log('Loading candidates...');
        try {
            const res = await fetch('/api/candidates');
            const candidates = await res.json();
            const container = document.getElementById('candidatesList');
            if (candidates.length === 0) {
                container.innerHTML = '<div class="card">No candidates yet</div>';
            } else {
                container.innerHTML = candidates.map(c => `<div class="card"><h3>${escapeHtml(c.first_name + ' ' + c.last_name || 'Unknown')}</h3></div>`).join('');
            }
            const candidateSelect = document.getElementById('candidateSelect');
            if (candidateSelect) {
                candidateSelect.innerHTML = '<option value="">-- Select Candidate --</option>' + candidates.map(c => `<option value="${c.id}">${escapeHtml(c.first_name + ' ' + c.last_name || 'Unknown')}</option>`).join('');
            }
            log(`Loaded ${candidates.length} candidates`);
        } catch(e) {
            log(`Error loading candidates: ${e.message}`, false);
        }
    }
    
    // Parse Resume
    const parseResumeBtn = document.getElementById('parseResumeBtn');
    if (parseResumeBtn) {
        parseResumeBtn.onclick = async function() {
            const file = document.getElementById('resumeFile').files[0];
            if (!file) { alert('Select a file'); return; }
            log(`Parsing resume: ${file.name}`);
            const fd = new FormData();
            fd.append('resume', file);
            const div = document.getElementById('parseResult');
            div.innerHTML = '<div class="card">Parsing...</div>';
            try {
                const res = await fetch('/api/parse-resume', { method: 'POST', body: fd });
                const result = await res.json();
                if (result.error) {
                    div.innerHTML = `<div class="card red">${result.error}</div>`;
                    log(`Parse error: ${result.error}`, false);
                } else {
                    div.innerHTML = `<div class="card green">✅ Parsed: ${result.first_name} ${result.last_name}</div>`;
                    log(`Parsed successfully: ${result.first_name} ${result.last_name}`);
                }
            } catch(e) {
                div.innerHTML = `<div class="card red">Error: ${e.message}</div>`;
                log(`Parse error: ${e.message}`, false);
            }
        };
    }
    
    // Create Job
    const createJobSubmitBtn = document.getElementById('createJobSubmitBtn');
    if (createJobSubmitBtn) {
        createJobSubmitBtn.onclick = async function() {
            const title = document.getElementById('jobTitle').value;
            if (!title) { alert('Title required'); return; }
            log(`Creating job: ${title}`);
            const res = await fetch('/api/jobs', { method: 'POST', headers: {'Content-Type':'application/json'}, body: JSON.stringify({ title }) });
            if (res.ok) {
                alert('Job created!');
                log('Job created successfully');
                document.getElementById('jobTitle').value = '';
                loadJobs();
            } else {
                log('Error creating job', false);
            }
        };
    }
    
    // Run Analysis
    const runAnalysisBtn = document.getElementById('runAnalysisBtn');
    if (runAnalysisBtn) {
        runAnalysisBtn.onclick = async function() {
            const jobId = document.getElementById('jobSelect').value;
            const candidateId = document.getElementById('candidateSelect').value;
            if (!jobId || !candidateId) { alert('Select both'); return; }
            log(`Analyzing job ${jobId} with candidate ${candidateId}`);
            const div = document.getElementById('analysisResult');
            div.innerHTML = '<div class="card">Analyzing...</div>';
            try {
                const res = await fetch('/api/analyze-match', { method: 'POST', headers: {'Content-Type':'application/json'}, body: JSON.stringify({ job_id: jobId, candidate_id: candidateId }) });
                const result = await res.json();
                if (result.error) {
                    div.innerHTML = `<div class="card red">${result.error}</div>`;
                    log(`Analysis error: ${result.error}`, false);
                } else {
                    div.innerHTML = `<div class="card green">✅ Score: ${result.match_score || 0}%</div>`;
                    log(`Analysis complete: ${result.match_score || 0}%`);
                }
            } catch(e) {
                div.innerHTML = `<div class="card red">Error: ${e.message}</div>`;
                log(`Analysis error: ${e.message}`, false);
            }
        };
    }
    
    function escapeHtml(str) { if (!str) return ''; return str.replace(/[&<>]/g, function(m) { if (m === '&') return '&amp;'; if (m === '<') return '&lt;'; if (m === '>') return '&gt;'; return m; }); }
    
    log('Debug page loaded. Try clicking the test buttons!');
</script>
</body>
</html>
'''

@app.route('/')
def index():
    return HTML_TEMPLATE

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
