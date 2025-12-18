# Outdated Code Removal Summary

## Date: October 31, 2025

This document summarizes the outdated implementations that were removed as part of the gem economy migration.

---

## ✅ Removed from Backend (`backend/main.py`)

### 1. Pydantic Models
- **`UpdatePaymentRequest`** - Used for manual payment status updates
- **`CreateHITRequest`** - Used for dynamic HIT creation

### 2. API Endpoints
- **`PATCH /api/admin/sessions/{session_id}/payment`** - Manual payment status/amount updates
- **`POST /api/admin/mturk/create-hit`** - Dynamic HIT creation
- **`GET /api/admin/mturk/hits`** - List all MTurk HITs
- **`GET /api/admin/mturk/balance`** - Get MTurk account balance

**Reason**: These endpoints were part of the old payment system where admins manually managed payments and dynamically created HITs. With the gem economy, payments are automated through the redemption code system with a single standing HIT.

---

## ✅ Removed from Backend (`backend/mturk_api.py`)

### 1. MTurkClient Methods
- **`create_hit()`** - Create dynamic HITs with custom parameters
- **`list_hits()`** - List all active HITs

### 2. Convenience Functions
- **`create_game_hit()`** - Wrapper for creating game-specific HITs

**Reason**: Dynamic HIT creation is replaced by a single, standing HIT for all cashouts. Workers submit redemption codes to this standing HIT.

---

## ✅ Removed from Frontend (`frontend/src/pages/AdminPage.jsx`)

### 1. Functions
- **`handleUpdatePayment()`** - Called outdated API to update payment status
- **`promptPaymentAmount()`** - Prompted admin to manually enter payment amount
- **`acceptSuggestedAmount()`** - Auto-accepted suggested payment amount

**Reason**: Manual payment management is replaced by automated gem-based cashouts. Admins no longer need to manually set payment amounts or statuses.

---

## ✅ Removed from Frontend (`frontend/src/services/sessionsAPI.js`)

### 1. API Functions
- **`updatePaymentStatus()`** - Called the removed PATCH endpoint

**Reason**: This API endpoint no longer exists in the backend.

---

## ✅ Removed from Frontend (`frontend/src/services/mturkAPI.js`)

### 1. API Functions
- **`createHIT()`** - Called the removed POST endpoint to create HITs
- **`listHITs()`** - Called the removed GET endpoint to list HITs
- **`getBalance()`** - Called the removed GET endpoint to check balance

**Reason**: These API endpoints no longer exist in the backend. Only `approvePayment()` remains for legacy session support.

---

## 🟢 Kept for Legacy Support

These implementations remain to support old sessions created before the gem economy:

### Backend
- **`POST /api/admin/mturk/sessions/{session_id}/approve-payment`** - Approve legacy session payments
- **`process_payment()`** function in `mturk_api.py` - Process legacy payments
- **`PaymentStatus` enum** in `database.py` - Track legacy payment status
- **`payment_status` and `payment_amount` fields** in `Session` model

### Frontend
- **`handleMTurkPayment()`** in `AdminPage.jsx` - Trigger legacy payments
- **`approvePayment()`** in `mturkAPI.js` - Call legacy payment endpoint
- **MTurk Payment display** in `SessionDetailPage.jsx` - Show legacy payment info

---

## 🔵 Active Implementations (Current System)

These are the active implementations for the gem economy:

### Backend
- Gem economy endpoints (`/api/wallet/*`)
- Cashout service with redemption codes
- Standing HIT configuration (`CASHOUT_HIT_ID`)
- Cashout monitor for expired redemptions

### Frontend
- Wallet component and dashboard integration
- Cashout modal with redemption code display
- Profile page for MTurk Worker ID management
- CashoutConfirm page for redemption submission

---

## 📊 Impact Summary

| Category | Removed | Kept (Legacy) | Active (Current) |
|----------|---------|---------------|------------------|
| Backend Endpoints | 4 | 1 | 5 |
| Backend Functions | 3 | 1 | 10+ |
| Frontend Functions | 6 | 2 | 15+ |
| Database Models | 0 | 2 fields | 3 fields + 1 table |

---

## ✨ Benefits of Removal

1. **Code Clarity**: Removed ~500 lines of obsolete code
2. **Reduced Confusion**: No mixing of old and new payment systems
3. **Easier Maintenance**: Single payment flow to maintain
4. **Better UX**: Users interact with a consistent gem-based system
5. **Lower Costs**: One standing HIT instead of dynamic HITs per user

---

## 🔍 Testing Checklist

- [x] Backend linting passes (no errors)
- [x] Frontend linting passes (no errors)
- [x] Legacy payment endpoint still exists
- [x] Wallet endpoints still exist
- [x] MTurk Worker ID management still works
- [x] AdminPage legacy button still present

---

## Notes

- All removals were non-breaking for existing functionality
- Legacy support ensures old sessions can still be paid
- The gem economy is now the primary payment system
- MTurk is used solely as a payment processor via the standing HIT

