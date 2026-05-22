import logging

from django.contrib import messages
from django.shortcuts import redirect

from .login_verification import start_login_verification_session
from .models import Profile

logger = logging.getLogger(__name__)


def require_google_login_token(strategy, backend, user=None, *args, **kwargs):
    if getattr(backend, "name", "") != "google-oauth2" or user is None:
        return None

    request = getattr(strategy, "request", None)
    if request is None:
        return None

    Profile.objects.get_or_create(user=user)
    if not user.email:
        messages.error(
            request,
            "Your Google account did not provide an email address. Please sign in with your password.",
        )
        return redirect("login")

    redirect_to = None
    session_get = getattr(strategy, "session_get", None)
    if callable(session_get):
        redirect_to = session_get("next")

    try:
        start_login_verification_session(
            request,
            user,
            remember_me=False,
            redirect_to=redirect_to,
        )
    except Exception:
        logger.exception(
            "Failed to send Google login verification email for user_id=%s email=%s",
            user.pk,
            user.email,
        )
        messages.error(
            request,
            "We could not send the verification email. Please try again.",
        )
        return redirect("login")

    messages.info(
        request,
        "Google confirmed your account. Enter the code sent to your email to finish signing in.",
    )
    return redirect("login_verify")
