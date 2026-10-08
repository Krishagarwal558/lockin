from __future__ import annotations

import json
from typing import List, Dict, Any, Optional, Tuple
from database.database import db_manager
from database.models import User, StudySession, Quiz, Question, Achievement
from database.repositories.quiz_repository import QuizRepository
from database.repositories.user_repository import UserRepository
from database.repositories.session_repository import SessionRepository
from database.repositories.achievement_repository import AchievementRepository
from services.xp_service import xp_service
from services.achievement_service import achievement_service
from ai.client import ai_client
from utils.logging import setup_logger
from config import settings

logger = setup_logger("lockin.quiz_service", settings.LOG_LEVEL)


class ActiveQuizSession:
    def __init__(
        self,
        quiz_id: int,
        session_id: Optional[int],
        user_id: int,
        discord_user_id: int,
        topic: str,
        questions: List[Question],
    ):
        self.quiz_id = quiz_id
        self.session_id = session_id
        self.user_id = user_id
        self.discord_user_id = discord_user_id
        self.topic = topic
        self.questions = questions
        self.current_question_index = 0
        self.results: List[Dict[str, Any]] = []

    @property
    def current_question(self) -> Optional[Question]:
        if 0 <= self.current_question_index < len(self.questions):
            return self.questions[self.current_question_index]
        return None

    @property
    def is_finished(self) -> bool:
        return self.current_question_index >= len(self.questions)

    @property
    def total_questions(self) -> int:
        return len(self.questions)

    @property
    def correct_count(self) -> int:
        return sum(1 for r in self.results if r.get("is_correct"))


class QuizService:
    def __init__(self):
        self._active_quizzes: Dict[int, ActiveQuizSession] = {} # discord_user_id -> ActiveQuizSession

    def get_active_quiz(self, discord_user_id: int) -> Optional[ActiveQuizSession]:
        return self._active_quizzes.get(discord_user_id)

    async def start_quiz(
        self,
        user: User,
        topic: str,
        question_count: int = 5,
        session_id: Optional[int] = None,
    ) -> ActiveQuizSession:
        """Generates questions via AI and prepares an active quiz session."""
        logger.info(f"Generating quiz for user {user.discord_user_id} on '{topic}' ({question_count} questions)...")
        generated = await ai_client.generate_quiz(topic=topic, question_count=question_count)

        async with db_manager.session() as sess:
            quiz_repo = QuizRepository(sess)
            quiz = await quiz_repo.create_quiz(
                user_id=user.id,
                topic=topic,
                question_count=len(generated.questions),
                session_id=session_id,
            )

            questions_dicts = [q.model_dump() for q in generated.questions]
            db_questions = await quiz_repo.add_questions(quiz.id, questions_dicts)

            active_quiz = ActiveQuizSession(
                quiz_id=quiz.id,
                session_id=session_id,
                user_id=user.id,
                discord_user_id=user.discord_user_id,
                topic=topic,
                questions=db_questions,
            )
            self._active_quizzes[user.discord_user_id] = active_quiz
            return active_quiz

    async def submit_answer(
        self,
        discord_user_id: int,
        user_answer: str,
    ) -> Tuple[bool, float, str, str]:
        """
        Submits answer for current active question.
        Returns: (is_correct, score, feedback, explanation)
        """
        active_quiz = self._active_quizzes.get(discord_user_id)
        if not active_quiz or active_quiz.is_finished:
            raise ValueError("No active quiz in progress.")

        q = active_quiz.current_question
        if not q:
            raise ValueError("Invalid current question state.")

        q_type = q.question_type
        is_correct = False
        score = 0.0
        feedback = ""
        explanation = q.explanation or ""

        if q_type in ["multiple_choice", "true_false"]:
            clean_user = user_answer.strip().lower()
            clean_correct = q.correct_answer.strip().lower()
            if clean_user == clean_correct or (len(clean_user) == 1 and clean_user in "abcd"):
                # Handle option letter matching if user clicked A/B/C/D
                if len(clean_user) == 1 and q.options_json:
                    options = json.loads(q.options_json)
                    letter_idx = ord(clean_user) - ord('a')
                    if 0 <= letter_idx < len(options):
                        is_correct = options[letter_idx].strip().lower() == clean_correct
                    else:
                        is_correct = False
                else:
                    is_correct = True
            else:
                is_correct = (clean_user == clean_correct)

            score = 1.0 if is_correct else 0.0
            feedback = "Correct! Well done." if is_correct else f"The correct answer is {q.correct_answer}."

        else: # short_answer
            eval_res = await ai_client.evaluate_answer(
                question=q.question_text,
                expected_answer=q.correct_answer,
                user_answer=user_answer,
            )
            is_correct = eval_res.correct
            score = eval_res.score
            feedback = eval_res.feedback

        # Save to DB
        async with db_manager.session() as sess:
            quiz_repo = QuizRepository(sess)
            await quiz_repo.record_answer(
                question_id=q.id,
                user_answer=user_answer,
                is_correct=is_correct,
                score=score,
                feedback=feedback,
            )

        active_quiz.results.append({
            "question_id": q.id,
            "question": q.question_text,
            "user_answer": user_answer,
            "correct_answer": q.correct_answer,
            "is_correct": is_correct,
            "score": score,
            "feedback": feedback,
            "explanation": explanation,
        })

        active_quiz.current_question_index += 1
        return is_correct, score, feedback, explanation

    async def finalize_quiz(
        self,
        discord_user_id: int,
        study_duration_minutes: int = 60,
    ) -> Dict[str, Any]:
        """Finalizes quiz session, queries study feedback, updates user stats & XP."""
        active_quiz = self._active_quizzes.pop(discord_user_id, None)
        if not active_quiz:
            raise ValueError("No active quiz to finalize.")

        correct_count = active_quiz.correct_count
        total_questions = max(1, active_quiz.total_questions)
        overall_score = sum(r["score"] for r in active_quiz.results) / total_questions

        # AI study feedback
        ai_feedback = await ai_client.generate_study_feedback(
            topic=active_quiz.topic,
            duration_minutes=study_duration_minutes,
            quiz_results=active_quiz.results,
        )

        quiz_bonus_xp = xp_service.calculate_quiz_bonus_xp(overall_score)

        newly_unlocked_achievements: List[Achievement] = []

        async with db_manager.session() as sess:
            quiz_repo = QuizRepository(sess)
            session_repo = SessionRepository(sess)
            user_repo = UserRepository(sess)
            ach_repo = AchievementRepository(sess)

            # Finalize quiz
            quiz = await quiz_repo.complete_quiz(
                quiz_id=active_quiz.quiz_id,
                correct_count=correct_count,
                score=overall_score,
                summary_feedback=ai_feedback.verdict,
            )

            # Link quiz info to session
            if active_quiz.session_id:
                await session_repo.update_session_topic_and_quiz(
                    session_id=active_quiz.session_id,
                    topic=active_quiz.topic,
                    quiz_score=overall_score,
                    bonus_xp=quiz_bonus_xp,
                )

            # Award quiz bonus XP to user
            user = await user_repo.get_by_id(active_quiz.user_id)
            if user:
                new_level, _, _ = xp_service.calculate_level_from_xp(user.xp + quiz_bonus_xp)
                user = await user_repo.add_xp(user.id, quiz_bonus_xp, new_level)

                # Check quiz achievements
                quiz_stats = await quiz_repo.get_user_quiz_stats(user.id)
                newly_unlocked_achievements = await achievement_service.check_quiz_achievements(
                    ach_repo=ach_repo,
                    user=user,
                    quiz=quiz,
                    total_quizzes=quiz_stats["total_quizzes"],
                )
                # Award achievement XP
                for ach in newly_unlocked_achievements:
                    if ach.xp_reward > 0:
                        nl, _, _ = xp_service.calculate_level_from_xp(user.xp + ach.xp_reward)
                        await user_repo.add_xp(user.id, ach.xp_reward, nl)

        return {
            "quiz_id": active_quiz.quiz_id,
            "topic": active_quiz.topic,
            "total_questions": total_questions,
            "correct_count": correct_count,
            "score_ratio": overall_score,
            "quiz_bonus_xp": quiz_bonus_xp,
            "ai_feedback": ai_feedback,
            "newly_unlocked_achievements": newly_unlocked_achievements,
        }


quiz_service = QuizService()
