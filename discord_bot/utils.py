"""
Room and Player Management Utilities
Handles Discord-specific room management and player tracking.
"""

import random
import string
import time
from typing import Dict, List, Optional, Literal
from dataclasses import dataclass, field
from backend.langgraph_state import GameState, PlayerInfo

# Type aliases
RoomStatus = Literal["waiting", "in_progress", "completed"]


@dataclass
class DiscordPlayer:
    """Represents a Discord player in a game room."""
    discord_id: int
    discord_name: str
    display_name: str
    game_player_id: str  # ID used in game state
    joined_at: float
    is_ready: bool = True


@dataclass
class DiscordRoom:
    """Represents a game room in Discord."""
    room_code: str
    channel_id: int  # Lobby channel where room was created
    creator_id: int
    room_name: str
    max_humans: int
    total_players: int
    status: RoomStatus
    created_at: float
    players: Dict[int, DiscordPlayer] = field(default_factory=dict)  # discord_id -> player
    game_state: Optional[GameState] = None
    lobby_message_id: Optional[int] = None
    waiting_message_id: Optional[int] = None
    game_message_id: Optional[int] = None
    game_channel_id: Optional[int] = None  # Dedicated channel for the game
    
    @property
    def num_humans(self) -> int:
        """Current number of human players."""
        return len(self.players)
    
    @property
    def num_ai(self) -> int:
        """Number of AI players needed."""
        return self.total_players - self.max_humans
    
    @property
    def is_full(self) -> bool:
        """Check if room has reached capacity."""
        return self.num_humans >= self.max_humans
    
    @property
    def can_start(self) -> bool:
        """Check if game can start."""
        return self.is_full and self.status == "waiting"


class DiscordRoomManager:
    """Manages all game rooms across Discord channels."""
    
    def __init__(self):
        self.rooms: Dict[str, DiscordRoom] = {}  # room_code -> room
        self.player_to_room: Dict[int, str] = {}  # discord_id -> room_code
    
    def generate_room_code(self) -> str:
        """
        Generate a unique 6-character alphanumeric room code.
        Format: AB12CD (uppercase letters and numbers)
        
        Returns:
            Unique room code
        """
        chars = string.ascii_uppercase + string.digits
        while True:
            code = ''.join(random.choice(chars) for _ in range(6))
            if code not in self.rooms:
                return code
    
    def create_room(
        self,
        channel_id: int,
        creator_id: int,
        room_name: str,
        max_humans: int,
        total_players: int
    ) -> DiscordRoom:
        """
        Create a new game room.
        
        Args:
            channel_id: Discord channel ID where room is created
            creator_id: Discord user ID of room creator
            room_name: Display name for the room
            max_humans: Maximum number of human players
            total_players: Total players including AI
        
        Returns:
            Created DiscordRoom instance
        """
        room_code = self.generate_room_code()
        room = DiscordRoom(
            room_code=room_code,
            channel_id=channel_id,
            creator_id=creator_id,
            room_name=room_name,
            max_humans=max_humans,
            total_players=total_players,
            status="waiting",
            created_at=time.time()
        )
        self.rooms[room_code] = room
        return room
    
    def get_room(self, room_code: str) -> Optional[DiscordRoom]:
        """Get room by code."""
        return self.rooms.get(room_code)
    
    def get_player_room(self, discord_id: int) -> Optional[DiscordRoom]:
        """Get the room a player is currently in."""
        room_code = self.player_to_room.get(discord_id)
        if room_code:
            return self.rooms.get(room_code)
        return None
    
    def add_player_to_room(
        self,
        room_code: str,
        discord_id: int,
        discord_name: str,
        display_name: str
    ) -> bool:
        """
        Add a player to a room.
        
        Args:
            room_code: Room code to join
            discord_id: Discord user ID
            discord_name: Discord username
            display_name: Display name for the game
        
        Returns:
            True if player was added, False if room is full or doesn't exist
        """
        room = self.rooms.get(room_code)
        if not room:
            return False
        
        if room.is_full:
            return False
        
        if room.status != "waiting":
            return False
        
        # Remove player from any previous room
        if discord_id in self.player_to_room:
            old_room_code = self.player_to_room[discord_id]
            self.remove_player_from_room(old_room_code, discord_id)
        
        # Generate game player ID
        player_num = len(room.players) + 1
        game_player_id = f"Human_{player_num}"
        
        # Create player object
        player = DiscordPlayer(
            discord_id=discord_id,
            discord_name=discord_name,
            display_name=display_name,
            game_player_id=game_player_id,
            joined_at=time.time()
        )
        
        room.players[discord_id] = player
        self.player_to_room[discord_id] = room_code
        
        return True
    
    def remove_player_from_room(self, room_code: str, discord_id: int) -> bool:
        """
        Remove a player from a room.
        
        Args:
            room_code: Room code
            discord_id: Discord user ID
        
        Returns:
            True if player was removed, False otherwise
        """
        room = self.rooms.get(room_code)
        if not room:
            return False
        
        if discord_id in room.players:
            del room.players[discord_id]
            
        if discord_id in self.player_to_room:
            del self.player_to_room[discord_id]
        
        # If room is empty and not in progress, delete it
        if len(room.players) == 0 and room.status == "waiting":
            del self.rooms[room_code]
        
        return True
    
    def get_rooms_for_channel(self, channel_id: int) -> List[DiscordRoom]:
        """
        Get all rooms in a specific channel.
        
        Args:
            channel_id: Discord channel ID
        
        Returns:
            List of rooms in the channel
        """
        return [
            room for room in self.rooms.values()
            if room.channel_id == channel_id
        ]
    
    def get_waiting_rooms_for_channel(self, channel_id: int) -> List[DiscordRoom]:
        """Get only waiting rooms for a channel."""
        return [
            room for room in self.rooms.values()
            if room.channel_id == channel_id and room.status == "waiting"
        ]
    
    def start_game(self, room_code: str) -> bool:
        """
        Mark a room as in progress.
        
        Args:
            room_code: Room code
        
        Returns:
            True if status changed, False otherwise
        """
        room = self.rooms.get(room_code)
        if not room:
            return False
        
        if room.status != "waiting":
            return False
        
        room.status = "in_progress"
        return True
    
    def end_game(self, room_code: str) -> bool:
        """
        Mark a room as completed and clean up.
        
        Args:
            room_code: Room code
        
        Returns:
            True if room was ended, False otherwise
        """
        room = self.rooms.get(room_code)
        if not room:
            return False
        
        room.status = "completed"
        
        # Remove player mappings
        for discord_id in list(room.players.keys()):
            if discord_id in self.player_to_room:
                del self.player_to_room[discord_id]
        
        # Delete the room
        if room_code in self.rooms:
            del self.rooms[room_code]
        
        return True
    
    def cleanup_inactive_rooms(self, timeout: int = 3600):
        """
        Remove rooms that have been inactive for too long.
        
        Args:
            timeout: Inactivity timeout in seconds (default: 1 hour)
        """
        current_time = time.time()
        rooms_to_delete = []
        
        for room_code, room in self.rooms.items():
            if current_time - room.created_at > timeout:
                if room.status == "waiting" or room.status == "completed":
                    rooms_to_delete.append(room_code)
        
        for room_code in rooms_to_delete:
            self.end_game(room_code)


# Global room manager instance
room_manager = DiscordRoomManager()

