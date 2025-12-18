# How to Run the Application

Quick reference for starting the backend and frontend.

---

## 🚀 Backend

### Option 1: Using the Startup Script (Recommended)

```bash
python run_backend_local.py
```

**Pros:**
- ✅ Checks environment variables
- ✅ Shows helpful startup messages
- ✅ Configured for external connections

**When to use:** First time setup, production-like environment

**Expected output:**
```
🚀 Starting Local Backend Server
✅ All required environment variables are set
📡 Backend will be available at: http://localhost:8000

INFO:     Started server process
✅ MTurk client initialized (sandbox environment)
💰 Base pay: $0.05, Max bonus: $0.05
🚀 Application started successfully
INFO:     Uvicorn running on http://0.0.0.0:8000
```

---

### Option 2: Using uvicorn directly (Development)

```bash
cd backend
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

**Pros:**
- ✅ Auto-reload on code changes
- ✅ Faster iteration during development

**When to use:** Active development, making code changes

---

### Option 3: Using Python module

```bash
python -m uvicorn backend.main:app --reload --host 0.0.0.0 --port 8000
```

**Pros:**
- ✅ Works from project root
- ✅ Auto-reload enabled

**When to use:** Running from project root directory

---

## 🎨 Frontend

```bash
cd frontend
npm run dev
```

**Default URL:** http://localhost:5173

---

## 🧪 Testing MTurk Integration

### 1. Start Backend
```bash
python run_backend_local.py
```

### 2. Start Frontend
```bash
cd frontend
npm run dev
```

### 3. Test Auto-Registration
Visit: `http://localhost:5173/lobby?workerId=ATEST123&assignmentId=3TEST&hitId=3TEST`

You should see the MTurk auto-login animation!

---

## 🔧 Troubleshooting

### "ModuleNotFoundError: No module named 'backend'"

**Solution:** Run from project root, not from `backend/` directory:
```bash
# ❌ Wrong
cd backend
python -m uvicorn main:app

# ✅ Correct
python -m uvicorn backend.main:app
```

### "Address already in use"

**Solution:** Kill the process using port 8000:
```bash
# Find process
lsof -i :8000

# Kill it
kill -9 <PID>
```

### "Missing environment variables"

**Solution:** Create `.env` file from `env.example`:
```bash
cp env.example .env
# Edit .env with your values
```

---

## 📝 Quick Start Checklist

- [ ] `.env` file configured
- [ ] **Database migration run:** `cd backend && python3 -m alembic upgrade head` ⚠️ **REQUIRED!**
- [ ] Backend dependencies installed: `pip install -r backend/requirements.txt`
- [ ] Frontend dependencies installed: `cd frontend && npm install`
- [ ] Backend running: `python run_backend_local.py`
- [ ] Frontend running: `cd frontend && npm run dev`
- [ ] Test URL: http://localhost:5173

### ⚠️ Common Mistake

**Error:** `no such column: sessions.mturk_worker_id`

**Fix:** You forgot to run the migration! Run from the `backend` directory:
```bash
cd backend
python3 -m alembic upgrade head
```

---

**All set!** 🎉 Your application should now be running.

