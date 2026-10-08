from __future__ import annotations

from typing import List, Optional, Sequence
from datetime import datetime
from sqlalchemy import select, update, desc
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from database.models import User, utc_now


class UserRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_or_create_user(self, discord_user_id: int, username: str) -> User:
        """Retrieves an existing user or creates a new one if not found."""
        stmt = select(User).where(User.discord_user_id == discord_user_id)
        result = await self.session.execute(stmt)
        user = result.scalar_one_or_none()

        if not user:
            try:
                user = User(
                    discord_user_id=discord_user_id,
                    username=username,
                    xp=0,
                    level=1,
                    current_streak=0,
                    longest_streak=0,
                    total_study_seconds=0,
                    last_study_date=None,
                )
                self.session.add(user)
                await self.session.flush()
            except Exception:
                # If race condition occurred, re-fetch
                await self.session.rollback()
                stmt = select(User).where(User.discord_user_id == discord_user_id)
                res = await self.session.execute(stmt)
                user = res.scalar_one()
        elif user.username != username:
            user.username = username
            user.updated_at = utc_now()
            await self.session.flush()

        return user

    async def get_by_discord_id(self, discord_user_id: int) -> Optional[User]:
        """Gets user by Discord user ID."""
        stmt = (
            select(User)
            .options(
                selectinload(User.achievements),
                selectinload(User.study_sessions),
            )
            .where(User.discord_user_id == discord_user_id)
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_by_id(self, user_id: int) -> Optional[User]:
        """Gets user by database ID."""
        stmt = select(User).where(User.id == user_id)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def add_xp(self, user_id: int, xp_amount: int, new_level: int) -> User:
        """Adds XP and updates level."""
        stmt = (
            update(User)
            .where(User.id == user_id)
            .values(
                xp=User.xp + xp_amount,
                level=new_level,
                updated_at=utc_now()
            )
            .returning(User)
        )
        result = await self.session.execute(stmt)
        return result.scalar_one()

    async def add_study_time(self, user_id: int, seconds: int) -> User:
        """Increments total study seconds for user."""
        stmt = (
            update(User)
            .where(User.id == user_id)
            .values(
                total_study_seconds=User.total_study_seconds + seconds,
                updated_at=utc_now()
            )
            .returning(User)
        )
        result = await self.session.execute(stmt)
        return result.scalar_one()

    async def update_streak(
        self,
        user_id: int,
        current_streak: int,
        longest_streak: int,
        last_study_date: datetime,
    ) -> User:
        """Updates streak numbers and last study date."""
        stmt = (
            update(User)
            .where(User.id == user_id)
            .values(
                current_streak=current_streak,
                longest_streak=longest_streak,
                last_study_date=last_study_date,
                updated_at=utc_now()
            )
            .returning(User)
        )
        result = await self.session.execute(stmt)
        return result.scalar_one()

    async def update_preferences(
        self,
        user_id: int,
        motivation_enabled: Optional[bool] = None,
        motivation_interval_minutes: Optional[int] = None,
        auto_quiz_enabled: Optional[bool] = None,
    ) -> User:
        """Updates user preferences."""
        values_to_update = {"updated_at": utc_now()}
        if motivation_enabled is not None:
            values_to_update["motivation_enabled"] = motivation_enabled
        if motivation_interval_minutes is not None:
            values_to_update["motivation_interval_minutes"] = motivation_interval_minutes
        if auto_quiz_enabled is not None:
            values_to_update["auto_quiz_enabled"] = auto_quiz_enabled

        stmt = update(User).where(User.id == user_id).values(**values_to_update).returning(User)
        result = await self.session.execute(stmt)
        return result.scalar_one()

    async def get_leaderboard(
        self,
        limit: int = 10,
        discord_user_ids: Optional[List[int]] = None,
        order_by_xp: bool = False
    ) -> Sequence[User]:
        """Fetches top users sorted by study time or XP."""
        order_col = User.xp if order_by_xp else User.total_study_seconds
        stmt = select(User).order_by(desc(order_col)).limit(limit)

        if discord_user_ids:
            stmt = stmt.where(User.discord_user_id.in_(discord_user_ids))

        result = await self.session.execute(stmt)
        return result.scalars().all()
