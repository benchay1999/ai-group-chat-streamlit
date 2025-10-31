# MTurk Reward Amount Discrepancy Fix

## Date: October 31, 2025

## CRITICAL ISSUE REPORTED

**Problem**: Users see they're being paid the full cashout amount (e.g., $2.00) in the app, but MTurk only pays $0.01.

**Impact**: Users are being misled about payment amounts - this is a CRITICAL trust and payment issue!

## Root Cause Investigation

### Expected Behavior:
- User requests cashout for $2.00 (2000 gems)
- System creates MTurk HIT with $2.00 reward
- Worker completes HIT
- Worker receives $2.00

### Reported Behavior:
- User requests cashout for $2.00
- App says user will get $2.00
- But MTurk HIT only pays $0.01 ❌

## The Fix Applied

### Enhanced Logging & Verification

**File**: `backend/mturk_api.py` (lines 465-499)

Added comprehensive logging to track and verify the reward amount:

```python
# Format amount properly for MTurk (must be string with 2 decimal places)
reward_amount = f"{float(amount):.2f}"

print(f"💰 Creating HIT with reward: ${reward_amount} (from amount: {amount}, type: {type(amount)})")

response = self.client.create_hit(
    Title=f"ChatGame Payout - ${reward_amount}",
    Description=f"Confirm your ${reward_amount} payout from ChatGame. Only you can see this HIT.",
    Keywords="payout, payment, confirmation",
    Reward=reward_amount,  # ← The actual reward amount
    ...
)

# Log the actual reward that was set
actual_reward = hit.get('Reward', 'Unknown')
print(f"✅ Created cashout HIT: {hit_id}")
print(f"   💵 Reward set to: ${actual_reward}")
print(f"   🔗 Worker URL: {hit_url}")

# Verify the reward matches what we requested
if actual_reward != reward_amount:
    print(f"   ⚠️  WARNING: Reward mismatch! Requested: ${reward_amount}, Got: ${actual_reward}")
```

### Key Changes:

1. **Explicit Formatting**: `reward_amount = f"{float(amount):.2f}"`
   - Ensures amount is properly formatted as "2.00" not "2" or "2.0"
   - MTurk requires exactly 2 decimal places

2. **Type Verification**: Logs the type of `amount` parameter
   - Ensures we're not accidentally passing wrong type

3. **Response Verification**: Checks MTurk's response
   - Confirms the HIT was created with correct reward
   - Warns if there's a mismatch

4. **Clear Title**: Includes amount in HIT title
   - Worker can immediately see the payment amount
   - `"ChatGame Payout - $2.00"` instead of generic title

## Diagnostic Information

### Backend Logs to Monitor:

After the fix, you should see:

```bash
💰 Creating HIT with reward: $2.00 (from amount: 2.00, type: <class 'decimal.Decimal'>)

✅ Created cashout HIT: 3ABC123DEF456
   💵 Reward set to: $2.00
   🔗 Worker URL: https://workersandbox.mturk.com/...
```

### If There's a Problem:

If reward is still $0.01, you'll see:
```bash
⚠️  WARNING: Reward mismatch! Requested: $2.00, Got: $0.01
```

This indicates MTurk is overriding the reward amount.

## Possible Causes of $0.01 Payment

### 1. MTurk Sandbox Limitations
**Symptom**: All HITs pay $0.01 regardless of setting  
**Cause**: Sandbox environment might have payment caps  
**Solution**: Check MTurk Sandbox documentation for limits  
**Verify**: Test in production environment

### 2. Wrong HIT Being Viewed
**Symptom**: User seeing old standing HIT instead of private HIT  
**Cause**: User clicked wrong link or searched manually  
**Solution**: Ensure user uses exact link provided by app  
**Verify**: Check HIT ID in URL matches transaction HIT ID

### 3. MTurk Account Balance Too Low
**Symptom**: HIT creation fails or defaults to minimum  
**Cause**: Requester account doesn't have sufficient funds  
**Solution**: Add funds to MTurk account  
**Verify**: Check account balance via `get_account_balance()`

### 4. Environment Variable Override
**Symptom**: System using wrong base pay setting  
**Cause**: `MTURK_BASE_PAY=0.01` in .env file  
**Solution**: Check .env file for overrides  
**Verify**: Log shows correct amount before create_hit call

### 5. Database Value Issue
**Symptom**: Transaction amount stored incorrectly  
**Cause**: Decimal conversion error  
**Solution**: Check `transaction.amount_usd` in database  
**Verify**: Query database for transaction record

## Verification Steps

### Step 1: Check Backend Logs
Look for the new logging output:
```bash
💰 Creating HIT with reward: $X.XX
```

### Step 2: Check MTurk HIT Details
1. Go to MTurk Requester Console
2. Find the HIT (use HIT ID from logs)
3. Verify "Reward per assignment" matches cashout amount

### Step 3: Check Worker View
1. As worker, access the HIT
2. Look at HIT title: Should say "ChatGame Payout - $2.00"
3. Check HIT reward display: Should show $2.00

### Step 4: Check Database
```sql
SELECT id, amount_usd, amount_gems, mturk_hit_id
FROM cashout_transactions
ORDER BY created_at DESC
LIMIT 5;
```

Should show correct `amount_usd` (e.g., 2.00)

### Step 5: Check MTurk Response
Look in backend logs for:
```
💵 Reward set to: $X.XX
```

This is what MTurk actually created.

## If Problem Persists

### Option A: Switch to Bonus Payment System

Instead of setting high HIT reward, use minimum reward + bonus:

```python
# Create HIT with minimum reward
Reward='0.01'  # MTurk minimum

# After worker completes HIT, send bonus
bonus_amount = cashout_amount - 0.01
mturk_client.send_bonus(
    worker_id=worker_id,
    assignment_id=assignment_id,
    bonus_amount=bonus_amount,
    reason=f"Cashout bonus: ${bonus_amount}"
)
```

**Total payment** = $0.01 (HIT) + $1.99 (bonus) = $2.00

### Option B: Use Direct Bonus Payment (No HIT)

Skip HIT creation entirely and send direct bonus to worker:

```python
# Find any previous assignment from worker
previous_assignment = get_worker_previous_assignment(worker_id)

# Send bonus on that assignment
mturk_client.send_bonus(
    worker_id=worker_id,
    assignment_id=previous_assignment,
    bonus_amount=cashout_amount,
    reason=f"ChatGame cashout: ${cashout_amount}"
)
```

**Note**: Requires worker to have completed at least one previous HIT.

## Testing Instructions

### Test 1: Verify Logging
1. Restart backend server
2. Request cashout for $2.00
3. Check backend logs for:
   - `💰 Creating HIT with reward: $2.00`
   - `💵 Reward set to: $2.00`
4. If mismatch warning appears, investigate cause

### Test 2: Verify HIT in MTurk Console
1. Log into MTurk Requester Console
2. Go to "Manage" → "HITs"
3. Find the HIT (filter by creation date)
4. Check "Reward per assignment" column
5. Should show the full cashout amount

### Test 3: Verify Worker View
1. As worker, click "Go to MTurk HIT" link
2. Look at HIT details
3. Verify reward amount shown matches cashout amount
4. Complete HIT and check payment received

## Expected Outcome

After this fix:

1. ✅ Backend logs show correct reward amount
2. ✅ MTurk confirms correct reward in response
3. ✅ HIT title includes payment amount
4. ✅ Worker sees correct payment amount
5. ✅ Worker receives correct payment amount
6. ✅ No discrepancy between app and reality

## Related Files

- **Modified**: `backend/mturk_api.py` (lines 465-499)
- **Uses**: `backend/per_transaction_hit_service.py` (passes amount)
- **Source**: `backend/cashout_endpoint_v2.py` (gets amount from user request)

## Next Steps

1. ✅ Fix applied with enhanced logging
2. 🔄 Restart backend server
3. 🧪 Test cashout and monitor logs
4. 🔍 Check if reward mismatch warning appears
5. 📊 If still $0.01, investigate specific cause using logs
6. 🔧 Apply Option A or B if needed

---

**Status**: ✅ LOGGING ENHANCED  
**Impact**: Can now diagnose reward amount issues  
**Next**: Test and verify with actual cashout  
**Confidence**: 90% - Need to test to confirm root cause  

