# Quick Start Guide - Human Hunter

Complete setup guide to get the Human Hunter AI social deduction game running on your local machine.

## Prerequisites

Before you begin, ensure you have:

- **Python 3.8+** (Python 3.11+ recommended)
- **Node.js 18+** and npm
- **OpenAI API Key** (get from https://platform.openai.com/api-keys)
- **Git** (for cloning the repository)

## Step 1: Clone and Configure

### Clone the Repository

```bash
git clone <repository-url>
cd ai-group-chat-streamlit
```

### Set Up Environment Variables

Copy the example environment file:

```bash
cp env.example .env
```

Edit `.env` and add your OpenAI API key:

```env
# Required: Your OpenAI API key
OPENAI_API_KEY=sk-your-api-key-here

# Database (SQLite for development)
DATABASE_URL=sqlite+aiosqlite:///./group_chat.db

# JWT Secrets (generate with: python -c "import secrets; print(secrets.token_urlsafe(32))")
JWT_SECRET_KEY=your-secret-key-here
JWT_COMPLETION_SECRET=your-completion-secret-here

# Optional: Game configuration
NUM_AI_PLAYERS=4
AI_MODEL_NAME=gpt-4o-mini
DISCUSSION_TIME=180
VOTING_TIME=60
ROUNDS_TO_WIN=3
```

**Generate secure JWT secrets:**

```bash
python -c "import secrets; print(secrets.token_urlsafe(32))"
python -c "import secrets; print(secrets.token_urlsafe(32))"
```

Copy the output and paste into your `.env` file for `JWT_SECRET_KEY` and `JWT_COMPLETION_SECRET`.

## Step 2: Backend Setup

### Install Backend Dependencies

```bash
cd backend
pip install -r requirements.txt
```

This installs:
- FastAPI (web framework)
- LangGraph (multi-agent orchestration)
- SQLAlchemy (database ORM)
- OpenAI/Anthropic/Groq clients
- And other required packages

### Initialize Database

The database will be automatically created when you start the backend. Tables are created on first run.

For production, see [MTURK_SETUP.md](MTURK_SETUP.md) for PostgreSQL migration.

### Start the Backend Server

```bash
# From the backend directory
python main.py

# Alternative: using uvicorn directly
uvicorn backend.main:app --reload --host 0.0.0.0 --port 8000
```

You should see:

```
🚀 Starting Backend Server
✅ Environment variables loaded
📡 Backend available at: http://localhost:8000
📊 API docs at: http://localhost:8000/docs
```

**Test it:** Open http://localhost:8000/health in your browser. You should see `{"status":"healthy"}`

## Step 3: Frontend Setup

Open a **new terminal window** (keep backend running).

### Install Frontend Dependencies

```bash
cd frontend
npm install
```

This installs:
- React 18
- React Router (navigation)
- Tailwind CSS (styling)
- Axios (HTTP client)
- WebSocket client
- UI components

### Configure Backend URL

The frontend automatically connects to `http://localhost:8000` in development.

To override, create `frontend/.env`:

```env
VITE_BACKEND_URL=http://localhost:8000
```

### Start the Frontend Development Server

```bash
npm run dev
```

You should see:

```
  VITE v5.x.x  ready in XXX ms

  ➜  Local:   http://localhost:5173/
  ➜  Network: use --host to expose
```

## Step 4: Play the Game!

1. **Open your browser** at http://localhost:5173

2. **Register/Login** (optional but recommended for tracking progress)
   - Click "Register" and create an account
   - Or skip and play as guest

3. **Create or Join a Room**
   - Click "Create Room" to start a new game
   - Or join an existing room from the lobby
   - Configure game settings (AI count, discussion time, etc.)

4. **Play!**
   - **Discussion Phase**: Chat with players (mix of humans and AI)
   - **Voting Phase**: Vote for who you think is AI (or human, if you're AI)
   - **Survive**: Make it through multiple rounds to win!

## Optional: MTurk Payment System

If you want to enable the gem economy and MTurk payment system:

1. **Set up AWS MTurk credentials** - See [MTURK_SETUP.md](MTURK_SETUP.md)
2. **Configure cashout settings** in `.env`
3. **Create admin user** for managing payments

This is optional and not required for basic gameplay.

## Game Configuration

Customize game settings in `.env`:

### AI Configuration

```env
# Number of AI players (4-8 recommended)
NUM_AI_PLAYERS=4

# AI model to use
AI_MODEL_NAME=gpt-4o-mini          # Fast and cheap (recommended)
# AI_MODEL_NAME=gpt-4o              # More capable but expensive
# AI_MODEL_NAME=claude-3-5-sonnet-20241022  # Anthropic Claude

# AI provider
AI_MODEL_PROVIDER=openai           # Options: openai, anthropic, groq
```

### Game Timing

```env
# Discussion phase duration (seconds)
DISCUSSION_TIME=180                # 3 minutes default

# Voting phase duration (seconds)
VOTING_TIME=60                     # 1 minute default

# Rounds to win
ROUNDS_TO_WIN=3                    # Human must survive 3 rounds
```

### Multiple API Keys (Optional)

For high-traffic deployments, distribute load across multiple API keys:

```env
# Comma-separated list of API keys
OPENAI_API_KEYS=sk-key1...,sk-key2...,sk-key3...
```

## Troubleshooting

### Backend Issues

**Problem: "ModuleNotFoundError"**
- Solution: Make sure you're in the `backend` directory and ran `pip install -r requirements.txt`

**Problem: "OPENAI_API_KEY not found"**
- Solution: Check your `.env` file is in the project root and contains `OPENAI_API_KEY=sk-...`

**Problem: "Database error"**
- Solution: Delete `group_chat.db` and restart the backend to recreate the database

**Problem: Port 8000 already in use**
- Solution: Kill the existing process or use a different port:
  ```bash
  uvicorn backend.main:app --reload --port 8001
  ```

### Frontend Issues

**Problem: "Cannot connect to backend"**
- Solution: Ensure backend is running on http://localhost:8000
- Check browser console for CORS errors
- Verify `VITE_BACKEND_URL` in frontend/.env (if set)

**Problem: "npm install" fails**
- Solution: Update Node.js to version 18+
  ```bash
  node --version  # Should be 18.x or higher
  ```

**Problem: WebSocket connection failed**
- Solution: Check that backend WebSocket endpoint is accessible at ws://localhost:8000/ws/game/{room_code}
- Verify no firewall is blocking WebSocket connections

### Game Issues

**Problem: AI players not responding**
- Solution: Check backend logs for API errors
- Verify OpenAI API key is valid and has credits
- Check rate limits on your API key

**Problem: "Room not found" error**
- Solution: Room codes expire after inactivity
- Create a new room if the old one expired

**Problem: Players stuck in waiting room**
- Solution: Refresh the page or create a new room
- Check backend logs for errors

## Development Tips

### Backend Development

- **Auto-reload**: The `--reload` flag automatically restarts the server when code changes
- **API Docs**: Visit http://localhost:8000/docs for interactive API documentation
- **Logs**: Backend logs show AI agent thinking, token usage, and costs

### Frontend Development

- **Hot Reload**: Vite automatically refreshes when you edit React components
- **React DevTools**: Install browser extension for debugging React components
- **Console**: Check browser console for errors and WebSocket messages

### Database Management

**View database contents:**

```bash
sqlite3 group_chat.db "SELECT * FROM users;"
sqlite3 group_chat.db "SELECT * FROM sessions;"
```

**Reset database:**

```bash
rm group_chat.db
# Restart backend to recreate
```

**Backup database:**

```bash
cp group_chat.db group_chat.db.backup
```

## Next Steps

### For Developers

- **Customize AI Personalities**: Edit `backend/services/game_coordinator.py`
- **Add New Features**: Check `markdowns/DEVELOPER_GUIDE.md`
- **Run Tests**: `pytest` in backend directory, `npm test` in frontend

### For Researchers

- **Set Up MTurk**: See [MTURK_SETUP.md](MTURK_SETUP.md) for payment system
- **Configure Gem Economy**: Edit gem rewards in backend config
- **Admin Dashboard**: Create admin user for analytics access

### For Production Deployment

- **Migrate to PostgreSQL**: See `markdowns/SQLITE_TO_POSTGRESQL.md`
- **Deploy Backend**: Railway, Render, or Heroku
- **Deploy Frontend**: Vercel, Netlify, or Cloudflare Pages
- **Security Checklist**: See `markdowns/PRODUCTION_DEPLOYMENT_SECURITY_CHECKLIST.md`

## Additional Documentation

- **[MTURK_SETUP.md](MTURK_SETUP.md)** - Complete MTurk integration guide
- **[env.example](env.example)** - All configuration options
- **[markdowns/SYSTEM_ARCHITECTURE.md](markdowns/SYSTEM_ARCHITECTURE.md)** - Technical architecture details
- **[markdowns/DEPLOYMENT.md](markdowns/DEPLOYMENT.md)** - Deployment guides
- **[markdowns/DEVELOPER_GUIDE.md](markdowns/DEVELOPER_GUIDE.md)** - Developer documentation

## Support

If you encounter issues:

1. Check this guide's troubleshooting section
2. Review backend logs for errors
3. Check browser console for frontend errors
4. Verify all prerequisites are installed
5. Ensure `.env` is configured correctly

Happy gaming! 🎮
