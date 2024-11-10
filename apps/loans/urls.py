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
    # Loan repayment
    path(
        "repay/",
        views.loan_repayment_create_view,
        name="loan_repayment_create",
    ),
    path("<int:loan_id>/", views.loan_detail_view, name="loan_detail"),
    path("loan-aging-report/", views.loan_aging_report, name="loan_aging_report"),
    path("loan-arrears-report/", views.loan_arrears_report, name="loan-arrears-report"),
    path("loan-portfolio/", views.loan_portfolio_report, name="loan_portfolio_report"),
    path(
        "portfolio-at-risk/", views.portfolio_at_risk, name="portfolio_at_risk_report"
    ),
    path("import/", views.import_loan_data, name="import_loan_data"),
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
    path("import-accounts/", views.import_coa_data, name="import_coa_data"),
    path("ledger_report/", views.ledger_report_view, name="ledger_report"),
    path(
        "ledger_report/<int:account_id>/",
        views.ledger_report_view,
        name="ledger_report_with_id",
    ),
]
