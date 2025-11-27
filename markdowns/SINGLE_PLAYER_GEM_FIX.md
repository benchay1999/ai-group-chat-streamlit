# Single Player Game Gem Earning Fix

## Date: October 31, 2025

## Problem Statement

Players in single-player games (1 human + N AIs) were not earning gems because they could never "win" according to the game logic, even when they correctly identified an AI.

### Root Cause

The win determination logic had a flaw for single-player scenarios:

1. **Voting Process**: The suspect is determined by whoever gets the most votes
2. **Single-Player Issue**: AIs collectively outvote the single human player
3. **Result**: The human becomes the suspect (even if they correctly voted for an AI)
4. **Win Check**: The code only counted it as a "win" if:
   - The selected suspect was an AI (`suspect_role == 'ai'`)
   - AND the player voted for that AI

Since the human was selected as the suspect, `suspect_role == 'human'`, so the win condition was never met.

## Solution Implemented

### 1. Fixed Win Logic for Single-Player Games

**Location**: `/home/wschay/ai-group-chat-streamlit/backend/main.py` (lines 1129-1151)

**Change**: Added separate logic for single-player games:

```python
# FIXED: For single-player games, check if player voted for an AI (regardless of who was selected as suspect)
if num_humans == 1:
    # Single-player game: check if they voted for an AI
    player_vote = state.get('votes', {}).get(human_player['id'])
    if player_vote:
        for p in state.get('players', []):
            if p['id'] == player_vote and p.get('role') == 'ai':
                won_game = True
                break
else:
    # Multi-player game: use original logic (only win if the AI was actually selected as suspect)
    if state.get('selected_suspect') and state.get('suspect_role') == 'ai':
        player_vote = state.get('votes', {}).get(human_player['id'])
        if player_vote:
            for p in state.get('players', []):
                if p['id'] == player_vote and p.get('role') == 'ai':
                    won_game = True
                    break
```

**Result**: Players in single-player games now get the win bonus ($0.50) if they vote for an AI, regardless of the voting outcome.

### 2. Added 2000 Gems Bonus for Single-Player Games (TEMPORARY)

**Location**: `/home/wschay/ai-group-chat-streamlit/backend/main.py` (lines 1181-1185)

**Purpose**: To test MTurk payment system by ensuring players get a substantial gem amount

**Change**: Added flat 2000 gems bonus for single-player games:

```python
# TEMPORARY: Add 2000 gems bonus for single-player games (for MTurk testing)
# TODO: Remove this temporary bonus after MTurk payment system is verified
if num_humans == 1:
    gems_earned += 2000
    print(f"🎁 BONUS: Added 2000 gems for single-player game (temporary for MTurk testing)")
```

**Important**: This is marked as TEMPORARY and should be removed after MTurk payment verification is complete.

## Expected Earnings After Fix

### Single-Player Game (with win + participation):
- Base earning: $0.25
- Win bonus: $0.50 (now awarded correctly!)
- Vote bonus: $0.10
- Participation multiplier: 0.5x - 1.5x
- **Example total**: ~$0.42 - $1.27 USD = **420 - 1270 gems**
- **Plus temporary bonus**: +2000 gems
- **Total**: **2420 - 3270 gems per game**

### Multi-Player Game (unchanged):
- Same formula as before
- Win logic unchanged (requires collective voting to identify AI)

## Testing Recommendations

1. **Single-Player Game Test**:
   - Create a game with 1 human player
   - Play through and vote for an AI
   - Verify gems are awarded (should include win bonus + 2000 temporary bonus)
   - Check console logs for "🎁 BONUS" message

2. **Multi-Player Game Test**:
   - Create a game with 2+ human players
   - Verify win logic still works as expected
   - Confirm no 2000 gems bonus is applied

3. **MTurk Integration Test**:
   - Test cashout flow with gems earned from single-player games
   - Verify redemption codes are generated correctly
   - Confirm MTurk payments process successfully

## Future Actions

**When MTurk payment system is verified:**
1. Remove the temporary 2000 gems bonus (lines 1181-1185)
2. Keep the fixed win logic for single-player games (permanent fix)
3. Update this document with verification date

## Critical Bug Fix (October 31, 2025 - Second Update)

### Issue: No Gems Were Being Credited

**Root Cause**: The `save_session_stats` function was being called without the `current_user` parameter at line 555:

```python
await save_session_stats(room_code, state)  # Missing user info!
```

This meant the gem crediting logic never executed because it checked `if current_user:` which was always `None`.

### Solution: Restructured Gem Crediting

**Changed**: Modified gem crediting to work with ALL authenticated players in the game, not just one `current_user`:

1. **Removed dependency on `current_user` parameter**: Instead of expecting a single user to be passed in, the function now:
   - Reads `player_user_map` from room data (which maps player_id → user_id)
   - Iterates through all human players in the game
   - Credits gems to each authenticated player individually

2. **Per-player earnings calculation**: Each player now gets their own:
   - Message count
   - Vote status
   - Win determination (with single-player fix)
   - Earnings calculation
   - Gem credit

3. **Works for both single and multi-player games**: All authenticated human players get gems credited automatically.

**Result**: Gems are now correctly credited when games end, regardless of how `save_session_stats` is called.

## Files Modified

- `/home/wschay/ai-group-chat-streamlit/backend/main.py` (3 changes in `save_session_stats` function)
  - Removed redundant user-finding code (lines 1110-1162 → simplified to 1108-1109)
  - Restructured gem crediting to iterate all authenticated players (lines 1169-1254)
  - Now works without requiring `current_user` parameter

## Related Files

- `/home/wschay/ai-group-chat-streamlit/backend/earnings.py` - Earnings calculation formulas
- `/home/wschay/ai-group-chat-streamlit/backend/config.py` - GEMS_PER_DOLLAR constant (1000)
- `/home/wschay/ai-group-chat-streamlit/backend/cashout_service.py` - Gem redemption system

