# Deployment Guide: ngrok + Netlify

A beginner-friendly guide to deploying Human Hunter using ngrok (for backend) and Netlify (for frontend).

## Overview

This deployment strategy keeps your backend running locally while making it accessible online, and hosts your frontend on Netlify's free tier.

```
┌────────────────┐        ┌─────────┐        ┌──────────┐
│  Your Computer │◄───────│  ngrok  │◄───────│ Netlify  │
│  Backend :8000 │  Tunnel│         │  HTTPS │ Frontend │
└────────────────┘        └─────────┘        └──────────┘
```

**Why this approach?**
- ✅ Fast to set up (under 30 minutes)
- ✅ Backend runs on your machine (full control, easy debugging)
- ✅ Frontend on CDN (fast, reliable)
- ✅ Stable with ngrok paid plan ($20/month for permanent URL)

**Recommended for Production**: Use ngrok's paid plan ($20/month) for a stable, permanent URL without interruptions or warning pages.

---

## Part 1: Setting Up ngrok

ngrok creates a secure tunnel from the internet to your local backend.

> **💡 Important for Stability:** While you can start with ngrok's free tier to test, **we strongly recommend upgrading to the paid plan ($20/month)** for a stable, production-ready app. The paid plan provides a permanent URL, removes warning pages, and ensures reliability for your users.

### Step 1: Sign Up for ngrok

1. Go to https://ngrok.com
2. Click "Sign up" (top right)
3. Sign up with GitHub, Google, or email (free account)
4. After signing up, you'll land on the dashboard

### Step 2: Get Your Auth Token

1. On the ngrok dashboard, go to **"Your Authtoken"** section
2. Copy your authtoken (looks like: `2abc123def456...`)
3. Keep this handy - you'll need it in the next step

### Step 3: Install ngrok

**Option A: Already Installed (Check First)**

If ngrok is already in your project directory:

```bash
# From project root
./ngrok --version
```

If this works, skip to Step 4!

**Option B: Download ngrok**

```bash
# Linux/macOS
wget https://bin.equinox.io/c/bNyj1mQVY4c/ngrok-v3-stable-linux-amd64.tgz
tar -xvzf ngrok-v3-stable-linux-amd64.tgz

# Or visit https://ngrok.com/download for other systems
```

> **📝 Side Note:** If you're having trouble installing ngrok, this repository already includes an ngrok binary. Simply use `./ngrok` from the project root directory instead of installing a new copy.

### Step 4: Authenticate ngrok (One-Time Setup)

```bash
# Replace YOUR_AUTH_TOKEN with the token from Step 2
./ngrok config add-authtoken YOUR_AUTH_TOKEN
```

You should see: `Authtoken saved to configuration file`

### Step 5: Start Your Backend

Before starting ngrok, make sure your backend is running:

```bash
# In terminal 1
cd backend
pip install -r requirements.txt
python main.py
```

Backend should be running on `http://localhost:8000`

### Step 6: Start ngrok Tunnel

In a **new terminal window**:

```bash
# In terminal 2
./ngrok http 8000
```

You'll see output like:

```
ngrok                                                                     

Session Status                online
Account                       your-email@example.com
Version                       3.x.x
Region                        United States (us)
Latency                       20ms
Web Interface                 http://127.0.0.1:4040
Forwarding                    https://abc123def456.ngrok-free.app -> http://localhost:8000

Connections                   ttl     opn     rt1     rt5     p50     p90
                              0       0       0.00    0.00    0.00    0.00
```

### Step 7: Copy Your ngrok URL

Look for the "Forwarding" line:
```
Forwarding    https://abc123def456.ngrok-free.app -> http://localhost:8000
```

Copy the HTTPS URL: `https://abc123def456.ngrok-free.app`

### Step 8: Test Your ngrok URL

```bash
# In terminal 3 (or browser)
curl https://YOUR-NGROK-URL.ngrok-free.app/health
```

You should see: `{"status":"healthy"}`

**Important Notes:**
- Keep the ngrok terminal open! Closing it stops the tunnel
- Free tier URL changes each time you restart ngrok
- There's a banner on free tier (users click "Visit Site" to continue)

### Step 9: Upgrade to ngrok Paid Plan (Recommended for Stability)

**For a stable, production-ready app, upgrade to ngrok's paid plan ($20/month).**

**Why upgrade?**
- ✅ **Permanent URL**: Your URL never changes, even after restarts
- ✅ **No warning page**: Users go directly to your app
- ✅ **More reliability**: Better uptime and connection stability
- ✅ **Custom domains**: Use your own domain (optional)
- ✅ **Better support**: Priority customer support

**How to upgrade:**

1. Go to https://dashboard.ngrok.com/billing/subscription
2. Select the "Personal" or "Pro" plan ($20/month)
3. Add payment information
4. After upgrading, reserve a permanent domain:
   - Go to: https://dashboard.ngrok.com/cloud-edge/domains
   - Click "New Domain"
   - Choose a subdomain (e.g., `your-app.ngrok.app`)
5. Start ngrok with your reserved domain:
   ```bash
   ./ngrok http --domain=your-app.ngrok.app 8000
   ```

**Your URL is now permanent!** Use `https://your-app.ngrok.app` in Netlify's `VITE_BACKEND_URL` and never update it again.

**Note:** The free tier is fine for testing, but for a stable app that others will use regularly, the paid plan is highly recommended.

---

## Part 2: Deploying Frontend to Netlify

Netlify hosts static sites for free with automatic deployments from GitHub.

### Step 1: Push Code to GitHub

If you haven't already:

```bash
git init
git add .
git commit -m "Initial commit"
git branch -M main
git remote add origin https://github.com/YOUR-USERNAME/YOUR-REPO.git
git push -u origin main
```

### Step 2: Sign Up for Netlify

1. Go to https://netlify.com
2. Click "Sign up" (top right)
3. Choose "Sign up with GitHub" (easiest)
4. Authorize Netlify to access your GitHub repos

### Step 3: Create New Site

1. Click "Add new site" → "Import an existing project"
2. Choose "GitHub"
3. Authorize Netlify to access your repositories (if prompted)
4. Search for and select your project repository

### Step 4: Configure Build Settings

Netlify will auto-detect settings, but verify:

| Setting | Value |
|---------|-------|
| **Branch to deploy** | `main` |
| **Base directory** | `frontend` |
| **Build command** | `npm run build` |
| **Publish directory** | `frontend/dist` |

### Step 5: Add Environment Variables

Before deploying, add your backend URL:

1. Click "Show advanced" → "New variable"
2. Add:
   - **Key**: `VITE_BACKEND_URL`
   - **Value**: Your ngrok URL (from Part 1, Step 7)
   
   Example: `https://abc123def456.ngrok-free.app`

### Step 6: Deploy Site

1. Click "Deploy site"
2. Wait 2-3 minutes for build to complete
3. Your site will be live at: `https://random-name-12345.netlify.app`

### Step 7: Update Backend CORS

Your backend needs to allow requests from Netlify:

1. Open your `.env` file
2. Update `CORS_ALLOWED_ORIGINS`:

```env
CORS_ALLOWED_ORIGINS=https://your-site-name.netlify.app,http://localhost:5173
```

3. Restart your backend:

```bash
# In terminal 1 (Ctrl+C to stop, then restart)
python backend/main.py
```

### Step 8: Test Your Deployed Site

1. Open your Netlify URL: `https://your-site-name.netlify.app`
2. Click "Create Room" or "Join Room"
3. Start playing!

---

## Part 3: Customizing Your Netlify Site

### Change Site Name

1. Go to Netlify dashboard
2. Click on your site
3. Go to "Site settings" → "Site details"
4. Click "Change site name"
5. Enter a custom name (e.g., `human-hunter-game`)
6. Your site is now: `https://human-hunter-game.netlify.app`

### Add Custom Domain (Optional)

1. Buy a domain from Namecheap, Google Domains, etc.
2. In Netlify: "Domain settings" → "Add custom domain"
3. Follow instructions to update DNS settings
4. Netlify provides free SSL automatically!

---

## Daily Usage

### Starting Everything

1. **Start Backend** (Terminal 1):
   ```bash
   cd backend
   python main.py
   ```

2. **Start ngrok** (Terminal 2):
   
   **If using free tier:**
   ```bash
   ./ngrok http 8000
   ```
   
   **If using paid plan (recommended):**
   ```bash
   ./ngrok http --domain=your-reserved-domain.ngrok.app 8000
   ```

3. **Update Netlify** (only if using free tier and URL changed):
   - Go to Netlify dashboard
   - Site settings → Environment variables
   - Update `VITE_BACKEND_URL` with new ngrok URL
   - Trigger redeploy: Deploys → Trigger deploy → Deploy site
   - **Note:** Paid plan users skip this step - your URL never changes!

4. **Access your game**: Visit `https://your-site-name.netlify.app`

### Stopping Everything

1. Stop ngrok: Press `Ctrl+C` in terminal 2
2. Stop backend: Press `Ctrl+C` in terminal 1

---

## Troubleshooting

### ngrok Issues

**Problem: "command not found: ngrok"**
```bash
# Make sure you're in the project root
pwd

# Try with ./
./ngrok http 8000
```

**Problem: "authentication failed"**
```bash
# Re-add your auth token
./ngrok config add-authtoken YOUR_TOKEN
```

**Problem: "tunnel expired"**
- Free ngrok tunnels don't expire, but the URL changes on restart
- Use ngrok's paid plan ($20/month) for permanent URLs and better stability

### Netlify Issues

**Problem: "Build failed"**

Check the build logs:
1. In Netlify dashboard, click your site
2. Go to "Deploys"
3. Click the failed deploy
4. Read the error message

Common fixes:
```bash
# Missing dependencies
cd frontend
npm install
git add package-lock.json
git commit -m "Add package-lock.json"
git push
```

**Problem: "Cannot connect to backend"**

1. Check ngrok is running: `./ngrok http 8000`
2. Check backend is running: Visit `http://localhost:8000/health`
3. Check Netlify env variable: Site settings → Environment variables → `VITE_BACKEND_URL`
4. Redeploy: Deploys → Trigger deploy → Deploy site

**Problem: "CORS error" in browser console**

Update your backend `.env`:
```env
CORS_ALLOWED_ORIGINS=https://your-netlify-site.netlify.app,http://localhost:5173
```

Restart backend after changing `.env`.

### General Issues

**Problem: ngrok URL keeps changing**

Options:
1. **Free**: Update Netlify env variable each time (takes 2 minutes) - **not recommended for production**
2. **Paid (Recommended)**: Get ngrok paid plan ($20/month) for permanent URL and stability
3. **Alternative**: Deploy backend to Railway/Render ($5-10/month)

**Problem: Players see ngrok warning page**

Free ngrok shows a warning. Players must click "Visit Site" to continue. To remove:
- **Recommended**: Upgrade to ngrok paid plan ($20/month) for professional experience
- **Alternative**: Deploy backend to Railway/Render instead ($5-10/month)

---

## Updating Your Deployment

### After Code Changes

**Frontend changes**:
```bash
git add .
git commit -m "Update frontend"
git push
# Netlify auto-deploys in ~2 minutes
```

**Backend changes**:
```bash
# Just restart your backend
# In terminal 1 (Ctrl+C then restart)
python backend/main.py
```

### Automatic Netlify Deploys

Netlify automatically deploys when you push to GitHub:
1. Make changes locally
2. Commit and push to GitHub
3. Netlify detects the push
4. Automatically builds and deploys
5. Live in 2-3 minutes!

---

## Cost Breakdown

| Service | Cost | Notes |
|---------|------|-------|
| **ngrok Free** | $0/month | URL changes on restart, warning page |
| **ngrok Paid** | $20/month | Permanent URL, no warning, **recommended for stability** |
| **Netlify** | $0/month | 100GB bandwidth/month |
| **Total (Free)** | $0/month | Good for testing only |
| **Total (Stable)** | $20/month | **Recommended for production use** |

---

## Alternative: Full Cloud Deployment

If you prefer not to run the backend on your local machine (even with ngrok paid plan):

1. **Backend**: Deploy to Railway ($5/month) or Render ($7/month)
2. **Frontend**: Keep on Netlify (free)
3. **Database**: PostgreSQL on Supabase (free) or Neon (free)

**Comparison:**
- **ngrok + Local Backend ($20/month)**: Full control, easy debugging, runs on your machine
- **Cloud Backend ($5-10/month)**: Always online, no local machine needed, requires cloud setup

See [markdowns/DEPLOYMENT.md](markdowns/DEPLOYMENT.md) for cloud deployment guides.

---

## Need Help?

- **ngrok docs**: https://ngrok.com/docs
- **Netlify docs**: https://docs.netlify.com
- **Project docs**: See [README.md](README.md) and [TUTORIAL.md](TUTORIAL.md)
- **Backend logs**: Check terminal 1 for errors
- **Frontend logs**: Check browser DevTools → Console

---

## Quick Reference

```bash
# Start backend
cd backend && python main.py

# Start ngrok (new terminal)
./ngrok http 8000

# Get ngrok URL
# Look for "Forwarding" line in ngrok output

# Update Netlify env variable
# Dashboard → Site settings → Environment variables → VITE_BACKEND_URL

# Test backend
curl https://YOUR-NGROK-URL/health

# Push frontend changes
git add . && git commit -m "Update" && git push
```

Happy deploying! 🚀

