from django.urls import path
from . import views

app_name = "loans"

urlpatterns = [
    # Loan application URLs
    path("apply/", views.loan_apply, name="apply_for_loan"),
    path("applications/", views.loan_applications, name="loan_applications"),
    path("disbursed/", views.disbursed_loans_view, name="disbursed_loans"),
    path(
        "loan/<int:loan_id>/repayment-schedule/",
        views.repayment_schedule,
        name="repayment_schedule",
    ),
    # Loan management URLs
    path("<int:loan_id>/approve/", views.approve_loan, name="approve_loan"),
    path("<int:loan_id>/reject/", views.reject_loan, name="reject_loan"),
    path("disburse/", views.disburse_loan, name="disburse_loan"),
    path("delete/<int:loan_id>/", views.delete_loan, name="delete_loan"),
    # Loan repayment (commented out for future use)
    # path("<int:loan_id>/repayment/", views.loan_repayment_view, name="loan_repayment"),
    # Chart of accounts URLs
    path("accounts/add/", views.add_chart_of_account_view, name="add_chart_of_account"),
    path("accounts/", views.chart_of_accounts_list_view, name="chart_of_accounts_list"),
    path(
        "accounts/update/<str:account_id>/",
        views.chart_of_account_update_view,
        name="chart_of_account_update",
    ),
    path(
        "accounts/delete/<str:account_id>/",
        views.chart_of_account_delete_view,
        name="chart_of_account_delete",
    ),
]