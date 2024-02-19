from django.urls import path
from .views import home, dashboard

urlpatterns = [
    path("", home, name="users-home"),
    path("dashboard/", dashboard, name="main-dashboard"),
]
