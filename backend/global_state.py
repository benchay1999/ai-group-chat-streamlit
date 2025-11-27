import asyncio
import time
from typing import Dict
from concurrent.futures import ThreadPoolExecutor
from .config import OPENAI_API_KEYS
from .api_key_manager import APIKeyManager, APIKeyManagerError

# Thread pool for running blocking AI operations without blocking the event loop
# Increased to 60 to handle 10+ concurrent rooms (40+ AIs) without starvation
executor = ThreadPoolExecutor(max_workers=60)

# Room management
rooms: Dict[str, Dict] = {}
# Structure: {
#   room_code: {
#     'state': GameState,
#     'connections': {player_id: WebSocket},
#     'tasks': [],
#     'ai_processing_agents': set(),
#     'ai_lock': asyncio.Lock(),
#     'room_name': str,                  # Display name for the room
#     'max_humans': int,                  # Maximum human players (1-4)
#     'total_players': int,               # Total players including AI (default 5)
#     'room_status': str,                 # 'waiting' | 'in_progress' | 'abandoned' | 'resuming' | 'completed'
#     'created_at': float,                # Timestamp
#     'creator_id': str,                  # Creator's player ID
#     'assigned_humans': List[str],       # Players with permanent slots (formerly current_humans)
#     'current_humans': List[str],        # DEPRECATED - use assigned_humans (kept for backward compat)
#     'connected_humans': List[str],      # Currently connected players (internal use only, never expose to clients)
#     'player_user_map': Dict[str, str],  # Maps player_id -> user_id for authenticated users
#     'game_graph': GameGraph,            # Room-specific GameGraph instance with assigned API key
#     'api_key_index': int,               # Index of the API key assigned to this room (0-based)
#     'permanently_left': Set[str],       # Players who explicitly left (cannot rejoin)
#     'player_last_activity': Dict[str, float],  # Maps player_id -> last activity timestamp
#     'player_heartbeat': Dict[str, float],      # Maps player_id -> last heartbeat timestamp
#     'available_numbers': List[int],     # Player numbers not yet assigned
#     'human_overflow_counter': int,      # Counter for H1, H2 fallback numbering
#     'language': str,                    # Room language ('english' or 'korean')
#     'discussion_duration': int,         # Discussion phase duration in seconds
#     'voting_duration': int              # Voting phase duration in seconds
#   }
# }

# Room locks for preventing race conditions in AI processing
room_locks: Dict[str, asyncio.Lock] = {}

# ============================================================================
# User Activity Tracking (for online user count)
# ============================================================================

# Global user activity tracking
# Structure: {user_id: last_activity_timestamp, ...}
user_activity: Dict[str, float] = {}
ONLINE_THRESHOLD_SECONDS = 90  # Consider user online if active within 90 seconds

# Initialize API key manager for round-robin distribution
api_key_manager = None
try:
    if OPENAI_API_KEYS:
        api_key_manager = APIKeyManager(OPENAI_API_KEYS)
    else:
        print(f"⚠️  WARNING: No OpenAI API keys configured")
        print(f"⚠️  AI features will not work without valid API keys!")
        print(f"⚠️  Set OPENAI_API_KEY or OPENAI_API_KEYS environment variable")
except (ValueError, APIKeyManagerError) as e:
    print(f"⚠️  CRITICAL: Failed to initialize APIKeyManager: {e}")
    print(f"⚠️  AI features will NOT work! Check your API key configuration.")
    api_key_manager = None
except Exception as e:
    print(f"⚠️  UNEXPECTED ERROR initializing APIKeyManager: {e}")
    import traceback
    traceback.print_exc()
    api_key_manager = None


