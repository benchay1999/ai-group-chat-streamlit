# Deployment Guide for AI Group Chat Game

## Problem
Your Streamlit app is deployed to Streamlit Cloud (https://ai-group-chat-dev.streamlit.app/), but it can't connect to your FastAPI backend running on `localhost:8000` because:
- Streamlit Cloud is a remote server
- It can't access your local computer
- `localhost` on Streamlit Cloud refers to the Streamlit Cloud server, not your computer

## Solution: Deploy the Backend

You need to deploy your FastAPI backend to a cloud service and configure the Streamlit app to use that URL.

---

## Option 1: Deploy to Render.com (Recommended - Free Tier)

### Step 1: Prepare Your Backend

1. **Move requirements.txt to root** (or create a new one):

Create `/home/wschay/group-chat/requirements.txt`:
```txt
fastapi
uvicorn[standard]
openai
websockets
python-dotenv
langgraph
langchain
langchain-openai
langchain-core
```

2. **Create a `render.yaml` file** in the root:

```yaml
services:
  - type: web
    name: ai-group-chat-backend
    env: python
    buildCommand: pip install -r requirements.txt
    startCommand: uvicorn backend.main:app --host 0.0.0.0 --port $PORT
    envVars:
      - key: OPENAI_API_KEY
        sync: false
      - key: ANTHROPIC_API_KEY
        sync: false
```

### Step 2: Deploy to Render

1. **Push your code to GitHub** (if not already):
   ```bash
   git init
   git add .
   git commit -m "Prepare for deployment"
   git remote add origin <your-github-repo-url>
   git push -u origin main
   ```

2. **Sign up at [render.com](https://render.com)**

3. **Create a new Web Service:**
   - Click "New +" → "Web Service"
   - Connect your GitHub repository
   - Settings:
     - **Name:** ai-group-chat-backend
     - **Environment:** Python 3
     - **Build Command:** `pip install -r requirements.txt`
     - **Start Command:** `uvicorn backend.main:app --host 0.0.0.0 --port $PORT`
     - **Plan:** Free

4. **Add Environment Variables:**
   - Go to "Environment" tab
   - Add:
     - `OPENAI_API_KEY` = your-key
     - `ANTHROPIC_API_KEY` = your-key (if using Anthropic)

5. **Deploy!** Render will give you a URL like: `https://ai-group-chat-backend.onrender.com`

### Step 3: Update Streamlit Cloud Configuration

1. Go to [share.streamlit.io](https://share.streamlit.io)
2. Click on your app → ⚙️ Settings
3. Go to "Secrets" and add:
   ```toml
   BACKEND_URL = "https://ai-group-chat-backend.onrender.com"
   ```

4. Reboot the app

---

## Option 2: Deploy to Railway.app (Also Free Tier)

### Step 1: Prepare Backend

Same as Option 1 - ensure you have `requirements.txt` in the root.

### Step 2: Deploy to Railway

1. **Sign up at [railway.app](https://railway.app)**

2. **Create a new project:**
   - Click "New Project"
   - Select "Deploy from GitHub repo"
   - Connect your repository

3. **Configure the service:**
   - Railway will auto-detect Python
   - Add start command: `uvicorn backend.main:app --host 0.0.0.0 --port $PORT`

4. **Add Environment Variables:**
   - Click on Variables tab
   - Add:
     - `OPENAI_API_KEY`
     - `ANTHROPIC_API_KEY` (if needed)
     - `PORT` = 8000

5. **Generate Domain:**
   - Go to Settings → Generate Domain
   - You'll get a URL like: `https://ai-group-chat-backend-production.up.railway.app`

### Step 3: Update Streamlit Cloud

Same as Option 1 - add the Railway URL to Streamlit Secrets.

---

## Option 3: Quick Test with ngrok (Temporary)

This exposes your local backend to the internet temporarily (for testing only).

### Step 1: Install ngrok

```bash
# Download from https://ngrok.com/download
# Or with snap:
sudo snap install ngrok
```

### Step 2: Run ngrok

```bash
# Terminal 1: Start backend
cd /home/wschay/group-chat
conda activate group-chat
uvicorn backend.main:app --reload

# Terminal 2: Expose with ngrok
ngrok http 8000
```

### Step 3: Copy the URL

ngrok will show something like:
```
Forwarding   https://abc123.ngrok.io -> http://localhost:8000
```

### Step 4: Update Streamlit Secrets

Add to Streamlit Cloud secrets:
```toml
BACKEND_URL = "https://abc123.ngrok.io"
```

**⚠️ Warning:** This is temporary. The URL changes every time you restart ngrok (unless you have a paid plan).

---

## Option 4: Deploy Backend to Heroku

### Step 1: Prepare Files

1. **Create `Procfile`** in root:
   ```
   web: uvicorn backend.main:app --host 0.0.0.0 --port $PORT
   ```

2. **Create `runtime.txt`**:
   ```
   python-3.11.0
   ```

### Step 2: Deploy to Heroku

```bash
# Install Heroku CLI
curl https://cli-assets.heroku.com/install.sh | sh

# Login
heroku login

# Create app
heroku create ai-group-chat-backend

# Add environment variables
heroku config:set OPENAI_API_KEY=your-key
heroku config:set ANTHROPIC_API_KEY=your-key

# Deploy
git push heroku main
```

Your backend will be at: `https://ai-group-chat-backend.herokuapp.com`

---

## Recommended Approach

**I recommend Option 1 (Render.com) because:**
1. ✅ Free tier is generous
2. ✅ Easy to set up
3. ✅ Auto-deploys from GitHub
4. ✅ Environment variables support
5. ✅ Stays running (doesn't sleep like free Heroku)

---

## After Backend Deployment

### Test Your Backend

Visit: `https://your-backend-url.com/docs`

This opens the FastAPI Swagger UI where you can test endpoints.

### Update Streamlit App

1. Go to [share.streamlit.io](https://share.streamlit.io)
2. Open your app settings
3. Add to Secrets:
   ```toml
   BACKEND_URL = "https://your-backend-url.com"
   ```
4. Save and reboot

### Verify Connection

Your Streamlit app should now show "✅ Server Online" and work properly!

---

## Troubleshooting

### "Server Offline" still showing

1. **Check backend is running:**
   - Visit `https://your-backend-url.com/health`
   - Should return `{"status": "ok"}`

2. **Check BACKEND_URL in Streamlit:**
   - Go to app settings → Secrets
   - Ensure `BACKEND_URL` is set correctly (no trailing slash)

3. **Check backend logs:**
   - On Render: Logs tab
   - On Railway: View logs
   - Look for errors

### CORS Errors

If you see CORS errors, ensure your backend `main.py` has:
```python
from fastapi.middleware.cors import CORSMiddleware

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify your Streamlit URL
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

### Backend Crashes on Startup

1. Check environment variables are set (OPENAI_API_KEY)
2. Check all dependencies are in requirements.txt
3. Check start command is correct
4. Review deployment logs for errors

---

## Production Considerations

### Security
- [ ] Set specific CORS origins (not `*`)
- [ ] Use secrets management for API keys
- [ ] Add rate limiting
- [ ] Add authentication if needed

### Performance
- [ ] Use a production ASGI server (uvicorn with gunicorn)
- [ ] Add database for persistence (currently in-memory)
- [ ] Add Redis for session management
- [ ] Monitor performance and errors

### Monitoring
- [ ] Set up error tracking (e.g., Sentry)
- [ ] Add logging
- [ ] Monitor API usage
- [ ] Set up alerts for downtime

---

## Quick Start Checklist

- [ ] 1. Create `requirements.txt` in root with all dependencies
- [ ] 2. Choose a hosting provider (Render recommended)
- [ ] 3. Push code to GitHub
- [ ] 4. Create web service on hosting provider
- [ ] 5. Configure start command: `uvicorn backend.main:app --host 0.0.0.0 --port $PORT`
- [ ] 6. Add environment variables (OPENAI_API_KEY, etc.)
- [ ] 7. Wait for deployment (3-5 minutes)
- [ ] 8. Copy the deployed URL
- [ ] 9. Add `BACKEND_URL` to Streamlit Cloud secrets
- [ ] 10. Reboot Streamlit app
- [ ] 11. Test at https://ai-group-chat-dev.streamlit.app/

---

## Need Help?

If you encounter issues:
1. Check backend deployment logs
2. Test backend directly at `/docs` endpoint
3. Verify environment variables are set
4. Check CORS configuration
5. Ensure requirements.txt has all dependencies

