from __future__ import annotations

from typing import Optional
from datetime import timedelta
import discord
from discord import app_commands
from discord.ext import commands
from discord.ui import Modal, TextInput

from services.study_service import study_service
from services.timer_service import timer_service
from bot.views.study_view import DurationSelectView, StopConfirmationView
from bot.embeds.study_embeds import lockin_started_embed, early_stop_confirm_embed
from utils.time import utc_now
from utils.logging import setup_logger

logger = setup_logger("lockin.commands.study")


class SubjectInputModal(Modal, title="Start Lock-In Session"):
    subject_input = TextInput(
        label="📚 What are you studying?",
        placeholder="e.g. Physics, Data Structures, Calculus, History...",
        required=True,
        max_length=100,
    )

    async def on_submit(self, interaction: discord.Interaction):
        subject = self.subject_input.value.strip()
        view = DurationSelectView(user_id=interaction.user.id, subject=subject)
        await interaction.response.send_message(
            f"📚 **Subject:** `{subject}`\n⏱️ **How long are you locking in?**",
            view=view,
            ephemeral=False,
        )


class StudyCog(commands.Cog, name="Study"):
    """Commands for starting, tracking, and stopping focus study sessions."""

    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(name="study", description="Start a focus study session and lock in.")
    @app_commands.describe(
        subject="What subject or topic you are studying (e.g. Physics, Chemistry, Math)",
        minutes="Optional duration in minutes (e.g. 25, 45, 60, 90)",
    )
    async def study(
        self,
        interaction: discord.Interaction,
        subject: Optional[str] = None,
        minutes: Optional[int] = None,
    ):
        """Starts an accountability study session."""
        user_id = interaction.user.id

        if timer_service.is_user_studying(user_id):
            await interaction.response.send_message(
                "⚠️ You already have an active study session running! Use `/stop` if you need to end it.",
                ephemeral=True,
            )
            return

        # Case 1: Neither subject nor minutes given -> Pop up Subject Modal
        if not subject:
            modal = SubjectInputModal()
            await interaction.response.send_modal(modal)
            return

        # Case 2: Subject given, but no minutes -> Show duration selection buttons
        if not minutes:
            view = DurationSelectView(user_id=user_id, subject=subject.strip())
            await interaction.response.send_message(
                f"📚 **Subject:** `{subject.strip()}`\n⏱️ **How long are you locking in?**",
                view=view,
            )
            return

        # Case 3: Both subject and minutes provided -> Start directly
        if minutes < 1 or minutes > 720:
            await interaction.response.send_message(
                "❌ Session duration must be between 1 and 720 minutes (12 hours).",
                ephemeral=True,
            )
            return

        planned_seconds = minutes * 60
        end_time = utc_now() + timedelta(seconds=planned_seconds)

        try:
            session, timer = await study_service.start_study_session(
                discord_user_id=user_id,
                username=interaction.user.display_name,
                subject=subject.strip(),
                planned_seconds=planned_seconds,
                channel_id=interaction.channel_id,
                guild_id=interaction.guild_id,
            )

            embed = lockin_started_embed(
                user_id=user_id,
                subject=subject.strip(),
                duration_minutes=minutes,
                end_time=end_time,
            )
            await interaction.response.send_message(embed=embed)

        except ValueError as e:
            await interaction.response.send_message(f"⚠️ {e}", ephemeral=True)

    @app_commands.command(name="stop", description="Stop your active study session.")
    async def stop(self, interaction: discord.Interaction):
        """Stops the ongoing study session with confirmation."""
        user_id = interaction.user.id
        timer = timer_service.get_active_timer(user_id)

        if not timer:
            await interaction.response.send_message(
                "❌ You don't have an active study session running. Start one with `/study`!",
                ephemeral=True,
            )
            return

        remaining_seconds = timer.remaining_seconds
        embed = early_stop_confirm_embed(remaining_seconds)
        view = StopConfirmationView(user_id=user_id, remaining_seconds=remaining_seconds)
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)


async def setup(bot: commands.Bot):
    await bot.add_cog(StudyCog(bot))
