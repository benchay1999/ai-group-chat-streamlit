# Vote Command & Rounds Configuration Update

## Summary of Changes

Two new features have been implemented:

1. **`/vote` Command**: Players can now vote directly in the game channel using a slash command
2. **Default Rounds**: Changed from 3 rounds to 1 round (single elimination game)

---

## Feature 1: `/vote` Command

### Overview

Players can now vote in two ways during the voting phase:
- **Option 1 (NEW)**: Use `/vote <player>` command in the game channel
- **Option 2**: Continue using DM voting with dropdown menu

### How to Use

**Basic Usage:**
```
/vote Player 1
/vote Human_1
/vote Player 2
```

**Fuzzy Matching:**
The command supports partial matching, so these all work:
```
/vote player 1    (lowercase)
/vote player      (partial match)
/vote 1           (just the number)
```

### Features

- ✅ **Private voting**: Only the voter sees the confirmation message (ephemeral response)
- ✅ **Validation**: Checks if it's voting phase, if player is in game, if target is valid
- ✅ **One vote only**: Cannot change vote once cast
- ✅ **Fuzzy matching**: Supports partial player name matching
- ✅ **Error messages**: Clear feedback for invalid votes
- ✅ **Works alongside DM voting**: Both methods work simultaneously

### Implementation Details

**Files Modified:**

1. **`discord_bot/coordinator_bot.py`**
   - Added `/vote` command registration (lines 99-103)
   - Implemented `vote_impl()` method (lines 442-493)

2. **`discord_bot/game_manager.py`**
   - Added `handle_channel_vote()` method (lines 431-499)
   - Updated voting phase message to show both options (lines 415-426)
   - Lists all active players when voting phase starts

3. **`discord_bot/README.md`**
   - Updated voting phase documentation
   - Added `/vote` to command list

### Example Flow

```
[Voting Phase Starts]

Bot: 🗳️ Voting Phase Started!

     How to vote:
     • Use /vote <player> command in this channel
     • Or check your DMs for the voting menu

     Active Players: Player 1, Player 2, Player 3, Human_1
     ⏰ You have 60 seconds to vote!

[Player types: /vote Player 1]

Bot (only to voter): ✅ Vote recorded for Player 1

[Voting ends]

Bot: ⚔️ Elimination Results
     Player 1 has been eliminated!
     ...
```

### Error Messages

| Error | Message |
|-------|---------|
| Not in a game | "❌ You're not in a game!" |
| Game not in progress | "❌ Game is not in progress!" |
| Not voting phase | "❌ Not in voting phase (current phase: Discussion)" |
| Player eliminated | "❌ You've been eliminated and cannot vote" |
| Already voted | "❌ You've already voted! (Vote cannot be changed)" |
| Invalid player | "❌ Invalid player. Available players: Player 1, Player 2..." |

---

## Feature 2: Default Rounds Changed to 1

### Overview

The default number of rounds required for humans to win has been changed from **3 rounds** to **1 round**, making games faster and more accessible.

### What Changed

**Before:**
- Humans needed to survive 3 elimination rounds to win
- Games could take 15-20 minutes

**After:**
- Humans win after surviving 1 elimination round
- Games are faster (5-10 minutes)
- Still configurable via environment variable

### Configuration

**File Modified:** `backend/config.py` (line 13)

```python
# Before:
ROUNDS_TO_WIN = int(os.getenv("ROUNDS_TO_WIN", "3"))

# After:
ROUNDS_TO_WIN = int(os.getenv("ROUNDS_TO_WIN", "1"))
```

### How to Change

To use a different number of rounds, set the environment variable:

```bash
# In .env file or environment
ROUNDS_TO_WIN=3    # For 3 rounds (original)
ROUNDS_TO_WIN=1    # For 1 round (new default)
ROUNDS_TO_WIN=5    # For 5 rounds
```

### Game Flow with 1 Round

```
Round 1:
├─ Discussion Phase (3 minutes)
├─ Voting Phase (1 minute)
├─ Elimination (1 player eliminated)
└─ Game Ends
   ├─ If human survived → Humans Win 🎉
   └─ If all humans eliminated → AI Wins 🤖
```

### Documentation Updated

- `discord_bot/README.md` - Updated win conditions section
- Changed "Survive 3 rounds" to "Survive 1 round (default, configurable)"

---

## Testing the Features

### Test `/vote` Command

1. **Start a game:**
   ```
   /create max_humans:2 total_players:6
   ```

2. **Wait for voting phase**

3. **Try voting:**
   ```
   /vote Player 1
   ```

4. **Verify:**
   - ✅ You see ephemeral confirmation message
   - ✅ Other players don't see your vote
   - ✅ Trying to vote again shows error
   - ✅ Results shown at end of voting phase

### Test 1 Round Game

1. **Start a game and play through:**
   - Discussion phase
   - Voting phase
   - One elimination

2. **Verify game ends after 1 round:**
   - ✅ If human survives → "Humans Win!" message
   - ✅ If human eliminated → "AI Wins!" message
   - ✅ No second round starts

---

## Benefits

### `/vote` Command Benefits

1. **Convenience**: Faster than opening DMs
2. **Accessibility**: Works for users with DMs disabled
3. **Flexibility**: Players can choose their preferred method
4. **Transparency**: See who hasn't voted yet (via timeout)
5. **Mobile-friendly**: Easier on mobile devices

### 1 Round Default Benefits

1. **Faster games**: 5-10 minutes instead of 15-20 minutes
2. **Lower barrier to entry**: New players can try quickly
3. **More games possible**: Play multiple games in a session
4. **Still configurable**: Can increase for longer games
5. **Better for Discord**: Doesn't require long time commitment

---

## Backward Compatibility

Both features maintain backward compatibility:

- ✅ DM voting still works (not removed)
- ✅ Can still configure rounds via environment variable
- ✅ Existing games continue to work
- ✅ No breaking changes to API

---

## Technical Notes

### Vote Command Implementation

The `handle_channel_vote()` method:
- Uses async lock for thread-safe vote recording
- Validates player status (active, not eliminated, not already voted)
- Implements fuzzy matching for player names
- Returns tuple `(success: bool, message: str)` for clean error handling

### Rounds Configuration

The `ROUNDS_TO_WIN` is used in:
- `backend/langgraph_game.py` - Win condition check
- Game logic throughout the backend
- No Discord-specific changes needed

---

## Future Enhancements

Possible improvements:

1. **Vote autocomplete**: Add autocomplete to `/vote` command with player list
2. **Vote tracker**: Show who has voted (without revealing who they voted for)
3. **Vote countdown**: Visual countdown timer in channel
4. **Quick game mode**: Even faster games with shorter discussion time
5. **Tournament mode**: Multiple games with leaderboard

---

## Commands Reference

### New Command

```
/vote <player>        Cast your vote during voting phase
                      Example: /vote Player 1
```

### All Commands

```
/lobby               Open the game lobby
/create              Create a new game room
/join <code>         Join a game room
/leave               Leave your current room
/rooms               List all active rooms
/vote <player>       Cast your vote (NEW!)
```

---

## Configuration Reference

### Environment Variables

```bash
# Game configuration
ROUNDS_TO_WIN=1              # Number of rounds humans must survive (default: 1)
DISCUSSION_TIME=180          # Discussion phase duration in seconds (default: 180)
VOTING_TIME=60               # Voting phase duration in seconds (default: 60)

# AI configuration
NUM_AI_PLAYERS=4             # Number of AI players (default: 4)
AI_MODEL_NAME=gpt-4o-mini    # AI model to use
OPENAI_API_KEY=sk-...        # OpenAI API key
```

---

## Troubleshooting

### `/vote` command not working?

1. Check bot has been restarted after update
2. Verify commands are synced: Look for "Commands synced" in logs
3. Make sure you're in voting phase
4. Confirm you're spelling player name correctly

### Games ending too quickly?

1. Check `ROUNDS_TO_WIN` environment variable
2. Default is now 1 round
3. Set `ROUNDS_TO_WIN=3` for longer games
4. Restart bot after changing environment

### Vote not registering?

1. Check if voting phase is active
2. Verify player name is correct (use autocomplete)
3. Check if you already voted (can't change vote)
4. Look in logs for detailed error messages

---

## Rollback Instructions

If needed, you can revert these changes:

### Revert to 3 rounds:
```bash
# Set environment variable
export ROUNDS_TO_WIN=3

# Or edit backend/config.py line 13:
ROUNDS_TO_WIN = int(os.getenv("ROUNDS_TO_WIN", "3"))
```

### Disable `/vote` command:
The DM voting still works, so `/vote` is optional. To remove it:
1. Comment out lines 99-103 in `discord_bot/coordinator_bot.py`
2. Restart bot

---

## Summary

✅ **`/vote` command** added for convenient in-channel voting
✅ **Default rounds** changed to 1 for faster games
✅ **Both features** are configurable and backward compatible
✅ **Documentation** updated in README
✅ **No breaking changes** to existing functionality

Restart the bot to apply these changes!

