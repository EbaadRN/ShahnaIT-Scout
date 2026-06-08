# app.py - MINIMAL TEST VERSION (Just to check buttons)
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

init_db()
os.makedirs('/tmp/candidate_docs', exist_ok=True)

app.register_blueprint(candidates_bp, url_prefix='/api')
app.register_blueprint(jobs_bp, url_prefix='/api')
app.register_blueprint(analyze_bp, url_prefix='/api')
app.register_blueprint(export_bp, url_prefix='/api')
app.register_blueprint(documents_bp, url_prefix='/api')

HTML_TEMPLATE = '''
<!DOCTYPE html>
<html>
<head>
    <title>ShahnaIT Scout</title>
    <style>
        body { font-family: Arial; background: #F5F0E8; margin: 0; padding: 20px; }
        .header { background: #1A4D4A; color: white; padding: 20px; border-radius: 10px; margin-bottom: 20px; }
        button { background: #1A4D4A; color: white; border: none; padding: 10px 20px; margin: 5px; cursor: pointer; border-radius: 8px; }
        button:hover { background: #2A6B67; }
        .tab-btn { background: white; color: #1A4D4A; border: 1px solid #1A4D4A; padding: 10px 20px; margin: 5px; cursor: pointer; border-radius: 8px; }
        .tab-btn.active { background: #1A4D4A; color: white; }
        .card { background: white; padding: 15px; margin: 10px 0; border-radius: 8px; border-left: 4px solid #1A4D4A; }
        .flex { display: flex; gap: 10px; }
        .flex-1 { flex: 1; }
    </style>
</head>
<body>
<div style="max-width: 1000px; margin: 0 auto;">
    <div class="header">
        <h1>🎯 ShahnaIT Scout - TEST</h1>
        <p>Testing button functionality</p>
    </div>
    
    <div>
        <button class="tab-btn active" id="testBtn1">Test Button 1</button>
        <button class="tab-btn" id="testBtn2">Test Button 2</button>
        <button class="tab-btn" id="testBtn3">Test Button 3</button>
    </div>
    
    <div id="result" style="margin-top:20px; padding:15px; background:white; border-radius:8px;">
        Click a button above
    </div>
</div>

<script>
    document.getElementById('testBtn1').onclick = function() {
        document.getElementById('result').innerHTML = '✅ Test Button 1 CLICKED!';
    };
    document.getElementById('testBtn2').onclick = function() {
        document.getElementById('result').innerHTML = '✅ Test Button 2 CLICKED!';
    };
    document.getElementById('testBtn3').onclick = function() {
        document.getElementById('result').innerHTML = '✅ Test Button 3 CLICKED!';
    };
</script>
</body>
</html>
'''

@app.route('/')
def index():
    return HTML_TEMPLATE

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
