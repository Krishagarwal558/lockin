from __future__ import annotations

from typing import Dict, Any, List, Sequence
import discord
from database.models import User, Achievement, UserAchievement
from utils.formatting import render_progress_bar, streak_badge, format_percentage, get_rank_medal
from utils.time import format_duration, format_minutes_short


def profile_embed(profile_data: Dict[str, Any], user_obj: discord.User | discord.Member) -> discord.Embed:
    """Renders user's core profile card."""
    user: User = profile_data["user"]
    level: int = profile_data["level"]
    xp_in_level: int = profile_data["xp_in_level"]
    xp_needed: int = profile_data["xp_needed"]
    total_xp: int = profile_data["total_xp"]
    current_streak: int = profile_data["current_streak"]
    longest_streak: int = profile_data["longest_streak"]
    total_seconds: int = profile_data["total_study_seconds"]
    sessions_count: int = profile_data["sessions_completed"]
    best_subject: str = profile_data["best_subject"]
    recent_topics: List[str] = profile_data["recent_topics"]
    quiz_stats: Dict[str, Any] = profile_data["quiz_stats"]
    achievements: List[tuple[Achievement, UserAchievement]] = profile_data["achievements"]

    progress_bar = render_progress_bar(xp_in_level, xp_needed, length=12)
    badge = streak_badge(current_streak)
    avg_score_str = format_percentage(quiz_stats.get("average_score", 0.0))

    embed = discord.Embed(
        title=f"📚 {user.username.upper()}'S PROFILE",
        color=discord.Color.blue(),
    )
    if hasattr(user_obj, "display_avatar") and user_obj.display_avatar:
        embed.set_thumbnail(url=user_obj.display_avatar.url)

    # Level & XP
    embed.add_field(
        name=f"⭐ Level {level}",
        value=(
            f"`{progress_bar}`\n"
            f"**{xp_in_level:,} / {xp_needed:,} XP** (Total: `{total_xp:,} XP`)"
        ),
        inline=False,
    )

    # Streak
    embed.add_field(
        name="🔥 Streak",
        value=f"{badge} **{current_streak} days** (Best: `{longest_streak}d`)",
        inline=True,
    )

    # Total Study Time
    embed.add_field(
        name="⏱️ Study Time",
        value=f"`{format_duration(total_seconds)}`",
        inline=True,
    )

    # Sessions
    embed.add_field(
        name="🎯 Sessions",
        value=f"`{sessions_count} completed`",
        inline=True,
    )

    # Quiz performance
    embed.add_field(
        name="🧠 Quiz Mastery",
        value=f"`{avg_score_str}` avg ({quiz_stats.get('total_quizzes', 0)} quizzes)",
        inline=True,
    )

    # Best Subject
    embed.add_field(
        name="🌟 Top Subject",
        value=f"`{best_subject}`",
        inline=True,
    )

    # Achievements summary
    embed.add_field(
        name="🏆 Achievements",
        value=f"`{len(achievements)} unlocked`",
        inline=True,
    )

    # Recent Topics
    if recent_topics:
        topics_str = "\n".join([f"• {t}" for t in recent_topics[:4]])
        embed.add_field(
            name="📝 Recent Topics",
            value=topics_str,
            inline=False,
        )

    embed.set_footer(text="LOCKIN • Stay disciplined, stay focused.")
    return embed


def stats_embed(profile_data: Dict[str, Any], user_obj: discord.User | discord.Member) -> discord.Embed:
    """Renders comprehensive study analytics embed."""
    user: User = profile_data["user"]
    total_seconds: int = profile_data["total_study_seconds"]
    sessions_count: int = profile_data["sessions_completed"]
    subjects = profile_data["subjects"]
    quiz_stats = profile_data["quiz_stats"]

    avg_sec = total_seconds / max(1, sessions_count)

    embed = discord.Embed(
        title=f"📊 Study Statistics — {user.username}",
        color=discord.Color.teal(),
    )
    if hasattr(user_obj, "display_avatar") and user_obj.display_avatar:
        embed.set_thumbnail(url=user_obj.display_avatar.url)

    embed.add_field(name="⏳ Total Focus Time", value=f"`{format_duration(total_seconds)}`", inline=True)
    embed.add_field(name="📅 Completed Sessions", value=f"`{sessions_count}`", inline=True)
    embed.add_field(name="📈 Average Session", value=f"`{format_duration(avg_sec)}`", inline=True)

    embed.add_field(name="🔥 Current Streak", value=f"`{user.current_streak} days`", inline=True)
    embed.add_field(name="⚡ Best Streak", value=f"`{user.longest_streak} days`", inline=True)
    embed.add_field(name="🧠 Quiz Avg Score", value=f"`{format_percentage(quiz_stats.get('average_score', 0.0))}`", inline=True)

    if subjects:
        subj_lines = []
        for s in subjects[:5]:
            subj_lines.append(f"• **{s['subject']}**: {format_duration(s['seconds'])} ({s['sessions']} sessions)")
        embed.add_field(
            name="📚 Subject Distribution",
            value="\n".join(subj_lines),
            inline=False,
        )

    return embed


def leaderboard_embed(users: Sequence[User], is_xp_leaderboard: bool = False) -> discord.Embed:
    """Renders the server study leaderboard embed."""
    title_metric = "XP" if is_xp_leaderboard else "Study Time"
    embed = discord.Embed(
        title=f"🏆 LOCKIN LEADERBOARD ({title_metric.upper()})",
        description="Top studiers putting in the work!",
        color=discord.Color.gold(),
    )

    if not users:
        embed.description = "No study sessions recorded yet. Start one with `/study`!"
        return embed

    lines = []
    for rank, u in enumerate(users, start=1):
        medal = get_rank_medal(rank)
        if is_xp_leaderboard:
            score_text = f"**{u.xp:,} XP** (Lvl {u.level})"
        else:
            score_text = f"**{format_duration(u.total_study_seconds)}**"
        
        badge = streak_badge(u.current_streak)
        lines.append(f"{medal} <@{u.discord_user_id}> — {score_text} {badge}")

    embed.add_field(name="Rankings", value="\n".join(lines), inline=False)
    embed.set_footer(text="Climb the ranks by locking in daily!")
    return embed


def achievements_embed(all_achievements: Sequence[Achievement], unlocked_slugs: set[str], username: str) -> discord.Embed:
    """Renders user's achievements list with locked/unlocked states."""
    embed = discord.Embed(
        title=f"🏆 Achievements Showcase — {username}",
        description=f"Unlocked **{len(unlocked_slugs)}/{len(all_achievements)}** badges",
        color=discord.Color.purple(),
    )

    for ach in all_achievements:
        is_unlocked = ach.slug in unlocked_slugs
        status_icon = ach.icon if is_unlocked else "🔒"
        status_name = ach.name if is_unlocked else f"~~{ach.name}~~"
        status_desc = ach.description if is_unlocked else f"*{ach.description}*"
        reward_text = f"`+{ach.xp_reward} XP`"

        embed.add_field(
            name=f"{status_icon} {status_name} ({reward_text})",
            value=f"{status_desc} {'✅' if is_unlocked else '❌'}",
            inline=False,
        )

    return embed
