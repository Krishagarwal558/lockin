from __future__ import annotations

from typing import Optional
import discord
from discord import app_commands
from discord.ext import commands

from services.study_service import study_service
from bot.embeds.profile_embeds import profile_embed
from bot.views.profile_view import ProfileNavigationView
from utils.logging import setup_logger

logger = setup_logger("lockin.commands.profile")


class ProfileCog(commands.Cog, name="Profile"):
    """Commands for viewing learner profiles and progression cards."""

    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(name="profile", description="View your or another user's LOCKIN study profile.")
    @app_commands.describe(user="The user whose profile you want to inspect (defaults to yourself)")
    async def profile(
        self,
        interaction: discord.Interaction,
        user: Optional[discord.User] = None,
    ):
        """Displays user profile card with level, XP progress bar, streaks, and stats."""
        target_user = user or interaction.user
        await interaction.response.defer()

        try:
            profile_data = await study_service.get_user_profile(
                discord_user_id=target_user.id,
                username=target_user.display_name,
            )
            embed = profile_embed(profile_data, target_user)
            view = ProfileNavigationView(target_user=target_user, viewer_id=interaction.user.id)
            await interaction.followup.send(embed=embed, view=view)

        except Exception as e:
            logger.error(f"Error fetching profile for user {target_user.id}: {e}", exc_info=True)
            await interaction.followup.send(f"⚠️ Could not load profile: {e}", ephemeral=True)


async def setup(bot: commands.Bot):
    await bot.add_cog(ProfileCog(bot))
