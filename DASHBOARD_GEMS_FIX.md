# Dashboard Gems Display Fix - Implementation Complete

## Problem
In multi-player games, losers were seeing the same gem amount as winners on their dashboard because the session-level `calculated_earnings` field stored only the first player's gems.

## Solution Implemented
Added per-player gem tracking to the `SessionPlayer` table and updated the dashboard query logic to use player-specific data.

## Changes Made

### 1. Database Model Update
**File**: `backend/database.py` (line ~212)

Added `gems_earned` field to the `SessionPlayer` model:
```python
gems_earned = Column(Integer, nullable=True)  # Gems credited/debited for this player (can be negative for losses)
```

### 2. Database Migration
**File**: `backend/alembic/versions/010_add_session_player_gems.py` (NEW)

Created Alembic migration to add the `gems_earned` column to the `session_players` table:
- Revision ID: 010
- Revises: 009
- Column is nullable for backward compatibility with old records

### 3. Session Saving Logic Update
**File**: `backend/main.py` (lines ~2476-2509)

Updated the `save_session_stats` function to store gems_earned when creating SessionPlayer records:
```python
# Find gems_earned for this player from credited_players list
player_gems = None
for credited_player in credited_players:
    if credited_player['player_id'] == player_id:
        player_gems = credited_player['gems_earned']
        print(f"      💎 Gems earned: {player_gems}")
        break

session_player = SessionPlayer(
    session_id=session_id,
    user_id=user_uuid,
    player_id=player_id,
    role=role,
    gems_earned=player_gems  # NEW: Store per-player gems
)
```

### 4. Dashboard Query Logic Update
**File**: `backend/main.py` (lines ~3841-3867)

Updated the `get_user_earnings` function to use `SessionPlayer.gems_earned` as a fallback:

**New fallback order**:
1. **PRIMARY**: Load from JSON file (existing)
2. **NEW FALLBACK 1**: Query `SessionPlayer.gems_earned` for user-specific value
3. **FALLBACK 2**: Use `calculated_earnings` (legacy, for old data)
4. **LAST RESORT**: Use average per game

```python
# METHOD 1: Try SessionPlayer.gems_earned (per-player accurate value)
try:
    from .database import SessionPlayer
    player_result = await db.execute(
        select(SessionPlayer).where(
            SessionPlayer.session_id == session.id,
            SessionPlayer.user_id == current_user.id
        )
    )
    user_player = player_result.scalar_one_or_none()
    if user_player and user_player.gems_earned is not None:
        actual_gems = user_player.gems_earned
        display_amount = actual_gems
        print(f"   Session {idx}: {actual_gems} gems (from SessionPlayer.gems_earned)")
except Exception as sp_error:
    print(f"   Session {idx}: Could not query SessionPlayer: {sp_error}")
```

## How It Works

### Before Fix
```
Game Complete:
- Winner earns +500 gems
- Loser loses -400 gems
- Session.calculated_earnings = $0.50 (first player's value)

Dashboard Display (when JSON fails):
- Winner sees: 500 gems ✅
- Loser sees: 500 gems ❌ (WRONG - using session-level value)
```

### After Fix
```
Game Complete:
- Winner earns +500 gems
- Loser loses -400 gems
- Session.calculated_earnings = $0.50 (legacy, still set)
- SessionPlayer[winner].gems_earned = 500
- SessionPlayer[loser].gems_earned = -400

Dashboard Display (when JSON fails):
- Winner sees: 500 gems ✅ (from SessionPlayer.gems_earned)
- Loser sees: -400 gems ✅ (from SessionPlayer.gems_earned)
```

## Migration Instructions

### Step 1: Run Database Migration
```bash
cd backend
alembic upgrade head
```

This will add the `gems_earned` column to the `session_players` table.

### Step 2: Verify Migration
Check that the migration was successful:
```bash
# For SQLite
sqlite3 group_chat.db ".schema session_players"
```

You should see the `gems_earned` column in the table schema.

### Step 3: Restart Backend
Restart the backend server to load the updated code:
```bash
# Stop current backend process
# Then restart with:
cd backend
uvicorn main:app --reload
```

## Testing Checklist

### Test Case 1: Multi-Player Game (Winner)
1. Create a multi-player game with stakes
2. Play as the winner (get most votes)
3. Complete the game
4. Go to `/dashboard`
5. **Expected**: "Last Game" shows positive gems (e.g., +500 gems)
6. **Expected**: "Recent Games" chart shows positive bar

### Test Case 2: Multi-Player Game (Loser)
1. Create a multi-player game with stakes
2. Play as the loser (get fewer votes)
3. Complete the game
4. Go to `/dashboard`
5. **Expected**: "Last Game" shows negative gems (e.g., -400 gems)
6. **Expected**: "Recent Games" chart shows negative bar (red)

### Test Case 3: Single-Player Game
1. Play a single-player game
2. Complete the game
3. Go to `/dashboard`
4. **Expected**: "Last Game" shows correct gems (e.g., +50 gems)

### Test Case 4: Backward Compatibility
1. Check dashboard for old games (played before migration)
2. **Expected**: Old games still display using fallback logic (calculated_earnings or average)
3. **Expected**: No errors in logs

## Verification Points

### Backend Logs
When a new game completes, you should see:
```
🔹 Player Player 1 (human): mapped_user_id = ...
  ✅ Mapped to user ...
  💎 Gems earned: 500
  💾 SessionPlayer record added (user_id=..., gems_earned=500)

🔹 Player Player 2 (human): mapped_user_id = ...
  ✅ Mapped to user ...
  💎 Gems earned: -400
  💾 SessionPlayer record added (user_id=..., gems_earned=-400)
```

### Dashboard Query Logs
When viewing the dashboard, you should see:
```
Session 0: 500 gems (from SessionPlayer.gems_earned)
✅ Last game gems set to: 500 (net change)
```

For losers:
```
Session 0: -400 gems (from SessionPlayer.gems_earned)
✅ Last game gems set to: -400 (net change)
```

## Files Modified
1. ✅ `backend/database.py` - Added `gems_earned` field to SessionPlayer model
2. ✅ `backend/alembic/versions/010_add_session_player_gems.py` - Created migration
3. ✅ `backend/main.py` - Updated session saving logic (~line 2495)
4. ✅ `backend/main.py` - Updated dashboard query logic (~line 3841)

## Backward Compatibility
- Old sessions (before this fix) will use fallback logic
- `gems_earned` column is nullable, so old SessionPlayer records won't break
- Dashboard will gracefully fall back to `calculated_earnings` then average for old data
- New sessions will have accurate per-player gems

## Status
✅ **IMPLEMENTATION COMPLETE**

All code changes have been made. The migration needs to be run and the system tested with multi-player games to verify the fix works correctly.

