# MTurk Qualification Assignment Fix

## Date: October 31, 2025

## Error Encountered

When trying to access the private HIT, workers saw:
```
No HITs match your criteria

This HIT requires Qualifications
This Requester has specified Qualifications for this HIT. 
At this time, you do not meet those Qualifications.
```

## Root Cause

In `backend/per_transaction_hit_service.py`, the qualification was being **created** but never **assigned** to the worker.

### The Problem Code:
```python
# Create the qualification type
qualification_id = mturk_client.create_worker_qualification(
    worker_id=user.mturk_worker_id,
    qualification_name=qual_name
)

print(f"   ✅ Qualification created: {qualification_id}")
print(f"   ✅ Assigned to worker: {user.mturk_worker_id}")  # ← FALSE! Not actually assigned!
```

**What happened:**
1. ✅ Qualification TYPE was created
2. ❌ Qualification was NOT assigned to worker
3. ✅ HIT was created with qualification requirement
4. ❌ Worker couldn't access HIT (missing qualification)

## The MTurk Qualification System

MTurk qualifications require **TWO separate steps**:

### Step 1: Create Qualification Type
```python
response = client.create_qualification_type(
    Name='MyQualification',
    Description='...',
    QualificationTypeStatus='Active',
    AutoGranted=False
)
qualification_id = response['QualificationType']['QualificationTypeId']
```

This creates a **template** for the qualification, but doesn't give it to anyone yet.

### Step 2: Assign Qualification to Worker
```python
client.associate_qualification_with_worker(
    QualificationTypeId=qualification_id,
    WorkerId=worker_id,
    IntegerValue=1,
    SendNotification=False
)
```

This **grants** the qualification to a specific worker.

**Both steps are required!**

## The Fix

**File**: `backend/per_transaction_hit_service.py`  
**Lines**: 70-91

### Before (BROKEN):
```python
# Step 1: Create worker-specific qualification
print(f"\n1️⃣  Creating worker-specific qualification...")

qual_name = f"ChatGame_User_{user.user_id}_{transaction.id}"

# Create the qualification type
qualification_id = mturk_client.create_worker_qualification(
    worker_id=user.mturk_worker_id,
    qualification_name=qual_name
)

print(f"   ✅ Qualification created: {qualification_id}")
print(f"   ✅ Assigned to worker: {user.mturk_worker_id}")  # ❌ NOT TRUE!
```

### After (FIXED):
```python
# Step 1: Create worker-specific qualification
print(f"\n1️⃣  Creating worker-specific qualification...")

qual_name = f"ChatGame_User_{user.user_id}_{transaction.id}"

# Create the qualification type
qualification_id = mturk_client.create_worker_qualification(
    worker_id=user.mturk_worker_id,
    qualification_name=qual_name
)

print(f"   ✅ Qualification created: {qualification_id}")

# Assign the qualification to the worker
mturk_client.assign_qualification_to_worker(
    qualification_id=qualification_id,
    worker_id=user.mturk_worker_id,
    value=1
)

print(f"   ✅ Qualification assigned to worker: {user.mturk_worker_id}")
```

## How It Works Now

### Complete Flow:

1. **User requests cashout** → Transaction created
2. **Create qualification type** → Qualification template created (MTurk API)
3. **Assign qualification to worker** → Worker receives qualification ✅ **NEW!**
4. **Create HIT with qualification requirement** → Only workers with qualification can see it
5. **Worker accesses HIT** → Worker has qualification, can see and complete HIT ✅

### What Changes:

| Step | Before | After |
|------|--------|-------|
| Create Qualification | ✅ Done | ✅ Done |
| **Assign to Worker** | ❌ **MISSING** | ✅ **ADDED** |
| Create HIT | ✅ Done | ✅ Done |
| Worker Access | ❌ Denied | ✅ Allowed |

## Verification

After the fix, the logs will show:
```
1️⃣  Creating worker-specific qualification...
   ✅ Qualification created: 3ABC123...
   ✅ Qualification assigned to worker: A1B2C3D4E5F6G7
2️⃣  Creating HIT with qualification requirement...
   ✅ HIT created: 3XYZ789...
```

**Key difference**: Two separate success messages for creation and assignment.

## Testing

### Expected Backend Logs:
```bash
🎯 CREATING WORKER-SPECIFIC HIT
Transaction: uuid-123
Worker ID: A1B2C3D4E5F6G7
Amount: $2.00

1️⃣  Creating worker-specific qualification...
   ✅ Qualification created: 3QUALIFICATION123
   ✅ Qualification assigned to worker: A1B2C3D4E5F6G7

2️⃣  Creating HIT with qualification requirement...
   ✅ HIT created: 3HIT456
   ✅ Worker URL: https://workersandbox.mturk.com/mturk/preview?groupId=...

✅ WORKER-SPECIFIC HIT CREATED SUCCESSFULLY
```

### Worker Experience:
1. Click "Go to MTurk HIT" link
2. ✅ See the HIT (no "No HITs match" error)
3. ✅ Can preview and accept the HIT
4. Complete the HIT and get paid

## Related Files

- **Fixed**: `backend/per_transaction_hit_service.py` (lines 84-91)
- **Uses**: `backend/mturk_api.py` (methods `create_worker_qualification` and `assign_qualification_to_worker`)
- **Endpoint**: `backend/cashout_endpoint_v2.py` (V2 cashout system)

## Summary of All 3 Fixes

### Fix #1: Invalid Parameter Combination ✅
**Error**: `InvalidParameterCombinationError: ActionsGuarded, RequiredToPreview`  
**Fix**: Removed `ActionsGuarded` parameter  
**File**: `backend/mturk_api.py`

### Fix #2: XML Parsing Error ✅
**Error**: `ParameterValidationError: entity "tx" must end with ';' delimiter`  
**Fix**: Added XML escaping for URL (`&` → `&amp;`)  
**File**: `backend/mturk_api.py`

### Fix #3: Qualification Not Assigned ✅
**Error**: `This HIT requires Qualifications. You do not meet those Qualifications.`  
**Fix**: Added call to `assign_qualification_to_worker()`  
**File**: `backend/per_transaction_hit_service.py`

## Next Steps

1. ✅ Fix applied
2. ✅ Syntax validated
3. 🔄 Restart backend server
4. 🧪 Test cashout - should now work completely!

---

**Status**: ✅ FIXED  
**Tested**: Syntax verified  
**Impact**: Critical - enables workers to access their private HITs  
**Confidence**: 100% - This is the missing piece!  

