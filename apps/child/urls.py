from django.urls import path

from . import views

urlpatterns = [
    path("", views.home, name="users-home"),
    path("dashboard/", views.dashboard, name="main-dashboard"),

    # The child paths
    path("child/add/", views.register_child, name="manage_child"),
    path("child/list/", views.child_list, name="child_list"),
    path("child/list/details/<int:pk>", views.child_details, name="child_details"),
    path("child/update/<int:pk>", views.update_child, name="update_child"),
    path("child/delete/<int:pk>", views.delete_child, name="delete_child"),

    # For the related models
    path("child/profile-picture/", views.update_picture, name="update_picture"),
    path("child/profile-picture/list/", views.profile_pictures, name="profile_pictures"),
    path("child/profile-picture/delete/<int:pk>", views.delete_profile_picture, name="delete_profile_picture"),
    path('child/progress/', views.child_progress, name='child_progress'),
    path('child/progress/report/', views.child_progress_report, name='child_progress_report'),
    path("child/progress/delete/<int:pk>", views.delete_progress, name="delete_progress"),
    path("child/correspondence/", views.child_correspondence, name="child_correspondence"),
    path('child/correspondence/report/', views.child_correspondence_report, name='child_correspondence_report'),
    path("child/correspondence/delete/<int:pk>", views.delete_correspondence, name="delete_correspondence"),
    path("child/incident/", views.child_incident, name="child_incident"),
    path('child/incident/report/', views.child_incident_report, name='child_incident_report'),
    path("child/incident/delete/<int:pk>", views.delete_incident, name="delete_incident"),
    path('child/departure/', views.child_departure, name='child_departure'),
    path("child/departure/list/", views.depature_list, name="depature_list"),
    path("child/reinstate/<int:pk>", views.reinstate_child, name="reinstate_child"),
    
    # User Feedback
    path("user/feedback/", views.user_feedback, name="users-feedback"),
    path("user/feedback/delete/<int:pk>", views.delete_feedback, name="delete_feedback"),

    # Excel import paths
    path("child/import/", views.import_data, name="import"),
    path("child/excel/list/", views.import_details, name="imported_data"),
    path("child/excel-data/delete/<int:pk>", views.delete_excel_data, name="delete_excel"),
    path("child/delete_confirmation/", views.delete_confirmation, name="delete_confirmation"),
]
