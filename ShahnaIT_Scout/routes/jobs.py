# routes/jobs.py
from flask import Blueprint, request, jsonify
from models.database import get_jobs, create_job

# Create the Blueprint
jobs_bp = Blueprint('jobs', __name__)

@jobs_bp.route('/jobs', methods=['GET'])
def get_all_jobs():
    jobs = get_jobs()
    return jsonify(jobs)

@jobs_bp.route('/jobs', methods=['POST'])
def add_job():
    data = request.json
    create_job(data.get('title'), data.get('company'), data.get('description', ''))
    return jsonify({'message': 'Job created'})
