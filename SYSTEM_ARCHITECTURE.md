# System Architecture - Matching Room System

## High-Level Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                        User's Browser                            │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │            Streamlit Frontend (Port 8501)                 │  │
│  │                                                            │  │
│  │  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐ │  │
│  │  │  Lobby   │  │   Join   │  │ Waiting  │  │   Game   │ │  │
│  │  │   Page   │  │   Page   │  │  Screen  │  │   Page   │ │  │
│  │  └────┬─────┘  └────┬─────┘  └────┬─────┘  └────┬─────┘ │  │
│  │       │             │              │             │        │  │
│  │       └─────────────┴──────────────┴─────────────┘        │  │
│  │                         │                                  │  │
│  │                   Navigation State                         │  │
│  │              (st.session_state.current_page)               │  │
│  └────────────────────────┬───────────────────────────────────┘  │
└───────────────────────────┼───────────────────────────────────────┘
                            │
                    HTTP REST API
                    (Polling-based)
                            │
┌───────────────────────────┼───────────────────────────────────────┐
│                           ▼                                        │
│  ┌──────────────────────────────────────────────────────────┐    │
│  │        FastAPI Backend (Port 8000)                       │    │
│  │                                                            │    │
│  │  ┌───────────────────────────────────────────────────┐  │    │
│  │  │             Matching Room Endpoints                │  │    │
│  │  │                                                     │  │    │
│  │  │  POST /api/rooms/create                           │  │    │
│  │  │  GET  /api/rooms/list                             │  │    │
│  │  │  GET  /api/rooms/{code}/info                      │  │    │
│  │  │  POST /api/rooms/{code}/join  (modified)          │  │    │
│  │  └───────────────────────────────────────────────────┘  │    │
│  │                                                            │    │
│  │  ┌───────────────────────────────────────────────────┐  │    │
│  │  │              Game Endpoints                        │  │    │
│  │  │                                                     │  │    │
│  │  │  GET  /api/rooms/{code}/state                     │  │    │
│  │  │  POST /api/rooms/{code}/message                   │  │    │
│  │  │  POST /api/rooms/{code}/vote                      │  │    │
│  │  │  WS   /ws/{code}/{player_id}                      │  │    │
│  │  └───────────────────────────────────────────────────┘  │    │
│  │                                                            │    │
│  │  ┌───────────────────────────────────────────────────┐  │    │
│  │  │           Room Management (In-Memory)              │  │    │
│  │  │                                                     │  │    │
│  │  │  rooms: Dict[room_code, RoomData]                 │  │    │
│  │  │                                                     │  │    │
│  │  │  RoomData:                                         │  │    │
│  │  │    - state: GameState (LangGraph)                 │  │    │
│  │  │    - room_name: str                               │  │    │
│  │  │    - max_humans: int                              │  │    │
│  │  │    - total_players: int                           │  │    │
│  │  │    - room_status: str                             │  │    │
│  │  │    - current_humans: List[str]                    │  │    │
│  │  │    - created_at: float                            │  │    │
│  │  └───────────────────────────────────────────────────┘  │    │
│  │                                                            │    │
│  │  ┌───────────────────────────────────────────────────┐  │    │
│  │  │          LangGraph Game Engine                     │  │    │
│  │  │                                                     │  │    │
│  │  │  - AI Agent Orchestration                         │  │    │
│  │  │  - Game State Management                          │  │    │
│  │  │  - Phase Transitions                              │  │    │
│  │  └───────────────────────────────────────────────────┘  │    │
│  └──────────────────────────┬─────────────────────────────────┘    │
└─────────────────────────────┼─────────────────────────────────────┘
                              │
                         OpenAI API
                              │
                              ▼
                      GPT-4 Mini (AI Players)
```

---

## Data Flow Diagrams

### 1. Create Room Flow

```
User                 Frontend              Backend              LangGraph
 │                      │                     │                     │
 │  Click "Create"      │                     │                     │
 ├─────────────────────>│                     │                     │
 │                      │                     │                     │
 │  Fill Form           │                     │                     │
 │  - Name: "Test"      │                     │                     │
 │  - Humans: 2         │                     │                     │
 │  - Total: 5          │                     │                     │
 │                      │                     │                     │
 │  Submit              │  POST /rooms/create │                     │
 ├─────────────────────>├────────────────────>│                     │
 │                      │                     │                     │
 │                      │                     │  generate_room_code()
 │                      │                     │  → "AB12CD"         │
 │                      │                     │                     │
 │                      │                     │  create_game_for_room()
 │                      │                     ├────────────────────>│
 │                      │                     │                     │
 │                      │                     │  Create AI players  │
 │                      │                     │  (total - humans)   │
 │                      │                     │                     │
 │                      │                     │<────────────────────┤
 │                      │                     │  GameState          │
 │                      │                     │                     │
 │                      │                     │  Store room:        │
 │                      │                     │  {                  │
 │                      │                     │    state: GameState │
 │                      │                     │    room_name: "..."│
 │                      │                     │    max_humans: 2   │
 │                      │                     │    total_players: 5│
 │                      │                     │    room_status:    │
 │                      │                     │      'waiting'     │
 │                      │                     │    current_humans: []
 │                      │                     │  }                  │
 │                      │                     │                     │
 │                      │  Response:          │                     │
 │                      │  {room_code,name}   │                     │
 │                      │<────────────────────┤                     │
 │                      │                     │                     │
 │                      │  POST /rooms/join   │                     │
 │                      │  (auto-join creator)│                     │
 │                      ├────────────────────>│                     │
 │                      │                     │                     │
 │                      │  current_humans.    │                     │
 │                      │  append(creator)    │                     │
 │                      │                     │                     │
 │                      │  {can_start: false} │                     │
 │  Waiting Screen      │<────────────────────┤                     │
 │<─────────────────────┤                     │                     │
 │                      │                     │                     │
```

### 2. Join Room Flow

```
Player 2             Frontend              Backend              Game
 │                      │                     │                     │
 │  View Lobby          │  GET /rooms/list    │                     │
 ├─────────────────────>├────────────────────>│                     │
 │                      │                     │                     │
 │                      │  Filter by status   │                     │
 │                      │  'waiting'          │                     │
 │                      │                     │                     │
 │  Room List           │  [rooms...]         │                     │
 │<─────────────────────┤<────────────────────┤                     │
 │                      │                     │                     │
 │  Click "Join"        │                     │                     │
 ├─────────────────────>│                     │                     │
 │                      │                     │                     │
 │  Enter name          │                     │                     │
 ├─────────────────────>│                     │                     │
 │                      │                     │                     │
 │  Submit              │  POST /rooms/join   │                     │
 ├─────────────────────>├────────────────────>│                     │
 │                      │                     │                     │
 │                      │                     │  Check capacity:    │
 │                      │                     │  len(current_humans)│
 │                      │                     │  < max_humans? ✓    │
 │                      │                     │                     │
 │                      │                     │  current_humans.    │
 │                      │                     │  append("Player2")  │
 │                      │                     │                     │
 │                      │                     │  Check if full:     │
 │                      │                     │  len == max_humans? │
 │                      │                     │  ✓ YES              │
 │                      │                     │                     │
 │                      │                     │  room_status =      │
 │                      │                     │  'in_progress'      │
 │                      │                     │                     │
 │                      │                     │  initialize_game()  │
 │                      │                     ├────────────────────>│
 │                      │                     │                     │
 │                      │                     │  Start discussion   │
 │                      │                     │  phase              │
 │                      │                     │                     │
 │  Game Page           │  {can_start: true}  │                     │
 │<─────────────────────┤<────────────────────┤                     │
 │                      │                     │                     │
```

### 3. Waiting Screen Polling

```
User                 Frontend              Backend
 │                      │                     │
 │  On Waiting Screen   │                     │
 │                      │                     │
 │                      │  Every 2 seconds:   │
 │                      │                     │
 │                      │  GET /rooms/{code}  │
 │                      │       /info         │
 │                      ├────────────────────>│
 │                      │                     │
 │                      │  {                  │
 │                      │    current_humans,  │
 │                      │    max_humans,      │
 │                      │    room_status      │
 │                      │  }                  │
 │                      │<────────────────────┤
 │                      │                     │
 │                      │  Update UI:         │
 │                      │  "2/3 Players"      │
 │                      │                     │
 │  "2/3 Players"       │                     │
 │<─────────────────────┤                     │
 │                      │                     │
 │                      │  ... wait 2s ...    │
 │                      │                     │
 │                      │  GET /rooms/{code}  │
 │                      │       /info         │
 │                      ├────────────────────>│
 │                      │                     │
 │                      │  {                  │
 │                      │    room_status:     │
 │                      │    'in_progress'    │
 │                      │  }                  │
 │                      │<────────────────────┤
 │                      │                     │
 │                      │  Navigate to game   │
 │                      │                     │
 │  Game Started!       │                     │
 │<─────────────────────┤                     │
 │                      │                     │
```

---

## Component Interactions

### Frontend Components

```
┌─────────────────────────────────────────────────────────┐
│                    Streamlit App                         │
│                                                           │
│  ┌────────────────────────────────────────────────────┐ │
│  │         Session State (st.session_state)           │ │
│  │                                                     │ │
│  │  - current_page: 'lobby' | 'join' | 'waiting' |   │ │
│  │                  'game'                            │ │
│  │  - room_code: str                                  │ │
│  │  - player_id: str                                  │ │
│  │  - joined: bool                                    │ │
│  │  - selected_room_code: str                         │ │
│  │  - waiting_for_players: bool                       │ │
│  │  - show_create_form: bool                          │ │
│  │  - current_lobby_page: int                         │ │
│  │  ... (20+ state variables)                         │ │
│  └────────────────────────────────────────────────────┘ │
│                                                           │
│  ┌────────────────────────────────────────────────────┐ │
│  │                Page Router (main)                  │ │
│  │                                                     │ │
│  │  if current_page == 'lobby':                       │ │
│  │      render_lobby_page()                           │ │
│  │  elif current_page == 'join':                      │ │
│  │      render_join_page()                            │ │
│  │  elif current_page == 'waiting':                   │ │
│  │      render_waiting_screen()                       │ │
│  │  elif current_page == 'game':                      │ │
│  │      render_game_ui()                              │ │
│  └────────────────────────────────────────────────────┘ │
│                                                           │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐     │
│  │   Lobby     │  │    Join     │  │  Waiting    │     │
│  │   render_   │  │   render_   │  │   render_   │     │
│  │   lobby_    │  │   join_     │  │   waiting_  │     │
│  │   page()    │  │   page()    │  │   screen()  │     │
│  │             │  │             │  │             │     │
│  │ - Room grid │  │ - Name form │  │ - Counter   │     │
│  │ - Create btn│  │ - Room info │  │ - Player    │     │
│  │ - Pagination│  │ - Join btn  │  │   list      │     │
│  └─────────────┘  └─────────────┘  └─────────────┘     │
│                                                           │
│  ┌────────────────────────────────────────────────────┐ │
│  │              API Helper Functions                  │ │
│  │                                                     │ │
│  │  - fetch_room_list(page)                           │ │
│  │  - create_room_api(...)                            │ │
│  │  - get_room_info(code)                             │ │
│  │  - join_room(code, player)                         │ │
│  └────────────────────────────────────────────────────┘ │
└───────────────────────────────────────────────────────────┘
```

### Backend Components

```
┌─────────────────────────────────────────────────────────┐
│                   FastAPI Backend                        │
│                                                           │
│  ┌────────────────────────────────────────────────────┐ │
│  │              Routing Layer                         │ │
│  │                                                     │ │
│  │  @app.post("/api/rooms/create")                    │ │
│  │  @app.get("/api/rooms/list")                       │ │
│  │  @app.get("/api/rooms/{code}/info")                │ │
│  │  @app.post("/api/rooms/{code}/join")               │ │
│  │  @app.get("/api/rooms/{code}/state")               │ │
│  │  @app.post("/api/rooms/{code}/message")            │ │
│  │  @app.post("/api/rooms/{code}/vote")               │ │
│  │  @app.websocket("/ws/{code}/{player}")             │ │
│  └────────────────────────────────────────────────────┘ │
│                                                           │
│  ┌────────────────────────────────────────────────────┐ │
│  │           Business Logic Layer                     │ │
│  │                                                     │ │
│  │  - generate_room_code()                            │ │
│  │  - validate_room_params()                          │ │
│  │  - check_capacity()                                │ │
│  │  - auto_start_game()                               │ │
│  └────────────────────────────────────────────────────┘ │
│                                                           │
│  ┌────────────────────────────────────────────────────┐ │
│  │            Data Layer (In-Memory)                  │ │
│  │                                                     │ │
│  │  rooms: Dict[str, Dict] = {                        │ │
│  │    'AB12CD': {                                     │ │
│  │      'state': GameState,                           │ │
│  │      'connections': {},                            │ │
│  │      'room_name': 'Test Room',                     │ │
│  │      'max_humans': 2,                              │ │
│  │      'total_players': 5,                           │ │
│  │      'room_status': 'waiting',                     │ │
│  │      'current_humans': ['Player1'],                │ │
│  │      'created_at': 1234567890,                     │ │
│  │      'creator_id': 'Player1'                       │ │
│  │    }                                                │ │
│  │  }                                                  │ │
│  └────────────────────────────────────────────────────┘ │
│                                                           │
│  ┌────────────────────────────────────────────────────┐ │
│  │          Game Engine (LangGraph)                   │ │
│  │                                                     │ │
│  │  - create_game_for_room(code, num_ai)              │ │
│  │  - initialize_game_node(state)                     │ │
│  │  - process_human_message(state, msg)               │ │
│  │  - process_human_vote(state, vote)                 │ │
│  │  - run_discussion_phase(code)                      │ │
│  │  - run_voting_phase(code)                          │ │
│  │  - trigger_agent_decisions(code)                   │ │
│  └────────────────────────────────────────────────────┘ │
└───────────────────────────────────────────────────────────┘
```

---

## State Transitions

### Room Status Lifecycle

```
                    ┌──────────┐
                    │  CREATE  │
                    │   ROOM   │
                    └────┬─────┘
                         │
                         ▼
                  ┌─────────────┐
                  │   WAITING   │
                  │             │
                  │ - Created   │
                  │ - Accepting │
                  │   players   │
                  └──────┬──────┘
                         │
                         │ len(current_humans)
                         │ == max_humans
                         │
                         ▼
                  ┌─────────────┐
                  │ IN_PROGRESS │
                  │             │
                  │ - Game      │
                  │   started   │
                  │ - No more   │
                  │   joins     │
                  └──────┬──────┘
                         │
                         │ Game ends
                         │
                         ▼
                  ┌─────────────┐
                  │  COMPLETED  │
                  │             │
                  │ - Game over │
                  │ - Stats     │
                  │   saved     │
                  └─────────────┘
```

### Page Navigation Flow

```
    ┌───────┐
    │ LOBBY │◄─────────────────┐
    └───┬───┘                  │
        │                      │
        │ Select room          │
        │                      │
        ▼                      │
    ┌──────┐                  │
    │ JOIN │                  │
    └───┬──┘                  │
        │                      │
        │ Enter name           │
        │                      │
        ▼                      │
  ┌─────────┐                 │
  │ WAITING │                 │
  └────┬────┘                 │
       │                      │
       │ Room full            │
       │                      │
       ▼                      │
   ┌──────┐                  │
   │ GAME │                  │
   └───┬──┘                  │
       │                      │
       │ Leave room           │
       │                      │
       └──────────────────────┘
```

---

## Key Design Decisions

### 1. In-Memory Storage
- **Choice**: Store rooms in Python dict
- **Rationale**: Simple, fast, sufficient for prototype
- **Trade-off**: No persistence across restarts
- **Future**: Could add Redis/PostgreSQL

### 2. Polling vs WebSocket
- **Choice**: Polling for waiting screen (2s interval)
- **Rationale**: Simpler than WebSocket, sufficient for low-frequency updates
- **Trade-off**: Slight delay, more HTTP requests
- **Future**: Could upgrade to WebSocket for instant updates

### 3. Auto-Start vs Ready-Up
- **Choice**: Auto-start when capacity reached
- **Rationale**: Simpler UX, fewer clicks
- **Trade-off**: No player control over start timing
- **Future**: Could add ready-up system

### 4. Page-Based Navigation
- **Choice**: Single-page app with state-based routing
- **Rationale**: Streamlit limitation, but works well
- **Trade-off**: Full reloads on navigation
- **Future**: Could migrate to React for smoother transitions

### 5. Room Code Format
- **Choice**: 6-char alphanumeric (A-Z, 0-9)
- **Rationale**: Easy to share, read, type
- **Trade-off**: 36^6 = 2.1B possible codes (sufficient)
- **Future**: Could add shorter codes with word list

---

## Performance Characteristics

### Backend
- **Room Creation**: O(1) - constant time
- **Room List**: O(n) - linear in number of rooms
- **Room Join**: O(1) - constant time
- **Game Start**: O(m) - linear in AI players

### Frontend
- **Lobby Render**: O(r) - linear in rooms per page (max 10)
- **Waiting Poll**: O(1) - single HTTP request
- **Game Render**: O(p) - linear in players (max 12)

### Network
- **Create Room**: 1 request
- **Join Room**: 2 requests (info + join)
- **Waiting**: 1 request per 2 seconds
- **Game**: Multiple requests (polling + actions)

---

## Security Model

### Current (Development)
- No authentication required
- All rooms public
- No rate limiting
- Trust-based system

### Production Recommendations
- Add user authentication (JWT tokens)
- Implement rate limiting (10 req/min per IP)
- Add input validation (XSS prevention)
- Configure CORS properly
- Add room passwords for privacy
- Implement admin controls
- Log suspicious activity

---

## Scalability Considerations

### Current Limits
- ~100 concurrent rooms (in-memory)
- ~1000 concurrent users (single server)
- No horizontal scaling
- No load balancing

### Scaling Strategy (if needed)
1. **Short-term**: Add Redis for room storage
2. **Medium-term**: Add database (PostgreSQL)
3. **Long-term**: Microservices architecture
   - Room service
   - Game service
   - User service
   - Load balancer

---

## Technology Stack

```
┌─────────────────────────────────────┐
│         Frontend Layer              │
│                                     │
│  - Streamlit 1.x                    │
│  - Python 3.8+                      │
│  - Custom CSS                       │
│  - HTML Components                  │
└──────────────┬──────────────────────┘
               │ HTTP/REST
               │
┌──────────────▼──────────────────────┐
│         Backend Layer               │
│                                     │
│  - FastAPI                          │
│  - Uvicorn (ASGI server)            │
│  - Python 3.8+                      │
│  - Async/await                      │
└──────────────┬──────────────────────┘
               │
     ┌─────────┴─────────┐
     │                   │
     ▼                   ▼
┌──────────┐     ┌──────────────┐
│LangGraph │     │  OpenAI API  │
│          │     │              │
│- Game    │     │ - GPT-4 Mini │
│  State   │     │ - AI Players │
│- AI      │     │              │
│  Agents  │     │              │
└──────────┘     └──────────────┘
```

---

## Deployment Architecture

### Development (Current)
```
localhost:8501 (Streamlit) → localhost:8000 (FastAPI) → OpenAI API
```

### Production (Recommended)
```
                    ┌──────────┐
                    │  Nginx   │ (Reverse Proxy)
                    │  :80/443 │
                    └────┬─────┘
                         │
             ┌───────────┴───────────┐
             │                       │
             ▼                       ▼
      ┌─────────────┐         ┌─────────────┐
      │  Streamlit  │         │   FastAPI   │
      │   :8501     │───────> │    :8000    │
      └─────────────┘         └──────┬──────┘
                                     │
                              ┌──────┴──────┐
                              │             │
                              ▼             ▼
                         ┌────────┐   ┌─────────┐
                         │ Redis  │   │ OpenAI  │
                         │  :6379 │   │   API   │
                         └────────┘   └─────────┘
```

---

This architecture provides a solid foundation for the matching room system while maintaining simplicity and extensibility for future enhancements.

