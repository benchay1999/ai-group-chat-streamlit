# MTurk HIT "No More HITs Available" - URGENT FIX

## Problem

After completing ONE cashout, MTurk shows:
> "There are no more of these HITs available"

This prevents users from cashing out again.

## Root Cause

The HIT was likely created with `MaxAssignments=1` instead of the intended `MaxAssignments=99,999` (or 1,000 for sandbox).

This could happen if:
1. The HIT was created manually with wrong settings
2. An older version of the script was used
3. The environment variable was incorrect during creation

## Immediate Solution

You have TWO options:

### Option 1: Extend Existing HIT (RECOMMENDED - Quick Fix)

Add more assignments to your existing HIT:

```bash
cd /home/wschay/ai-group-chat-streamlit/backend
conda activate group-chat

# First, check current status
python check_hit_status.py

# Then, extend assignments (adds 10,000 by default)
python fix_hit_assignments.py

# Or specify custom amount
python fix_hit_assignments.py --assignments 50000
```

**Advantages:**
- ✅ Quick (takes seconds)
- ✅ Keeps existing HIT ID (no config changes needed)
- ✅ Workers keep using same HIT URL

**Disadvantages:**
- ⚠️ Requires additional MTurk pre-authorization

### Option 2: Create New Standing HIT (Clean Start)

Delete the old HIT and create a new one with correct settings:

```bash
cd /home/wschay/ai-group-chat-streamlit/backend
conda activate group-chat

# Step 1: Delete old HITs
python delete_all_hits.py

# Step 2: Create new standing HIT with correct MaxAssignments
python create_standing_hit.py

# Step 3: Update .env file with new HIT ID
# The script will tell you what to add

# Step 4: Restart backend
pkill -f uvicorn
uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

**Advantages:**
- ✅ Clean slate
- ✅ Correct settings from the start
- ✅ Full control over configuration

**Disadvantages:**
- ⚠️ Need to update .env file
- ⚠️ Need to restart backend
- ⚠️ Old HIT URL becomes invalid

## Detailed Steps - Option 1 (RECOMMENDED)

### Step 1: Check Current Status

```bash
cd /home/wschay/ai-group-chat-streamlit/backend
conda activate group-chat
python check_hit_status.py
```

Expected output:
```
MTurk HIT Status Checker
======================================================================

📋 Checking HIT: 3N4EXAMPLE5M6L7K8J9H0
🌍 Environment: SANDBOX
✅ Connected to MTurk

======================================================================
HIT DETAILS
======================================================================

📝 Title: ChatGame - Redeem Your Earnings (Instant Payment)
💰 Reward: $0.01
📊 Status: Reviewable

📈 ASSIGNMENTS:
   Max Assignments: 1          ← PROBLEM!
   Available: 0                ← PROBLEM!
   Pending: 0
   Completed: 1

📊 USAGE:
   Used: 1 / 1
   Percentage: 100.00%
   Remaining: 0                ← NO MORE AVAILABLE!

======================================================================
DIAGNOSIS
======================================================================

❌ PROBLEM FOUND: No assignments available!
   Max Assignments: 1
   Completed: 1
   Pending: 0

⚠️  CRITICAL: HIT was created with MaxAssignments=1
   This means only ONE cashout is possible!

   SOLUTION: You need to either:
   1. Extend this HIT's assignments (run: python fix_hit_assignments.py)
   2. Create a NEW standing HIT with higher MaxAssignments
```

### Step 2: Extend Assignments

```bash
python fix_hit_assignments.py --assignments 10000
```

The script will:
1. Show current HIT status
2. Ask for confirmation (type `EXTEND`)
3. Add 10,000 assignments to the HIT
4. Verify the new status

Expected output:
```
MTurk HIT Assignment Extender
======================================================================

📋 Target HIT: 3N4EXAMPLE5M6L7K8J9H0
🌍 Environment: SANDBOX
✅ Connected to MTurk

📊 Checking current HIT status...

   Current MaxAssignments: 1
   Available: 0
   Pending: 0
   Completed: 1

💡 Plan:
   Current Max: 1
   Adding: 10,000
   New Max: 10,001

💰 Estimated pre-authorization: $100.00

======================================================================
⚠️  CONFIRMATION REQUIRED
======================================================================

You are about to extend the HIT by 10,000 assignments
MTurk will pre-authorize an additional $100.00

Type 'EXTEND' to continue: EXTEND

🔄 Extending HIT assignments...
✅ SUCCESS! HIT extended

📊 Verifying new status...

   New MaxAssignments: 10,001
   Available: 10,000
   Completed: 1

======================================================================
✅ HIT SUCCESSFULLY EXTENDED
======================================================================

Your cashout HIT now supports 10,001 total cashouts!
Workers can now cash out 10,000 more times.
```

### Step 3: Verify

Test a cashout:
1. Go to your app dashboard
2. Request a cashout
3. Click "Go to MTurk HIT"
4. You should see the HIT available now!

## Why This Happened

### Possible Causes

1. **Manual HIT Creation**
   - If you created the HIT manually on MTurk website
   - Default MaxAssignments on MTurk is 1

2. **Wrong Environment Variable**
   - If `MTURK_ENVIRONMENT` was set incorrectly during HIT creation
   - Sandbox gets 1000, production gets 99999

3. **Old Script Version**
   - If an older version of `create_standing_hit.py` was used
   - May have had different default values

4. **Test HIT Not Deleted**
   - If you created a test HIT with MaxAssignments=1
   - Then used that HIT ID in production

## Prevention for Future

### When Creating New HITs

Always verify the MaxAssignments setting:

```python
# In create_standing_hit.py, line 89:
max_assignments = 1000 if environment == 'sandbox' else 99999
```

Check environment:
```bash
# Before creating HIT
echo $MTURK_ENVIRONMENT
# Should be 'sandbox' or 'production'
```

After creating HIT:
```bash
# Always check status after creation
python check_hit_status.py
```

### Monitor HIT Health

Set up periodic checks:

```bash
# Add to crontab or run weekly
python check_hit_status.py
```

Alert when assignments running low:
- < 100 assignments: Warning
- < 10 assignments: Critical
- 0 assignments: Emergency

## MTurk Pre-Authorization

When you extend assignments, MTurk pre-authorizes funds:

```
Pre-authorization = Additional Assignments × Base Reward
                  = 10,000 × $0.01
                  = $100.00
```

**Important:**
- This is a **hold**, not a charge
- Actual payment only happens when workers submit valid codes
- Pre-authorization is released when HIT expires or is deleted

## Quick Reference Commands

```bash
# Check HIT status
cd /home/wschay/ai-group-chat-streamlit/backend
conda activate group-chat
python check_hit_status.py

# Extend assignments (add 10,000)
python fix_hit_assignments.py

# Extend with custom amount
python fix_hit_assignments.py --assignments 50000

# Create new HIT
python create_standing_hit.py

# Delete all HITs
python delete_all_hits.py
```

## Files Created

1. **`backend/check_hit_status.py`** - Check HIT status and diagnose issues
2. **`backend/fix_hit_assignments.py`** - Extend MaxAssignments for existing HIT
3. **`FIX_HIT_EXHAUSTED.md`** - This documentation

## FAQ

### Q: Will this affect pending cashouts?
**A**: No! Extending assignments doesn't affect completed or pending assignments.

### Q: Do I need to restart my backend?
**A**: No, for Option 1. Yes, for Option 2 (new HIT).

### Q: Can I extend multiple times?
**A**: Yes! You can extend as many times as needed.

### Q: What's the maximum MaxAssignments?
**A**: MTurk allows up to 1,000,000 assignments per HIT.

### Q: Will workers see any difference?
**A**: No! Same HIT, same URL, they just see "Available" instead of "No HITs available".

### Q: How often should I extend?
**A**: Monitor your usage. Extend before hitting 0 available assignments.

## Summary

**Problem**: HIT exhausted after 1 cashout  
**Cause**: MaxAssignments=1 instead of 10,000+  
**Quick Fix**: Run `python fix_hit_assignments.py`  
**Long-term**: Monitor HIT status, extend before running out  

---

**Status**: Scripts Created ✅  
**Ready to Fix**: YES ✅  
**Estimated Time**: 2-3 minutes ⏱️

