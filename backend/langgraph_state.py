"""
LangGraph State Schema for the Human Hunter game.
Defines the complete game state structure used by the StateGraph.
"""

from typing import TypedDict, List, Dict, Optional, Literal, Annotated
from enum import Enum
import operator


class Phase(str, Enum):
    """Game phases"""
    DISCUSSION = "Discussion"
    VOTING = "Voting"
    ELIMINATION = "Elimination"
    GAME_OVER = "GameOver"


class PlayerInfo(TypedDict):
    """Individual player information"""
    id: str
    role: Literal["human", "ai"]
    eliminated: bool
    personality: Optional[str]  # Only for AI players


class ChatMessage(TypedDict):
    """Chat message structure"""
    sender: str
    message: str
    timestamp: float


class GameState(TypedDict):
    """
    Complete game state for LangGraph.
    
    This state is passed through all nodes in the graph and can be updated
    by any node. Use Annotated with operator.add for lists to append rather
    than replace.
    """
    # Game metadata
    room_code: str
    round: int
    phase: Phase
    num_ai_players: int
    
    # Players
    players: List[PlayerInfo]
    
    # Chat and communication
    chat_history: Annotated[List[ChatMessage], operator.add]
    
    # Current round topic
    topic: str
    
    # Voting
    votes: Dict[str, str]  # voter_id -> voted_for_id
    
    # AI-specific data
    ai_personalities: Dict[str, str]  # ai_id -> personality
    pseudonym_map: Dict[str, str]  # {real_id: pseudo_label} shared across all agents
    human_external_name: str  # How AIs refer to the human (e.g., "Player 5")
    
    # Timing
    last_message_time: float
    round_start_time: float
    
    # Game outcome
    winner: Optional[Literal["human", "ai"]]
    eliminated_player: Optional[str]
    
    # Pending actions (for async coordination)
    pending_ai_messages: List[str]  # List of AI IDs that need to send messages
    pending_ai_votes: List[str]  # List of AI IDs that need to vote
    
    # WebSocket broadcast queue (messages to send to frontend)
    broadcast_queue: Annotated[List[Dict], operator.add]


def create_initial_state(room_code: str, num_ai_players: int) -> GameState:
    """
    Create the initial game state.
    
    Args:
        room_code: Unique identifier for the game room
        num_ai_players: Number of AI players (4-8)
    
    Returns:
        Initial GameState ready for graph execution
    """
    import random
    import time
    from .config import GAME_TOPICS, AI_PERSONALITIES
    
    # Create AI player names
    ai_names = [f"Player {i}" for i in range(1, num_ai_players + 1)]
    random.shuffle(ai_names)
    
    # Create player list with AIs only at initialization; humans join later via API
    players: List[PlayerInfo] = []
    for name in ai_names:
        players.append({
            "id": name,
            "role": "ai",
            "eliminated": False,
            "personality": random.choice(AI_PERSONALITIES)
        })
    
    # Assign personalities to AIs
    ai_personalities = {
        p["id"]: p["personality"] 
        for p in players 
        if p["role"] == "ai"
    }
    
    # Create ONE shared pseudonym map for all agents (not used by prompts now)
    all_player_ids = [p["id"] for p in players]
    pseudos = [f"P{i+1}" for i in range(len(all_player_ids))]
    random.shuffle(pseudos)
    pseudonym_map = dict(zip(all_player_ids, pseudos))
    
    # No single human external name in multi-human mode; keep empty string for compatibility
    human_external_name = ""
    
    return GameState(
        room_code=room_code,
        round=1,
        phase=Phase.DISCUSSION,
        num_ai_players=num_ai_players,
        players=players,
        chat_history=[],
        topic=random.choice(GAME_TOPICS),
        votes={},
        ai_personalities=ai_personalities,
        pseudonym_map=pseudonym_map,
        human_external_name=human_external_name,
        last_message_time=time.time(),
        round_start_time=time.time(),
        winner=None,
        eliminated_player=None,
        pending_ai_messages=[],  # Start empty; active decision-making will populate this
        pending_ai_votes=[],
        broadcast_queue=[]
    )

