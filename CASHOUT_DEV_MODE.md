# Cashout System - Development Mode

## Overview

The cashout system now has a **Development Mode** that allows you to test the gem redemption flow without needing to go through actual MTurk HITs.

---

## 🧪 **Development Mode Features**

### What It Does:
- ✅ **Skips MTurk API calls** - No actual assignment approval needed
- ✅ **Simulates successful redemption** - Marks transaction as completed
- ✅ **Allows direct testing** - Access cashout-confirm page without MTurk
- ✅ **Preserves gem balance changes** - Gems are deducted/returned properly
- ✅ **Full transaction tracking** - Everything is logged in database

### What It Doesn't Do:
- ❌ **No actual MTurk payment** - Real money isn't sent
- ❌ **No MTurk assignment approval** - Assignment IDs are fake
- ❌ **No bonus payment** - Bonus logic is skipped

---

## 🚀 **How to Use Development Mode**

### Method 1: Direct URL Access (Recommended for Testing)

1. **Request a cashout in the game** (you'll get a redemption code)
2. **Go directly to cashout-confirm page**:
   ```
   http://localhost:5173/cashout-confirm?dev=true
   ```
3. **Paste your redemption code** and submit
4. ✅ **Success!** Transaction completes without MTurk

### Method 2: Automatic (on localhost)

When running on `localhost`, dev mode is **automatically enabled**:

1. Request cashout in game
2. Click the cashout link
3. If on localhost, fake MTurk IDs are used automatically
4. Paste code and submit - works!

---

## 📋 **Testing the Full Flow**

### Step 1: Earn Gems
Play a single-player game:
```
Expected gems: ~2850 (includes 2000 bonus)
```

### Step 2: Request Cashout
1. Go to wallet/profile
2. Click "Cash Out"
3. Enter amount (minimum $2.00 = 2000 gems)
4. You'll get a **redemption code** (64 characters)

Example code:
```
abc123def456...
```

### Step 3: Redeem Code (Dev Mode)
Go to:
```
http://localhost:5173/cashout-confirm?dev=true
```

Paste your code and click "Submit & Claim Payment"

### Step 4: Verify
You should see:
```
✅ Redemption Successful! 🧪
$X.XX redeemed (dev mode)

🧪 Development Mode
No actual MTurk payment processed. This is for testing only.
```

### Step 5: Check Database
Your transaction should be marked as `COMPLETED` with:
- Status: COMPLETED
- Worker ID: DEV_WORKER_TEST
- Assignment ID: DEV_ASSIGNMENT_TEST
- Completed timestamp

---

## 🔍 **How It Works**

### Backend (cashout_service.py)

```python
# Checks if in dev mode
mturk_environment = os.getenv('MTURK_ENVIRONMENT', 'sandbox')
is_dev_mode = (mturk_environment == 'sandbox' and 
              (not assignment_id or assignment_id.startswith('DEV_') or 
               assignment_id == 'ASSIGNMENT_ID_NOT_AVAILABLE'))

if not is_dev_mode:
    # Normal flow: Call MTurk API
    mturk_client.approve_assignment(...)
else:
    # Dev mode: Skip MTurk, just log
    print("🧪 DEV MODE: Skipping MTurk API call")
```

### Frontend (CashoutConfirm.jsx)

```javascript
// Auto-detects dev mode
const isDevMode = params.get('dev') === 'true' || 
                  window.location.hostname === 'localhost';

if (isDevMode) {
  // Use fake MTurk IDs
  setAssignmentId('DEV_ASSIGNMENT_TEST');
  setWorkerId('DEV_WORKER_TEST');
  setHitId('DEV_HIT_TEST');
}
```

---

## ⚠️ **Important Notes**

### When Dev Mode Activates:

1. **MTURK_ENVIRONMENT = sandbox** (in .env)
2. **AND** one of:
   - Assignment ID starts with `DEV_`
   - Assignment ID is empty/null
   - Assignment ID is `ASSIGNMENT_ID_NOT_AVAILABLE`
   - Running on `localhost`

### Production Safety:

- ✅ Dev mode **ONLY works in sandbox**
- ✅ Production environment **always requires real MTurk IDs**
- ✅ Invalid assignment IDs in production will **fail** (as intended)

---

## 🧰 **Console Output**

### Development Mode:
```
💎 Starting gem credit process for 1 mapped players
💵 Calculated earnings for Player1: $0.85
🧪 DEV MODE: Skipping MTurk API call for testing (assignment_id: DEV_ASSIGNMENT_TEST)
   In production, this would approve assignment and send payment
✅ Redeemed cashout code for user test_user
   Amount: $2.50
   Worker: DEV_WORKER_TEST
```

### Production Mode:
```
💎 Starting gem credit process for 1 mapped players
💵 Calculated earnings for Player1: $0.85
✅ Approved assignment: 3XXXXXXXXX
✅ Sent bonus: $2.49
✅ Redeemed cashout code for user worker_A1B2C3D4
   Amount: $2.50
   Worker: A1B2C3D4EFGH5678
```

---

## 🐛 **Troubleshooting**

### "Payment processing failed" Error

**Still getting this error?** Check:

1. ✅ MTURK_ENVIRONMENT is `sandbox` in .env
2. ✅ Backend is restarted after code changes
3. ✅ You're using the dev URL: `?dev=true`
4. ✅ Redemption code is valid and not already used

### "Invalid redemption code"

- Code might be expired (7 days)
- Code already redeemed
- Typo in code (they're 64 characters, easy to mistype)

### "This cashout was cancelled"

- Previous redemption attempt failed
- Gems should be returned to your balance
- Request a new cashout

---

## 📊 **Testing Checklist**

- [ ] Earn gems by playing game
- [ ] Request cashout (minimum $2.00)
- [ ] Receive redemption code
- [ ] Access /cashout-confirm?dev=true
- [ ] Paste code and submit
- [ ] See success message with dev mode indicator
- [ ] Verify transaction in database (status: COMPLETED)
- [ ] Check gem balance reduced correctly
- [ ] Try using same code again (should fail: "already redeemed")
- [ ] Request new cashout with updated balance

---

## 🚀 **Switching to Production**

When ready for real MTurk payments:

1. **Update .env**:
   ```bash
   MTURK_ENVIRONMENT=production
   ```

2. **Create production HIT**:
   ```bash
   python create_standing_hit.py
   # Confirm you want production mode
   # Get new HIT ID
   ```

3. **Update .env with production HIT ID**:
   ```bash
   CASHOUT_HIT_ID=3XXXXXXXXX  # New production HIT
   ```

4. **Restart backend**

5. **Test with REAL MTurk worker**:
   - Worker must accept HIT from MTurk
   - Worker pastes code in HIT interface
   - Real payment processed

---

## ✅ **Summary**

**Dev Mode** = Quick testing without MTurk complexity  
**Production Mode** = Real payments, real MTurk workflow

Both modes:
- Track transactions properly
- Validate redemption codes
- Update gem balances correctly
- Log all activities

The only difference: Dev mode skips the actual MTurk API calls!

**Current Status**: ✅ Ready for development testing

