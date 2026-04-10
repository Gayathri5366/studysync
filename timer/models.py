"""
StudySync Models
Defines StudySession and UserProfile with full ORM-level data isolation.
"""

from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone


class UserProfile(models.Model):
    """Extended profile for study goals and notification preferences."""

    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    daily_goal_minutes = models.PositiveIntegerField(default=120, help_text="Daily study goal in minutes")
    weekly_goal_minutes = models.PositiveIntegerField(default=600, help_text="Weekly study goal in minutes")
    sns_notifications_enabled = models.BooleanField(default=True, help_text="Receive SNS push notifications")
    sns_endpoint_arn = models.CharField(max_length=512, blank=True, null=True, help_text="User SNS subscription ARN")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Profile({self.user.username})"

    class Meta:
        verbose_name = "User Profile"
        verbose_name_plural = "User Profiles"


class StudySession(models.Model):
    """Represents a single timed study session for a user."""

    STATUS_ACTIVE = 'active'
    STATUS_COMPLETED = 'completed'
    STATUS_CHOICES = [
        (STATUS_ACTIVE, 'Active'),
        (STATUS_COMPLETED, 'Completed'),
    ]

    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='study_sessions',
        db_index=True
    )
    subject = models.CharField(max_length=100, blank=True, default='General', help_text="Subject or topic tag")
    started_at = models.DateTimeField(default=timezone.now, db_index=True)
    ended_at = models.DateTimeField(null=True, blank=True)
    duration_seconds = models.PositiveIntegerField(null=True, blank=True, help_text="Total duration in seconds")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=STATUS_ACTIVE, db_index=True)
    notes = models.TextField(blank=True, default='')

    class Meta:
        ordering = ['-started_at']
        verbose_name = "Study Session"
        verbose_name_plural = "Study Sessions"
        indexes = [
            models.Index(fields=['user', 'status']),
            models.Index(fields=['user', 'started_at']),
        ]

    def __str__(self):
        return f"{self.user.username} | {self.subject} | {self.started_at:%Y-%m-%d %H:%M}"

    def get_elapsed_seconds(self):
        """Return elapsed seconds for an active session (or duration if completed)."""
        if self.status == self.STATUS_COMPLETED and self.duration_seconds is not None:
            return self.duration_seconds
        return int((timezone.now() - self.started_at).total_seconds())

    def stop(self):
        """
        Atomically stop the session and record duration.
        Uses Django ORM transactions to prevent partial writes (NFR-08).
        """
        from django.db import transaction
        with transaction.atomic():
            self.ended_at = timezone.now()
            self.duration_seconds = int((self.ended_at - self.started_at).total_seconds())
            self.status = self.STATUS_COMPLETED
            self.save(update_fields=['ended_at', 'duration_seconds', 'status'])
        return self.duration_seconds
