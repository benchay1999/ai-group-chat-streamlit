# Quick Start Guide (5 Minutes)

Get your AI Group Chat game running locally and accessible online in 5 minutes!

## Step 1: Setup Environment (1 minute)

```bash
# Copy environment template
cp env.example .env

# Edit and add your OpenAI API key
nano .env
# Set: OPENAI_API_KEY=your-key-here
# Save and exit (Ctrl+X, Y, Enter)
```

## Step 2: Start Backend (1 minute)

```bash
# Terminal 1: Start local backend
./start_local.sh
```

You should see:
```
✅ All required environment variables are set
📡 Backend will be available at: http://localhost:8000
```

## Step 3: Test Backend (30 seconds)

In a new terminal:

```bash
./test_backend.sh
```

You should see all green checkmarks ✅

## Step 4: Expose to Internet (1 minute)

Choose the easiest option for you:

### Option A: localhost.run (Fastest - No Signup!)

```bash
# Terminal 2
ssh -R 80:localhost:8000 nokey@localhost.run
```

Copy the URL shown (e.g., `https://abc123.localhost.run`)

### Option B: ngrok (More Reliable)

```bash
# One-time setup (if not done yet)
./ngrok config add-authtoken YOUR_TOKEN  # Get token from https://dashboard.ngrok.com

# Terminal 2
./ngrok http 8000
```

Copy the HTTPS URL shown (e.g., `https://abc123.ngrok-free.app`)

## Step 5: Test Local Frontend (1 minute)

Before deploying to cloud, test everything locally:

```bash
# Terminal 3
export BACKEND_URL=http://localhost:8000
streamlit run streamlit_app.py
```

Open http://localhost:8501 and verify the game works!

## Step 6: Deploy to Streamlit Cloud (2 minutes)

### Push to GitHub

```bash
git add .
git commit -m "Setup local backend + cloud frontend"
git push origin main
```

### Deploy on Streamlit Cloud

1. Go to https://share.streamlit.io/
2. Click **"New app"**
3. Select your repository
4. Set **Main file path** to: `streamlit_cloud_app.py`
5. Click **"Advanced settings"**
6. In **Secrets** section, add:
   ```toml
   BACKEND_URL = "https://your-tunnel-url-from-step-4"
   ```
7. Click **"Deploy"**

## You're Done! 🎉

Your game is now live! Share the Streamlit Cloud URL with friends.

---

## Daily Usage

Once set up, just run these two commands:

```bash
# Terminal 1: Backend
./start_local.sh

# Terminal 2: Tunnel (choose one)
./ngrok http 8000                              # ngrok
# OR
ssh -R 80:localhost:8000 nokey@localhost.run   # localhost.run
```

If your tunnel URL changes, update it in Streamlit Cloud:
1. Go to app settings
2. Update `BACKEND_URL` in secrets
3. Reboot app

---

## Troubleshooting

### "Backend URL not configured"
- Check you added `BACKEND_URL` to Streamlit Cloud secrets
- Reboot the app after adding secrets

### "Connection refused"
- Make sure backend is running: `./test_backend.sh`
- Make sure tunnel is running (check Terminal 2)
- Test tunnel URL: `curl https://your-tunnel-url/health`

### "OPENAI_API_KEY not set"
- Edit `.env` file: `nano .env`
- Add your API key
- Restart backend: `./start_local.sh`

### ngrok URL keeps changing
- This is normal for free tier
- Update Streamlit Cloud secrets when it changes
- Or use localhost.run instead (same behavior)
- Or deploy backend to cloud for permanent URL

---

## Next Steps

- **For permanent setup**: See [TUNNELING_OPTIONS.md](TUNNELING_OPTIONS.md) for cloud deployment options
- **For detailed guide**: See [DEPLOYMENT.md](DEPLOYMENT.md)
- **For customization**: Edit `backend/config.py` to change game settings

---

## File Reference

- `start_local.sh` - Start backend
- `test_backend.sh` - Test backend is working
- `setup_ngrok.sh` - Setup ngrok (if needed)
- `env.example` - Environment variables template
- `streamlit_cloud_app.py` - Frontend entry point for Streamlit Cloud
- `streamlit_app.py` - Main UI code

---

## Architecture

```
┌─────────────────────┐         ┌──────────────────┐         ┌─────────────────┐
│   Your Computer     │         │     Tunnel       │         │ Streamlit Cloud │
│                     │         │  (ngrok/etc)     │         │                 │
│  FastAPI Backend    │◄────────┤                  │◄────────┤   Frontend UI   │
│  (LangGraph Agents) │         │  Public URL      │         │  (streamlit_app)│
│  localhost:8000     │         │                  │         │                 │
└─────────────────────┘         └──────────────────┘         └─────────────────┘
```

Fast backend on your machine, free frontend hosting!

Enjoy your game! 🎮

