import time
import asyncio
from collections import defaultdict
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from backend.database import get_async_session, User
from backend.auth import get_current_user_optional
from backend.global_state import rooms, room_locks
from backend.langgraph_state import Phase
from backend.langgraph_game import (
    create_game_for_room, create_game_graph_for_room,
    process_human_message, process_human_vote
)
from backend.config import (
    NUM_AI_PLAYERS, DISCUSSION_TIME, VOTING_TIME, STAKE_PERCENTAGE
)
from backend.services.room_management import (
    create_room as create_room_logic,
    get_assigned_humans,
    sync_assigned_and_current_humans,
    update_player_activity,
    update_player_heartbeat,
    get_api_key_for_room
)
from backend.services.game_coordinator import (
    run_discussion_phase,
    trigger_agent_decisions,
    complete_voting
)
from backend.services.messaging import broadcast_to_room

router = APIRouter()

@router.post("/api/rooms/create")
async def create_room(
    room_data: dict, 
    current_user: User = Depends(get_current_user_optional),
    db: AsyncSession = Depends(get_async_session)
):
    """
    Create a new matching room.
    """
    max_humans = room_data.get('max_humans', 1)
    total_players = room_data.get('total_players', 5)
    language = room_data.get('language', 'english')
    discussion_duration = room_data.get('discussion_duration', 180)
    voting_duration = room_data.get('voting_duration', 60)
    # Use configured default stake percentage (converted to int 0-100 safely)
    default_stake = int(round(STAKE_PERCENTAGE * 100))
    stake_percentage = room_data.get('stake_percentage', default_stake)
    
    # Check if user is already in an active room
    if current_user:
        user_id = str(current_user.id)
        
        # Search all rooms for this user's active session
        for existing_room_code, existing_room_data in rooms.items():
            existing_room_status = existing_room_data.get('room_status', '')
            
            # Only check rooms that are waiting or in_progress
            if existing_room_status not in ['waiting', 'in_progress']:
                continue
            
            # Check player_user_map for this user
            player_user_map = existing_room_data.get('player_user_map', {})
            
            for player_id, mapped_user_id in player_user_map.items():
                if mapped_user_id == user_id:
                    # User already in active room
                    return {
                        "success": False, 
                        "error": f"You are already in an active game ({existing_room_code}). Please finish or leave that game before creating a new one."
                    }

    # Validation
    if not (1 <= max_humans <= 5):
        return {"success": False, "error": "max_humans must be between 1 and 5"}
    
    if total_players < max_humans:
        return {"success": False, "error": "total_players must be >= max_humans"}
    
    if total_players > 12:
        return {"success": False, "error": "total_players cannot exceed 12"}
    
    if language not in ["english", "korean"]:
        return {"success": False, "error": "language must be 'english' or 'korean'"}
    
    # Allow debug durations (60s discussion, 30s voting) in addition to normal durations
    if discussion_duration not in [60, 180, 240]:
        return {"success": False, "error": "discussion_duration must be 60, 180, or 240 seconds"}
    
    if voting_duration not in [30, 60, 120]:
        return {"success": False, "error": "voting_duration must be 30, 60, or 120 seconds"}
    
    # Stake percentage validation
    if stake_percentage not in [0, 10, 30, 50, 100]:
        return {"success": False, "error": "stake_percentage must be 0, 10, 30, 50, or 100"}
    
    # Multi-human room validation: Must have at least 250 gems IF stakes are involved
    if max_humans > 1:
        if stake_percentage > 0:
            if not current_user:
                return {"success": False, "error": "Authentication required to create staked multi-human rooms"}
            
            if current_user.gem_balance < 250:
                return {
                    "success": False, 
                    "error": f"Insufficient gems. You need at least 250 gems to create a staked multi-human room. Your balance: {current_user.gem_balance} gems"
                }
    
    # Create room using service logic
    return create_room_logic(
        max_humans=max_humans,
        total_players=total_players,
        language=language,
        discussion_duration=discussion_duration,
        voting_duration=voting_duration,
        stake_percentage=stake_percentage
    )


@router.get("/api/rooms/{room_code}/stake_info")
async def get_stake_info(room_code: str):
    """
    Get stake information for a multi-human room.
    """
    if room_code not in rooms:
        raise HTTPException(status_code=404, detail="Room not found")
    
    room_data = rooms[room_code]
    max_humans = room_data.get('max_humans', 1)
    
    # Single-human games don't have stakes
    if max_humans == 1:
        return {
            "has_stakes": False,
            "stake_percentage": 0,
            "minimum_stake": 0,
            "player_stakes": {}
        }
    
    stake_percentage = room_data.get('stake_percentage', 0)
    player_stakes = room_data.get('player_stakes', {})
    minimum_stake = room_data.get('minimum_stake', 0)
    
    return {
        "has_stakes": stake_percentage > 0,
        "stake_percentage": stake_percentage,
        "minimum_stake": minimum_stake,
        "player_stakes": player_stakes,
        "num_players_joined": len(player_stakes)
    }


@router.get("/api/rooms/list")
async def list_rooms(page: int = 0, per_page: int = 10):
    """
    List available rooms (waiting status only).
    """
    # Filter rooms with 'waiting' status
    # Use assigned_humans to show slots, never expose who's actually connected
    waiting_rooms = [
        {
            'room_code': code,
            'room_name': data['room_name'],
            'current_humans': len(get_assigned_humans(data)),  # Use assigned slots, not connections
            'max_humans': data['max_humans'],
            'total_players': data['total_players'],
            'room_status': data['room_status'],
            'created_at': data['created_at'],
            'language': data.get('language', 'english'),
            'discussion_duration': data.get('discussion_duration', 180),
            'voting_duration': data.get('voting_duration', 60),
            'stake_percentage': data.get('stake_percentage', 0),
            'minimum_stake': data.get('minimum_stake', 0),
            'has_stakes': data.get('max_humans', 1) > 1 and data.get('stake_percentage', 0) > 0
        }
        for code, data in rooms.items()
        if data.get('room_status') == 'waiting'
    ]
    
    # Sort by created_at descending (newest first)
    waiting_rooms.sort(key=lambda r: r['created_at'], reverse=True)
    
    # Paginate
    total = len(waiting_rooms)
    start = page * per_page
    end = start + per_page
    page_rooms = waiting_rooms[start:end]
    
    return {
        "rooms": page_rooms,
        "total": total,
        "page": page,
        "per_page": per_page,
        "total_pages": (total + per_page - 1) // per_page if total > 0 else 0
    }


@router.get("/api/rooms/{room_code}/info")
async def get_room_info(room_code: str):
    """
    Get room metadata without full game state.
    """
    if room_code not in rooms:
        return {"error": "Room not found", "exists": False}
    
    room = rooms[room_code]
    
    # Use assigned_humans for display (never expose connected_humans to maintain anonymity)
    assigned_humans = get_assigned_humans(room)
    
    return {
        "exists": True,
        "room_code": room_code,
        "room_name": room['room_name'],
        "current_humans": assigned_humans,  # Shows assigned slots, not actual connections
        "max_humans": room['max_humans'],
        "total_players": room['total_players'],
        "room_status": room['room_status'],
        "created_at": room['created_at'],
        "language": room.get('language', 'english'),
        "discussion_duration": room.get('discussion_duration', 180),
        "voting_duration": room.get('voting_duration', 60)
    }


@router.post("/api/rooms/{room_code}/leave")
async def leave_room_endpoint(room_code: str, player_data: dict):
    """
    Handle a player leaving a room.
    """
    if room_code not in rooms:
        return {"success": False, "error": "Room not found"}
    
    player_id = player_data.get('player_id', '')
    room = rooms[room_code]
    
    # Get room metadata
    current_humans = room.get('current_humans', [])
    room_status = room.get('room_status', '')
    max_humans = room.get('max_humans', 1)
    
    print(f"🚪 Player {player_id} leaving room {room_code} (max_humans={max_humans}, status={room_status})")
    
    # CASE 1: Single-player game (max_humans == 1) - Always terminate
    if max_humans == 1:
        print(f"🗑️ Terminating single-player room {room_code}")
        
        # Broadcast to any connected clients
        await broadcast_to_room(room_code, {
            "type": "room_terminated",
            "message": "Room has been terminated"
        })
        
        # Clean up room
        if room_code in rooms:
            del rooms[room_code]
        if room_code in room_locks:
            del room_locks[room_code]
        
        return {
            "success": True,
            "action": "terminated",
            "message": "Single-player room terminated"
        }
    
    # CASE 2: Multi-player game in waiting status - Terminate
    if max_humans > 1 and room_status == 'waiting':
        print(f"🗑️ Terminating room {room_code} (in waiting status)")
    
        # Broadcast to any connected clients
        await broadcast_to_room(room_code, {
            "type": "room_terminated",
            "message": "Room was cancelled"
        })
        
        # Clean up room
        if room_code in rooms:
            del rooms[room_code]
        if room_code in room_locks:
            del room_locks[room_code]
        
        return {
            "success": True,
            "action": "terminated",
            "message": "Room terminated (waiting status)"
        }
    
    # CASE 3: Multi-player game in progress - Keep room alive, remove player from assigned_humans
    # This is an EXPLICIT leave (not a temporary disconnect)
    
    # Get assigned_humans list (with backward compatibility)
    # Work with a copy to avoid modifying the original list directly
    current_assigned = get_assigned_humans(room)
    assigned_humans = current_assigned.copy() if current_assigned else []
    
    if player_id in assigned_humans:
        assigned_humans.remove(player_id)
        print(f"👋 Removed {player_id} from assigned_humans in room {room_code}. Remaining: {assigned_humans}")
    
    # Update assigned_humans in room (sync will update current_humans automatically)
    room['assigned_humans'] = assigned_humans
    sync_assigned_and_current_humans(room)
    
    # IMPORTANT: Remove from player_user_map to allow user to join other games
    player_user_map = room.get('player_user_map', {})
    if player_id in player_user_map:
        removed_user_id = player_user_map.pop(player_id)
        print(f"🗑️  Removed {player_id} from player_user_map (user_id: {removed_user_id[:8] if removed_user_id else 'N/A'}...)")
    
    # Remove from player_stakes and recalculate minimum_stake
    player_stakes = room.get('player_stakes', {})
    if player_id in player_stakes:
        removed_stake = player_stakes.pop(player_id)
        print(f"💎 Removed {player_id}'s stake ({removed_stake} gems)")
        
        # Recalculate minimum stake
        remaining_stakes = list(player_stakes.values())
        if remaining_stakes:
            room['minimum_stake'] = min(remaining_stakes)
            print(f"💎 Minimum stake recalculated to: {room['minimum_stake']} gems")
            
            # Broadcast stake update to remaining players
            await broadcast_to_room(room_code, {
                "type": "stake_update",
                "minimum_stake": room['minimum_stake'],
                "stake_percentage": room.get('stake_percentage', 0),
                "num_players": len(player_stakes)
            })
        else:
            room['minimum_stake'] = 0
    
    # Add to permanently_left set to prevent rejoin
    if 'permanently_left' not in room:
        room['permanently_left'] = set()
    room['permanently_left'].add(player_id)
    print(f"🚫 Added {player_id} to permanently_left - cannot rejoin this room")
    
    # DO NOT remove from game state - they stay in the game as eliminated/absent
    # DO NOT add back their number to available_numbers - it's permanently assigned
    
    # Note: We keep the room alive even if assigned_humans is empty
    # The room will be cleaned up by the periodic cleanup task or when the game ends
    
    return {
        "success": True,
        "action": "left_permanently",
        "message": f"Player left the room permanently. {len(assigned_humans)} players remaining"
    }


@router.get("/api/rooms/{room_code}/state")
async def get_room_state(room_code: str, player_id: str = "StreamlitUser"):
    """
    Get the current state of a room for polling-based clients (Streamlit).
    """
    if room_code not in rooms:
        return {
            "error": "Room not found",
            "exists": False
        }
    
    # Ensure lock exists
    if room_code not in room_locks:
        room_locks[room_code] = asyncio.Lock()
    
    # CRITICAL: Use lock to prevent reading while state is being updated
    async with room_locks[room_code]:
        room = rooms[room_code]
        state = room['state']
        
        # Calculate remaining time based on phase
        timer = 0
        current_time = time.time()
        
        if state['phase'] == Phase.DISCUSSION:
            duration = room.get('discussion_duration', DISCUSSION_TIME)
            if 'phase_start_time' in room:
                elapsed = current_time - room['phase_start_time']
                timer = max(0, int(duration - elapsed))
            else:
                timer = duration
                
        elif state['phase'] == Phase.VOTING:
            duration = room.get('voting_duration', VOTING_TIME)
            if 'phase_start_time' in room:
                elapsed = current_time - room['phase_start_time']
                timer = max(0, int(duration - elapsed))
            else:
                timer = duration
                
        # Get persistent typing indicators from room metadata
        if 'typing_players' not in room:
            room['typing_players'] = set()
            if 'typing_players' in state and isinstance(state['typing_players'], (set, list)):
                room['typing_players'] = set(state['typing_players'])
                
        typing_players = list(room['typing_players'])
        
        # Prepare response dict inside lock
        response = {
            "exists": True,
            "phase": state['phase'].value,
            "round": state['round'],
            "topic": state['topic'],
            "players": [
                {
                    "id": p['id'],
                    "role": p['role'],
                    "eliminated": p['eliminated'],
                    "voted": p['id'] in state.get('votes', {})
                }
                for p in state['players']
            ],
            "chat_history": list(state.get('chat_history', [])),
            "votes": state.get('votes', {}).copy(),
            "winner": state.get('winner'),
            "winning_players": list(state.get('winning_players', [])),
            "selected_suspect": state.get('selected_suspect'),
            "suspect_role": state.get('suspect_role'),
            "current_player_id": player_id,
            "typing": typing_players,
            "timer": timer
        }
    
    return response


@router.post("/api/rooms/{room_code}/join")
async def join_room(
    room_code: str, 
    player_data: dict,
    current_user: User = Depends(get_current_user_optional),
    db: AsyncSession = Depends(get_async_session)
):
    """
    Join a room for Streamlit client (with matching room system support).
    """
    # Log authentication status
    if current_user:
        print(f"🔐 User '{current_user.user_id}' (ID: {str(current_user.id)[:8]}...) joining room {room_code} via API")
    else:
        print(f"🔓 Anonymous user joining room {room_code} via API")
    
    # Initialize lock for this room if needed
    if room_code not in room_locks:
        room_locks[room_code] = asyncio.Lock()
    
    # CRITICAL: Use lock to prevent race conditions during join
    async with room_locks[room_code]:
        # VALIDATE: Check if user already has an active session in another room
        if current_user:
            user_id = str(current_user.id)
            
            for other_room_code, other_room_data in rooms.items():
                # Skip the room they're trying to join (allow rejoin)
                if other_room_code == room_code:
                    continue
            
                other_room_status = other_room_data.get('room_status', '')
            
                # Only check rooms that are waiting or in_progress
                if other_room_status not in ['waiting', 'in_progress']:
                    continue
            
                # Check player_user_map for this user
                player_user_map = other_room_data.get('player_user_map', {})
            
                for player_id, mapped_user_id in player_user_map.items():
                    if mapped_user_id == user_id:
                        # User already in another active room
                        print(f"❌ User {current_user.user_id} already in active room {other_room_code} (player={player_id}, status={other_room_status})")
                        return {
                            "success": False, 
                            "error": "You are already in an active game. Please leave that game first.",
                            "active_room_code": other_room_code,
                            "active_player_id": player_id
                        }
    
        # HANDLE REJOIN: Check if user is already in THIS room
        if current_user and room_code in rooms:
            user_id = str(current_user.id)
            room = rooms[room_code]
            room_status = room.get('room_status', '')
            
            # VALIDATION: Don't allow rejoin to completed games
            if room_status == 'completed':
                return {
                    "success": False,
                    "error": "This game has already been completed. You cannot rejoin."
                }
            
            player_user_map = room.get('player_user_map', {})
        
            for player_id, mapped_user_id in player_user_map.items():
                if mapped_user_id == user_id:
                    # Check if player explicitly left (permanently)
                    permanently_left = room.get('permanently_left', set())
                    if player_id in permanently_left:
                        return {
                            "success": False,
                            "error": "You have left this room permanently and cannot rejoin."
                        }
                    
                    # User is rejoining their existing session
                    print(f"🔄 User {current_user.user_id} rejoining room {room_code} as {player_id}")
                
                    current_assigned = get_assigned_humans(room)
                    assigned_humans = current_assigned.copy() if current_assigned else []
                
                    # Add back to assigned_humans if not there
                    if player_id not in assigned_humans:
                        assigned_humans.append(player_id)
                        room['assigned_humans'] = assigned_humans
                        sync_assigned_and_current_humans(room)
                        print(f"✅ Added {player_id} back to assigned_humans. Total: {len(assigned_humans)}")
                    else:
                        print(f"ℹ️  {player_id} already in assigned_humans (duplicate avoided)")
                        room['assigned_humans'] = assigned_humans
                    
                    # Track player activity
                    update_player_activity(room, player_id)
                    update_player_heartbeat(room, player_id)
                
                    # Check if room can/should start or resume
                    max_humans = room.get('max_humans', 4)
                    can_start = len(assigned_humans) >= max_humans
                    room_status = room.get('room_status', '')
                
                    # STATE MACHINE: Handle different room states
                    if can_start and room_status == 'waiting':
                        room['room_status'] = 'in_progress'
                        print(f"🎮 Starting game in room {room_code} after rejoin")
                    
                        # Initialize game if needed
                        state = room['state']
                        if 'initialized' not in room or not room['initialized']:
                            game_graph = rooms[room_code]['game_graph']
                            result = game_graph.initialize_game_node(state)
                            state.update(result)
                            rooms[room_code]['state'] = state
                            rooms[room_code]['initialized'] = True
                        
                            # Start phases
                            asyncio.create_task(run_discussion_phase(room_code))
                            
                            # Immediately send timer sync
                            discussion_duration = room.get('discussion_duration', DISCUSSION_TIME)
                            await broadcast_to_room(room_code, {
                                "type": "timer_sync",
                                "phase": "Discussion",
                                "time_remaining": int(discussion_duration)
                            })
                            
                            await asyncio.sleep(0.75)
                            asyncio.create_task(trigger_agent_decisions(room_code))
                    
                    elif room_status == 'resuming' and can_start:
                        room['room_status'] = 'in_progress'
                        print(f"🔄 Resuming game in room {room_code} after players rejoined ({len(assigned_humans)}/{max_humans})")
                    
                    elif room_status == 'abandoned' and len(assigned_humans) >= 1:
                        room['room_status'] = 'resuming'
                        print(f"🔄 Room {room_code} transitioning from abandoned to resuming ({len(assigned_humans)} players back)")
                
                    return {
                        "success": True,
                        "player_id": player_id,
                        "room_code": room_code,
                        "room_name": room.get('room_name', room_code),
                        "can_start": room.get('room_status') == 'in_progress',
                        "rejoined": True,
                        "room_status": room.get('room_status', 'waiting')
                    }
    
        # Check if room exists
        if room_code not in rooms:
            print(f"⚠️ Room {room_code} does NOT exist, creating legacy room")
            # Legacy behavior: Create room if doesn't exist (for old room codes)
            # For legacy rooms, assign random player numbers too
            # Legacy rooms are now explicitly SINGLE-PLAYER ONLY (1 human + N AI)
            max_humans = 1
            total_players = NUM_AI_PLAYERS + max_humans
            all_numbers = list(range(1, total_players + 1))
            import random
            random.shuffle(all_numbers)
            human_number = all_numbers[0]
            player_id = f"Player {human_number}"
        
            # Assign remaining numbers to AI players
            ai_numbers = all_numbers[1:]
            ai_player_ids = [f"Player {num}" for num in ai_numbers]
        
            # Get next API key
            try:
                api_key, api_key_index = get_api_key_for_room()
            except HTTPException as e:
                return {
                    "success": False,
                    "error": f"Failed to create room: {e.detail}",
                    "player_id": None
                }
        
            # Create game state
            state = create_game_for_room(room_code, NUM_AI_PLAYERS, ai_player_ids)
            
            # Create game graph
            try:
                game_graph = create_game_graph_for_room(api_key)
            except Exception as e:
                print(f"⚠️  CRITICAL: Failed to create game graph for legacy room {room_code}: {e}")
                import traceback
                traceback.print_exc()
                return {
                    "success": False,
                    "error": "Failed to initialize AI system. Please try again.",
                    "player_id": None
                }
        
            rooms[room_code] = {
                'state': state,
                'connections': {},
                'tasks': [],
                'ai_processing_agents': set(),
                'room_name': f"Room {room_code}",
                'max_humans': max_humans,
                'total_players': total_players,
                'room_status': 'waiting',
                'created_at': time.time(),
                'creator_id': player_id,
                'player_user_map': {},
                'current_humans': [],
                'assigned_humans': [],
                'connected_humans': [],
                'permanently_left': set(),
                'player_last_activity': {},
                'player_heartbeat': {},
                'available_numbers': [],
                'human_overflow_counter': 0,
                'discussion_duration': DISCUSSION_TIME,
                'voting_duration': VOTING_TIME,
                'game_graph': game_graph,
                'api_key_index': api_key_index
            }
            if room_code not in room_locks:
                room_locks[room_code] = asyncio.Lock()
        
            # Initialize game
            game_graph = rooms[room_code]['game_graph']
            result = game_graph.initialize_game_node(state)
            state.update(result)
            rooms[room_code]['state'] = state
        
            # Start phases
            asyncio.create_task(run_discussion_phase(room_code))
            
            # Immediately send timer sync
            discussion_duration = rooms[room_code].get('discussion_duration', DISCUSSION_TIME)
            await broadcast_to_room(room_code, {
                "type": "timer_sync",
                "phase": "Discussion",
                "time_remaining": int(discussion_duration)
            })
            
            await asyncio.sleep(0.75)
            asyncio.create_task(trigger_agent_decisions(room_code))
    
        room = rooms[room_code]
        print(f"🔍 Room {room_code} exists - discussion_duration: {room.get('discussion_duration', 'NOT SET')}, voting_duration: {room.get('voting_duration', 'NOT SET')}")
    
        # Check room status
        room_status = room.get('room_status', '')
        
        if room_status == 'in_progress':
            return {"success": False, "error": "Room already in progress"}
        
        if room_status == 'completed':
            return {"success": False, "error": "Room game completed"}
        
        if room_status in ['abandoned', 'resuming']:
            return {"success": False, "error": "Room is not accepting new players. Only rejoins allowed."}
    
        # Check capacity
        max_humans = room.get('max_humans', 4)
        assigned_humans = get_assigned_humans(room)
    
        if len(assigned_humans) >= max_humans:
            return {"success": False, "error": f"Room full ({max_humans} humans max)"}
        
        # MULTI-HUMAN ROOM VALIDATION
        if max_humans > 1:
            stake_percentage = room.get('stake_percentage', 0)
            if stake_percentage > 0:
                if not current_user:
                    return {
                        "success": False, 
                        "error": "Authentication required to join staked multi-human rooms"
                    }
                
                if current_user.gem_balance < 250:
                    return {
                        "success": False, 
                        "error": f"Insufficient gems. You need at least 250 gems to join a staked multi-human room. Your balance: {current_user.gem_balance} gems"
                    }
    
        # Get state
        state = room['state']
    
        # Assign a random player number
        available_numbers = room.get('available_numbers', [])
        if not available_numbers:
            human_overflow_counter = room.get('human_overflow_counter', 0)
            human_overflow_counter += 1
            room['human_overflow_counter'] = human_overflow_counter
            player_id = f"Player H{human_overflow_counter}"
            print(f"⚠️  WARNING: available_numbers exhausted! Using overflow numbering: {player_id}")
        else:
            player_number = available_numbers.pop(0)
            player_id = f"Player {player_number}"
    
        # Add player to assigned_humans list
        current_assigned = get_assigned_humans(room)
        assigned_humans = current_assigned.copy() if current_assigned else []
        assigned_humans.append(player_id)
        room['assigned_humans'] = assigned_humans
        sync_assigned_and_current_humans(room)
    
        # Track player activity
        update_player_activity(room, player_id)
        update_player_heartbeat(room, player_id)
    
        # If first human, mark as creator
        if len(room['current_humans']) == 1:
            room['creator_id'] = player_id
            print(f"👑 {player_id} is the creator of room {room_code}")
    
        # Add player to game state
        state['players'].append({
            'id': player_id,
            'role': 'human',
            'eliminated': False,
            'personality': None
        })
        rooms[room_code]['state'] = state
    
        # Store user mapping
        if current_user:
            user_id_str = str(current_user.id)
            room['player_user_map'][player_id] = user_id_str
            print(f"👤 ✅ Player {player_id} joined room {room_code} ({len(room['current_humans'])}/{max_humans}) - Mapped to user {user_id_str[:8]}...")
            
            # Calculate and store stake
            if max_humans > 1:
                stake_percentage = room.get('stake_percentage', 0)
                player_stake = int(current_user.gem_balance * stake_percentage / 100)
                room['player_stakes'][player_id] = player_stake
                
                # Recalculate minimum stake
                all_stakes = list(room['player_stakes'].values())
                if all_stakes:
                    room['minimum_stake'] = min(all_stakes)
                    print(f"💎 Player {player_id} stake: {player_stake} gems ({stake_percentage}% of {current_user.gem_balance})")
                    print(f"💎 Room minimum stake updated to: {room['minimum_stake']} gems")
                    
                    # Broadcast stake update
                    await broadcast_to_room(room_code, {
                        "type": "stake_update",
                        "minimum_stake": room['minimum_stake'],
                        "stake_percentage": stake_percentage,
                        "num_players": len(room['player_stakes'])
                    })
        else:
            print(f"👤 Player {player_id} joined room {room_code} ({len(room['current_humans'])}/{max_humans}) - Anonymous")
    
        # Check if room is ready to start
        can_start = len(room['current_humans']) >= max_humans
    
        if can_start:
            # Update room status
            room['room_status'] = 'in_progress'
        
            print(f"🎮 Starting game in room {room_code} with {len(room['current_humans'])} humans")
        
            # Initialize game if not already initialized
            if 'initialized' not in room:
                game_graph = rooms[room_code]['game_graph']
                result = game_graph.initialize_game_node(state)
                state.update(result)
                rooms[room_code]['state'] = state
                rooms[room_code]['initialized'] = True
            
                if 'broadcast_queue' in result:
                    for msg in result['broadcast_queue']:
                        await broadcast_to_room(room_code, msg)
                
                print(f"💎 Stakes configured but NOT deducted yet (will deduct after successful voting)")
                print(f"   Minimum stake: {room.get('minimum_stake', 0)} gems per player")
                print(f"   Stakes at risk (not charged): {room.get('player_stakes', {})}")
            
                # Start phases
                print(f"🚀 Starting game phases - discussion_duration: {room.get('discussion_duration', 'NOT SET')}, voting_duration: {room.get('voting_duration', 'NOT SET')}")
                asyncio.create_task(run_discussion_phase(room_code))
                
                # Immediately send timer sync
                discussion_duration = room.get('discussion_duration', DISCUSSION_TIME)
                await broadcast_to_room(room_code, {
                    "type": "timer_sync",
                    "phase": "Discussion",
                    "time_remaining": int(discussion_duration)
                })
                
                await asyncio.sleep(0.75)
                asyncio.create_task(trigger_agent_decisions(room_code))
    
        assigned_humans_count = len(get_assigned_humans(room))
        
        return {
            "success": True,
            "message": f"Joined room {room_code}",
            "player_id": player_id,
            "can_start": can_start,
            "waiting": not can_start,
            "current_humans": assigned_humans_count,
            "max_humans": max_humans
        }


@router.post("/api/rooms/{room_code}/message")
async def send_message(room_code: str, message_data: dict):
    """
    Send a chat message from Streamlit client.
    """
    if room_code not in rooms:
        return {"error": "Room not found"}
    
    player_id = message_data.get('player_id', 'StreamlitUser')
    message = message_data.get('message', '')
    
    if not message.strip():
        return {"error": "Empty message"}
    
    room = rooms[room_code]
    
    # Track player activity
    update_player_activity(room, player_id)
    
    # Validate message length
    if len(message) > 400:
        return {"error": "Message exceeds 400 character limit"}

    # Rate limiting
    current_time = time.time()
    
    # Ensure lock exists
    if room_code not in room_locks:
        room_locks[room_code] = asyncio.Lock()
    
    # CRITICAL: Use lock to prevent state overwrite race conditions
    async with room_locks[room_code]:
        room = rooms[room_code]
        state = room['state']
        
        # Check if in discussion phase
        if state['phase'] != Phase.DISCUSSION:
            return {"error": "Not in discussion phase"}
            
        player_cooldowns = room.get('player_message_cooldowns')
        # Handle legacy rooms that might not have this key
        if player_cooldowns is None:
            player_cooldowns = defaultdict(float)
            room['player_message_cooldowns'] = player_cooldowns
        
        last_message_time = player_cooldowns[player_id]
        if current_time - last_message_time < 0.1:
            return {"error": "You are sending messages too fast"}
        
        # Update last message time
        player_cooldowns[player_id] = current_time
        
        # Process human message
        state = await process_human_message(state, message, player_id)
        rooms[room_code]['state'] = state
    
    # Broadcast to WebSocket clients
    last_msg = state['chat_history'][-1] if state['chat_history'] else {}
    msg_timestamp = last_msg.get('timestamp', current_time)

    await broadcast_to_room(room_code, {
        "type": "message",
        "sender": player_id,
        "message": message,
        "timestamp": msg_timestamp
    })
    
    # Trigger agent decision-making
    asyncio.create_task(trigger_agent_decisions(room_code))
    
    return {"success": True}


@router.post("/api/rooms/{room_code}/vote")
async def cast_vote(room_code: str, vote_data: dict):
    """
    Cast votes from Streamlit client.
    """
    if room_code not in rooms:
        return {"error": "Room not found"}
    
    player_id = vote_data.get('player_id', 'StreamlitUser')
    voted_for = vote_data.get('voted_for')
    
    # Convert single vote to list for consistency
    if not isinstance(voted_for, list):
        voted_for = [voted_for] if voted_for else []
    
    # Ensure lock exists
    if room_code not in room_locks:
        room_locks[room_code] = asyncio.Lock()
    
    should_complete = False
    
    # CRITICAL: Use lock to prevent race conditions with AI voting/timers
    async with room_locks[room_code]:
        room = rooms[room_code]
        state = room['state']
        
        print(f"🗳️ Vote submission from {player_id} in room {room_code}")
        print(f"   Voted for: {voted_for}")
        
        # Check if in voting phase
        if state['phase'] != Phase.VOTING:
            error_msg = f"Not in voting phase (current: {state['phase'].value})"
            print(f"   ❌ {error_msg}")
            return {"error": error_msg}
        
        # Check if already voted
        if player_id in state.get('votes', {}):
            error_msg = "Already voted"
            print(f"   ❌ {error_msg}")
            return {"error": error_msg}
        
        # Validate vote count for multi-human games
        human_players = [p for p in state['players'] if p['role'] == 'human' and not p['eliminated']]
        num_humans = len(human_players)
        
        if num_humans > 1:
            expected_votes = num_humans - 1
            if len(voted_for) != expected_votes:
                error_msg = f"Must vote for exactly {expected_votes} players in multi-human games. You selected {len(voted_for)}."
                print(f"   ❌ {error_msg}")
                return {"error": error_msg}
            
            # Validate: cannot vote for self
            if player_id in voted_for:
                error_msg = "Cannot vote for yourself"
                print(f"   ❌ {error_msg}")
                return {"error": error_msg}
            
            # Validate: all voted players exist and are not eliminated
            for vote in voted_for:
                if not any(p['id'] == vote and not p['eliminated'] for p in state['players']):
                    error_msg = f"Invalid vote target: {vote} (not found or eliminated)"
                    print(f"   ❌ {error_msg}")
                    return {"error": error_msg}
        
        # Track player activity
        update_player_activity(rooms[room_code], player_id)
        
        # Process human vote
        state['votes'][player_id] = voted_for
        rooms[room_code]['state'] = state
        
        print(f"✅ Human vote recorded: {player_id} → {voted_for}")
        
        # Broadcast vote to WebSocket clients
        await broadcast_to_room(room_code, {
            "type": "voted",
            "player": player_id
        })
        
        # Check if all votes are in
        active_player_ids = [p['id'] for p in state['players'] if not p['eliminated']]
        human_player_ids = [p['id'] for p in state['players'] if p['role'] == 'human' and not p['eliminated']]
        
        if num_humans > 1:
            required_votes = len(human_player_ids)
        else:
            required_votes = len(active_player_ids)
        
        if len(state['votes']) >= required_votes:
            print(f"✅ All required votes received, completing voting...")
            should_complete = True
    
    if should_complete:
        try:
            await complete_voting(room_code)
        except Exception as completion_error:
            print(f"❌ Error during vote completion: {type(completion_error).__name__}: {str(completion_error)}")
            import traceback
            traceback.print_exc()
            raise
    
    return {"success": True}


@router.post("/api/rooms/{room_code}/typing")
async def send_typing_status(room_code: str, typing_data: dict):
    """
    Send typing status from Streamlit client.
    """
    if room_code not in rooms:
        return {"error": "Room not found"}
    
    player_id = typing_data.get('player_id', 'StreamlitUser')
    status = typing_data.get('status', 'stop')
    
    # Ensure lock exists
    if room_code not in room_locks:
        room_locks[room_code] = asyncio.Lock()
        
    async with room_locks[room_code]:
        room = rooms[room_code]
        
        if 'typing_players' not in room:
            room['typing_players'] = set()
        
        if status == 'start':
            room['typing_players'].add(player_id)
        else:
            room['typing_players'].discard(player_id)
    
    # Broadcast to WebSocket clients
    await broadcast_to_room(room_code, {
        "type": "typing",
        "player": player_id,
        "status": status
    })
    
    return {"success": True}


@router.post("/api/rooms/{room_code}/heartbeat")
async def player_heartbeat(room_code: str, heartbeat_data: dict):
    """
    Receive heartbeat ping from a player.
    This is used to track player activity and detect disconnections.
    """
    if room_code not in rooms:
        return {"success": False, "error": "Room not found"}
    
    player_id = heartbeat_data.get('player_id', '')
    if not player_id:
        return {"success": False, "error": "player_id required"}
    
    room = rooms[room_code]
    
    # Update heartbeat and activity timestamps
    update_player_heartbeat(room, player_id)
    
    # If room was abandoned and players are coming back, transition to resuming
    room_status = room.get('room_status', '')
    if room_status == 'abandoned':
        # Check if enough players are back
        assigned_humans = get_assigned_humans(room)
        active_count = 0
        current_time = time.time()
        player_heartbeat = room.get('player_heartbeat', {})
        
        for pid in assigned_humans:
            last_hb = player_heartbeat.get(pid, 0)
            if current_time - last_hb < 60:  # Active in last minute
                active_count += 1
        
        if active_count >= 1:  # At least one player is back
            room['room_status'] = 'resuming'
            print(f"🔄 Room {room_code} transitioning from abandoned to resuming ({active_count} players active)")
    
    return {
        "success": True,
        "timestamp": time.time()
    }


@router.get("/start/{room_code}")
async def start_game(room_code: str):
    """
    Reset and start a game in a room.
    """
    if room_code in rooms:
        # Reset room
        state = create_game_for_room(room_code, NUM_AI_PLAYERS)
        rooms[room_code]['state'] = state
        rooms[room_code]['ai_processing_agents'] = set()
        
        # Broadcast reset
        await broadcast_to_room(room_code, {
            "type": "game_reset",
            "message": "Game reset"
        })
        
        # Initialize game
        game_graph = rooms[room_code]['game_graph']
        result = game_graph.initialize_game_node(state)
        state.update(result)
        rooms[room_code]['state'] = state
        
        if 'broadcast_queue' in result:
            for msg in result['broadcast_queue']:
                await broadcast_to_room(room_code, msg)
        
        # Start phases
        asyncio.create_task(run_discussion_phase(room_code))
        
        # Immediately send timer sync
        discussion_duration = rooms[room_code].get('discussion_duration', DISCUSSION_TIME)
        await broadcast_to_room(room_code, {
            "type": "timer_sync",
            "phase": "Discussion",
            "time_remaining": int(discussion_duration)
        })
        
        # Trigger active decision-making for AI responses
        await asyncio.sleep(1)
        asyncio.create_task(trigger_agent_decisions(room_code))
        
        return {"message": "Game started in room"}
    
    return {"message": "Room not found"}


