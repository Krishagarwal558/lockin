from __future__ import annotations

import math
from typing import Tuple


class XPService:
    """
    Handles all XP computations, level progression formulas, and quiz/streak bonuses.
    """

    @staticmethod
    def calculate_study_xp(actual_seconds: int) -> int:
        """
        1 minute studied = 1 XP.
        Minimum 1 XP if studied for at least 30 seconds.
        """
        if actual_seconds < 30:
            return 0
        return max(1, actual_seconds // 60)

    @staticmethod
    def calculate_quiz_bonus_xp(score_ratio: float) -> int:
        """
        Calculates bonus XP based on quiz performance (0.0 to 1.0):
        - 90–100% = +50 XP
        - 70–89%  = +30 XP
        - 50–69%  = +15 XP
        - <50%    = +5 XP
        """
        pct = score_ratio * 100 if score_ratio <= 1.0 else score_ratio
        if pct >= 90.0:
            return 50
        elif pct >= 70.0:
            return 30
        elif pct >= 50.0:
            return 15
        else:
            return 5

    @staticmethod
    def calculate_streak_bonus_xp(streak_days: int) -> int:
        """
        Awards +5 XP per consecutive streak day, capped at +50 XP.
        """
        if streak_days <= 1:
            return 0
        return min(streak_days * 5, 50)

    @staticmethod
    def xp_for_level(level: int) -> int:
        """
        Returns total cumulative XP required to reach a specific level.
        Level 1 -> 0 XP
        Level 2 -> 100 XP
        Level 3 -> 250 XP
        Level 4 -> 450 XP
        Formula: For Level L >= 2, cumulative XP = 50 * (L - 1) * (L + 2) // 2
        """
        if level <= 1:
            return 0
        # Level 2 -> 50 * 1 * 4 // 2 = 100
        # Level 3 -> 50 * 2 * 5 // 2 = 250
        # Level 4 -> 50 * 3 * 6 // 2 = 450
        # Level 5 -> 50 * 4 * 7 // 2 = 700
        return 25 * (level - 1) * (level + 2)

    @classmethod
    def calculate_level_from_xp(cls, total_xp: int) -> Tuple[int, int, int]:
        """
        Given a user's total XP, calculates:
        (current_level, xp_progress_in_level, xp_needed_for_next_level)
        """
        total_xp = max(0, total_xp)
        level = 1
        while True:
            next_req = cls.xp_for_level(level + 1)
            if total_xp < next_req:
                break
            level += 1

        curr_level_base = cls.xp_for_level(level)
        next_level_base = cls.xp_for_level(level + 1)
        xp_in_level = total_xp - curr_level_base
        xp_needed = next_level_base - curr_level_base

        return level, xp_in_level, xp_needed


xp_service = XPService()
