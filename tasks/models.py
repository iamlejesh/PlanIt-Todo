
from django.db import models
from django.contrib.auth.models import User


class Task(models.Model):

    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='tasks'
    )

    title = models.CharField(max_length=200)
    description = models.TextField(blank=True, null=True)
    status = models.BooleanField(default=False)
    priority = models.CharField(max_length=10, default='Medium')
    created_at = models.DateTimeField(auto_now_add=True)
    due_date = models.DateTimeField(blank=True, null=True)
    upcoming_reminder_sent_for = models.DateTimeField(null=True,blank=True)
    overdue_reminder_sent_for = models.DateTimeField(null=True,blank=True)

    category = models.CharField(
        max_length=20,
        choices=[
            ('Work', 'Work'),
            ('Personal', 'Personal'),
            ('Study', 'Study'),
            ('Shopping', 'Shopping'),
            ('Other', 'Other'),
        ],
        default='Other'
    )

    def __str__(self):
        return self.title


class Notification(models.Model):

    NOTIFICATION_TYPES = [
        ('task_created', 'Task Created'),
        ('task_completed', 'Task Completed'),
        ('task_updated', 'Task Updated'),
        ('task_deleted', 'Task Deleted'),
    ]

    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='notifications'
    )

    message = models.CharField(max_length=255)

    notification_type = models.CharField(
        max_length=30,
        choices=NOTIFICATION_TYPES
    )

    is_read = models.BooleanField(default=False)

    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.message


class NotificationPreference(models.Model):

    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name='notification_preferences'
    )

    upcoming_email_enabled = models.BooleanField(default=True)

    overdue_email_enabled = models.BooleanField(default=True)

    in_app_notifications_enabled = models.BooleanField(default=True)

    def __str__(self):
        return f'{self.user.username} - Notification Preferences'
