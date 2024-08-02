from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.contrib.auth import views as auth_views
from django.urls import include, path, re_path

from apps.users.forms import LoginForm
from apps.users.views import (
    ChangePasswordView,
    CustomLoginView,
    ResetPasswordView,
)

urlpatterns = [
    path("admin/", admin.site.urls),
    path("", include("apps.users.urls")),
    path(
        "login/",
        CustomLoginView.as_view(
            redirect_authenticated_user=True,
            template_name="users/login.html",
            authentication_form=LoginForm,
        ),
        name="login",
    ),
    path(
        "logout/",
        auth_views.LogoutView.as_view(template_name="users/logout.html"),
        name="logout",
    ),
    path("password-reset/", ResetPasswordView.as_view(), name="password_reset"),
    path(
        "password-reset-confirm/<uidb64>/<token>/",
        auth_views.PasswordResetConfirmView.as_view(
            template_name="users/password_reset_confirm.html"
        ),
        name="password_reset_confirm",
    ),
    path(
        "password-reset-complete/",
        auth_views.PasswordResetCompleteView.as_view(
            template_name="users/password_reset_complete.html"
        ),
        name="password_reset_complete",
    ),
    path("password-change/", ChangePasswordView.as_view(), name="password_change"),
    re_path(r"^oauth/", include("social_django.urls", namespace="social")),
    path("child/", include("apps.child.urls")),
    path("sponsor/", include("apps.sponsor.urls")),
    path("sponsorship/", include("apps.sponsorship.urls")),
    path("staff/", include("apps.staff.urls")),
    path("finance/", include("apps.finance.urls")),
    path("client/", include("apps.client.urls")),
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
