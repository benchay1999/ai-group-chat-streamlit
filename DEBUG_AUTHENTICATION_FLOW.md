# Debug Authentication Flow

## Testing Steps

1. **Clear old sessions:**
   ```bash
   python clear_old_sessions.py
   ```

2. **Restart backend:**
   ```bash
   cd backend && python main.py
   ```

3. **Test flow:**
   - Open browser (incognito recommended)
   - Login as testuser1 FIRST
   - Verify logged in (see username in header)
   - Start/join a game
   - Play through to completion
   - Watch backend console carefully

---

## Expected Console Output (When Working)

### Step 1: WebSocket Connection
```
🔌 WebSocket accepted for player Player 5 in room ABC123
🔑 Token received: Yes
🔓 Decoding JWT token...
🆔 User UUID from token: ba6c5d1b-70c2-4fc6-80a0-2cda849ff6c6
👤 ✅ Authenticated user 'testuser1' (ID: ba6c5d1b...) as Player 5
✅ Connection added. Total connections: 1
👤 ✅ Stored initial mapping: Player 5 -> user ba6c5d1b...
✅ Added human player Player 5 to game state
👤 ✅ Mapped Player 5 (human) -> user ba6c5d1b...
📋 Current player_user_map: {'Player 5': 'ba6c5d1b-70c2-4fc6-80a0-2cda849ff6c6'}
```

### Step 2: Game Ends - Saving to Database
```
👥 Saving player-user mappings...
📋 player_user_map from room_data: {'Player 5': 'ba6c5d1b-70c2-4fc6-80a0-2cda849ff6c6'}
👥 state['players']: ['Player 1 (ai)', 'Player 2 (ai)', 'Player 3 (ai)', 'Player 4 (ai)', 'Player 5 (human)']
🔍 Processing player Player 1 (ai): mapped_user_id = None
ℹ️  Player 1 (ai) -> No user mapping (anonymous)
💾 SessionPlayer added to DB: Player 1, user_id=None
🔍 Processing player Player 2 (ai): mapped_user_id = None
ℹ️  Player 2 (ai) -> No user mapping (anonymous)
💾 SessionPlayer added to DB: Player 2, user_id=None
🔍 Processing player Player 3 (ai): mapped_user_id = None
ℹ️  Player 3 (ai) -> No user mapping (anonymous)
💾 SessionPlayer added to DB: Player 3, user_id=None
🔍 Processing player Player 4 (ai): mapped_user_id = None
ℹ️  Player 4 (ai) -> No user mapping (anonymous)
💾 SessionPlayer added to DB: Player 4, user_id=None
🔍 Processing player Player 5 (human): mapped_user_id = ba6c5d1b-70c2-4fc6-80a0-2cda849ff6c6
✅ Mapped Player 5 (human) -> user ba6c5d1b-70c2-4fc6-80a0-2cda849ff6c6
💾 SessionPlayer added to DB: Player 5, user_id=ba6c5d1b-70c2-4fc6-80a0-2cda849ff6c6
✅ Session saved to database with ID: abc-123-def
```

---

## Problem Scenarios & Solutions

### Scenario 1: No Token Received
```
🔌 WebSocket accepted for player Player 5 in room ABC123
🔑 Token received: No
ℹ️ No token provided - user playing anonymously
```

**Problem:** User not logged in OR token not sent in WebSocket URL

**Solution:**
1. Check browser localStorage: `localStorage.getItem('token')`
2. If null → User not logged in
3. Check WebSocket URL in network tab - should include `?token=...`

---

### Scenario 2: Token Invalid/Expired
```
🔌 WebSocket accepted for player Player 5 in room ABC123
🔑 Token received: Yes
🔓 Decoding JWT token...
⚠️ Could not authenticate WebSocket user: Signature verification failed
```

**Problem:** JWT signature mismatch or expired token

**Solution:**
1. Logout and login again to get fresh token
2. Check JWT_SECRET_KEY matches in .env

---

### Scenario 3: User Not Found
```
🔌 WebSocket accepted for player Player 5 in room ABC123
🔑 Token received: Yes
🔓 Decoding JWT token...
🆔 User UUID from token: abc-123-def
⚠️ User not found in database for UUID: abc-123-def
```

**Problem:** User was deleted or UUID mismatch

**Solution:**
1. Check database: `SELECT * FROM users WHERE id = 'abc-123-def'`
2. Re-register user if needed

---

### Scenario 4: Mapping Not Stored
```
👤 ✅ Authenticated user 'testuser1' (ID: ba6c5d1b...) as Player 5
✅ Connection added. Total connections: 1
⚠️ No user_id to store for player Player 5
```

**Problem:** `user_id` is None even though authentication succeeded

**Solution:**
- Check if authentication is properly returning user_id
- Verify `authenticated_user` variable is set

---

### Scenario 5: Player Not Added to State
```
👤 ✅ Stored initial mapping: Player 5 -> user ba6c5d1b...
[No "Added human player" message]
```

**Problem:** Human player addition logic not executing

**Solution:**
- Check if room already exists
- Check if player already in state

---

### Scenario 6: Mapping Lost During Save
```
👥 Saving player-user mappings...
📋 player_user_map from room_data: {}
👥 state['players']: ['Player 1 (ai)', 'Player 2 (ai)', 'Player 5 (human)']
🔍 Processing player Player 5 (human): mapped_user_id = None
ℹ️  Player 5 (human) -> No user mapping (anonymous)
```

**Problem:** `player_user_map` is empty when saving!

**Possible Causes:**
1. Room data was reset/cleared during game
2. Wrong room_code being used
3. Mapping stored in different room

**Solution:**
- Check if room data persists throughout game
- Verify room_code matches

---

## Verification After Game

### Check Database
```bash
python3 -c "
import sqlite3
conn = sqlite3.connect('backend/group_chat.db')
cursor = conn.cursor()

print('=== Latest Session Players ===')
cursor.execute('''
    SELECT sp.player_id, sp.role, sp.user_id, u.user_id as username
    FROM session_players sp
    LEFT JOIN users u ON sp.user_id = u.id
    ORDER BY sp.rowid DESC
    LIMIT 10
''')
for row in cursor.fetchall():
    print(f'Player: {row[0]}, Role: {row[1]}, User: {row[3] if row[3] else \"NULL\"}')

conn.close()
"
```

**Expected Output:**
```
=== Latest Session Players ===
Player: Player 5, Role: human, User: testuser1
Player: Player 4, Role: ai, User: NULL
Player: Player 3, Role: ai, User: NULL
Player: Player 2, Role: ai, User: NULL
Player: Player 1, Role: ai, User: NULL
```

---

## Key Debug Points

### 1. Token Present?
Look for: `🔑 Token received: Yes`
If No → Login issue

### 2. Token Valid?
Look for: `👤 ✅ Authenticated user 'testuser1'`
If missing → Token decode issue

### 3. Mapping Stored?
Look for: `👤 ✅ Stored initial mapping: Player 5 -> user ba6c5d1b...`
If missing → Storage issue

### 4. Human Added to State?
Look for: `✅ Added human player Player 5 to game state`
If missing → State update issue

### 5. Mapping in Save?
Look for: `📋 player_user_map from room_data: {'Player 5': '...'}`
If empty → Data persistence issue

### 6. DB Insert?
Look for: `💾 SessionPlayer added to DB: Player 5, user_id=ba6c5d1b...`
If user_id is None → Mapping lost

---

## What to Send Me

If it still doesn't work, send me the backend console output from:

1. When WebSocket connects (lines with 🔌 🔑 👤)
2. When human player is added (lines with ✅ Added human player)
3. When game ends (lines with 👥 Saving and 🔍 Processing)

This will show exactly where the flow breaks!

