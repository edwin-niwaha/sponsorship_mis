from django.urls import path

from . import views

urlpatterns = [
    path("", views.home, name="users-home"),
    path("dashboard/", views.dashboard, name="main-dashboard"),

    # The child paths
    path("add/", views.register_child, name="manage_child"),
    path("list/", views.child_list, name="child_list"),
    path("list/details/<int:pk>", views.child_details, name="child_details"),
    path("update/<int:pk>", views.update_child, name="update_child"),
    path("delete/<int:pk>", views.delete_child, name="delete_child"),

    # For the related models
    path("profile-picture/", views.update_picture, name="update_picture"),
    path("profile-picture/list/", views.profile_pictures, name="profile_pictures"),
    path("profile-picture/delete/<int:pk>", views.delete_profile_picture, name="delete_profile_picture"),
    path('progress/', views.child_progress, name='child_progress'),
    path('progress/report/', views.child_progress_report, name='child_progress_report'),
    path("progress/delete/<int:pk>", views.delete_progress, name="delete_progress"),
    path("correspondence/", views.child_correspondence, name="child_correspondence"),
    path('correspondence/report/', views.child_correspondence_report, name='child_correspondence_report'),
    path("correspondence/delete/<int:pk>", views.delete_correspondence, name="delete_correspondence"),
    path("incident/", views.child_incident, name="child_incident"),
    path('incident/report/', views.child_incident_report, name='child_incident_report'),
    path("incident/delete/<int:pk>", views.delete_incident, name="delete_incident"),
    path('departure/', views.child_departure, name='child_departure'),
    path("departure/list/", views.depature_list, name="depature_list"),
    path("reinstate/<int:pk>", views.reinstate_child, name="reinstate_child"),
    
    # User Feedback
    path("user/feedback/", views.user_feedback, name="users-feedback"),
    path("user/feedback/delete/<int:pk>", views.delete_feedback, name="delete_feedback"),

    # Excel import paths
    path("import/", views.import_data, name="import"),
    path("excel/list/", views.import_details, name="imported_data"),
    path("excel-data/delete/<int:pk>", views.delete_excel_data, name="delete_excel"),
    path("delete_confirmation/", views.delete_confirmation, name="delete_confirmation"),
]
