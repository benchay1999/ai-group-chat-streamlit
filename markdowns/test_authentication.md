# Testing User Authentication in Games

## Current Database State

```
Total session_players records: 5
Records with user_id: 0  ← ALL NULL!
Records without user_id: 5

Users in database:
- benchay (admin)
- testuser1 (regular user)
```

**Problem:** All games were played WITHOUT authentication!

---

## Why Sessions Don't Appear

The sessions list query looks for:
```sql
WHERE (session.user_id = current_user.id) 
   OR (session_players.user_id = current_user.id)
```

Since ALL `user_id` values are NULL, no sessions match!

---

## How to Fix & Test

### Step 1: Clear Old Sessions (Optional)

Delete old sessions that have no user mappings:

```bash
cd backend
python3 -c "
import sqlite3
conn = sqlite3.connect('group_chat.db')
cursor = conn.cursor()
cursor.execute('DELETE FROM sessions')
cursor.execute('DELETE FROM session_players')
cursor.execute('DELETE FROM ai_agent_usage')
conn.commit()
print('✅ Cleared all old sessions')
conn.close()
"
```

### Step 2: Test Authentication Flow

**CRITICAL**: You must login BEFORE playing!

1. **Open browser in INCOGNITO mode** (to ensure clean state)

2. **Login FIRST:**
   - Go to http://localhost:3000
   - Click "Login"
   - Login as `testuser1`
   - **Verify you're logged in** (see username in header)

3. **Then start game:**
   - Click "New Game" or "Join Game"
   - Play through the game
   - Complete it

4. **Check console output:**

```
Should see:
🔌 WebSocket accepted for player You in room ABC123
👤 Authenticated user testuser1 as You
👤 Stored mapping: You -> user ba6c5d1b-70c2-4fc6-80a0-2cda849ff6c6
...
[Game plays]
...
👥 Saving player-user mappings: {'You': 'ba6c5d1b-70c2-4fc6-80a0-2cda849ff6c6'}
✅ Mapped You (human) -> user ba6c5d1b-70c2-4fc6-80a0-2cda849ff6c6
```

5. **Check dashboard:**
   - Click "View Dashboard & Stats"
   - **Session should appear!** ✅

### Step 3: Verify in Database

```bash
cd backend
python3 -c "
import sqlite3
conn = sqlite3.connect('group_chat.db')
cursor = conn.cursor()

print('=== After New Game ===')
cursor.execute('SELECT player_id, role, user_id FROM session_players WHERE user_id IS NOT NULL')
rows = cursor.fetchall()
if rows:
    print(f'✅ Found {len(rows)} authenticated player(s)!')
    for row in rows:
        print(f'  Player: {row[0]}, Role: {row[1]}, User: {row[2][:8]}...')
else:
    print('❌ No authenticated players found')

conn.close()
"
```

---

## Common Mistakes

### ❌ Mistake 1: Playing While Logged Out

```
User flow:
1. Opens http://localhost:3000  ← Not logged in
2. Clicks "New Game"
3. Plays game
4. Logs in AFTER game
5. Checks dashboard → Empty! ❌
```

**Why:** The WebSocket connection was made BEFORE login, so no token was sent.

### ✅ Correct Flow:

```
User flow:
1. Opens http://localhost:3000
2. Clicks "Login" → Logs in as testuser1
3. Clicks "New Game"  ← Now has token in localStorage
4. WebSocket sends token
5. Game saves with user_id
6. Dashboard shows session! ✅
```

### ❌ Mistake 2: Old Token/Session

Browser might have stale auth state. Use:
- Incognito/Private mode, OR
- Clear localStorage: `localStorage.clear()`

---

## Debugging Authentication Issues

### Check if Token Exists

Open browser console:
```javascript
localStorage.getItem('token')
// Should show: "eyJhbGciOiJIUzI1NiIsInR5cCI6..."
// If null → Not logged in!
```

### Check WebSocket URL

```javascript
// Should include ?token=...
ws://localhost:8000/ws/ABC123/You?token=eyJhbG...
```

### Check Backend Logs

**If authentication works:**
```
👤 Authenticated user testuser1 as You
👤 Stored mapping: You -> user ba6c5d1b-70c2-4fc6-80a0-2cda849ff6c6
```

**If authentication fails:**
```
⚠️ Could not authenticate WebSocket user: [error message]
```

Common errors:
- `'NoneType' object has no attribute 'get'` → Token is None/invalid
- `Invalid signature` → JWT_SECRET_KEY mismatch
- `Token has expired` → Token too old, re-login

---

## Expected Results

### After Following Correct Flow:

**Backend Console:**
```
🔌 WebSocket accepted for player You in room ABC123
👤 Authenticated user testuser1 as You
👤 Stored mapping: You -> user ba6c5d1b...
...
👥 Saving player-user mappings: {'You': 'ba6c5d1b...'}
✅ Mapped You (human) -> user ba6c5d1b...
✅ Session saved to database
```

**Frontend Dashboard:**
```
Your Sessions
┌─────────────────────────────────────┐
│ Room ABC123 - Oct 29, 2025 17:30   │
│ English  1/5 players  3m            │
│ Payment: pending  $0.00             │
│ View Details →                      │
└─────────────────────────────────────┘
```

**Database:**
```
session_players:
- player_id: "You"
- role: "human" 
- user_id: "ba6c5d1b..." ← NOT NULL!
```

---

## Still Not Working?

1. **Clear everything and start fresh:**
   ```bash
   # Clear database
   cd backend && python3 -c "import sqlite3; conn = sqlite3.connect('group_chat.db'); cursor = conn.cursor(); cursor.execute('DELETE FROM sessions'); cursor.execute('DELETE FROM session_players'); conn.commit(); conn.close()"
   
   # Clear browser
   # Open browser console and run:
   # localStorage.clear()
   # Then refresh page
   ```

2. **Restart backend:**
   ```bash
   # Kill existing process
   # Then restart:
   cd backend && python main.py
   ```

3. **Follow exact steps:**
   - Open incognito window
   - Go to http://localhost:3000
   - **LOGIN FIRST** as testuser1
   - **Then** click New Game
   - Play and complete
   - Check dashboard

4. **Watch console logs carefully:**
   - Look for "👤 Authenticated user testuser1"
   - If you don't see it → authentication failed
   - Check the error message

---

## Summary

The issue is simple:
- ❌ All existing games were played **without being logged in first**
- ✅ Login **BEFORE** starting a game
- ✅ Then the session will have user_id
- ✅ Then it will appear in dashboard

**Key takeaway:** Authentication happens during WebSocket connection. Must be logged in when joining the game!

