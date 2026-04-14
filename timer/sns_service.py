"""
StudySync SNS Service
Handles all AWS SNS publish operations for session events, goal achievements,
and admin alerts.
"""

import boto3
import logging
from django.conf import settings

logger = logging.getLogger(__name__)


def _get_sns_client():
    """Return a boto3 SNS client using IAM role credentials."""
    session = boto3.Session()
    return session.client(
        'sns',
        region_name=settings.AWS_SNS_REGION,
    )


def _publish(topic_arn: str, subject: str, message: str) -> bool:
    """
    Publish a message to an SNS topic.
    Returns True on success, False on failure.
    """
    if not topic_arn:
        logger.warning("SNS publish skipped — no topic ARN configured.")
        return False
    try:
        client = _get_sns_client()
        response = client.publish(
            TopicArn=topic_arn,
            Subject=subject,
            Message=message,
        )
        logger.info(f"SNS published MessageId={response['MessageId']} to {topic_arn}")
        return True
    except Exception as exc:
        logger.error(f"SNS publish failed: {exc}")
        return False


# ── Student Notifications ──────────────────────────────────────────────────────

def notify_session_started(user, session):
    """Publish an SNS notification when a student starts a study session."""
    if not _should_notify(user):
        return
    subject = f"[StudySync] Session Started — {session.subject}"
    message = (
        f"Hi {user.get_full_name() or user.username},\n\n"
        f"Your study session has started!\n"
        f"Subject : {session.subject}\n"
        f"Started : {session.started_at.strftime('%Y-%m-%d %H:%M UTC')}\n\n"
        f"Good luck! StudySync"
    )
    _publish(settings.SNS_STUDENT_TOPIC_ARN, subject, message)


def notify_session_completed(user, session):
    """Publish an SNS notification when a student completes a study session."""
    if not _should_notify(user):
        return
    from studytimer_analytics.formatters import DurationFormatter
    fmt = DurationFormatter()
    duration_str = fmt.format_duration(session.duration_seconds or 0)
    subject = f"[StudySync] Session Complete — {duration_str}"
    message = (
        f"Hi {user.get_full_name() or user.username},\n\n"
        f"Great work! Your session is complete.\n"
        f"Subject  : {session.subject}\n"
        f"Duration : {duration_str}\n"
        f"Ended    : {session.ended_at.strftime('%Y-%m-%d %H:%M UTC')}\n\n"
        f"Keep it up! StudySync"
    )
    _publish(settings.SNS_STUDENT_TOPIC_ARN, subject, message)


def notify_goal_achieved(user, goal_type: str, total_minutes: int, goal_minutes: int):
    """Publish an SNS notification when a student achieves a daily or weekly goal."""
    if not _should_notify(user):
        return
    subject = f"[StudySync] {goal_type.capitalize()} Goal Achieved!"
    message = (
        f"Hi {user.get_full_name() or user.username},\n\n"
        f"Congratulations! You've achieved your {goal_type} study goal.\n"
        f"Goal    : {goal_minutes} minutes\n"
        f"Studied : {total_minutes} minutes\n\n"
        f"Excellent focus! StudySync"
    )
    _publish(settings.SNS_STUDENT_TOPIC_ARN, subject, message)


# ── Admin Notifications ────────────────────────────────────────────────────────

def notify_admin_critical_error(error_context: dict):
    """Publish a critical error alert to the admin SNS topic."""
    import json
    subject = "[StudySync ALERT] Critical Error Detected"
    message = (
        f"A critical error was detected in StudySync.\n\n"
        f"Details:\n{json.dumps(error_context, indent=2, default=str)}\n\n"
        f"Please investigate via AWS CloudWatch Logs."
    )
    _publish(settings.SNS_ADMIN_TOPIC_ARN, subject, message)


def notify_admin_health_degraded(environment_health: str):
    """Publish a health degraded alert to the admin topic."""
    subject = f"[StudySync ALERT] Environment Health: {environment_health}"
    message = (
        f"StudySync environment health has degraded.\n"
        f"Status: {environment_health}\n\n"
        f"Check CloudWatch alarms and EC2 health dashboard."
    )
    _publish(settings.SNS_ADMIN_TOPIC_ARN, subject, message)


# ── Helpers ───────────────────────────────────────────────────────────────────

def _should_notify(user) -> bool:
    """Return True if the user has SNS notifications enabled."""
    try:
        return user.profile.sns_notifications_enabled
    except Exception:
        return False