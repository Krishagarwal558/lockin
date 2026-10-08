from __future__ import annotations

import asyncio
import sys
from config import settings
from bot.client import create_bot
from utils.logging import setup_logger

logger = setup_logger("lockin.main", settings.LOG_LEVEL)


def main():
    """Main entrypoint for LOCKIN bot application."""
    logger.info("Starting LOCKIN — Discord Study Accountability & Learning Bot...")

    if not settings.DISCORD_TOKEN:
        logger.error(
            "DISCORD_TOKEN is not set in environment or .env file!\n"
            "Please copy .env.example to .env and configure your bot credentials."
        )
        sys.exit(1)

    bot = create_bot()

    try:
        bot.run(settings.DISCORD_TOKEN)
    except KeyboardInterrupt:
        logger.info("Received keyboard interrupt. Exiting cleanly.")
    except Exception as e:
        logger.critical(f"Fatal error during bot execution: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
