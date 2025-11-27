# MTurk Integration Workflow

**Complete workflow documentation for MTurk automated payment system**

---

## 📋 Table of Contents

1. [Overview](#overview)
2. [Complete Workflow Diagram](#complete-workflow-diagram)
3. [Worker Journey](#worker-journey)
4. [Admin Journey](#admin-journey)
5. [Technical Flow](#technical-flow)
6. [Payment Processing](#payment-processing)
7. [Error Handling](#error-handling)
8. [Best Practices](#best-practices)

---

## 🎯 Overview

This system automates the entire MTurk worker lifecycle:

1. **Admin creates HIT** → Posted to MTurk
2. **Worker accepts HIT** → Auto-registered in app
3. **Worker plays game** → Session tracked with MTurk IDs
4. **Admin reviews session** → Approves payment
5. **System processes payment** → MTurk API called automatically
6. **Worker receives payment** → In MTurk account

**Key Benefits:**
- ✅ No manual hash key entry
- ✅ Automatic worker registration
- ✅ One-click payment approval
- ✅ Bonus based on performance
- ✅ Complete audit trail

---

## 🗺️ Complete Workflow Diagram

```
┌─────────────────────────────────────────────────────────────────────┐
│                         ADMIN: Create HIT                            │
└─────────────────────────────────────────────────────────────────────┘
                                  │
                                  ▼
                    ┌─────────────────────────┐
                    │   MTurk API: CreateHIT  │
                    │   - Title, Description  │
                    │   - Base Pay: $0.05     │
                    │   - Max Workers: N      │
                    └─────────────────────────┘
                                  │
                                  ▼
                    ┌─────────────────────────┐
                    │  HIT Posted to MTurk    │
                    │  (Visible to workers)   │
                    └─────────────────────────┘
                                  │
                                  ▼
┌─────────────────────────────────────────────────────────────────────┐
│                      WORKER: Browse & Accept HIT                     │
└─────────────────────────────────────────────────────────────────────┘
                                  │
                                  ▼
                    ┌─────────────────────────┐
                    │  MTurk Generates URL    │
                    │  with Parameters:       │
                    │  - workerId             │
                    │  - assignmentId         │
                    │  - hitId                │
                    └─────────────────────────┘
                                  │
                                  ▼
┌─────────────────────────────────────────────────────────────────────┐
│                    WORKER: Land on Game Lobby                        │
│  URL: https://yourapp.com/lobby?workerId=A...&assignmentId=3...     │
└─────────────────────────────────────────────────────────────────────┘
                                  │
                                  ▼
                    ┌─────────────────────────┐
                    │  Frontend Detects       │
                    │  MTurk Parameters       │
                    │  (MTurkAutoLogin)       │
                    └─────────────────────────┘
                                  │
                                  ▼
                    ┌─────────────────────────┐
                    │  POST /api/auth/        │
                    │  mturk-register         │
                    │  {workerId, ...}        │
                    └─────────────────────────┘
                                  │
                                  ▼
                    ┌─────────────────────────┐
                    │  Backend:               │
                    │  1. Check if user exists│
                    │  2. Create if new       │
                    │  3. Generate JWT token  │
                    └─────────────────────────┘
                                  │
                                  ▼
                    ┌─────────────────────────┐
                    │  Worker Auto-Logged In  │
                    │  ✅ MTurk Badge Shown   │
                    └─────────────────────────┘
                                  │
                                  ▼
┌─────────────────────────────────────────────────────────────────────┐
│                       WORKER: Play Game                              │
└─────────────────────────────────────────────────────────────────────┘
                                  │
                                  ▼
                    ┌─────────────────────────┐
                    │  Join Room              │
                    │  (WebSocket connects)   │
                    └─────────────────────────┘
                                  │
                                  ▼
                    ┌─────────────────────────┐
                    │  MTurk Context Stored   │
                    │  in Room Data:          │
                    │  - worker_id            │
                    │  - assignment_id        │
                    │  - hit_id               │
                    └─────────────────────────┘
                                  │
                                  ▼
                    ┌─────────────────────────┐
                    │  Worker Plays Game:     │
                    │  - Chat with players    │
                    │  - Vote for AI          │
                    │  - Complete session     │
                    └─────────────────────────┘
                                  │
                                  ▼
                    ┌─────────────────────────┐
                    │  Game Ends              │
                    │  Earnings Calculated:   │
                    │  - Base: $0.25          │
                    │  - Win bonus: $0.50     │
                    │  - Vote bonus: $0.10    │
                    │  - Participation: 0.5-1.5x│
                    │  = Total: $0.99 (example)│
                    └─────────────────────────┘
                                  │
                                  ▼
                    ┌─────────────────────────┐
                    │  Session Saved to DB    │
                    │  with MTurk Fields:     │
                    │  - mturk_worker_id      │
                    │  - mturk_assignment_id  │
                    │  - mturk_hit_id         │
                    │  - calculated_earnings  │
                    │  - payment_status: pending│
                    └─────────────────────────┘
                                  │
                                  ▼
┌─────────────────────────────────────────────────────────────────────┐
│                    ADMIN: Review & Approve Payment                   │
└─────────────────────────────────────────────────────────────────────┘
                                  │
                                  ▼
                    ┌─────────────────────────┐
                    │  Admin Panel Shows:     │
                    │  - MTurk worker badge   │
                    │  - Calculated earnings  │
                    │  - "MTurk Pay" button   │
                    └─────────────────────────┘
                                  │
                                  ▼
                    ┌─────────────────────────┐
                    │  Admin Clicks           │
                    │  "MTurk Pay $0.99"      │
                    └─────────────────────────┘
                                  │
                                  ▼
                    ┌─────────────────────────┐
                    │  POST /api/admin/mturk/ │
                    │  sessions/{id}/         │
                    │  approve-payment        │
                    └─────────────────────────┘
                                  │
                                  ▼
                    ┌─────────────────────────┐
                    │  Backend Processes:     │
                    │  1. Get session data    │
                    │  2. Calculate payments: │
                    │     - Base: $0.05       │
                    │     - Raw bonus: $0.94  │
                    │     - Capped: $0.05     │
                    │     - Total: $0.10      │
                    └─────────────────────────┘
                                  │
                                  ▼
                    ┌─────────────────────────┐
                    │  MTurk API Call #1:     │
                    │  ApproveAssignment      │
                    │  - assignment_id        │
                    │  - Pays base: $0.05     │
                    └─────────────────────────┘
                                  │
                                  ▼
                    ┌─────────────────────────┐
                    │  MTurk API Call #2:     │
                    │  SendBonus              │
                    │  - worker_id            │
                    │  - assignment_id        │
                    │  - amount: $0.05        │
                    │  - reason: "Performance │
                    │    bonus (capped)"      │
                    └─────────────────────────┘
                                  │
                                  ▼
                    ┌─────────────────────────┐
                    │  Database Updated:      │
                    │  - mturk_payment_sent: 1│
                    │  - mturk_bonus_sent: 1  │
                    │  - payment_status: paid │
                    └─────────────────────────┘
                                  │
                                  ▼
┌─────────────────────────────────────────────────────────────────────┐
│                    WORKER: Receives Payment                          │
│                    (In MTurk Account)                                │
└─────────────────────────────────────────────────────────────────────┘
```

---

## 👤 Worker Journey

### Step 1: Discover HIT

**Location:** MTurk Marketplace (https://www.mturk.com or sandbox)

**What Worker Sees:**
```
┌────────────────────────────────────────────────┐
│ Identify AI in Group Chat Game (5-10 min)     │
│ ⭐⭐⭐⭐⭐ (4.8/5.0)                              │
│                                                │
│ Reward: $0.05 + up to $0.05 bonus             │
│ Time: 10 minutes                               │
│                                                │
│ Play a conversation game and identify which    │
│ player is AI. Earn bonus for good performance! │
│                                                │
│ [Preview] [Accept HIT]                         │
└────────────────────────────────────────────────┘
```

**Actions:**
1. Click "Preview" to see instructions
2. Click "Accept HIT" to start

---

### Step 2: Preview Mode (Optional)

**URL:** `https://yourapp.com/lobby?workerId=...&assignmentId=ASSIGNMENT_ID_NOT_AVAILABLE&hitId=...`

**What Worker Sees:**
```
┌────────────────────────────────────────────────┐
│ 🟡 Preview Mode                                │
│                                                │
│ You are previewing this HIT. Please accept     │
│ the HIT to participate.                        │
│                                                │
│ To participate:                                │
│ 1. Return to MTurk                             │
│ 2. Click "Accept HIT"                          │
│ 3. Come back to this page                      │
└────────────────────────────────────────────────┘
```

**Technical:**
- `assignmentId === "ASSIGNMENT_ID_NOT_AVAILABLE"` triggers preview mode
- No account created
- No game access

---

### Step 3: Accept HIT & Auto-Login

**URL:** `https://yourapp.com/lobby?workerId=A3EXAMPLE&assignmentId=3EXAMPLE&hitId=3EXAMPLE`

**What Worker Sees:**
```
┌────────────────────────────────────────────────┐
│ 🟢 MTurk Authentication                        │
│                                                │
│ Authenticating MTurk worker...                 │
│ [Progress bar animation]                       │
│                                                │
│ ✅ Welcome, MTurk Worker! 🎯                   │
│ Authentication successful! Redirecting...      │
└────────────────────────────────────────────────┘
```

**Technical Flow:**
1. `MTurkAutoLogin` component detects URL parameters
2. Calls `POST /api/auth/mturk-register`
3. Backend creates/finds user account
4. JWT token generated and stored
5. Worker logged in automatically
6. MTurk context saved to localStorage

**User State:**
```javascript
{
  user_id: "A3EXAMPLE",
  role: "worker",
  is_mturk_worker: true,
  access_token: "eyJ..."
}
```

**MTurk Context:**
```javascript
{
  worker_id: "A3EXAMPLE",
  assignment_id: "3EXAMPLE",
  hit_id: "3EXAMPLE"
}
```

---

### Step 4: Browse Rooms

**What Worker Sees:**
```
┌────────────────────────────────────────────────┐
│ 🎮 Game Lobby                                  │
│                                                │
│ [🏆 A3EXAMPLE] [MTurk] [🇺🇸 EN]                │
│                                                │
│ Available Rooms (3)                            │
│                                                │
│ ┌──────────────────────────────────────────┐  │
│ │ Room ABC123                              │  │
│ │ Players: 2/5  Language: English          │  │
│ │ [Join Room]                              │  │
│ └──────────────────────────────────────────┘  │
└────────────────────────────────────────────────┘
```

**MTurk Badge:**
- Yellow "MTurk" badge next to username
- Award icon (🏆) indicates MTurk worker
- Visible throughout the app

---

### Step 5: Play Game

**Game Flow:**
1. **Join Room** → Assigned Player number
2. **Discussion Phase** (3 min) → Chat with other players
3. **Voting Phase** (1 min) → Vote for suspected AI
4. **Results** → See if you identified AI correctly

**What Worker Sees:**
```
┌────────────────────────────────────────────────┐
│ 🎮 Game Room ABC123                            │
│ Round 1 - Discussion Phase (2:45 remaining)    │
│                                                │
│ Players:                                       │
│ • Player 1 (You) 🏆                            │
│ • Player 2                                     │
│ • Player 3                                     │
│ • Player 4                                     │
│ • Player 5                                     │
│                                                │
│ Chat:                                          │
│ Player 2: Hi everyone! What do you think       │
│           about this topic?                    │
│ Player 1: I think...                           │
│                                                │
│ [Type your message...]                         │
└────────────────────────────────────────────────┘
```

**Earnings Tracking:**
- Base participation: $0.25
- Correct AI identification: +$0.50
- Voted: +$0.10
- Participation multiplier: 0.5x - 1.5x (based on messages)

---

### Step 6: Game Complete

**What Worker Sees:**
```
┌────────────────────────────────────────────────┐
│ 🎉 Game Complete!                              │
│                                                │
│ Results:                                       │
│ • You identified: Player 3                     │
│ • AI was: Player 3 ✅                          │
│ • You won! 🏆                                  │
│                                                │
│ Your Earnings:                                 │
│ • Base participation: $0.25                    │
│ • Win bonus: $0.50                             │
│ • Vote bonus: $0.10                            │
│ • Participation (1.2x): +$0.14                 │
│ ─────────────────────────────                  │
│ Total Earned: $0.99                            │
│                                                │
│ ⚠️ Note: Earnings are capped at $0.10 total   │
│    You will receive: $0.10                     │
│                                                │
│ Payment will be processed by admin within      │
│ 24-48 hours. Thank you for participating!      │
│                                                │
│ [Return to MTurk] [Play Again]                 │
└────────────────────────────────────────────────┘
```

**Instructions:**
1. Click "Return to MTurk"
2. Submit HIT on MTurk (if required)
3. Wait for admin approval
4. Payment appears in MTurk account

---

## 👨‍💼 Admin Journey

### Step 1: Create HIT (Optional)

**Location:** Admin Panel → MTurk Management (future feature)

**Or via API:**
```bash
curl -X POST https://yourapp.com/api/admin/mturk/create-hit \
  -H "Authorization: Bearer $ADMIN_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "max_workers": 10,
    "title": "Identify AI in Group Chat Game (5-10 min)",
    "description": "Play a conversation game and identify which player is AI. Earn bonus for good performance!",
    "keywords": "game, chat, AI, conversation, research"
  }'
```

**Response:**
```json
{
  "success": true,
  "hit_id": "3EXAMPLE",
  "hit_type_id": "3EXAMPLE",
  "max_assignments": 10,
  "reward": "0.05",
  "external_url": "https://yourapp.com/lobby"
}
```

---

### Step 2: Monitor Sessions

**Location:** Admin Panel → Sessions List

**What Admin Sees:**
```
┌──────────────────────────────────────────────────────────────────────┐
│ Admin Panel - All Sessions                                           │
├──────────────────────────────────────────────────────────────────────┤
│ Room    │ Worker      │ Lang │ Players │ Completed   │ Status │ Amt  │
├─────────┼─────────────┼──────┼─────────┼─────────────┼────────┼──────┤
│ ABC123  │ 🏆 A3EX...  │ EN   │ 1/5     │ Oct 30 14:30│ ⏰ Pend│ $0.99│
│         │ 3EX...      │      │         │             │ ✓Base  │      │
│         │             │      │         │             │ ✓Bonus │      │
│         │             │      │         │             │        │      │
│         │ [⚡ MTurk Pay $0.99] [View Details →]      │        │      │
├─────────┼─────────────┼──────┼─────────┼─────────────┼────────┼──────┤
│ DEF456  │ Regular user│ EN   │ 1/5     │ Oct 30 13:15│ ⏰ Pend│ $0.85│
│         │             │      │         │             │        │      │
│         │ [Mark Paid] [Set Amount] [View Details →] │        │      │
└──────────────────────────────────────────────────────────────────────┘
```

**Key Indicators:**
- 🏆 **MTurk Badge:** Yellow highlight, award icon
- **Worker ID:** Truncated (A3EX...), full ID in tooltip
- **Assignment ID:** Truncated (3EX...), full ID in tooltip
- **Payment Flags:** ✓Base, ✓Bonus (if already paid)
- **⚡ MTurk Pay Button:** Prominent, gradient button for MTurk workers

---

### Step 3: Review Session Quality

**Click "View Details →"**

**What Admin Sees:**
```
┌──────────────────────────────────────────────────────────────────────┐
│ Session Details - ABC123                                             │
├──────────────────────────────────────────────────────────────────────┤
│ MTurk Information:                                                   │
│ • Worker ID: A3EXAMPLE                                               │
│ • Assignment ID: 3EXAMPLE                                            │
│ • HIT ID: 3EXAMPLE                                                   │
│ • Payment Status: Pending                                            │
│ • Base Payment Sent: No                                              │
│ • Bonus Sent: No                                                     │
│                                                                      │
│ Game Performance:                                                    │
│ • Completed: Yes ✅                                                  │
│ • Winner: Yes (identified AI correctly) ✅                           │
│ • Voted: Yes ✅                                                      │
│ • Messages Sent: 12                                                  │
│ • Participation Score: 1.2x                                          │
│                                                                      │
│ Earnings Breakdown:                                                  │
│ • Base: $0.25                                                        │
│ • Win Bonus: $0.50                                                   │
│ • Vote Bonus: $0.10                                                  │
│ • Participation: +$0.14 (1.2x)                                       │
│ ─────────────────────────                                            │
│ • Raw Total: $0.99                                                   │
│ • Capped Total: $0.10 (base $0.05 + bonus $0.05)                    │
│                                                                      │
│ Chat Log: [View Full Chat]                                           │
│                                                                      │
│ [⚡ Approve & Pay via MTurk API] [Reject Session]                    │
└──────────────────────────────────────────────────────────────────────┘
```

**Quality Checks:**
- ✅ Worker participated actively (12 messages)
- ✅ Worker voted
- ✅ Worker identified AI correctly
- ✅ No spam or inappropriate content

---

### Step 4: Approve Payment

**Click "⚡ MTurk Pay $0.99"**

**Confirmation Dialog:**
```
┌──────────────────────────────────────────────┐
│ Confirm MTurk Payment                        │
│                                              │
│ This will trigger the MTurk API to:          │
│ 1. Approve assignment (base pay: $0.05)     │
│ 2. Send bonus (capped: $0.05)               │
│                                              │
│ Worker: A3EXAMPLE                            │
│ Assignment: 3EXAMPLE                         │
│ Total Payment: $0.10                         │
│                                              │
│ [Cancel] [Confirm Payment]                   │
└──────────────────────────────────────────────┘
```

**Click "Confirm Payment"**

**Processing:**
```
┌──────────────────────────────────────────────┐
│ Processing MTurk Payment...                  │
│                                              │
│ ✅ Assignment approved ($0.05)               │
│ ✅ Bonus sent ($0.05)                        │
│ ✅ Database updated                          │
│                                              │
│ Payment processed successfully!              │
└──────────────────────────────────────────────┘
```

**Result:**
- Session status → "Paid"
- `mturk_payment_sent` → 1
- `mturk_bonus_sent` → 1
- Worker receives payment in MTurk account

---

## 🔧 Technical Flow

### Auto-Registration Flow

```javascript
// 1. Frontend detects MTurk parameters
const searchParams = new URLSearchParams(window.location.search);
const workerId = searchParams.get('workerId');
const assignmentId = searchParams.get('assignmentId');
const hitId = searchParams.get('hitId');

// 2. Check for preview mode
if (assignmentId === 'ASSIGNMENT_ID_NOT_AVAILABLE') {
  showPreviewMode();
  return;
}

// 3. Call auto-registration endpoint
const response = await fetch('/api/auth/mturk-register', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({ worker_id: workerId, assignment_id: assignmentId, hit_id: hitId })
});

// 4. Store token and context
const data = await response.json();
localStorage.setItem('access_token', data.access_token);
localStorage.setItem('mturk_context', JSON.stringify(data.mturk_context));

// 5. User is now logged in
setUser(data.user);
```

### Backend Registration Logic

```python
# backend/auth.py
async def register_or_login_mturk_worker(db, worker_id):
    # Check if worker exists
    user = await get_user_by_username(db, worker_id)
    
    if not user:
        # Create new user with random password
        random_password = secrets.token_urlsafe(32)
        user = await register_user(db, worker_id, random_password, role=UserRole.WORKER)
    
    # Generate JWT token
    access_token = create_access_token({"sub": user.username, "user_id": user.user_id})
    
    return user, access_token
```

### Session Tracking

```python
# backend/main.py - save_session_stats()
async def save_session_stats(room_code, state, current_user=None):
    # ... existing logic ...
    
    # Add MTurk fields if present in room data
    mturk_context = room_data.get('mturk_context', {})
    if mturk_context:
        session_data["mturk_worker_id"] = mturk_context.get('worker_id')
        session_data["mturk_assignment_id"] = mturk_context.get('assignment_id')
        session_data["mturk_hit_id"] = mturk_context.get('hit_id')
    
    db_session = DBSession(**session_data)
    db.add(db_session)
    await db.commit()
```

### Payment Processing

```python
# backend/mturk_api.py - process_payment()
def process_payment(assignment_id, worker_id, calculated_earnings, max_bonus=None):
    client = get_mturk_client()
    
    # Calculate payments
    base_pay = Decimal('0.05')
    max_bonus = max_bonus or base_pay
    raw_bonus = calculated_earnings - base_pay
    bonus_amount = min(raw_bonus, max_bonus)  # Cap bonus
    
    # 1. Approve assignment (pays base)
    client.approve_assignment(
        AssignmentId=assignment_id,
        RequesterFeedback="Thank you for participating!"
    )
    
    # 2. Send bonus (if any)
    if bonus_amount > 0:
        client.send_bonus(
            WorkerId=worker_id,
            AssignmentId=assignment_id,
            BonusAmount=str(bonus_amount),
            Reason=f"Performance bonus: ${bonus_amount} (capped)"
        )
    
    return {'approved': True, 'bonus_sent': bonus_amount > 0}
```

---

## 💰 Payment Processing

### Earnings Calculation

```python
# Base earnings
base = 0.25

# Win bonus
win_bonus = 0.50 if identified_ai_correctly else 0.00

# Vote bonus
vote_bonus = 0.10 if voted else 0.00

# Participation multiplier (0.5x - 1.5x)
message_count = len([m for m in messages if m['player_id'] == player_id])
participation_multiplier = min(1.5, max(0.5, message_count / 10))

# Total
raw_earnings = (base + win_bonus + vote_bonus) * participation_multiplier
```

### Payment Caps

```python
# Configuration
MTURK_BASE_PAY = 0.05  # Paid via ApproveAssignment
MTURK_MAX_BONUS = 0.05  # Paid via SendBonus

# Processing
base_pay = Decimal('0.05')
raw_bonus = raw_earnings - base_pay  # e.g., $0.94
capped_bonus = min(raw_bonus, Decimal('0.05'))  # $0.05
total_payment = base_pay + capped_bonus  # $0.10
```

### Cost Breakdown

```
Per Worker:
  Base Pay:     $0.05
  Bonus (max):  $0.05
  ─────────────────
  Subtotal:     $0.10
  MTurk Fee (20%): $0.02
  ─────────────────
  Total Cost:   $0.12

100 Workers:    $12.00
1,000 Workers:  $120.00
```

---

## ⚠️ Error Handling

### Common Errors & Solutions

#### 1. Preview Mode Detection

**Error:** Worker tries to play in preview mode

**Solution:**
```javascript
if (assignmentId === 'ASSIGNMENT_ID_NOT_AVAILABLE') {
  return {
    success: false,
    preview_mode: true,
    message: "Preview mode - accept HIT to participate"
  };
}
```

#### 2. Duplicate Assignment

**Error:** Assignment ID already exists in database

**Solution:**
```python
# Database constraint prevents duplicates
mturk_assignment_id = Column(String(255), unique=True)

# Check before processing
existing = await db.execute(
    select(Session).where(Session.mturk_assignment_id == assignment_id)
)
if existing.scalar():
    raise HTTPException(400, "Assignment already submitted")
```

#### 3. Payment Already Sent

**Error:** Admin tries to pay twice

**Solution:**
```python
if session.mturk_payment_sent:
    raise HTTPException(400, "Payment already processed")
```

#### 4. Insufficient Funds

**Error:** MTurk account balance too low

**Solution:**
```python
balance = get_account_balance()
if balance < Decimal('10.00'):
    raise HTTPException(400, "Insufficient MTurk balance. Please add funds.")
```

#### 5. Invalid Assignment

**Error:** Assignment not found in MTurk

**Solution:**
```python
try:
    assignment = client.get_assignment(AssignmentId=assignment_id)
except ClientError as e:
    if e.response['Error']['Code'] == 'RequestError':
        raise HTTPException(404, "Assignment not found in MTurk")
```

---

## ✅ Best Practices

### For Admins

1. **Review Sessions Promptly**
   - Approve within 24 hours
   - Workers appreciate fast payment
   - Builds good reputation

2. **Check Quality**
   - Review chat logs
   - Verify participation
   - Reject spam/low-effort

3. **Monitor Costs**
   - Check balance daily
   - Set spending alerts
   - Track cost per session

4. **Maintain Good Ratings**
   - Fair payment
   - Clear instructions
   - Responsive to issues

### For Workers

1. **Participate Actively**
   - Send meaningful messages
   - Engage with other players
   - Vote thoughtfully

2. **Follow Instructions**
   - Read HIT description
   - Complete all phases
   - Submit properly

3. **Quality Over Speed**
   - Better performance = higher bonus
   - Don't rush through
   - Think strategically

### For Developers

1. **Test Thoroughly**
   - Use sandbox extensively
   - Test all error cases
   - Verify payment flow

2. **Monitor Logs**
   - Track MTurk API calls
   - Log payment processing
   - Alert on errors

3. **Secure Credentials**
   - Use environment variables
   - Rotate keys regularly
   - Limit IAM permissions

4. **Handle Edge Cases**
   - Preview mode
   - Duplicate assignments
   - Network failures
   - API rate limits

---

## 📊 Metrics & Analytics

### Track These Metrics

1. **Worker Metrics:**
   - Completion rate
   - Average earnings
   - Time to complete
   - Quality score

2. **Payment Metrics:**
   - Total paid
   - Average payment per worker
   - Bonus distribution
   - Payment approval time

3. **Cost Metrics:**
   - Daily spending
   - Cost per session
   - MTurk fees
   - Budget utilization

4. **Quality Metrics:**
   - Rejection rate
   - Worker satisfaction
   - Data quality
   - Repeat workers

---

## 🎉 Success Checklist

### Worker Success
- ✅ HIT accepted successfully
- ✅ Auto-logged in without issues
- ✅ Game completed
- ✅ Earnings displayed correctly
- ✅ Payment received in MTurk account

### Admin Success
- ✅ HIT created and visible on MTurk
- ✅ Sessions tracked with MTurk IDs
- ✅ Payment processed via API
- ✅ Database updated correctly
- ✅ No errors in logs

### System Success
- ✅ 100% auto-registration rate
- ✅ <1% payment errors
- ✅ <24h payment approval time
- ✅ Positive worker feedback
- ✅ Cost within budget

---

**Workflow Complete!** 🎉

For setup instructions, see [MTURK_API_SETUP.md](./MTURK_API_SETUP.md)

For security review, see [MTURK_SECURITY_REVIEW.md](./MTURK_SECURITY_REVIEW.md)

