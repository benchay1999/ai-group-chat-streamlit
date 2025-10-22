# Group Chat - React Frontend

A modern, real-time frontend for the Group Chat game with matching room system.

## Features

- **Lobby System**: Browse and join available game rooms
- **Room Creation**: Create custom rooms with configurable settings
- **Waiting Room**: Real-time player counter with auto-start
- **Game Interface**: WebSocket-powered real-time chat and voting
- **Modern UI**: Gradient backgrounds, smooth animations, responsive design

## Tech Stack

- React 18
- React Router 6 (multi-page navigation)
- Tailwind CSS (styling)
- Axios (REST API)
- WebSocket (real-time updates)
- React Hot Toast (notifications)

## Setup

### 1. Install Dependencies

```bash
cd frontend
npm install
```

### 2. Configure Backend URL

Create a `.env` file in the `frontend/` directory:

```env
VITE_BACKEND_URL=http://localhost:8000
```

For production, set to your deployed backend URL (e.g., `https://your-backend.com`).

### 3. Start Development Server

```bash
npm run dev
```

The app will be available at `http://localhost:5173`.

## Architecture

### Pages

1. **LobbyPage** (`/`) - Browse and create rooms
   - Grid view of available rooms
   - Auto-refresh every 5 seconds
   - Create room modal
   - Pagination

2. **JoinPage** (`/join`) - Join selected room
   - Room information display
   - Auto-assigned player numbers
   - Direct join without name input

3. **WaitingPage** (`/waiting`) - Wait for players
   - Real-time player counter
   - Room info and player list
   - Polls backend every 2 seconds
   - Auto-navigates when game starts

4. **GamePage** (`/game`) - Main game interface
   - WebSocket connection for real-time updates
   - Chat with typing indicators
   - Voting interface
   - Player list with status
   - Phase timer
   - Game over screen

### Communication Strategy

- **REST API**: Room management (create, list, join, leave)
- **WebSocket**: Real-time game updates (chat, voting, phase changes)
- **Polling**: Waiting room status (2-second interval)

### API Endpoints Used

```javascript
// Room Management
POST /api/rooms/create
GET  /api/rooms/list?page={page}&per_page={per_page}
GET  /api/rooms/{code}/info
POST /api/rooms/{code}/join
POST /api/rooms/{code}/leave

// Game Actions (REST)
POST /api/rooms/{code}/message
POST /api/rooms/{code}/vote

// Real-time (WebSocket)
WS   /ws/{code}/{player_id}
```

### WebSocket Events

**Incoming:**
- `message` - Chat message
- `typing` - Typing indicator
- `phase` - Phase change
- `topic` - Game topic
- `player_list` - Player list update
- `voted` - Player voted
- `voting_result` - Voting results
- `game_over` - Game ended
- `room_terminated` - Room closed

**Outgoing:**
- Messages sent via REST API (`POST /api/rooms/{code}/message`)
- Votes sent via REST API (`POST /api/rooms/{code}/vote`)

## Building for Production

```bash
npm run build
```

The build output will be in the `dist/` directory.

## Deployment

### Vercel

1. Install Vercel CLI: `npm i -g vercel`
2. Run: `vercel`
3. Set environment variable: `VITE_BACKEND_URL=https://your-backend.com`

### Netlify

1. Build command: `npm run build`
2. Publish directory: `dist`
3. Environment variable: `VITE_BACKEND_URL=https://your-backend.com`

### Docker

```dockerfile
FROM node:18-alpine
WORKDIR /app
COPY package*.json ./
RUN npm install
COPY . .
RUN npm run build
EXPOSE 5173
CMD ["npm", "run", "preview"]
```

## Development Tips

### Hot Reload

The development server supports hot module replacement (HMR). Changes to components will update instantly.

### Backend Connection

Make sure your backend is running on the URL specified in `.env`:

```bash
# In backend directory
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

### Debugging WebSocket

Open browser console to see WebSocket connection logs:
- 🔌 Connection events
- 📥 Incoming messages
- 📤 Outgoing messages

### Testing

1. Open multiple browser windows/tabs
2. Create a room in one window
3. Join the room from other windows
4. Test chat, voting, and game flow

## Customization

### Colors

Edit `tailwind.config.js` to customize the color scheme:

```js
module.exports = {
  theme: {
    extend: {
      colors: {
        primary: '#your-color',
      },
    },
  },
}
```

### Animations

Add custom animations in `src/index.css`.

### Room Settings

Default room settings can be modified in `CreateRoomModal.jsx`:
- Max humans: 1-4 (default: 1)
- Total players: max_humans to 12 (default: 5)

## Troubleshooting

### Backend Connection Failed

- Check backend URL in `.env`
- Verify backend is running: `curl http://localhost:8000/health`
- Check CORS settings in backend

### WebSocket Not Connecting

- Check WebSocket URL format (ws:// for http, wss:// for https)
- Verify firewall/proxy settings
- Check browser console for errors

### Rooms Not Loading

- Check backend `/api/rooms/list` endpoint
- Verify backend database/in-memory storage is working
- Check network tab in browser developer tools

## License

MIT

