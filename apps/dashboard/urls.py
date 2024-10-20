from django.urls import path

from . import views

urlpatterns = [
    path("", views.home, name="users-home"),
    # sponsorship urls
    path("sdms/", views.dashboard, name="main-dashboard"),
    path(
        "get_sponsors_data/",
        views.get_sponsors_data,
        name="get_sponsors_data",
    ),
    path(
        "get_children_data/",
        views.get_children_data,
        name="get_children_data",
    ),
    path(
        "birthdays_by_month/",
        views.birthdays_by_month,
        name="birthdays_by_month",
    ),
    path(
        "get_combined_data/",
        views.get_combined_data,
        name="get_combined_data",
    ),
    path(
        "get_payments_children/",
        views.get_payments_children,
        name="get_payments_children",
    ),
    path(
        "get_payments_staff/",
        views.get_payments_staff,
        name="get_payments_staff",
    ),
    path("sponsorship-chart/", views.sponsorship_chart, name="sponsorship-chart"),
    # inventory urls
    path("inventory/", views.inventory_dashboard, name="inventory-dashboard"),
    path(
        "monthly_earnings/",
        views.monthly_earnings_view,
        name="monthly_earnings_view",
    ),
    path("sales-data/", views.sales_data_api, name="sales-data-api"),
]
