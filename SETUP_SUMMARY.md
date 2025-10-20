# Setup Summary - Local Backend + Cloud Frontend

## What Was Created

I've set up your project to run the **backend locally** (fast, powerful) and the **frontend on Streamlit Cloud** (free hosting, accessible anywhere).

### New Files

1. **`streamlit_cloud_app.py`** - Frontend-only entry point for Streamlit Cloud
   - Checks that BACKEND_URL is configured
   - Shows helpful setup instructions if not
   - Imports and runs your main streamlit_app

2. **`run_backend_local.py`** - Local backend startup script
   - Checks environment variables
   - Runs FastAPI/LangGraph backend
   - Shows helpful status messages

3. **`start_local.sh`** - Quick start shell script
   - Automatically creates .env file if missing
   - Loads environment variables
   - Starts backend with one command

4. **`DEPLOYMENT.md`** - Complete deployment guide
   - Step-by-step instructions
   - Architecture diagram
   - Troubleshooting tips
   - Alternative deployment options

5. **`env.example`** - Environment variable template
   - Shows all configurable options
   - Copy to .env to get started

### Updated Files

- **`deploy.py`** - Now detects Streamlit context (legacy, not needed for new setup)
- **`README.md`** - Added deployment section highlighting the recommended setup

## How to Use

### First-Time Setup

1. **Install ngrok** (one-time setup):
   ```bash
   # macOS
   brew install ngrok
   
   # Linux
   curl -s https://ngrok-agent.s3.amazonaws.com/ngrok.asc | sudo tee /etc/apt/trusted.gpg.d/ngrok.asc >/dev/null
   echo "deb https://ngrok-agent.s3.amazonaws.com buster main" | sudo tee /etc/apt/sources.list.d/ngrok.list
   sudo apt update && sudo apt install ngrok
   ```

2. **Authenticate ngrok** (one-time):
   - Sign up at https://ngrok.com
   - Get your auth token from dashboard
   - Run: `ngrok config add-authtoken YOUR_TOKEN`

3. **Set up environment**:
   ```bash
   cp env.example .env
   nano .env  # Add your OPENAI_API_KEY
   ```

### Every Time You Want to Run

**Terminal 1 - Start Backend:**
```bash
./start_local.sh
```

**Terminal 2 - Start ngrok:**
```bash
ngrok http 8000
```

Copy the HTTPS URL from ngrok output (e.g., `https://abc123.ngrok-free.app`)

### Streamlit Cloud Setup (One-Time)

1. **Push to GitHub**:
   ```bash
   git add .
   git commit -m "Add local backend + cloud frontend setup"
   git push origin main
   ```

2. **Deploy to Streamlit Cloud**:
   - Go to https://share.streamlit.io/
   - Click "New app"
   - Select your repository
   - Set **Main file path** to: `streamlit_cloud_app.py`
   - Click "Advanced settings"

3. **Add Secret**:
   In the Secrets section, add:
   ```toml
   BACKEND_URL = "https://your-ngrok-url.ngrok-free.app"
   ```
   (Use your actual ngrok URL from Terminal 2)

4. **Deploy** and open your app!

### Updating Backend URL

When you restart ngrok, the URL changes. Update it in Streamlit Cloud:
1. Go to your app settings
2. Edit Secrets section
3. Update `BACKEND_URL` with new ngrok URL
4. Save and reboot app

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

**Why this setup?**
- ⚡ **Fast**: Backend runs on your powerful local machine
- 🆓 **Free**: Frontend hosted for free on Streamlit Cloud
- 🔧 **Easy**: Develop and debug locally with full logs
- 💰 **Cheap**: No cloud backend costs

## Testing Locally First

Before deploying to Streamlit Cloud, test everything locally:

```bash
# Terminal 1: Backend
./start_local.sh

# Terminal 2: Frontend
export BACKEND_URL=http://localhost:8000
streamlit run streamlit_app.py
```

Open http://localhost:8501 and test the game.

## Common Issues

### "Backend URL not configured"
- Make sure you added `BACKEND_URL` to Streamlit Cloud secrets
- Reboot the app after adding secrets

### "Can't connect to backend"
1. Check backend is running: http://localhost:8000/health
2. Check ngrok is running: should see "Forwarding" in terminal
3. Test ngrok URL: `https://your-url.ngrok-free.app/health`
4. Verify BACKEND_URL in Streamlit matches ngrok URL exactly

### "ngrok URL keeps changing"
- Free tier generates new URL each restart
- Options:
  1. Update Streamlit secrets each time (quick)
  2. Use ngrok paid plan for permanent URL ($8/month)
  3. Deploy backend to Railway/Render (permanent URL)

### Backend is slow
- Normal for AI agents with OpenAI API
- First message takes longest (model initialization)
- Subsequent messages faster (agents respond in parallel)

## Alternative: Full Cloud Deployment

If you don't want to run backend locally, deploy it to a cloud service:

### Railway (Recommended, $5/month)
1. Go to https://railway.app
2. Create new project from GitHub repo
3. Add `OPENAI_API_KEY` environment variable
4. Deploy!
5. Copy the public URL
6. Set as `BACKEND_URL` in Streamlit Cloud

### Render (Free tier available)
1. Go to https://render.com
2. Create new Web Service
3. Connect GitHub repo
4. Set start command: `uvicorn backend.main:app --host 0.0.0.0 --port $PORT`
5. Add `OPENAI_API_KEY` environment variable
6. Deploy and get public URL
7. Set as `BACKEND_URL` in Streamlit Cloud

## Files You Can Ignore

- `deploy.py` - Legacy combined deployment (not needed for this setup)
- `frontend/` - React frontend (alternative to Streamlit)

## Questions?

See [DEPLOYMENT.md](DEPLOYMENT.md) for detailed instructions and troubleshooting.

## Quick Commands Reference

```bash
# Start local backend
./start_local.sh

# Start ngrok tunnel
ngrok http 8000

# Test backend locally
curl http://localhost:8000/health

# Test ngrok tunnel
curl https://your-ngrok-url.ngrok-free.app/health

# Run frontend locally
export BACKEND_URL=http://localhost:8000
streamlit run streamlit_app.py
```

Enjoy your fast, cloud-hosted AI Group Chat game! 🎮

