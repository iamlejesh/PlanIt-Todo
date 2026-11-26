from django.urls import path
from . import views

urlpatterns = [
    path('register/', views.register, name='register'),
    path('login/', views.user_login, name='login'),
    path('dashboard/', views.dashboard, name='dashboard'),
    path('logout/', views.user_logout, name='logout'),
    path('create-task/', views.create_task, name='create_task'), 
    path('edit-task/<int:task_id>/', views.edit_task, name='edit_task'),  
    path('delete-task/<int:task_id>/', views.delete_task, name='delete_task'),
    path('toggle-task/<int:task_id>/', views.toggle_task_status, name='toggle_task_status'),
    path('edit-profile/', views.edit_profile, name='edit_profile'),
    path('change-password/', views.change_password, name='change_password'),
]