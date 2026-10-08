from __future__ import annotations

import os
from pathlib import Path
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict
from dotenv import load_dotenv

# Load .env file explicitly if it exists
env_path = Path(__file__).parent / ".env"
load_dotenv(dotenv_path=env_path)


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )

    # Discord
    DISCORD_TOKEN: str = Field(default="", description="Discord bot application token")

    # AI Configuration
    AI_API_KEY: str = Field(default="", description="API key for LLM services")
    AI_MODEL: str = Field(default="gpt-4o-mini", description="LLM model identifier")
    AI_BASE_URL: str = Field(default="https://api.openai.com/v1", description="Base URL for OpenAI-compatible endpoint")
    AI_PROVIDER: str = Field(default="openai", description="AI provider (openai, groq, gemini, mock)")

    # Database
    DATABASE_URL: str = Field(
        default="sqlite+aiosqlite:///lockin.db",
        description="Async SQLAlchemy database connection string"
    )

    # Bot Preferences
    LOG_LEVEL: str = Field(default="INFO", description="Logging level")
    DEFAULT_MOTIVATION_INTERVAL_MINUTES: int = Field(default=20, description="Minutes between motivational messages")
    DEFAULT_QUIZ_QUESTIONS: int = Field(default=5, description="Number of questions in post-study quiz")
    AUTO_START_QUIZ_DEFAULT: bool = Field(default=True, description="Whether to prompt post-study quiz by default")


settings = Settings()
