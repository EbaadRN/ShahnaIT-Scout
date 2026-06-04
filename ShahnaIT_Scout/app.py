# app.py - PART 2/2 (HTML Template and API Routes)

# ============ HTML TEMPLATE ============
HTML_TEMPLATE = '''
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>ShahnaIT Scout — Professional ATS</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        :root {
            --bg-primary: #F9F6F0;
            --sidebar-bg: #FFFFFF;
            --primary-dark: #1A3A3A;
            --primary: #1D5E5A;
            --primary-light: #2A7A76;
            --text-dark: #2C3E3E;
            --text-muted: #6B7B7B;
            --accent-gold: #C9A96E;
            --border-light: #EAE5DC;
        }
        body { background-color: var(--bg-primary); font-family: 'Inter', system-ui, sans-serif; color: var(--text-dark); height: 100vh; overflow: hidden; }
        .app-layout { display: flex; height: 100vh; width: 100%; }
        
        .sidebar { width: 280px; background: var(--sidebar-bg); border-right: 1px solid var(--border-light); display: flex; flex-direction: column; padding: 32px 20px; flex-shrink: 0; overflow-y: auto; }
        .logo-area { margin-bottom: 48px; }
        .logo-area h1 { font-size: 1.7rem; font-weight: 700; background: linear-gradient(135deg, var(--primary-dark) 0%, var(--primary) 100%); -webkit-background-clip: text; background-clip: text; color: transparent; }
        .nav-menu { flex: 1; display: flex; flex-direction: column; gap: 8px; }
        .nav-item { display: flex; align-items: center; gap: 14px; padding: 12px 16px; border-radius: 14px; font-weight: 500; color: var(--text-muted); cursor: pointer; transition: all 0.2s ease; }
        .nav-item:hover { background-color: var(--bg-primary); color: var(--primary); }
        .nav-item.active { background: linear-gradient(135deg, var(--primary-dark), var(--primary)); color: white; }
        .ai-badge-side { margin-top: 32px; padding: 16px; background: var(--bg-primary); border-radius: 20px; text-align: center; }
        
        .main-content { flex: 1; overflow-y: auto; padding: 32px 40px; }
        .card { background: #FFFFFF; border-radius: 20px; padding: 24px; margin-bottom: 24px; box-shadow: 0 8px 20px rgba(0,0,0,0.03); border: 1px solid var(--border-light); cursor: pointer; transition: all 0.25s ease; }
        .card:hover { transform: translateY(-3px); box-shadow: 0 12px 28px rgba(0,0,0,0.08); }
        .card.no-click { cursor: default; }
        .card.no-click:hover { transform: none; }
        
        .skill-tag { display: inline-block; background: var(--bg-primary); padding: 4px 12px; border-radius: 30px; font-size: 0.75rem; margin: 4px 4px 0 0; color: var(--primary-dark); font-weight: 500; }
        .match-high { background: #1B6B2E; color: white; padding: 2px 10px; border-radius: 30px; font-weight: 600; display: inline-block; }
        .match-medium { background: #CC5500; color: white; padding: 2px 10px; border-radius: 30px; font-weight: 600; display: inline-block; }
        .match-low { background: #B22222; color: white; padding: 2px 10px; border-radius: 30px; font-weight: 600; display: inline-block; }
        
        .btn-primary { background: var(--primary); border: none; padding: 10px 24px; border-radius: 40px; font-weight: 600; color: white; cursor: pointer; }
        .btn-primary:hover { background: var(--primary-light); }
        .btn-secondary { background: var(--text-muted); border: none; padding: 8px 20px; border-radius: 40px; font-weight: 500; color: white; cursor: pointer; }
        .btn-edit { background: #C9A96E; border: none; padding: 6px 16px; border-radius: 30px; font-weight: 500; color: white; cursor: pointer; font-size: 12px; }
        
        input, textarea, select { width: 100%; padding: 12px 16px; border: 1px solid var(--border-light); border-radius: 16px; background: white; margin-bottom: 16px; }
        input:focus, textarea:focus, select:focus { outline: none; border-color: var(--primary); }
        
        .modal { display: none; position: fixed; z-index: 1000; left: 0; top: 0; width: 100%; height: 100%; background: rgba(0,0,0,0.5); backdrop-filter: blur(4px); overflow-y: auto; }
        .modal-content { background: var(--bg-primary); margin: 3% auto; border-radius: 28px; max-width: 950px; width: 90%; box-shadow: 0 25px 50px rgba(0,0,0,0.3); }
        .modal-header { background: var(--primary-dark); color: white; padding: 20px 28px; border-radius: 28px 28px 0 0; display: flex; justify-content: space-between; align-items: center; }
        .modal-header h2 { margin: 0; }
        .modal-body { padding: 28px; max-height: 70vh; overflow-y: auto; }
        .close { font-size: 32px; cursor: pointer; color: white; }
        
        .detail-row { display: flex; margin-bottom: 12px; border-bottom: 1px solid var(--border-light); padding-bottom: 8px; }
        .detail-label { width: 140px; font-weight: 600; color: var(--primary-dark); }
        .detail-value { flex: 1; color: var(--text-dark); word-break: break-word; }
        
        .company-item { background: #F9F6F0; padding: 12px; border-radius: 16px; margin-bottom: 8px; border-left: 3px solid var(--primary); }
        
        .search-bar { margin-bottom: 20px; display: flex; gap: 10px; }
        .search-bar input { flex: 1; margin-bottom: 0; }
        
        .flex { display: flex; gap: 16px; flex-wrap: wrap; }
        .flex-1 { flex: 1; }
        
        .spinner { border: 3px solid var(--bg-primary); border-top: 3px solid var(--primary); border-radius: 50%; width: 45px; height: 45px; animation: spin 0.8s linear infinite; margin: 20px auto; }
        @keyframes spin { 0% { transform: rotate(0deg); } 100% { transform: rotate(360deg); } }
        
        .alert-success { background: #1B6B2E; color: white; padding: 14px; border-radius: 16px; margin: 12px 0; }
        .alert-error { background: #B22222; color: white; padding: 14px; border-radius: 16px; margin: 12px 0; }
        .alert-info { background: #3498DB; color: white; padding: 14px; border-radius: 16px; margin: 12px 0; }
        
        @media (max-width: 768px) { .sidebar { width: 80px; } .nav-item span:last-child { display: none; } .detail-label { width: 100px; } }
    </style>
</head>
<body>
<div class="app-layout">
    <div class="sidebar">
        <div class="logo-area"><h1>ShahnaIT</h1></div>
        <div class="nav-menu">
            <div class="nav-item active" data-tab="jobs">📋 Jobs</div>
            <div class="nav-item" data-tab="candidates">👥 Candidates</div>
            <div class="nav-item" data-tab="upload">📄 Upload Resume</div>
            <div class="nav-item" data-tab="create-job">➕ Create Job</div>
            <div class="nav-item" data-tab="analyze">🔍 Analyze Match</div>
        </div>
        <div class="ai-badge-side"><span>⚡ GROQ + 🤖 DEEPSEEK</span></div>
    </div>

    <div class="main-content">
        <div id="jobs-view"><div style="display: flex; justify-content: space-between; margin-bottom: 20px;"><h2>📋 Jobs</h2><button class="btn-primary" onclick="switchTab('create-job')">+ New Job</button></div><div id="jobs-list"></div></div>
        <div id="candidates-view" style="display:none;"><div style="display: flex; justify-content: space-between; margin-bottom: 20px;"><h2>👥 Candidates</h2><button class="btn-primary" onclick="exportToCSV()">📥 Export CSV</button></div><div class="search-bar"><input type="text" id="candidate-search" placeholder="🔍 Search by name, skills..." onkeyup="filterCandidates()"><button class="btn-secondary" onclick="clearSearch()">Clear</button></div><div id="candidates-list"></div></div>
        <div id="upload-view" style="display:none;"><div class="card no-click"><h3>📄 Upload Resume</h3><div class="alert-info">🤖 AI will auto-fill candidate details</div><input type="file" id="resume-file" accept=".pdf,.docx"><button class="btn-primary" id="parseBtn">🔍 Parse & Auto-Fill</button><div id="parse-result"></div></div></div>
        <div id="create-job-view" style="display:none;"><div class="card no-click"><h3>➕ Create Job</h3><form id="jobForm"><input type="text" id="job-title" placeholder="Job Title *" required><input type="text" id="job-company" placeholder="Company"><textarea id="job-desc" rows="5" placeholder="Job Description"></textarea><button type="submit" class="btn-primary">Create Job</button></form></div></div>
        <div id="analyze-view" style="display:none;"><div class="card no-click"><h3>🔍 AI Match Analysis</h3><div class="flex"><div class="flex-1"><select id="analyze-job-select"></select></div><div class="flex-1"><select id="analyze-candidate-select"></select></div></div><button class="btn-primary" id="analyzeBtn">🤖 Run DeepSeek Analysis</button><div id="analyze-result"></div></div></div>
    </div>
</div>

<!-- Candidate Modal -->
<div id="candidateModal" class="modal">
    <div class="modal-content">
        <div class="modal-header"><h2 id="modalTitle">Candidate Profile</h2><span class="close" onclick="closeModal()">&times;</span></div>
        <div class="modal-body" id="modalBody">Loading...</div>
    </div>
</div>

<script>
    let jobsData = [], candidatesData = [], currentCandidateId = null;
    
    function switchTab(tabId) {
        document.querySelectorAll('[id$="-view"]').forEach(el => el.style.display = 'none');
        document.getElementById(tabId + '-view').style.display = 'block';
        document.querySelectorAll('.nav-item').forEach(item => item.classList.remove('active'));
        document.querySelector(`.nav-item[data-tab="${tabId}"]`).classList.add('active');
        if (tabId === 'jobs') loadJobs();
        if (tabId === 'candidates') loadCandidates();
        if (tabId === 'analyze') { loadJobs(); loadCandidates(); }
    }
    
    async function loadJobs() {
        const res = await fetch('/api/jobs');
        jobsData = await res.json();
        const container = document.getElementById('jobs-list');
        if (!jobsData.length) { container.innerHTML = '<div class="card no-click">No jobs yet</div>'; return; }
        container.innerHTML = jobsData.map(job => `<div class="card no-click"><h3>${escapeHtml(job.title)}</h3>${job.company ? `<p>🏢 ${escapeHtml(job.company)}</p>` : ''}<small>📅 ${new Date(job.created_at).toLocaleDateString()}</small></div>`).join('');
        document.getElementById('analyze-job-select').innerHTML = '<option value="">-- Select Job --</option>' + jobsData.map(j => `<option value="${j.id}">${escapeHtml(j.title)}</option>`).join('');
    }
    
    async function loadCandidates() {
        const res = await fetch('/api/candidates');
        candidatesData = await res.json();
        renderCandidateList(candidatesData);
        document.getElementById('analyze-candidate-select').innerHTML = '<option value="">-- Select Candidate --</option>' + candidatesData.map(c => `<option value="${c.id}">${escapeHtml(c.first_name + ' ' + c.last_name || 'Unknown')}</option>`).join('');
    }
    
    function renderCandidateList(candidates) {
        const container = document.getElementById('candidates-list');
        if (!candidates.length) { container.innerHTML = '<div class="card no-click">No candidates yet</div>'; return; }
        container.innerHTML = candidates.map(c => {
            const fullName = `${c.first_name || ''} ${c.last_name || ''}`.trim() || 'Unknown';
            const skills = c.core_skills ? JSON.parse(c.core_skills || '[]') : [];
            return `<div class="card" onclick="viewCandidate(${c.id})"><h3>👤 ${escapeHtml(fullName)}</h3>${c.email ? `<p>📧 ${escapeHtml(c.email)}</p>` : ''}<p>🔧 ${skills.slice(0,3).map(s => `<span class="skill-tag">${escapeHtml(s.skill)}</span>`).join('')}</p>${c.match_score ? `<p>🎯 Score: <span class="${c.match_score >= 70 ? 'match-high' : (c.match_score >= 40 ? 'match-medium' : 'match-low')}">${c.match_score}%</span></p>` : ''}<small>📅 ${new Date(c.created_at).toLocaleDateString()}</small></div>`;
        }).join('');
    }
    
    function filterCandidates() {
        const term = document.getElementById('candidate-search').value.toLowerCase();
        const filtered = candidatesData.filter(c => {
            const name = `${c.first_name || ''} ${c.last_name || ''}`.toLowerCase();
            const skills = c.core_skills ? JSON.parse(c.core_skills).map(s => s.skill.toLowerCase()).join(' ') : '';
            return name.includes(term) || skills.includes(term);
        });
        renderCandidateList(filtered);
    }
    
    function clearSearch() { document.getElementById('candidate-search').value = ''; renderCandidateList(candidatesData); }
    
    async function viewCandidate(id) {
        const c = candidatesData.find(c => c.id == id);
        if (!c) return;
        
        const fullName = `${c.first_name || ''} ${c.middle_name || ''} ${c.last_name || ''}`.trim();
        const workExp = JSON.parse(c.work_experience || '[]');
        const certs = JSON.parse(c.certifications || '[]');
        const skills = JSON.parse(c.core_skills || '[]');
        
        const docRes = await fetch(`/api/candidates/${id}/documents`);
        const documents = await docRes.json();
        const resumeDoc = documents.find(d => d.is_resume === 1);
        const otherDocs = documents.filter(d => !d.is_resume);
        
        document.getElementById('modalBody').innerHTML = `
            <div style="display: flex; gap: 10px; justify-content: flex-end; margin-bottom: 15px;">
                <button class="btn-primary" onclick="openEditForm(${id})">✏️ Edit Profile</button>
                <button class="btn-secondary" onclick="copyAllDetails()">📋 Copy All</button>
            </div>
            <div class="detail-row"><div class="detail-label">Full Name:</div><div class="detail-value">${escapeHtml(fullName)}</div></div>
            <div class="detail-row"><div class="detail-label">Phone:</div><div class="detail-value">${escapeHtml(c.phone || 'N/A')}</div></div>
            <div class="detail-row"><div class="detail-label">Email:</div><div class="detail-value">${escapeHtml(c.email || 'N/A')}</div></div>
            <div class="detail-row"><div class="detail-label">Address:</div><div class="detail-value">${escapeHtml(c.address || 'N/A')}</div></div>
            <div class="detail-row"><div class="detail-label">LinkedIn:</div><div class="detail-value">${escapeHtml(c.linkedin || 'N/A')}</div></div>
            <div class="detail-row"><div class="detail-label">Current Role:</div><div class="detail-value">${escapeHtml(c.current_role || 'N/A')}</div></div>
            <div class="detail-row"><div class="detail-label">Status:</div><div class="detail-value">${escapeHtml(c.employment_status || 'N/A')}${c.notice_period_days ? ` (${c.notice_period_days} days)` : ''}</div></div>
            
            <h4 style="margin-top: 20px;">💼 Work Experience</h4>
            ${workExp.map(w => `<div class="company-item"><strong>${escapeHtml(w.company)}</strong> — ${escapeHtml(w.role)}<br><small>${escapeHtml(w.start_date || '')} - ${escapeHtml(w.end_date || 'Present')}</small></div>`).join('') || '<p>None</p>'}
            
            <h4>⭐ Core Skills</h4>
            ${skills.map(s => `<span class="skill-tag">${escapeHtml(s.skill)} (${s.years_of_experience || '?'} yrs)</span>`).join('') || '<p>None</p>'}
            
            <h4>📜 Certifications</h4>
            ${certs.map(cert => `<div>📜 ${escapeHtml(cert)}</div>`).join('') || '<p>None</p>'}
            
            <h4>🎓 Education</h4>
            <p>${escapeHtml(c.education || 'N/A')}</p>
            
            <h4>📄 Resume</h4>
            ${resumeDoc ? `<div><a href="/api/documents/${resumeDoc.id}" target="_blank">📄 ${escapeHtml(resumeDoc.original_filename)}</a> <span style="background:#1B6B2E; color:white; padding:2px 8px; border-radius:12px; font-size:10px;">Original Resume</span></div>` : '<p>No resume attached</p>'}
            
            <h4>📎 Other Documents (${otherDocs.length})</h4>
            ${otherDocs.map(d => `<div><a href="/api/documents/${d.id}" target="_blank">📄 ${escapeHtml(d.original_filename)}</a></div>`).join('') || '<p>No additional documents</p>'}
            
            <button class="btn-primary" onclick="closeModal()" style="margin-top: 20px;">Close</button>
        `;
        document.getElementById('candidateModal').style.display = 'block';
    }
    
    function openEditForm(id) {
        window.location.href = `/edit-candidate/${id}`;
    }
    
    function copyAllDetails() {
        let text = '';
        document.querySelectorAll('#modalBody .detail-row, #modalBody h4, #modalBody .company-item, #modalBody .skill-tag').forEach(el => {
            text += el.innerText + '\n';
        });
        navigator.clipboard.writeText(text);
        alert('Copied to clipboard!');
    }
    
    function closeModal() { document.getElementById('candidateModal').style.display = 'none'; }
    
    document.getElementById('parseBtn').onclick = async () => {
        const file = document.getElementById('resume-file').files[0];
        if (!file) return alert('Select a file');
        const fd = new FormData(); fd.append('resume', file);
        const div = document.getElementById('parse-result');
        div.innerHTML = '<div class="spinner"></div>';
        try {
            const res = await fetch('/api/parse-resume-detailed', { method: 'POST', body: fd });
            const result = await res.json();
            if (result.error) { div.innerHTML = `<div class="alert-error">${result.error}</div>`; return; }
            div.innerHTML = `<div class="alert-success"><h4>✅ Parsed</h4><p>${escapeHtml(result.first_name || '')} ${escapeHtml(result.last_name || '')}</p><button class="btn-primary" id="saveDetailedBtn">Save Candidate</button></div>`;
            document.getElementById('saveDetailedBtn').onclick = async () => {
                const saveRes = await fetch('/api/candidates/detailed', { method: 'POST', headers: {'Content-Type':'application/json'}, body: JSON.stringify(result) });
                if (saveRes.ok) { alert('Saved!'); div.innerHTML = ''; document.getElementById('resume-file').value = ''; loadCandidates(); }
                else alert('Error');
            };
        } catch(e) { div.innerHTML = '<div class="alert-error">Error</div>'; }
    };
    
    document.getElementById('analyzeBtn').onclick = async () => {
        const jobId = document.getElementById('analyze-job-select').value;
        const candidateId = document.getElementById('analyze-candidate-select').value;
        if (!jobId || !candidateId) return alert('Select both');
        const job = jobsData.find(j => j.id == jobId);
        const cand = candidatesData.find(c => c.id == candidateId);
        const div = document.getElementById('analyze-result');
        div.innerHTML = '<div class="spinner"></div><p>🤖 Running DeepSeek analysis...</p>';
        try {
            const res = await fetch('/api/analyze-match', { method: 'POST', headers: {'Content-Type':'application/json'}, body: JSON.stringify({ job_id: jobId, candidate_id: candidateId, jd_text: job.description || '', resume_text: cand.resume_text || '' }) });
            const result = await res.json();
            if (result.error) { div.innerHTML = `<div class="alert-error">${result.error}</div>`; return; }
            const matchClass = result.match_score >= 70 ? 'match-high' : (result.match_score >= 40 ? 'match-medium' : 'match-low');
            div.innerHTML = `<div class="alert-success"><h4>📊 DeepSeek Analysis Complete</h4><p>🎯 Match Score: <span class="${matchClass}">${result.match_score || 0}%</span></p><p>📌 Recommendation: ${result.recommendation || 'Review'}</p><div class="alert-info" style="margin-top:10px;"><strong>📝 ${result.executive_summary?.final_verdict || ''}</strong></div>${result.pre_screening_questions ? `<div style="margin-top:10px;"><strong>📋 Pre-screening Questions:</strong><ul>${result.pre_screening_questions.map(q => `<li>${escapeHtml(q)}</li>`).join('')}</ul></div>` : ''}<small>✅ Analysis saved</small></div>`;
            loadCandidates();
        } catch(e) { div.innerHTML = '<div class="alert-error">Analysis failed</div>'; }
    };
    
    window.exportToCSV = function() { window.location.href = '/api/export-candidates'; };
    
    document.getElementById('jobForm').onsubmit = async (e) => {
        e.preventDefault();
        const data = { title: document.getElementById('job-title').value, company: document.getElementById('job-company').value, description: document.getElementById('job-desc').value };
        if (!data.title) return alert('Title required');
        const res = await fetch('/api/jobs', { method: 'POST', headers: {'Content-Type':'application/json'}, body: JSON.stringify(data) });
        if (res.ok) { alert('Job created'); document.getElementById('job-title').value = ''; document.getElementById('job-company').value = ''; document.getElementById('job-desc').value = ''; switchTab('jobs'); loadJobs(); }
        else alert('Error');
    };
    
    function escapeHtml(str) { if (!str) return ''; const div = document.createElement('div'); div.textContent = str; return div.innerHTML; }
    
    document.querySelectorAll('.nav-item').forEach(item => item.addEventListener('click', () => switchTab(item.getAttribute('data-tab'))));
    loadJobs(); loadCandidates();
</script>
</body>
</html>
'''

# ============ API ROUTES ============
@app.route('/')
def index():
    return render_template_string(HTML_TEMPLATE, groq_enabled=GROQ_ENABLED, deepseek_enabled=DEEPSEEK_ENABLED)

@app.route('/api/parse-resume-detailed', methods=['POST'])
def parse_resume_detailed_api():
    if 'resume' not in request.files:
        return jsonify({'error': 'No file'}), 400
    file = request.files['resume']
    if file.filename == '':
        return jsonify({'error': 'No file'}), 400
    
    filename = secure_filename(file.filename)
    original_filename = file.filename
    filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
    file.save(filepath)
    
    if filename.endswith('.pdf'):
        text = extract_text_from_pdf(filepath)
    else:
        text = extract_text_from_docx(filepath)
    
    if not text:
        os.remove(filepath)
        return jsonify({'error': 'Could not extract text'}), 400
    
    parsed = parse_resume_with_ai(text)
    if parsed and parsed.get('first_name'):
        parsed['resume_text'] = text[:3000]
        parsed['resume_filename'] = original_filename
        parsed['ai_used'] = True
        parsed['file_path'] = filepath
        parsed['original_filename'] = original_filename
        return jsonify(parsed)
    else:
        fallback = fallback_parse_resume(text)
        fallback['resume_text'] = text[:3000]
        fallback['resume_filename'] = original_filename
        fallback['ai_used'] = False
        fallback['file_path'] = filepath
        fallback['original_filename'] = original_filename
        return jsonify(fallback)

@app.route('/api/candidates/detailed', methods=['POST'])
def create_candidate_detailed():
    data = request.json
    conn = sqlite3.connect('shahnai.db')
    c = conn.cursor()
    c.execute('''INSERT INTO candidates 
        (first_name, last_name, middle_name, phone, email, address, linkedin, other_social,
         current_role, employment_status, notice_period_days, work_experience, certifications,
         core_skills, education, resume_text, resume_filename)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)''',
        (data.get('first_name'), data.get('last_name'), data.get('middle_name'),
         data.get('phone'), data.get('email'), data.get('address'), data.get('linkedin'), data.get('other_social'),
         data.get('current_role'), data.get('employment_status'), data.get('notice_period_days', 0),
         json.dumps(data.get('work_experience', [])), json.dumps(data.get('certifications', [])),
         json.dumps(data.get('core_skills', [])), data.get('education'), data.get('resume_text'), data.get('resume_filename')))
    
    candidate_id = c.lastrowid
    
    file_path = data.get('file_path')
    original_filename = data.get('original_filename')
    
    if file_path and os.path.exists(file_path):
        permanent_filename = secure_filename(f"{candidate_id}_{datetime.now().timestamp()}_{original_filename}")
        permanent_path = os.path.join(app.config['DOCUMENTS_FOLDER'], permanent_filename)
        shutil.move(file_path, permanent_path)
        
        c.execute('INSERT INTO candidate_documents (candidate_id, filename, original_filename, file_path, file_type, is_resume) VALUES (?, ?, ?, ?, ?, ?)',
                  (candidate_id, permanent_filename, original_filename, permanent_path, original_filename.split('.')[-1], 1))
    
    conn.commit()
    conn.close()
    return jsonify({'message': 'Candidate saved', 'id': candidate_id})

@app.route('/api/candidates', methods=['GET'])
def get_candidates():
    conn = sqlite3.connect('shahnai.db')
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    c.execute('SELECT * FROM candidates ORDER BY created_at DESC')
    candidates = [dict(row) for row in c.fetchall()]
    conn.close()
    return jsonify(candidates)

@app.route('/api/candidates/<int:candidate_id>', methods=['PUT'])
def update_candidate(candidate_id):
    data = request.json
    conn = sqlite3.connect('shahnai.db')
    c = conn.cursor()
    c.execute('''UPDATE candidates SET 
        first_name=?, middle_name=?, last_name=?, email=?, phone=?, address=?, linkedin=?,
        current_role=?, employment_status=?, notice_period_days=?, education=?,
        work_experience=?, certifications=?, core_skills=?
        WHERE id=?''',
        (data.get('first_name'), data.get('middle_name'), data.get('last_name'),
         data.get('email'), data.get('phone'), data.get('address'), data.get('linkedin'),
         data.get('current_role'), data.get('employment_status'), data.get('notice_period_days', 0),
         data.get('education'), data.get('work_experience'), data.get('certifications'),
         data.get('core_skills'), candidate_id))
    conn.commit()
    conn.close()
    return jsonify({'message': 'Candidate updated'})

@app.route('/api/candidates/<int:candidate_id>/documents', methods=['GET'])
def get_candidate_documents(candidate_id):
    conn = sqlite3.connect('shahnai.db')
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    c.execute('SELECT * FROM candidate_documents WHERE candidate_id = ? ORDER BY is_resume DESC, uploaded_at DESC', (candidate_id,))
    docs = [dict(row) for row in c.fetchall()]
    conn.close()
    return jsonify(docs)

@app.route('/api/documents/<int:doc_id>', methods=['GET'])
def get_document(doc_id):
    conn = sqlite3.connect('shahnai.db')
    c = conn.cursor()
    c.execute('SELECT * FROM candidate_documents WHERE id = ?', (doc_id,))
    doc = c.fetchone()
    conn.close()
    if doc and os.path.exists(doc[4]):
        return send_file(doc[4], as_attachment=False, download_name=doc[3])
    return jsonify({'error': 'File not found'}), 404

@app.route('/api/jobs', methods=['GET'])
def get_jobs():
    conn = sqlite3.connect('shahnai.db')
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    c.execute('SELECT * FROM jobs ORDER BY created_at DESC')
    jobs = [dict(row) for row in c.fetchall()]
    conn.close()
    return jsonify(jobs)

@app.route('/api/jobs', methods=['POST'])
def create_job():
    data = request.json
    conn = sqlite3.connect('shahnai.db')
    c = conn.cursor()
    c.execute('INSERT INTO jobs (title, company, description) VALUES (?, ?, ?)',
              (data.get('title'), data.get('company'), data.get('description', '')))
    conn.commit()
    conn.close()
    return jsonify({'message': 'Job created'})

@app.route('/api/analyze-match', methods=['POST'])
def analyze_match():
    data = request.json
    resume_text = data.get('resume_text', '')
    jd_text = data.get('jd_text', '')
    candidate_id = data.get('candidate_id')
    
    if not resume_text or not jd_text:
        return jsonify({'error': 'Missing text'}), 400
    
    result = analyze_with_deepseek(resume_text, jd_text)
    
    if not result:
        # Fallback to Groq
        result = quick_match_with_groq(resume_text, jd_text)
    
    if result and candidate_id:
        detailed_json = json.dumps(result, indent=2)
        conn = sqlite3.connect('shahnai.db')
        c = conn.cursor()
        c.execute('UPDATE candidates SET match_score = ?, recommendation = ?, detailed_analysis = ? WHERE id = ?',
                  (result.get('match_score', 0), result.get('recommendation', 'review'), detailed_json, candidate_id))
        conn.commit()
        conn.close()
        return jsonify(result)
    
    return jsonify({'error': 'Analysis failed. Check API keys.'}), 500

@app.route('/api/export-candidates', methods=['GET'])
def export_candidates():
    conn = sqlite3.connect('shahnai.db')
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    c.execute('SELECT id, first_name, last_name, email, phone, current_role, match_score, created_at FROM candidates ORDER BY created_at DESC')
    rows = c.fetchall()
    conn.close()
    
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(['ID', 'First Name', 'Last Name', 'Email', 'Phone', 'Current Role', 'Match Score (%)', 'Created Date'])
    
    for row in rows:
        writer.writerow([
            row['id'], row['first_name'] or '', row['last_name'] or '',
            row['email'] or '', row['phone'] or '', row['current_role'] or '',
            row['match_score'] or 0, row['created_at']
        ])
    
    output.seek(0)
    return Response(output.getvalue(), mimetype='text/csv', headers={'Content-Disposition': 'attachment; filename=candidates_export.csv'})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
    # app.py - PART 2/2 (HTML Template and API Routes)

# ============ HTML TEMPLATE ============
HTML_TEMPLATE = '''
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>ShahnaIT Scout — Professional ATS</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        :root {
            --bg-primary: #F9F6F0;
            --sidebar-bg: #FFFFFF;
            --primary-dark: #1A3A3A;
            --primary: #1D5E5A;
            --primary-light: #2A7A76;
            --text-dark: #2C3E3E;
            --text-muted: #6B7B7B;
            --accent-gold: #C9A96E;
            --border-light: #EAE5DC;
        }
        body { background-color: var(--bg-primary); font-family: 'Inter', system-ui, sans-serif; color: var(--text-dark); height: 100vh; overflow: hidden; }
        .app-layout { display: flex; height: 100vh; width: 100%; }
        
        .sidebar { width: 280px; background: var(--sidebar-bg); border-right: 1px solid var(--border-light); display: flex; flex-direction: column; padding: 32px 20px; flex-shrink: 0; overflow-y: auto; }
        .logo-area { margin-bottom: 48px; }
        .logo-area h1 { font-size: 1.7rem; font-weight: 700; background: linear-gradient(135deg, var(--primary-dark) 0%, var(--primary) 100%); -webkit-background-clip: text; background-clip: text; color: transparent; }
        .nav-menu { flex: 1; display: flex; flex-direction: column; gap: 8px; }
        .nav-item { display: flex; align-items: center; gap: 14px; padding: 12px 16px; border-radius: 14px; font-weight: 500; color: var(--text-muted); cursor: pointer; transition: all 0.2s ease; }
        .nav-item:hover { background-color: var(--bg-primary); color: var(--primary); }
        .nav-item.active { background: linear-gradient(135deg, var(--primary-dark), var(--primary)); color: white; }
        .ai-badge-side { margin-top: 32px; padding: 16px; background: var(--bg-primary); border-radius: 20px; text-align: center; }
        
        .main-content { flex: 1; overflow-y: auto; padding: 32px 40px; }
        .card { background: #FFFFFF; border-radius: 20px; padding: 24px; margin-bottom: 24px; box-shadow: 0 8px 20px rgba(0,0,0,0.03); border: 1px solid var(--border-light); cursor: pointer; transition: all 0.25s ease; }
        .card:hover { transform: translateY(-3px); box-shadow: 0 12px 28px rgba(0,0,0,0.08); }
        .card.no-click { cursor: default; }
        .card.no-click:hover { transform: none; }
        
        .skill-tag { display: inline-block; background: var(--bg-primary); padding: 4px 12px; border-radius: 30px; font-size: 0.75rem; margin: 4px 4px 0 0; color: var(--primary-dark); font-weight: 500; }
        .match-high { background: #1B6B2E; color: white; padding: 2px 10px; border-radius: 30px; font-weight: 600; display: inline-block; }
        .match-medium { background: #CC5500; color: white; padding: 2px 10px; border-radius: 30px; font-weight: 600; display: inline-block; }
        .match-low { background: #B22222; color: white; padding: 2px 10px; border-radius: 30px; font-weight: 600; display: inline-block; }
        
        .btn-primary { background: var(--primary); border: none; padding: 10px 24px; border-radius: 40px; font-weight: 600; color: white; cursor: pointer; }
        .btn-primary:hover { background: var(--primary-light); }
        .btn-secondary { background: var(--text-muted); border: none; padding: 8px 20px; border-radius: 40px; font-weight: 500; color: white; cursor: pointer; }
        .btn-edit { background: #C9A96E; border: none; padding: 6px 16px; border-radius: 30px; font-weight: 500; color: white; cursor: pointer; font-size: 12px; }
        
        input, textarea, select { width: 100%; padding: 12px 16px; border: 1px solid var(--border-light); border-radius: 16px; background: white; margin-bottom: 16px; }
        input:focus, textarea:focus, select:focus { outline: none; border-color: var(--primary); }
        
        .modal { display: none; position: fixed; z-index: 1000; left: 0; top: 0; width: 100%; height: 100%; background: rgba(0,0,0,0.5); backdrop-filter: blur(4px); overflow-y: auto; }
        .modal-content { background: var(--bg-primary); margin: 3% auto; border-radius: 28px; max-width: 950px; width: 90%; box-shadow: 0 25px 50px rgba(0,0,0,0.3); }
        .modal-header { background: var(--primary-dark); color: white; padding: 20px 28px; border-radius: 28px 28px 0 0; display: flex; justify-content: space-between; align-items: center; }
        .modal-header h2 { margin: 0; }
        .modal-body { padding: 28px; max-height: 70vh; overflow-y: auto; }
        .close { font-size: 32px; cursor: pointer; color: white; }
        
        .detail-row { display: flex; margin-bottom: 12px; border-bottom: 1px solid var(--border-light); padding-bottom: 8px; }
        .detail-label { width: 140px; font-weight: 600; color: var(--primary-dark); }
        .detail-value { flex: 1; color: var(--text-dark); word-break: break-word; }
        
        .company-item { background: #F9F6F0; padding: 12px; border-radius: 16px; margin-bottom: 8px; border-left: 3px solid var(--primary); }
        
        .search-bar { margin-bottom: 20px; display: flex; gap: 10px; }
        .search-bar input { flex: 1; margin-bottom: 0; }
        
        .flex { display: flex; gap: 16px; flex-wrap: wrap; }
        .flex-1 { flex: 1; }
        
        .spinner { border: 3px solid var(--bg-primary); border-top: 3px solid var(--primary); border-radius: 50%; width: 45px; height: 45px; animation: spin 0.8s linear infinite; margin: 20px auto; }
        @keyframes spin { 0% { transform: rotate(0deg); } 100% { transform: rotate(360deg); } }
        
        .alert-success { background: #1B6B2E; color: white; padding: 14px; border-radius: 16px; margin: 12px 0; }
        .alert-error { background: #B22222; color: white; padding: 14px; border-radius: 16px; margin: 12px 0; }
        .alert-info { background: #3498DB; color: white; padding: 14px; border-radius: 16px; margin: 12px 0; }
        
        @media (max-width: 768px) { .sidebar { width: 80px; } .nav-item span:last-child { display: none; } .detail-label { width: 100px; } }
    </style>
</head>
<body>
<div class="app-layout">
    <div class="sidebar">
        <div class="logo-area"><h1>ShahnaIT</h1></div>
        <div class="nav-menu">
            <div class="nav-item active" data-tab="jobs">📋 Jobs</div>
            <div class="nav-item" data-tab="candidates">👥 Candidates</div>
            <div class="nav-item" data-tab="upload">📄 Upload Resume</div>
            <div class="nav-item" data-tab="create-job">➕ Create Job</div>
            <div class="nav-item" data-tab="analyze">🔍 Analyze Match</div>
        </div>
        <div class="ai-badge-side"><span>⚡ GROQ + 🤖 DEEPSEEK</span></div>
    </div>

    <div class="main-content">
        <div id="jobs-view"><div style="display: flex; justify-content: space-between; margin-bottom: 20px;"><h2>📋 Jobs</h2><button class="btn-primary" onclick="switchTab('create-job')">+ New Job</button></div><div id="jobs-list"></div></div>
        <div id="candidates-view" style="display:none;"><div style="display: flex; justify-content: space-between; margin-bottom: 20px;"><h2>👥 Candidates</h2><button class="btn-primary" onclick="exportToCSV()">📥 Export CSV</button></div><div class="search-bar"><input type="text" id="candidate-search" placeholder="🔍 Search by name, skills..." onkeyup="filterCandidates()"><button class="btn-secondary" onclick="clearSearch()">Clear</button></div><div id="candidates-list"></div></div>
        <div id="upload-view" style="display:none;"><div class="card no-click"><h3>📄 Upload Resume</h3><div class="alert-info">🤖 AI will auto-fill candidate details</div><input type="file" id="resume-file" accept=".pdf,.docx"><button class="btn-primary" id="parseBtn">🔍 Parse & Auto-Fill</button><div id="parse-result"></div></div></div>
        <div id="create-job-view" style="display:none;"><div class="card no-click"><h3>➕ Create Job</h3><form id="jobForm"><input type="text" id="job-title" placeholder="Job Title *" required><input type="text" id="job-company" placeholder="Company"><textarea id="job-desc" rows="5" placeholder="Job Description"></textarea><button type="submit" class="btn-primary">Create Job</button></form></div></div>
        <div id="analyze-view" style="display:none;"><div class="card no-click"><h3>🔍 AI Match Analysis</h3><div class="flex"><div class="flex-1"><select id="analyze-job-select"></select></div><div class="flex-1"><select id="analyze-candidate-select"></select></div></div><button class="btn-primary" id="analyzeBtn">🤖 Run DeepSeek Analysis</button><div id="analyze-result"></div></div></div>
    </div>
</div>

<!-- Candidate Modal -->
<div id="candidateModal" class="modal">
    <div class="modal-content">
        <div class="modal-header"><h2 id="modalTitle">Candidate Profile</h2><span class="close" onclick="closeModal()">&times;</span></div>
        <div class="modal-body" id="modalBody">Loading...</div>
    </div>
</div>

<script>
    let jobsData = [], candidatesData = [], currentCandidateId = null;
    
    function switchTab(tabId) {
        document.querySelectorAll('[id$="-view"]').forEach(el => el.style.display = 'none');
        document.getElementById(tabId + '-view').style.display = 'block';
        document.querySelectorAll('.nav-item').forEach(item => item.classList.remove('active'));
        document.querySelector(`.nav-item[data-tab="${tabId}"]`).classList.add('active');
        if (tabId === 'jobs') loadJobs();
        if (tabId === 'candidates') loadCandidates();
        if (tabId === 'analyze') { loadJobs(); loadCandidates(); }
    }
    
    async function loadJobs() {
        const res = await fetch('/api/jobs');
        jobsData = await res.json();
        const container = document.getElementById('jobs-list');
        if (!jobsData.length) { container.innerHTML = '<div class="card no-click">No jobs yet</div>'; return; }
        container.innerHTML = jobsData.map(job => `<div class="card no-click"><h3>${escapeHtml(job.title)}</h3>${job.company ? `<p>🏢 ${escapeHtml(job.company)}</p>` : ''}<small>📅 ${new Date(job.created_at).toLocaleDateString()}</small></div>`).join('');
        document.getElementById('analyze-job-select').innerHTML = '<option value="">-- Select Job --</option>' + jobsData.map(j => `<option value="${j.id}">${escapeHtml(j.title)}</option>`).join('');
    }
    
    async function loadCandidates() {
        const res = await fetch('/api/candidates');
        candidatesData = await res.json();
        renderCandidateList(candidatesData);
        document.getElementById('analyze-candidate-select').innerHTML = '<option value="">-- Select Candidate --</option>' + candidatesData.map(c => `<option value="${c.id}">${escapeHtml(c.first_name + ' ' + c.last_name || 'Unknown')}</option>`).join('');
    }
    
    function renderCandidateList(candidates) {
        const container = document.getElementById('candidates-list');
        if (!candidates.length) { container.innerHTML = '<div class="card no-click">No candidates yet</div>'; return; }
        container.innerHTML = candidates.map(c => {
            const fullName = `${c.first_name || ''} ${c.last_name || ''}`.trim() || 'Unknown';
            const skills = c.core_skills ? JSON.parse(c.core_skills || '[]') : [];
            return `<div class="card" onclick="viewCandidate(${c.id})"><h3>👤 ${escapeHtml(fullName)}</h3>${c.email ? `<p>📧 ${escapeHtml(c.email)}</p>` : ''}<p>🔧 ${skills.slice(0,3).map(s => `<span class="skill-tag">${escapeHtml(s.skill)}</span>`).join('')}</p>${c.match_score ? `<p>🎯 Score: <span class="${c.match_score >= 70 ? 'match-high' : (c.match_score >= 40 ? 'match-medium' : 'match-low')}">${c.match_score}%</span></p>` : ''}<small>📅 ${new Date(c.created_at).toLocaleDateString()}</small></div>`;
        }).join('');
    }
    
    function filterCandidates() {
        const term = document.getElementById('candidate-search').value.toLowerCase();
        const filtered = candidatesData.filter(c => {
            const name = `${c.first_name || ''} ${c.last_name || ''}`.toLowerCase();
            const skills = c.core_skills ? JSON.parse(c.core_skills).map(s => s.skill.toLowerCase()).join(' ') : '';
            return name.includes(term) || skills.includes(term);
        });
        renderCandidateList(filtered);
    }
    
    function clearSearch() { document.getElementById('candidate-search').value = ''; renderCandidateList(candidatesData); }
    
    async function viewCandidate(id) {
        const c = candidatesData.find(c => c.id == id);
        if (!c) return;
        
        const fullName = `${c.first_name || ''} ${c.middle_name || ''} ${c.last_name || ''}`.trim();
        const workExp = JSON.parse(c.work_experience || '[]');
        const certs = JSON.parse(c.certifications || '[]');
        const skills = JSON.parse(c.core_skills || '[]');
        
        const docRes = await fetch(`/api/candidates/${id}/documents`);
        const documents = await docRes.json();
        const resumeDoc = documents.find(d => d.is_resume === 1);
        const otherDocs = documents.filter(d => !d.is_resume);
        
        document.getElementById('modalBody').innerHTML = `
            <div style="display: flex; gap: 10px; justify-content: flex-end; margin-bottom: 15px;">
                <button class="btn-primary" onclick="openEditForm(${id})">✏️ Edit Profile</button>
                <button class="btn-secondary" onclick="copyAllDetails()">📋 Copy All</button>
            </div>
            <div class="detail-row"><div class="detail-label">Full Name:</div><div class="detail-value">${escapeHtml(fullName)}</div></div>
            <div class="detail-row"><div class="detail-label">Phone:</div><div class="detail-value">${escapeHtml(c.phone || 'N/A')}</div></div>
            <div class="detail-row"><div class="detail-label">Email:</div><div class="detail-value">${escapeHtml(c.email || 'N/A')}</div></div>
            <div class="detail-row"><div class="detail-label">Address:</div><div class="detail-value">${escapeHtml(c.address || 'N/A')}</div></div>
            <div class="detail-row"><div class="detail-label">LinkedIn:</div><div class="detail-value">${escapeHtml(c.linkedin || 'N/A')}</div></div>
            <div class="detail-row"><div class="detail-label">Current Role:</div><div class="detail-value">${escapeHtml(c.current_role || 'N/A')}</div></div>
            <div class="detail-row"><div class="detail-label">Status:</div><div class="detail-value">${escapeHtml(c.employment_status || 'N/A')}${c.notice_period_days ? ` (${c.notice_period_days} days)` : ''}</div></div>
            
            <h4 style="margin-top: 20px;">💼 Work Experience</h4>
            ${workExp.map(w => `<div class="company-item"><strong>${escapeHtml(w.company)}</strong> — ${escapeHtml(w.role)}<br><small>${escapeHtml(w.start_date || '')} - ${escapeHtml(w.end_date || 'Present')}</small></div>`).join('') || '<p>None</p>'}
            
            <h4>⭐ Core Skills</h4>
            ${skills.map(s => `<span class="skill-tag">${escapeHtml(s.skill)} (${s.years_of_experience || '?'} yrs)</span>`).join('') || '<p>None</p>'}
            
            <h4>📜 Certifications</h4>
            ${certs.map(cert => `<div>📜 ${escapeHtml(cert)}</div>`).join('') || '<p>None</p>'}
            
            <h4>🎓 Education</h4>
            <p>${escapeHtml(c.education || 'N/A')}</p>
            
            <h4>📄 Resume</h4>
            ${resumeDoc ? `<div><a href="/api/documents/${resumeDoc.id}" target="_blank">📄 ${escapeHtml(resumeDoc.original_filename)}</a> <span style="background:#1B6B2E; color:white; padding:2px 8px; border-radius:12px; font-size:10px;">Original Resume</span></div>` : '<p>No resume attached</p>'}
            
            <h4>📎 Other Documents (${otherDocs.length})</h4>
            ${otherDocs.map(d => `<div><a href="/api/documents/${d.id}" target="_blank">📄 ${escapeHtml(d.original_filename)}</a></div>`).join('') || '<p>No additional documents</p>'}
            
            <button class="btn-primary" onclick="closeModal()" style="margin-top: 20px;">Close</button>
        `;
        document.getElementById('candidateModal').style.display = 'block';
    }
    
    function openEditForm(id) {
        window.location.href = `/edit-candidate/${id}`;
    }
    
    function copyAllDetails() {
        let text = '';
        document.querySelectorAll('#modalBody .detail-row, #modalBody h4, #modalBody .company-item, #modalBody .skill-tag').forEach(el => {
            text += el.innerText + '\n';
        });
        navigator.clipboard.writeText(text);
        alert('Copied to clipboard!');
    }
    
    function closeModal() { document.getElementById('candidateModal').style.display = 'none'; }
    
    document.getElementById('parseBtn').onclick = async () => {
        const file = document.getElementById('resume-file').files[0];
        if (!file) return alert('Select a file');
        const fd = new FormData(); fd.append('resume', file);
        const div = document.getElementById('parse-result');
        div.innerHTML = '<div class="spinner"></div>';
        try {
            const res = await fetch('/api/parse-resume-detailed', { method: 'POST', body: fd });
            const result = await res.json();
            if (result.error) { div.innerHTML = `<div class="alert-error">${result.error}</div>`; return; }
            div.innerHTML = `<div class="alert-success"><h4>✅ Parsed</h4><p>${escapeHtml(result.first_name || '')} ${escapeHtml(result.last_name || '')}</p><button class="btn-primary" id="saveDetailedBtn">Save Candidate</button></div>`;
            document.getElementById('saveDetailedBtn').onclick = async () => {
                const saveRes = await fetch('/api/candidates/detailed', { method: 'POST', headers: {'Content-Type':'application/json'}, body: JSON.stringify(result) });
                if (saveRes.ok) { alert('Saved!'); div.innerHTML = ''; document.getElementById('resume-file').value = ''; loadCandidates(); }
                else alert('Error');
            };
        } catch(e) { div.innerHTML = '<div class="alert-error">Error</div>'; }
    };
    
    document.getElementById('analyzeBtn').onclick = async () => {
        const jobId = document.getElementById('analyze-job-select').value;
        const candidateId = document.getElementById('analyze-candidate-select').value;
        if (!jobId || !candidateId) return alert('Select both');
        const job = jobsData.find(j => j.id == jobId);
        const cand = candidatesData.find(c => c.id == candidateId);
        const div = document.getElementById('analyze-result');
        div.innerHTML = '<div class="spinner"></div><p>🤖 Running DeepSeek analysis...</p>';
        try {
            const res = await fetch('/api/analyze-match', { method: 'POST', headers: {'Content-Type':'application/json'}, body: JSON.stringify({ job_id: jobId, candidate_id: candidateId, jd_text: job.description || '', resume_text: cand.resume_text || '' }) });
            const result = await res.json();
            if (result.error) { div.innerHTML = `<div class="alert-error">${result.error}</div>`; return; }
            const matchClass = result.match_score >= 70 ? 'match-high' : (result.match_score >= 40 ? 'match-medium' : 'match-low');
            div.innerHTML = `<div class="alert-success"><h4>📊 DeepSeek Analysis Complete</h4><p>🎯 Match Score: <span class="${matchClass}">${result.match_score || 0}%</span></p><p>📌 Recommendation: ${result.recommendation || 'Review'}</p><div class="alert-info" style="margin-top:10px;"><strong>📝 ${result.executive_summary?.final_verdict || ''}</strong></div>${result.pre_screening_questions ? `<div style="margin-top:10px;"><strong>📋 Pre-screening Questions:</strong><ul>${result.pre_screening_questions.map(q => `<li>${escapeHtml(q)}</li>`).join('')}</ul></div>` : ''}<small>✅ Analysis saved</small></div>`;
            loadCandidates();
        } catch(e) { div.innerHTML = '<div class="alert-error">Analysis failed</div>'; }
    };
    
    window.exportToCSV = function() { window.location.href = '/api/export-candidates'; };
    
    document.getElementById('jobForm').onsubmit = async (e) => {
        e.preventDefault();
        const data = { title: document.getElementById('job-title').value, company: document.getElementById('job-company').value, description: document.getElementById('job-desc').value };
        if (!data.title) return alert('Title required');
        const res = await fetch('/api/jobs', { method: 'POST', headers: {'Content-Type':'application/json'}, body: JSON.stringify(data) });
        if (res.ok) { alert('Job created'); document.getElementById('job-title').value = ''; document.getElementById('job-company').value = ''; document.getElementById('job-desc').value = ''; switchTab('jobs'); loadJobs(); }
        else alert('Error');
    };
    
    function escapeHtml(str) { if (!str) return ''; const div = document.createElement('div'); div.textContent = str; return div.innerHTML; }
    
    document.querySelectorAll('.nav-item').forEach(item => item.addEventListener('click', () => switchTab(item.getAttribute('data-tab'))));
    loadJobs(); loadCandidates();
</script>
</body>
</html>
'''

# ============ API ROUTES ============
@app.route('/')
def index():
    return render_template_string(HTML_TEMPLATE, groq_enabled=GROQ_ENABLED, deepseek_enabled=DEEPSEEK_ENABLED)

@app.route('/api/parse-resume-detailed', methods=['POST'])
def parse_resume_detailed_api():
    if 'resume' not in request.files:
        return jsonify({'error': 'No file'}), 400
    file = request.files['resume']
    if file.filename == '':
        return jsonify({'error': 'No file'}), 400
    
    filename = secure_filename(file.filename)
    original_filename = file.filename
    filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
    file.save(filepath)
    
    if filename.endswith('.pdf'):
        text = extract_text_from_pdf(filepath)
    else:
        text = extract_text_from_docx(filepath)
    
    if not text:
        os.remove(filepath)
        return jsonify({'error': 'Could not extract text'}), 400
    
    parsed = parse_resume_with_ai(text)
    if parsed and parsed.get('first_name'):
        parsed['resume_text'] = text[:3000]
        parsed['resume_filename'] = original_filename
        parsed['ai_used'] = True
        parsed['file_path'] = filepath
        parsed['original_filename'] = original_filename
        return jsonify(parsed)
    else:
        fallback = fallback_parse_resume(text)
        fallback['resume_text'] = text[:3000]
        fallback['resume_filename'] = original_filename
        fallback['ai_used'] = False
        fallback['file_path'] = filepath
        fallback['original_filename'] = original_filename
        return jsonify(fallback)

@app.route('/api/candidates/detailed', methods=['POST'])
def create_candidate_detailed():
    data = request.json
    conn = sqlite3.connect('shahnai.db')
    c = conn.cursor()
    c.execute('''INSERT INTO candidates 
        (first_name, last_name, middle_name, phone, email, address, linkedin, other_social,
         current_role, employment_status, notice_period_days, work_experience, certifications,
         core_skills, education, resume_text, resume_filename)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)''',
        (data.get('first_name'), data.get('last_name'), data.get('middle_name'),
         data.get('phone'), data.get('email'), data.get('address'), data.get('linkedin'), data.get('other_social'),
         data.get('current_role'), data.get('employment_status'), data.get('notice_period_days', 0),
         json.dumps(data.get('work_experience', [])), json.dumps(data.get('certifications', [])),
         json.dumps(data.get('core_skills', [])), data.get('education'), data.get('resume_text'), data.get('resume_filename')))
    
    candidate_id = c.lastrowid
    
    file_path = data.get('file_path')
    original_filename = data.get('original_filename')
    
    if file_path and os.path.exists(file_path):
        permanent_filename = secure_filename(f"{candidate_id}_{datetime.now().timestamp()}_{original_filename}")
        permanent_path = os.path.join(app.config['DOCUMENTS_FOLDER'], permanent_filename)
        shutil.move(file_path, permanent_path)
        
        c.execute('INSERT INTO candidate_documents (candidate_id, filename, original_filename, file_path, file_type, is_resume) VALUES (?, ?, ?, ?, ?, ?)',
                  (candidate_id, permanent_filename, original_filename, permanent_path, original_filename.split('.')[-1], 1))
    
    conn.commit()
    conn.close()
    return jsonify({'message': 'Candidate saved', 'id': candidate_id})

@app.route('/api/candidates', methods=['GET'])
def get_candidates():
    conn = sqlite3.connect('shahnai.db')
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    c.execute('SELECT * FROM candidates ORDER BY created_at DESC')
    candidates = [dict(row) for row in c.fetchall()]
    conn.close()
    return jsonify(candidates)

@app.route('/api/candidates/<int:candidate_id>', methods=['PUT'])
def update_candidate(candidate_id):
    data = request.json
    conn = sqlite3.connect('shahnai.db')
    c = conn.cursor()
    c.execute('''UPDATE candidates SET 
        first_name=?, middle_name=?, last_name=?, email=?, phone=?, address=?, linkedin=?,
        current_role=?, employment_status=?, notice_period_days=?, education=?,
        work_experience=?, certifications=?, core_skills=?
        WHERE id=?''',
        (data.get('first_name'), data.get('middle_name'), data.get('last_name'),
         data.get('email'), data.get('phone'), data.get('address'), data.get('linkedin'),
         data.get('current_role'), data.get('employment_status'), data.get('notice_period_days', 0),
         data.get('education'), data.get('work_experience'), data.get('certifications'),
         data.get('core_skills'), candidate_id))
    conn.commit()
    conn.close()
    return jsonify({'message': 'Candidate updated'})

@app.route('/api/candidates/<int:candidate_id>/documents', methods=['GET'])
def get_candidate_documents(candidate_id):
    conn = sqlite3.connect('shahnai.db')
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    c.execute('SELECT * FROM candidate_documents WHERE candidate_id = ? ORDER BY is_resume DESC, uploaded_at DESC', (candidate_id,))
    docs = [dict(row) for row in c.fetchall()]
    conn.close()
    return jsonify(docs)

@app.route('/api/documents/<int:doc_id>', methods=['GET'])
def get_document(doc_id):
    conn = sqlite3.connect('shahnai.db')
    c = conn.cursor()
    c.execute('SELECT * FROM candidate_documents WHERE id = ?', (doc_id,))
    doc = c.fetchone()
    conn.close()
    if doc and os.path.exists(doc[4]):
        return send_file(doc[4], as_attachment=False, download_name=doc[3])
    return jsonify({'error': 'File not found'}), 404

@app.route('/api/jobs', methods=['GET'])
def get_jobs():
    conn = sqlite3.connect('shahnai.db')
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    c.execute('SELECT * FROM jobs ORDER BY created_at DESC')
    jobs = [dict(row) for row in c.fetchall()]
    conn.close()
    return jsonify(jobs)

@app.route('/api/jobs', methods=['POST'])
def create_job():
    data = request.json
    conn = sqlite3.connect('shahnai.db')
    c = conn.cursor()
    c.execute('INSERT INTO jobs (title, company, description) VALUES (?, ?, ?)',
              (data.get('title'), data.get('company'), data.get('description', '')))
    conn.commit()
    conn.close()
    return jsonify({'message': 'Job created'})

@app.route('/api/analyze-match', methods=['POST'])
def analyze_match():
    data = request.json
    resume_text = data.get('resume_text', '')
    jd_text = data.get('jd_text', '')
    candidate_id = data.get('candidate_id')
    
    if not resume_text or not jd_text:
        return jsonify({'error': 'Missing text'}), 400
    
    result = analyze_with_deepseek(resume_text, jd_text)
    
    if not result:
        result = quick_match_with_groq(resume_text, jd_text)
    
    if result and candidate_id:
        detailed_json = json.dumps(result, indent=2)
        conn = sqlite3.connect('shahnai.db')
        c = conn.cursor()
        c.execute('UPDATE candidates SET match_score = ?, recommendation = ?, detailed_analysis = ? WHERE id = ?',
                  (result.get('match_score', 0), result.get('recommendation', 'review'), detailed_json, candidate_id))
        conn.commit()
        conn.close()
        return jsonify(result)
    
    return jsonify({'error': 'Analysis failed. Check API keys.'}), 500

@app.route('/api/export-candidates', methods=['GET'])
def export_candidates():
    conn = sqlite3.connect('shahnai.db')
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    c.execute('SELECT id, first_name, last_name, email, phone, current_role, match_score, created_at FROM candidates ORDER BY created_at DESC')
    rows = c.fetchall()
    conn.close()
    
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(['ID', 'First Name', 'Last Name', 'Email', 'Phone', 'Current Role', 'Match Score (%)', 'Created Date'])
    
    for row in rows:
        writer.writerow([
            row['id'], row['first_name'] or '', row['last_name'] or '',
            row['email'] or '', row['phone'] or '', row['current_role'] or '',
            row['match_score'] or 0, row['created_at']
        ])
    
    output.seek(0)
    return Response(output.getvalue(), mimetype='text/csv', headers={'Content-Disposition': 'attachment; filename=candidates_export.csv'})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
