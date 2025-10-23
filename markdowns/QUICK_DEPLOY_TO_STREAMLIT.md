# Quick Deploy to Streamlit Cloud

## TL;DR - 3 Steps

### 1. Push to GitHub
```bash
cd /home/wschay/group-chat
git init
git add .
git commit -m "Deploy to Streamlit Cloud"
git remote add origin https://github.com/YOUR_USERNAME/YOUR_REPO.git
git push -u origin main
```

### 2. Deploy on Streamlit Cloud

1. Go to https://share.streamlit.io
2. Click "New app"
3. Select your repository
4. **Set Main file path to:** `deploy.py` ⚠️ **IMPORTANT!**
5. Add secrets (click Advanced settings → Secrets):
   ```toml
   OPENAI_API_KEY = "sk-your-key-here"
   ```
6. Click "Deploy!"

### 3. Wait & Test

- Wait 3-5 minutes for deployment
- Check logs for "✅ Backend is ready"
- Visit your app URL
- Should see "✅ Server Online"
- Create a room and play!

## What `deploy.py` Does

```
┌─────────────────────────────────────┐
│     Streamlit Cloud Container       │
│                                     │
│  ┌───────────────────────────────┐ │
│  │     deploy.py (Main)          │ │
│  │                               │ │
│  │  1. Start Backend (Thread)    │ │
│  │     ↓                         │ │
│  │     FastAPI on :8000          │ │
│  │     ↓                         │ │
│  │  2. Wait for health check     │ │
│  │     ↓                         │ │
│  │  3. Start Frontend (Main)     │ │
│  │     ↓                         │ │
│  │     Streamlit on :8501        │ │
│  │                               │ │
│  │  Frontend → localhost:8000 →  │ │
│  │  Backend (same container!)    │ │
│  └───────────────────────────────┘ │
└─────────────────────────────────────┘
```

## Why This Works

- ✅ Backend and frontend in **same container**
- ✅ Frontend connects to `localhost:8000` (same machine)
- ✅ No need for separate backend hosting
- ✅ No CORS issues
- ✅ Free on Streamlit Cloud

## Files Needed

- ✅ `deploy.py` - Main entry point (runs both backend + frontend)
- ✅ `streamlit_app.py` - Frontend code
- ✅ `backend/main.py` - Backend code
- ✅ `requirements.txt` - All dependencies

## Secrets Configuration

In Streamlit Cloud, go to Settings → Secrets and add:

```toml
# Required
OPENAI_API_KEY = "sk-proj-..."

# Optional - for Anthropic models
ANTHROPIC_API_KEY = "sk-ant-..."

# Optional - customize game settings
AI_MODEL_PROVIDER = "openai"
AI_MODEL_NAME = "gpt-4o-mini"
NUM_AI_PLAYERS = "4"
DISCUSSION_TIME = "180"
VOTING_TIME = "60"
```

## Common Issues

### ❌ "Server Offline"
- Check logs for errors
- Verify `OPENAI_API_KEY` is set
- Try rebooting the app

### ❌ Module not found errors
- Check `requirements.txt` has all dependencies
- Redeploy

### ❌ Port already in use
- Script auto-finds free port (8000-8009)
- Check logs for actual port used

## Test Locally (Optional)

```bash
cd /home/wschay/group-chat
conda activate group-chat
python deploy.py
```

Then visit: http://localhost:8501

## Need More Help?

See `DEPLOY_WITH_STREAMLIT_CLOUD.md` for detailed instructions.

---

**Ready?** Start with Step 1! 🚀

