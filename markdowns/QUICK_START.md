# 🚀 Quick Start: LangGraph Multi-Agent Game

## ⚡ Fast Setup (5 minutes)

### 1. Install Backend Dependencies
```bash
cd backend
pip install -r requirements.txt
```

### 2. Set Your OpenAI API Key
```bash
export OPENAI_API_KEY='your-openai-api-key-here'
```

### 3. Start Backend Server
```bash
cd backend
uvicorn main:app --reload
```

You should see:
```
INFO:     Uvicorn running on http://127.0.0.1:8000
INFO:     Application startup complete.
```

### 4. Start Frontend (in new terminal)

**Option A: React Frontend (Real-time WebSocket)**
```bash
cd frontend
npm install  # First time only
npm run dev
```
if this does not work
```
curl -o- https://raw.githubusercontent.com/nvm-sh/nvm/v0.39.7/install.sh | bash
```

**Option B: Streamlit Frontend (Simpler, Python-based)**
```bash
# From project root
pip install -r streamlit_requirements.txt
streamlit run streamlit_app.py
```

### 5. Play!
- **React**: Open your browser to **http://localhost:5173**
- **Streamlit**: Browser opens automatically at **http://localhost:8501**

---

## 🎮 Quick Configuration Changes

### Change Number of AI Players (Default: 4)
```bash
# Try with 6 AI players
export NUM_AI_PLAYERS=6
uvicorn main:app --reload
```

### Use Different AI Model
```bash
# Use GPT-5 instead of GPT-4o-mini
export AI_MODEL_NAME=gpt-5
uvicorn main:app --reload
```

### Adjust Game Speed
```bash
# Faster rounds: 2 min discussion, 30 sec voting
export DISCUSSION_TIME=120
export VOTING_TIME=30
uvicorn main:app --reload
```

---

## 📁 What Changed?

| File | Status | Description |
|------|--------|-------------|
| `backend/config.py` | ✅ NEW | Configuration system |
| `backend/langgraph_state.py` | ✅ NEW | State schema |
| `backend/langgraph_game.py` | ✅ NEW | LangGraph implementation |
| `backend/main.py` | ✅ UPDATED | FastAPI + LangGraph integration |
| `backend/requirements.txt` | ✅ UPDATED | Added LangGraph dependencies |
| `backend/ai.py` | 📦 ARCHIVED | → `ai_legacy.py` |
| `backend/game.py` | 📦 ARCHIVED | → `game_legacy.py` |
| `frontend/` | ✅ NO CHANGES | Works as-is! |

---

## 🎯 Key Features

✅ **Configurable AI Count**: 2-10+ AI players  
✅ **Multi-Model Support**: OpenAI, Anthropic, Groq ready  
✅ **Advanced State Management**: Full game history tracked  
✅ **Modular Architecture**: Easy to extend  
✅ **100% Frontend Compatible**: No UI changes needed  

---

## 🖥️ Frontend Comparison

| Feature | React Frontend | Streamlit Frontend |
|---------|---------------|-------------------|
| **Technology** | React + Vite + Tailwind CSS | Python + Streamlit |
| **Communication** | WebSocket (real-time) | HTTP Polling (~1s updates) |
| **Setup** | Requires Node.js 18+ | Python only |
| **UI Style** | Modern, responsive, custom | Clean, Python-native |
| **Updates** | Instant | 1-2 second delay |
| **Typing Indicators** | Real-time | Delayed |
| **Best For** | Production, best UX | Development, quick demos, Python devs |

Both frontends work with the same backend simultaneously!

---

## 📖 Documentation

| Document | Purpose |
|----------|---------|
| **QUICK_START.md** (this file) | Get running in 5 minutes |
| **LANGGRAPH_MIGRATION.md** | Complete migration guide |
| **DEVELOPER_GUIDE.md** | Developer documentation |
| **IMPLEMENTATION_SUMMARY.md** | Technical implementation details |
| **README.md** | General project overview |

---

## 🔧 Troubleshooting

### "ModuleNotFoundError: No module named 'langgraph'"
```bash
pip install -r requirements.txt
```

### "API key not found"
```bash
export OPENAI_API_KEY='your-key-here'
```

### Frontend won't connect
- Ensure backend is running on port 8000
- Check browser console for errors
- Verify CORS settings in `main.py`

### AI not responding
- Check API key is valid
- Look at backend terminal for errors
- Verify OpenAI API has credits

### Streamlit won't start
```bash
pip install -r streamlit_requirements.txt
```

### Streamlit connection errors
- Ensure backend is running on port 8000 first
- Check the backend URL in streamlit_app.py (default: http://localhost:8000)
- Look for error messages in the Streamlit UI

---

## 🧪 Quick Test

1. Start game in browser
2. Type a message in chat
3. Watch AI agents respond (2-10 seconds)
4. After 3 minutes, voting starts automatically
5. Click a player name to vote
6. Watch elimination and new round

**Expected behavior**: 
- 4-5 players (1 human + 4 AI by default)
- AI agents chat naturally
- Voting happens after discussion
- Game continues until winner

---

## 🌟 Try These Configurations

### Maximum Chaos (8 AI Players)
```bash
export NUM_AI_PLAYERS=8
uvicorn main:app --reload
```

### Speed Run (Quick rounds)
```bash
export DISCUSSION_TIME=60
export VOTING_TIME=20
uvicorn main:app --reload
```

### Premium Model (GPT-5)
```bash
export AI_MODEL_NAME=gpt-5
uvicorn main:app --reload
```

---

## 💡 Next Steps

1. ✅ Get the game running (above)
2. 📖 Read **LANGGRAPH_MIGRATION.md** to understand architecture
3. 🛠️ Read **DEVELOPER_GUIDE.md** to customize
4. 🎨 Modify `config.py` to add personalities or topics
5. 🚀 Deploy to production (see README.md)

---

## 🎊 You're Ready!

The game is now powered by LangGraph's advanced multi-agent system. Enjoy playing and extending it!

**Questions?** Check the documentation files or review the code comments.

