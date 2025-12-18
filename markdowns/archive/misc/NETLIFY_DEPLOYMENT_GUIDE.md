# Netlify Deployment Guide - Group Chat React Frontend

Complete step-by-step instructions for deploying the Group Chat React frontend to Netlify.

## Prerequisites

✅ You have completed:
- React frontend built successfully (`npm run build`)
- `dist/` folder exists in `/frontend/` directory
- Backend API is accessible (local or deployed)

## Deployment Options

You have **two main options** for deploying to Netlify:

1. **Option A: Manual Deployment** (Drag & Drop) - Fastest, good for testing
2. **Option B: Git-based Deployment** - Automated, best for production

---

## Option A: Manual Deployment (Drag & Drop)

### Step 1: Create Netlify Account

1. Go to https://www.netlify.com/
2. Click **"Sign up"** (top right)
3. Choose sign-up method:
   - **GitHub** (recommended if you use GitHub)
   - **GitLab**
   - **Bitbucket**
   - **Email** (manual signup)
4. Complete the registration process
5. Verify your email if required

### Step 2: Prepare Build for Deployment

The build is already done! Verify it exists:

```bash
cd /home/wschay/ai-group-chat-streamlit/frontend
ls -la dist/
```

You should see:
```
dist/
├── index.html
└── assets/
    ├── index-[hash].css
    └── index-[hash].js
```

### Step 3: Deploy to Netlify (Drag & Drop)

#### 3.1: Access Netlify Dashboard

1. Log in to https://app.netlify.com/
2. You'll see your Netlify dashboard

#### 3.2: Deploy Site

**Method 1: Drag & Drop (Easiest)**

1. Click **"Add new site"** → **"Deploy manually"**
2. **Drag the entire `dist/` folder** onto the upload area
   
   ```bash
   # Or compress first (optional):
   cd /home/wschay/ai-group-chat-streamlit/frontend
   tar -czf dist.tar.gz dist/
   ```

3. Wait for upload (usually 10-30 seconds)
4. Netlify will automatically:
   - Upload your files
   - Deploy to a random URL like `random-name-123456.netlify.app`
   - Show you the live site

**Method 2: Browse to Upload**

1. Click **"Add new site"** → **"Deploy manually"**
2. Click **"Browse to upload"**
3. Navigate to `/home/wschay/ai-group-chat-streamlit/frontend/dist`
4. Select all files and upload
5. Wait for deployment

#### 3.3: Your Site is Live! 🎉

After deployment, you'll see:
- **Site URL**: `https://random-name-123456.netlify.app`
- **Deployment status**: Published
- **Last published**: Timestamp

### Step 4: Configure Environment Variables

Your React app needs to connect to your backend API.

#### 4.1: Set Backend URL

1. In Netlify dashboard, click on your site
2. Go to **"Site settings"**
3. Click **"Environment variables"** (left sidebar)
4. Click **"Add a variable"** → **"Add a single variable"**
5. Enter:
   - **Key**: `VITE_BACKEND_URL`
   - **Value**: Your backend URL (see options below)
   - **Scopes**: Select "All" or specific branches

**Backend URL Options:**

**Option 1: Local Backend (for testing)**
```
http://localhost:8000
```
⚠️ **Note**: This only works when testing locally. Remote users won't be able to access localhost.

**Option 2: Ngrok Tunnel (temporary)**
```
https://abc123.ngrok.io
```
✅ Good for: Quick demos, testing
❌ Limitations: URL changes when restarted

**Option 3: Deployed Backend (production)**
```
https://your-backend.onrender.com
https://your-backend.railway.app
https://your-backend.fly.io
```
✅ Good for: Production deployment
✅ Persistent URL

#### 4.2: Redeploy After Setting Variables

1. Go to **"Deploys"** tab
2. Click **"Trigger deploy"** → **"Clear cache and deploy site"**
3. Wait 30-60 seconds for redeployment
4. Your site will now use the new environment variable

### Step 5: Customize Site Name (Optional)

Instead of `random-name-123456.netlify.app`:

1. Go to **"Site settings"**
2. Click **"Change site name"**
3. Enter your desired name: `group-chat-app` (if available)
4. Your new URL: `https://group-chat-app.netlify.app`

---

## Option B: Git-Based Deployment (Automated)

### Step 1: Push Code to Git Repository

#### 1.1: Initialize Git (if not done)

```bash
cd /home/wschay/ai-group-chat-streamlit
git init
git add .
git commit -m "Initial commit: Group Chat React frontend"
```

#### 1.2: Create GitHub Repository

1. Go to https://github.com/new
2. Create repository:
   - **Name**: `group-chat-app`
   - **Visibility**: Public or Private
   - **Don't** initialize with README (you already have code)
3. Click **"Create repository"**

#### 1.3: Push to GitHub

```bash
# Add remote
git remote add origin https://github.com/YOUR_USERNAME/group-chat-app.git

# Push code
git branch -M main
git push -u origin main
```

### Step 2: Connect Netlify to GitHub

#### 2.1: Import from Git

1. Log in to https://app.netlify.com/
2. Click **"Add new site"** → **"Import an existing project"**
3. Choose **"Deploy with GitHub"**
4. Authorize Netlify to access your GitHub account
5. Select your repository: `group-chat-app`

#### 2.2: Configure Build Settings

Netlify will auto-detect settings, but verify:

**Build settings:**
- **Base directory**: `frontend`
- **Build command**: `npm run build`
- **Publish directory**: `frontend/dist`

**Advanced options:**
- **Node version**: Click "Show advanced" → Environment variables:
  - Key: `NODE_VERSION`
  - Value: `18`

#### 2.3: Add Environment Variables

Before deploying, add your backend URL:

1. Click **"Add environment variables"**
2. Add:
   - **Key**: `VITE_BACKEND_URL`
   - **Value**: Your backend URL (e.g., `https://your-backend.onrender.com`)

#### 2.4: Deploy

1. Click **"Deploy site"**
2. Watch the deployment logs (this may take 2-5 minutes)
3. Once complete, you'll see: **"Site is live ✓"**
4. Your URL: `https://random-name.netlify.app`

### Step 3: Automatic Deployments

With Git-based deployment:

✅ **Every push to `main` branch** triggers automatic deployment
✅ **Pull request previews** (optional, can enable in settings)
✅ **Rollback** to any previous deployment

To update your site:
```bash
# Make changes
git add .
git commit -m "Update feature X"
git push origin main

# Netlify automatically rebuilds and deploys!
```

---

## Post-Deployment Configuration

### 1. Custom Domain (Optional)

#### 1.1: Buy a Domain

Purchase from:
- Namecheap
- GoDaddy
- Google Domains
- etc.

#### 1.2: Connect to Netlify

1. In Netlify, go to **"Domain settings"**
2. Click **"Add custom domain"**
3. Enter your domain: `groupchat.com`
4. Follow instructions to update DNS:

**Option A: Use Netlify DNS (Recommended)**
- Point nameservers to Netlify
- Netlify manages everything

**Option B: Keep Current DNS**
- Add CNAME record: `www` → `your-site.netlify.app`
- Add A record: `@` → Netlify IP

#### 1.3: Enable HTTPS

1. Netlify automatically provisions SSL certificate (Let's Encrypt)
2. Wait 10-60 minutes for certificate
3. Force HTTPS redirect:
   - Go to **"Domain settings"**
   - Enable **"Force HTTPS"**

### 2. Site Configuration (_redirects)

Create a `_redirects` file to handle React Router:

```bash
cd /home/wschay/ai-group-chat-streamlit/frontend/public
```

If `public/` doesn't exist, create it:
```bash
mkdir -p /home/wschay/ai-group-chat-streamlit/frontend/public
```

Create `_redirects` file:
```bash
cat > /home/wschay/ai-group-chat-streamlit/frontend/public/_redirects << 'EOF'
# Redirect all routes to index.html for React Router
/*    /index.html   200
EOF
```

Then rebuild and redeploy:
```bash
cd /home/wschay/ai-group-chat-streamlit/frontend
npm run build

# Manual: Upload dist/ to Netlify again
# OR
# Git: Commit and push (automatic deployment)
```

### 3. Performance Optimization

#### 3.1: Enable Asset Optimization

1. Go to **"Site settings"** → **"Build & deploy"** → **"Post processing"**
2. Enable:
   - ✅ **Bundle CSS**
   - ✅ **Minify CSS**
   - ✅ **Minify JavaScript**
   - ✅ **Pretty URLs** (optional)

#### 3.2: Enable Caching

Already enabled by default! Netlify automatically caches static assets.

### 4. Analytics (Optional)

Enable Netlify Analytics to track visitors:

1. Go to **"Site settings"** → **"Analytics"**
2. Click **"Enable analytics"**
3. Cost: $9/month (optional)

---

## Testing Your Deployed Site

### 1. Basic Functionality Test

1. Open your Netlify URL: `https://your-site.netlify.app`
2. Verify:
   - ✅ Lobby page loads
   - ✅ "Group Chat" title appears
   - ✅ Server status shows (green if backend is running)

### 2. Full Flow Test

#### Test A: Room Creation
1. Click **"Create Room"**
2. Configure settings
3. Click **"Create"**
4. Should navigate to waiting page
5. Should see your player number

#### Test B: Room Joining
1. Open in another browser/incognito
2. See the room in lobby
3. Click **"Join Room"**
4. Should get different player number
5. Game should start when room is full

#### Test C: Game Play
1. Type messages in chat
2. Messages should appear
3. Wait for voting phase
4. Cast votes
5. See game over screen

### 3. Backend Connection Test

If site doesn't connect to backend:

1. Open browser console (F12)
2. Check for errors:
   - ❌ `ERR_CONNECTION_REFUSED` → Backend not running
   - ❌ `CORS error` → Backend CORS settings need update
   - ❌ `404 Not Found` → Wrong backend URL

3. Fix CORS on backend:
   ```python
   # In backend/main.py
   app.add_middleware(
       CORSMiddleware,
       allow_origins=[
           "http://localhost:5173",
           "https://your-site.netlify.app"  # Add your Netlify URL
       ],
       allow_credentials=True,
       allow_methods=["*"],
       allow_headers=["*"],
   )
   ```

---

## Troubleshooting

### Issue 1: "Site Not Found"

**Problem**: Netlify shows 404 error

**Solution**:
1. Check `dist/` folder was uploaded correctly
2. Verify `index.html` exists in root of deploy
3. Check deploy logs for errors

### Issue 2: Blank White Page

**Problem**: Site loads but shows nothing

**Solution**:
1. Check browser console (F12)
2. Look for JavaScript errors
3. Verify `VITE_BACKEND_URL` is set correctly
4. Check if assets loaded (Network tab)

### Issue 3: Routes Don't Work

**Problem**: Direct URLs like `/game` show 404

**Solution**:
1. Add `_redirects` file (see Post-Deployment Configuration)
2. Rebuild and redeploy

### Issue 4: Backend Connection Failed

**Problem**: "Server Offline" or connection errors

**Solutions**:

**A. Backend not accessible:**
```bash
# Test backend directly
curl https://your-backend.com/health

# If fails, backend is down or URL is wrong
```

**B. CORS issues:**
- Add Netlify URL to backend's allowed origins
- Redeploy backend

**C. Environment variable not set:**
- Check Netlify environment variables
- Redeploy after adding variables

### Issue 5: Old Version Still Showing

**Problem**: Changes not appearing after deploy

**Solution**:
1. Clear browser cache (Ctrl+Shift+R or Cmd+Shift+R)
2. Check deployment succeeded in Netlify
3. Try incognito/private browsing
4. Wait 2-3 minutes for CDN to update

---

## Deployment Checklist

Before going live, verify:

- [ ] Build completes successfully (`npm run build`)
- [ ] Backend is deployed and accessible
- [ ] `VITE_BACKEND_URL` environment variable is set
- [ ] CORS allows Netlify URL
- [ ] `_redirects` file added for React Router
- [ ] Custom domain configured (if using)
- [ ] HTTPS enabled
- [ ] Site tested in multiple browsers
- [ ] Mobile responsiveness checked
- [ ] All features work (create, join, chat, vote)

---

## Cost & Limits

### Netlify Free Tier

✅ **Included Free:**
- 100 GB bandwidth/month
- 300 build minutes/month
- Unlimited sites
- HTTPS (automatic)
- Deploy previews
- Serverless functions (125k requests/month)

❌ **Costs Extra:**
- Analytics: $9/month
- Extra bandwidth: $20 per 100 GB
- Extra build minutes: $7 per 500 minutes

### Typical Usage

For Group Chat app:
- **Bandwidth**: ~1 MB per user per session
- **100 GB** = ~100,000 user sessions
- **More than enough** for most use cases!

---

## Quick Reference Commands

```bash
# Build for production
cd /home/wschay/ai-group-chat-streamlit/frontend
npm run build

# Preview build locally
npm run preview

# Update and redeploy (Git method)
git add .
git commit -m "Update description"
git push origin main

# Manual redeploy (Drag & Drop method)
# Just drag dist/ folder to Netlify again
```

---

## Next Steps After Deployment

1. **Share your URL** 🎉
   - Your app is live at `https://your-site.netlify.app`
   - Share with friends to test multiplayer

2. **Monitor performance**
   - Check Netlify dashboard for traffic
   - Review deploy logs for errors

3. **Iterate and improve**
   - Make changes locally
   - Test with `npm run dev`
   - Build and redeploy when ready

4. **Deploy backend properly**
   - Don't rely on ngrok for production
   - Deploy to Render, Railway, or Fly.io
   - Update `VITE_BACKEND_URL` in Netlify

---

## Support Resources

- **Netlify Docs**: https://docs.netlify.com/
- **Community Forum**: https://answers.netlify.com/
- **Status Page**: https://www.netlifystatus.com/
- **Support**: support@netlify.com (or in-app chat)

---

## Summary

You now have a **complete deployment workflow** for your Group Chat React frontend on Netlify! 

**Quick Start:**
1. Upload `dist/` folder to Netlify (drag & drop)
2. Set `VITE_BACKEND_URL` environment variable
3. Redeploy
4. Test your live site
5. Share with the world! 🚀

Good luck with your deployment! 🎉

