# Streamlit Frontend for Human Hunter

## Overview

This is a Streamlit-based frontend for the Human Hunter game, providing an alternative to the React WebSocket frontend. It uses HTTP polling to communicate with the FastAPI backend.

## Features

- ✅ Pure Python implementation
- ✅ Simple setup (no Node.js required)
- ✅ Auto-refresh polling (~1 second updates)
- ✅ Clean, intuitive UI
- ✅ Works alongside React frontend
- ✅ Easy to customize and extend

## Quick Start

### 1. Install Dependencies

```bash
pip install -r streamlit_requirements.txt
```

Or install individually:
```bash
pip install streamlit>=1.28.0 requests>=2.31.0
```

### 2. Start Backend

Make sure the FastAPI backend is running:
```bash
cd backend
export OPENAI_API_KEY='your-api-key-here'
uvicorn main:app --reload
```

### 3. Run Streamlit App

From the project root:
```bash
streamlit run streamlit_app.py
```

Your browser will automatically open at http://localhost:8501

## Configuration

### Backend URL

By default, the app connects to `http://localhost:8000`. To change this, set the `BACKEND_URL` environment variable:

```bash
export BACKEND_URL='http://your-backend-url:8000'
streamlit run streamlit_app.py
```

### Polling Interval

Edit `streamlit_app.py` to adjust the polling frequency:
```python
POLL_INTERVAL = 1.0  # seconds (default)
```

- Lower values = more responsive but higher CPU usage
- Higher values = less responsive but lower resource usage

### Room Code

Change the default room code:
```python
DEFAULT_ROOM = 'your-custom-room'
```

## How to Play

1. **Join or Create Room**
   - Enter a room code (or use default)
   - Choose your player name
   - Click "Join Game"

2. **Discussion Phase** (3 minutes)
   - Type messages in the chat input
   - Observe AI players responding
   - Try to blend in if you're the human!

3. **Voting Phase** (1 minute)
   - Click "Vote to Eliminate" button next to a player's name
   - Vote for who you think should be eliminated

4. **Elimination & New Round**
   - See who was eliminated
   - Game continues with new topic
   - Survive multiple rounds to win!

## Architecture

### Polling Strategy

The Streamlit frontend uses HTTP polling instead of WebSockets:

1. **Auto-refresh**: Page reruns every 1-2 seconds during active phases
2. **State synchronization**: Polls `/api/rooms/{room_code}/state` endpoint
3. **Actions**: POSTs to REST endpoints (message, vote, typing)
4. **Compatibility**: Works with same backend as React frontend

### Key Components

- `poll_game_state()`: Fetches current game state from backend
- `send_message()`: Sends chat messages
- `cast_vote()`: Submits votes
- `render_*()`: UI rendering functions
- `check_phase_change()`: Detects phase transitions

## Differences from React Frontend

| Aspect | React | Streamlit |
|--------|-------|-----------|
| **Updates** | Real-time (WebSocket) | 1-second polling |
| **Technology** | JavaScript/React | Python/Streamlit |
| **Setup** | Node.js + npm | Python + pip |
| **UI Framework** | Tailwind CSS | Streamlit components |
| **Typing Indicators** | Instant | Delayed |
| **Best For** | Production | Development/Demos |

## Customization

### Changing Theme

Edit `.streamlit/config.toml`:

```toml
[theme]
primaryColor = "#3b82f6"
backgroundColor = "#ffffff"
secondaryBackgroundColor = "#f3f4f6"
textColor = "#1f2937"
```

### Adding Features

The app is organized into functions:

- `render_header()`: Game status header
- `render_player_list()`: Sidebar player list
- `render_chat()`: Chat message display
- `render_message_input()`: Message input field

Simply modify these functions to customize the UI.

### Custom Styling

Use Streamlit's built-in styling:

```python
st.markdown("""
    <style>
    .stButton>button {
        background-color: #3b82f6;
        color: white;
    }
    </style>
""", unsafe_allow_html=True)
```

## Troubleshooting

### "Cannot connect to backend server"

- Ensure backend is running: `cd backend && uvicorn main:app --reload`
- Check backend URL in streamlit_app.py
- Verify port 8000 is not blocked

### "ModuleNotFoundError: No module named 'streamlit'"

```bash
pip install -r streamlit_requirements.txt
```

### Game not updating

- Check polling interval (may be too slow)
- Look for errors in terminal
- Refresh manually with 🔄 button

### Multiple players in same room

- Each user can join the same room code
- Only one "You" player expected per room (the human)
- Use different room codes for separate games

## Development

### Running in Development Mode

```bash
streamlit run streamlit_app.py --server.runOnSave=true
```

### Debug Mode

Add debug information:
```python
st.write("Debug:", st.session_state)
```

### Testing REST API

Test endpoints directly:
```python
import requests

# Get state
response = requests.get("http://localhost:8000/api/rooms/test-room/state")
print(response.json())

# Join room
response = requests.post(
    "http://localhost:8000/api/rooms/test-room/join",
    json={"player_id": "TestPlayer"}
)
print(response.json())
```

## Deployment

### Deploy to Streamlit Cloud

1. Push code to GitHub
2. Go to https://share.streamlit.io
3. Deploy `streamlit_app.py`
4. Set `BACKEND_URL` environment variable to your hosted backend

### Deploy Backend

Deploy FastAPI backend to:
- Render.com
- Railway.app
- Heroku
- AWS/GCP/Azure

Set environment variables:
- `OPENAI_API_KEY`
- `NUM_AI_PLAYERS` (optional)
- `DISCUSSION_TIME` (optional)
- `VOTING_TIME` (optional)

## Contributing

Contributions welcome! Areas for improvement:

- Enhanced UI/UX
- Additional visualizations
- Game statistics/analytics
- More configuration options
- Performance optimizations

## License

Same as main project.

## Support

See main project documentation:
- `README.md` - General overview
- `QUICK_START.md` - Quick start guide
- `DEVELOPER_GUIDE.md` - Development guide

