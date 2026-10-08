from __future__ import annotations

import discord
from discord import app_commands
from discord.ext import commands


class HelpCog(commands.Cog, name="Help"):
    """Command guide and user manual for LOCKIN."""

    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(name="help", description="Learn how to use LOCKIN and master your study sessions.")
    async def help_command(self, interaction: discord.Interaction):
        """Displays full interactive user guide."""
        embed = discord.Embed(
            title="🔒 LOCKIN — Your Personal Study & Accountability Bot",
            description=(
                "LOCKIN is designed to keep you focused, consistent, and accountable.\n"
                "Here is everything you need to know to lock in and level up."
            ),
            color=discord.Color.gold(),
        )

        embed.add_field(
            name="📚 Core Commands",
            value=(
                "• `/study [subject] [minutes]` — Start a focused study session.\n"
                "• `/stop` — Abandon or end your study session early (proportional XP awarded, no streak loss).\n"
                "• `/profile [user]` — View XP level, progress bar, streak, and recent topics.\n"
                "• `/stats [user]` — Deep dive into study analytics, hours, and subject breakdown.\n"
                "• `/leaderboard [metric] [scope]` — Check top studiers across the server or globally.\n"
                "• `/settings` — Customize motivation interval and quiz triggers.\n"
                "• `/help` — Display this manual."
            ),
            inline=False,
        )

        embed.add_field(
            name="⚡ XP & Level System",
            value=(
                "• **1 minute studied = 1 XP**\n"
                "• **Post-Study Quiz Bonuses:** Up to `+50 XP` for 90-100% score.\n"
                "• **Daily Streak Bonuses:** Up to `+50 XP` per active streak day.\n"
                "• **Milestone Achievements:** Unlock badges with large XP bursts!"
            ),
            inline=False,
        )

        embed.add_field(
            name="🔥 Streak Rules",
            value=(
                "• Study at least once each day to maintain and increment your streak.\n"
                "• Multiple sessions in one day keep your streak active.\n"
                "• Stopping early does **not** break an existing streak.\n"
                "• If a streak ends, start a new one anytime without heavy penalties."
            ),
            inline=False,
        )

        embed.add_field(
            name="🧠 AI Post-Study Quizzes",
            value=(
                "When your timer hits zero, LOCKIN generates a personalized 5-question quiz.\n"
                "Answer Multiple Choice, True/False, and Short Answer questions to test your real comprehension!"
            ),
            inline=False,
        )

        embed.set_footer(text="Ready to cook? Type /study to begin.")
        await interaction.response.send_message(embed=embed)


async def setup(bot: commands.Bot):
    await bot.add_cog(HelpCog(bot))
