
import json
from datetime import timedelta
from urllib.request import Request, urlopen
from urllib.error import HTTPError, URLError

from django.conf import settings
from django.core.management.base import BaseCommand
from django.utils import timezone
from django.db import models

from tasks.models import Task, NotificationPreference


def send_reminder_email(task, reminder_type):
    user_email = task.user.email

    if not user_email:
        return False

    if reminder_type == 'upcoming':
        subject = 'Upcoming task deadline - PlanIt-Todo'
        message = (
            f'Hello {task.user.username},\n\n'
            f'Your task "{task.title}" is due within the next 24 hours.\n'
            f'Deadline: {task.due_date}\n\n'
            'Please complete it on time.\n\nPlanIt-Todo'
        )
    else:
        subject = 'Overdue task reminder - PlanIt-Todo'
        message = (
            f'Hello {task.user.username},\n\n'
            f'Your task "{task.title}" is overdue.\n'
            f'Deadline: {task.due_date}\n\n'
            'Please review and complete your task.\n\nPlanIt-Todo'
        )

    payload = {
        'sender': {
            'name': 'PlanIt-Todo',
            'email': settings.BREVO_SENDER_EMAIL,
        },
        'to': [{'email': user_email}],
        'subject': subject,
        'textContent': message,
    }

    request = Request(
        'https://api.brevo.com/v3/smtp/email',
        data=json.dumps(payload).encode('utf-8'),
        headers={
            'api-key': settings.BREVO_API_KEY,
            'Content-Type': 'application/json',
            'Accept': 'application/json',
        },
        method='POST',
    )

    try:
        with urlopen(request, timeout=15):
            return True
    except (HTTPError, URLError, TimeoutError) as error:
        print(f'Email failed for task {task.id}: {error}')
        return False


class Command(BaseCommand):
    help = 'Send upcoming and overdue task reminder emails'

    def handle(self, *args, **options):
        now = timezone.now()
        upcoming_limit = now + timedelta(hours=24)

        upcoming_tasks = Task.objects.filter(
            status=False,
            due_date__gt=now,
            due_date__lte=upcoming_limit,
        ).exclude(
            upcoming_reminder_sent_for=models.F('due_date')
        )

        overdue_tasks = Task.objects.filter(
            status=False,
            due_date__lt=now,
        ).exclude(
            overdue_reminder_sent_for=models.F('due_date')
        )

        upcoming_count = 0
        overdue_count = 0

        # Upcoming deadline reminders
        for task in upcoming_tasks:

            preferences, created = NotificationPreference.objects.get_or_create(
                user=task.user
            )

            if not preferences.upcoming_email_enabled:
                continue

            if send_reminder_email(task, 'upcoming'):
                task.upcoming_reminder_sent_for = task.due_date
                task.save(update_fields=['upcoming_reminder_sent_for'])
                upcoming_count += 1

        # Overdue task reminders
        for task in overdue_tasks:

            preferences, created = NotificationPreference.objects.get_or_create(
                user=task.user
            )

            if not preferences.overdue_email_enabled:
                continue

            if send_reminder_email(task, 'overdue'):
                task.overdue_reminder_sent_for = task.due_date
                task.save(update_fields=['overdue_reminder_sent_for'])
                overdue_count += 1

        self.stdout.write(
            self.style.SUCCESS(
                f'Upcoming reminders sent: {upcoming_count}'
            )
        )

        self.stdout.write(
            self.style.SUCCESS(
                f'Overdue reminders sent: {overdue_count}'
            )
        )
