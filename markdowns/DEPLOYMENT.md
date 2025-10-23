# Deployment Guide: Local Backend + Streamlit Cloud Frontend

This setup runs the heavy FastAPI/LangGraph backend on your local machine while hosting the lightweight Streamlit frontend on Streamlit Cloud.

## Architecture

```
┌─────────────────────┐         ┌──────────────────┐         ┌─────────────────┐
│   Your Computer     │         │     ngrok        │         │ Streamlit Cloud │
│                     │         │   (Tunnel)       │         │                 │
│  FastAPI Backend    │◄────────┤                  │◄────────┤   Frontend UI   │
│  (LangGraph Agents) │         │  Public URL      │         │  (streamlit_app)│
│  localhost:8000     │         │                  │         │                 │
└─────────────────────┘         └──────────────────┘         └─────────────────┘
```

## Prerequisites

1. Python 3.11+ installed locally
2. OpenAI API key
3. ngrok account (free tier works fine)
4. Streamlit Cloud account

## Setup Instructions

### Part 1: Set Up Local Backend

#### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

#### 2. Set Environment Variables

Create a `.env` file in the project root:

```bash
OPENAI_API_KEY=your-openai-api-key-here
```

Or export directly:

```bash
export OPENAI_API_KEY='your-openai-api-key-here'
```

#### 3. Start the Backend

```bash
python run_backend_local.py
```

You should see:
```
🚀 Starting Local Backend Server
✅ All required environment variables are set
📡 Backend will be available at: http://localhost:8000
📊 API docs at: http://localhost:8000/docs
```

Test it: Open http://localhost:8000/health in your browser. You should see `{"status":"healthy"}`

### Part 2: Expose Backend via Tunneling

You need to expose your local backend to the internet. **Multiple options available - choose one:**

#### Option A: ngrok (Recommended) - Already Installed! ✅

**No sudo required** - ngrok is already downloaded in your project directory.

1. **Authenticate ngrok** (one-time):
   ```bash
   # Sign up at https://ngrok.com (free)
   # Get token from: https://dashboard.ngrok.com/get-started/your-authtoken
   ./ngrok config add-authtoken YOUR_AUTH_TOKEN
   ```

2. **Start tunnel**:
   ```bash
   ./ngrok http 8000
   ```

3. **Copy the HTTPS URL** from output (e.g., `https://abc123def456.ngrok-free.app`)

4. **Test it**:
   ```bash
   curl https://your-ngrok-url.ngrok-free.app/health
   ```

⚠️ **Important:** Keep this terminal window open! Closing it will stop the tunnel.

#### Option B: localhost.run - Zero Installation! 🚀

No installation or signup required:

```bash
ssh -R 80:localhost:8000 nokey@localhost.run
```

Copy the HTTPS URL from output (e.g., `https://abc123.localhost.run`)

#### Option C: Other Tunneling Services

See **[TUNNELING_OPTIONS.md](TUNNELING_OPTIONS.md)** for more options including:
- **Cloudflare Tunnel** (free permanent URL)
- **serveo.net** (no installation)
- **bore** (simple Rust tool)
- **Cloud deployment** (Railway, Render, Fly.io)

#### Test Your Public URL

Open `https://your-tunnel-url/health` in your browser.
You should see `{"status":"healthy"}`

### Part 3: Deploy Frontend to Streamlit Cloud

#### 1. Push Code to GitHub

If not already done:

```bash
git add .
git commit -m "Add local backend + cloud frontend setup"
git push origin main
```

#### 2. Create Streamlit Cloud App

1. Go to https://share.streamlit.io/
2. Click "New app"
3. Select your repository
4. Set **Main file path** to: `streamlit_cloud_app.py`
5. Click "Advanced settings"

#### 3. Configure Secrets

In the "Secrets" section, add:

```toml
BACKEND_URL = "https://your-ngrok-url.ngrok-free.app"
```

Replace with your actual ngrok URL from Part 2, Step 3.

#### 4. Deploy

Click "Deploy" and wait for the app to start.

## Usage

### Starting Everything

1. **Start backend** (terminal 1):
   ```bash
   python run_backend_local.py
   ```

2. **Start ngrok** (terminal 2):
   ```bash
   ngrok http 8000
   ```

3. **Update Streamlit secrets** (if ngrok URL changed):
   - Go to your Streamlit Cloud app settings
   - Update `BACKEND_URL` with the new ngrok URL
   - Reboot the app

4. **Access your app**:
   - Open your Streamlit Cloud URL: `https://your-app.streamlit.app`

### Stopping Everything

1. Stop ngrok: `Ctrl+C` in terminal 2
2. Stop backend: `Ctrl+C` in terminal 1

## Troubleshooting

### Frontend shows "Backend URL not configured"

- Make sure you added `BACKEND_URL` to Streamlit Cloud secrets
- Reboot the Streamlit app after adding secrets

### Frontend can't connect to backend

- Check if backend is running: http://localhost:8000/health
- Check if ngrok is running and URL is correct
- Verify `BACKEND_URL` in Streamlit secrets matches your ngrok URL
- Try accessing the ngrok URL directly: `https://your-url.ngrok-free.app/health`

### ngrok URL keeps changing

Free ngrok URLs change on each restart. Options:
- Use a paid ngrok plan for a permanent URL
- Update Streamlit secrets each time ngrok restarts
- Consider deploying backend to a cloud service (AWS, GCP, Railway, Render)

### Backend is slow

This is normal for LangGraph agents with OpenAI API calls. The backend processes AI responses asynchronously, but initial setup takes time.

## Alternative: Cloud Backend

If you want to avoid ngrok and run everything in the cloud:

### Option 1: Railway/Render (Recommended)

1. Deploy backend to Railway.app or Render.com
2. Get the public URL (e.g., `https://your-app.up.railway.app`)
3. Set this as `BACKEND_URL` in Streamlit secrets

### Option 2: Full Streamlit Cloud (Original)

Use `deploy.py` instead, but note it will be slow due to Streamlit Cloud's resource limits.

## Tips

- **Development**: Test locally first with `streamlit run streamlit_app.py` and `BACKEND_URL=http://localhost:8000`
- **Production**: Keep ngrok and backend running 24/7, or deploy backend to a cloud service
- **Monitoring**: Check backend logs in terminal 1 for errors
- **Performance**: Local backend is much faster than Streamlit Cloud for AI operations

## File Overview

- `streamlit_cloud_app.py` - Frontend-only entry point for Streamlit Cloud
- `run_backend_local.py` - Local backend startup script
- `streamlit_app.py` - Main Streamlit UI (imported by streamlit_cloud_app.py)
- `backend/main.py` - FastAPI backend with LangGraph agents
- `deploy.py` - (Legacy) Combined deployment for Streamlit Cloud

