from __future__ import annotations

import pytest
from services.xp_service import xp_service
from utils.formatting import render_progress_bar


def test_study_xp_calculation():
    # Less than 30s -> 0 XP
    assert xp_service.calculate_study_xp(20) == 0
    # 30s -> 1 XP minimum
    assert xp_service.calculate_study_xp(35) == 1
    # 25 min (1500s) -> 25 XP
    assert xp_service.calculate_study_xp(1500) == 25
    # 50 min (3000s) -> 50 XP
    assert xp_service.calculate_study_xp(3000) == 50
    # 90 min (5400s) -> 90 XP
    assert xp_service.calculate_study_xp(5400) == 90


def test_quiz_bonus_xp():
    # 100% -> +50 XP
    assert xp_service.calculate_quiz_bonus_xp(1.0) == 50
    # 92% -> +50 XP
    assert xp_service.calculate_quiz_bonus_xp(0.92) == 50
    # 80% -> +30 XP
    assert xp_service.calculate_quiz_bonus_xp(0.80) == 30
    # 60% -> +15 XP
    assert xp_service.calculate_quiz_bonus_xp(0.60) == 15
    # 40% -> +5 XP
    assert xp_service.calculate_quiz_bonus_xp(0.40) == 5


def test_streak_bonus_xp():
    assert xp_service.calculate_streak_bonus_xp(1) == 0
    assert xp_service.calculate_streak_bonus_xp(3) == 15
    assert xp_service.calculate_streak_bonus_xp(7) == 35
    assert xp_service.calculate_streak_bonus_xp(10) == 50
    # Capped at 50 XP
    assert xp_service.calculate_streak_bonus_xp(25) == 50


def test_level_progression_formula():
    # Level 1 threshold = 0
    assert xp_service.xp_for_level(1) == 0
    # Level 2 threshold = 100
    assert xp_service.xp_for_level(2) == 100
    # Level 3 threshold = 250
    assert xp_service.xp_for_level(3) == 250
    # Level 4 threshold = 450
    assert xp_service.xp_for_level(4) == 450

    # User with 0 XP -> Level 1 (0 / 100)
    lvl, curr_xp, req_xp = xp_service.calculate_level_from_xp(0)
    assert lvl == 1
    assert curr_xp == 0
    assert req_xp == 100

    # User with 150 XP -> Level 2 (50 / 150)
    lvl, curr_xp, req_xp = xp_service.calculate_level_from_xp(150)
    assert lvl == 2
    assert curr_xp == 50
    assert req_xp == 150

    # User with 1420 XP
    lvl, curr_xp, req_xp = xp_service.calculate_level_from_xp(1420)
    assert lvl >= 7


def test_render_progress_bar():
    bar_empty = render_progress_bar(0, 100, length=10)
    assert bar_empty == "░░░░░░░░░░"

    bar_full = render_progress_bar(100, 100, length=10)
    assert bar_full == "██████████"

    bar_half = render_progress_bar(50, 100, length=10)
    assert bar_half == "█████░░░░░"
