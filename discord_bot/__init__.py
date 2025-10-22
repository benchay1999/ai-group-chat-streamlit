"""
Discord Bot Package for Human Hunter Game

A Discord bot implementation that allows players to play the Human Hunter
social deduction game directly in Discord channels.
"""

__version__ = "1.0.0"
__author__ = "Human Hunter Team"

from .coordinator_bot import CoordinatorBot
from .ai_agent_bot import AIAgentBot
from .game_manager import DiscordGameManager
from .utils import room_manager, DiscordRoom, DiscordPlayer

__all__ = [
    "CoordinatorBot",
    "AIAgentBot",
    "DiscordGameManager",
    "room_manager",
    "DiscordRoom",
    "DiscordPlayer",
]

