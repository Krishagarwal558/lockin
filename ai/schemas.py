from __future__ import annotations

from typing import List, Optional, Literal
from pydantic import BaseModel, Field


class QuizQuestionSchema(BaseModel):
    id: int = Field(description="Sequential question index starting from 1")
    type: Literal["multiple_choice", "true_false", "short_answer"] = Field(
        default="multiple_choice",
        description="Type of question: multiple_choice, true_false, or short_answer"
    )
    question: str = Field(description="Clear and concise question text testing conceptual understanding")
    options: Optional[List[str]] = Field(
        default=None,
        description="List of 4 distinct choices for multiple choice, or ['True', 'False'] for true/false. None for short answer."
    )
    answer: str = Field(description="Exact correct answer string or expected key concept")
    explanation: str = Field(description="Brief educational explanation of why this answer is correct")


class GeneratedQuizSchema(BaseModel):
    topic: str = Field(description="Topic name the quiz was generated for")
    questions: List[QuizQuestionSchema] = Field(
        description="List of structured questions testing understanding"
    )


class AnswerEvaluationSchema(BaseModel):
    correct: bool = Field(description="Whether the user's answer is conceptually correct")
    score: float = Field(
        ge=0.0,
        le=1.0,
        description="Normalized score from 0.0 (wrong) to 1.0 (perfect)"
    )
    feedback: str = Field(description="Brief, constructive, and slightly playful feedback on the user's answer")


class StudyFeedbackSchema(BaseModel):
    verdict: str = Field(description="High-level personality review of the session")
    strengths: List[str] = Field(default_factory=list, description="Subtopics/concepts the student grasped well")
    weaknesses: List[str] = Field(default_factory=list, description="Subtopics/concepts the student struggled with")
    recommendation: str = Field(description="Actionable next step or topic recommendation for their next study session")
