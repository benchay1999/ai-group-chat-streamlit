"""
Coordinator Bot
Main Discord bot that handles lobby, room management, and game coordination.
"""

import discord
from discord import app_commands
from discord.ext import commands
import logging
from typing import Optional

from config import (
    DISCORD_MAIN_BOT_TOKEN,
    MIN_HUMANS,
    MAX_HUMANS,
    MIN_TOTAL_PLAYERS,
    MAX_TOTAL_PLAYERS,
)
from utils import room_manager, DiscordRoom
from ui_components import (
    create_waiting_embed,
    create_room_info_embed,
    RoomCreateModal,
    RoomJoinModal,
    WaitingView,
)

logger = logging.getLogger(__name__)


class CoordinatorBot(commands.Bot):
    """
    Main coordinator bot for Human Hunter.
    Handles lobby, room creation, joining, and game coordination.
    """
    
    def __init__(self):
        """Initialize coordinator bot."""
        intents = discord.Intents.default()
        intents.message_content = True
        intents.members = True
        intents.guilds = True
        intents.dm_messages = True
        
        super().__init__(
            command_prefix="!",
            intents=intents,
            activity=discord.Game(name="Human Hunter")
        )
        
        self.game_manager = None  # Will be set by main.py
        
        # Register commands
        self.register_commands()
        
        logger.info("Coordinator Bot initialized")
    
    def register_commands(self):
        """Register all slash commands."""
        
        # Create command
        @self.tree.command(name="create", description="Create a new game room")
        @app_commands.describe(
            room_name="Name for the room (optional)",
            max_humans="Number of human players (1-4)",
            total_players="Total players including AI (2-12)"
        )
        async def create(
            interaction: discord.Interaction,
            max_humans: int = 2,
            total_players: int = 6,
            room_name: str = None
        ):
            await self.create_impl(interaction, max_humans, total_players, room_name)
        
        # Join command
        @self.tree.command(name="join", description="Join a game room")
        @app_commands.describe(room_code="6-character room code")
        async def join(interaction: discord.Interaction, room_code: str):
            await self.join_impl(interaction, room_code)
        
        # Leave command
        @self.tree.command(name="leave", description="Leave your current room")
        async def leave(interaction: discord.Interaction):
            await self.leave_impl(interaction)
        
        # Rooms command
        @self.tree.command(name="rooms", description="List all active rooms")
        async def rooms(interaction: discord.Interaction):
            await self.rooms_impl(interaction)
        
        # Vote command
        @self.tree.command(name="vote", description="Cast your vote during voting phase")
        @app_commands.describe(player="Player to vote for (e.g., Player 1, Human_1)")
        async def vote(interaction: discord.Interaction, player: str):
            await self.vote_impl(interaction, player)
    
    async def setup_hook(self):
        """Called when bot is setting up."""
        # Sync commands globally
        try:
            synced = await self.tree.sync()
            logger.info(f"Commands synced: {len(synced)} command(s)")
            for cmd in synced:
                logger.info(f"  - /{cmd.name}")
        except Exception as e:
            logger.error(f"Failed to sync commands: {e}")
    
    async def on_ready(self):
        """Called when bot is ready."""
        logger.info(f"🎮 Coordinator Bot is online! ({self.user.name})")
        logger.info(f"Connected to {len(self.guilds)} guilds")
        
        # Update status
        await self.change_presence(
            activity=discord.Game(name="Human Hunter | /create or /join"),
            status=discord.Status.online
        )
    
    async def on_message(self, message: discord.Message):
        """Handle messages in game channels."""
        # Ignore bot messages
        if message.author.bot:
            return
        
        # Check if message is in a game room
        room = room_manager.get_player_room(message.author.id)
        if room and room.status == "in_progress":
            # This is a game message - check both game channel and lobby channel
            game_channel_id = room.game_channel_id or room.channel_id
            if message.channel.id == game_channel_id:
                logger.info(f"📨 Human message from {message.author.name} in game {room.room_code}: {message.content[:50]}")
                await self.game_manager.handle_human_message(
                    room.room_code,
                    message.author.id,
                    message.content
                )
        
        # Process commands
        await self.process_commands(message)
    
    async def on_interaction(self, interaction: discord.Interaction):
        """Handle button clicks and modals."""
        try:
            # Skip if this is a command interaction (handled by command tree)
            if interaction.type == discord.InteractionType.application_command:
                return
            
            if interaction.type == discord.InteractionType.component:
                # Button click
                custom_id = interaction.data.get("custom_id")
                
                # Check if already responded
                if interaction.response.is_done():
                    logger.warning(f"Interaction already responded to: {custom_id}")
                    return
                
                if custom_id == "create_room":
                    await interaction.response.send_modal(RoomCreateModal())
                
                elif custom_id == "join_room":
                    await interaction.response.send_modal(RoomJoinModal())
                
                # Removed lobby functionality - use /create and /join directly
            
            elif interaction.type == discord.InteractionType.modal_submit:
                # Modal submission
                custom_id = interaction.data.get("custom_id")
                
                if "room_create" in str(interaction.data):
                    await self.handle_room_creation(interaction)
                
                elif "room_join" in str(interaction.data):
                    await self.handle_room_join(interaction)
        
        except discord.errors.HTTPException as e:
            if e.code == 40060:  # Interaction already acknowledged
                logger.warning(f"Interaction already acknowledged: {e}")
            else:
                logger.error(f"HTTP error in interaction handler: {e}", exc_info=True)
        except Exception as e:
            logger.error(f"Error handling interaction: {e}", exc_info=True)
    
    def set_game_manager(self, game_manager):
        """Set the game manager reference."""
        self.game_manager = game_manager
        logger.info("Game manager set")
    
    # ========================================================================
    # Slash Commands
    # ========================================================================
    
    async def create_impl(
        self,
        interaction: discord.Interaction,
        max_humans: int = 2,
        total_players: int = 6,
        room_name: str = None
    ):
        """Create a new game room via slash command."""
        # Defer only if not already responded
        if not interaction.response.is_done():
            await interaction.response.defer(thinking=True)
        
        # Validate inputs
        if not MIN_HUMANS <= max_humans <= MAX_HUMANS:
            await interaction.followup.send(
                f"❌ Max humans must be between {MIN_HUMANS} and {MAX_HUMANS}",
                ephemeral=True
            )
            return
        
        if not MIN_TOTAL_PLAYERS <= total_players <= MAX_TOTAL_PLAYERS:
            await interaction.followup.send(
                f"❌ Total players must be between {MIN_TOTAL_PLAYERS} and {MAX_TOTAL_PLAYERS}",
                ephemeral=True
            )
            return
        
        if max_humans >= total_players:
            await interaction.followup.send(
                "❌ Max humans must be less than total players (need at least 1 AI)",
                ephemeral=True
            )
            return
        
        # Generate room name if not provided
        if not room_name:
            room_name = f"Room {room_manager.generate_room_code()[:4]}"
        
        # Create room
        room = room_manager.create_room(
            channel_id=interaction.channel_id,
            creator_id=interaction.user.id,
            room_name=room_name,
            max_humans=max_humans,
            total_players=total_players
        )
        
        # Add creator to room
        room_manager.add_player_to_room(
            room.room_code,
            interaction.user.id,
            interaction.user.name,
            interaction.user.display_name
        )
        
        # Send waiting room embed
        embed = create_waiting_embed(room)
        view = WaitingView(room.room_code)
        
        message = await interaction.followup.send(
            f"✅ Room created! Code: **`{room.room_code}`**",
            embed=embed,
            view=view
        )
        
        room.waiting_message_id = message.id
        
        logger.info(f"Room {room.room_code} created by {interaction.user.name}")
        
        # Check if can start immediately (single player)
        if room.can_start:
            await self.start_game(room.room_code, interaction.channel)
    
    async def join_impl(self, interaction: discord.Interaction, room_code: str):
        """Join a game room via slash command."""
        # Defer only if not already responded
        if not interaction.response.is_done():
            await interaction.response.defer(thinking=True, ephemeral=True)
        
        # Validate room code
        room_code = room_code.upper().strip()
        
        room = room_manager.get_room(room_code)
        if not room:
            await interaction.followup.send(
                f"❌ Room `{room_code}` not found",
                ephemeral=True
            )
            return
        
        if room.status != "waiting":
            await interaction.followup.send(
                f"❌ Room `{room_code}` is not accepting players",
                ephemeral=True
            )
            return
        
        if room.is_full:
            await interaction.followup.send(
                f"❌ Room `{room_code}` is full",
                ephemeral=True
            )
            return
        
        # Check if already in a room
        current_room = room_manager.get_player_room(interaction.user.id)
        if current_room:
            await interaction.followup.send(
                f"❌ You are already in room `{current_room.room_code}`",
                ephemeral=True
            )
            return
        
        # Add player to room
        success = room_manager.add_player_to_room(
            room_code,
            interaction.user.id,
            interaction.user.name,
            interaction.user.display_name
        )
        
        if not success:
            await interaction.followup.send(
                "❌ Failed to join room",
                ephemeral=True
            )
            return
        
        await interaction.followup.send(
            f"✅ Joined room `{room_code}`!",
            ephemeral=True
        )
        
        # Update waiting room embed
        channel = self.get_channel(room.channel_id)
        if channel and room.waiting_message_id:
            try:
                message = await channel.fetch_message(room.waiting_message_id)
                embed = create_waiting_embed(room)
                view = WaitingView(room.room_code)
                await message.edit(embed=embed, view=view)
            except:
                pass
        
        logger.info(f"Player {interaction.user.name} joined room {room_code}")
        
        # Check if can start
        if room.can_start:
            await self.start_game(room.room_code, channel)
    
    async def leave_impl(self, interaction: discord.Interaction):
        """Leave current room."""
        # Defer only if not already responded
        if not interaction.response.is_done():
            await interaction.response.defer(thinking=True, ephemeral=True)
        
        room = room_manager.get_player_room(interaction.user.id)
        if not room:
            await interaction.followup.send(
                "❌ You are not in a room",
                ephemeral=True
            )
            return
        
        room_code = room.room_code
        room_manager.remove_player_from_room(room_code, interaction.user.id)
        
        await interaction.followup.send(
            f"✅ Left room `{room_code}`",
            ephemeral=True
        )
        
        # Update waiting room embed if still exists
        if room.status == "waiting":
            channel = self.get_channel(room.channel_id)
            if channel and room.waiting_message_id:
                try:
                    message = await channel.fetch_message(room.waiting_message_id)
                    embed = create_waiting_embed(room)
                    view = WaitingView(room.room_code)
                    await message.edit(embed=embed, view=view)
                except:
                    pass
        
        logger.info(f"Player {interaction.user.name} left room {room_code}")
    
    async def rooms_impl(self, interaction: discord.Interaction):
        """List all rooms in current channel."""
        # Defer only if not already responded
        if not interaction.response.is_done():
            await interaction.response.defer(thinking=True)
        
        rooms = room_manager.get_rooms_for_channel(interaction.channel_id)
        
        if not rooms:
            await interaction.followup.send(
                "📭 No active rooms in this channel",
                ephemeral=True
            )
            return
        
        # Create embed with room list
        embed = discord.Embed(
            title="🎮 Active Rooms",
            description=f"Found {len(rooms)} active room(s)",
            color=0x00ffff
        )
        
        for room in rooms:
            status_emoji = {
                "waiting": "🟢",
                "in_progress": "🔴",
                "completed": "⚫"
            }.get(room.status, "⚪")
            
            embed.add_field(
                name=f"{status_emoji} {room.room_name} (`{room.room_code}`)",
                value=(
                    f"Status: {room.status.capitalize()}\n"
                    f"Players: {room.num_humans}/{room.max_humans}\n"
                    f"AI: {room.num_ai}"
                ),
                inline=False
            )
        
        await interaction.followup.send(embed=embed)
    
    async def vote_impl(self, interaction: discord.Interaction, player: str):
        """
        Cast a vote during voting phase.
        
        Args:
            interaction: Discord interaction
            player: Player ID to vote for
        """
        # Defer ephemeral (only voter sees response)
        if not interaction.response.is_done():
            await interaction.response.defer(ephemeral=True)
        
        # Check if player is in a game
        room = room_manager.get_player_room(interaction.user.id)
        if not room:
            await interaction.followup.send(
                "❌ You're not in a game!",
                ephemeral=True
            )
            return
        
        # Check if game is in progress
        if room.status != "in_progress":
            await interaction.followup.send(
                "❌ Game is not in progress!",
                ephemeral=True
            )
            return
        
        # Check if voting phase
        if self.game_manager:
            success, message = await self.game_manager.handle_channel_vote(
                room.room_code,
                interaction.user.id,
                player
            )
            
            if success:
                await interaction.followup.send(
                    f"✅ {message}",
                    ephemeral=True
                )
            else:
                await interaction.followup.send(
                    f"❌ {message}",
                    ephemeral=True
                )
        else:
            await interaction.followup.send(
                "❌ Game system error!",
                ephemeral=True
            )
    
    # ========================================================================
    # Helper Methods
    # ========================================================================
    
    async def refresh_waiting_room(self, interaction: discord.Interaction, room_code: str):
        """Refresh the waiting room display."""
        room = room_manager.get_room(room_code)
        if not room:
            return
        
        embed = create_waiting_embed(room)
        view = WaitingView(room_code)
        
        try:
            await interaction.response.edit_message(embed=embed, view=view)
        except:
            await interaction.response.send_message(embed=embed, view=view)
    
    async def handle_room_creation(self, interaction: discord.Interaction):
        """Handle room creation modal submission."""
        # Defer the response first (modals need to be responded to quickly)
        await interaction.response.defer(thinking=True)
        
        # Extract values from modal
        components = interaction.data.get("components", [])
        
        room_name = None
        max_humans = 2
        total_players = 6
        
        for action_row in components:
            for component in action_row.get("components", []):
                custom_id = component.get("custom_id", "")
                value = component.get("value", "")
                
                if "room_name" in custom_id and value:
                    room_name = value
                elif "max_humans" in custom_id and value:
                    try:
                        max_humans = int(value)
                    except:
                        pass
                elif "total_players" in custom_id and value:
                    try:
                        total_players = int(value)
                    except:
                        pass
        
        # Validate
        if not MIN_HUMANS <= max_humans <= MAX_HUMANS:
            await interaction.followup.send(
                f"❌ Max humans must be between {MIN_HUMANS} and {MAX_HUMANS}",
                ephemeral=True
            )
            return
        
        if not MIN_TOTAL_PLAYERS <= total_players <= MAX_TOTAL_PLAYERS:
            await interaction.followup.send(
                f"❌ Total players must be between {MIN_TOTAL_PLAYERS} and {MAX_TOTAL_PLAYERS}",
                ephemeral=True
            )
            return
        
        if max_humans >= total_players:
            await interaction.followup.send(
                "❌ Max humans must be less than total players",
                ephemeral=True
            )
            return
        
        # Generate room name if not provided
        if not room_name:
            room_name = f"Room {room_manager.generate_room_code()[:4]}"
        
        # Create room directly (don't delegate to avoid double-defer)
        room = room_manager.create_room(
            channel_id=interaction.channel_id,
            creator_id=interaction.user.id,
            room_name=room_name,
            max_humans=max_humans,
            total_players=total_players
        )
        
        # Add creator to room
        room_manager.add_player_to_room(
            room.room_code,
            interaction.user.id,
            interaction.user.name,
            interaction.user.display_name
        )
        
        # Send waiting room embed
        embed = create_waiting_embed(room)
        view = WaitingView(room.room_code)
        
        message = await interaction.followup.send(
            f"✅ Room created! Code: **`{room.room_code}`**",
            embed=embed,
            view=view
        )
        
        room.waiting_message_id = message.id
        
        logger.info(f"Room {room.room_code} created by {interaction.user.name}")
        
        # Check if can start immediately (single player)
        if room.can_start:
            await self.start_game(room.room_code, interaction.channel)
    
    async def handle_room_join(self, interaction: discord.Interaction):
        """Handle room join modal submission."""
        # Defer the response first (modals need to be responded to quickly)
        await interaction.response.defer(thinking=True, ephemeral=True)
        
        # Extract room code from modal
        components = interaction.data.get("components", [])
        
        room_code = None
        for action_row in components:
            for component in action_row.get("components", []):
                if "room_code" in component.get("custom_id", ""):
                    room_code = component.get("value", "").upper().strip()
        
        if not room_code:
            await interaction.followup.send(
                "❌ Room code is required",
                ephemeral=True
            )
            return
        
        # Join room directly (don't delegate to avoid double-defer)
        room = room_manager.get_room(room_code)
        if not room:
            await interaction.followup.send(
                f"❌ Room `{room_code}` not found",
                ephemeral=True
            )
            return
        
        if room.status != "waiting":
            await interaction.followup.send(
                f"❌ Room `{room_code}` is not accepting players",
                ephemeral=True
            )
            return
        
        if room.is_full:
            await interaction.followup.send(
                f"❌ Room `{room_code}` is full",
                ephemeral=True
            )
            return
        
        # Check if already in a room
        current_room = room_manager.get_player_room(interaction.user.id)
        if current_room:
            await interaction.followup.send(
                f"❌ You are already in room `{current_room.room_code}`",
                ephemeral=True
            )
            return
        
        # Add player to room
        success = room_manager.add_player_to_room(
            room_code,
            interaction.user.id,
            interaction.user.name,
            interaction.user.display_name
        )
        
        if not success:
            await interaction.followup.send(
                "❌ Failed to join room",
                ephemeral=True
            )
            return
        
        await interaction.followup.send(
            f"✅ Joined room `{room_code}`!",
            ephemeral=True
        )
        
        # Update waiting room embed
        channel = self.get_channel(room.channel_id)
        if channel and room.waiting_message_id:
            try:
                message = await channel.fetch_message(room.waiting_message_id)
                embed = create_waiting_embed(room)
                view = WaitingView(room.room_code)
                await message.edit(embed=embed, view=view)
            except:
                pass
        
        logger.info(f"Player {interaction.user.name} joined room {room_code}")
        
        # Check if can start
        if room.can_start:
            await self.start_game(room.room_code, channel)
    
    async def start_game(self, room_code: str, channel: discord.TextChannel):
        """
        Start a game when room is ready.
        Creates a dedicated channel for the game.
        
        Args:
            room_code: Room code to start
            channel: Discord lobby channel where room was created
        """
        logger.info(f"Starting game for room {room_code}")
        
        # Get room
        room = room_manager.get_room(room_code)
        if not room:
            logger.error(f"Room {room_code} not found")
            return
        
        try:
            # Create dedicated game channel
            guild = channel.guild
            category = channel.category  # Use same category as lobby channel
            
            # Create channel with room-specific name
            game_channel = await guild.create_text_channel(
                name=f"game-{room_code.lower()}",
                category=category,
                topic=f"Human Hunter Game - Room {room_code} - {room.room_name}",
                reason=f"Game channel for room {room_code}"
            )
            
            # Store game channel ID in room
            room.game_channel_id = game_channel.id
            logger.info(f"Created game channel: {game_channel.name} (ID: {game_channel.id})")
            
            # Notify in lobby channel
            player_mentions = " ".join([f"<@{pid}>" for pid in room.players.keys()])
            await channel.send(
                f"🎮 **Game Starting!**\n"
                f"Room **{room_code}** is now live!\n"
                f"Head over to {game_channel.mention} to play!\n"
                f"{player_mentions}"
            )
            
            # Send welcome message in game channel
            await game_channel.send(
                f"🎉 **Welcome to Human Hunter!**\n"
                f"Room Code: **{room_code}**\n"
                f"Players: {player_mentions}\n\n"
                f"The game is starting now..."
            )
            
            # Initialize game through game manager
            if self.game_manager:
                success = await self.game_manager.initialize_game(room_code)
                if success:
                    logger.info(f"Game {room_code} started successfully")
                else:
                    logger.error(f"Failed to start game {room_code}")
                    await game_channel.send(f"❌ Failed to start game for room {room_code}")
                    # Clean up the channel if game failed to start
                    await game_channel.delete(reason="Game failed to start")
                    room.game_channel_id = None
            else:
                logger.error("Game manager not set!")
                await game_channel.send("❌ Game system error - please try again")
                # Clean up the channel
                await game_channel.delete(reason="Game system error")
                room.game_channel_id = None
                
        except discord.Forbidden:
            logger.error(f"Bot lacks permission to create channels in {guild.name}")
            await channel.send("❌ I don't have permission to create channels. Please check my permissions!")
        except Exception as e:
            logger.error(f"Error creating game channel: {e}", exc_info=True)
            await channel.send(f"❌ Error creating game channel: {e}")

