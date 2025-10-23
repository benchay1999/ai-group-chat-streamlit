# Testing Guide for Room Leave System

## Setup

1. **Start the Backend:**
   ```bash
   cd /home/wschay/group-chat
   conda activate group-chat
   python backend/main.py
   ```

2. **Start the Frontend (in a new terminal):**
   ```bash
   cd /home/wschay/group-chat
   conda activate group-chat
   streamlit run streamlit_app.py --server.port 8501
   ```

3. **Open Multiple Browser Windows:**
   - Open 2-3 browser windows/tabs to `http://localhost:8501`
   - Use incognito/private windows to simulate different users
   - Each window will be a separate player

## Test Cases

### Test 1: Creator Leaves Waiting Room (Critical)

**Steps:**
1. In Browser 1 (Creator):
   - Click "🎮 Create New Room"
   - Set "Number of Human Players" to 2
   - Set "Total Players" to 5
   - Click "Create & Join"
   - Wait on the waiting screen

2. In Browser 2 (Joiner):
   - Click on the room card for the room created above
   - Click "Join Game"
   - You should see waiting screen showing 2/2 players

3. In Browser 1 (Creator):
   - Click "🚪 Leave Room"

**Expected Results:**
- ✅ Creator returns to lobby immediately
- ✅ Joiner sees error: "⚠️ Room no longer exists (may have been terminated)"
- ✅ Joiner automatically redirected to lobby after 2 seconds
- ✅ Room no longer appears in room list

---

### Test 2: Joiner Leaves Waiting Room

**Steps:**
1. In Browser 1 (Creator):
   - Create room with 3 human players, 5 total
   - Wait on waiting screen (1/3 players)

2. In Browser 2 (Joiner 1):
   - Join the room
   - Wait on waiting screen (2/3 players)

3. In Browser 3 (Joiner 2):
   - Join the room
   - Wait on waiting screen (3/3 players - game about to start)

4. In Browser 2 (Joiner 1):
   - Quickly click "🚪 Leave Room" before game starts

**Expected Results:**
- ✅ Joiner 1 returns to lobby
- ✅ Creator and Joiner 2 see count drop to 2/3
- ✅ Room status remains "waiting"
- ✅ Another player can join the now-available slot

---

### Test 3: Creator Leaves Active Game

**Steps:**
1. Create room with 1 human player (game starts immediately)
2. Wait for game to reach discussion phase
3. Send a few messages
4. Click "Leave Room" button

**Expected Results:**
- ✅ Creator returns to lobby
- ✅ Room is deleted (since only 1 human)
- ✅ Game session ends
- ✅ Room no longer in room list

---

### Test 4: Joiner Leaves Active Game

**Steps:**
1. In Browser 1: Create room with 2 humans, 5 total
2. In Browser 2: Join the room
3. Game starts (2/2 humans)
4. Both players reach discussion phase
5. In Browser 2: Click "Leave Room"

**Expected Results:**
- ✅ Joiner returns to lobby
- ✅ Creator sees updated player list (joiner removed)
- ✅ Creator can continue playing or leave
- ✅ Game continues (doesn't crash)

---

### Test 5: Multiple Joiners Leave Sequentially

**Steps:**
1. Create room with 4 humans
2. Have 3 players join (total 4/4)
3. Player 2 leaves → count 3/4
4. Player 3 leaves → count 2/4
5. Player 4 leaves → count 1/4 (only creator)

**Expected Results:**
- ✅ Each leave properly updates the count
- ✅ Room remains active with creator
- ✅ New players can join available slots
- ✅ Player numbers are properly recycled

---

### Test 6: Empty Room Cleanup

**Steps:**
1. Create room with 2 humans
2. Have second player join
3. Creator leaves immediately
4. Check backend console logs

**Expected Results:**
- ✅ Backend logs: "🗑️ Terminating room {code}"
- ✅ Room removed from `rooms` dict
- ✅ Room removed from `room_locks` dict
- ✅ Both players redirected to lobby
- ✅ No orphaned data structures

---

### Test 7: Rapid Leave During Room Start

**Steps:**
1. Create room with 2 humans
2. Have second player join (game about to start)
3. Immediately (within 1 second) have second player click "Leave Room"

**Expected Results:**
- ✅ System handles the race condition properly
- ✅ Either:
  - Game doesn't start, joiner leaves
  - OR game starts, joiner is removed from active game
- ✅ No crashes or errors
- ✅ Creator can continue or restart

---

### Test 8: Network Error During Leave

**Steps:**
1. Create room and join
2. Stop the backend server
3. Try to click "Leave Room"
4. Restart backend

**Expected Results:**
- ✅ Frontend handles error gracefully
- ✅ User still redirected to lobby (local state cleared)
- ✅ Backend logs may show disconnection
- ✅ No hanging states

---

### Test 9: Room Polling After Termination

**Steps:**
1. In Browser 1: Create room with 2 humans
2. In Browser 2: Join room, wait on waiting screen
3. In Browser 1: Click "Leave Room" (terminates room)
4. Wait 2 seconds (polling interval) in Browser 2

**Expected Results:**
- ✅ Browser 2 detects room no longer exists
- ✅ Error message appears: "⚠️ Room no longer exists"
- ✅ Browser 2 auto-redirects to lobby
- ✅ Both browsers show updated room list (room gone)

---

### Test 10: Leave Button Visibility

**Steps:**
1. Test in lobby → No leave button
2. Test in waiting screen → "🚪 Leave Room" button present
3. Test in game screen → "Leave Room" button in sidebar
4. Test after game over → Can start new session or leave

**Expected Results:**
- ✅ Leave button only appears in appropriate contexts
- ✅ Button is always accessible and clickable
- ✅ Button styling is consistent
- ✅ Button action is immediate (no delays)

## Backend Verification

### Check Backend Logs
When running tests, monitor the backend console for these logs:

**Room Creation:**
```
🎮 Created room ABC123 (Room ABC123): 2 humans, 5 total
```

**Player Joining:**
```
👤 Player 3 joined room ABC123 (1/2)
👑 Player 3 is the creator of room ABC123
```

**Player Leaving:**
```
🚪 Player 3 leaving room ABC123 (creator: True)
🗑️ Terminating room ABC123 (creator left or in waiting status)
```

**Room Cleanup:**
```
🗑️ Room ABC123 now empty, deleting
```

### Check Room State via API

You can manually check room state using curl:

```bash
# List all rooms
curl http://localhost:8000/api/rooms/list?page=1

# Get specific room info
curl http://localhost:8000/api/rooms/ABC123/info

# Get game state
curl http://localhost:8000/api/rooms/ABC123/state?player_id=Player%203
```

## Common Issues and Fixes

### Issue: "Room not found" immediately after creation
**Fix:** Backend might not have finished initializing the room. Wait 0.5s before joining.

### Issue: Players not redirected after creator leaves
**Fix:** Check polling interval is 2 seconds in waiting screen. Verify room polling logic.

### Issue: Room still appears in list after termination
**Fix:** Refresh the lobby page. Check backend has deleted the room.

### Issue: Player number not recycled
**Fix:** Verify `available_numbers` is being updated when player leaves.

### Issue: Leave button doesn't work
**Fix:** Check player_id is set in session state. Verify backend endpoint is responding.

## Performance Testing

### Stress Test 1: Many Rooms
1. Create 20+ rooms with 1 human each
2. Check lobby pagination works
3. Leave all rooms
4. Verify all rooms cleaned up

### Stress Test 2: Rapid Join/Leave
1. Create room with 4 humans
2. Have 3 players join and immediately leave 10 times
3. Verify no memory leaks or orphaned data

### Stress Test 3: Concurrent Leaves
1. Create room with 4 humans
2. All 4 players join
3. All 4 click "Leave Room" simultaneously
4. Verify proper cleanup and no crashes

## Success Criteria

✅ **Creator Leave:** Room terminates, all players notified and redirected
✅ **Joiner Leave:** Player removed, room continues, number recycled
✅ **Empty Room:** Automatically deleted with no orphaned data
✅ **Real-time Detection:** Players detect terminated rooms within 2 seconds
✅ **UI Feedback:** Clear messages on leave action results
✅ **No Crashes:** System handles all edge cases gracefully
✅ **Data Cleanup:** No memory leaks or orphaned rooms/locks
✅ **Number Recycling:** Player numbers properly reused

## Notes

- **Polling Interval:** Waiting screen polls every 2 seconds, game screen every 0.3-2 seconds
- **Creator Detection:** First player to join is always the creator
- **Termination:** Creator leaving OR room in waiting status triggers termination
- **Cleanup:** Empty rooms are immediately deleted
- **Session Reset:** All session state variables properly cleared on leave

