from __future__ import annotations

import pytest
import json
from ai.schemas import (
    QuizQuestionSchema,
    GeneratedQuizSchema,
    AnswerEvaluationSchema,
    StudyFeedbackSchema,
)
from ai.client import extract_json_string, AIClient


def test_quiz_schema_validation():
    valid_data = {
        "topic": "Newton's Laws",
        "questions": [
            {
                "id": 1,
                "type": "multiple_choice",
                "question": "A 5 kg object experiences a net force of 20 N. What is its acceleration?",
                "options": ["2 m/s²", "4 m/s²", "10 m/s²", "25 m/s²"],
                "answer": "4 m/s²",
                "explanation": "Using F = ma, a = 20 / 5 = 4 m/s²."
            },
            {
                "id": 2,
                "type": "true_false",
                "question": "Action and reaction force pairs act on the same object.",
                "options": ["True", "False"],
                "answer": "False",
                "explanation": "Action-reaction pairs always act on different interacting bodies."
            }
        ]
    }
    quiz = GeneratedQuizSchema.model_validate(valid_data)
    assert quiz.topic == "Newton's Laws"
    assert len(quiz.questions) == 2
    assert quiz.questions[0].type == "multiple_choice"
    assert quiz.questions[1].answer == "False"


def test_answer_evaluation_schema():
    eval_data = {
        "correct": True,
        "score": 0.85,
        "feedback": "You correctly explained the net force relationship."
    }
    res = AnswerEvaluationSchema.model_validate(eval_data)
    assert res.correct is True
    assert res.score == 0.85


def test_json_extractor_helpers():
    # Markdown json block
    text_with_block = "Here is the output:\n```json\n{\"test\": 123}\n```\nHope it helps!"
    assert json.loads(extract_json_string(text_with_block)) == {"test": 123}

    # Raw text without fences
    raw_text = "Some intro {\"key\": \"value\"} trailer text"
    assert json.loads(extract_json_string(raw_text)) == {"key": "value"}


@pytest.mark.asyncio
async def test_ai_client_mock_mode():
    client = AIClient(provider="mock")
    quiz = await client.generate_quiz("Thermodynamics", question_count=3)
    assert quiz.topic == "Thermodynamics"
    assert len(quiz.questions) == 3

    eval_res = await client.evaluate_answer(
        question="What is entropy?",
        expected_answer="Entropy measures disorder or unavailable energy in a closed thermodynamic system.",
        user_answer="It is a measure of molecular disorder in a system.",
    )
    assert eval_res.correct is True
    assert eval_res.score > 0.5
