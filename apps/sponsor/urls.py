from django.urls import path

from . import views

urlpatterns = [
    path("add/", views.register_sponsor, name="register_sponsor"),
    path("list/", views.sponsor_list, name="sponsor_list"),
    path("update/<int:pk>/", views.update_sponsor, name="update_sponsor"),
    path("delete/<int:pk>/", views.delete_sponsor, name="delete_sponsor"),
    path("departure/", views.sponsor_departure, name="sponsor_departure"),
    path("departure/list/", views.sponsor_depature_list, name="sponsor_depature_list"),
    path("reinstate/<int:pk>/", views.reinstate_sponsor, name="reinstate_sponsor"),
    path("import/", views.import_sponsor_data, name="import_sponsor_data"),
    path("delete-all-records/", views.delete_sponsors, name="delete_sponsors"),
    path(
        "imported/",
        views.imported_sponsors,
        name="imported_sponsors",
    ),
    path(
        "update-sponsors-contacts/",
        views.update_sponsor_contacts,
        name="update_sponsor_contacts",
    ),
]
