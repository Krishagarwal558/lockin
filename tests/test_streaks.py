from __future__ import annotations

from datetime import datetime, timezone, timedelta
import pytest
from services.streak_service import streak_service


def test_first_session_streak():
    now = datetime(2026, 10, 10, 12, 0, tzinfo=timezone.utc)
    res = streak_service.evaluate_streak_update(
        current_streak=0,
        longest_streak=0,
        last_study_date=None,
        now=now,
    )
    assert res["new_current_streak"] == 1
    assert res["new_longest_streak"] == 1
    assert res["streak_increased"] is True
    assert res["streak_maintained"] is False


def test_same_day_study_maintains_streak():
    last_date = datetime(2026, 10, 10, 8, 0, tzinfo=timezone.utc)
    now = datetime(2026, 10, 10, 18, 0, tzinfo=timezone.utc) # same day
    res = streak_service.evaluate_streak_update(
        current_streak=5,
        longest_streak=10,
        last_study_date=last_date,
        now=now,
    )
    assert res["new_current_streak"] == 5
    assert res["new_longest_streak"] == 10
    assert res["streak_increased"] is False
    assert res["streak_maintained"] is True


def test_consecutive_day_increments_streak():
    last_date = datetime(2026, 10, 9, 20, 0, tzinfo=timezone.utc)
    now = datetime(2026, 10, 10, 14, 0, tzinfo=timezone.utc) # 1 day later
    res = streak_service.evaluate_streak_update(
        current_streak=7,
        longest_streak=7,
        last_study_date=last_date,
        now=now,
    )
    assert res["new_current_streak"] == 8
    assert res["new_longest_streak"] == 8
    assert res["streak_increased"] is True
    assert res["streak_maintained"] is False


def test_missed_day_resets_streak_gracefully():
    last_date = datetime(2026, 10, 5, 12, 0, tzinfo=timezone.utc)
    now = datetime(2026, 10, 10, 12, 0, tzinfo=timezone.utc) # 5 days later
    res = streak_service.evaluate_streak_update(
        current_streak=12,
        longest_streak=15,
        last_study_date=last_date,
        now=now,
    )
    assert res["new_current_streak"] == 1
    assert res["new_longest_streak"] == 15
    assert res["streak_reset_from"] == 12
    assert "The streak ended at 12 days" in res["message"]
    assert "No big deal" in res["message"]
