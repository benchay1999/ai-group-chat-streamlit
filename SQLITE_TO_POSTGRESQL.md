# SQLite to PostgreSQL Migration Guide

## Current Status

**You are currently using SQLite** as a temporary development database. This works great for:
- Local development and testing
- Small-scale data collection
- No sudo/installation requirements

## Why Migrate to PostgreSQL?

For production deployment, PostgreSQL is recommended because:

1. **Better Concurrency**: Handles multiple concurrent users writing simultaneously
2. **Better Performance**: Optimized for larger datasets and complex queries
3. **Advanced Features**: Replication, clustering, advanced indexing
4. **Industry Standard**: Used by major companies for production systems
5. **Better Backup/Recovery**: Built-in tools and cloud provider support

## When to Migrate?

Migrate when:
- ✅ You're ready to deploy to production
- ✅ You expect multiple concurrent users (>10 simultaneous)
- ✅ You're collecting data at scale (hundreds of sessions)
- ✅ You want better reliability and backups

Stay with SQLite for now if:
- ✅ You're still in development/testing phase
- ✅ You have light usage (few users, occasional sessions)
- ✅ You want simplicity and no external dependencies

## Migration Options

### Option 1: Cloud PostgreSQL (Recommended - No Sudo Required!)

Choose a managed PostgreSQL service:

#### Supabase (Recommended)
- **Free Tier**: 500MB database
- **Setup Time**: 5 minutes
- **URL**: https://supabase.com

**Steps:**
1. Sign up at Supabase
2. Create a new project (select region closest to your users)
3. Wait for database provisioning (~2 minutes)
4. Go to Settings → Database
5. Copy the connection string (Connection pooling → Transaction mode)
6. Update your `.env`:
   ```env
   DATABASE_URL=postgresql+asyncpg://your-connection-string
   ```
7. Install PostgreSQL drivers:
   ```bash
   pip install asyncpg psycopg2-binary
   ```
8. Restart backend - tables will be created automatically

#### Neon
- **Free Tier**: 3GB storage
- **Setup Time**: 3 minutes
- **URL**: https://neon.tech

**Steps:**
1. Sign up at Neon
2. Create a new project
3. Copy connection string from dashboard
4. Update `.env` and restart

#### Railway
- **Free Tier**: Includes PostgreSQL + app hosting
- **Setup Time**: 5 minutes
- **URL**: https://railway.app

**Steps:**
1. Sign up at Railway
2. New Project → Add PostgreSQL
3. Copy connection string
4. Update `.env` and restart

#### ElephantSQL
- **Free Tier**: 20MB (small but works)
- **Setup Time**: 2 minutes
- **URL**: https://www.elephantsql.com

### Option 2: Local PostgreSQL (If Available Without Sudo)

If PostgreSQL is already installed on your system:

```bash
# Check if PostgreSQL is available
psql --version

# Try to connect
psql -U your_username -d postgres

# If successful, create database
CREATE DATABASE group_chat_db;
\q

# Update .env
DATABASE_URL=postgresql+asyncpg://your_username:your_password@localhost:5432/group_chat_db
```

### Option 3: Conda/Miniconda PostgreSQL

If you have conda access:

```bash
# Install PostgreSQL via conda
conda install -c conda-forge postgresql

# Initialize database in your directory
initdb -D ~/pgdata

# Start PostgreSQL
pg_ctl -D ~/pgdata -l logfile start

# Create database
createdb group_chat_db

# Update .env
DATABASE_URL=postgresql+asyncpg://localhost:5432/group_chat_db
```

## Migration Steps (Detailed)

### Phase 1: Backup Current SQLite Data

```bash
# Backup the entire database file
cp group_chat.db group_chat.db.backup

# Optional: Export to SQL
sqlite3 group_chat.db .dump > sqlite_backup.sql

# Optional: Export specific data
sqlite3 group_chat.db "SELECT * FROM users;" > users_backup.txt
sqlite3 group_chat.db "SELECT * FROM sessions;" > sessions_backup.txt
```

### Phase 2: Set Up PostgreSQL

Choose one of the options above (Supabase recommended).

### Phase 3: Update Configuration

1. **Update `.env`:**
   ```env
   # OLD (SQLite):
   # DATABASE_URL=sqlite+aiosqlite:///./group_chat.db
   
   # NEW (PostgreSQL):
   DATABASE_URL=postgresql+asyncpg://your-connection-string
   ```

2. **Update `backend/requirements.txt`:**
   ```txt
   # Uncomment these lines:
   asyncpg
   psycopg2-binary
   ```

3. **Install PostgreSQL drivers:**
   ```bash
   pip install asyncpg psycopg2-binary
   ```

### Phase 4: Test Connection

```bash
# Start backend - it will create tables automatically
cd backend
uvicorn backend.main:app --reload

# Check logs for successful connection
# You should see: "✅ Database tables created successfully"
```

### Phase 5: Migrate Existing Data (If Needed)

**For Fresh Deployments:** Skip this - just start using PostgreSQL!

**If You Have Important Existing Sessions:**

```python
# migration_script.py
import asyncio
import sqlite3
from backend.database import async_session_maker, User, DBSession as Session
from backend.auth import hash_password

async def migrate_data():
    # Connect to SQLite
    sqlite_conn = sqlite3.connect('group_chat.db')
    sqlite_conn.row_factory = sqlite3.Row
    
    async with async_session_maker() as db:
        # Migrate Users
        sqlite_users = sqlite_conn.execute('SELECT * FROM users').fetchall()
        for row in sqlite_users:
            user = User(
                id=row['id'],
                user_id=row['user_id'],
                password_hash=row['password_hash'],
                role=row['role'],
                created_at=row['created_at']
            )
            db.add(user)
        
        # Migrate Sessions
        sqlite_sessions = sqlite_conn.execute('SELECT * FROM sessions').fetchall()
        for row in sqlite_sessions:
            session = Session(
                id=row['id'],
                room_code=row['room_code'],
                completion_key=row['completion_key'],
                user_id=row['user_id'],
                language=row['language'],
                total_players=row['total_players'],
                num_human_players=row['num_human_players'],
                discussion_duration=row['discussion_duration'],
                voting_duration=row['voting_duration'],
                payment_status=row['payment_status'],
                payment_amount=row['payment_amount'],
                stats_file_path=row['stats_file_path'],
                completed_at=row['completed_at'],
                claimed_at=row['claimed_at']
            )
            db.add(session)
        
        await db.commit()
        print("✅ Migration complete!")
    
    sqlite_conn.close()

if __name__ == '__main__':
    asyncio.run(migrate_data())
```

Run migration:
```bash
python migration_script.py
```

### Phase 6: Verify Migration

```bash
# Test registration
curl -X POST http://localhost:8000/api/auth/register \
  -H "Content-Type: application/json" \
  -d '{"user_id": "test_user", "password": "test123"}'

# Test login
curl -X POST http://localhost:8000/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"user_id": "test_user", "password": "test123"}'

# Play a game and verify completion key is saved
```

### Phase 7: Update Documentation

Update any deployment documentation to reference PostgreSQL instead of SQLite.

## Rollback Plan

If something goes wrong:

```bash
# 1. Stop backend
# 2. Restore .env to SQLite
DATABASE_URL=sqlite+aiosqlite:///./group_chat.db

# 3. Restore SQLite backup if needed
cp group_chat.db.backup group_chat.db

# 4. Restart backend
uvicorn backend.main:app --reload
```

## Performance Comparison

### SQLite (Current)
- ✅ Fast for reads
- ✅ Simple, no setup
- ⚠️ Single writer at a time
- ⚠️ Limited concurrent connections
- ⚠️ File locks can cause issues

### PostgreSQL (After Migration)
- ✅ Multiple concurrent writes
- ✅ Better connection pooling
- ✅ Advanced query optimization
- ✅ Better for production
- ✅ Industry standard

## Cost Comparison

### SQLite
- **Cost**: $0
- **Maintenance**: Minimal
- **Scaling**: Limited

### PostgreSQL Cloud Services
- **Supabase Free**: 500MB, unlimited API requests
- **Neon Free**: 3GB, 100 hours compute/month
- **Railway**: $5/month for starter
- **ElephantSQL Free**: 20MB
- **Cost for Production**: ~$10-50/month depending on scale

## Frequently Asked Questions

**Q: Can I keep using SQLite for production?**
A: It's possible for light usage (<10 concurrent users), but not recommended. PostgreSQL provides better reliability and scalability.

**Q: Will my completion keys still work after migration?**
A: Yes! Completion keys are JWT tokens that work independently of the database type.

**Q: Do I need to migrate my JSON stats files?**
A: No, the JSON files in `group-chat-stats/` are independent and will continue to work.

**Q: How long does migration take?**
A: 5-15 minutes for setup, plus time to migrate data if you have existing sessions.

**Q: Can I test PostgreSQL before fully migrating?**
A: Yes! Set up a PostgreSQL instance, test it in a separate environment, then migrate your production data when ready.

**Q: What if I lose my SQLite database?**
A: Always backup `group_chat.db` regularly. The JSON files in `group-chat-stats/` provide a secondary backup of session data.

**Q: Are there any password length limits?**
A: No! We use Argon2 which has NO password length limits (unlike bcrypt). Use any password length you want - 12+ characters is recommended for security.

## Support

If you encounter issues during migration:

1. Check backend logs for connection errors
2. Verify your connection string is correct
3. Ensure PostgreSQL drivers are installed (`asyncpg`, `psycopg2-binary`)
4. Test connection string with `psql` or Python script
5. Check cloud provider dashboard for database status

## Next Steps

1. ✅ Continue using SQLite for development
2. ✅ Choose a PostgreSQL provider when ready for production
3. ✅ Follow migration steps above
4. ✅ Test thoroughly before switching production traffic
5. ✅ Set up database backups and monitoring

---

**Remember**: SQLite is perfectly fine for development and small-scale testing. Migrate to PostgreSQL when you're ready to scale up!

