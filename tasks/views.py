
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.models import User
from django.contrib.auth import authenticate, login
from django.contrib.auth.decorators import login_required
from django.contrib.auth import logout
from django.http import JsonResponse
from .models import Task, Notification, NotificationPreference
from django.core.paginator import Paginator
from django.contrib.auth import update_session_auth_hash
from django.utils import timezone
from django.db.models import Case, When, Value, IntegerField
from datetime import timedelta
import calendar
from datetime import datetime, timedelta
import json
from urllib.request import Request, urlopen
from urllib.error import HTTPError, URLError
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from django.conf import settings
from django.contrib.auth.tokens import default_token_generator
from django.urls import reverse
from django.utils.encoding import force_bytes, force_str
from django.utils.http import urlsafe_base64_encode, urlsafe_base64_decode
import hashlib
from django.core.cache import cache
from django.contrib import messages


def create_user_notification(user, message, notification_type):

    preferences, created = NotificationPreference.objects.get_or_create(
        user=user
    )

    if preferences.in_app_notifications_enabled:
        Notification.objects.create(
            user=user,
            message=message,
            notification_type=notification_type
        )


def send_verification_email(user):

    uid = urlsafe_base64_encode(force_bytes(user.pk))
    token = default_token_generator.make_token(user)

    verification_path = reverse(
        'verify_email',
        kwargs={
            'uidb64': uid,
            'token': token
        }
    )

    verification_url = (
        f"{settings.SITE_URL.rstrip('/')}{verification_path}"
    )

    payload = {
        "sender": {
            "name": "PlanIt-Todo",
            "email": settings.BREVO_SENDER_EMAIL
        },
        "to": [
            {
                "email": user.email
            }
        ],
        "subject": "Verify your PlanIt-Todo email",
        "htmlContent": f"""
            <h2>Welcome to PlanIt-Todo!</h2>
            <p>Please verify your email address by clicking below:</p>
            <a href="{verification_url}">Verify Email</a>
        """
    }

    request = Request(
        "https://api.brevo.com/v3/smtp/email",
        data=json.dumps(payload).encode('utf-8'),
        headers={
            "api-key": settings.BREVO_API_KEY,
            "Content-Type": "application/json",
            "Accept": "application/json"
        },
        method="POST"
    )

    try:
        with urlopen(request, timeout=15) as response:
            return response.status in (200, 201, 202)

    except (HTTPError, URLError, TimeoutError) as error:
        print("Brevo email error:", error)
        return False


def register(request):

    if request.method == 'POST':

        username = request.POST.get('username')
        first_name = request.POST.get('first_name')
        last_name = request.POST.get('last_name')
        email = request.POST.get('email')
        password = request.POST.get('password')
        confirm_password = request.POST.get('confirm_password')

        if password != confirm_password:
            return render(request, 'tasks/register.html', {
                'error': 'Passwords do not match'
            })

        if User.objects.filter(username=username).exists():
            return render(request, 'tasks/register.html', {
                'error': 'Username already exists'
            })

        if User.objects.filter(email=email).exists():
            return render(request, 'tasks/register.html', {
                'error': 'Email already registered'
            })

        if not email:
            return render(request, 'tasks/register.html', {
                'error': 'Email is required'
            })

        user = User.objects.create_user(
            username=username,
            first_name=first_name,
            last_name=last_name,
            email=email,
            password=password,
            is_active=False
        )

        if send_verification_email(user):
            return render(
                request,
                'tasks/email_verification_sent.html'
            )

        user.delete()

        return render(request, 'tasks/register.html', {
            'error': 'Unable to send verification email. Please try again.'
        })

    return render(request, 'tasks/register.html')


def verify_email(request, uidb64, token):

    try:
        uid = force_str(urlsafe_base64_decode(uidb64))
        user = User.objects.get(pk=uid)

    except (TypeError, ValueError, OverflowError, User.DoesNotExist):
        user = None

    if user is not None and default_token_generator.check_token(user, token):

        user.is_active = True
        user.save(update_fields=['is_active'])

        return render(request, 'tasks/email_verified.html')

    return render(request, 'tasks/email_verification_invalid.html')


@login_required
def dashboard(request):

    status = request.GET.get('status')
    search_query = request.GET.get('search')
    category = request.GET.get('category')
    priority = request.GET.get('priority')
    start_date = request.GET.get('start_date')
    end_date = request.GET.get('end_date')

    tasks = Task.objects.filter(user=request.user)

    total_tasks = tasks.count()
    completed_tasks = tasks.filter(status=True).count()
    pending_tasks = tasks.filter(status=False).count()

    overdue_tasks = Task.objects.filter(
        user=request.user,
        status=False,
        due_date__lt=timezone.now()
    )

    upcoming_tasks = Task.objects.filter(
        user=request.user,
        status=False,
        due_date__gte=timezone.now(),
        due_date__lte=timezone.now() + timedelta(hours=24)
    ).order_by('due_date')

    if search_query:
        tasks = tasks.filter(title__icontains=search_query)

    if status == 'pending':
        tasks = tasks.filter(status=False)

    elif status == 'completed':
        tasks = tasks.filter(status=True)

    if category:
        tasks = tasks.filter(category=category)

    if priority:
        tasks = tasks.filter(priority=priority)

    if start_date:
        tasks = tasks.filter(due_date__date__gte=start_date)

    if end_date:
        tasks = tasks.filter(due_date__date__lte=end_date)

    sort_by = request.GET.get('sort', 'newest')

    if sort_by == 'oldest':
        tasks = tasks.order_by('created_at')

    elif sort_by == 'priority':
        tasks = tasks.order_by(
            Case(
                When(priority='High', then=Value(1)),
                When(priority='Medium', then=Value(2)),
                When(priority='Low', then=Value(3)),
                default=Value(4),
                output_field=IntegerField()
            )
        )

    elif sort_by == 'due_date':
        tasks = tasks.order_by('due_date')

    else:
        sort_by = 'newest'
        tasks = tasks.order_by('-created_at')

    paginator = Paginator(tasks, 2)

    page_number = request.GET.get('page')

    tasks = paginator.get_page(page_number)

    # Get unread notification count
    unread_notifications_count = Notification.objects.filter(
        user=request.user,
        is_read=False
    ).count()

    return render(request, 'tasks/dashboard.html', {
        'tasks': tasks,
        'selected_status': status,
        'search_query': search_query,
        'overdue_tasks': overdue_tasks,
        'upcoming_tasks': upcoming_tasks,
        'total_tasks': total_tasks,
        'completed_tasks': completed_tasks,
        'pending_tasks': pending_tasks,
        'selected_sort': sort_by,
        'selected_category': category,
        'selected_priority': priority,
        'start_date': start_date,
        'end_date': end_date,
        'unread_notifications_count': unread_notifications_count,
    })


def user_login(request):

    MAX_LOGIN_ATTEMPTS = 5
    LOCKOUT_TIME = 15 * 60  # 15 minutes

    if request.method == 'POST':

        username = request.POST.get('username', '').strip()
        password = request.POST.get('password', '')

        # Get client IP address
        ip_address = request.META.get('REMOTE_ADDR', 'unknown')

        # Generate secure cache keys
        username_hash = hashlib.sha256(
            username.casefold().encode()
        ).hexdigest()

        ip_hash = hashlib.sha256(
            ip_address.encode()
        ).hexdigest()

        username_key = f'login_username_{username_hash}'
        ip_key = f'login_ip_{ip_hash}'

        # Check whether the login attempts have exceeded the limit
        username_attempts = cache.get(username_key, 0)
        ip_attempts = cache.get(ip_key, 0)

        if (
            username_attempts >= MAX_LOGIN_ATTEMPTS
            or ip_attempts >= MAX_LOGIN_ATTEMPTS
        ):
            return render(request, 'tasks/login.html', {
                'error': 'Too many failed login attempts. Please try again after 15 minutes.'
            })

        # Authenticate user
        user = authenticate(
            request,
            username=username,
            password=password
        )

        if user is not None:

            # Clear failed attempts after successful login
            cache.delete(username_key)
            cache.delete(ip_key)

            login(request, user)

            return redirect('dashboard')

        # Increase failed login attempts
        cache.set(
            username_key,
            username_attempts + 1,
            timeout=LOCKOUT_TIME
        )

        cache.set(
            ip_key,
            ip_attempts + 1,
            timeout=LOCKOUT_TIME
        )

        return render(request, 'tasks/login.html', {
            'error': 'Invalid username or password'
        })

    return render(request, 'tasks/login.html')


def user_logout(request):

    if request.method == 'POST':
        logout(request)
        return redirect('login')

    return redirect('dashboard')


@login_required
def create_task(request):

    if request.method == 'POST':

        title = request.POST.get('title')
        description = request.POST.get('description')
        priority = request.POST.get('priority')
        due_date = request.POST.get('due_date')
        category = request.POST.get('category')

        task = Task.objects.create(
            user=request.user,
            title=title,
            description=description,
            priority=priority,
            due_date=due_date if due_date else None,
            category=category
        )

        create_user_notification(
            request.user,
            f'Your task "{task.title}" was created.',
            'task_created'
        )

        return redirect('dashboard')


@login_required
def edit_task(request, task_id):

    task = get_object_or_404(
        Task,
        id=task_id,
        user=request.user
    )

    if request.method == 'POST':

        task.title = request.POST.get('title')
        task.description = request.POST.get('description')

        due_date = request.POST.get('due_date')
        task.due_date = due_date if due_date else None

        task.priority = request.POST.get('priority')
        task.category = request.POST.get('category')

        task.save()

        create_user_notification(
            request.user,
            f'Your task "{task.title}" was updated.',
            'task_updated'
        )

        return redirect('dashboard')

    return render(request, 'tasks/edit_task.html', {
        'task': task
    })


@login_required
def delete_task(request, task_id):

    if request.method == 'POST':

        task = get_object_or_404(
            Task,
            id=task_id,
            user=request.user
        )

        # Create notification before deleting the task
        create_user_notification(
            request.user,
            f'Your task "{task.title}" was deleted.',
            'task_deleted'
        )

        task.delete()

    return redirect('dashboard')


@login_required
def toggle_task_status(request, task_id):

    if request.method == 'POST':

        task = get_object_or_404(
            Task,
            id=task_id,
            user=request.user
        )

        task.status = not task.status

        task.save()

        if task.status:
            create_user_notification(
                request.user,
                f'You completed "{task.title}".',
                'task_completed'
            )

    return redirect('dashboard')


@login_required
def edit_profile(request):

    if request.method == 'POST':

        first_name = request.POST.get('first_name')
        last_name = request.POST.get('last_name')
        email = request.POST.get('email')

        user = request.user

        user.first_name = first_name
        user.last_name = last_name
        user.email = email

        user.save()

        return redirect('dashboard')

    return render(request, 'tasks/edit_profile.html')


@login_required
def change_password(request):

    if request.method == 'POST':

        old_password = request.POST.get('old_password')
        new_password = request.POST.get('new_password')
        confirm_password = request.POST.get('confirm_password')

        user = request.user

        if not user.check_password(old_password):
            return render(request, 'tasks/change_password.html', {
                'error': 'Incorrect old password'
            })

        if new_password != confirm_password:
            return render(request, 'tasks/change_password.html', {
                'error': 'New passwords do not match'
            })

        user.set_password(new_password)
        user.save()

        update_session_auth_hash(request, user)

        return redirect('dashboard')

    return render(request, 'tasks/change_password.html')


@login_required
def calendar_view(request):

    today = timezone.localdate()

    try:
        year = int(request.GET.get('year', today.year))
        month = int(request.GET.get('month', today.month))

        if month < 1 or month > 12:
            raise ValueError

        if year < 1900 or year > 9999:
            raise ValueError

    except (ValueError, TypeError):
        year = today.year
        month = today.month

    first_day = datetime(year, month, 1)

    if month == 12:
        next_month = datetime(year + 1, 1, 1)
    else:
        next_month = datetime(year, month + 1, 1)

    start_date = timezone.make_aware(
        first_day,
        timezone.get_current_timezone()
    )

    end_date = timezone.make_aware(
        next_month,
        timezone.get_current_timezone()
    )

    tasks = Task.objects.filter(
        user=request.user,
        due_date__gte=start_date,
        due_date__lt=end_date
    ).order_by('due_date')

    tasks_by_date = {}

    for task in tasks:
        task_date = timezone.localtime(task.due_date).date()

        tasks_by_date.setdefault(task_date, []).append(task)

    calendar_data = []

    month_calendar = calendar.Calendar(
        firstweekday=0
    ).monthdatescalendar(year, month)

    for week in month_calendar:

        week_data = []

        for day in week:

            week_data.append({
                'date': day,
                'is_current_month': day.month == month,
                'tasks': tasks_by_date.get(day, [])
                if day.month == month else []
            })

        calendar_data.append(week_data)

    previous_month = (
        datetime(year, month, 1) - timedelta(days=1)
    )

    if month == 12:
        following_month = datetime(year + 1, 1, 1)
    else:
        following_month = datetime(year, month + 1, 1)

    return render(request, 'tasks/calendar.html', {
        'calendar_data': calendar_data,
        'month_name': calendar.month_name[month],
        'year': year,
        'previous_month': previous_month,
        'following_month': following_month,
        'today': today,
    })


@login_required
def daily_tasks(request):

    selected_date = request.GET.get('date')

    try:
        if selected_date:
            selected_date = datetime.strptime(
                selected_date, '%Y-%m-%d'
            ).date()
        else:
            selected_date = timezone.localdate()

    except ValueError:
        selected_date = timezone.localdate()

    tasks = Task.objects.filter(
        user=request.user,
        due_date__date=selected_date
    ).order_by('due_date')

    return render(request, 'tasks/daily_tasks.html', {
        'tasks': tasks,
        'selected_date': selected_date,
    })


@login_required
def weekly_tasks(request):

    today = timezone.localdate()

    selected_date = request.GET.get('date')

    try:
        if selected_date:
            selected_date = datetime.strptime(
                selected_date, '%Y-%m-%d'
            ).date()
        else:
            selected_date = today

    except ValueError:
        selected_date = today

    start_date = selected_date - timedelta(
        days=selected_date.weekday()
    )

    end_date = start_date + timedelta(days=7)

    tasks = Task.objects.filter(
        user=request.user,
        due_date__date__gte=start_date,
        due_date__date__lt=end_date
    ).order_by('due_date')

    weekly_data = []

    for day_offset in range(7):

        current_day = start_date + timedelta(days=day_offset)

        day_tasks = [
            task for task in tasks
            if timezone.localtime(task.due_date).date() == current_day
        ]

        weekly_data.append({
            'date': current_day,
            'tasks': day_tasks,
            'is_today': current_day == today,
        })

    return render(request, 'tasks/weekly_tasks.html', {
        'weekly_data': weekly_data,
        'start_date': start_date,
        'end_date': end_date - timedelta(days=1),
        'previous_week': start_date - timedelta(days=7),
        'next_week': start_date + timedelta(days=7),
        'selected_date': selected_date,
    })


def send_password_reset_email(user):

    uid = urlsafe_base64_encode(force_bytes(user.pk))
    token = default_token_generator.make_token(user)

    reset_path = reverse(
        'password_reset_confirm',
        kwargs={
            'uidb64': uid,
            'token': token
        }
    )

    reset_url = f"{settings.SITE_URL.rstrip('/')}{reset_path}"

    payload = {
        "sender": {
            "name": "PlanIt-Todo",
            "email": settings.BREVO_SENDER_EMAIL
        },
        "to": [
            {
                "email": user.email
            }
        ],
        "subject": "Reset Your PlanIt-Todo Password",
        "htmlContent": f"""
            <h2>Password Reset Request</h2>
            <p>Click the link below to reset your password:</p>
            <a href="{reset_url}">Reset Password</a>
            <p>If you did not request this, ignore this email.</p>
        """
    }

    request = Request(
        "https://api.brevo.com/v3/smtp/email",
        data=json.dumps(payload).encode('utf-8'),
        headers={
            "api-key": settings.BREVO_API_KEY,
            "Content-Type": "application/json",
            "Accept": "application/json"
        },
        method="POST"
    )

    try:
        with urlopen(request, timeout=15) as response:
            return response.status in (200, 201, 202)

    except (HTTPError, URLError, TimeoutError) as error:
        print("Brevo password reset error:", error)
        return False


def password_reset_request(request):

    if request.method == 'POST':

        email = request.POST.get('email', '').strip()

        user = User.objects.filter(
            email__iexact=email,
            is_active=True
        ).first()

        if user:
            send_password_reset_email(user)

        return render(
            request,
            'tasks/password_reset_sent.html'
        )

    return render(request, 'tasks/password_reset.html')


def password_reset_confirm(request, uidb64, token):

    try:
        uid = force_str(urlsafe_base64_decode(uidb64))
        user = User.objects.get(pk=uid, is_active=True)

    except (TypeError, ValueError, OverflowError, User.DoesNotExist):
        user = None

    if user is None or not default_token_generator.check_token(user, token):
        return render(
            request,
            'tasks/password_reset.html',
            {
                'error': 'Invalid or expired password reset link.'
            }
        )

    if request.method == 'POST':

        password = request.POST.get('password')
        confirm_password = request.POST.get('confirm_password')

        if password != confirm_password:
            return render(request, 'tasks/password_reset_confirm.html', {
                'error': 'Passwords do not match.'
            })

        try:
            validate_password(password, user)

        except ValidationError as error:
            return render(request, 'tasks/password_reset_confirm.html', {
                'error': ' '.join(error.messages)
            })

        user.set_password(password)
        user.save()

        return render(
            request,
            'tasks/password_reset_complete.html'
        )

    return render(
        request,
        'tasks/password_reset_confirm.html'
    )


@login_required
def notifications(request):

    user_notifications = Notification.objects.filter(
        user=request.user
    ).order_by('-created_at')

    return render(request, 'tasks/notifications.html', {
        'notifications': user_notifications
    })


@login_required
def mark_notification_read(request, notification_id):

    if request.method == 'POST':

        notification = get_object_or_404(
            Notification,
            id=notification_id,
            user=request.user
        )

        notification.is_read = True
        notification.save(update_fields=['is_read'])

    return redirect('notifications')


@login_required
def delete_notification(request, notification_id):

    if request.method == 'POST':

        notification = get_object_or_404(
            Notification,
            id=notification_id,
            user=request.user
        )

        notification.delete()

    return redirect('notifications')


@login_required
def notification_settings(request):

    preferences, created = NotificationPreference.objects.get_or_create(
        user=request.user
    )

    if request.method == 'POST':
        preferences.upcoming_email_enabled = (
            request.POST.get('upcoming_email_enabled') == 'on'
        )

        preferences.overdue_email_enabled = (
            request.POST.get('overdue_email_enabled') == 'on'
        )

        preferences.in_app_notifications_enabled = (
            request.POST.get('in_app_notifications_enabled') == 'on'
        )

        preferences.save()

        messages.success(request, 'Notification preferences updated successfully.')

        return redirect('notification_settings')

    return render(
        request,
        'tasks/notification_settings.html',
        {'preferences': preferences}
    )


@login_required
def notification_updates(request):

    preferences, created = NotificationPreference.objects.get_or_create(
        user=request.user
    )

    unread_count = Notification.objects.filter(
        user=request.user,
        is_read=False
    ).count()

    if not preferences.in_app_notifications_enabled:
        return JsonResponse({
            'unread_count': unread_count,
            'notifications': []
        })

    try:
        last_id = int(request.GET.get('last_id', 0))
    except (ValueError, TypeError):
        last_id = 0

    new_notifications = Notification.objects.filter(
        user=request.user,
        id__gt=last_id
    ).order_by('id')[:20]

    notifications_data = [
        {
            'id': notification.id,
            'message': notification.message,
            'created_at': notification.created_at.isoformat(),
        }
        for notification in new_notifications
    ]

    return JsonResponse({
        'unread_count': unread_count,
        'notifications': notifications_data
    })
