# Human-AI Group Chat

The Challenge: Join a group chat with AI bots and/or other humans. Chat, analyze behavior, and vote for who you think is the most human-like player (besides yourself). In a single-human game, you have to get the most votes from the players. In a multi-human game, you have to (1) get the most votes from the players, and (2) identify other human players.

## Key Features

- **Multi-Agent AI System**: Built with LangGraph for advanced agent orchestration
- **Real-Time WebSocket Chat**: Instant messaging and game updates
- **Gem-Based Economy**: Earn gems by playing, cash out via MTurk
- **Gamification System**: Levels, achievements, streaks, and rewards
- **MTurk Integration**: Automated payment processing for research participants
- **Flexible Configuration**: Adjustable AI models, player counts, and game parameters

## Quick Start

Get running in 5 minutes:

```bash
# 1. Clone and configure
git clone https://github.com/benchay1999/ai-group-chat-streamlit.git
cd ai-group-chat-streamlit
cp env.example .env
# Edit .env and add your OPENAI_API_KEY

# 2. Start backend
cd backend
pip install -r requirements.txt
uvicorn backend.main:app

# 3. Start frontend (new terminal)
cd frontend
npm install
npm run dev
```

Open http://localhost:5173 and start playing!

## Documentation

### For New Developers

Start with the comprehensive tutorial that covers everything you need to understand and work on this project:

**[TUTORIAL.md](TUTORIAL.md)** - Complete project tutorial with architecture, codebase walkthrough, and development guide

### Additional Documentation

- **[START_HERE.md](START_HERE.md)** - Quick setup guide with troubleshooting
- **[DEPLOYMENT_GUIDE_NGROK_NETLIFY.md](DEPLOYMENT_GUIDE_NGROK_NETLIFY.md)** - Step-by-step deployment with ngrok & Netlify
- **[ENVIRONMENT_REFERENCE.md](ENVIRONMENT_REFERENCE.md)** - Complete environment variable reference
- **[MTURK_SETUP.md](MTURK_SETUP.md)** - MTurk integration and payment system
- **[env.example](env.example)** - Configuration template
- **[markdowns/](markdowns/)** - Technical documentation (see [markdowns/README.md](markdowns/README.md) for index)

## How It Works

### Game Flow

1. **Lobby**: Players join a room (or create one with custom settings)
2. **Discussion Phase**: Everyone chats about a topic (default: 4 minutes)
3. **Voting Phase**: Vote based on game mode (default: 2 minutes)
   - **Single-human:** Vote for 1 player (most human-like)
   - **Multi-human:** Vote for N-1 players (all other humans)
4. **Results**:
   - **Single-human:** Elimination; continue if AI eliminated, game over if human eliminated
   - **Multi-human:** No elimination; winners determined by most votes, gems distributed
5. **Victory**:
   - **Single-human:** Human survives configured rounds (default: 1) or AIs eliminate human
   - **Multi-human:** Player(s) with most votes win and earn gems based on performance

### Architecture

```
Frontend (React)          Backend (FastAPI)           AI Layer
├── Lobby System          ├── REST API                ├── LangGraph
├── Real-time Chat        ├── WebSocket Server        ├── Multi-Agent System
├── Voting Interface      ├── Room Management         ├── OpenAI/Anthropic/Groq
└── Admin Dashboard       ├── Game Coordinator        └── Configurable Models
                          └── Database (SQLite/PostgreSQL)
```

**Tech Stack:**
- **Frontend**: React 18, Tailwind CSS, WebSocket
- **Backend**: FastAPI, LangGraph, SQLAlchemy
- **AI**: OpenAI GPT-4/GPT-4o-mini (default), Anthropic Claude, or Groq

## Configuration

Key settings in `.env` (see [env.example](env.example) for all options):

```env
# Required
OPENAI_API_KEY=sk-...

# Game Settings
NUM_AI_PLAYERS=4              # Number of AI opponents (4-8)
AI_MODEL_NAME=gpt-4o-mini     # AI model to use
DISCUSSION_TIME=240           # Discussion phase (seconds) - default 4 minutes
VOTING_TIME=120               # Voting phase (seconds) - default 2 minutes
ROUNDS_TO_WIN=1               # Rounds to survive (default 1)

# Database (SQLite for dev, PostgreSQL for production)
DATABASE_URL=sqlite+aiosqlite:///./backend/group_chat.db

# MTurk (optional - for payment system)
AWS_ACCESS_KEY_ID=...
AWS_SECRET_ACCESS_KEY=...
MTURK_ENVIRONMENT=sandbox
```

## Gem Economy & MTurk Payment

Players earn gems by playing games and can convert them to real USD via MTurk (1000 gems = $1 USD):

### Earning Gems

**Single-Human Games (1 human vs AI agents):**
- **All participants:** 50 gems
- Simple participation reward
- No stakes, no risk
- Perfect for building initial balance

**Multi-Human Games (2+ humans competing):**
- **Base Gems:** 100 gems (requires voting)
- **Stakes System:** Optional risk/reward mechanism
  - Choose stake percentage: 0%, 10%, 30%, 50%, or 100% of balance
  - Minimum 250 gems required to join
  - Winners: Stake refund + share of loser pool (based on voting accuracy)
  - Losers: Forfeit their stake
- **Voting Accuracy Matters:** Correctly identify all other humans to maximize winnings
- **Example:** In a 2-player game with 10% stakes (160 gems each), winner gets +420 gems total, loser gets +100 gems

### Voting Mechanics

**Single-Human Mode:**
- Vote for 1 player (who seems most human-like)
- AI agents participate in voting

**Multi-Human Mode:**
- Vote for N-1 players (all humans except yourself)
- Must identify all other human players correctly
- Voting accuracy determines share of loser stakes
- Formula: `accuracy = correct_votes / (num_humans - 1)`

### Cashing Out

- **Minimum Cashout:** $2.00 (2000 gems)
- **Method:** Worker-specific MTurk HITs with qualification system
- **Requirement:** MTurk Worker ID (add in profile)
- **Processing:** Auto-approved within 1 hour
- **Wallet Page:** View balance, request cashouts, track transaction history

See [MTURK_SETUP.md](MTURK_SETUP.md) for complete setup guide. For detailed gem mechanics and examples, visit `/gems-info` page in the application.

## Development

### Prerequisites

- Python 3.8+
- Node.js 18+
- OpenAI API key (or Anthropic/Groq API key)

### Project Structure

```
ai-group-chat-streamlit/
├── backend/
│   ├── main.py              # FastAPI server entry point
│   ├── services/
│   │   └── game_coordinator.py  # LangGraph game logic
│   ├── routers/             # API endpoints
│   ├── models/              # Database models
│   └── requirements.txt
├── frontend/
│   ├── src/
│   │   ├── pages/           # React pages
│   │   └── components/      # React components
│   └── package.json
├── markdowns/               # Detailed documentation
├── env.example              # Configuration template
└── README.md               # This file
```

### Running Tests

```bash
# Backend tests
cd backend
pytest

# Frontend tests
cd frontend
npm test
```

## Deployment

### Quick Deploy (Recommended for Beginners)

**ngrok + Netlify (Free, 30 minutes setup):**

Complete step-by-step guide for deploying with ngrok tunneling and Netlify hosting:

**[DEPLOYMENT_GUIDE_NGROK_NETLIFY.md](DEPLOYMENT_GUIDE_NGROK_NETLIFY.md)** - Beginner-friendly ngrok + Netlify deployment guide

### Alternative Deployment Options

For production or alternative setups, see:
- [markdowns/DEPLOYMENT.md](markdowns/DEPLOYMENT.md) - Multiple deployment strategies
- [markdowns/TUNNELING_OPTIONS.md](markdowns/TUNNELING_OPTIONS.md) - Alternative tunneling services

### Production Checklist

- [ ] Switch to PostgreSQL (see [markdowns/SQLITE_TO_POSTGRESQL.md](markdowns/SQLITE_TO_POSTGRESQL.md))
- [ ] Set strong JWT secrets in `.env`
- [ ] Configure CORS allowed origins
- [ ] Set `ENVIRONMENT=production`
- [ ] Enable HTTPS
- [ ] Set up database backups
- [ ] Configure monitoring/logging

## Contributing

Contributions welcome! See [markdowns/DEVELOPER_GUIDE.md](markdowns/DEVELOPER_GUIDE.md) for development guidelines.

## Support

- Check [START_HERE.md](START_HERE.md) for troubleshooting
- Review [markdowns/](markdowns/) for detailed technical docs
- Check backend logs: `uvicorn backend.main:app --reload`
- Check browser console for frontend errors

## License

[Add your license here]
