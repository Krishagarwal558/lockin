from __future__ import annotations

import asyncio
import sys
import threading
from config import settings
from bot.client import create_bot
from utils.logging import setup_logger

logger = setup_logger("lockin.main", settings.LOG_LEVEL)


def start_discord_bot():
    """Runs the Discord bot event loop."""
    if not settings.DISCORD_TOKEN:
        logger.error("DISCORD_TOKEN is not set in environment or .env file!")
        return

    bot = create_bot()
    bot.run(settings.DISCORD_TOKEN)


def main():
    logger.info("Starting LOCKIN — Discord Study Accountability & Learning Bot...")

    # Check if gradio is available (e.g. Hugging Face Spaces environment)
    try:
        import gradio as gr

        # Start Discord bot in a background daemon thread
        bot_thread = threading.Thread(target=start_discord_bot, daemon=True)
        bot_thread.start()

        # Build clean status UI for Hugging Face Space
        with gr.Blocks(title="LOCKIN Discord Bot") as demo:
            gr.Markdown("# 🔒 LOCKIN — Discord Study Accountability Bot")
            gr.Markdown("### Status: 🟢 **ONLINE & HEALTHY**")
            gr.Markdown("The bot is running in the background and listening for Discord commands (`/study`, `/profile`, `/stats`, `/leaderboard`).")
            gr.Markdown("🔗 [Invite Bot to Discord](https://discord.com/oauth2/authorize?client_id=1557831922858594434&permissions=277025778752&scope=bot%20applications.commands)")

        # Launch Gradio server on port 7860 for Hugging Face
        demo.launch(server_name="0.0.0.0", server_port=7860)

    except ImportError:
        # Standard CLI mode without Gradio
        start_discord_bot()


if __name__ == "__main__":
    main()
