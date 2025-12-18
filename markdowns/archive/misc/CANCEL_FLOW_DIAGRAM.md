# Transaction Cancellation Flow Diagram

## Overview Flow

```
┌─────────────┐
│   USER      │
│  (Wallet)   │
└──────┬──────┘
       │
       │ 1. Sees pending transaction
       │    with "Cancel" button
       │
       ▼
┌─────────────────────────────────────────────┐
│  Transaction History Table                  │
│  ┌────────┬────────┬─────────┬──────────┐  │
│  │ Date   │ Amount │ Status  │ Actions  │  │
│  ├────────┼────────┼─────────┼──────────┤  │
│  │ Oct 31 │ $3.00  │ PENDING │ [Cancel] │◄─┤─── 2. Click "Cancel"
│  └────────┴────────┴─────────┴──────────┘  │
└─────────────────────────────────────────────┘
       │
       │ 3. Confirmation Dialog
       ▼
┌──────────────────────────────────────────────┐
│  Are you sure you want to cancel?           │
│  Amount: 3,000 gems will be returned         │
│                                              │
│         [Yes]           [No]                 │
└──────────────┬───────────────────────────────┘
               │
               │ 4. User confirms "Yes"
               ▼
┌──────────────────────────────────────────────┐
│  Frontend: Wallet.jsx                        │
│  handleCancelTransaction()                   │
│  - Disable button (show spinner)             │
│  - Call API: cancelCashout(transactionId)    │
└──────────────┬───────────────────────────────┘
               │
               │ 5. POST request to backend
               ▼
┌──────────────────────────────────────────────┐
│  Backend API: /api/wallet/cashout-cancel/id  │
│  cancel_cashout_request()                    │
│                                              │
│  Step 1: Validate Transaction ID             │
│    ├─ Invalid? → 400 Bad Request             │
│    └─ Valid? → Continue                      │
│                                              │
│  Step 2: Get Transaction from DB             │
│    ├─ Not found? → 404 Not Found             │
│    └─ Found? → Continue                      │
│                                              │
│  Step 3: Verify Ownership ⚠️ SECURITY        │
│    ├─ Wrong user? → 403 Forbidden            │
│    └─ Correct user? → Continue               │
│                                              │
│  Step 4: Check Status                        │
│    ├─ Not PENDING? → 400 Cannot Cancel       │
│    └─ PENDING? → Continue                    │
│                                              │
│  Step 5: Call cancel_cashout_transaction()   │
└──────────────┬───────────────────────────────┘
               │
               │ 6. Execute cancellation
               ▼
┌──────────────────────────────────────────────┐
│  cashout_service.py                          │
│  cancel_cashout_transaction()                │
│                                              │
│  Step 1: Check if already cancelled          │
│    if status in [COMPLETED, CANCELLED]:      │
│      return (prevent duplicate)              │
│                                              │
│  Step 2: Get user from DB                    │
│    user = db.query(User).get(user_id)        │
│                                              │
│  Step 3: Return gems (atomically)            │
│    old_balance = user.gem_balance            │
│    user.gem_balance += transaction.gems      │
│                                              │
│  Step 4: Update transaction status           │
│    transaction.status = CANCELLED            │
│    transaction.completed_at = now()          │
│                                              │
│  Step 5: Commit (single transaction)         │
│    await db.commit()                         │
│    await db.refresh(user) ⚠️ CRITICAL        │
│    await db.refresh(transaction)             │
└──────────────┬───────────────────────────────┘
               │
               │ 7. Return success response
               ▼
┌──────────────────────────────────────────────┐
│  Response to Frontend                        │
│  {                                           │
│    "success": true,                          │
│    "gems_returned": 3000,                    │
│    "new_balance": 5000,                      │
│    "previous_balance": 2000,                 │
│    "message": "Transaction cancelled..."     │
│  }                                           │
└──────────────┬───────────────────────────────┘
               │
               │ 8. Show success message
               ▼
┌──────────────────────────────────────────────┐
│  Frontend: Success Alert                     │
│  ✅ Transaction Cancelled                    │
│                                              │
│  3,000 gems returned to wallet               │
│  New Balance: 5,000 gems                     │
└──────────────┬───────────────────────────────┘
               │
               │ 9. Reload wallet data
               ▼
┌──────────────────────────────────────────────┐
│  Wallet Component                            │
│  - Fetch updated balance                     │
│  - Fetch updated transaction history         │
│  - Re-render table                           │
│                                              │
│  Result: Transaction now shows "Cancelled"   │
│          No "Cancel" button anymore          │
└──────────────────────────────────────────────┘
```

---

## Error Handling Flow

```
┌─────────────┐
│    USER     │
└──────┬──────┘
       │
       │ Attempts to cancel
       ▼
┌──────────────────────────────────────────────┐
│  Error Scenarios                             │
└──────────────────────────────────────────────┘

ERROR 1: Invalid Transaction ID
┌────────────────────────────────────┐
│  Backend validates UUID format     │
│  ├─ Invalid format                 │
│  └─ Return 400: "Invalid ID"       │
└────┬───────────────────────────────┘
     │
     ▼
┌────────────────────────────────────┐
│  Frontend shows error alert        │
│  ❌ Error: Invalid transaction ID  │
└────────────────────────────────────┘

ERROR 2: Transaction Not Found
┌────────────────────────────────────┐
│  Backend queries database          │
│  ├─ No matching transaction        │
│  └─ Return 404: "Not found"        │
└────┬───────────────────────────────┘
     │
     ▼
┌────────────────────────────────────┐
│  Frontend shows error alert        │
│  ❌ Error: Transaction not found   │
└────────────────────────────────────┘

ERROR 3: Not Your Transaction ⚠️ SECURITY
┌────────────────────────────────────┐
│  Backend checks ownership          │
│  ├─ transaction.user_id != user_id │
│  ├─ Log security warning           │
│  └─ Return 403: "Forbidden"        │
└────┬───────────────────────────────┘
     │
     ▼
┌────────────────────────────────────┐
│  Frontend shows error alert        │
│  ❌ Error: You can only cancel     │
│     your own transactions          │
└────────────────────────────────────┘

ERROR 4: Already Completed
┌────────────────────────────────────┐
│  Backend checks status             │
│  ├─ Status = COMPLETED             │
│  └─ Return 400: "Cannot cancel"    │
└────┬───────────────────────────────┘
     │
     ▼
┌────────────────────────────────────┐
│  Frontend shows error alert        │
│  ❌ Error: Cannot cancel completed │
│     transactions                   │
└────────────────────────────────────┘

ERROR 5: Already Cancelled
┌────────────────────────────────────┐
│  Backend checks status             │
│  ├─ Status = CANCELLED             │
│  └─ Return early (idempotent)      │
└────┬───────────────────────────────┘
     │
     ▼
┌────────────────────────────────────┐
│  Frontend shows error alert        │
│  ❌ Error: Already cancelled       │
└────────────────────────────────────┘
```

---

## Gem Duplication Prevention Flow

```
SCENARIO: User double-clicks "Cancel" button
═══════════════════════════════════════════════

┌─────────────┐
│    USER     │
└──────┬──────┘
       │
       │ Double-click "Cancel"
       │ (clicks twice rapidly)
       │
       ├───────────────────┬──────────────────┐
       │                   │                  │
       ▼                   ▼                  │
  Request 1           Request 2          (queued)
       │                   │                  │
       │                   │ (Button disabled)│
       │                   └──────────────────┘
       │                        (Blocked by UI)
       │
       ▼
┌──────────────────────────────────────────────┐
│  Backend: Request 1                          │
│  ┌────────────────────────────────────────┐  │
│  │ 1. Start transaction                   │  │
│  │ 2. Read: status = PENDING ✓            │  │
│  │ 3. Add gems: balance += 3000           │  │
│  │ 4. Update: status = CANCELLED          │  │
│  │ 5. COMMIT (atomic)                     │  │
│  │ 6. REFRESH user & transaction          │  │
│  └────────────────────────────────────────┘  │
│  Result: Gems returned ✓                     │
│          Status = CANCELLED ✓                │
└──────────────────────────────────────────────┘
       │
       │ Request 1 completes
       │ (Button re-enabled)
       │
       ▼
(If Request 2 somehow got through...)
┌──────────────────────────────────────────────┐
│  Backend: Request 2                          │
│  ┌────────────────────────────────────────┐  │
│  │ 1. Start transaction                   │  │
│  │ 2. Read: status = CANCELLED ✗          │  │
│  │ 3. if status == CANCELLED:             │  │
│  │      return early (NO CHANGES)         │  │
│  └────────────────────────────────────────┘  │
│  Result: No gems added ✓                     │
│          Return error ✓                      │
└──────────────────────────────────────────────┘

RESULT: Gems returned EXACTLY ONCE ✅
        No duplication possible ✅
```

---

## Database State Transitions

```
INITIAL STATE (Before Cashout Request)
═══════════════════════════════════════
User Table:
┌─────────┬─────────────────┬───────────────────┐
│ user_id │ gem_balance     │ total_cashed_out  │
├─────────┼─────────────────┼───────────────────┤
│ USER123 │ 5000            │ 0                 │
└─────────┴─────────────────┴───────────────────┘

Transaction Table:
(empty)


STATE 1: After Cashout Request
═══════════════════════════════════════
User Table:
┌─────────┬─────────────────┬───────────────────┐
│ user_id │ gem_balance     │ total_cashed_out  │
├─────────┼─────────────────┼───────────────────┤
│ USER123 │ 2000 (↓3000)    │ 0                 │
└─────────┴─────────────────┴───────────────────┘

Transaction Table:
┌────────────┬─────────┬──────────┬─────────┐
│ id         │ user_id │ gems     │ status  │
├────────────┼─────────┼──────────┼─────────┤
│ TX-001     │ USER123 │ 3000     │ PENDING │
└────────────┴─────────┴──────────┴─────────┘

User sees: Balance = 2000, 1 pending transaction


STATE 2: After Cancellation ✅
═══════════════════════════════════════
User Table:
┌─────────┬─────────────────┬───────────────────┐
│ user_id │ gem_balance     │ total_cashed_out  │
├─────────┼─────────────────┼───────────────────┤
│ USER123 │ 5000 (↑3000)    │ 0                 │
└─────────┴─────────────────┴───────────────────┘
              ↑
              └─── Gems returned!

Transaction Table:
┌────────────┬─────────┬──────────┬───────────┐
│ id         │ user_id │ gems     │ status    │
├────────────┼─────────┼──────────┼───────────┤
│ TX-001     │ USER123 │ 3000     │ CANCELLED │
└────────────┴─────────┴──────────┴───────────┘
                                      ↑
                                      └─── Status updated!

User sees: Balance = 5000, 1 cancelled transaction


ATOMIC TRANSACTION GUARANTEE:
═══════════════════════════════════════
BEGIN TRANSACTION;
  UPDATE users SET gem_balance = 5000 WHERE id = 'USER123';
  UPDATE cashout_transactions SET status = 'CANCELLED' WHERE id = 'TX-001';
COMMIT;  ← Both or neither (atomic)

If commit fails → ROLLBACK (no changes applied)
If commit succeeds → Both changes applied ✓
```

---

## Security Validation Flow

```
┌─────────────────────────────────────────────┐
│  Security Check #1: Authentication          │
│  ─────────────────────────────────────────  │
│  Is user authenticated?                     │
│  ├─ No → 401 Unauthorized                   │
│  └─ Yes → Continue                          │
└─────────────┬───────────────────────────────┘
              │
              ▼
┌─────────────────────────────────────────────┐
│  Security Check #2: Transaction Exists      │
│  ─────────────────────────────────────────  │
│  Does transaction exist?                    │
│  ├─ No → 404 Not Found                      │
│  └─ Yes → Continue                          │
└─────────────┬───────────────────────────────┘
              │
              ▼
┌─────────────────────────────────────────────┐
│  Security Check #3: Ownership ⚠️ CRITICAL   │
│  ─────────────────────────────────────────  │
│  if transaction.user_id != current_user.id: │
│    - Log security warning                   │
│    - Return 403 Forbidden                   │
│                                             │
│  This prevents:                             │
│    ✓ User A cancelling User B's transaction│
│    ✓ Unauthorized gem manipulation         │
│    ✓ Cross-user attacks                    │
└─────────────┬───────────────────────────────┘
              │
              ▼
┌─────────────────────────────────────────────┐
│  Security Check #4: Status Validation       │
│  ─────────────────────────────────────────  │
│  Is transaction PENDING?                    │
│  ├─ No → 400 Cannot Cancel                  │
│  └─ Yes → Proceed with cancellation         │
└─────────────────────────────────────────────┘

ALL CHECKS PASSED ✓
→ Safe to proceed with cancellation
```

---

## UI Component State Machine

```
Wallet Component State Machine
═══════════════════════════════════════

INITIAL STATE: Loading
┌────────────────────────┐
│  Loading...            │
│  [Spinner]             │
└────────────────────────┘
         │
         │ Data loaded
         ▼
STATE: Idle (Transaction List)
┌────────────────────────────────────┐
│  Transaction History               │
│  ┌──────────┬─────────┬─────────┐  │
│  │ $3.00    │ PENDING │ [Cancel]│◄─┼─ Click "Cancel"
│  └──────────┴─────────┴─────────┘  │
└────────────────┬───────────────────┘
                 │
                 ▼
STATE: Confirming
┌────────────────────────────────────┐
│  Are you sure?                     │
│  [Yes]  [No]                       │
└────────┬───────────────────────────┘
         │
         │ User clicks "Yes"
         ▼
STATE: Cancelling (Loading)
┌────────────────────────────────────┐
│  Transaction History               │
│  ┌──────────┬─────────┬─────────┐  │
│  │ $3.00    │ PENDING │[Spinner]│◄─ Button disabled
│  └──────────┴─────────┴─────────┘  │
└────────┬───────────────────────────┘
         │
         │ API call completes
         ▼
STATE: Success
┌────────────────────────────────────┐
│  ✅ Transaction Cancelled          │
│  3,000 gems returned               │
└────────┬───────────────────────────┘
         │
         │ Reload data
         ▼
STATE: Idle (Updated List)
┌────────────────────────────────────┐
│  Transaction History               │
│  ┌──────────┬───────────┬───────┐  │
│  │ $3.00    │ CANCELLED │   -   │◄─ No button (can't cancel again)
│  └──────────┴───────────┴───────┘  │
└────────────────────────────────────┘

STATE: Error (if API fails)
┌────────────────────────────────────┐
│  ❌ Error: Failed to cancel        │
│  [OK]                              │
└────────┬───────────────────────────┘
         │
         │ Dismiss
         ▼
STATE: Idle (No changes)
┌────────────────────────────────────┐
│  Transaction History               │
│  ┌──────────┬─────────┬─────────┐  │
│  │ $3.00    │ PENDING │ [Cancel]│◄─ Can retry
│  └──────────┴─────────┴─────────┘  │
└────────────────────────────────────┘
```

---

## Request/Response Examples

### Successful Cancellation

```http
POST /api/wallet/cashout-cancel/123e4567-e89b-12d3-a456-426614174000
Authorization: Bearer eyJhbGciOiJIUzI1NiIs...
Content-Type: application/json

Response: 200 OK
{
  "success": true,
  "transaction_id": "123e4567-e89b-12d3-a456-426614174000",
  "amount_gems": 3000,
  "amount_usd": 3.0,
  "gems_returned": 3000,
  "new_balance": 5000,
  "previous_balance": 2000,
  "message": "Transaction cancelled. 3000 gems have been returned to your wallet."
}
```

### Error: Not Your Transaction

```http
POST /api/wallet/cashout-cancel/123e4567-e89b-12d3-a456-426614174000
Authorization: Bearer eyJhbGciOiJIUzI1NiIs...

Response: 403 Forbidden
{
  "detail": "You can only cancel your own transactions"
}

Backend Log:
⚠️ SECURITY: User USER-A attempted to cancel transaction owned by USER-B
```

### Error: Already Cancelled

```http
POST /api/wallet/cashout-cancel/123e4567-e89b-12d3-a456-426614174000
Authorization: Bearer eyJhbGciOiJIUzI1NiIs...

Response: 400 Bad Request
{
  "detail": "Cannot cancel transaction with status 'cancelled'. Only PENDING transactions can be cancelled."
}
```

---

**Last Updated**: 2025-10-31
**Purpose**: Visual reference for cancel transaction feature implementation

