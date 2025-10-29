# Player Identification Feature Implementation

## Overview
This feature allows users and admins to see which player each participant was in a game session, solving the problem of identifying who played which role in multi-player sessions.

## What Was Implemented

### 1. Backend: Database Changes

#### New Table: `session_players`
Tracks the mapping between users and their player IDs in each session.

**Fields**:
- `id` (UUID) - Primary key
- `session_id` (UUID) - Foreign key to sessions table
- `user_id` (UUID, nullable) - Foreign key to users table (null for non-authenticated players)
- `player_id` (String) - Player identifier (e.g., "Player 3", "You")
- `role` (String) - "human" or "ai"

**Indexes**:
- `idx_session_player` - On (session_id, player_id)
- `idx_user_sessions` - On (user_id, session_id)

### 2. Backend: Room State Tracking

#### Added `player_user_map` to Room Data Structure
Each room now includes a dictionary that maps player IDs to user IDs:
```python
rooms[room_code] = {
    ...
    'player_user_map': {}  # Maps player_id -> user_id
}
```

### 3. Backend: WebSocket Authentication

#### Updated WebSocket Endpoint
The WebSocket endpoint now accepts an optional `token` query parameter:
```
ws://backend/ws/{room_code}/{player_id}?token={jwt_token}
```

When a user connects:
1. Extracts JWT token from query params
2. Decodes token to get user UUID
3. Stores mapping in `rooms[room_code]['player_user_map']`
4. Prints confirmation: `👤 Authenticated user {user.user_id} as {player_id}`

### 4. Backend: Session Saving

#### Updated `save_session_stats`
When saving a completed session:
1. Retrieves `player_user_map` from room data
2. Creates `SessionPlayer` records for each player
3. Links authenticated users to their player IDs
4. Stores all player mappings in database

### 5. Backend: Session Detail API

#### Enhanced `/api/sessions/{session_id}` Response
Now returns:
```json
{
  ...
  "player_mappings": [
    {
      "player_id": "Player 3",
      "role": "human",
      "user_id": "uuid-here",
      "user_name": "john_doe"
    },
    ...
  ],
  "current_user_player_id": "Player 3"  // Which player the requesting user was
}
```

### 6. Frontend: WebSocket Token Passing

#### Updated `getWebSocketURL`
Automatically includes auth token if user is logged in:
```javascript
const token = localStorage.getItem('token');
const queryParam = token ? `?token=${token}` : '';
return `${wsProtocol}://${baseURL}/ws/${roomCode}/${playerId}${queryParam}`;
```

### 7. Frontend: Session Detail Display

#### For Regular Users
Shows a prominent blue card:
```
👤 You were Player 3
This was your player identity in this session
```

#### For Admins
Shows a "Player Identities" card with all mappings:
```
👤 Human  Player 3    User: john_doe
🤖 AI     Player 7    Not logged in
👤 Human  Player 1    User: jane_smith
...
```

## User Experience

### For Regular Users Viewing Their Sessions
1. Navigate to Dashboard → Sessions
2. Click on a session
3. See **"You were Player X"** card at the top
4. Easily identify their messages in the chat history
5. Understand their role in voting results

### For Admins Viewing Any Session
1. Navigate to Admin Panel → Sessions or individual session
2. See **"Player Identities"** card showing:
   - Each player ID (Player 1, Player 2, etc.)
   - Their role (Human/AI) with color coding
   - Associated username (if logged in)
   - "Not logged in" for anonymous players
3. Can cross-reference players with usernames

## Database Migration

Run the migration to create the new table:
```bash
cd backend
python -m alembic upgrade head
```

This runs migration `003_add_session_players.py` which creates the `session_players` table.

## Benefits

1. **User Clarity**: Users always know which player they were
2. **Admin Oversight**: Admins can track who participated in each session
3. **Support Queries**: Easily identify users when investigating issues
4. **Data Analysis**: Link user accounts to game behavior
5. **Accountability**: Track participation for rewards/moderation

## Technical Details

### Authentication Flow
1. User logs in → receives JWT token → stored in localStorage
2. User joins game → WebSocket connects with token
3. Backend decodes token → maps player_id to user_id
4. Session ends → mappings saved to database
5. User views session → sees their player identity

### Non-Authenticated Players
- Can still play games without logging in
- Their `SessionPlayer` records have `user_id = NULL`
- Shown as "Not logged in" in admin view
- No "You were..." card shown (since not logged in for viewing)

### Privacy Considerations
- Regular users only see "You were Player X" (their own identity)
- Other players' identities hidden from regular users
- Only admins see full player-user mappings
- Non-logged-in players remain anonymous

## Future Enhancements

Potential additions:
1. **Bulk Analysis**: Export player participation data
2. **Player Stats**: Track performance per user across sessions
3. **Moderation Tools**: Flag/ban users based on session behavior
4. **Team Matching**: Group players by historical performance
5. **Social Features**: "You played with [username] in this session"

## Testing

### Test Scenario 1: Authenticated User
1. Login as user
2. Join a game
3. Complete the game
4. View session details
5. ✅ Should see "You were Player X"

### Test Scenario 2: Admin View
1. Login as admin
2. Navigate to any session
3. ✅ Should see player mappings with usernames

### Test Scenario 3: Anonymous Player
1. Join game without logging in
2. Complete game
3. ✅ Session should save with player record (user_id = NULL)
4. Admin views session
5. ✅ Shows player as "Not logged in"

### Test Scenario 4: Mixed Session
1. One logged-in user + anonymous player
2. Complete game
3. Logged-in user views session
4. ✅ Sees "You were Player X"
5. Admin views session
6. ✅ Sees one mapped user + one "Not logged in"

## Migration Path

### For Existing Sessions
Old sessions (before this feature) will:
- Have no `SessionPlayer` records
- Show no "You were..." card
- Show no player mappings (even for admins)
- Continue to display chat history and votes normally

### For New Sessions
All new sessions will:
- Automatically track player-user mappings
- Display player identification for logged-in users
- Show full mappings to admins
- Work seamlessly with anonymous players

## Files Modified

### Backend
- `backend/database.py` - Added `SessionPlayer` model
- `backend/main.py` - Updated WebSocket, session saving, session detail endpoint
- `backend/alembic/versions/003_add_session_players.py` - New migration

### Frontend
- `frontend/src/services/api.js` - Updated WebSocket URL with token
- `frontend/src/pages/SessionDetailPage.jsx` - Added player identification display

## Console Messages

When working correctly, you'll see:
```
🔌 WebSocket accepted for player Player 3 in room ABC123
👤 Authenticated user john_doe as Player 3
✅ Connection added. Total connections: 1
👤 Stored mapping: Player 3 -> user uuid-here
```

When saving session:
```
📊 Total token usage: 1250 input, 875 output
💰 Total cost: $0.004250 (model: gpt-4o-mini)
✅ Session saved to database with ID: session-uuid
```

## Success! ✅

Users now know exactly which player they were, and admins have full visibility into session participation!

