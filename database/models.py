from __future__ import annotations

from datetime import datetime, timezone
from typing import List, Optional
from sqlalchemy import (
    BigInteger,
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class Base(DeclarativeBase):
    pass


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    discord_user_id: Mapped[int] = mapped_column(BigInteger, unique=True, index=True, nullable=False)
    username: Mapped[str] = mapped_column(String(100), nullable=False)
    xp: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    level: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    current_streak: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    longest_streak: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    total_study_seconds: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    last_study_date: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    # Preferences
    motivation_enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    motivation_interval_minutes: Mapped[int] = mapped_column(Integer, default=20, nullable=False)
    auto_quiz_enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, onupdate=utc_now, nullable=False)

    # Relationships
    study_sessions: Mapped[List[StudySession]] = relationship("StudySession", back_populates="user", cascade="all, delete-orphan")
    quizzes: Mapped[List[Quiz]] = relationship("Quiz", back_populates="user", cascade="all, delete-orphan")
    achievements: Mapped[List[UserAchievement]] = relationship("UserAchievement", back_populates="user", cascade="all, delete-orphan")


class StudySession(Base):
    __tablename__ = "study_sessions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    discord_user_id: Mapped[int] = mapped_column(BigInteger, index=True, nullable=False)
    channel_id: Mapped[Optional[int]] = mapped_column(BigInteger, nullable=True)
    guild_id: Mapped[Optional[int]] = mapped_column(BigInteger, nullable=True)
    
    subject: Mapped[str] = mapped_column(String(100), nullable=False)
    topic: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)
    planned_seconds: Mapped[int] = mapped_column(Integer, nullable=False)
    actual_seconds: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)
    ended_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    
    # Status: 'active', 'completed', 'stopped'
    status: Mapped[str] = mapped_column(String(20), default="active", nullable=False, index=True)
    quiz_score: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    xp_earned: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    motivation_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    # Relationships
    user: Mapped[User] = relationship("User", back_populates="study_sessions")
    quiz: Mapped[Optional[Quiz]] = relationship("Quiz", back_populates="session", uselist=False)


class Quiz(Base):
    __tablename__ = "quizzes"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    session_id: Mapped[Optional[int]] = mapped_column(Integer, ForeignKey("study_sessions.id", ondelete="SET NULL"), nullable=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    
    topic: Mapped[str] = mapped_column(String(200), nullable=False)
    question_count: Mapped[int] = mapped_column(Integer, nullable=False)
    correct_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    score: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    summary_feedback: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)

    # Relationships
    user: Mapped[User] = relationship("User", back_populates="quizzes")
    session: Mapped[Optional[StudySession]] = relationship("StudySession", back_populates="quiz")
    questions: Mapped[List[Question]] = relationship("Question", back_populates="quiz", cascade="all, delete-orphan")


class Question(Base):
    __tablename__ = "questions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    quiz_id: Mapped[int] = mapped_column(Integer, ForeignKey("quizzes.id", ondelete="CASCADE"), nullable=False, index=True)
    
    question_text: Mapped[str] = mapped_column(Text, nullable=False)
    question_type: Mapped[str] = mapped_column(String(30), nullable=False) # multiple_choice, true_false, short_answer
    options_json: Mapped[Optional[str]] = mapped_column(Text, nullable=True) # JSON list of options
    correct_answer: Mapped[str] = mapped_column(Text, nullable=False)
    user_answer: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    is_correct: Mapped[Optional[bool]] = mapped_column(Boolean, nullable=True)
    score: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    feedback: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    explanation: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Relationships
    quiz: Mapped[Quiz] = relationship("Quiz", back_populates="questions")


class Achievement(Base):
    __tablename__ = "achievements"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    slug: Mapped[str] = mapped_column(String(50), unique=True, index=True, nullable=False)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    description: Mapped[str] = mapped_column(String(255), nullable=False)
    xp_reward: Mapped[int] = mapped_column(Integer, default=50, nullable=False)
    icon: Mapped[str] = mapped_column(String(10), default="🏆", nullable=False)

    user_achievements: Mapped[List[UserAchievement]] = relationship("UserAchievement", back_populates="achievement")


class UserAchievement(Base):
    __tablename__ = "user_achievements"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    achievement_id: Mapped[int] = mapped_column(Integer, ForeignKey("achievements.id", ondelete="CASCADE"), nullable=False, index=True)
    unlocked_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)

    user: Mapped[User] = relationship("User", back_populates="achievements")
    achievement: Mapped[Achievement] = relationship("Achievement", back_populates="user_achievements")
