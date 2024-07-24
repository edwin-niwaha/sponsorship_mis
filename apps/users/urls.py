from django.urls import path

from .views import (
    RegisterView,
    contact_us,
    delete_ebook,
    delete_policy,
    ebook_list,
    home,
    policy_list,
    policy_report,
    profile,
    read_policy,
    update_ebook,
    update_policy,
    upload_ebook,
    upload_policy,
    validate_policy,
)

urlpatterns = [
    path("", home, name="users-home"),
    path("register/", RegisterView.as_view(), name="users-register"),
    path("profile/", profile, name="users-profile"),
    path("contact-us/", contact_us, name="contact_us"),
    path("policy-list/", policy_list, name="policy_list"),
    path("create-policy/", upload_policy, name="upload_policy"),
    path("policy/update/<int:pk>", update_policy, name="update_policy"),
    path("policy/delete/<int:pk>", delete_policy, name="delete_policy"),
    path("policy/validate/<int:policy_id>/", validate_policy, name="validate_policy"),
    path("policy/read/<int:policy_id>/", read_policy, name="read_policy"),
    path("policy/read/", policy_report, name="policy_report"),
    path("ebook/upload/", upload_ebook, name="upload_ebook"),
    path("ebook/list/", ebook_list, name="ebook_list"),
    path("ebook/delete/<int:pk>", delete_ebook, name="delete_ebook"),
    path("ebook/update/<int:pk>", update_ebook, name="update_ebook"),

    ]