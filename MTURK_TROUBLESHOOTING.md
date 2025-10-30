# MTurk Integration Troubleshooting

Quick fixes for common MTurk integration issues.

---

## ❓ "MTurk initialization message not showing"

### Problem
When starting the backend, you don't see:
```
✅ MTurk client initialized (sandbox environment)
💰 Base pay: $0.05, Max bonus: $0.05
```

### Solution
**This is now fixed!** The MTurk client now initializes at startup.

**Restart your backend:**
```bash
uvicorn backend.main:app --reload --host 0.0.0.0 --port 8000
```

**You should now see:**
```
INFO:     Started server process
✅ MTurk client initialized (sandbox environment)
💰 Base pay: $0.05, Max bonus: $0.05
🚀 Application started successfully
```

### If you still don't see it
Check if AWS credentials are set in `.env`:
```bash
# Check if variables are set
grep AWS_ACCESS_KEY_ID .env
grep AWS_SECRET_ACCESS_KEY .env
grep MTURK_ENVIRONMENT .env
```

If missing, add them:
```bash
AWS_ACCESS_KEY_ID=your-key-here
AWS_SECRET_ACCESS_KEY=your-secret-here
MTURK_ENVIRONMENT=sandbox
MTURK_BASE_PAY=0.05
MTURK_MAX_BONUS=0.05
```

---

## ❓ "MTurk client initialization failed"

### Error Message
```
⚠️  MTurk client initialization failed: ...
   MTurk features will not be available until credentials are configured.
```

### Possible Causes & Solutions

#### 1. Missing AWS Credentials
**Check:**
```bash
cat .env | grep AWS
```

**Fix:**
Add to `.env`:
```bash
AWS_ACCESS_KEY_ID=AKIAIOSFODNN7EXAMPLE
AWS_SECRET_ACCESS_KEY=wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY
```

#### 2. Invalid AWS Credentials
**Error:** `InvalidClientTokenId` or `SignatureDoesNotMatch`

**Fix:**
1. Go to AWS IAM Console
2. Verify access key is active
3. Regenerate keys if needed
4. Update `.env` with new keys

#### 3. Missing IAM Permissions
**Error:** `AccessDeniedException`

**Fix:**
1. Go to AWS IAM Console
2. Find your user (`mturk-api-user`)
3. Ensure `AmazonMechanicalTurkFullAccess` policy is attached

#### 4. boto3 Not Installed
**Error:** `ModuleNotFoundError: No module named 'boto3'`

**Fix:**
```bash
pip install boto3
# Or
pip install -r backend/requirements.txt
```

---

## ❓ "Worker not auto-registering"

### Problem
Worker lands on lobby but doesn't see the auto-login animation.

### Solutions

#### 1. Check URL Parameters
**URL should look like:**
```
http://localhost:5173/lobby?workerId=A3EXAMPLE&assignmentId=3EXAMPLE&hitId=3EXAMPLE
```

**Missing parameters?**
- Make sure HIT was created with correct `ExternalURL`
- Check `EXTERNAL_URL` in `.env`

#### 2. Check Browser Console
Open browser DevTools (F12) and look for errors:
```javascript
// Should see:
POST /api/auth/mturk-register 200 OK
```

**If 401 Unauthorized:**
- Backend endpoint might not be accessible
- Check CORS configuration

**If 500 Internal Server Error:**
- Check backend logs
- Database might not be initialized

#### 3. Preview Mode
**URL has `assignmentId=ASSIGNMENT_ID_NOT_AVAILABLE`?**

This is preview mode - worker needs to accept the HIT first.

**Expected behavior:**
- Shows yellow preview mode notification
- Instructions to accept HIT
- No account created

---

## ❓ "Payment not processing"

### Problem
Admin clicks "MTurk Pay" but payment fails.

### Solutions

#### 1. Check Session Has MTurk Data
**Backend logs should show:**
```
💼 MTurk context saved: worker=A3EXAMPLE, assignment=3EXAMPLE
```

**If missing:**
- Worker might not have joined via MTurk URL
- Check WebSocket connection passed MTurk context
- Verify `localStorage.getItem('mturk_context')` in browser

#### 2. Check Assignment Status
**Error:** `Assignment already submitted`

**Cause:** Assignment was already approved in MTurk

**Fix:**
- Each assignment can only be paid once
- Check `mturk_payment_sent` flag in database
- Worker needs to accept a new HIT

#### 3. Check Account Balance
**Error:** `InsufficientFunds`

**Fix (Sandbox):**
- Shouldn't happen - sandbox has unlimited balance
- Check `MTURK_ENVIRONMENT=sandbox` in `.env`

**Fix (Production):**
```bash
# Check balance via API
curl http://localhost:8000/api/admin/mturk/balance \
  -H "Authorization: Bearer YOUR_TOKEN"

# Add funds at https://requester.mturk.com
```

#### 4. Check Calculated Earnings
**Error:** `No calculated earnings for this session`

**Cause:** Session doesn't have earnings calculated

**Fix:**
- Make sure game completed fully
- Check `calculated_earnings` field in database
- Earnings calculated at game end

---

## ❓ "Database migration failed"

### Error
```
sqlalchemy.exc.OperationalError: no such column: sessions.mturk_worker_id
```

### Solution
Run the migration:
```bash
cd backend
python3 -m alembic upgrade head
```

**Expected output:**
```
INFO  [alembic.runtime.migration] Running upgrade 004 -> 006, Add MTurk integration fields
```

**If migration already applied:**
```
INFO  [alembic.runtime.migration] Context impl SQLiteImpl.
INFO  [alembic.runtime.migration] Will assume non-transactional DDL.
```

---

## ❓ "Frontend not detecting MTurk parameters"

### Problem
MTurkAutoLogin component not showing.

### Solutions

#### 1. Check Component Import
**In `LobbyPage.jsx`:**
```javascript
import MTurkAutoLogin from '../components/MTurkAutoLogin';

// In render:
<MTurkAutoLogin />
```

#### 2. Check URL Parameters
**Open browser console:**
```javascript
const params = new URLSearchParams(window.location.search);
console.log('workerId:', params.get('workerId'));
console.log('assignmentId:', params.get('assignmentId'));
console.log('hitId:', params.get('hitId'));
```

**All should have values** (not null)

#### 3. Check React Router
**URL parameters might be stripped by router**

**Fix:** Ensure router doesn't strip query params:
```javascript
// App.jsx
<Route path="/lobby" element={<LobbyPage />} />
// Should preserve ?workerId=... params
```

---

## ❓ "CORS errors in browser"

### Error
```
Access to fetch at 'http://localhost:8000/api/auth/mturk-register' 
from origin 'http://localhost:5173' has been blocked by CORS policy
```

### Solution
**Check backend CORS configuration:**

In `backend/main.py`:
```python
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Development
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

**For production:**
```python
allow_origins=[
    "https://yourdomain.com",
    "https://worker.mturk.com",
    "https://workersandbox.mturk.com"
]
```

---

## ❓ "HIT not showing on MTurk"

### Problem
Created HIT via API but can't find it on MTurk marketplace.

### Solutions

#### 1. Check Environment
**Sandbox vs Production mismatch?**

**Backend `.env`:**
```bash
MTURK_ENVIRONMENT=sandbox
```

**Check at:**
- Sandbox: https://workersandbox.mturk.com
- Production: https://www.mturk.com

#### 2. Check HIT Status
**Via API:**
```bash
curl http://localhost:8000/api/admin/mturk/hits \
  -H "Authorization: Bearer YOUR_TOKEN"
```

**Look for:**
```json
{
  "hits": [
    {
      "HITId": "3EXAMPLE",
      "Title": "Your HIT title",
      "HITStatus": "Assignable"  // Should be Assignable
    }
  ]
}
```

#### 3. Check Qualifications
**HIT might have qualification requirements that filter you out**

**Solution:**
- Create HIT without qualifications first
- Test with your worker account
- Add qualifications later

---

## 🆘 Still Having Issues?

### Check Logs

**Backend logs:**
```bash
# Look for errors in terminal where backend is running
# Key indicators:
✅ = Success
⚠️ = Warning (might still work)
❌ = Error (won't work)
```

**Browser console:**
```javascript
// Open DevTools (F12)
// Check Console tab for errors
// Check Network tab for failed requests
```

### Test Individual Components

**1. Test MTurk API directly:**
```bash
python -c "from backend.mturk_api import get_account_balance; print(get_account_balance())"
```

**2. Test worker registration:**
```bash
curl -X POST http://localhost:8000/api/auth/mturk-register \
  -H "Content-Type: application/json" \
  -d '{"worker_id":"ATEST","assignment_id":"3TEST","hit_id":"3TEST"}'
```

**3. Test database:**
```bash
python -c "
from backend.database import async_session_maker, Session
import asyncio

async def test():
    async with async_session_maker() as db:
        from sqlalchemy import select
        result = await db.execute(select(Session).limit(1))
        print('Database OK:', result.scalar())

asyncio.run(test())
"
```

### Get Help

1. **Check documentation:**
   - `MTURK_API_SETUP.md` - Setup guide
   - `MTURK_WORKFLOW.md` - How it works
   - `MTURK_SECURITY_REVIEW.md` - Security details

2. **Check AWS documentation:**
   - https://docs.aws.amazon.com/mturk/
   - https://boto3.amazonaws.com/v1/documentation/api/latest/reference/services/mturk.html

3. **Check backend logs carefully:**
   - Most errors are logged with helpful messages
   - Look for 💼, ✅, ⚠️, ❌ emojis

---

**Most issues are configuration-related!** Double-check your `.env` file first. 🔧

