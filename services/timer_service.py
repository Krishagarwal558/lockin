from __future__ import annotations

import asyncio
from datetime import datetime, timezone
from typing import Dict, Optional, Callable, Any, Coroutine
import discord

from config import settings
from database.database import db_manager
from database.repositories.session_repository import SessionRepository
from database.repositories.user_repository import UserRepository
from services.motivation_service import motivation_service
from utils.logging import setup_logger
from utils.time import utc_now, ensure_utc

logger = setup_logger("lockin.timer", settings.LOG_LEVEL)


class ActiveTimer:
    def __init__(
        self,
        session_id: int,
        user_id: int,
        discord_user_id: int,
        channel_id: Optional[int],
        guild_id: Optional[int],
        subject: str,
        planned_seconds: int,
        started_at: datetime,
        task: Optional[asyncio.Task] = None,
    ):
        self.session_id = session_id
        self.user_id = user_id
        self.discord_user_id = discord_user_id
        self.channel_id = channel_id
        self.guild_id = guild_id
        self.subject = subject
        self.planned_seconds = planned_seconds
        self.started_at = started_at
        self.task = task
        self.is_cancelled = False

    @property
    def elapsed_seconds(self) -> int:
        now = utc_now()
        start = ensure_utc(self.started_at) or now
        delta = (now - start).total_seconds()
        return max(0, int(delta))

    @property
    def remaining_seconds(self) -> int:
        return max(0, self.planned_seconds - self.elapsed_seconds)


class TimerService:
    def __init__(self):
        self._active_timers: Dict[int, ActiveTimer] = {}
        self._bot: Optional[discord.Client] = None
        self._completion_callback: Optional[Callable[[ActiveTimer], Coroutine[Any, Any, None]]] = None

    def initialize(
        self,
        bot: discord.Client,
        completion_callback: Optional[Callable[[ActiveTimer], Coroutine[Any, Any, None]]] = None,
    ) -> None:
        """Sets the Discord bot instance and optional completion callback."""
        self._bot = bot
        self._completion_callback = completion_callback

    def is_user_studying(self, discord_user_id: int) -> bool:
        """Checks if a user currently has a running timer in memory."""
        return discord_user_id in self._active_timers

    def get_active_timer(self, discord_user_id: int) -> Optional[ActiveTimer]:
        """Returns the active timer object for a user."""
        return self._active_timers.get(discord_user_id)

    def register_timer(
        self,
        session_id: int,
        user_id: int,
        discord_user_id: int,
        channel_id: Optional[int],
        guild_id: Optional[int],
        subject: str,
        planned_seconds: int,
        started_at: Optional[datetime] = None,
        motivation_interval_seconds: int = 1200, # 20 mins
        motivation_enabled: bool = True,
    ) -> ActiveTimer:
        """Creates and schedules a background timer task."""
        if discord_user_id in self._active_timers:
            self.cancel_timer(discord_user_id)

        start_time = started_at or utc_now()
        timer = ActiveTimer(
            session_id=session_id,
            user_id=user_id,
            discord_user_id=discord_user_id,
            channel_id=channel_id,
            guild_id=guild_id,
            subject=subject,
            planned_seconds=planned_seconds,
            started_at=start_time,
        )

        task = None
        try:
            loop = asyncio.get_running_loop()
            task = loop.create_task(
                self._timer_worker(
                    timer=timer,
                    motivation_interval=motivation_interval_seconds,
                    motivation_enabled=motivation_enabled,
                ),
                name=f"timer-{discord_user_id}-{session_id}"
            )
        except RuntimeError:
            pass

        timer.task = task
        self._active_timers[discord_user_id] = timer
        logger.info(f"Registered timer for user {discord_user_id} ({subject}, {planned_seconds}s)")
        return timer

    def cancel_timer(self, discord_user_id: int) -> Optional[ActiveTimer]:
        """Cancels and unregisters an active timer."""
        timer = self._active_timers.pop(discord_user_id, None)
        if timer:
            timer.is_cancelled = True
            if timer.task and not timer.task.done():
                timer.task.cancel()
            logger.info(f"Cancelled timer for user {discord_user_id}")
        return timer

    async def _timer_worker(
        self,
        timer: ActiveTimer,
        motivation_interval: int,
        motivation_enabled: bool,
    ) -> None:
        """Background coroutine that sleeps, sends periodic motivational nudges, and triggers completion."""
        try:
            logger.debug(f"Timer worker started for session {timer.session_id}")
            while not timer.is_cancelled:
                remaining = timer.remaining_seconds
                if remaining <= 0:
                    break

                # Sleep either for the motivation interval or the remaining duration
                sleep_duration = min(remaining, motivation_interval if motivation_enabled else remaining)
                await asyncio.sleep(sleep_duration)

                if timer.is_cancelled:
                    break

                remaining_after = timer.remaining_seconds
                if remaining_after > 0 and motivation_enabled:
                    # Send motivational nudge
                    await self._send_motivation_nudge(timer)

            # Session completed naturally
            if not timer.is_cancelled:
                self._active_timers.pop(timer.discord_user_id, None)
                if self._completion_callback:
                    await self._completion_callback(timer)

        except asyncio.CancelledError:
            logger.info(f"Timer worker for session {timer.session_id} cancelled.")
        except Exception as e:
            logger.error(f"Unexpected error in timer worker for session {timer.session_id}: {e}", exc_info=True)
            self._active_timers.pop(timer.discord_user_id, None)

    async def _send_motivation_nudge(self, timer: ActiveTimer) -> None:
        """Sends a periodic motivation nudge to channel or DM."""
        if not self._bot:
            return

        try:
            elapsed = timer.elapsed_seconds
            total = timer.planned_seconds
            nudge_text = motivation_service.get_interval_message(elapsed, total)

            channel = None
            if timer.channel_id:
                channel = self._bot.get_channel(timer.channel_id)
                if not channel:
                    try:
                        channel = await self._bot.fetch_channel(timer.channel_id)
                    except Exception:
                        pass

            embed = discord.Embed(
                description=f"<@{timer.discord_user_id}>\n{nudge_text}",
                color=discord.Color.gold(),
            )
            embed.set_footer(text=f"Subject: {timer.subject} • Stay locked in!")

            if channel:
                await channel.send(embed=embed)
            else:
                user = self._bot.get_user(timer.discord_user_id) or await self._bot.fetch_user(timer.discord_user_id)
                if user:
                    await user.send(embed=embed)

            # Record motivation count in DB
            async with db_manager.session() as sess:
                session_repo = SessionRepository(sess)
                await session_repo.increment_motivation_count(timer.session_id)

        except Exception as e:
            logger.warning(f"Failed to deliver motivation nudge to user {timer.discord_user_id}: {e}")

    async def recover_active_sessions(self) -> None:
        """Recovers running sessions from database upon bot restart."""
        logger.info("Checking for unfinished active sessions to recover...")
        try:
            async with db_manager.session() as sess:
                session_repo = SessionRepository(sess)
                user_repo = UserRepository(sess)
                active_sessions = await session_repo.get_all_active_sessions()

                for db_sess in active_sessions:
                    now = utc_now()
                    start = ensure_utc(db_sess.started_at) or now
                    elapsed = int((now - start).total_seconds())
                    user = await user_repo.get_by_id(db_sess.user_id)

                    if elapsed >= db_sess.planned_seconds:
                        # Expired while bot was offline; mark completed
                        logger.info(f"Session {db_sess.id} finished while offline. Marking completed.")
                        await session_repo.complete_session(
                            session_id=db_sess.id,
                            actual_seconds=db_sess.planned_seconds,
                            xp_earned=db_sess.planned_seconds // 60,
                        )
                    else:
                        # Resume tracking
                        mot_enabled = user.motivation_enabled if user else True
                        mot_interval = (user.motivation_interval_minutes * 60) if user else 1200
                        self.register_timer(
                            session_id=db_sess.id,
                            user_id=db_sess.user_id,
                            discord_user_id=db_sess.discord_user_id,
                            channel_id=db_sess.channel_id,
                            guild_id=db_sess.guild_id,
                            subject=db_sess.subject,
                            planned_seconds=db_sess.planned_seconds,
                            started_at=db_sess.started_at,
                            motivation_interval_seconds=mot_interval,
                            motivation_enabled=mot_enabled,
                        )
                        logger.info(f"Resumed active timer for session {db_sess.id} ({db_sess.planned_seconds - elapsed}s remaining)")

        except Exception as e:
            logger.error(f"Error during active session recovery: {e}", exc_info=True)


timer_service = TimerService()
