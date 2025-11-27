import time as _time
import random
import asyncio
import json
from collections import defaultdict
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, status, HTTPException
from jose import jwt, JWTError

from backend.global_state import rooms, room_locks, executor
from backend.config import (
    NUM_AI_PLAYERS, DISCUSSION_TIME, VOTING_TIME
)
from backend.auth import JWT_SECRET_KEY, JWT_ALGORITHM, get_user_by_uuid
from backend.database import async_session_maker
from backend.middleware_utils import websocket_connect_rate_limiter
from backend.services.room_management import (
    get_api_key_for_room, get_connected_humans, update_player_activity, 
    update_player_heartbeat, sync_assigned_and_current_humans,
    get_assigned_humans
)
from backend.services.messaging import broadcast_to_room
from backend.services.game_coordinator import (
    run_discussion_phase, trigger_agent_decisions, complete_voting
)
from backend.langgraph_game import (
    create_game_for_room, create_game_graph_for_room,
    process_human_message, process_human_vote
)
from backend.langgraph_state import Phase

router = APIRouter()

@router.websocket("/ws/{room_code}/{player_id}")
async def websocket_endpoint(websocket: WebSocket, room_code: str, player_id: str):
    """
    WebSocket endpoint for game connections.
    """
    # Rate limit check BEFORE accepting connection
    client_host = websocket.client.host
    if not websocket_connect_rate_limiter.is_allowed(client_host):
        print(f"⛔ WebSocket connection blocked - rate limit exceeded for {client_host}")
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return

    await websocket.accept()
    print(f"🔌 WebSocket accepted for player {player_id} in room {room_code}")
    
    # Try to get authenticated user from token query param
    user_id = None
    mturk_context = None
    try:
        token = websocket.query_params.get('token')
        print(f"🔑 Token received: {'Yes' if token else 'No'}")
        
        if token:
            print(f"🔓 Decoding JWT token...")
            payload = jwt.decode(token, JWT_SECRET_KEY, algorithms=[JWT_ALGORITHM])
            user_uuid = payload.get("sub")
            print(f"🆔 User UUID from token: {user_uuid}")
            
            if user_uuid:
                async with async_session_maker() as db:
                    user = await get_user_by_uuid(db, user_uuid)
                    if user:
                        user_id = str(user.id)
                        print(f"👤 ✅ Authenticated user '{user.user_id}' (ID: {user_id[:8]}...) as {player_id}")
                        
                        # Check if this is an MTurk worker
                        if user.user_id and len(user.user_id) == 14 and user.user_id.startswith('A'):
                            mturk_json = websocket.query_params.get('mturk_context')
                            if mturk_json:
                                try:
                                    mturk_context = json.loads(mturk_json)
                                    print(f"💼 MTurk worker detected: {mturk_context.get('worker_id')}")
                                except:
                                    pass
                    else:
                        print(f"⚠️ User not found in database for UUID: {user_uuid}")
            else:
                print(f"⚠️ No 'sub' field in JWT payload")
        else:
            print(f"ℹ️ No token provided - user playing anonymously")
    except Exception as e:
        print(f"⚠️ Could not authenticate WebSocket user: {e}")
        import traceback
        traceback.print_exc()
    
    # Initialize room if needed
    if room_code not in rooms:
        print(f"⚠️ WebSocket connection to non-existent room: {room_code}")
        print(f"🎮 Creating legacy WebSocket room: {room_code}")
        
        # For legacy WebSocket rooms, use proper number assignment
        # Legacy rooms are now explicitly SINGLE-PLAYER ONLY (1 human + N AI)
        max_humans = 1
        total_players = NUM_AI_PLAYERS + max_humans
        all_numbers = list(range(1, total_players + 1))
        random.shuffle(all_numbers)
        ai_numbers = all_numbers[:NUM_AI_PLAYERS]
        available_numbers = all_numbers[NUM_AI_PLAYERS:]
        ai_player_ids = [f"Player {num}" for num in ai_numbers]
        
        try:
            api_key, api_key_index = get_api_key_for_room()
        except HTTPException as e:
            await websocket.send_json({
                "type": "error",
                "message": f"Failed to create room: {e.detail}"
            })
            await websocket.close()
            return
        
        state = create_game_for_room(room_code, NUM_AI_PLAYERS, ai_player_ids, "english")
        
        try:
            game_graph = create_game_graph_for_room(api_key)
        except Exception as e:
            print(f"⚠️  CRITICAL: Failed to create game graph: {e}")
            import traceback
            traceback.print_exc()
            await websocket.send_json({
                "type": "error",
                "message": "Failed to initialize AI system. Please try again."
            })
            await websocket.close()
            return
        
        rooms[room_code] = {
            'state': state,
            'connections': {},
            'tasks': [],
            'ai_processing_agents': set(),
            'room_name': f"Room {room_code}",
            'max_humans': max_humans,
            'total_players': total_players,
            'room_status': 'in_progress',
            'created_at': _time.time(),
            'creator_id': player_id,
            'player_user_map': {},
            'current_humans': [],
            'assigned_humans': [],
            'connected_humans': [],
            'permanently_left': set(),
            'player_last_activity': {},
            'player_heartbeat': {},
            'available_numbers': available_numbers,
            'human_overflow_counter': 0,
            'discussion_duration': DISCUSSION_TIME,
            'voting_duration': VOTING_TIME,
            'game_graph': game_graph,
            'api_key_index': api_key_index,
            'player_message_cooldowns': defaultdict(float)
        }
        if room_code not in room_locks:
            room_locks[room_code] = asyncio.Lock()
        
        print(f"📝 Legacy WebSocket room created - Topic: {state['topic']}")
    else:
        print(f"✅ WebSocket connecting to existing room: {room_code}")

    # Enforce anonymous user restriction:
    # - Single-player games (max_humans = 1): ALLOWED
    # - Multi-player games (max_humans > 1) with 0% stakes: ALLOWED
    # - Multi-player games (max_humans > 1) with > 0% stakes: BLOCKED
    room_max_humans = rooms[room_code].get('max_humans', 1)
    room_stake_percentage = rooms[room_code].get('stake_percentage', 0)
    
    if room_max_humans > 1 and room_stake_percentage > 0 and not user_id:
        print(f"⛔ Anonymous user attempted to join staked multi-human room {room_code} (max_humans={room_max_humans}, stake={room_stake_percentage}%)")
        await websocket.send_json({
            "type": "error",
            "message": "Login required for staked multi-player games"
        })
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return
    
    # Add connection
    rooms[room_code]['connections'][player_id] = websocket
    print(f"✅ Connection added. Total connections: {len(rooms[room_code]['connections'])}")
    
    # Store MTurk context if available
    if mturk_context:
        if 'mturk_context' not in rooms[room_code]:
            rooms[room_code]['mturk_context'] = {}
        rooms[room_code]['mturk_context'][player_id] = mturk_context
        print(f"💼 ✅ Stored MTurk context for {player_id}: worker={mturk_context.get('worker_id')}")
    
    # Ensure lock exists
    if room_code not in room_locks:
        room_locks[room_code] = asyncio.Lock()
    
    # CRITICAL: Protect player connection setup with lock to prevent race conditions
    async with room_locks[room_code]:
        state = rooms[room_code]['state']
        existing_player = None
        player_id_map = rooms[room_code].get('player_id_map', {})
        numbered_id = player_id_map.get(player_id)
        
        for p in state.get('players', []):
            if p['id'] == player_id or (numbered_id and p['id'] == numbered_id):
                existing_player = p
                break
        
        if not existing_player:
            available_nums = rooms[room_code].get('available_numbers', [])
            if available_nums:
                assigned_number = available_nums.pop(0)
                numbered_player_id = f"Player {assigned_number}"
            else:
                numbered_player_id = player_id
            
            state['players'].append({
                "id": numbered_player_id,
                "role": "human",
                "eliminated": False,
                "personality": None
            })
            
            rooms[room_code]['player_id_map'] = rooms[room_code].get('player_id_map', {})
            rooms[room_code]['player_id_map'][player_id] = numbered_player_id
            
            if user_id:
                rooms[room_code]['player_user_map'][numbered_player_id] = user_id
                print(f"👤 ✅ Mapped {numbered_player_id} (human) -> user {user_id[:8]}...")
            else:
                print(f"⚠️ No user_id to map for {numbered_player_id}")
            
            rooms[room_code]['state'] = state
            print(f"✅ Added human player {numbered_player_id} to game state")
            
            connected_humans = get_connected_humans(rooms[room_code])
            if numbered_player_id not in connected_humans:
                connected_humans.append(numbered_player_id)
                rooms[room_code]['connected_humans'] = connected_humans
                print(f"🔗 Added {numbered_player_id} to connected_humans")
            
            update_player_activity(rooms[room_code], numbered_player_id)
            update_player_heartbeat(rooms[room_code], numbered_player_id)
        else:
            numbered_player_id = existing_player['id']
            rooms[room_code]['player_id_map'] = rooms[room_code].get('player_id_map', {})
            rooms[room_code]['player_id_map'][player_id] = numbered_player_id
            
            connected_humans = get_connected_humans(rooms[room_code])
            if numbered_player_id not in connected_humans:
                connected_humans.append(numbered_player_id)
                rooms[room_code]['connected_humans'] = connected_humans
                print(f"🔗 Added existing player {numbered_player_id} to connected_humans")
            
            update_player_activity(rooms[room_code], numbered_player_id)
            update_player_heartbeat(rooms[room_code], numbered_player_id)
            
            existing_mapping = rooms[room_code]['player_user_map'].get(numbered_player_id)
            
            if existing_mapping:
                print(f"ℹ️ Player {numbered_player_id} already mapped via API -> user {existing_mapping[:8]}...")
                if user_id and user_id != existing_mapping:
                    print(f"⚠️ WebSocket user {user_id[:8]}... differs from API user {existing_mapping[:8]}... - keeping API mapping")
            elif user_id:
                rooms[room_code]['player_user_map'][numbered_player_id] = user_id
                print(f"👤 ✅ Mapped {numbered_player_id} (existing player from API) -> user {user_id[:8]}... via WebSocket")
            else:
                print(f"⚠️ No user_id to map for existing player {numbered_player_id}")
        
        # Game initialization (if needed)
        state = rooms[room_code]['state']
        needs_init = 'initialized' not in rooms[room_code]
        
        if needs_init:
            game_graph = rooms[room_code]['game_graph']
            result = game_graph.initialize_game_node(state)
            
            rooms[room_code]['state'] = state
            rooms[room_code]['initialized'] = True
            
            # Store initialization data for broadcasting outside lock
            broadcast_queue = result.get('broadcast_queue', [])
            discussion_duration = rooms[room_code].get('discussion_duration', DISCUSSION_TIME)
    
    # Broadcast initialization messages (outside lock)
    if needs_init:
        if broadcast_queue:
            for msg in broadcast_queue:
                print(f"📤 Sending initial broadcast: {msg['type']}")
                await broadcast_to_room(room_code, msg)
        
        asyncio.create_task(run_discussion_phase(room_code))
        
        await broadcast_to_room(room_code, {
            "type": "timer_sync",
            "phase": "Discussion",
            "time_remaining": int(discussion_duration)
        })
        
        await asyncio.sleep(1.75)
        asyncio.create_task(trigger_agent_decisions(room_code))
    
    state = rooms[room_code]['state']
    room = rooms[room_code]
    await websocket.send_json({"type": "player_list", "players": [p["id"] for p in state["players"]]})
    await websocket.send_json({"type": "topic", "topic": state["topic"]})
    
    num_human_players = len([p for p in state['players'] if p['role'] == 'human' and not p['eliminated']])
    phase_msg = {
        "type": "phase",
        "phase": state["phase"].value,
        "message": f"Currently in {state['phase'].value}",
        "num_human_players": num_human_players
    }
    if state["phase"].value == "Discussion":
        phase_msg["discussion_duration"] = room.get('discussion_duration', DISCUSSION_TIME)
    elif state["phase"].value == "Voting":
        phase_msg["voting_duration"] = room.get('voting_duration', VOTING_TIME)
    await websocket.send_json(phase_msg)
    
    typing_players = list(state.get('typing_players', set()))
    if typing_players:
        for player in typing_players:
            await websocket.send_json({
                "type": "typing",
                "player": player,
                "status": "start"
            })
    
    if state["phase"].value in ["Discussion", "Voting"] and 'phase_start_time' in room:
        phase_start = room['phase_start_time']
        if state["phase"].value == "Discussion":
            total_duration = room.get('discussion_duration', DISCUSSION_TIME)
        else:
            total_duration = room.get('voting_duration', VOTING_TIME)
        
        elapsed = _time.time() - phase_start
        remaining = max(0, int(total_duration - elapsed))
        
        await websocket.send_json({
            "type": "timer_sync",
            "phase": state["phase"].value,
            "time_remaining": remaining
        })
    
    try:
        while True:
            data = await websocket.receive_json()
            
            if room_code not in rooms:
                print(f"⚠️ Room {room_code} was deleted, closing connection")
                break
            
            if data["type"] == "message":
                message = data["message"]
                print(f"💬 Human message received: {message}")
                
                # Ensure lock exists
                if room_code not in room_locks:
                    room_locks[room_code] = asyncio.Lock()
                
                # CRITICAL: Use lock to prevent race conditions during state updates
                async with room_locks[room_code]:
                    room = rooms[room_code]
                    state = room['state']
                    
                    # Check if in discussion phase
                    if state['phase'] != Phase.DISCUSSION:
                        await websocket.send_json({
                            "type": "error",
                            "message": "Messages only allowed during discussion phase"
                        })
                        continue
                    
                    player_id_map = room.get('player_id_map', {})
                    actual_player_id = player_id_map.get(player_id, player_id)
                    
                    if len(message) > 400:
                        await websocket.send_json({
                            "type": "error",
                            "message": "Message exceeds 400 character limit"
                        })
                        continue

                    current_time = _time.time()
                    player_cooldowns = room.get('player_message_cooldowns')
                    if player_cooldowns is None:
                        player_cooldowns = defaultdict(float)
                        room['player_message_cooldowns'] = player_cooldowns
                    
                    last_message_time = player_cooldowns[actual_player_id]
                    if current_time - last_message_time < 0.1:
                        await websocket.send_json({
                            "type": "error",
                            "message": "You are sending messages too fast"
                        })
                        continue
                    
                    player_cooldowns[actual_player_id] = current_time
                    
                    # Process human message and update state atomically
                    state = await process_human_message(state, message, actual_player_id)
                    rooms[room_code]['state'] = state
                    
                    last_msg = state['chat_history'][-1] if state['chat_history'] else {}
                    msg_timestamp = last_msg.get('timestamp', current_time)
                
                # Broadcast outside lock (async-safe)
                await broadcast_to_room(room_code, {
                    "type": "message",
                    "sender": player_id,
                    "message": message,
                    "timestamp": msg_timestamp
                }, exclude_player=player_id)
                
                asyncio.create_task(trigger_agent_decisions(room_code))
                
            elif data["type"] == "typing":
                status = data["status"]
                await broadcast_to_room(room_code, {
                    "type": "typing",
                    "player": player_id,
                    "status": status
                })
                
            elif data["type"] == "vote":
                voted_for = data["voted"]
                
                # Ensure lock exists
                if room_code not in room_locks:
                    room_locks[room_code] = asyncio.Lock()
                
                should_complete = False
                
                # CRITICAL: Use lock to prevent race conditions during voting
                async with room_locks[room_code]:
                    room = rooms[room_code]
                    state = room['state']
                    
                    player_id_map = room.get('player_id_map', {})
                    actual_player_id = player_id_map.get(player_id, player_id)
                    
                    # Process human vote and update state atomically
                    state = await process_human_vote(state, actual_player_id, voted_for)
                    rooms[room_code]['state'] = state
                    
                    # Check if all votes are in
                    # CRITICAL FIX: Exclude permanently_left players from vote requirement
                    permanently_left = room.get('permanently_left', set())
                    active_players = [p['id'] for p in state['players'] 
                                     if not p['eliminated'] and p['id'] not in permanently_left]
                    
                    print(f"📊 Vote check (WS): {len(state['votes'])}/{len(active_players)} votes (excluding {len(permanently_left)} left players)")
                    
                    if len(state['votes']) >= len(active_players):
                        should_complete = True
                
                # Broadcast outside lock (async-safe)
                await broadcast_to_room(room_code, {
                    "type": "voted",
                    "player": actual_player_id
                })
                
                # Complete voting if all votes received
                if should_complete:
                    await complete_voting(room_code)
    
    except WebSocketDisconnect:
        if room_code in rooms:
            room = rooms[room_code]
            room['connections'].pop(player_id, None)
            print(f"🔌 Player {player_id} disconnected from room {room_code}")
            
            player_id_map = room.get('player_id_map', {})
            actual_player_id = player_id_map.get(player_id, player_id)
            
            connected_humans = get_connected_humans(room)
            if actual_player_id in connected_humans:
                connected_humans.remove(actual_player_id)
                room['connected_humans'] = connected_humans
                print(f"🔌 Removed {actual_player_id} from connected_humans")
            
            if 'player_last_activity' not in room:
                room['player_last_activity'] = {}
            room['player_last_activity'][actual_player_id] = _time.time()
            
            if not room['connections']:
                print(f"⚠️ Room {room_code} has no active connections but keeping it alive for potential rejoin")


