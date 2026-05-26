from django.conf import settings
from django.core.checks import Warning, register


@register()
def email_configuration_check(app_configs, **kwargs):
    backend = getattr(settings, "EMAIL_BACKEND", "")
    if "ResendEmailBackend" in backend:
        warnings = []
        if not getattr(settings, "RESEND_API_KEY", ""):
            warnings.append(
                Warning(
                    "RESEND_API_KEY is not configured; production API emails will not send.",
                    hint="Set RESEND_API_KEY in Railway variables for web, worker, and beat services.",
                    id="users.W004",
                )
            )
        if not getattr(settings, "RESEND_FROM_EMAIL", ""):
            warnings.append(
                Warning(
                    "RESEND_FROM_EMAIL is empty; Resend requires a verified sender address.",
                    hint="Set RESEND_FROM_EMAIL to a verified sender such as Pendeza Uganda <noreply@yourdomain>.",
                    id="users.W005",
                )
            )
        return warnings

    if "smtp.EmailBackend" not in backend:
        return []

    warnings = []
    if not getattr(settings, "EMAIL_HOST_USER", ""):
        warnings.append(
            Warning(
                "EMAIL_HOST_USER is not configured; app-triggered emails will not send through SMTP.",
                hint="Set EMAIL_HOST_USER in Railway variables for the web service.",
                id="users.W001",
            )
        )
    if not getattr(settings, "EMAIL_HOST_PASSWORD", ""):
        warnings.append(
            Warning(
                "EMAIL_HOST_PASSWORD is not configured; app-triggered emails will not send through SMTP.",
                hint="Set EMAIL_HOST_PASSWORD in Railway variables for the web service.",
                id="users.W002",
            )
        )
    if not getattr(settings, "DEFAULT_FROM_EMAIL", ""):
        warnings.append(
            Warning(
                "DEFAULT_FROM_EMAIL is empty; some emails may be rejected by the SMTP provider.",
                hint="Set DEFAULT_FROM_EMAIL to the same verified sender used by EMAIL_HOST_USER.",
                id="users.W003",
            )
        )
    return warnings
