from __future__ import annotations

import json
import re
import asyncio
from typing import Optional, List, Dict, Any, Type, TypeVar
from pydantic import BaseModel, ValidationError
import aiohttp

from config import settings
from utils.logging import setup_logger
from ai.schemas import (
    GeneratedQuizSchema,
    QuizQuestionSchema,
    AnswerEvaluationSchema,
    StudyFeedbackSchema,
)
from ai.prompts import (
    QUIZ_GENERATION_SYSTEM_PROMPT,
    get_quiz_generation_user_prompt,
    ANSWER_EVALUATION_SYSTEM_PROMPT,
    get_answer_evaluation_user_prompt,
    STUDY_FEEDBACK_SYSTEM_PROMPT,
    get_study_feedback_user_prompt,
)

logger = setup_logger("lockin.ai", settings.LOG_LEVEL)

T = TypeVar("T", bound=BaseModel)


def extract_json_string(text: str) -> str:
    """Extracts raw JSON substring from potentially markdown-wrapped or messy LLM response."""
    text = text.strip()
    
    # Try finding markdown ```json ... ``` or ``` ... ```
    match = re.search(r"```(?:json)?\s*([\s\S]*?)\s*```", text, re.DOTALL)
    if match:
        text = match.group(1).strip()
    
    # Fallback to finding first '{' and last '}'
    start_idx = text.find("{")
    end_idx = text.rfind("}")
    if start_idx != -1 and end_idx != -1 and end_idx > start_idx:
        return text[start_idx : end_idx + 1]
    
    return text


class AIClient:
    def __init__(
        self,
        api_key: Optional[str] = None,
        model: Optional[str] = None,
        base_url: Optional[str] = None,
        provider: Optional[str] = None,
    ):
        self.api_key = api_key or settings.AI_API_KEY
        self.model = model or settings.AI_MODEL
        self.base_url = (base_url or settings.AI_BASE_URL).rstrip("/")
        self.provider = provider or settings.AI_PROVIDER

    @property
    def current_model(self) -> str:
        return self.model or settings.AI_MODEL

    @property
    def current_base_url(self) -> str:
        return (self.base_url or settings.AI_BASE_URL).rstrip("/")

    @property
    def current_api_key(self) -> str:
        return self.api_key or settings.AI_API_KEY

    async def _call_llm(
        self,
        system_prompt: str,
        user_prompt: str,
        temperature: float = 0.5,
        max_tokens: int = 1500,
    ) -> str:
        """Sends chat completion request to configured LLM endpoint."""
        api_key = self.current_api_key
        base_url = self.current_base_url
        model = self.current_model

        if not api_key or self.provider == "mock":
            raise ValueError("No valid AI_API_KEY configured or mock mode active.")

        url = f"{base_url}/chat/completions"
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        }
        payload = {
            "model": model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            "temperature": temperature,
            "max_tokens": max_tokens,
            "response_format": {"type": "json_object"},
        }

        logger.info(f"Sending LLM request to {url} using model '{model}'...")
        async with aiohttp.ClientSession() as session:
            async with session.post(url, headers=headers, json=payload, timeout=aiohttp.ClientTimeout(total=45)) as resp:
                if resp.status != 200:
                    error_text = await resp.text()
                    logger.error(f"LLM API request failed [{resp.status}]: {error_text}")
                    raise RuntimeError(f"AI service returned HTTP status {resp.status}: {error_text}")
                data = await resp.json()
                content = data["choices"][0]["message"]["content"]
                logger.info(f"Received successful LLM response ({len(content)} chars)")
                return content

    async def _generate_structured(
        self,
        system_prompt: str,
        user_prompt: str,
        schema: Type[T],
        fallback_factory: Optional[callable] = None,
        max_retries: int = 2,
    ) -> T:
        """Attempts LLM completion and validates against target Pydantic schema with retry."""
        api_key = self.current_api_key
        if not api_key or self.provider == "mock":
            if fallback_factory:
                logger.info("Using local mock generator (no API key configured).")
                return fallback_factory()
            raise RuntimeError("AI API key is missing and no fallback provided.")

        current_user_prompt = user_prompt
        last_error = None

        for attempt in range(max_retries + 1):
            try:
                raw_response = await self._call_llm(system_prompt, current_user_prompt)
                json_str = extract_json_string(raw_response)
                parsed_data = json.loads(json_str)
                validated = schema.model_validate(parsed_data)
                logger.info(f"Structured validation succeeded for {schema.__name__}")
                return validated
            except (json.JSONDecodeError, ValidationError) as e:
                logger.warning(f"Schema validation error on attempt {attempt + 1}: {e}")
                last_error = e
                if attempt < max_retries:
                    await asyncio.sleep(1.0)
                    current_user_prompt = (
                        f"{user_prompt}\n\n"
                        f"IMPORTANT: Your previous response caused this JSON validation error: {str(e)}.\n"
                        f"Please correct the JSON output and adhere strictly to the schema."
                    )
            except Exception as e:
                logger.error(f"LLM request error on attempt {attempt + 1}: {e}")
                last_error = e
                if attempt < max_retries:
                    await asyncio.sleep(1.5)

        logger.error(f"Failed to generate structured AI response after {max_retries + 1} attempts: {last_error}")
        if fallback_factory:
            logger.warning("Falling back to local fallback generator.")
            return fallback_factory()
        raise RuntimeError(f"Failed to obtain valid AI output: {last_error}")

    async def generate_quiz(
        self,
        topic: str,
        question_count: int = 5,
        difficulty: str = "medium",
    ) -> GeneratedQuizSchema:
        """Generates a structured post-study quiz."""
        system_prompt = QUIZ_GENERATION_SYSTEM_PROMPT
        user_prompt = get_quiz_generation_user_prompt(topic, question_count, difficulty)

        def mock_fallback() -> GeneratedQuizSchema:
            return self._build_mock_quiz(topic, question_count)

        return await self._generate_structured(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            schema=GeneratedQuizSchema,
            fallback_factory=mock_fallback,
        )

    async def evaluate_answer(
        self,
        question: str,
        expected_answer: str,
        user_answer: str,
    ) -> AnswerEvaluationSchema:
        """Evaluates student's short answer response against expected concept."""
        system_prompt = ANSWER_EVALUATION_SYSTEM_PROMPT
        user_prompt = get_answer_evaluation_user_prompt(question, expected_answer, user_answer)

        def mock_fallback() -> AnswerEvaluationSchema:
            user_clean = user_answer.strip().lower()
            expected_clean = expected_answer.strip().lower()
            if not user_clean:
                return AnswerEvaluationSchema(correct=False, score=0.0, feedback="No answer provided.")
            
            # Token overlap against user's substantive answer tokens
            stopwords = {"a", "an", "the", "in", "on", "at", "to", "for", "of", "and", "or", "is", "are", "it", "this", "that"}
            expected_tokens = {w for w in re.findall(r'\w+', expected_clean) if w not in stopwords}
            user_tokens = {w for w in re.findall(r'\w+', user_clean) if w not in stopwords}
            
            common = expected_tokens & user_tokens
            overlap = len(common) / max(len(user_tokens), 1) if user_tokens else 0.0
            
            is_correct = len(common) >= 1 or overlap >= 0.25 or user_clean in expected_clean or expected_clean in user_clean
            score = 0.90 if overlap >= 0.5 or len(common) >= 2 else (0.75 if is_correct else 0.2)
            feedback = "Great grasp of the core concept!" if is_correct else f"The key concept involves: {expected_answer}"
            return AnswerEvaluationSchema(correct=is_correct, score=score, feedback=feedback)

        return await self._generate_structured(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            schema=AnswerEvaluationSchema,
            fallback_factory=mock_fallback,
        )

    async def generate_study_feedback(
        self,
        topic: str,
        duration_minutes: int,
        quiz_results: List[Dict[str, Any]],
    ) -> StudyFeedbackSchema:
        """Generates a personalized study verdict and recommendations."""
        system_prompt = STUDY_FEEDBACK_SYSTEM_PROMPT
        user_prompt = get_study_feedback_user_prompt(topic, duration_minutes, quiz_results)

        def mock_fallback() -> StudyFeedbackSchema:
            correct_count = sum(1 for q in quiz_results if q.get("is_correct"))
            total = len(quiz_results) if quiz_results else 1
            ratio = correct_count / total

            if ratio >= 0.8:
                verdict = "🗿 ACADEMIC WEAPON DETECTED. You completely locked in and crushed this topic."
            elif ratio >= 0.5:
                verdict = "Solid session! The fundamentals are clicking, just need a quick polish."
            else:
                verdict = "Respect for putting the time in. A few concepts need a second pass, but we're building momentum."

            strengths = [f"Fundamentals of {topic}"] if ratio >= 0.5 else ["Dedication & Focus Time"]
            weaknesses = [f"Advanced applications of {topic}"] if ratio < 0.9 else []
            recommendation = f"Review {topic} key formulas and edge cases tomorrow for 15 minutes."

            return StudyFeedbackSchema(
                verdict=verdict,
                strengths=strengths,
                weaknesses=weaknesses,
                recommendation=recommendation,
            )

        return await self._generate_structured(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            schema=StudyFeedbackSchema,
            fallback_factory=mock_fallback,
        )

    def _build_mock_quiz(self, topic: str, count: int) -> GeneratedQuizSchema:
        """Constructs a rich mock quiz for fallback/offline mode."""
        questions: List[QuizQuestionSchema] = []
        
        # 1. Multiple choice 1
        questions.append(QuizQuestionSchema(
            id=1,
            type="multiple_choice",
            question=f"What is the foundational core principle behind {topic}?",
            options=[
                f"The fundamental governing law of {topic}",
                "Random thermal fluctuations without cause",
                "Unrelated mathematical coincidence",
                "None of the above"
            ],
            answer=f"The fundamental governing law of {topic}",
            explanation=f"{topic} relies on this foundational rule to predict system behavior."
        ))

        # 2. True / False
        if count >= 2:
            questions.append(QuizQuestionSchema(
                id=2,
                type="true_false",
                question=f"True or False: In {topic}, key properties remain invariant under ideal conditions.",
                options=["True", "False"],
                answer="True",
                explanation=f"Conservation and symmetry principles typically hold true in standard {topic} frameworks."
            ))

        # 3. Multiple Choice 2
        if count >= 3:
            questions.append(QuizQuestionSchema(
                id=3,
                type="multiple_choice",
                question=f"When applying {topic} to real-world scenarios, which factor is most crucial to account for?",
                options=[
                    "System boundary and initial conditions",
                    "Arbitrary aesthetic preferences",
                    "Ignoring all external constraints",
                    "Using only qualitative intuition"
                ],
                answer="System boundary and initial conditions",
                explanation="Properly defining the boundaries and constraints ensures valid analysis."
            ))

        # 4. Short Answer
        if count >= 4:
            questions.append(QuizQuestionSchema(
                id=4,
                type="short_answer",
                question=f"In 1-2 sentences, explain the primary relationship governed by {topic}.",
                options=None,
                answer=f"{topic} describes how inputs/forces produce proportional outputs or state transitions.",
                explanation=f"Demonstrates the core input-output / cause-effect relationship in {topic}."
            ))

        # 5. Multiple Choice 3
        if count >= 5:
            questions.append(QuizQuestionSchema(
                id=5,
                type="multiple_choice",
                question=f"Which outcome is expected when the primary variable in {topic} is doubled?",
                options=[
                    "A proportional change according to the system relation",
                    "Zero effect under all circumstances",
                    "Immediate collapse of the system",
                    "An unpredictable random number"
                ],
                answer="A proportional change according to the system relation",
                explanation="Direct mathematical dependency dictates a proportional change."
            ))

        # Trim to count
        return GeneratedQuizSchema(topic=topic, questions=questions[:count])


ai_client = AIClient()
