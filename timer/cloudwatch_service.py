"""
StudySync CloudWatch Service
Publishes custom metrics to AWS CloudWatch for operational observability.
"""

import logging
import boto3
from botocore.exceptions import BotoCoreError, ClientError
from django.conf import settings

logger = logging.getLogger(__name__)
NAMESPACE = "StudySync"


def _get_client():
    return boto3.client("cloudwatch", region_name=settings.AWS_CLOUDWATCH_REGION)


def _put_metric(metric_name, value, unit, dimensions=None):
    if not getattr(settings, "CLOUDWATCH_ENABLED", False):
        logger.debug(f"CloudWatch disabled — skipping {metric_name}")
        return False
    metric_data = {"MetricName": metric_name, "Value": value, "Unit": unit}
    if dimensions:
        metric_data["Dimensions"] = dimensions
    try:
        _get_client().put_metric_data(Namespace=NAMESPACE, MetricData=[metric_data])
        logger.debug(f"CloudWatch metric: {metric_name}={value} {unit}")
        return True
    except (BotoCoreError, ClientError) as exc:
        logger.error(f"CloudWatch failed [{metric_name}]: {exc}")
        return False


def record_session_started(user, session):
    _put_metric("SessionStarted", 1, "Count",
                [{"Name": "Environment", "Value": settings.CLOUDWATCH_ENV}])


def record_session_completed(user, session):
    _put_metric("SessionCompleted", 1, "Count",
                [{"Name": "Environment", "Value": settings.CLOUDWATCH_ENV}])
    if session.duration_seconds:
        _put_metric("SessionDuration", float(session.duration_seconds), "Seconds",
                    [{"Name": "Environment", "Value": settings.CLOUDWATCH_ENV}])


def record_active_sessions(count):
    _put_metric("ActiveSessions", float(count), "Count",
                [{"Name": "Environment", "Value": settings.CLOUDWATCH_ENV}])


def record_goal_achieved(user, goal_type):
    _put_metric("GoalAchieved", 1, "Count", [
        {"Name": "Environment", "Value": settings.CLOUDWATCH_ENV},
        {"Name": "GoalType", "Value": goal_type},
    ])