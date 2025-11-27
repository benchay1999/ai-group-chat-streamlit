# Creating an Admin User

## Quick Command

```bash
conda activate group-chat
cd /home/wschay/ai-group-chat-streamlit
python create_admin.py
```

---

## What Was Fixed

### Problem
The script had incorrect imports:
```python
from backend.database import async_session_maker  # ❌ Wrong
from backend.auth import create_admin_user         # ❌ Wrong
```

### Solution
Since the script adds `backend/` to `sys.path`, we import directly:
```python
sys.path.insert(0, 'backend')
from database import async_session_maker  # ✅ Correct
from auth import create_admin_user        # ✅ Correct
```

---

## Usage

### Step 1: Make sure backend is NOT running
```bash
# If backend is running, stop it with Ctrl+C
```

### Step 2: Activate conda environment
```bash
conda activate group-chat
```

### Step 3: Run from project root
```bash
cd /home/wschay/ai-group-chat-streamlit
python create_admin.py
```

### Step 4: Follow the prompts
```
============================================================
Admin User Creation Tool
============================================================

Note: No password length limits with Argon2! Use any length.

Enter admin user ID: admin
Enter admin password: ********
Confirm admin password: ********

Creating admin user...

============================================================
✅ Admin user created successfully!
   User ID: admin
   Role: admin
============================================================

You can now login at: http://localhost:5173/login
```

---

## Important Notes

1. **Run from project root** (not from `backend/` directory)
2. **Backend must NOT be running** (close it first)
3. **Database must exist** (run migrations first if needed):
   ```bash
   cd backend
   python -m alembic upgrade head
   ```

---

## Password Guidelines

- ✅ **No length limits** with Argon2 (unlike bcrypt)
- ✅ Use **12+ characters** for security
- ✅ Mix uppercase, lowercase, numbers, special chars
- ✅ Avoid common passwords

---

## Troubleshooting

### Error: "No module named 'database'"
**Fix:** Make sure you're in the project root directory:
```bash
pwd  # Should show: /home/wschay/ai-group-chat-streamlit
```

### Error: "table users has no column named total_games"
**Fix:** Database has old schema. Reset it:
```bash
cd backend
rm -f group_chat.db
python -m alembic upgrade head
cd ..
python create_admin.py
```

### Error: "User already exists"
**Fix:** Try a different user_id or delete the old user from database

### Error: "Database connection failed"
**Fix:** Make sure database exists:
```bash
ls backend/group_chat.db  # Should exist
```

If it doesn't exist:
```bash
cd backend
python -m alembic upgrade head
```

---

## What Admin Users Can Do

Once created, admin users can:
1. ✅ Access `/admin` - Session management panel
2. ✅ Access `/admin/analytics` - Token usage analytics
3. ✅ View all users' sessions
4. ✅ Update payment statuses
5. ✅ See player-user mappings in session details
6. ✅ View cost/token breakdowns

---

## Creating Multiple Admins

You can create multiple admin users by running the script multiple times with different user IDs:

```bash
python create_admin.py
# First admin: admin1

python create_admin.py
# Second admin: admin2
```

---

## Quick Test

After creating admin:

1. **Start backend:**
   ```bash
   cd backend && python main.py
   ```

2. **Start frontend:**
   ```bash
   cd frontend && npm run dev
   ```

3. **Login:**
   - Go to http://localhost:3000
   - Click "Login"
   - Enter your admin credentials
   - You should see "Admin Panel" and "Analytics" buttons

---

## Summary

✅ **Script location:** `/home/wschay/ai-group-chat-streamlit/create_admin.py`  
✅ **Run from:** Project root directory  
✅ **Command:** `python create_admin.py`  
✅ **Fixed:** Import paths corrected  
✅ **Ready to use!**

