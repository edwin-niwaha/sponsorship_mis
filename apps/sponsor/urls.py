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

    # Child Sponsorship operations
    path("child-sponsorship/create/", views.child_sponsorship, name="child_sponsorship"),
    path("child-sponsorship/report/", views.child_sponsorship_report, name="child_sponsorship_report"),
    path("child-sponsorship/delete/<int:pk>/", views.delete_child_sponsorship, name="delete_child_sponsorship"),
    path("child-sponsorship/terminate/<int:sponsorship_id>/", views.terminate_child_sponsorship, 
         name="terminate_child_sponsorship"),
    path('child-sponsorship/<int:sponsorship_id>/edit/', views.edit_child_sponsorship, name='edit_child_sponsorship'),

    # Staff Sponsorship operations
    path("staff-sponsorship/create/", views.staff_sponsorship_create, name="staff_sponsorship_create"),
    path("staff-sponsorship/report/", views.staff_sponsorship_report, name="staff_sponsorship_report"),
    path("staff-sponsorship/delete/<int:pk>/", views.delete_staff_sponsorship, name="delete_staff_sponsorship"),
    path('staff-sponsorship/terminate/<int:sponsorship_id>/', views.terminate_staff_sponsorship, 
         name='terminate_staff_sponsorship'),
    path('staff-sponsorship/<int:sponsorship_id>/edit/', views.edit_staff_sponsorship, name='edit_staff_sponsorship'),
]
