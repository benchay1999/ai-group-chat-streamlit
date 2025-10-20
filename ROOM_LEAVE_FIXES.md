# Room Leave System Fixes

## Overview
This document describes the fixes implemented to handle players leaving rooms in the matching room system.

## Issues Fixed

### 1. ⚠️ Creator Leaving Room
**Problem:** When the room creator left, the room would remain active, leading to orphaned rooms and confusion for other players.

**Solution:**
- Track the first player to join a room as the creator via `creator_id` field
- When the creator leaves, terminate the entire room and notify all connected players
- Clean up room data structures (rooms dict and room_locks)

### 2. ⚠️ Joiner Leaving Room
**Problem:** When a joiner left, they would still appear in the player list and their slot would be occupied.

**Solution:**
- Remove the player from `current_humans` list
- Remove the player from game state's `players` array
- Return the player's number to the `available_numbers` pool for reuse
- If room becomes empty after joiner leaves, delete the room

### 3. ⚠️ Real-time Detection of Terminated Rooms
**Problem:** Players in waiting screen or game screen wouldn't know if the room was terminated by another action.

**Solution:**
- Added polling checks in both waiting screen and game screen
- Detect when room no longer exists (returns `exists: false`)
- Automatically redirect players to lobby with an error message
- Reset all session state variables properly

## Implementation Details

### Backend Changes (`backend/main.py`)

#### New Endpoint: `/api/rooms/{room_code}/leave`
```python
@app.post("/api/rooms/{room_code}/leave")
async def leave_room_endpoint(room_code: str, player_data: dict):
    """
    Handle a player leaving a room.
    - If creator leaves: Terminate the entire room
    - If joiner leaves: Remove them from the room
    """
```

**Logic:**
1. Check if player is the creator (first in `current_humans` list)
2. If creator or room is in waiting status:
   - Broadcast termination message via WebSocket
   - Delete room and associated locks
   - Return "terminated" action
3. If joiner:
   - Remove from `current_humans` list
   - Remove from game state `players` array
   - Add player number back to `available_numbers`
   - If room is empty, delete it
   - Return "removed" action

#### Modified: `join_room` endpoint
- Track the first human to join as the creator:
```python
# If this is the first human to join, mark as creator
if len(room['current_humans']) == 1:
    room['creator_id'] = player_id
    print(f"👑 {player_id} is the creator of room {room_code}")
```

### Frontend Changes (`streamlit_app.py`)

#### New Function: `leave_room_api()`
```python
def leave_room_api(room_code: str, player_id: str):
    """Leave a room via API."""
    # Makes POST request to /api/rooms/{room_code}/leave
```

#### Updated: Leave Buttons
Both the waiting screen and game screen "Leave Room" buttons now:
1. Call `leave_room_api()` with current `room_code` and `player_id`
2. Reset all local session state variables
3. Show appropriate message based on action result
4. Redirect to lobby

**Waiting Screen:**
```python
if st.button("🚪 Leave Room", use_container_width=True):
    # Notify backend about leaving
    player_id = st.session_state.player_id
    leave_result = leave_room_api(room_code, player_id)
    
    # Reset local state
    st.session_state.joined = False
    st.session_state.waiting_for_players = False
    st.session_state.current_page = 'lobby'
    st.session_state.game_state = None
    st.session_state.player_id = 'You'
    
    # Show result message
    if leave_result:
        action = leave_result.get('action', '')
        if action == 'terminated':
            st.warning("Room was terminated")
        elif action == 'removed':
            st.info("Left the room")
    
    st.rerun()
```

**Game Screen:** Similar logic with additional cleanup of chat state.

#### Updated: Room Polling Logic
Added checks in both waiting screen and game screen to detect terminated rooms:

**Waiting Screen Polling:**
```python
# If room no longer exists, return to lobby
if not room_info or not room_info.get('exists'):
    st.error("⚠️ Room no longer exists (may have been terminated)")
    st.session_state.joined = False
    st.session_state.waiting_for_players = False
    st.session_state.current_page = 'lobby'
    st.session_state.game_state = None
    time.sleep(2)  # Show message briefly
    st.rerun()
    return
```

**Game Screen Polling:**
```python
# If room no longer exists, return to lobby
if not game_state or not game_state.get('exists'):
    st.error("⚠️ Room no longer exists (may have been terminated)")
    st.session_state.joined = False
    st.session_state.waiting_for_players = False
    st.session_state.current_page = 'lobby'
    st.session_state.game_state = None
    time.sleep(2)  # Show message briefly
    st.rerun()
    return
```

## Room Lifecycle

### Normal Flow:
1. **Creator creates room** → Marked as creator, assigned first player number
2. **Joiners join** → Get assigned player numbers from `available_numbers`
3. **Game starts** → When `current_humans` count reaches `max_humans`
4. **Game completes** → Players can leave or start new session
5. **Last player leaves** → Room is automatically deleted

### Creator Leaves During Waiting:
1. **Creator clicks "Leave Room"**
2. **Backend terminates room** → Broadcasts to all connected players
3. **All players redirected to lobby** → Via polling detection

### Joiner Leaves During Waiting:
1. **Joiner clicks "Leave Room"**
2. **Backend removes player** → Updates `current_humans`, returns player number
3. **Other players see updated count** → Via polling, waiting screen refreshes
4. **If room empty** → Room is deleted

### Player Leaves During Game:
1. **Player clicks "Leave Room"**
2. **Backend removes player** → Updates game state
3. **Remaining players continue** → Game logic handles missing player
4. **If creator leaves** → Room is terminated, all players redirected

## Error Handling

- **Room not found:** Returns error message, player redirected to lobby
- **Player not in room:** Safe no-op, returns success
- **Network errors:** Handled gracefully with error messages
- **Empty rooms:** Automatically cleaned up

## Testing Scenarios

### Test 1: Creator Leaves Waiting Room
1. Create room with max 2 humans
2. Have second player join
3. Creator leaves
4. **Expected:** Room terminates, both players return to lobby

### Test 2: Joiner Leaves Waiting Room
1. Create room with max 2 humans
2. Have second player join
3. Second player leaves
4. **Expected:** Count goes back to 1/2, creator can wait for new player

### Test 3: Player Leaves Active Game
1. Start game with 2 humans
2. One player leaves during discussion phase
3. **Expected:** Remaining player sees updated player list, game continues

### Test 4: Multiple Joiners Leave
1. Create room with max 4 humans
2. Have 3 joiners join (total 4)
3. 2 joiners leave
4. **Expected:** Count goes to 2/4, game hasn't started yet

### Test 5: Empty Room Cleanup
1. Create room with 1 human (game starts immediately)
2. Creator leaves
3. **Expected:** Room is deleted immediately, no orphaned data

## Future Enhancements

- **Kick player functionality:** Allow creator to remove specific players
- **Transfer ownership:** Allow creator to transfer creator role before leaving
- **Reconnection:** Allow players to reconnect to ongoing games after disconnect
- **Vote to end:** Allow players to vote to end a game early
- **Pause game:** Allow creator to pause the game when players leave

