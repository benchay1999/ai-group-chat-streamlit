# Netlify Deployment - Quick Start

## TL;DR - 5 Minute Deployment

### Step 1: Go to Netlify
1. Visit https://app.netlify.com/
2. Sign up/Login (use GitHub for easiest setup)

### Step 2: Deploy Your Site
1. Click **"Add new site"** → **"Deploy manually"**
2. **Drag the `dist/` folder** from:
   ```
   /home/wschay/ai-group-chat-streamlit/frontend/dist/
   ```
   onto the Netlify upload area
3. Wait 20 seconds
4. Your site is live! 🎉

### Step 3: Configure Backend Connection
1. In Netlify dashboard → **"Site settings"** → **"Environment variables"**
2. Add variable:
   - **Key**: `VITE_BACKEND_URL`
   - **Value**: Your backend URL (e.g., `https://your-backend.com`)
3. Go to **"Deploys"** → **"Trigger deploy"** → **"Clear cache and deploy site"**

### Step 4: Test Your Site
Open your Netlify URL (e.g., `https://random-name.netlify.app`) and verify:
- ✅ Lobby page loads with "Group Chat" title
- ✅ Can create a room
- ✅ Can join a room
- ✅ Can send chat messages

---

## What You Need Ready

✅ **Your build folder**: `/home/wschay/ai-group-chat-streamlit/frontend/dist/`
✅ **Backend URL**: Where your API is running (localhost:8000 or deployed URL)

---

## Current Build Status

✅ **Build completed successfully!**

Your production files are in:
```
frontend/dist/
├── index.html          (0.39 kB)
├── _redirects          (for React Router)
└── assets/
    ├── index-*.css     (23.82 kB)
    └── index-*.js      (243.07 kB)
```

Total size: **~244 kB** (79 kB gzipped)

---

## Backend URL Options

### Option 1: Local Backend (Testing Only)
```
http://localhost:8000
```
⚠️ Only works on your computer

### Option 2: Ngrok Tunnel (Quick Demo)
```bash
# In another terminal:
cd backend
ngrok http 8000

# Use the URL ngrok gives you:
# https://abc123.ngrok.io
```
⚠️ URL changes each time you restart

### Option 3: Deploy Backend (Production)
Best option - deploy backend to:
- **Render.com** (recommended, free tier)
- **Railway.app** 
- **Fly.io**

Then use that permanent URL.

---

## Troubleshooting

### Issue: "Server Offline" in lobby

**Cause**: Backend not running or URL wrong

**Fix**:
1. Check backend is running
2. Check `VITE_BACKEND_URL` in Netlify environment variables
3. Redeploy after fixing

### Issue: Routes show 404

**Cause**: React Router needs special config

**Fix**: Already done! The `_redirects` file is included.

### Issue: CORS Error

**Cause**: Backend blocking Netlify's requests

**Fix**: Add Netlify URL to backend CORS:
```python
# backend/main.py
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "https://your-site.netlify.app"  # Add this
    ],
    # ... rest of config
)
```

---

## Next Steps After Deployment

1. **Customize site name**:
   - Netlify dashboard → Site settings → Change site name
   - From: `random-name-123456.netlify.app`
   - To: `group-chat-app.netlify.app`

2. **Deploy backend** (if you haven't):
   - Don't rely on localhost for production!
   - Deploy to Render/Railway/Fly.io
   - Update `VITE_BACKEND_URL`

3. **Share your app**:
   - Send the URL to friends
   - Test with multiple players
   - Have fun! 🎮

---

## Full Documentation

For detailed instructions, see: **`NETLIFY_DEPLOYMENT_GUIDE.md`**

Includes:
- Git-based deployment (auto-deploy on push)
- Custom domain setup
- HTTPS configuration
- Performance optimization
- Complete troubleshooting guide

---

## Quick Commands Reference

```bash
# Rebuild (if you make changes)
cd /home/wschay/ai-group-chat-streamlit/frontend
npm run build

# Preview locally before deploying
npm run preview  # Opens at http://localhost:4173

# The dist/ folder is what you upload to Netlify!
```

---

**You're all set!** Your Group Chat app is ready to deploy to Netlify. Just drag the `dist/` folder and you're live in 30 seconds! 🚀

