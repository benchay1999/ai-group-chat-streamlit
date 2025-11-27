# Deployment Setup Guide

**Your Deployment Configuration:**
- **Frontend:** https://ai-group-chat.netlify.app/ (Netlify)
- **Backend:** https://ai-groupchat.ngrok.io (ngrok tunnel)

---

## Environment Configuration

### Backend (.env file)

Your backend should have the following configuration:

```bash
# MTurk External URL - Points to your Netlify frontend
# Workers will be redirected to this URL when they accept the HIT
EXTERNAL_URL=https://ai-group-chat.netlify.app/lobby

# CORS - Must include your Netlify domain
# This allows your frontend to make API calls to the backend
CORS_ALLOWED_ORIGINS=https://ai-group-chat.netlify.app,http://localhost:5173,http://localhost:3000

# MTurk Configuration
MTURK_ENVIRONMENT=sandbox  # Change to 'production' when ready
MTURK_BASE_PAY=0.05
MTURK_MAX_BONUS=0.05

# AWS Credentials (required for MTurk API)
AWS_ACCESS_KEY_ID=your-aws-access-key-id
AWS_SECRET_ACCESS_KEY=your-aws-secret-access-key

# JWT Secrets (change these!)
JWT_SECRET_KEY=your-secret-key-change-this-in-production
JWT_COMPLETION_SECRET=your-completion-key-secret-change-this

# Database
DATABASE_URL=sqlite+aiosqlite:///./group_chat.db
# Or PostgreSQL: DATABASE_URL=postgresql+asyncpg://user:pass@host:port/group_chat_db
```

### Frontend (Netlify Environment Variables)

In your Netlify dashboard, set:

```bash
# Backend URL - Your ngrok tunnel URL
VITE_BACKEND_URL=https://ai-groupchat.ngrok.io
# Or if using REACT_APP prefix:
REACT_APP_BACKEND_URL=https://ai-groupchat.ngrok.io
```

---

## Important Notes

### 1. ngrok URL Updates

⚠️ **ngrok URLs change on restart!** Each time you restart ngrok, you get a new URL.

**When your ngrok URL changes, you must update:**

1. **Backend .env:**
   - No changes needed (backend doesn't reference itself)

2. **Frontend environment variable on Netlify:**
   - Update `VITE_BACKEND_URL` or `REACT_APP_BACKEND_URL`
   - Redeploy frontend

3. **If using ngrok for EXTERNAL_URL (MTurk workers):**
   - Update `EXTERNAL_URL` in backend .env
   - Restart backend

**Solution:** Use ngrok reserved domain (paid feature) or keep frontend pointing to backend URL, not MTurk workers.

### 2. CORS Configuration

Your backend CORS must include your Netlify domain:

```python
# In backend/main.py - Already configured!
CORS_ALLOWED_ORIGINS=https://ai-group-chat.netlify.app,http://localhost:5173,http://localhost:3000
```

This allows:
- ✅ Netlify frontend to call backend API
- ✅ Local development (localhost:5173, localhost:3000)
- ❌ Blocks all other domains

### 3. MTurk Worker Flow

When MTurk workers accept your HIT:

1. **MTurk redirects to:** `EXTERNAL_URL` (your Netlify frontend)
   - URL: `https://ai-group-chat.netlify.app/lobby?workerId=A...&assignmentId=3...&hitId=3...`

2. **Frontend detects MTurk parameters** and calls backend:
   - `POST https://ai-groupchat.ngrok.io/api/auth/mturk-register`

3. **Worker is auto-registered** and plays game

4. **Session data saved** with MTurk IDs

5. **Admin approves payment** via backend API

---

## Testing Your Setup

### 1. Test CORS Configuration

From your browser console on https://ai-group-chat.netlify.app/:

```javascript
// Test if CORS is working
fetch('https://ai-groupchat.ngrok.io/api/auth/me', {
  headers: {
    'Authorization': 'Bearer YOUR_TOKEN'
  }
})
.then(r => r.json())
.then(console.log)
.catch(console.error)
```

**Expected:** Should return user data (not CORS error)

### 2. Test MTurk Registration

Create a test HIT:

```bash
curl -X POST https://ai-groupchat.ngrok.io/api/admin/mturk/create-hit \
  -H "Authorization: Bearer YOUR_ADMIN_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "max_workers": 1,
    "title": "Test HIT - AI Group Chat",
    "description": "Play a 5-minute group chat game and identify AI players",
    "keywords": "chat,game,conversation,AI"
  }'
```

### 3. Verify Worker Registration

1. Accept HIT in sandbox: https://workersandbox.mturk.com
2. You'll be redirected to: `https://ai-group-chat.netlify.app/lobby?workerId=...`
3. Check frontend auto-login notification
4. Check backend logs for: `✅ MTurk worker detected: A...`

### 4. Verify Session Saving

After playing a game:

```bash
# Check database for MTurk fields
sqlite3 group_chat.db "SELECT mturk_worker_id, mturk_assignment_id, room_code FROM sessions WHERE mturk_worker_id IS NOT NULL LIMIT 5;"
```

**Expected:** Should see worker_id and assignment_id populated

---

## Troubleshooting

### CORS Errors

**Error:** "Access to fetch at 'https://ai-groupchat.ngrok.io' from origin 'https://ai-group-chat.netlify.app' has been blocked by CORS policy"

**Solutions:**
1. Verify `CORS_ALLOWED_ORIGINS` includes your Netlify URL
2. Restart backend after changing CORS settings
3. Check backend startup logs for: `🔒 CORS configured for production with origins: [...]`

### ngrok Tunnel Expired

**Error:** "ERR_CONNECTION_REFUSED" or "502 Bad Gateway"

**Solutions:**
1. Check if ngrok is still running: `ps aux | grep ngrok`
2. If stopped, restart: `ngrok http 8000`
3. Update frontend env variable with new ngrok URL
4. Redeploy frontend on Netlify

### MTurk Workers Can't Register

**Error:** "Invalid MTurk worker ID format" or "Too many registration attempts"

**Solutions:**
1. Check worker_id format: Must be 14 chars, start with 'A'
2. Check rate limiting: Max 10 requests per minute per IP
3. Verify backend logs for validation errors
4. Check if assignment already registered (409 error)

### Session Data Not Saving

**Error:** MTurk fields are NULL in database

**Solutions:**
1. Check backend logs for: `💼 Found MTurk context for user...`
2. Verify worker is authenticated (JWT token valid)
3. Check if user_id matches MTurk pattern (14 chars, starts with 'A')
4. Verify `mturk_context` passed in WebSocket connection

---

## Production Deployment Checklist

Before going to production:

### Backend

- [ ] Set `MTURK_ENVIRONMENT=production`
- [ ] Update `EXTERNAL_URL=https://ai-group-chat.netlify.app/lobby`
- [ ] Update `CORS_ALLOWED_ORIGINS` (remove localhost if not needed)
- [ ] Set strong `JWT_SECRET_KEY` and `JWT_COMPLETION_SECRET`
- [ ] Switch to PostgreSQL database (recommended)
- [ ] Complete MTurk Requester registration
- [ ] Add funds to MTurk production account
- [ ] Consider using permanent ngrok domain or proper cloud hosting

### Frontend

- [ ] Update `VITE_BACKEND_URL` to production backend
- [ ] Test all API endpoints work
- [ ] Verify WebSocket connections work
- [ ] Test MTurk auto-login flow
- [ ] Check all CORS requests succeed

### MTurk

- [ ] Test complete workflow in sandbox first
- [ ] Verify payments work correctly
- [ ] Check worker experience (UI, flow, completion)
- [ ] Monitor for any errors in logs
- [ ] Set up alerts for payment failures

---

## Monitoring

### Backend Logs to Watch

**Success indicators:**
```
🔒 CORS configured for production with origins: [...]
✅ MTurk client initialized (sandbox environment)
✅ MTurk worker detected: A...
💼 Found MTurk context for user...
💼 MTurk context saved: worker=..., assignment=...
✅ Approved assignment: ...
✅ Sent bonus $... to worker...
```

**Warning signs:**
```
❌ MTurk payment error: ...
⚠️ No user_id to store for player
⚠️ MTurk client initialization failed
429 Too Many Requests (if excessive)
```

### Frontend Errors to Watch

**In browser console:**
- CORS errors → Check CORS_ALLOWED_ORIGINS
- 401 Unauthorized → Check JWT token
- 429 Too Many Requests → Rate limit hit (normal protection)
- 409 Conflict → Assignment already registered (expected if re-attempting)

---

## Recommended Improvements

### 1. Use Permanent Backend URL

Instead of ngrok (which changes URLs), consider:

**Option A: ngrok Paid Plan**
- Get reserved domain that doesn't change
- Cost: ~$8/month
- Setup: `ngrok http 8000 --domain=your-domain.ngrok-free.app`

**Option B: Cloud Hosting**
- Deploy backend to: Railway, Render, Fly.io, or AWS
- Get permanent HTTPS URL
- Better for production use

### 2. Use PostgreSQL Database

For production, migrate from SQLite to PostgreSQL:

```bash
# Example: Use Railway PostgreSQL
DATABASE_URL=postgresql+asyncpg://user:pass@railway.app:5432/group_chat_db
```

Benefits:
- Better concurrent access
- Better reliability
- Built-in backups

### 3. Add Monitoring

Set up error tracking:
- **Backend:** Sentry, CloudWatch, or similar
- **Frontend:** Sentry, LogRocket, or similar
- **Alerts:** Email/Slack notifications for payment failures

---

## Quick Reference

### Your URLs

| Service | URL |
|---------|-----|
| Frontend (Public) | https://ai-group-chat.netlify.app/ |
| Backend API | https://ai-groupchat.ngrok.io |
| MTurk Worker Entry | https://ai-group-chat.netlify.app/lobby?workerId=...&assignmentId=...&hitId=... |
| Admin Panel | https://ai-group-chat.netlify.app/admin |

### Important Endpoints

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/api/auth/mturk-register` | POST | Auto-register MTurk worker |
| `/api/admin/mturk/sessions/{id}/approve-payment` | POST | Process payment |
| `/api/admin/mturk/create-hit` | POST | Create new HIT |
| `/api/admin/mturk/hits` | GET | List active HITs |
| `/api/admin/mturk/balance` | GET | Check account balance |

---

## Support

If you encounter issues:

1. **Check backend logs** for error messages
2. **Check browser console** for frontend errors
3. **Verify CORS** configuration includes Netlify URL
4. **Test with curl** to isolate frontend vs backend issues
5. **Check ngrok status** - is tunnel still active?
6. **Review** `MTURK_FIXES_COMPLETE.md` for troubleshooting guide

---

**Last Updated:** October 31, 2025  
**Status:** Ready for Testing

