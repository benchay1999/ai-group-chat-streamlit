# Timer Synchronization Fix - Implementation Summary

## Date: November 26, 2025

## Problems Fixed

### 1. New Players Joining Mid-Phase Got Wrong Timer (CRITICAL)
**Issue:** When a player joined a game mid-phase, they received the total phase duration instead of the actual remaining time.

**Fix:** Added immediate `timer_sync` message in WebSocket connection handler (line ~2950) that calculates and sends the current remaining time based on `phase_start_time`.

### 2. Phase Transitions Caused Brief Timer Desync (MODERATE)
**Issue:** During phase transitions, all clients reset to full duration before getting corrected.

**Fix:** Added immediate `timer_sync` broadcast right after phase transition announcements (line ~850 for voting, and multiple locations for discussion phase starts).

## Changes Made

### File: `backend/main.py`

#### Change 1: WebSocket Connection Handler (Line ~2950)
Added calculation and broadcast of current timer state when a player connects:

```python
# Send current timer state if in an active phase (FIX: Timer sync for mid-phase joins)
if state["phase"].value in ["Discussion", "Voting"] and 'phase_start_time' in room:
    phase_start = room['phase_start_time']
    if state["phase"].value == "Discussion":
        total_duration = room.get('discussion_duration', DISCUSSION_TIME)
    else:
        total_duration = room.get('voting_duration', VOTING_TIME)
    
    elapsed = _time.time() - phase_start
    remaining = max(0, int(total_duration - elapsed))
    
    await websocket.send_json({
        "type": "timer_sync",
        "phase": state["phase"].value,
        "time_remaining": remaining
    })
    print(f"⏱️ Sent initial timer sync to {player_id}: {remaining}s remaining in {state['phase'].value}")
```

#### Change 2: Discussion → Voting Phase Transition (Line ~850)
Added immediate timer sync after phase change broadcast:

```python
# Immediately send timer sync for phase transition (FIX: Prevent timer desync during phase change)
await broadcast_to_room(room_code, {
    "type": "timer_sync",
    "phase": "Voting",
    "time_remaining": int(voting_duration)
})
```

#### Change 3: Discussion Phase Start - WebSocket Initialization (Line ~2930)
Added immediate timer sync after discussion phase starts:

```python
# Immediately send timer sync for initial discussion phase (FIX: Prevent timer desync at game start)
discussion_duration = rooms[room_code].get('discussion_duration', DISCUSSION_TIME)
await broadcast_to_room(room_code, {
    "type": "timer_sync",
    "phase": "Discussion",
    "time_remaining": int(discussion_duration)
})
```

#### Change 4: Discussion Phase Start - Game Restart Endpoint (Line ~3138)
Added immediate timer sync after discussion phase starts in game restart flow.

#### Change 5: Discussion Phase Start - Rejoin Flow (Line ~5856)
Added immediate timer sync after discussion phase starts when players rejoin.

#### Change 6: Discussion Phase Start - Legacy Room Join (Line ~5970)
Added immediate timer sync after discussion phase starts for legacy room joins.

#### Change 7: Discussion Phase Start - Standard Room Join (Line ~6125)
Added immediate timer sync after discussion phase starts for standard room joins.

## Testing Recommendations

1. **Test Case 1: New player joining mid-Discussion**
   - Start a game with Player 1
   - Wait 60 seconds into discussion phase
   - Have Player 2 join
   - **Expected:** Player 2 should see ~120 seconds remaining (not 180)

2. **Test Case 2: New player joining mid-Voting**
   - Start a game and wait until voting phase
   - Wait 20 seconds into voting phase
   - Have Player 2 join
   - **Expected:** Player 2 should see ~40 seconds remaining (not 60)

3. **Test Case 3: Phase transition synchronization**
   - Have 2+ players in a game
   - Wait for discussion → voting transition
   - **Expected:** All players should see voting timer start at the same time with no flicker/reset

4. **Test Case 4: Player disconnect and rejoin**
   - Start game with Player 1
   - Player 1 disconnects after 90 seconds
   - Player 1 reconnects immediately
   - **Expected:** Player 1 should see correct remaining time (~90 seconds)

5. **Test Case 5: Multiple players timer sync**
   - Have 3+ players in the same game
   - Monitor timer on all clients
   - **Expected:** All clients should show the same time (±1 second tolerance due to client-side countdown)

## Technical Details

### Timer Synchronization Architecture

1. **Server Authority:** The server is the authoritative source for time tracking
   - Uses `phase_start_time` stored in room data
   - Calculates elapsed time using wall clock (`_time.time()`)
   - Broadcasts remaining time every 5 seconds via `timer_sync` messages

2. **Client-Side Countdown:** Clients count down locally between server syncs
   - Improves UX by showing smooth countdown
   - Gets corrected every 5 seconds by server
   - Marked as `serverSynced: true` when receiving server update, `false` during local countdown

3. **New Player Sync:** Players joining mid-phase immediately receive accurate timer
   - Server calculates elapsed time from `phase_start_time`
   - Sends `timer_sync` with actual remaining time
   - No waiting for next periodic broadcast

4. **Phase Transition Sync:** All players get immediate timer update when phases change
   - Phase message includes duration (for backwards compatibility)
   - Immediate `timer_sync` message provides exact starting time
   - Prevents brief desynchronization

## Verification

After implementing these changes:
- [x] No linter errors
- [ ] Manual testing with multiple players
- [ ] Verify timer stays synchronized across clients
- [ ] Verify new players get correct timer on join
- [ ] Verify phase transitions are smooth

## Notes

- All timer broadcasts use `int()` to round remaining time for display
- The `phase_start_time` field is critical - must be set when each phase starts
- Client-side countdown provides smooth UX between 5-second server syncs
- Server sync every 5 seconds keeps all clients aligned

