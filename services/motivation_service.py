from __future__ import annotations

import random
from typing import Optional, List, Dict


class MotivationService:
    """
    Supplies witty, goofy, encouraging, and teasing motivational messages.
    """

    MESSAGES: Dict[str, List[str]] = {
        "encouraging": [
            "You've got this. Stay locked in.",
            "Keep going. One more section.",
            "You're making real progress. Keep the momentum going.",
            "Future you is going to thank current you for this focus session.",
            "Focus is a muscle. You are building it right now.",
            "Small consistent steps turn into massive breakthroughs.",
        ],
        "goofy": [
            "THE LOCK-IN IS REAL 🗣️",
            "Bro is actually studying. Respect.",
            "Academic weapon loading... 🔋",
            "Dopamine receptors healing in real-time.",
            "Brain wrinkles multiplying right now. 🧠",
            "No distractions. Pure intellectual grit.",
            "Lock in mode: ACTIVATED 🔒",
        ],
        "teasing": [
            "Don't you dare open that social media tab. 👀",
            "I saw that micro-distraction. Eyes back on the prize!",
            "Do not fumble the lock-in now.",
            "The textbook thinks it can beat you? Prove it wrong.",
            "Stay strong. The memes will still be there after you finish.",
        ],
        "milestone": [
            "🧠 Good chunk of time down. Keep cooking.",
            "🔥 Halfway through the session. Unstoppable pace.",
            "👀 Still studying? Absolute dedication.",
            "⚡ Final stretch incoming. Bring it home!",
        ],
        "high_score": [
            "🗿 ACADEMIC WEAPON DETECTED.",
            "👑 God-tier focus unlocked.",
            "🚀 In an absolute flow state right now.",
        ]
    }

    @classmethod
    def get_random_message(cls, category: Optional[str] = None) -> str:
        """Returns a random motivational message, optionally filtered by category."""
        if category and category in cls.MESSAGES:
            pool = cls.MESSAGES[category]
        else:
            # Combine all
            pool = [msg for cat_msgs in cls.MESSAGES.values() for msg in cat_msgs]
        return random.choice(pool)

    @classmethod
    def get_interval_message(cls, elapsed_seconds: int, total_seconds: int) -> str:
        """Generates contextual motivational nudge based on session progress."""
        elapsed_min = elapsed_seconds // 60
        total_min = max(1, total_seconds // 60)
        progress = elapsed_seconds / max(1, total_seconds)

        if 0.45 <= progress <= 0.55:
            return f"🔥 Halfway there ({elapsed_min}/{total_min} mins).\nDo not fumble the lock-in."
        elif elapsed_min >= 20 and elapsed_min < 30:
            return f"🧠 {elapsed_min} minutes down.\nKeep cooking."
        elif progress >= 0.8:
            return f"⚡ In the final stretch ({elapsed_min}/{total_min} mins)!\nFinish strong."
        else:
            msg = cls.get_random_message()
            return f"👀 {elapsed_min} minutes in.\n{msg}"


motivation_service = MotivationService()
