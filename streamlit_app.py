"""
Streamlit Frontend for Human Hunter Game
A polling-based alternative to the React WebSocket frontend.
"""

import streamlit as st
import streamlit.components.v1 as components
import requests
import time
import os
import json
from datetime import datetime

# -----------------------------------------------------------------------------
# UI Styling Helpers
# -----------------------------------------------------------------------------

def inject_global_styles():
    """Inject global CSS to polish the app's visual design."""
    st.markdown(
        """
        <style>
        /* Game-like theme with light/dark mode support */
        :root {
          /* Light mode colors (default) */
          --bg: #f5f7fb;
          --bg-2: #e8ebf5;
          --bg-gradient: linear-gradient(135deg, #f5f7fb 0%, #e8ebf5 50%, #dce1f0 100%);
          --panel: rgba(255, 255, 255, 0.95);
          --panel-light: rgba(248, 250, 255, 0.9);
          --text: #1a1f36;
          --text-bright: #0f1419;
          --text-secondary: #4a5568;
          --muted: #6b7280;
          --primary: #0284c7;
          --secondary: #c026d3;
          --accent: #7c3aed;
          --success: #059669;
          --warning: #d97706;
          --danger: #dc2626;
          --border: rgba(0, 0, 0, 0.1);
          --border-glow: rgba(2, 132, 199, 0.3);
          --bubble-left-bg: #f3f4f6;
          --bubble-left-text: #1f2937;
          --bubble-right-bg: linear-gradient(135deg, #0284c7, #7c3aed);
          --bubble-right-text: #ffffff;
          --card-hover: rgba(2, 132, 199, 0.08);
          --shadow: rgba(0, 0, 0, 0.1);
          --shadow-glow: rgba(2, 132, 199, 0.2);
        }
        
        /* Dark mode colors */
        @media (prefers-color-scheme: dark) {
          :root {
            --bg: #0f1419;
            --bg-2: #1a1f2e;
            --bg-gradient: linear-gradient(135deg, #0f1419 0%, #1a1f2e 50%, #252a3a 100%);
            --panel: rgba(30, 35, 50, 0.95);
            --panel-light: rgba(40, 46, 65, 0.9);
            --text: #e5e7eb;
            --text-bright: #f9fafb;
            --text-secondary: #d1d5db;
            --muted: #9ca3af;
            --primary: #38bdf8;
            --secondary: #e879f9;
            --accent: #a78bfa;
            --success: #34d399;
            --warning: #fbbf24;
            --danger: #f87171;
            --border: rgba(255, 255, 255, 0.1);
            --border-glow: rgba(56, 189, 248, 0.4);
            --bubble-left-bg: rgba(45, 52, 70, 0.9);
            --bubble-left-text: #e5e7eb;
            --bubble-right-bg: linear-gradient(135deg, #38bdf8, #a78bfa);
            --bubble-right-text: #ffffff;
            --card-hover: rgba(56, 189, 248, 0.12);
            --shadow: rgba(0, 0, 0, 0.3);
            --shadow-glow: rgba(56, 189, 248, 0.3);
          }
        }
        
        /* Global background */
        .stApp {
          background: var(--bg-gradient) !important;
        }
        .appview-container {
          background: var(--bg-gradient) !important;
        }
        
        /* Buttons with glow effect */
        .stButton>button {
          background: linear-gradient(135deg, var(--primary), var(--accent)) !important;
          color: #ffffff !important;
          border: 2px solid var(--primary) !important;
          border-radius: 12px !important;
          font-weight: 600 !important;
          padding: 0.6rem 1.5rem !important;
          transition: all 0.3s ease !important;
          box-shadow: 0 2px 10px var(--shadow-glow) !important;
        }
        .stButton>button:hover {
          box-shadow: 0 4px 20px var(--shadow-glow) !important;
          transform: translateY(-2px) !important;
          border-color: var(--border-glow) !important;
        }
        
        /* Cards and panels */
        .stAlert, .stMetric {
          border-radius: 12px !important;
          background: var(--panel) !important;
          border: 1px solid var(--border) !important;
        }
        
        /* Topic card */
        .topic-card {
          background: var(--panel);
          border: 2px solid var(--border);
          border-radius: 16px;
          padding: 12px 18px;
          color: var(--text);
          box-shadow: 0 4px 20px rgba(0, 212, 255, 0.15);
          margin: 10px 0;
        }
        
        /* Chat */
        .chat-wrap {
          background: var(--panel);
          border: 2px solid var(--border);
          border-radius: 16px;
          padding: 12px 16px;
          max-height: 52vh;
          overflow-y: auto;
          box-shadow: 0 4px 20px var(--shadow);
        }
        .chat-item { display: flex; gap: 10px; margin: 8px 0; align-items: flex-end; }
        .chat-avatar {
          width: 32px;
          height: 32px;
          border-radius: 50%;
          display: flex;
          align-items: center;
          justify-content: center;
          font-weight: 700;
          color: #fff;
          box-shadow: 0 2px 8px var(--shadow-glow);
        }
        .chat-bubble { padding: 10px 12px; border-radius: 12px; max-width: 75%; line-height: 1.35; }
        .chat-left { justify-content: flex-start; }
        .chat-left .chat-bubble {
          background: var(--bubble-left-bg);
          color: var(--bubble-left-text);
          border: 1px solid var(--border);
        }
        .chat-right { justify-content: flex-end; }
        .chat-right .chat-bubble {
          background: var(--bubble-right-bg);
          color: #ffffff;
          box-shadow: 0 2px 12px var(--shadow-glow);
        }
        .chat-meta { font-size: 11px; color: var(--muted); margin-top: 2px; }
        .typing { font-style: italic; color: var(--text-secondary); padding: 6px 12px; }

        /* Chat input styling */
        [data-testid="stChatInput"] > div {
          background: var(--panel) !important;
          border: 2px solid var(--border) !important;
          border-radius: 16px !important;
          padding: 8px 12px !important;
        }
        [data-testid="stChatInput"] textarea, [data-testid="stChatInput"] input {
          color: var(--text) !important;
          background: transparent !important;
        }
        [data-testid="stChatInput"] textarea::placeholder, [data-testid="stChatInput"] input::placeholder {
          color: var(--muted) !important;
        }

        /* Sidebar player list */
        .player-card {
          display: flex;
          align-items: center;
          gap: 10px;
          padding: 10px 12px;
          border-radius: 12px;
          border: 2px solid var(--border);
          background: var(--panel);
          margin-bottom: 10px;
          transition: all 0.3s ease;
        }
        .player-card:hover {
          border-color: var(--border-glow);
          box-shadow: 0 0 15px rgba(0, 212, 255, 0.2);
        }
        .player-name { font-weight: 600; color: var(--text); }
        .player-badge {
          font-size: 11px;
          padding: 3px 8px;
          border-radius: 999px;
          font-weight: 600;
          border: 1px solid;
        }
        .badge-danger {
          background: rgba(255, 0, 85, 0.2);
          color: var(--danger);
          border-color: var(--danger);
        }
        .badge-ok {
          background: rgba(0, 255, 136, 0.2);
          color: var(--success);
          border-color: var(--success);
        }
        
        /* Room card for lobby */
        .room-card {
          background: var(--panel);
          border: 2px solid var(--border);
          border-radius: 16px;
          padding: 20px;
          margin: 12px 0;
          transition: all 0.3s ease;
          cursor: pointer;
          box-shadow: 0 4px 15px var(--shadow);
        }
        .room-card:hover {
          border-color: var(--border-glow);
          box-shadow: 0 4px 25px var(--shadow-glow);
          transform: translateY(-4px);
          background: var(--card-hover);
        }
        .room-card-title {
          font-size: 1.3rem;
          font-weight: 700;
          color: var(--primary);
          margin-bottom: 12px;
        }
        .room-card-info {
          display: flex;
          justify-content: space-between;
          align-items: center;
          margin: 8px 0;
          color: var(--text);
          font-size: 0.95rem;
        }
        .room-card-label {
          color: var(--text-secondary);
          font-weight: 500;
        }
        .room-card-value {
          color: var(--text-bright);
          font-weight: 600;
        }
        .room-status-badge {
          display: inline-block;
          padding: 4px 12px;
          border-radius: 999px;
          font-size: 0.85rem;
          font-weight: 600;
          margin: 8px 0;
        }
        .status-waiting {
          background: rgba(0, 255, 136, 0.2);
          color: var(--success);
          border: 1px solid var(--success);
        }
        .status-almost {
          background: rgba(255, 170, 0, 0.2);
          color: var(--warning);
          border: 1px solid var(--warning);
        }
        
        /* Lobby header */
        .lobby-header {
          text-align: center;
          padding: 20px 0;
          margin-bottom: 20px;
        }
        .lobby-title {
          font-size: 2.5rem;
          font-weight: 800;
          background: linear-gradient(135deg, var(--primary), var(--secondary));
          -webkit-background-clip: text;
          -webkit-text-fill-color: transparent;
          background-clip: text;
          margin-bottom: 10px;
        }
        .lobby-subtitle {
          font-size: 1.1rem;
          color: var(--text-secondary);
          font-weight: 400;
        }
        
        /* Waiting screen */
        .waiting-container {
          text-align: center;
          padding: 40px 20px;
          background: var(--panel);
          border: 2px solid var(--border);
          border-radius: 20px;
          margin: 20px auto;
          max-width: 600px;
          box-shadow: 0 4px 30px var(--shadow-glow);
        }
        .waiting-title {
          font-size: 2rem;
          font-weight: 700;
          color: var(--primary);
          margin-bottom: 20px;
        }
        .waiting-count {
          font-size: 3rem;
          font-weight: 800;
          background: linear-gradient(135deg, var(--primary), var(--accent));
          -webkit-background-clip: text;
          -webkit-text-fill-color: transparent;
          background-clip: text;
          margin: 20px 0;
        }
        .waiting-players {
          margin: 20px 0;
          padding: 20px;
          background: var(--panel-light);
          border-radius: 12px;
          border: 1px solid var(--border);
        }
        .waiting-player {
          padding: 8px 12px;
          margin: 6px 0;
          background: var(--card-hover);
          border-radius: 8px;
          color: var(--text);
          font-weight: 600;
        }
        
        /* Animations */
        @keyframes glow {
          0%, 100% { box-shadow: 0 4px 20px var(--shadow-glow); }
          50% { box-shadow: 0 6px 40px var(--shadow-glow); }
        }
        .glow-animation {
          animation: glow 2s ease-in-out infinite;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )

def fetch_backend_config():
    """Fetch backend-configured timers so the timer matches the server."""
    try:
        resp = requests.get(f"{BACKEND_URL}/config", timeout=5)
        if resp.status_code == 200:
            return resp.json()
    except Exception:
        pass
    return None

COLOR_PALETTE = [
    "#6366f1", "#22d3ee", "#10b981", "#f59e0b", "#ef4444", "#8b5cf6",
    "#14b8a6", "#84cc16", "#f97316", "#06b6d4", "#0ea5e9", "#a855f7",
    "#e11d48", "#16a34a", "#d97706", "#3b82f6", "#db2777", "#059669",
    "#7c3aed", "#f43f5e"
]

def _ensure_player_color_map(players):
    """Assign distinct colors to all players, persisted in session state."""
    ids = [p.get('id') for p in players if p and 'id' in p]
    current_ids = set(st.session_state.player_colors.keys())
    incoming_ids = set(ids)
    if current_ids == incoming_ids and current_ids:
        return
    color_map = {}
    palette = COLOR_PALETTE.copy()
    # Extend palette if needed
    if len(ids) > len(palette):
        extra_needed = len(ids) - len(palette)
        for i in range(extra_needed):
            hue = int(360 * (i + 1) / (extra_needed + 1))
            color_map[f"__extra_{i}"] = f"hsl({hue}, 75%, 55%)"
        palette += [color_map[k] for k in color_map]
    for i, pid in enumerate(ids):
        color = palette[i % len(palette)]
        color_map[pid] = color
    st.session_state.player_colors = color_map

def _color_for_player(name: str) -> str:
    return st.session_state.player_colors.get(name) or COLOR_PALETTE[hash(name) % len(COLOR_PALETTE)]

def _avatar_letter(name: str) -> str:
    for ch in name:
        if ch.isalnum():
            return ch.upper()
    return "?"

def render_chat_bubble(sender: str, message: str, is_self: bool, timestamp: float | None) -> str:
    """Return an HTML snippet for a single chat message."""
    alignment_class = "chat-right" if is_self else "chat-left"
    avatar_bg = _color_for_player(sender)
    avatar_txt = _avatar_letter(sender)
    time_str = "" if not timestamp else datetime.fromtimestamp(timestamp).strftime("%H:%M")
    # Layout differs depending on side
    if is_self:
        # Right side: bubble then avatar
        return (
            f"<div class='chat-item {alignment_class}'>"
            f"  <div class='chat-bubble'><div><strong style='color:{avatar_bg}'>{sender}</strong></div>{message}<div class='chat-meta'>{time_str}</div></div>"
            f"  <div class='chat-avatar' style='background:{avatar_bg}'>{avatar_txt}</div>"
            f"</div>"
        )
    else:
        # Left side: avatar then bubble
        return (
            f"<div class='chat-item {alignment_class}'>"
            f"  <div class='chat-avatar' style='background:{avatar_bg}'>{avatar_txt}</div>"
            f"  <div class='chat-bubble'><div><strong style='color:{avatar_bg}'>{sender}</strong></div>{message}<div class='chat-meta'>{time_str}</div></div>"
            f"</div>"
        )

# Configuration
BACKEND_URL = os.getenv('BACKEND_URL', 'http://localhost:8000')
POLL_INTERVAL = 0.3  # seconds (increased from 1.0 for better responsiveness)
DEFAULT_ROOM = 'streamlit-room'

# Initialize session state
if 'room_code' not in st.session_state:
    st.session_state.room_code = DEFAULT_ROOM
if 'player_id' not in st.session_state:
    st.session_state.player_id = 'You'
if 'joined' not in st.session_state:
    st.session_state.joined = False
if 'last_chat_count' not in st.session_state:
    st.session_state.last_chat_count = 0
if 'game_state' not in st.session_state:
    st.session_state.game_state = None
if 'last_poll_time' not in st.session_state:
    st.session_state.last_poll_time = 0
if 'message_input' not in st.session_state:
    st.session_state.message_input = ''
if 'last_phase' not in st.session_state:
    st.session_state.last_phase = None
if 'phase_start_time' not in st.session_state:
    st.session_state.phase_start_time = time.time()
if 'pending_message' not in st.session_state:
    st.session_state.pending_message = None
if 'last_sent_message' not in st.session_state:
    st.session_state.last_sent_message = None
if 'pending_message_time' not in st.session_state:
    st.session_state.pending_message_time = 0
if 'local_chat_cache' not in st.session_state:
    st.session_state.local_chat_cache = []
if 'last_backend_chat_length' not in st.session_state:
    st.session_state.last_backend_chat_length = 0
if 'last_rendered_chat_length' not in st.session_state:
    st.session_state.last_rendered_chat_length = -1
if 'config' not in st.session_state:
    st.session_state.config = None
if 'player_colors' not in st.session_state:
    st.session_state.player_colors = {}
if 'has_voted' not in st.session_state:
    st.session_state.has_voted = False
if 'voted_for' not in st.session_state:
    st.session_state.voted_for = None
if 'pending_vote_choice' not in st.session_state:
    st.session_state.pending_vote_choice = None

# Matching room system session state
if 'current_page' not in st.session_state:
    st.session_state.current_page = 'lobby'  # 'lobby' or 'game'
if 'selected_room_code' not in st.session_state:
    st.session_state.selected_room_code = None
if 'is_room_creator' not in st.session_state:
    st.session_state.is_room_creator = False
if 'room_list' not in st.session_state:
    st.session_state.room_list = []
if 'current_lobby_page' not in st.session_state:
    st.session_state.current_lobby_page = 0
if 'show_create_form' not in st.session_state:
    st.session_state.show_create_form = False
if 'waiting_for_players' not in st.session_state:
    st.session_state.waiting_for_players = False
if 'last_room_poll_time' not in st.session_state:
    st.session_state.last_room_poll_time = 0


def merge_chat_messages(backend_messages, local_cache):
    """
    Intelligently merge backend messages with local cache.
    Never delete messages, only add new ones.
    Handles race conditions and ensures no messages are lost.
    
    Args:
        backend_messages: List of messages from backend
        local_cache: Local cached messages
    
    Returns:
        Merged list of messages with deduplication
    """
    # Create a set of message signatures for deduplication
    # Use sender:message only (not timestamp) to avoid duplicates with different timestamps
    def message_signature(msg):
        return f"{msg.get('sender')}:{msg.get('message')}"
    
    seen_signatures = set()
    merged = []
    
    # Process backend messages first (authoritative source)
    for msg in backend_messages:
        sig = message_signature(msg)
        if sig not in seen_signatures:
            merged.append(msg)
            seen_signatures.add(sig)
    
    # Then add any local messages not in backend yet
    for msg in local_cache:
        sig = message_signature(msg)
        if sig not in seen_signatures:
            merged.append(msg)
            seen_signatures.add(sig)
    
    # Sort by timestamp if available, otherwise maintain order
    try:
        merged.sort(key=lambda x: x.get('timestamp', 0))
    except:
        pass  # Keep original order if sorting fails
    
    return merged


def join_room(room_code: str, player_id: str):
    """Join or create a room."""
    try:
        response = requests.post(
            f"{BACKEND_URL}/api/rooms/{room_code}/join",
            json={"player_id": player_id},
            timeout=10  # Backend creates room quickly now (AI runs in background)
        )
        if response.status_code == 200:
            return response.json()
        return None
    except Exception as e:
        st.error(f"Error joining room: {str(e)}")
        return None


def poll_game_state(room_code: str, player_id: str):
    """Poll the current game state from backend."""
    try:
        response = requests.get(
            f"{BACKEND_URL}/api/rooms/{room_code}/state",
            params={"player_id": player_id},
            timeout=5  # Backend now non-blocking, so 5 seconds is sufficient
        )
        if response.status_code == 200:
            return response.json()
        return None
    except Exception as e:
        st.error(f"Error polling game state: {str(e)}")
        return None


def send_message(room_code: str, player_id: str, message: str):
    """Send a chat message."""
    try:
        response = requests.post(
            f"{BACKEND_URL}/api/rooms/{room_code}/message",
            json={"player_id": player_id, "message": message},
            timeout=10  # AI responses run in background, endpoint returns quickly
        )
        return response.status_code == 200
    except Exception as e:
        st.error(f"Error sending message: {str(e)}")
        return False


def cast_vote(room_code: str, player_id: str, voted_for: str):
    """Cast a vote for elimination."""
    try:
        response = requests.post(
            f"{BACKEND_URL}/api/rooms/{room_code}/vote",
            json={"player_id": player_id, "voted_for": voted_for},
            timeout=10  # AI voting runs in background, endpoint returns quickly
        )
        if response.status_code == 200:
            result = response.json()
            if 'error' in result:
                st.warning(result['error'])
                return False
            return True
        return False
    except Exception as e:
        st.error(f"Error casting vote: {str(e)}")
        return False


def render_header(game_state):
    """Render the game header with status information."""
    if not game_state or not game_state.get('exists'):
        st.title("🎮 Human Hunter - Streamlit Edition")
        return
    
    phase = game_state.get('phase', 'Unknown')
    round_num = game_state.get('round', 1)
    topic = game_state.get('topic', 'No topic')
    
    # Calculate elapsed time since phase started
    elapsed = int(time.time() - st.session_state.phase_start_time)
    phase_lower = str(phase).lower()
    # Ensure we have backend-configured durations
    if not st.session_state.config:
        st.session_state.config = fetch_backend_config()
    cfg = st.session_state.config or {}
    discussion_time = cfg.get('discussion_time', 180)
    voting_time = cfg.get('voting_time', 60)
    # Determine max time based on phase (case-insensitive)
    max_time = discussion_time if phase_lower == 'discussion' else voting_time if phase_lower == 'voting' else 0
    remaining = max(0, max_time - elapsed)
    
    st.title(f"🎮 Human Hunter - Round {round_num}")
    
    # Phase indicator with color
    phase_color = {
        'discussion': '🟢',
        'voting': '🔴',
        'elimination': '⚫',
        'gameover': '🏁',
        'game_over': '🏁'
    }.get(phase_lower, '⚪')
    
    col1, col2, col3 = st.columns(3)
    with col1:
        try:
            st.metric("Phase", f"{phase_color} {phase.title()}")
        except Exception:
            st.metric("Phase", f"{phase_color} {str(phase)}")
    with col2:
        if remaining > 0:
            st.metric("Time Remaining", f"{remaining}s")
        else:
            st.metric("Time", "Processing...")
    with col3:
        st.metric("Room", st.session_state.room_code)
    
    if topic:
        st.markdown(f"""
        <div class="topic-card">💭 <strong>Topic:</strong> {topic}</div>
        """, unsafe_allow_html=True)


def render_player_list(game_state):
    """Render the player list in the sidebar."""
    if not game_state or not game_state.get('exists'):
        st.sidebar.info("Join a room to see players")
        return
    
    st.sidebar.header("👥 Players")
    
    players = game_state.get('players', [])
    _ensure_player_color_map(players)
    phase = game_state.get('phase', '')
    current_player = st.session_state.player_id
    
    # Check if current player has voted (backend) or locally for instant UI update
    current_player_voted_backend = any(
        p['id'] == current_player and p['voted']
        for p in players
    )
    has_voted_local = st.session_state.has_voted or current_player_voted_backend
    # Show who you voted for (from local state or backend votes)
    voted_for_backend = None
    try:
        voted_for_backend = (game_state.get('votes') or {}).get(current_player)
    except Exception:
        voted_for_backend = None
    if has_voted_local:
        voted_name = st.session_state.voted_for or voted_for_backend
        if voted_name:
            st.sidebar.info(f"You voted: {voted_name}")
    
    for player in players:
        player_id = player['id']
        eliminated = player.get('eliminated', False)
        voted = player.get('voted', False)
        is_you = player_id == current_player
        avatar_bg = _color_for_player(player_id)
        avatar_txt = _avatar_letter(player_id)
        name_html = f"<span class='player-name' style='color:{avatar_bg}'>{player_id}{' (You)' if is_you else ''}</span>"
        badge = "<span class='player-badge'>Active</span>"
        if eliminated:
            badge = "<span class='player-badge badge-danger'>Eliminated</span>"
        elif voted and str(phase).lower() == 'voting':
            badge = "<span class='player-badge badge-ok'>Voted</span>"
        card_html = (
            f"<div class='player-card'>"
            f"  <div class='chat-avatar' style='background:{avatar_bg}'>{avatar_txt}</div>"
            f"  <div style='display:flex; flex-direction:column; gap:2px'>"
            f"    {name_html}"
            f"    {badge}"
            f"  </div>"
            f"</div>"
        )
        st.sidebar.markdown(card_html, unsafe_allow_html=True)
        # Voting action
        if (str(phase).lower() == 'voting' and not eliminated and not is_you and not has_voted_local):
            if st.sidebar.button(f"Vote as AI: {player_id}", key=f"vote_{player_id}"):
                # Optimistically set local vote state to hide all other buttons immediately
                st.session_state.has_voted = True
                st.session_state.voted_for = player_id
                # Send vote to backend (allow backend to enforce single-vote rule)
                _ = cast_vote(st.session_state.room_code, current_player, player_id)
                st.rerun()

    # Vote summary (show during voting and after game over)
    phase_l = str(phase).lower()
    if phase_l in ['voting', 'game_over', 'gameover']:
        votes = game_state.get('votes') or {}
        # Include local pending vote if not yet in backend
        display_votes = votes.copy()
        if has_voted_local and current_player not in display_votes:
            voted_name = st.session_state.voted_for
            if voted_name:
                display_votes[current_player] = voted_name
        
        if display_votes:
            st.sidebar.divider()
            st.sidebar.subheader("🗳️ Vote Summary")
            # Per-voter line
            for voter, target in display_votes.items():
                st.sidebar.write(f"{voter} → {target}")
            # Counts
            counts = {}
            for _, target in display_votes.items():
                counts[target] = counts.get(target, 0) + 1
            st.sidebar.markdown("**Totals:**")
            for target, cnt in sorted(counts.items(), key=lambda x: (-x[1], x[0])):
                st.sidebar.write(f"{target}: {cnt}")
            
            # Show voting result after game is over
            if phase_l in ['game_over', 'gameover']:
                selected_suspect = game_state.get('selected_suspect')
                suspect_role = game_state.get('suspect_role')
                winner = game_state.get('winner')
                
                if selected_suspect:
                    st.sidebar.divider()
                    st.sidebar.subheader("📊 Voting Result")
                    
                    # Show who was selected
                    if suspect_role == 'ai':
                        st.sidebar.success(f"✅ Selected: **{selected_suspect}** (AI)")
                        st.sidebar.success("🎉 Humans Win!")
                    else:
                        st.sidebar.error(f"❌ Selected: **{selected_suspect}** (Human)")
                        st.sidebar.error("🤖 AI Wins!")
                    
                    # Show winner
                    if winner:
                        st.sidebar.markdown(f"**Winner:** {winner.upper()}")


def render_chat(game_state):
    """Render the chat window with robust message handling."""
    if not game_state or not game_state.get('exists'):
        st.info("Join a room to start chatting")
        return
    
    st.subheader("💬 Chat")
    
    # Get backend messages
    backend_messages = game_state.get('chat_history', [])
    
    # Merge with local cache to prevent message loss
    chat_history = merge_chat_messages(backend_messages, st.session_state.local_chat_cache)
    
    # Update local cache with merged result
    st.session_state.local_chat_cache = chat_history.copy()
    
    typing_players = game_state.get('typing', [])
    
    # Check if our pending message has appeared in the chat
    if st.session_state.pending_message:
        # Check for timeout (5 seconds max for pending state)
        if time.time() - st.session_state.pending_message_time > 5.0:
            # Timeout - assume message failed or was processed
            st.session_state.pending_message = None
        else:
            # Check if message appeared in merged history
            message_found = any(
                msg.get('sender') == st.session_state.player_id and 
                msg.get('message') == st.session_state.pending_message
                for msg in chat_history
            )
            if message_found:
                # Message confirmed, clear pending state
                st.session_state.pending_message = None
    
    # Build chat HTML with bubbles
    bubbles = []
    if not chat_history and not st.session_state.pending_message:
        bubbles.append("<div class='typing'>No messages yet. Start the conversation!</div>")
    else:
        for m in chat_history:
            sender = m.get('sender', 'Unknown')
            message = m.get('message', '')
            ts = m.get('timestamp')
            is_self = sender == st.session_state.player_id
            bubbles.append(render_chat_bubble(sender, message, is_self, ts))
        # Pending optimistic message
        if st.session_state.pending_message:
            pending_exists = any(
                msg.get('sender') == st.session_state.player_id and 
                msg.get('message') == st.session_state.pending_message
                for msg in chat_history
            )
            if not pending_exists:
                bubbles.append(render_chat_bubble(
                    st.session_state.player_id,
                    f"{st.session_state.pending_message} <em style='opacity:0.7'>✓</em>",
                    True,
                    time.time(),
                ))
    # Typing indicators
    if typing_players:
        typing_text = ', '.join(typing_players)
        bubbles.append(f"<div class='typing'>{typing_text} {'are' if len(typing_players) > 1 else 'is'} typing...</div>")

    chat_html = "<div class='chat-wrap'>" + "".join(bubbles) + "</div>"
    st.markdown(chat_html, unsafe_allow_html=True)

    # Auto-scroll to bottom when new messages arrive
    chat_len = len(chat_history) + (1 if st.session_state.pending_message else 0)
    if chat_len != st.session_state.last_rendered_chat_length:
        st.session_state.last_rendered_chat_length = chat_len
        components.html(
            """
            <script>
            const el = window.parent.document.querySelector('.chat-wrap');
            if (el) { el.scrollTo({top: el.scrollHeight, behavior: 'smooth'}); }
            </script>
            """,
            height=0,
        )


def render_message_input(game_state):
    """Render the message input field."""
    if not game_state or not game_state.get('exists'):
        return
    
    phase = game_state.get('phase', '')
    # Session end handling for single-topic mode
    phase_lower = str(game_state.get('phase', '')).lower()
    if phase_lower in ['game_over', 'gameover']:
        st.success("🏁 Session complete for this topic.")
        # Download stats
        try:
            r = requests.get(f"{BACKEND_URL}/api/rooms/{st.session_state.room_code}/stats", timeout=5)
            if r.status_code == 200:
                stats = r.json()
                st.download_button(
                    'Download Session Stats',
                    data=json.dumps(stats, indent=2),
                    file_name=f"{st.session_state.room_code}-stats.json"
                )
        except Exception:
            pass
        if st.button("Start New Session"):
            st.session_state.joined = False
            st.session_state.game_state = None
            st.session_state.local_chat_cache = []
            st.session_state.pending_message = None
            st.rerun()
        return
    
    # Only allow input during discussion phase
    if phase.lower() != 'discussion':
        st.chat_input(
            f"Chat disabled during {phase} phase",
            disabled=True,
            key="disabled_chat_input"
        )
        return

    # Sticky chat input at bottom
    message = st.chat_input("Type your message and press Enter…")
    if message is None:
        return
    if not message.strip():
        st.warning("Please enter a message")
        return

    # Optimistic local add
    local_msg = {
        'sender': st.session_state.player_id,
        'message': message,
        'timestamp': time.time()
    }
    st.session_state.local_chat_cache.append(local_msg)
    st.session_state.pending_message = message
    st.session_state.pending_message_time = time.time()
    st.session_state.last_sent_message = message

    success = send_message(st.session_state.room_code, st.session_state.player_id, message)
    if success:
        game_state = poll_game_state(st.session_state.room_code, st.session_state.player_id)
        if game_state:
            st.session_state.game_state = game_state
            st.session_state.last_poll_time = time.time()
        st.rerun()
    else:
        st.session_state.local_chat_cache = [
            m for m in st.session_state.local_chat_cache 
            if not (m['sender'] == st.session_state.player_id and m['message'] == message)
        ]
        st.session_state.pending_message = None
        st.session_state.pending_message_time = 0
        st.error("Failed to send message")


def check_phase_change(game_state):
    """Check if phase has changed and update timer."""
    if not game_state:
        return
    
    current_phase = game_state.get('phase', '')
    
    if current_phase != st.session_state.last_phase:
        st.session_state.last_phase = current_phase
        st.session_state.phase_start_time = time.time()
        # Reset local voting flags on phase change
        if current_phase.lower() == 'voting':
            st.session_state.has_voted = False
            st.session_state.voted_for = None
        
        # Show notification for phase changes
        if current_phase.lower() == 'voting':
            st.toast("⏰ Voting phase started!", icon="🔴")
        elif current_phase.lower() == 'discussion':
            st.toast("💬 Discussion phase started!", icon="🟢")


# ============================================================================
# Matching Room System Functions
# ============================================================================

def fetch_room_list(page: int = 0):
    """Fetch list of available rooms from backend."""
    try:
        response = requests.get(
            f"{BACKEND_URL}/api/rooms/list",
            params={"page": page, "per_page": 10},
            timeout=5
        )
        if response.status_code == 200:
            return response.json()
        return None
    except Exception as e:
        st.error(f"Error fetching room list: {str(e)}")
        return None


def create_room_api(max_humans: int, total_players: int):
    """Create a new room via API."""
    try:
        response = requests.post(
            f"{BACKEND_URL}/api/rooms/create",
            json={
                "max_humans": max_humans,
                "total_players": total_players
            },
            timeout=10
        )
        if response.status_code == 200:
            return response.json()
        return None
    except Exception as e:
        st.error(f"Error creating room: {str(e)}")
        return None


def get_room_info(room_code: str):
    """Get room information from backend."""
    try:
        response = requests.get(
            f"{BACKEND_URL}/api/rooms/{room_code}/info",
            timeout=5
        )
        if response.status_code == 200:
            return response.json()
        return None
    except Exception as e:
        st.error(f"Error fetching room info: {str(e)}")
        return None


def leave_room_api(room_code: str, player_id: str):
    """Leave a room via API."""
    try:
        response = requests.post(
            f"{BACKEND_URL}/api/rooms/{room_code}/leave",
            json={"player_id": player_id},
            timeout=5
        )
        if response.status_code == 200:
            return response.json()
        return None
    except Exception as e:
        print(f"Error leaving room: {str(e)}")
        return None


def render_room_card(room):
    """Render a single room card."""
    current_humans = room['current_humans']
    max_humans = room['max_humans']
    total_players = room['total_players']
    room_code = room['room_code']
    room_name = room['room_name']
    
    # Determine status badge
    if current_humans >= max_humans - 1 and current_humans < max_humans:
        status_class = "status-almost"
        status_text = "🟡 Almost Full"
    else:
        status_class = "status-waiting"
        status_text = "🟢 Waiting"
    
    card_html = f"""
    <div class="room-card">
        <div class="room-card-title">🎯 {room_name}</div>
        <div class="room-status-badge {status_class}">{status_text}</div>
        <div class="room-card-info">
            <span class="room-card-label">👥 Players:</span>
            <span class="room-card-value">{current_humans}/{max_humans} humans</span>
        </div>
        <div class="room-card-info">
            <span class="room-card-label">🤖 Total Slots:</span>
            <span class="room-card-value">{total_players}</span>
        </div>
        <div class="room-card-info">
            <span class="room-card-label">🔑 Code:</span>
            <span class="room-card-value">{room_code}</span>
        </div>
    </div>
    """
    st.markdown(card_html, unsafe_allow_html=True)
    
    # Join button below the card
    if st.button(f"Join Room", key=f"join_{room_code}", use_container_width=True):
        return room_code
    return None


def render_lobby_page():
    """Render the main lobby page with room browser."""
    # Header
    st.markdown("""
    <div class="lobby-header">
        <div class="lobby-title">🎮 Human Hunter</div>
        <div class="lobby-subtitle">Find Your Match</div>
    </div>
    """, unsafe_allow_html=True)
    
    # Create room button
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        if st.button("➕ Create New Room", use_container_width=True, type="primary"):
            st.session_state.show_create_form = True
            st.rerun()
    
    # Show create room form if requested
    if st.session_state.show_create_form:
        render_create_room_form()
        return
    
    st.divider()
    
    # Fetch and display rooms
    room_data = fetch_room_list(st.session_state.current_lobby_page)
    
    if room_data and room_data.get('rooms'):
        rooms = room_data['rooms']
        total_pages = room_data.get('total_pages', 1)
        
        st.subheader(f"🌐 Available Rooms ({room_data.get('total', 0)} total)")
        
        # Display rooms in 2 columns
        cols = st.columns(2)
        for idx, room in enumerate(rooms):
            with cols[idx % 2]:
                selected_room = render_room_card(room)
                if selected_room:
                    # Join room logic
                    st.session_state.selected_room_code = selected_room
                    st.session_state.current_page = 'join'
                    st.rerun()
        
        # Pagination
        if total_pages > 1:
            st.divider()
            col1, col2, col3, col4, col5 = st.columns([1, 1, 1, 1, 1])
            with col2:
                if st.button("⬅️ Previous", disabled=st.session_state.current_lobby_page == 0):
                    st.session_state.current_lobby_page -= 1
                    st.rerun()
            with col3:
                st.write(f"Page {st.session_state.current_lobby_page + 1} of {total_pages}")
            with col4:
                if st.button("Next ➡️", disabled=st.session_state.current_lobby_page >= total_pages - 1):
                    st.session_state.current_lobby_page += 1
                    st.rerun()
    else:
        st.info("🔍 No rooms available. Create one to get started!")
    
    # Refresh button
    st.divider()
    if st.button("🔄 Refresh Room List", use_container_width=True):
        st.rerun()


def render_create_room_form():
    """Render the create room form."""
    # Initialize creating flag if not exists
    if 'is_creating' not in st.session_state:
        st.session_state.is_creating = False
    
    st.markdown("### 🎮 Create New Room")
    
    st.info("ℹ️ Room name and player names are automatically assigned")
    
    # Show creating status
    if st.session_state.is_creating:
        st.info("⏳ Creating room and joining... Please wait")
        return
    
    # Sliders outside form for real-time updates
    col1, col2 = st.columns(2)
    with col1:
        max_humans = st.slider("Number of Human Players", min_value=1, max_value=4, value=1, 
                               key="create_max_humans", help="How many human players can join (1-4)")
    with col2:
        total_players = st.slider("Total Players", min_value=max_humans, max_value=12, value=5, 
                                  key="create_total_players", help="Total players including AI")
    
    # This updates in real-time as sliders change
    ai_count = total_players - max_humans
    st.info(f"🤖 AI Players: {ai_count}")
    
    # Buttons in columns for layout
    col_submit, col_cancel = st.columns(2)
    with col_submit:
        submitted = st.button("Create & Join", use_container_width=True, type="primary", 
                             key="create_submit", disabled=st.session_state.is_creating)
    with col_cancel:
        cancelled = st.button("Cancel", use_container_width=True, key="create_cancel",
                             disabled=st.session_state.is_creating)
    
    if cancelled:
        st.session_state.show_create_form = False
        st.session_state.is_creating = False
        st.rerun()
    
    if submitted:
        # Set flag to prevent double-clicking
        st.session_state.is_creating = True
        
        # Create room (room name and player name auto-generated)
        result = create_room_api(max_humans, total_players)
        
        if result and result.get('success'):
            room_code = result['room_code']
            st.success(f"✅ Room created: {result['room_name']}")
            
            # Store room info
            st.session_state.room_code = room_code
            st.session_state.selected_room_code = room_code
            st.session_state.is_room_creator = True
            st.session_state.show_create_form = False
            
            # Join the room (backend will assign player number)
            time.sleep(0.5)
            join_result = join_room(room_code, "")
            
            if join_result and join_result.get('success'):
                # Get the assigned player ID from the backend
                assigned_player_id = join_result.get('player_id', 'Player ?')
                st.session_state.player_id = assigned_player_id
                st.session_state.joined = True
                
                st.info(f"✅ You are: **{assigned_player_id}**")
                time.sleep(1)  # Show the assigned name briefly
                
                # Check if can start immediately
                if join_result.get('can_start'):
                    st.session_state.current_page = 'game'
                    st.session_state.waiting_for_players = False
                else:
                    st.session_state.current_page = 'waiting'
                    st.session_state.waiting_for_players = True
                
                # Reset creating flag
                st.session_state.is_creating = False
                st.rerun()
            else:
                error_msg = join_result.get('error') if join_result else 'Failed to join room'
                st.error(f"❌ {error_msg}")
                # Reset creating flag on error
                st.session_state.is_creating = False
        else:
            error_msg = result.get('error') if result else 'Failed to create room'
            st.error(f"❌ {error_msg}")
            # Reset creating flag on error
            st.session_state.is_creating = False


def render_waiting_screen():
    """Render waiting screen for players."""
    room_code = st.session_state.room_code
    
    # Poll for room updates
    current_time = time.time()
    if current_time - st.session_state.last_room_poll_time >= 2.0:
        room_info = get_room_info(room_code)
        st.session_state.last_room_poll_time = current_time
        
        # If room no longer exists, return to lobby
        if not room_info or not room_info.get('exists'):
            st.error("⚠️ Room no longer exists (may have been terminated)")
            st.session_state.joined = False
            st.session_state.waiting_for_players = False
            st.session_state.current_page = 'lobby'
            st.session_state.game_state = None
            time.sleep(2)  # Show message briefly
            st.rerun()
            return
        
        if room_info and room_info.get('exists'):
            # Check if game started
            if room_info['room_status'] == 'in_progress':
                st.session_state.waiting_for_players = False
                st.session_state.current_page = 'game'
                st.rerun()
            
            current_humans = room_info['current_humans']
            max_humans = room_info['max_humans']
            
            # Render waiting UI
            st.markdown(f"""
            <div class="waiting-container glow-animation">
                <div class="waiting-title">⏳ Waiting for Players</div>
                <div class="waiting-count">{len(current_humans)}/{max_humans}</div>
                <div class="waiting-players">
                    <h4 style="color: var(--primary); margin-bottom: 10px; font-weight: 600;">Joined Players:</h4>
                    {"".join(f'<div class="waiting-player">👤 {player}</div>' for player in current_humans)}
                </div>
                <p style="color: var(--text-secondary); margin-top: 20px;">
                    Game will start automatically when all players join...
                </p>
            </div>
            """, unsafe_allow_html=True)
            
            # Leave room button
            st.divider()
            if st.button("🚪 Leave Room", use_container_width=True):
                # Notify backend about leaving
                player_id = st.session_state.player_id
                leave_result = leave_room_api(room_code, player_id)
                
                # Reset local state
                st.session_state.joined = False
                st.session_state.waiting_for_players = False
                st.session_state.current_page = 'lobby'
                st.session_state.game_state = None
                st.session_state.player_id = 'You'
                
                # Show result message
                if leave_result:
                    action = leave_result.get('action', '')
                    if action == 'terminated':
                        st.warning("Room was terminated")
                    elif action == 'removed':
                        st.info("Left the room")
                
                st.rerun()
            
    # Auto-refresh
    time.sleep(2)
    st.rerun()


def render_join_page():
    """Render the join page."""
    room_code = st.session_state.selected_room_code
    
    # Initialize joining flag if not exists
    if 'is_joining' not in st.session_state:
        st.session_state.is_joining = False
    
    st.markdown("""
    <div class="lobby-header">
        <div class="lobby-title">🎮 Join Room</div>
        <div class="lobby-subtitle">Your player number will be auto-assigned</div>
    </div>
    """, unsafe_allow_html=True)
    
    # Get room info
    room_info = get_room_info(room_code)
    
    if not room_info or not room_info.get('exists'):
        st.error("❌ Room not found or no longer available")
        if st.button("← Back to Lobby"):
            st.session_state.current_page = 'lobby'
            st.session_state.selected_room_code = None
            st.session_state.is_joining = False
            st.rerun()
        return
    
    # Display room info
    st.markdown(f"""
    <div class="room-card" style="max-width: 500px; margin: 20px auto;">
        <div class="room-card-title">🎯 {room_info['room_name']}</div>
        <div class="room-card-info">
            <span class="room-card-label">👥 Players:</span>
            <span class="room-card-value">{len(room_info['current_humans'])}/{room_info['max_humans']} humans</span>
        </div>
        <div class="room-card-info">
            <span class="room-card-label">🤖 Total Slots:</span>
            <span class="room-card-value">{room_info['total_players']}</span>
        </div>
    </div>
    """, unsafe_allow_html=True)
    
    st.divider()
    
    # Show joining status
    if st.session_state.is_joining:
        st.info("⏳ Joining room... Please wait")
        return
    
    st.info("🎲 Click 'Join Game' and you'll be assigned a random player number")
    
    col1, col2 = st.columns(2)
    with col1:
        # Disable button if already joining
        if st.button("Join Game", type="primary", use_container_width=True, disabled=st.session_state.is_joining):
            # Set flag to prevent double-clicking
            st.session_state.is_joining = True
            
            # Join the room (backend assigns player number)
            join_result = join_room(room_code, "")
            
            if join_result and join_result.get('success'):
                # Get the assigned player ID from the backend
                assigned_player_id = join_result.get('player_id', 'Player ?')
                st.session_state.player_id = assigned_player_id
                st.session_state.room_code = room_code
                st.session_state.joined = True
                
                st.success(f"✅ You are: **{assigned_player_id}**")
                time.sleep(1)  # Show the assigned name briefly
                
                # Check if can start immediately
                if join_result.get('can_start'):
                    st.session_state.current_page = 'game'
                    st.session_state.waiting_for_players = False
                else:
                    st.session_state.current_page = 'waiting'
                    st.session_state.waiting_for_players = True
                
                # Reset joining flag
                st.session_state.is_joining = False
                st.rerun()
            else:
                error_msg = join_result.get('error') if join_result else 'Failed to join room'
                st.error(f"❌ {error_msg}")
                # Reset joining flag on error
                st.session_state.is_joining = False
    
    with col2:
        if st.button("Cancel", use_container_width=True, disabled=st.session_state.is_joining):
            st.session_state.current_page = 'lobby'
            st.session_state.selected_room_code = None
            st.session_state.is_joining = False
            st.rerun()


def main():
    """Main Streamlit application."""
    st.set_page_config(
        page_title="Human Hunter - Streamlit",
        page_icon="🎮",
        layout="wide",
        initial_sidebar_state="expanded"
    )
    inject_global_styles()
    
    # Check current page and route accordingly
    current_page = st.session_state.current_page
    
    # =================================================================================
    # LOBBY PAGE - Browse and create rooms
    # =================================================================================
    if current_page == 'lobby':
        # Show backend status in sidebar
        with st.sidebar:
            st.title("🎮 Human Hunter")
            st.divider()
        try:
            response = requests.get(f"{BACKEND_URL}/health", timeout=5)
            if response.status_code == 200:
                    st.success("✅ Server Online")
            else:
                    st.error("❌ Server Error")
        except:
                st.error("❌ Server Offline")
                st.caption("Start backend:\n`uvicorn main:app`")
        
        # Render lobby page
        render_lobby_page()
        return
    
    # =================================================================================
    # JOIN PAGE - Enter name to join selected room
    # =================================================================================
    elif current_page == 'join':
        render_join_page()
        return
    
    # =================================================================================
    # WAITING PAGE - Wait for other players to join
    # =================================================================================
    elif current_page == 'waiting':
        render_waiting_screen()
        return
    
    # =================================================================================
    # GAME PAGE - Main game UI
    # =================================================================================
    elif current_page == 'game':
        # Sidebar - Player list and controls
        with st.sidebar:
            st.title("🎮 Game Setup")
            
            if st.session_state.joined:
                st.success(f"✅ Connected as **{st.session_state.player_id}**")
                if st.button("Leave Room", use_container_width=True):
                    # Notify backend about leaving
                    room_code = st.session_state.room_code
                    player_id = st.session_state.player_id
                    leave_result = leave_room_api(room_code, player_id)
                    
                    # Reset local state
                    st.session_state.joined = False
                    st.session_state.game_state = None
                    st.session_state.local_chat_cache = []
                    st.session_state.pending_message = None
                    st.session_state.current_page = 'lobby'
                    st.session_state.waiting_for_players = False
                    st.session_state.player_id = 'You'
                    
                    # Show result message
                    if leave_result:
                        action = leave_result.get('action', '')
                        if action == 'terminated':
                            st.warning("Room was terminated")
                        elif action == 'removed':
                            st.info("Left the game")
                    
                    st.rerun()
                
                st.divider()
    
    # Poll game state
    current_time = time.time()
    poll_interval = 0.3 if st.session_state.pending_message else POLL_INTERVAL
    
    if current_time - st.session_state.last_poll_time >= poll_interval:
        game_state = poll_game_state(st.session_state.room_code, st.session_state.player_id)
        
        # If room no longer exists, return to lobby
        if not game_state or not game_state.get('exists'):
            st.error("⚠️ Room no longer exists (may have been terminated)")
            st.session_state.joined = False
            st.session_state.waiting_for_players = False
            st.session_state.current_page = 'lobby'
            st.session_state.game_state = None
            time.sleep(2)  # Show message briefly
            st.rerun()
            return
        
        if game_state:
            st.session_state.game_state = game_state
            st.session_state.last_poll_time = current_time
            check_phase_change(game_state)
    
    game_state = st.session_state.game_state
    
    # Render game UI
    render_header(game_state)
    render_player_list(game_state)
    
    # Main content area
    st.divider()
    render_chat(game_state)
    st.divider()
    render_message_input(game_state)
    
    # Auto-refresh during active phases
    if game_state and game_state.get('exists'):
        phase = game_state.get('phase', '').lower()
        winner = game_state.get('winner')
        
        if not winner and phase in ['discussion', 'voting']:
            time.sleep(POLL_INTERVAL)
            st.rerun()


if __name__ == "__main__":
    main()

