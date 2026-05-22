from django.contrib import messages
from django.shortcuts import redirect

from .models import Profile


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

    return None
