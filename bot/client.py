from __future__ import annotations

import discord
from discord.ext import commands

from config import settings
from utils.logging import setup_logger
from bot.events import register_events

logger = setup_logger("lockin.client", settings.LOG_LEVEL)

COMMAND_EXTENSIONS = [
    "bot.commands.study",
    "bot.commands.profile",
    "bot.commands.stats",
    "bot.commands.leaderboard",
    "bot.commands.settings",
    "bot.commands.help",
]


class LockinBot(commands.Bot):
    def __init__(self):
        intents = discord.Intents.default()
        intents.members = True # For server leaderboard member resolution
        intents.guilds = True

        super().__init__(
            command_prefix="!",
            intents=intents,
            help_command=None,
        )

        register_events(self)

    async def setup_hook(self) -> None:
        """Loads command cogs during bot initialization."""
        logger.info("Loading command extensions...")
        for extension in COMMAND_EXTENSIONS:
            try:
                await self.load_extension(extension)
                logger.info(f"Loaded extension: {extension}")
            except Exception as e:
                logger.error(f"Failed to load extension {extension}: {e}", exc_info=True)

    async def close(self) -> None:
        """Gracefully closes bot and database connections."""
        logger.info("Shutting down LOCKIN bot...")
        from database.database import db_manager
        await db_manager.close()
        await super().close()


def create_bot() -> LockinBot:
    return LockinBot()
