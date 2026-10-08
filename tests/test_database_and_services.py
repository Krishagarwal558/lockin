import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from database.models import Base
from database.database import DatabaseManager, DEFAULT_ACHIEVEMENTS
from database.repositories.user_repository import UserRepository
from database.repositories.session_repository import SessionRepository
from database.repositories.quiz_repository import QuizRepository
from database.repositories.achievement_repository import AchievementRepository
from services.achievement_service import achievement_service
from services.xp_service import xp_service


@pytest_asyncio.fixture
async def test_db():
    db = DatabaseManager("sqlite+aiosqlite:///:memory:")
    await db.init_db()
    yield db
    await db.close()


@pytest.mark.asyncio
async def test_user_and_session_flow(test_db: DatabaseManager):
    async with test_db.session() as sess:
        user_repo = UserRepository(sess)
        session_repo = SessionRepository(sess)
        ach_repo = AchievementRepository(sess)

        # 1. Create user
        user = await user_repo.get_or_create_user(1001, "TestStudent")
        assert user.discord_user_id == 1001
        assert user.xp == 0
        assert user.level == 1

        # 2. Create study session
        study_sess = await session_repo.create_session(
            user_id=user.id,
            discord_user_id=1001,
            subject="Organic Chemistry",
            planned_seconds=3600,
        )
        assert study_sess.status == "active"

        # 3. Complete study session
        actual_seconds = 3600
        xp_earned = xp_service.calculate_study_xp(actual_seconds)
        completed_sess = await session_repo.complete_session(
            session_id=study_sess.id,
            actual_seconds=actual_seconds,
            xp_earned=xp_earned,
        )
        assert completed_sess.status == "completed"

        # 4. Award XP & study time to user
        await user_repo.add_study_time(user.id, actual_seconds)
        new_level, _, _ = xp_service.calculate_level_from_xp(user.xp + xp_earned)
        updated_user = await user_repo.add_xp(user.id, xp_earned, new_level)
        assert updated_user.xp == 60
        assert updated_user.total_study_seconds == 3600

        # 5. Check first lock-in achievement
        unlocked = await achievement_service.check_session_achievements(
            ach_repo=ach_repo,
            user=updated_user,
            session=completed_sess,
            total_completed_sessions=1,
        )
        assert len(unlocked) == 1
        assert unlocked[0].slug == "first_lockin"


@pytest.mark.asyncio
async def test_quiz_persistence(test_db: DatabaseManager):
    async with test_db.session() as sess:
        user_repo = UserRepository(sess)
        quiz_repo = QuizRepository(sess)
        ach_repo = AchievementRepository(sess)

        user = await user_repo.get_or_create_user(2002, "QuizTester")

        # Create Quiz
        quiz = await quiz_repo.create_quiz(
            user_id=user.id,
            topic="Calculus",
            question_count=2,
        )
        assert quiz.id is not None

        # Add questions
        questions = await quiz_repo.add_questions(
            quiz_id=quiz.id,
            questions=[
                {
                    "question": "What is the derivative of sin(x)?",
                    "type": "multiple_choice",
                    "options": ["cos(x)", "-cos(x)", "tan(x)", "sec(x)"],
                    "answer": "cos(x)",
                    "explanation": "d/dx(sin(x)) = cos(x)",
                },
                {
                    "question": "True or False: The integral of e^x is e^x + C.",
                    "type": "true_false",
                    "options": ["True", "False"],
                    "answer": "True",
                    "explanation": "Exponential function base e is its own derivative and integral.",
                }
            ]
        )
        assert len(questions) == 2

        # Record answers
        await quiz_repo.record_answer(
            question_id=questions[0].id,
            user_answer="cos(x)",
            is_correct=True,
            score=1.0,
            feedback="Correct!",
        )
        await quiz_repo.record_answer(
            question_id=questions[1].id,
            user_answer="True",
            is_correct=True,
            score=1.0,
            feedback="Correct!",
        )

        completed_quiz = await quiz_repo.complete_quiz(
            quiz_id=quiz.id,
            correct_count=2,
            score=1.0,
            summary_feedback="Perfect execution on Calculus.",
        )
        assert completed_quiz.score == 1.0

        # Check Sharpshooter & Knowledge check achievements
        unlocked = await achievement_service.check_quiz_achievements(
            ach_repo=ach_repo,
            user=user,
            quiz=completed_quiz,
            total_quizzes=1,
        )
        unlocked_slugs = {a.slug for a in unlocked}
        assert "knowledge_check" in unlocked_slugs
        assert "sharpshooter" in unlocked_slugs
