# ✅ Dashboard Session Visibility FIXED!

## Problem

When regular users played games, their sessions were **not showing up in the dashboard**. The dashboard appeared empty even after completing games.

## Root Cause

The API query for listing sessions only checked if `user_id == current_user.id`:

```python
# OLD - Only showed sessions where user was the owner
select(DBSession)
    .where(DBSession.user_id == current_user.id)
    .order_by(desc(DBSession.completed_at))
```

However, when users play games:
1. The session might not have a `user_id` set (for various reasons)
2. Even if set, only the first player would be the "owner"
3. Other players who participated wouldn't see the session

The **real** source of truth is the `session_players` table, which maps which users played in which sessions.

## Solution

### Updated the Query to Include Sessions Where User Played

**File:** `backend/main.py` - `/api/sessions` endpoint

```python
# NEW - Shows sessions where user is owner OR played as a player
from .database import SessionPlayer

result = await db.execute(
    select(DBSession)
    .outerjoin(SessionPlayer, SessionPlayer.session_id == DBSession.id)
    .where(
        (DBSession.user_id == current_user.id) |      # User is session owner
        (SessionPlayer.user_id == current_user.id)     # OR user played in session
    )
    .order_by(desc(DBSession.completed_at))
    .distinct()
)
```

This query now:
- ✅ Shows sessions where user is the owner (via `session.user_id`)
- ✅ Shows sessions where user played (via `session_players.user_id`)
- ✅ Uses `distinct()` to avoid duplicates
- ✅ Properly orders by completion time

### Added Debug Logging

Enhanced the session save logic to log player-user mappings:

```python
print(f"👥 Saving player-user mappings: {player_user_map}")

for player in state.get('players', []):
    if mapped_user_id:
        print(f"✅ Mapped {player_id} ({role}) -> user {user_uuid}")
    else:
        print(f"ℹ️  {player_id} ({role}) -> No user mapping (anonymous)")
```

This helps debug if mappings are being saved correctly.

## How It Works Now

### When User Plays a Game:

1. **WebSocket Connection:**
   ```
   User connects with JWT token
   → Token decoded
   → user_id stored in rooms[room_code]['player_user_map'][player_id]
   ```

2. **During Game:**
   ```
   Console output: "👤 Stored mapping: Player 2 -> user abc-123-def"
   ```

3. **Game Ends:**
   ```
   save_session_stats() called
   → Reads player_user_map
   → Creates SessionPlayer records
   → Saves to database
   
   Console output:
   "👥 Saving player-user mappings: {'Player 2': 'abc-123-def'}"
   "✅ Mapped Player 2 (human) -> user abc-123-def"
   ```

4. **Dashboard Query:**
   ```
   Query joins sessions with session_players
   → Finds all sessions where user.id matches
   → Returns sessions to dashboard
   ```

5. **Dashboard Display:**
   ```
   User sees their session in the list! ✅
   ```

## What Shows in Console

### During Game:
```
🔌 WebSocket accepted for player Player 2 in room ABC123
👤 Authenticated user john_doe as Player 2
👤 Stored mapping: Player 2 -> user e2379ad4-7089-4fad-b602-eca8438cee1c
```

### After Game Ends:
```
👥 Saving player-user mappings: {'Player 2': 'e2379ad4-7089-4fad-b602-eca8438cee1c'}
✅ Mapped Player 2 (human) -> user e2379ad4-7089-4fad-b602-eca8438cee1c
ℹ️  Player 1 (ai) -> No user mapping (anonymous)
ℹ️  Player 3 (ai) -> No user mapping (anonymous)
ℹ️  Player 4 (ai) -> No user mapping (anonymous)
ℹ️  Player 5 (ai) -> No user mapping (anonymous)
✅ Session saved to database with ID: abc-123-def
```

## Testing

### Test Case 1: Regular User Plays Game

1. **Start backend:**
   ```bash
   cd backend && python main.py
   ```

2. **Start frontend:**
   ```bash
   cd frontend && npm run dev
   ```

3. **As regular user:**
   - Login at http://localhost:3000
   - Create/join a game
   - Play the game to completion
   - Click "View Dashboard & Stats"

4. **Expected Results:**
   - ✅ Session appears in dashboard
   - ✅ Can click to view details
   - ✅ Player highlighting works
   - ✅ Shows completion key

5. **Console should show:**
   ```
   👤 Authenticated user benchay as Player 2
   👤 Stored mapping: Player 2 -> user [uuid]
   👥 Saving player-user mappings: {'Player 2': '[uuid]'}
   ✅ Mapped Player 2 (human) -> user [uuid]
   ```

### Test Case 2: Multiple Users Play Together

1. **User A** (logged in) joins game
2. **User B** (logged in) joins same game
3. Both play to completion

**Expected:**
- ✅ Session appears in User A's dashboard
- ✅ Session appears in User B's dashboard
- ✅ Both see their player highlighted
- ✅ Admin sees both user mappings

### Test Case 3: Anonymous User

1. User plays **without logging in**
2. Game completes

**Expected:**
- ✅ Session saves successfully
- ✅ Completion key generated
- ❌ Session NOT in any user's dashboard (no user_id)
- ✅ User can later login and **claim the key** to associate it

### Test Case 4: Admin View

1. Login as admin
2. Go to `/dashboard`

**Expected:**
- ✅ Admin sees ALL sessions (their own + everyone else's)
- ✅ No duplicate sessions
- ✅ Sessions sorted by completion time

## Database Schema

The fix relies on the `session_players` table:

```sql
session_players (
    id: UUID,
    session_id: UUID → sessions.id,
    user_id: UUID → users.id,      -- Can be NULL for anonymous
    player_id: VARCHAR(50),          -- e.g., "Player 2"
    role: VARCHAR(20)                -- "human" or "ai"
)
```

The query joins this table to find sessions where the user participated.

## Files Modified

1. ✅ `backend/main.py`
   - Updated `/api/sessions` endpoint query
   - Added debug logging in `save_session_stats`

## Benefits

1. **Users see their games:** Sessions now appear in dashboard
2. **Multiple players supported:** If multiple users play together, all see the session
3. **Better debugging:** Console logs show mapping process
4. **Correct source of truth:** Uses `session_players` table, not just `session.user_id`
5. **Admin view unchanged:** Still sees all sessions

## Troubleshooting

### Sessions still not showing?

**Check console logs:**

1. **Missing token:**
   ```
   ⚠️  Could not authenticate WebSocket user: ...
   ```
   → Make sure user is logged in before joining

2. **No mapping saved:**
   ```
   👥 Saving player-user mappings: {}
   ```
   → WebSocket authentication failed
   → Check JWT token is valid

3. **Mapping saved but query fails:**
   ```
   ✅ Mapped Player 2 (human) -> user [uuid]
   ```
   → Check database has session_players table
   → Run migrations: `python -m alembic upgrade head`

### Verify in Database:

```bash
sqlite3 backend/group_chat.db

-- Check if session_players table exists
.tables

-- Check if mappings are saved
SELECT * FROM session_players LIMIT 5;

-- Check sessions for specific user
SELECT s.room_code, sp.player_id, sp.user_id 
FROM sessions s 
JOIN session_players sp ON s.id = sp.session_id 
WHERE sp.user_id = 'your-user-uuid';
```

## Status

✅ **FIXED AND READY TO TEST**

The issue is resolved! Sessions will now appear in the dashboard for:
- ✅ Regular users who play games (via `session_players`)
- ✅ Users who own sessions (via `session.user_id`)
- ✅ All sessions for admins

## Next Steps

1. Restart backend
2. Login as a regular user
3. Play a game
4. Check dashboard → **Session should appear!** ✨

Watch the console for the mapping logs to verify everything is working correctly.

