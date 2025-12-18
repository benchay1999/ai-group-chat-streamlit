# Port Configuration Guide

## Default Ports

The Human Hunter game uses three different ports:

| Service | Port | URL |
|---------|------|-----|
| **Backend (FastAPI)** | 8000 | http://localhost:8000 |
| **React Frontend** | 5173 | http://localhost:5173 |
| **Streamlit Frontend** | 8502 | http://localhost:8502 |

## Port 8501 vs 8502

**Why 8502?** Port 8501 is Streamlit's default, but it may already be in use on shared systems. We've configured this project to use **port 8502** to avoid conflicts.

## How to Change Ports

### Streamlit Port

**Option 1: Edit config file**
```bash
# Edit .streamlit/config.toml
[server]
port = 8503  # Change to any available port
```

**Option 2: Command line**
```bash
streamlit run streamlit_app.py --server.port 8503
```

**Option 3: Use the launch script**
```bash
./run_streamlit.sh
# Automatically finds available port (8501, 8502, or 8503)
```

### Backend Port

```bash
# Default (port 8000)
uvicorn main:app --reload

# Custom port
uvicorn main:app --reload --port 8001

# Update BACKEND_URL in streamlit_app.py if you change this
```

### React Frontend Port

```bash
# Edit frontend/vite.config.js
export default defineConfig({
  server: {
    port: 5174  // Change port here
  }
})
```

## Checking Port Usage

### Check if port is in use
```bash
# Check specific port
lsof -i :8501
netstat -tlnp | grep 8501
ss -tlnp | grep 8501

# Check all Streamlit processes
ps aux | grep streamlit

# Check all ports used by services
netstat -tlnp | grep LISTEN
```

### Kill process on port
```bash
# Find process ID
lsof -ti :8501

# Kill the process
kill $(lsof -ti :8501)

# Force kill if needed
kill -9 $(lsof -ti :8501)
```

## Current Configuration

This project is configured to use:

✅ **Backend**: Port 8000 (FastAPI)
✅ **Streamlit**: Port 8502 (default in config.toml)
✅ **React**: Port 5173 (Vite default)

## Running All Services

```bash
# Terminal 1: Backend
cd backend
export OPENAI_API_KEY='your-key'
uvicorn main:app --reload
# → http://localhost:8000

# Terminal 2: Streamlit
streamlit run streamlit_app.py
# → http://localhost:8502

# Terminal 3: React (optional)
cd frontend
npm run dev
# → http://localhost:5173
```

## Troubleshooting

### "Port 8502 is already in use"

**Solution 1**: Use a different port
```bash
streamlit run streamlit_app.py --server.port 8503
```

**Solution 2**: Kill the existing process
```bash
kill $(lsof -ti :8502)
streamlit run streamlit_app.py
```

**Solution 3**: Use the launch script (auto-detects)
```bash
./run_streamlit.sh
```

### "Cannot connect to backend"

Check if backend is running:
```bash
curl http://localhost:8000/health
# Should return: {"status":"healthy"}
```

If not running, start it:
```bash
cd backend
uvicorn main:app --reload
```

### Backend URL Mismatch

If backend is on different port, update `streamlit_app.py`:
```python
BACKEND_URL = os.getenv('BACKEND_URL', 'http://localhost:8000')
```

Or set environment variable:
```bash
export BACKEND_URL='http://localhost:8001'
streamlit run streamlit_app.py
```

## Port Requirements Summary

**Minimum**: 1 port
- Backend only (port 8000)

**Standard**: 2 ports
- Backend (port 8000)
- Streamlit OR React (port 8502 or 5173)

**Full Setup**: 3 ports
- Backend (port 8000)
- Streamlit (port 8502)
- React (port 5173)

All three can run simultaneously without conflicts! 🎉

