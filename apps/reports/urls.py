from django.urls import path

from . import views

urlpatterns = [
    path("dashboard/", views.reports_dash, name="reports_dash"),
]
