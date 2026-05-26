from flask import Flask, jsonify, request, render_template_string
from datetime import datetime
import os

app = Flask(__name__)

# Simple HTML template as a string (so no file needed!)
HTML_TEMPLATE = '''
<!DOCTYPE html>
<html>
<head>
    <title>ShahnaIT Scout</title>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.1.3/dist/css/bootstrap.min.css" rel="stylesheet">
</head>
<body>
    <div class="container mt-5">
        <h1>🚀 ShahnaIT Scout</h1>
        <p class="text-success">✅ Application is running successfully!</p>
        <hr>
        
        <div class="row">
            <div class="col-md-4">
                <div class="card">
                    <div class="card-body">
                        <h5>Open Positions</h5>
                        <h2 id="openPos">0</h2>
                    </div>
                </div>
            </div>
            <div class="col-md-4">
                <div class="card">
                    <div class="card-body">
                        <h5>Total Candidates</h5>
                        <h2 id="totalCand">0</h2>
                    </div>
                </div>
            </div>
            <div class="col-md-4">
                <div class="card">
                    <div class="card-body">
                        <h5>Applications</h5>
                        <h2 id="totalApps">0</h2>
                    </div>
                </div>
            </div>
        </div>
        
        <div class="mt-4">
            <button class="btn btn-primary" onclick="createJob()">Create Job</button>
            <button class="btn btn-success" onclick="createCandidate()">Add Candidate</button>
        </div>
        
        <div class="mt-4" id="result"></div>
    </div>
    
    <script>
        async function loadStats() {
            const res = await fetch('/api/dashboard/stats');
            const data = await res.json();
            document.getElementById('openPos').innerText = data.overview.open_positions;
            document.getElementById('totalCand').innerText = data.overview.total_candidates;
            document.getElementById('totalApps').innerText = data.overview.total_applications;
        }
        
        async function createJob() {
            const title = prompt("Enter Job Title:");
            if(title) {
                const res = await fetch('/api/jds', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({title: title, location: "Remote"})
                });
                const result = await res.json();
                document.getElementById('result').innerHTML = `<div class="alert alert-success">Job created: ${result.jd_code}</div>`;
                loadStats();
            }
        }
        
        async function createCandidate() {
            const name = prompt("Enter Candidate Name:");
            const email = prompt("Enter Email:");
            if(name && email) {
                const res = await fetch('/api/candidates', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({first_name: name, email: email})
                });
                const result = await res.json();
                document.getElementById('result').innerHTML = `<div class="alert alert-success">Candidate added: ${result.candidate_code}</div>`;
                loadStats();
            }
        }
        
        loadStats();
        setInterval(loadStats, 5000);
    </script>
</body>
</html>
'''

# In-memory storage
jobs = []
candidates = []
applications = []
next_id = 1

@app.route('/')
def index():
    return render_template_string(HTML_TEMPLATE)

@app.route('/api/dashboard/stats')
def dashboard_stats():
    return jsonify({
        'overview': {
            'open_positions': len([j for j in jobs if j.get('status') == 'open']),
            'total_candidates': len(candidates),
            'total_applications': len(applications),
            'interviews_today': 0,
            'offers_accepted': 0
        },
        'pipeline': {
            'new': len([a for a in applications if a.get('status') == 'new']),
            'shortlisted': 0,
            'interviewed': 0,
            'selected': 0,
            'rejected': 0
        },
        'recent_activities': [],
        'top_jds': []
    })

@app.route('/api/jds', methods=['GET', 'POST'])
def manage_jds():
    global next_id
    if request.method == 'POST':
        data = request.json
        job = {
            'id': next_id,
            'code': f"JD-{next_id:04d}",
            'title': data.get('title'),
            'location': data.get('location', 'Remote'),
            'status': 'open',
            'applications': 0,
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
        data = request.json
        candidate = {
            'id': next_id,
            'code': f"CAN-{next_id:04d}",
            'first_name': data.get('first_name'),
            'last_name': data.get('last_name', ''),
            'name': f"{data.get('first_name')} {data.get('last_name', '')}",
            'email': data.get('email'),
            'created_at': datetime.now().isoformat()
        }
        candidates.append(candidate)
        next_id += 1
        return jsonify({'success': True, 'candidate_id': candidate['id'], 'candidate_code': candidate['code']})
    
    page = int(request.args.get('page', 1))
    per_page = 20
    search = request.args.get('skill', '')
    
    filtered = candidates
    if search:
        filtered = [c for c in candidates if search.lower() in c.get('name', '').lower()]
    
    start = (page - 1) * per_page
    end = start + per_page
    paginated = filtered[start:end]
    
    return jsonify({
        'candidates': paginated,
        'total': len(filtered),
        'page': page,
        'pages': (len(filtered) + per_page - 1) // per_page
    })

@app.route('/api/applications', methods=['GET', 'POST'])
def manage_applications():
    if request.method == 'POST':
        data = request.json
        application = {
            'id': len(applications) + 1,
            'candidate_id': data.get('candidate_id'),
            'jd_id': data.get('jd_id'),
            'status': 'new',
            'application_date': datetime.now().date().isoformat()
        }
        applications.append(application)
        return jsonify({'success': True, 'application_id': application['id']})
    return jsonify(applications)

@app.route('/api/clients', methods=['GET'])
def get_clients():
    return jsonify([])

@app.route('/api/candidates/parse-resume', methods=['POST'])
def parse_resume():
    return jsonify({
        'success': True,
        'data': {
            'first_name': 'Sample',
            'last_name': 'Candidate',
            'email': 'sample@example.com',
            'phone': '1234567890'
        }
    })

@app.route('/health')
def health():
    return jsonify({'status': 'ok', 'timestamp': datetime.now().isoformat()})

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 8080))
    app.run(host='0.0.0.0', port=port, debug=False)
