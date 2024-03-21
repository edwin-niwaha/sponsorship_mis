from django.urls import path
from . import views

urlpatterns = [
    path('', views.home, name="users-home"),
    path('dashboard/', views.dashboard, name='main-dashboard'),

# The child paths
    path('child/add/', views.register_child, name="manage_child"),
    path('child/profile/', views.upload_profile_picture, name="profile_picture"), 
    path('child/list/', views.child_list, name="child_list"),    
    path('child/list/details/<int:pk>', views.child_details, name="child_details"),    
    path('up/<int:pk>', views.update_child, name= 'update_child'),
    path('del/<int:pk>', views.delete_child, name= 'delete_child'),

# Excel import paths
    path('child/import/', views.import_data, name="import"),
    path('excel/list/', views.import_details, name="data_list"),   
    path('del/excel-data/<int:pk>', views.delete_excel_data, name= 'delete_excel'),
    path('delete_confirmation/', views.delete_confirmation, name='delete_confirmation'),
]
