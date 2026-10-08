from __future__ import annotations

from typing import Optional
import discord
from discord import app_commands
from discord.ext import commands

from database.database import db_manager
from database.repositories.user_repository import UserRepository
from utils.logging import setup_logger

logger = setup_logger("lockin.commands.settings")


class SettingsCog(commands.Cog, name="Settings"):
    """Commands for customizing study motivation, notification frequency, and quiz preferences."""

    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(name="settings", description="Configure your personal study preferences.")
    @app_commands.describe(
        motivation="Enable or disable periodic motivational nudges during study sessions",
        interval="Minutes between motivational messages (10 to 60 minutes)",
        auto_quiz="Prompt post-study quiz immediately upon timer completion",
    )
    async def settings_command(
        self,
        interaction: discord.Interaction,
        motivation: Optional[bool] = None,
        interval: Optional[int] = None,
        auto_quiz: Optional[bool] = None,
    ):
        """Updates user preferences."""
        if motivation is None and interval is None and auto_quiz is None:
            # Display current settings
            async with db_manager.session() as sess:
                user_repo = UserRepository(sess)
                user = await user_repo.get_or_create_user(interaction.user.id, interaction.user.display_name)

            embed = discord.Embed(
                title=f"⚙️ Study Preferences — {interaction.user.display_name}",
                description="Use `/settings [motivation] [interval] [auto_quiz]` to adjust values.",
                color=discord.Color.blurple(),
            )
            embed.add_field(
                name="🔔 Motivation Nudges",
                value="`Enabled ✅`" if user.motivation_enabled else "`Disabled ❌`",
                inline=True,
            )
            embed.add_field(
                name="⏱️ Motivation Interval",
                value=f"`Every {user.motivation_interval_minutes} mins`",
                inline=True,
            )
            embed.add_field(
                name="🧠 Auto-Quiz Prompt",
                value="`Enabled ✅`" if user.auto_quiz_enabled else "`Disabled ❌`",
                inline=True,
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return

        if interval is not None and (interval < 5 or interval > 120):
            await interaction.response.send_message(
                "❌ Motivation interval must be between 5 and 120 minutes.",
                ephemeral=True,
            )
            return

        async with db_manager.session() as sess:
            user_repo = UserRepository(sess)
            user = await user_repo.get_or_create_user(interaction.user.id, interaction.user.display_name)
            updated_user = await user_repo.update_preferences(
                user_id=user.id,
                motivation_enabled=motivation,
                motivation_interval_minutes=interval,
                auto_quiz_enabled=auto_quiz,
            )

        embed = discord.Embed(
            title="✅ Preferences Updated",
            description="Your study preferences have been successfully updated.",
            color=discord.Color.green(),
        )
        embed.add_field(
            name="🔔 Motivation Nudges",
            value="`Enabled ✅`" if updated_user.motivation_enabled else "`Disabled ❌`",
            inline=True,
        )
        embed.add_field(
            name="⏱️ Motivation Interval",
            value=f"`Every {updated_user.motivation_interval_minutes} mins`",
            inline=True,
        )
        embed.add_field(
            name="🧠 Auto-Quiz Prompt",
            value="`Enabled ✅`" if updated_user.auto_quiz_enabled else "`Disabled ❌`",
            inline=True,
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)


async def setup(bot: commands.Bot):
    await bot.add_cog(SettingsCog(bot))
