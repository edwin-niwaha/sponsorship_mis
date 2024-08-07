from django.urls import path

from . import views

urlpatterns = [
    path("dashboard/", views.reports_dash, name="reports_dash"),
    path("all_children_list/", views.all_children_list, name="all_children_list"),
]
