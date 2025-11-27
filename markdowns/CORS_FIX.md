# CORS 400 Bad Request Fix

## Problem
Getting `400 Bad Request` on `OPTIONS /api/auth/login` during login.

## Root Cause
The frontend's origin (domain/URL) is not in the backend's `CORS_ALLOWED_ORIGINS` list.

## Solution

### Step 1: Identify Your Frontend URL
Your frontend is likely hosted at one of these:
- Netlify: `https://your-app-name.netlify.app`
- Vercel: `https://your-app-name.vercel.app`  
- Custom domain: `https://yourdomain.com`
- Or running on a server with specific IP/port

### Step 2: Update Backend .env File

Add your frontend URL to `CORS_ALLOWED_ORIGINS`:

```bash
# In your backend/.env or .env file:
CORS_ALLOWED_ORIGINS=https://your-actual-frontend-url.com,http://localhost:5173,http://localhost:3000
```

**Examples:**
```bash
# If deployed on Netlify
CORS_ALLOWED_ORIGINS=https://ai-group-chat.netlify.app,http://localhost:5173

# If using custom domain
CORS_ALLOWED_ORIGINS=https://mychat.com,http://localhost:5173

# If frontend is on specific IP/port
CORS_ALLOWED_ORIGINS=http://211.46.30.211:5173,http://localhost:5173

# Multiple domains (comma-separated, no spaces)
CORS_ALLOWED_ORIGINS=https://prod.com,https://staging.com,http://localhost:5173
```

### Step 3: Restart Backend
```bash
# Stop your backend server (Ctrl+C)
# Start it again
cd backend
uvicorn main:app --reload
```

### Step 4: Verify CORS in Logs
When backend starts, you should see:
```
🔓 CORS configured for development with origins: ['https://your-frontend-url.com', 'http://localhost:5173']
```

---

## Temporary Development Fix (NOT for Production)

If you need to test quickly, you can temporarily allow all origins:

**backend/main.py** (lines 66-72):
```python
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # ⚠️ INSECURE - Only for testing!
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

**⚠️ WARNING**: This is insecure and should NEVER be used in production!

---

## How to Find Your Frontend URL

### Method 1: Check Browser Console
1. Open browser DevTools (F12)
2. Go to Console tab
3. Type: `window.location.origin`
4. That's your frontend URL!

### Method 2: Check Network Tab
1. Open browser DevTools (F12)
2. Go to Network tab
3. Try to login
4. Look at the failed OPTIONS request
5. Check the "Origin" header - that's what you need to add

### Method 3: Check Deployment Platform
- **Netlify**: Site settings → Domain management
- **Vercel**: Project settings → Domains
- **Custom server**: Your configured domain/IP

---

## Verification

After fixing, the OPTIONS request should return `204 No Content`:
```
211.46.30.211:0 - "OPTIONS /api/auth/login HTTP/1.1" 204 No Content
211.46.30.211:0 - "POST /api/auth/login HTTP/1.1" 200 OK
```

---

## If Still Not Working

### Check 1: Frontend Environment Variables
Make sure your frontend `.env` file has the correct backend URL:
```bash
# frontend/.env
VITE_BACKEND_URL=https://your-backend-url.com
```

### Check 2: Both Must Use HTTPS (in Production)
If frontend uses HTTPS, backend must also use HTTPS:
- Frontend: `https://myapp.netlify.app` ✅
- Backend: `https://myapi.herokuapp.com` ✅
- Backend: `http://myapi.com` ❌ (won't work with HTTPS frontend)

### Check 3: No Trailing Slashes
```bash
# Good
CORS_ALLOWED_ORIGINS=https://myapp.com,http://localhost:5173

# Bad (trailing slashes)
CORS_ALLOWED_ORIGINS=https://myapp.com/,http://localhost:5173/
```

---

## Common Scenarios

### Scenario 1: Netlify Frontend + Render Backend
```bash
# Backend .env
CORS_ALLOWED_ORIGINS=https://my-chat-game.netlify.app

# Frontend .env
VITE_BACKEND_URL=https://my-backend.onrender.com
```

### Scenario 2: Both on Same Server, Different Ports
```bash
# Backend .env
CORS_ALLOWED_ORIGINS=http://your-server-ip:3000

# Frontend .env
VITE_BACKEND_URL=http://your-server-ip:8000
```

### Scenario 3: Custom Domain with Nginx
```bash
# Backend .env
CORS_ALLOWED_ORIGINS=https://chatgame.com

# Frontend .env
VITE_BACKEND_URL=https://api.chatgame.com
```

