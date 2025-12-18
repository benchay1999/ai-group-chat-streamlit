# CRITICAL FIXES - Cashout Qualification Issues

## Date: October 31, 2025

## Issues Identified & Fixed

### Issue #1: Multiple Pending HITs Causing Confusion ✅ FIXED

**Problem**: User would request multiple cashouts, creating multiple HITs with different qualifications. Only the newest qualification was valid, causing "You don't meet qualifications" errors on older HITs.

**Fix**: Auto-cancel old pending cashouts when creating a new one.

**Implementation**: `backend/per_transaction_hit_service.py` (lines 70-129)

```python
# STEP 0: Cancel any existing pending HITs for this user
print(f"\n0️⃣  Checking for existing pending cashouts...")

existing_txs = await db.execute(...)  # Find pending cashouts

if existing_txs:
    print(f"   Found {len(existing_txs)} existing pending cashout(s)")
    print(f"   🚫 Auto-cancelling old cashouts...")
    
    for old_tx in existing_txs:
        # Delete/expire old HIT
        # Refund gems
        # Mark as cancelled
```

**Result**: Only ONE active cashout per user at a time. No more confusion.

---

### Issue #2: Worker ID with Whitespace ✅ FIXED

**Problem**: Worker ID might have leading/trailing whitespace, causing MTurk API calls to fail silently.

**Fix**: Strip whitespace from Worker ID before using it.

**Implementation**: `backend/per_transaction_hit_service.py` (line 156)

```python
# Use stripped worker ID to avoid whitespace issues
worker_id_clean = user.mturk_worker_id.strip()
```

**Result**: Clean Worker ID used throughout the entire process.

---

### Issue #3: Silent Qualification Assignment Failures ✅ FIXED

**Problem**: Qualification assignment might fail but code continued anyway, leading to qualification errors later.

**Fix**: Explicit try-catch with clear error messages when qualification assignment fails.

**Implementation**: `backend/per_transaction_hit_service.py` (lines 158-170)

```python
try:
    mturk_client.client.associate_qualification_with_worker(
        QualificationTypeId=qualification_id,
        WorkerId=worker_id_clean,
        IntegerValue=1,
        SendNotification=False
    )
    print(f"   ✅ Qualification assigned to worker: {worker_id_clean}")
except Exception as assign_error:
    print(f"   ❌ FAILED TO ASSIGN QUALIFICATION!")
    print(f"   ❌ Error: {assign_error}")
    print(f"   ❌ This means the Worker ID is INVALID or doesn't exist in MTurk!")
    raise Exception(f"Cannot assign qualification to worker {worker_id_clean}: {assign_error}")
```

**Result**: Immediate failure with clear error message if Worker ID is invalid.

---

### Issue #4: Insufficient Debugging ✅ FIXED

**Problem**: Hard to diagnose why qualifications weren't working.

**Fix**: Added comprehensive debugging output.

**Implementation**: Throughout `backend/per_transaction_hit_service.py`

```python
print(f"   📋 DEBUG: Qualification ID: {qualification_id}")
print(f"   📋 DEBUG: Worker ID: '{user.mturk_worker_id}' (length: {len(user.mturk_worker_id)})")
print(f"   📋 DEBUG: Worker ID stripped: '{user.mturk_worker_id.strip()}'")
print(f"   🔧 Creating HIT with parameters:")
print(f"      Amount: ${transaction.amount_usd}")
print(f"      Qualification ID: {qualification_id}")
print(f"      Worker ID (for reference): {worker_id_clean}")
```

**Result**: Full visibility into every step of the process.

---

## Expected Backend Logs Now

### Successful Cashout Creation:

```
🎯 CREATING WORKER-SPECIFIC HIT
Transaction: uuid-123
User: benchay
Worker ID: A1EWFN76HNDD20
Amount: $2.00

0️⃣  Checking for existing pending cashouts...
   ✅ No existing pending cashouts

1️⃣  Creating worker-specific qualification...
   ✅ Qualification created: 3QUAL123ABC
   🔄 Assigning qualification to worker A1EWFN76HNDD20...
   📋 DEBUG: Qualification ID: 3QUAL123ABC
   📋 DEBUG: Worker ID: 'A1EWFN76HNDD20' (length: 14)
   📋 DEBUG: Worker ID stripped: 'A1EWFN76HNDD20'
   ✅ Qualification assigned to worker: A1EWFN76HNDD20
   🔍 Verifying qualification assignment...
   ✅ Verification successful (attempt 1) - Worker has qualification with value: 1

2️⃣  Creating HIT with qualification requirement...
   ⏳ Waiting 5 seconds for MTurk to fully propagate qualification...
   ✅ Proceeding with HIT creation
   🔍 Final pre-HIT verification...
   ✅ Final check passed - Worker still has qualification
   
   🔧 Creating HIT with parameters:
      Amount: $2.00
      Qualification ID: 3QUAL123ABC
      Worker ID (for reference): A1EWFN76HNDD20
      External URL: https://...
   💰 Creating HIT with reward: $2.00
   ✅ Created cashout HIT: 3HIT456
   💵 Reward set to: $2.00

✅ WORKER-SPECIFIC HIT CREATED SUCCESSFULLY
```

### With Auto-Cancel of Old HITs:

```
0️⃣  Checking for existing pending cashouts...
   Found 2 existing pending cashout(s)
   🚫 Auto-cancelling old cashouts...
   Cancelling: uuid-old-1
      ✅ Old HIT deleted
      ✅ 2000 gems refunded
   Cancelling: uuid-old-2
      ✅ Old HIT expired
      ✅ 2000 gems refunded
   ✅ Old cashouts cleaned up
```

### If Worker ID Is Invalid:

```
🔄 Assigning qualification to worker INVALID123...
❌ FAILED TO ASSIGN QUALIFICATION!
❌ Error: InvalidParameterValueException: Worker ID does not exist
❌ This means the Worker ID is INVALID or doesn't exist in MTurk!
```

---

## What This Fixes

### Before:
1. ❌ User creates cashout → HIT 1 with Qualification A
2. ❌ User creates another cashout → HIT 2 with Qualification B
3. ❌ User clicks HIT 1 link → "You don't meet qualifications" (needs Qualification A, but only has B)
4. ❌ No visibility into what went wrong

### After:
1. ✅ User creates cashout → HIT 1 with Qualification A
2. ✅ User creates another cashout → **Auto-cancels HIT 1**, creates HIT 2 with Qualification B
3. ✅ User only has ONE active HIT at a time
4. ✅ Full debugging output shows exactly what's happening

---

## Testing Instructions

### Test 1: Single Cashout (No Previous HITs)

```bash
# 1. Ensure no pending cashouts
cd backend
python3 cancel_old_hits.py benchay 0

# 2. Restart backend
pkill -f uvicorn
uvicorn main:app --host 0.0.0.0 --port 8000 --reload

# 3. Request cashout from app
# 4. Watch backend logs carefully
# 5. Look for qualification assignment success
# 6. Click HIT link immediately
```

**Expected**: Should work if Worker ID is correct.

### Test 2: Multiple Cashouts (Auto-Cancel)

```bash
# 1. Request first cashout
# 2. Request second cashout immediately
# 3. Check backend logs for auto-cancel message
# 4. Verify gems were refunded for first cashout
# 5. Click HIT link for second cashout
```

**Expected**: First cashout auto-cancelled, second works.

### Test 3: Invalid Worker ID

```bash
# 1. Set Worker ID to something invalid
# 2. Request cashout
# 3. Check backend logs
```

**Expected**: Clear error message about invalid Worker ID, cashout fails immediately.

---

## If Still Getting Qualification Error

### Check These in Backend Logs:

1. **Worker ID Debug Output**:
   ```
   📋 DEBUG: Worker ID: 'A1EWFN76HNDD20' (length: 14)
   ```
   - Is this the correct Worker ID?
   - Does it match your MTurk account?

2. **Qualification Assignment**:
   ```
   ✅ Qualification assigned to worker: A1EWFN76HNDD20
   ```
   - Do you see this line?
   - Or do you see "❌ FAILED TO ASSIGN QUALIFICATION!"?

3. **Verification**:
   ```
   ✅ Verification successful (attempt 1)
   ```
   - Does verification pass?
   - If it fails 3 times, Worker ID is wrong

4. **Final Check**:
   ```
   ✅ Final check passed - Worker still has qualification
   ```
   - This confirms qualification exists right before HIT creation

### If All Checks Pass But Still Error:

**Then the issue is**:
- You're logged into MTurk with a DIFFERENT Worker ID than what's in your profile
- You're clicking an OLD HIT link instead of the new one
- Browser cache is showing old HIT

**Solution**:
1. Verify you're logged into MTurk with Worker ID `A1EWFN76HNDD20`
2. Clear browser cache or use incognito mode
3. Use the EXACT link from the app (don't search MTurk manually)

---

## Files Modified

1. **`backend/per_transaction_hit_service.py`** - Core logic
   - Lines 70-129: Auto-cancel old HITs
   - Lines 150-170: Enhanced qualification assignment with error handling
   - Lines 156: Worker ID cleaning
   - Throughout: Debug logging

2. **`backend/cancel_old_hits.py`** - Utility script
   - Can manually cancel old HITs if needed

3. **`backend/check_recent_cashouts.py`** - Diagnostic script
   - Shows which HITs are active

---

## Summary

✅ **Auto-cancel old HITs** when creating new cashout  
✅ **Strip whitespace** from Worker ID  
✅ **Explicit error handling** for qualification assignment  
✅ **Comprehensive debugging** output  
✅ **Fail fast** if Worker ID is invalid  

**Status**: Ready for testing with backend restart

---

**Next Step**: Restart backend and test cashout. Watch logs carefully for any errors.
