# Connection Issues Troubleshooting

## Common Error: SSL/EOF Connection Issues

If you see this error:
```
SSLError(SSLEOFError(8, '[SSL: UNEXPECTED_EOF_WHILE_READING] EOF occurred in violation of protocol'
```

This means the connection to your backend was interrupted.

## Why This Happens

### 1. ngrok Tunnel Restarted
- **Free ngrok** sessions can timeout or restart
- The URL stays the same but the connection drops briefly

**Fix:**
```bash
# Check Terminal 2 where ngrok is running
# If you see disconnection messages, restart ngrok:
Ctrl+C
./ngrok http 8000
```

### 2. Backend Server Crashed
Your local backend might have stopped running.

**Fix:**
```bash
# Check Terminal 1 where backend is running
# If you see errors or it stopped, restart:
./start_local.sh
```

### 3. ngrok Rate Limiting
Free ngrok has rate limits:
- **40 connections/minute** for free tier
- **20 HTTP requests/minute** per IP

**Fix:**
- Wait 1 minute for rate limit to reset
- Consider ngrok paid plan ($8/mo) for higher limits
- Or deploy backend to cloud (Railway, Render)

### 4. Network Interruption
Your internet connection dropped briefly.

**Fix:**
- Wait a moment and refresh the page
- Check your internet connection

## Quick Diagnosis

### Step 1: Check Backend
```bash
# In Terminal 1 - is backend running?
# Should see ongoing logs
```

### Step 2: Check ngrok
```bash
# In Terminal 2 - is ngrok running?
# Should show "Forwarding" line
```

### Step 3: Test Connection
```bash
# In a new terminal
curl https://your-ngrok-url.ngrok-free.app/health
# Should return: {"status":"healthy"}
```

## Prevention Strategies

### Option 1: Use Permanent Tunneling (Recommended)

**Cloudflare Tunnel (Free, Permanent URL):**
```bash
./cloudflared tunnel --url http://localhost:8000
```
- Never changes URL
- More stable than ngrok free
- No rate limits

See [TUNNELING_OPTIONS.md](TUNNELING_OPTIONS.md) for setup.

### Option 2: Deploy Backend to Cloud

**Railway.app ($5/month):**
- Permanent URL that never changes
- Always running, no manual restart
- No connection issues
- No rate limits

**Steps:**
1. Deploy backend to Railway
2. Get permanent URL (e.g., `https://your-app.up.railway.app`)
3. Set in Streamlit Cloud secrets
4. Never worry about ngrok again!

### Option 3: Increase ngrok Stability

**Paid ngrok ($8/month):**
- Higher rate limits
- More stable connections
- Permanent URL option

### Option 4: Auto-Restart ngrok

Create a script to auto-restart ngrok on failure:

```bash
#!/bin/bash
# save as: restart_ngrok.sh
while true; do
    ./ngrok http 8000
    echo "ngrok died, restarting in 5 seconds..."
    sleep 5
done
```

## Error Messages Explained

### "Connection interrupted. Please refresh the page."
- **Cause:** Brief network hiccup
- **Fix:** Refresh browser
- **Prevention:** Switch to cloud deployment

### "Lost connection to backend"
- **Cause:** Backend or ngrok stopped
- **Fix:** Check both terminals, restart if needed
- **Prevention:** Use cloud deployment

### "Backend request timed out"
- **Cause:** Backend is busy processing AI responses
- **Fix:** Wait a moment, will retry automatically
- **Prevention:** Normal during gameplay, no action needed

### "Cannot connect to backend"
- **Cause:** Backend is not running or wrong URL
- **Fix:** 
  1. Check backend is running
  2. Verify BACKEND_URL in Streamlit secrets
  3. Test with curl command above

## During Active Gameplay

If connection drops during a game:

1. **Don't panic!** Game state is saved on backend
2. Check if backend/ngrok is running
3. Refresh the Streamlit page
4. You should rejoin the same room automatically

## Best Practice Setup for Production

For the most stable experience:

1. **Deploy backend to Railway/Render** (permanent URL)
2. **Deploy frontend to Streamlit Cloud** (free)
3. **Set BACKEND_URL once** (never changes)
4. **Enjoy stable gameplay!**

## Getting Help

1. Check backend logs in Terminal 1
2. Check ngrok logs in Terminal 2
3. Test connection with curl command
4. See [DEPLOYMENT.md](DEPLOYMENT.md) for deployment alternatives

## Quick Reference

| Issue | Check | Fix |
|-------|-------|-----|
| SSL/EOF Error | ngrok Terminal 2 | Restart ngrok |
| Connection Error | Backend Terminal 1 | Restart backend |
| Timeout | Backend busy | Wait, will retry |
| Rate Limited | Too many requests | Wait 1 minute |

## Need More Stable Solution?

See [TUNNELING_OPTIONS.md](TUNNELING_OPTIONS.md) for cloud deployment options that eliminate these connection issues entirely!

