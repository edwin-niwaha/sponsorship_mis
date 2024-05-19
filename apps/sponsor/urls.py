from django.urls import path

from . import views

urlpatterns = [
    path("add/", views.register_sponsor, name="register_sponsor"),
    path("list/", views.sponsor_list, name="sponsor_list"),
    path("update/<int:pk>", views.update_sponsor, name="update_sponsor"),
    path("delete/<int:pk>", views.delete_sponsor, name="delete_sponsor"),
    ]