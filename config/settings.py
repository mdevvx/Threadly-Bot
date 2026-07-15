"""
Bot settings and constants
"""

import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Discord Configuration
DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
BOT_PREFIX = os.getenv("BOT_PREFIX", "$")

# Supabase Configuration
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

# Logging Configuration
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")

# Bot Constants
DEFAULT_EMBED_COLOR = 0xF77378  # Threadly brand color
MAX_EMBED_TITLE_LENGTH = 256
MAX_EMBED_DESCRIPTION_LENGTH = 4096
MAX_EMBED_FIELDS = 25

# Welcome Mode Types
WELCOME_MODE_THREAD = "thread"
WELCOME_MODE_CHANNEL = "channel"

# Validation
if not DISCORD_TOKEN:
    raise ValueError("DISCORD_TOKEN is not set in .env file")
