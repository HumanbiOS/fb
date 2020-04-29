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
# Security tokens
INSTANCE_SECURITY_TOKEN = os.getenv("INSTANCE_SECURITY_TOKEN", "")
SERVER_SECURITY_TOKEN = os.getenv("SERVER_SECURITY_TOKEN", "")
INSTANCE_NAME = os.getenv("INSTANCE_NAME")
# Sever url
SERVER_URL = os.getenv("SERVER_ADDRESS", "")
# Webhook
WEBHOOK = os.getenv("WEBHOOK", "")
