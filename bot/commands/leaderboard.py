from __future__ import annotations

from typing import Literal, Optional
import discord
from discord import app_commands
from discord.ext import commands

from database.database import db_manager
from database.repositories.user_repository import UserRepository
from bot.embeds.profile_embeds import leaderboard_embed
from utils.logging import setup_logger

logger = setup_logger("lockin.commands.leaderboard")


class LeaderboardCog(commands.Cog, name="Leaderboard"):
    """Commands for displaying study leaderboards."""

    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(name="leaderboard", description="View the study leaderboard.")
    @app_commands.describe(
        metric="Rank by total study time or total XP earned",
        scope="View server members only or global ranking",
    )
    async def leaderboard(
        self,
        interaction: discord.Interaction,
        metric: Literal["time", "xp"] = "time",
        scope: Literal["server", "global"] = "server",
    ):
        """Displays top studiers leaderboard."""
        await interaction.response.defer()

        try:
            guild_user_ids = None
            if scope == "server" and interaction.guild:
                guild_user_ids = [m.id for m in interaction.guild.members]

            async with db_manager.session() as sess:
                user_repo = UserRepository(sess)
                top_users = await user_repo.get_leaderboard(
                    limit=10,
                    discord_user_ids=guild_user_ids,
                    order_by_xp=(metric == "xp"),
                )

            embed = leaderboard_embed(top_users, is_xp_leaderboard=(metric == "xp"))
            await interaction.followup.send(embed=embed)

        except Exception as e:
            logger.error(f"Error fetching leaderboard: {e}", exc_info=True)
            await interaction.followup.send(f"⚠️ Could not load leaderboard: {e}", ephemeral=True)


async def setup(bot: commands.Bot):
    await bot.add_cog(LeaderboardCog(bot))
