"""
AI Agent Bot
Individual Discord bot representing an AI player with unique personality.
"""

import discord
from discord.ext import commands
from typing import Optional, Dict
import asyncio
import logging

from config import AI_PERSONALITIES

logger = logging.getLogger(__name__)


class AIAgentBot(commands.Bot):
    """
    Individual bot for each AI player.
    Each bot has a unique personality and participates in games.
    """
    
    def __init__(self, agent_id: str, personality: str):
        """
        Initialize AI agent bot.
        
        Args:
            agent_id: Unique identifier for this AI agent (e.g., "AI_1")
            personality: Personality trait for this agent
        """
        intents = discord.Intents.default()
        intents.message_content = True
        intents.members = True
        intents.guilds = True
        
        super().__init__(
            command_prefix="!",
            intents=intents,
            activity=discord.Game(name="Human Hunter (AI)")
        )
        
        self.agent_id = agent_id
        self.personality = personality
        self.active_games: Dict[str, dict] = {}  # room_code -> game_info
        self.game_manager = None  # Will be set by main.py
        
        logger.info(f"AI Agent {agent_id} initialized with personality: {personality}")
    
    async def on_ready(self):
        """Called when bot is ready."""
        logger.info(f"🤖 AI Agent {self.agent_id} is online! ({self.user.name})")
        
        # Update status
        await self.change_presence(
            activity=discord.Game(name=f"Human Hunter | {self.personality}"),
            status=discord.Status.online
        )
    
    async def join_game(
        self,
        room_code: str,
        channel: discord.TextChannel,
        game_player_id: str
    ):
        """
        Join a game in a Discord channel.
        
        Args:
            room_code: Game room code
            channel: Discord text channel for the game
            game_player_id: Player ID in game state (e.g., "Player 1")
        """
        if room_code in self.active_games:
            logger.warning(f"AI {self.agent_id} already in game {room_code}")
            return
        
        self.active_games[room_code] = {
            "channel_id": channel.id,
            "game_player_id": game_player_id,
            "is_eliminated": False
        }
        
        logger.info(f"AI {self.agent_id} joined game {room_code} as {game_player_id}")
        
        # Send join message
        await channel.send(f"🤖 {game_player_id} has joined the game!")
    
    async def leave_game(self, room_code: str):
        """
        Leave a game.
        
        Args:
            room_code: Game room code
        """
        if room_code not in self.active_games:
            logger.warning(f"AI {self.agent_id} not in game {room_code}")
            return
        
        game_info = self.active_games[room_code]
        channel_id = game_info["channel_id"]
        
        # Remove from active games
        del self.active_games[room_code]
        
        logger.info(f"AI {self.agent_id} left game {room_code}")
        
        # Optionally send leave message
        try:
            channel = self.get_channel(channel_id)
            if channel:
                player_id = game_info["game_player_id"]
                if game_info["is_eliminated"]:
                    await channel.send(f"💀 {player_id} has been eliminated!")
        except Exception as e:
            logger.error(f"Error sending leave message: {e}")
    
    async def post_message(self, room_code: str, message: str):
        """
        Post a message in the game channel.
        
        Args:
            room_code: Game room code
            message: Message to post
        """
        if room_code not in self.active_games:
            logger.warning(f"AI {self.agent_id} not in game {room_code}, cannot post")
            return
        
        game_info = self.active_games[room_code]
        
        # Check if eliminated
        if game_info["is_eliminated"]:
            logger.info(f"AI {self.agent_id} is eliminated, not posting")
            return
        
        channel_id = game_info["channel_id"]
        channel = self.get_channel(channel_id)
        
        if not channel:
            logger.error(f"Channel {channel_id} not found")
            return
        
        try:
            # Get player name from game state
            player_name = game_info["game_player_id"]
            
            # Format message with player name
            formatted_message = f"**{player_name}**: {message}"
            
            await channel.send(formatted_message)
            logger.info(f"AI {self.agent_id} posted message in {room_code}")
        except Exception as e:
            logger.error(f"Error posting message: {e}")
    
    async def mark_eliminated(self, room_code: str):
        """
        Mark this AI as eliminated in a game.
        
        Args:
            room_code: Game room code
        """
        if room_code in self.active_games:
            self.active_games[room_code]["is_eliminated"] = True
            logger.info(f"AI {self.agent_id} marked as eliminated in {room_code}")
    
    async def update_status(self, room_code: str, phase: str):
        """
        Update bot status based on game phase.
        
        Args:
            room_code: Game room code
            phase: Current game phase
        """
        if room_code not in self.active_games:
            return
        
        game_info = self.active_games[room_code]
        
        if game_info["is_eliminated"]:
            status_text = f"Eliminated | {self.personality}"
        else:
            status_text = f"{phase} | {self.personality}"
        
        try:
            await self.change_presence(
                activity=discord.Game(name=status_text),
                status=discord.Status.online if not game_info["is_eliminated"] else discord.Status.idle
            )
        except Exception as e:
            logger.error(f"Error updating status: {e}")
    
    def is_in_game(self, room_code: str) -> bool:
        """Check if bot is in a specific game."""
        return room_code in self.active_games
    
    def is_eliminated_in_game(self, room_code: str) -> bool:
        """Check if bot is eliminated in a specific game."""
        if room_code not in self.active_games:
            return False
        return self.active_games[room_code]["is_eliminated"]
    
    def get_game_player_id(self, room_code: str) -> Optional[str]:
        """Get the game player ID for a room."""
        if room_code in self.active_games:
            return self.active_games[room_code]["game_player_id"]
        return None


async def create_ai_bot(agent_id: str, personality: str, token: str) -> AIAgentBot:
    """
    Factory function to create and start an AI bot.
    
    Args:
        agent_id: Unique agent ID
        personality: Personality trait
        token: Discord bot token
    
    Returns:
        Initialized AIAgentBot instance
    """
    bot = AIAgentBot(agent_id, personality)
    
    # Start bot in background
    asyncio.create_task(bot.start(token))
    
    # Wait for bot to be ready
    await bot.wait_until_ready()
    
    return bot

