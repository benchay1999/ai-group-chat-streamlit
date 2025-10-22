# Testing Guide - Discord Bot

Comprehensive guide for testing the Human Hunter Discord bot.

## 🧪 Pre-Testing Setup

### Prerequisites

- [ ] Discord server with admin permissions (or create test server)
- [ ] 5+ Discord bot applications created and configured
- [ ] All bot tokens in `.env` file
- [ ] OpenAI API key configured
- [ ] Dependencies installed
- [ ] Bot running successfully (`python main.py`)

### Create Test Server (Recommended)

1. In Discord, click "+" to add server
2. Choose "Create My Own"
3. Select "For me and my friends"
4. Name it "Human Hunter Test"
5. Invite all your bots using OAuth2 URLs

## 🔍 Testing Phases

### Phase 1: Bot Connection (5 minutes)

**Goal**: Verify all bots are online and responding

#### Test 1.1: Bot Status
```
Expected: All bots show as online in Discord member list
- [ ] Coordinator bot online (green status)
- [ ] AI Bot 1 online (green status)
- [ ] AI Bot 2 online (green status)
- [ ] AI Bot 3 online (green status)
- [ ] AI Bot 4 online (green status)
```

#### Test 1.2: Slash Commands
```
In any text channel, type "/"
Expected: Human Hunter commands appear in autocomplete
- [ ] /lobby appears
- [ ] /create appears
- [ ] /join appears
- [ ] /leave appears
- [ ] /rooms appears
```

#### Test 1.3: Basic Command
```
Run: /lobby
Expected: Bot posts lobby embed with buttons
- [ ] Embed displays correctly
- [ ] "Create Room" button visible
- [ ] "Join Room" button visible
- [ ] "Refresh" button visible
```

**If Phase 1 fails**: Check bot tokens, intents, permissions, and logs.

---

### Phase 2: Room System (10 minutes)

**Goal**: Test room creation, joining, and waiting rooms

#### Test 2.1: Create Room (Single Player)
```
Run: /create max_humans:1 total_players:5 room_name:Solo Test
Expected:
- [ ] Success message posted
- [ ] Room code displayed (6 characters)
- [ ] Waiting room embed appears
- [ ] Progress bar shows 1/1
- [ ] Your name in player list
- [ ] Game starts automatically (since room is full)
```

#### Test 2.2: Create Room (Multiplayer)
```
Run: /create max_humans:2 total_players:6 room_name:Multi Test
Expected:
- [ ] Success message posted
- [ ] Room code displayed
- [ ] Waiting room embed appears
- [ ] Progress bar shows 1/2
- [ ] Your name in player list
- [ ] "Leave Room" button visible
- [ ] Game does NOT start yet
```

#### Test 2.3: Join Room
```
From second Discord account:
Run: /join room_code:<code from test 2.2>
Expected:
- [ ] Success message (ephemeral)
- [ ] Waiting room embed updates
- [ ] Progress bar shows 2/2
- [ ] Both players listed
- [ ] Game starts automatically
```

#### Test 2.4: List Rooms
```
Run: /rooms
Expected:
- [ ] Shows in-progress room from test 2.3
- [ ] Displays room status
- [ ] Shows player count
```

#### Test 2.5: Leave Room
```
Create room: /create max_humans:2 total_players:6
Then run: /leave
Expected:
- [ ] Success message (left room)
- [ ] Waiting room embed disappears or updates
- [ ] Can create/join other rooms
```

**If Phase 2 fails**: Check room manager logic, channel permissions, and embed formatting.

---

### Phase 3: Game Flow (20 minutes)

**Goal**: Test complete game cycle

#### Test 3.1: Game Start
```
Create single-player game: /create max_humans:1 total_players:5
Expected immediately after creation:
- [ ] "Game Starting!" message
- [ ] Game status embed appears
- [ ] Shows "Round 1"
- [ ] Shows "Discussion Phase"
- [ ] Shows discussion topic
- [ ] Lists all players (1 human + 4 AI)
- [ ] 4 AI bots join the channel
- [ ] AI bots post join messages
```

#### Test 3.2: Discussion Phase
```
During discussion phase:
Post message: "I think pineapple belongs on pizza!"
Expected:
- [ ] Your message appears normally
- [ ] AI bots start responding (within ~20 seconds)
- [ ] AI messages formatted as "Player X: message"
- [ ] Multiple AI bots participate
- [ ] Phase lasts ~3 minutes
```

#### Test 3.3: Voting Phase
```
After discussion time ends:
Expected:
- [ ] "Voting Phase Started!" message in channel
- [ ] You receive a DM from coordinator bot
- [ ] DM contains vote embed
- [ ] DM has dropdown with active players
- [ ] You can select a player
- [ ] Confirmation message after voting
```

#### Test 3.4: Vote Processing
```
After voting (or 60 second timeout):
Expected:
- [ ] Results posted in channel
- [ ] Shows vote breakdown
- [ ] Shows eliminated player
- [ ] Reveals eliminated player's role (human or AI)
- [ ] Shows remaining players
```

#### Test 3.5: Next Round
```
If humans survive:
Expected:
- [ ] "Round 2" message
- [ ] New discussion topic
- [ ] Discussion phase starts again
- [ ] Eliminated players don't participate
```

#### Test 3.6: Game End
```
After human elimination OR surviving 3 rounds:
Expected:
- [ ] Game over embed
- [ ] Shows winner (humans or AI)
- [ ] Shows game statistics
- [ ] Lists all players with roles
- [ ] AI bots leave channel
```

**If Phase 3 fails**: Check game manager, phase transitions, and LangGraph integration.

---

### Phase 4: Multi-Room (15 minutes)

**Goal**: Test concurrent games without interference

#### Test 4.1: Multiple Rooms in Same Channel
```
From Account 1: /create max_humans:1 total_players:5 room_name:Room A
From Account 2: /create max_humans:1 total_players:5 room_name:Room B
Expected:
- [ ] Both games start
- [ ] Both games run simultaneously
- [ ] Messages don't interfere
- [ ] AI bots assigned correctly to each game
- [ ] Votes go to correct game
```

#### Test 4.2: Room Isolation
```
With 2+ concurrent games:
Post message in Room A
Expected:
- [ ] Only Room A's AI bots respond
- [ ] Room B unaffected
- [ ] Vote DMs tagged correctly
```

#### Test 4.3: Lobby with Multiple Rooms
```
Create 2-3 waiting rooms (not full)
Run: /lobby
Expected:
- [ ] All waiting rooms listed
- [ ] Shows player count for each
- [ ] Can join any room from lobby
- [ ] In-progress rooms not shown
```

**If Phase 4 fails**: Check room isolation, player-to-room mapping, and state management.

---

### Phase 5: Edge Cases (10 minutes)

**Goal**: Test error handling and edge cases

#### Test 5.1: Invalid Room Code
```
Run: /join room_code:INVALID
Expected:
- [ ] Error message: "Room not found"
- [ ] Message is ephemeral (only you see it)
```

#### Test 5.2: Join Full Room
```
Create room: /create max_humans:1 (auto-starts)
From another account: /join room_code:<code>
Expected:
- [ ] Error: "Room is full" or "not accepting players"
```

#### Test 5.3: Already in Room
```
Create/join a room
Try to join another room
Expected:
- [ ] Error: "You are already in room X"
```

#### Test 5.4: Invalid Settings
```
Run: /create max_humans:5 total_players:4
Expected:
- [ ] Error: Settings validation failure
```

#### Test 5.5: No DMs Allowed
```
Disable DMs from server members in user settings
Try to play game and vote
Expected:
- [ ] Error logged (check logs)
- [ ] Game continues with timeout
```

**If Phase 5 fails**: Review error handling and input validation.

---

### Phase 6: Performance (15 minutes)

**Goal**: Test under heavier load

#### Test 6.1: Maximum Players
```
Run: /create max_humans:4 total_players:12
Join with 4 accounts (or use bots)
Expected:
- [ ] Game handles 4 humans + 8 AI
- [ ] All players can chat
- [ ] All players can vote
- [ ] Performance acceptable
```

#### Test 6.2: Multiple Concurrent Games
```
Start 3+ games simultaneously in different channels
Expected:
- [ ] All games run smoothly
- [ ] No crashes or errors
- [ ] Response times acceptable
- [ ] Memory usage reasonable
```

#### Test 6.3: Long Running Game
```
Create game and let it run multiple rounds
Expected:
- [ ] Game completes successfully
- [ ] No memory leaks
- [ ] No timeout issues
- [ ] Proper cleanup on end
```

**If Phase 6 fails**: Check for memory leaks, optimize AI response times, add rate limiting.

---

## 📊 Test Results Template

Use this to track your testing:

```
Test Date: _______________
Tester: _______________
Environment: Production / Test Server

Phase 1: Bot Connection
- [ ] All tests passed
- Issues: _______________

Phase 2: Room System
- [ ] All tests passed
- Issues: _______________

Phase 3: Game Flow
- [ ] All tests passed
- Issues: _______________

Phase 4: Multi-Room
- [ ] All tests passed
- Issues: _______________

Phase 5: Edge Cases
- [ ] All tests passed
- Issues: _______________

Phase 6: Performance
- [ ] All tests passed
- Issues: _______________

Overall Status: ✅ Pass / ❌ Fail
Notes: _______________
```

## 🐛 Common Issues & Fixes

### Issue: Bots Not Responding
**Fix**: 
- Check bot tokens in `.env`
- Verify bots online in Discord
- Check logs for errors
- Verify intents enabled in Developer Portal

### Issue: Commands Not Showing
**Fix**:
- Wait 5-10 minutes for Discord to sync
- Re-invite bots with correct OAuth2 URL
- Check "Use Slash Commands" permission

### Issue: AI Bots Not Joining Games
**Fix**:
- Verify all AI bot tokens valid
- Check all bots invited to server
- Check "Send Messages" permission
- Review logs for connection errors

### Issue: DM Voting Not Working
**Fix**:
- Enable DMs from server members (user privacy settings)
- Check bot can DM users
- Verify user shares server with bot

### Issue: Game Crashes Mid-Game
**Fix**:
- Check logs for stack trace
- Verify OpenAI API key valid and has credits
- Check for rate limiting
- Restart bot

## 📝 Logging for Testing

Enable debug logging for detailed output:

```python
# In main.py, change logging level:
logging.basicConfig(level=logging.DEBUG)
```

Check logs:
```bash
tail -f discord_bot.log
```

## ✅ Sign-Off Checklist

Before deploying to production:

- [ ] All Phase 1-6 tests passed
- [ ] No critical errors in logs
- [ ] Performance acceptable
- [ ] Error handling works
- [ ] Documentation complete
- [ ] Backup/recovery plan in place
- [ ] Monitoring set up

## 🚀 Next Steps After Testing

1. **Fix Issues**: Address any failed tests
2. **Optimize**: Improve performance based on testing
3. **Document**: Record any quirks or edge cases
4. **Deploy**: Roll out to production server
5. **Monitor**: Watch logs and user feedback

---

**Testing is complete when all phases pass!** ✅

