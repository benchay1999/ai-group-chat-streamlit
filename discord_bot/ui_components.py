"""
Discord UI Components
Embeds, buttons, and views for the game interface.
"""

import discord
from discord import ui
from typing import List, Optional, Callable, Awaitable
from datetime import datetime
from config import (
    EMBED_COLOR_LOBBY,
    EMBED_COLOR_WAITING,
    EMBED_COLOR_GAME,
    EMBED_COLOR_VOTING,
    EMBED_COLOR_ELIMINATION,
    EMBED_COLOR_VICTORY,
)
from utils import DiscordRoom, DiscordPlayer
from backend.langgraph_state import GameState, Phase


def create_lobby_embed(rooms: List[DiscordRoom]) -> discord.Embed:
    """
    Create lobby embed showing available rooms.
    
    Args:
        rooms: List of waiting rooms to display
    
    Returns:
        Discord embed for lobby
    """
    embed = discord.Embed(
        title="🎮 Human Hunter - Lobby",
        description="Welcome to Human Hunter! Create or join a room to start playing.",
        color=EMBED_COLOR_LOBBY,
        timestamp=datetime.utcnow()
    )
    
    if rooms:
        rooms_text = []
        for room in rooms[:10]:  # Show max 10 rooms
            status_emoji = "🟢" if not room.is_full else "🟡"
            rooms_text.append(
                f"{status_emoji} **{room.room_name}** (`{room.room_code}`)\n"
                f"   Players: {room.num_humans}/{room.max_humans} humans | "
                f"{room.num_ai} AI | {room.total_players} total"
            )
        embed.add_field(
            name=f"🌐 Available Rooms ({len(rooms)})",
            value="\n\n".join(rooms_text),
            inline=False
        )
    else:
        embed.add_field(
            name="📭 No Active Rooms",
            value="Be the first to create a room!",
            inline=False
        )
    
    embed.set_footer(text="Click 'Create Room' or 'Join Room' below")
    return embed


def create_room_info_embed(room: DiscordRoom) -> discord.Embed:
    """
    Create embed with detailed room information.
    
    Args:
        room: Room to display
    
    Returns:
        Discord embed for room info
    """
    embed = discord.Embed(
        title=f"📋 Room: {room.room_name}",
        description=f"Room Code: **`{room.room_code}`**",
        color=EMBED_COLOR_WAITING,
        timestamp=datetime.utcnow()
    )
    
    embed.add_field(
        name="👥 Capacity",
        value=f"{room.num_humans}/{room.max_humans} humans\n{room.num_ai} AI players",
        inline=True
    )
    
    embed.add_field(
        name="🎯 Total Players",
        value=str(room.total_players),
        inline=True
    )
    
    embed.add_field(
        name="📊 Status",
        value=room.status.capitalize(),
        inline=True
    )
    
    return embed


def create_waiting_embed(room: DiscordRoom) -> discord.Embed:
    """
    Create waiting room embed with player list.
    
    Args:
        room: Room in waiting state
    
    Returns:
        Discord embed for waiting room
    """
    embed = discord.Embed(
        title=f"⏳ Waiting Room: {room.room_name}",
        description=f"Room Code: **`{room.room_code}`**\nWaiting for players to join...",
        color=EMBED_COLOR_WAITING,
        timestamp=datetime.utcnow()
    )
    
    # Progress bar
    progress = room.num_humans
    total = room.max_humans
    filled = "█" * progress
    empty = "░" * (total - progress)
    embed.add_field(
        name="📊 Players Ready",
        value=f"{filled}{empty} ({progress}/{total})",
        inline=False
    )
    
    # Player list
    if room.players:
        player_list = []
        for i, player in enumerate(room.players.values(), 1):
            ready_emoji = "✅" if player.is_ready else "⏳"
            player_list.append(f"{ready_emoji} {i}. {player.display_name}")
        
        embed.add_field(
            name="👥 Joined Players",
            value="\n".join(player_list),
            inline=False
        )
    
    # Game settings
    embed.add_field(
        name="⚙️ Game Settings",
        value=(
            f"**Humans:** {room.max_humans}\n"
            f"**AI Players:** {room.num_ai}\n"
            f"**Total:** {room.total_players}"
        ),
        inline=False
    )
    
    if room.is_full:
        embed.add_field(
            name="🎮 Ready to Start!",
            value="Game will start automatically...",
            inline=False
        )
    
    embed.set_footer(text="Game starts automatically when full")
    return embed


def create_game_status_embed(room: DiscordRoom, state: GameState) -> discord.Embed:
    """
    Create game status embed showing current phase and topic.
    
    Args:
        room: Current game room
        state: Current game state
    
    Returns:
        Discord embed for game status
    """
    phase = state["phase"]
    round_num = state["round"]
    topic = state["topic"]
    
    # Choose color based on phase
    if phase == Phase.DISCUSSION:
        color = EMBED_COLOR_GAME
        phase_emoji = "💬"
        phase_name = "Discussion Phase"
    elif phase == Phase.VOTING:
        color = EMBED_COLOR_VOTING
        phase_emoji = "🗳️"
        phase_name = "Voting Phase"
    elif phase == Phase.ELIMINATION:
        color = EMBED_COLOR_ELIMINATION
        phase_emoji = "⚔️"
        phase_name = "Elimination"
    else:
        color = EMBED_COLOR_GAME
        phase_emoji = "🎮"
        phase_name = "Game"
    
    embed = discord.Embed(
        title=f"{phase_emoji} {room.room_name} - Round {round_num}",
        description=f"**Phase:** {phase_name}",
        color=color,
        timestamp=datetime.utcnow()
    )
    
    if phase == Phase.DISCUSSION:
        embed.add_field(
            name="💭 Discussion Topic",
            value=f"*{topic}*",
            inline=False
        )
    
    # Active players
    active_players = [p for p in state["players"] if not p["eliminated"]]
    player_names = [p["id"] for p in active_players]
    
    embed.add_field(
        name=f"👥 Active Players ({len(active_players)})",
        value=", ".join(player_names[:10]),  # Show max 10
        inline=False
    )
    
    # Eliminated players
    eliminated_players = [p for p in state["players"] if p["eliminated"]]
    if eliminated_players:
        eliminated_names = [p["id"] for p in eliminated_players]
        embed.add_field(
            name=f"💀 Eliminated ({len(eliminated_players)})",
            value=", ".join(eliminated_names),
            inline=False
        )
    
    return embed


def create_vote_embed(room: DiscordRoom, state: GameState, voter_id: str) -> discord.Embed:
    """
    Create voting embed for DM to player.
    
    Args:
        room: Current game room
        state: Current game state
        voter_id: ID of the player voting
    
    Returns:
        Discord embed for vote DM
    """
    embed = discord.Embed(
        title="🗳️ Voting Time!",
        description=(
            f"**Room:** {room.room_name} (Round {state['round']})\n\n"
            "Select a player to eliminate using the dropdown menu below.\n"
            "Choose wisely - who do you think is hiding their true nature?"
        ),
        color=EMBED_COLOR_VOTING,
        timestamp=datetime.utcnow()
    )
    
    # Active players (excluding the voter)
    active_players = [
        p for p in state["players"] 
        if not p["eliminated"] and p["id"] != voter_id
    ]
    
    if active_players:
        player_list = [f"• {p['id']}" for p in active_players]
        embed.add_field(
            name="🎯 Available Targets",
            value="\n".join(player_list),
            inline=False
        )
    
    embed.set_footer(text="Vote is private and will be revealed after voting ends")
    return embed


def create_results_embed(
    room: DiscordRoom,
    state: GameState,
    eliminated_player: str,
    vote_counts: dict,
    was_human: bool
) -> discord.Embed:
    """
    Create elimination results embed.
    
    Args:
        room: Current game room
        state: Current game state
        eliminated_player: Player who was eliminated
        vote_counts: Dictionary of vote counts
        was_human: Whether eliminated player was human
    
    Returns:
        Discord embed for results
    """
    embed = discord.Embed(
        title="⚔️ Elimination Results",
        description=f"**{eliminated_player}** has been eliminated!",
        color=EMBED_COLOR_ELIMINATION,
        timestamp=datetime.utcnow()
    )
    
    # Reveal role
    role_emoji = "👤" if was_human else "🤖"
    role_name = "Human" if was_human else "AI"
    embed.add_field(
        name="🎭 Identity Revealed",
        value=f"{role_emoji} **{eliminated_player}** was a **{role_name}**!",
        inline=False
    )
    
    # Vote breakdown
    if vote_counts:
        vote_text = []
        for player, count in sorted(vote_counts.items(), key=lambda x: x[1], reverse=True):
            bar = "█" * count + "░" * (5 - min(count, 5))
            vote_text.append(f"{player}: {bar} ({count} vote{'s' if count != 1 else ''})")
        
        embed.add_field(
            name="📊 Vote Breakdown",
            value="\n".join(vote_text[:10]),
            inline=False
        )
    
    # Remaining players
    active_players = [p for p in state["players"] if not p["eliminated"]]
    embed.add_field(
        name=f"👥 Remaining Players ({len(active_players)})",
        value=", ".join([p["id"] for p in active_players]),
        inline=False
    )
    
    return embed


def create_game_over_embed(state: GameState, winner: str) -> discord.Embed:
    """
    Create game over embed.
    
    Args:
        state: Final game state
        winner: 'human' or 'ai'
    
    Returns:
        Discord embed for game over
    """
    if winner == "human":
        title = "👤 Humans Win!"
        description = "The human players survived and outsmarted the AI!"
        color = EMBED_COLOR_VICTORY
    else:
        title = "🤖 AI Wins!"
        description = "The AI successfully identified and eliminated the humans!"
        color = EMBED_COLOR_VICTORY
    
    embed = discord.Embed(
        title=title,
        description=description,
        color=color,
        timestamp=datetime.utcnow()
    )
    
    embed.add_field(
        name="📊 Game Statistics",
        value=(
            f"**Rounds Played:** {state['round']}\n"
            f"**Total Players:** {len(state['players'])}\n"
            f"**Messages:** {len(state['chat_history'])}"
        ),
        inline=False
    )
    
    # Final standings
    humans = [p["id"] for p in state["players"] if p["role"] == "human"]
    ais = [p["id"] for p in state["players"] if p["role"] == "ai"]
    
    embed.add_field(
        name="👤 Humans",
        value="\n".join(humans) if humans else "None",
        inline=True
    )
    
    embed.add_field(
        name="🤖 AI Players",
        value="\n".join(ais[:10]) if ais else "None",
        inline=True
    )
    
    embed.set_footer(text="Thanks for playing Human Hunter!")
    return embed


# ============================================================================
# Interactive Views (Buttons and Select Menus)
# ============================================================================

class LobbyView(ui.View):
    """Lobby view with Create and Join buttons."""
    
    def __init__(self):
        super().__init__(timeout=None)  # Persistent view
    
    @ui.button(label="Create Room", style=discord.ButtonStyle.green, emoji="➕", custom_id="create_room")
    async def create_room_button(self, interaction: discord.Interaction, button: ui.Button):
        """Handle create room button click."""
        await interaction.response.send_modal(RoomCreateModal())
    
    @ui.button(label="Join Room", style=discord.ButtonStyle.blurple, emoji="🚪", custom_id="join_room")
    async def join_room_button(self, interaction: discord.Interaction, button: ui.Button):
        """Handle join room button click."""
        await interaction.response.send_modal(RoomJoinModal())
    
    @ui.button(label="Refresh", style=discord.ButtonStyle.gray, emoji="🔄", custom_id="refresh_lobby")
    async def refresh_button(self, interaction: discord.Interaction, button: ui.Button):
        """Handle refresh button click."""
        # This will be handled by the coordinator bot
        await interaction.response.defer()


class RoomCreateModal(ui.Modal, title="Create Game Room"):
    """Modal for creating a new game room."""
    
    room_name = ui.TextInput(
        label="Room Name",
        placeholder="Enter room name (optional)",
        required=False,
        max_length=50
    )
    
    max_humans = ui.TextInput(
        label="Number of Human Players",
        placeholder="1-4",
        default="2",
        min_length=1,
        max_length=1
    )
    
    total_players = ui.TextInput(
        label="Total Players (including AI)",
        placeholder="2-12",
        default="6",
        min_length=1,
        max_length=2
    )
    
    async def on_submit(self, interaction: discord.Interaction):
        """Handle modal submission."""
        # Validation will be done by coordinator bot
        await interaction.response.defer()


class RoomJoinModal(ui.Modal, title="Join Game Room"):
    """Modal for joining an existing room."""
    
    room_code = ui.TextInput(
        label="Room Code",
        placeholder="Enter 6-character room code",
        min_length=6,
        max_length=6
    )
    
    async def on_submit(self, interaction: discord.Interaction):
        """Handle modal submission."""
        await interaction.response.defer()


class WaitingView(ui.View):
    """Waiting room view with Leave button."""
    
    def __init__(self, room_code: str):
        super().__init__(timeout=None)
        self.room_code = room_code
    
    @ui.button(label="Leave Room", style=discord.ButtonStyle.red, emoji="🚪")
    async def leave_button(self, interaction: discord.Interaction, button: ui.Button):
        """Handle leave room button click."""
        await interaction.response.defer()


class VoteView(ui.View):
    """Voting view with player select menu."""
    
    def __init__(self, players: List[str], room_code: str, callback: Callable[[str], Awaitable[None]]):
        super().__init__(timeout=60)  # 60 second timeout
        self.room_code = room_code
        self.callback = callback
        self.add_item(VoteSelect(players))


class VoteSelect(ui.Select):
    """Select menu for voting."""
    
    def __init__(self, players: List[str]):
        options = [
            discord.SelectOption(label=player, value=player, emoji="🎯")
            for player in players
        ]
        
        super().__init__(
            placeholder="Select a player to eliminate...",
            options=options,
            min_values=1,
            max_values=1
        )
    
    async def callback(self, interaction: discord.Interaction):
        """Handle vote selection."""
        selected_player = self.values[0]
        await interaction.response.send_message(
            f"✅ You voted to eliminate **{selected_player}**",
            ephemeral=True
        )
        
        # Call the callback from VoteView
        if hasattr(self.view, 'callback'):
            await self.view.callback(selected_player)


class GameControlView(ui.View):
    """In-game control view."""
    
    def __init__(self, room_code: str):
        super().__init__(timeout=None)
        self.room_code = room_code
    
    @ui.button(label="Leave Game", style=discord.ButtonStyle.red, emoji="🚪")
    async def leave_button(self, interaction: discord.Interaction, button: ui.Button):
        """Handle leave game button click."""
        await interaction.response.defer()

