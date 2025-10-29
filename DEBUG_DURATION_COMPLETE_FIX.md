




















# 🔧 Debug Duration Complete Fix

## Problem Summary
When creating a room with debug durations (1-minute discussion, 30-second voting), the game was still running with default 3-minute discussion and 1-minute voting.

## Root Causes

### 1. **Backend: Room durations stored correctly but frontend timer hardcoded** ❌
- Backend stored `discussion_duration: 60, voting_duration: 30` correctly
- But frontend `GamePage.jsx` hardcoded timer values: `timer: 180` and `timer: 60`
- Frontend display showed wrong countdown even if backend timing was correct

### 2. **Backend: Phase change messages didn't include durations** ❌
- When backend sent `"type": "phase"` messages, it didn't include duration info
- Frontend had no way to know what timer value to use

## Complete Solution

### Backend Changes (`backend/main.py`)

**1. Added extensive debugging:**
```python
# In create_room:
print(f"🔍 Verifying room dict after creation - discussion_duration: {rooms[room_code].get('discussion_duration')}")

# In join_room:
print(f"🔍 Room {room_code} exists - discussion_duration: {room.get('discussion_duration')}")
print(f"🚀 Starting game phases - discussion_duration: {room.get('discussion_duration')}")

# In WebSocket endpoint:
print(f"⚠️ WebSocket connection to non-existent room: {room_code}")  # If room doesn't exist
print(f"✅ WebSocket connecting to existing room: {room_code}")  # If room exists
print(f"✅ Existing room durations - discussion: {rooms[room_code].get('discussion_duration')}")

# In run_discussion_phase:
print(f"⏱️ Starting discussion phase for room {room_code}: {discussion_time} seconds")

# In run_voting_phase:
print(f"🗳️ Starting voting phase for room {room_code}: {voting_time} seconds")
```

**2. Send durations in phase change broadcasts:**
```python
# When transitioning to voting:
voting_duration = rooms[room_code].get('voting_duration', VOTING_TIME)
await broadcast_to_room(room_code, {
    "type": "phase",
    "phase": "Voting",
    "message": "Discussion ended. Time to vote.",
    "voting_duration": voting_duration  # ✅ NEW
})
```

**3. Send durations in initial WebSocket connection:**
```python
# When client connects via WebSocket:
phase_msg = {
    "type": "phase",
    "phase": state["phase"].value,
    "message": f"Currently in {state['phase'].value}"
}
if state["phase"].value == "Discussion":
    phase_msg["discussion_duration"] = room.get('discussion_duration', DISCUSSION_TIME)
elif state["phase"].value == "Voting":
    phase_msg["voting_duration"] = room.get('voting_duration', VOTING_TIME)
await websocket.send_json(phase_msg)
```

### Frontend Changes (`frontend/src/pages/GamePage.jsx`)

**1. Use server-provided durations instead of hardcoded values:**

**Before:**
```javascript
case 'phase':
  // ...
  if (data.phase === 'Discussion') {
    setGameState(prev => ({ ...prev, timer: 180 }));  // ❌ HARDCODED
  } else if (data.phase === 'Voting') {
    setGameState(prev => ({ ...prev, timer: 60 }));   // ❌ HARDCODED
  }
  break;
```

**After:**
```javascript
case 'phase':
  // ...
  // Update timer based on phase duration from server
  if (data.phase === 'Discussion' && data.discussion_duration) {
    setGameState(prev => ({ ...prev, timer: data.discussion_duration }));  // ✅ FROM SERVER
  } else if (data.phase === 'Voting' && data.voting_duration) {
    setGameState(prev => ({ ...prev, timer: data.voting_duration }));  // ✅ FROM SERVER
  } else if (data.phase === 'Discussion') {
    setGameState(prev => ({ ...prev, timer: 180 }));  // Fallback
  } else if (data.phase === 'Voting') {
    setGameState(prev => ({ ...prev, timer: 60 }));  // Fallback
  }
  break;
```

**2. Fix new_round timer:**

**Before:**
```javascript
case 'new_round':
  setGameState(prev => ({
    // ...
    timer: 180,  // ❌ HARDCODED
  }));
  break;
```

**After:**
```javascript
case 'new_round':
  setGameState(prev => ({
    // ...
    timer: data.discussion_duration || 180,  // ✅ FROM SERVER
  }));
  break;
```

## Testing Instructions

### 1. Restart Backend & Frontend
```bash
# Terminal 1 - Backend
cd backend && python main.py

# Terminal 2 - Frontend
cd frontend && npm start
```

### 2. Create Debug Room
1. Login to the app
2. Click "Create Room"
3. Select:
   - ⚡ **1 minute** discussion (Debug)
   - ⚡ **30 seconds** voting (Debug)
   - **1 human** player
4. Click "Create"

### 3. Watch Backend Console
You should see:
```
🎮 Created room ABC123: ... discussion: 60s, voting: 30s
🔍 Verifying room dict after creation - discussion_duration: 60, voting_duration: 30
🔐 User 'testuser1' joining room ABC123 via API
🔍 Room ABC123 exists - discussion_duration: 60, voting_duration: 30
🚀 Starting game phases - discussion_duration: 60, voting_duration: 30
⏱️ Starting discussion phase for room ABC123: 60 seconds
✅ WebSocket connecting to existing room: ABC123
✅ Existing room durations - discussion: 60, voting: 30
```

### 4. Watch Frontend Timer
- **Discussion phase:** Timer should start at **1:00** (60 seconds) ✅
- **Voting phase:** Timer should start at **0:30** (30 seconds) ✅

### 5. Verify Actual Duration
- Discussion should end after exactly **1 minute** ✅
- Voting should end after exactly **30 seconds** ✅
- **Total game time: ~1.5 minutes** ⚡

## Common Issues & Solutions

### Issue: Room durations show "NOT SET" in console
**Cause:** Room created via legacy WebSocket path instead of API
**Solution:** Make sure you're creating rooms via the "Create Room" button, not connecting directly via WebSocket URL

### Issue: Frontend timer still shows 3:00 / 1:00
**Cause:** Frontend not receiving duration data from backend
**Solution:** 
1. Check backend console for phase change broadcasts
2. Check browser console for WebSocket messages
3. Ensure frontend code changes were saved and rebuilt

### Issue: Backend uses correct duration but frontend timer doesn't match
**Cause:** Frontend using fallback values because server didn't send durations
**Solution:** Restart backend to ensure phase broadcast changes are active

## Expected Debug Log Flow

```
📱 FRONTEND: Create room with 60s discussion, 30s voting
🎮 BACKEND: Created room ABC123 with durations
🔍 BACKEND: Verified - discussion_duration: 60, voting_duration: 30

📱 FRONTEND: Join room ABC123
🔐 BACKEND: User joining room ABC123
🔍 BACKEND: Room exists with durations: 60, 30
🚀 BACKEND: Starting game with durations: 60, 30
⏱️ BACKEND: Starting discussion phase: 60 seconds

📱 FRONTEND: Connect WebSocket
✅ BACKEND: WebSocket connecting to existing room
✅ BACKEND: Existing room durations: 60, 30
📤 BACKEND: Sending phase message with discussion_duration: 60
📱 FRONTEND: Received phase=Discussion, discussion_duration=60
📱 FRONTEND: Setting timer to 60 seconds ✅

⏱️ (60 seconds later)
⏱️ BACKEND: Discussion time elapsed, transitioning to voting
🗳️ BACKEND: Starting voting phase: 30 seconds
📤 BACKEND: Broadcasting phase change with voting_duration: 30
📱 FRONTEND: Received phase=Voting, voting_duration=30
📱 FRONTEND: Setting timer to 30 seconds ✅

🗳️ (30 seconds later)
🗳️ BACKEND: Voting time elapsed, completing game
🏁 BACKEND: Game over
📱 FRONTEND: Game over screen
```

## Files Modified

### Backend
- `backend/main.py`:
  - Added debug logging throughout
  - Modified phase broadcast to include `voting_duration`
  - Modified WebSocket initial phase message to include durations
  - Fixed legacy room creation paths (already done in previous fix)

### Frontend
- `frontend/src/pages/GamePage.jsx`:
  - Changed `case 'phase'` to use `data.discussion_duration` and `data.voting_duration`
  - Changed `case 'new_round'` to use `data.discussion_duration`
  - Added fallbacks to default values if server doesn't provide durations

## Status
✅ **COMPLETE** - Debug durations now work end-to-end from backend to frontend!

**Total test time with debug mode: ~1.5 minutes** ⚡ (vs. 4+ minutes with standard durations)

