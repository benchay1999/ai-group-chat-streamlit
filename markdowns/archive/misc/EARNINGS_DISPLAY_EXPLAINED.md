# Earnings Display - What Shows Where

## Summary

**YES**, the emphasized earnings panel syncs with admin-set paid amounts. Here's exactly what shows where:

## Giant Earnings Display (Main Hero)

**Field:** `earnings.total_lifetime_earnings`  
**Source:** Sum of all `payment_amount` where `payment_status = 'PAID'`  
**Set by:** Admin only  
**Shows:** ACTUAL money marked as paid by admins

```javascript
<EarningsCounter target={earnings.total_lifetime_earnings} />
// This shows: $XX.XX (only admin-set payments that are marked PAID)
```

## Secondary Stats Cards

### 1. Pending Earnings (Yellow Glow)
**Field:** `earnings.pending_earnings`  
**Source:** Sum of all `payment_amount` where `payment_status = 'PENDING'`  
**Set by:** Admin only  
**Shows:** Money admin has set but not yet marked as paid

### 2. Last Game Earned (Blue)
**Field:** `earnings.recent_sessions[0].amount`  
**Source:** `payment_amount` from most recent session  
**Set by:** Admin only  
**Shows:** What admin set for the last game (0 if not set yet)

### 3. Average Per Game (Purple)
**Field:** `earnings.average_per_game`  
**Source:** `total_paid / total_games`  
**Set by:** Calculated from admin-set paid amounts  
**Shows:** Average of all PAID amounts divided by total games

### 4. This Week (Green Glow)
**Field:** `earnings.earnings_this_week`  
**Source:** Sum of `payment_amount` where `payment_status = 'PAID'` AND `completed_at >= 7 days ago`  
**Set by:** Admin only (filtered by date)  
**Shows:** Money marked as PAID in the last 7 days

## Earnings Trend Chart

**Data:** Last 10 sessions  
**Y-axis:** `session.amount` (admin-set `payment_amount`)  
**Shows:** ONLY actual admin-set payments, not calculated suggestions  
**Note:** Will show $0.00 for games where admin hasn't set payment yet

## Earnings Tier Badge

**Field:** `earnings.tier`  
**Based on:** `total_paid` (total lifetime earnings marked as PAID)  
**Thresholds:**
- Newcomer: $0+
- Apprentice: $5+
- Journeyman: $25+
- Expert: $100+
- Master: $500+

## Session Table (Earnings Column)

**Shows:** Individual `payment_amount` for each session  
**Set by:** Admin only  
**Note:** May show `calculated_earnings` as a suggestion (in admin view only)

---

## Behind the Scenes: System Suggestions

The system calculates a **suggested** earning (`calculated_earnings`) based on performance:
- Game completion
- Win/loss
- Message participation
- Voting participation
- Discussion duration

**WHERE IT'S SHOWN:**
- ❌ NOT in the giant earnings display
- ❌ NOT in any stats cards
- ❌ NOT in the chart
- ✅ ONLY visible to admins as a suggestion when setting payment amounts

**Admin workflow:**
1. Game completes
2. System calculates suggested earning (e.g., $0.35)
3. Admin reviews chat quality and performance
4. Admin can:
   - Accept suggestion ($0.35)
   - Increase for great quality ($0.50)
   - Decrease for poor quality ($0.10)
   - Set custom amount ($0.25)
5. Admin marks as PAID
6. NOW it appears in user's earnings display

---

## Data Flow

```
Game Completes
    ↓
System calculates: calculated_earnings = $0.35 (suggestion only)
    ↓
Admin reviews and sets: payment_amount = $0.40
    ↓
Status = PENDING → Shows in "Pending Earnings" ($0.40)
    ↓
Admin marks as PAID
    ↓
Shows in:
- Total Lifetime Earnings: $0.40
- This Week: $0.40
- Chart: $0.40
- Average Per Game: (updated)
- Last Game Earned: $0.40
```

---

## Fixed Issues

### Bug 1: Highest Earning Tracking (FIXED)
**Before:** Tracked highest `calculated_earnings` (system suggestion)  
**After:** Tracks highest `payment_amount` (admin-set amount)

### Bug 2: Chart Fallback (FIXED)
**Before:** Chart showed `session.amount || session.calculated || 0` (mixed data)  
**After:** Chart shows `session.amount || 0` (only actual payments)

---

## Key Takeaways

✅ **User sees:** Only what admins have set/paid  
✅ **Giant number:** 100% admin-controlled (paid amounts only)  
✅ **All stats:** Based on admin-set payment amounts  
✅ **Chart:** Only actual payments (no suggestions)  
✅ **Transparency:** Users see real money, not performance scores

❌ **User does NOT see:** System's calculated suggestions  
❌ **No mixing:** Suggestions never appear in user earnings display

The play-to-earn panel is **completely synced** with admin-set paid amounts!

