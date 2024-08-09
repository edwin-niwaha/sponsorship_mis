from django.urls import path

from . import views

urlpatterns = [
    path("dashboard/", views.reports_dash, name="reports_dash"),
    path("children/list", views.all_children, name="all_children"),
    path("sponsored", views.sponsored_children, name="sponsored_children"),
]
