# routes/documents.py
import os
import base64
from flask import Blueprint, request, jsonify, send_file
from services.resume_parser import extract_text_from_pdf, extract_text_from_docx
from models.database import get_document_by_id, add_document
from werkzeug.utils import secure_filename
from datetime import datetime

documents_bp = Blueprint('documents', __name__)

DOCUMENTS_FOLDER = '/tmp/candidate_docs'

@documents_bp.route('/candidates/upload-document', methods=['POST'])
def upload_document():
    candidate_id = request.form.get('candidate_id')
    if 'document' not in request.files:
        return jsonify({'error': 'No file'}), 400
    file = request.files['document']
    if file.filename == '':
        return jsonify({'error': 'No file'}), 400
    
    original_filename = file.filename
    filename = secure_filename(f"{candidate_id}_{datetime.now().timestamp()}_{file.filename}")
    filepath = os.path.join(DOCUMENTS_FOLDER, filename)
    file.save(filepath)
    
    add_document(candidate_id, filename, original_filename, filepath, 
                original_filename.split('.')[-1], 0)
    return jsonify({'message': 'Document uploaded'})

@documents_bp.route('/documents/<int:doc_id>/preview', methods=['GET'])
def preview_document(doc_id):
    doc = get_document_by_id(doc_id)
    if doc and os.path.exists(doc[4]):
        file_path = doc[4]
        file_type = doc[5]
        
        if file_type == 'pdf':
            text = extract_text_from_pdf(file_path)
            return jsonify({'type': 'text', 'content': text[:2000]})
        elif file_type == 'docx':
            text = extract_text_from_docx(file_path)
            return jsonify({'type': 'text', 'content': text[:2000]})
        elif file_type in ['png', 'jpg', 'jpeg']:
            with open(file_path, 'rb') as f:
                img_data = base64.b64encode(f.read()).decode('utf-8')
                return jsonify({'type': 'image', 'content': img_data})
    
    return jsonify({'error': 'File not found'}), 404

@documents_bp.route('/documents/<int:doc_id>', methods=['GET'])
def get_document(doc_id):
    doc = get_document_by_id(doc_id)
    if doc and os.path.exists(doc[4]):
        return send_file(doc[4], as_attachment=False, download_name=doc[3])
    return jsonify({'error': 'File not found'}), 404
