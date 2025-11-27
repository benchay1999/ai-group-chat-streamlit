# MTurk Standing HIT System - How Multiple Cashouts Work

## Your Question

> "If a worker submits the hash key to the HIT, then the worker cannot do the same task again? If this is the case, how can a user submit the hash keys multiple times?"

## Short Answer

✅ **Workers CAN submit multiple times!** The system uses a **"Standing HIT"** with `MaxAssignments=99,999`, which allows the **same worker** to complete the **same HIT** up to 99,999 times.

## How It Works

### The Standing HIT Concept

Instead of creating a **NEW HIT for every cashout**, the system creates **ONE HIT** that can be completed **many times**.

```
Traditional Approach (NOT used):
  Cashout #1 → Create HIT #1 (MaxAssignments=1) → Worker completes → HIT #1 done ❌
  Cashout #2 → Create HIT #2 (MaxAssignments=1) → Worker completes → HIT #2 done ❌
  Problem: Workers can't find the same HIT again!

Standing HIT Approach (USED):
  Setup: Create ONE HIT (MaxAssignments=99,999) ✅
  Cashout #1 → Worker submits code A → Assignment 1/99,999 complete
  Cashout #2 → Worker submits code B → Assignment 2/99,999 complete
  Cashout #3 → Worker submits code C → Assignment 3/99,999 complete
  ...and so on up to 99,999 times!
```

### Key Settings

From `backend/create_standing_hit.py`:

```python
max_assignments = 99999  # Production (allows 99,999 separate cashouts)
# OR
max_assignments = 1000   # Sandbox (allows 1,000 cashouts for testing)

response = mturk.create_hit(
    Title='ChatGame - Redeem Your Earnings (Instant Payment)',
    Reward='0.01',  # Base reward
    MaxAssignments=max_assignments,  # ← THE KEY SETTING!
    LifetimeInSeconds=31536000,  # 1 year
    # ...
)
```

## The Flow Explained

### 1. Initial Setup (Done Once)

```bash
# Administrator runs this ONCE
python backend/create_standing_hit.py
```

This creates:
- **ONE HIT** with a unique HIT ID
- **MaxAssignments = 99,999** (can be completed 99,999 times)
- **Lifetime = 1 year** (stays available for 1 year)
- **No qualification requirements** (all workers can see it)

The HIT ID is saved to `.env`:
```
CASHOUT_HIT_ID=3N4EXAMPLE5M6L7K8J9H0
```

### 2. User Requests Cashout #1

```
User: "I want to cash out 5000 gems ($5.00)"
System:
  1. Deducts 5000 gems from user's balance
  2. Generates unique redemption code: "a1b2c3d4e5f6..."
  3. Stores transaction in database:
     - redemption_code: "a1b2c3d4e5f6..."
     - amount_usd: $5.00
     - status: PENDING
  4. Gives user the redemption code + HIT URL
```

### 3. Worker Submits First Redemption

```
Worker:
  1. Visits the standing HIT URL
  2. Sees the HIT (still available, showing 99,999 assignments)
  3. Accepts assignment (takes 1 of 99,999 slots)
  4. Pastes redemption code: "a1b2c3d4e5f6..."
  5. Submits assignment

System:
  1. Validates redemption code is unique and valid
  2. Approves assignment immediately
  3. Sends $0.01 base reward + $4.99 bonus = $5.00 total
  4. Marks transaction as COMPLETED
  5. HIT now shows 99,998 assignments remaining
```

### 4. User Requests Cashout #2 (Same User!)

```
User: "I want to cash out 3000 gems ($3.00)"
System:
  1. Deducts 3000 gems
  2. Generates NEW redemption code: "z9y8x7w6v5u4..."  ← DIFFERENT CODE
  3. Stores NEW transaction
  4. Gives user the SAME HIT URL (still the standing HIT)
```

### 5. Worker Submits Second Redemption

```
Worker:
  1. Visits the SAME standing HIT URL
  2. Sees the HIT (still available, 99,998 assignments left)
  3. Accepts assignment (takes another slot)  ← NEW ASSIGNMENT
  4. Pastes NEW redemption code: "z9y8x7w6v5u4..."
  5. Submits assignment

System:
  1. Validates NEW code is unique and valid
  2. Approves assignment immediately
  3. Sends $3.00 total
  4. Marks transaction as COMPLETED
  5. HIT now shows 99,997 assignments remaining
```

## Why This Works

### MTurk Assignment Concept

In MTurk:
- **HIT** = The task definition (title, description, reward, etc.)
- **Assignment** = A single completion of that HIT

**Key Point**: `MaxAssignments` controls how many separate **assignments** (completions) are allowed for the **same HIT**.

### Example Analogy

Think of it like a restaurant:
- **Traditional**: Each customer gets a custom menu (one HIT per person) ❌
- **Standing HIT**: One menu (HIT) that 99,999 customers can order from ✅

The menu stays the same, but each customer's order (assignment) is unique.

## Database Structure

### Redemption Codes Are Unique

From `backend/database.py`:

```python
class CashoutTransaction(Base):
    id = Column(UUID, primary_key=True)
    user_id = Column(UUID, ForeignKey('users.id'))
    amount_usd = Column(DECIMAL(10, 2))
    
    # Each transaction has a UNIQUE redemption code
    redemption_code = Column(String(64), unique=True)  # ← UNIQUE!
    
    # MTurk details (filled when worker submits)
    mturk_worker_id = Column(String(255))      # e.g., A1BC2DEF3GHI
    mturk_assignment_id = Column(String(255))  # e.g., Assignment123 (unique per submission)
    mturk_hit_id = Column(String(255))         # e.g., HIT456 (SAME for all)
```

### Key Fields:

1. **redemption_code**: UNIQUE per cashout (different every time)
2. **mturk_assignment_id**: UNIQUE per submission (different every time)
3. **mturk_hit_id**: SAME for all cashouts (the standing HIT)

## Example Scenario

Let's say user "Alice" (MTurk Worker ID: A1BCDEFG) plays multiple games:

### Cashout #1: $5.00
```
Transaction ID: tx-001
Redemption Code: "a1b2c3d4..."
Worker ID: A1BCDEFG
Assignment ID: assignment-001  ← UNIQUE
HIT ID: hit-standing-001      ← SAME
Status: COMPLETED
```

### Cashout #2: $3.00
```
Transaction ID: tx-002
Redemption Code: "z9y8x7w6..."  ← DIFFERENT CODE
Worker ID: A1BCDEFG            ← SAME WORKER
Assignment ID: assignment-002  ← DIFFERENT ASSIGNMENT
HIT ID: hit-standing-001      ← SAME HIT
Status: COMPLETED
```

### Cashout #3: $10.00
```
Transaction ID: tx-003
Redemption Code: "m5n6o7p8..."  ← DIFFERENT CODE
Worker ID: A1BCDEFG            ← SAME WORKER
Assignment ID: assignment-003  ← DIFFERENT ASSIGNMENT
HIT ID: hit-standing-001      ← SAME HIT
Status: COMPLETED
```

**Result**: Alice successfully cashed out 3 times using the SAME HIT!

## Advantages of Standing HIT

### ✅ Worker Convenience
- Workers bookmark ONE HIT URL
- No need to search for new HITs
- Familiar interface every time

### ✅ System Simplicity
- Create HIT once, use forever
- No HIT creation overhead per cashout
- Less API calls to MTurk

### ✅ Scalability
- Supports up to 99,999 cashouts per year
- When limit reached, create a new standing HIT
- Easy to monitor (one HIT to track)

### ✅ Cost Efficiency
- MTurk charges per HIT creation
- Standing HIT = create once, pay once
- Bonuses have no additional fees

## Limitations & Considerations

### 1. MaxAssignments Limit
- **Production**: 99,999 assignments max
- **Sandbox**: 1,000 assignments max (for testing)
- When limit reached, must create a new standing HIT

### 2. Pre-Authorization
MTurk pre-authorizes funds based on MaxAssignments:
```
Pre-auth = MaxAssignments × Base Reward
         = 99,999 × $0.01
         = $999.99
```

This is held (not charged) from your MTurk account balance.

### 3. Expiration
- Standing HIT lifetime: 1 year
- After 1 year, create a new standing HIT
- Or extend the HIT using `extend_hit_assignments.py`

### 4. Code Security
- Redemption codes are SHA-256 hashes (secure)
- Each code can only be used ONCE
- Codes are validated server-side

## Monitoring Standing HIT

Check HIT status:

```bash
cd backend
python check_hit_status.py
```

Output:
```
HIT ID: 3N4EXAMPLE5M6L7K8J9H0
Status: Reviewable
Max Assignments: 99,999
Completed: 127
Pending: 2
Available: 99,870
```

## When to Create a New Standing HIT

Create a new standing HIT when:
1. Current HIT is full (99,999 assignments used)
2. Current HIT expired (after 1 year)
3. Need to change HIT parameters (title, description, etc.)
4. Switching environments (sandbox ↔ production)

## Code References

### HIT Creation
- **File**: `backend/create_standing_hit.py`
- **Key Setting**: `MaxAssignments=99999`

### Cashout Request
- **File**: `backend/main.py` (lines 2506-2650)
- **Flow**: Generate code → Store transaction → Return HIT URL

### Redemption
- **File**: `backend/cashout_service.py` (lines 200-400)
- **Flow**: Validate code → Approve assignment → Send payment

### Database
- **File**: `backend/database.py` (lines 197-234)
- **Model**: `CashoutTransaction` with unique redemption codes

## FAQ

### Q: Can the same worker submit the same code twice?
**A**: No! Each redemption code can only be used once (enforced by database UNIQUE constraint).

### Q: What if MaxAssignments runs out?
**A**: You'll need to create a new standing HIT and update `CASHOUT_HIT_ID` in `.env`.

### Q: Can different workers use the same standing HIT?
**A**: Yes! That's the beauty of it. All workers see the same HIT and can submit their unique codes.

### Q: What happens to completed assignments?
**A**: They remain in the HIT's history but don't prevent new submissions (as long as MaxAssignments isn't reached).

### Q: Is this an MTurk best practice?
**A**: Yes! Standing HITs are commonly used for:
- Receipt verification systems
- Redemption code systems
- Survey pools
- Ongoing data collection

## Summary

**Your concern**: "Workers can't do the same task again"  
**Reality**: ✅ Workers CAN because it's a **Standing HIT** with 99,999 assignments

**The Magic**:
1. ONE HIT (stays available)
2. MANY assignments (up to 99,999)
3. UNIQUE codes (different every cashout)
4. SAME worker (can complete multiple times)

**Result**: Perfect system for repeat cashouts! 🎉

---

**Last Updated**: October 31, 2025  
**Status**: Production-Ready ✅

