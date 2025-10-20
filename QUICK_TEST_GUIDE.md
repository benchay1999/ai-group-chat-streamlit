# Quick Test Guide - Matching Room System

## Quick Start (5 Minutes)

### Step 1: Start Backend
```bash
cd /home/wschay/group-chat
conda activate group-chat
cd backend
uvicorn main:app --reload
```

Keep this terminal open. You should see:
```
INFO:     Uvicorn running on http://127.0.0.1:8000
```

### Step 2: Start Streamlit (New Terminal)
```bash
cd /home/wschay/group-chat
conda activate group-chat
streamlit run streamlit_app.py
```

Browser should auto-open to `http://localhost:8501`

### Step 3: Create Your First Room

You'll see a dark cyberpunk-themed lobby with:
- Big "🎮 Human Hunter - Find Your Match" title
- "Create New Room" button

Click **"Create New Room"** and fill in:
- **Your Name**: "TestPlayer"
- **Room Name**: "My First Room" (or leave blank)
- **Number of Human Players**: 1
- **Total Players**: 5

Click **"Create & Join"** 

✅ **Expected Result**: Game starts immediately since you're the only human needed!

---

## Test 2: Multi-Player Room (Requires 2 Browser Windows)

### Browser Window 1

1. Click "Leave Room" to return to lobby
2. Click "Create New Room"
3. Fill in:
   - **Your Name**: "Player1"
   - **Room Name**: "2 Player Test"
   - **Number of Human Players**: 2
   - **Total Players**: 5
4. Click "Create & Join"

✅ **Expected**: You see a waiting screen showing "1/2" players

### Browser Window 2 (Incognito/Different Browser)

1. Navigate to `http://localhost:8501`
2. You should see the lobby with your room listed
3. Find the "2 Player Test" room card showing:
   ```
   🎯 2 Player Test
   🟢 Waiting...
   👥 Players: 1/2 humans
   🤖 Total Slots: 5
   ```
4. Click "Join Room"
5. Enter name: "Player2"
6. Click "Join Game"

✅ **Expected**: Both windows automatically transition to game with:
- Player1 and Player2 (humans)
- Player 1, Player 2, Player 3 (AI agents)
- Total: 5 players

---

## Test 3: Room Browsing

Create multiple rooms with different settings to test the lobby:

### Create Room 1
- Name: "Quick Match"
- Humans: 1
- Total: 3
- **Result**: Click "Create & Join", game starts immediately

### Create Room 2
- Leave game, return to lobby
- Name: "Squad Up"
- Humans: 3
- Total: 6
- **Result**: Waiting screen

### Create Room 3 (New Browser)
- Name: "Duo Party"
- Humans: 2
- Total: 5
- **Result**: Waiting screen

Now your lobby should show both waiting rooms. Test:
- ✅ Both rooms visible
- ✅ Player counts accurate
- ✅ Status badges showing
- ✅ Join button works

---

## Test 4: Room Full Scenario

### Browser 1: Create Room
- Name: "Full Test"
- Humans: 2
- Total: 4
- You're at waiting screen (1/2)

### Browser 2: Join Room
- Join "Full Test" room
- Enter name
- ✅ Both transition to game
- ✅ Room disappears from lobby

### Browser 3: Try to Join
- Refresh lobby
- ✅ Room no longer visible (status: in_progress)
- If you try to join via direct link: Error message

---

## Visual Checkpoints

### Lobby Page ✓
- [ ] Dark cyberpunk background gradient
- [ ] Glowing cyan/purple title
- [ ] Room cards with neon borders
- [ ] Hover effect on room cards (glow + lift)
- [ ] Status badges (green/yellow)
- [ ] Clean grid layout (2 columns)

### Room Card ✓
- [ ] Room name prominently displayed
- [ ] Status badge visible
- [ ] Player count (current/max)
- [ ] Total slots shown
- [ ] Room code visible
- [ ] Join button glowing

### Create Form ✓
- [ ] Clean modal design
- [ ] Sliders for player counts
- [ ] AI count auto-calculated
- [ ] Validation working
- [ ] Cancel button works

### Waiting Screen ✓
- [ ] Large animated counter (e.g., "2/3")
- [ ] Player list with styling
- [ ] Glowing animation effect
- [ ] Leave room button
- [ ] Auto-refresh working

### Game Screen ✓
- [ ] Existing UI unchanged
- [ ] Leave room returns to lobby
- [ ] All game features working

---

## API Testing (Optional)

Test the backend directly:

### Create Room
```bash
curl -X POST http://localhost:8000/api/rooms/create \
  -H "Content-Type: application/json" \
  -d '{
    "creator_id": "APITest",
    "room_name": "API Room",
    "max_humans": 2,
    "total_players": 5
  }'
```

Expected response:
```json
{
  "success": true,
  "room_code": "AB12CD",
  "room_name": "API Room",
  "max_humans": 2,
  "total_players": 5
}
```

### List Rooms
```bash
curl http://localhost:8000/api/rooms/list?page=0&per_page=10
```

### Get Room Info
```bash
curl http://localhost:8000/api/rooms/{ROOM_CODE}/info
```

Replace `{ROOM_CODE}` with actual code from create response.

---

## Common Issues

### Issue: "Server Offline"
**Solution**: Start backend first (`uvicorn main:app --reload`)

### Issue: Room not appearing
**Solution**: Only 'waiting' rooms show. In-progress rooms are hidden.

### Issue: Can't join room
**Possible causes**:
- Room already full
- Room already started
- Room code incorrect

### Issue: Waiting screen stuck
**Solution**: 
- Wait 2 seconds for next poll
- Check backend logs
- Verify backend is running

### Issue: Visual glitches
**Solution**: 
- Hard refresh (Ctrl+Shift+R)
- Clear Streamlit cache
- Check browser console for errors

---

## Success Criteria

Your implementation is working correctly if:

1. ✅ Can create rooms with custom settings
2. ✅ Rooms appear in lobby list
3. ✅ Can join rooms from lobby
4. ✅ Waiting screen shows correct count
5. ✅ Game auto-starts when full
6. ✅ Multiple players can join same room
7. ✅ UI looks polished with cyberpunk theme
8. ✅ Page navigation works smoothly
9. ✅ Leave room returns to lobby
10. ✅ Existing game features unchanged

---

## Next Steps

Once basic testing is complete:

1. **Stress Test**: Create 15+ rooms to test pagination
2. **Race Conditions**: Multiple players join simultaneously
3. **Edge Cases**: Try invalid inputs, extreme values
4. **Mobile Testing**: Test on mobile browsers
5. **Multi-Device**: Test on different screen sizes

---

## Need Help?

Check these files:
- `MATCHING_ROOM_IMPLEMENTATION.md` - Full technical documentation
- `backend/main.py` - Backend API implementation
- `streamlit_app.py` - Frontend implementation
- Backend logs - Check terminal running uvicorn
- Browser console - Check for JavaScript errors

Happy testing! 🎮

