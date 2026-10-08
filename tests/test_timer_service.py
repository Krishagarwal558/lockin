from __future__ import annotations

import pytest
from utils.time import parse_duration_string, format_duration, format_duration_clock
from services.timer_service import timer_service


def test_duration_string_parsing():
    # Plain numbers
    assert parse_duration_string("25") == 25 * 60
    assert parse_duration_string("60") == 60 * 60

    # Minutes format
    assert parse_duration_string("45m") == 45 * 60
    assert parse_duration_string("45 mins") == 45 * 60
    assert parse_duration_string("90 minutes") == 90 * 60

    # Hours format
    assert parse_duration_string("1h") == 3600
    assert parse_duration_string("2 hours") == 7200
    assert parse_duration_string("1h 30m") == 5400

    # Invalid / out of bounds
    assert parse_duration_string("0") is None
    assert parse_duration_string("abc") is None
    assert parse_duration_string("1000h") is None


def test_duration_formatters():
    assert format_duration(3600) == "1h 00m"
    assert format_duration(3665) == "1h 01m"
    assert format_duration(1500) == "25m 00s"
    assert format_duration(45) == "45s"

    assert format_duration_clock(3600) == "01:00:00"
    assert format_duration_clock(1500) == "00:25:00"
    assert format_duration_clock(7325) == "02:02:05"


def test_timer_registration_and_cancellation():
    timer = timer_service.register_timer(
        session_id=999,
        user_id=1,
        discord_user_id=123456789,
        channel_id=111,
        guild_id=222,
        subject="Physics",
        planned_seconds=3600,
    )
    assert timer_service.is_user_studying(123456789) is True
    assert timer.subject == "Physics"
    assert timer.planned_seconds == 3600

    cancelled = timer_service.cancel_timer(123456789)
    assert cancelled is not None
    assert timer_service.is_user_studying(123456789) is False
