from django.urls import path

from . import views

urlpatterns = [
    path("add/", views.register_staff, name="register_staff"),
    path("list/", views.staff_list, name="staff_list"),
    path("update/<int:pk>", views.update_staff, name="update_staff"),
    path("delete/<int:pk>", views.delete_staff, name="delete_staff"),
    path("departure/", views.staff_departure, name="staff_departure"),
    path("departure/list/", views.staff_depature_list, name="staff_depature_list"),
    path("reinstate/<int:pk>", views.reinstate_staff, name="reinstate_staff"),
]
