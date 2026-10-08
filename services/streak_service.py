from __future__ import annotations

from datetime import datetime, timezone, date
from typing import Optional, Tuple, Dict, Any


class StreakService:
    """
    Manages daily study streaks, friendly reset messages, and longest streak tracking.
    """

    @staticmethod
    def evaluate_streak_update(
        current_streak: int,
        longest_streak: int,
        last_study_date: Optional[datetime],
        now: Optional[datetime] = None,
    ) -> Dict[str, Any]:
        """
        Evaluates streak progression based on current time and last study timestamp.

        Returns:
            dict with:
                - 'new_current_streak': int
                - 'new_longest_streak': int
                - 'streak_increased': bool (True if streak incremented today)
                - 'streak_maintained': bool (True if studied already today)
                - 'streak_reset_from': Optional[int] (previous streak if broken)
                - 'message': str (encouraging feedback)
        """
        current_time = now or datetime.now(timezone.utc)
        today = current_time.date()

        if last_study_date is None:
            # Very first session ever
            new_current = 1
            new_longest = max(longest_streak, 1)
            return {
                "new_current_streak": new_current,
                "new_longest_streak": new_longest,
                "streak_increased": True,
                "streak_maintained": False,
                "streak_reset_from": None,
                "message": "🔥 1-day streak unlocked! The journey begins.",
            }

        # Convert last study date to date object
        if isinstance(last_study_date, datetime):
            last_date = last_study_date.date()
        else:
            last_date = last_study_date

        delta_days = (today - last_date).days

        if delta_days == 0:
            # Already studied today; streak is maintained, not incremented again
            return {
                "new_current_streak": current_streak,
                "new_longest_streak": longest_streak,
                "streak_increased": False,
                "streak_maintained": True,
                "streak_reset_from": None,
                "message": f"🔥 Streak maintained at {current_streak} days. Keep cooking!",
            }
        elif delta_days == 1:
            # Consecutive day! Increment streak
            new_current = current_streak + 1
            new_longest = max(longest_streak, new_current)
            return {
                "new_current_streak": new_current,
                "new_longest_streak": new_longest,
                "streak_increased": True,
                "streak_maintained": False,
                "streak_reset_from": None,
                "message": f"🔥 **{new_current} DAY STREAK!** Unstoppable momentum.",
            }
        else:
            # Missed a day or more. Reset gracefully to 1
            reset_from = current_streak if current_streak > 0 else None
            new_current = 1
            new_longest = longest_streak
            msg = (
                f"The streak ended at {reset_from} days.\nNo big deal. Start another one today."
                if reset_from and reset_from > 1
                else "🔥 1-day streak started. Let's build a massive streak!"
            )
            return {
                "new_current_streak": new_current,
                "new_longest_streak": new_longest,
                "streak_increased": True,
                "streak_maintained": False,
                "streak_reset_from": reset_from,
                "message": msg,
            }


streak_service = StreakService()
