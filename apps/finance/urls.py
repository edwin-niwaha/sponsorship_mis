from django.urls import path

from . import views

urlpatterns = [
    # Child Payments operations
    path("child-sponsor-payments/create/", views.child_sponsor_payment, name="child_sponsor_payment"),
    path("child-sponsorship/payment/report/", views.child_sponsor_payments_report, name="child_sponsor_payments_report"),
    path("child-sponsorship/payment/validate/<int:payment_id>/", views.validate_child_payment, name="validate_child_payment"),
    path('child-sponsorship/payment/<int:payment_id>/edit/', views.edit_child_payment, name='edit_child_payment'),
    path("child-sponsorship/payment/delete/<int:pk>/", views.delete_child_payment, name="delete_child_payment"),
    
    # Staff Payments operations   
     
    ]
