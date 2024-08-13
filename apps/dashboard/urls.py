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
]
