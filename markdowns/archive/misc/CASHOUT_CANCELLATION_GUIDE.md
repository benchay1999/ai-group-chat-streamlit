# Cashout Cancellation & HIT Garbage Collection

## Date: October 31, 2025

## Overview

Implemented robust cashout cancellation and HIT cleanup system with:
- ✅ User-initiated cancellation
- ✅ Gem refund with duplication protection
- ✅ HIT deletion/expiration
- ✅ Garbage collection for abandoned HITs
- ✅ Admin cleanup tools

---

## Features

### 1. User Cancellation

Users can cancel their pending cashout transactions.

**Endpoint**: `POST /api/wallet/cashout-cancel/{transaction_id}`

**What happens**:
1. ✅ Verifies transaction belongs to user
2. ✅ Checks if transaction can be cancelled
3. ✅ Deletes/expires the MTurk HIT
4. ✅ Refunds gems (with duplication protection)
5. ✅ Updates transaction status to CANCELLED

**Which transactions can be cancelled**:
- ✅ PENDING - Just created, no HIT yet
- ✅ HIT_CREATED - HIT created but not started
- ✅ PROCESSING - Worker accepted but not completed
- ❌ COMPLETED - Already finished, cannot cancel
- ❌ CANCELLED - Already cancelled
- ❌ FAILED - Already failed (gems already refunded)

### 2. HIT Cleanup

When cancelling, the system attempts to clean up the MTurk HIT:

**Method 1: Delete HIT** (preferred)
- If HIT has no submissions, it's deleted permanently
- Removes it from MTurk completely

**Method 2: Expire HIT** (fallback)
- If HIT has pending submissions, it's expired instead
- Sets expiration to now (workers can no longer access it)

**If both fail**:
- Transaction is still cancelled
- Gems are still refunded
- HIT may remain visible in MTurk (will be cleaned later by garbage collection)

### 3. Gem Refund Protection

**Critical safeguards** to prevent duplication:

```python
# Database-level locking
.with_for_update()  # Locks the transaction row

# Status-based refund logic
if transaction.status in [PENDING, HIT_CREATED, PROCESSING]:
    # Refund gems (status indicates gems were deducted)
    user.gem_balance += transaction.amount_gems
    user.total_gems_cashed_out -= transaction.amount_gems
else:
    # No refund (status indicates gems already handled)
    pass
```

**Prevents**:
- ❌ Double refunds
- ❌ Race conditions (two cancels at once)
- ❌ Refunding already-failed transactions

### 4. Garbage Collection

Automatically cleans up old, abandoned HITs.

**Endpoint**: `POST /api/admin/garbage-collect-hits?age_hours=48` (Admin only)

**What it does**:
1. Finds transactions that are:
   - Status: PENDING, HIT_CREATED, or PROCESSING
   - Older than X hours (default: 48)
   - Not completed
2. For each:
   - Deletes/expires the HIT
   - Refunds gems to user
   - Marks transaction as CANCELLED

**Use cases**:
- User forgot to cancel
- User abandoned the HIT
- System crashed during cashout
- HIT link expired/broken

---

## API Reference

### User Endpoint: Cancel Cashout

```http
POST /api/wallet/cashout-cancel/{transaction_id}
Authorization: Bearer <token>
```

**Parameters**:
- `transaction_id` (path): UUID of the transaction

**Response (Success)**:
```json
{
  "success": true,
  "message": "Cashout cancelled successfully",
  "hit_deleted": true,
  "refunded": true,
  "gems_returned": 2000,
  "new_balance": 2000,
  "transaction_id": "uuid-123"
}
```

**Response (Error - Cannot Cancel)**:
```json
{
  "detail": "Cannot cancel completed transaction"
}
```

**Response (Error - Not Found)**:
```json
{
  "detail": "Transaction not found or does not belong to you"
}
```

### Admin Endpoint: Garbage Collection

```http
POST /api/admin/garbage-collect-hits?age_hours=48
Authorization: Bearer <admin-token>
```

**Parameters**:
- `age_hours` (query, optional): Hours before considering abandoned (default: 48)

**Response**:
```json
{
  "success": true,
  "transactions_cleaned": 3,
  "hits_deleted": 2,
  "gems_refunded": 6000,
  "errors": 0
}
```

---

## Implementation Details

### File Structure

**New Files**:
- `backend/cashout_cancel_service.py` - Cancellation and GC logic

**Modified Files**:
- `backend/main.py` - Updated cancel endpoint, added GC endpoint

### Database Changes

**No schema changes required!**

Uses existing `CashoutTransaction` fields:
- `status` - Updated to CANCELLED
- `error_message` - Set to cancellation reason
- `completed_at` - Set to cancellation time

### Transaction Status Flow

```
PENDING → HIT_CREATED → PROCESSING → COMPLETED
   ↓           ↓            ↓
CANCELLED   CANCELLED    CANCELLED
   ↓           ↓            ↓
(refund)    (refund)     (refund)

FAILED ← (already refunded, no refund on cancel)
```

---

## Usage Examples

### Example 1: User Cancels Cashout

```javascript
// Frontend code
async function cancelCashout(transactionId) {
  const response = await fetch(`/api/wallet/cashout-cancel/${transactionId}`, {
    method: 'POST',
    headers: {
      'Authorization': `Bearer ${token}`
    }
  });
  
  const result = await response.json();
  console.log(`Refunded ${result.gems_returned} gems`);
  console.log(`New balance: ${result.new_balance} gems`);
}
```

### Example 2: Admin Runs Garbage Collection

```bash
# Manual trigger via curl
curl -X POST "http://localhost:8000/api/admin/garbage-collect-hits?age_hours=24" \
  -H "Authorization: Bearer ADMIN_TOKEN"
```

### Example 3: Automated Cleanup (Cron Job)

```python
# backend/scheduled_cleanup.py
import asyncio
from database import async_session_maker
from cashout_cancel_service import garbage_collect_old_hits

async def run_cleanup():
    async with async_session_maker() as db:
        result = await garbage_collect_old_hits(db=db, age_hours=48)
        print(f"Cleaned {result['transactions_cleaned']} transactions")

if __name__ == "__main__":
    asyncio.run(run_cleanup())
```

Add to crontab:
```bash
# Run cleanup daily at 3 AM
0 3 * * * cd /path/to/backend && python3 scheduled_cleanup.py
```

---

## Testing

### Test 1: Cancel Pending Cashout

```bash
# 1. Request cashout
curl -X POST "/api/wallet/cashout/v2" \
  -H "Authorization: Bearer TOKEN" \
  -d '{"amount_usd": 2.00}'

# Response includes transaction_id

# 2. Cancel it
curl -X POST "/api/wallet/cashout-cancel/TRANSACTION_ID" \
  -H "Authorization: Bearer TOKEN"

# 3. Verify gems refunded
curl -X GET "/api/wallet/balance" \
  -H "Authorization: Bearer TOKEN"
```

### Test 2: Cannot Cancel Completed

```bash
# 1. Request and complete cashout
# 2. Try to cancel
curl -X POST "/api/wallet/cashout-cancel/TRANSACTION_ID" \
  -H "Authorization: Bearer TOKEN"

# Should return error: "Cannot cancel completed transaction"
```

### Test 3: Garbage Collection

```bash
# 1. Create some old test transactions (manually in DB or wait 48 hours)

# 2. Run garbage collection
curl -X POST "/api/admin/garbage-collect-hits?age_hours=1" \
  -H "Authorization: Bearer ADMIN_TOKEN"

# 3. Check result shows transactions cleaned
```

---

## Monitoring

### Backend Logs

**Successful Cancellation**:
```
🚫 CANCELLING CASHOUT TRANSACTION
Transaction ID: uuid-123
User: testuser
Reason: User requested cancellation

📊 Transaction Status: HIT_CREATED
   Amount: $2.00 (2000 gems)
   HIT ID: 3ABC123

1️⃣  Cleaning up MTurk HIT...
   ✅ HIT deleted: 3ABC123

2️⃣  Processing gem refund...
   Current balance: 0 gems
   Gems to refund: 2000 gems
   ✅ Gems refunded: 2000
   New balance: 2000 gems

3️⃣  Updating transaction status...
   ✅ Status updated to: CANCELLED

✅ CASHOUT CANCELLED SUCCESSFULLY
   HIT cleaned up: True
   Gems refunded: 2000
   New balance: 2000 gems
```

**Garbage Collection**:
```
🗑️  GARBAGE COLLECTION: Old HITs
Looking for transactions older than 48 hours...
Found 3 abandoned transactions

Processing transaction uuid-456
   User: user-789
   Amount: $2.00 (2000 gems)
   Created: 2025-10-29 10:00:00
   Age: 2 days, 1:23:45
   ✅ HIT deleted
   ✅ Refunded 2000 gems to user
   ✅ Transaction cancelled

...

✅ GARBAGE COLLECTION COMPLETE
   Transactions cleaned: 3
   HITs deleted/expired: 3
   Gems refunded: 6000
   Errors: 0
```

---

## Security

### Ownership Verification

```python
# Transaction must belong to requesting user
if transaction.user_id != current_user.id:
    raise ValueError("Transaction not found or does not belong to you")
```

### Row Locking

```python
# Prevents race conditions (two cancels at once)
.with_for_update()  # Database-level lock
```

### Admin-Only GC

```python
# Only admins can run garbage collection
admin_user: User = Depends(require_admin)
```

---

## Edge Cases Handled

### 1. Double Cancellation
**Problem**: User clicks cancel twice  
**Solution**: Transaction locked with `with_for_update()`, second call fails

### 2. Cancel After Completion
**Problem**: User tries to cancel completed transaction  
**Solution**: Status check prevents cancellation, returns error

### 3. HIT Can't Be Deleted
**Problem**: HIT has pending submissions  
**Solution**: Expire instead of delete, transaction still cancelled

### 4. User Account Deleted
**Problem**: GC finds transaction but user is gone  
**Solution**: Skips refund, still cancels transaction

### 5. MTurk API Failure
**Problem**: Cannot connect to MTurk  
**Solution**: Still cancels transaction and refunds gems, logs HIT cleanup failure

---

## Best Practices

### For Users:
1. ✅ Cancel unused cashouts promptly
2. ✅ Check balance after cancellation
3. ✅ Don't try to cancel completed transactions

### For Admins:
1. ✅ Run garbage collection weekly (or daily)
2. ✅ Monitor GC logs for patterns
3. ✅ Adjust `age_hours` based on usage patterns

### For Developers:
1. ✅ Always use `with_for_update()` for transaction modifications
2. ✅ Check status before refunding gems
3. ✅ Log all cancellation attempts
4. ✅ Handle MTurk API failures gracefully

---

## Future Enhancements

### Optional:
1. **Automatic expiration** - Auto-cancel after 7 days
2. **Email notifications** - Notify users when GC cancels their transaction
3. **Cancellation limits** - Limit cancellations per day to prevent abuse
4. **Partial refunds** - If worker started HIT, partial refund
5. **Cancel button in UI** - Add "Cancel Cashout" button to transaction history

---

## Summary

✅ **Implemented**: User cancellation with gem refunds  
✅ **Implemented**: HIT cleanup (delete/expire)  
✅ **Implemented**: Duplication protection  
✅ **Implemented**: Admin garbage collection  
✅ **Implemented**: Comprehensive logging  
✅ **Tested**: Syntax validation passed  

**Status**: Ready for backend restart and testing!

---

**Last Updated**: October 31, 2025  
**Status**: ✅ COMPLETE  
**Files**: `cashout_cancel_service.py`, `main.py` (updated)

