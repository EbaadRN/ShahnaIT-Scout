# routes/candidates.py
import os
import json
from flask import Blueprint, request, jsonify
from models.database import get_candidates, create_candidate, update_candidate, add_document, get_documents
from services.resume_parser import extract_text_from_pdf, extract_text_from_docx, fallback_parse_resume
from services.groq_service import parse_resume_with_groq
from werkzeug.utils import secure_filename
from datetime import datetime
import shutil

candidates_bp = Blueprint('candidates', __name__)

UPLOAD_FOLDER = '/tmp'
DOCUMENTS_FOLDER = '/tmp/candidate_docs'

@candidates_bp.route('/candidates', methods=['GET'])
def get_all_candidates():
    candidates = get_candidates()
    return jsonify(candidates)

@candidates_bp.route('/candidates', methods=['POST'])
def add_candidate():
    data = request.json
    candidate_id = create_candidate(data)
    
    file_path = data.get('file_path')
    original_filename = data.get('original_filename')
    
    if file_path and os.path.exists(file_path):
        permanent_filename = secure_filename(f"{candidate_id}_{datetime.now().timestamp()}_{original_filename}")
        permanent_path = os.path.join(DOCUMENTS_FOLDER, permanent_filename)
        shutil.move(file_path, permanent_path)
        add_document(candidate_id, permanent_filename, original_filename, permanent_path, 
                    original_filename.split('.')[-1], 1)
    
    return jsonify({'message': 'Candidate saved', 'id': candidate_id})

@candidates_bp.route('/candidates/<int:candidate_id>', methods=['PUT'])
def update_candidate_info(candidate_id):
    data = request.json
    update_candidate(candidate_id, data)
    return jsonify({'message': 'Candidate updated'})

@candidates_bp.route('/candidates/<int:candidate_id>/documents', methods=['GET'])
def get_candidate_documents(candidate_id):
    docs = get_documents(candidate_id)
    return jsonify(docs)

@candidates_bp.route('/parse-resume', methods=['POST'])
def parse_resume():
    if 'resume' not in request.files:
        return jsonify({'error': 'No file'}), 400
    file = request.files['resume']
    if file.filename == '':
        return jsonify({'error': 'No file'}), 400
    
    filename = secure_filename(file.filename)
    original_filename = file.filename
    temp_filepath = os.path.join(UPLOAD_FOLDER, filename)
    file.save(temp_filepath)
    
    if filename.endswith('.pdf'):
        text = extract_text_from_pdf(temp_filepath)
    else:
        text = extract_text_from_docx(temp_filepath)
    
    if not text:
        os.remove(temp_filepath)
        return jsonify({'error': 'Could not extract text'}), 400
    
    # Try Groq first
    parsed = parse_resume_with_groq(text)
    if parsed and parsed.get('first_name'):
        parsed['resume_text'] = text[:3000]
        parsed['ai_used'] = True
    else:
        parsed = fallback_parse_resume(text)
        parsed['ai_used'] = False
    
    parsed['file_path'] = temp_filepath
    parsed['original_filename'] = original_filename
    
    return jsonify(parsed)
