from __future__ import annotations

from datetime import datetime, timezone, timedelta
from typing import Optional


def utc_now() -> datetime:
    """Returns the current UTC datetime with timezone awareness."""
    return datetime.now(timezone.utc)


def ensure_utc(dt: Optional[datetime]) -> Optional[datetime]:
    """Ensures datetime is timezone-aware UTC datetime."""
    if dt is None:
        return None
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def format_duration(seconds: int | float) -> str:
    """
    Formats total seconds into human-readable hours, minutes, and seconds.
    Example: 3665 -> "01h 01m 05s" or "45m 00s"
    """
    sec = max(0, int(seconds))
    hours = sec // 3600
    minutes = (sec % 3600) // 60
    remaining_sec = sec % 60

    if hours > 0:
        return f"{hours}h {minutes:02d}m"
    elif minutes > 0:
        return f"{minutes}m {remaining_sec:02d}s"
    else:
        return f"{remaining_sec}s"


def format_duration_clock(seconds: int | float) -> str:
    """
    Formats total seconds into standard digital clock format: HH:MM:SS.
    Example: 3600 -> "01:00:00"
    """
    sec = max(0, int(seconds))
    hours = sec // 3600
    minutes = (sec % 3600) // 60
    remaining_sec = sec % 60
    return f"{hours:02d}:{minutes:02d}:{remaining_sec:02d}"


def format_minutes_short(minutes: int) -> str:
    """
    Formats minutes into a friendly string.
    Example: 60 -> "60 minutes", 120 -> "2 hours"
    """
    if minutes < 60:
        return f"{minutes} minutes"
    hours = minutes // 60
    rem_min = minutes % 60
    if rem_min == 0:
        return f"{hours} hour" if hours == 1 else f"{hours} hours"
    return f"{hours}h {rem_min}m"


def discord_timestamp(dt: datetime, style: str = "R") -> str:
    """
    Returns a Discord markdown timestamp tag.
    Styles: 'R' (relative: 10 minutes ago), 't' (short time: 9:01 PM), 'T' (long time), 'd' (short date), 'D' (long date), 'F' (full).
    """
    unix_time = int(dt.timestamp())
    return f"<t:{unix_time}:{style}>"


def parse_duration_string(text: str) -> Optional[int]:
    """
    Parses duration input like "25", "25m", "1h", "1h30m", "90 mins" into seconds.
    Returns None if parsing fails or result is invalid.
    """
    cleaned = text.strip().lower()
    # Direct integer assumed as minutes
    if cleaned.isdigit():
        mins = int(cleaned)
        return mins * 60 if 1 <= mins <= 720 else None

    # Common text match
    import re
    h_match = re.search(r'(\d+)\s*(?:h|hr|hour|hours)', cleaned)
    m_match = re.search(r'(\d+)\s*(?:m|min|minute|minutes)', cleaned)

    hours = int(h_match.group(1)) if h_match else 0
    minutes = int(m_match.group(1)) if m_match else 0

    if hours == 0 and minutes == 0:
        # Check if just digits in string
        digits_only = re.sub(r'[^\d]', '', cleaned)
        if digits_only:
            mins = int(digits_only)
            return mins * 60 if 1 <= mins <= 720 else None
        return None

    total_seconds = (hours * 3600) + (minutes * 60)
    # Range check: 1 min to 12 hours (43200s)
    if 60 <= total_seconds <= 43200:
        return total_seconds
    return None
