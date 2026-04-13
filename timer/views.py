"""
StudySync Views
All views require authentication. All queries are scoped to request.user (NFR-03).
"""

import logging
from datetime import date, timedelta

from django.contrib.auth import login
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.contrib import messages
from django.db import transaction
from django.http import JsonResponse
from django.shortcuts import render, redirect, get_object_or_404
from django.utils import timezone
from django.core.paginator import Paginator

from .models import StudySession, UserProfile
from .forms import RegisterForm, ProfileForm, SessionStartForm
from . import sns_service, cloudwatch_service
from studytimer_analytics.aggregators import ReportAggregator
from studytimer_analytics.evaluators import StudyGoalEvaluator
from studytimer_analytics.formatters import DurationFormatter

logger = logging.getLogger(__name__)


# ── Auth ──────────────────────────────────────────────────────────────────────

def register_view(request):
    """FR-01: User Registration."""
    if request.user.is_authenticated:
        return redirect('dashboard')
    if request.method == 'POST':
        form = RegisterForm(request.POST)
        if form.is_valid():
            user = form.save()
            UserProfile.objects.create(user=user)
            login(request, user)
            logger.info(f"New user registered: {user.username}")
            return redirect('dashboard')
    else:
        form = RegisterForm()
    return render(request, 'registration/register.html', {'form': form})


# ── Dashboard ─────────────────────────────────────────────────────────────────

@login_required
def dashboard(request):
    """
    FR-04, FR-05: Show active session with live timer, or session start form.
    Timer state persists across page refreshes by reading elapsed time from DB.
    """
    active_session = StudySession.objects.filter(
        user=request.user, status=StudySession.STATUS_ACTIVE
    ).first()

    elapsed = active_session.get_elapsed_seconds() if active_session else 0
    form = SessionStartForm()

    active_count = StudySession.objects.filter(status=StudySession.STATUS_ACTIVE).count()
    cloudwatch_service.record_active_sessions(active_count)

    context = {
        'active_session': active_session,
        'elapsed_seconds': elapsed,
        'form': form,
    }
    return render(request, 'timer/dashboard.html', context)


@login_required
def start_session(request):
    """FR-04: Start a new study session. Only one active session allowed per user."""
    if request.method == 'POST':
        # Enforce one active session per user
        if StudySession.objects.filter(user=request.user, status=StudySession.STATUS_ACTIVE).exists():
            messages.warning(request, "You already have an active session running.")
            return redirect('dashboard')

        form = SessionStartForm(request.POST)
        if form.is_valid():
            session = StudySession.objects.create(
                user=request.user,
                subject=form.cleaned_data.get('subject', 'General') or 'General',
            )
            logger.info(f"Session started: user={request.user.username} session_id={session.pk}")
            sns_service.notify_session_started(request.user, session)
            cloudwatch_service.record_session_started(request.user, session)
            messages.success(request, f"Study session started! Subject: {session.subject}")
    return redirect('dashboard')


@login_required
def stop_session(request):
    """FR-06: Stop active session, persist duration atomically, trigger SNS."""
    if request.method == 'POST':
        session = get_object_or_404(
            StudySession,
            user=request.user,
            status=StudySession.STATUS_ACTIVE
        )
        duration = session.stop()
        logger.info(f"Session stopped: user={request.user.username} session_id={session.pk} duration={duration}s")
        sns_service.notify_session_completed(request.user, session)
        cloudwatch_service.record_session_completed(request.user, session)

        # Check goals after session (FR-12)
        _check_and_notify_goals(request.user)

        fmt = DurationFormatter()
        messages.success(request, f"Session complete! Duration: {fmt.format_duration(duration)}")
    return redirect('dashboard')


def _check_and_notify_goals(user):
    """Check daily/weekly goal achievement and send SNS if newly achieved."""
    try:
        profile = user.profile
        evaluator = StudyGoalEvaluator()
        aggregator = ReportAggregator(user)

        today = date.today()
        daily_report = aggregator.daily_report(today)
        daily_minutes = daily_report['total_seconds'] // 60
        if evaluator.is_goal_achieved(daily_minutes, profile.daily_goal_minutes):
            sns_service.notify_goal_achieved(user, 'daily', daily_minutes, profile.daily_goal_minutes)
            cloudwatch_service.record_goal_achieved(user, 'daily')

        weekly_report = aggregator.weekly_report(today)
        weekly_minutes = weekly_report['total_seconds'] // 60
        if evaluator.is_goal_achieved(weekly_minutes, profile.weekly_goal_minutes):
            sns_service.notify_goal_achieved(user, 'weekly', weekly_minutes, profile.weekly_goal_minutes)
            cloudwatch_service.record_goal_achieved(user, 'weekly')
    except Exception as exc:
        logger.error(f"Goal check failed for {user.username}: {exc}")


# ── AJAX Timer Endpoint ───────────────────────────────────────────────────────

@login_required
def timer_status(request):
    """
    FR-05: AJAX endpoint returning current elapsed seconds for the active session.
    Allows the JS timer to sync with DB state. Response target: <300ms (NFR-04).
    """
    session = StudySession.objects.filter(
        user=request.user, status=StudySession.STATUS_ACTIVE
    ).first()
    if session:
        return JsonResponse({'active': True, 'elapsed': session.get_elapsed_seconds()})
    return JsonResponse({'active': False, 'elapsed': 0})


# ── Reports ───────────────────────────────────────────────────────────────────

@login_required
def daily_report(request):
    """FR-07: Daily report with Chart.js bar chart."""
    report_date = _parse_date(request.GET.get('date')) or date.today()
    aggregator = ReportAggregator(request.user)
    report = aggregator.daily_report(report_date)
    fmt = DurationFormatter()
    context = {
        'report': report,
        'report_date': report_date,
        'total_formatted': fmt.format_duration(report['total_seconds']),
        'avg_formatted': fmt.format_duration(report['avg_session_seconds']),
        'chart_labels': list(report['subject_breakdown'].keys()),
        'chart_data': [v // 60 for v in report['subject_breakdown'].values()],
    }
    return render(request, 'timer/daily_report.html', context)


@login_required
def weekly_report(request):
    """FR-08: Rolling 7-day report with Chart.js daily bar chart."""
    end_date = _parse_date(request.GET.get('end')) or date.today()
    aggregator = ReportAggregator(request.user)
    report = aggregator.weekly_report(end_date)
    fmt = DurationFormatter()
    context = {
        'report': report,
        'end_date': end_date,
        'start_date': end_date - timedelta(days=6),
        'total_formatted': fmt.format_duration(report['total_seconds']),
        'chart_labels': report['daily_labels'],
        'chart_data': [v // 60 for v in report['daily_totals']],
    }
    return render(request, 'timer/weekly_report.html', context)


@login_required
def session_history(request):
    """FR-09: Paginated session history with subject filter."""
    subject_filter = request.GET.get('subject', '')
    qs = StudySession.objects.filter(
        user=request.user,
        status=StudySession.STATUS_COMPLETED
    ).order_by('-started_at')

    if subject_filter:
        qs = qs.filter(subject__icontains=subject_filter)

    subjects = StudySession.objects.filter(
        user=request.user
    ).values_list('subject', flat=True).distinct()

    paginator = Paginator(qs, 15)
    page_obj = paginator.get_page(request.GET.get('page'))
    fmt = DurationFormatter()

    sessions_display = [
        {
            'session': s,
            'duration_fmt': fmt.format_duration(s.duration_seconds or 0),
        }
        for s in page_obj
    ]

    context = {
        'page_obj': page_obj,
        'sessions_display': sessions_display,
        'subject_filter': subject_filter,
        'subjects': subjects,
    }
    return render(request, 'timer/session_history.html', context)


# ── Profile ───────────────────────────────────────────────────────────────────

@login_required
def profile_settings(request):
    """FR-11: Update daily/weekly goals and SNS notification preference."""
    profile, _ = UserProfile.objects.get_or_create(user=request.user)
    if request.method == 'POST':
        form = ProfileForm(request.POST, instance=profile)
        if form.is_valid():
            form.save()
            messages.success(request, "Profile updated successfully.")
            return redirect('profile_settings')
    else:
        form = ProfileForm(instance=profile)
    return render(request, 'timer/profile.html', {'form': form, 'profile': profile})


# ── Admin ─────────────────────────────────────────────────────────────────────

@login_required
def admin_stats(request):
    """AR-01: System-wide statistics (admin only)."""
    if not request.user.is_staff:
        messages.error(request, "Access denied.")
        return redirect('dashboard')

    from django.contrib.auth.models import User as AuthUser
    context = {
        'total_users': AuthUser.objects.filter(is_active=True).count(),
        'total_sessions': StudySession.objects.filter(status=StudySession.STATUS_COMPLETED).count(),
        'active_sessions': StudySession.objects.filter(status=StudySession.STATUS_ACTIVE).count(),
    }
    return render(request, 'timer/admin_stats.html', context)


@login_required
def admin_user_list(request):
    """AR-02, AR-03: User list with activate/deactivate."""
    if not request.user.is_staff:
        messages.error(request, "Access denied.")
        return redirect('dashboard')

    users = User.objects.all().select_related('profile').order_by('-date_joined')
    return render(request, 'timer/admin_users.html', {'users': users})


@login_required
def delete_session(request, session_id):
    """DELETE: Allow a user to delete one of their own completed sessions."""
    if request.method == 'POST':
        session = get_object_or_404(
            StudySession,
            pk=session_id,
            user=request.user,
            status=StudySession.STATUS_COMPLETED
        )
        session.delete()
        logger.info(f"Session deleted: user={request.user.username} session_id={session_id}")
        messages.success(request, "Study session deleted.")
    return redirect('session_history')


@login_required
def delete_user(request, user_id):
    """DELETE: Admin-only. Permanently delete a user account and all their data."""
    if not request.user.is_staff:
        messages.error(request, "Access denied.")
        return redirect('dashboard')
    if request.method == 'POST':
        target = get_object_or_404(User, pk=user_id)
        if target == request.user:
            messages.error(request, "You cannot delete your own account.")
            return redirect('admin_user_list')
        username = target.username
        target.delete()
        logger.info(f"Admin {request.user.username} deleted user {username}")
        messages.success(request, f"User '{username}' and all their data have been permanently deleted.")
    return redirect('admin_user_list')


@login_required
def toggle_user_status(request, user_id):
    """AR-03: Activate or deactivate a user account."""
    if not request.user.is_staff:
        messages.error(request, "Access denied.")
        return redirect('dashboard')
    if request.method == 'POST':
        target = get_object_or_404(User, pk=user_id)
        target.is_active = not target.is_active
        target.save(update_fields=['is_active'])
        action = "activated" if target.is_active else "deactivated"
        logger.info(f"Admin {request.user.username} {action} user {target.username}")
        messages.success(request, f"User {target.username} {action}.")
    return redirect('admin_user_list')


# ── Helpers ───────────────────────────────────────────────────────────────────

def _parse_date(date_str):
    """Parse a YYYY-MM-DD string to a date object, returning None on failure."""
    if not date_str:
        return None
    try:
        return date.fromisoformat(date_str)
    except ValueError:
        return None