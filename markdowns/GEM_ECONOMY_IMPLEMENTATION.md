# Gem Economy Implementation Summary

## How The Gem System Works (User-Facing)

### Overview
Gems are the in-game currency that players earn by participating in games. They can be converted to real USD via Amazon Mechanical Turk at a rate of **1000 gems = $1.00 USD**.

### Game Modes & Rewards

#### Single-Human Games (1 human vs AI agents)
- **Simple participation-based rewards**
- **All participants:** 50 gems (human + AI)
- **No stakes required**
- **No risk of losing gems**
- Perfect for building your initial gem balance

#### Multi-Human Games (2+ human players competing)
- **Performance-based rewards with optional stakes**
- **Base Gems:** 100 gems for all participants who vote
- **Stakes System:** Optional risk/reward mechanism
  - Room creator selects stake percentage: 0%, 10%, 30%, 50%, or 100%
  - Minimum 250 gems required to join
  - All players pay the **minimum stake** (lowest among all players)
  - Anonymous users can only join 0% stake games

### Stakes Mechanics (Multi-Human Games)

#### Phase 1: Game Start (Deduction)
When a multi-human game starts with stakes enabled:

1. System calculates each player's stake: `balance × percentage / 100`
2. Finds the **minimum stake** across all players
3. All players pay this minimum stake amount

**Example (3 players, 10% stake):**
```
Player A: 1000 gems × 10% = 100 gems stake
Player B: 900 gems × 10% = 90 gems stake  
Player C: 800 gems × 10% = 80 gems stake

minimum_stake = 80 gems
→ All players pay 80 gems (deducted immediately after voting)
```

#### Phase 2: Game End (Rewards Distribution)

**Base Gems (Everyone Who Voted):**
- All participants who cast a vote: **+100 gems**
- No vote = no base gems (forfeited)

**Stakes Distribution:**

**Winners (Most Votes):**
1. **Stake Refund:** Get your stake back (if you voted)
2. **Loser Pool:** All loser stakes combined
3. **Equal Division:** Pool divided by number of winners
4. **Accuracy Bonus:** You get `accuracy% × your_share` of the pool

```python
# Formulas for winners
loser_pool = minimum_stake × num_losers
max_share = loser_pool ÷ num_winners

# Voting accuracy calculation
votes_needed = num_humans - 1  # Must vote for all OTHER humans
correct_votes = count(voted for other humans)  # Not self, not AI
accuracy = correct_votes / votes_needed  # Returns 0.0 to 1.0

# Rewards
stake_refund = minimum_stake  # Always returned if you voted
stake_winnings = int(accuracy × max_share)  # Proportional to accuracy
TOTAL = 100 + stake_refund + stake_winnings
```

**Losers (Fewer Votes):**
- Stakes returned: **0 gems** (forfeit entirely)
- Only get base 100 gems (if voted)
- Net loss = 100 - minimum_stake

**Voting Penalty:**
- **Must vote** to receive base gems and stake refund
- No vote = forfeit both base gems AND stake refund (even if you win!)

### Voting Accuracy Impact

In multi-human games, you vote for **all other humans** (N-1 players, excluding yourself). Your accuracy determines your stake winnings:

| Accuracy | Result |
|----------|--------|
| **100%** | Full share of loser pool |
| **50%** | Half of your share |
| **0%** | Only stake refund (no winnings) |

**Key Principle:** Higher accuracy = higher reward

### Example: 2-Player Game (10% stakes)

**Game Start:**
- Player A: 1000 gems → 840 gems (-160 deducted)
- Player B: 1000 gems → 840 gems (-160 deducted)

**Voting Results:**
- Player A: 1 vote ← Winner 🏆
- Player B: 0 votes

**Rewards:**

**Player A (Winner, 100% accuracy):**
- Base: +100 gems
- Stake refund: +160 gems
- Stakes won (100%): +160 gems (full share of loser pool)
- **Total credited: +420 gems**
- **Final balance: 1260 gems (+260 net 🎉)**

**Player B (Loser):**
- Base: +100 gems
- Stakes returned: 0 gems (forfeited)
- **Total credited: +100 gems**
- **Final balance: 940 gems (-60 net 💔)**

### Guarantees

✅ **Winners never lose gems** - Minimum: +100 base (even with 0% accuracy)  
✅ **Higher accuracy = higher reward** - Up to full share of loser pool  
✅ **Fair competition** - Winners split loser pool equally  
⚠️ **House collects residual** - Uncollected gems (from low accuracy) don't return to losers

### Cashout System

**Converting Gems to USD:**
- **Conversion Rate:** 1000 gems = $1.00 USD
- **Minimum Cashout:** $2.00 (2000 gems)
- **Method:** Amazon Mechanical Turk worker-specific HITs
- **Requirement:** Must add MTurk Worker ID to profile
- **Processing:** Auto-approved within 1 hour

Visit `/wallet` page in the app to request cashouts and view transaction history.

---

## ✅ COMPLETED: Backend Implementation

All backend functionality is fully implemented and ready for testing:

### Database & Migrations
- ✅ Added `gem_balance`, `total_gems_earned`, `total_gems_cashed_out`, `mturk_worker_id` to Users table
- ✅ Created `CashoutTransaction` model with status tracking
- ✅ Created Alembic migration `007_add_gem_economy.py`
- ✅ Created data migration script `backend/migrate_to_gems.py` to convert existing earnings

### Configuration
- ✅ Added `MINIMUM_CASHOUT_AMOUNT`, `CASHOUT_HIT_DURATION`, `CASHOUT_HIT_AUTO_APPROVE` to config
- ✅ Updated `env.example` with new variables
- ✅ Set default minimum cashout to $2.00 (configurable)

### MTurk API Functions
- ✅ `create_worker_qualification()` - Creates unique qualification for specific worker
- ✅ `assign_qualification_to_worker()` - Assigns qualification to worker
- ✅ `create_cashout_hit()` - Creates worker-specific HIT with qualification requirement
- ✅ `check_hit_status()` - Monitors HIT status and assignments
- ✅ `find_and_approve_cashout_assignment()` - Auto-approves completed HITs
- ✅ `expire_and_delete_hit()` - Handles HIT cleanup

### Cashout Service (`backend/cashout_service.py`)
- ✅ `gems_to_usd()` and `usd_to_gems()` conversion utilities
- ✅ `validate_cashout_request()` - Validates worker ID, balance, minimum amount
- ✅ `create_cashout_transaction()` - Creates transaction, deducts gems, creates HIT
- ✅ `check_cashout_status()` - Monitors and updates transaction status
- ✅ `cancel_cashout_transaction()` - Returns gems if HIT expires
- ✅ `get_user_cashout_history()` - Retrieves transaction history

### API Endpoints (`backend/main.py`)
- ✅ `GET /api/wallet/balance` - Returns gem balance and statistics
- ✅ `POST /api/wallet/cashout` - Initiates cashout transaction
- ✅ `GET /api/wallet/cashout-history` - Returns transaction history
- ✅ `GET /api/wallet/cashout-status/{transaction_id}` - Polls transaction status
- ✅ `GET /api/profile` - Returns complete user profile with wallet data
- ✅ `PUT /api/profile/mturk-worker-id` - Updates MTurk Worker ID with validation

### Earnings System
- ✅ Modified `save_session_stats()` to credit gems immediately after each game
- ✅ Converts calculated_earnings to gems (multiplies by 1000)
- ✅ Updates `gem_balance` and `total_gems_earned` automatically
- ✅ Still saves `calculated_earnings` to sessions for records

### Background Monitor (`backend/cashout_monitor.py`)
- ✅ Periodic task checks pending cashout transactions
- ✅ Auto-approves completed HITs
- ✅ Returns gems to wallet if HITs expire
- ✅ Integrated into app startup/shutdown lifecycle

### Documentation
- ✅ Updated `README.md` with gem economy documentation
- ✅ Listed future enhancement plans (level bonuses, rogue-like features, etc.)

## ✅ COMPLETED: Frontend Wallet Components

### Core Wallet Functionality
- ✅ `frontend/src/services/walletAPI.js` - API service for wallet operations
- ✅ `frontend/src/components/Wallet.jsx` - Full wallet page with balance display, cashout button, transaction history
- ✅ `frontend/src/components/CashoutModal.jsx` - Cashout request modal with amount input
- ✅ `frontend/src/pages/CashoutConfirm.jsx` - MTurk HIT confirmation page

## 🔨 TODO: Remaining Frontend Integration (Simple UI Updates)

### 1. Profile Page with Worker ID Field
**File to create:** `frontend/src/pages/ProfilePage.jsx`

```jsx
// Profile page that displays:
// - User info (user_id, email, join date)
// - Gem statistics (from /api/profile)
// - MTurk Worker ID input field with validation
// - Save button that calls updateMTurkWorkerId()
// Reference: Use walletAPI.getUserProfile() and walletAPI.updateMTurkWorkerId()
```

**Pattern:** Similar to existing pages like `DashboardPage.jsx`

### 2. Update Game Results
**File to modify:** `frontend/src/components/GameOver.jsx`

```jsx
// Add after existing gamification display:
// - Show gems earned from this game
// - Link to /wallet page
// - Reference gamificationData.gems_earned if available
```

**Changes needed:**
- Add gems earned display after points animation
- Add "View Wallet" button linking to `/wallet`
- Update completion modal to mention gems earned

### 3. Navigation Updates
**Files to modify:** Main navigation component (likely `App.jsx` or `NavBar.jsx`)

```jsx
// Add to navigation:
// - "Wallet" link to /wallet route
// - Gem balance badge in header (fetch from /api/wallet/balance)
// - Display as "💎 {balance}" next to user menu
```

**Pattern:**
- Use `useEffect` to fetch balance on mount
- Poll balance every 30 seconds while user is active
- Show loading state while fetching

### 4. Routes Registration
**File to modify:** `frontend/src/App.jsx` (or main router file)

```jsx
// Add routes:
import Wallet from './components/Wallet';
import CashoutConfirm from './pages/CashoutConfirm';
import ProfilePage from './pages/ProfilePage';

// In router:
<Route path="/wallet" element={<ProtectedRoute><Wallet /></ProtectedRoute>} />
<Route path="/cashout-confirm" element={<CashoutConfirm />} />
<Route path="/profile" element={<ProtectedRoute><ProfilePage /></ProtectedRoute>} />
```

## 📋 Deployment Steps

### 1. Run Database Migration
```bash
cd backend
python -m alembic upgrade head
```

### 2. Migrate Existing Earnings (One-time)
```bash
cd backend
python migrate_to_gems.py
```

### 3. Update Environment Variables
```bash
# Add to .env:
MINIMUM_CASHOUT_AMOUNT=2.00
CASHOUT_HIT_DURATION=86400
CASHOUT_HIT_AUTO_APPROVE=3600
CASHOUT_MONITOR_INTERVAL=300
```

### 4. Restart Backend
```bash
# Backend will auto-start the cashout monitor
python main.py
```

### 5. Test Cashout Flow (Sandbox)

1. **Earn Gems**: Play a game to earn gems
2. **Add Worker ID**: Go to profile, add MTurk Worker ID
3. **Request Cashout**: Navigate to /wallet, click "Request Cash Out"
4. **Check HIT**: Open the MTurk HIT URL provided
5. **Complete HIT**: Accept and submit the HIT
6. **Verify**: Monitor logs for auto-approval (within 1 hour)

## 🎯 System Flow

### User Flow
1. Player registers/logs in
2. Plays games and earns gems automatically:
   - **Single-human:** 50 gems per game
   - **Multi-human:** 100 base + stakes (based on performance)
3. Views balance in dashboard or wallet page
4. When ready, adds MTurk Worker ID to profile
5. Requests cashout (minimum $2.00 = 2000 gems)
6. System creates unique qualification + HIT
7. Player accepts HIT on MTurk
8. System auto-approves within 1 hour
9. Payment sent via MTurk

### Technical Flow
```
Game Completed
  ↓
Calculate Rewards (gems)
  │
  ├─ Single-human: 50 gems for all
  │
  └─ Multi-human: 
      ├─ Deduct stakes (minimum_stake from all players)
      ├─ Determine winners (most votes)
      ├─ Calculate voting accuracy for each player
      └─ Distribute rewards:
          ├─ Base: 100 gems (if voted)
          ├─ Winners: stake_refund + (accuracy × share of loser_pool)
          └─ Losers: 0 stake return (forfeited)
  ↓
Credit to user.gem_balance (atomic transaction)
  ↓
Update user.total_gems_earned

User Requests Cashout ($2.00)
  ↓
Validate (worker_id, balance >= minimum)
  ↓
Create Qualification for Worker
  ↓
Assign Qualification to Worker
  ↓
Create HIT with Qualification Requirement
  ↓
Deduct Gems from Balance (pending)
  ↓
Worker Accepts & Completes HIT
  ↓
Monitor detects submission
  ↓
Auto-Approve Assignment
  ↓
Mark Transaction as Completed
  ↓
Update user.total_gems_cashed_out
```

## 🔧 Configuration Options

All configurable via environment variables:

```bash
# Minimum cashout amount (USD)
MINIMUM_CASHOUT_AMOUNT=2.00

# HIT duration (24 hours = 86400 seconds)
CASHOUT_HIT_DURATION=86400

# Auto-approval delay (1 hour = 3600 seconds)
CASHOUT_HIT_AUTO_APPROVE=3600

# Monitor check interval (5 minutes = 300 seconds)
CASHOUT_MONITOR_INTERVAL=300

# Gems per dollar
# GEMS_PER_DOLLAR=1000 (hardcoded in config.py, change if needed)
```

## 🐛 Troubleshooting

### Gems Not Credited After Game
- Check backend logs for "💎 Credited" message
- Verify migration 007 was applied: `python -m alembic current`
- Check user record in database: `gem_balance` and `total_gems_earned` columns

### Cashout HIT Not Visible
- Verify qualification was created and assigned (check backend logs)
- Confirm worker is logged into correct MTurk environment (sandbox/prod)
- Check HIT hasn't expired (24 hours)
- Verify worker ID format is correct (starts with 'A')

### Monitor Not Running
- Check startup logs for "✅ Cashout monitor started"
- Verify no errors in monitor initialization
- Check `CASHOUT_MONITOR_INTERVAL` is set correctly

### HIT Not Auto-Approved
- Verify worker submitted HIT (check MTurk dashboard)
- Check monitor logs for processing messages
- Manually trigger check: call `/api/wallet/cashout-status/{transaction_id}`
- Verify `CASHOUT_HIT_AUTO_APPROVE` delay has passed

## 🚀 Future Enhancements (As Noted in README)

1. **Level-Based Bonuses**: Higher level = more gems per game
2. **Achievement Rewards**: Bonus gems for achievements
3. **Rogue-like Features**: Buy power-ups with gems
4. **Daily Bonuses**: Login streaks
5. **Referral System**: Earn gems for referrals
6. **Leaderboards**: Compete for top earner status

## 📊 Database Schema Reference

### Users Table (New Columns)
```sql
gem_balance INTEGER DEFAULT 0 NOT NULL
total_gems_earned INTEGER DEFAULT 0 NOT NULL
total_gems_cashed_out INTEGER DEFAULT 0 NOT NULL
mturk_worker_id VARCHAR(255) NULLABLE (indexed)
```

### CashoutTransactions Table
```sql
id UUID PRIMARY KEY
user_id UUID FOREIGN KEY
amount_gems INTEGER NOT NULL
amount_usd DECIMAL(10,2) NOT NULL
status VARCHAR(20) NOT NULL  -- pending, hit_created, completed, failed, cancelled
mturk_hit_id VARCHAR(255)
mturk_assignment_id VARCHAR(255)
mturk_qualification_id VARCHAR(255)
created_at DATETIME NOT NULL
completed_at DATETIME
expires_at DATETIME
error_message TEXT
```

## ✨ Key Features Delivered

1. ✅ **Standalone Game Economy**: MTurk is just the payment processor
2. ✅ **Immediate Rewards**: Gems credited after each game
3. ✅ **Worker-Specific HITs**: Only cashout requester can see/complete HIT
4. ✅ **Auto-Approval**: No manual intervention needed
5. ✅ **Expired HIT Handling**: Gems automatically returned to wallet
6. ✅ **Transaction History**: Full audit trail of cashouts
7. ✅ **Flexible Minimum**: Configurable minimum cashout threshold
8. ✅ **Validation**: Worker ID format validation, balance checks
9. ✅ **Background Monitoring**: Automatic HIT status checking
10. ✅ **Dual Systems**: Gems (money) separate from XP/Points (gamification)

---

**Status**: Backend 100% Complete | Frontend Core Complete | Remaining: Simple UI Integration

**Next Steps**: Complete the 4 simple frontend tasks above, then run deployment steps and test in sandbox.

