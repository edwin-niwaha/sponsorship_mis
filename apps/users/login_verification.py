from secrets import randbelow

from django.conf import settings
from django.core import signing
from django.core.mail import send_mail
from django.utils import timezone
from django.utils.crypto import constant_time_compare

LOGIN_VERIFICATION_SESSION_KEY = "pending_login_verification"
LOGIN_VERIFICATION_TIMEOUT_SECONDS = 10 * 60
LOGIN_VERIFICATION_SALT = "apps.users.login-verification"


def generate_login_token():
    return f"{randbelow(1000000):06d}"


def build_token_digest(token):
    return signing.dumps(token, salt=LOGIN_VERIFICATION_SALT)


def token_matches(token, signed_token):
    try:
        expected = signing.loads(
            signed_token,
            salt=LOGIN_VERIFICATION_SALT,
            max_age=LOGIN_VERIFICATION_TIMEOUT_SECONDS,
        )
    except signing.BadSignature:
        return False
    return constant_time_compare(token, expected)


def send_login_verification_email(user, token):
    subject = "Your Pendeza login verification code"
    message = (
        f"Hello {user.get_full_name() or user.get_username()},\n\n"
        f"Your login verification code is {token}.\n\n"
        "This code expires in 10 minutes. If you did not try to sign in, "
        "you can ignore this email.\n\n"
        "Pendeza Uganda"
    )
    send_mail(
        subject,
        message,
        settings.DEFAULT_FROM_EMAIL,
        [user.email],
        fail_silently=False,
    )


def start_login_verification_session(
    request,
    user,
    *,
    remember_me=False,
    redirect_to=None,
):
    token = generate_login_token()
    send_login_verification_email(user, token)
    request.session[LOGIN_VERIFICATION_SESSION_KEY] = {
        "user_id": user.pk,
        "email": user.email,
        "token": build_token_digest(token),
        "remember_me": bool(remember_me),
        "redirect_to": redirect_to,
        "created_at": timezone.now().isoformat(),
        "attempts": 0,
    }
    request.session.modified = True
    return token
