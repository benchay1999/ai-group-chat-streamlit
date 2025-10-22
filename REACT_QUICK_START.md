# React Frontend - Quick Start Guide

This guide will help you get started with the new React-based matching room system for Group Chat.

## Overview

The React frontend provides a modern, real-time interface for the Group Chat game with these key features:

- **Browse Rooms**: View all available game rooms in a beautiful grid layout
- **Create Rooms**: Configure custom rooms with AI and human player counts
- **Join Rooms**: Join any available room with auto-assigned player numbers
- **Real-time Gameplay**: WebSocket-powered chat, voting, and game updates
- **Modern UI**: Gradient backgrounds, smooth animations, and responsive design

## Getting Started

### 1. Start the Backend

First, make sure the backend server is running:

```bash
# From the project root
cd backend
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

You should see:
```
INFO:     Uvicorn running on http://0.0.0.0:8000
```

### 2. Configure the Frontend

Create a `.env` file in the `frontend/` directory:

```bash
cd frontend
echo "VITE_BACKEND_URL=http://localhost:8000" > .env
```

### 3. Install Dependencies (if not done)

```bash
npm install
```

### 4. Start the React App

```bash
npm run dev
```

The frontend will start at `http://localhost:5173`.

Open your browser and navigate to this URL.

## Using the Application

### Lobby Page

When you first open the app, you'll see the **Lobby Page**:

1. **Server Status**: Top right shows if the backend is online (green = online)
2. **Available Rooms**: Grid of rooms waiting for players
3. **Create Room Button**: Top right to create a new room
4. **Refresh Button**: Manually refresh room list (auto-refreshes every 5 seconds)

### Creating a Room

1. Click **"+ Create Room"** button
2. Configure your room:
   - **Max Humans**: Use slider to set 1-4 human players (default: 1)
   - **Total Players**: Use slider to set total players including AI (default: 5)
   - Preview shows AI count automatically
3. Click **"Create Room"**
4. You'll be taken to the **Waiting Page** automatically

### Joining a Room

1. On the Lobby, click **"Join Room"** on any available room
2. Review room details on the **Join Page**
3. Click **"Join Game"**
4. You'll receive an auto-assigned player number (e.g., "Player 42")
5. Navigate to **Waiting Page** if room isn't full, or **Game Page** if ready

### Waiting for Players

On the **Waiting Page**, you'll see:

- **Player Counter**: Large display showing X / Y players
- **Progress Bar**: Visual indicator of room capacity
- **Room Code**: Share this code with friends (they can join from lobby)
- **Joined Players List**: See who's already in the room
- **Auto-Navigation**: Game starts automatically when room is full

**Leave Room**: Click the red "Leave Room" button at any time

### Playing the Game

Once the game starts, you'll see the **Game Page**:

#### Header
- **Room Code**: Current room identifier
- **Round**: Current round number
- **Phase**: Discussion, Voting, or Game Over
- **Timer**: Countdown for current phase (green → yellow → red as time runs out)
- **Connection Status**: WebSocket connection indicator
- **Topic**: Conversation topic for the round

#### Left Sidebar - Players
- **Player List**: All players with status indicators
  - Green dot = Active
  - Gray dot = Eliminated
  - Blue highlight = You
  - "✓ Voted" badge = Player has voted
- **Vote Buttons**: Appear during Voting phase
- **Leave Room**: Red button at bottom to exit

#### Main Area - Chat
- **Chat Window**: See all messages
  - Your messages appear on the right (blue/purple gradient)
  - Others' messages appear on the left (white)
  - Typing indicators show who's typing
- **Message Input**: Type and press Enter to send
  - Disabled during Voting phase
  - Shows placeholder text based on current phase

### Game Phases

#### 1. Discussion Phase
- **Duration**: 3 minutes (180 seconds)
- **Action**: Chat with other players about the topic
- **Goal**: 
  - **If Human**: Try to blend in with AI players
  - **If AI**: Try to identify the human player
- **Tips**: Watch for unusual patterns, typos, or off-topic responses

#### 2. Voting Phase
- **Duration**: 1 minute (60 seconds)
- **Action**: Vote to eliminate a player you suspect
- **How**: Click "Vote to Eliminate" button next to a player's name
- **Rules**: 
  - One vote per player
  - Cannot vote for yourself
  - Cannot change vote once cast
- **Visual Feedback**: "✓ Voted" appears next to players who've voted

#### 3. Game Over
- **Display**: Modal overlay with results
- **Shows**:
  - Winner (Humans or AIs)
  - Suspected player and their role
  - Vote counts for each player
- **Action**: Click "Back to Lobby" to return and start a new game

## Features in Detail

### Real-time Updates via WebSocket

The game uses WebSocket for instant updates:
- Chat messages appear immediately
- Typing indicators show in real-time
- Phase changes notify all players simultaneously
- Vote status updates as players vote
- Connection status shown in header

### Responsive Design

The app works on:
- Desktop (optimized for 1920x1080)
- Tablets (iPad, Android tablets)
- Mobile phones (some features adapted)

### Toast Notifications

Small popup notifications appear for:
- Room created
- Successfully joined
- Vote cast
- Phase changes
- Errors and warnings

## Testing Locally

### Single Player (with AI)

1. Create a room with Max Humans = 1, Total Players = 5
2. Join the room
3. Game starts immediately with 4 AI players
4. Play against the AI

### Multiple Players

1. **Player 1**: Create a room with Max Humans = 2, Total Players = 5
2. **Player 2**: Open a new browser window/tab (or incognito mode)
3. **Player 2**: Join the room from the lobby
4. Game starts automatically with 3 AI players

### Testing on Same Computer

Use multiple browser windows or tabs:
- Regular window + Incognito window
- Chrome + Firefox
- Different browser profiles

## Keyboard Shortcuts

- **Enter**: Send message (when typing)
- **Shift + Enter**: Not supported (single-line input)

## Troubleshooting

### "Server Offline" in Lobby

**Problem**: Red dot showing "Server Offline"

**Solution**:
1. Check backend is running: `curl http://localhost:8000/health`
2. Verify `.env` has correct URL
3. Check terminal for backend errors

### WebSocket "Disconnected"

**Problem**: Connection status shows red "Disconnected"

**Solution**:
1. Refresh the page
2. Check browser console for WebSocket errors
3. Verify backend is running
4. Check firewall/antivirus blocking WebSocket connections

### Room Not Appearing in Lobby

**Problem**: Created room doesn't show up

**Solution**:
1. Click "Refresh" button
2. Wait 5 seconds for auto-refresh
3. Check room wasn't immediately filled (status changed to 'in_progress')

### Can't Send Messages

**Problem**: Message input is disabled

**Solution**:
- Check you're in Discussion phase (not Voting)
- Verify WebSocket is connected (green dot in header)
- Try refreshing the page

### Game Didn't Start

**Problem**: Stuck on waiting page even though room is full

**Solution**:
1. Check browser console for errors
2. Verify all players actually joined (check player list)
3. Wait 2 seconds for polling to detect status change
4. Try leaving and rejoining

## Advanced Configuration

### Change Backend URL for Production

Edit `.env`:
```
VITE_BACKEND_URL=https://your-production-backend.com
```

Rebuild:
```bash
npm run build
```

### Modify Room Settings

Edit `frontend/src/components/CreateRoomModal.jsx`:

```jsx
const [maxHumans, setMaxHumans] = useState(2);  // Change default
const [totalPlayers, setTotalPlayers] = useState(8);  // Change default
```

### Adjust Polling Interval

Edit `frontend/src/hooks/useRoomPolling.js`:

```js
const DEFAULT_INTERVAL = 1000; // Change from 2000 to 1000 (1 second)
```

### Customize Colors

Edit `frontend/tailwind.config.js` or component files:

```jsx
// Change gradient colors
className="bg-gradient-to-r from-green-600 to-teal-600"
```

## Comparison with Streamlit Frontend

| Feature | React | Streamlit |
|---------|-------|-----------|
| **Speed** | Fast, instant updates | Slower, polling-based |
| **UI** | Modern, gradient design | Simple, functional |
| **Real-time** | WebSocket native | WebSocket bridge via JS |
| **Mobile** | Fully responsive | Desktop-optimized |
| **Development** | JavaScript/React | Python only |
| **Deployment** | Static hosting (Vercel) | Streamlit Cloud |

## Next Steps

1. **Play a game**: Create a room and test all features
2. **Invite friends**: Share room codes to play together
3. **Customize**: Modify colors, layouts, or features
4. **Deploy**: Host on Vercel, Netlify, or your own server

## Support

If you encounter issues:

1. Check browser console (F12 → Console)
2. Check backend terminal for errors
3. Review network tab (F12 → Network)
4. Verify all services are running

For WebSocket issues, look for:
- Red WebSocket errors in console
- Failed WS connection attempts
- CORS errors

## FAQ

**Q: Can I use this with the Streamlit frontend simultaneously?**
A: Yes! Both frontends connect to the same backend and can coexist.

**Q: Do I need to stop the Streamlit app?**
A: No, they run on different ports (React: 5173, Streamlit: 8501)

**Q: Can players using React play with players using Streamlit?**
A: Yes, as long as they're in the same room, they can see each other's messages and votes.

**Q: How do I deploy this to production?**
A: See `frontend/README.md` for deployment guides (Vercel, Netlify, Docker).

**Q: Can I change the player number format?**
A: The backend assigns numbers automatically. You can modify the backend logic in `main.py` if needed.

Enjoy playing Group Chat with the new React frontend! 🎮

