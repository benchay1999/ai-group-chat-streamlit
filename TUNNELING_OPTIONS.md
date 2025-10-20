# Tunneling Options (No Sudo Required)

You need to expose your local backend to the internet so Streamlit Cloud can connect to it. Here are several options:

## Option 1: ngrok (Recommended) ✅

**Already installed for you!** No sudo required.

### Setup (One-Time)

1. **Authenticate ngrok**:
   ```bash
   # Get free auth token from: https://dashboard.ngrok.com/get-started/your-authtoken
   ./ngrok config add-authtoken YOUR_TOKEN
   ```

2. **Start tunnel**:
   ```bash
   ./ngrok http 8000
   ```

3. Copy the HTTPS URL from the output (e.g., `https://abc123.ngrok-free.app`)

**Pros**: Fast, reliable, popular  
**Cons**: Free tier changes URL on restart

---

## Option 2: localhost.run (No Installation!)

No installation or signup required!

```bash
ssh -R 80:localhost:8000 nokey@localhost.run
```

Copy the HTTPS URL from the output (e.g., `https://abc123.localhost.run`)

**Pros**: Zero setup, no signup  
**Cons**: URL changes on restart, requires SSH

---

## Option 3: Cloudflare Tunnel (Free, Permanent URL)

### Setup (One-Time)

1. **Download cloudflared** (no sudo):
   ```bash
   wget https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-amd64
   mv cloudflared-linux-amd64 cloudflared
   chmod +x cloudflared
   ```

2. **Authenticate**:
   ```bash
   ./cloudflared tunnel login
   ```
   This opens a browser to login to Cloudflare (free account)

3. **Create tunnel**:
   ```bash
   ./cloudflared tunnel create ai-group-chat
   ```

4. **Start tunnel**:
   ```bash
   ./cloudflared tunnel --url http://localhost:8000
   ```

**Pros**: Free permanent URL, no restart issues  
**Cons**: Requires Cloudflare account, more setup

---

## Option 4: serveo.net (No Installation!)

Similar to localhost.run:

```bash
ssh -R 80:localhost:8000 serveo.net
```

**Pros**: Zero setup  
**Cons**: URL changes on restart

---

## Option 5: Bore (Rust-based, Simple)

### Setup (One-Time)

1. **Download bore** (no sudo):
   ```bash
   wget https://github.com/ekzhang/bore/releases/latest/download/bore-x86_64-unknown-linux-musl
   mv bore-x86_64-unknown-linux-musl bore
   chmod +x bore
   ```

2. **Start tunnel**:
   ```bash
   ./bore local 8000 --to bore.pub
   ```

**Pros**: Simple, fast  
**Cons**: URL changes on restart

---

## Option 6: Deploy Backend to Cloud (Best for Production)

Instead of tunneling, deploy your backend to a cloud service with a permanent URL:

### Railway.app (Recommended, $5/month after free trial)

1. Go to https://railway.app
2. Connect GitHub repo
3. Add `OPENAI_API_KEY` environment variable
4. Deploy!
5. Get permanent URL (e.g., `https://your-app.up.railway.app`)

**Pros**: Permanent URL, always running, no local setup  
**Cons**: Costs money after free tier

### Render.com (Free Tier Available)

1. Go to https://render.com
2. Create new Web Service
3. Connect GitHub repo
4. Set start command: `uvicorn backend.main:app --host 0.0.0.0 --port $PORT`
5. Add `OPENAI_API_KEY` environment variable
6. Deploy and get permanent URL

**Pros**: Free tier available, permanent URL  
**Cons**: Free tier spins down after inactivity (slow cold starts)

### Fly.io (Free Tier Available)

1. Install flyctl (no sudo):
   ```bash
   curl -L https://fly.io/install.sh | sh
   export FLYCTL_INSTALL="$HOME/.fly"
   export PATH="$FLYCTL_INSTALL/bin:$PATH"
   ```

2. Login:
   ```bash
   flyctl auth login
   ```

3. Create app:
   ```bash
   flyctl launch
   ```

4. Deploy:
   ```bash
   flyctl deploy
   ```

**Pros**: Free tier with good resources, permanent URL  
**Cons**: Requires credit card for verification

---

## Comparison Table

| Option | Setup Time | Cost | Permanent URL | Always Running |
|--------|------------|------|---------------|----------------|
| ngrok | 5 min | Free | ❌ | ✅ |
| localhost.run | 1 min | Free | ❌ | ✅ |
| Cloudflare | 10 min | Free | ✅ | ✅ |
| serveo.net | 1 min | Free | ❌ | ✅ |
| bore | 5 min | Free | ❌ | ✅ |
| Railway | 10 min | $5/mo* | ✅ | ✅ |
| Render | 10 min | Free* | ✅ | ⚠️ (sleeps) |
| Fly.io | 15 min | Free* | ✅ | ✅ |

*After free trial/tier

---

## Recommendations

### For Quick Testing
Use **localhost.run** - zero setup, just one SSH command

### For Development
Use **ngrok** - already installed, reliable, easy to use

### For Production
Deploy to **Railway** or **Fly.io** - permanent URL, always running

---

## Quick Start Commands

Choose one:

```bash
# Option 1: ngrok (already installed)
./ngrok http 8000

# Option 2: localhost.run (no installation)
ssh -R 80:localhost:8000 nokey@localhost.run

# Option 3: serveo.net (no installation)
ssh -R 80:localhost:8000 serveo.net

# Then copy the HTTPS URL and add to Streamlit Cloud secrets
```

---

## Need Help?

See [DEPLOYMENT.md](DEPLOYMENT.md) for complete setup instructions with screenshots.

