"""
FastAPI main application with LangGraph integration.
Maintains WebSocket compatibility with frontend while using graph-based backend.
"""

import asyncio
import random
import time
from typing import Dict
from concurrent.futures import ThreadPoolExecutor
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
import os
from dotenv import load_dotenv

from .langgraph_game import (
    game_graph, 
    create_game_for_room,
    process_human_message,
    process_human_vote
)
from .langgraph_state import GameState, Phase
from .config import NUM_AI_PLAYERS, DISCUSSION_TIME, VOTING_TIME
import json
import os
import time as _time

load_dotenv()

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Thread pool for running blocking AI operations without blocking the event loop
executor = ThreadPoolExecutor(max_workers=10)

# Room management
rooms: Dict[str, Dict] = {}
# Structure: {
#   room_code: {
#     'state': GameState,
#     'connections': {player_id: WebSocket},
#     'tasks': [],
#     'ai_processing_agents': set(),
#     'ai_lock': asyncio.Lock(),
#     'room_name': str,          # Display name for the room
#     'max_humans': int,          # Maximum human players (1-4)
#     'total_players': int,       # Total players including AI (default 5)
#     'room_status': str,         # 'waiting' | 'in_progress' | 'completed'
#     'created_at': float,        # Timestamp
#     'creator_id': str,          # Creator's player ID
#     'current_humans': List[str] # List of joined human player IDs
#   }
# }

# Room locks for preventing race conditions in AI processing
room_locks: Dict[str, asyncio.Lock] = {}


def generate_room_code() -> str:
    """
    Generate a unique 6-character alphanumeric room code.
    Format: AB12CD (uppercase letters and numbers)
    
    Returns:
        Unique room code
    """
    import string
    chars = string.ascii_uppercase + string.digits
    while True:
        code = ''.join(random.choice(chars) for _ in range(6))
        if code not in rooms:
            return code


async def broadcast_to_room(room_code: str, message: dict, exclude_player: str = None):
    """
    Broadcast a message to all connections in a room.
    Automatically removes stale connections that fail.
    
    Args:
        room_code: Room identifier
        message: Message dictionary to broadcast
        exclude_player: Optional player_id to exclude from broadcast (e.g., message sender)
    """
    if room_code not in rooms:
        return
    
    connections = rooms[room_code]['connections']
    print(f"📡 Broadcasting to {len(connections)} clients: {message.get('type', 'unknown')}")
    
    # Track failed connections to remove after iteration
    failed_connections = []
    
    for player_id, websocket in connections.items():
        if exclude_player and player_id == exclude_player:
            print(f"⏭️  Skipping broadcast to sender: {player_id}")
            continue
        try:
            await websocket.send_json(message)
        except Exception as e:
            print(f"❌ Error broadcasting to {player_id}: {type(e).__name__}: {str(e)}")
            failed_connections.append(player_id)
    
    # Clean up stale connections
    for player_id in failed_connections:
        print(f"🗑️ Removing stale connection: {player_id}")
        rooms[room_code]['connections'].pop(player_id, None)


async def process_broadcast_queue(room_code: str, state: GameState):
    """
    Process and send all messages in the broadcast queue.
    
    Args:
        room_code: Room identifier
        state: Current game state with broadcast_queue
    """
    for message in state.get("broadcast_queue", []):
        await broadcast_to_room(room_code, message)


async def proactive_agent_engagement(room_code: str):
    """
    Periodically check if agents should proactively engage in conversation.
    This prevents long silences and encourages natural conversation flow.
    
    Args:
        room_code: Room identifier
    """
    while room_code in rooms:
        state = rooms[room_code]['state']
        
        # Only during discussion phase
        if state['phase'] != Phase.DISCUSSION:
            break
        
        # Wait for a period before checking (stagger checks to avoid conflicts)
        await asyncio.sleep(random.uniform(8, 15))
        
        if room_code not in rooms:
            break
        
        state = rooms[room_code]['state']
        
        # Check if still in discussion
        if state['phase'] != Phase.DISCUSSION:
            break
        
        # Check if conversation has been quiet (no messages in last 10 seconds)
        last_message_time = state.get('last_message_time', 0)
        time_since_last = time.time() - last_message_time
        
        if time_since_last > 10:
            print(f"💤 Conversation quiet for {time_since_last:.1f}s, triggering proactive engagement")
            asyncio.create_task(trigger_agent_decisions(room_code))


async def run_discussion_phase(room_code: str):
    """
    Run the discussion phase for a room.
    Manages timer and triggers voting phase.
    Also enables proactive agent engagement.
    
    Args:
        room_code: Room identifier
    """
    # Start proactive engagement task
    engagement_task = asyncio.create_task(proactive_agent_engagement(room_code))
    
    await asyncio.sleep(DISCUSSION_TIME)
    
    # Cancel proactive engagement when discussion ends
    engagement_task.cancel()
    
    if room_code not in rooms:
        return
    
    state = rooms[room_code]['state']
    
    # Check if still in discussion phase
    if state['phase'] == Phase.DISCUSSION:
        # Transition to voting
        state['phase'] = Phase.VOTING
        
        # CRITICAL: Clear ALL pending operations to prevent late messages
        state['pending_ai_messages'] = []
        
        # Stop all typing indicators for any AI that might be typing
        ai_players = [p['id'] for p in state['players'] if p['role'] == 'ai']
        for ai_id in ai_players:
            await broadcast_to_room(room_code, {
                "type": "typing",
                "player": ai_id,
                "status": "stop"
            })
        
        state['pending_ai_votes'] = [
            p['id'] for p in state['players']
            if p['role'] == 'ai' and not p['eliminated']
        ]
        state['votes'] = {}
        
        # Save state BEFORE broadcasting to ensure checks see VOTING phase
        rooms[room_code]['state'] = state
        
        # Broadcast phase change
        await broadcast_to_room(room_code, {
            "type": "phase",
            "phase": "Voting",
            "message": "Discussion ended. Time to vote."
        })
        
        print(f"✅ Phase transition complete: DISCUSSION → VOTING in room {room_code}")
        
        # Start voting phase
        asyncio.create_task(run_voting_phase(room_code))
        asyncio.create_task(process_ai_votes(room_code))


async def run_voting_phase(room_code: str):
    """
    Run the voting phase for a room.
    Manages timer and triggers elimination.
    
    Args:
        room_code: Room identifier
    """
    await asyncio.sleep(VOTING_TIME)
    
    if room_code not in rooms:
        return
    
    state = rooms[room_code]['state']
    
    # Check if still in voting phase
    if state['phase'] == Phase.VOTING:
        # Force completion of voting
        await complete_voting(room_code)


async def process_ai_votes(room_code: str):
    """
    Process AI votes asynchronously.
    
    Args:
        room_code: Room identifier
    """
    if room_code not in rooms:
        return
    
    state = rooms[room_code]['state']
    
    while state.get('pending_ai_votes') and state['phase'] == Phase.VOTING:
        # Get next AI voter
        ai_id = state['pending_ai_votes'][0]
        
        # Run single AI vote node in thread pool to avoid blocking
        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(
            executor,
            lambda: game_graph.ai_vote_agent_node(state, ai_id=ai_id)
        )
        
        # Update state - merge votes instead of replacing to preserve human votes
        if 'votes' in result:
            print(f"🤖 AI {ai_id} voting. Before: {state['votes']}")
            state['votes'].update(result['votes'])
            print(f"🤖 AI {ai_id} voted. After: {state['votes']}")
        state['pending_ai_votes'] = result.get('pending_ai_votes', [])
        rooms[room_code]['state'] = state
        
        # Broadcast vote
        if 'broadcast_queue' in result:
            for msg in result['broadcast_queue']:
                await broadcast_to_room(room_code, msg)
        
        # Check if voting complete
        active_players = [p['id'] for p in state['players'] if not p['eliminated']]
        if len(state['votes']) >= len(active_players):
            await complete_voting(room_code)
            break


async def complete_voting(room_code: str):
    """
    Complete the voting phase and process elimination.
    
    Args:
        room_code: Room identifier
    """
    if room_code not in rooms:
        return
    
    state = rooms[room_code]['state']
    
    if state['phase'] != Phase.VOTING:
        return
    
    print(f"🏁 Completing voting for room {room_code}")
    print(f"📊 Final votes before processing: {state.get('votes', {})}")
    
    # Determine suspect (player with most votes) and winner directly; no elimination
    vote_counts: Dict[str, int] = {}
    for _, target in state.get('votes', {}).items():
        if target is None:
            continue
        vote_counts[target] = vote_counts.get(target, 0) + 1
    suspect = None
    if vote_counts:
        max_votes = max(vote_counts.values())
        candidates = [pid for pid, cnt in vote_counts.items() if cnt == max_votes]
        suspect = random.choice(candidates) if len(candidates) > 1 else candidates[0]
    # Default fallback if no votes: choose a random AI
    if not suspect:
        ai_ids = [p['id'] for p in state['players'] if p['role'] == 'ai']
        suspect = random.choice(ai_ids) if ai_ids else None
    suspect_role = None
    for p in state['players']:
        if p['id'] == suspect:
            suspect_role = p['role']
            break
    # Humans win if suspect is actually an AI; otherwise AIs win
    state['selected_suspect'] = suspect
    state['suspect_role'] = suspect_role
    state['winner'] = 'human' if suspect_role == 'ai' else 'ai'
    state['phase'] = Phase.GAME_OVER
    rooms[room_code]['state'] = state
    
    # Broadcast voting result
    await broadcast_to_room(room_code, {
        "type": "voting_result",
        "suspect": suspect,
        "role": suspect_role,
        "vote_counts": vote_counts
    })
    
    # Broadcast game over
    result = game_graph.game_over_node(state)
    state.update(result)
    if 'broadcast_queue' in result:
        for msg in result['broadcast_queue']:
            await broadcast_to_room(room_code, msg)
    rooms[room_code]['state'] = state
    
    # Save stats at end
    await save_session_stats(room_code, state)


async def process_single_ai_message(room_code: str, ai_id: str):
    """
    Process a single AI agent's message asynchronously.
    Allows multiple AI agents to respond simultaneously.
    Note: Should only be called from process_ai_messages() which handles locking.
    
    Args:
        room_code: Room identifier
        ai_id: AI agent identifier
    """
    if room_code not in rooms:
        return
    
    print(f"🤖 Processing message for AI {ai_id} in room {room_code}")
    
    try:
        state = rooms[room_code]['state']
        
        # Check if this AI is still in pending messages
        if ai_id not in state.get('pending_ai_messages', []):
            return
        
        # Run AI chat node for this specific agent in thread pool to avoid blocking event loop
        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(
            executor, 
            lambda: game_graph.ai_chat_agent_node(state, ai_id=ai_id)
        )
        
        if not result:
            return
        
        # DEFENSE LAYER 1: Check phase BEFORE doing anything
        # AI generation can take seconds, phase might have changed
        current_state = rooms[room_code]['state']
        if current_state['phase'] != Phase.DISCUSSION:
            print(f"🚫 AI {ai_id} message blocked - phase is {current_state['phase'].value}, not DISCUSSION")
            # Remove from pending without saving message
            if 'pending_ai_messages' in current_state:
                current_state['pending_ai_messages'] = [p for p in current_state['pending_ai_messages'] if p != ai_id]
                rooms[room_code]['state'] = current_state
            return
        
        # Extract message details before updating state
        if 'ai_sender' not in result or 'ai_message' not in result:
            return
            
        ai_sender = result['ai_sender']
        ai_message = result['ai_message']
        typing_delay = result.get('typing_delay', 1.5)
        
        # DEFENSE LAYER 2: Check phase before typing indicator
        current_state = rooms[room_code]['state']
        if current_state['phase'] != Phase.DISCUSSION:
            print(f"🚫 AI {ai_id} typing blocked - phase changed to {current_state['phase'].value}")
            return
            
        # Broadcast typing start
        await broadcast_to_room(room_code, {
            "type": "typing",
            "player": ai_sender,
            "status": "start"
        })
        
        # Wait for typing delay
        await asyncio.sleep(typing_delay)
        
        # DEFENSE LAYER 3: Check phase AFTER typing delay, BEFORE saving/broadcasting
        current_state = rooms[room_code]['state']
        if current_state['phase'] != Phase.DISCUSSION:
            print(f"🚫 AI {ai_id} message blocked after typing - phase changed to {current_state['phase'].value}")
            # Cancel typing indicator
            await broadcast_to_room(room_code, {
                "type": "typing",
                "player": ai_sender,
                "status": "stop"
            })
            return
        
        # NOW it's safe to update state and broadcast message
        # Update chat history ONLY if still in discussion
        if 'chat_history' in result:
            current_state['chat_history'] = current_state['chat_history'] + result['chat_history']
        if 'last_message_time' in result:
            current_state['last_message_time'] = result['last_message_time']
        if 'pending_ai_messages' in result:
            current_state['pending_ai_messages'] = result['pending_ai_messages']
        
        rooms[room_code]['state'] = current_state
        
        # Broadcast message and typing stop
        await broadcast_to_room(room_code, {
            "type": "message",
            "sender": ai_sender,
            "message": ai_message
        })
        await broadcast_to_room(room_code, {
            "type": "typing",
            "player": ai_sender,
            "status": "stop"
        })
        
        # Handle any other broadcasts from result
        if 'broadcast_queue' in result:
            for msg in result['broadcast_queue']:
                await broadcast_to_room(room_code, msg)
        
        # After AI speaks, give other agents a chance to respond
        # Add small delay to allow message to be processed
        await asyncio.sleep(1.5)
        
        # DEFENSE LAYER 4: Check phase before triggering more AI responses
        current_state = rooms[room_code]['state']
        if current_state['phase'] == Phase.DISCUSSION:
            # Only trigger new responses if still in discussion
            asyncio.create_task(trigger_agent_decisions(room_code, exclude_agents=[ai_id]))
        else:
            print(f"🚫 Not triggering new AI responses - phase is {current_state['phase'].value}")
                
    finally:
        # Remove this AI from processing set
        if room_code in rooms:
            processing_agents = rooms[room_code].get('ai_processing_agents', set())
            processing_agents.discard(ai_id)
            rooms[room_code]['ai_processing_agents'] = processing_agents
            print(f"✅ AI {ai_id} completed message in room {room_code}")


async def trigger_agent_decisions(room_code: str, exclude_agents: list = None):
    """
    Trigger all agents to actively decide whether to respond to the current conversation.
    This enables agents to respond to each other and engage proactively.
    
    Args:
        room_code: Room identifier
        exclude_agents: List of agent IDs to exclude from decision-making (e.g., the one that just spoke)
    """
    if room_code not in rooms:
        return
    
    state = rooms[room_code]['state']
    
    # Only trigger during discussion phase
    if state['phase'] != Phase.DISCUSSION:
        return
    
    # Check if we're still processing previous decisions (cooldown to prevent loops)
    if 'last_decision_trigger_time' not in rooms[room_code]:
        rooms[room_code]['last_decision_trigger_time'] = 0
    
    current_time = time.time()
    time_since_last_trigger = current_time - rooms[room_code]['last_decision_trigger_time']
    
    # Cooldown: don't trigger decisions too frequently (minimum 2 seconds between triggers)
    if time_since_last_trigger < 2.0:
        print(f"⏸️ Skipping agent decision trigger (cooldown: {time_since_last_trigger:.1f}s < 2.0s)")
        return
    
    rooms[room_code]['last_decision_trigger_time'] = current_time
    
    # Get all active AIs, excluding specified ones
    active_ais = [
        p["id"] for p in state["players"]
        if p["role"] == "ai" and not p["eliminated"]
    ]
    
    if exclude_agents:
        active_ais = [ai for ai in active_ais if ai not in exclude_agents]
    
    if not active_ais:
        return
    
    # Run decision-making in thread pool to avoid blocking
    loop = asyncio.get_event_loop()
    
    # Let each AI decide if they should respond
    responding_ais = []
    for ai_id in active_ais:
        try:
            should_respond = await loop.run_in_executor(
                executor,
                lambda aid=ai_id: game_graph._should_agent_respond(state, aid)
            )
            if should_respond:
                responding_ais.append(ai_id)
        except Exception as e:
            print(f"⚠️ Error in decision for {ai_id}: {e}")
    
    # Update pending AI messages
    if responding_ais:
        state['pending_ai_messages'] = responding_ais
        rooms[room_code]['state'] = state
        print(f"🎯 {len(responding_ais)}/{len(active_ais)} agents decided to respond: {responding_ais}")
        
        # Trigger the responses
        asyncio.create_task(process_ai_messages(room_code))
    else:
        print(f"🤐 No agents decided to respond this time")


async def process_ai_messages(room_code: str):
    """
    Trigger all pending AI agents to respond simultaneously.
    Each AI agent runs in its own task for realistic concurrent responses.
    Uses a lock to prevent race conditions and duplicate responses.
    
    Args:
        room_code: Room identifier
    """
    if room_code not in rooms:
        return
    
    # Get or create lock for this room
    if room_code not in room_locks:
        room_locks[room_code] = asyncio.Lock()
    
    # Use lock to prevent concurrent calls from creating duplicate tasks
    async with room_locks[room_code]:
        state = rooms[room_code]['state']
        
        # DEFENSE: Only process AI messages during discussion phase
        if state['phase'] != Phase.DISCUSSION:
            print(f"🚫 Not processing AI messages - phase is {state['phase'].value}, not DISCUSSION")
            return
        
        pending_ais = state.get('pending_ai_messages', []).copy()
        processing_agents = rooms[room_code].get('ai_processing_agents', set())
        
        if not pending_ais:
            return
        
        # Filter out AIs that are already processing
        ais_to_process = [ai_id for ai_id in pending_ais if ai_id not in processing_agents]
        
        if not ais_to_process:
            print(f"⏭️  All pending AIs already processing in room {room_code}")
            return
        
        print(f"🤖 Triggering {len(ais_to_process)} AI agents to respond: {ais_to_process}")
        
        # Mark these AIs as processing BEFORE creating tasks
        for ai_id in ais_to_process:
            processing_agents.add(ai_id)
        rooms[room_code]['ai_processing_agents'] = processing_agents
        
        # Create concurrent tasks for each AI agent
        tasks = [
            asyncio.create_task(process_single_ai_message(room_code, ai_id))
            for ai_id in ais_to_process
        ]
    
    # Wait for all AI responses to complete (outside the lock)
    if tasks:
        await asyncio.gather(*tasks, return_exceptions=True)


async def save_session_stats(room_code: str, state: dict) -> dict:
    """
    Save session statistics to group-chat-stats directory.
    """
    root = os.path.dirname(os.path.dirname(__file__))
    out_dir = os.path.join(root, 'group-chat-stats')
    os.makedirs(out_dir, exist_ok=True)
    vote_counts: Dict[str, int] = {}
    for _, target in state.get('votes', {}).items():
        vote_counts[target] = vote_counts.get(target, 0) + 1
    payload = {
        'room_code': room_code,
        'topic': state.get('topic'),
        'started_at': state.get('round_start_time'),
        'ended_at': _time.time(),
        'players': [{'id': p['id'], 'role': p['role']} for p in state.get('players', [])],
        'chat_history': state.get('chat_history', []),
        'votes': state.get('votes', {}),
        'vote_counts': vote_counts,
        'selected_suspect': state.get('selected_suspect'),
        'suspect_role': state.get('suspect_role'),
        'winner': state.get('winner')
    }
    fname = f"{room_code}-{int(_time.time())}.json"
    path = os.path.join(out_dir, fname)
    with open(path, 'w') as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)
    rooms[room_code]['last_stats_path'] = path
    return payload


@app.get('/api/rooms/{room_code}/stats')
async def get_room_stats(room_code: str):
    if room_code not in rooms or 'last_stats_path' not in rooms[room_code]:
        return {'error': 'No stats for room'}
    with open(rooms[room_code]['last_stats_path'], 'r') as f:
        return json.load(f)


@app.websocket("/ws/{room_code}/{player_id}")
async def websocket_endpoint(websocket: WebSocket, room_code: str, player_id: str):
    """
    WebSocket endpoint for game connections.
    
    Args:
        websocket: WebSocket connection
        room_code: Unique room identifier
        player_id: Player identifier (should be "You" for human)
    """
    await websocket.accept()
    print(f"🔌 WebSocket accepted for player {player_id} in room {room_code}")
    
    # Initialize room if needed
    if room_code not in rooms:
        print(f"🎮 Creating new game room: {room_code}")
        
        # For legacy WebSocket rooms, use proper number assignment
        total_players = NUM_AI_PLAYERS + 1  # 1 human via WebSocket
        all_numbers = list(range(1, total_players + 1))
        random.shuffle(all_numbers)
        ai_numbers = all_numbers[:NUM_AI_PLAYERS]
        available_numbers = all_numbers[NUM_AI_PLAYERS:]
        ai_player_ids = [f"Player {num}" for num in ai_numbers]
        
        state = create_game_for_room(room_code, NUM_AI_PLAYERS, ai_player_ids)
        rooms[room_code] = {
            'state': state,
            'connections': {},
            'tasks': [],
            'ai_processing_agents': set(),
            'room_name': f"Room {room_code}",
            'max_humans': 4,
            'total_players': NUM_AI_PLAYERS + 4,
            'room_status': 'in_progress',  # WebSocket rooms start immediately
            'created_at': time.time(),
            'creator_id': player_id,
            'current_humans': [],
            'available_numbers': available_numbers
        }
        # Initialize lock for this room to prevent race conditions
        if room_code not in room_locks:
            room_locks[room_code] = asyncio.Lock()
        
        print(f"📝 Game state created - Topic: {state['topic']}")
    
    # Add connection BEFORE broadcasting
    rooms[room_code]['connections'][player_id] = websocket
    print(f"✅ Connection added. Total connections: {len(rooms[room_code]['connections'])}")
    
    # If this was a new room, initialize and broadcast
    state = rooms[room_code]['state']
    if 'initialized' not in rooms[room_code]:
        # Initialize game
        result = game_graph.initialize_game_node(state)
        
        # Broadcast initial state
        if 'broadcast_queue' in result:
            for msg in result['broadcast_queue']:
                print(f"📤 Sending initial broadcast: {msg['type']}")
                await broadcast_to_room(room_code, msg)
        
        rooms[room_code]['state'] = state
        rooms[room_code]['initialized'] = True
        
        # Start discussion phase
        asyncio.create_task(run_discussion_phase(room_code))
        
        # Trigger active decision-making for initial AI responses
        # AIs will individually decide if they should start the conversation
        await asyncio.sleep(2)  # Small delay for realism
        asyncio.create_task(trigger_agent_decisions(room_code))
    
    # Send current game state to the newly connected client
    state = rooms[room_code]['state']
    await websocket.send_json({"type": "player_list", "players": [p["id"] for p in state["players"]]})
    await websocket.send_json({"type": "topic", "topic": state["topic"]})
    await websocket.send_json({"type": "phase", "phase": state["phase"].value, "message": f"Currently in {state['phase'].value}"})
    
    # Send chat history
    for msg in state["chat_history"]:
        await websocket.send_json({"type": "message", "sender": msg["sender"], "message": msg["message"]})
    
    try:
        while True:
            data = await websocket.receive_json()
            
            # Check if room still exists after receiving data
            if room_code not in rooms:
                print(f"⚠️ Room {room_code} was deleted, closing connection")
                break
            
            state = rooms[room_code]['state']
            
            if data["type"] == "message":
                # Process human message
                message = data["message"]
                print(f"💬 Human message received: {message}")
                
                # Validate phase - only allow messages during discussion
                if state['phase'] != Phase.DISCUSSION:
                    print(f"⚠️ Message rejected - not in discussion phase (current: {state['phase'].value})")
                    await websocket.send_json({
                        "type": "error",
                        "message": "Messages only allowed during discussion phase"
                    })
                    continue
                
                # Update state
                state = await process_human_message(state, message, player_id)
                rooms[room_code]['state'] = state
                
                # Broadcast message (exclude sender since frontend shows it optimistically)
                print(f"📤 Broadcasting human message to room (excluding sender)")
                await broadcast_to_room(room_code, {
                    "type": "message",
                    "sender": player_id,
                    "message": message
                }, exclude_player=player_id)
                
                # Trigger agent decision-making (they'll decide if they want to respond)
                asyncio.create_task(trigger_agent_decisions(room_code))
                
            elif data["type"] == "typing":
                status = data["status"]
                await broadcast_to_room(room_code, {
                    "type": "typing",
                    "player": player_id,
                    "status": status
                })
                
            elif data["type"] == "vote":
                # Process human vote
                voted_for = data["voted"]
                
                # Update state
                state = await process_human_vote(state, player_id, voted_for)
                rooms[room_code]['state'] = state
                
                # Broadcast vote
                await broadcast_to_room(room_code, {
                    "type": "voted",
                    "player": player_id
                })
                
                # Check if all votes are in
                active_players = [p['id'] for p in state['players'] if not p['eliminated']]
                if len(state['votes']) >= len(active_players):
                    await complete_voting(room_code)
    
    except WebSocketDisconnect:
        # Remove connection
        if room_code in rooms:
            rooms[room_code]['connections'].pop(player_id, None)
            
            # Clean up empty rooms
            if not rooms[room_code]['connections']:
                del rooms[room_code]
                print(f"🗑️ Deleted room {room_code} - no connections left")


@app.get("/start/{room_code}")
async def start_game(room_code: str):
    """
    Reset and start a game in a room.
    
    Args:
        room_code: Room identifier
    
    Returns:
        Status message
    """
    if room_code in rooms:
        # Reset room
        state = create_game_for_room(room_code, NUM_AI_PLAYERS)
        rooms[room_code]['state'] = state
        rooms[room_code]['ai_processing_agents'] = set()  # Reset processing agents
        
        # Broadcast reset
        await broadcast_to_room(room_code, {
            "type": "game_reset",
            "message": "Game reset"
        })
        
        # Initialize game
        result = game_graph.initialize_game_node(state)
        state.update(result)
        rooms[room_code]['state'] = state
        
        if 'broadcast_queue' in result:
            for msg in result['broadcast_queue']:
                await broadcast_to_room(room_code, msg)
        
        # Start phases
        asyncio.create_task(run_discussion_phase(room_code))
        # Trigger active decision-making for AI responses
        await asyncio.sleep(1)  # Small delay
        asyncio.create_task(trigger_agent_decisions(room_code))
        
        return {"message": "Game started in room"}
    
    return {"message": "Room not found"}


@app.get("/config")
async def get_config():
    """
    Get current game configuration.
    
    Returns:
        Configuration dictionary
    """
    return {
        "num_ai_players": NUM_AI_PLAYERS,
        "discussion_time": DISCUSSION_TIME,
        "voting_time": VOTING_TIME
    }


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy"}


# ============================================================================
# Matching Room System API Endpoints
# ============================================================================

@app.post("/api/rooms/create")
async def create_room(room_data: dict):
    """
    Create a new matching room.
    
    Args:
        room_data: Dict with:
            - max_humans: Maximum human players (1-4, default 1)
            - total_players: Total players including AI (default 5)
    
    Returns:
        Room creation response with room_code and room_name
    """
    max_humans = room_data.get('max_humans', 1)
    total_players = room_data.get('total_players', 5)
    
    # Validation
    if not (1 <= max_humans <= 4):
        return {"success": False, "error": "max_humans must be between 1 and 4"}
    
    if total_players < max_humans:
        return {"success": False, "error": "total_players must be >= max_humans"}
    
    if total_players > 12:
        return {"success": False, "error": "total_players cannot exceed 12"}
    
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
    
    # Create initial game state with properly numbered AI players
    state = create_game_for_room(room_code, num_ai_players, ai_player_ids)
    
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
        'current_humans': [],
        'available_numbers': available_numbers  # Numbers reserved for human players
    }
    
    # Initialize lock for this room
    if room_code not in room_locks:
        room_locks[room_code] = asyncio.Lock()
    
    print(f"🎮 Created room {room_code} ({room_name}): {max_humans} humans, {total_players} total")
    
    # Assign a player number for the creator (they'll get it when they join)
    # Return the first available number so they know what to expect
    creator_number = available_numbers[0] if available_numbers else 1
    
    return {
        "success": True,
        "room_code": room_code,
        "room_name": room_name,
        "max_humans": max_humans,
        "total_players": total_players,
        "creator_number": creator_number
    }


@app.get("/api/rooms/list")
async def list_rooms(page: int = 0, per_page: int = 10):
    """
    List available rooms (waiting status only).
    
    Args:
        page: Page number (0-indexed)
        per_page: Rooms per page (default 10)
    
    Returns:
        Paginated list of rooms with metadata
    """
    # Filter rooms with 'waiting' status
    waiting_rooms = [
        {
            'room_code': code,
            'room_name': data['room_name'],
            'current_humans': len(data['current_humans']),
            'max_humans': data['max_humans'],
            'total_players': data['total_players'],
            'room_status': data['room_status'],
            'created_at': data['created_at']
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


@app.get("/api/rooms/{room_code}/info")
async def get_room_info(room_code: str):
    """
    Get room metadata without full game state.
    
    Args:
        room_code: Room identifier
    
    Returns:
        Room metadata including current players and status
    """
    if room_code not in rooms:
        return {"error": "Room not found", "exists": False}
    
    room = rooms[room_code]
    
    return {
        "exists": True,
        "room_code": room_code,
        "room_name": room['room_name'],
        "current_humans": room['current_humans'],
        "max_humans": room['max_humans'],
        "total_players": room['total_players'],
        "room_status": room['room_status'],
        "created_at": room['created_at']
    }


@app.post("/api/rooms/{room_code}/leave")
async def leave_room_endpoint(room_code: str, player_data: dict):
    """
    Handle a player leaving a room.
    - If creator leaves: Terminate the entire room
    - If joiner leaves: Remove them from the room
    
    Args:
        room_code: Room identifier
        player_data: Dict with 'player_id' field
    
    Returns:
        Success status and action taken
    """
    if room_code not in rooms:
        return {"success": False, "error": "Room not found"}
    
    player_id = player_data.get('player_id', '')
    room = rooms[room_code]
    
    # Get room metadata
    current_humans = room.get('current_humans', [])
    room_status = room.get('room_status', '')
    creator_id = room.get('creator_id', '')
    is_creator = (player_id == creator_id) or (len(current_humans) > 0 and player_id == current_humans[0])
    
    print(f"🚪 Player {player_id} leaving room {room_code} (creator: {is_creator})")
    
    # If creator leaves or room is still in waiting status, terminate the room
    if is_creator or room_status == 'waiting':
        print(f"🗑️ Terminating room {room_code} (creator left or in waiting status)")
        
        # Broadcast to any connected clients
        await broadcast_to_room(room_code, {
            "type": "room_terminated",
            "message": "Room has been terminated" if is_creator else "Room was cancelled"
        })
        
        # Clean up room
        if room_code in rooms:
            del rooms[room_code]
        if room_code in room_locks:
            del room_locks[room_code]
        
        return {
            "success": True,
            "action": "terminated",
            "message": "Room terminated"
        }
    
    # Joiner leaving: Remove from room
    if player_id in current_humans:
        current_humans.remove(player_id)
        print(f"👋 Removed {player_id} from room {room_code}. Remaining: {current_humans}")
    
    # Remove from game state
    state = room['state']
    state['players'] = [p for p in state['players'] if p['id'] != player_id]
    
    # Update available numbers (add back the player's number)
    if 'Player ' in player_id:
        try:
            player_num = int(player_id.split('Player ')[1])
            available_nums = room.get('available_numbers', [])
            if player_num not in available_nums:
                available_nums.append(player_num)
                room['available_numbers'] = available_nums
        except:
            pass
    
    # If room becomes empty, delete it
    if len(current_humans) == 0:
        print(f"🗑️ Room {room_code} now empty, deleting")
        if room_code in rooms:
            del rooms[room_code]
        if room_code in room_locks:
            del room_locks[room_code]
        
        return {
            "success": True,
            "action": "deleted",
            "message": "Room deleted (empty)"
        }
    
    return {
        "success": True,
        "action": "removed",
        "message": f"Player removed from room. {len(current_humans)} players remaining"
    }


# ============================================================================
# REST API Endpoints for Streamlit Frontend
# ============================================================================

@app.get("/api/rooms/{room_code}/state")
async def get_room_state(room_code: str, player_id: str = "StreamlitUser"):
    """
    Get the current state of a room for polling-based clients (Streamlit).
    
    Args:
        room_code: Room identifier
        player_id: Player identifier (query parameter)
    
    Returns:
        Complete game state including phase, round, topic, players, chat, timer
    """
    if room_code not in rooms:
        return {
            "error": "Room not found",
            "exists": False
        }
    
    state = rooms[room_code]['state']
    
    # Calculate remaining time based on phase
    timer = 0
    if state['phase'] == Phase.DISCUSSION:
        timer = DISCUSSION_TIME  # Simplified, actual timer managed by frontend
    elif state['phase'] == Phase.VOTING:
        timer = VOTING_TIME
    
    return {
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
        "chat_history": state['chat_history'],
        "votes": state.get('votes', {}),
        "winner": state.get('winner'),
        "selected_suspect": state.get('selected_suspect'),
        "suspect_role": state.get('suspect_role'),
        "current_player_id": player_id,
        "typing": list(state.get('typing_players', set()))
    }


@app.post("/api/rooms/{room_code}/join")
async def join_room(room_code: str, player_data: dict):
    """
    Join a room for Streamlit client (with matching room system support).
    Player names are auto-assigned as random numbers.
    
    Args:
        room_code: Room identifier
        player_data: Dict (player_id ignored, auto-assigned)
    
    Returns:
        Room status and initial game state with assigned player_id
    """
    
    # Check if room exists
    if room_code not in rooms:
        # Legacy behavior: Create room if doesn't exist (for old room codes)
        # For legacy rooms, assign random player numbers too
        total_players = NUM_AI_PLAYERS + 1
        all_numbers = list(range(1, total_players + 1))
        random.shuffle(all_numbers)
        human_number = all_numbers[0]
        player_id = f"Player {human_number}"
        
        # Assign remaining numbers to AI players
        ai_numbers = all_numbers[1:]
        ai_player_ids = [f"Player {num}" for num in ai_numbers]
        
        # Create game state with properly numbered AI players
        state = create_game_for_room(room_code, NUM_AI_PLAYERS, ai_player_ids)
        
        rooms[room_code] = {
            'state': state,
            'connections': {},
            'tasks': [],
            'ai_processing_agents': set(),
            'room_name': f"Room {room_code}",
            'max_humans': 4,
            'total_players': total_players,
            'room_status': 'waiting',
            'created_at': time.time(),
            'creator_id': player_id,
            'current_humans': [],
            'available_numbers': []  # All assigned for legacy rooms
        }
        # Initialize lock for this room to prevent race conditions
        if room_code not in room_locks:
            room_locks[room_code] = asyncio.Lock()
        
        # Initialize game
        result = game_graph.initialize_game_node(state)
        state.update(result)
        rooms[room_code]['state'] = state
        
        # Start phases
        asyncio.create_task(run_discussion_phase(room_code))
        # Trigger active decision-making for AI responses
        await asyncio.sleep(1)  # Small delay
        asyncio.create_task(trigger_agent_decisions(room_code))
    
    room = rooms[room_code]
    
    # Check if room is in waiting status (for matching rooms)
    if room.get('room_status') == 'in_progress':
        return {"success": False, "error": "Room already in progress"}
    
    if room.get('room_status') == 'completed':
        return {"success": False, "error": "Room game completed"}
    
    # Check capacity
    max_humans = room.get('max_humans', 4)
    current_humans = room.get('current_humans', [])
    
    if len(current_humans) >= max_humans:
        return {"success": False, "error": f"Room full ({max_humans} humans max)"}
    
    # Get state
    state = room['state']
    
    # Assign a random player number from available numbers
    available_numbers = room.get('available_numbers', [])
    if not available_numbers:
        # Fallback: generate a random number if somehow we run out
        player_number = random.randint(100, 999)
        player_id = f"Player {player_number}"
    else:
        # Pop a random number from available
        player_number = available_numbers.pop(0)
        player_id = f"Player {player_number}"
    
    # Add player to current_humans list
    room['current_humans'].append(player_id)
    
    # If this is the first human to join, mark as creator
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
    
    print(f"👤 Player {player_id} joined room {room_code} ({len(room['current_humans'])}/{max_humans})")
    
    # Check if room is ready to start
    can_start = len(room['current_humans']) >= max_humans
    
    if can_start:
        # Update room status to in_progress
        room['room_status'] = 'in_progress'
        
        print(f"🎮 Starting game in room {room_code} with {len(room['current_humans'])} humans")
        
        # Initialize game if not already initialized
        if 'initialized' not in room:
            result = game_graph.initialize_game_node(state)
            state.update(result)
            rooms[room_code]['state'] = state
            rooms[room_code]['initialized'] = True
            
            # Broadcast initial state to any connected clients
            if 'broadcast_queue' in result:
                for msg in result['broadcast_queue']:
                    await broadcast_to_room(room_code, msg)
            
            # Start phases
            asyncio.create_task(run_discussion_phase(room_code))
            # Trigger active decision-making for AI responses
            await asyncio.sleep(1)  # Small delay
            asyncio.create_task(trigger_agent_decisions(room_code))
    
    return {
        "success": True,
        "message": f"Joined room {room_code}",
        "player_id": player_id,
        "can_start": can_start,
        "waiting": not can_start,
        "current_humans": len(room['current_humans']),
        "max_humans": max_humans
    }


@app.post("/api/rooms/{room_code}/message")
async def send_message(room_code: str, message_data: dict):
    """
    Send a chat message from Streamlit client.
    
    Args:
        room_code: Room identifier
        message_data: Dict with 'player_id' and 'message' fields
    
    Returns:
        Success status
    """
    if room_code not in rooms:
        return {"error": "Room not found"}
    
    player_id = message_data.get('player_id', 'StreamlitUser')
    message = message_data.get('message', '')
    
    if not message.strip():
        return {"error": "Empty message"}
    
    state = rooms[room_code]['state']
    
    # Check if in discussion phase
    if state['phase'] != Phase.DISCUSSION:
        return {"error": "Not in discussion phase"}
    
    # Process human message
    state = await process_human_message(state, message, player_id)
    rooms[room_code]['state'] = state
    
    # Broadcast to WebSocket clients
    await broadcast_to_room(room_code, {
        "type": "message",
        "sender": player_id,
        "message": message
    })
    
    # Trigger agent decision-making (they'll decide if they want to respond)
    asyncio.create_task(trigger_agent_decisions(room_code))
    
    return {"success": True}


@app.post("/api/rooms/{room_code}/vote")
async def cast_vote(room_code: str, vote_data: dict):
    """
    Cast a vote from Streamlit client.
    
    Args:
        room_code: Room identifier
        vote_data: Dict with 'player_id' and 'voted_for' fields
    
    Returns:
        Success status
    """
    if room_code not in rooms:
        return {"error": "Room not found"}
    
    player_id = vote_data.get('player_id', 'StreamlitUser')
    voted_for = vote_data.get('voted_for')
    
    state = rooms[room_code]['state']
    
    # Check if in voting phase
    if state['phase'] != Phase.VOTING:
        return {"error": "Not in voting phase"}
    
    # Check if already voted (enforce single vote per player)
    if player_id in state.get('votes', {}):
        return {"error": "Already voted"}
    
    # Process human vote - directly update votes dict to avoid race conditions with AI voting
    state['votes'][player_id] = voted_for
    rooms[room_code]['state'] = state
    
    print(f"✅ Human vote recorded: {player_id} → {voted_for}")
    print(f"📊 Current votes after human: {state.get('votes', {})}")
    
    # Broadcast vote to WebSocket clients
    await broadcast_to_room(room_code, {
        "type": "voted",
        "player": player_id
    })
    
    # Check if all votes are in
    active_players = [p['id'] for p in state['players'] if not p['eliminated']]
    if len(state['votes']) >= len(active_players):
        await complete_voting(room_code)
    
    return {"success": True}


@app.post("/api/rooms/{room_code}/typing")
async def send_typing_status(room_code: str, typing_data: dict):
    """
    Send typing status from Streamlit client.
    
    Args:
        room_code: Room identifier
        typing_data: Dict with 'player_id' and 'status' ('start' or 'stop') fields
    
    Returns:
        Success status
    """
    if room_code not in rooms:
        return {"error": "Room not found"}
    
    player_id = typing_data.get('player_id', 'StreamlitUser')
    status = typing_data.get('status', 'stop')
    
    state = rooms[room_code]['state']
    
    # Update typing players set
    if 'typing_players' not in state:
        state['typing_players'] = set()
    
    if status == 'start':
        state['typing_players'].add(player_id)
    else:
        state['typing_players'].discard(player_id)
    
    # Broadcast to WebSocket clients
    await broadcast_to_room(room_code, {
        "type": "typing",
        "player": player_id,
        "status": status
    })
    
    return {"success": True}
