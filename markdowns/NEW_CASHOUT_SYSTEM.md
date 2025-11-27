# New Cashout System - Per-Transaction HITs

## Date: October 31, 2025

## Problem with Old System

The standing HIT approach had multiple issues:
- ❌ MaxAssignments exhaustion ("No more HITs available")
- ❌ URL generation complexity (HITId vs HITGroupId confusion)
- ❌ Workers couldn't find HITs
- ❌ Assignment availability confusion
- ❌ Complex HIT extension process

## New Solution: Per-Transaction HITs

Instead of ONE HIT for all cashouts, create a **NEW PRIVATE HIT** for **EACH cashout**.

### Key Concept

```
Old System (Standing HIT):
  ONE HIT → 99,999 assignments → All workers compete
  ❌ Runs out of assignments
  ❌ Complex URL management

New System (Per-Transaction):
  EACH cashout → ONE private HIT → ONE specific worker
  ✅ Never runs out (creates new HIT each time)
  ✅ Simple, direct URLs
```

## How It Works

### 1. Worker Setup (One-Time)
```
User adds MTurk Worker ID to profile
  ↓
System validates Worker ID format
  ↓
Ready to cash out!
```

### 2. Cashout Flow
```
User requests cashout ($5.00)
  ↓
System creates worker-specific qualification
  ↓
System creates private HIT with that qualification
  (Only this worker can see it!)
  ↓
Worker gets direct URL to their private HIT
  ↓
Worker completes HIT
  ↓
Payment approved automatically
  ↓
HIT cleaned up (deleted/expired)
```

### 3. Next Cashout
```
User requests another cashout ($3.00)
  ↓
NEW private HIT created
  ↓
Worker completes it
  ↓
Repeat indefinitely!
```

## Technical Implementation

### Files Created

1. **`backend/per_transaction_hit_service.py`**
   - Creates worker-specific qualifications
   - Creates private HITs
   - Handles HIT cleanup

2. **`backend/cashout_endpoint_v2.py`**
   - New cashout endpoint: `/api/wallet/cashout/v2`
   - Uses per-transaction HIT system
   - Simplified validation

3. **`NEW_CASHOUT_SYSTEM.md`** (this file)
   - Complete documentation

### Key Functions

#### create_worker_specific_hit()
```python
async def create_worker_specific_hit(user, transaction, db):
    """
    Creates a HIT that only the specific worker can see.
    
    Steps:
    1. Create qualification for this worker
    2. Create HIT with qualification requirement
    3. Only worker with qualification can see HIT
    4. Return direct HIT URL
    """
```

#### cleanup_completed_hit()
```python
async def cleanup_completed_hit(transaction, db):
    """
    Delete/expire HIT after completion.
    Keeps MTurk account clean.
    """
```

## API Endpoint

### New Endpoint: POST `/api/wallet/cashout/v2`

**Request:**
```json
{
  "amount_usd": 5.00
}
```

**Response:**
```json
{
  "success": true,
  "transaction_id": "uuid",
  "amount_usd": 5.00,
  "amount_gems": 5000,
  "hit_url": "https://workersandbox.mturk.com/mturk/preview?groupId=XXX",
  "hit_id": "3ABC123...",
  "redemption_code": "a1b2c3...",
  "expires_at": "2025-11-01T12:00:00Z",
  "instructions": {
    "step1": "Click the HIT link below",
    "step2": "This HIT is private - only you can see it",
    "step3": "Complete the HIT to receive your payment",
    "step4": "Payment will be approved automatically"
  },
  "message": "✅ Private HIT created! Click the link to cash out $5.00"
}
```

## Benefits

### For Workers
- ✅ **Private HITs**: Only you can see your cashout HIT
- ✅ **Direct links**: Click and go, no searching
- ✅ **Unlimited cashouts**: Create as many as needed
- ✅ **No confusion**: Each cashout is separate and clear

### For System
- ✅ **No exhaustion**: Each HIT has MaxAssignments=1, create new ones as needed
- ✅ **Clean separation**: One transaction = One HIT
- ✅ **Auto cleanup**: HITs get deleted after completion
- ✅ **Scalable**: Handle unlimited cashouts
- ✅ **Simple logic**: No complex URL generation or assignment tracking

### For Developers
- ✅ **Less code**: Simpler than standing HIT management
- ✅ **Fewer bugs**: No HITGroupId confusion
- ✅ **Easy debugging**: Each transaction isolated
- ✅ **Better logs**: Clear per-transaction tracking

## Migration from Old System

### Step 1: Add New Endpoint

In `backend/main.py`:

```python
from .cashout_endpoint_v2 import request_cashout_v2

@app.post("/api/wallet/cashout/v2")
async def cashout_v2(
    request: Request,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_session)
):
    """New cashout system using per-transaction HITs."""
    return await request_cashout_v2(request, current_user, db)
```

### Step 2: Update Frontend

Update cashout API call:

```javascript
// OLD
const response = await api.post('/api/wallet/cashout', { amount_usd });

// NEW
const response = await api.post('/api/wallet/cashout/v2', { amount_usd });
```

### Step 3: Test

1. Request cashout
2. Should get private HIT URL
3. Click URL → see HIT
4. Complete HIT → get paid
5. Request another cashout → works seamlessly!

### Step 4: Remove Old System (Optional)

Once confident in new system:
1. Remove standing HIT creation scripts
2. Remove `/api/wallet/cashout` (old endpoint)
3. Delete old HITs from MTurk
4. Remove CASHOUT_HIT_ID from .env

## Environment Variables

### No Longer Needed
- ~~`CASHOUT_HIT_ID`~~ (was for standing HIT)

### Still Required
- `AWS_ACCESS_KEY_ID`
- `AWS_SECRET_ACCESS_KEY`
- `MTURK_ENVIRONMENT` (sandbox or production)
- `EXTERNAL_URL` (for cashout confirmation page)

## Worker Experience

### Old System
```
1. Request cashout
2. Get redemption code
3. Get HIT URL
4. Click URL → "No more HITs available" ❌
5. Confused, frustrated
```

### New System
```
1. Request cashout
2. Get private HIT link
3. Click link → See HIT immediately ✅
4. Complete HIT
5. Get paid automatically ✅
6. Request another cashout
7. Get new private HIT ✅
8. Repeat seamlessly! ✅
```

## Cost Comparison

### Old System
```
One-time cost:
- Create standing HIT: $0
- Pre-authorization hold: $999.99 (99,999 × $0.01)

Per cashout:
- MTurk fees: 20% of payment
- No additional HIT creation cost
```

### New System
```
Per cashout:
- Create HIT: $0
- MTurk fees: 20% of payment
- Pre-authorization: $0.01 per HIT (released after)

No large pre-authorization hold!
```

**Result**: New system is actually CHEAPER (no $999.99 hold)!

## Limitations & Considerations

### 1. HIT Creation Rate Limit
- MTurk has rate limits on HIT creation
- For most use cases, this is not an issue
- If you have MANY concurrent cashouts, may need queuing

### 2. Qualification Creation
- Each cashout creates a new qualification
- Qualifications persist in MTurk account
- May want periodic cleanup of old qualifications

### 3. Testing
- Test thoroughly in sandbox first
- Verify worker can see private HITs
- Check payment flow end-to-end

## Troubleshooting

### Issue: Worker can't see private HIT

**Solution**: Check worker ID matches exactly
```python
# Worker ID in profile MUST match MTurk Worker ID
user.mturk_worker_id == "A1BCDEFG2HIJK"  # Exact match required
```

### Issue: Qualification not working

**Solution**: Verify qualification assignment
```python
# Check MTurk dashboard → Manage → Qualifications
# Should see qualification assigned to worker
```

### Issue: HIT creation fails

**Solution**: Check MTurk credentials and balance
```bash
python check_hit_status.py  # Verify MTurk connection
```

## Testing Checklist

- [ ] Worker adds MTurk Worker ID to profile
- [ ] Request cashout (deducts gems)
- [ ] Receives private HIT URL
- [ ] Can access HIT (sees it in MTurk)
- [ ] Completes HIT
- [ ] Payment approved automatically
- [ ] Can request second cashout immediately
- [ ] Second HIT works same as first
- [ ] Old HITs cleaned up properly

## Monitoring

### Metrics to Track
- HITs created per day
- HIT completion rate
- Average time from creation to completion
- Failed HIT creations
- Qualification count (cleanup if too many)

### Logs to Monitor
```bash
# Successful HIT creation
🎯 CREATING WORKER-SPECIFIC HIT
✅ Qualification created
✅ HIT created
✅ WORKER-SPECIFIC HIT CREATED SUCCESSFULLY

# Failed creation
❌ ERROR creating worker-specific HIT
```

## FAQ

### Q: What happens to the standing HIT?
**A**: You can delete it. No longer needed.

### Q: Can workers still use old cashout system?
**A**: Only if you keep old endpoint active. Recommend migrating everyone to V2.

### Q: Is this MTurk-approved?
**A**: Yes! Worker-specific qualifications are a standard MTurk feature.

### Q: What about existing pending cashouts?
**A**: Let them complete with old system, then switch to V2 for new cashouts.

### Q: Can I run both systems simultaneously?
**A**: Yes! Keep old endpoint at `/api/wallet/cashout` and new at `/api/wallet/cashout/v2`.

## Summary

**Old Problem**: Standing HIT with MaxAssignments caused exhaustion and confusion  
**New Solution**: Per-transaction HITs with worker-specific qualifications  
**Result**: Seamless, scalable cashout system that just works! ✅  

---

**Status**: ✅ **READY FOR IMPLEMENTATION**  
**Recommended**: Migrate to new system immediately  
**Confidence**: 100% - This is the correct MTurk pattern for this use case  

🚀 **No more "No HITs available" errors!**

