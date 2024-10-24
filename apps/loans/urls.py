from django.urls import path
from . import views

app_name = "loans"
urlpatterns = [
    path("apply-for-loan/", views.loan_application_view, name="apply_for_loan"),
    path("loan-applications/", views.loan_applications, name="loan-applications"),
    path("disbursed/", views.disbursed_loans_view, name="disbursed-loans"),
    path(
        "disbursement/",
        views.loan_disbursement_view,
        name="loan-disbursement",
    ),
    # path(
    #     "loan/<int:loan_id>/repayment/",
    #     views.loan_repayment_view,
    #     name="loan_repayment",
    # ),
]
