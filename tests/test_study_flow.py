from __future__ import annotations

import pytest
import pytest_asyncio
from datetime import datetime, timezone, timedelta
from database.database import db_manager
from database.repositories.user_repository import UserRepository
from database.repositories.session_repository import SessionRepository
from services.study_service import study_service
from services.timer_service import timer_service


@pytest_asyncio.fixture(autouse=True)
async def init_test_db():
    async with db_manager.engine.begin() as conn:
        from database.models import Base
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)
    await db_manager.init_db()
    yield


@pytest.mark.asyncio
async def test_early_stop_proportional_xp():
    user_id = 987654321
    
    # 1. Start a 60-minute session
    session, timer = await study_service.start_study_session(
        discord_user_id=user_id,
        username="EarlyStopper",
        subject="Linear Algebra",
        planned_seconds=3600,
    )
    assert timer_service.is_user_studying(user_id) is True

    # 2. Simulate 23 minutes elapsed (1380 seconds)
    timer.started_at = timer.started_at - timedelta(seconds=1380)

    # 3. Stop session early
    stopped_sess, actual_sec, xp_earned, msg = await study_service.stop_study_session_early(user_id)
    
    assert stopped_sess.status == "stopped"
    assert actual_sec >= 1380
    assert xp_earned == 23
    assert timer_service.is_user_studying(user_id) is False

    # 4. Verify user received 23 XP and study time recorded
    async with db_manager.session() as sess:
        user_repo = UserRepository(sess)
        user = await user_repo.get_by_discord_id(user_id)
        assert user is not None
        assert user.xp == 23
        assert user.total_study_seconds >= 1380


@pytest.mark.asyncio
async def test_session_recovery_expired_and_ongoing():
    now = datetime.now(timezone.utc)
    
    async with db_manager.session() as sess:
        user_repo = UserRepository(sess)
        session_repo = SessionRepository(sess)

        user = await user_repo.get_or_create_user(5555, "OfflineStudier")

        # Session 1: Started 2 hours ago for 60m -> Expired while bot was offline
        s1 = await session_repo.create_session(
            user_id=user.id,
            discord_user_id=5555,
            subject="History",
            planned_seconds=3600,
        )
        s1.started_at = now - timedelta(hours=2)

        # Session 2: Started 10 minutes ago for 60m -> Still running (50m left)
        s2 = await session_repo.create_session(
            user_id=user.id,
            discord_user_id=7777,
            subject="Algorithms",
            planned_seconds=3600,
        )
        s2.started_at = now - timedelta(minutes=10)

    # Trigger recovery
    await timer_service.recover_active_sessions()

    # Verify s1 is marked completed
    async with db_manager.session() as sess:
        session_repo = SessionRepository(sess)
        recent_s1 = await session_repo.get_recent_sessions(5555, limit=1)
        assert recent_s1[0].status == "completed"
        assert recent_s1[0].actual_seconds == 3600

    # Verify s2 is active in timer_service
    assert timer_service.is_user_studying(7777) is True
    t2 = timer_service.get_active_timer(7777)
    assert t2 is not None
    assert t2.remaining_seconds <= 3000
    timer_service.cancel_timer(7777)
