"""
Presentation helpers for the PlanIt templates.

These tags and filters only format data that views already provide. They do
not change any task, notification or authentication behaviour.
"""

from datetime import timedelta

from django import template
from django.utils import timezone
from django.utils.html import format_html

from ..models import Notification

register = template.Library()


@register.simple_tag
def icon(name, size=16, css_class=''):
    """Render an icon from the inline SVG sprite (partials/icons.html)."""
    return format_html(
        '<svg class="icon {}" width="{}" height="{}" aria-hidden="true" '
        'focusable="false"><use href="#i-{}"></use></svg>',
        css_class, size, size, name,
    )


@register.simple_tag(takes_context=True)
def notification_summary(context):
    """Unread count and newest notification id for the signed-in user."""
    request = context.get('request')
    user = getattr(request, 'user', None)

    if user is None or not user.is_authenticated:
        return {'unread': 0, 'latest_id': 0}

    notifications = Notification.objects.filter(user=user)

    latest_id = (
        notifications.order_by('-id').values_list('id', flat=True).first()
    )

    return {
        'unread': notifications.filter(is_read=False).count(),
        'latest_id': latest_id or 0,
    }


@register.filter
def due_state(task):
    """Classify a task's due date: overdue, today, tomorrow, week or later."""
    due = getattr(task, 'due_date', None)

    if not due:
        return ''

    if getattr(task, 'status', False):
        return 'done'

    if due < timezone.now():
        return 'overdue'

    due_day = timezone.localtime(due).date()
    today = timezone.localdate()

    if due_day == today:
        return 'today'

    if due_day == today + timedelta(days=1):
        return 'tomorrow'

    if due_day <= today + timedelta(days=6):
        return 'week'

    return 'later'


@register.filter
def add_days(value, days):
    try:
        return value + timedelta(days=int(days))
    except (TypeError, ValueError):
        return value


@register.filter
def display_name(user):
    return (getattr(user, 'first_name', '') or getattr(user, 'username', '')).strip()


@register.filter
def initials(user):
    first = (getattr(user, 'first_name', '') or '').strip()
    last = (getattr(user, 'last_name', '') or '').strip()

    if first or last:
        return ((first[:1]) + (last[:1])).upper() or '?'

    username = (getattr(user, 'username', '') or '?').strip()
    return username[:2].upper()


@register.filter
def completed_count(tasks):
    return sum(1 for task in tasks if getattr(task, 'status', False))


@register.filter
def minus(value, amount):
    try:
        return int(value) - int(amount)
    except (TypeError, ValueError):
        return value


@register.filter
def percent_of(part, whole):
    try:
        part, whole = float(part), float(whole)
    except (TypeError, ValueError):
        return 0
    return round(part * 100 / whole) if whole else 0


@register.simple_tag
def local_today():
    return timezone.localdate()


@register.simple_tag
def week_strip(selected):
    start = selected - timedelta(days=selected.weekday())
    return [start + timedelta(days=offset) for offset in range(7)]


@register.simple_tag
def week_stats(weekly_data):
    total = sum(len(day['tasks']) for day in weekly_data)
    done = sum(
        1 for day in weekly_data for task in day['tasks'] if task.status
    )
    return {
        'total': total,
        'done': done,
        'percent': round(done * 100 / total) if total else 0,
    }


@register.simple_tag
def page_window(page_obj):
    """Compact page range, e.g. 1 … 4 5 6 … 12."""
    return page_obj.paginator.get_elided_page_range(
        page_obj.number, on_each_side=1, on_ends=1
    )
