#!/usr/bin/env python3
"""
OneMinuta Telegram Bot Launcher
Clean entry point for running the Telegram bot
"""

import os
import sys
from pathlib import Path

# Add project root to Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

# Import the bot from scripts
from scripts.telegram.run_telegram_bot_channels import main

if __name__ == "__main__":
    import asyncio
    asyncio.run(main())