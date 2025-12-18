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
- **[MTURK_SETUP.md](MTURK_SETUP.md)** - MTurk integration and payment system
- **[env.example](env.example)** - Configuration options reference
- **[markdowns/](markdowns/)** - Technical documentation (see [markdowns/README.md](markdowns/README.md) for index)

## How It Works

### Game Flow

1. **Lobby**: Players join a room (or create one with custom settings)
2. **Discussion Phase**: Everyone chats about a topic (default: 3 minutes)
3. **Voting Phase**: Vote for who seems most AI-like (default: 1 minute)
4. **Elimination**: Player with most votes is eliminated
5. **Repeat**: Continue for multiple rounds (default: 3 rounds)
6. **Victory**: Humans win if they survive; AIs win if all humans are eliminated

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
DISCUSSION_TIME=180           # Discussion phase (seconds)
VOTING_TIME=60                # Voting phase (seconds)
ROUNDS_TO_WIN=3               # Rounds to survive

# Database (SQLite for dev, PostgreSQL for production)
DATABASE_URL=sqlite+aiosqlite:///./backend/group_chat.db

# MTurk (optional - for payment system)
AWS_ACCESS_KEY_ID=...
AWS_SECRET_ACCESS_KEY=...
MTURK_ENVIRONMENT=sandbox
```

## Gem Economy & MTurk Payment

Players earn gems by playing games (1000 gems = $1 USD):

- **Performance-Based**: Earn more for winning, voting correctly, active participation
- **Flexible Cashouts**: Redeem gems via MTurk when reaching minimum threshold ($2 default)
- **Automated HITs**: Worker-specific qualification-based HITs
- **Admin Dashboard**: Track earnings, manage cashouts, view analytics

See [MTURK_SETUP.md](MTURK_SETUP.md) for complete integration guide.

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

### Quick Deploy (Recommended)

**Local Backend + Cloud Frontend:**

1. Run backend locally with tunneling (ngrok or localhost.run)
2. Deploy frontend to Vercel/Netlify with backend URL

See [markdowns/DEPLOYMENT.md](markdowns/DEPLOYMENT.md) for detailed deployment guides.

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
