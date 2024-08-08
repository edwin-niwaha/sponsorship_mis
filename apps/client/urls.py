from django.urls import path

from . import views

urlpatterns = [
    path("add/", views.register_client, name="register_client"),
    path("list/", views.client_list, name="client_list"),
    path("update/<int:pk>", views.update_client, name="update_client"),
    path("delete/<int:pk>", views.delete_client, name="delete_client"),
    path("import/", views.import_client_data, name="import_client_data"),
    path("delete-confirm/", views.delete_confirm, name="delete_confirm"),
]
