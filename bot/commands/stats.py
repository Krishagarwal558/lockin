from __future__ import annotations

from typing import Optional
import discord
from discord import app_commands
from discord.ext import commands

from services.study_service import study_service
from bot.embeds.profile_embeds import stats_embed
from utils.logging import setup_logger

logger = setup_logger("lockin.commands.stats")


class StatsCog(commands.Cog, name="Stats"):
    """Commands for viewing detailed study statistics."""

    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(name="stats", description="View detailed study metrics and subject breakdown.")
    @app_commands.describe(user="The user whose stats you want to view (defaults to yourself)")
    async def stats(
        self,
        interaction: discord.Interaction,
        user: Optional[discord.User] = None,
    ):
        """Displays in-depth study session analytics."""
        target_user = user or interaction.user
        await interaction.response.defer()

        try:
            profile_data = await study_service.get_user_profile(
                discord_user_id=target_user.id,
                username=target_user.display_name,
            )
            embed = stats_embed(profile_data, target_user)
            await interaction.followup.send(embed=embed)

        except Exception as e:
            logger.error(f"Error fetching stats for user {target_user.id}: {e}", exc_info=True)
            await interaction.followup.send(f"⚠️ Could not load statistics: {e}", ephemeral=True)


async def setup(bot: commands.Bot):
    await bot.add_cog(StatsCog(bot))
