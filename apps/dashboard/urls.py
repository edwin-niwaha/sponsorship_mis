from django.urls import path

from . import views

urlpatterns = [
    path("", views.home, name="users-home"),
    path("main/", views.dashboard, name="main-dashboard"),
    path(
        "get_sponsors_data/",
        views.get_sponsors_data,
        name="get_sponsors_data",
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
]
