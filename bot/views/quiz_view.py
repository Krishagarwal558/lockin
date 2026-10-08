from __future__ import annotations

import json
from typing import Optional
import discord
from discord.ui import View, Button, Modal, TextInput

from services.quiz_service import quiz_service, ActiveQuizSession
from bot.embeds.quiz_embeds import (
    quiz_question_embed,
    answer_result_embed,
    study_report_embed,
)
from database.database import db_manager
from database.repositories.user_repository import UserRepository
from utils.logging import setup_logger

logger = setup_logger("lockin.views.quiz")


class PostStudyTopicModal(Modal, title="Post-Study Knowledge Check"):
    topic_input = TextInput(
        label="What specific topic did you study?",
        placeholder="e.g. Newton's Laws, Organic Chemistry, Dynamic Programming...",
        required=True,
        max_length=150,
    )

    def __init__(self, session_id: Optional[int], study_duration_seconds: int):
        super().__init__()
        self.session_id = session_id
        self.study_duration_seconds = study_duration_seconds

    async def on_submit(self, interaction: discord.Interaction):
        topic = self.topic_input.value.strip()
        await interaction.response.defer(ephemeral=False)

        try:
            async with db_manager.session() as sess:
                user_repo = UserRepository(sess)
                user = await user_repo.get_or_create_user(interaction.user.id, interaction.user.display_name)

            # Start AI quiz generation
            active_quiz = await quiz_service.start_quiz(
                user=user,
                topic=topic,
                question_count=5,
                session_id=self.session_id,
            )

            # Render Question 1
            first_q = active_quiz.current_question
            if not first_q:
                await interaction.followup.send("❌ Error generating quiz questions. Please try again.")
                return

            embed = quiz_question_embed(
                current_index=1,
                total_count=active_quiz.total_questions,
                question=first_q,
                topic=active_quiz.topic,
            )
            view = QuizQuestionView(
                user_id=interaction.user.id,
                study_duration_seconds=self.study_duration_seconds,
            )
            await interaction.followup.send(embed=embed, view=view)

        except Exception as e:
            logger.error(f"Failed to generate quiz: {e}", exc_info=True)
            await interaction.followup.send(f"⚠️ Could not generate quiz right now: {e}")


class TopicPromptView(View):
    """View shown when study session completes to prompt for post-study quiz."""
    def __init__(self, user_id: int, session_id: Optional[int], duration_seconds: int):
        super().__init__(timeout=300)
        self.user_id = user_id
        self.session_id = session_id
        self.duration_seconds = duration_seconds

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("❌ This post-study check is for someone else!", ephemeral=True)
            return False
        return True

    @discord.ui.button(label="🧠 Start Post-Study Quiz", style=discord.ButtonStyle.success, emoji="📝")
    async def btn_start_quiz(self, interaction: discord.Interaction, button: Button):
        modal = PostStudyTopicModal(session_id=self.session_id, study_duration_seconds=self.duration_seconds)
        await interaction.response.send_modal(modal)

    @discord.ui.button(label="Skip Quiz", style=discord.ButtonStyle.secondary, emoji="⏭️")
    async def btn_skip(self, interaction: discord.Interaction, button: Button):
        await interaction.response.edit_message(
            content="🫡 Quiz skipped for this session. Study stats & XP have been saved!",
            view=None,
        )


class ShortAnswerModal(Modal, title="Submit Short Answer"):
    answer_input = TextInput(
        label="Your Answer",
        style=discord.TextStyle.paragraph,
        placeholder="Explain the concept concisely in your own words...",
        required=True,
        max_length=500,
    )

    def __init__(self, parent_view: QuizQuestionView):
        super().__init__()
        self.parent_view = parent_view

    async def on_submit(self, interaction: discord.Interaction):
        await interaction.response.defer()
        await self.parent_view.process_answer(interaction, self.answer_input.value.strip())


class QuizQuestionView(View):
    def __init__(self, user_id: int, study_duration_seconds: int):
        super().__init__(timeout=300)
        self.user_id = user_id
        self.study_duration_seconds = study_duration_seconds
        self._setup_dynamic_buttons()

    def _setup_dynamic_buttons(self):
        self.clear_items()
        active_quiz = quiz_service.get_active_quiz(self.user_id)
        if not active_quiz or active_quiz.is_finished:
            return

        current_q = active_quiz.current_question
        if not current_q:
            return

        q_type = current_q.question_type

        if q_type == "multiple_choice":
            # Add buttons A, B, C, D
            for letter in ["A", "B", "C", "D"]:
                btn = Button(
                    label=letter,
                    style=discord.ButtonStyle.primary,
                    custom_id=f"mc_{letter.lower()}"
                )
                btn.callback = self._make_choice_callback(letter)
                self.add_item(btn)
        elif q_type == "true_false":
            btn_true = Button(label="True", style=discord.ButtonStyle.success, custom_id="tf_true")
            btn_true.callback = self._make_choice_callback("True")
            btn_false = Button(label="False", style=discord.ButtonStyle.danger, custom_id="tf_false")
            btn_false.callback = self._make_choice_callback("False")
            self.add_item(btn_true)
            self.add_item(btn_false)
        else: # short_answer
            btn_write = Button(label="✍️ Type Answer", style=discord.ButtonStyle.primary, custom_id="sa_write")
            btn_write.callback = self._short_answer_callback
            self.add_item(btn_write)

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("❌ This is not your quiz!", ephemeral=True)
            return False
        return True

    def _make_choice_callback(self, choice_text: str):
        async def callback(interaction: discord.Interaction):
            await interaction.response.defer()
            await self.process_answer(interaction, choice_text)
        return callback

    async def _short_answer_callback(self, interaction: discord.Interaction):
        modal = ShortAnswerModal(parent_view=self)
        await interaction.response.send_modal(modal)

    async def process_answer(self, interaction: discord.Interaction, user_answer: str):
        active_quiz = quiz_service.get_active_quiz(self.user_id)
        if not active_quiz:
            await interaction.followup.send("⚠️ Quiz session expired.", ephemeral=True)
            return

        current_q = active_quiz.current_question
        is_correct, score, feedback, explanation = await quiz_service.submit_answer(
            discord_user_id=self.user_id,
            user_answer=user_answer,
        )

        # Show answer result embed with "Next Question" or "View Final Report"
        result_embed = answer_result_embed(
            is_correct=is_correct,
            score=score,
            user_answer=user_answer,
            correct_answer=current_q.correct_answer,
            feedback=feedback,
            explanation=explanation,
        )

        next_view = QuizTransitionView(
            user_id=self.user_id,
            study_duration_seconds=self.study_duration_seconds,
        )

        await interaction.edit_original_response(embed=result_embed, view=next_view)


class QuizTransitionView(View):
    def __init__(self, user_id: int, study_duration_seconds: int):
        super().__init__(timeout=180)
        self.user_id = user_id
        self.study_duration_seconds = study_duration_seconds

        active_quiz = quiz_service.get_active_quiz(self.user_id)
        if active_quiz and active_quiz.is_finished:
            self.btn_next.label = "📊 View Final Study Report"
            self.btn_next.style = discord.ButtonStyle.success

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("❌ This is not your quiz!", ephemeral=True)
            return False
        return True

    @discord.ui.button(label="Next Question ▶️", style=discord.ButtonStyle.primary)
    async def btn_next(self, interaction: discord.Interaction, button: Button):
        await interaction.response.defer()
        active_quiz = quiz_service.get_active_quiz(self.user_id)

        if not active_quiz:
            await interaction.followup.send("⚠️ Quiz session ended.", ephemeral=True)
            return

        if active_quiz.is_finished:
            # Finalize quiz & show study report
            summary = await quiz_service.finalize_quiz(
                discord_user_id=self.user_id,
                study_duration_minutes=max(1, self.study_duration_seconds // 60),
            )

            # Retrieve streak info
            async with db_manager.session() as sess:
                user_repo = UserRepository(sess)
                user = await user_repo.get_by_discord_id(self.user_id)
                streak_days = user.current_streak if user else 1

            report_embed = study_report_embed(
                topic=summary["topic"],
                duration_seconds=self.study_duration_seconds,
                correct_count=summary["correct_count"],
                total_questions=summary["total_questions"],
                score_ratio=summary["score_ratio"],
                total_xp_earned=(self.study_duration_seconds // 60) + summary["quiz_bonus_xp"],
                streak_days=streak_days,
                feedback=summary["ai_feedback"],
                new_achievements=summary["newly_unlocked_achievements"],
            )
            await interaction.edit_original_response(embed=report_embed, view=None)

        else:
            # Show next question
            next_q = active_quiz.current_question
            q_embed = quiz_question_embed(
                current_index=active_quiz.current_question_index + 1,
                total_count=active_quiz.total_questions,
                question=next_q,
                topic=active_quiz.topic,
            )
            q_view = QuizQuestionView(
                user_id=self.user_id,
                study_duration_seconds=self.study_duration_seconds,
            )
            await interaction.edit_original_response(embed=q_embed, view=q_view)
