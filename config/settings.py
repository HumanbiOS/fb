"""
settings for messenger bot
"""

import os
import dotenv
import environ
from pathlib import Path

# (corona/config/settings.py - 2 = corona/)
ROOT_DIR = (environ.Path(__file__) - 2)

# load bot token from .env
env_path = Path(ROOT_DIR) / '.env'
dotenv.load_dotenv(env_path)
# Facebook Page Access Token
PAT = os.getenv("PAT", "")
VERIFY_TOKEN = os.getenv("VERIFY_TOKEN", "")
# Telegram bot
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
# Telegram channels
DOCTORS_ROOM_TG = os.getenv("DOCTORS_ROOM_TG", "")
PSYCHOLOGIST_ROOM_TG = os.getenv("PSYCHOLOGIST_ROOM_TG", "")
HELPER_ROOM_TG = os.getenv("HELPER_ROOM_TG", "")

# Webhook
WEBHOOK = os.getenv("WEBHOOK", "")
