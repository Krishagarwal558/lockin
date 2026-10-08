from __future__ import annotations

from datetime import datetime
import discord
from utils.time import format_duration, format_duration_clock, discord_timestamp, format_minutes_short
from utils.formatting import streak_badge


def lockin_started_embed(
    user_id: int,
    subject: str,
    duration_minutes: int,
    end_time: datetime,
) -> discord.Embed:
    """Creates the signature LOCK-IN STARTED embed."""
    embed = discord.Embed(
        title="🔒 LOCK-IN STARTED",
        description=(
            f"<@{user_id}> has initiated a focus session.\n\n"
            f"**Subject:** `{subject}`\n"
            f"**Duration:** `{format_minutes_short(duration_minutes)}`\n"
            f"**Completes:** {discord_timestamp(end_time, 'R')} ({discord_timestamp(end_time, 't')})\n\n"
            f"> *No excuses. I'll see you at the finish line.* 🗿"
        ),
        color=discord.Color.blue(),
    )
    embed.set_footer(text="Use /stop to end session early.")
    return embed


def session_complete_embed(
    user_id: int,
    subject: str,
    duration_seconds: int,
    base_xp: int,
    streak_days: int,
) -> discord.Embed:
    """Creates the SESSION COMPLETE embed announcing post-study check."""
    badge = streak_badge(streak_days)
    embed = discord.Embed(
        title="⏰ SESSION COMPLETE",
        description=(
            f"Congratulations <@{user_id}>! You survived **{format_duration(duration_seconds)}** of pure focus.\n\n"
            f"**Subject:** `{subject}`\n"
            f"**Base XP Earned:** `+{base_xp} XP`\n"
            f"**Current Streak:** {badge} `{streak_days} days`\n\n"
            f"Now prove you actually learned something. 🧠\n"
            f"**POST-STUDY CHECK**"
        ),
        color=discord.Color.green(),
    )
    embed.set_footer(text="Click 'Start Post-Study Quiz' or provide your topic below!")
    return embed


def early_stop_confirm_embed(remaining_seconds: int) -> discord.Embed:
    """Creates the confirmation prompt for early stop."""
    rem_min = max(1, remaining_seconds // 60)
    embed = discord.Embed(
        title="⚠️ Abandon Session?",
        description=(
            f"You still have **{rem_min} minutes** remaining on your timer.\n\n"
            f"Are you sure you want to abandon the session?"
        ),
        color=discord.Color.orange(),
    )
    return embed


def early_stop_summary_embed(
    subject: str,
    actual_seconds: int,
    xp_earned: int,
    fun_message: str,
) -> discord.Embed:
    """Creates the summary embed after an early stop."""
    embed = discord.Embed(
        title="🫡 Session Ended Early",
        description=(
            f"**Subject:** `{subject}`\n"
            f"**Actual Study Time:** `{format_duration(actual_seconds)}`\n"
            f"**XP Awarded:** `+{xp_earned} XP`\n\n"
            f"> *{fun_message}*"
        ),
        color=discord.Color.dark_gray(),
    )
    return embed
