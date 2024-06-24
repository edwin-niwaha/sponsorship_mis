from django.urls import path

from . import views

urlpatterns = [
    # Sponsor CRUD operations
    path("add/", views.register_sponsor, name="register_sponsor"),
    path("list/", views.sponsor_list, name="sponsor_list"),
    path("update/<int:pk>/", views.update_sponsor, name="update_sponsor"),
    path("delete/<int:pk>/", views.delete_sponsor, name="delete_sponsor"),
    path("departure/", views.sponsor_departure, name="sponsor_departure"),
    path("departure/list/", views.sponsor_depature_list, name="sponsor_depature_list"),
    path("reinstate/<int:pk>/", views.reinstate_sponsor, name="reinstate_sponsor"),

]
