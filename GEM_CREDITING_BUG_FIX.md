# Gem Crediting Bug Fix

## Date: October 31, 2025

## Problem

**Symptom**: No gems were being added when finishing a group chat game.

## Root Cause

The `save_session_stats()` function was being called **without user information**:

```python
# Line 555 in backend/main.py
await save_session_stats(room_code, state)  # ❌ No user parameter!
```

The gem crediting logic inside `save_session_stats` required a `current_user` parameter:

```python
if current_user and calculated_earnings_value:
    # Credit gems...
```

Since `current_user` was always `None`, this condition never passed, and **no gems were ever credited**.

## Solution

Completely restructured the gem crediting logic to work **without requiring a `current_user` parameter**.

### Key Changes:

1. **Use `player_user_map` from room data**: This map stores player_id → user_id for all authenticated players
2. **Iterate through all human players**: Calculate earnings and credit gems for each authenticated player
3. **Per-player calculations**: Each player gets their own:
   - Message count
   - Vote status  
   - Win determination (with single-player fix applied)
   - Earnings calculation
   - Gem credit to database

### Code Flow:

```python
# Get player-user mapping from room data
player_user_map = room_data.get('player_user_map', {})

# Process each human player
for player in state.get('players', []):
    if player.get('role') != 'human':
        continue
    
    mapped_user_id = player_user_map.get(player['id'])
    if not mapped_user_id:
        continue  # Skip unauthenticated players
    
    # Calculate earnings for this player
    earnings = calculate_earnings(...)
    
    # Credit gems to their account
    db_user = get_user(mapped_user_id)
    db_user.gem_balance += gems_earned
    db_user.total_gems_earned += gems_earned
```

## Benefits

✅ **Works for all game types**: Single-player, multi-player
✅ **Credits all players**: Not just one user
✅ **No parameter dependency**: Works regardless of how `save_session_stats` is called
✅ **Robust error handling**: Catches exceptions per player, doesn't fail entire batch
✅ **Detailed logging**: Shows exactly which players get gems and why

## Testing

1. ✅ Single-player game: Gems credited with 2000 bonus
2. ✅ Multi-player game: All authenticated players get gems
3. ✅ Anonymous players: Skipped with warning message
4. ✅ Database errors: Caught per-player, doesn't break batch

## Console Output Example

```
💵 Calculated earnings for Player1: $0.85
💡 Breakdown: {'base': Decimal('0.25'), 'win_bonus': Decimal('0.50'), ...}
🎁 BONUS: Added 2000 gems for single-player game (temporary for MTurk testing)
💎 Credited 2850 gems to user mturk_worker_123 ($0.85)
   New balance: 2850 gems
```

## Files Changed

- `/home/wschay/ai-group-chat-streamlit/backend/main.py`
  - Lines 1105-1109: Simplified initialization
  - Lines 1169-1254: New per-player gem crediting loop

## Related Issues

This fix also ensures the single-player win bonus logic (added earlier) actually works, since gems are now being credited at all.

