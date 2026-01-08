# Mechanical Turk Integration & Gem Cashout System

This guide covers the gem-based economy and MTurk payment system for converting in-game gems to real USD.

## Modern Gem-Based Cashout System

The Human Hunter game features a comprehensive gem economy where players earn gems through gameplay and can convert them to real money via Amazon Mechanical Turk.

### How It Works

**Gems as In-Game Currency:**
- Players earn gems by playing games (single-human or multi-human modes)
- 1000 gems = $1.00 USD
- Gems accumulate in player's wallet
- Can be cashed out via MTurk when minimum threshold reached

**Earning Gems:**
- **Single-Human Games:** 50 gems for all participants (no stakes, no risk)
- **Multi-Human Games:** 100 base gems + stakes system
  - Performance-based rewards
  - Winners get stake refund + share of loser pool
  - Voting accuracy determines winnings
  - See [markdowns/RULES.md](markdowns/RULES.md) for complete details

**Viewing Balance:**
- Dashboard page: Overview of earnings and current balance
- Wallet page (`/wallet`): Detailed balance, transaction history, cashout button

**Cashing Out:**
- Minimum: $2.00 (2000 gems)
- Requires MTurk Worker ID (add in profile)
- Worker-specific qualification-based HITs
- Auto-approved within 1 hour

## ⚠️ Current Database: SQLite (Temporary)

**This setup currently uses SQLite** - a file-based database requiring no installation.

> **Important**: This is a **temporary development solution**. For production deployment with multiple concurrent users, you should migrate to a cloud PostgreSQL service. See the [PostgreSQL Migration](#postgresql-migration-production) section below.

## System Overview

The MTurk integration includes:
- **Gem-based economy** - Players earn gems through gameplay
- **User authentication** - Secure user_id/password system
- **Session tracking** - Complete game history with stats
- **Gem wallet** - Track balance, earnings, and cashouts
- **Worker-specific HITs** - Unique qualification system prevents fraud
- **Automated payments** - Auto-approval within 1 hour
- **Admin dashboard** - Monitor cashouts and earnings
- **Role-based access** - Regular users and admins
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

1. **Register/Login** - Create account at `/login` (or play as guest initially)
2. **Play Games** - Join games from lobby
   - Single-human games: Earn 50 gems per game (no stakes)
   - Multi-human games: Earn 100+ gems based on performance (optional stakes)
3. **Earn Gems** - Gems credited automatically after each game
4. **View Balance** - Check gem balance in dashboard or wallet page (`/wallet`)
5. **Add MTurk Worker ID** - Go to profile page and add your MTurk Worker ID
6. **Request Cashout** - When you reach $2.00 (2000 gems), request cashout in wallet page
7. **Complete HIT** - Accept and complete the worker-specific HIT created for you
8. **Get Paid** - Auto-approved within 1 hour, payment sent via MTurk

### For Researchers (Admins)

1. **Login as Admin** - Use admin credentials
2. **Monitor Earnings** - View admin analytics at `/admin/analytics`
3. **Review Cashouts** - Track pending and completed cashout requests
4. **Verify HITs** - System auto-approves HITs, admin can monitor status
5. **View Sessions** - Access complete game history and chat logs
6. **Manage Users** - View user balances, earnings, and activity

## Gem Earning Rules

### Single-Human Games
- **Participants:** 1 human vs AI agents
- **Reward:** 50 gems for everyone (human + AI)
- **Stakes:** None
- **Risk:** None
- **Purpose:** Build initial gem balance safely

### Multi-Human Games
- **Participants:** 2+ human players competing
- **Base Reward:** 100 gems (must vote to receive)
- **Stakes:** Optional (0%, 10%, 30%, 50%, or 100% of balance)
- **Minimum Balance:** 250 gems required to join
- **Winners:** Get stake refund + share of loser pool (based on voting accuracy)
- **Losers:** Forfeit their stake
- **Risk:** Can lose gems if you perform poorly

### Voting Mechanics

**Single-Human Mode:**
- Vote for 1 player (who seems most human-like)
- AI agents participate in voting

**Multi-Human Mode:**
- Vote for N-1 players (all humans except yourself)
- Must identify all other human players correctly
- Voting accuracy affects gem winnings
- Formula: `accuracy = correct_votes / (num_humans - 1)`

### Detailed Examples

For complete gem mechanics, calculation formulas, and example scenarios, see:
- Visit `/gems-info` page in the application
- Read [markdowns/GEM_ECONOMY_IMPLEMENTATION.md](markdowns/GEM_ECONOMY_IMPLEMENTATION.md)
- Check [markdowns/RULES.md](markdowns/RULES.md)

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

### Cashout Workflow

1. Worker plays games and accumulates gems
2. Worker reaches minimum cashout threshold ($2.00 = 2000 gems)
3. Worker adds MTurk Worker ID in profile (if not already done)
4. Worker requests cashout in wallet page
5. System creates worker-specific qualification
6. System assigns qualification to worker
7. System creates HIT with qualification requirement (only that worker can see it)
8. Worker accepts and completes HIT on MTurk
9. Background monitor detects HIT submission
10. System auto-approves HIT within 1 hour
11. MTurk sends payment to worker
12. Transaction marked as completed in database

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

