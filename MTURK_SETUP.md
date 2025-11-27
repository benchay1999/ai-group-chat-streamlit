# Mechanical Turk Data Collection System Setup Guide

This guide covers the new authentication, session tracking, and payment management features for collecting group chat data via Mechanical Turk.

## ⚠️ Current Database: SQLite (Temporary)

**This setup currently uses SQLite** - a file-based database requiring no installation.

> **Important**: This is a **temporary development solution**. For production deployment with multiple concurrent users, you should migrate to a cloud PostgreSQL service. See the [PostgreSQL Migration](#postgresql-migration-production) section below.

## Overview

The system now includes:
- **User authentication** (user_id/password)
- **Session tracking** with completion keys
- **Payment management** for compensating participants
- **Admin dashboard** for managing sessions
- **Role-based access control** (regular users and admins)
- **SQLite database** (temporary, will migrate to PostgreSQL for production)

## Quick Start (SQLite - No Sudo Required)

### 1. Install Dependencies

#### Backend
```bash
cd backend
pip install -r requirements.txt
```

New dependencies added:
- `sqlalchemy>=2.0.0` - Database ORM
- `aiosqlite` - Async SQLite driver (current temporary solution)
- `python-jose[cryptography]` - JWT tokens
- `passlib[bcrypt]` - Password hashing
- `alembic` - Database migrations
- `python-multipart` - Form data handling
- *(Commented out for now: `asyncpg`, `psycopg2-binary` - for PostgreSQL migration)*

#### Frontend
```bash
cd frontend
npm install
```

New dependencies added:
- `recharts` - Chart visualization
- `date-fns` - Date formatting
- `lucide-react` - Icon library

### 2. Configure Environment Variables

Update your `.env` file:

```env
# Existing variables...
OPENAI_API_KEY=your-api-key-here

# NEW: Database Configuration (TEMPORARY: Using SQLite)
# TODO: Migrate to PostgreSQL for production
DATABASE_URL=sqlite+aiosqlite:///./group_chat.db

# NEW: JWT Secrets (CHANGE THESE IN PRODUCTION!)
JWT_SECRET_KEY=your-secret-key-change-this-in-production
JWT_COMPLETION_SECRET=your-completion-key-secret-change-this
```

**Important**: Generate secure random strings for JWT secrets:
```bash
python -c "import secrets; print(secrets.token_urlsafe(32))"
```

### 3. Initialize Database

The database file and tables are automatically created when you start the backend:

```bash
# From project root
cd backend
uvicorn backend.main:app --reload
```

The SQLite file `group_chat.db` will be created in your project directory, and the tables `users` and `sessions` will be created automatically on startup.

### 4. Create Admin User (Optional)

To create an admin user, you can use the Python console:

```bash
python -c "
import asyncio
from backend.database import async_session_maker
from backend.auth import create_admin_user

async def main():
    async with async_session_maker() as db:
        # Use a strong password (12+ characters recommended)
        admin = await create_admin_user(db, 'admin', 'SecureAdminPass123!')
        print(f'Admin user created: {admin.user_id}')

asyncio.run(main())
"
```

**Password Requirements:**
- **No length limits** (uses Argon2 password hashing)
- Recommended: 12+ characters with mix of letters, numbers, symbols
- Example: `MyAdmin!Pass2024` (16 characters, secure enough)
- Any password length supported - Argon2 handles it securely

## System Architecture

### Backend Components

#### 1. Database Models (`backend/database.py`)
- **Users Table**: Stores user authentication info
- **Sessions Table**: Stores game sessions with completion keys
- Async SQLAlchemy with SQLite (development) or PostgreSQL (production)

#### 2. Authentication (`backend/auth.py`)
- Password hashing with Argon2 (secure, no length limits)
- JWT token generation/verification
- Role-based access control
- Token expiration (24 hours for auth tokens)

#### 3. Completion Keys (`backend/completion_keys.py`)
- JWT-based completion keys
- Encode session metadata (room code, language, players, duration)
- Verifiable and tamper-proof
- No expiration (permanent proof of completion)

#### 4. API Endpoints (`backend/main.py`)

**Authentication:**
- `POST /api/auth/register` - Register new user
- `POST /api/auth/login` - Login and get JWT token
- `GET /api/auth/me` - Get current user info

**Sessions:**
- `GET /api/sessions` - List user's sessions (all sessions for admins)
- `GET /api/sessions/{id}` - Get detailed session info with chat history
- `POST /api/sessions/claim` - Manually claim a completion key

**Admin:**
- `GET /api/admin/dashboard` - Get dashboard statistics
- `PATCH /api/admin/sessions/{id}/payment` - Update payment status

### Frontend Components

#### Pages
- **LoginPage** (`/login`) - Login/register interface
- **DashboardPage** (`/dashboard`) - User's sessions and claim key form
- **SessionDetailPage** (`/sessions/:id`) - Detailed session view with visualizations
- **AdminPage** (`/admin`) - Admin panel for payment management

#### Components
- **AuthContext** - Global authentication state
- **ProtectedRoute** - Route guard for authenticated pages
- **CompletionKeyModal** - Modal showing completion key after game
- **GameOver** - Game over screen with completion key button

## User Flow

### For Participants (MTurk Workers)

1. **Register** - Create account at `/login`
2. **Play Game** - Join a game from lobby
3. **Complete Session** - Chat and vote during the game
4. **Get Completion Key** - Automatic modal after game ends
5. **Submit on MTurk** - Copy completion key to MTurk form
6. **View Dashboard** - Check payment status at `/dashboard`

### For Researchers (Admins)

1. **Login as Admin** - Use admin credentials
2. **View All Sessions** - Access admin panel at `/admin`
3. **Review Sessions** - Click to view detailed chat history and votes
4. **Verify Completion Keys** - Keys are automatically validated
5. **Update Payment Status** - Mark sessions as paid
6. **Set Payment Amount** - Record compensation amounts

## Completion Key System

### How It Works

1. **Game Ends** → Backend saves session to JSON + PostgreSQL
2. **Generate Key** → JWT token encoding session metadata
3. **Associate User** → Automatically linked to logged-in user (if any)
4. **Display Key** → Modal shows key for copying
5. **Submit to MTurk** → Worker pastes key in MTurk form
6. **Verify** → You can decode key to verify all session details

### Completion Key Contents

The JWT token includes:
- `session_id` - Database UUID
- `room_code` - Original room code
- `language` - english/korean
- `total_players` - Total number of players
- `num_humans` - Number of human players
- `discussion_duration` - Discussion time in seconds
- `voting_duration` - Voting time in seconds
- `completed_at` - Unix timestamp
- `iat` - Issued at timestamp

### Manual Claiming

Users can claim completion keys from other devices/accounts:

1. Navigate to `/dashboard`
2. Enter completion key in "Claim Completion Key" form
3. Key validated and associated with their account
4. Prevents duplicate claims

## Admin Features

### Dashboard Statistics

- Total sessions count
- Pending payments count
- Paid sessions count
- Unclaimed sessions count

### Session Management

- View all sessions in table format
- Filter and sort sessions
- Update payment status (pending ↔ paid)
- Set payment amount
- View detailed session info

### Payment Workflow

1. Worker completes session and submits completion key to MTurk
2. Admin verifies completion on MTurk
3. Admin marks session as "paid" in dashboard
4. Admin sets payment amount (if needed)
5. Worker sees updated status in their dashboard

## Security Considerations

### Production Checklist

- [ ] **Migrate from SQLite to PostgreSQL** (critical for production!)
- [ ] Change JWT_SECRET_KEY and JWT_COMPLETION_SECRET
- [ ] Use strong admin password
- [ ] Enable HTTPS in production
- [ ] Configure CORS to specific origins
- [ ] Set up database backups (PostgreSQL managed service handles this)
- [ ] Use PostgreSQL connection pooling
- [ ] Enable rate limiting (optional)
- [ ] Monitor for suspicious completion key claims
- [ ] Test with multiple concurrent users
- [ ] Set up monitoring and alerting

### Password Security

- Passwords hashed with **Argon2** (winner of Password Hashing Competition 2015)
- **No password length limits** (unlike bcrypt's 72-byte limit)
- Memory-hard algorithm resistant to GPU cracking
- No plain-text password storage
- Secure JWT token transmission
- Recommended password length: 12+ characters with mixed case, numbers, symbols

### Completion Key Security

- Cryptographically signed (can't be forged)
- Contains all session metadata
- Can be verified without database lookup
- One-time claimable (prevents fraud)

## PostgreSQL Migration (Production)

When you're ready to deploy to production with multiple concurrent users, migrate to PostgreSQL:

### Step 1: Choose a Cloud PostgreSQL Service (No Sudo Required)

**Recommended Options:**

1. **Supabase** (https://supabase.com)
   - Free tier: 500MB database
   - Easy setup, great UI
   - Includes auth and storage features

2. **Neon** (https://neon.tech)
   - Free tier: 3GB storage
   - Serverless PostgreSQL
   - Auto-scaling

3. **Railway** (https://railway.app)
   - PostgreSQL included with app hosting
   - Easy deployment

4. **ElephantSQL** (https://www.elephantsql.com)
   - Free tier: 20MB
   - Simple managed PostgreSQL

### Step 2: Get Connection String

After creating your PostgreSQL instance, copy the connection string (usually in the format):
```
postgresql://user:password@host:port/database
```

### Step 3: Update Configuration

1. Update `.env`:
   ```env
   DATABASE_URL=postgresql+asyncpg://your-connection-string
   ```

2. Update `backend/requirements.txt` (uncomment PostgreSQL lines):
   ```
   asyncpg
   psycopg2-binary
   ```

3. Install PostgreSQL drivers:
   ```bash
   pip install asyncpg psycopg2-binary
   ```

### Step 4: Restart Backend

```bash
uvicorn backend.main:app --reload
```

Tables will be automatically created in your PostgreSQL database.

### Step 5: Migrate Data (If Needed)

If you have existing sessions in SQLite:

```bash
# Export SQLite data
sqlite3 group_chat.db .dump > backup.sql

# Then manually import or write a migration script
# (This is usually not needed for fresh deployments)
```

## Troubleshooting

### SQLite Database Issues (Current Setup)

```bash
# Check database file exists
ls -lh group_chat.db

# View database contents
sqlite3 group_chat.db "SELECT * FROM users;"
sqlite3 group_chat.db "SELECT * FROM sessions;"

# Backup database
cp group_chat.db group_chat.db.backup
```

### PostgreSQL Connection Issues (After Migration)

```bash
# Test connection with psql (if available)
psql -U your_user -d group_chat_db -c "SELECT 1;"

# Or use Python to test
python -c "
import asyncio
from backend.database import engine
async def test():
    async with engine.begin() as conn:
        result = await conn.execute('SELECT 1')
        print('✅ Connected!')
asyncio.run(test())
"
```

### JWT Token Issues

- Token expired → Re-login required
- Invalid signature → Check JWT_SECRET_KEY matches
- Token missing → Check axios interceptor in api.js

### Completion Key Not Showing

- Check backend logs for errors
- Verify session was saved to database
- Check `/api/rooms/{room_code}/stats` endpoint
- Ensure user is authenticated (or key will be unclaimed)

## Database Migrations

For schema changes, use Alembic:

```bash
# Initialize Alembic (already done)
cd backend
alembic init alembic

# Create migration
alembic revision --autogenerate -m "Description"

# Apply migration
alembic upgrade head

# Rollback
alembic downgrade -1
```

**Note**: With the current SQLite setup, the database is small enough that you can often just delete `group_chat.db` and restart to recreate tables. For PostgreSQL in production, use Alembic properly.

## API Reference

### Authentication Endpoints

#### Register
```http
POST /api/auth/register
Content-Type: application/json

{
  "user_id": "participant_123",
  "password": "secure_password"
}
```

#### Login
```http
POST /api/auth/login
Content-Type: application/json

{
  "user_id": "participant_123",
  "password": "secure_password"
}

Response:
{
  "access_token": "eyJ0eXAiOiJKV1Q...",
  "token_type": "bearer",
  "user_id": "participant_123",
  "role": "user"
}
```

### Session Endpoints

#### List Sessions
```http
GET /api/sessions
Authorization: Bearer {token}

Response:
{
  "sessions": [
    {
      "id": "uuid",
      "room_code": "ABC123",
      "completion_key": "eyJ0eXAi...",
      "language": "english",
      "total_players": 5,
      "num_human_players": 1,
      "completed_at": "2025-10-29T12:34:56",
      "payment_status": "pending",
      "payment_amount": null
    }
  ]
}
```

#### Claim Completion Key
```http
POST /api/sessions/claim
Authorization: Bearer {token}
Content-Type: application/json

{
  "completion_key": "eyJ0eXAiOiJKV1Q..."
}
```

## Deployment

### Backend Deployment

1. Set up PostgreSQL database on cloud provider
2. Update DATABASE_URL in environment
3. Set secure JWT secrets
4. Deploy FastAPI backend (Render, Railway, Heroku, etc.)
5. Ensure database tables are created on first startup

### Frontend Deployment

1. Update VITE_BACKEND_URL to production backend URL
2. Build frontend: `npm run build`
3. Deploy to Vercel, Netlify, or serve with nginx

## Support

For issues or questions:
1. Check backend logs: `uvicorn backend.main:app --reload`
2. Check browser console for frontend errors
3. Verify database connection and tables exist
4. Review this documentation

## Future Enhancements

Potential improvements:
- Email verification for accounts
- Password reset functionality
- Bulk payment updates (CSV upload)
- Advanced session filtering and search
- Export sessions to CSV/JSON
- Analytics dashboard with charts
- Rate limiting on auth endpoints
- Two-factor authentication (2FA)

