"""
Discord Bot Configuration
Manages bot tokens, settings, and imports from existing backend config.
"""

import os
import sys
from pathlib import Path
from dotenv import load_dotenv

# Add parent directory to path to import backend modules
parent_dir = Path(__file__).parent.parent
sys.path.insert(0, str(parent_dir))

# Import existing backend configuration
from backend.config import (
    AI_MODEL_NAME,
    AI_MODEL_PROVIDER,
    AI_TEMPERATURE,
    AI_PERSONALITIES,
    GAME_TOPICS,
    DISCUSSION_TIME,
    VOTING_TIME,
    ROUNDS_TO_WIN,
    MESSAGE_COOLDOWN,
    NUM_AI_PLAYERS
)

load_dotenv()

# Discord Bot Tokens
DISCORD_MAIN_BOT_TOKEN = os.getenv("DISCORD_MAIN_BOT_TOKEN")
DISCORD_AI_BOT_TOKENS = [
    os.getenv(f"DISCORD_AI_BOT_TOKEN_{i}")
    for i in range(1, 9)  # Support up to 8 AI bots
    if os.getenv(f"DISCORD_AI_BOT_TOKEN_{i}")
]

# Validate configuration
if not DISCORD_MAIN_BOT_TOKEN:
    raise ValueError("DISCORD_MAIN_BOT_TOKEN is required in .env file")

if len(DISCORD_AI_BOT_TOKENS) < 4:
    raise ValueError(f"At least 4 AI bot tokens required, found {len(DISCORD_AI_BOT_TOKENS)}")

# Discord-specific settings
COMMAND_PREFIX = "!"
BOT_ACTIVITY_STATUS = "Human Hunter"
BOT_STATUS_TYPE = "playing"  # playing, watching, listening

# Discord Intents (required permissions)
REQUIRED_INTENTS = [
    "guilds",
    "members",
    "messages",
    "message_content",
    "dm_messages",
    "guild_messages"
]

# UI Configuration
EMBED_COLOR_LOBBY = 0x00ffff  # Cyan
EMBED_COLOR_WAITING = 0xffa500  # Orange
EMBED_COLOR_GAME = 0x00ff00  # Green
EMBED_COLOR_VOTING = 0xff00ff  # Magenta
EMBED_COLOR_ELIMINATION = 0xff0000  # Red
EMBED_COLOR_VICTORY = 0xffd700  # Gold

# Game Settings
MIN_HUMANS = 1
MAX_HUMANS = 4
MIN_TOTAL_PLAYERS = 2
MAX_TOTAL_PLAYERS = 12

# Timing
WAITING_ROOM_POLL_INTERVAL = 2  # seconds
GAME_STATUS_UPDATE_INTERVAL = 5  # seconds
VOTE_REMINDER_INTERVAL = 15  # seconds

# Room Management
ROOM_CODE_LENGTH = 6
MAX_ROOMS_PER_CHANNEL = 10
INACTIVE_ROOM_TIMEOUT = 3600  # 1 hour

# Export commonly used items
__all__ = [
    "DISCORD_MAIN_BOT_TOKEN",
    "DISCORD_AI_BOT_TOKENS",
    "AI_MODEL_NAME",
    "AI_PERSONALITIES",
    "GAME_TOPICS",
    "DISCUSSION_TIME",
    "VOTING_TIME",
    "ROUNDS_TO_WIN",
    "EMBED_COLOR_LOBBY",
    "EMBED_COLOR_WAITING",
    "EMBED_COLOR_GAME",
    "EMBED_COLOR_VOTING",
    "EMBED_COLOR_ELIMINATION",
    "EMBED_COLOR_VICTORY",
]

