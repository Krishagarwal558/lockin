from __future__ import annotations

from typing import List, Set, Sequence, Tuple
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from database.models import Achievement, UserAchievement, utc_now


class AchievementRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_all_achievements(self) -> Sequence[Achievement]:
        """Gets all system achievements."""
        stmt = select(Achievement)
        result = await self.session.execute(stmt)
        return result.scalars().all()

    async def get_unlocked_slugs(self, user_id: int) -> Set[str]:
        """Returns set of slugs for achievements already unlocked by user."""
        stmt = (
            select(Achievement.slug)
            .join(UserAchievement, UserAchievement.achievement_id == Achievement.id)
            .where(UserAchievement.user_id == user_id)
        )
        result = await self.session.execute(stmt)
        return set(result.scalars().all())

    async def award_achievement(self, user_id: int, slug: str) -> Tuple[bool, Achievement | None]:
        """
        Awards an achievement to user if not already earned.
        Returns (is_newly_unlocked, achievement_obj).
        """
        stmt = select(Achievement).where(Achievement.slug == slug)
        res = await self.session.execute(stmt)
        achievement = res.scalar_one_or_none()

        if not achievement:
            return False, None

        # Check if already unlocked
        check_stmt = (
            select(UserAchievement)
            .where(
                UserAchievement.user_id == user_id,
                UserAchievement.achievement_id == achievement.id,
            )
        )
        check_res = await self.session.execute(check_stmt)
        if check_res.scalar_one_or_none():
            return False, achievement

        user_ach = UserAchievement(
            user_id=user_id,
            achievement_id=achievement.id,
            unlocked_at=utc_now(),
        )
        self.session.add(user_ach)
        await self.session.flush()
        return True, achievement

    async def get_user_achievements(self, user_id: int) -> List[Tuple[Achievement, UserAchievement]]:
        """Returns all achievements for a user with unlock timestamps."""
        stmt = (
            select(Achievement, UserAchievement)
            .join(UserAchievement, UserAchievement.achievement_id == Achievement.id)
            .where(UserAchievement.user_id == user_id)
            .order_by(UserAchievement.unlocked_at.desc())
        )
        result = await self.session.execute(stmt)
        return list(result.all())
