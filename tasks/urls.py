
from django.urls import path
from . import views

urlpatterns = [
    path('', views.user_login, name='home'),
    path('register/', views.register, name='register'),
    path('verify-email/<uidb64>/<token>/', views.verify_email, name='verify_email'),
    path('login/', views.user_login, name='login'),
    path('dashboard/', views.dashboard, name='dashboard'),
    path('logout/', views.user_logout, name='logout'),
    path('create-task/', views.create_task, name='create_task'),
    path('edit-task/<int:task_id>/', views.edit_task, name='edit_task'),
    path('delete-task/<int:task_id>/', views.delete_task, name='delete_task'),
    path('toggle-task/<int:task_id>/', views.toggle_task_status, name='toggle_task_status'),
    path('edit-profile/', views.edit_profile, name='edit_profile'),
    path('change-password/', views.change_password, name='change_password'),
    path('calendar/', views.calendar_view, name='calendar'),
    path('daily-tasks/', views.daily_tasks, name='daily_tasks'),
    path('weekly-tasks/', views.weekly_tasks, name='weekly_tasks'),
    path('password-reset/', views.password_reset_request, name='password_reset'),
    path('password-reset-confirm/<uidb64>/<token>/', views.password_reset_confirm, name='password_reset_confirm'),
    path('notifications/', views.notifications, name='notifications'),
    path('notifications/read/<int:notification_id>/', views.mark_notification_read, name='mark_notification_read'),
    path('notifications/delete/<int:notification_id>/', views.delete_notification, name='delete_notification'),
    path('notification-settings/', views.notification_settings, name='notification_settings'),

    # Real-time notifications
    path('notification-updates/', views.notification_updates, name='notification_updates'),
]
