from __future__ import annotations

import json
from typing import List, Optional, Sequence, Dict, Any
from sqlalchemy import select, update, desc, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from database.models import Quiz, Question, utc_now


class QuizRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def create_quiz(
        self,
        user_id: int,
        topic: str,
        question_count: int,
        session_id: Optional[int] = None,
    ) -> Quiz:
        """Creates a new Quiz entry."""
        quiz = Quiz(
            user_id=user_id,
            session_id=session_id,
            topic=topic,
            question_count=question_count,
            correct_count=0,
            score=0.0,
            created_at=utc_now(),
        )
        self.session.add(quiz)
        await self.session.flush()
        return quiz

    async def add_questions(
        self,
        quiz_id: int,
        questions: List[Dict[str, Any]],
    ) -> List[Question]:
        """Inserts generated questions for a quiz."""
        db_questions = []
        for q in questions:
            options_str = json.dumps(q.get("options")) if q.get("options") else None
            db_q = Question(
                quiz_id=quiz_id,
                question_text=q["question"],
                question_type=q.get("type", "multiple_choice"),
                options_json=options_str,
                correct_answer=q["answer"],
                explanation=q.get("explanation"),
                is_correct=None,
                score=0.0,
            )
            self.session.add(db_q)
            db_questions.append(db_q)
        await self.session.flush()
        return db_questions

    async def record_answer(
        self,
        question_id: int,
        user_answer: str,
        is_correct: bool,
        score: float,
        feedback: Optional[str] = None,
    ) -> Optional[Question]:
        """Saves user's response and grading for a single question."""
        stmt = (
            update(Question)
            .where(Question.id == question_id)
            .values(
                user_answer=user_answer,
                is_correct=is_correct,
                score=score,
                feedback=feedback,
            )
            .returning(Question)
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def complete_quiz(
        self,
        quiz_id: int,
        correct_count: int,
        score: float,
        summary_feedback: Optional[str] = None,
    ) -> Optional[Quiz]:
        """Finalizes quiz grading and feedback."""
        stmt = (
            update(Quiz)
            .where(Quiz.id == quiz_id)
            .values(
                correct_count=correct_count,
                score=score,
                summary_feedback=summary_feedback,
            )
            .returning(Quiz)
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_quiz_with_questions(self, quiz_id: int) -> Optional[Quiz]:
        """Retrieves a quiz along with all its question objects."""
        stmt = (
            select(Quiz)
            .options(selectinload(Quiz.questions))
            .where(Quiz.id == quiz_id)
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_user_quiz_stats(self, user_id: int) -> Dict[str, Any]:
        """Gets quiz statistics for a user."""
        count_stmt = select(func.count(Quiz.id)).where(Quiz.user_id == user_id)
        total_quizzes = (await self.session.execute(count_stmt)).scalar() or 0

        avg_stmt = select(func.avg(Quiz.score)).where(Quiz.user_id == user_id)
        avg_score = (await self.session.execute(avg_stmt)).scalar() or 0.0

        return {
            "total_quizzes": total_quizzes,
            "average_score": float(avg_score),
        }
