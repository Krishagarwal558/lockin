from __future__ import annotations


def render_progress_bar(current: int, total: int, length: int = 15, fill: str = "█", empty: str = "░") -> str:
    """
    Renders an ASCII/Unicode progress bar.
    Example: ██████████████░░░
    """
    if total <= 0:
        return empty * length
    ratio = min(max(current / total, 0.0), 1.0)
    filled_length = int(round(length * ratio))
    return (fill * filled_length) + (empty * (length - filled_length))


def format_percentage(score: float) -> str:
    """Formats a float score (0.0 - 1.0) or (0-100) into a clean percentage string."""
    if score <= 1.0:
        pct = score * 100
    else:
        pct = score
    return f"{pct:.0f}%"


def streak_badge(streak_days: int) -> str:
    """Returns a dynamic emoji badge based on streak count."""
    if streak_days >= 30:
        return "👑"
    elif streak_days >= 14:
        return "⚡"
    elif streak_days >= 7:
        return "🔥"
    elif streak_days >= 3:
        return "✨"
    elif streak_days >= 1:
        return "🌱"
    return "💤"


def get_rank_medal(index: int) -> str:
    """Returns podium medal for top positions."""
    if index == 1:
        return "🥇"
    elif index == 2:
        return "🥈"
    elif index == 3:
        return "🥉"
    return f"`#{index}`"
