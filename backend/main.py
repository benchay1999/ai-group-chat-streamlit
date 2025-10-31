"""
FastAPI main application with LangGraph integration.
Maintains WebSocket compatibility with frontend while using graph-based backend.
"""

import asyncio
import random
import re
import time
from typing import Dict, List, Optional
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Depends, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import os
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, desc
import uuid as uuid_lib

from .langgraph_game import (
    game_graph, 
    create_game_for_room,
    process_human_message,
    process_human_vote
)
from .langgraph_state import GameState, Phase
from .config import NUM_AI_PLAYERS, DISCUSSION_TIME, VOTING_TIME
from .database import (
    init_db, close_db, get_async_session, 
    User, Session as DBSession, UserRole, PaymentStatus
)
from .auth import (
    hash_password, authenticate_user, create_access_token,
    get_current_user, get_current_user_optional, require_admin,
    register_or_login_mturk_worker
)
from .completion_keys import (
    generate_completion_key, decode_completion_key, extract_session_info
)
import json
import os
import time as _time
from collections import defaultdict
from fastapi import Request

# Import robust environment configuration
# This module handles .env loading with explicit path resolution
from . import env_config

app = FastAPI(title="AI Group Chat API", version="2.0.0")

# CORS Configuration - Production-safe
# Get allowed origins from environment variable, default to localhost for development
allowed_origins_str = os.getenv('CORS_ALLOWED_ORIGINS', 'http://localhost:5173,http://localhost:3000')
allowed_origins = [origin.strip() for origin in allowed_origins_str.split(',')]

# In production, MTURK_ENVIRONMENT should be set, and we should restrict CORS
if os.getenv('MTURK_ENVIRONMENT') == 'production':
    # In production, only allow specified domains (never use "*")
    print(f"🔒 CORS configured for production with origins: {allowed_origins}")
else:
    # In development/sandbox, allow localhost origins
    print(f"🔓 CORS configured for development with origins: {allowed_origins}")

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["*"],  # Allow all headers to be exposed
)


# ============================================================================
# Rate Limiting Configuration
# ============================================================================

class SimpleRateLimiter:
    """Simple in-memory rate limiter for API endpoints."""
    
    def __init__(self, max_requests: int, window_seconds: int):
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self.requests = defaultdict(list)
    
    def is_allowed(self, key: str) -> bool:
        """Check if request is allowed based on rate limit."""
        now = _time.time()
        
        # Clean old requests outside the window
        self.requests[key] = [
            req_time for req_time in self.requests[key]
            if now - req_time < self.window_seconds
        ]
        
        # Check if under limit
        if len(self.requests[key]) >= self.max_requests:
            return False
        
        # Add current request
        self.requests[key].append(now)
        return True
    
    def cleanup_old_entries(self):
        """Periodically cleanup old entries to prevent memory leak."""
        now = _time.time()
        keys_to_delete = []
        
        for key, timestamps in self.requests.items():
            # Remove timestamps outside window
            self.requests[key] = [
                ts for ts in timestamps
                if now - ts < self.window_seconds
            ]
            # Mark empty entries for deletion
            if not self.requests[key]:
                keys_to_delete.append(key)
        
        for key in keys_to_delete:
            del self.requests[key]

# Rate limiter for MTurk registration: 10 requests per minute per IP
mturk_rate_limiter = SimpleRateLimiter(max_requests=10, window_seconds=60)


# ============================================================================
# Application Lifecycle Events
# ============================================================================

@app.on_event("startup")
async def startup_event():
    """Initialize database and MTurk client on application startup."""
    await init_db()
    
    # Initialize MTurk client to verify credentials and show configuration
    try:
        from .mturk_api import get_mturk_client
        client = get_mturk_client()
        print(f"💰 Base pay: ${client.base_pay}, Max bonus: ${os.getenv('MTURK_MAX_BONUS', '0.05')}")
    except Exception as e:
        print(f"⚠️  MTurk client initialization failed: {e}")
        print("   MTurk features will not be available until credentials are configured.")
    
    # Start cashout monitor background task
    try:
        from .cashout_monitor import start_cashout_monitor
        await start_cashout_monitor()
    except Exception as e:
        print(f"⚠️  Cashout monitor initialization failed: {e}")
    
    # Configuration validation already done by env_config module at import time
    # Additional startup validation
    config_status = env_config.get_config_status()
    if not config_status['cashout_hit_id_configured']:
        print("⚠️  CASHOUT SYSTEM NOT CONFIGURED - Cashout requests will fail!")
    
    print("🚀 Application started successfully")


@app.on_event("shutdown")
async def shutdown_event():
    """Close database connections and stop background tasks on application shutdown."""
    # Stop cashout monitor
    try:
        from .cashout_monitor import stop_cashout_monitor
        await stop_cashout_monitor()
    except Exception as e:
        print(f"⚠️  Error stopping cashout monitor: {e}")
    
    await close_db()
    print("👋 Application shut down gracefully")


# ============================================================================
# Pydantic Models for API Requests/Responses
# ============================================================================

class RegisterRequest(BaseModel):
    user_id: str
    password: str
    
class LoginRequest(BaseModel):
    user_id: str
    password: str

class LoginResponse(BaseModel):
    access_token: str
    token_type: str
    user_id: str
    role: str

class UserResponse(BaseModel):
    id: str
    user_id: str
    role: str
    created_at: str

class ClaimKeyRequest(BaseModel):
    completion_key: str

class SessionResponse(BaseModel):
    id: str
    room_code: str
    completion_key: str
    language: str
    total_players: int
    num_human_players: int
    discussion_duration: int
    voting_duration: int
    completed_at: str
    payment_status: str
    payment_amount: Optional[float]
    claimed_at: Optional[str]
    stats_file_path: str

class MTurkRegisterRequest(BaseModel):
    worker_id: str
    assignment_id: str
    hit_id: str

class MTurkPaymentRequest(BaseModel):
    session_id: str


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
    # Get room-specific discussion time (fallback to global config)
    discussion_time = rooms[room_code].get('discussion_duration', DISCUSSION_TIME)
    print(f"⏱️ Starting discussion phase for room {room_code}: {discussion_time} seconds")
    
    # Start proactive engagement task
    engagement_task = asyncio.create_task(proactive_agent_engagement(room_code))
    
    await asyncio.sleep(discussion_time)
    print(f"⏱️ Discussion time ({discussion_time}s) elapsed for room {room_code}, transitioning to voting")
    
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
        
        # Broadcast phase change with voting duration
        voting_duration = rooms[room_code].get('voting_duration', VOTING_TIME)
        await broadcast_to_room(room_code, {
            "type": "phase",
            "phase": "Voting",
            "message": "Discussion ended. Time to vote.",
            "voting_duration": voting_duration
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
    # Get room-specific voting time (fallback to global config)
    voting_time = rooms[room_code].get('voting_duration', VOTING_TIME)
    print(f"🗳️ Starting voting phase for room {room_code}: {voting_time} seconds")
    
    await asyncio.sleep(voting_time)
    print(f"🗳️ Voting time ({voting_time}s) elapsed for room {room_code}, completing game")
    
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
    # Humans win if suspect is actually a human (most human-like); otherwise AIs win
    state['selected_suspect'] = suspect
    state['suspect_role'] = suspect_role
    state['winner'] = 'human' if suspect_role == 'human' else 'ai'
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


def chunk_message(message: str, max_chunks: int = 4) -> List[str]:
    """
    Split a message into 2-4 chunks based on commas and sentence boundaries.
    Simulates human-like incremental typing by removing commas and keeping sentence endings.
    Respects quoted text - doesn't split inside quotes.
    
    Args:
        message: Full message text to chunk
        max_chunks: Maximum number of chunks (default 4)
    
    Returns:
        List of message chunks (commas removed, sentence punctuation preserved)
    
    Example:
        "yes, I think so. That makes sense!" → ["yes", "I think so.", "That makes sense!"]
        'He said "stop." Then left.' → ['He said "stop."', 'Then left.']
    """
    # Handle empty or whitespace-only messages
    if not message or not message.strip():
        return [message]
    
    # If message is very short, don't chunk it
    if len(message) < 20:
        return [message]
    
    # Find split points that are NOT inside quotes
    def find_split_points(text):
        """Find positions where we can split (sentence endings and commas outside quotes)"""
        split_points = []
        in_double_quote = False
        in_single_quote = False
        
        for i, char in enumerate(text):
            # Track quote state
            if char == '"' and (i == 0 or text[i-1] != '\\'):
                in_double_quote = not in_double_quote
            elif char == "'" and (i == 0 or text[i-1] != '\\'):
                in_single_quote = not in_single_quote
            
            # Only split at punctuation outside quotes
            if not in_double_quote and not in_single_quote:
                if char in '.!?,':
                    # Record split point with punctuation type
                    split_points.append((i, char))
        
        return split_points
    
    split_points = find_split_points(message)
    
    # If no split points found, return original
    if not split_points:
        return [message]
    
    # Create chunks from split points
    chunks = []
    start = 0
    
    for pos, punct in split_points:
        # Extract text up to and including the punctuation
        chunk_text = message[start:pos+1].strip()
        
        if chunk_text:
            # Remove commas to make chunks more natural
            # Keep sentence-ending punctuation (. ! ?)
            if punct == ',':
                chunk_text = chunk_text[:-1].strip()  # Remove trailing comma
            
            if chunk_text:  # Only add non-empty chunks
                chunks.append(chunk_text)
        
        start = pos + 1
    
    # Add any remaining text after the last split point
    if start < len(message):
        remaining = message[start:].strip()
        if remaining:
            chunks.append(remaining)
    
    # If we have no chunks, return original
    if not chunks:
        return [message]
    
    # Limit to max_chunks by combining adjacent chunks if needed
    if len(chunks) > max_chunks:
        combined = []
        items_per_chunk = len(chunks) / max_chunks
        
        for chunk_idx in range(max_chunks):
            start_idx = int(chunk_idx * items_per_chunk)
            end_idx = int((chunk_idx + 1) * items_per_chunk) if chunk_idx < max_chunks - 1 else len(chunks)
            combined_text = ' '.join(chunks[start_idx:end_idx])
            if combined_text:
                combined.append(combined_text)
        
        chunks = combined
    
    # Ensure we have at least 2 chunks for longer messages
    if len(chunks) == 1 and len(message) > 40:
        # Try to split roughly in half at a word boundary
        mid = len(message) // 2
        # Find nearest space after midpoint
        space_pos = message.find(' ', mid)
        if space_pos == -1:  # No space after mid, try before
            space_pos = message.rfind(' ', 0, mid)
        if space_pos > 0:
            chunks = [message[:space_pos].strip(), message[space_pos+1:].strip()]
    
    # Final filter: ensure minimum of 2 chunks for meaningful chunking
    if len(chunks) < 2:
        return [message]
    
    return chunks


async def process_single_ai_message(room_code: str, ai_id: str):
    """
    Process a single AI agent's message asynchronously.
    Allows multiple AI agents to respond simultaneously.
    Implements chunk-based message sending for human-like typing behavior.
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
        
        # Randomly decide whether to chunk message (30% probability)
        should_chunk = random.random() < 0.3
        
        if should_chunk:
            # Split message into chunks for human-like typing
            chunks = chunk_message(ai_message, max_chunks=4)
            print(f"📝 AI {ai_id} message split into {len(chunks)} chunks: {chunks}")
        else:
            # Send as single complete message (70% of the time)
            chunks = [ai_message]
            print(f"📝 AI {ai_id} sending complete message (no chunking)")
        
        # Update pending_ai_messages to remove this AI
        current_state = rooms[room_code]['state']
        if 'pending_ai_messages' in result:
            current_state['pending_ai_messages'] = result['pending_ai_messages']
        # CRITICAL: Persist state update immediately to prevent duplicate processing
        rooms[room_code]['state'] = current_state
        
        # Define typing speed (300 chars/minute = 5 chars/sec)
        typing_speed_chars_per_sec = 290 / 60  # 5 characters per second
        
        # DEFENSE: Check phase before starting
        current_state = rooms[room_code]['state']
        if current_state['phase'] != Phase.DISCUSSION:
            print(f"🚫 AI {ai_id} blocked - phase is {current_state['phase'].value}")
            return
        
        # Show typing indicator before sending chunks
        await broadcast_to_room(room_code, {
            "type": "typing",
            "player": ai_sender,
            "status": "start"
        })
        
        # Send each chunk with individual typing delays
        for chunk_idx, chunk in enumerate(chunks):
            # DEFENSE: Check phase before each chunk
            current_state = rooms[room_code]['state']
            if current_state['phase'] != Phase.DISCUSSION:
                print(f"🚫 AI {ai_id} chunk {chunk_idx+1}/{len(chunks)} blocked - phase changed to {current_state['phase'].value}")
                # Stop typing indicator
                await broadcast_to_room(room_code, {
                    "type": "typing",
                    "player": ai_sender,
                    "status": "stop"
                })
                return
            
            # Add thinking/reaction delay before each utterance
            # Short utterances (<=3 words) get 0.2s delay, longer ones get 1s
            word_count = len(chunk.split())
            thinking_delay = 0.2 if word_count <= 3 else 1.0
            print(f"💭 AI {ai_id} thinking before chunk {chunk_idx+1}/{len(chunks)} ({word_count} words, {thinking_delay}s delay)")
            await asyncio.sleep(thinking_delay)
            
            # DEFENSE: Check room and phase after thinking delay
            if room_code not in rooms:
                print(f"🚫 AI {ai_id} chunk {chunk_idx+1}/{len(chunks)} blocked - room deleted during thinking")
                return
            
            current_state = rooms[room_code]['state']
            if current_state['phase'] != Phase.DISCUSSION:
                print(f"🚫 AI {ai_id} chunk {chunk_idx+1}/{len(chunks)} blocked after thinking - phase changed to {current_state['phase'].value}")
                # Stop typing indicator
                await broadcast_to_room(room_code, {
                    "type": "typing",
                    "player": ai_sender,
                    "status": "stop"
                })
                return
            
            # Calculate typing delay for this chunk (250 chars/min = ~4.17 chars/sec)
            chunk_typing_delay = len(chunk) / typing_speed_chars_per_sec
            # Add variance for realism
            chunk_typing_delay = chunk_typing_delay * random.uniform(0.8, 1.2)
            
            print(f"⌨️  AI {ai_id} typing chunk {chunk_idx+1}/{len(chunks)} ({len(chunk)} chars, {chunk_typing_delay:.1f}s delay)")
            
            # Wait for typing delay (typing indicator already shown)
            await asyncio.sleep(chunk_typing_delay)
            
            # DEFENSE: Check room still exists after typing delay
            if room_code not in rooms:
                print(f"🚫 AI {ai_id} chunk {chunk_idx+1}/{len(chunks)} blocked - room deleted during typing")
                return
            
            # DEFENSE: Check phase after typing delay
            current_state = rooms[room_code]['state']
            if current_state['phase'] != Phase.DISCUSSION:
                print(f"🚫 AI {ai_id} chunk {chunk_idx+1}/{len(chunks)} blocked after typing - phase changed to {current_state['phase'].value}")
                # Stop typing indicator
                await broadcast_to_room(room_code, {
                    "type": "typing",
                    "player": ai_sender,
                    "status": "stop"
                })
                return
            
            # Create chat message for this chunk
            chat_msg = {
                "sender": ai_sender,
                "message": chunk,
                "timestamp": time.time()
            }
            
            # Add to chat history
            current_state['chat_history'].append(chat_msg)
            current_state['last_message_time'] = time.time()
            rooms[room_code]['state'] = current_state
            
            # Broadcast chunk
            await broadcast_to_room(room_code, {
                "type": "message",
                "sender": ai_sender,
                "message": chunk
            })
            
            # Small pause between chunks (0.3-0.5s) if not the last chunk
            # Simulates time to press "enter" and start next message
            if chunk_idx < len(chunks) - 1:
                await asyncio.sleep(random.uniform(0.3, 0.5))
                
                # DEFENSE: Check room still exists after inter-chunk sleep
                if room_code not in rooms:
                    print(f"🚫 AI {ai_id} blocked after inter-chunk pause - room deleted")
                    # Stop typing indicator
                    await broadcast_to_room(room_code, {
                        "type": "typing",
                        "player": ai_sender,
                        "status": "stop"
                    })
                    return
        
        # Stop typing indicator after all chunks sent
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
        await asyncio.sleep(1.25)
        
        # DEFENSE: Check room still exists after final sleep
        if room_code not in rooms:
            print(f"🚫 AI {ai_id} blocked after final delay - room deleted")
            return
        
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


async def save_session_stats(room_code: str, state: dict, current_user: Optional[User] = None) -> dict:
    """
    Save session statistics to both group-chat-stats directory and PostgreSQL database.
    Generates a completion key for Mechanical Turk compensation tracking.
    
    Args:
        room_code: Room identifier
        state: Game state dictionary
        current_user: Optional authenticated user (automatically associated with session)
    
    Returns:
        Dictionary with session stats including completion_key
    """
    root = os.path.dirname(os.path.dirname(__file__))
    out_dir = os.path.join(root, 'group-chat-stats')
    os.makedirs(out_dir, exist_ok=True)
    
    # Calculate vote counts
    vote_counts: Dict[str, int] = {}
    for _, target in state.get('votes', {}).items():
        vote_counts[target] = vote_counts.get(target, 0) + 1
    
    # Prepare stats payload for JSON file
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
    
    # Save to JSON file
    fname = f"{room_code}-{int(_time.time())}.json"
    path = os.path.join(out_dir, fname)
    with open(path, 'w') as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)
    rooms[room_code]['last_stats_path'] = path
    
    # Extract session metadata
    room_data = rooms.get(room_code, {})
    language = state.get('language', 'english')
    total_players = room_data.get('total_players', len(state.get('players', [])))
    num_humans = len([p for p in state.get('players', []) if p.get('role') == 'human'])
    discussion_duration = room_data.get('discussion_duration', DISCUSSION_TIME)
    voting_duration = room_data.get('voting_duration', VOTING_TIME)
    completed_at = payload['ended_at']
    
    # Generate session UUID
    session_id = uuid_lib.uuid4()
    
    # Generate completion key
    completion_key = generate_completion_key(
        session_id=str(session_id),
        room_code=room_code,
        language=language,
        total_players=total_players,
        num_humans=num_humans,
        discussion_duration=discussion_duration,
        voting_duration=voting_duration,
        completed_at=completed_at
    )
    
    # Calculate token usage and costs
    from .pricing import calculate_cost
    from .langgraph_game import game_graph
    from .database import AIAgentUsage
    
    total_input_tokens = state.get('total_input_tokens', 0)
    total_output_tokens = state.get('total_output_tokens', 0)
    model_name = game_graph.model_name
    total_cost = calculate_cost(total_input_tokens, total_output_tokens, model_name)
    agent_token_usage = state.get('agent_token_usage', {})
    
    print(f"📊 Total token usage: {total_input_tokens} input, {total_output_tokens} output")
    print(f"💰 Total cost: ${total_cost:.6f} (model: {model_name})")
    
    # Calculate earnings based on performance
    from .earnings import calculate_earnings
    
    # Will be set if current_user is in the game (for legacy session data compatibility)
    calculated_earnings_value = None
    
    # Save to PostgreSQL
    try:
        from .database import async_session_maker
        from .config import GEMS_PER_DOLLAR
        from sqlalchemy import select as sql_select
        import traceback
        
        async with async_session_maker() as db:
            # IDEMPOTENCY CHECK: Check if this session already exists
            # Use room_code + completion timestamp as unique identifier
            timestamp = int(payload['ended_at'])
            existing_check = await db.execute(
                sql_select(DBSession).where(
                    DBSession.room_code == room_code,
                    DBSession.stats_file_path == path
                )
            )
            existing_session = existing_check.scalar_one_or_none()
            
            if existing_session:
                print(f"⚠️ Session for room {room_code} already exists (ID: {existing_session.id}), skipping duplicate save")
                return {
                    'session_id': str(existing_session.id),
                    'completion_key': existing_session.completion_key,
                    'already_existed': True
                }
            
            # Credit gems to ALL authenticated human players in the game
            player_user_map = room_data.get('player_user_map', {})
            print(f"💎 Starting gem credit process for {len(player_user_map)} mapped players")
            
            # Track successfully credited players for session data
            credited_players = []
            
            # Process each human player
            for player in state.get('players', []):
                if player.get('role') != 'human':
                    continue
                
                player_id = player['id']
                mapped_user_id_str = player_user_map.get(player_id)
                
                # Skip unauthenticated players
                if not mapped_user_id_str:
                    print(f"⚠️ Player {player_id} is not authenticated, skipping gem credit")
                    continue
                
                # Calculate this player's earnings
                num_messages = sum(1 for msg in state.get('chat_history', []) if msg.get('sender') == player_id)
                voted = player_id in state.get('votes', {})
                
                # Check if player won
                won_game = False
                if num_humans == 1:
                    # Single-player game: check if they voted for an AI
                    player_vote = state.get('votes', {}).get(player_id)
                    if player_vote:
                        for p in state.get('players', []):
                            if p['id'] == player_vote and p.get('role') == 'ai':
                                won_game = True
                                break
                else:
                    # Multi-player game: use original logic
                    if state.get('selected_suspect') and state.get('suspect_role') == 'ai':
                        player_vote = state.get('votes', {}).get(player_id)
                        if player_vote:
                            for p in state.get('players', []):
                                if p['id'] == player_vote and p.get('role') == 'ai':
                                    won_game = True
                                    break
                
                player_earnings_value, earnings_breakdown = calculate_earnings(
                    game_completed=True,
                    won_game=won_game,
                    num_messages=num_messages,
                    discussion_duration=discussion_duration,
                    voted=voted
                )
                
                print(f"💵 Calculated earnings for {player_id}: ${player_earnings_value}")
                print(f"💡 Breakdown: {earnings_breakdown}")
                
                # Get the user object and credit gems
                try:
                    # CRITICAL FIX: Convert string UUID to UUID object for SQL comparison
                    try:
                        mapped_user_uuid = uuid_lib.UUID(mapped_user_id_str)
                    except (ValueError, AttributeError) as uuid_err:
                        print(f"❌ Invalid UUID format for player {player_id}: {mapped_user_id_str}, error: {uuid_err}")
                        continue
                    
                    user_result = await db.execute(
                        sql_select(User).where(User.id == mapped_user_uuid)
                    )
                    db_user = user_result.scalar_one_or_none()
                    
                    if not db_user:
                        print(f"❌ User with UUID {mapped_user_uuid} not found in database")
                        continue
                    
                    # FIXED PAYOUT: Single-player games get exactly 2000 gems (for MTurk testing)
                    # Multi-player games use performance-based earnings
                    if num_humans == 1:
                        # Fixed payout for single-player games
                        gems_earned = 2000
                        print(f"💎 Fixed payout: 2000 gems for single-player game (MTurk standard rate)")
                    else:
                        # Convert USD to gems for multi-player games (1000 gems = $1.00)
                        gems_earned = int(float(player_earnings_value) * GEMS_PER_DOLLAR)
                        print(f"💎 Performance-based payout: {gems_earned} gems (${player_earnings_value})")
                    
                    # VALIDATION: Ensure gems_earned is reasonable
                    if gems_earned < 0:
                        print(f"⚠️ Negative gems calculated ({gems_earned}), setting to 0")
                        gems_earned = 0
                    elif gems_earned > 100000:  # Sanity check: max 100,000 gems per game ($100)
                        print(f"⚠️ Suspiciously high gems ({gems_earned}), capping at 100,000")
                        gems_earned = 100000
                    
                    # Validate final amount
                    if gems_earned <= 0:
                        print(f"⚠️ No gems to credit for player {player_id} (amount: {gems_earned})")
                        continue
                    
                    # Credit gems to user's balance (ATOMIC OPERATION)
                    old_balance = db_user.gem_balance
                    db_user.gem_balance += gems_earned
                    db_user.total_gems_earned += gems_earned
                    db_user.total_games += 1  # INCREMENT TOTAL GAMES COUNTER
                    
                    print(f"💎 Credited {gems_earned} gems to user {db_user.user_id} (${player_earnings_value})")
                    print(f"   Balance: {old_balance} → {db_user.gem_balance} gems")
                    print(f"   Total games played: {db_user.total_games}")
                    
                    # Track for session data (use first authenticated player's earnings for legacy)
                    credited_players.append({
                        'player_id': player_id,
                        'user_id': str(mapped_user_uuid),
                        'gems_earned': gems_earned,
                        'earnings_usd': float(player_earnings_value)
                    })
                    
                    # Store for legacy session.calculated_earnings field (use TOTAL gems earned including bonuses)
                    # FIXED: Set for ANY authenticated player, not just current_user
                    # This ensures calculated_earnings is ALWAYS populated for proper last_game_gems display
                    if not calculated_earnings_value and mapped_user_uuid:
                        # Convert total gems earned (including bonuses) back to USD for storage
                        from .cashout_service import gems_to_usd
                        calculated_earnings_value = gems_to_usd(gems_earned)
                        print(f"📊 Session calculated_earnings set to ${calculated_earnings_value} ({gems_earned} gems total) for player {player_id}")
                        
                except Exception as e:
                    print(f"❌ Error crediting gems to player {player_id} (user {mapped_user_id_str}): {e}")
                    print(f"   Stack trace: {traceback.format_exc()}")
                    continue
            
            print(f"✅ Gem credit complete: {len(credited_players)}/{len(player_user_map)} players credited")
            
            # Build session data dict
            session_data = {
                "id": session_id,
                "room_code": room_code,
                "completion_key": completion_key,
                "user_id": current_user.id if current_user else None,
                "language": language,
                "total_players": total_players,
                "num_human_players": num_humans,
                "discussion_duration": discussion_duration,
                "voting_duration": voting_duration,
                "payment_status": PaymentStatus.PENDING,
                "stats_file_path": path,
                "claimed_at": _time.time() if current_user else None,
                "total_input_tokens": total_input_tokens,
                "total_output_tokens": total_output_tokens,
                "total_cost": total_cost,
                "model_name": model_name
            }
            
            # Only add calculated_earnings if the column exists in the model
            if hasattr(DBSession, 'calculated_earnings'):
                session_data["calculated_earnings"] = calculated_earnings_value
            
            # Add MTurk fields if present in room data
            # MTurk context is stored per-player, so we need to find the authenticated user's context
            mturk_context = None
            if current_user:
                # Find which player_id belongs to this user
                player_user_map = room_data.get('player_user_map', {})
                mturk_contexts = room_data.get('mturk_context', {})
                
                # Find the player_id for this user
                user_id_str = str(current_user.id)
                for player_id, mapped_user_id in player_user_map.items():
                    if mapped_user_id == user_id_str:
                        # Found the player_id for this user, get their MTurk context
                        mturk_context = mturk_contexts.get(player_id)
                        if mturk_context:
                            print(f"💼 Found MTurk context for user {current_user.user_id} (player {player_id})")
                        break
            
            if mturk_context:
                session_data["mturk_worker_id"] = mturk_context.get('worker_id')
                session_data["mturk_assignment_id"] = mturk_context.get('assignment_id')
                session_data["mturk_hit_id"] = mturk_context.get('hit_id')
                print(f"💼 MTurk context saved: worker={mturk_context.get('worker_id')}, assignment={mturk_context.get('assignment_id')}")
            
            db_session = DBSession(**session_data)
            db.add(db_session)
            
            # Save per-agent token usage
            for agent_id, usage in agent_token_usage.items():
                agent_cost = calculate_cost(
                    usage.get('input', 0),
                    usage.get('output', 0),
                    model_name
                )
                agent_usage_record = AIAgentUsage(
                    session_id=session_id,
                    agent_id=agent_id,
                    input_tokens=usage.get('input', 0),
                    output_tokens=usage.get('output', 0),
                    cost=agent_cost,
                    message_count=usage.get('calls', 0)
                )
                db.add(agent_usage_record)
            
            # Save player-user mappings
            from .database import SessionPlayer
            player_user_map = room_data.get('player_user_map', {})
            
            print(f"👥 Saving player-user mappings...")
            print(f"📋 player_user_map from room_data: {player_user_map}")
            print(f"👥 state['players']: {[p['id'] + ' (' + p['role'] + ')' for p in state.get('players', [])]}")
            
            for player in state.get('players', []):
                player_id = player['id']
                role = player['role']
                mapped_user_id = player_user_map.get(player_id)
                
                print(f"🔍 Processing player {player_id} ({role}): mapped_user_id = {mapped_user_id}")
                
                # Convert user_id string to UUID if present
                user_uuid = None
                if mapped_user_id:
                    try:
                        user_uuid = uuid_lib.UUID(mapped_user_id)
                        print(f"✅ Mapped {player_id} ({role}) -> user {user_uuid}")
                    except (ValueError, AttributeError) as e:
                        print(f"⚠️ Invalid user_id format for player {player_id}: {mapped_user_id}, error: {e}")
                else:
                    print(f"ℹ️  {player_id} ({role}) -> No user mapping (anonymous)")
                
                session_player = SessionPlayer(
                    session_id=session_id,
                    user_id=user_uuid,
                    player_id=player_id,
                    role=role
                )
                db.add(session_player)
                print(f"💾 SessionPlayer added to DB: {player_id}, user_id={user_uuid}")
            
            await db.commit()
            print(f"✅ Session saved to database with ID: {session_id}")
    except Exception as e:
        print(f"⚠️  Error saving session to database: {e}")
        import traceback
        traceback.print_exc()
        # Don't fail the game completion if database save fails
    
    # Add completion key to payload
    payload['completion_key'] = completion_key
    payload['session_id'] = str(session_id)
    
    # =========================================================================
    # Gamification: Award points and check achievements
    # =========================================================================
    if current_user:
        try:
            from .gamification import (
                calculate_game_points, check_achievements, update_streak,
                calculate_level, ACHIEVEMENTS
            )
            from .database import async_session_maker
            
            # Determine if user won (correctly identified AI)
            user_won = False
            suspect_role = state.get('suspect_role')
            if suspect_role == 'ai':
                user_won = True
            
            # Count user messages
            user_messages = [
                msg for msg in state.get('chat_history', [])
                if any(p['id'] == msg.get('sender') and p['role'] == 'human' 
                       for p in state.get('players', []))
            ]
            num_user_messages = len(user_messages)
            
            # Check if user voted
            user_voted = any(
                p['id'] in state.get('votes', {}) and p['role'] == 'human'
                for p in state.get('players', [])
            )
            
            # Calculate points earned
            points_earned, points_breakdown = calculate_game_points(
                game_completed=True,
                won_game=user_won,
                discussion_duration=discussion_duration,
                num_messages=num_user_messages,
                voted=user_voted
            )
            
            print(f"🎮 User earned {points_earned} points! Breakdown: {points_breakdown}")
            
            # Update user stats in database
            async with async_session_maker() as db:
                # Refresh user from database
                result = await db.execute(
                    select(User).where(User.id == current_user.id)
                )
                user = result.scalar_one_or_none()
                
                if user:
                    # Get unlocked achievements before update (for checking new ones)
                    old_achievements = []
                    for achievement in ACHIEVEMENTS:
                        if achievement.requirement_type == "games_played" and user.total_games >= achievement.requirement_value:
                            old_achievements.append(achievement.id)
                        elif achievement.requirement_type == "wins" and user.total_wins >= achievement.requirement_value:
                            old_achievements.append(achievement.id)
                        elif achievement.requirement_type == "streak" and user.current_streak >= achievement.requirement_value:
                            old_achievements.append(achievement.id)
                    
                    # Update streak
                    new_current_streak, new_longest_streak = update_streak(
                        user.last_played_at,
                        user.current_streak,
                        user.longest_streak
                    )
                    
                    # Update user stats
                    user.total_games += 1
                    if user_won:
                        user.total_wins += 1
                    user.total_points += points_earned
                    user.current_streak = new_current_streak
                    user.longest_streak = new_longest_streak
                    user.last_played_at = datetime.utcnow()
                    
                    # Recalculate level
                    user.level = calculate_level(user.total_points)
                    
                    await db.commit()
                    
                    # Check for new achievements
                    new_achievements = check_achievements(
                        user.total_games,
                        user.total_wins,
                        user.current_streak,
                        user.total_points,
                        old_achievements
                    )
                    
                    # Add gamification data to payload for frontend
                    payload['gamification'] = {
                        'points_earned': points_earned,
                        'points_breakdown': points_breakdown,
                        'new_achievements': [
                            {
                                'id': ach.id,
                                'name': ach.name,
                                'description': ach.description,
                                'icon': ach.icon,
                                'points': ach.points
                            }
                            for ach in new_achievements
                        ],
                        'user_stats': {
                            'level': user.level,
                            'total_points': user.total_points,
                            'total_games': user.total_games,
                            'total_wins': user.total_wins,
                            'current_streak': user.current_streak,
                            'longest_streak': user.longest_streak
                        },
                        'won_game': user_won
                    }
                    
                    if new_achievements:
                        print(f"🏆 User unlocked {len(new_achievements)} new achievements!")
                        for ach in new_achievements:
                            print(f"   - {ach.icon} {ach.name}: {ach.description}")
                
        except Exception as e:
            print(f"⚠️  Error updating gamification stats: {e}")
            import traceback
            traceback.print_exc()
            # Don't fail the game completion if gamification fails
    
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
    
    Query params:
        token: Optional JWT token for authenticated users
    """
    await websocket.accept()
    print(f"🔌 WebSocket accepted for player {player_id} in room {room_code}")
    
    # Try to get authenticated user from token query param
    user_id = None
    authenticated_user = None
    mturk_context = None
    try:
        token = websocket.query_params.get('token')
        print(f"🔑 Token received: {'Yes' if token else 'No'}")
        
        if token:
            from .auth import get_user_by_uuid
            from .database import async_session_maker
            from jose import jwt, JWTError
            from .auth import JWT_SECRET_KEY, JWT_ALGORITHM
            
            print(f"🔓 Decoding JWT token...")
            payload = jwt.decode(token, JWT_SECRET_KEY, algorithms=[JWT_ALGORITHM])
            user_uuid = payload.get("sub")
            print(f"🆔 User UUID from token: {user_uuid}")
            
            if user_uuid:
                async with async_session_maker() as db:
                    user = await get_user_by_uuid(db, user_uuid)
                    if user:
                        user_id = str(user.id)
                        authenticated_user = user
                        print(f"👤 ✅ Authenticated user '{user.user_id}' (ID: {user_id[:8]}...) as {player_id}")
                        
                        # Check if this is an MTurk worker (user_id starts with 'A' and is 14 chars)
                        # MTurk worker IDs follow pattern: A[A-Z0-9]{13}
                        if user.user_id and len(user.user_id) == 14 and user.user_id.startswith('A'):
                            # Try to get MTurk context from localStorage (passed via query params)
                            import json
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
        # Continue without authentication - game works for non-logged-in users too
    
    # Initialize room if needed
    if room_code not in rooms:
        print(f"⚠️ WebSocket connection to non-existent room: {room_code}")
        print(f"🎮 Creating legacy WebSocket room: {room_code}")
        
        # For legacy WebSocket rooms, use proper number assignment
        total_players = NUM_AI_PLAYERS + 1  # 1 human via WebSocket
        all_numbers = list(range(1, total_players + 1))
        random.shuffle(all_numbers)
        ai_numbers = all_numbers[:NUM_AI_PLAYERS]
        available_numbers = all_numbers[NUM_AI_PLAYERS:]
        ai_player_ids = [f"Player {num}" for num in ai_numbers]
        
        # Create game with default language (english) for WebSocket rooms
        state = create_game_for_room(room_code, NUM_AI_PLAYERS, ai_player_ids, "english")
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
            'player_user_map': {},  # Maps player_id -> user_id (for authenticated users)
            'current_humans': [],
            'available_numbers': available_numbers,
            'discussion_duration': DISCUSSION_TIME,  # Use default config
            'voting_duration': VOTING_TIME  # Use default config
        }
        # Initialize lock for this room to prevent race conditions
        if room_code not in room_locks:
            room_locks[room_code] = asyncio.Lock()
        
        print(f"📝 Legacy WebSocket room created - Topic: {state['topic']}")
        print(f"📝 Using default durations - discussion: {DISCUSSION_TIME}s, voting: {VOTING_TIME}s")
    else:
        print(f"✅ WebSocket connecting to existing room: {room_code}")
        print(f"✅ Existing room durations - discussion: {rooms[room_code].get('discussion_duration', 'NOT SET')}, voting: {rooms[room_code].get('voting_duration', 'NOT SET')}")
    
    # Add connection BEFORE broadcasting
    rooms[room_code]['connections'][player_id] = websocket
    print(f"✅ Connection added. Total connections: {len(rooms[room_code]['connections'])}")
    
    # Store player-user mapping if user is authenticated
    if user_id:
        rooms[room_code]['player_user_map'][player_id] = user_id
        print(f"👤 ✅ Stored initial mapping: {player_id} -> user {user_id[:8]}...")
    else:
        print(f"⚠️ No user_id to store for player {player_id}")
    
    # Store MTurk context if available
    if mturk_context:
        if 'mturk_context' not in rooms[room_code]:
            rooms[room_code]['mturk_context'] = {}
        rooms[room_code]['mturk_context'][player_id] = mturk_context
        print(f"💼 ✅ Stored MTurk context for {player_id}: worker={mturk_context.get('worker_id')}")
    
    # Add human player to game state if not already there
    state = rooms[room_code]['state']
    # Check if this player (by connection ID or numbered ID) is already in the state
    existing_player = None
    for p in state.get('players', []):
        if p['id'] == player_id or p.get('role') == 'human':
            existing_player = p
            break
    
    if not existing_player:
        # Assign a numbered player ID from available numbers
        available_nums = rooms[room_code].get('available_numbers', [])
        if available_nums:
            assigned_number = available_nums.pop(0)
            numbered_player_id = f"Player {assigned_number}"
        else:
            # Fallback if no numbers available
            numbered_player_id = player_id
        
        # Add human player to state
        state['players'].append({
            "id": numbered_player_id,
            "role": "human",
            "eliminated": False,
            "personality": None
        })
        
        # Store mapping from connection player_id to state player_id
        rooms[room_code]['player_id_map'] = rooms[room_code].get('player_id_map', {})
        rooms[room_code]['player_id_map'][player_id] = numbered_player_id
        
        # Update user mapping to use numbered player ID
        if user_id:
            rooms[room_code]['player_user_map'][numbered_player_id] = user_id
            print(f"👤 ✅ Mapped {numbered_player_id} (human) -> user {user_id[:8]}...")
            print(f"📋 Current player_user_map: {rooms[room_code]['player_user_map']}")
        else:
            print(f"⚠️ No user_id to map for {numbered_player_id}")
        
        rooms[room_code]['state'] = state
        print(f"✅ Added human player {numbered_player_id} to game state")
    else:
        # Player already exists (joined via API), just store the connection mapping
        numbered_player_id = existing_player['id']
        rooms[room_code]['player_id_map'] = rooms[room_code].get('player_id_map', {})
        rooms[room_code]['player_id_map'][player_id] = numbered_player_id
        
        # Check if mapping already exists (set via API join)
        existing_mapping = rooms[room_code]['player_user_map'].get(numbered_player_id)
        
        if existing_mapping:
            print(f"ℹ️ Player {numbered_player_id} already mapped via API -> user {existing_mapping[:8]}...")
            # If WebSocket has different/additional user info, keep the existing one from API
            if user_id and user_id != existing_mapping:
                print(f"⚠️ WebSocket user {user_id[:8]}... differs from API user {existing_mapping[:8]}... - keeping API mapping")
        elif user_id:
            # No existing mapping, add it now from WebSocket auth
            rooms[room_code]['player_user_map'][numbered_player_id] = user_id
            print(f"👤 ✅ Mapped {numbered_player_id} (existing player from API) -> user {user_id[:8]}... via WebSocket")
            print(f"📋 Current player_user_map: {rooms[room_code]['player_user_map']}")
        else:
            print(f"⚠️ No user_id to map for existing player {numbered_player_id}")
    
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
        await asyncio.sleep(1.75)  # Small delay for realism
        asyncio.create_task(trigger_agent_decisions(room_code))
    
    # Send current game state to the newly connected client
    state = rooms[room_code]['state']
    room = rooms[room_code]
    await websocket.send_json({"type": "player_list", "players": [p["id"] for p in state["players"]]})
    await websocket.send_json({"type": "topic", "topic": state["topic"]})
    
    # Send phase with durations
    phase_msg = {
        "type": "phase",
        "phase": state["phase"].value,
        "message": f"Currently in {state['phase'].value}"
    }
    if state["phase"].value == "Discussion":
        phase_msg["discussion_duration"] = room.get('discussion_duration', DISCUSSION_TIME)
    elif state["phase"].value == "Voting":
        phase_msg["voting_duration"] = room.get('voting_duration', VOTING_TIME)
    await websocket.send_json(phase_msg)
    
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
                
                # Get the numbered player ID for this connection
                player_id_map = rooms[room_code].get('player_id_map', {})
                actual_player_id = player_id_map.get(player_id, player_id)
                
                # Update state
                state = await process_human_message(state, message, actual_player_id)
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
                
                # Get the numbered player ID for this connection
                player_id_map = rooms[room_code].get('player_id_map', {})
                actual_player_id = player_id_map.get(player_id, player_id)
                
                # Update state
                state = await process_human_vote(state, actual_player_id, voted_for)
                rooms[room_code]['state'] = state
                
                # Broadcast vote
                await broadcast_to_room(room_code, {
                    "type": "voted",
                    "player": actual_player_id
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
# Authentication API Endpoints
# ============================================================================

@app.post("/api/auth/register")
async def register(
    request: RegisterRequest,
    db: AsyncSession = Depends(get_async_session)
):
    """
    Register a new user.
    
    Args:
        request: User registration data (user_id, password)
        db: Database session
    
    Returns:
        Success message
    """
    # Check if user already exists
    existing_user = await db.execute(
        select(User).where(User.user_id == request.user_id)
    )
    if existing_user.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User ID already exists"
        )
    
    # Create new user
    hashed_password = hash_password(request.password)
    new_user = User(
        user_id=request.user_id,
        password_hash=hashed_password,
        role=UserRole.USER
    )
    db.add(new_user)
    await db.commit()
    await db.refresh(new_user)
    
    return {
        "success": True,
        "message": "User registered successfully",
        "user_id": new_user.user_id
    }


@app.post("/api/auth/login", response_model=LoginResponse)
async def login(
    request: LoginRequest,
    db: AsyncSession = Depends(get_async_session)
):
    """
    Authenticate user and return JWT token.
    
    Args:
        request: Login credentials (user_id, password)
        db: Database session
    
    Returns:
        JWT access token and user info
    """
    user = await authenticate_user(db, request.user_id, request.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect user ID or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Create access token
    access_token = create_access_token(data={"sub": str(user.id)})
    
    return LoginResponse(
        access_token=access_token,
        token_type="bearer",
        user_id=user.user_id,
        role=user.role.value
    )


@app.get("/api/auth/me", response_model=UserResponse)
async def get_current_user_info(
    current_user: User = Depends(get_current_user)
):
    """
    Get current authenticated user information.
    
    Args:
        current_user: Current authenticated user
    
    Returns:
        User information
    """
    return UserResponse(
        id=str(current_user.id),
        user_id=current_user.user_id,
        role=current_user.role.value,
        created_at=current_user.created_at.isoformat()
    )


@app.get("/api/profile")
async def get_user_profile(
    current_user: User = Depends(get_current_user)
):
    """
    Get detailed user profile information including wallet and MTurk data.
    
    Args:
        current_user: Current authenticated user
    
    Returns:
        Complete user profile
    """
    from .cashout_service import gems_to_usd
    
    return {
        "id": str(current_user.id),
        "user_id": current_user.user_id,
        "role": current_user.role.value,
        "created_at": current_user.created_at.isoformat(),
        "mturk_worker_id": current_user.mturk_worker_id,
        "gem_balance": current_user.gem_balance,
        "gem_balance_usd": float(gems_to_usd(current_user.gem_balance)),
        "total_gems_earned": current_user.total_gems_earned,
        "total_gems_cashed_out": current_user.total_gems_cashed_out,
        "total_games": current_user.total_games,
        "total_wins": current_user.total_wins,
        "total_points": current_user.total_points,
        "level": current_user.level,
        "current_streak": current_user.current_streak,
        "longest_streak": current_user.longest_streak,
        "last_played_at": current_user.last_played_at.isoformat() if current_user.last_played_at else None
    }


@app.put("/api/profile/mturk-worker-id")
async def update_mturk_worker_id(
    request: Request,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_session)
):
    """
    Update user's MTurk Worker ID.
    
    Args:
        request: Request with worker_id in body
        current_user: Current authenticated user
        db: Database session
    
    Returns:
        Updated profile information
    """
    import re
    
    body = await request.json()
    worker_id = body.get('worker_id', '').strip()
    
    # Validate MTurk Worker ID format (typically starts with 'A' and is alphanumeric)
    if worker_id:
        # MTurk Worker IDs are typically 14 characters starting with 'A'
        if not re.match(r'^A[A-Z0-9]{13,}$', worker_id):
            raise HTTPException(
                status_code=400,
                detail="Invalid MTurk Worker ID format. Worker IDs typically start with 'A' followed by alphanumeric characters (e.g., A12TU3EXAMPLE93)"
            )
    
    # Update user's worker ID
    current_user.mturk_worker_id = worker_id if worker_id else None
    await db.commit()
    await db.refresh(current_user)
    
    print(f"✅ Updated MTurk Worker ID for user {current_user.user_id}: {worker_id}")
    
    return {
        "success": True,
        "mturk_worker_id": current_user.mturk_worker_id,
        "message": "MTurk Worker ID updated successfully"
    }


# ============================================================================
# MTurk Integration API Endpoints
# ============================================================================

@app.post("/api/auth/mturk-register")
async def mturk_register(
    request: MTurkRegisterRequest,
    http_request: Request,
    db: AsyncSession = Depends(get_async_session)
):
    """
    Auto-register or login an MTurk worker.
    Called by frontend when MTurk URL parameters are detected.
    
    Args:
        request: MTurk worker credentials (workerId, assignmentId, hitId)
        http_request: FastAPI Request object (for rate limiting)
        db: Database session
    
    Returns:
        JWT access token and user info
    """
    import re
    
    # Rate limiting check
    client_ip = http_request.client.host
    if not mturk_rate_limiter.is_allowed(client_ip):
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many registration attempts. Please wait a minute and try again."
        )
    
    # Check for preview mode
    if request.assignment_id == "ASSIGNMENT_ID_NOT_AVAILABLE":
        return {
            "success": True,
            "preview_mode": True,
            "message": "Preview mode - accept HIT to participate"
        }
    
    # Validate worker_id format (MTurk worker IDs: A followed by 13 alphanumeric chars)
    worker_id_pattern = re.compile(r'^A[A-Z0-9]{13}$')
    if not worker_id_pattern.match(request.worker_id):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid MTurk worker ID format. Expected format: A followed by 13 alphanumeric characters."
        )
    
    # Validate assignment_id format (MTurk assignment IDs typically start with '3' and are ~30 chars)
    assignment_id_pattern = re.compile(r'^3[A-Z0-9]{20,40}$')
    if not assignment_id_pattern.match(request.assignment_id):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid MTurk assignment ID format."
        )
    
    # Check if this assignment_id already exists in sessions (prevent duplicate registrations)
    existing_session = await db.execute(
        select(DBSession).where(DBSession.mturk_assignment_id == request.assignment_id)
    )
    if existing_session.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"This assignment has already been registered. Each assignment can only be used once."
        )
    
    # Register or login worker
    user, access_token = await register_or_login_mturk_worker(db, request.worker_id)
    
    # Store MTurk IDs in session context (will be saved with game session)
    return {
        "success": True,
        "access_token": access_token,
        "token_type": "bearer",
        "user_id": user.user_id,
        "role": user.role.value,
        "mturk_context": {
            "worker_id": request.worker_id,
            "assignment_id": request.assignment_id,
            "hit_id": request.hit_id
        }
    }


@app.get("/api/users/stats")
async def get_user_stats(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_session)
):
    """
    Get detailed user statistics and gamification data.
    
    Args:
        current_user: Current authenticated user
        db: Database session
    
    Returns:
        User statistics including points, level, achievements, etc.
    """
    from .gamification import (
        calculate_level, points_for_next_level, 
        get_next_close_achievements, get_motivational_message,
        ACHIEVEMENTS
    )
    
    # Get user's sessions for win calculation
    result = await db.execute(
        select(DBSession).where(DBSession.user_id == current_user.id)
    )
    sessions = result.scalars().all()
    
    # Calculate win rate
    win_rate = (current_user.total_wins / current_user.total_games * 100) if current_user.total_games > 0 else 0
    
    # Calculate level and progress
    current_level = current_user.level
    points_for_level_up = points_for_next_level(current_level)
    current_level_start = int(100 * (current_level ** 1.5)) if current_level > 1 else 0
    progress_in_level = current_user.total_points - current_level_start
    progress_needed = points_for_level_up - current_level_start
    level_progress_percentage = (progress_in_level / progress_needed * 100) if progress_needed > 0 else 0
    
    # Get next close achievements (assuming we track unlocked achievements separately - for now, calculate based on current stats)
    # In a full implementation, you'd store unlocked achievements in a separate table
    unlocked_ids = []
    for achievement in ACHIEVEMENTS:
        if achievement.requirement_type == "games_played" and current_user.total_games >= achievement.requirement_value:
            unlocked_ids.append(achievement.id)
        elif achievement.requirement_type == "wins" and current_user.total_wins >= achievement.requirement_value:
            unlocked_ids.append(achievement.id)
        elif achievement.requirement_type == "streak" and current_user.current_streak >= achievement.requirement_value:
            unlocked_ids.append(achievement.id)
    
    next_achievements = get_next_close_achievements(
        current_user.total_games,
        current_user.total_wins,
        current_user.current_streak,
        unlocked_ids,
        limit=3
    )
    
    motivational_msg = get_motivational_message(
        current_user.total_games,
        current_user.total_wins,
        current_user.current_streak,
        [ach for ach, _ in next_achievements]
    )
    
    return {
        "user_id": current_user.user_id,
        "level": current_level,
        "total_points": current_user.total_points,
        "points_for_next_level": points_for_level_up,
        "level_progress": {
            "current": progress_in_level,
            "needed": progress_needed,
            "percentage": round(level_progress_percentage, 1)
        },
        "games": {
            "total": current_user.total_games,
            "wins": current_user.total_wins,
            "losses": current_user.total_games - current_user.total_wins,
            "win_rate": round(win_rate, 1)
        },
        "streak": {
            "current": current_user.current_streak,
            "longest": current_user.longest_streak
        },
        "achievements": {
            "unlocked_count": len(unlocked_ids),
            "total_count": len(ACHIEVEMENTS),
            "unlocked_ids": unlocked_ids
        },
        "next_achievements": [
            {
                "id": ach.id,
                "name": ach.name,
                "description": ach.description,
                "icon": ach.icon,
                "points": ach.points,
                "progress_needed": progress
            }
            for ach, progress in next_achievements
        ],
        "motivational_message": motivational_msg,
        "last_played_at": current_user.last_played_at.isoformat() if current_user.last_played_at else None
    }


@app.get("/api/users/earnings")
async def get_user_earnings(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_session)
):
    """
    Get detailed earnings statistics for current user.
    USES GEM ECONOMY SYSTEM - synced with wallet balance.
    
    Args:
        current_user: Current authenticated user
        db: Database session
    
    Returns:
        Earnings statistics including total, pending, average, etc.
    """
    from decimal import Decimal
    from sqlalchemy import func
    from datetime import datetime, timedelta
    from .config import GEMS_PER_DOLLAR
    from .cashout_service import gems_to_usd
    
    print(f"\n{'='*70}")
    print(f"📊 EARNINGS REQUEST for user: {current_user.user_id}")
    print(f"{'='*70}")
    
    # GEM ECONOMY: Use user's gem statistics (SYNCED WITH WALLET)
    total_gems_earned = current_user.total_gems_earned
    current_gem_balance = current_user.gem_balance
    total_gems_cashed_out = current_user.total_gems_cashed_out
    total_games = current_user.total_games
    
    # FALLBACK: If total_games is 0 but user has sessions, sync it from session count
    if total_games == 0:
        result = await db.execute(
            select(func.count(DBSession.id))
            .where(DBSession.user_id == current_user.id)
        )
        session_count = result.scalar() or 0
        if session_count > 0:
            print(f"⚠️ SYNC: User {current_user.user_id} has {session_count} sessions but total_games=0. Syncing...")
            current_user.total_games = session_count
            await db.commit()
            await db.refresh(current_user)
            total_games = session_count
            print(f"✅ SYNCED: total_games updated to {total_games}")
    
    # Convert to USD for display
    current_balance_usd = gems_to_usd(current_gem_balance)
    total_cashed_out_usd = gems_to_usd(total_gems_cashed_out)  # This is the real "lifetime earnings"
    
    print(f"User Stats (GEM ECONOMY - synced with wallet):")
    print(f"   Total games: {total_games}")
    print(f"   Total gems earned: {total_gems_earned} gems")
    print(f"   Current balance: {current_gem_balance} gems = ${current_balance_usd}")
    print(f"   Lifetime earnings (cashed out): {total_gems_cashed_out} gems = ${total_cashed_out_usd}")
    
    # Calculate average per game (IN GEMS, not USD)
    avg_gems_per_game = int((total_gems_earned / total_games) if total_games > 0 else 0)
    
    # Get recent sessions via SessionPlayer table (PROPER USER-SESSION MAPPING)
    # This correctly handles cases where Session.user_id is NULL
    from .database import SessionPlayer
    
    result = await db.execute(
        select(DBSession)
        .join(SessionPlayer, SessionPlayer.session_id == DBSession.id)
        .where(SessionPlayer.user_id == current_user.id)
        .where(SessionPlayer.role == 'human')  # Only human players, not AI
        .order_by(desc(DBSession.completed_at))
        .limit(10)
    )
    sessions = result.scalars().all()
    
    print(f"📊 Found {len(sessions)} recent sessions for user {current_user.user_id}")
    
    # Calculate last game amount (IN GEMS) - Use a smarter approach
    last_game_gems = 0  # Start with 0, will be updated if we find a recent game
    highest_earning_gems = 0
    recent_sessions = []
    
    for idx, session in enumerate(sessions):
        # Try multiple methods to estimate gems (in order of reliability)
        estimated_gems = 0
        
        # METHOD 1: Use calculated_earnings if available (includes bonuses per fix)
        if hasattr(session, 'calculated_earnings') and session.calculated_earnings:
            estimated_gems = int(float(session.calculated_earnings) * GEMS_PER_DOLLAR)
            print(f"   Session {idx}: {estimated_gems} gems (from calculated_earnings=${session.calculated_earnings})")
        
        # METHOD 2: For new sessions without calculated_earnings, estimate from total_gems_earned
        elif idx == 0 and total_games > 0:
            # For the most recent game, use the average as best estimate
            estimated_gems = avg_gems_per_game
            print(f"   Session {idx}: {estimated_gems} gems (estimated from average)")
        
        # METHOD 3: Fallback to average for older sessions
        else:
            estimated_gems = avg_gems_per_game
            print(f"   Session {idx}: {estimated_gems} gems (fallback to average)")
        
        if idx == 0:  # Most recent game
            last_game_gems = estimated_gems
            print(f"✅ Last game gems set to: {last_game_gems}")
        
        if estimated_gems > highest_earning_gems:
            highest_earning_gems = estimated_gems
        
        # Store sessions with gem amounts for trend chart
        recent_sessions.append({
            "date": session.completed_at.isoformat(),
            "amount": estimated_gems,
            "status": "completed"
        })
    
    # FALLBACK: If no sessions found but user has gems, use average
    if len(sessions) == 0 and total_games > 0:
        last_game_gems = avg_gems_per_game
        print(f"⚠️ No sessions found via SessionPlayer, using average: {last_game_gems} gems")
    
    # Get dates for time-based stats
    now = datetime.utcnow()
    week_ago = now - timedelta(days=7)
    month_ago = now - timedelta(days=30)
    
    # Calculate actual cashouts this week/month (REAL EARNINGS, not estimated)
    from .database import CashoutTransaction, CashoutStatus
    
    result_week = await db.execute(
        select(func.sum(CashoutTransaction.amount_gems))
        .where(CashoutTransaction.user_id == current_user.id)
        .where(CashoutTransaction.status == CashoutStatus.COMPLETED)
        .where(CashoutTransaction.created_at >= week_ago)
    )
    gems_cashed_week = result_week.scalar() or 0
    earnings_this_week_usd = gems_to_usd(gems_cashed_week)
    
    result_month = await db.execute(
        select(func.sum(CashoutTransaction.amount_gems))
        .where(CashoutTransaction.user_id == current_user.id)
        .where(CashoutTransaction.status == CashoutStatus.COMPLETED)
        .where(CashoutTransaction.created_at >= month_ago)
    )
    gems_cashed_month = result_month.scalar() or 0
    earnings_this_month_usd = gems_to_usd(gems_cashed_month)
    
    # Get earnings tier (based on total cashed out, not total earned)
    from .earnings import get_earnings_tier
    tier_info = get_earnings_tier(total_cashed_out_usd)
    
    print(f"\nCalculated Stats:")
    print(f"   Avg per game: {avg_gems_per_game} gems")
    print(f"   Last game: {last_game_gems} gems")
    print(f"   Cashed out this week: {gems_cashed_week} gems = ${earnings_this_week_usd}")
    print(f"   Tier: {tier_info['name']} (based on total cashed out)")
    print(f"✅ SYNCED: total_lifetime_earnings (${total_cashed_out_usd}) = wallet.total_gems_cashed_out ({total_gems_cashed_out} gems)")
    print(f"{'='*70}\n")
    
    return {
        # PRIMARY STATS (✅ SYNCED WITH WALLET)
        # NOTE: "total_lifetime_earnings" now means ACTUAL CASH EARNED (cashed out), not total gems
        "total_lifetime_earnings": float(total_cashed_out_usd),  # = wallet.total_gems_cashed_out / 1000
        # "pending_earnings" REMOVED per user request
        "current_balance": float(current_balance_usd),  # = wallet.gem_balance / 1000
        "total_cashed_out": float(total_cashed_out_usd),  # = wallet.total_gems_cashed_out / 1000
        
        # PER-GAME STATS (IN GEMS, not USD)
        "average_per_game": avg_gems_per_game,  # Gems per game
        "last_game_gems": last_game_gems,  # Last game in gems
        "highest_single_game": highest_earning_gems,  # Highest in gems
        "total_games": total_games,
        
        # TIME-BASED STATS (Actual cashouts, not estimated)
        "earnings_this_week": float(earnings_this_week_usd),  # USD cashed out this week
        "earnings_this_month": float(earnings_this_month_usd),  # USD cashed out this month
        
        # RECENT HISTORY (now in gems)
        "recent_sessions": recent_sessions,
        
        # TIER INFO (based on total cashed out)
        "tier": {
            "name": tier_info["name"],
            "color": tier_info["color"],
            "current_amount": float(total_cashed_out_usd),
            "next_threshold": float(tier_info["next"]) if tier_info["next"] else None
        },
        
        # GEM ECONOMY DETAILS
        "gem_details": {
            "total_gems_earned": total_gems_earned,
            "current_gem_balance": current_gem_balance,
            "total_gems_cashed_out": total_gems_cashed_out,
            "conversion_rate": GEMS_PER_DOLLAR
        }
    }


# ============================================================================
# Wallet & Cashout API Endpoints
# ============================================================================

@app.get("/api/wallet/balance")
async def get_wallet_balance(
    current_user: User = Depends(get_current_user)
):
    """
    Get user's gem wallet balance and statistics.
    
    Args:
        current_user: Current authenticated user
    
    Returns:
        Wallet balance information
    """
    from .config import GEMS_PER_DOLLAR
    from .cashout_service import gems_to_usd
    
    return {
        "gem_balance": current_user.gem_balance,
        "usd_equivalent": float(gems_to_usd(current_user.gem_balance)),
        "total_gems_earned": current_user.total_gems_earned,
        "total_gems_cashed_out": current_user.total_gems_cashed_out,
        "conversion_rate": {
            "gems_per_dollar": GEMS_PER_DOLLAR,
            "description": f"{GEMS_PER_DOLLAR} gems = $1.00 USD"
        },
        "mturk_worker_id": current_user.mturk_worker_id,
        "has_worker_id": bool(current_user.mturk_worker_id)
    }


@app.post("/api/wallet/cashout")
async def request_cashout(
    request: Request,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_session)
):
    """
    Request a cashout of gems to USD via MTurk redemption code.
    Generates a unique code for user to submit in the standing MTurk HIT.
    
    Args:
        request: Request with amount_usd in body
        current_user: Current authenticated user
        db: Database session
    
    Returns:
        Cashout transaction with redemption code
    """
    from decimal import Decimal
    from .cashout_service import create_cashout_transaction, CashoutError
    from .config import EXTERNAL_URL
    
    body = await request.json()
    amount_usd = Decimal(str(body.get('amount_usd', 0)))
    
    print(f"\n{'='*70}")
    print(f"📥 CASHOUT REQUEST from user: {current_user.user_id}")
    print(f"   Amount: ${amount_usd}")
    print(f"   User balance: {current_user.gem_balance} gems")
    print(f"{'='*70}")
    
    try:
        # Check if cashout system is configured (using cached value)
        print(f"🔍 Step 1: Checking cashout configuration...")
        try:
            mturk_hit_id = env_config.get_cashout_hit_id()
            print(f"   ✅ HIT ID loaded: {mturk_hit_id}")
        except ValueError as e:
            # Detailed error with diagnostic info
            config_status = env_config.get_config_status()
            error_details = {
                "error": "Cashout system not properly configured",
                "env_file_path": config_status['env_file_path'],
                "env_file_exists": config_status['env_file_exists'],
                "solution": "Set CASHOUT_HIT_ID in your .env file and restart the server"
            }
            print(f"   ❌ Configuration error: {error_details}")
            raise HTTPException(
                status_code=503,
                detail=f"Cashout system not configured. Environment file: {config_status['env_file_path']}, Exists: {config_status['env_file_exists']}. Please contact administrator."
            )
        
        # Create cashout transaction with redemption code
        print(f"🔍 Step 2: Creating cashout transaction...")
        transaction = await create_cashout_transaction(
            user=current_user,
            amount_usd=amount_usd,
            db=db
        )
        print(f"   ✅ Transaction created: {transaction.id}")
        
        # Get MTurk environment to provide correct HIT URL
        print(f"🔍 Step 3: Getting MTurk environment...")
        from .mturk_api import get_mturk_client
        mturk_client = get_mturk_client()
        environment = mturk_client.environment
        worker_endpoint = mturk_client.worker_endpoints[environment]
        print(f"   ✅ Environment: {environment}")
        print(f"   ✅ Worker endpoint: {worker_endpoint}")
        
        # Generate MTurk HIT URL and testing URL
        
        print(f"🔍 Step 4: Generating redemption URLs...")
        
        # Get HITGroupId from MTurk (needed for worker preview URL)
        # Note: HITId != HITGroupId, must query MTurk to get the group ID
        try:
            hit_response = mturk_client.client.get_hit(HITId=mturk_hit_id)
            hit_group_id = hit_response['HIT']['HITGroupId']
            print(f"   ✅ HITGroupId: {hit_group_id}")
        except Exception as e:
            print(f"   ⚠️ Could not get HITGroupId, using HITId as fallback: {e}")
            hit_group_id = mturk_hit_id  # Fallback (may not work)
        
        # MTurk HIT preview URL (for production use)
        mturk_hit_url = f"{worker_endpoint}/mturk/preview?groupId={hit_group_id}"
        
        # Dev/Testing URL (for testing without accepting HIT)
        # This allows testing the redemption flow without MTurk API calls
        dev_test_url = f"{EXTERNAL_URL.replace('/lobby', '')}/cashout-confirm?dev=true&code={transaction.redemption_code}"
        
        print(f"   ✅ Environment: {environment}")
        print(f"   ✅ MTurk HIT URL: {mturk_hit_url}")
        print(f"   ✅ Dev Test URL: {dev_test_url}")
        
        response_data = {
            "success": True,
            "transaction_id": str(transaction.id),
            "amount_usd": float(transaction.amount_usd),
            "amount_gems": transaction.amount_gems,
            "redemption_code": transaction.redemption_code,
            "status": transaction.status.value,
            "expires_at": transaction.expires_at.isoformat() if transaction.expires_at else None,
            "environment": environment,
            "hit_url": mturk_hit_url,  # MTurk HIT URL (official)
            "dev_test_url": dev_test_url if environment == 'sandbox' else None,  # Testing URL (sandbox only)
            "instructions": {
                "step1": "Copy your redemption code (shown above)",
                "step2": "Choose redemption method below",
                "step3": "MTurk HIT: For real MTurk workers (requires accepting HIT)",
                "step4": "Test Mode: For testing without MTurk (sandbox only)",
                "note": "Your code is valid for 7 days. Payment processes immediately after redemption.",
                "troubleshooting": "If you see 'No HITs available', you may have already accepted one. Return it first from your MTurk dashboard."
            }
        }
        
        print(f"✅ CASHOUT REQUEST SUCCESSFUL")
        print(f"   Transaction ID: {response_data['transaction_id']}")
        print(f"   Redemption Code: {response_data['redemption_code'][:16]}...")
        print(f"{'='*70}\n")
        
        return response_data
        
    except HTTPException:
        # Re-raise HTTP exceptions as-is
        print(f"❌ CASHOUT REQUEST FAILED - HTTP Exception")
        print(f"{'='*70}\n")
        raise
    except CashoutError as e:
        print(f"❌ CASHOUT REQUEST FAILED - Cashout Error: {e}")
        print(f"{'='*70}\n")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        print(f"❌ CASHOUT REQUEST FAILED - Unexpected Error: {e}")
        import traceback
        print(f"   Stack trace:\n{traceback.format_exc()}")
        print(f"{'='*70}\n")
        raise HTTPException(status_code=500, detail=f"Failed to create cashout: {str(e)}")


@app.get("/api/wallet/cashout-history")
async def get_cashout_history(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_session)
):
    """
    Get cashout transaction history for current user.
    
    Args:
        current_user: Current authenticated user
        db: Database session
    
    Returns:
        List of cashout transactions
    """
    from .cashout_service import get_user_cashout_history
    
    try:
        history = await get_user_cashout_history(user=current_user, db=db, limit=50)
        
        return {
            "transactions": history,
            "total_count": len(history)
        }
        
    except Exception as e:
        print(f"❌ Error getting cashout history: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get cashout history: {str(e)}")


# ============================================================================
# NEW: Per-Transaction HIT Cashout System (V2)
# ============================================================================

@app.post("/api/wallet/cashout/v2")
async def cashout_v2(
    request: Request,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_session)
):
    """
    NEW cashout system using per-transaction private HITs.
    
    Each cashout creates a private HIT visible only to the requesting worker.
    This eliminates:
    - MaxAssignments exhaustion issues
    - "No HITs available" errors
    - HITGroupId vs HITId confusion
    - Complex standing HIT management
    
    Benefits:
    - Creates a new private HIT for each cashout
    - Worker-specific (only the cashout requester can see it)
    - Scalable to unlimited cashouts
    - Auto-cleanup after completion
    
    This is the RECOMMENDED cashout method going forward.
    """
    from .cashout_endpoint_v2 import request_cashout_v2
    return await request_cashout_v2(request, current_user, db)


@app.get("/api/wallet/cashout-status/{transaction_id}")
async def get_cashout_status(
    transaction_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_session)
):
    """
    Get status of a specific cashout transaction.
    
    Args:
        transaction_id: Transaction UUID
        current_user: Current authenticated user
        db: Database session
    
    Returns:
        Transaction status information
    """
    import uuid as uuid_module
    from .cashout_service import check_cashout_status, CashoutError
    
    try:
        transaction_uuid = uuid_module.UUID(transaction_id)
        status_info = await check_cashout_status(transaction_id=transaction_uuid, db=db)
        
        # Verify transaction belongs to current user
        from .database import CashoutTransaction
        result = await db.execute(
            select(CashoutTransaction).where(CashoutTransaction.id == transaction_uuid)
        )
        transaction = result.scalar_one_or_none()
        
        if not transaction or transaction.user_id != current_user.id:
            raise HTTPException(status_code=404, detail="Transaction not found")
        
        return status_info
        
    except CashoutError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid transaction ID")
    except Exception as e:
        print(f"❌ Error getting cashout status: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get cashout status: {str(e)}")


@app.post("/api/wallet/cashout-cancel/{transaction_id}")
async def cancel_cashout_request(
    transaction_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_session)
):
    """
    Cancel a pending cashout transaction and return gems to user.
    Only PENDING transactions can be cancelled.
    Only the transaction owner can cancel their own transactions.
    
    Args:
        transaction_id: Transaction UUID to cancel
        current_user: Current authenticated user
        db: Database session
        
    Returns:
        Cancellation confirmation with returned gems
    """
    from .cashout_cancel_service import cancel_cashout_transaction
    import uuid as uuid_module
    import traceback
    
    try:
        # Parse transaction ID
        try:
            transaction_uuid = uuid_module.UUID(transaction_id)
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid transaction ID format")
        
        # Use the new cancellation service
        result = await cancel_cashout_transaction(
            transaction_id=str(transaction_uuid),
            user=current_user,
            db=db,
            reason="User requested cancellation"
        )
        
        return result
        
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        print(f"❌ Error cancelling cashout: {e}")
        print(f"   Stack trace: {traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=f"Failed to cancel cashout: {str(e)}")


@app.post("/api/wallet/redeem")
async def redeem_cashout(
    request: Request,
    db: AsyncSession = Depends(get_async_session)
):
    """
    Redeem a cashout code (called from MTurk HIT).
    Validates code and processes payment immediately.
    
    Args:
        request: Request with redemption_code, worker_id, assignment_id, hit_id
        db: Database session
    
    Returns:
        Redemption result
    """
    from .cashout_service import redeem_cashout_code, CashoutError
    
    body = await request.json()
    redemption_code = body.get('redemption_code', '').strip()
    worker_id = body.get('worker_id', '').strip()
    assignment_id = body.get('assignment_id', '').strip()
    hit_id = body.get('hit_id', '').strip()
    
    if not all([redemption_code, worker_id, assignment_id, hit_id]):
        raise HTTPException(status_code=400, detail="Missing required fields")
    
    try:
        result = await redeem_cashout_code(
            redemption_code=redemption_code,
            worker_id=worker_id,
            assignment_id=assignment_id,
            hit_id=hit_id,
            db=db
        )
        
        return result
        
    except CashoutError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        print(f"❌ Error redeeming cashout: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to process redemption: {str(e)}")


# ============================================================================
# Session Management API Endpoints
# ============================================================================

@app.get("/api/sessions")
async def list_sessions(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_session)
):
    """
    List sessions for current user. Admins see all sessions.
    
    Args:
        current_user: Current authenticated user
        db: Database session
    
    Returns:
        List of sessions
    """
    if current_user.role == UserRole.ADMIN:
        # Admins see all sessions
        result = await db.execute(
            select(DBSession).order_by(desc(DBSession.completed_at))
        )
    else:
        # Regular users see sessions where they're the owner OR where they played
        from .database import SessionPlayer
        from sqlalchemy import or_
        
        # Get sessions where user is owner OR participated as a player
        result = await db.execute(
            select(DBSession)
            .outerjoin(SessionPlayer, SessionPlayer.session_id == DBSession.id)
            .where(
                or_(
                    DBSession.user_id == current_user.id,
                    SessionPlayer.user_id == current_user.id
                )
            )
            .order_by(desc(DBSession.completed_at))
            .distinct()
        )
    
    sessions = result.scalars().all()
    
    return {
        "sessions": [
            {
                "id": str(s.id),
                "room_code": s.room_code,
                "completion_key": s.completion_key,
                "language": s.language,
                "total_players": s.total_players,
                "num_human_players": s.num_human_players,
                "discussion_duration": s.discussion_duration,
                "voting_duration": s.voting_duration,
                "completed_at": s.completed_at.isoformat(),
                "payment_status": s.payment_status.value,
                "payment_amount": float(s.payment_amount) if s.payment_amount else None,
                "calculated_earnings": float(getattr(s, 'calculated_earnings', None)) if getattr(s, 'calculated_earnings', None) else None,
                "claimed_at": s.claimed_at.isoformat() if s.claimed_at else None
            }
            for s in sessions
        ]
    }


@app.get("/api/sessions/{session_id}")
async def get_session_detail(
    session_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_session)
):
    """
    Get detailed session information including chat history.
    
    Args:
        session_id: Session UUID
        current_user: Current authenticated user
        db: Database session
    
    Returns:
        Detailed session information
    """
    # Convert session_id to UUID
    import uuid as uuid_lib
    try:
        session_uuid = uuid_lib.UUID(session_id)
    except (ValueError, AttributeError):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid session ID format"
        )
    
    # Get session from database
    result = await db.execute(
        select(DBSession).where(DBSession.id == session_uuid)
    )
    session = result.scalar_one_or_none()
    
    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Session not found"
        )
    
    # Check authorization
    if current_user.role != UserRole.ADMIN:
        # Authorized if user is the session owner OR participated as a player
        is_owner = session.user_id == current_user.id
        is_participant = False
        if not is_owner:
            try:
                from .database import SessionPlayer
                part_result = await db.execute(
                    select(SessionPlayer).where(
                        SessionPlayer.session_id == session_uuid,
                        SessionPlayer.user_id == current_user.id
                    )
                )
                is_participant = part_result.scalar_one_or_none() is not None
            except Exception as e:
                print(f"⚠️ Authorization check failed: {e}")
        
        if not (is_owner or is_participant):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not authorized to view this session"
            )
    
    # Load chat history from JSON file
    try:
        with open(session.stats_file_path, 'r') as f:
            stats_data = json.load(f)
    except Exception as e:
        print(f"Error loading stats file: {e}")
        stats_data = {}
    
    # Get player identification - which player was the current user?
    from .database import SessionPlayer
    current_user_player_id = None
    try:
        player_result = await db.execute(
            select(SessionPlayer).where(
                SessionPlayer.session_id == session_uuid,
                SessionPlayer.user_id == current_user.id
            )
        )
        user_player = player_result.scalar_one_or_none()
        if user_player:
            current_user_player_id = user_player.player_id
    except Exception as e:
        print(f"Error getting player identification: {e}")
    
    # Get player-user mappings (for admins)
    player_mappings = []
    if current_user.role == UserRole.ADMIN:
        try:
            players_result = await db.execute(
                select(SessionPlayer).where(SessionPlayer.session_id == session_uuid)
            )
            session_players = players_result.scalars().all()
            
            for sp in session_players:
                mapping = {
                    "player_id": sp.player_id,
                    "role": sp.role,
                    "user_id": None,
                    "user_name": None
                }
                
                if sp.user_id:
                    user_result = await db.execute(
                        select(User).where(User.id == sp.user_id)
                    )
                    player_user = user_result.scalar_one_or_none()
                    if player_user:
                        mapping["user_id"] = str(player_user.id)
                        mapping["user_name"] = player_user.user_id
                
                player_mappings.append(mapping)
        except Exception as e:
            print(f"Error getting player mappings: {e}")
    
    return {
        "id": str(session.id),
        "room_code": session.room_code,
        "completion_key": session.completion_key,
        "language": session.language,
        "total_players": session.total_players,
        "num_human_players": session.num_human_players,
        "discussion_duration": session.discussion_duration,
        "voting_duration": session.voting_duration,
        "completed_at": session.completed_at.isoformat(),
        "payment_status": session.payment_status.value,
        "payment_amount": float(session.payment_amount) if session.payment_amount else None,
        "claimed_at": session.claimed_at.isoformat() if session.claimed_at else None,
        "stats": stats_data,
        "current_user_player_id": current_user_player_id,
        "player_mappings": player_mappings,
        # MTurk information
        "mturk_worker_id": session.mturk_worker_id,
        "mturk_assignment_id": session.mturk_assignment_id,
        "mturk_hit_id": session.mturk_hit_id,
        "mturk_payment_sent": bool(session.mturk_payment_sent),
        "mturk_bonus_sent": bool(session.mturk_bonus_sent),
        # Gem economy information
        "calculated_earnings": float(session.calculated_earnings) if session.calculated_earnings else None
    }


@app.post("/api/sessions/claim")
async def claim_completion_key(
    request: ClaimKeyRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_session)
):
    """
    Manually claim a completion key by entering it.
    Prevents duplicate claims.
    
    Args:
        request: Completion key to claim
        current_user: Current authenticated user
        db: Database session
    
    Returns:
        Success message and session info
    """
    # Verify completion key
    try:
        key_data = decode_completion_key(request.completion_key)
        session_id = key_data['session_id']
    except HTTPException as e:
        raise e
    
    # Find session in database (convert string to UUID)
    import uuid as uuid_lib
    try:
        session_uuid = uuid_lib.UUID(session_id)
    except (ValueError, AttributeError):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid session ID format"
        )
    
    result = await db.execute(
        select(DBSession).where(DBSession.id == session_uuid)
    )
    session = result.scalar_one_or_none()
    
    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Session not found"
        )
    
    # Check if already claimed
    if session.user_id is not None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="This completion key has already been claimed"
        )
    
    # Claim the session
    session.user_id = current_user.id
    session.claimed_at = _time.time()
    await db.commit()
    await db.refresh(session)
    
    return {
        "success": True,
        "message": "Completion key claimed successfully",
        "session": {
            "id": str(session.id),
            "room_code": session.room_code,
            "language": session.language,
            "completed_at": session.completed_at.isoformat(),
            "payment_status": session.payment_status.value
        }
    }


# ============================================================================
# Admin API Endpoints
# ============================================================================

@app.get("/api/admin/dashboard")
async def admin_dashboard(
    admin_user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_async_session)
):
    """
    Get admin dashboard statistics.
    
    Args:
        admin_user: Current admin user
        db: Database session
    
    Returns:
        Dashboard statistics
    """
    # Total sessions
    total_sessions = await db.execute(select(DBSession))
    total_count = len(total_sessions.scalars().all())
    
    # Pending payment sessions
    pending_sessions = await db.execute(
        select(DBSession).where(DBSession.payment_status == PaymentStatus.PENDING)
    )
    pending_count = len(pending_sessions.scalars().all())
    
    # Paid sessions
    paid_sessions = await db.execute(
        select(DBSession).where(DBSession.payment_status == PaymentStatus.PAID)
    )
    paid_count = len(paid_sessions.scalars().all())
    
    # Unclaimed sessions
    unclaimed_sessions = await db.execute(
        select(DBSession).where(DBSession.user_id == None)
    )
    unclaimed_count = len(unclaimed_sessions.scalars().all())
    
    return {
        "total_sessions": total_count,
        "pending_payments": pending_count,
        "paid_sessions": paid_count,
        "unclaimed_sessions": unclaimed_count
    }


@app.get("/api/admin/analytics")
async def admin_analytics(
    time_range: str = "all",  # "24h", "7d", "30d", "all"
    admin_user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_async_session)
):
    """
    Get analytics and token usage statistics for admin dashboard.
    
    Args:
        time_range: Time range filter ("24h", "7d", "30d", "all")
        admin_user: Current admin user
        db: Database session
    
    Returns:
        Analytics data with token usage, costs, and session statistics
    """
    from sqlalchemy import func
    from datetime import datetime, timedelta
    from .database import AIAgentUsage
    from .pricing import format_cost, format_tokens
    from decimal import Decimal
    
    # Calculate time filter
    now = datetime.utcnow()
    if time_range == "24h":
        time_filter = now - timedelta(hours=24)
    elif time_range == "7d":
        time_filter = now - timedelta(days=7)
    elif time_range == "30d":
        time_filter = now - timedelta(days=30)
    else:
        time_filter = None
    
    # Build base query with time filter
    base_query = select(DBSession)
    if time_filter:
        base_query = base_query.where(DBSession.completed_at >= time_filter)
    
    # Get all sessions for the time range
    result = await db.execute(base_query)
    sessions = result.scalars().all()
    
    # Calculate aggregate statistics
    total_sessions = len(sessions)
    total_input_tokens = sum(s.total_input_tokens for s in sessions)
    total_output_tokens = sum(s.total_output_tokens for s in sessions)
    total_cost = sum(s.total_cost for s in sessions)
    
    # Cost per session statistics
    session_costs = [float(s.total_cost) for s in sessions if s.total_cost > 0]
    avg_cost_per_session = sum(session_costs) / len(session_costs) if session_costs else 0
    median_cost_per_session = sorted(session_costs)[len(session_costs) // 2] if session_costs else 0
    min_cost = min(session_costs) if session_costs else 0
    max_cost = max(session_costs) if session_costs else 0
    
    # Token usage by model
    model_stats = {}
    for session in sessions:
        model = session.model_name or "unknown"
        if model not in model_stats:
            model_stats[model] = {
                "sessions": 0,
                "input_tokens": 0,
                "output_tokens": 0,
                "cost": Decimal(0)
            }
        model_stats[model]["sessions"] += 1
        model_stats[model]["input_tokens"] += session.total_input_tokens
        model_stats[model]["output_tokens"] += session.total_output_tokens
        model_stats[model]["cost"] += session.total_cost
    
    # Cost over time (hourly for 24h, daily for longer periods)
    if time_range == "24h":
        # Hourly breakdown
        time_series = {}
        for session in sessions:
            hour_key = session.completed_at.strftime("%Y-%m-%d %H:00")
            if hour_key not in time_series:
                time_series[hour_key] = {"cost": Decimal(0), "sessions": 0, "tokens": 0}
            time_series[hour_key]["cost"] += session.total_cost
            time_series[hour_key]["sessions"] += 1
            time_series[hour_key]["tokens"] += session.total_input_tokens + session.total_output_tokens
    else:
        # Daily breakdown
        time_series = {}
        for session in sessions:
            day_key = session.completed_at.strftime("%Y-%m-%d")
            if day_key not in time_series:
                time_series[day_key] = {"cost": Decimal(0), "sessions": 0, "tokens": 0}
            time_series[day_key]["cost"] += session.total_cost
            time_series[day_key]["sessions"] += 1
            time_series[day_key]["tokens"] += session.total_input_tokens + session.total_output_tokens
    
    # Convert time series to list format
    time_series_list = [
        {
            "timestamp": key,
            "cost": float(value["cost"]),
            "sessions": value["sessions"],
            "tokens": value["tokens"]
        }
        for key, value in sorted(time_series.items())
    ]
    
    # Recent high-cost sessions
    high_cost_sessions = sorted(sessions, key=lambda s: s.total_cost, reverse=True)[:10]
    high_cost_list = [
        {
            "session_id": str(s.id),
            "room_code": s.room_code,
            "cost": float(s.total_cost),
            "input_tokens": s.total_input_tokens,
            "output_tokens": s.total_output_tokens,
            "model": s.model_name,
            "completed_at": s.completed_at.isoformat()
        }
        for s in high_cost_sessions
    ]
    
    return {
        "time_range": time_range,
        "summary": {
            "total_sessions": total_sessions,
            "total_input_tokens": total_input_tokens,
            "total_output_tokens": total_output_tokens,
            "total_tokens": total_input_tokens + total_output_tokens,
            "total_cost": float(total_cost),
            "avg_cost_per_session": avg_cost_per_session,
            "median_cost_per_session": median_cost_per_session,
            "min_cost": min_cost,
            "max_cost": max_cost,
            # Formatted strings for display
            "total_cost_formatted": format_cost(total_cost),
            "total_tokens_formatted": format_tokens(total_input_tokens + total_output_tokens)
        },
        "by_model": {
            model: {
                "sessions": stats["sessions"],
                "input_tokens": stats["input_tokens"],
                "output_tokens": stats["output_tokens"],
                "total_tokens": stats["input_tokens"] + stats["output_tokens"],
                "cost": float(stats["cost"]),
                "cost_formatted": format_cost(stats["cost"])
            }
            for model, stats in model_stats.items()
        },
        "time_series": time_series_list,
        "high_cost_sessions": high_cost_list
    }


# ============================================================================
# MTurk Admin API Endpoints
# ============================================================================

@app.post("/api/admin/garbage-collect-hits")
async def admin_garbage_collect_hits(
    age_hours: int = 48,
    admin_user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_async_session)
):
    """
    Admin endpoint to garbage collect old, abandoned HITs.
    
    Finds and cleans up transactions with HITs that are:
    - Status: PENDING, HIT_CREATED, or PROCESSING  
    - Older than specified hours
    - No completion
    
    For each, it will:
    - Delete/expire the HIT
    - Cancel the transaction
    - Refund gems
    
    Args:
        age_hours: How old (in hours) before considering abandoned (default: 48)
        admin_user: Admin user (required)
        db: Database session
        
    Returns:
        Cleanup statistics
    """
    from .cashout_cancel_service import garbage_collect_old_hits
    
    print(f"\n🗑️  Admin {admin_user.user_id} triggered garbage collection")
    print(f"   Age threshold: {age_hours} hours")
    
    try:
        result = await garbage_collect_old_hits(db=db, age_hours=age_hours)
        return result
    except Exception as e:
        print(f"❌ Error during garbage collection: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Garbage collection failed: {str(e)}")


@app.post("/api/admin/mturk/sessions/{session_id}/approve-payment")
async def approve_mturk_payment(
    session_id: str,
    admin_user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_async_session)
):
    """
    Approve MTurk assignment and send bonus payment.
    Triggers MTurk API calls to approve assignment (base pay) and send bonus.
    
    Args:
        session_id: Session UUID
        admin_user: Current admin user
        db: Database session
    
    Returns:
        Payment result with approval and bonus status
    """
    from decimal import Decimal
    from .mturk_api import process_payment
    
    # Convert session_id to UUID
    try:
        session_uuid = uuid_lib.UUID(session_id)
    except (ValueError, AttributeError):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid session ID format"
        )
    
    # Get session
    result = await db.execute(
        select(DBSession).where(DBSession.id == session_uuid)
    )
    session = result.scalar_one_or_none()
    
    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Session not found"
        )
    
    # Check if this is an MTurk session
    if not session.mturk_assignment_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="This is not an MTurk session"
        )
    
    # Check if already paid
    if session.mturk_payment_sent:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Payment already sent for this session"
        )
    
    # Check if calculated earnings exist
    if not session.calculated_earnings:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No calculated earnings for this session"
        )
    
    try:
        # Process payment via MTurk API with max_bonus cap
        from .config import MTURK_MAX_BONUS, MTURK_BASE_PAY
        from .mturk_api import get_mturk_client
        
        client = get_mturk_client()
        base_pay = Decimal(str(MTURK_BASE_PAY))
        max_bonus = Decimal(str(MTURK_MAX_BONUS))
        calculated_earnings = Decimal(str(session.calculated_earnings))
        
        # Calculate bonus amount
        raw_bonus = calculated_earnings - base_pay
        bonus_amount = max(Decimal('0'), min(raw_bonus, max_bonus))
        
        # Process payment via MTurk API
        payment_result = process_payment(
            assignment_id=session.mturk_assignment_id,
            worker_id=session.mturk_worker_id,
            calculated_earnings=calculated_earnings,
            max_bonus=max_bonus
        )
        
        # Only update database if payment was successful
        if payment_result['approved']:
            # Update session with payment status
            session.mturk_payment_sent = 1
            session.mturk_bonus_sent = 1 if payment_result.get('bonus_sent', False) else 0
            session.payment_status = PaymentStatus.PAID
            session.payment_amount = session.calculated_earnings
            
            await db.commit()
            await db.refresh(session)
            
            return {
                "success": True,
                "message": "MTurk payment processed successfully",
                "base_pay": float(base_pay),
                "bonus_amount": float(bonus_amount),
                "total_paid": float(base_pay + bonus_amount),
                "payment_result": payment_result,
                "session": {
                    "id": str(session.id),
                    "room_code": session.room_code,
                    "worker_id": session.mturk_worker_id,
                    "assignment_id": session.mturk_assignment_id,
                    "payment_amount": float(session.payment_amount),
                    "payment_status": session.payment_status.value
                }
            }
        else:
            # Payment approval failed, rollback any changes
            await db.rollback()
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="MTurk assignment approval failed. Payment was not processed."
            )
        
    except HTTPException:
        # Re-raise HTTP exceptions
        raise
    except Exception as e:
        # Rollback on any error
        await db.rollback()
        
        # Provide more specific error messages
        error_str = str(e)
        if "InvalidParameterValue" in error_str:
            detail = "Invalid MTurk parameters. Please check worker_id and assignment_id."
        elif "RequestError" in error_str or "credentials" in error_str.lower():
            detail = "MTurk API authentication failed. Please check AWS credentials."
        elif "InsufficientFunds" in error_str:
            detail = "Insufficient funds in MTurk account. Please add funds to continue."
        elif "AssignmentAlreadyApproved" in error_str:
            detail = "This assignment has already been approved in MTurk."
        else:
            detail = f"MTurk API error: {error_str}"
        
        print(f"❌ MTurk payment error: {e}")
        import traceback
        traceback.print_exc()
        
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=detail
        )


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
            - language: Room language - "english" or "korean" (default "english")
            - discussion_duration: Discussion time in seconds (60, 180, or 240, default 180)
            - voting_duration: Voting time in seconds (30, 60, or 120, default 60)
    
    Returns:
        Room creation response with room_code and room_name
    """
    max_humans = room_data.get('max_humans', 1)
    total_players = room_data.get('total_players', 5)
    language = room_data.get('language', 'english')
    discussion_duration = room_data.get('discussion_duration', 180)
    voting_duration = room_data.get('voting_duration', 60)
    
    # Validation
    if not (1 <= max_humans <= 4):
        return {"success": False, "error": "max_humans must be between 1 and 4"}
    
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
    
    # Create initial game state with properly numbered AI players and language
    state = create_game_for_room(room_code, num_ai_players, ai_player_ids, language)
    
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
        'current_humans': [],
        'available_numbers': available_numbers,  # Numbers reserved for human players
        'language': language,  # Store room language
        'discussion_duration': discussion_duration,  # Store discussion duration
        'voting_duration': voting_duration  # Store voting duration
    }
    
    # Initialize lock for this room
    if room_code not in room_locks:
        room_locks[room_code] = asyncio.Lock()
    
    print(f"🎮 Created room {room_code} ({room_name}): {max_humans} humans, {total_players} total, language: {language}, discussion: {discussion_duration}s, voting: {voting_duration}s")
    print(f"🔍 Verifying room dict after creation - discussion_duration: {rooms[room_code].get('discussion_duration')}, voting_duration: {rooms[room_code].get('voting_duration')}")
    
    # Assign a player number for the creator (they'll get it when they join)
    # Return the first available number so they know what to expect
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
        "voting_duration": voting_duration
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
            'created_at': data['created_at'],
            'language': data.get('language', 'english'),
            'discussion_duration': data.get('discussion_duration', 180),
            'voting_duration': data.get('voting_duration', 60)
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
        "created_at": room['created_at'],
        "language": room.get('language', 'english'),
        "discussion_duration": room.get('discussion_duration', 180),
        "voting_duration": room.get('voting_duration', 60)
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
async def join_room(
    room_code: str, 
    player_data: dict,
    current_user: User = Depends(get_current_user_optional)
):
    """
    Join a room for Streamlit client (with matching room system support).
    Player names are auto-assigned as random numbers.
    
    Args:
        room_code: Room identifier
        player_data: Dict (player_id ignored, auto-assigned)
        current_user: Optional authenticated user
    
    Returns:
        Room status and initial game state with assigned player_id
    """
    
    # Log authentication status
    if current_user:
        print(f"🔐 User '{current_user.user_id}' (ID: {str(current_user.id)[:8]}...) joining room {room_code} via API")
    else:
        print(f"🔓 Anonymous user joining room {room_code} via API")
    
    # Check if room exists
    if room_code not in rooms:
        print(f"⚠️ Room {room_code} does NOT exist, creating legacy room")
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
            'player_user_map': {},  # Maps player_id -> user_id (for authenticated users)
            'current_humans': [],
            'available_numbers': [],  # All assigned for legacy rooms
            'discussion_duration': DISCUSSION_TIME,  # Use default config for legacy rooms
            'voting_duration': VOTING_TIME  # Use default config for legacy rooms
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
        await asyncio.sleep(0.75)  # Small delay
        asyncio.create_task(trigger_agent_decisions(room_code))
    
    room = rooms[room_code]
    print(f"🔍 Room {room_code} exists - discussion_duration: {room.get('discussion_duration', 'NOT SET')}, voting_duration: {room.get('voting_duration', 'NOT SET')}")
    
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
    
    # Store user mapping if authenticated
    if current_user:
        user_id_str = str(current_user.id)
        room['player_user_map'][player_id] = user_id_str
        print(f"👤 ✅ Player {player_id} joined room {room_code} ({len(room['current_humans'])}/{max_humans}) - Mapped to user {user_id_str[:8]}...")
        print(f"📋 Current player_user_map: {room['player_user_map']}")
    else:
        print(f"👤 Player {player_id} joined room {room_code} ({len(room['current_humans'])}/{max_humans}) - Anonymous")
    
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
            print(f"🚀 Starting game phases - discussion_duration: {room.get('discussion_duration', 'NOT SET')}, voting_duration: {room.get('voting_duration', 'NOT SET')}")
            asyncio.create_task(run_discussion_phase(room_code))
            # Trigger active decision-making for AI responses
            await asyncio.sleep(0.75)  # Small delay
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
