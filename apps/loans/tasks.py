from celery import shared_task
from django.core.mail import EmailMultiAlternatives
from django.conf import settings
import logging

logger = logging.getLogger(__name__)

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