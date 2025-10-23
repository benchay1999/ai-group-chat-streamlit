# Deploy to Streamlit Cloud (All-in-One Solution)

## Overview

This guide shows you how to deploy both the backend and frontend together on Streamlit Cloud using the `deploy.py` script. **No separate backend hosting needed!**

## ✅ Advantages

- 🎯 **Single deployment** - Backend and frontend in one place
- 💰 **Free** - No need for separate backend hosting
- 🚀 **Easy** - Just push to GitHub and deploy
- 🔒 **Secure** - Backend only accessible from frontend (localhost)
- 📦 **Simple** - One repository, one deployment

## 📋 Prerequisites

- GitHub account
- Streamlit Cloud account (free at https://share.streamlit.io)
- OpenAI API key

## 🚀 Deployment Steps

### Step 1: Prepare Your Repository

1. **Make sure you have the required files:**
   - ✅ `deploy.py` (main entry point)
   - ✅ `streamlit_app.py` (frontend)
   - ✅ `backend/main.py` (backend)
   - ✅ `backend/config.py`
   - ✅ `backend/langgraph_game.py`
   - ✅ `backend/langgraph_state.py`
   - ✅ `requirements.txt` (all dependencies)

2. **Create `.gitignore` if not exists:**
   ```
   __pycache__/
   *.py[cod]
   .env
   .streamlit/secrets.toml
   group-chat-stats/
   ```

3. **Push to GitHub:**
   ```bash
   cd /home/wschay/group-chat
   git init
   git add .
   git commit -m "Deploy with combined backend+frontend"
   git branch -M main
   git remote add origin https://github.com/YOUR_USERNAME/YOUR_REPO.git
   git push -u origin main
   ```

### Step 2: Deploy to Streamlit Cloud

1. **Go to https://share.streamlit.io**

2. **Click "New app"**

3. **Configure the deployment:**
   - **Repository:** Select your GitHub repository
   - **Branch:** main
   - **Main file path:** `deploy.py` ⚠️ **IMPORTANT: Use deploy.py, not streamlit_app.py**
   - **App URL:** Choose your preferred subdomain (e.g., `ai-group-chat-dev`)

4. **Click "Advanced settings"**

5. **Add secrets (Environment variables):**
   Click on "Secrets" and add your API keys in TOML format:
   ```toml
   OPENAI_API_KEY = "sk-your-openai-api-key-here"
   
   # Optional: if using Anthropic
   ANTHROPIC_API_KEY = "sk-ant-your-anthropic-key-here"
   
   # Optional: override default model
   AI_MODEL_PROVIDER = "openai"
   AI_MODEL_NAME = "gpt-4o-mini"
   ```

6. **Click "Deploy!"**

7. **Wait 3-5 minutes** for the app to build and deploy

### Step 3: Verify Deployment

1. **Check the logs** during deployment:
   - Should see: `🚀 Starting FastAPI backend on port 8000...`
   - Should see: `✅ Backend is ready on port 8000`
   - Should see: `🎨 Starting Streamlit frontend...`

2. **Once deployed, visit your app URL**

3. **Check the health indicator:**
   - Should see "✅ Server Online" in the sidebar
   - If you see "❌ Server Offline", check the logs for errors

4. **Test the functionality:**
   - Try creating a room
   - Try joining a room
   - Send messages and vote

## 🔧 Configuration

### Environment Variables (Streamlit Secrets)

You can configure the game through Streamlit secrets:

```toml
# Required
OPENAI_API_KEY = "sk-..."

# Optional
ANTHROPIC_API_KEY = "sk-ant-..."
AI_MODEL_PROVIDER = "openai"  # or "anthropic"
AI_MODEL_NAME = "gpt-4o-mini"
AI_TEMPERATURE = "0.8"

# Game settings
NUM_AI_PLAYERS = "4"
DISCUSSION_TIME = "180"  # seconds
VOTING_TIME = "60"  # seconds
ROUNDS_TO_WIN = "3"
```

### How It Works

The `deploy.py` script:

1. Finds a free port (usually 8000) for the backend
2. Sets `BACKEND_URL=http://127.0.0.1:8000` environment variable
3. Starts FastAPI backend in a background thread
4. Waits for backend to be ready (health check)
5. Starts Streamlit frontend in the main thread
6. Frontend connects to backend via localhost (same container)

## 🐛 Troubleshooting

### "Server Offline" message

**Cause:** Backend failed to start or crashed

**Solutions:**
1. Check deployment logs for errors
2. Verify `OPENAI_API_KEY` is set in secrets
3. Check if all dependencies are in `requirements.txt`
4. Look for Python errors in the logs
5. Try rebooting the app (Settings → Reboot)

### Import errors during deployment

**Cause:** Missing dependencies

**Solution:**
Add missing packages to `requirements.txt` and redeploy

### Backend port already in use

**Cause:** The `deploy.py` script tries ports 8000-8009

**Solution:**
The script automatically finds a free port. If all ports are in use (unlikely), check logs.

### WebSocket connection errors

**Cause:** Backend WebSocket endpoint not accessible

**Solution:**
1. This is expected on Streamlit Cloud (WebSockets have limitations)
2. The app uses HTTP polling instead (already configured)
3. No action needed - the app will work fine

### Slow response times

**Cause:** Free tier resource limits or AI API rate limits

**Solutions:**
1. Streamlit Cloud free tier has limited resources
2. Consider upgrading for production use
3. Optimize AI calls (already using async processing)
4. Use faster models (gpt-3.5-turbo or gpt-4o-mini)

### App crashes after some time

**Cause:** Memory limits on free tier

**Solutions:**
1. Monitor resource usage in Streamlit Cloud dashboard
2. Consider upgrading to a paid plan
3. Optimize memory usage (clear old rooms periodically)

## 📊 Monitoring

### View Logs

1. Go to https://share.streamlit.io
2. Click on your app
3. Click "Manage app"
4. View real-time logs

### Check Health

Visit: `https://your-app.streamlit.app/` and look for:
- "✅ Server Online" in the sidebar
- Room creation and joining works
- Messages send successfully

### Backend API Documentation

The backend API docs are not publicly accessible (only via localhost), but you can test endpoints through the Streamlit UI.

## 🔄 Updates and Redeployment

### Automatic Redeployment

Streamlit Cloud automatically redeploys when you push to GitHub:

```bash
git add .
git commit -m "Update game logic"
git push origin main
```

Wait 2-3 minutes for Streamlit Cloud to rebuild and redeploy.

### Manual Redeployment

1. Go to https://share.streamlit.io
2. Click on your app
3. Click "Reboot app"

### Updating Secrets

1. Go to app settings
2. Click on "Secrets"
3. Update the TOML configuration
4. Click "Save"
5. Reboot the app

## 🌐 Custom Domain (Optional)

Streamlit Cloud allows custom domains on paid plans:

1. Upgrade to a paid plan
2. Go to app settings
3. Add your custom domain
4. Update DNS records as instructed

## 📈 Scaling Considerations

### Free Tier Limits

- CPU: Limited
- Memory: ~1GB
- Concurrent users: Limited
- Uptime: Sleeps after inactivity

### For Production

Consider:
- Upgrading to Streamlit Cloud paid tier
- Or deploying backend separately for better scalability
- Using a database instead of in-memory storage
- Adding Redis for session management
- Load balancing for high traffic

## 🔐 Security Best Practice

### Do:
- ✅ Use Streamlit secrets for API keys
- ✅ Keep API keys private
- ✅ Use environment variables for configuration
- ✅ Validate user inputs
- ✅ Rate limit API calls

### Don't:
- ❌ Commit API keys to git
- ❌ Hardcode sensitive data
- ❌ Expose internal endpoints publicly
- ❌ Skip input validation

## 📝 File Structure

```
/home/wschay/group-chat/
├── deploy.py                    # 🎯 Main entry point (use this!)
├── streamlit_app.py             # Frontend UI
├── requirements.txt             # All dependencies
├── backend/
│   ├── main.py                  # FastAPI backend
│   ├── config.py                # Configuration
│   ├── langgraph_game.py        # Game logic
│   └── langgraph_state.py       # State definitions
├── .gitignore                   # Files to ignore
└── DEPLOY_WITH_STREAMLIT_CLOUD.md  # This file
```

## ✅ Deployment Checklist

Before deploying:

- [ ] All files committed to GitHub
- [ ] `deploy.py` exists in root directory
- [ ] `requirements.txt` has all dependencies
- [ ] `.gitignore` excludes sensitive files
- [ ] Repository is public or connected to Streamlit Cloud
- [ ] OpenAI API key is ready

During deployment on Streamlit Cloud:

- [ ] Repository selected
- [ ] Main file path set to `deploy.py`
- [ ] Secrets added (OPENAI_API_KEY)
- [ ] Deploy button clicked

After deployment:

- [ ] Logs show backend started successfully
- [ ] Logs show frontend started successfully
- [ ] App URL loads correctly
- [ ] "✅ Server Online" shows in sidebar
- [ ] Can create and join rooms
- [ ] Can send messages
- [ ] Can vote
- [ ] Game completes successfully

## 🎉 Success!

Once deployed, your app will be available at:
`https://your-app-name.streamlit.app/`

Share the URL with others to play together!

## 📞 Support

If you encounter issues:

1. Check the logs in Streamlit Cloud dashboard
2. Review this troubleshooting guide
3. Check `DEPLOYMENT_GUIDE.md` for alternative deployment methods
4. Verify all environment variables are set correctly
5. Try rebooting the app

## 🔄 Switching Deployment Methods

If you later want to deploy backend separately:

1. Deploy backend to Render/Railway/Heroku (see `DEPLOYMENT_GUIDE.md`)
2. Change main file path back to `streamlit_app.py`
3. Add `BACKEND_URL` to Streamlit secrets with your backend URL
4. Redeploy

---

**You're all set!** 🚀 Your game should now be live and fully functional on Streamlit Cloud.

