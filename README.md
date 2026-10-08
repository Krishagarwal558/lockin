# 🔒 LOCKIN — Discord Study Accountability & Learning Bot

[![Python Version](https://img.shields.io/badge/python-3.11%2B-blue.svg)](https://www.python.org/downloads/)
[![discord.py](https://img.shields.io/badge/discord.py-2.x-5865F2.svg)](https://github.com/Rapptz/discord.py)
[![SQLAlchemy](https://img.shields.io/badge/SQLAlchemy-2.0-red.svg)](https://www.sqlalchemy.org/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

**LOCKIN** is a production-quality, interactive Discord study companion designed for students and study groups who want to stay disciplined, focused, and motivated.

Instead of feeling like a dry, generic timer, LOCKIN behaves like an energetic personal coach: tracking deep work sessions, nudging you with witty motivational updates, challenging you with AI-generated post-study quizzes, and rewarding consistency with XP, levels, streak badges, and milestone achievements.

---

## 🌟 Core Features

- ⏱️ **Focus Timers & Deep Work Tracking**: Start custom or quick Pomodoro sessions (`/study` for 25m, 45m, 60m, 90m, or custom duration).
- 🧠 **AI Post-Study Quizzes**: Automatically creates 5-question comprehension quizzes (Multiple Choice, True/False, Short Answer) on whatever topic you just studied.
- ✍️ **Intelligent Short-Answer Grading**: Evaluates conceptual understanding, tolerance for phrasing differences, and assigns partial credit with helpful feedback.
- 📊 **Comprehensive Study Reports**: Summarizes focus time, quiz mastery, concepts mastered, concepts needing polish, and actionable recommendations.
- ⭐ **Scalable XP & Leveling Engine**: Earn base XP from study minutes, plus performance multipliers from quiz scores and active daily streaks.
- 🔥 **Forgiving Daily Streaks**: Encourages consistency without harsh psychological penalties. Stopping early awards proportional XP without resetting streaks.
- 🏆 **Achievements & Badges**: Unlock trophies like *Academic Weapon* (50 hours), *Sharpshooter* (100% quiz score), and *Final Boss* (30-day streak).
- 🥇 **Server Leaderboards**: Compare study time and XP with friends or across the server.
- 🔄 **Restart Recovery**: Automatically recovers active timers and calculates completed study time if the bot reboots.

---

## 🏗️ Architecture & Project Structure

```text
lockin/
├── app.py                      # Application entrypoint & runtime runner
├── config.py                   # Pydantic Settings & environment config
├── requirements.txt            # Project dependencies
├── .env.example                # Sample environment variables
├── README.md                   # Comprehensive documentation
│
├── bot/
│   ├── client.py               # Custom LockinBot subclass & cog loader
│   ├── events.py               # Startup, command sync, error handlers & event dispatchers
│   ├── commands/               # Slash command cogs
│   │   ├── study.py            # /study and /stop
│   │   ├── profile.py          # /profile
│   │   ├── stats.py            # /stats
│   │   ├── leaderboard.py      # /leaderboard
│   │   ├── settings.py         # /settings
│   │   └── help.py             # /help
│   ├── views/                  # Discord UI views (Buttons, Select menus, Modals)
│   │   ├── study_view.py       # Duration selection & stop confirmation views
│   │   ├── quiz_view.py        # Question interactive views & short answer modal
│   │   └── profile_view.py     # Profile tabs & navigation
│   └── embeds/                 # Clean, consistent Discord embeds
│       ├── study_embeds.py     # Lock-in started, interval nudges, early stop
│       ├── quiz_embeds.py      # Questions, grading feedback & study reports
│       └── profile_embeds.py   # Profile cards, stats breakdown & leaderboards
│
├── services/                   # Business logic layer
│   ├── study_service.py        # Study session orchestration & lifecycle
│   ├── timer_service.py        # Asyncio background timers & crash recovery
│   ├── quiz_service.py         # Quiz generation, grading & feedback orchestration
│   ├── motivation_service.py   # Randomized contextual encouragement & memes
│   ├── xp_service.py           # Scalable XP calculation & level curves
│   ├── streak_service.py       # Daily streak evaluation & forgiveness rules
│   └── achievement_service.py  # Achievement checks & unlocking logic
│
├── ai/                         # Isolated AI integration
│   ├── client.py               # Resilient LLM client (OpenAI/Groq/Gemini/Mock)
│   ├── prompts.py              # Structured prompt templates
│   └── schemas.py              # Pydantic validation schemas
│
├── database/                   # Data layer (SQLAlchemy 2.0 Async)
│   ├── database.py             # Engine, session factory & schema initialization
│   ├── models.py               # User, StudySession, Quiz, Question, Achievement
│   └── repositories/           # Repository pattern data access
│       ├── user_repository.py
│       ├── session_repository.py
│       ├── quiz_repository.py
│       └── achievement_repository.py
│
├── utils/                      # Helper utilities
│   ├── time.py                 # Duration parser, formatters, Discord timestamps
│   ├── formatting.py           # Progress bar generator, rank medals, badges
│   └── logging.py              # Sanitized logging setup
│
└── tests/                      # Automated test suite
    ├── test_xp.py
    ├── test_streaks.py
    ├── test_timer_service.py
    ├── test_ai_schemas.py
    └── test_database_and_services.py
```

---

## 🚀 Setup & Installation

### 1. Prerequisites

- **Python 3.11+** installed
- **Git**

### 2. Clone & Prepare Virtual Environment

```bash
cd lockin
python -m venv .venv

# On Windows:
.venv\Scripts\activate

# On Linux/macOS:
source .venv/bin/activate

pip install -r requirements.txt
```

### 3. Create a Discord Bot & Application

1. Go to the [Discord Developer Portal](https://discord.com/developers/applications).
2. Click **New Application** and name it `LOCKIN`.
3. Go to the **Bot** tab on the left sidebar:
   - Click **Add Bot** / **Reset Token** to copy your **Bot Token**.
   - Under **Privileged Gateway Intents**, enable **Server Members Intent** and **Message Content Intent**.
4. Go to **OAuth2 > URL Generator**:
   - In **Scopes**, check `bot` and `applications.commands`.
   - In **Bot Permissions**, check:
     - `Send Messages`
     - `Embed Links`
     - `Attach Files`
     - `Read Message History`
     - `Use Slash Commands`
5. Copy the generated URL and open it in your browser to invite LOCKIN to your Discord server.

### 4. Configure Environment Variables

Copy the example file:

```bash
cp .env.example .env
```

Edit `.env` with your credentials:

```env
# Discord Bot Token
DISCORD_TOKEN=your_bot_token_here

# AI Configuration (Supports OpenAI, Groq, OpenRouter, Gemini, or Mock)
AI_API_KEY=your_llm_api_key_here
AI_MODEL=gpt-4o-mini
AI_BASE_URL=https://api.openai.com/v1
AI_PROVIDER=openai

# Database Configuration (SQLite default, PostgreSQL supported)
DATABASE_URL=sqlite+aiosqlite:///lockin.db

# Logging & Preferences
LOG_LEVEL=INFO
DEFAULT_MOTIVATION_INTERVAL_MINUTES=20
DEFAULT_QUIZ_QUESTIONS=5
AUTO_START_QUIZ_DEFAULT=true
```

> **Note on AI Providers:** You can use standard OpenAI API keys, or point `AI_BASE_URL` to Groq (`https://api.groq.com/openai/v1`), OpenRouter (`https://openrouter.ai/api/v1`), or local Ollama. If no API key is provided, the bot runs in **Mock Mode**, providing dynamic template questions so you can test all features offline!

---

## 🏃 Running the Bot

Start the bot:

```bash
python app.py
```

Upon launch, LOCKIN will initialize the SQLite database schema, seed default achievements, sync slash commands with Discord, and check for any interrupted sessions to recover.

---

## 🧪 Running Automated Tests

Run the test suite with `pytest`:

```bash
pytest -v
```

Tests cover:
- XP formulas and level calculations
- Daily streak maintenance, increment, and friendly reset rules
- Study duration string parsing and clock formatters
- Pydantic schema validation for AI quizzes and short answers
- End-to-end database session, quiz, and achievement workflows

---

## 📖 Command Reference

| Command | Description | Example |
|---|---|---|
| `/study [subject] [minutes]` | Starts a study session with focus timer & motivation. | `/study subject:Physics minutes:60` |
| `/stop` | Prompts confirmation to stop session early. Awards actual XP. | `/stop` |
| `/profile [user]` | Displays level, progress bar, streak, and recent topics. | `/profile` |
| `/stats [user]` | Detailed analytics: total hours, subject distribution, quiz average. | `/stats` |
| `/leaderboard [metric] [scope]` | Ranks top studiers by study time or XP. | `/leaderboard metric:time scope:server` |
| `/settings` | Customize motivation nudges, intervals, and auto-quizzes. | `/settings motivation:True interval:25` |
| `/help` | Explains rules, leveling system, and features. | `/help` |

---

## 🎮 Core Flow Walkthrough

```text
User:
  /study subject:Physics

Bot:
  ⏱️ How long are you locking in?
  [ 🍅 25m ] [ ⏳ 45m ] [ 🔥 60m ] [ 🗿 90m ] [ ⚙️ Custom ]

User clicks 60m:
  🔒 LOCK-IN STARTED
  Subject: Physics
  Duration: 60 minutes
  No excuses. I'll see you in 60 minutes. 🗿

(During session):
  🧠 20 minutes down. Keep cooking.
  🔥 Halfway there. Do not fumble the lock-in.

(60 minutes pass):
  ⏰ SESSION COMPLETE
  You survived 60 minutes.
  Now prove you actually learned something. 🧠
  [ 📝 Start Post-Study Quiz ]

User enters topic: "Newton's Laws"

Bot presents 5 AI questions (Multiple choice, True/False, Short answer).
User answers interactively via Discord buttons and modals.

Bot presents Final Study Report:
  ╔════════════════════════════╗
         📚 STUDY REPORT
  ╚════════════════════════════╝
  • Topic: Newton's Laws
  • Study Time: 01:00:00
  • Quiz Score: 4 / 5 (80%)
  • Total XP: +110 XP
  • 🔥 Streak: 8 days
  • Bot Verdict: "Solid session. You mastered F=ma calculations."
  • 📌 Recommended: "Review Newton's Third Law action-reaction pairs."
```

---

## 🛡️ Privacy & Reliability

- **Non-blocking Architecture**: All database operations use async SQLAlchemy (`aiosqlite`), and AI calls use async `aiohttp`.
- **Sensitive Data Masking**: Bot tokens and API keys are automatically redacted from logs.
- **Fail-Safe Crash Recovery**: If the bot restarts during a session, active sessions are restored seamlessly upon reconnect.
- **Privacy-first**: User study answers are evaluated securely and never logged or exposed in public channels without user action.

---

## 🗺️ Future Roadmap

- [ ] Voice channel study room auto-tracking (Pomodoro lounge).
- [ ] Group study sessions & multiplayer quiz battles.
- [ ] Flashcard deck generation and export (Anki compatible).
- [ ] PostgreSQL Docker compose deployment guide.
