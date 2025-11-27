import time
import asyncio
import random
import string
from typing import Dict, List, Tuple
from fastapi import HTTPException
from collections import defaultdict

from backend.global_state import rooms, room_locks, api_key_manager
from backend.langgraph_game import create_game_for_room, create_game_graph_for_room
from backend.config import STAKE_PERCENTAGE, DISCUSSION_TIME, VOTING_TIME, NUM_AI_PLAYERS
from backend.api_key_manager import APIKeyManagerError

def get_api_key_for_room() -> Tuple[str, int]:
    """
    Get the next API key for a new room.
    Handles errors gracefully and provides clear error messages.
    """
    if api_key_manager is None:
        raise HTTPException(
            status_code=503,
            detail="AI service unavailable: No API keys configured. Please contact administrator."
        )
    
    try:
        api_key, api_key_index = api_key_manager.get_next_api_key()
        return api_key, api_key_index
    except APIKeyManagerError as e:
        print(f"⚠️  CRITICAL: Failed to get API key: {e}")
        raise HTTPException(
            status_code=503,
            detail=f"AI service unavailable: {str(e)}"
        )
    except Exception as e:
        print(f"⚠️  UNEXPECTED ERROR getting API key: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(
            status_code=500,
            detail="Internal error assigning API key. Please try again."
        )

def generate_room_code() -> str:
    """
    Generate a unique 6-character alphanumeric room code.
    Format: AB12CD (uppercase letters and numbers)
    """
    chars = string.ascii_uppercase + string.digits
    while True:
        code = ''.join(random.choice(chars) for _ in range(6))
        if code not in rooms:
            return code

def create_room(max_humans: int, total_players: int, language: str, 
                discussion_duration: int, voting_duration: int, stake_percentage: int) -> Dict:
    """
    Create a new room structure and return the result dict.
    """
    # Generate unique room code
    room_code = generate_room_code()
    
    # Auto-generate room name based on room code
    room_name = f"Room {room_code}"
    
    # Calculate number of AI players needed
    num_ai_players = total_players - max_humans
    
    # Generate random player numbers (shuffled 1 to total_players)
    all_numbers = list(range(1, total_players + 1))
    random.shuffle(all_numbers)
    available_numbers = all_numbers.copy()
    
    # Assign numbers to AI players
    ai_numbers = available_numbers[:num_ai_players]
    available_numbers = available_numbers[num_ai_players:]  # Reserve rest for humans
    
    # Create AI player IDs with assigned numbers
    ai_player_ids = [f"Player {num}" for num in ai_numbers]
    
    # Get next API key for this room (round-robin with error handling)
    api_key, api_key_index = get_api_key_for_room()
    
    # Create initial game state with properly numbered AI players and language
    state = create_game_for_room(room_code, num_ai_players, ai_player_ids, language)
    
    # Create game graph with assigned API key
    try:
        game_graph = create_game_graph_for_room(api_key)
    except Exception as e:
        print(f"⚠️  CRITICAL: Failed to create game graph for room {room_code}: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(
            status_code=500,
            detail="Failed to initialize AI system. Please contact administrator."
        )
    
    # Initialize room with metadata
    rooms[room_code] = {
        'state': state,
        'connections': {},
        'tasks': [],
        'ai_processing_agents': set(),
        'room_name': room_name,
        'max_humans': max_humans,
        'total_players': total_players,
        'room_status': 'waiting',
        'created_at': time.time(),
        'creator_id': '',  # No longer used, auto-assigned on join
        'player_user_map': {},  # Maps player_id -> user_id (for authenticated users)
        'current_humans': [],  # DEPRECATED - kept for backward compatibility
        'assigned_humans': [],  # Players with permanent slots
        'connected_humans': [],  # Currently connected (internal use only)
        'permanently_left': set(),  # Players who explicitly left
        'player_last_activity': {},  # player_id -> timestamp
        'player_heartbeat': {},  # player_id -> timestamp
        'available_numbers': available_numbers,  # Numbers reserved for human players
        'human_overflow_counter': 0,  # Counter for H1, H2 fallback numbering
        'language': language,  # Store room language
        'discussion_duration': discussion_duration,  # Store discussion duration
        'voting_duration': voting_duration,  # Store voting duration
        'game_graph': game_graph,  # Room-specific GameGraph with assigned API key
        'api_key_index': api_key_index,  # Track which API key is assigned
        'stake_percentage': stake_percentage,  # Stake percentage for multi-human games
        'player_stakes': {},  # Maps player_id -> calculated stake amount (in gems)
        'minimum_stake': 0,  # Minimum stake across all players (recalculated as players join)
        'player_message_cooldowns': defaultdict(float) # Track last message time per player for rate limiting
    }
    
    # Initialize lock for this room
    if room_code not in room_locks:
        room_locks[room_code] = asyncio.Lock()
    
    print(f"🎮 Created room {room_code} ({room_name}): {max_humans} humans, {total_players} total, language: {language}, discussion: {discussion_duration}s, voting: {voting_duration}s, stake: {stake_percentage}%")
    
    # Assign a player number for the creator (they'll get it when they join)
    creator_number = available_numbers[0] if available_numbers else 1
    
    return {
        "success": True,
        "room_code": room_code,
        "room_name": room_name,
        "max_humans": max_humans,
        "total_players": total_players,
        "creator_number": creator_number,
        "language": language,
        "discussion_duration": discussion_duration,
        "voting_duration": voting_duration,
        "stake_percentage": stake_percentage,
        "minimum_stake": 0
    }

def get_assigned_humans(room: Dict) -> List[str]:
    """
    Get the list of assigned human players with backward compatibility.
    Tries 'assigned_humans' first, falls back to 'current_humans' for old rooms.
    
    Args:
        room: Room dictionary
    
    Returns:
        List of player IDs with permanent room slots
    """
    # New field takes precedence
    if 'assigned_humans' in room and room['assigned_humans']:
        return room['assigned_humans']
    # Fall back to deprecated field
    return room.get('current_humans', [])

def get_connected_humans(room: Dict) -> List[str]:
    """
    Get the list of currently connected human players (internal use only).
    This should NEVER be exposed to clients to maintain player anonymity.
    
    Args:
        room: Room dictionary
    
    Returns:
        List of currently connected player IDs
    """
    return room.get('connected_humans', [])

def sync_assigned_and_current_humans(room: Dict):
    """
    Synchronize assigned_humans and current_humans for backward compatibility.
    Call this after modifying assigned_humans to keep current_humans in sync.
    
    Args:
        room: Room dictionary
    """
    room['current_humans'] = room.get('assigned_humans', []).copy()

def update_player_activity(room: Dict, player_id: str):
    """
    Update the last activity timestamp for a player.
    Call this when a player sends a message, votes, or performs any action.
    
    Args:
        room: Room dictionary
        player_id: Player identifier
    """
    current_time = time.time()
    if 'player_last_activity' not in room:
        room['player_last_activity'] = {}
    room['player_last_activity'][player_id] = current_time

def update_player_heartbeat(room: Dict, player_id: str):
    """
    Update the heartbeat timestamp for a player.
    Call this when receiving a heartbeat ping from the client.
    
    Args:
        room: Room dictionary
        player_id: Player identifier
    """
    current_time = time.time()
    if 'player_heartbeat' not in room:
        room['player_heartbeat'] = {}
    room['player_heartbeat'][player_id] = current_time
    # Heartbeat also counts as activity
    update_player_activity(room, player_id)

async def periodic_room_cleanup():
    """
    Background task to clean up abandoned rooms.
    Runs every 10 minutes.
    """
    while True:
        try:
            await asyncio.sleep(600)  # 10 minutes
            
            print("\n🧹 Running periodic room cleanup...")
            current_time = time.time()
            rooms_to_delete = []
            
            for room_code, room_data in list(rooms.items()):
                room_status = room_data.get('room_status', '')
                created_at = room_data.get('created_at', 0)
                age_minutes = (current_time - created_at) / 60
                
                assigned_humans = get_assigned_humans(room_data)
                connections = room_data.get('connections', {})
                
                # Rule 1: Waiting rooms with no assigned humans for >60 minutes
                if room_status == 'waiting':
                    if len(assigned_humans) == 0 and age_minutes > 60:
                        print(f"🗑️  Cleanup: Waiting room {room_code} abandoned for {age_minutes:.1f}m (no players)")
                        rooms_to_delete.append(room_code)
                        continue
                    # Rule 1b: Waiting rooms with assigned humans but no connections for >30 minutes
                    if len(connections) == 0 and age_minutes > 30:
                        print(f"🗑️  Cleanup: Waiting room {room_code} abandoned for {age_minutes:.1f}m (no connections)")
                        rooms_to_delete.append(room_code)
                        continue
                
                # Rule 2: In-progress rooms with no active connections for >30 minutes
                if room_status == 'in_progress':
                    if len(connections) == 0 and age_minutes > 30:
                        print(f"🗑️  Cleanup: In-progress room {room_code} abandoned for {age_minutes:.1f}m")
                        rooms_to_delete.append(room_code)
                        continue
                
                # Rule 3: Abandoned rooms with no activity for >30 minutes
                if room_status == 'abandoned':
                    if len(connections) == 0 and age_minutes > 30:
                        print(f"🗑️  Cleanup: Abandoned room {room_code} aged {age_minutes:.1f}m")
                        rooms_to_delete.append(room_code)
                        continue
                
                # Rule 4: Completed rooms older than 2 hours
                if room_status == 'completed' and age_minutes > 120:
                    print(f"🗑️  Cleanup: Completed room {room_code} aged {age_minutes:.1f}m")
                    rooms_to_delete.append(room_code)
                    continue
            
            # Delete identified rooms (with lock protection to avoid race conditions)
            for room_code in rooms_to_delete:
                # Try to acquire lock before deleting (with timeout to avoid deadlock)
                try:
                    # Initialize lock if it doesn't exist (shouldn't happen but be defensive)
                    if room_code not in room_locks:
                        room_locks[room_code] = asyncio.Lock()
                    
                    # Try to acquire lock with timeout (using wait_for for Python 3.7+ compatibility)
                    lock = room_locks[room_code]
                    acquired = await asyncio.wait_for(lock.acquire(), timeout=5.0)
                    try:
                        if room_code in rooms:
                            # Clean up player_user_map entries
                            player_user_map = rooms[room_code].get('player_user_map', {})
                            if player_user_map:
                                print(f"🗑️  Cleaning up {len(player_user_map)} player_user_map entries from {room_code}")
                            
                            del rooms[room_code]
                        if room_code in room_locks:
                            # Note: We can't delete the lock while holding it, so we'll leave it
                            # It will be cleaned up on next iteration or eventually garbage collected
                            pass
                        print(f"✅ Cleaned up room {room_code}")
                    finally:
                        lock.release()
                except asyncio.TimeoutError:
                    print(f"⚠️  Timeout acquiring lock for room {room_code}, will retry next cleanup cycle")
                except Exception as e:
                    print(f"❌ Error cleaning up room {room_code}: {e}")
            
            if rooms_to_delete:
                print(f"🧹 Cleanup complete: Removed {len(rooms_to_delete)} rooms")
            else:
                print("🧹 Cleanup complete: No rooms to remove")
                
        except Exception as e:
            print(f"❌ Error in periodic cleanup: {e}")
            import traceback
            traceback.print_exc()

async def monitor_room_health():
    """
    Background task to monitor room health and detect inconsistencies.
    Runs every 1 minute.
    """
    while True:
        try:
            await asyncio.sleep(60)  # 1 minute
            
            print("\n🏥 Running room health check...")
            current_time = time.time()
            issues_found = 0
            
            for room_code, room_data in list(rooms.items()):
                room_status = room_data.get('room_status', '')
                
                # Get all relevant lists
                assigned_humans = get_assigned_humans(room_data)
                connected_humans = get_connected_humans(room_data)
                connections = room_data.get('connections', {})
                player_user_map = room_data.get('player_user_map', {})
                player_heartbeat = room_data.get('player_heartbeat', {})
                
                # Check 1: Inactive players (no heartbeat for >5 minutes)
                inactive_players = []
                for player_id in assigned_humans:
                    last_heartbeat = player_heartbeat.get(player_id, 0)
                    if current_time - last_heartbeat > 300:  # 5 minutes
                        inactive_players.append(player_id)
                
                if inactive_players and room_status == 'in_progress':
                    print(f"⚠️  Room {room_code}: {len(inactive_players)} inactive players (no heartbeat >5min)")
                    
                    # If ALL players are inactive, transition to abandoned state
                    if len(inactive_players) == len(assigned_humans) and len(connections) == 0:
                        print(f"🚨 Room {room_code}: All players inactive, transitioning to 'abandoned'")
                        room_data['room_status'] = 'abandoned'
                        issues_found += 1
                
                # Check 2: Duplicate player IDs in assigned_humans
                if len(assigned_humans) != len(set(assigned_humans)):
                    duplicates = [p for p in assigned_humans if assigned_humans.count(p) > 1]
                    print(f"🚨 Room {room_code}: DUPLICATE players in assigned_humans: {duplicates}")
                    issues_found += 1
                
                # Check 3: player_user_map inconsistency
                for player_id in player_user_map.keys():
                    if player_id not in assigned_humans:
                        print(f"⚠️  Room {room_code}: Player {player_id} in player_user_map but not in assigned_humans")
                        issues_found += 1
                
                # Check 4: Connections without assigned slots
                for player_id in connections.keys():
                    if player_id not in assigned_humans:
                        print(f"⚠️  Room {room_code}: Player {player_id} connected but not in assigned_humans")
                        issues_found += 1
            
            if issues_found == 0:
                print("🏥 Health check complete: All rooms healthy")
            else:
                print(f"🏥 Health check complete: {issues_found} issues detected")
                
        except Exception as e:
            print(f"❌ Error in room health monitoring: {e}")
            import traceback
            traceback.print_exc()


