# routes/export.py
import io
import csv
from flask import Blueprint, Response
from models.database import get_candidates

export_bp = Blueprint('export', __name__)

@export_bp.route('/export-candidates', methods=['GET'])
def export_candidates():
    candidates = get_candidates()
    
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(['ID', 'First Name', 'Last Name', 'Email', 'Phone', 'Current Role', 'Match Score', 'Created Date'])
    
    for cand in candidates:
        writer.writerow([cand['id'], cand['first_name'] or '', cand['last_name'] or '',
                         cand['email'] or '', cand['phone'] or '', cand['current_role'] or '',
                         cand['match_score'] or 0, cand['created_at']])
    
    output.seek(0)
    return Response(output.getvalue(), mimetype='text/csv', 
                   headers={'Content-Disposition': 'attachment; filename=candidates.csv'})
