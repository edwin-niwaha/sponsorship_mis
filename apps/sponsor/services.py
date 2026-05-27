import logging

from django.conf import settings
from django.core.mail import send_mail
from django.utils import timezone

logger = logging.getLogger(__name__)


def sponsor_feedback_recipients():
    recipients = [
        getattr(settings, "PROGS_ADMIN_EMAIL", ""),
        getattr(settings, "BOO_EMAIL", ""),
        getattr(settings, "ED_EMAIL", ""),
    ]
    return [email for email in recipients if email]


def send_sponsor_feedback_email(feedback):
    recipients = sponsor_feedback_recipients()
    from_email = getattr(settings, "DEFAULT_FROM_EMAIL", "") or getattr(
        settings,
        "EMAIL_HOST_USER",
        "",
    )

    if not recipients or not from_email:
        feedback.email_error = (
            "Sponsor feedback email skipped: recipients or sender missing."
        )
        feedback.save(update_fields=["email_error", "updated_at"])
        logger.warning(
            "Sponsor feedback %s email skipped; email settings missing.", feedback.id
        )
        return False

    sponsor = feedback.sponsor
    body = "\n".join(
        [
            "A sponsor has submitted feedback from the sponsor portal.",
            "",
            f"Sponsor: {sponsor.first_name} {sponsor.last_name} ({sponsor.prefixed_id})",
            f"Email: {sponsor.email}",
            f"Subject: {feedback.subject}",
            "",
            feedback.message,
        ]
    )

    try:
        send_mail(
            subject=f"Sponsor feedback: {feedback.subject}",
            message=body,
            from_email=from_email,
            recipient_list=recipients,
            fail_silently=False,
        )
    except Exception as exc:
        feedback.email_error = str(exc)
        feedback.save(update_fields=["email_error", "updated_at"])
        logger.exception("Sponsor feedback %s email failed.", feedback.id)
        return False

    feedback.email_sent_at = timezone.now()
    feedback.email_error = ""
    feedback.save(update_fields=["email_sent_at", "email_error", "updated_at"])
    return True
