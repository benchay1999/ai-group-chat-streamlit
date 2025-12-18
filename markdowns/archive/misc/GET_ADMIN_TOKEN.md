# How to Get Your Admin Token

Quick guide to getting your JWT admin token for API testing.

---

## 🎯 Quick Methods

### Method 1: Via curl (Recommended)

```bash
curl -X POST https://ai-groupchat.ngrok.io/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": "your_admin_username",
    "password": "your_admin_password"
  }'
```

**Response:**
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJhZG1pbiIsInVzZXJfaWQiOiJhZG1pbiIsImlhdCI6MTY5ODY3ODAwMH0.abc123def456...",
  "token_type": "bearer",
  "user_id": "admin",
  "role": "admin"
}
```

**Copy the `access_token` value** - that's your token!

---

### Method 2: From Browser Console

**Step 1:** Login to your app
- Go to http://localhost:5173/login
- Enter your admin credentials
- Click "Login"

**Step 2:** Open DevTools
- Press `F12` (or right-click → Inspect)
- Go to **Console** tab

**Step 3:** Get the token
```javascript
localStorage.getItem('access_token')
```

**Step 4:** Copy the result (without quotes)

---

### Method 3: Using Python

```python
import requests

# Login
response = requests.post('https://ai-groupchat.ngrok.io/api/auth/login', json={
    'user_id': 'admin',
    'password': 'your_password'
})

# Get token
token = response.json()['access_token']
print(f"Your admin token:\n{token}")

# Use it
headers = {'Authorization': f'Bearer {token}'}
result = requests.get('https://ai-groupchat.ngrok.io/api/admin/mturk/balance', headers=headers)
print(f"\nMTurk Balance: {result.json()}")
```

---

## 🔐 Don't Have an Admin Account?

### Option 1: Use create_admin.py

```bash
python create_admin.py
```

Follow the prompts:
```
Enter admin username: admin
Enter admin password: ********
Confirm password: ********
✅ Admin user created successfully!
```

### Option 2: Create Manually via Python

```python
import asyncio
from backend.database import async_session_maker
from backend.auth import register_user
from backend.database import UserRole

async def create_admin():
    async with async_session_maker() as db:
        user = await register_user(
            db, 
            user_id="admin",
            password="your_secure_password",
            role=UserRole.ADMIN
        )
        print(f"✅ Admin created: {user.user_id}")
        await db.commit()

asyncio.run(create_admin())
```

---

## 📝 Using the Token

### In curl

```bash
curl -X POST https://ai-groupchat.ngrok.io/api/admin/mturk/create-hit \
  -H "Authorization: Bearer YOUR_TOKEN_HERE" \
  -H "Content-Type: application/json" \
  -d '{
    "max_workers": 1,
    "title": "Test HIT",
    "description": "Test description",
    "keywords": "test, game"
  }'
```

### In Python

```python
import requests

token = "YOUR_TOKEN_HERE"
headers = {
    'Authorization': f'Bearer {token}',
    'Content-Type': 'application/json'
}

# Create HIT
response = requests.post(
    'https://ai-groupchat.ngrok.io/api/admin/mturk/create-hit',
    headers=headers,
    json={
        'max_workers': 1,
        'title': 'Test HIT',
        'description': 'Test description',
        'keywords': 'test, game'
    }
)

print(response.json())
```

### In JavaScript/Fetch

```javascript
const token = "YOUR_TOKEN_HERE";

fetch('https://ai-groupchat.ngrok.io/api/admin/mturk/create-hit', {
  method: 'POST',
  headers: {
    'Authorization': `Bearer ${token}`,
    'Content-Type': 'application/json'
  },
  body: JSON.stringify({
    max_workers: 1,
    title: 'Test HIT',
    description: 'Test description',
    keywords: 'test, game'
  })
})
.then(res => res.json())
.then(data => console.log(data));
```

---

## ⏰ Token Expiration

**Tokens expire after 24 hours** (configured in `backend/config.py`)

If you get `401 Unauthorized`, your token has expired. Get a new one by logging in again.

---

## 🔍 Verify Your Token

Check if your token is valid:

```bash
curl -X GET https://ai-groupchat.ngrok.io/api/auth/me \
  -H "Authorization: Bearer YOUR_TOKEN_HERE"
```

**Valid token response:**
```json
{
  "user_id": "admin",
  "role": "admin",
  "created_at": "2025-10-30T00:00:00"
}
```

**Invalid token response:**
```json
{
  "detail": "Could not validate credentials"
}
```

---

## 🎯 Quick Test Script

Save this as `test_admin_token.sh`:

```bash
#!/bin/bash

# Login and get token
echo "🔐 Logging in..."
RESPONSE=$(curl -s -X POST https://ai-groupchat.ngrok.io/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": "admin",
    "password": "your_password"
  }')

# Extract token
TOKEN=$(echo $RESPONSE | grep -o '"access_token":"[^"]*' | cut -d'"' -f4)

if [ -z "$TOKEN" ]; then
  echo "❌ Login failed!"
  echo $RESPONSE
  exit 1
fi

echo "✅ Token obtained!"
echo ""
echo "Your admin token:"
echo "$TOKEN"
echo ""
echo "📋 Copied to clipboard (if xclip installed):"
echo "$TOKEN" | xclip -selection clipboard 2>/dev/null || echo "(xclip not available)"
echo ""
echo "🧪 Testing token..."
curl -X GET https://ai-groupchat.ngrok.io/api/admin/mturk/balance \
  -H "Authorization: Bearer $TOKEN"
```

Make it executable:
```bash
chmod +x test_admin_token.sh
./test_admin_token.sh
```

---

## 💡 Pro Tips

1. **Save your token temporarily:**
   ```bash
   export ADMIN_TOKEN="your_token_here"
   curl -H "Authorization: Bearer $ADMIN_TOKEN" https://ai-groupchat.ngrok.io/api/admin/mturk/balance
   ```

2. **Store in a file (for testing only):**
   ```bash
   echo "your_token_here" > .admin_token
   curl -H "Authorization: Bearer $(cat .admin_token)" https://ai-groupchat.ngrok.io/api/admin/mturk/balance
   ```
   
   ⚠️ **Don't commit `.admin_token` to git!** Add to `.gitignore`

3. **Use environment variables:**
   ```bash
   # In .env.local (not committed)
   ADMIN_TOKEN=your_token_here
   
   # In your script
   source .env.local
   curl -H "Authorization: Bearer $ADMIN_TOKEN" ...
   ```

---

**That's it!** You now know how to get and use your admin token. 🎉

