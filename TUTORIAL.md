# Human Hunter - Complete Project Tutorial

Welcome to the Human Hunter project! This tutorial provides everything you need to understand, develop, and maintain this AI social deduction game.

## Table of Contents

1. [Introduction](#1-introduction)
2. [Architecture Overview](#2-architecture-overview)
3. [Codebase Walkthrough](#3-codebase-walkthrough)
4. [Core Concepts](#4-core-concepts)
5. [Setup and Development](#5-setup-and-development)
6. [Key Features Deep Dive](#6-key-features-deep-dive)
7. [Deployment](#7-deployment)
8. [Troubleshooting and FAQ](#8-troubleshooting-and-faq)

---

## 1. Introduction

### What is Human Hunter?

Human Hunter is a real-time multiplayer social deduction game where human players join a group chat with AI bots. The objective varies by game mode:

- **Single-Human Mode**: One human tries to blend in with AI players. The human must convince AI players that they are the most "human-like" to receive votes and win.
- **Multi-Human Mode**: Multiple humans compete to identify each other while avoiding detection by AI players.

### Game Flow

```
┌─────────────┐     ┌──────────────────┐     ┌───────────────┐
│   LOBBY     │────▶│  DISCUSSION      │────▶│    VOTING     │
│  Join Room  │     │  Chat with all   │     │  Vote for AI  │
│  Wait for   │     │  players (3 min) │     │  (1 min)      │
│  players    │     │                  │     │               │
└─────────────┘     └──────────────────┘     └───────┬───────┘
                                                     │
                    ┌──────────────────┐             │
                    │   ELIMINATION    │◀────────────┘
                    │  Most-voted out  │
                    │  Reveal identity │
                    └────────┬─────────┘
                             │
              ┌──────────────┴──────────────┐
              ▼                             ▼
       ┌────────────┐               ┌─────────────┐
       │  CONTINUE  │               │  GAME OVER  │
       │ Next Round │               │ Winner      │
       │ (if alive) │               │ Announced   │
       └────────────┘               └─────────────┘
```

### Key Features

| Feature | Description |
|---------|-------------|
| **Multi-Agent AI** | LangGraph orchestrates AI players with distinct personalities |
| **Real-Time Chat** | WebSocket-based instant messaging |
| **Gem Economy** | Earn gems by playing, convert to real money via MTurk |
| **Gamification** | Levels, achievements, streaks, and leaderboards |
| **MTurk Integration** | Automated payment system for research participants |
| **Flexible Config** | Adjustable AI models, timing, and player counts |

---

## 2. Architecture Overview

### System Diagram

```
┌─────────────────────────────────────────────────────────────────────────┐
│                           USER'S BROWSER                                 │
│  ┌───────────────────────────────────────────────────────────────────┐  │
│  │                    REACT FRONTEND (Port 5173)                      │  │
│  │                                                                    │  │
│  │  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌──────────┐ │  │
│  │  │   Lobby     │  │   Game      │  │  Dashboard  │  │  Admin   │ │  │
│  │  │   Page      │  │   Page      │  │   Page      │  │  Panel   │ │  │
│  │  └─────────────┘  └─────────────┘  └─────────────┘  └──────────┘ │  │
│  │                                                                    │  │
│  │  ┌─────────────────────────────────────────────────────────────┐  │  │
│  │  │          Services: API Client, WebSocket, Auth               │  │  │
│  │  └─────────────────────────────────────────────────────────────┘  │  │
│  └───────────────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────────────┘
                                    │
                    HTTP REST + WebSocket (WSS)
                                    │
┌───────────────────────────────────┴─────────────────────────────────────┐
│                       FASTAPI BACKEND (Port 8000)                        │
│                                                                          │
│  ┌──────────────────────────────────────────────────────────────────┐  │
│  │                         ROUTERS                                   │  │
│  │  ┌────────┐ ┌────────┐ ┌─────────┐ ┌─────────┐ ┌──────────────┐  │  │
│  │  │  auth  │ │ rooms  │ │ wallet  │ │ admin   │ │  websocket   │  │  │
│  │  └────────┘ └────────┘ └─────────┘ └─────────┘ └──────────────┘  │  │
│  └──────────────────────────────────────────────────────────────────┘  │
│                                                                          │
│  ┌──────────────────────────────────────────────────────────────────┐  │
│  │                         SERVICES                                  │  │
│  │  ┌──────────────────┐ ┌──────────────────┐ ┌──────────────────┐  │  │
│  │  │ game_coordinator │ │  room_management │ │  stats_service   │  │  │
│  │  │ (Phase Control)  │ │  (Room CRUD)     │ │  (Session Data)  │  │  │
│  │  └──────────────────┘ └──────────────────┘ └──────────────────┘  │  │
│  └──────────────────────────────────────────────────────────────────┘  │
│                                                                          │
│  ┌──────────────────────────────────────────────────────────────────┐  │
│  │                    LANGGRAPH AI LAYER                             │  │
│  │  ┌──────────────────┐  ┌─────────────────┐  ┌─────────────────┐  │  │
│  │  │  GameGraph       │  │  GameState      │  │  AI Agents      │  │  │
│  │  │  (Orchestrator)  │  │  (State Schema) │  │  (LLM Calls)    │  │  │
│  │  └──────────────────┘  └─────────────────┘  └─────────────────┘  │  │
│  └──────────────────────────────────────────────────────────────────┘  │
│                                                                          │
│  ┌──────────────────────────────────────────────────────────────────┐  │
│  │                        DATABASE                                   │  │
│  │     SQLite (dev) / PostgreSQL (prod)  +  In-Memory Room State    │  │
│  └──────────────────────────────────────────────────────────────────┘  │
└──────────────────────────────────────────────────────────────────────────┘
                                    │
                              OpenAI API
                                    │
                    ┌───────────────┴───────────────┐
                    │     GPT-4o / gpt-5.1-nano     │
                    │     (AI Player Responses)     │
                    └───────────────────────────────┘
```

### Technology Stack

| Layer | Technologies |
|-------|-------------|
| **Frontend** | React 18, Vite, Tailwind CSS, WebSocket API |
| **Backend** | FastAPI, Uvicorn (ASGI), Python 3.8+ |
| **AI/LLM** | LangGraph, LangChain, OpenAI gpt-5.1-nano|
| **Database** | SQLAlchemy (async), SQLite/PostgreSQL |
| **Auth** | JWT tokens, Argon2 password hashing |
| **Payments** | AWS MTurk API |

### Data Flow

1. **User Action** → React component calls API service
2. **API Request** → FastAPI router validates and processes
3. **Game Logic** → LangGraph node executes state update
4. **AI Response** → LLM generates message/vote
5. **Broadcast** → WebSocket sends update to all clients
6. **UI Update** → React re-renders with new state

---

## 3. Codebase Walkthrough

### Project Structure

```
ai-group-chat-streamlit/
├── backend/                    # FastAPI + LangGraph backend
│   ├── main.py                 # App entry, CORS, middleware
│   ├── langgraph_game.py       # GameGraph class, AI nodes
│   ├── langgraph_state.py      # GameState TypedDict schema
│   ├── config.py               # Game configuration
│   ├── database.py             # SQLAlchemy async setup
│   ├── auth.py                 # JWT, password hashing
│   ├── routers/                # API endpoint modules
│   │   ├── auth.py             # Login, register, me
│   │   ├── rooms.py            # Room CRUD, join, leave
│   │   ├── wallet.py           # Gem balance, cashout
│   │   ├── admin.py            # Admin dashboard APIs
│   │   └── websocket.py        # WebSocket handler
│   ├── services/               # Business logic
│   │   ├── game_coordinator.py # Phase management
│   │   ├── room_management.py  # Room lifecycle
│   │   ├── messaging.py        # WebSocket broadcasting
│   │   └── stats_service.py    # Session stats
│   └── requirements.txt        # Python dependencies
│
├── frontend/                   # React + Vite frontend
│   ├── src/
│   │   ├── App.jsx             # Router, auth context
│   │   ├── main.jsx            # Entry point
│   │   ├── pages/              # Route components
│   │   │   ├── LobbyPage.jsx   # Room list, create
│   │   │   ├── GamePage.jsx    # Main game UI
│   │   │   ├── DashboardPage.jsx
│   │   │   └── AdminPage.jsx
│   │   ├── components/         # Reusable UI
│   │   │   ├── ChatWindow.jsx
│   │   │   ├── PlayerList.jsx
│   │   │   ├── PhaseTimer.jsx
│   │   │   └── ...
│   │   ├── services/           # API clients
│   │   │   └── api.js          # Axios instance
│   │   └── contexts/           # React contexts
│   │       └── AuthContext.jsx
│   ├── package.json
│   └── vite.config.js
│
├── markdowns/                  # Documentation (organized)
│   ├── README.md               # Doc index
│   ├── SYSTEM_ARCHITECTURE.md
│   ├── DEVELOPER_GUIDE.md
│   └── archive/                # Historical docs
│
├── .env                        # Environment variables (gitignored)
├── env.example                 # Template for .env
├── README.md                   # Project overview
├── START_HERE.md               # Quick start guide
├── MTURK_SETUP.md              # MTurk integration
└── TUTORIAL.md                 # This file
```

### Key Backend Files

#### `backend/langgraph_game.py` - AI Orchestration

The `GameGraph` class is the heart of the AI system:

```python
class GameGraph:
    """Main game graph orchestrator."""
    
    def __init__(self, api_key: str = None):
        # Initialize LLM (OpenAI)
        self.llm = ChatOpenAI(model="gpt-4o-mini", temperature=0.8)
        self.graph = self._build_graph()
    
    def _build_graph(self):
        """Build the LangGraph StateGraph."""
        workflow = StateGraph(GameState)
        
        # Add nodes for each game action
        workflow.add_node("ai_chat", self.ai_chat_node)
        workflow.add_node("ai_vote", self.ai_vote_node)
        workflow.add_node("elimination", self.elimination_node)
        # ... more nodes
        
        return workflow.compile()
```

#### `backend/langgraph_state.py` - State Schema

Defines the complete game state:

```python
class GameState(TypedDict):
    room_code: str
    round: int
    phase: Phase  # DISCUSSION, VOTING, ELIMINATION, GAME_OVER
    players: List[PlayerInfo]
    chat_history: Annotated[List[ChatMessage], operator.add]
    votes: Dict[str, List[str]]
    topic: str
    # ... and more
```

#### `backend/services/game_coordinator.py` - Phase Control

Manages game timing and phase transitions:

```python
async def run_discussion_phase(room_code: str):
    """Run discussion with timer and AI engagement."""
    discussion_time = rooms[room_code].get('discussion_duration', 180)
    # Broadcast timer updates, trigger AI responses
    
async def run_voting_phase(room_code: str):
    """Run voting with deadline enforcement."""
    # Collect votes, handle timeouts
```

### Key Frontend Files

#### `frontend/src/pages/GamePage.jsx` - Main Game UI

```jsx
function GamePage() {
    const [gameState, setGameState] = useState(null);
    const [messages, setMessages] = useState([]);
    
    // WebSocket connection
    useEffect(() => {
        const ws = new WebSocket(`ws://localhost:8000/ws/game/${roomCode}`);
        ws.onmessage = (event) => {
            const data = JSON.parse(event.data);
            handleWebSocketMessage(data);
        };
    }, [roomCode]);
    
    return (
        <div className="game-container">
            <PlayerList players={gameState?.players} />
            <ChatWindow messages={messages} />
            <MessageInput onSend={sendMessage} />
            <PhaseTimer phase={gameState?.phase} />
        </div>
    );
}
```

#### `frontend/src/services/api.js` - API Client

```javascript
import axios from 'axios';

const api = axios.create({
    baseURL: import.meta.env.VITE_BACKEND_URL || 'http://localhost:8000',
});

// Add JWT token to requests
api.interceptors.request.use((config) => {
    const token = localStorage.getItem('token');
    if (token) {
        config.headers.Authorization = `Bearer ${token}`;
    }
    return config;
});
```

---

## 4. Core Concepts

### LangGraph State Management

LangGraph uses a declarative state machine approach:

1. **State**: A TypedDict containing all game data
2. **Nodes**: Functions that process state and return updates
3. **Edges**: Transitions between nodes (conditional or static)

```python
# Node example: AI generates a chat message
def ai_chat_node(self, state: GameState) -> GameState:
    ai_id = state["pending_ai_messages"][0]
    message = self._generate_with_llm(state, ai_id)
    
    return {
        "chat_history": [{"sender": ai_id, "message": message}],
        "pending_ai_messages": state["pending_ai_messages"][1:]
    }
```

**Key Principle**: Nodes return partial updates. Lists with `operator.add` annotation append; other fields replace.

### WebSocket Protocol

The game uses a message-based WebSocket protocol:

| Message Type | Direction | Description |
|--------------|-----------|-------------|
| `player_list` | Server→Client | Current players in room |
| `message` | Both | Chat message |
| `typing` | Both | Typing indicator |
| `phase` | Server→Client | Phase change (discussion/voting) |
| `timer_sync` | Server→Client | Server time remaining |
| `vote` | Client→Server | Vote submission |
| `elimination` | Server→Client | Player eliminated |
| `game_over` | Server→Client | Game ended, winner revealed |

### Game Phases

```python
class Phase(str, Enum):
    DISCUSSION = "Discussion"  # Chat freely
    VOTING = "Voting"          # Cast votes
    ELIMINATION = "Elimination" # Process votes
    GAME_OVER = "GameOver"     # Show results
```

Phase transitions are server-controlled with strict timing.

### Authentication Flow

```
┌────────────┐     ┌─────────────┐     ┌──────────────┐
│   Login    │────▶│ Validate    │────▶│ Generate JWT │
│   Request  │     │ Credentials │     │ Token        │
└────────────┘     └─────────────┘     └──────┬───────┘
                                              │
┌────────────┐     ┌─────────────┐            │
│  Protected │◀────│ Verify JWT  │◀───────────┘
│  API Call  │     │ on Request  │
└────────────┘     └─────────────┘
```

JWT tokens are stored in localStorage and sent in Authorization header.

---

## 5. Setup and Development

### Prerequisites

- **Python 3.8+** (3.11 recommended)
- **Node.js 18+**
- **OpenAI API Key**

### Local Development Setup

#### 1. Clone and Configure

```bash
git clone <repository-url>
cd ai-group-chat-streamlit
cp env.example .env
# Edit .env with your OPENAI_API_KEY
```

#### 2. Backend Setup

```bash
cd backend
pip install -r requirements.txt

# Run backend
python main.py
# Or: uvicorn backend.main:app --reload
```

Backend runs at http://localhost:8000

#### 3. Frontend Setup

```bash
cd frontend
npm install
npm run dev
```

Frontend runs at http://localhost:5173

### Configuration Options

Key settings in `.env`:

```env
# Required
OPENAI_API_KEY=sk-...

# Game Settings
NUM_AI_PLAYERS=4              # 4-8 AI opponents
AI_MODEL_NAME=gpt-5.1-nano    # or gpt-4o, claude-3-5-sonnet
DISCUSSION_TIME=240           # seconds (default 4 minutes)
VOTING_TIME=120               # seconds (default 2 minutes)
ROUNDS_TO_WIN=1               # default 1 round

# Database
DATABASE_URL=sqlite+aiosqlite:///./group_chat.db

# Security (CHANGE IN PRODUCTION)
JWT_SECRET_KEY=your-secret-key
ENVIRONMENT=development       # or production
```

### Running Tests

```bash
# Backend
cd backend
pytest

# Frontend
cd frontend
npm test
```

### Common Development Tasks

**Reset Database:**
```bash
rm backend/group_chat.db
# Restart backend - tables recreate automatically
```

**View API Documentation:**
Open http://localhost:8000/docs (Swagger UI)

**Create Admin User:**
```bash
python create_admin.py
```

**Check Backend Logs:**
Logs show AI thinking, token usage, and errors.

---

## 6. Key Features Deep Dive

### AI Agent System

Each AI player has a distinct personality affecting their:
- Writing style and vocabulary
- Response timing
- Voting patterns

Personalities are defined in `config.py` and assigned randomly:

```python
PERSONALITY_IMPERFECTION_LEVELS = {
    "casual_typo_maker": {...},
    "overly_formal": {...},
    "enthusiastic": {...},
    # ... more personalities
}
```

AI agents use chain-of-thought prompting to analyze conversation and generate responses.

### Gem Economy

The game features a comprehensive gem-based economy where players earn gems through gameplay and can convert them to real USD via MTurk (1000 gems = $1.00).

#### Game Modes & Earning Rates

**Single-Human Games (1 human vs AI agents):**

| Participant | Gems Earned |
|-------------|-------------|
| All players (human + AI) | 50 gems |

- Simple participation-based rewards
- No stakes required, no risk
- Perfect for building initial gem balance

**Multi-Human Games (2+ humans competing):**

| Component | Amount | Condition |
|-----------|--------|-----------|
| Base gems | 100 gems | Must vote to receive |
| Stake refund | variable | Winners only (if voted) |
| Stake winnings | variable | Based on voting accuracy |

**Requirements:**
- Minimum 250 gems required to join multi-human games
- Stakes are optional: 0%, 10%, 30%, 50%, or 100% of balance
- Anonymous users can only join 0% stake games

#### Stakes System Mechanics (Multi-Human Games)

**Phase 1: Stake Deduction (Game Start)**

When a multi-human game begins with stakes enabled:

1. Each player's stake calculated: `balance × stake_percentage / 100`
2. System finds **minimum stake** across all players
3. All players pay this minimum amount (deducted immediately after voting)

**Example (3 players, 10% stake):**
```python
Player A: 1000 gems × 10% = 100 stake
Player B: 900 gems × 10% = 90 stake
Player C: 800 gems × 10% = 80 stake

minimum_stake = 80 gems  # Lowest among all players
→ All 3 players pay 80 gems
```

**Phase 2: Reward Distribution (Game End)**

**For Winners (Most Votes):**
```python
# Calculate loser pool
loser_pool = minimum_stake × num_losers

# Divide among winners
max_share = loser_pool / num_winners

# Voting accuracy
votes_needed = num_humans - 1  # Must vote for all OTHER humans
correct_votes = count(voted for other humans)  # Not self, not AI
accuracy = correct_votes / votes_needed  # Returns 0.0 to 1.0

# Rewards
stake_refund = minimum_stake  # Always returned if you voted
stake_winnings = int(accuracy × max_share)  # Proportional to accuracy
total_gems = 100 + stake_refund + stake_winnings
```

**For Losers (Fewer Votes):**
- Base gems: 100 (if voted)
- Stake refund: 0 (forfeited entirely)
- Total: 100 gems
- Net change: 100 - minimum_stake (always negative)

**Voting Penalty:**
- Must vote to receive base gems AND stake refund
- No vote = forfeit everything (even if you win!)

#### Voting Accuracy Impact

In multi-human games, you must vote for **all other humans** (N-1 players, excluding yourself). Your accuracy determines your stake winnings:

| Accuracy | Share of Loser Pool | Example (1000 gem pool) |
|----------|---------------------|-------------------------|
| 100% | Full share | 1000 gems |
| 75% | 3/4 of share | 750 gems |
| 50% | Half of share | 500 gems |
| 25% | 1/4 of share | 250 gems |
| 0% | No winnings | 0 gems (only stake refund) |

#### Complete Example: 2-Player Game (10% Stakes)

**Initial Balances:**
- Player A: 1000 gems
- Player B: 1000 gems

**Stakes Calculation:**
- Player A: 1000 × 10% = 100 gems
- Player B: 1000 × 10% = 100 gems
- minimum_stake = 100 gems (same for both)

**Game Start (Deduction):**
- Player A: 1000 → 900 gems (-100 deducted)
- Player B: 1000 → 900 gems (-100 deducted)

**Voting Results:**
- Player A: 1 vote ← Winner 🏆
- Player B: 0 votes ← Loser

**Voting Accuracy:**
- Player A voted for Player B: 1/1 = 100% accuracy ✅
- Player B voted for Player A: 1/1 = 100% accuracy (but lost)

**Reward Calculation:**

**Player A (Winner, 100% accuracy):**
```python
base_gems = 100
stake_refund = 100  # Got their stake back
loser_pool = 100 × 1 = 100  # Player B's forfeited stake
max_share = 100 / 1 = 100  # Only 1 winner
stake_winnings = int(1.0 × 100) = 100  # 100% accuracy

total_credited = 100 + 100 + 100 = 300 gems
final_balance = 900 + 300 = 1200 gems
net_change = +200 gems 🎉
```

**Player B (Loser, 100% accuracy but lost):**
```python
base_gems = 100
stake_refund = 0  # Forfeited to winner
stake_winnings = 0  # Losers don't get winnings

total_credited = 100 gems
final_balance = 900 + 100 = 1000 gems
net_change = 0 gems (broke even due to base gems)
```

**System Balance:**
- Total deducted: 200 gems (100 from each)
- Total returned: 300 gems (to winners)
- House collects: 0 gems (winner got 100% accuracy)

If winner had 50% accuracy: winner would get 50 gems winnings instead of 100, and 50 gems would be collected by the house.

#### Gem Wallet & Cashout System

**Viewing Balance:**
- Dashboard page: Shows total earned, current balance, recent games
- Wallet page (`/wallet`): Detailed balance, cashout options, transaction history

**Cashing Out:**
1. **Requirement:** Add MTurk Worker ID in profile page
2. **Minimum:** $2.00 (2000 gems)
3. **Process:**
   - Click "Request Cash Out" in wallet page
   - System creates worker-specific qualification + HIT
   - Accept HIT on MTurk platform
   - Complete HIT by entering provided confirmation code
   - Auto-approved within 1 hour
   - Payment sent via MTurk

**Conversion Rate**: 1000 gems = $1.00 USD

For complete cashout setup and troubleshooting, see [MTURK_SETUP.md](MTURK_SETUP.md).

**Gem to USD Rate**: 1000 gems = $1.00

### MTurk Integration

For research deployments, the system integrates with Amazon Mechanical Turk:

1. **Worker Authentication**: MTurk workers are assigned unique IDs
2. **Standing HIT**: A persistent HIT accepts redemption codes
3. **Cashout Flow**: Workers earn gems → Request cashout → Get redemption code → Submit to MTurk HIT → Receive payment

See `MTURK_SETUP.md` for complete setup instructions.

### Gamification

- **Levels**: XP-based progression
- **Achievements**: Milestone rewards (first win, 10 games played, etc.)
- **Streaks**: Bonus for consecutive days playing
- **Leaderboards**: Weekly and all-time rankings

---

## 7. Deployment

### Development (Local)

```
localhost:5173 (React) ←→ localhost:8000 (FastAPI) ←→ OpenAI API
```

### Production Architecture

```
                    ┌──────────────┐
                    │   Netlify    │  (Frontend - Static)
                    │   /Vercel    │
                    └──────┬───────┘
                           │
                           ▼
                    ┌──────────────┐
                    │   Railway/   │  (Backend - Python)
                    │   Render     │
                    └──────┬───────┘
                           │
              ┌────────────┴────────────┐
              ▼                         ▼
       ┌────────────┐            ┌─────────────┐
       │ PostgreSQL │            │   OpenAI    │
       │ (Supabase) │            │     API     │
       └────────────┘            └─────────────┘
```

### Production Checklist

- [ ] Migrate to PostgreSQL (see `markdowns/SQLITE_TO_POSTGRESQL.md`)
- [ ] Generate strong JWT secrets
- [ ] Set `ENVIRONMENT=production`
- [ ] Configure CORS for your domain only
- [ ] Enable HTTPS
- [ ] Set up database backups
- [ ] Configure monitoring/logging
- [ ] Test with multiple concurrent users

### Quick Deploy Steps

1. **Frontend** → Netlify/Vercel (connect GitHub repo)
2. **Backend** → Railway/Render (Dockerfile or Python buildpack)
3. **Database** → Supabase/Neon (free PostgreSQL)
4. **Update** → Frontend env with backend URL

---

## 8. Troubleshooting and FAQ

### Common Issues

#### Backend Won't Start

**"ModuleNotFoundError"**
- Ensure you're in `backend/` directory
- Run `pip install -r requirements.txt`

**"OPENAI_API_KEY not found"**
- Check `.env` file exists in project root
- Verify key format: `OPENAI_API_KEY=sk-...`

**Port 8000 in use**
```bash
# Kill existing process
lsof -ti:8000 | xargs kill -9
# Or use different port
uvicorn backend.main:app --port 8001
```

#### Frontend Connection Issues

**"Cannot connect to backend"**
- Verify backend is running on http://localhost:8000
- Check browser console for CORS errors
- Ensure `VITE_BACKEND_URL` is correct in frontend

**WebSocket fails**
- Check WebSocket URL matches backend
- Verify no firewall blocking WS connections

#### Game Issues

**AI not responding**
- Check backend logs for API errors
- Verify OpenAI API key is valid and has credits
- Check rate limits

**Players stuck in waiting**
- Refresh page
- Check if room expired (rooms clean up after inactivity)

### Where to Find Logs

| Log Type | Location |
|----------|----------|
| Backend stdout | Terminal running `uvicorn` |
| Frontend console | Browser DevTools → Console |
| API requests | Browser DevTools → Network |
| Database queries | Enable SQLAlchemy echo mode |

### Debugging Tips

1. **Enable verbose logging** in backend:
   ```python
   import logging
   logging.basicConfig(level=logging.DEBUG)
   ```

2. **Inspect game state** via API:
   ```
   GET /api/rooms/{code}/state
   ```

3. **Check WebSocket messages** in browser DevTools Network tab (WS filter)

4. **Use API docs** at http://localhost:8000/docs to test endpoints

### FAQ

**Q: Can I use a different LLM provider?**
A: Yes! Change `AI_MODEL_PROVIDER` in `.env`. Supported: `openai`, `anthropic`, `groq`

**Q: How do I add more AI personalities?**
A: Edit `PERSONALITY_IMPERFECTION_LEVELS` in `backend/config.py`

**Q: Can I run without MTurk?**
A: Yes, MTurk is optional. The game works standalone without payment features.

**Q: How do I reset all data?**
A: Delete `backend/group_chat.db` and restart backend.

---

## Further Reading

- **[README.md](README.md)** - Project overview
- **[START_HERE.md](START_HERE.md)** - Quick start guide
- **[MTURK_SETUP.md](MTURK_SETUP.md)** - MTurk payment integration
- **[env.example](env.example)** - All configuration options
- **[markdowns/DEVELOPER_GUIDE.md](markdowns/DEVELOPER_GUIDE.md)** - LangGraph development patterns
- **[markdowns/SYSTEM_ARCHITECTURE.md](markdowns/SYSTEM_ARCHITECTURE.md)** - Detailed architecture docs

---

## Getting Help

1. Check this tutorial's troubleshooting section
2. Review backend logs for error messages
3. Check browser console for frontend errors
4. Inspect API responses in Network tab
5. Review the documentation in `markdowns/`

---

*Last updated: December 2025*

