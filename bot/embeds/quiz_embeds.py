from __future__ import annotations

import json
from typing import Optional, List, Dict, Any
import discord
from database.models import Question, Achievement
from utils.time import format_duration_clock, format_duration
from utils.formatting import format_percentage, streak_badge
from ai.schemas import StudyFeedbackSchema


def quiz_question_embed(
    current_index: int,
    total_count: int,
    question: Question,
    topic: str,
) -> discord.Embed:
    """Renders single question card for quiz presentation."""
    q_type = question.question_type
    embed = discord.Embed(
        title=f"🧠 QUESTION {current_index}/{total_count}",
        description=f"**Topic:** `{topic}`\n\n### {question.question_text}",
        color=discord.Color.purple(),
    )

    if q_type == "multiple_choice" and question.options_json:
        options = json.loads(question.options_json)
        letters = ["A", "B", "C", "D", "E"]
        opt_lines = [f"**{letters[i]}.** {opt}" for i, opt in enumerate(options)]
        embed.add_field(
            name="Options",
            value="\n".join(opt_lines),
            inline=False,
        )
    elif q_type == "true_false":
        embed.add_field(
            name="Options",
            value="**A.** True\n**B.** False",
            inline=False,
        )
    else:
        embed.add_field(
            name="✍️ Short Answer Question",
            value="Click the **'Submit Answer'** button below to type your response.",
            inline=False,
        )

    embed.set_footer(text=f"Question Type: {q_type.replace('_', ' ').title()}")
    return embed


def answer_result_embed(
    is_correct: bool,
    score: float,
    user_answer: str,
    correct_answer: str,
    feedback: str,
    explanation: Optional[str] = None,
) -> discord.Embed:
    """Renders immediate feedback card after user submits answer."""
    if is_correct:
        title = "✅ Correct!"
        color = discord.Color.green()
        xp_text = "+20 XP" if score >= 0.8 else "+10 XP"
    else:
        title = "❌ Not quite."
        color = discord.Color.red()
        xp_text = "+0 XP"

    desc_lines = [
        f"**Your Answer:** `{user_answer}`",
        f"**Expected Answer:** `{correct_answer}`",
        f"**Evaluation Score:** `{format_percentage(score)}`\n",
        f"> *{feedback}*",
    ]

    if explanation:
        desc_lines.append(f"\n💡 **Explanation:** {explanation}")

    desc_lines.append(f"\n**{xp_text}**")

    embed = discord.Embed(
        title=title,
        description="\n".join(desc_lines),
        color=color,
    )
    return embed


def study_report_embed(
    topic: str,
    duration_seconds: int,
    correct_count: int,
    total_questions: int,
    score_ratio: float,
    total_xp_earned: int,
    streak_days: int,
    feedback: StudyFeedbackSchema,
    new_achievements: Optional[List[Achievement]] = None,
) -> discord.Embed:
    """Renders the comprehensive final study report embed."""
    badge = streak_badge(streak_days)
    score_pct = format_percentage(score_ratio)

    embed = discord.Embed(
        title="╔════════════════════════════╗\n       📚 STUDY REPORT\n╚════════════════════════════╝",
        description=f"Great job locking in on **{topic}**!",
        color=discord.Color.gold(),
    )

    embed.add_field(name="📖 Topic", value=f"`{topic}`", inline=True)
    embed.add_field(name="⏱️ Study Time", value=f"`{format_duration_clock(duration_seconds)}`", inline=True)
    embed.add_field(name="🎯 Quiz Score", value=f"`{correct_count} / {total_questions}` ({score_pct})", inline=True)

    embed.add_field(name="✨ Total XP Earned", value=f"`+{total_xp_earned} XP`", inline=True)
    embed.add_field(name=f"{badge} Streak", value=f"`{streak_days} days`", inline=True)
    embed.add_field(name="📊 Comprehension", value=f"`{score_pct}`", inline=True)

    # Bot Verdict
    embed.add_field(
        name="🤖 Bot Verdict",
        value=f"> {feedback.verdict}",
        inline=False,
    )

    if feedback.strengths:
        embed.add_field(
            name="💪 Concepts Mastered",
            value="\n".join([f"• {s}" for s in feedback.strengths]),
            inline=True,
        )

    if feedback.weaknesses:
        embed.add_field(
            name="🔍 Needs Polish",
            value="\n".join([f"• {w}" for w in feedback.weaknesses]),
            inline=True,
        )

    # Recommendation
    embed.add_field(
        name="📌 Recommended Next Step",
        value=f"```fix\n{feedback.recommendation}\n```",
        inline=False,
    )

    # Achievements
    if new_achievements:
        ach_lines = [f"{a.icon} **{a.name}** (`+{a.xp_reward} XP`)" for a in new_achievements]
        embed.add_field(
            name="🏆 Achievements Unlocked!",
            value="\n".join(ach_lines),
            inline=False,
        )

    embed.set_footer(text="Keep the momentum going! Use /study for your next session.")
    return embed
