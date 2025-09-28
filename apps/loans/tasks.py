from celery import shared_task
from django.core.mail import EmailMultiAlternatives
from django.utils.html import strip_tags
from django.conf import settings
import logging

logger = logging.getLogger(__name__)

# Generic task to send an email
def build_html_template(content: str, title: str) -> str:
    """
    Generates a styled HTML email template.
    """
    return f"""
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
        <style>
            body {{ font-family: Arial, sans-serif; background-color: #f4f7fa; }}
            .card {{ border-radius: 10px; max-width: 600px; margin: 0 auto; }}
            .card-header {{ background-color: #007bff; padding: 1rem; }}
            .card-body {{ padding: 30px; background-color: #ffffff; }}
            .btn-view {{ 
                background-color: #4CAF50; 
                color: white; 
                padding: 12px 20px; 
                text-decoration: none; 
                border-radius: 5px; 
                font-size: 16px; 
                display: inline-block;
                transition: all 0.3s ease; 
                border: none;
            }}
            .btn-view:hover {{ 
                background-color: #218838; 
                transform: translateY(-2px); 
                box-shadow: 0 4px 8px rgba(0,0,0,0.2);
            }}
            .footer {{ font-size: 0.85rem; color: #6c757d; text-align: center; }}
        </style>
    </head>
    <body>
        <div class="container my-4">
            <div class="card shadow-sm">
                <div class="card-header text-white text-center">
                    <h3 class="mb-0">{title}</h3>
                </div>
                <div class="card-body">{content}</div>
                <div class="card-footer footer">
                    Pendeza Uganda - Loan Management System (LMS)
                </div>
            </div>
        </div>
    </body>
    </html>
    """


@shared_task
def send_email_task(subject, text_content, html_content, recipients):
    """
    Celery task to send an email asynchronously.
    """
    email = EmailMultiAlternatives(
        subject=subject,
        body=text_content,
        from_email=settings.EMAIL_HOST_USER,
        to=recipients,
    )
    email.attach_alternative(html_content, "text/html")
    try:
        email.send(fail_silently=False)
        logger.info(f"Email sent to {', '.join(recipients)}: {subject}")
        return True
    except Exception as e:
        logger.error(f"Failed to send email to {', '.join(recipients)}: {e}")
        return False

    

# Task to send loan application email
@shared_task
def send_loan_application_email_task(
    recipient_name, client_name, recipient_email, application_id, is_applicant=True
):
    applicant_dashboard_url = "https://sponsorwithpendeza.org/loans/applications/"
    officer_review_url = "https://sponsorwithpendeza.org/loans/applications/"
    subject = (
        "Your Loan Application Submitted"
        if is_applicant
        else "New Loan Application for Review"
    )

    if is_applicant:
        email_body = f"""
        <html>
        <body style="font-family: Arial, sans-serif; color: #333;">
            <div style="max-width: 600px; margin: auto; padding: 20px; border: 1px solid #ddd; border-radius: 10px;">
                <h2 style="color: #2E86C1; text-align: center;">Loan Application Submitted on Behalf of Client</h2>
                <p>Hello <strong>{recipient_name}</strong>,</p>
                <p>A loan application has been successfully submitted on behalf of <strong>{client_name}</strong>. The application ID is <strong>{application_id}</strong>. You can track the status of this application by clicking the button below:</p>
                <div style="text-align: center; margin: 20px 0;">
                    <a href="{applicant_dashboard_url}" style="background-color: #2E86C1; color: #fff; text-decoration: none; padding: 10px 20px; border-radius: 5px;">View Application Status</a>
                </div>
                <p>Thank you for assisting clients with their financial needs through Pendeza Uganda.</p>
                <p style="color: #888;">- Pendeza Uganda - Finance Department</p>
            </div>
        </body>
        </html>
        """
    else:
        email_body = f"""
        <html>
        <body style="font-family: Arial, sans-serif; color: #333;">
            <div style="max-width: 600px; margin: auto; padding: 20px; border: 1px solid #ddd; border-radius: 10px;">
                <h2 style="color: #C0392B; text-align: center;">Loan Application Approval Needed</h2>
                <p>Hello <strong>{recipient_name}</strong>,</p>
                <p>A new loan application with ID <strong>{application_id}</strong> is awaiting your review. Please review and process the application by clicking the button below:</p>
                <div style="text-align: center; margin: 20px 0;">
                    <a href="{officer_review_url}" style="background-color: #C0392B; color: #fff; text-decoration: none; padding: 10px 20px; border-radius: 5px;">Review Application</a>
                </div>
                <p>Thank you for your prompt attention to this matter.</p>
                <p style="color: #888;">- Pendeza Uganda - Finance Department</p>
            </div>
        </body>
        </html>
        """

    from_email = getattr(settings, "EMAIL_HOST_USER", None)
    to = [recipient_email]

    try:
        email = EmailMultiAlternatives(subject, strip_tags(email_body), from_email, to)
        email.attach_alternative(email_body, "text/html")
        email.send()
        return True
    except Exception as e:
        logger.error(f"Error sending email to {recipient_email}: {str(e)}")
        return False