# Human Hunter - A Turing Test-inspired Social Deduction Game

## Overview
This is a web-based game where one human player competes against multiple AI agents (configurable, default 4) in a social deduction setting. The human tries to blend in while the AIs try to identify and vote out the human.

**Architecture**: Built with LangGraph for advanced multi-agent orchestration, providing a graph-based state machine for game flow management.

## Setup

### Prerequisites
- Python 3.8+
- Node.js 18+ (with npm). If you have an older version (like 10.x), you'll need to upgrade. On Ubuntu, the default apt version may be outdated. We recommend using Node Version Manager (nvm) to install Node.js 18:
  1. Install nvm:
     ```
     curl -o- https://raw.githubusercontent.com/nvm-sh/nvm/v0.39.7/install.sh | bash
     ```
     Then close and reopen your terminal, or run `source ~/.bashrc`.
  2. Install Node.js 18:
     ```
     nvm install 18
     nvm use 18
     ```
  3. Verify:
     ```
     node -v  # Should show v18.x.x
     npm -v
     ```
- An OpenAI API key for AI agents

### Backend Setup
1. Navigate to the backend directory:
   ```
   cd backend
   ```
2. Install dependencies:
   ```
   pip install -r requirements.txt
   ```
3. Set the OpenAI API key as an environment variable:
   ```
   export OPENAI_API_KEY='your-api-key-here'
   ```
4. Run the backend server:
   ```
   uvicorn main:app --reload
   ```

### Frontend Setup

You can choose between two frontend options:

#### Option 1: React Frontend (WebSocket-based, Real-time)
1. Navigate to the frontend directory:
   ```
   cd frontend
   ```
2. Install dependencies:
   ```
   npm install
   ```
3. Run the frontend development server:
   ```
   npm run dev
   ```
4. Open your browser at http://localhost:5173

#### Option 2: Streamlit Frontend (Polling-based, Simpler)
1. From the project root directory:
   ```
   pip install -r streamlit_requirements.txt
   ```
2. Run the Streamlit app:
   ```
   streamlit run streamlit_app.py
   ```
3. Your browser will open automatically at http://localhost:8501

**Note**: Both frontends connect to the same backend and can coexist. Choose based on your preference:
- **React**: Real-time updates via WebSocket, modern UI with Tailwind CSS
- **Streamlit**: Simpler Python-based UI, polling updates (~1 second refresh), easier to customize

### Playing the Game
- The game will start automatically with you as the human player.
- During the **Discussion Phase**: Chat with other players (AI agents) about the topic
- During the **Voting Phase**: Vote to eliminate a player you suspect is human (if you're AI) or an AI (if you're human)
- **Survive multiple rounds** to win!

## Configuration
The game is now highly configurable via environment variables in `backend/config.py`:
- `NUM_AI_PLAYERS`: Number of AI opponents (default: 4, supports up to 8+)
- `AI_MODEL_NAME`: LLM model to use (default: 'gpt-4o-mini')
- `AI_MODEL_PROVIDER`: Choose between 'openai', 'anthropic', or 'groq' (default: 'openai')
- `DISCUSSION_TIME`: Discussion phase duration in seconds (default: 180)
- `VOTING_TIME`: Voting phase duration in seconds (default: 60)
- `ROUNDS_TO_WIN`: Number of rounds human must survive to win (default: 3)

You can set these as environment variables or modify `backend/config.py` directly.

## LangGraph Architecture
The backend uses LangGraph's StateGraph for advanced multi-agent orchestration:

### Key Components
- **State Management**: All game state is managed through a TypedDict (`GameState`) that flows through the graph
- **Agent Nodes**: Each AI player is represented as a node with:
  - Unique personality and behavioral traits
  - Independent decision-making for chat messages and votes
  - Pseudonymized view of other players for anonymity
- **Orchestration Nodes**: Game flow nodes manage phases:
  - Discussion phase (parallel AI chat generation)
  - Voting phase (sequential AI vote processing)
  - Elimination (vote counting and player removal)
  - Win condition checking
  - New round initialization

### Graph Flow
```
Initialize → Discussion → AI Chat Agents → Voting → AI Vote Agents → Elimination → Win Check
                                                                                      ↓
                                                                          New Round ←┘ (if no winner)
```

### Benefits
- **Scalability**: Easily adjust number of AI agents (4-8+)
- **Modularity**: Each game phase is a discrete node
- **State Tracking**: Complete game history maintained in state
- **Extensibility**: Easy to add new agent types or game mechanics

## Documentation

- **README.md** (this file) - General overview and setup
- **QUICK_START.md** - Get running in 5 minutes
- **STREAMLIT_README.md** - Streamlit frontend guide
- **STREAMLIT_IMPLEMENTATION.md** - Technical implementation details
- **LANGGRAPH_MIGRATION.md** - LangGraph architecture guide
- **DEVELOPER_GUIDE.md** - Developer documentation
- **IMPLEMENTATION_SUMMARY.md** - Complete implementation summary

## Deployment
To host the game publicly:

### Backend (FastAPI)
Deploy to a platform like Render, Heroku, or a VPS:
- Set OPENAI_API_KEY env var
- Expose on a public URL (e.g., https://your-backend.onrender.com)

### Frontend Options

**React/Vite**: Deploy to Vercel, Netlify, or similar
- Set REACT_APP_BACKEND_URL env var to your backend URL

**Streamlit**: Deploy to Streamlit Cloud (free)
- Connect GitHub repository
- Deploy streamlit_app.py
- Set BACKEND_URL environment variable

Users access the frontend URL in their browser; each can play in their own room by entering a room code or auto-generating one.
