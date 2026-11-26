from django.shortcuts import render, redirect
from django.contrib.auth.models import User
from django.contrib.auth import authenticate, login
from django.contrib.auth.decorators import login_required
from django.contrib.auth import logout
from .models import Task
from django.core.paginator import Paginator
from django.contrib.auth import update_session_auth_hash
from django.utils import timezone
from django.db.models import Case, When, Value, IntegerField

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
    tasks = Task.objects.filter(user=request.user)
    total_tasks = tasks.count()
    completed_tasks = tasks.filter(status=True).count()
    pending_tasks = tasks.filter(status=False).count()
    overdue_tasks = Task.objects.filter(
    user=request.user,
    status=False,
    due_date__lt=timezone.now()
)
    if search_query:
        tasks = tasks.filter(title__icontains=search_query)
    if status == 'pending':
        tasks = tasks.filter(status=False)

    elif status == 'completed':
        tasks = tasks.filter(status=True)

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
    'total_tasks': total_tasks,
    'completed_tasks': completed_tasks,
    'pending_tasks': pending_tasks,
    'selected_sort': sort_by,
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
        
        Task.objects.create(
            user=request.user,
            title=title,
            description=description,
            priority=priority,
            due_date=due_date if due_date else None
        )

        return redirect('dashboard')
    

@login_required
def edit_task(request, task_id):

    task = Task.objects.get(id=task_id, user=request.user)

    if request.method == 'POST':

        task.title = request.POST.get('title')
        task.description = request.POST.get('description')
        due_date = request.POST.get('due_date')
        task.due_date = due_date if due_date else None
        task.priority = request.POST.get('priority')
        task.save()

        return redirect('dashboard')

    return render(request, 'tasks/edit_task.html', {
        'task': task
    })

@login_required
def delete_task(request, task_id):

    if request.method == 'POST':

        task = Task.objects.get(id=task_id, user=request.user)

        task.delete()

    return redirect('dashboard')

@login_required
def toggle_task_status(request, task_id):

    if request.method == 'POST':

        task = Task.objects.get(id=task_id, user=request.user)

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