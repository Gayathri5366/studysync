from django.contrib import admin
from .models import StudySession, UserProfile


@admin.register(StudySession)
class StudySessionAdmin(admin.ModelAdmin):
    list_display = ['user', 'subject', 'started_at', 'status', 'duration_seconds']
    list_filter = ['status', 'subject']
    search_fields = ['user__username', 'subject']
    readonly_fields = ['started_at', 'ended_at', 'duration_seconds']


@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = ['user', 'daily_goal_minutes', 'weekly_goal_minutes', 'sns_notifications_enabled']
    search_fields = ['user__username', 'user__email']
