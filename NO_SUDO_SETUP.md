# No Sudo Required Setup ✅

Everything you need has been set up without requiring sudo access!

## What's Installed

✅ **ngrok** - Downloaded to project directory (no system installation)  
✅ **Helper scripts** - All ready to use  
✅ **Documentation** - Complete guides for all options  

## Immediate Next Steps

### 1. Set Up Your Environment

```bash
cp env.example .env
nano .env
```

Add your OpenAI API key:
```
OPENAI_API_KEY=your-actual-key-here
```

Save and exit (Ctrl+X, Y, Enter)

### 2. Start the Backend

```bash
./start_local.sh
```

Keep this terminal open!

### 3. Choose a Tunneling Option

Open a **new terminal** and choose ONE of these:

#### Option A: ngrok (Recommended)

```bash
# One-time setup (if not done)
./ngrok config add-authtoken YOUR_TOKEN  # Get from https://dashboard.ngrok.com

# Start tunnel
./ngrok http 8000
```

Copy the HTTPS URL (e.g., `https://abc123.ngrok-free.app`)

#### Option B: localhost.run (Zero Setup!)

```bash
ssh -R 80:localhost:8000 nokey@localhost.run
```

Copy the HTTPS URL from output

#### Option C: serveo.net (Also Zero Setup!)

```bash
ssh -R 80:localhost:8000 serveo.net
```

Copy the HTTPS URL from output

### 4. Test Everything

```bash
# In a third terminal
./test_backend.sh
```

All tests should pass ✅

### 5. Deploy Frontend to Streamlit Cloud

1. **Push to GitHub**:
   ```bash
   git add .
   git commit -m "Setup local backend + cloud frontend"
   git push origin main
   ```

2. **Create Streamlit Cloud app**:
   - Go to https://share.streamlit.io/
   - Click "New app"
   - Select your repository
   - Set **Main file path** to: `streamlit_cloud_app.py`
   - Click "Advanced settings"

3. **Add secret**:
   ```toml
   BACKEND_URL = "https://your-tunnel-url-from-step-3"
   ```

4. **Deploy!**

## Available Scripts

All these work without sudo:

```bash
./start_local.sh      # Start backend with environment checks
./test_backend.sh     # Test backend is working correctly
./setup_ngrok.sh      # Help with ngrok setup
./ngrok http 8000     # Start ngrok tunnel
```

## Tunneling Comparison

| Method | Setup | Signup | Permanent URL |
|--------|-------|--------|---------------|
| **localhost.run** | None | No | No |
| **serveo.net** | None | No | No |
| **ngrok** | 1 min | Yes (free) | No* |
| **Cloudflare** | 5 min | Yes (free) | Yes |

*ngrok paid plan ($8/mo) offers permanent URLs

## Documentation

- **[QUICKSTART.md](QUICKSTART.md)** - 5-minute setup guide
- **[TUNNELING_OPTIONS.md](TUNNELING_OPTIONS.md)** - All tunneling options explained
- **[DEPLOYMENT.md](DEPLOYMENT.md)** - Detailed deployment guide
- **[SETUP_SUMMARY.md](SETUP_SUMMARY.md)** - Quick reference

## What If Tunnel URL Changes?

When you restart your tunnel, the URL changes. To update:

1. Go to your Streamlit Cloud app
2. Click ⚙️ Settings
3. Go to Secrets section
4. Update `BACKEND_URL` with new tunnel URL
5. Click "Save"
6. Reboot app

## Production Option (Permanent URL)

Don't want to deal with changing URLs? Deploy backend to cloud:

### Railway.app (Easiest)

```bash
# 1. Install Railway CLI (no sudo)
npm install -g railway

# 2. Login
railway login

# 3. Create project
railway init

# 4. Add environment variable
railway variables set OPENAI_API_KEY=your-key-here

# 5. Deploy
railway up
```

Get permanent URL, set it in Streamlit Cloud secrets, done! 🎉

### Render.com (Free Tier)

1. Go to https://render.com
2. Connect GitHub repo
3. Create "Web Service"
4. Set start command: `uvicorn backend.main:app --host 0.0.0.0 --port $PORT`
5. Add `OPENAI_API_KEY` environment variable
6. Deploy!

## Common Issues

### "Command not found: ngrok"
Use `./ngrok` (with `./`) instead of just `ngrok`

### "Permission denied: ./ngrok"
Already fixed! But if needed: `chmod +x ngrok`

### "ssh: connect to host localhost.run port 22: Connection refused"
SSH port blocked by firewall. Try:
- Use ngrok instead
- Try serveo.net
- Check firewall settings

### "Backend not responding"
```bash
# Check if backend is running
./test_backend.sh

# If not, start it
./start_local.sh
```

## Help

Need help? Check the documentation:

1. **Quick issues**: [SETUP_SUMMARY.md](SETUP_SUMMARY.md)
2. **Tunneling**: [TUNNELING_OPTIONS.md](TUNNELING_OPTIONS.md)
3. **Full guide**: [DEPLOYMENT.md](DEPLOYMENT.md)
4. **Questions**: [QUICKSTART.md](QUICKSTART.md)

## Summary

You're all set! Everything is configured to work **without sudo access**. 

Just run:
1. `./start_local.sh` (backend)
2. Choose tunneling (ngrok, localhost.run, etc.)
3. Deploy to Streamlit Cloud
4. Play! 🎮

Enjoy your AI Group Chat game!

