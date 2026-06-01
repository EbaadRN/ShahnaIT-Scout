from flask import Flask, render_template_string, jsonify, request
from datetime import datetime
import os

app = Flask(__name__)

DASHBOARD_TEMPLATE = '''
<!DOCTYPE html>
<html>
<head>
    <title>ShahnaIT Scout</title>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.1.3/dist/css/bootstrap.min.css" rel="stylesheet">
</head>
<body>
    <div class="container mt-5">
        <h1>ShahnaIT Scout</h1>
        <p class="text-success">Application is running!</p>
        <hr>
        <div class="row">
            <div class="col-md-4">
                <div class="card">
                    <div class="card-body">
                        <h5>Jobs</h5>
                        <p id="jobCount">0</p>
                        <button class="btn btn-primary" onclick="createJob()">Create Job</button>
                    </div>
                </div>
            </div>
            <div class="col-md-4">
                <div class="card">
                    <div class="card-body">
                        <h5>Candidates</h5>
                        <p id="candidateCount">0</p>
                        <button class="btn btn-success" onclick="createCandidate()">Add Candidate</button>
                    </div>
                </div>
            </div>
        </div>
    </div>
    <script>
        async function createJob() {
            let title = prompt("Enter Job Title:");
            if(title) {
                let res = await fetch('/api/jobs', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({title: title})
                });
                let data = await res.json();
                if(data.success) alert('Job created!');
                loadStats();
            }
        }
        async function createCandidate() {
            let name = prompt("Enter Candidate Name:");
            let email = prompt("Enter Email:");
            if(name && email) {
                let res = await fetch('/api/candidates', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({name: name, email: email})
                });
                let data = await res.json();
                if(data.success) alert('Candidate added!');
                loadStats();
            }
        }
        async function loadStats() {
            let res = await fetch('/api/stats');
            let data = await res.json();
            document.getElementById('jobCount').innerText = data.jobs || 0;
            document.getElementById('candidateCount').innerText = data.candidates || 0;
        }
        loadStats();
    </script>
</body>
</html>
'''

jobs = []
candidates = []
next_id = 1

@app.route('/')
def index():
    return render_template_string(DASHBOARD_TEMPLATE)

@app.route('/api/stats')
def stats():
    return jsonify({'jobs': len(jobs), 'candidates': len(candidates)})

@app.route('/api/jobs', methods=['GET', 'POST'])
def manage_jobs():
    global next_id
    if request.method == 'POST':
        data = request.json
        job = {'id': next_id, 'title': data.get('title'), 'created_at': datetime.now().isoformat()}
        jobs.append(job)
        next_id += 1
        return jsonify({'success': True, 'job_id': job['id']})
    return jsonify(jobs)

@app.route('/api/candidates', methods=['GET', 'POST'])
def manage_candidates():
    global next_id
    if request.method == 'POST':
        data = request.json
        candidate = {'id': next_id, 'name': data.get('name'), 'email': data.get('email'), 'created_at': datetime.now().isoformat()}
        candidates.append(candidate)
        next_id += 1
        return jsonify({'success': True, 'candidate_id': candidate['id']})
    return jsonify(candidates)

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 8080))
    app.run(host='0.0.0.0', port=port, debug=False)
# ============= DATABASE MODELS =============
from flask_sqlalchemy import SQLAlchemy

app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///recruitment.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

class Job(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    location = db.Column(db.String(100))
    skills_required = db.Column(db.Text)
    status = db.Column(db.String(50), default='open')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class Candidate(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200), nullable=False)
    email = db.Column(db.String(100), unique=True)
    phone = db.Column(db.String(20))
    skills = db.Column(db.Text)
    current_role = db.Column(db.String(200))
    total_experience = db.Column(db.Float, default=0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class Application(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    candidate_id = db.Column(db.Integer, db.ForeignKey('candidate.id'))
    job_id = db.Column(db.Integer, db.ForeignKey('job.id'))
    match_score = db.Column(db.Float, default=0)
    status = db.Column(db.String(50), default='new')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
