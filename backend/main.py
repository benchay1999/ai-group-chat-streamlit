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
from sqlalchemy import select, update, desc, func
import uuid as uuid_lib

from .langgraph_game import (
    create_game_for_room,
    create_game_graph_for_room,
    process_human_message,
    process_human_vote
)
from .langgraph_state import GameState, Phase
from .config import (
    NUM_AI_PLAYERS, DISCUSSION_TIME, VOTING_TIME, OPENAI_API_KEYS,
    STAKE_PERCENTAGE, SINGLE_HUMAN_BASE_GEMS, MULTI_HUMAN_BASE_GEMS
)
from .api_key_manager import APIKeyManager, APIKeyManagerError
from .database import (
    init_db, close_db, get_async_session, 
    User, Session as DBSession, UserRole, PaymentStatus, RoomStake
)
from .auth import (
    hash_password, authenticate_user, create_access_token,
    get_current_user, get_current_user_optional, require_admin,
    register_or_login_mturk_worker
)
from .security_monitor import (
    get_security_monitor, log_failed_login, log_rate_limit_violation,
    log_invalid_token, log_admin_access_attempt, log_unusual_cashout
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
default_origins = 'http://localhost:5173,http://localhost:3000,https://ai-group-chat.netlify.app'
allowed_origins_str = os.getenv('CORS_ALLOWED_ORIGINS', default_origins)
allowed_origins = [origin.strip() for origin in allowed_origins_str.split(',')]

# Security validation: Never allow wildcard origins
if '*' in allowed_origins:
    raise ValueError(
        "SECURITY ERROR: Wildcard CORS origins ('*') are not allowed. "
        "Please specify explicit origins in CORS_ALLOWED_ORIGINS environment variable."
    )

# In production, MTURK_ENVIRONMENT should be set, and we should restrict CORS
if os.getenv('MTURK_ENVIRONMENT') == 'production':
    # In production, only allow HTTPS origins
    for origin in allowed_origins:
        if origin.startswith('http://') and 'localhost' not in origin:
            raise ValueError(
                f"SECURITY ERROR: HTTP origin '{origin}' not allowed in production. "
                f"All production origins must use HTTPS."
            )
    print(f"🔒 CORS configured for production with origins: {allowed_origins}")
else:
    # In development/sandbox, allow localhost origins
    print(f"🔓 CORS configured for development with origins: {allowed_origins}")

print(f"🌐 CORS allowed origins: {allowed_origins}")

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["*"],  # Allow all headers to be exposed
)


# ============================================================================
# Rate Limiting Middleware
# ============================================================================

@app.middleware("http")
async def rate_limit_middleware(request: Request, call_next):
    """
    Global rate limiting middleware for API endpoints.
    Skips static files and docs.
    """
    path = request.url.path
    
    # Skip rate limiting for:
    # 1. Static files (usually handled by frontend server in prod, but good to safe)
    # 2. Documentation endpoints
    # 3. WebSocket upgrade requests (handled by websocket_connect_rate_limiter)
    if (path.startswith("/static") or 
        path.startswith("/docs") or 
        path.startswith("/openapi.json") or 
        "ws" in request.scope.get("type", "")):
        return await call_next(request)
    
    # Apply global API rate limit
    client_ip = request.client.host
    if not api_rate_limiter.is_allowed(client_ip):
        return JSONResponse(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            content={
                "success": False,
                "error": "Too many requests",
                "detail": "You are sending too many requests. Please wait a moment."
            }
        )
        
    response = await call_next(request)
    return response


# ============================================================================
# Exception Handlers
# ============================================================================

from fastapi.responses import JSONResponse
from fastapi import Request

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """
    Global exception handler that ensures CORS headers are included in error responses.
    This prevents CORS errors when backend exceptions occur.
    """
    print(f"❌ Global exception handler caught: {type(exc).__name__}: {str(exc)}")
    import traceback
    traceback.print_exc()
    
    # Determine origin for CORS
    origin = request.headers.get("origin")
    
    # Create error response
    response = JSONResponse(
        status_code=500,
        content={
            "success": False,
            "error": "Internal server error",
            "detail": str(exc)[:200]  # Limit error message length
        }
    )
    
    # Add CORS headers
    if origin and (origin in allowed_origins or "*" in allowed_origins):
        response.headers["Access-Control-Allow-Origin"] = origin
        response.headers["Access-Control-Allow-Credentials"] = "true"
        response.headers["Access-Control-Allow-Methods"] = "*"
        response.headers["Access-Control-Allow-Headers"] = "*"
    
    return response


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

# Rate limiters for security-critical endpoints
# NOTE: These limits are per IP address (or per user for cashout)
# 
# For 100-120 concurrent users, limits should allow legitimate traffic
# while still preventing abuse. Adjust based on your deployment:
# - Single public IP (e.g., corporate network): Higher limits needed
# - Distributed users (home networks): Lower limits acceptable
#
# MTurk registration: 20 requests per minute per IP
mturk_rate_limiter = SimpleRateLimiter(max_requests=20, window_seconds=60)
# Login: 30 attempts per minute per IP (allow rapid legitimate logins)
login_rate_limiter = SimpleRateLimiter(max_requests=30, window_seconds=60)
# Registration: 20 per minute per IP (allow concurrent user onboarding)
register_rate_limiter = SimpleRateLimiter(max_requests=20, window_seconds=60)
# Cashout: 10 per minute per user (prevent abuse)
cashout_rate_limiter = SimpleRateLimiter(max_requests=10, window_seconds=60)
# WebSocket connection: 5 per 10 seconds per IP (prevent DOS)
# Allows quick reloads but stops aggressive connection flooding
websocket_connect_rate_limiter = SimpleRateLimiter(max_requests=5, window_seconds=10)
# General API: 100 requests per minute per IP (prevent API flooding)
# Covers polling endpoints (Lobby, Waiting, Dashboard)
api_rate_limiter = SimpleRateLimiter(max_requests=100, window_seconds=60)


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
    
    # Start periodic room cleanup task
    asyncio.create_task(periodic_room_cleanup())
    print("🧹 Started periodic room cleanup task")
    
    # Start room health monitoring task
    asyncio.create_task(monitor_room_health())
    print("🏥 Started room health monitoring task")
    
    # Start periodic rate limiter cleanup task
    asyncio.create_task(periodic_rate_limiter_cleanup())
    print("🧹 Started periodic rate limiter cleanup task")
    
    print("🚀 Application started successfully")


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


async def periodic_rate_limiter_cleanup():
    """
    Background task to clean up old rate limiter entries.
    Runs every 1 hour.
    Prevents memory leaks from indefinite storage of timestamps.
    """
    while True:
        try:
            await asyncio.sleep(3600)  # 1 hour
            
            print("\n🧹 Running rate limiter cleanup...")
            
            # Clean up all global rate limiters
            mturk_rate_limiter.cleanup_old_entries()
            login_rate_limiter.cleanup_old_entries()
            register_rate_limiter.cleanup_old_entries()
            cashout_rate_limiter.cleanup_old_entries()
            websocket_connect_rate_limiter.cleanup_old_entries()
            api_rate_limiter.cleanup_old_entries()
            
            print("✅ Rate limiter cleanup complete")
            
        except Exception as e:
            print(f"❌ Error in rate limiter cleanup: {e}")
            import traceback
            traceback.print_exc()


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
#     'human_overflow_counter': int,      # Counter for H1, H2, etc. fallback numbering
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


def update_user_activity(user_id: str):
    """Update last activity timestamp for a user."""
    user_activity[user_id] = time.time()


def get_online_users_count() -> int:
    """
    Get count of users active within the online threshold.
    Cleans up stale entries (>5 minutes inactive).
    """
    current_time = time.time()
    online_count = 0
    stale_users = []
    
    for user_id, last_seen in user_activity.items():
        if current_time - last_seen <= ONLINE_THRESHOLD_SECONDS:
            online_count += 1
        elif current_time - last_seen > 300:  # Remove after 5 minutes of inactivity
            stale_users.append(user_id)
    
    # Cleanup stale entries
    for user_id in stale_users:
        user_activity.pop(user_id, None)
    
    return online_count

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


# ============================================================================
# API Key Assignment Helper
# ============================================================================

def get_api_key_for_room() -> tuple:
    """
    Get the next API key for a new room.
    Handles errors gracefully and provides clear error messages.
    
    Returns:
        Tuple of (api_key, api_key_index) or raises HTTPException
        
    Raises:
        HTTPException: If no API keys are available or assignment fails
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


# ============================================================================
# Room Helper Functions for Backward Compatibility
# ============================================================================

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
        await asyncio.sleep(random.uniform(4, 8))
        
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
    Broadcasts server time remaining every 5 seconds for synchronization.
    
    Args:
        room_code: Room identifier
    """
    # Get room-specific discussion time (fallback to global config)
    discussion_time = rooms[room_code].get('discussion_duration', DISCUSSION_TIME)
    print(f"⏱️ Starting discussion phase for room {room_code}: {discussion_time} seconds")
    
    # Store phase start time for accurate tracking
    phase_start = _time.time()
    rooms[room_code]['phase_start_time'] = phase_start
    
    # Start proactive engagement task
    engagement_task = asyncio.create_task(proactive_agent_engagement(room_code))
    
    # Countdown with periodic broadcasts for synchronization
    # Use actual wall clock time to avoid drift from sleep inaccuracies
    while True:
        # Calculate elapsed time from wall clock (accurate)
        elapsed = _time.time() - phase_start
        remaining = max(0, discussion_time - elapsed)
        
        # Exit if time is up
        if remaining <= 0:
            break
        
        # Broadcast current server time to all clients
        await broadcast_to_room(room_code, {
            "type": "timer_sync",
            "phase": "Discussion",
            "time_remaining": int(remaining)  # Round to int for display
        })
        
        # Sleep for up to 5 seconds (or remaining time if less)
        sleep_duration = min(5.0, remaining)
        await asyncio.sleep(sleep_duration)
        
        # Check if room still exists
        if room_code not in rooms:
            engagement_task.cancel()
            return
    
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
        
        # Count human players to determine voting rules
        num_human_players = len([p for p in state['players'] if p['role'] == 'human' and not p['eliminated']])
        
        # AI agents only vote in SINGLE-HUMAN games
        # In multi-human games, only humans vote
        if num_human_players == 1:
            # Single-human game: AI agents participate in voting
            state['pending_ai_votes'] = [
                p['id'] for p in state['players']
                if p['role'] == 'ai' and not p['eliminated']
            ]
            print(f"🤖 Single-human game: {len(state['pending_ai_votes'])} AI agents will vote")
        else:
            # Multi-human game: only humans vote, AI agents don't vote
            state['pending_ai_votes'] = []
            print(f"👥 Multi-human game ({num_human_players} humans): Only humans vote, AI agents will not vote")
        
        state['votes'] = {}
        
        # Save state BEFORE broadcasting to ensure checks see VOTING phase
        rooms[room_code]['state'] = state
        
        # Broadcast phase change with voting duration and num_human_players
        voting_duration = rooms[room_code].get('voting_duration', VOTING_TIME)
        await broadcast_to_room(room_code, {
            "type": "phase",
            "phase": "Voting",
            "message": "Discussion ended. Time to vote.",
            "voting_duration": voting_duration,
            "num_human_players": num_human_players
        })
        
        # Immediately send timer sync for phase transition (FIX: Prevent timer desync during phase change)
        await broadcast_to_room(room_code, {
            "type": "timer_sync",
            "phase": "Voting",
            "time_remaining": int(voting_duration)
        })
        
        print(f"✅ Phase transition complete: DISCUSSION → VOTING in room {room_code}")
        
        # Start voting phase
        asyncio.create_task(run_voting_phase(room_code))
        
        # Only trigger AI voting for single-human games
        if num_human_players == 1:
            asyncio.create_task(process_ai_votes(room_code))


async def run_voting_phase(room_code: str):
    """
    Run the voting phase for a room.
    Manages timer and triggers elimination.
    Broadcasts server time remaining every 5 seconds for synchronization.
    
    Args:
        room_code: Room identifier
    """
    # Get room-specific voting time (fallback to global config)
    voting_time = rooms[room_code].get('voting_duration', VOTING_TIME)
    print(f"🗳️ Starting voting phase for room {room_code}: {voting_time} seconds")
    
    # Store phase start time for accurate tracking
    phase_start = _time.time()
    rooms[room_code]['phase_start_time'] = phase_start
    
    # Countdown with periodic broadcasts for synchronization
    # Use actual wall clock time to avoid drift from sleep inaccuracies
    while True:
        # Calculate elapsed time from wall clock (accurate)
        elapsed = _time.time() - phase_start
        remaining = max(0, voting_time - elapsed)
        
        # Exit if time is up
        if remaining <= 0:
            break
        
        # Broadcast current server time to all clients
        await broadcast_to_room(room_code, {
            "type": "timer_sync",
            "phase": "Voting",
            "time_remaining": int(remaining)  # Round to int for display
        })
        
        # Sleep for up to 5 seconds (or remaining time if less)
        sleep_duration = min(5.0, remaining)
        await asyncio.sleep(sleep_duration)
        
        # Check if room still exists
        if room_code not in rooms:
            return
    
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
        
        # DEFENSE: Check if AI has already voted
        if ai_id in state.get('votes', {}):
            print(f"⚠️ AI {ai_id} already voted - skipping duplicate vote")
            # Remove from pending list and continue
            state['pending_ai_votes'] = state['pending_ai_votes'][1:]
            rooms[room_code]['state'] = state
            continue
        
        # Run single AI vote node in thread pool to avoid blocking
        loop = asyncio.get_event_loop()
        game_graph = rooms[room_code]['game_graph']
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
        
        # Check if voting complete (all players who should vote have voted)
        # In single-human games: All active players vote (humans + AIs)
        # In multi-human games: Only humans vote (handled in pending_ai_votes being empty)
        active_players = [p['id'] for p in state['players'] if not p['eliminated']]
        num_humans = len([p for p in state['players'] if p['role'] == 'human' and not p['eliminated']])
        
        # Single-human game: all active players vote
        required_votes = len(active_players)
        
        if len(state['votes']) >= required_votes:
            await complete_voting(room_code)
            break


async def deduct_stakes(room_code: str, db: AsyncSession) -> bool:
    """
    Deduct stakes from all players (multi-human games only).
    
    IMPORTANT: This function does NOT commit the transaction.
    The caller MUST commit the transaction to finalize deductions.
    This allows atomic deduction + reward crediting in one transaction.
    
    Args:
        room_code: Room identifier
        db: Database session (must be managed by caller)
    
    Returns:
        True if successful, False if any deduction failed
    """
    import uuid as uuid_lib
    
    if room_code not in rooms:
        print(f"❌ Room {room_code} not found for stake deduction")
        return False
    
    room_data = rooms[room_code]
    max_humans = room_data.get('max_humans', 1)
    
    # Only deduct stakes in multi-human games
    if max_humans <= 1:
        print(f"ℹ️  Single-human game, no stakes to deduct")
        return True
    
    # Use configured stake percentage (default from config if not in room)
    # Config is 0.5 (float), but room stores 50 (int). Convert to int scale safely.
    stake_percentage = room_data.get('stake_percentage', int(round(STAKE_PERCENTAGE * 100)))
    if stake_percentage == 0:
        print(f"ℹ️  No stakes configured for room {room_code}")
        return True
    
    player_stakes = room_data.get('player_stakes', {})
    player_user_map = room_data.get('player_user_map', {})
    minimum_stake = room_data.get('minimum_stake', 0)
    
    if not player_stakes:
        print(f"⚠️  No player stakes calculated for room {room_code}")
        return True
    
    print(f"💎 Deducting stakes for room {room_code}: {minimum_stake} gems per player")
    
    # Deduct stakes from each player
    deduction_records = []
    try:
        for player_id, stake_amount in player_stakes.items():
            # Get user ID from mapping
            user_id_str = player_user_map.get(player_id)
            if not user_id_str:
                print(f"⚠️  Player {player_id} not authenticated, skipping stake deduction")
                continue
            
            try:
                user_uuid = uuid_lib.UUID(user_id_str)
            except ValueError:
                print(f"❌ Invalid user ID format for player {player_id}: {user_id_str}")
                continue
            
            # Get user from database
            # CRITICAL FIX: Use row-level locking to prevent race conditions
            result = await db.execute(select(User).where(User.id == user_uuid).with_for_update())
            user = result.scalar_one_or_none()
            
            if not user:
                print(f"❌ User not found for player {player_id} (ID: {user_id_str})")
                # Rollback and return failure
                await db.rollback()
                return False
            
            # Validate user has sufficient gems
            if user.gem_balance < minimum_stake:
                print(f"❌ User {user.user_id} has insufficient gems: {user.gem_balance} < {minimum_stake}")
                await db.rollback()
                return False
            
            # Deduct minimum stake (actual winnings calculated at end)
            user.gem_balance -= minimum_stake
            
            # Create RoomStake record
            stake_record = RoomStake(
                id=uuid_lib.uuid4(),
                room_code=room_code,
                user_id=user_uuid,
                player_id=player_id,
                stake_percentage=stake_percentage,
                stake_amount=minimum_stake,
                deducted=1,  # True
                returned_amount=0,
                won_amount=0,
                created_at=datetime.utcnow()
            )
            db.add(stake_record)
            deduction_records.append(stake_record)
            
            print(f"💎 Deducted {minimum_stake} gems from {user.user_id} ({player_id}), new balance: {user.gem_balance}")
        
        # DON'T commit here - let the caller commit atomically with rewards
        # await db.commit()  # REMOVED - caller must commit
        print(f"✅ Stake deductions prepared for {len(deduction_records)} players (not committed yet)")
        
        # Don't broadcast yet - wait until transaction commits
        # The caller will broadcast after successful commit
        
        return True
        
    except Exception as e:
        print(f"❌ Error deducting stakes for room {room_code}: {e}")
        import traceback
        traceback.print_exc()
        await db.rollback()
        return False


async def calculate_game_rewards(
    room_code: str,
    room_data: dict,
    state: GameState,
    db: AsyncSession
) -> dict:
    """
    Calculate and distribute gems for completed game.
    
    Handles both single-human and multi-human games with stake system.
    
    Args:
        room_code: Room identifier
        room_data: Room metadata
        state: Current game state
        db: Database session
    
    Returns:
        Dictionary mapping player_id to reward details:
        {
            player_id: {
                'base_gems': int,
                'stake_gems': int,  # positive for won, negative for lost
                'total_gems': int,
                'is_winner': bool,
                'identification_accuracy': float,  # for multi-human
                'votes_received': int
            }
        }
    """
    from collections import Counter
    
    # Get human players
    human_players = [p for p in state['players'] if p['role'] == 'human' and not p['eliminated']]
    num_humans = len(human_players)
    human_player_ids = [p['id'] for p in human_players]
    
    # Get player_user_map to find authenticated users
    player_user_map = room_data.get('player_user_map', {})
    
    # Initialize rewards dict
    rewards = {}
    for player in state['players']:
        if player['role'] == 'human':
            rewards[player['id']] = {
                'base_gems': 0,
                'stake_gems': 0,
                'total_gems': 0,
                'is_winner': False,
                'identification_accuracy': 0.0,
                'votes_received': 0
            }
    
    # Count votes received by each player (for determining most voted)
    vote_counts = Counter()
    for voter_id, voted_for_list in state.get('votes', {}).items():
        if isinstance(voted_for_list, list):
            for voted_player in voted_for_list:
                vote_counts[voted_player] += 1
        else:
            # Backward compatibility for single votes
            vote_counts[voted_for_list] += 1
    
    # Store vote counts in rewards
    for player_id in human_player_ids:
        rewards[player_id]['votes_received'] = vote_counts.get(player_id, 0)
    
    # Identify players who actually cast a vote
    voters = state.get('votes', {})
    voted_player_ids = set(voters.keys())
    print(f"🗳️ Players who voted: {voted_player_ids}")
    
    if num_humans == 1:
        # SINGLE-HUMAN GAME: Participation-based
        # Everyone gets base gems (participation fee)
        # Winner is tracked but doesn't affect rewards
        # No stakes in single-human games
        
        if vote_counts:
            max_votes = max(vote_counts.values())
            winners = [pid for pid, count in vote_counts.items() if count == max_votes and pid in human_player_ids]
        else:
            winners = []
        
        # Everyone gets base gems (participation fee) - IF THEY VOTED
        for player_id in human_player_ids:
            if player_id in voted_player_ids:
                rewards[player_id]['base_gems'] = SINGLE_HUMAN_BASE_GEMS
            else:
                print(f"⚠️ Player {player_id} did not vote - forfeiting base gems")
                rewards[player_id]['base_gems'] = 0
            
            rewards[player_id]['stake_gems'] = 0  # No stakes
            rewards[player_id]['total_gems'] = rewards[player_id]['base_gems']
            rewards[player_id]['is_winner'] = (player_id in winners)  # Track winner for display
        
        print(f"💎 Single-human game rewards (participation-based): {rewards}")
        
    else:
        # MULTI-HUMAN GAME: Complex with partial credit
        # Base reward: 100 gems for all participants
        # Stakes: Calculated based on voting accuracy
        
        # All humans get base gems - IF THEY VOTED
        for player_id in human_player_ids:
            if player_id in voted_player_ids:
                rewards[player_id]['base_gems'] = MULTI_HUMAN_BASE_GEMS
            else:
                print(f"⚠️ Player {player_id} did not vote - forfeiting base gems")
                rewards[player_id]['base_gems'] = 0
        
        # Find player(s) with most votes
        if vote_counts:
            max_votes = max(vote_counts.values())
            top_voted_players = [pid for pid, count in vote_counts.items() if count == max_votes and pid in human_player_ids]
        else:
            top_voted_players = []
        
        # Get stake configuration
        stake_percentage = room_data.get('stake_percentage', 0)
        player_stakes = room_data.get('player_stakes', {})
        
        if stake_percentage > 0 and player_stakes:
            # Calculate minimum stake (what each player risked)
            minimum_stake = room_data.get('minimum_stake', 0)
            
            num_winners = len(top_voted_players)
            num_losers = num_humans - num_winners
            
            if num_winners > 0 and num_losers > 0:
                # NEW LOGIC: Ensures winners never lose gems
                # Step 1: All winners get their stakes back (guaranteed refund)
                # Step 2: Loser stakes are pooled and split equally among winners
                # Step 3: Each winner gets (accuracy%) of their share
                
                loser_stakes_pool = minimum_stake * num_losers
                max_share_per_winner = loser_stakes_pool / num_winners  # Equal division ceiling
                
                print(f"💎 Stake distribution:")
                print(f"   Loser pool: {loser_stakes_pool} gems ({num_losers} losers × {minimum_stake})")
                print(f"   Max per winner: {max_share_per_winner} gems ({num_winners} winners)")
                
                # For each winner, calculate identification accuracy
                total_distributed = 0
                for winner_id in top_voted_players:
                    votes_needed = num_humans - 1
                    winner_votes = state['votes'].get(winner_id, [])
                    if not isinstance(winner_votes, list):
                        winner_votes = [winner_votes] if winner_votes else []
                    
                    # Calculate correct identifications (voted for other humans, not self)
                    correct_identifications = sum(1 for v in winner_votes if v in human_player_ids and v != winner_id)
                    accuracy = correct_identifications / votes_needed if votes_needed > 0 else 0.0
                    
                    # Winner gets:
                    # 1. Their stake back (guaranteed IF THEY VOTED)
                    # 2. (accuracy%) * (their equal share of loser pool)
                    if winner_id in voted_player_ids:
                        stake_refund = minimum_stake
                    else:
                        print(f"   ⚠️ Winner {winner_id} did not vote - forfeiting stake refund")
                        stake_refund = 0
                        
                    stake_winnings = int(accuracy * max_share_per_winner)
                    total_stake_reward = stake_refund + stake_winnings
                    
                    rewards[winner_id]['identification_accuracy'] = accuracy
                    rewards[winner_id]['stake_gems'] = total_stake_reward
                    rewards[winner_id]['is_winner'] = True
                    
                    total_distributed += stake_winnings
                    
                    print(f"   Winner {winner_id}:")
                    print(f"     Accuracy: {correct_identifications}/{votes_needed} = {accuracy*100:.1f}%")
                    print(f"     Refund: {stake_refund} gems (guaranteed if voted)")
                    print(f"     Winnings: {stake_winnings} gems ({accuracy*100:.1f}% of {max_share_per_winner})")
                    print(f"     Total: {total_stake_reward} gems")
                
                # Calculate residual (goes to house)
                residual = loser_stakes_pool - total_distributed
                print(f"   Residual to house: {residual} gems")
                
                # Losers get NOTHING back
                loser_ids = [pid for pid in human_player_ids if pid not in top_voted_players]
                for loser_id in loser_ids:
                    rewards[loser_id]['stake_gems'] = 0  # Get nothing back
                    print(f"   Loser {loser_id}: Lost {minimum_stake} gems, returned 0 gems")
            elif num_winners > 0 and num_losers == 0:
                # Everyone tied - no stakes change hands, refund stakes to everyone
                # Since stakes were deducted at game start, we need to credit them back
                for player_id in top_voted_players:
                    rewards[player_id]['is_winner'] = True
                    if player_id in voted_player_ids:
                        rewards[player_id]['stake_gems'] = minimum_stake  # Refund the deducted stake
                    else:
                        rewards[player_id]['stake_gems'] = 0 # Penalty for not voting
            elif num_winners == 0:
                # No one got any votes - no winners, refund stakes to everyone
                # Since stakes were deducted at game start, we need to credit them back
                for player_id in human_player_ids:
                    if player_id in voted_player_ids:
                        rewards[player_id]['stake_gems'] = minimum_stake  # Refund the deducted stake
                    else:
                        rewards[player_id]['stake_gems'] = 0 # Penalty for not voting
        else:
            # No stakes - just mark winners for display purposes
            # Even without stakes, we want to show who won (got most votes)
            if top_voted_players:
                print(f"💎 No stakes game - marking winners: {top_voted_players}")
                for player_id in top_voted_players:
                     rewards[player_id]['is_winner'] = True
        
        # Calculate total gems
        for player_id in human_player_ids:
            rewards[player_id]['total_gems'] = rewards[player_id]['base_gems'] + rewards[player_id]['stake_gems']
        
        print(f"💎 Multi-human game rewards: {rewards}")
    
    return rewards


async def complete_voting(room_code: str):
    """
    Complete the voting phase and process elimination.
    
    Args:
        room_code: Room identifier
    """
    print(f"🟢🟢🟢 COMPLETE_VOTING CALLED for room {room_code} 🟢🟢🟢")
    
    if room_code not in rooms:
        print(f"⚠️ Room {room_code} not found in rooms dict, returning")
        return
    
    state = rooms[room_code]['state']
    
    if state['phase'] != Phase.VOTING:
        print(f"⚠️ Room {room_code} not in voting phase (current: {state['phase']}), returning")
        return
    
    print(f"🏁 Completing voting for room {room_code}")
    print(f"📊 Final votes before processing: {state.get('votes', {})}")
    
    # Determine suspect (player with most votes) and winner directly; no elimination
    # FIXED: Handle both list votes (multi-human) and single votes (backward compatibility)
    vote_counts: Dict[str, int] = {}
    for _, target_list in state.get('votes', {}).items():
        if not target_list:
            continue
        if isinstance(target_list, list):
            # Multi-human game: count each voted player
            for target in target_list:
                vote_counts[target] = vote_counts.get(target, 0) + 1
        else:
            # Backward compatibility: single vote
            vote_counts[target_list] = vote_counts.get(target_list, 0) + 1
    
    # Determine winner based on game type
    num_humans = len([p for p in state['players'] if p['role'] == 'human' and not p['eliminated']])
    human_ids = [p['id'] for p in state['players'] if p['role'] == 'human' and not p['eliminated']]
    
    # MULTI-HUMAN GAME: Winner is the human player(s) with most votes FROM OTHER HUMANS
    if num_humans > 1:
        print(f"🎭 Multi-human game: Determining winner among {num_humans} humans")
        
        # In multi-human games, only votes FOR human players count
        # AI agents are not candidates for winning
        human_vote_counts = {pid: vote_counts.get(pid, 0) for pid in human_ids}
        
        print(f"   Human vote counts: {human_vote_counts}")
        
        if human_vote_counts and max(human_vote_counts.values()) > 0:
            max_human_votes = max(human_vote_counts.values())
            winners = [pid for pid, cnt in human_vote_counts.items() if cnt == max_human_votes]
            
            if len(winners) > 1:
                # Multiple humans tied for most votes
                state['winner'] = 'tie'
                state['winning_players'] = winners
                state['selected_suspect'] = winners[0]  # Show one for display
                state['suspect_role'] = 'human'
                print(f"   🤝 TIE between {winners} (each with {max_human_votes} votes)")
            else:
                # Single winner - the human with most votes
                state['winner'] = winners[0]  # Specific player ID
                state['winning_players'] = winners
                state['selected_suspect'] = winners[0]
                state['suspect_role'] = 'human'
                print(f"   🏆 WINNER: {winners[0]} with {max_human_votes} votes")
        else:
            # No votes or all zeros - everyone ties
            state['winner'] = 'tie'
            state['winning_players'] = human_ids
            state['selected_suspect'] = human_ids[0] if human_ids else None
            state['suspect_role'] = 'human'
            print(f"   🤝 TIE (no votes cast)")
            
    else:
        # SINGLE-HUMAN GAME: Team-based (human vs AI)
        # Most voted player determines the outcome
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
        
        state['selected_suspect'] = suspect
        state['suspect_role'] = suspect_role
        
        # Humans win if suspect is actually a human (most human-like); otherwise AIs win
        winning_team = 'human' if suspect_role == 'human' else 'ai'
        state['winner'] = winning_team
        winning_players = [p['id'] for p in state.get('players', []) if p.get('role') == winning_team]
        state['winning_players'] = winning_players
        print(f"🎮 Single-human game result: {winning_team} team wins (suspect: {suspect})")
    
    state['phase'] = Phase.GAME_OVER
    rooms[room_code]['state'] = state
    
    # CRITICAL: Mark room as completed so it doesn't count as "operating"
    rooms[room_code]['room_status'] = 'completed'
    print(f"✅ Room {room_code} marked as COMPLETED")
    
    # Get suspect info from state (works for both single and multi-human games)
    suspect = state.get('selected_suspect')
    suspect_role = state.get('suspect_role')
    
    # Broadcast voting result
    await broadcast_to_room(room_code, {
        "type": "voting_result",
        "suspect": suspect,
        "role": suspect_role,
        "vote_counts": vote_counts
    })
    
    # Broadcast game over
    game_graph = rooms[room_code]['game_graph']
    result = game_graph.game_over_node(state)
    state.update(result)
    if 'broadcast_queue' in result:
        for msg in result['broadcast_queue']:
            await broadcast_to_room(room_code, msg)
    rooms[room_code]['state'] = state
    
    # Save stats at end and get gem rewards
    gem_rewards = {}  # Will store player_id -> gem_amount
    try:
        room_data = rooms.get(room_code, {})
        minimum_stake = room_data.get('minimum_stake', 0)
        
        # Calculate rewards first (for frontend display)
        from .database import async_session_maker
        async with async_session_maker() as temp_db:
            rewards = await calculate_game_rewards(room_code, room_data, state, temp_db)
            # Extract full breakdown for each player
            # NEW: Stakes are deducted and credited in the same transaction above
            # So total_gems already includes the net result
            for player_id, reward_data in rewards.items():
                stake_gems_credited = reward_data.get('stake_gems', 0)
                base_gems = reward_data.get('base_gems', 0)
                total_gems = reward_data.get('total_gems', 0)
                
                # Calculate for display
                # In multi-human games: total_gems = base + stake_reward
                # Net change = total_gems - minimum_stake (what they risked)
                if minimum_stake > 0:
                    # Multi-human game with stakes
                    stake_display = stake_gems_credited - minimum_stake  # Net stake result
                    net_change = total_gems - minimum_stake  # Net change (base + stakes - deduction)
                else:
                    # Single-human game (no stakes)
                    stake_display = 0
                    net_change = total_gems  # Just the base gems
                
                gem_rewards[player_id] = {
                    'base_gems': base_gems,
                    'stake_gems': stake_display,  # Net stake change (can be negative)
                    'stake_amount': minimum_stake,  # What was at risk
                    'stake_returned': stake_gems_credited,  # What they got back
                    'total_gems': total_gems,  # What's credited (includes deduction already)
                    'net_change': net_change,  # True net profit/loss
                    'is_winner': reward_data.get('is_winner', False)
                }
        
        # Now save the session (which will credit the gems AND deduct stakes atomically)
        await save_session_stats(room_code, state, deduct_stakes_first=True)
        
        # Broadcast gem rewards to players with full breakdown
        print(f"💎 Broadcasting gem rewards breakdown: {gem_rewards}")
        await broadcast_to_room(room_code, {
            "type": "gem_rewards",
            "rewards": gem_rewards
        })
        
    except Exception as save_error:
        # Log the error
        print(f"❌❌❌ CRITICAL: save_session_stats failed for room {room_code}")
        print(f"   Error: {save_error}")
        import traceback
        traceback.print_exc()
        
        # Broadcast error to frontend so players can see it
        error_message = f"⚠️ Game completed but failed to award gems. Please contact support if this persists."
        try:
            await broadcast_to_room(room_code, {
                "type": "system_message",
                "message": error_message,
                "severity": "error"
            })
        except Exception as broadcast_err:
            print(f"❌ Also failed to broadcast error: {broadcast_err}")
        
        # DON'T re-raise - game is already complete, gem rewards are secondary
        # Raising here would cause CORS errors and prevent vote response from returning
        print(f"⚠️ Continuing despite gem reward failure - game completion is more important")


async def schedule_correction_message(room_code: str, ai_id: str, correction_text: str, ai_sender: str, messages_before_correction: int):
    """
    Schedule a delayed correction message for a typo.
    Waits 2-8 seconds and sends correction with asterisk prefix.
    
    Args:
        room_code: Room identifier
        ai_id: AI agent identifier
        correction_text: The correction message (e.g., "*meant")
        ai_sender: The display name of the AI sender
        messages_before_correction: Number of messages in chat history before scheduling
    """
    # Wait 2-8 seconds before sending correction
    correction_delay = random.uniform(2.0, 8.0)
    print(f"⏱️  Scheduling correction for {ai_id} in {correction_delay:.2f}s")
    await asyncio.sleep(correction_delay)
    
    # Check if room still exists
    if room_code not in rooms:
        print(f"🚫 Correction for {ai_id} cancelled - room deleted")
        return
    
    current_state = rooms[room_code]['state']
    
    # Check if still in discussion phase
    if current_state['phase'] != Phase.DISCUSSION:
        print(f"🚫 Correction for {ai_id} cancelled - phase is {current_state['phase'].value}")
        return
    
    # Check if other messages were sent in between (adds realism)
    messages_now = len(current_state.get('chat_history', []))
    messages_between = messages_now - messages_before_correction
    
    print(f"📝 Sending correction for {ai_id}. {messages_between} messages sent in between.")
    
    # Create correction message
    chat_msg = {
        "sender": ai_sender,
        "message": correction_text,
        "timestamp": time.time()
    }
    
    # Add to chat history
    current_state['chat_history'].append(chat_msg)
    current_state['last_message_time'] = time.time()
    rooms[room_code]['state'] = current_state
    
    # Broadcast correction (minimal delay, just thinking time)
    await broadcast_to_room(room_code, {
        "type": "message",
        "sender": ai_sender,
        "message": correction_text,
        "timestamp": chat_msg.get("timestamp", time.time())
    })
    
    print(f"✅ Correction sent for {ai_id}: {correction_text}")


async def process_single_ai_message(room_code: str, ai_id: str):
    """
    Process a single AI agent's message asynchronously.
    Allows multiple AI agents to respond simultaneously.
    Implements LLM-generated chunk-based message sending for human-like typing behavior.
    
    HYBRID DELAY SYSTEM:
    - Statistical model: 1 + N(0.255, 0.0255)×n_char + N(0.03, 0.003)×n_char_prev + Γ(2.5, 0.25)
    - Typing speed: 15% faster than baseline (~3.92 chars/sec)
    - Chunking behavior: LLM generates natural message chunks (1-4 chunks)
    - Context awareness: Considers previous message length (cognitive load)
    - Human-like imperfections: Typos, netspeak, self-corrections based on personality
    
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
        game_graph = rooms[room_code]['game_graph']
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
        if 'ai_sender' not in result or 'ai_message_data' not in result:
            return
            
        ai_sender = result['ai_sender']
        message_data = result['ai_message_data']
        
        # Extract chunks and typo information from LLM-generated response
        chunks = message_data.get('chunks', [])
        has_typo = message_data.get('has_typo', False)
        correction = message_data.get('correction', '')
        
        if not chunks:
            print(f"⚠️ No chunks in message_data for {ai_id}")
            return
        
        print(f"📝 AI {ai_id} generated {len(chunks)} chunks: {chunks}")
        if has_typo and correction:
            print(f"🔧 AI {ai_id} has typo, will send correction: {correction}")
        
        # =====================================================================
        # HYBRID DELAY CALCULATION
        # =====================================================================
        import numpy as np
        
        # Get previous message length for context awareness (cognitive load)
        chat_history = current_state.get('chat_history', [])
        n_char_prev = len(chat_history[-1]['message']) if chat_history else 0
        
        # Calculate total message length from all chunks
        full_message = " ".join(chunks)
        n_char = len(full_message)
        
        # Statistical model parameters
        # 1 + N(0.255, 0.0255)×n_char + N(0.03, 0.003)×n_char_prev + Γ(2.5, 0.25)
        # https://dl.acm.org/doi/full/10.1145/3715275.3732108
        
        # Note: Typing speed enhanced by 15% (0.3 → 0.255s per char)
        base_delay = 0.3  # Base reaction time
        
        # Typing rate with variance (Normal distribution)
        # Enhanced by 15% (0.3 → 0.255s per char = ~3.92 chars/sec instead of 3.33)
        typing_rate_per_char = max(0.1, np.random.normal(0.12, 0.02))  # Clamp to avoid negative
        
        # Context factor - cognitive load from processing previous message
        context_rate_per_char = max(0.0, np.random.normal(0.02, 0.003))
        context_delay = context_rate_per_char * n_char_prev
        
        # Thinking time - Gamma distribution (right-skewed, models human thinking)
        # Gamma(shape=2.5, scale=0.25) has mean=0.625s, variance=0.156s²
        thinking_time = np.random.gamma(1.5, 0.15)
        
        # Total statistical delay
        total_statistical_delay = base_delay + (typing_rate_per_char * n_char) + context_delay + thinking_time
        
        print(f"📊 Delay calculation for {ai_id}:")
        print(f"   Message length: {n_char} chars, Previous: {n_char_prev} chars")
        print(f"   Base: {base_delay:.2f}s, Typing: {typing_rate_per_char:.3f}s/char × {n_char} = {typing_rate_per_char * n_char:.2f}s")
        print(f"   Context: {context_delay:.2f}s, Thinking: {thinking_time:.2f}s")
        print(f"   Total delay: {total_statistical_delay:.2f}s")
        
        # Update pending_ai_messages to remove this AI
        current_state = rooms[room_code]['state']
        if 'pending_ai_messages' in result:
            current_state['pending_ai_messages'] = result['pending_ai_messages']
        # CRITICAL: Persist state update immediately to prevent duplicate processing
        rooms[room_code]['state'] = current_state
        
        # =====================================================================
        # DISTRIBUTE DELAY ACROSS CHUNKS (HYBRID APPROACH)
        # =====================================================================
        
        # Calculate per-chunk delays proportionally
        chunk_delays = []
        total_chunk_chars = sum(len(chunk) for chunk in chunks)
        
        if len(chunks) > 1:
            # Multi-chunk: Distribute delay proportionally by character count
            for chunk in chunks:
                chunk_proportion = len(chunk) / total_chunk_chars if total_chunk_chars > 0 else 1.0 / len(chunks)
                chunk_delay = total_statistical_delay * chunk_proportion
                chunk_delays.append(chunk_delay)
        else:
            # Single chunk: Use entire delay
            chunk_delays = [total_statistical_delay]
        
        print(f"⏱️  Chunk delays: {[f'{d:.2f}s' for d in chunk_delays]}")
        
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
        
        # Send each chunk with statistically calculated delays
        for chunk_idx, (chunk, chunk_delay) in enumerate(zip(chunks, chunk_delays)):
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
            
            # Split chunk delay into thinking (30%) and typing (70%) for better UX
            thinking_portion = chunk_delay * 0.3
            typing_portion = chunk_delay * 0.7
            
            # Add small variance to thinking time for realism
            thinking_portion = thinking_portion * random.uniform(0.8, 1.2)
            
            print(f"💭 AI {ai_id} chunk {chunk_idx+1}/{len(chunks)}: thinking={thinking_portion:.2f}s, typing={typing_portion:.2f}s")
            
            # Thinking delay
            await asyncio.sleep(thinking_portion)
            
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
            
            # Typing delay (simulates actual character-by-character typing)
            await asyncio.sleep(typing_portion)
            
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
                "message": chunk,
                "timestamp": chat_msg.get("timestamp", time.time())
            })
            
            # Small pause between chunks if not the last chunk
            # Simulates time to press "enter" and start next message
            if chunk_idx < len(chunks) - 1:
                inter_chunk_pause = random.uniform(0.3, 0.5)
                print(f"⏸️  Inter-chunk pause: {inter_chunk_pause:.2f}s")
                await asyncio.sleep(inter_chunk_pause)
                
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
        
        # Schedule correction message if has_typo is true
        # Add 20-60% probability that another AI responds between typo and correction
        if has_typo and correction and correction.strip():
            # Record current message count for tracking
            messages_before_correction = len(rooms[room_code]['state'].get('chat_history', []))
            # Schedule the correction as a background task
            asyncio.create_task(
                schedule_correction_message(room_code, ai_id, correction, ai_sender, messages_before_correction)
            )
        
        # Handle any other broadcasts from result
        if 'broadcast_queue' in result:
            for msg in result['broadcast_queue']:
                await broadcast_to_room(room_code, msg)
        
        # After AI speaks, give other agents a chance to respond
        # Cooldown period to prevent immediate back-and-forth (models natural conversation pacing)
        cooldown = random.uniform(0.8, 1.5)  # More natural than fixed 1.25s
        print(f"⏱️  Post-message cooldown: {cooldown:.2f}s")
        await asyncio.sleep(cooldown)
        
        # DEFENSE: Check room still exists after cooldown
        if room_code not in rooms:
            print(f"🚫 AI {ai_id} blocked after cooldown - room deleted")
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
    game_graph = rooms[room_code]['game_graph']
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
        # Merge with existing pending messages to avoid revoking previous decisions
        current_pending = state.get('pending_ai_messages', [])
        # Add new ones that aren't already pending (preserve order)
        new_pending = current_pending + [ai for ai in responding_ais if ai not in current_pending]
        
        state['pending_ai_messages'] = new_pending
        rooms[room_code]['state'] = state
        print(f"🎯 {len(responding_ais)}/{len(active_ais)} agents decided to respond: {responding_ais} (Merged with pending: {current_pending})")
        
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


async def save_session_stats(room_code: str, state: dict, current_user: Optional[User] = None, deduct_stakes_first: bool = False) -> dict:
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
    print(f"🔴🔴🔴 SAVE_SESSION_STATS CALLED for room {room_code} 🔴🔴🔴")
    print(f"   State keys: {list(state.keys())}")
    print(f"   Players: {[p['id'] for p in state.get('players', [])]}")
    print(f"   Votes: {state.get('votes', {})}")
    
    root = os.path.dirname(os.path.dirname(__file__))
    out_dir = os.path.join(root, 'group-chat-stats')
    os.makedirs(out_dir, exist_ok=True)
    
    # Calculate vote counts
    print(f"📊 Calculating vote counts...")
    vote_counts: Dict[str, int] = {}
    for _, target_list in state.get('votes', {}).items():
        # Skip empty votes
        if not target_list:
            continue
        # Handle both list votes (multi-human) and single votes (backward compatibility)
        if isinstance(target_list, list):
            # Multi-human game: count each voted player
            for target in target_list:
                if target:  # Skip empty strings in the list
                    vote_counts[target] = vote_counts.get(target, 0) + 1
        else:
            # Backward compatibility: single vote (string)
            vote_counts[target_list] = vote_counts.get(target_list, 0) + 1
    print(f"   Vote counts: {vote_counts}")
    
    # Prepare stats payload for JSON file
    print(f"📝 Preparing stats payload...")
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
        'winner': state.get('winner'),
        'winning_players': state.get('winning_players', []),
        'gem_rewards': {}  # Will be populated after calculating rewards
    }
    print(f"✅ Payload prepared successfully")
    
    # Save to JSON file
    print(f"💾 Saving JSON file...")
    fname = f"{room_code}-{int(_time.time())}.json"
    path = os.path.join(out_dir, fname)
    try:
        with open(path, 'w') as f:
            json.dump(payload, f, ensure_ascii=False, indent=2)
        rooms[room_code]['last_stats_path'] = path
        print(f"✅ JSON file saved: {path}")
    except Exception as json_error:
        print(f"❌ FAILED to save JSON file: {json_error}")
        import traceback
        traceback.print_exc()
        raise
    
    # Extract session metadata
    room_data = rooms.get(room_code, {})
    language = state.get('language', 'english')
    total_players = room_data.get('total_players', len(state.get('players', [])))
    num_humans = len([p for p in state.get('players', []) if p.get('role') == 'human'])
    discussion_duration = room_data.get('discussion_duration', DISCUSSION_TIME)
    voting_duration = room_data.get('voting_duration', VOTING_TIME)
    completed_at = payload['ended_at']
    
    # Check if debug mode (EARLY CHECK to prevent stake deductions)
    is_debug_mode = (discussion_duration == 60 or voting_duration == 30)
    print(f"🐛 Debug mode check: discussion={discussion_duration}s, voting={voting_duration}s, is_debug={is_debug_mode}")
    if is_debug_mode:
        print(f"🐛 Debug mode detected - will skip all gem distributions and stake deductions")
    
    # Generate session UUID
    session_id = uuid_lib.uuid4()
    
    # Generate a placeholder completion key for backward compatibility with database schema
    # This is no longer used for verification - MTurk uses worker_id/assignment_id instead
    completion_key = f"DEPRECATED_{session_id}"
    
    # Calculate token usage and costs
    from .pricing import calculate_cost
    from .database import AIAgentUsage
    
    total_input_tokens = state.get('total_input_tokens', 0)
    total_output_tokens = state.get('total_output_tokens', 0)
    game_graph = rooms[room_code]['game_graph']
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
            
            # CRITICAL: Deduct stakes FIRST if requested (after voting, before rewards)
            # This makes the entire operation atomic: deduct + credit in ONE transaction
            # SKIP stake deduction in debug mode
            if deduct_stakes_first and not is_debug_mode:
                max_humans = room_data.get('max_humans', 1)
                minimum_stake = room_data.get('minimum_stake', 0)
                
                if max_humans > 1 and minimum_stake > 0:
                    print(f"💎 Deducting stakes in atomic transaction with rewards")
                    stake_success = await deduct_stakes(room_code, db)
                    if not stake_success:
                        print(f"❌ Stake deduction failed - rolling back entire transaction")
                        await db.rollback()
                        raise Exception("Failed to deduct stakes - transaction rolled back")
                    print(f"✅ Stakes deducted (not committed yet - will commit with rewards)")
            elif deduct_stakes_first and is_debug_mode:
                print(f"🐛 Debug mode - skipping stake deduction")
            
            # Calculate and distribute gems using new gem reward system
            player_user_map = room_data.get('player_user_map', {})
            
            # CRITICAL VALIDATION: Check if player_user_map is populated
            print(f"=" * 80)
            print(f"📊 SAVE SESSION STATS - Room {room_code}")
            print(f"=" * 80)
            print(f"💎 Starting gem distribution using calculate_game_rewards for {len(player_user_map)} players")
            print(f"📋 player_user_map contents: {player_user_map}")
            
            if not player_user_map:
                print(f"⚠️ WARNING: player_user_map is EMPTY for room {room_code}!")
                print(f"   Room data keys: {list(room_data.keys())}")
                print(f"   Players in state: {[p['id'] + ' (' + p['role'] + ')' for p in state.get('players', [])]}")
                print(f"   This is expected for anonymous games, but unusual for multi-human games")
            
            # Call the comprehensive reward calculation function
            print(f"🔄 Calling calculate_game_rewards...")
            rewards = await calculate_game_rewards(room_code, room_data, state, db)
            print(f"✅ calculate_game_rewards completed. Rewards calculated for {len(rewards)} players")
            print(f"📊 Rewards breakdown: {rewards}")
            
            # Track successfully credited players for session data
            credited_players = []
            
            # Calculate minimum stake once for net change calculation
            stake_percentage = room_data.get('stake_percentage', 0)
            minimum_stake = room_data.get('minimum_stake', 0) if stake_percentage > 0 else 0
            
            # Process each human player based on calculated rewards
            print(f"👥 Processing {len([p for p in state.get('players', []) if p.get('role') == 'human'])} human players for gem credits...")
            for player in state.get('players', []):
                if player.get('role') != 'human':
                    continue
                
                player_id = player['id']
                mapped_user_id_str = player_user_map.get(player_id)
                
                print(f"  🔹 Player {player_id}: mapped_user_id = {mapped_user_id_str}")
                
                # Skip unauthenticated players
                if not mapped_user_id_str:
                    print(f"     ⚠️ No user mapping found - skipping gem credit (anonymous player)")
                    continue
                
                # Get reward details from calculated rewards
                player_rewards = rewards.get(player_id, {
                    'base_gems': 0,
                    'stake_gems': 0,
                    'total_gems': 0,
                    'is_winner': False,
                    'identification_accuracy': 0.0,
                    'votes_received': 0
                })
                
                total_gems = player_rewards['total_gems']
                base_gems = player_rewards['base_gems']
                stake_gems = player_rewards['stake_gems']
                is_winner = player_rewards.get('is_winner', False)
                
                print(f"     💎 Rewards: total={total_gems}, base={base_gems}, stake={stake_gems}, winner={is_winner}")
                
                # Calculate legacy earnings value for database compatibility
                player_earnings_value = total_gems / 1000.0  # Convert gems to USD equivalent
                
                # Get the user object and credit gems
                try:
                    # CRITICAL FIX: Convert string UUID to UUID object for SQL comparison
                    try:
                        mapped_user_uuid = uuid_lib.UUID(mapped_user_id_str)
                        print(f"     ✅ UUID conversion successful: {mapped_user_uuid}")
                    except (ValueError, AttributeError) as uuid_err:
                        print(f"     ❌ Invalid UUID format: {mapped_user_id_str}, error: {uuid_err}")
                        continue
                    
                    print(f"     🔍 Querying database for user {mapped_user_uuid}...")
                    user_result = await db.execute(
                        sql_select(User).where(User.id == mapped_user_uuid)
                    )
                    db_user = user_result.scalar_one_or_none()
                    
                    if not db_user:
                        print(f"     ❌ User with UUID {mapped_user_uuid} not found in database")
                        continue
                    
                    print(f"     ✅ User found: {db_user.user_id}, current balance: {db_user.gem_balance} gems")
                    
                    # Skip debug mode games
                    if is_debug_mode:
                        print(f"     🐛 Debug mode - skipping gem credit for {player_id}")
                        continue
                    
                    # Use calculated gems from reward system
                    gems_earned = total_gems
                    
                    # VALIDATION: Ensure gems_earned is reasonable (allow negative for stake losses)
                    if gems_earned < -100000:  # Sanity check: max 100,000 gem loss
                        print(f"⚠️ Suspiciously high gem loss ({gems_earned}), capping at -100,000")
                        gems_earned = -100000
                    elif gems_earned > 100000:  # Sanity check: max 100,000 gems per game ($100)
                        print(f"⚠️ Suspiciously high gems ({gems_earned}), capping at 100,000")
                        gems_earned = 100000
                    
                    # Credit/debit gems to user's balance (ATOMIC OPERATION)
                    # NEW: Stakes are deducted in complete_voting() just before this function
                    # So the net operation here is:
                    #   - Deduction happened just before (in complete_voting)
                    #   - Now we credit the total reward
                    #   - Net effect = -stake + reward
                    old_balance = db_user.gem_balance
                    old_total_earned = db_user.total_gems_earned
                    old_total_games = db_user.total_games
                    
                    print(f"     💰 Crediting gems to user...")
                    print(f"        Current balance: {old_balance} gems")
                    print(f"        Adding: {gems_earned} gems")
                    db_user.gem_balance += gems_earned
                    
                    # Only add to total_gems_earned if positive (don't count stake losses)
                    if gems_earned > 0:
                        db_user.total_gems_earned += gems_earned
                    
                    db_user.total_games += 1  # INCREMENT TOTAL GAMES COUNTER
                    
                    print(f"     ✅ Gems credited successfully to user {db_user.user_id}")
                    print(f"        Balance: {old_balance} → {db_user.gem_balance} gems ({gems_earned:+d})")
                    print(f"        Total earned: {old_total_earned} → {db_user.total_gems_earned}")
                    print(f"        Total games: {old_total_games} → {db_user.total_games}")
                    print(f"        Breakdown - Base: {base_gems}, Stakes: {stake_gems}")
                    
                    # Update RoomStake record with final amounts (if exists)
                    stake_result = await db.execute(
                        sql_select(RoomStake).where(
                            RoomStake.room_code == room_code,
                            RoomStake.user_id == mapped_user_uuid
                        )
                    )
                    stake_record = stake_result.scalar_one_or_none()
                    
                    if stake_record:
                        minimum_stake = room_data.get('minimum_stake', 0)
                        
                        if stake_gems > minimum_stake:
                            # Winner: got refund + winnings
                            stake_record.won_amount = stake_gems - minimum_stake
                            stake_record.returned_amount = minimum_stake
                        elif stake_gems == minimum_stake:
                            # Tie or no stakes: got full refund, no winnings
                            stake_record.won_amount = 0
                            stake_record.returned_amount = minimum_stake
                        elif stake_gems > 0:
                            # Loser with partial return
                            stake_record.won_amount = 0
                            stake_record.returned_amount = stake_gems
                        else:
                            # Loser with no return
                            stake_record.won_amount = 0
                            stake_record.returned_amount = 0
                        
                        print(f"   Updated RoomStake record: won={stake_record.won_amount}, returned={stake_record.returned_amount}")
                    
                    # Track for session data (use first authenticated player's earnings for legacy)
                    # Calculate net change (Profit/Loss) for accurate reporting
                    # gems_earned is Gross (credited amount), but user cares about Net
                    net_change = gems_earned - minimum_stake
                    
                    credited_players.append({
                        'player_id': player_id,
                        'user_id': str(mapped_user_uuid),
                        'gems_earned': gems_earned,
                        'earnings_usd': float(player_earnings_value),
                        'base_gems': base_gems,
                        'stake_gems': stake_gems,
                        'net_change': net_change,  # Store net change for accurate SessionPlayer record
                        'is_winner': player_rewards.get('is_winner', False)
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
                    print(f"     ❌ ERROR crediting gems to player {player_id} (user {mapped_user_id_str})")
                    print(f"        Error type: {type(e).__name__}")
                    print(f"        Error message: {e}")
                    print(f"        Stack trace:")
                    print(traceback.format_exc())
                    # Continue to next player - don't let one player's error stop the whole session save
                    continue
            
            print(f"=" * 80)
            print(f"✅ Gem credit phase complete")
            print(f"   Credited players: {len(credited_players)}/{len(player_user_map)}")
            if credited_players:
                print(f"   Successfully credited: {[p['player_id'] for p in credited_players]}")
            print(f"=" * 80)
            
            # Update payload with gem rewards (for JSON file storage) - FULL BREAKDOWN
            payload['gem_rewards'] = {}
            for player_id in [p['id'] for p in state.get('players', []) if p['role'] == 'human']:
                reward = rewards.get(player_id, {})
                stake_returned = reward.get('stake_gems', 0)
                base_gems = reward.get('base_gems', 0)
                total_gems = reward.get('total_gems', 0)
                
                # Calculate display values
                if minimum_stake > 0:
                    stake_display = stake_returned - minimum_stake
                    net_change = total_gems - minimum_stake
                else:
                    stake_display = 0
                    net_change = total_gems
                
                payload['gem_rewards'][player_id] = {
                    'base_gems': base_gems,
                    'stake_gems': stake_display,  # Net stake change (negative for losers)
                    'stake_amount': minimum_stake,  # What was at risk
                    'stake_returned': stake_returned,  # What came back
                    'total_gems': total_gems,  # What's credited (net after deduction)
                    'net_change': net_change,  # True net profit/loss
                    'is_winner': reward.get('is_winner', False)
                }
            payload['credited_players'] = credited_players  # Store detailed credit info
            
            # Build session data dict
            print(f"💾 Building session record...")
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
            
            print(f"   Session ID: {session_id}")
            print(f"   Room: {room_code}")
            print(f"   Players: {num_humans} human(s), {total_players} total")
            print(f"   Duration: {discussion_duration}s discussion, {voting_duration}s voting")
            
            db_session = DBSession(**session_data)
            db.add(db_session)
            print(f"✅ Session record created and added to transaction")
            
            # Save per-agent token usage
            print(f"💾 Saving AI agent usage records ({len(agent_token_usage)} agents)...")
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
            
            print(f"✅ AI agent usage records added")
            
            # Save player-user mappings
            from .database import SessionPlayer
            player_user_map = room_data.get('player_user_map', {})
            
            print(f"=" * 80)
            print(f"👥 Creating SessionPlayer records...")
            print(f"   player_user_map: {player_user_map}")
            print(f"   state['players']: {[p['id'] + ' (' + p['role'] + ')' for p in state.get('players', [])]}")
            
            session_players_created = 0
            for player in state.get('players', []):
                player_id = player['id']
                role = player['role']
                mapped_user_id = player_user_map.get(player_id)
                
                print(f"   🔹 Player {player_id} ({role}): mapped_user_id = {mapped_user_id}")
                
                # Convert user_id string to UUID if present
                user_uuid = None
                if mapped_user_id:
                    try:
                        user_uuid = uuid_lib.UUID(mapped_user_id)
                        print(f"      ✅ Mapped to user {user_uuid}")
                    except (ValueError, AttributeError) as e:
                        print(f"      ⚠️ Invalid user_id format: {mapped_user_id}, error: {e}")
                else:
                    print(f"      ℹ️  No user mapping (anonymous or AI)")
                
                # Find gems_earned for this player from credited_players list
                player_gems = None
                for credited_player in credited_players:
                    if credited_player['player_id'] == player_id:
                        # Use net_change (Profit/Loss) for SessionPlayer record so dashboard shows accurate P/L
                        player_gems = credited_player.get('net_change', credited_player['gems_earned'])
                        print(f"      💎 Gems Net Change: {player_gems}")
                        break
                
                session_player = SessionPlayer(
                    session_id=session_id,
                    user_id=user_uuid,
                    player_id=player_id,
                    role=role,
                    gems_earned=player_gems
                )
                db.add(session_player)
                session_players_created += 1
                print(f"      💾 SessionPlayer record added (user_id={user_uuid}, gems_earned={player_gems})")
            
            print(f"✅ {session_players_created} SessionPlayer records created")
            
            # CRITICAL: Commit all changes (Session, AIAgentUsage, SessionPlayer, User gem balances)
            print(f"💾 Committing transaction to database...")
            await db.commit()
            print(f"=" * 80)
            print(f"✅ ✅ ✅ SESSION SAVED SUCCESSFULLY ✅ ✅ ✅")
            print(f"   Session ID: {session_id}")
            print(f"   Room: {room_code}")
            print(f"   Players credited: {len(credited_players)}/{len(player_user_map)}")
            print(f"   File saved: {path}")
            print(f"=" * 80)
    except Exception as e:
        print(f"=" * 80)
        print(f"❌ ❌ ❌ CRITICAL ERROR: Failed to save session to database ❌ ❌ ❌")
        print(f"   Room: {room_code}")
        print(f"   Error: {e}")
        print(f"=" * 80)
        import traceback
        traceback.print_exc()
        
        # Try to rollback the failed transaction
        try:
            await db.rollback()
            print(f"✅ Transaction rolled back successfully")
        except Exception as rollback_error:
            print(f"❌ Failed to rollback transaction: {rollback_error}")
        
        # RE-RAISE THE EXCEPTION to surface the actual error
        # This will help us identify what's breaking
        print(f"🔄 Re-raising exception to surface the error...")
        raise
    
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
    # Rate limit check BEFORE accepting connection
    # Use client host as key
    client_host = websocket.client.host
    if not websocket_connect_rate_limiter.is_allowed(client_host):
        print(f"⛔ WebSocket connection blocked - rate limit exceeded for {client_host}")
        # Cannot send JSON since connection is not accepted yet
        # Just close with Policy Violation code
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return

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
        
        # Get next API key for this room (round-robin with error handling)
        try:
            api_key, api_key_index = get_api_key_for_room()
        except HTTPException as e:
            # Send error to client and close connection
            await websocket.send_json({
                "type": "error",
                "message": f"Failed to create room: {e.detail}"
            })
            await websocket.close()
            return
        
        # Create game with default language (english) for WebSocket rooms
        state = create_game_for_room(room_code, NUM_AI_PLAYERS, ai_player_ids, "english")
        
        # Create game graph with assigned API key
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
            'max_humans': 4,
            'total_players': NUM_AI_PLAYERS + 4,
            'room_status': 'in_progress',  # WebSocket rooms start immediately
            'created_at': time.time(),
            'creator_id': player_id,
            'player_user_map': {},  # Maps player_id -> user_id (for authenticated users)
            'current_humans': [],  # DEPRECATED - kept for backward compatibility
            'assigned_humans': [],  # Players with permanent slots
            'connected_humans': [],  # Currently connected (internal use only)
            'permanently_left': set(),  # Players who explicitly left
            'player_last_activity': {},  # player_id -> timestamp
            'player_heartbeat': {},  # player_id -> timestamp
            'available_numbers': available_numbers,
            'human_overflow_counter': 0,  # Counter for H1, H2 fallback numbering
            'discussion_duration': DISCUSSION_TIME,  # Use default config
            'voting_duration': VOTING_TIME,  # Use default config
            'game_graph': game_graph,  # Room-specific GameGraph with assigned API key
            'api_key_index': api_key_index,  # Track which API key is assigned
            'player_message_cooldowns': defaultdict(float)  # Track last message time per player for rate limiting
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
    
    # Add to connected_humans (internal tracking - never exposed to clients)
    # Note: player_id here might not be the numbered ID yet, that's added later in the flow
    # We'll update connected_humans with the actual numbered player ID after it's assigned
    
    # REMOVED: Initial player-user mapping moved to after numbered_player_id is assigned
    # to prevent duplicate mappings and ensure consistent player identification
    # The mapping is now only done once with the numbered player ID (see lines below)
    
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
    player_id_map = rooms[room_code].get('player_id_map', {})
    numbered_id = player_id_map.get(player_id)
    
    for p in state.get('players', []):
        # Only match if this exact player_id or its mapped numbered_id exists
        # FIXED: Removed overly broad 'p.get('role') == 'human'' check that caused
        # multiple users to be mapped to the same player
        if p['id'] == player_id or (numbered_id and p['id'] == numbered_id):
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
            
            # VALIDATION: Check for duplicate user mappings
            user_count = {}
            for pid, uid in rooms[room_code]['player_user_map'].items():
                user_count[uid] = user_count.get(uid, 0) + 1
            duplicates = {uid: count for uid, count in user_count.items() if count > 1}
            if duplicates:
                print(f"⚠️ WARNING: Duplicate user mappings detected: {duplicates}")
                print(f"⚠️ Full player_user_map: {rooms[room_code]['player_user_map']}")
        else:
            print(f"⚠️ No user_id to map for {numbered_player_id}")
        
        rooms[room_code]['state'] = state
        print(f"✅ Added human player {numbered_player_id} to game state")
        
        # Add to connected_humans (internal tracking)
        connected_humans = get_connected_humans(rooms[room_code])
        if numbered_player_id not in connected_humans:
            connected_humans.append(numbered_player_id)
            rooms[room_code]['connected_humans'] = connected_humans
            print(f"🔗 Added {numbered_player_id} to connected_humans")
        
        # Track initial activity and heartbeat for WebSocket connection
        update_player_activity(rooms[room_code], numbered_player_id)
        update_player_heartbeat(rooms[room_code], numbered_player_id)
    else:
        # Player already exists (joined via API), just store the connection mapping
        numbered_player_id = existing_player['id']
        rooms[room_code]['player_id_map'] = rooms[room_code].get('player_id_map', {})
        rooms[room_code]['player_id_map'][player_id] = numbered_player_id
        
        # Add to connected_humans (internal tracking)
        connected_humans = get_connected_humans(rooms[room_code])
        if numbered_player_id not in connected_humans:
            connected_humans.append(numbered_player_id)
            rooms[room_code]['connected_humans'] = connected_humans
            print(f"🔗 Added existing player {numbered_player_id} to connected_humans")
        
        # Track activity and heartbeat for existing player reconnecting via WebSocket
        update_player_activity(rooms[room_code], numbered_player_id)
        update_player_heartbeat(rooms[room_code], numbered_player_id)
        
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
            
            # VALIDATION: Check for duplicate user mappings
            user_count = {}
            for pid, uid in rooms[room_code]['player_user_map'].items():
                user_count[uid] = user_count.get(uid, 0) + 1
            duplicates = {uid: count for uid, count in user_count.items() if count > 1}
            if duplicates:
                print(f"⚠️ WARNING: Duplicate user mappings detected: {duplicates}")
                print(f"⚠️ Full player_user_map: {rooms[room_code]['player_user_map']}")
        else:
            print(f"⚠️ No user_id to map for existing player {numbered_player_id}")
    
    # If this was a new room, initialize and broadcast
    state = rooms[room_code]['state']
    if 'initialized' not in rooms[room_code]:
        # Initialize game
        game_graph = rooms[room_code]['game_graph']
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
        
        # Immediately send timer sync for initial discussion phase (FIX: Prevent timer desync at game start)
        discussion_duration = rooms[room_code].get('discussion_duration', DISCUSSION_TIME)
        await broadcast_to_room(room_code, {
            "type": "timer_sync",
            "phase": "Discussion",
            "time_remaining": int(discussion_duration)
        })
        
        # Trigger active decision-making for initial AI responses
        # AIs will individually decide if they should start the conversation
        await asyncio.sleep(1.75)  # Small delay for realism
        asyncio.create_task(trigger_agent_decisions(room_code))
    
    # Send current game state to the newly connected client
    state = rooms[room_code]['state']
    room = rooms[room_code]
    await websocket.send_json({"type": "player_list", "players": [p["id"] for p in state["players"]]})
    await websocket.send_json({"type": "topic", "topic": state["topic"]})
    
    # Send phase with durations and num_human_players
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
    
    # Send current timer state if in an active phase (FIX: Timer sync for mid-phase joins)
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
        print(f"⏱️ Sent initial timer sync to {player_id}: {remaining}s remaining in {state['phase'].value}")
    
    # Send chat history
    for msg in state["chat_history"]:
        await websocket.send_json({
            "type": "message", 
            "sender": msg["sender"], 
            "message": msg["message"],
            "timestamp": msg.get("timestamp", time.time())
        })
    
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
                
                # Validate message length
                if len(message) > 400:
                    print(f"⚠️ Message rejected - too long ({len(message)} chars)")
                    await websocket.send_json({
                        "type": "error",
                        "message": "Message exceeds 400 character limit"
                    })
                    continue

                # Rate limiting
                current_time = time.time()
                player_cooldowns = rooms[room_code].get('player_message_cooldowns')
                # Handle legacy rooms that might not have this key
                if player_cooldowns is None:
                    player_cooldowns = defaultdict(float)
                    rooms[room_code]['player_message_cooldowns'] = player_cooldowns
                
                last_message_time = player_cooldowns[actual_player_id]
                if current_time - last_message_time < 0.1:
                    print(f"⚠️ Message rejected - rate limit (0.1s) for {actual_player_id}")
                    await websocket.send_json({
                        "type": "error",
                        "message": "You are sending messages too fast"
                    })
                    continue
                
                # Update last message time
                player_cooldowns[actual_player_id] = current_time
                
                # Update state
                state = await process_human_message(state, message, actual_player_id)
                rooms[room_code]['state'] = state
                
                # Broadcast message (exclude sender since frontend shows it optimistically)
                # Include timestamp from the last added message in history
                last_msg = state['chat_history'][-1] if state['chat_history'] else {}
                msg_timestamp = last_msg.get('timestamp', current_time)
                
                print(f"📤 Broadcasting human message to room (excluding sender)")
                await broadcast_to_room(room_code, {
                    "type": "message",
                    "sender": player_id,
                    "message": message,
                    "timestamp": msg_timestamp
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
        # Remove connection but keep room alive for rejoin
        if room_code in rooms:
            room = rooms[room_code]
            
            # Remove from connections
            room['connections'].pop(player_id, None)
            print(f"🔌 Player {player_id} disconnected from room {room_code}")
            print(f"📊 Remaining connections: {len(room['connections'])}")
            
            # Get the actual player ID (might be mapped)
            player_id_map = room.get('player_id_map', {})
            actual_player_id = player_id_map.get(player_id, player_id)
            
            # Remove from connected_humans (internal tracking only)
            connected_humans = get_connected_humans(room)
            if actual_player_id in connected_humans:
                connected_humans.remove(actual_player_id)
                room['connected_humans'] = connected_humans
                print(f"🔌 Removed {actual_player_id} from connected_humans")
            
            # Update last activity timestamp
            if 'player_last_activity' not in room:
                room['player_last_activity'] = {}
            room['player_last_activity'][actual_player_id] = time.time()
            
            # DO NOT remove from assigned_humans (allow rejoin)
            # DO NOT remove from player_user_map (allow rejoin)
            # DO NOT broadcast disconnection to other players (maintain anonymity)
            
            # DO NOT delete room when connections become empty
            # In multi-player games, players can rejoin
            # Room will be cleaned up when:
            # 1. Game ends naturally (game_over)
            # 2. Player explicitly leaves (calls leave endpoint)
            # 3. Periodic cleanup for abandoned rooms
            
            if not room['connections']:
                print(f"⚠️ Room {room_code} has no active connections but keeping it alive for potential rejoin")


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
        game_graph = rooms[room_code]['game_graph']
        result = game_graph.initialize_game_node(state)
        state.update(result)
        rooms[room_code]['state'] = state
        
        if 'broadcast_queue' in result:
            for msg in result['broadcast_queue']:
                await broadcast_to_room(room_code, msg)
        
        # Start phases
        asyncio.create_task(run_discussion_phase(room_code))
        
        # Immediately send timer sync for initial discussion phase (FIX: Prevent timer desync at game start)
        discussion_duration = rooms[room_code].get('discussion_duration', DISCUSSION_TIME)
        await broadcast_to_room(room_code, {
            "type": "timer_sync",
            "phase": "Discussion",
            "time_remaining": int(discussion_duration)
        })
        
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
    """
    Health check endpoint with API key manager status.
    
    Returns:
        Dictionary with health status and API configuration details
    """
    health_info = {
        "status": "healthy",
        "api_keys_configured": api_key_manager is not None
    }
    
    if api_key_manager:
        try:
            stats = api_key_manager.get_stats()
            health_info.update({
                "api_key_count": stats["total_keys"],
                "total_rooms_created": stats["total_assigned"],
                "api_system": "operational"
            })
        except Exception as e:
            health_info["api_system"] = f"degraded: {str(e)}"
    else:
        health_info["api_system"] = "unavailable - no API keys configured"
    
    return health_info


# ============================================================================
# Authentication API Endpoints
# ============================================================================

@app.post("/api/auth/register")
async def register(
    request: RegisterRequest,
    http_request: Request,
    db: AsyncSession = Depends(get_async_session)
):
    """
    Register a new user.
    
    Args:
        request: User registration data (user_id, password)
        http_request: FastAPI Request object (for rate limiting)
        db: Database session
    
    Returns:
        Success message
    """
    # Rate limiting check
    client_ip = http_request.client.host
    if not register_rate_limiter.is_allowed(client_ip):
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many registration attempts. Please wait a minute and try again."
        )
    
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
    http_request: Request,
    db: AsyncSession = Depends(get_async_session)
):
    """
    Authenticate user and return JWT token.
    
    Args:
        request: Login credentials (user_id, password)
        http_request: FastAPI Request object (for rate limiting)
        db: Database session
    
    Returns:
        JWT access token and user info
    """
    # Rate limiting check (prevent brute-force attacks)
    client_ip = http_request.client.host
    if not login_rate_limiter.is_allowed(client_ip):
        log_rate_limit_violation(client_ip, "/api/auth/login")
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many login attempts. Please wait a minute and try again."
        )
    
    user = await authenticate_user(db, request.user_id, request.password)
    if not user:
        # Log failed login attempt
        log_failed_login(request.user_id, client_ip, "Invalid credentials")
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
        "age": current_user.age,
        "gender": current_user.gender,
        "nationality": current_user.nationality,
        "major": current_user.major,
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
    Update user's MTurk Worker ID and demographic information.
    
    Args:
        request: Request with worker_id, age, gender, nationality, major in body
        current_user: Current authenticated user
        db: Database session
    
    Returns:
        Updated profile information
    """
    import re
    
    body = await request.json()
    worker_id = body.get('worker_id', '').strip()
    age = body.get('age')
    gender = body.get('gender', '').strip().lower()
    nationality = body.get('nationality', '').strip()
    major = body.get('major', '').strip()
    
    # Validate MTurk Worker ID format (typically starts with 'A' and is alphanumeric)
    if worker_id:
        # MTurk Worker IDs are typically 14 characters starting with 'A'
        if not re.match(r'^A[A-Z0-9]{13,}$', worker_id):
            raise HTTPException(
                status_code=400,
                detail="Invalid MTurk Worker ID format. Worker IDs typically start with 'A' followed by alphanumeric characters (e.g., A12TU3EXAMPLE93)"
            )
        
        # Demographic fields are MANDATORY when setting worker ID
        if not age:
            raise HTTPException(
                status_code=400,
                detail="Age is required when setting MTurk Worker ID"
            )
        
        if not gender:
            raise HTTPException(
                status_code=400,
                detail="Gender is required when setting MTurk Worker ID"
            )
        
        if not nationality:
            raise HTTPException(
                status_code=400,
                detail="Nationality is required when setting MTurk Worker ID"
            )
        
        if not major:
            raise HTTPException(
                status_code=400,
                detail="Major/field of study is required when setting MTurk Worker ID"
            )
        
        # Validate age
        try:
            age_int = int(age)
            if age_int < 18 or age_int > 100:
                raise HTTPException(
                    status_code=400,
                    detail="Age must be between 18 and 100"
                )
        except (ValueError, TypeError):
            raise HTTPException(
                status_code=400,
                detail="Age must be a valid number"
            )
        
        # Validate gender
        valid_genders = ['male', 'female', 'wish_not_to_answer']
        if gender not in valid_genders:
            raise HTTPException(
                status_code=400,
                detail=f"Gender must be one of: {', '.join(valid_genders)}"
            )
        
        # Validate nationality and major (non-empty strings)
        if len(nationality) < 2:
            raise HTTPException(
                status_code=400,
                detail="Nationality must be at least 2 characters"
            )
        
        if len(major) < 2:
            raise HTTPException(
                status_code=400,
                detail="Major/field of study must be at least 2 characters"
            )
        
        # Update all fields atomically
        current_user.mturk_worker_id = worker_id
        current_user.age = age_int
        current_user.gender = gender
        current_user.nationality = nationality
        current_user.major = major
    else:
        # If clearing worker ID, clear demographics too
        current_user.mturk_worker_id = None
        current_user.age = None
        current_user.gender = None
        current_user.nationality = None
        current_user.major = None
    
    await db.commit()
    await db.refresh(current_user)
    
    print(f"✅ Updated MTurk Worker ID and demographics for user {current_user.user_id}: {worker_id}")
    
    return {
        "success": True,
        "mturk_worker_id": current_user.mturk_worker_id,
        "age": current_user.age,
        "gender": current_user.gender,
        "nationality": current_user.nationality,
        "major": current_user.major,
        "message": "MTurk Worker ID and demographics updated successfully"
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
    from .config import MTURK_WORKER_ID_PATTERN
    worker_id_pattern = re.compile(MTURK_WORKER_ID_PATTERN)
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
    # OPTIMIZATION: Select gems_earned directly to avoid N+1 queries
    from .database import SessionPlayer
    
    result = await db.execute(
        select(DBSession, SessionPlayer.gems_earned)
        .join(SessionPlayer, SessionPlayer.session_id == DBSession.id)
        .where(SessionPlayer.user_id == current_user.id)
        .where(SessionPlayer.role == 'human')  # Only human players, not AI
        .order_by(desc(DBSession.completed_at))
        .limit(10)
    )
    sessions_data = result.all()
    
    print(f"📊 Found {len(sessions_data)} recent sessions for user {current_user.user_id}")
    
    # Calculate last game amount (IN GEMS)
    last_game_gems = 0  # Start with 0, will be updated if we find a recent game
    highest_earning_gems = 0
    recent_sessions = []
    
    for idx, (session, gems_earned) in enumerate(sessions_data):
        # PRIMARY SOURCE: SessionPlayer.gems_earned (database truth)
        # This value represents the NET CHANGE (profit/loss) for the user in this session
        actual_gems = gems_earned
        display_amount = gems_earned
        
        # Fallback: JSON file (only if database value is missing - legacy support)
        if actual_gems is None:
            try:
                if session.stats_file_path and os.path.exists(session.stats_file_path):
                    with open(session.stats_file_path, 'r') as f:
                        stats_data = json.load(f)
                        gem_rewards = stats_data.get('gem_rewards', {})
                        
                        # We need to find the player ID again since we don't have it easily here
                        # But this is a rare fallback path, so a query is acceptable
                        player_result = await db.execute(
                            select(SessionPlayer).where(
                                SessionPlayer.session_id == session.id,
                                SessionPlayer.user_id == current_user.id
                            )
                        )
                        user_player = player_result.scalar_one_or_none()
                        
                        if user_player and user_player.player_id in gem_rewards:
                            reward_data = gem_rewards[user_player.player_id]
                            if isinstance(reward_data, dict):
                                display_amount = reward_data.get('net_change', reward_data.get('total_gems', 0))
                                actual_gems = display_amount
                            else:
                                actual_gems = reward_data
                                display_amount = actual_gems
                            print(f"   Session {idx} (fallback): {display_amount} gems from JSON")
            except Exception as e:
                print(f"   Session {idx}: Error in fallback loading: {e}")

        # Legacy Fallback: calculated_earnings
        if actual_gems is None and hasattr(session, 'calculated_earnings') and session.calculated_earnings:
             actual_gems = int(float(session.calculated_earnings) * GEMS_PER_DOLLAR)
             display_amount = actual_gems
        
        # Final Fallback: Average
        if actual_gems is None:
            actual_gems = avg_gems_per_game
            display_amount = actual_gems
            
        # Ensure we have a value
        if display_amount is None:
            display_amount = 0
            actual_gems = 0

        # Log the value found
        print(f"   Session {idx}: {display_amount} gems (Source: {'DB' if gems_earned is not None else 'Fallback'})")
        
        if idx == 0:  # Most recent game
            last_game_gems = display_amount
            print(f"✅ Last game gems set to: {last_game_gems}")
        
        # Track highest EARNING (not loss)
        if actual_gems > highest_earning_gems:
            highest_earning_gems = actual_gems
        
        # Store sessions with gem amounts for trend chart
        recent_sessions.append({
            "date": session.completed_at.isoformat(),
            "amount": display_amount,
            "status": "completed"
        })
    
    # FALLBACK: If no sessions found but user has gems, use average
    if len(sessions_data) == 0 and total_games > 0:
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


@app.get("/api/users/active-session")
async def get_active_session(
    current_user: User = Depends(get_current_user_optional)
):
    """
    Check if the current user has an active game session.
    Returns session info if user is currently in a game (waiting or in_progress).
    
    Args:
        current_user: Current authenticated user (optional)
    
    Returns:
        Active session info or indication that no active session exists
    """
    if not current_user:
        # Anonymous users - check by player_id in all rooms would require tracking
        # For now, anonymous users rely on client-side localStorage only
        return {
            "has_active_session": False,
            "room_code": None,
            "player_id": None,
            "room_status": None,
            "max_humans": None
        }
    
    user_id = str(current_user.id)
    print(f"🔍 Checking active session for user {current_user.user_id} (ID: {user_id[:8]}...)")
    
    # Search all rooms for this user's active session
    for room_code, room_data in rooms.items():
        room_status = room_data.get('room_status', '')
        
        # Only check rooms that are waiting or in_progress
        if room_status not in ['waiting', 'in_progress']:
            continue
        
        # Check player_user_map for this user
        player_user_map = room_data.get('player_user_map', {})
        
        for player_id, mapped_user_id in player_user_map.items():
            if mapped_user_id == user_id:
                # Found active session for this user
                # Use assigned_humans, never expose connection status
                assigned_humans = get_assigned_humans(room_data)
                max_humans = room_data.get('max_humans', 1)
                
                print(f"✅ Found active session: room={room_code}, player={player_id}, status={room_status}")
                
                return {
                    "has_active_session": True,
                    "room_code": room_code,
                    "player_id": player_id,
                    "room_status": room_status,
                    "max_humans": max_humans,
                    "current_humans_count": len(assigned_humans)
                    # NOTE: Do NOT expose is_connected - maintains player anonymity
                }
    
    print(f"❌ No active session found for user {current_user.user_id}")
    return {
        "has_active_session": False,
        "room_code": None,
        "player_id": None,
        "room_status": None,
        "max_humans": None
    }


@app.post("/api/users/heartbeat")
async def user_heartbeat(
    current_user: User = Depends(get_current_user_optional)
):
    """
    Receive heartbeat from active users to track online status.
    Works for both authenticated and anonymous users.
    
    Users send this periodically (every 30s) while browsing lobby, dashboard, or in-game.
    Users are considered "online" if they've sent a heartbeat within ONLINE_THRESHOLD_SECONDS.
    
    Args:
        current_user: Current authenticated user (optional)
    
    Returns:
        Status confirmation
    """
    if current_user:
        # Authenticated user - track by user_id
        user_id = str(current_user.id)
        update_user_activity(user_id)
        return {"status": "ok", "user_type": "authenticated", "user_id": current_user.user_id}
    else:
        # Anonymous user - for now we don't track anonymous users
        # Could be extended to use session tokens if needed
        return {"status": "ok", "user_type": "anonymous"}


@app.get("/api/lobby/online-users")
async def get_online_users():
    """
    Get the count of currently online users.
    Returns count of users who have sent a heartbeat within ONLINE_THRESHOLD_SECONDS.
    
    Returns:
        Dictionary with total_online count and threshold_seconds
    """
    online_count = get_online_users_count()
    
    return {
        "total_online": online_count,
        "threshold_seconds": ONLINE_THRESHOLD_SECONDS
    }


@app.get("/api/leaderboard")
async def get_leaderboard(
    db: AsyncSession = Depends(get_async_session),
    limit: int = 10
):
    """
    Get the top users by total gems earned, excluding admins.
    
    Args:
        db: Database session
        limit: Maximum number of users to return (default: 10)
    
    Returns:
        List of top users with rank, username, stats
    """
    # Query users table, filtering out admins
    result = await db.execute(
        select(User)
        .where(User.role == UserRole.USER)  # Exclude admins
        .order_by(desc(User.total_gems_earned))
        .limit(limit)
    )
    users = result.scalars().all()
    
    # Format leaderboard data
    leaderboard = []
    for rank, user in enumerate(users, start=1):
        # Calculate win rate
        win_rate = 0.0
        if user.total_games > 0:
            win_rate = (user.total_wins / user.total_games) * 100
        
        leaderboard.append({
            "rank": rank,
            "user_id": user.user_id,
            "total_gems_earned": user.total_gems_earned,
            "total_games": user.total_games,
            "total_wins": user.total_wins,
            "win_rate": round(win_rate, 1),  # Round to 1 decimal place
            "level": user.level
        })
    
    return {
        "leaderboard": leaderboard,
        "total_users": len(leaderboard)
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
    
    # Check if user has complete MTurk profile (worker ID + demographics)
    has_complete_profile = bool(
        current_user.mturk_worker_id and 
        current_user.age and 
        current_user.gender and 
        current_user.nationality and 
        current_user.major
    )
    
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
        "has_worker_id": has_complete_profile,  # Now checks for complete profile
        "has_demographics": bool(current_user.age and current_user.gender and current_user.nationality and current_user.major)
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
    # Rate limiting check (per user to prevent cashout spam)
    user_key = f"cashout_{current_user.id}"
    if not cashout_rate_limiter.is_allowed(user_key):
        log_rate_limit_violation(current_user.user_id, "/api/wallet/cashout")
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many cashout requests. Please wait a minute and try again."
        )
    
    from decimal import Decimal
    from .cashout_service import create_cashout_transaction, CashoutError
    from .config import EXTERNAL_URL
    
    body = await request.json()
    amount_usd = Decimal(str(body.get('amount_usd', 0)))
    
    # Log unusual cashout amounts for monitoring
    if amount_usd >= Decimal("50.00"):
        log_unusual_cashout(current_user.user_id, float(amount_usd))
    
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
    # Rate limiting check (per user to prevent cashout spam)
    user_key = f"cashout_{current_user.id}"
    if not cashout_rate_limiter.is_allowed(user_key):
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many cashout requests. Please wait a minute and try again."
        )
    
    from .cashout_endpoint_v2 import request_cashout_v2
    return await request_cashout_v2(request, current_user, db)


@app.get("/api/wallet/cashout/{transaction_id}/hit-ready")
async def check_cashout_hit_ready(
    transaction_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_session)
):
    """
    Check if MTurk HIT is ready for the worker to access.
    
    Returns:
        - ready: boolean indicating if HIT is accessible
        - message: status message
    """
    from .check_hit_ready import check_hit_ready
    return await check_hit_ready(transaction_id, current_user, db)


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
    # Rate limiting check (prevent abuse of cancel/re-request)
    user_key = f"cashout_cancel_{current_user.id}"
    if not cashout_rate_limiter.is_allowed(user_key):
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many requests. Please wait a minute and try again."
        )
    
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
    participant_name: Optional[str] = None,
    winner_name: Optional[str] = None,
    language: Optional[str] = None,
    discussion_duration: Optional[int] = None,
    voting_duration: Optional[int] = None,
    num_human_players: Optional[int] = None,
    total_players: Optional[int] = None,
    sort_by: Optional[str] = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_session)
):
    """
    List sessions for current user. Admins see all sessions with filtering options.
    
    Args:
        participant_name: Filter by participant username (Admin only)
        winner_name: Filter by winner username (Admin only)
        language: Filter by game language
        discussion_duration: Filter by discussion duration
        voting_duration: Filter by voting duration
        num_human_players: Filter by number of human players
        total_players: Filter by total players
        sort_by: Sort order (e.g., 'highest_reward')
        current_user: Current authenticated user
        db: Database session
    
    Returns:
        List of sessions
    """
    if current_user.role == UserRole.ADMIN:
        # Admins see all sessions with optional filters
        from .database import SessionPlayer
        from sqlalchemy.orm import aliased
        
        query = select(DBSession)
        
        # 1. Participant Filter
        if participant_name:
            p_player = aliased(SessionPlayer)
            p_user = aliased(User)
            query = query.join(p_player, p_player.session_id == DBSession.id)\
                         .join(p_user, p_player.user_id == p_user.id)\
                         .where(p_user.user_id.ilike(f"%{participant_name}%"))
        
        # 2. Winner Filter (User who participated and earned > 0 gems)
        if winner_name:
            w_player = aliased(SessionPlayer)
            w_user = aliased(User)
            query = query.join(w_player, w_player.session_id == DBSession.id)\
                         .join(w_user, w_player.user_id == w_user.id)\
                         .where(w_user.user_id.ilike(f"%{winner_name}%"))\
                         .where(w_player.gems_earned > 0)
        
        # 3. Game Type Filters
        if language:
            query = query.where(DBSession.language == language)
        if discussion_duration is not None:
            query = query.where(DBSession.discussion_duration == discussion_duration)
        if voting_duration is not None:
            query = query.where(DBSession.voting_duration == voting_duration)
        if num_human_players is not None:
            query = query.where(DBSession.num_human_players == num_human_players)
        if total_players is not None:
            query = query.where(DBSession.total_players == total_players)
            
        # 4. Sorting
        if sort_by == 'highest_reward':
            # Sort by max gems earned in the session
            subq = select(func.max(SessionPlayer.gems_earned)).where(SessionPlayer.session_id == DBSession.id).scalar_subquery()
            query = query.order_by(desc(subq))
        else:
            # Default sort: Most recent first
            query = query.order_by(desc(DBSession.completed_at))
            
        result = await db.execute(query.distinct())
        sessions_with_gems = [(s, None) for s in result.scalars().all()]
    else:
        # Regular users see sessions where they're the owner OR where they played
        from .database import SessionPlayer
        from sqlalchemy import or_, and_
        
        # Get sessions where user is owner OR participated as a player
        # OPTIMIZATION: Fetch gems_earned directly to avoid N+1 file reads
        result = await db.execute(
            select(DBSession, SessionPlayer.gems_earned)
            .outerjoin(SessionPlayer, and_(
                SessionPlayer.session_id == DBSession.id,
                SessionPlayer.user_id == current_user.id
            ))
            .where(
                or_(
                    DBSession.user_id == current_user.id,
                    SessionPlayer.user_id == current_user.id
                )
            )
            .order_by(desc(DBSession.completed_at))
        )
        sessions_with_gems = result.all()
    
    # Extract sessions for highest reward query
    sessions = [s for s, _ in sessions_with_gems]
    
    # Load gem rewards for each session from JSON files
    session_list = []
    
    # Import for highest_reward query
    from .database import SessionPlayer
    
    # Optimization: Fetch all highest rewards in a single query to avoid N+1
    highest_rewards_map = {}
    if sessions:
        try:
            session_ids = [s.id for s in sessions]
            # Query max gems earned per session for the current batch
            stmt = select(SessionPlayer.session_id, func.max(SessionPlayer.gems_earned))\
                   .where(SessionPlayer.session_id.in_(session_ids))\
                   .group_by(SessionPlayer.session_id)
            
            rewards_result = await db.execute(stmt)
            # Map session_id -> max_gems
            highest_rewards_map = {row[0]: (row[1] or 0) for row in rewards_result.all()}
        except Exception as e:
            print(f"Error fetching highest rewards batch: {e}")
    
    for s, gems_earned_db in sessions_with_gems:
        # Get highest reward for this session from pre-fetched map
        highest_reward = highest_rewards_map.get(s.id, 0)

        session_data = {
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
            "highest_reward": highest_reward,
            "claimed_at": s.claimed_at.isoformat() if s.claimed_at else None,
            "gem_earned": gems_earned_db  # Use DB value!
        }
        
        # Fallback: Load from JSON only if DB value is missing (legacy sessions)
        if session_data["gem_earned"] is None:
            try:
                if s.stats_file_path and os.path.exists(s.stats_file_path):
                    with open(s.stats_file_path, 'r') as f:
                        stats_data = json.load(f)
                        gem_rewards = stats_data.get('gem_rewards', {})
                        
                        # Find which player was this user
                        from .database import SessionPlayer
                        # We still need to query here if we don't have the player ID
                        # But this only runs for legacy data.
                        player_result = await db.execute(
                            select(SessionPlayer).where(
                                SessionPlayer.session_id == s.id,
                                SessionPlayer.user_id == current_user.id
                            )
                        )
                        user_player = player_result.scalar_one_or_none()
                        if user_player and user_player.player_id in gem_rewards:
                            reward_data = gem_rewards[user_player.player_id]
                            if isinstance(reward_data, dict):
                                session_data["gem_earned"] = reward_data.get('net_change', reward_data.get('total_gems', 0))
                            else:
                                session_data["gem_earned"] = reward_data
            except Exception as gem_load_error:
                print(f"⚠️ Could not load gem_earned for session {s.id}: {gem_load_error}")
        
        session_list.append(session_data)
    
    return {
        "sessions": session_list
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
        print(f"🔍 Looking for player identification: session_id={session_uuid}, user_id={current_user.id}")
        player_result = await db.execute(
            select(SessionPlayer).where(
                SessionPlayer.session_id == session_uuid,
                SessionPlayer.user_id == current_user.id
            )
        )
        user_player = player_result.scalar_one_or_none()
        if user_player:
            current_user_player_id = user_player.player_id
            print(f"✅ Found player identification: {current_user_player_id} for user {current_user.user_id}")
        else:
            print(f"⚠️ No player identification found for user {current_user.user_id} in session {session_uuid}")
            # Debug: List all SessionPlayers for this session
            debug_result = await db.execute(
                select(SessionPlayer).where(SessionPlayer.session_id == session_uuid)
            )
            all_session_players = debug_result.scalars().all()
            print(f"📋 All SessionPlayers in this session: {[(sp.player_id, sp.user_id, sp.role) for sp in all_session_players]}")
    except Exception as e:
        print(f"❌ Error getting player identification: {e}")
        import traceback
        traceback.print_exc()
    
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
    
    # Get gem earned for this specific user (full breakdown)
    gem_earned = None
    gem_breakdown = None
    if current_user_player_id and stats_data:
        gem_rewards = stats_data.get('gem_rewards', {})
        if current_user_player_id in gem_rewards:
            reward_data = gem_rewards[current_user_player_id]
            # Handle both old format (just number) and new format (breakdown)
            if isinstance(reward_data, dict):
                gem_breakdown = reward_data
                gem_earned = reward_data.get('net_change', reward_data.get('total_gems', 0))  # Use net_change for display
            else:
                gem_earned = reward_data  # Old format (just a number)
            print(f"💎 User {current_user.user_id} net change: {gem_earned} gems as {current_user_player_id}")
    
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
        "calculated_earnings": float(session.calculated_earnings) if session.calculated_earnings else None,
        "gem_earned": gem_earned,  # Actual gems won/lost (can be negative)
        "gem_breakdown": gem_breakdown  # Full breakdown: base_gems, stake_gems, total_gems
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


@app.get("/api/admin/room-stats")
async def get_admin_room_stats(
    admin_user: User = Depends(require_admin)
):
    """
    Get statistics about currently operating rooms for admins.
    
    Args:
        admin_user: Current admin user
    
    Returns:
        Room operation statistics including solo-human and multi-human breakdowns
    """
    # Count rooms that are actually operating (in_progress or waiting with players)
    operating_rooms = []
    for room_code, room_data in rooms.items():
        room_status = room_data.get('room_status', '')
        
        # Only count rooms that are truly active
        # in_progress = game is running
        # waiting = game hasn't started but has players
        if room_status == 'in_progress':
            operating_rooms.append({
                'room_code': room_code,
                'max_humans': room_data.get('max_humans'),
                'total_players': room_data.get('total_players'),
                'status': room_status
            })
        elif room_status == 'waiting':
            # Only count waiting rooms that have at least 1 player
            assigned_humans = room_data.get('assigned_humans', [])
            if len(assigned_humans) > 0:
                operating_rooms.append({
                    'room_code': room_code,
                    'max_humans': room_data.get('max_humans'),
                    'total_players': room_data.get('total_players'),
                    'status': room_status
                })
    
    # Count solo-human rooms (max_humans == 1)
    solo_human_count = len([r for r in operating_rooms if r['max_humans'] == 1])
    total_operating = len(operating_rooms)
    
    print(f"📊 Admin room stats: {total_operating} operating ({solo_human_count} solo, {total_operating - solo_human_count} multi)")
    
    return {
        "total_operating": total_operating,
        "solo_human_count": solo_human_count,
        "multi_human_count": total_operating - solo_human_count,
        "rooms": operating_rooms  # For debugging
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
async def create_room(
    room_data: dict, 
    current_user: User = Depends(get_current_user_optional),
    db: AsyncSession = Depends(get_async_session)
):
    """
    Create a new matching room.
    
    Args:
        room_data: Dict with:
            - max_humans: Maximum human players (1-4, default 1)
            - total_players: Total players including AI (default 5)
            - language: Room language - "english" or "korean" (default "english")
            - discussion_duration: Discussion time in seconds (60, 180, or 240, default 180)
            - voting_duration: Voting time in seconds (30, 60, or 120, default 60)
            - stake_percentage: Stake percentage for multi-human games (0, 10, 30, 50, 100)
    
    Returns:
        Room creation response with room_code and room_name
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
    
    # Multi-human room validation: Must have at least 250 gems
    if max_humans > 1:
        if not current_user:
            return {"success": False, "error": "Authentication required to create multi-human rooms"}
        
        if current_user.gem_balance < 250:
            return {
                "success": False, 
                "error": f"Insufficient gems. You need at least 250 gems to create a multi-human room. Your balance: {current_user.gem_balance} gems"
            }
    
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
    # This will raise HTTPException if API keys are not configured
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
        'minimum_stake': 0  # Minimum stake across all players (recalculated as players join)
    }
    
    # Initialize lock for this room
    if room_code not in room_locks:
        room_locks[room_code] = asyncio.Lock()
    
    print(f"🎮 Created room {room_code} ({room_name}): {max_humans} humans, {total_players} total, language: {language}, discussion: {discussion_duration}s, voting: {voting_duration}s, stake: {stake_percentage}%")
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
        "voting_duration": voting_duration,
        "stake_percentage": stake_percentage,
        "minimum_stake": 0  # Will be calculated as players join
    }


@app.get("/api/rooms/{room_code}/stake_info")
async def get_stake_info(room_code: str):
    """
    Get stake information for a multi-human room.
    
    Args:
        room_code: Room identifier
    
    Returns:
        Stake information including current minimum stake and player stakes
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


@app.post("/api/rooms/{room_code}/leave")
async def leave_room_endpoint(room_code: str, player_data: dict):
    """
    Handle a player leaving a room.
    - Single-player (max_humans=1): Terminate room immediately
    - Multi-player in waiting: Terminate room
    - Multi-player in progress: Keep room alive, remove player from current_humans
    
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
        "winning_players": state.get('winning_players', []),
        "selected_suspect": state.get('selected_suspect'),
        "suspect_role": state.get('suspect_role'),
        "current_player_id": player_id,
        "typing": list(state.get('typing_players', set()))
    }


@app.post("/api/rooms/{room_code}/join")
async def join_room(
    room_code: str, 
    player_data: dict,
    current_user: User = Depends(get_current_user_optional),
    db: AsyncSession = Depends(get_async_session)
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
    
    # Initialize lock for this room if needed (before any room operations)
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
    
        # HANDLE REJOIN: Check if user is already in THIS room (disconnected and rejoining)
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
                
                    # Get assigned_humans list (with backward compatibility)
                    # Get a copy to avoid modifying the original list directly
                    current_assigned = get_assigned_humans(room)
                    assigned_humans = current_assigned.copy() if current_assigned else []
                
                    # Add back to assigned_humans if not there (CHECK FOR DUPLICATES)
                    if player_id not in assigned_humans:
                        assigned_humans.append(player_id)
                        room['assigned_humans'] = assigned_humans
                        sync_assigned_and_current_humans(room)
                        print(f"✅ Added {player_id} back to assigned_humans. Total: {len(assigned_humans)}")
                    else:
                        print(f"ℹ️  {player_id} already in assigned_humans (duplicate avoided)")
                        # Even if already there, update the room's assigned_humans to use our copy
                        room['assigned_humans'] = assigned_humans
                    
                    # Track player activity (rejoining counts as activity)
                    update_player_activity(room, player_id)
                    update_player_heartbeat(room, player_id)  # Update heartbeat on rejoin
                
                    # Check if room can/should start or resume
                    max_humans = room.get('max_humans', 4)
                    can_start = len(assigned_humans) >= max_humans
                    room_status = room.get('room_status', '')
                
                    # STATE MACHINE: Handle different room states
                    # waiting -> in_progress (when enough players join)
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
                            
                            # Immediately send timer sync for initial discussion phase (FIX: Prevent timer desync at game start)
                            discussion_duration = room.get('discussion_duration', DISCUSSION_TIME)
                            await broadcast_to_room(room_code, {
                                "type": "timer_sync",
                                "phase": "Discussion",
                                "time_remaining": int(discussion_duration)
                            })
                            
                            await asyncio.sleep(0.75)
                            asyncio.create_task(trigger_agent_decisions(room_code))
                    
                    # resuming -> in_progress (when enough players rejoin an abandoned game)
                    elif room_status == 'resuming' and can_start:
                        room['room_status'] = 'in_progress'
                        print(f"🔄 Resuming game in room {room_code} after players rejoined ({len(assigned_humans)}/{max_humans})")
                        # Game was already initialized, just continue where it left off
                    
                    # abandoned -> resuming (handled by heartbeat endpoint, but ensure consistency)
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
            total_players = NUM_AI_PLAYERS + 1
            all_numbers = list(range(1, total_players + 1))
            random.shuffle(all_numbers)
            human_number = all_numbers[0]
            player_id = f"Player {human_number}"
        
            # Assign remaining numbers to AI players
            ai_numbers = all_numbers[1:]
            ai_player_ids = [f"Player {num}" for num in ai_numbers]
        
            # Get next API key for this room (round-robin with error handling)
            try:
                api_key, api_key_index = get_api_key_for_room()
            except HTTPException as e:
                # Legacy room creation failure - return error
                return {
                    "success": False,
                    "error": f"Failed to create room: {e.detail}",
                    "player_id": None
                }
        
            # Create game state with properly numbered AI players
            state = create_game_for_room(room_code, NUM_AI_PLAYERS, ai_player_ids)
            
            # Create game graph with assigned API key
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
                'max_humans': 4,
                'total_players': total_players,
                'room_status': 'waiting',
                'created_at': time.time(),
                'creator_id': player_id,
                'player_user_map': {},  # Maps player_id -> user_id (for authenticated users)
                'current_humans': [],  # DEPRECATED - kept for backward compatibility
                'assigned_humans': [],  # Players with permanent slots
                'connected_humans': [],  # Currently connected (internal use only)
                'permanently_left': set(),  # Players who explicitly left
                'player_last_activity': {},  # player_id -> timestamp
                'player_heartbeat': {},  # player_id -> timestamp
                'available_numbers': [],  # All assigned for legacy rooms
                'human_overflow_counter': 0,  # Counter for H1, H2 fallback numbering
                'discussion_duration': DISCUSSION_TIME,  # Use default config for legacy rooms
                'voting_duration': VOTING_TIME,  # Use default config for legacy rooms
                'game_graph': game_graph,  # Room-specific GameGraph with assigned API key
                'api_key_index': api_key_index  # Track which API key is assigned
            }
            # Initialize lock for this room to prevent race conditions
            if room_code not in room_locks:
                room_locks[room_code] = asyncio.Lock()
        
            # Initialize game
            game_graph = rooms[room_code]['game_graph']
            result = game_graph.initialize_game_node(state)
            state.update(result)
            rooms[room_code]['state'] = state
        
            # Start phases
            asyncio.create_task(run_discussion_phase(room_code))
            
            # Immediately send timer sync for initial discussion phase (FIX: Prevent timer desync at game start)
            discussion_duration = rooms[room_code].get('discussion_duration', DISCUSSION_TIME)
            await broadcast_to_room(room_code, {
                "type": "timer_sync",
                "phase": "Discussion",
                "time_remaining": int(discussion_duration)
            })
            
            # Trigger active decision-making for AI responses
            await asyncio.sleep(0.75)  # Small delay
            asyncio.create_task(trigger_agent_decisions(room_code))
    
        room = rooms[room_code]
        print(f"🔍 Room {room_code} exists - discussion_duration: {room.get('discussion_duration', 'NOT SET')}, voting_duration: {room.get('voting_duration', 'NOT SET')}")
    
        # Check room status - only allow new joins to "waiting" rooms
        room_status = room.get('room_status', '')
        
        if room_status == 'in_progress':
            return {"success": False, "error": "Room already in progress"}
        
        if room_status == 'completed':
            return {"success": False, "error": "Room game completed"}
        
        if room_status in ['abandoned', 'resuming']:
            return {"success": False, "error": "Room is not accepting new players. Only rejoins allowed."}
    
        # Check capacity (use assigned_humans for accurate count)
        max_humans = room.get('max_humans', 4)
        assigned_humans = get_assigned_humans(room)
    
        if len(assigned_humans) >= max_humans:
            return {"success": False, "error": f"Room full ({max_humans} humans max)"}
        
        # MULTI-HUMAN ROOM VALIDATION: Check gem balance requirement
        if max_humans > 1:
            if not current_user:
                return {
                    "success": False, 
                    "error": "Authentication required to join multi-human rooms"
                }
            
            if current_user.gem_balance < 250:
                return {
                    "success": False, 
                    "error": f"Insufficient gems. You need at least 250 gems to join a multi-human room. Your balance: {current_user.gem_balance} gems"
                }
    
        # Get state
        state = room['state']
    
        # Assign a random player number from available numbers
        available_numbers = room.get('available_numbers', [])
        if not available_numbers:
            # Fallback: use deterministic numbering (Player H1, H2, etc.)
            # This should NEVER happen in normal operation
            human_overflow_counter = room.get('human_overflow_counter', 0)
            human_overflow_counter += 1
            room['human_overflow_counter'] = human_overflow_counter
            player_id = f"Player H{human_overflow_counter}"
            print(f"⚠️  WARNING: available_numbers exhausted! Using overflow numbering: {player_id}")
        else:
            # Pop a number from available
            player_number = available_numbers.pop(0)
            player_id = f"Player {player_number}"
    
        # Add player to assigned_humans list (and sync with current_humans)
        # Get a copy to avoid modifying the original list directly
        current_assigned = get_assigned_humans(room)
        assigned_humans = current_assigned.copy() if current_assigned else []
        assigned_humans.append(player_id)
        room['assigned_humans'] = assigned_humans
        sync_assigned_and_current_humans(room)
    
        # Track player activity (joining counts as activity)
        update_player_activity(room, player_id)
        update_player_heartbeat(room, player_id)  # Initial heartbeat
    
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
            
            # Calculate and store stake for multi-human rooms
            if max_humans > 1:
                stake_percentage = room.get('stake_percentage', 0)
                player_stake = int(current_user.gem_balance * stake_percentage / 100)
                room['player_stakes'][player_id] = player_stake
                
                # Recalculate minimum stake across all joined players
                all_stakes = list(room['player_stakes'].values())
                if all_stakes:
                    room['minimum_stake'] = min(all_stakes)
                    print(f"💎 Player {player_id} stake: {player_stake} gems ({stake_percentage}% of {current_user.gem_balance})")
                    print(f"💎 Room minimum stake updated to: {room['minimum_stake']} gems")
                    
                    # Broadcast stake update to all connected players
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
            # Update room status to in_progress
            room['room_status'] = 'in_progress'
        
            print(f"🎮 Starting game in room {room_code} with {len(room['current_humans'])} humans")
        
            # Initialize game if not already initialized
            if 'initialized' not in room:
                game_graph = rooms[room_code]['game_graph']
                result = game_graph.initialize_game_node(state)
                state.update(result)
                rooms[room_code]['state'] = state
                rooms[room_code]['initialized'] = True
            
                # Broadcast initial state to any connected clients
                if 'broadcast_queue' in result:
                    for msg in result['broadcast_queue']:
                        await broadcast_to_room(room_code, msg)
                
                # CHANGED: Don't deduct stakes at game start anymore
                # Stakes will only be deducted AFTER voting completes successfully
                # This protects players from losing gems due to technical failures
                print(f"💎 Stakes configured but NOT deducted yet (will deduct after successful voting)")
                print(f"   Minimum stake: {room.get('minimum_stake', 0)} gems per player")
                print(f"   Stakes at risk (not charged): {room.get('player_stakes', {})}")
            
                # Start phases
                print(f"🚀 Starting game phases - discussion_duration: {room.get('discussion_duration', 'NOT SET')}, voting_duration: {room.get('voting_duration', 'NOT SET')}")
                asyncio.create_task(run_discussion_phase(room_code))
                
                # Immediately send timer sync for initial discussion phase (FIX: Prevent timer desync at game start)
                discussion_duration = room.get('discussion_duration', DISCUSSION_TIME)
                await broadcast_to_room(room_code, {
                    "type": "timer_sync",
                    "phase": "Discussion",
                    "time_remaining": int(discussion_duration)
                })
                
                # Trigger active decision-making for AI responses
                await asyncio.sleep(0.75)  # Small delay
                asyncio.create_task(trigger_agent_decisions(room_code))
    
        # Use assigned_humans count for display (never expose connected_humans)
        assigned_humans_count = len(get_assigned_humans(room))
        
        return {
            "success": True,
            "message": f"Joined room {room_code}",
            "player_id": player_id,
            "can_start": can_start,
            "waiting": not can_start,
            "current_humans": assigned_humans_count,  # Shows assigned slots, not actual connections
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
    
    room = rooms[room_code]
    state = room['state']
    
    # Track player activity
    update_player_activity(room, player_id)
    
    # Check if in discussion phase
    if state['phase'] != Phase.DISCUSSION:
        return {"error": "Not in discussion phase"}
    
    # Validate message length
    if len(message) > 400:
        return {"error": "Message exceeds 400 character limit"}

    # Rate limiting
    current_time = time.time()
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
    # Include timestamp from the last added message in history
    last_msg = state['chat_history'][-1] if state['chat_history'] else {}
    msg_timestamp = last_msg.get('timestamp', current_time)

    await broadcast_to_room(room_code, {
        "type": "message",
        "sender": player_id,
        "message": message,
        "timestamp": msg_timestamp
    })
    
    # Trigger agent decision-making (they'll decide if they want to respond)
    asyncio.create_task(trigger_agent_decisions(room_code))
    
    return {"success": True}


@app.post("/api/rooms/{room_code}/vote")
async def cast_vote(room_code: str, vote_data: dict):
    """
    Cast votes from Streamlit client.
    
    Args:
        room_code: Room identifier
        vote_data: Dict with 'player_id' and 'voted_for' fields
                  voted_for can be a single string (legacy) or list of strings (multi-human)
    
    Returns:
        Success status
    """
    if room_code not in rooms:
        return {"error": "Room not found"}
    
    player_id = vote_data.get('player_id', 'StreamlitUser')
    voted_for = vote_data.get('voted_for')
    
    # Convert single vote to list for consistency
    if not isinstance(voted_for, list):
        voted_for = [voted_for] if voted_for else []
    
    state = rooms[room_code]['state']
    
    # Detailed logging for vote submission
    print(f"🗳️ Vote submission from {player_id} in room {room_code}")
    print(f"   Voted for: {voted_for}")
    print(f"   Current phase: {state['phase']}")
    print(f"   Current votes: {state.get('votes', {})}")
    
    # Check if in voting phase
    if state['phase'] != Phase.VOTING:
        error_msg = f"Not in voting phase (current: {state['phase'].value})"
        print(f"   ❌ {error_msg}")
        return {"error": error_msg}
    
    # Check if already voted (enforce single vote per player)
    if player_id in state.get('votes', {}):
        error_msg = "Already voted"
        print(f"   ❌ {error_msg} - Player {player_id} attempted duplicate vote in room {room_code}")
        return {"error": error_msg}
    
    # Validate vote count for multi-human games
    human_players = [p for p in state['players'] if p['role'] == 'human' and not p['eliminated']]
    num_humans = len(human_players)
    
    print(f"   Human players: {[p['id'] for p in human_players]}")
    print(f"   All players: {[(p['id'], p['role']) for p in state['players']]}")
    
    if num_humans > 1:
        # Multi-human game: must vote for exactly N-1 humans
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
                print(f"   Available players: {[p['id'] for p in state['players'] if not p['eliminated']]}")
                return {"error": error_msg}
    
    # Track player activity
    update_player_activity(rooms[room_code], player_id)
    
    # Process human vote - directly update votes dict to avoid race conditions with AI voting
    state['votes'][player_id] = voted_for
    rooms[room_code]['state'] = state
    
    print(f"✅ Human vote recorded: {player_id} → {voted_for}")
    print(f"📊 Current votes after human: {state.get('votes', {})}")
    
    try:
        # Broadcast vote to WebSocket clients
        await broadcast_to_room(room_code, {
            "type": "voted",
            "player": player_id
        })
        
        # Check if all votes are in
        # In multi-human games: only humans vote
        # In single-human games: all active players vote
        active_player_ids = [p['id'] for p in state['players'] if not p['eliminated']]
        human_player_ids = [p['id'] for p in state['players'] if p['role'] == 'human' and not p['eliminated']]
        
        if num_humans > 1:
            # Multi-human game: wait for all humans to vote
            required_votes = len(human_player_ids)
            print(f"📊 Multi-human voting check: {len(state['votes'])}/{required_votes} humans voted")
        else:
            # Single-human game: wait for all active players (human + AIs) to vote
            required_votes = len(active_player_ids)
            print(f"📊 Single-human voting check: {len(state['votes'])}/{required_votes} players voted")
        
        if len(state['votes']) >= required_votes:
            print(f"✅ All required votes received, completing voting...")
            try:
                await complete_voting(room_code)
            except Exception as completion_error:
                print(f"❌ Error during vote completion: {type(completion_error).__name__}: {str(completion_error)}")
                import traceback
                traceback.print_exc()
                # Return success for the vote itself, but log the completion error
                # The global exception handler will handle this
                raise
        
        return {"success": True}
        
    except Exception as e:
        print(f"❌ Error processing vote for {player_id}: {type(e).__name__}: {str(e)}")
        import traceback
        traceback.print_exc()
        # Re-raise to let global exception handler deal with it
        raise


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


@app.post("/api/rooms/{room_code}/heartbeat")
async def player_heartbeat(room_code: str, heartbeat_data: dict):
    """
    Receive heartbeat ping from a player.
    This is used to track player activity and detect disconnections.
    
    IMPORTANT: This endpoint does NOT expose any information about other players
    to maintain anonymity about who is connected vs disconnected.
    
    Args:
        room_code: Room identifier
        heartbeat_data: Dict with 'player_id' field
    
    Returns:
        Minimal success response (no room state info)
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
    
    # Return minimal response (no room state information)
    return {
        "success": True,
        "timestamp": time.time()
    }