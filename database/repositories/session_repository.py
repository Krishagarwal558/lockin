from __future__ import annotations

from typing import List, Optional, Sequence, Dict, Any
from datetime import datetime
from sqlalchemy import select, update, desc, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from database.models import StudySession, utc_now


class SessionRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def create_session(
        self,
        user_id: int,
        discord_user_id: int,
        subject: str,
        planned_seconds: int,
        channel_id: Optional[int] = None,
        guild_id: Optional[int] = None,
    ) -> StudySession:
        """Creates a new active study session."""
        study_session = StudySession(
            user_id=user_id,
            discord_user_id=discord_user_id,
            subject=subject,
            planned_seconds=planned_seconds,
            channel_id=channel_id,
            guild_id=guild_id,
            status="active",
            started_at=utc_now(),
        )
        self.session.add(study_session)
        await self.session.flush()
        return study_session

    async def get_active_session(self, discord_user_id: int) -> Optional[StudySession]:
        """Gets the currently active study session for a Discord user."""
        stmt = (
            select(StudySession)
            .where(
                StudySession.discord_user_id == discord_user_id,
                StudySession.status == "active",
            )
            .order_by(desc(StudySession.started_at))
            .limit(1)
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_all_active_sessions(self) -> Sequence[StudySession]:
        """Gets all currently active study sessions across the bot (used for restart recovery)."""
        stmt = select(StudySession).where(StudySession.status == "active")
        result = await self.session.execute(stmt)
        return result.scalars().all()

    async def complete_session(
        self,
        session_id: int,
        actual_seconds: int,
        xp_earned: int,
        topic: Optional[str] = None,
        quiz_score: Optional[float] = None,
    ) -> Optional[StudySession]:
        """Marks a session as completed."""
        stmt = (
            update(StudySession)
            .where(StudySession.id == session_id)
            .values(
                status="completed",
                actual_seconds=actual_seconds,
                xp_earned=xp_earned,
                topic=topic,
                quiz_score=quiz_score,
                ended_at=utc_now(),
            )
            .returning(StudySession)
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def stop_session(
        self,
        session_id: int,
        actual_seconds: int,
        xp_earned: int,
    ) -> Optional[StudySession]:
        """Marks a session as stopped early."""
        stmt = (
            update(StudySession)
            .where(StudySession.id == session_id)
            .values(
                status="stopped",
                actual_seconds=actual_seconds,
                xp_earned=xp_earned,
                ended_at=utc_now(),
            )
            .returning(StudySession)
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def increment_motivation_count(self, session_id: int) -> None:
        """Increments motivation counter on a session."""
        stmt = (
            update(StudySession)
            .where(StudySession.id == session_id)
            .values(motivation_count=StudySession.motivation_count + 1)
        )
        await self.session.execute(stmt)

    async def update_session_topic_and_quiz(
        self,
        session_id: int,
        topic: str,
        quiz_score: float,
        bonus_xp: int = 0
    ) -> None:
        """Updates topic, quiz score and awards quiz bonus XP to the session."""
        stmt = (
            update(StudySession)
            .where(StudySession.id == session_id)
            .values(
                topic=topic,
                quiz_score=quiz_score,
                xp_earned=StudySession.xp_earned + bonus_xp,
            )
        )
        await self.session.execute(stmt)

    async def get_recent_sessions(
        self,
        discord_user_id: int,
        limit: int = 5
    ) -> Sequence[StudySession]:
        """Gets the most recent sessions for a user."""
        stmt = (
            select(StudySession)
            .where(StudySession.discord_user_id == discord_user_id)
            .order_by(desc(StudySession.started_at))
            .limit(limit)
        )
        result = await self.session.execute(stmt)
        return result.scalars().all()

    async def get_user_stats(self, discord_user_id: int) -> Dict[str, Any]:
        """Computes aggregated session statistics for a user."""
        # Total completed sessions count
        count_stmt = (
            select(func.count(StudySession.id))
            .where(
                StudySession.discord_user_id == discord_user_id,
                StudySession.status == "completed"
            )
        )
        total_completed = (await self.session.execute(count_stmt)).scalar() or 0

        # Total stopped sessions
        stopped_stmt = (
            select(func.count(StudySession.id))
            .where(
                StudySession.discord_user_id == discord_user_id,
                StudySession.status == "stopped"
            )
        )
        total_stopped = (await self.session.execute(stopped_stmt)).scalar() or 0

        # Average session duration
        avg_stmt = (
            select(func.avg(StudySession.actual_seconds))
            .where(
                StudySession.discord_user_id == discord_user_id,
                StudySession.actual_seconds > 0
            )
        )
        avg_seconds = (await self.session.execute(avg_stmt)).scalar() or 0

        # Subject breakdown
        subj_stmt = (
            select(StudySession.subject, func.count(StudySession.id), func.sum(StudySession.actual_seconds))
            .where(StudySession.discord_user_id == discord_user_id)
            .group_by(StudySession.subject)
            .order_by(desc(func.sum(StudySession.actual_seconds)))
        )
        subj_rows = (await self.session.execute(subj_stmt)).all()
        subjects = [
            {"subject": row[0], "sessions": row[1], "seconds": row[2] or 0}
            for row in subj_rows
        ]

        # Recent unique topics
        topics_stmt = (
            select(StudySession.topic)
            .where(
                StudySession.discord_user_id == discord_user_id,
                StudySession.topic.isnot(None)
            )
            .order_by(desc(StudySession.started_at))
            .limit(5)
        )
        topic_rows = (await self.session.execute(topics_stmt)).scalars().all()
        recent_topics = [t for t in topic_rows if t]

        return {
            "total_completed": total_completed,
            "total_stopped": total_stopped,
            "total_sessions": total_completed + total_stopped,
            "avg_seconds": float(avg_seconds),
            "subjects": subjects,
            "best_subject": subjects[0]["subject"] if subjects else "General",
            "recent_topics": recent_topics,
        }
