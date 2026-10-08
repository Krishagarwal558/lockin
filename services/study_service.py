from __future__ import annotations

from typing import Optional, Tuple, Dict, Any, List
from datetime import datetime
import discord

from config import settings
from database.database import db_manager
from database.models import User, StudySession, Achievement
from database.repositories.user_repository import UserRepository
from database.repositories.session_repository import SessionRepository
from database.repositories.achievement_repository import AchievementRepository
from database.repositories.quiz_repository import QuizRepository
from services.timer_service import timer_service, ActiveTimer
from services.xp_service import xp_service
from services.streak_service import streak_service
from services.achievement_service import achievement_service
from utils.logging import setup_logger
from utils.time import utc_now

logger = setup_logger("lockin.study_service", settings.LOG_LEVEL)


class StudyService:
    def __init__(self):
        pass

    async def start_study_session(
        self,
        discord_user_id: int,
        username: str,
        subject: str,
        planned_seconds: int,
        channel_id: Optional[int] = None,
        guild_id: Optional[int] = None,
    ) -> Tuple[StudySession, ActiveTimer]:
        """Initiates a new study session, creates DB records, and schedules timer."""
        # Ensure no duplicate active sessions
        if timer_service.is_user_studying(discord_user_id):
            raise ValueError("You already have an active study session running! Stop it first with `/stop`.")

        async with db_manager.session() as sess:
            user_repo = UserRepository(sess)
            session_repo = SessionRepository(sess)

            user = await user_repo.get_or_create_user(discord_user_id, username)

            study_session = await session_repo.create_session(
                user_id=user.id,
                discord_user_id=discord_user_id,
                subject=subject,
                planned_seconds=planned_seconds,
                channel_id=channel_id,
                guild_id=guild_id,
            )

            mot_enabled = user.motivation_enabled
            mot_interval = user.motivation_interval_minutes * 60

            timer = timer_service.register_timer(
                session_id=study_session.id,
                user_id=user.id,
                discord_user_id=discord_user_id,
                channel_id=channel_id,
                guild_id=guild_id,
                subject=subject,
                planned_seconds=planned_seconds,
                motivation_interval_seconds=mot_interval,
                motivation_enabled=mot_enabled,
            )

            return study_session, timer

    async def stop_study_session_early(
        self,
        discord_user_id: int,
    ) -> Tuple[StudySession, int, int, str]:
        """
        Manually stops an ongoing session early.
        Awards XP proportional to actual time studied. Does not penalize existing streak.
        Returns: (session, actual_seconds, xp_earned, fun_message)
        """
        timer = timer_service.cancel_timer(discord_user_id)
        if not timer:
            raise ValueError("No active study session found to stop.")

        actual_seconds = timer.elapsed_seconds
        base_xp = xp_service.calculate_study_xp(actual_seconds)

        async with db_manager.session() as sess:
            session_repo = SessionRepository(sess)
            user_repo = UserRepository(sess)

            study_session = await session_repo.stop_session(
                session_id=timer.session_id,
                actual_seconds=actual_seconds,
                xp_earned=base_xp,
            )

            user = await user_repo.get_by_id(timer.user_id)
            if user:
                await user_repo.add_study_time(user.id, actual_seconds)
                if base_xp > 0:
                    new_level, _, _ = xp_service.calculate_level_from_xp(user.xp + base_xp)
                    await user_repo.add_xp(user.id, base_xp, new_level)

        actual_mins = actual_seconds // 60
        if actual_mins < 15:
            fun_msg = "No streak penalty. But bro... we could've cooked."
        else:
            fun_msg = "Solid effort. Every minute counts towards the master plan."

        return study_session, actual_seconds, base_xp, fun_msg

    async def handle_session_completion(
        self,
        timer: ActiveTimer,
    ) -> Tuple[StudySession, User, int, Dict[str, Any], List[Achievement]]:
        """
        Processes timer expiration: awards study XP, updates streak, checks achievements.
        Returns: (session, user, base_xp, streak_info, unlocked_achievements)
        """
        actual_seconds = timer.planned_seconds
        base_xp = xp_service.calculate_study_xp(actual_seconds)
        now = utc_now()

        async with db_manager.session() as sess:
            session_repo = SessionRepository(sess)
            user_repo = UserRepository(sess)
            ach_repo = AchievementRepository(sess)

            study_session = await session_repo.complete_session(
                session_id=timer.session_id,
                actual_seconds=actual_seconds,
                xp_earned=base_xp,
            )

            user = await user_repo.get_by_id(timer.user_id)
            if not user:
                raise RuntimeError(f"User {timer.user_id} not found on completion.")

            # Update streak
            streak_info = streak_service.evaluate_streak_update(
                current_streak=user.current_streak,
                longest_streak=user.longest_streak,
                last_study_date=user.last_study_date,
                now=now,
            )

            # Streak bonus XP if streak incremented
            streak_bonus_xp = xp_service.calculate_streak_bonus_xp(streak_info["new_current_streak"])
            total_session_xp = base_xp + streak_bonus_xp

            # Update user stats
            await user_repo.add_study_time(user.id, actual_seconds)
            new_level, _, _ = xp_service.calculate_level_from_xp(user.xp + total_session_xp)
            user = await user_repo.add_xp(user.id, total_session_xp, new_level)
            user = await user_repo.update_streak(
                user_id=user.id,
                current_streak=streak_info["new_current_streak"],
                longest_streak=streak_info["new_longest_streak"],
                last_study_date=now,
            )

            # Check achievements
            user_stats = await session_repo.get_user_stats(user.discord_user_id)
            unlocked_achievements = await achievement_service.check_session_achievements(
                ach_repo=ach_repo,
                user=user,
                session=study_session,
                total_completed_sessions=user_stats["total_completed"],
            )

            # Award achievement XP
            for ach in unlocked_achievements:
                if ach.xp_reward > 0:
                    nl, _, _ = xp_service.calculate_level_from_xp(user.xp + ach.xp_reward)
                    user = await user_repo.add_xp(user.id, ach.xp_reward, nl)

            return study_session, user, total_session_xp, streak_info, unlocked_achievements

    async def get_user_profile(self, discord_user_id: int, username: str) -> Dict[str, Any]:
        """Compiles user profile details, level progression, streak, and stats."""
        async with db_manager.session() as sess:
            user_repo = UserRepository(sess)
            session_repo = SessionRepository(sess)
            quiz_repo = QuizRepository(sess)
            ach_repo = AchievementRepository(sess)

            user = await user_repo.get_or_create_user(discord_user_id, username)
            session_stats = await session_repo.get_user_stats(discord_user_id)
            quiz_stats = await quiz_repo.get_user_quiz_stats(user.id)
            user_achievements = await ach_repo.get_user_achievements(user.id)

            level, xp_in_level, xp_needed = xp_service.calculate_level_from_xp(user.xp)

            return {
                "user": user,
                "level": level,
                "xp_in_level": xp_in_level,
                "xp_needed": xp_needed,
                "total_xp": user.xp,
                "current_streak": user.current_streak,
                "longest_streak": user.longest_streak,
                "total_study_seconds": user.total_study_seconds,
                "sessions_completed": session_stats["total_completed"],
                "best_subject": session_stats["best_subject"],
                "recent_topics": session_stats["recent_topics"],
                "subjects": session_stats["subjects"],
                "quiz_stats": quiz_stats,
                "achievements": user_achievements,
            }


study_service = StudyService()
