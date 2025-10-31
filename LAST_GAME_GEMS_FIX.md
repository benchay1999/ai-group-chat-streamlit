# Last Game Gems Display Fix

## Problem

The "Last Game" metric on the dashboard was showing **0 gems** instead of the correct amount (e.g., **2000 gems** for single-player games with the temporary bonus).

## Root Cause

When saving a game session, we were storing the `calculated_earnings` field BEFORE adding bonuses:

```python
# OLD CODE (❌ WRONG)
# Line 1250
calculated_earnings_value = player_earnings_value  # Base earnings only!

# But gems_earned includes the bonus:
# Line 1222: gems_earned += 2000  # Bonus added here
```

**Flow:**
1. Player plays single-player game
2. Base earnings calculated: $0.35 (350 gems)
3. Bonus added: 350 + 2000 = **2350 gems** credited to user
4. But `calculated_earnings` stored: **$0.35** (only base amount)
5. Later when displaying "Last Game":
   - Read `calculated_earnings = 0.35`
   - Convert to gems: 0.35 * 1000 = **350 gems**
   - Missing the 2000 bonus! ❌

## The Fix

Store the TOTAL gems earned (including all bonuses) in the `calculated_earnings` field:

### File: `backend/main.py` (Lines 1248-1253)

```python
# Store for legacy session.calculated_earnings field (use TOTAL gems earned including bonuses)
if not calculated_earnings_value and current_user and str(current_user.id) == str(mapped_user_uuid):
    # Convert total gems earned (including bonuses) back to USD for storage
    from .cashout_service import gems_to_usd
    calculated_earnings_value = gems_to_usd(gems_earned)  # ✅ Use gems_earned (with bonus)
    print(f"📊 Session calculated_earnings set to ${calculated_earnings_value} ({gems_earned} gems total)")
```

**Now:**
1. Player plays single-player game
2. Base earnings: $0.35 (350 gems)
3. Bonus added: 350 + 2000 = **2350 gems**
4. `calculated_earnings` stored: **$2.35** (total including bonus) ✅
5. Later when displaying "Last Game":
   - Read `calculated_earnings = 2.35`
   - Convert to gems: 2.35 * 1000 = **2350 gems** ✅

## Verification

### Backend Logs

When a game completes, you'll now see:

```
💎 Credited 2350 gems to user alice (base: $0.35)
   Balance: 0 → 2350 gems
   Total games played: 1
📊 Session calculated_earnings set to $2.35 (2350 gems total)  ← NEW LOG
✅ Gem credit complete: 1/1 players credited
```

### Dashboard Display

After the fix:
- ✅ **Last Game**: Shows `2350 gems` (not 0 or 350)
- ✅ **Avg/Game**: Calculates correctly based on total gems earned
- ✅ **Chart**: Shows correct gem amounts per session

## Why This Matters

The `calculated_earnings` field is used to:
1. Display "Last Game" amount on dashboard
2. Show earnings trend in the chart
3. Calculate highest single game earnings
4. Provide historical earnings data

If it doesn't include bonuses, all these metrics are incorrect!

## Database Schema

```python
class Session(Base):
    calculated_earnings = Column(DECIMAL(10, 2), nullable=True)  
    # Now stores: TOTAL gems earned converted to USD (includes all bonuses)
```

## Example Calculations

### Single-Player Game (with 2000 gem bonus)

| Metric | Before Fix | After Fix |
|--------|-----------|-----------|
| Base earnings | $0.35 (350 gems) | $0.35 (350 gems) |
| Bonus | +2000 gems | +2000 gems |
| **Total credited** | 2350 gems | 2350 gems |
| **`calculated_earnings` stored** | $0.35 ❌ | $2.35 ✅ |
| **"Last Game" displayed** | 350 gems ❌ | 2350 gems ✅ |

### Multi-Player Game (no bonus)

| Metric | Before Fix | After Fix |
|--------|-----------|-----------|
| Earnings | $0.45 (450 gems) | $0.45 (450 gems) |
| Bonus | None | None |
| **Total credited** | 450 gems | 450 gems |
| **`calculated_earnings` stored** | $0.45 ✅ | $0.45 ✅ |
| **"Last Game" displayed** | 450 gems ✅ | 450 gems ✅ |

## Testing Instructions

1. **Restart backend:**
   ```bash
   cd /home/wschay/ai-group-chat-streamlit
   bash & conda activate group-chat & uvicorn backend.main:app --host 0.0.0.0 --port 8000 --reload
   ```

2. **Play a single-player game:**
   - Log in
   - Start a game with 1 human + AIs
   - Complete the game

3. **Check backend logs:**
   ```
   📊 Session calculated_earnings set to $2.35 (2350 gems total)
   ```

4. **Check dashboard:**
   - Go to `/dashboard`
   - Look at "Last Game" metric
   - Should show **2350 gems** (or whatever total was earned)

5. **Verify chart:**
   - Hover over chart data points
   - Should show correct gem amounts including bonuses

## Related Changes

This fix works in conjunction with the earnings display redesign:

- **Backend** (`backend/main.py` line 1252): Store total gems in `calculated_earnings`
- **Frontend** (`frontend/src/pages/DashboardPage.jsx` line 220): Display `last_game_gems`
- **API** (`backend/main.py` line 2344-2352): Convert `calculated_earnings` back to gems for display

## Backward Compatibility

**For old sessions** (saved before this fix):
- They still have `calculated_earnings` with only base amount
- Dashboard will show lower values for those historical sessions
- **New sessions** will show correct total amounts
- This is acceptable - historical data remains as-is, new data is correct

## Related Files

- ✅ `backend/main.py` (lines 1248-1253)
- 📚 `backend/main.py` (lines 2344-2352 - reads and converts back to gems)
- 📚 `backend/database.py` (Session model, line 118 - `calculated_earnings` field)
- 📚 `frontend/src/pages/DashboardPage.jsx` (displays last_game_gems)

---

**Status**: ✅ **FIXED**

The "Last Game" metric now correctly displays the total gems earned, including all bonuses like the temporary 2000 gem bonus for single-player games.

