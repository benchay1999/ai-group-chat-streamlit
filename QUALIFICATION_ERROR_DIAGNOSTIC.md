# Qualification Error Diagnostic Guide

## Error: "You do not meet those Qualifications"

This means the worker doesn't have the required qualification to view the HIT.

---

## 🔍 IMMEDIATE DIAGNOSTIC STEPS

### Step 1: Check Backend Logs

**CRITICAL**: Look at your backend server logs when you request a cashout.

You should see:
```
🎯 CREATING WORKER-SPECIFIC HIT
Worker ID: A1B2C3D4E5F6G7
Amount: $2.00

1️⃣  Creating worker-specific qualification...
   ✅ Qualification created: 3QUAL123
   🔄 Assigning qualification to worker A1B2C3D4E5F6G7...
   ✅ Qualification assigned to worker: A1B2C3D4E5F6G7
   🔍 Verifying qualification assignment...
   ✅ Verification successful (attempt 1) - Worker has qualification with value: 1
```

**If you DON'T see these logs**, the backend wasn't restarted with the new code!

### Step 2: Verify Worker ID Matches

**THIS IS THE MOST COMMON ISSUE!**

The Worker ID in your app profile **MUST EXACTLY MATCH** your MTurk Worker ID.

**How to find your MTurk Worker ID**:
1. Log into MTurk Sandbox: https://workersandbox.mturk.com
2. Click your name (top right)
3. Click "Account"  
4. Look for "Worker ID" - it looks like: `A1B2C3D4E5F6G7`

**How to check your app profile**:
1. Go to your profile in the app
2. Look at "MTurk Worker ID" field
3. **It must EXACTLY match** your MTurk Worker ID

**Common mistakes**:
- ❌ Extra spaces
- ❌ Wrong case (capital vs lowercase)
- ❌ Using email instead of Worker ID
- ❌ Using a test/dummy ID

### Step 3: Check Environment Match

Make sure you're in the right environment:

**Backend `.env` file**:
```
MTURK_ENVIRONMENT=sandbox
```

**MTurk account**: Must be logged into **Sandbox** worker account
- Sandbox: https://workersandbox.mturk.com
- Production: https://www.mturk.com

**They must match!** If backend uses sandbox, you must use sandbox worker account.

---

## 🛠️ ENHANCED FIXES APPLIED

I've added even more robust verification:

### Fix 1: Retry Logic (3 attempts)
- Tries verification 3 times
- Exponential backoff (2s, 4s, 6s)
- Fails fast if qualification can't be verified

### Fix 2: Longer Propagation Delay
- Increased from 3 to **5 seconds**
- Ensures MTurk has time to propagate

### Fix 3: Pre-HIT Final Check
- Double-checks qualification right before creating HIT
- Catches any last-minute issues

### Fix 4: Better Error Messages
- Shows exact Worker ID used
- Shows qualification ID
- Fails with clear error if verification fails

---

## 📊 Expected Backend Logs (After Fixes)

### Success Case:
```bash
🎯 CREATING WORKER-SPECIFIC HIT
Transaction: tx-uuid-123
User: user-uuid-456
Worker ID: A1B2C3D4E5F6G7
Amount: $2.00

1️⃣  Creating worker-specific qualification...
   ✅ Qualification created: 3QUALIFICATION123ABC
   🔄 Assigning qualification to worker A1B2C3D4E5F6G7...
   ✅ Qualification assigned to worker: A1B2C3D4E5F6G7
   🔍 Verifying qualification assignment...
   ✅ Verification successful (attempt 1) - Worker has qualification with value: 1

2️⃣  Creating HIT with qualification requirement...
   ⏳ Waiting 5 seconds for MTurk to fully propagate qualification...
   ✅ Proceeding with HIT creation
   🔍 Final pre-HIT verification...
   ✅ Final check passed - Worker still has qualification
   💰 Creating HIT with reward: $2.00
   ✅ Created cashout HIT: 3HIT456DEF
   💵 Reward set to: $2.00

✅ WORKER-SPECIFIC HIT CREATED SUCCESSFULLY
```

### Failure Case (Verification Failed):
```bash
🔍 Verifying qualification assignment...
⚠️  Verification attempt 1 failed: An error occurred...
⏳ Waiting 2 seconds before retry...
⚠️  Verification attempt 2 failed: An error occurred...
⏳ Waiting 4 seconds before retry...
⚠️  Verification attempt 3 failed: An error occurred...
❌ CRITICAL: Could not verify qualification assignment after 3 attempts!
❌ This means the worker may not be able to access the HIT!
❌ Worker ID used: A1B2C3D4E5F6G7
❌ Qualification ID: 3QUALIFICATION123ABC
```

This error means the Worker ID is likely incorrect or doesn't exist in MTurk.

---

## 🚨 MOST LIKELY CAUSES

### 1. Backend Not Restarted ⭐⭐⭐⭐⭐ (MOST COMMON)

**Problem**: Old code is still running without qualification assignment  
**Solution**: Restart backend server

```bash
cd /home/wschay/ai-group-chat-streamlit/backend
pkill -f "uvicorn main:app"
# Activate conda environment
uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

### 2. Worker ID Mismatch ⭐⭐⭐⭐⭐ (MOST COMMON)

**Problem**: Profile Worker ID ≠ Actual MTurk Worker ID  
**Solution**: 
1. Get your REAL Worker ID from MTurk
2. Update it in your profile
3. Try cashout again

### 3. Environment Mismatch ⭐⭐⭐

**Problem**: Backend uses sandbox, but worker logged into production (or vice versa)  
**Solution**: Match environments

### 4. Qualification Assignment Failing ⭐⭐

**Problem**: MTurk API rejecting qualification assignment  
**Solution**: Check backend logs for error messages

### 5. Viewing Wrong HIT ⭐

**Problem**: Worker is looking at an old standing HIT instead of their private HIT  
**Solution**: Use the EXACT link provided by the app (don't search manually)

---

## 🧪 STEP-BY-STEP TESTING

### Test 1: Verify Backend Restart

```bash
# Check if backend is running
ps aux | grep uvicorn

# Check when it started (should be recent)
ls -lh /home/wschay/ai-group-chat-streamlit/backend/*.py
```

### Test 2: Verify Worker ID

**In MTurk**:
1. Go to https://workersandbox.mturk.com
2. Click your name → Account
3. Copy your Worker ID: `A1B2C3D4E5F6G7`

**In App**:
1. Go to Profile
2. Check "MTurk Worker ID" field
3. Should be: `A1B2C3D4E5F6G7` (EXACT match!)

### Test 3: Request Cashout with Logging

1. Open terminal with backend logs visible
2. Request cashout from app
3. Watch logs in real-time
4. Look for qualification creation/assignment messages

### Test 4: Check MTurk Qualifications

**Manual Check** (requires MTurk Requester Console access):
1. Log into MTurk Requester Console
2. Go to "Manage" → "Qualification Types"
3. Find the qualification (look for `ChatGame_User_...`)
4. Check if your Worker ID is listed

---

## 🔧 EMERGENCY WORKAROUND

If qualification system continues to fail, use the old V1 system temporarily:

### Quick Fix: Use V1 Endpoint

**Change frontend** (`frontend/src/services/walletAPI.js` line 24):

```javascript
// Change from:
const response = await api.post('/api/wallet/cashout/v2', {

// To:
const response = await api.post('/api/wallet/cashout', {
```

This uses the old standing HIT approach (no qualifications needed).

**Then rebuild frontend**:
```bash
cd /home/wschay/ai-group-chat-streamlit/frontend
npm run build
```

---

## 📞 WHAT TO SHARE FOR HELP

If the issue persists, share:

1. **Backend logs** during cashout (the entire qualification section)
2. **Worker ID** from your profile (sanitize if needed)
3. **Environment** (sandbox or production)
4. **When backend was last restarted**
5. **Any error messages** from backend logs

---

## ✅ SUCCESS INDICATORS

You'll know it's working when:

1. ✅ Backend logs show successful verification
2. ✅ No "⚠️ WARNING" or "❌ CRITICAL" messages
3. ✅ You can see and access the HIT
4. ✅ HIT shows correct reward amount

---

**Most likely fix: Restart backend + Verify Worker ID matches!**

