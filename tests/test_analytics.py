"""
StudySync — Unit Tests for studytimer_analytics library
NFR-10: All four OOP classes tested with ≥70% code coverage.
Run: pytest tests/ -v --cov=studytimer_analytics --cov-report=term-missing
"""

import sys
import os
import pytest
from datetime import datetime, timezone as dt_tz, timedelta

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from studytimer_analytics.timers import SessionTimer
from studytimer_analytics.formatters import DurationFormatter
from studytimer_analytics.evaluators import StudyGoalEvaluator


# ── SessionTimer Tests ────────────────────────────────────────────────────────

class TestSessionTimer:
    """Unit tests for SessionTimer (NFR-10)."""

    def test_active_session_elapsed_is_positive(self):
        started = datetime.now(dt_tz.utc) - timedelta(minutes=5)
        timer = SessionTimer(started_at=started)
        assert timer.elapsed_seconds() >= 300

    def test_completed_session_exact_duration(self):
        started = datetime(2025, 1, 1, 10, 0, 0, tzinfo=dt_tz.utc)
        ended = datetime(2025, 1, 1, 11, 30, 0, tzinfo=dt_tz.utc)
        timer = SessionTimer(started_at=started, ended_at=ended)
        assert timer.elapsed_seconds() == 5400  # 90 minutes

    def test_is_active_true_when_no_end(self):
        timer = SessionTimer(started_at=datetime.now(dt_tz.utc))
        assert timer.is_active() is True

    def test_is_active_false_when_ended(self):
        started = datetime(2025, 1, 1, 9, 0, 0, tzinfo=dt_tz.utc)
        ended = datetime(2025, 1, 1, 10, 0, 0, tzinfo=dt_tz.utc)
        timer = SessionTimer(started_at=started, ended_at=ended)
        assert timer.is_active() is False

    def test_format_hms_zero(self):
        started = datetime.now(dt_tz.utc)
        ended = started
        timer = SessionTimer(started_at=started, ended_at=ended)
        assert timer.format_hms() == "00:00:00"

    def test_format_hms_one_hour(self):
        started = datetime(2025, 1, 1, 10, 0, 0, tzinfo=dt_tz.utc)
        ended = datetime(2025, 1, 1, 11, 0, 0, tzinfo=dt_tz.utc)
        timer = SessionTimer(started_at=started, ended_at=ended)
        assert timer.format_hms() == "01:00:00"

    def test_format_hms_complex(self):
        started = datetime(2025, 1, 1, 10, 0, 0, tzinfo=dt_tz.utc)
        ended = datetime(2025, 1, 1, 11, 23, 45, tzinfo=dt_tz.utc)
        timer = SessionTimer(started_at=started, ended_at=ended)
        assert timer.format_hms() == "01:23:45"

    def test_elapsed_minutes(self):
        started = datetime(2025, 1, 1, 10, 0, 0, tzinfo=dt_tz.utc)
        ended = datetime(2025, 1, 1, 10, 30, 0, tzinfo=dt_tz.utc)
        timer = SessionTimer(started_at=started, ended_at=ended)
        assert timer.elapsed_minutes() == 30.0

    def test_naive_datetime_handled(self):
        """SessionTimer should handle naive datetimes by assuming UTC."""
        started = datetime(2025, 1, 1, 10, 0, 0)  # naive
        ended = datetime(2025, 1, 1, 10, 1, 0)    # naive
        timer = SessionTimer(started_at=started, ended_at=ended)
        assert timer.elapsed_seconds() == 60

    def test_elapsed_never_negative(self):
        # If end is before start (data error), should return 0
        started = datetime(2025, 1, 1, 11, 0, 0, tzinfo=dt_tz.utc)
        ended = datetime(2025, 1, 1, 10, 0, 0, tzinfo=dt_tz.utc)
        timer = SessionTimer(started_at=started, ended_at=ended)
        assert timer.elapsed_seconds() == 0


# ── DurationFormatter Tests ───────────────────────────────────────────────────

class TestDurationFormatter:
    """Unit tests for DurationFormatter (NFR-10)."""

    def setup_method(self):
        self.fmt = DurationFormatter()

    def test_format_duration_zero(self):
        assert self.fmt.format_duration(0) == "0 sec"

    def test_format_duration_seconds_only(self):
        assert self.fmt.format_duration(45) == "45 sec"

    def test_format_duration_minutes(self):
        assert self.fmt.format_duration(90) == "1 min 30 sec"

    def test_format_duration_hours(self):
        assert self.fmt.format_duration(3661) == "1 hr 1 min 1 sec"

    def test_format_duration_exact_hour(self):
        assert self.fmt.format_duration(3600) == "1 hr 0 min 0 sec"

    def test_format_hms_zero(self):
        assert self.fmt.format_hms(0) == "00:00:00"

    def test_format_hms_full(self):
        assert self.fmt.format_hms(3661) == "01:01:01"

    def test_format_hms_large(self):
        assert self.fmt.format_hms(36000) == "10:00:00"

    def test_format_minutes_under_hour(self):
        assert self.fmt.format_minutes(45) == "45 min"

    def test_format_minutes_over_hour(self):
        assert self.fmt.format_minutes(90) == "1 hr 30 min"

    def test_format_minutes_zero(self):
        assert self.fmt.format_minutes(0) == "0 min"

    def test_seconds_to_minutes(self):
        assert self.fmt.seconds_to_minutes(120) == 2.0

    def test_format_duration_negative_treated_as_zero(self):
        assert self.fmt.format_duration(-10) == "0 sec"


# ── StudyGoalEvaluator Tests ──────────────────────────────────────────────────

class TestStudyGoalEvaluator:
    """Unit tests for StudyGoalEvaluator (NFR-10)."""

    def setup_method(self):
        self.ev = StudyGoalEvaluator()

    def test_goal_achieved_exact(self):
        assert self.ev.is_goal_achieved(120, 120) is True

    def test_goal_achieved_over(self):
        assert self.ev.is_goal_achieved(150, 120) is True

    def test_goal_not_achieved(self):
        assert self.ev.is_goal_achieved(90, 120) is False

    def test_goal_zero_target(self):
        assert self.ev.is_goal_achieved(50, 0) is False

    def test_progress_percent_half(self):
        assert self.ev.progress_percent(60, 120) == 50.0

    def test_progress_percent_over_100(self):
        assert self.ev.progress_percent(200, 100) == 100.0

    def test_progress_percent_zero_goal(self):
        assert self.ev.progress_percent(50, 0) == 0.0

    def test_remaining_minutes(self):
        assert self.ev.remaining_minutes(90, 120) == 30

    def test_remaining_minutes_achieved(self):
        assert self.ev.remaining_minutes(130, 120) == 0

    def test_evaluate_returns_dict(self):
        result = self.ev.evaluate(100, 120)
        assert isinstance(result, dict)
        assert 'achieved' in result
        assert 'progress_percent' in result
        assert 'remaining_minutes' in result

    def test_evaluate_not_achieved(self):
        result = self.ev.evaluate(60, 120)
        assert result['achieved'] is False
        assert result['progress_percent'] == 50.0
        assert result['remaining_minutes'] == 60

    def test_evaluate_achieved(self):
        result = self.ev.evaluate(120, 120)
        assert result['achieved'] is True
        assert result['remaining_minutes'] == 0


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
