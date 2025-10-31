# How to Test MTurk Frontend Features

**Why you can't see MTurk features:** They only appear when accessing via MTurk URLs with specific parameters!

---

## 🎯 MTurk Features in Frontend

### Features That Only Show for MTurk Workers:

1. **Auto-Login Animation** - Slide-in notification when worker arrives
2. **MTurk Badge** - Yellow "MTurk" pill next to username
3. **Award Icon** - 🏆 icon with pulse animation
4. **Preview Mode Notice** - Instructions for workers in preview mode

### Features That Only Show for Admins:

1. **Worker Column** - Shows MTurk worker info in admin table
2. **⚡ MTurk Pay Button** - Gradient button to approve payments
3. **Payment Status Badges** - ✓Base, ✓Bonus indicators
4. **Yellow Row Highlighting** - MTurk sessions highlighted

---

## 🧪 How to Test MTurk Features

### Method 1: Simulate MTurk URL (Easiest)

**Test the auto-login animation:**

1. **Go to this URL in your browser:**
   ```
   https://ai-groupchat.ngrok.io/lobby?workerId=ATEST123&assignmentId=3TEST456&hitId=3TEST789
   ```

2. **You should see:**
   - 🟢 Animated notification sliding in from top
   - "MTurk Authentication" with progress bar
   - "Welcome, MTurk Worker! 🎯"
   - Auto-login happens automatically

3. **After login, you should see:**
   - Yellow "MTurk" badge next to your username
   - 🏆 Award icon with pulse animation

**Test preview mode:**

1. **Go to this URL:**
   ```
   https://ai-groupchat.ngrok.io/lobby?workerId=ATEST123&assignmentId=ASSIGNMENT_ID_NOT_AVAILABLE&hitId=3TEST789
   ```

2. **You should see:**
   - 🟡 Yellow "Preview Mode" notification
   - Instructions on how to accept the HIT
   - No account created

---

### Method 2: Create Real HIT and Accept It

**Step 1: Create a HIT**

```bash
# Get your admin token
TOKEN=$(curl -s -X POST https://ai-groupchat.ngrok.io/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"user_id":"admin","password":"your_password"}' \
  | grep -o '"access_token":"[^"]*' | cut -d'"' -f4)

# Create HIT
curl -X POST https://ai-groupchat.ngrok.io/api/admin/mturk/create-hit \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "max_workers": 1,
    "title": "Test: Identify AI in Group Chat",
    "description": "Play a game and identify which player is AI",
    "keywords": "game, chat, AI"
  }'
```

**Step 2: Find HIT on MTurk Sandbox**

1. Go to: https://workersandbox.mturk.com
2. Sign in with your test worker account
3. Find your HIT (search for "Identify AI")
4. Click "Preview"

**Step 3: Preview Mode Test**

- You'll be redirected to your app with `assignmentId=ASSIGNMENT_ID_NOT_AVAILABLE`
- Should see preview mode notification

**Step 4: Accept HIT**

- Go back to MTurk
- Click "Accept HIT"
- You'll be redirected with real parameters
- Should see auto-login animation

---

### Method 3: Test Admin Features

**Step 1: Create a session with MTurk data**

Use Method 1 to create a MTurk worker session, then play a game.

**Step 2: Go to Admin Panel**

```
https://ai-groupchat.ngrok.io/admin
```

**Step 3: Look for MTurk features:**

- **Worker column** - Shows worker ID (truncated)
- **Yellow highlighting** - MTurk sessions have yellow background
- **⚡ MTurk Pay button** - Gradient button for MTurk sessions
- **Payment badges** - ✓Base, ✓Bonus indicators

---

## 📸 What You Should See

### 1. Auto-Login Animation (Worker View)

When accessing: `https://ai-groupchat.ngrok.io/lobby?workerId=A123&assignmentId=3456&hitId=789`

```
┌────────────────────────────────────────────────┐
│ 🟢 MTurk Authentication                        │
│                                                │
│ Authenticating MTurk worker...                 │
│ [████████░░] 80%                               │
│                                                │
│ ✅ Welcome, MTurk Worker! 🎯                   │
│ Authentication successful!                     │
└────────────────────────────────────────────────┘
```

### 2. MTurk Badge (Worker View)

In the lobby header:

```
┌────────────────────────────────────────────────┐
│ 🎮 Game Lobby                                  │
│                                                │
│ [🏆 A123...] [MTurk] [🇺🇸 EN]                  │
│     ↑          ↑                               │
│   Award    Yellow badge                        │
└────────────────────────────────────────────────┘
```

### 3. Preview Mode (Worker View)

When accessing with `assignmentId=ASSIGNMENT_ID_NOT_AVAILABLE`:

```
┌────────────────────────────────────────────────┐
│ 🟡 Preview Mode                                │
│                                                │
│ You are previewing this HIT. Please accept     │
│ the HIT to participate.                        │
│                                                │
│ 💡 To participate:                             │
│ 1. Return to MTurk                             │
│ 2. Click "Accept HIT"                          │
│ 3. Come back to this page                      │
└────────────────────────────────────────────────┘
```

### 4. Admin Panel (Admin View)

```
┌──────────────────────────────────────────────────────────────────────┐
│ Room    │ Worker      │ Lang │ Players │ Status │ Amount │ Actions   │
├─────────┼─────────────┼──────┼─────────┼────────┼────────┼───────────┤
│ ABC123  │ 🏆 A3EX...  │ EN   │ 1/5     │ ⏰ Pend│ $0.10  │           │
│         │ 3EX...      │      │         │ ✓Base  │        │           │
│         │             │      │         │ ✓Bonus │        │           │
│         │ [⚡ MTurk Pay $0.10] [View Details →]  │        │           │
│ ← Yellow background for MTurk sessions                               │
└──────────────────────────────────────────────────────────────────────┘
```

---

## 🔍 Debugging: Why You Don't See Features

### Check 1: Are you accessing via MTurk URL?

**Test URL:**
```
https://ai-groupchat.ngrok.io/lobby?workerId=ATEST&assignmentId=3TEST&hitId=3TEST
```

**Regular URL (no MTurk features):**
```
https://ai-groupchat.ngrok.io/lobby
```

### Check 2: Open Browser Console

Press `F12` → Console tab, then access the MTurk URL. You should see:

```javascript
// Check if parameters are detected
const params = new URLSearchParams(window.location.search);
console.log('workerId:', params.get('workerId'));      // Should show: ATEST
console.log('assignmentId:', params.get('assignmentId')); // Should show: 3TEST
console.log('hitId:', params.get('hitId'));            // Should show: 3TEST
```

### Check 3: Check Network Tab

In DevTools → Network tab:

- Should see `POST /api/auth/mturk-register`
- Status should be `200 OK`
- Response should have `access_token`

### Check 4: Check localStorage

In Console tab:

```javascript
localStorage.getItem('mturk_context')
// Should show: {"worker_id":"ATEST","assignment_id":"3TEST","hit_id":"3TEST"}

localStorage.getItem('access_token')
// Should show a JWT token
```

---

## 🎬 Quick Demo Script

Copy and paste this into your terminal:

```bash
#!/bin/bash

echo "🎯 MTurk Frontend Feature Demo"
echo ""
echo "1. Open this URL in your browser:"
echo "   https://ai-groupchat.ngrok.io/lobby?workerId=ATEST123&assignmentId=3TEST456&hitId=3TEST789"
echo ""
echo "2. You should see:"
echo "   ✅ Auto-login animation"
echo "   ✅ MTurk badge next to username"
echo "   ✅ Award icon (🏆)"
echo ""
echo "3. For preview mode, open:"
echo "   https://ai-groupchat.ngrok.io/lobby?workerId=ATEST123&assignmentId=ASSIGNMENT_ID_NOT_AVAILABLE&hitId=3TEST789"
echo ""
echo "4. For admin features, login as admin and go to:"
echo "   https://ai-groupchat.ngrok.io/admin"
echo ""
```

---

## ✅ Feature Checklist

Test each feature:

### Worker Features
- [ ] Open lobby with MTurk URL parameters
- [ ] See auto-login animation
- [ ] See "Welcome, MTurk Worker! 🎯" message
- [ ] See yellow "MTurk" badge in header
- [ ] See award icon (🏆) with pulse animation
- [ ] Badge persists after navigation
- [ ] Preview mode shows correct message
- [ ] Preview mode doesn't create account

### Admin Features
- [ ] Login as admin
- [ ] Go to admin panel
- [ ] See "Worker" column in table
- [ ] MTurk sessions have yellow background
- [ ] Worker ID shows (truncated)
- [ ] Assignment ID shows (truncated)
- [ ] See ⚡ MTurk Pay button for MTurk sessions
- [ ] Regular sessions show normal buttons
- [ ] Payment status badges show (✓Base, ✓Bonus)

---

## 💡 Key Points

1. **MTurk features are hidden by default** - They only appear when:
   - URL has `workerId`, `assignmentId`, `hitId` parameters
   - User is logged in as MTurk worker
   - Session has MTurk data (for admin view)

2. **This is by design** - Regular users don't see MTurk UI elements

3. **To test without creating HITs** - Use the test URL with fake parameters

4. **Admin features require MTurk sessions** - Play a game as MTurk worker first

---

## 🚀 Quick Test

**Right now, open this URL:**

```
https://ai-groupchat.ngrok.io/lobby?workerId=ATEST123&assignmentId=3TEST456&hitId=3TEST789
```

You should immediately see the MTurk features! 🎉

---

**Summary:** MTurk features are **conditional** - they only show when appropriate. Use the test URLs above to see them!


