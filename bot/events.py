from __future__ import annotations

import discord
from discord import app_commands
from discord.ext import commands

from database.database import db_manager
from services.timer_service import timer_service, ActiveTimer
from services.study_service import study_service
from bot.embeds.study_embeds import session_complete_embed
from bot.views.quiz_view import TopicPromptView
from utils.logging import setup_logger

logger = setup_logger("lockin.events")


async def handle_session_completion_event(bot: commands.Bot, timer: ActiveTimer) -> None:
    """Callback invoked by TimerService when a study timer naturally expires."""
    logger.info(f"Timer completed for user {timer.discord_user_id} on subject '{timer.subject}'.")

    try:
        session, user, total_xp, streak_info, achievements = await study_service.handle_session_completion(timer)

        embed = session_complete_embed(
            user_id=timer.discord_user_id,
            subject=timer.subject,
            duration_seconds=timer.planned_seconds,
            base_xp=total_xp,
            streak_days=streak_info["new_current_streak"],
        )

        view = TopicPromptView(
            user_id=timer.discord_user_id,
            session_id=session.id,
            duration_seconds=timer.planned_seconds,
        )

        channel = None
        if timer.channel_id:
            channel = bot.get_channel(timer.channel_id)
            if not channel:
                try:
                    channel = await bot.fetch_channel(timer.channel_id)
                except Exception:
                    pass

        content = f"⏰ <@{timer.discord_user_id}> **SESSION COMPLETE!**"
        if channel:
            await channel.send(content=content, embed=embed, view=view)
        else:
            user_obj = bot.get_user(timer.discord_user_id) or await bot.fetch_user(timer.discord_user_id)
            if user_obj:
                await user_obj.send(content=content, embed=embed, view=view)

    except Exception as e:
        logger.error(f"Error handling session completion for timer {timer.session_id}: {e}", exc_info=True)


def register_events(bot: commands.Bot) -> None:
    """Registers global bot listeners and app command error handlers."""

    @bot.event
    async def on_ready():
        logger.info(f"Logged in as {bot.user} (ID: {bot.user.id})")
        logger.info("Initializing database and seeding achievements...")
        await db_manager.init_db()

        # Initialize timer service with completion callback
        timer_service.initialize(
            bot=bot,
            completion_callback=lambda t: handle_session_completion_event(bot, t)
        )

        # Recover any active sessions that survived restart
        await timer_service.recover_active_sessions()

        # Sync slash commands
        try:
            synced = await bot.tree.sync()
            logger.info(f"Successfully synced {len(synced)} slash commands.")
        except Exception as e:
            logger.error(f"Failed to sync slash commands: {e}")

        # Set rich presence
        await bot.change_presence(
            activity=discord.Activity(
                type=discord.ActivityType.watching,
                name="you study | /study"
            )
        )

    @bot.tree.error
    async def on_app_command_error(interaction: discord.Interaction, error: app_commands.AppCommandError):
        logger.error(f"Command error on '{interaction.command.name if interaction.command else 'unknown'}': {error}", exc_info=True)

        if isinstance(error, app_commands.CommandOnCooldown):
            msg = f"⏳ This command is on cooldown. Try again in {error.retry_after:.1f}s."
        elif isinstance(error, app_commands.MissingPermissions):
            msg = "🚫 You do not have permission to execute this command."
        else:
            msg = "⚠️ An unexpected error occurred while processing this command."

        if interaction.response.is_done():
            await interaction.followup.send(msg, ephemeral=True)
        else:
            await interaction.response.send_message(msg, ephemeral=True)
