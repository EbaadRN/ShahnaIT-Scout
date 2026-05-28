# services/email_service.py
# Handle email sending (interview invites, offers, rejections)

import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import os

# Email configuration from environment variables
SMTP_SERVER = os.environ.get('MAIL_SERVER', 'smtp.gmail.com')
SMTP_PORT = int(os.environ.get('MAIL_PORT', 587))
SMTP_USERNAME = os.environ.get('MAIL_USERNAME', '')
SMTP_PASSWORD = os.environ.get('MAIL_PASSWORD', '')
FROM_EMAIL = os.environ.get('MAIL_DEFAULT_SENDER', 'noreply@shahnaiT.com')

EMAIL_CONFIGURED = bool(SMTP_USERNAME and SMTP_PASSWORD)


def send_email(to_email, subject, body, html_body=None):
    """Send an email to a recipient"""
    if not EMAIL_CONFIGURED:
        print(f"Email not configured. Would send to {to_email}: {subject}")
        return False
    
    try:
        msg = MIMEMultipart('alternative')
        msg['From'] = FROM_EMAIL
        msg['To'] = to_email
        msg['Subject'] = subject
        
        # Attach plain text version
        msg.attach(MIMEText(body, 'plain'))
        
        # Attach HTML version if provided
        if html_body:
            msg.attach(MIMEText(html_body, 'html'))
        
        # Send email
        server = smtplib.SMTP(SMTP_SERVER, SMTP_PORT)
        server.starttls()
        server.login(SMTP_USERNAME, SMTP_PASSWORD)
        server.send_message(msg)
        server.quit()
        
        print(f"✅ Email sent to {to_email}")
        return True
        
    except Exception as e:
        print(f"❌ Email error: {e}")
        return False


def send_application_received_email(candidate_name, candidate_email, job_title, match_score):
    """Send application received confirmation to candidate"""
    subject = f"Application Received - {job_title}"
    body = f"""Dear {candidate_name},

Thank you for applying for the {job_title} position.

Your application has been received and is under review.
AI Match Score: {match_score}%

We will contact you soon regarding the next steps.

Best regards,
ShahnaIT Recruitment Team"""
    
    return send_email(candidate_email, subject, body)


def send_interview_invite_email(candidate_name, candidate_email, job_title, interviewer, scheduled_time, meeting_link):
    """Send interview invitation to candidate"""
    subject = f"Interview Invitation - {job_title}"
    body = f"""Dear {candidate_name},

We are pleased to invite you for an interview for the {job_title} position.

📅 Date & Time: {scheduled_time}
👤 Interviewer: {interviewer}
🔗 Meeting Link: {meeting_link}

Please join 5 minutes before the scheduled time.

Best regards,
ShahnaIT Recruitment Team"""
    
    return send_email(candidate_email, subject, body)


def send_rejection_email(candidate_name, candidate_email, job_title):
    """Send rejection email to candidate"""
    subject = f"Application Update - {job_title}"
    body = f"""Dear {candidate_name},

Thank you for your interest in the {job_title} position.

After careful review, we have decided to move forward with other candidates whose qualifications more closely match our requirements.

We appreciate your interest and wish you success in your job search.

Best regards,
ShahnaIT Recruitment Team"""
    
    return send_email(candidate_email, subject, body)


def send_offer_email(candidate_name, candidate_email, job_title, salary, joining_date):
    """Send offer letter notification to candidate"""
    subject = f"Offer Letter - {job_title}"
    body = f"""Dear {candidate_name},

We are pleased to offer you the position of {job_title} at ShahnaIT Scout.

📋 Offer Details:
- Position: {job_title}
- Base Salary: ${salary:,.2f} per year
- Joining Date: {joining_date}

Please review the attached offer letter and confirm your acceptance.

We look forward to having you on our team!

Best regards,
ShahnaIT Recruitment Team"""
    
    return send_email(candidate_email, subject, body)


def send_status_update_email(candidate_name, candidate_email, job_title, status):
    """Send status update email to candidate"""
    status_messages = {
        'shortlisted': "Congratulations! You have been shortlisted for the next round.",
        'interview': "Your interview has been scheduled. Check your dashboard for details.",
        'selected': "Congratulations! You have been selected for the position.",
        'rejected': "We regret to inform you that you have not been selected for this position."
    }
    
    message = status_messages.get(status, f"Your application status has been updated to: {status}")
    
    subject = f"Application Status Update - {job_title}"
    body = f"""Dear {candidate_name},

{message}

Please check your candidate portal for more details.

Best regards,
ShahnaIT Recruitment Team"""
    
    return send_email(candidate_email, subject, body)
