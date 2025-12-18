# Quick Start: MTurk Data Collection System

## ⚠️ Current Setup: SQLite (Temporary Solution)

**This guide uses SQLite** - a file-based database that requires **no installation or sudo access**.

> **📝 Note**: This is a **temporary development solution**. For production deployment with multiple concurrent users, migrate to a cloud PostgreSQL service (see [Migration Guide](#migration-to-postgresql) below).

## 🚀 Get Started in 3 Steps (No Sudo Required!)

### 1. Update Environment Variables

Create/update `.env`:

```env
# Add these lines to your existing .env file
# TEMPORARY: Using SQLite (no installation required)
DATABASE_URL=sqlite+aiosqlite:///./group_chat.db

# Generate secure secrets (run the command below and paste the output)
JWT_SECRET_KEY=change-this-to-random-string
JWT_COMPLETION_SECRET=change-this-to-another-random-string
```

Generate secure secrets:
```bash
python -c "import secrets; print(secrets.token_urlsafe(32))"
```

### 2. Install Dependencies & Run

```bash
# Backend
cd backend
pip install -r requirements.txt
uvicorn backend.main:app --reload

# Frontend (new terminal)
cd frontend
npm install
npm run dev
```

**That's it!** The SQLite database file (`group_chat.db`) will be created automatically in your project directory.

### 3. Create Admin User (Optional)

```bash
python -c "
import asyncio
from backend.database import async_session_maker
from backend.auth import create_admin_user

async def main():
    async with async_session_maker() as db:
        # Password must be 72 characters or less (bcrypt limitation)
        admin = await create_admin_user(db, 'admin', 'SecureAdminPass123!')
        print(f'Admin created: {admin.user_id}')

asyncio.run(main())
"
```

**Important**: 
- Use any password length you want (no limitations with Argon2!)
- Recommended: 12+ characters with mix of letters, numbers, symbols
- Example good password: `MySecure!Admin@Pass2024`

## 📱 Using the System

### For Participants

1. **Register**: Go to `http://localhost:5173/login` → Register tab
2. **Play**: Join a game from lobby
3. **Get Key**: After game, copy completion key from modal
4. **View Dashboard**: Check your sessions at `/dashboard`

### For Admins

1. **Login**: Use admin credentials at `/login`
2. **Admin Panel**: Click "Admin Panel" or go to `/admin`
3. **Manage Sessions**: Update payment status, view all sessions
4. **View Details**: Click any session for full chat history and stats

## 🎮 Key Routes

- `/login` - Login/Register
- `/lobby` - Game lobby (play without login)
- `/dashboard` - Your sessions (requires login)
- `/sessions/:id` - Session details (requires login)
- `/admin` - Admin panel (requires admin role)

## 🔑 Key Features

1. **Completion Keys**: Automatically generated after each game
2. **Payment Tracking**: Admins mark sessions as paid
3. **Session History**: Full chat logs and voting results
4. **Visualizations**: Pie charts for votes, timeline for chat
5. **Manual Claiming**: Users can claim keys from other devices

## 📖 Full Documentation

- **Complete Setup**: [MTURK_SETUP.md](MTURK_SETUP.md)
- **Implementation Details**: [IMPLEMENTATION_SUMMARY.md](IMPLEMENTATION_SUMMARY.md)
- **General Game Info**: [README.md](README.md)

## ⚠️ Important Notes

1. **SQLite is Temporary**: This setup uses SQLite for development. Migrate to PostgreSQL for production.
2. **Change JWT Secrets**: Use secure random strings in production
3. **Admin Password**: Use a strong password for admin account
4. **CORS**: Configure `allow_origins` in `backend/main.py` for production
5. **HTTPS**: Enable HTTPS in production deployment
6. **Backups**: SQLite file is `group_chat.db` - back it up regularly

## 📊 SQLite vs PostgreSQL

### Current: SQLite ✅
- ✅ No installation required (perfect for development)
- ✅ No sudo access needed
- ✅ File-based (easy to backup)
- ✅ Works great for testing and small-scale collection
- ⚠️ Single writer at a time (fine for moderate use)
- ⚠️ Not recommended for production with many concurrent users

### Future: PostgreSQL 🎯
- ✅ Better for production with concurrent users
- ✅ Advanced features (replication, clustering)
- ✅ Better performance at scale
- ❌ Requires installation or cloud service

## 🚀 Migration to PostgreSQL

When you're ready to upgrade to PostgreSQL (recommended for production):

### Option 1: Cloud PostgreSQL Services (No Sudo Required)

**Supabase** (Recommended - Free Tier Available)
1. Sign up at https://supabase.com
2. Create a new project (free tier: 500MB database)
3. Get connection string from Settings → Database
4. Update `.env`:
   ```env
   DATABASE_URL=postgresql+asyncpg://[YOUR_CONNECTION_STRING]
   ```

**Other Options:**
- **Neon**: https://neon.tech (3GB free tier)
- **ElephantSQL**: https://www.elephantsql.com (20MB free tier)
- **Railway**: https://railway.app (PostgreSQL included)

### Option 2: Export/Import Data

When migrating from SQLite to PostgreSQL:

```bash
# 1. Export SQLite data (if needed)
sqlite3 group_chat.db .dump > backup.sql

# 2. Update DATABASE_URL in .env
DATABASE_URL=postgresql+asyncpg://your-connection-string

# 3. Update requirements.txt (uncomment PostgreSQL lines)
pip install asyncpg psycopg2-binary

# 4. Restart backend - tables will be recreated
uvicorn backend.main:app --reload

# Note: You may need to manually migrate data if you have existing sessions
```

## 🐛 Troubleshooting

### Database Connection Failed
```bash
# For SQLite: Check if database file exists
ls -lh group_chat.db

# For PostgreSQL (future): Check connection
# psql -U postgres -d group_chat_db -c "SELECT 1;"
```

### Login Not Working
- Check JWT_SECRET_KEY is set in .env
- Clear browser localStorage
- Check backend logs for errors

### Password Issues
- Argon2 has NO password length limits (any length works!)
- Recommended: 12+ characters is plenty secure
- Example: `MySecure!Pass2024`

### Completion Key Not Showing
- Check backend console for errors
- Verify session was saved to database
- Try refreshing the page

## 💬 Need Help?

Check the logs:
```bash
# Backend logs (when running uvicorn)
# Frontend console (browser Developer Tools → Console)
```

Review documentation:
- [MTURK_SETUP.md](MTURK_SETUP.md) - Detailed setup instructions
- [IMPLEMENTATION_SUMMARY.md](IMPLEMENTATION_SUMMARY.md) - Architecture details

## ✅ Verification Checklist

After setup, verify:

- [ ] Backend starts without errors
- [ ] SQLite database file created (`group_chat.db`)
- [ ] Database tables created (users, sessions)
- [ ] Can register new user
- [ ] Can login and receive JWT token
- [ ] Dashboard shows user info
- [ ] Can play a game
- [ ] Completion key appears after game
- [ ] Key is saved in dashboard
- [ ] Admin can access admin panel
- [ ] Admin can update payment status

## 📝 TODO: Production Deployment

Before deploying to production:

- [ ] Migrate to cloud PostgreSQL service (Supabase/Neon/Railway)
- [ ] Update DATABASE_URL in production environment
- [ ] Test with concurrent users
- [ ] Set up database backups
- [ ] Monitor performance and scale as needed

## 🎉 Success!

Your MTurk data collection system is ready! Start collecting valuable conversation data from Mechanical Turk workers.

