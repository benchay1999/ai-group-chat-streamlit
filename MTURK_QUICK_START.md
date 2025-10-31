# MTurk Quick Start Guide

**Your specific setup with ngrok**

---

## 🚀 Your URLs

- **Backend API:** https://ai-groupchat.ngrok.io
- **Game URL:** https://ai-groupchat.ngrok.io/lobby
- **MTurk Sandbox:** https://requestersandbox.mturk.com/developer

---

## ⚡ Quick Commands

### 1. Get Your Admin Token

```bash
curl -X POST https://ai-groupchat.ngrok.io/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": "admin",
    "password": "your_password"
  }'
```

Copy the `access_token` from the response.

---

### 2. Check MTurk Balance

```bash
curl -X GET https://ai-groupchat.ngrok.io/api/admin/mturk/balance \
  -H "Authorization: Bearer YOUR_TOKEN"
```

**Expected:** `{"available": "10000.00", "on_hold": "0.00"}`

---

### 3. Create a Test HIT

```bash
curl -X POST https://ai-groupchat.ngrok.io/api/admin/mturk/create-hit \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "max_workers": 1,
    "title": "Identify AI in Group Chat Game",
    "description": "Play a 5-minute conversation game and identify which player is AI. Earn bonus for good performance!",
    "keywords": "game, chat, AI, conversation, research"
  }'
```

**Success response:**
```json
{
  "success": true,
  "hit_id": "3EXAMPLE...",
  "external_url": "https://ai-groupchat.ngrok.io/lobby"
}
```

---

### 4. List Your HITs

```bash
curl -X GET https://ai-groupchat.ngrok.io/api/admin/mturk/hits \
  -H "Authorization: Bearer YOUR_TOKEN"
```

---

### 5. Approve Payment

```bash
curl -X POST https://ai-groupchat.ngrok.io/api/admin/mturk/sessions/SESSION_ID/approve-payment \
  -H "Authorization: Bearer YOUR_TOKEN"
```

---

## 🔧 Environment Configuration

Make sure your `.env` file has:

```bash
# AWS Credentials
AWS_ACCESS_KEY_ID=your-access-key
AWS_SECRET_ACCESS_KEY=your-secret-key

# MTurk Configuration
MTURK_ENVIRONMENT=sandbox
MTURK_BASE_PAY=0.05
MTURK_MAX_BONUS=0.05

# Your ngrok URL
EXTERNAL_URL=https://ai-groupchat.ngrok.io/lobby

MTURK_FRAME_HEIGHT=0
```

---

## 🧪 Testing Workflow

### Step 1: Complete MTurk Registration

1. Go to: https://requestersandbox.mturk.com/developer
2. Sign in with AWS credentials
3. Link your account
4. Add payment method

### Step 2: Create HIT

```bash
# Get token
TOKEN=$(curl -s -X POST https://ai-groupchat.ngrok.io/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"user_id":"admin","password":"your_password"}' \
  | grep -o '"access_token":"[^"]*' | cut -d'"' -f4)

# Create HIT
curl -X POST https://ai-groupchat.ngrok.io/api/admin/mturk/create-hit \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "max_workers": 1,
    "title": "Test: Identify AI in Group Chat",
    "description": "Play a game and identify which player is AI",
    "keywords": "game, chat, AI"
  }'
```

### Step 3: Accept HIT as Worker

1. Go to: https://workersandbox.mturk.com
2. Find your HIT
3. Click "Accept HIT"
4. You'll be redirected to: `https://ai-groupchat.ngrok.io/lobby?workerId=...&assignmentId=...`

### Step 4: Play Game

- Auto-login should happen automatically
- You'll see "MTurk Worker" badge
- Play the game normally
- Complete the session

### Step 5: Approve Payment (Admin)

```bash
# List sessions to find the session ID
curl -X GET https://ai-groupchat.ngrok.io/api/admin/sessions \
  -H "Authorization: Bearer $TOKEN"

# Approve payment
curl -X POST https://ai-groupchat.ngrok.io/api/admin/mturk/sessions/SESSION_ID/approve-payment \
  -H "Authorization: Bearer $TOKEN"
```

Or use the Admin UI at: https://ai-groupchat.ngrok.io/admin

---

## 🎯 One-Liner Test Script

```bash
#!/bin/bash

# Your setup
API_URL="https://ai-groupchat.ngrok.io"
ADMIN_USER="admin"
ADMIN_PASS="your_password"

# Get token
echo "🔐 Getting admin token..."
TOKEN=$(curl -s -X POST $API_URL/api/auth/login \
  -H "Content-Type: application/json" \
  -d "{\"user_id\":\"$ADMIN_USER\",\"password\":\"$ADMIN_PASS\"}" \
  | grep -o '"access_token":"[^"]*' | cut -d'"' -f4)

if [ -z "$TOKEN" ]; then
  echo "❌ Login failed!"
  exit 1
fi

echo "✅ Token obtained!"

# Check balance
echo ""
echo "💰 Checking MTurk balance..."
curl -s -X GET $API_URL/api/admin/mturk/balance \
  -H "Authorization: Bearer $TOKEN" | jq

# Create HIT
echo ""
echo "🎯 Creating test HIT..."
curl -s -X POST $API_URL/api/admin/mturk/create-hit \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "max_workers": 1,
    "title": "Test: Identify AI in Group Chat",
    "description": "Play a game and identify which player is AI",
    "keywords": "game, chat, AI"
  }' | jq

echo ""
echo "✅ Done! Check https://workersandbox.mturk.com for your HIT"
```

Save as `test_mturk.sh`, make executable: `chmod +x test_mturk.sh`, then run: `./test_mturk.sh`

---

## 📱 Admin UI Access

**Login:** https://ai-groupchat.ngrok.io/login

**Admin Panel:** https://ai-groupchat.ngrok.io/admin

From the admin panel, you can:
- ✅ View all sessions with MTurk info
- ✅ See worker IDs and assignment IDs
- ✅ Click "⚡ MTurk Pay" button to approve payments
- ✅ View payment status (✓Base, ✓Bonus)

---

## 🔍 Troubleshooting

### "AWS Account must be linked"

**Solution:** Complete registration at https://requestersandbox.mturk.com/developer

### "Invalid credentials"

**Check your `.env` file:**
```bash
cat .env | grep AWS
```

### "HIT not showing on MTurk"

**Wait 1-2 minutes** for MTurk to process, then check: https://workersandbox.mturk.com

### "Worker not auto-registering"

**Check URL parameters:**
- URL should have: `?workerId=...&assignmentId=...&hitId=...`
- Check browser console for errors

---

## 📚 Full Documentation

- **Setup Guide:** `MTURK_API_SETUP.md`
- **Workflow:** `MTURK_WORKFLOW.md`
- **Troubleshooting:** `MTURK_TROUBLESHOOTING.md`
- **Registration:** `MTURK_REGISTRATION_GUIDE.md`
- **Get Token:** `GET_ADMIN_TOKEN.md`

---

## ✅ Checklist

- [ ] MTurk Requester registration complete
- [ ] AWS credentials in `.env` file
- [ ] `EXTERNAL_URL=https://ai-groupchat.ngrok.io/lobby` in `.env`
- [ ] Backend running and accessible via ngrok
- [ ] Admin account created
- [ ] Test HIT created successfully
- [ ] Test worker account created
- [ ] Full flow tested (create HIT → accept → play → pay)

---

**Ready to go!** 🚀 Your MTurk integration is configured for `https://ai-groupchat.ngrok.io`

