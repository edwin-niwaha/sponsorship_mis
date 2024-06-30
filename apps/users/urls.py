from django.urls import path

from .views import (
    RegisterView,
    contact_us,
    create_policy,
    delete_policy,
    home,
    policy_list,
    policy_report,
    profile,
    read_policy,
    update_policy,
    validate_policy,
)

urlpatterns = [
    path("", home, name="users-home"),
    path("register/", RegisterView.as_view(), name="users-register"),
    path("profile/", profile, name="users-profile"),
    path("contact-us/", contact_us, name="contact_us"),
    path("policy-list/", policy_list, name="policy_list"),
    path("create-policy/", create_policy, name="create_policy"),
    path("policy/update/<int:pk>", update_policy, name="update_policy"),
    path("policy/delete/<int:pk>", delete_policy, name="delete_policy"),
    path("policy/validate/<int:policy_id>/", validate_policy, name="validate_policy"),
    path("policy/read/<int:policy_id>/", read_policy, name="read_policy"),
    path("policy/read/", policy_report, name="policy_report")
    ]