from __future__ import annotations

from typing import List, Tuple, Optional
from database.models import User, StudySession, Quiz, Achievement
from database.repositories.achievement_repository import AchievementRepository


class AchievementService:
    """
    Evaluates milestone criteria and awards unlocked achievements.
    """

    @staticmethod
    async def check_session_achievements(
        ach_repo: AchievementRepository,
        user: User,
        session: StudySession,
        total_completed_sessions: int,
    ) -> List[Achievement]:
        """Checks achievements triggered by finishing a study session."""
        newly_unlocked = []

        # 1. First Lock-In
        if total_completed_sessions >= 1:
            unlocked, ach = await ach_repo.award_achievement(user.id, "first_lockin")
            if unlocked and ach:
                newly_unlocked.append(ach)

        # 2. Long Haul (>= 2 hours / 7200s)
        if session.actual_seconds >= 7200:
            unlocked, ach = await ach_repo.award_achievement(user.id, "long_haul")
            if unlocked and ach:
                newly_unlocked.append(ach)

        # 3. Getting Serious (7 day streak)
        if user.current_streak >= 7:
            unlocked, ach = await ach_repo.award_achievement(user.id, "getting_serious")
            if unlocked and ach:
                newly_unlocked.append(ach)

        # 4. Final Boss (30 day streak)
        if user.current_streak >= 30:
            unlocked, ach = await ach_repo.award_achievement(user.id, "final_boss")
            if unlocked and ach:
                newly_unlocked.append(ach)

        # 5. Academic Weapon (>= 50 hours / 180,000s)
        if user.total_study_seconds >= 180000:
            unlocked, ach = await ach_repo.award_achievement(user.id, "academic_weapon")
            if unlocked and ach:
                newly_unlocked.append(ach)

        # 6. Century Club (>= 100 sessions)
        if total_completed_sessions >= 100:
            unlocked, ach = await ach_repo.award_achievement(user.id, "century_club")
            if unlocked and ach:
                newly_unlocked.append(ach)

        return newly_unlocked

    @staticmethod
    async def check_quiz_achievements(
        ach_repo: AchievementRepository,
        user: User,
        quiz: Quiz,
        total_quizzes: int,
    ) -> List[Achievement]:
        """Checks achievements triggered by completing a quiz."""
        newly_unlocked = []

        # 1. Knowledge Check (1st quiz)
        if total_quizzes >= 1:
            unlocked, ach = await ach_repo.award_achievement(user.id, "knowledge_check")
            if unlocked and ach:
                newly_unlocked.append(ach)

        # 2. Sharpshooter (100% score)
        if quiz.score >= 1.0 or quiz.correct_count == quiz.question_count:
            unlocked, ach = await ach_repo.award_achievement(user.id, "sharpshooter")
            if unlocked and ach:
                newly_unlocked.append(ach)

        return newly_unlocked


achievement_service = AchievementService()
