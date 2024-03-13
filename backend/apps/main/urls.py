from django.urls import path
from . import views

urlpatterns = [
    path('', views.home, name="users-home"),
    path('dashboard/', views.dashboard, name='main-dashboard'),

    path('child/add', views.register_child, name="manage_child"),
    path('child/list', views.child_list, name="child_list"),    

    path('up/<int:pk>', views.update_child, name= 'update_child'),
    path('del/<int:pk>', views.delete_child, name= 'delete_child'),
]
