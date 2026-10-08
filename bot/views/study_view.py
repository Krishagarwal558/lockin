from __future__ import annotations

from typing import Optional, Callable
from datetime import timedelta
import discord
from discord.ui import View, Button, Modal, TextInput

from services.study_service import study_service
from bot.embeds.study_embeds import (
    lockin_started_embed,
    early_stop_confirm_embed,
    early_stop_summary_embed,
)
from utils.time import utc_now, parse_duration_string
from utils.logging import setup_logger

logger = setup_logger("lockin.views.study")


class CustomDurationModal(Modal, title="Custom Study Duration"):
    duration_input = TextInput(
        label="Duration (in minutes or e.g. 1h 30m)",
        placeholder="e.g. 30, 45, 1h, 90m",
        required=True,
        max_length=20,
    )

    def __init__(self, subject: str, on_submit_callback: Callable[[int, str, discord.Interaction], None]):
        super().__init__()
        self.subject = subject
        self.on_submit_callback = on_submit_callback

    async def on_submit(self, interaction: discord.Interaction):
        seconds = parse_duration_string(self.duration_input.value)
        if not seconds:
            await interaction.response.send_message(
                "❌ Invalid duration. Please enter between 1 minute and 12 hours (e.g., 25, 45m, 1h30m).",
                ephemeral=True,
            )
            return

        minutes = seconds // 60
        await self.on_submit_callback(minutes, self.subject, interaction)


class DurationSelectView(View):
    def __init__(self, user_id: int, subject: str):
        super().__init__(timeout=120)
        self.user_id = user_id
        self.subject = subject

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("❌ This is not your session prompt!", ephemeral=True)
            return False
        return True

    async def _start_session_with_minutes(self, minutes: int, subject: str, interaction: discord.Interaction):
        planned_seconds = minutes * 60
        end_time = utc_now() + timedelta(seconds=planned_seconds)

        try:
            session, timer = await study_service.start_study_session(
                discord_user_id=interaction.user.id,
                username=interaction.user.display_name,
                subject=subject,
                planned_seconds=planned_seconds,
                channel_id=interaction.channel_id,
                guild_id=interaction.guild_id,
            )

            embed = lockin_started_embed(
                user_id=interaction.user.id,
                subject=subject,
                duration_minutes=minutes,
                end_time=end_time,
            )

            if not interaction.response.is_done():
                await interaction.response.edit_message(content=None, embed=embed, view=None)
            else:
                await interaction.edit_original_response(content=None, embed=embed, view=None)

        except ValueError as e:
            if not interaction.response.is_done():
                await interaction.response.send_message(f"⚠️ {e}", ephemeral=True)
            else:
                await interaction.followup.send(f"⚠️ {e}", ephemeral=True)

    @discord.ui.button(label="25m (Pomodoro)", style=discord.ButtonStyle.primary, emoji="🍅")
    async def btn_25(self, interaction: discord.Interaction, button: Button):
        await self._start_session_with_minutes(25, self.subject, interaction)

    @discord.ui.button(label="45m (Focus)", style=discord.ButtonStyle.primary, emoji="⏳")
    async def btn_45(self, interaction: discord.Interaction, button: Button):
        await self._start_session_with_minutes(45, self.subject, interaction)

    @discord.ui.button(label="60m (Deep Work)", style=discord.ButtonStyle.success, emoji="🔥")
    async def btn_60(self, interaction: discord.Interaction, button: Button):
        await self._start_session_with_minutes(60, self.subject, interaction)

    @discord.ui.button(label="90m (Mastery)", style=discord.ButtonStyle.secondary, emoji="🗿")
    async def btn_90(self, interaction: discord.Interaction, button: Button):
        await self._start_session_with_minutes(90, self.subject, interaction)

    @discord.ui.button(label="Custom Duration", style=discord.ButtonStyle.secondary, emoji="⚙️")
    async def btn_custom(self, interaction: discord.Interaction, button: Button):
        modal = CustomDurationModal(subject=self.subject, on_submit_callback=self._start_session_with_minutes)
        await interaction.response.send_modal(modal)


class StopConfirmationView(View):
    def __init__(self, user_id: int, remaining_seconds: int):
        super().__init__(timeout=60)
        self.user_id = user_id
        self.remaining_seconds = remaining_seconds

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("❌ This is not your session prompt!", ephemeral=True)
            return False
        return True

    @discord.ui.button(label="Continue Studying", style=discord.ButtonStyle.success, emoji="💪")
    async def btn_continue(self, interaction: discord.Interaction, button: Button):
        await interaction.response.edit_message(
            content="🔥 **Lock-in preserved!** Keep pushing.",
            embed=None,
            view=None,
        )

    @discord.ui.button(label="Stop Session", style=discord.ButtonStyle.danger, emoji="🛑")
    async def btn_stop(self, interaction: discord.Interaction, button: Button):
        try:
            session, actual_seconds, xp_earned, fun_msg = await study_service.stop_study_session_early(
                discord_user_id=interaction.user.id
            )
            embed = early_stop_summary_embed(
                subject=session.subject if session else "Study",
                actual_seconds=actual_seconds,
                xp_earned=xp_earned,
                fun_message=fun_msg,
            )
            await interaction.response.edit_message(content=None, embed=embed, view=None)
        except ValueError as e:
            await interaction.response.edit_message(content=f"⚠️ {e}", embed=None, view=None)
