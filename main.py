#!/usr/bin/env python3
"""
OSINT Telegram Bot

A comprehensive OSINT tool for Telegram that allows users to gather information
from various public sources in a legal and ethical manner.
"""
import asyncio
import sys
import logging

# Костыль для совместимости aiogram 2.x и Python 3.13
if sys.version_info >= (3, 13):
    if not hasattr(asyncio, "get_event_loop"):
        def _get_event_loop():
            try:
                return asyncio.get_running_loop()
            except RuntimeError:
                return asyncio.new_event_loop()
        asyncio.get_event_loop = _get_event_loop

from loguru import logger

# Debug print to verify token is loaded
from config.settings import settings
print(f"DEBUG: Token loaded: {settings.BOT_TOKEN[:5]}...")

from src.core.bot import start_bot

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)

# Disable noisy logs
logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("aiogram").setLevel(logging.WARNING)

if __name__ == "__main__":
    try:
        logger.info("🚀 Starting OSINT Bot...")
        asyncio.run(start_bot())
    except (KeyboardInterrupt, SystemExit):
        logger.info("👋 OSINT Bot has been stopped")
    except Exception as e:
        logger.critical(f"Fatal error: {e}", exc_info=True)
