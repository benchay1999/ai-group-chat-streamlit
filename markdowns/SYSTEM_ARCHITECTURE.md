# System Architecture - Human Hunter

## High-Level Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                        User's Browser                            │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │              React Frontend (Port 5173)                   │  │
│  │              Vite Dev Server / Production Build           │  │
│  │                                                            │  │
│  │  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐ │  │
│  │  │  Lobby   │  │ Waiting  │  │   Game   │  │Dashboard │ │  │
│  │  │   Page   │  │   Page   │  │   Page   │  │   Page   │ │  │
│  │  └──────────┘  └──────────┘  └──────────┘  └──────────┘ │  │
│  │  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐ │  │
│  │  │  Wallet  │  │GemsInfo  │  │  Admin   │  │ Profile  │ │  │
│  │  │   Page   │  │   Page   │  │   Panel  │  │   Page   │ │  │
│  │  └──────────┘  └──────────┘  └──────────┘  └──────────┘ │  │
│  │                         │                                  │  │
│  │                React Router (Client-Side)                  │  │
│  │                WebSocket + HTTP API                        │  │
│  └────────────────────────┬───────────────────────────────────┘  │
└───────────────────────────┼───────────────────────────────────────┘
                            │
                    HTTP REST + WebSocket
                            │
┌───────────────────────────┼───────────────────────────────────────┐
│                           ▼                                        │
│  ┌──────────────────────────────────────────────────────────┐    │
│  │        FastAPI Backend (Port 8000)                       │    │
│  │                                                            │    │
│  │  ┌───────────────────────────────────────────────────┐  │    │
│  │  │              Room Endpoints                        │  │    │
│  │  │                                                     │  │    │
│  │  │  POST /api/rooms/create                           │  │    │
│  │  │  GET  /api/rooms/list                             │  │    │
│  │  │  GET  /api/rooms/{code}/info                      │  │    │
│  │  │  POST /api/rooms/{code}/join                      │  │    │
│  │  │  POST /api/rooms/{code}/leave                     │  │    │
│  │  └───────────────────────────────────────────────────┘  │    │
│  │                                                            │    │
│  │  ┌───────────────────────────────────────────────────┐  │    │
│  │  │           Auth & User Endpoints                    │  │    │
│  │  │                                                     │  │    │
│  │  │  POST /api/auth/register                          │  │    │
│  │  │  POST /api/auth/login                             │  │    │
│  │  │  GET  /api/auth/me                                │  │    │
│  │  │  GET  /api/users/earnings                         │  │    │
│  │  └───────────────────────────────────────────────────┘  │    │
│  │                                                            │    │
│  │  ┌───────────────────────────────────────────────────┐  │    │
│  │  │            Gem Economy Endpoints                   │  │    │
│  │  │                                                     │  │    │
│  │  │  GET  /api/wallet/balance                         │  │    │
│  │  │  POST /api/wallet/cashout                         │  │    │
│  │  │  GET  /api/wallet/cashout-history                 │  │    │
│  │  └───────────────────────────────────────────────────┘  │    │
│  │                                                            │    │
│  │  ┌───────────────────────────────────────────────────┐  │    │
│  │  │              Game Endpoints                        │  │    │
│  │  │                                                     │  │    │
│  │  │  GET  /api/rooms/{code}/state                     │  │    │
│  │  │  POST /api/rooms/{code}/message                   │  │    │
│  │  │  POST /api/rooms/{code}/vote                      │  │    │
│  │  │  WS   /ws/game/{code}                             │  │    │
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
│  │  │    - stake_percentage: int                        │  │    │
│  │  │    - player_stakes: Dict                          │  │    │
│  │  │    - minimum_stake: int                           │  │    │
│  │  │    - player_user_map: Dict                        │  │    │
│  │  │    - created_at: float                            │  │    │
│  │  └───────────────────────────────────────────────────┘  │    │
│  │                                                            │    │
│  │  ┌───────────────────────────────────────────────────┐  │    │
│  │  │          LangGraph Game Engine                     │  │    │
│  │  │                                                     │  │    │
│  │  │  - AI Agent Orchestration                         │  │    │
│  │  │  - Game State Management                          │  │    │
│  │  │  - Phase Transitions                              │  │    │
│  │  │  - Multi-Human Mode Support                       │  │    │
│  │  └───────────────────────────────────────────────────┘  │    │
│  │                                                            │    │
│  │  ┌───────────────────────────────────────────────────┐  │    │
│  │  │          Database (SQLite/PostgreSQL)              │  │    │
│  │  │                                                     │  │    │
│  │  │  - Users (auth, gem balance)                      │  │    │
│  │  │  - Sessions (game history)                        │  │    │
│  │  │  - CashoutTransactions                            │  │    │
│  │  │  - RoomStakes                                     │  │    │
│  │  └───────────────────────────────────────────────────┘  │    │
│  └──────────────────────────┬─────────────────────────────────┘    │
└─────────────────────────────┼─────────────────────────────────────┘
                              │
                    ┌─────────┴──────────┐
                    │                    │
                    ▼                    ▼
              ┌──────────┐         ┌──────────┐
              │ OpenAI   │         │  MTurk   │
              │   API    │         │   API    │
              │          │         │          │
              │ gpt-5.1  │         │ Cashout  │
              │  -nano   │         │  HITs    │
              └──────────┘         └──────────┘
```

---

## Data Flow Diagrams

### 1. Create Room Flow (React Frontend)

```
User                 React App            Backend              LangGraph
 │                      │                     │                     │
 │  Click "Create"      │                     │                     │
 ├─────────────────────>│                     │                     │
 │                      │                     │                     │
 │  Fill Form (Modal)   │                     │                     │
 │  - Name: "Test"      │                     │                     │
 │  - Humans: 2         │                     │                     │
 │  - Total: 5          │                     │                     │
 │  - Stakes: 10%       │                     │                     │
 │                      │                     │                     │
 │  Submit              │  POST /rooms/create │                     │
 ├─────────────────────>├────────────────────>│                     │
 │                      │                     │                     │
 │                      │                     │  generate_room_code()
 │                      │                     │  → "AB12CD"         │
 │                      │                     │                     │
 │                      │                     │  validate stakes    │
 │                      │                     │  (if multi-human)   │
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
 │                      │                     │  Store room with    │
 │                      │                     │  gem stakes config  │
 │                      │                     │                     │
 │                      │  Response:          │                     │
 │                      │  {room_code,        │                     │
 │                      │   room_name,        │                     │
 │                      │   player_id}        │                     │
 │                      │<────────────────────┤                     │
 │                      │                     │                     │
 │                      │  Auto-navigate to   │                     │
 │                      │  waiting or game    │                     │
 │  Waiting/Game Page   │                     │                     │
 │<─────────────────────┤                     │                     │
 │                      │                     │                     │
```

### 2. Join Room Flow (React + WebSocket)

```
Player              React App            Backend              Game
 │                      │                     │                     │
 │  View Lobby          │  GET /rooms/list    │                     │
 ├─────────────────────>├────────────────────>│                     │
 │                      │                     │                     │
 │                      │  Filter & display   │                     │
 │  Room List           │  [rooms...]         │                     │
 │<─────────────────────┤<────────────────────┤                     │
 │                      │                     │                     │
 │  Click "Join"        │                     │                     │
 ├─────────────────────>│                     │                     │
 │                      │                     │                     │
 │  Navigate to /join   │  POST /rooms/join   │                     │
 ├─────────────────────>├────────────────────>│                     │
 │                      │                     │                     │
 │                      │                     │  Check capacity     │
 │                      │                     │  Check gem balance  │
 │                      │                     │  (if stakes > 0)    │
 │                      │                     │                     │
 │                      │  {                  │                     │
 │                      │    player_id,       │                     │
 │                      │    can_start: bool  │                     │
 │                      │  }                  │                     │
 │                      │<────────────────────┤                     │
 │                      │                     │                     │
 │  Waiting/Game Page   │  Establish WebSocket│                     │
 │<─────────────────────┤  /ws/game/{code}    │                     │
 │                      ├────────────────────>│                     │
 │                      │                     │                     │
 │                      │  Real-time updates  │                     │
 │                      │<────────────────────┤                     │
 │                      │                     │                     │
```

### 3. Game Flow (Single-Human Mode)

```
Players            Frontend            Backend            LangGraph
 │                     │                   │                   │
 │  In game page       │                   │                   │
 │                     │                   │                   │
 │                     │  WebSocket open   │  run_discussion() │
 │                     │<──────────────────┼──────────────────>│
 │                     │                   │                   │
 │  Discussion Phase   │  Timer sync msgs  │  AI agents chat   │
 │  (240s default)     │<──────────────────┤<──────────────────┤
 │                     │                   │                   │
 │  Human types msg    │  POST /message    │                   │
 ├────────────────────>├──────────────────>│  Broadcast to all │
 │                     │                   ├──────────────────>│
 │                     │  Broadcast msg    │                   │
 │  See all messages   │<──────────────────┤                   │
 │<────────────────────┤                   │                   │
 │                     │                   │                   │
 │  Phase: Voting      │  "phase": "Voting"│  run_voting()     │
 │  (120s default)     │<──────────────────┼──────────────────>│
 │                     │                   │                   │
 │  Cast vote          │  POST /vote       │                   │
 ├────────────────────>├──────────────────>│  Store vote       │
 │                     │                   │                   │
 │                     │                   │  AI agents vote   │
 │                     │                   │<──────────────────┤
 │                     │                   │                   │
 │  Game Over          │  "phase":         │  complete_voting()│
 │                     │  "GameOver"       │                   │
 │<────────────────────┤<──────────────────┤  Determine winner │
 │                     │                   │  Calculate gems   │
 │  +50 gems credited  │  Show results     │  (50 gems each)   │
 │<────────────────────┤                   │                   │
 │                     │                   │                   │
```

### 4. Game Flow (Multi-Human Mode with Stakes)

```
Players            Frontend            Backend            LangGraph
 │                     │                   │                   │
 │  Join multi-human   │                   │  Validate:        │
 │  game (10% stakes)  │  POST /join       │  - gem_balance    │
 ├────────────────────>├──────────────────>│    >= 250         │
 │                     │                   │  Calculate stakes │
 │                     │                   │  minimum_stake    │
 │                     │                   │                   │
 │  Discussion Phase   │  WebSocket msgs   │  run_discussion() │
 │  (240s)             │<──────────────────┤                   │
 │                     │                   │  AI agents don't  │
 │                     │                   │  vote in multi-   │
 │                     │                   │  human mode       │
 │                     │                   │                   │
 │  Voting Phase       │  "phase": "Voting"│  run_voting()     │
 │  (120s)             │<──────────────────┤                   │
 │                     │                   │                   │
 │  Vote for N-1       │  POST /vote       │  Store votes      │
 │  humans (all but    │  {voted_for: [...]}│  Validate count  │
 │  yourself)          ├──────────────────>│  (must be N-1)    │
 │                     │                   │                   │
 │  Game Over          │                   │  complete_voting()│
 │                     │                   │                   │
 │                     │                   │  Deduct stakes:   │
 │                     │                   │  -minimum_stake   │
 │                     │                   │                   │
 │                     │                   │  Determine winners│
 │                     │                   │  (most votes)     │
 │                     │                   │                   │
 │                     │                   │  Calculate gems:  │
 │                     │                   │  - Base: 100      │
 │                     │                   │  - Winners: get   │
 │                     │                   │    refund + share │
 │                     │                   │  - Losers: lose   │
 │                     │                   │    stake          │
 │                     │                   │                   │
 │  Results shown      │  "game_over" msg  │                   │
 │  Gems credited      │<──────────────────┤  Update balances  │
 │<────────────────────┤                   │  atomically       │
 │                     │                   │                   │
```

---

## Component Interactions

### Frontend Components (React)

```
┌─────────────────────────────────────────────────────────┐
│                    React Application                     │
│                                                           │
│  ┌────────────────────────────────────────────────────┐ │
│  │         Global State & Contexts                    │ │
│  │                                                     │ │
│  │  - AuthContext (user, token, login, logout)       │ │
│  │  - GameContext (room, player, session)            │ │
│  │  - LanguageContext (English/Korean)               │ │
│  │  - React Router (client-side routing)             │ │
│  └────────────────────────────────────────────────────┘ │
│                                                           │
│  ┌────────────────────────────────────────────────────┐ │
│  │                  Page Components                   │ │
│  │                                                     │ │
│  │  LobbyPage      - Room list, create, join         │ │
│  │  WaitingPage    - Wait for players                 │ │
│  │  GamePage       - Main game UI with WebSocket      │ │
│  │  DashboardPage  - Earnings, gem balance, stats    │ │
│  │  WalletPage     - Gem balance, cashout button     │ │
│  │  GemsInfoPage   - Gem system guide                 │ │
│  │  AdminPage      - Admin panel, analytics           │ │
│  │  ProfilePage    - User profile, MTurk Worker ID    │ │
│  └────────────────────────────────────────────────────┘ │
│                                                           │
│  ┌────────────────────────────────────────────────────┐ │
│  │              Shared Components                     │ │
│  │                                                     │ │
│  │  - ChatWindow (message display)                    │ │
│  │  - MessageInput (typing interface)                 │ │
│  │  - PlayerList (player status)                      │ │
│  │  - PhaseTimer (countdown timer)                    │ │
│  │  - RoomCard (lobby room display)                   │ │
│  │  - GameOver (results modal)                        │ │
│  │  - CreateRoomModal (room creation form)            │ │
│  └────────────────────────────────────────────────────┘ │
│                                                           │
│  ┌────────────────────────────────────────────────────┐ │
│  │                Custom Hooks                        │ │
│  │                                                     │ │
│  │  - useWebSocket (WebSocket connection)             │ │
│  │  - useHeartbeat (online status tracking)           │ │
│  │  - useAuth (authentication state)                  │ │
│  └────────────────────────────────────────────────────┘ │
│                                                           │
│  ┌────────────────────────────────────────────────────┐ │
│  │              API Services                          │ │
│  │                                                     │ │
│  │  - api.js (axios instance, JWT interceptor)        │ │
│  │  - roomAPI (room operations)                       │ │
│  │  - walletAPI (gem operations)                      │ │
│  │  - sessionsAPI (game history)                      │ │
│  └────────────────────────────────────────────────────┘ │
└───────────────────────────────────────────────────────────┘
```

### Backend Components

```
┌─────────────────────────────────────────────────────────┐
│                   FastAPI Backend                        │
│                                                           │
│  ┌────────────────────────────────────────────────────┐ │
│  │              Router Layer                          │ │
│  │                                                     │ │
│  │  auth.py        - Login, register, JWT auth        │ │
│  │  rooms.py       - Room CRUD, join, leave           │ │
│  │  wallet.py      - Gem balance, cashout             │ │
│  │  sessions.py    - Game history                     │ │
│  │  admin.py       - Admin APIs                       │ │
│  │  websocket.py   - WebSocket handler                │ │
│  │  general.py     - Health, online users             │ │
│  └────────────────────────────────────────────────────┘ │
│                                                           │
│  ┌────────────────────────────────────────────────────┐ │
│  │           Service Layer                            │ │
│  │                                                     │ │
│  │  game_coordinator.py  - Phase management           │ │
│  │  room_management.py   - Room lifecycle             │ │
│  │  stats_service.py     - Gem calculations           │ │
│  │  messaging.py         - WebSocket broadcast        │ │
│  │  cashout_service.py   - MTurk integration          │ │
│  │  cashout_monitor.py   - Background HIT monitor     │ │
│  └────────────────────────────────────────────────────┘ │
│                                                           │
│  ┌────────────────────────────────────────────────────┐ │
│  │            Data Layer                              │ │
│  │                                                     │ │
│  │  In-Memory (rooms dict):                           │ │
│  │    - Active game state                             │ │
│  │    - WebSocket connections                         │ │
│  │    - Player presence                               │ │
│  │                                                     │ │
│  │  Database (SQLite/PostgreSQL):                     │ │
│  │    - Users (auth, gems)                            │ │
│  │    - Sessions (history)                            │ │
│  │    - CashoutTransactions                           │ │
│  │    - RoomStakes                                    │ │
│  └────────────────────────────────────────────────────┘ │
│                                                           │
│  ┌────────────────────────────────────────────────────┐ │
│  │          Game Engine (LangGraph)                   │ │
│  │                                                     │ │
│  │  langgraph_game.py:                                │ │
│  │    - GameGraph class                               │ │
│  │    - AI agent nodes                                │ │
│  │    - State transitions                             │ │
│  │                                                     │ │
│  │  langgraph_state.py:                               │ │
│  │    - GameState TypedDict                           │ │
│  │    - Phase enum                                    │ │
│  │    - Player models                                 │ │
│  └────────────────────────────────────────────────────┘ │
└───────────────────────────────────────────────────────────┘
```

---

## Key Design Decisions

### 1. React vs Streamlit
- **Choice**: React 18 + Vite frontend
- **Rationale**: Better UX, WebSocket support, modern tooling
- **Trade-off**: More complex setup than Streamlit
- **Benefits**: Real-time updates, smooth navigation, better scalability

### 2. WebSocket vs Polling
- **Choice**: WebSocket for real-time game updates
- **Rationale**: Instant updates, reduced bandwidth, better scalability
- **Trade-off**: More complex connection management
- **Benefits**: 25x reduction in requests, <100ms latency

### 3. In-Memory + Database Hybrid
- **Choice**: In-memory for active games, database for persistence
- **Rationale**: Fast game state access, persistent user data
- **Trade-off**: Game state lost on restart (acceptable for short games)
- **Benefits**: Optimal performance for real-time gameplay

### 4. Gem-Based Economy
- **Choice**: Gems as intermediate currency (1000 gems = $1 USD)
- **Rationale**: Flexible reward system, gamification, MTurk integration
- **Trade-off**: Additional complexity
- **Benefits**: Engaging reward system, research participant compensation

### 5. Stakes System (Multi-Human)
- **Choice**: Optional risk/reward with voting accuracy
- **Rationale**: Competitive gameplay, strategic depth
- **Trade-off**: Requires minimum balance, can lose gems
- **Benefits**: Incentivizes careful play and human identification

---

## Technology Stack

```
┌─────────────────────────────────────┐
│         Frontend Layer              │
│                                     │
│  - React 18                         │
│  - Vite (build tool)                │
│  - React Router                     │
│  - Tailwind CSS                     │
│  - Axios (HTTP client)              │
│  - WebSocket API                    │
└──────────────┬──────────────────────┘
               │ HTTP REST + WebSocket
               │
┌──────────────▼──────────────────────┐
│         Backend Layer               │
│                                     │
│  - FastAPI                          │
│  - Uvicorn (ASGI server)            │
│  - Python 3.8+                      │
│  - Async/await                      │
│  - SQLAlchemy (async)               │
│  - JWT (python-jose)                │
│  - Argon2 (password hashing)        │
└──────────────┬──────────────────────┘
               │
     ┌─────────┴─────────┬────────────┐
     │                   │            │
     ▼                   ▼            ▼
┌──────────┐     ┌──────────────┐  ┌────────┐
│LangGraph │     │  OpenAI API  │  │ MTurk  │
│          │     │              │  │  API   │
│- Game    │     │- gpt-5.1-nano│  │        │
│  State   │     │  (or config) │  │- Worker│
│- AI      │     │- AI Players  │  │  HITs  │
│  Agents  │     │              │  │        │
└──────────┘     └──────────────┘  └────────┘
```

---

## Deployment Architecture

### Development (Current)
```
localhost:5173 (React/Vite) → localhost:8000 (FastAPI) → OpenAI API
                                    ↓
                            SQLite Database
```

### Production (Recommended)
```
                    ┌──────────┐
                    │ Netlify/ │ (React Frontend - Static)
                    │  Vercel  │
                    └────┬─────┘
                         │ HTTPS
                         ▼
                  ┌─────────────┐
                  │   Railway/  │ (FastAPI Backend)
                  │   Render    │
                  └──────┬──────┘
                         │
              ┌──────────┴──────────┬────────────┐
              │                     │            │
              ▼                     ▼            ▼
         ┌────────┐          ┌──────────┐  ┌──────────┐
         │ Neon/  │          │ OpenAI   │  │  MTurk   │
         │Supabase│          │   API    │  │   API    │
         │ (PG)   │          │          │  │          │
         └────────┘          └──────────┘  └──────────┘
```

---

## Performance Characteristics

### Backend
- **Room Creation**: O(1) - constant time
- **Room List**: O(n) - linear in number of rooms (paginated)
- **Room Join**: O(1) - constant time + gem validation
- **Game Start**: O(m) - linear in AI players
- **Gem Calculation**: O(h²) - quadratic in humans (voting accuracy matrix)

### Frontend
- **Lobby Render**: O(r) - linear in rooms per page (max 10)
- **Game Render**: O(p + m) - linear in players + messages
- **WebSocket Updates**: O(1) - instant state updates

### Network
- **Create Room**: 1-2 requests (create + auto-join)
- **Join Room**: 1 request
- **Game**: WebSocket (persistent connection, event-driven)
- **Bandwidth**: ~10 messages/second for 100 users (vs 250 req/s with polling)

---

## Scalability Considerations

### Current Limits
- ~200 concurrent rooms (in-memory)
- ~200+ concurrent users (with WebSocket)
- Single server (no horizontal scaling yet)

### Scaling Strategy
1. **Short-term**: PostgreSQL for persistence
2. **Medium-term**: Redis for session storage
3. **Long-term**: Microservices
   - Separate game engine service
   - Load balancer
   - Horizontal scaling

---

## Security Model

### Current (Production)
- JWT authentication (Argon2 password hashing)
- Rate limiting (10 req/min per IP on API endpoints)
- CORS configured for specific origins
- Input validation on all endpoints
- WebSocket authentication required
- Gem transaction atomicity (prevent race conditions)
- MTurk worker ID validation

### Additional Recommendations
- HTTPS in production (required)
- Database connection encryption
- API key rotation
- Audit logging for admin actions
- Monitoring and alerting
- DDoS protection (via CDN)

---

This architecture provides a scalable, real-time gaming platform with integrated gem economy and MTurk payment system for research purposes.
