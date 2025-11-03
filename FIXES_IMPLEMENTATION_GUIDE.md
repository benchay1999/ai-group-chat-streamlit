# Room Management Fixes - Implementation Guide

This document provides EXACT, EXECUTABLE fixes for the critical issues found in the room management system.

---

## P0-1: Add Lock Protection to join_room Endpoint

**File**: `backend/main.py`
**Function**: `join_room` (starts at line ~3873)
**Issue**: Race conditions when multiple players join simultaneously

### Implementation Steps:

1. Add lock initialization at the START of the function (before any room operations):

```python
@app.post("/api/rooms/{room_code}/join")
async def join_room(
    room_code: str, 
    player_data: dict,
    current_user: User = Depends(get_current_user_optional)
):
    """..."""
    
    # Initialize lock for this room if needed (before any room operations)
    if room_code not in room_locks:
        room_locks[room_code] = asyncio.Lock()
    
    # CRITICAL: Use lock to prevent race conditions during join
    async with room_locks[room_code]:
        # ALL THE EXISTING CODE FROM HERE ONWARDS NEEDS TO BE INDENTED
        # BY 4 SPACES (ONE TAB LEVEL)
        ...
```

2. Indent ALL lines from the first validation check down to the final `return` statement by 4 spaces.

3. The final structure should be:
   - Lock initialization (NOT indented - before lock)
   - `async with room_locks[room_code]:` (NOT indented - lock declaration)
   - ALL function logic (INDENTED by 4 spaces - inside lock)

**Quick Fix Command** (Linux/Mac):
```bash
cd /home/wschay/ai-group-chat-streamlit
# Create backup
cp backend/main.py backend/main.py.backup

# Use Python to programmatically fix the indentation
python3 << 'EOF'
with open('backend/main.py', 'r') as f:
    lines = f.readlines()

# Find the join_room function
in_join_room = False
join_room_start = None
function_indent = None
lock_added = False

for i, line in enumerate(lines):
    # Find function start
    if 'async def join_room(' in line:
        in_join_room = True
        join_room_start = i
        # Detect base indentation
        function_indent = len(line) - len(line.lstrip())
        continue
    
    # Add lock at the right place (after docstring, before first real code)
    if in_join_room and not lock_added and '# Log authentication status' in line:
        # Insert lock initialization before this line
        indent = ' ' * function_indent
        lock_code = [
            f"{indent}    # Initialize lock for this room if needed (before any room operations)\n",
            f"{indent}    if room_code not in room_locks:\n",
            f"{indent}        room_locks[room_code] = asyncio.Lock()\n",
            f"{indent}    \n",
            f"{indent}    # CRITICAL: Use lock to prevent race conditions during join\n",
            f"{indent}    async with room_locks[room_code]:\n",
        ]
        lines = lines[:i] + lock_code + lines[i:]
        lock_added = True
        
        # Now indent all lines from here until the function ends
        # This is complex, so marking for manual review
        break

with open('backend/main.py', 'w') as f:
    f.writelines(lines)
    
print("Partial fix applied. Manual indentation of function body required.")
print("Please use an IDE to indent all code inside join_room by 4 spaces.")
EOF
```

**Manual Alternative** (Recommended):
1. Open `backend/main.py` in your IDE
2. Go to line ~3890 (start of join_room logic)
3. Add these lines BEFORE the first "# Log authentication status":
   ```python
   # Initialize lock for this room if needed (before any room operations)
   if room_code not in room_locks:
       room_locks[room_code] = asyncio.Lock()
   
   # CRITICAL: Use lock to prevent race conditions during join
   async with room_locks[room_code]:
   ```
4. Select ALL code from "# Log authentication status" down to the final `return` statement of join_room
5. Press TAB (or indent by 4 spaces) to move everything inside the `async with` block
6. Verify indentation is correct

**Verification**:
- Run `python3 -m py_compile backend/main.py` to check syntax
- Look for the pattern:
  ```python
  async with room_locks[room_code]:
      # Log authentication status
      if current_user:
          print(...)
  ```
  (Notice the 4-space indent)

---

## P0-2: Implement Automatic Room Cleanup

**File**: `backend/main.py`
**Location**: Add new background task

### Implementation:

Add this function AFTER the `startup_event` function:

```python
async def periodic_room_cleanup():
    """
    Background task to clean up abandoned rooms.
    Runs every 10 minutes.
    """
    while True:
        try:
            await asyncio.sleep(600)  # 10 minutes
            
            print("\n🧹 Running periodic room cleanup...")
            current_time = time.time()
            rooms_to_delete = []
            
            for room_code, room_data in rooms.items():
                room_status = room_data.get('room_status', '')
                created_at = room_data.get('created_at', 0)
                age_minutes = (current_time - created_at) / 60
                
                # Rule 1: Waiting rooms with no humans for > 60 minutes
                if room_status == 'waiting':
                    current_humans = room_data.get('current_humans', [])
                    if len(current_humans) == 0 and age_minutes > 60:
                        print(f"🗑️  Cleanup: Waiting room {room_code} abandoned for {age_minutes:.1f}m")
                        rooms_to_delete.append(room_code)
                        continue
                
                # Rule 2: In-progress rooms with no active connections for > 30 minutes
                if room_status == 'in_progress':
                    connections = room_data.get('connections', {})
                    if len(connections) == 0 and age_minutes > 30:
                        print(f"🗑️  Cleanup: In-progress room {room_code} abandoned for {age_minutes:.1f}m")
                        rooms_to_delete.append(room_code)
                        continue
                
                # Rule 3: Completed rooms older than 2 hours
                if room_status == 'completed' and age_minutes > 120:
                    print(f"🗑️  Cleanup: Completed room {room_code} aged {age_minutes:.1f}m")
                    rooms_to_delete.append(room_code)
                    continue
            
            # Delete identified rooms
            for room_code in rooms_to_delete:
                if room_code in rooms:
                    del rooms[room_code]
                if room_code in room_locks:
                    del room_locks[room_code]
                print(f"✅ Cleaned up room {room_code}")
            
            if rooms_to_delete:
                print(f"🧹 Cleanup complete: Removed {len(rooms_to_delete)} rooms")
            else:
                print("🧹 Cleanup complete: No rooms to remove")
                
        except Exception as e:
            print(f"❌ Error in periodic cleanup: {e}")
            import traceback
            traceback.print_exc()
```

Add this line in the `startup_event` function:

```python
@app.on_event("startup")
async def startup_event():
    """Initialize database and MTurk client on application startup."""
    await init_db()
    
    # ... existing MTurk and cashout monitor code ...
    
    # Start periodic room cleanup task
    asyncio.create_task(periodic_room_cleanup())
    print("🧹 Started periodic room cleanup task")
    
    # Configuration validation already done by env_config module at import time
```

---

## P0-3: Fix player_user_map Cleanup

**File**: `backend/main.py`
**Function**: `leave_room_endpoint` (starts at line ~3727)

### Implementation:

Replace the CASE 3 section with:

```python
# CASE 3: Multi-player game in progress - Keep room alive, remove player from current_humans
# Player might rejoin, so keep them in game state
if player_id in current_humans:
    current_humans.remove(player_id)
    print(f"👋 Removed {player_id} from current_humans in room {room_code}. Remaining: {current_humans}")

# IMPORTANT: Also remove from player_user_map when explicitly leaving
# This allows the user to join other games
player_user_map = room.get('player_user_map', {})
if player_id in player_user_map:
    removed_user_id = player_user_map.pop(player_id)
    print(f"🗑️  Removed {player_id} from player_user_map (user_id: {removed_user_id[:8]}...)")

# DO NOT remove from game state - they can still see the game results
# DO NOT add back their number to available_numbers - it stays assigned

# Note: We keep the room alive even if current_humans is empty
# The room will be cleaned up by the periodic cleanup task or when the game ends

return {
    "success": True,
    "action": "disconnected",
    "message": f"Player disconnected from room. {len(current_humans)} players currently connected"
}
```

---

## P1-1: Fix current_humans Consistency

**File**: `backend/main.py`
**Function**: `join_room` - Rejoin section (lines ~3940)

### Implementation:

Replace the rejoin "add back to current_humans" section:

```python
# Add back to current_humans if not there (CHECK FOR DUPLICATES)
if player_id not in current_humans:
    current_humans.append(player_id)
    print(f"✅ Added {player_id} back to current_humans. Total: {len(current_humans)}")
else:
    print(f"ℹ️  {player_id} already in current_humans (possible duplicate avoided)")
```

---

## P1-2: Validate Rejoin Against Room Status

**File**: `backend/main.py`
**Function**: `join_room` - Rejoin section (lines ~3933)

### Implementation:

Add status validation at the START of the rejoin block:

```python
# HANDLE REJOIN: Check if user is already in THIS room (disconnected and rejoining)
if current_user and room_code in rooms:
    user_id = str(current_user.id)
    room = rooms[room_code]
    room_status = room.get('room_status', '')
    
    # VALIDATION: Don't allow rejoin to completed games
    if room_status == 'completed':
        return {
            "success": False,
            "error": "This game has already been completed. You cannot rejoin."
        }
    
    player_user_map = room.get('player_user_map', {})
    
    for player_id, mapped_user_id in player_user_map.items():
        if mapped_user_id == user_id:
            # ... rest of rejoin logic ...
```

---

## Testing After Fixes

### Test 1: Concurrent Join
```bash
# Terminal 1
curl -X POST http://localhost:8000/api/rooms/TEST01/join -H "Content-Type: application/json" -d '{}' &

# Terminal 2 (simultaneously)
curl -X POST http://localhost:8000/api/rooms/TEST01/join -H "Content-Type: application/json" -d '{}' &

# Verify: Only correct number of players joined
```

### Test 2: Room Cleanup
```python
# Create abandoned room
# Wait 11 minutes
# Check logs for cleanup message
```

### Test 3: Leave and Rejoin
```python
# User joins room A
# User leaves room A (explicit leave)
# User tries to join room B
# Should succeed (not blocked by room A)
```

---

## Summary of Changes

| Fix | File | Function/Location | Lines Changed | Complexity |
|-----|------|-------------------|---------------|------------|
| P0-1 | main.py | join_room | ~250 lines indented | HIGH |
| P0-2 | main.py | New function + startup | ~60 lines added | MEDIUM |
| P0-3 | main.py | leave_room_endpoint | ~5 lines modified | LOW |
| P1-1 | main.py | join_room (rejoin) | ~3 lines modified | LOW |
| P1-2 | main.py | join_room (rejoin) | ~8 lines added | LOW |

**Total Impact**: ~326 lines of code changes

**Estimated Time**: 
- P0 fixes: 2-3 hours (including testing)
- P1 fixes: 30 minutes
- **Total: 2.5-3.5 hours**

---

## Post-Implementation Checklist

- [ ] All Python syntax is valid (`python3 -m py_compile backend/main.py`)
- [ ] No linting errors (`pylint backend/main.py` or similar)
- [ ] Manual testing of join/leave/rejoin flows
- [ ] Load testing with concurrent requests
- [ ] Monitor logs for cleanup task running
- [ ] Check memory usage before/after cleanup runs
- [ ] Verify no users are blocked from joining rooms after leaving

---

**READY FOR IMPLEMENTATION**

