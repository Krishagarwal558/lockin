from __future__ import annotations

from typing import AsyncGenerator
from contextlib import asynccontextmanager
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy import select

from config import settings
from database.models import Base, Achievement
from utils.logging import setup_logger

logger = setup_logger("lockin.database", settings.LOG_LEVEL)

DEFAULT_ACHIEVEMENTS = [
    {
        "slug": "first_lockin",
        "name": "First Lock-In",
        "description": "Complete your first study session.",
        "xp_reward": 50,
        "icon": "🏆",
    },
    {
        "slug": "getting_serious",
        "name": "Getting Serious",
        "description": "Maintain a 7-day study streak.",
        "xp_reward": 150,
        "icon": "🔥",
    },
    {
        "slug": "academic_weapon",
        "name": "Academic Weapon",
        "description": "Accumulate 50 total hours of study time.",
        "xp_reward": 500,
        "icon": "🗿",
    },
    {
        "slug": "final_boss",
        "name": "Final Boss",
        "description": "Maintain an unstoppable 30-day streak.",
        "xp_reward": 1000,
        "icon": "👑",
    },
    {
        "slug": "knowledge_check",
        "name": "Knowledge Check",
        "description": "Complete your first post-study quiz.",
        "xp_reward": 50,
        "icon": "📚",
    },
    {
        "slug": "sharpshooter",
        "name": "Sharpshooter",
        "description": "Score 100% on a post-study quiz.",
        "xp_reward": 100,
        "icon": "🎯",
    },
    {
        "slug": "long_haul",
        "name": "Long Haul",
        "description": "Complete a single session of 2 hours or longer.",
        "xp_reward": 200,
        "icon": "💀",
    },
    {
        "slug": "century_club",
        "name": "Century Club",
        "description": "Complete 100 total study sessions.",
        "xp_reward": 800,
        "icon": "💯",
    },
]


class DatabaseManager:
    def __init__(self, db_url: str = settings.DATABASE_URL):
        self.db_url = db_url
        self.engine: AsyncEngine = create_async_engine(
            self.db_url,
            echo=False,
            future=True,
        )
        self.session_factory = async_sessionmaker(
            bind=self.engine,
            class_=AsyncSession,
            expire_on_commit=False,
        )

    @asynccontextmanager
    async def session(self) -> AsyncGenerator[AsyncSession, None]:
        """Provides an async transactional session context."""
        async with self.session_factory() as sess:
            try:
                yield sess
                await sess.commit()
            except Exception:
                await sess.rollback()
                raise

    async def init_db(self) -> None:
        """Initializes database tables and seeds initial achievements."""
        logger.info(f"Initializing database schema on {self.db_url}...")
        async with self.engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

        async with self.session() as sess:
            for ach_data in DEFAULT_ACHIEVEMENTS:
                stmt = select(Achievement).where(Achievement.slug == ach_data["slug"])
                result = await sess.execute(stmt)
                existing = result.scalar_one_or_none()
                if not existing:
                    new_ach = Achievement(**ach_data)
                    sess.add(new_ach)
            await sess.commit()
        logger.info("Database schema initialized and default achievements seeded.")

    async def close(self) -> None:
        """Closes the async database engine."""
        await self.engine.dispose()
        logger.info("Database engine closed.")


db_manager = DatabaseManager()
