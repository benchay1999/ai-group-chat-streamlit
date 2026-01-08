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

```bash
cd frontend
npm install  # First time only
npm run dev
```

**If Node.js is not installed:**
```bash
# Install nvm (Node Version Manager)
curl -o- https://raw.githubusercontent.com/nvm-sh/nvm/v0.39.7/install.sh | bash

# Install Node.js 18+
nvm install 18
nvm use 18
```

### 5. Play!

Open your browser to **http://localhost:5173**

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
# Use GPT-4o instead of gpt-5.1-nano (default)
export AI_MODEL_NAME=gpt-4o
uvicorn main:app --reload
```

### Adjust Game Speed
```bash
# Faster rounds: 2 min discussion, 45 sec voting (from default 4 min / 2 min)
export DISCUSSION_TIME=120
export VOTING_TIME=45
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
| `frontend/` | ✅ REACT | React 18 + Vite + Tailwind CSS |

---

## 🎯 Key Features

✅ **Configurable AI Count**: 2-10+ AI players  
✅ **Multi-Model Support**: OpenAI, Anthropic, Groq ready  
✅ **Advanced State Management**: Full game history tracked  
✅ **Modular Architecture**: Easy to extend  
✅ **100% Frontend Compatible**: No UI changes needed  

---

## 🖥️ Frontend Technology

**React 18 + Vite:**
- Modern, responsive UI with Tailwind CSS
- Real-time WebSocket communication
- Instant updates (<100ms latency)
- Smooth page transitions with React Router
- Mobile-friendly design
- Requires Node.js 18+

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

### React build errors
```bash
cd frontend
rm -rf node_modules package-lock.json
npm install
```

### React won't connect to backend
- Ensure backend is running on port 8000
- Check `VITE_BACKEND_URL` in `frontend/.env` (if set)
- Check browser DevTools → Console for errors
- Verify CORS settings allow localhost:5173

---

## 🧪 Quick Test

1. Start game in browser (http://localhost:5173)
2. Create or join a room
3. Type a message in chat
4. Watch AI agents respond (with realistic delays)
5. After discussion phase (default 4 minutes), voting starts automatically
6. Cast your vote(s) (1 player for single-human, N-1 for multi-human)
7. Watch results and gem rewards

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

### Premium Model (GPT-4o)
```bash
export AI_MODEL_NAME=gpt-4o  # More expensive but higher quality
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

