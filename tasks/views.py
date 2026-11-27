
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.models import User
from django.contrib.auth import authenticate, login
from django.contrib.auth.decorators import login_required
from django.contrib.auth import logout
from .models import Task
from django.core.paginator import Paginator
from django.contrib.auth import update_session_auth_hash
from django.utils import timezone
from django.db.models import Case, When, Value, IntegerField
from datetime import timedelta
import calendar
from datetime import datetime, timedelta

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

        User.objects.create_user(
            username=username,
            first_name=first_name,
            last_name=last_name,
            email=email,
            password=password
        )

        return redirect('login')

    return render(request, 'tasks/register.html')


@login_required
def dashboard(request):

    status = request.GET.get('status')
    search_query = request.GET.get('search')
    category = request.GET.get('category')
    priority = request.GET.get('priority')
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
    })


def user_login(request):

    if request.method == 'POST':

        username = request.POST.get('username')
        password = request.POST.get('password')

        user = authenticate(
            request,
            username=username,
            password=password
        )

        if user is not None:
            login(request, user)
            return redirect('dashboard')

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

        Task.objects.create(
            user=request.user,
            title=title,
            description=description,
            priority=priority,
            due_date=due_date if due_date else None,
            category=category
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