# routes/offers.py
# Offer letter generation routes

from flask import jsonify, request
from datetime import datetime, timedelta

# Global references
offers = []
applications = []
candidates = []

def init_offers_routes(app, offers_ref, applications_ref, candidates_ref, email_service):
    """Initialize offers routes with references to data stores"""
    global offers, applications, candidates
    offers = offers_ref
    applications = applications_ref
    candidates = candidates_ref
    
    def generate_offer_code():
        return f"OFF-{len(offers) + 1:04d}"
    
    def generate_offer_html(candidate_name, job_title, base_salary, joining_date):
        """Generate HTML offer letter"""
        salary_formatted = f"${base_salary:,.2f}" if base_salary else "TBD"
        
        return f'''<!DOCTYPE html>
<html>
<head>
    <title>Offer Letter - {candidate_name}</title>
    <style>
        body {{ font-family: Arial, sans-serif; margin: 50px; }}
        .container {{ max-width: 800px; margin: auto; background: white; padding: 40px; border-radius: 10px; }}
        .header {{ text-align: center; border-bottom: 2px solid #4caf50; padding-bottom: 20px; }}
        .content {{ margin: 30px 0; }}
        .signature {{ margin-top: 50px; }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>ShahnaIT Scout</h1>
            <h2>Offer of Employment</h2>
        </div>
        <div class="content">
            <p>Dear <strong>{candidate_name}</strong>,</p>
            <p>We are pleased to offer you the position of <strong>{job_title}</strong> at ShahnaIT Scout.</p>
            
            <h3>Offer Details</h3>
            <table style="width:100%; border-collapse: collapse;">
                <tr><td style="padding: 10px; border-bottom: 1px solid #ddd;"><strong>Position</strong></td><td style="padding: 10px; border-bottom: 1px solid #ddd;">{job_title}</td></tr>
                <tr><td style="padding: 10px; border-bottom: 1px solid #ddd;"><strong>Base Salary</strong></td><td style="padding: 10px; border-bottom: 1px solid #ddd;">{salary_formatted} per year</td></tr>
                <tr><td style="padding: 10px; border-bottom: 1px solid #ddd;"><strong>Joining Date</strong></td><td style="padding: 10px; border-bottom: 1px solid #ddd;">{joining_date}</td></tr>
            </table>
            
            <p>We look forward to having you on our team!</p>
        </div>
        <div class="signature">
            <p>Sincerely,<br><strong>ShahnaIT Recruitment Team</strong></p>
        </div>
    </div>
</body>
</html>'''
    
    @app.route('/api/offers', methods=['GET', 'POST'])
    def manage_offers():
        global offers
        
        if request.method == 'POST':
            data = request.get_json()
            
            # Find application if provided
            application = None
            if data.get('application_id'):
                application = next((a for a in applications if a['id'] == data.get('application_id')), None)
            
            joining_date = data.get('joining_date', (datetime.now().date() + timedelta(days=15)).isoformat())
            
            offer = {
                'id': len(offers) + 1,
                'offer_code': generate_offer_code(),
                'application_id': data.get('application_id'),
                'candidate_name': data.get('candidate_name'),
                'candidate_email': data.get('candidate_email'),
                'job_title': data.get('job_title'),
                'base_salary': data.get('base_salary'),
                'joining_bonus': data.get('joining_bonus', 0),
                'joining_date': joining_date,
                'status': 'draft',
                'created_at': datetime.now().isoformat(),
                'offer_html': generate_offer_html(
                    data.get('candidate_name'),
                    data.get('job_title'),
                    data.get('base_salary', 0),
                    joining_date
                )
            }
            offers.append(offer)
            
            # Update application status
            if application:
                application['status'] = 'offered'
            
            return jsonify({
                'success': True,
                'offer_id': offer['id'],
                'offer_code': offer['offer_code'],
                'offer_html': offer['offer_html']
            })
        
        return jsonify(offers)
    
    @app.route('/api/offers/<int:offer_id>/send', methods=['POST'])
    def send_offer(offer_id):
        """Send offer letter to candidate via email"""
        offer = next((o for o in offers if o['id'] == offer_id), None)
        if not offer:
            return jsonify({'error': 'Offer not found'}), 404
        
        offer['status'] = 'sent'
        offer['sent_at'] = datetime.now().isoformat()
        
        # Send email
        email_service.send_offer_email(
            offer.get('candidate_name'),
            offer.get('candidate_email'),
            offer.get('job_title'),
            offer.get('base_salary', 0),
            offer.get('joining_date', 'TBD')
        )
        
        return jsonify({'success': True, 'message': 'Offer sent successfully'})
