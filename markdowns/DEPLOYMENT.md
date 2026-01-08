# Deployment Guide: Full Cloud Deployment

This guide covers deploying Human Hunter to the cloud using modern hosting services. For local backend with ngrok, see [DEPLOYMENT_GUIDE_NGROK_NETLIFY.md](../DEPLOYMENT_GUIDE_NGROK_NETLIFY.md).

## Architecture Options

### Option 1: Netlify + Railway (Recommended)

```
┌─────────────────┐         ┌──────────────────┐         ┌─────────────┐
│   Netlify CDN   │         │   Railway.app    │         │   Neon/     │
│  (React Build)  │────────>│  (FastAPI)       │────────>│  Supabase   │
│  Static Hosting │  HTTPS  │  Backend API     │         │ (PostgreSQL)│
└─────────────────┘         └──────────────────┘         └─────────────┘
```

**Pros:**
- ✅ Free tier available (Netlify: 100GB bandwidth, Railway: $5 credit)
- ✅ Automatic deployments from GitHub
- ✅ Built-in SSL/HTTPS
- ✅ Good for small-medium traffic

**Cost:** $5-10/month (after free tier exhausted)

### Option 2: Vercel + Render

```
┌─────────────────┐         ┌──────────────────┐         ┌─────────────┐
│   Vercel        │         │   Render.com     │         │   Neon/     │
│  (React Build)  │────────>│  (FastAPI)       │────────>│  Supabase   │
│  Static Hosting │  HTTPS  │  Backend API     │         │ (PostgreSQL)│
└─────────────────┘         └──────────────────┘         └─────────────┘
```

**Pros:**
- ✅ Similar to Netlify + Railway
- ✅ Render free tier includes PostgreSQL
- ✅ Great developer experience

**Cost:** $7-10/month (Render Web Service)

### Option 3: AWS/GCP/Azure (Advanced)

For high traffic or enterprise use. Not covered in this guide.

---

## Part 1: Deploy Backend (Railway)

### Prerequisites
- GitHub account
- Railway account (https://railway.app)
- PostgreSQL database (recommended: Neon or Supabase)

### Step 1: Prepare Database

#### Using Neon (Free PostgreSQL)

1. Go to https://neon.tech
2. Sign up with GitHub
3. Create new project: "human-hunter-db"
4. Copy connection string from dashboard
5. Keep this for Step 4

#### Using Supabase (Alternative)

1. Go to https://supabase.com
2. Create new project
3. Go to Settings → Database → Connection string
4. Copy the connection string
5. Keep this for Step 4

### Step 2: Create Railway Project

1. Go to https://railway.app
2. Sign in with GitHub
3. Click "New Project"
4. Select "Deploy from GitHub repo"
5. Choose your repository
6. Select `main` branch

### Step 3: Configure Build Settings

Railway should auto-detect Python, but verify:

| Setting | Value |
|---------|-------|
| **Root Directory** | `/` (project root) |
| **Build Command** | `pip install -r backend/requirements.txt` |
| **Start Command** | `cd backend && uvicorn backend.main:app --host 0.0.0.0 --port $PORT` |

### Step 4: Add Environment Variables

In Railway dashboard, go to Variables tab and add:

```env
# Required
OPENAI_API_KEY=sk-your-key-here
DATABASE_URL=postgresql+asyncpg://user:pass@host/db

# Security (generate with: python -c "import secrets; print(secrets.token_urlsafe(32))")
JWT_SECRET_KEY=your-secure-random-key
JWT_COMPLETION_SECRET=another-secure-random-key
ENVIRONMENT=production

# Game Settings
NUM_AI_PLAYERS=4
DISCUSSION_TIME=240
VOTING_TIME=120
ROUNDS_TO_WIN=1
AI_MODEL_NAME=gpt-5.1-nano
AI_TEMPERATURE=0.8

# CORS (update after deploying frontend)
CORS_ALLOWED_ORIGINS=https://your-netlify-site.netlify.app

# Optional: MTurk
AWS_ACCESS_KEY_ID=your-aws-key
AWS_SECRET_ACCESS_KEY=your-aws-secret
MTURK_ENVIRONMENT=sandbox
CASHOUT_HIT_ID=your-hit-id
MINIMUM_CASHOUT_AMOUNT=2.00
```

### Step 5: Deploy

1. Click "Deploy"
2. Wait 3-5 minutes for deployment
3. Railway will provide a public URL like: `https://your-app.up.railway.app`
4. Test it: Visit `https://your-app.up.railway.app/health`

---

## Part 2: Deploy Frontend (Netlify)

### Step 1: Configure Build Settings

1. Go to https://netlify.com
2. Sign in with GitHub
3. Click "Add new site" → "Import an existing project"
4. Choose GitHub → Select your repository
5. Configure settings:

| Setting | Value |
|---------|-------|
| **Branch to deploy** | `main` |
| **Base directory** | `frontend` |
| **Build command** | `npm run build` |
| **Publish directory** | `frontend/dist` |

### Step 2: Add Environment Variables

In Netlify dashboard → Site settings → Environment variables:

```env
VITE_BACKEND_URL=https://your-railway-app.up.railway.app
```

Replace with your Railway backend URL from Part 1, Step 5.

### Step 3: Deploy

1. Click "Deploy site"
2. Wait 2-3 minutes for build
3. Your site will be live at: `https://random-name-12345.netlify.app`

### Step 4: Update Backend CORS

Go back to Railway → Variables and update:

```env
CORS_ALLOWED_ORIGINS=https://your-netlify-site.netlify.app,http://localhost:5173
```

Redeploy backend (click "Redeploy" in Railway).

### Step 5: Test Everything

1. Visit your Netlify URL
2. Create a room
3. Play a game
4. Check that everything works!

---

## Alternative Backend Hosting

### Render.com

**Pros:** Includes free PostgreSQL, simple setup
**Cons:** Free tier spins down after inactivity (slow cold starts)

**Setup:**
1. Go to https://render.com
2. Create new "Web Service"
3. Connect GitHub repo
4. Configure:
   - **Build Command:** `pip install -r backend/requirements.txt`
   - **Start Command:** `cd backend && uvicorn backend.main:app --host 0.0.0.0 --port $PORT`
5. Add environment variables (same as Railway)
6. Deploy

### Heroku

**Pros:** Mature platform, good documentation
**Cons:** No free tier anymore ($7/month minimum)

**Setup:**
1. Install Heroku CLI
2. Create `Procfile` in project root:
   ```
   web: cd backend && uvicorn backend.main:app --host 0.0.0.0 --port $PORT
   ```
3. Deploy:
   ```bash
   heroku create your-app-name
   heroku config:set OPENAI_API_KEY=sk-...
   git push heroku main
   ```

### Fly.io

**Pros:** Edge deployment, global distribution
**Cons:** More complex setup

See Fly.io documentation for details.

---

## Database Migration

If you're migrating from SQLite (development) to PostgreSQL (production):

### Step 1: Backup SQLite Data (if needed)

```bash
# Export users and sessions
sqlite3 backend/group_chat.db .dump > backup.sql
```

### Step 2: Update DATABASE_URL

```env
# Old (SQLite)
DATABASE_URL=sqlite+aiosqlite:///./group_chat.db

# New (PostgreSQL)
DATABASE_URL=postgresql+asyncpg://user:pass@host:5432/database
```

### Step 3: Run Migrations

```bash
cd backend
python -m alembic upgrade head
```

Tables will be created automatically in PostgreSQL.

### Step 4: Migrate Data (if needed)

If you have existing users/sessions to migrate, see [SQLITE_TO_POSTGRESQL.md](SQLITE_TO_POSTGRESQL.md) for detailed migration scripts.

---

## Production Checklist

Before going live:

### Security
- [ ] Generate strong JWT secrets (not defaults)
- [ ] Set `ENVIRONMENT=production`
- [ ] Configure CORS for your domain only
- [ ] Use PostgreSQL (not SQLite)
- [ ] Enable HTTPS (automatic with Netlify/Railway)
- [ ] Review [PRODUCTION_DEPLOYMENT_SECURITY_CHECKLIST.md](PRODUCTION_DEPLOYMENT_SECURITY_CHECKLIST.md)

### Configuration
- [ ] Set appropriate API key(s) with rate limits
- [ ] Configure game timing (DISCUSSION_TIME, VOTING_TIME)
- [ ] Set gem economy parameters
- [ ] Configure MTurk if using cashouts
- [ ] Test with multiple concurrent users

### Monitoring
- [ ] Set up error logging (Railway/Render provide logs)
- [ ] Monitor API usage (OpenAI dashboard)
- [ ] Check database performance
- [ ] Set up uptime monitoring (UptimeRobot, Pingdom)

### Testing
- [ ] Test user registration and login
- [ ] Test single-human game flow
- [ ] Test multi-human game with stakes
- [ ] Test gem earning and cashout
- [ ] Test WebSocket reconnection
- [ ] Test with multiple simultaneous games

---

## Cost Estimates

### Minimal Setup (Free Tier)
- **Frontend:** Netlify Free (100GB bandwidth/month)
- **Backend:** Railway $5 credit → ~2-3 days free, then $5-10/month
- **Database:** Neon Free (3GB storage)
- **Total:** $5-10/month after free tier

### Recommended Setup
- **Frontend:** Netlify Free
- **Backend:** Railway Pro ($10/month) or Render ($7/month)
- **Database:** Neon Free or Supabase Free
- **Total:** $7-10/month

### High-Traffic Setup (100+ concurrent users)
- **Frontend:** Netlify Pro ($19/month) or Vercel Pro ($20/month)
- **Backend:** Railway Pro ($20/month) or multiple instances
- **Database:** Neon Pro ($19/month) or Supabase Pro ($25/month)
- **Total:** $60-70/month

---

## Environment Variables Reference

### Required

| Variable | Example | Notes |
|----------|---------|-------|
| `OPENAI_API_KEY` | `sk-proj-...` | OpenAI API key |
| `DATABASE_URL` | `postgresql+asyncpg://...` | PostgreSQL connection string |
| `JWT_SECRET_KEY` | `random-32-char-string` | Generate with secrets.token_urlsafe(32) |
| `JWT_COMPLETION_SECRET` | `another-random-string` | Different from JWT_SECRET_KEY |
| `ENVIRONMENT` | `production` | Enables production security checks |
| `CORS_ALLOWED_ORIGINS` | `https://yoursite.netlify.app` | Frontend URL(s), comma-separated |

### Optional Game Settings

| Variable | Default | Notes |
|----------|---------|-------|
| `NUM_AI_PLAYERS` | `4` | Number of AI opponents |
| `DISCUSSION_TIME` | `240` | Discussion phase seconds |
| `VOTING_TIME` | `120` | Voting phase seconds |
| `ROUNDS_TO_WIN` | `1` | Rounds to survive |
| `AI_MODEL_NAME` | `gpt-5.1-nano` | AI model to use |
| `AI_TEMPERATURE` | `0.8` | LLM temperature |

### Optional MTurk/Gem Settings

| Variable | Default | Notes |
|----------|---------|-------|
| `AWS_ACCESS_KEY_ID` | - | Required for MTurk cashouts |
| `AWS_SECRET_ACCESS_KEY` | - | Required for MTurk cashouts |
| `MTURK_ENVIRONMENT` | `sandbox` | Use `production` for real money |
| `CASHOUT_HIT_ID` | - | Standing HIT for cashouts |
| `MINIMUM_CASHOUT_AMOUNT` | `2.00` | Minimum USD for cashout |
| `SINGLE_HUMAN_BASE_GEMS` | `50` | Gems for single-human games |
| `MULTI_HUMAN_BASE_GEMS` | `100` | Base gems for multi-human games |

For complete reference, see [ENVIRONMENT_REFERENCE.md](../ENVIRONMENT_REFERENCE.md).

---

## Monitoring & Maintenance

### Backend Logs

**Railway:**
- Dashboard → Your project → Deployments → View logs

**Render:**
- Dashboard → Your service → Logs tab

### Database Monitoring

**Neon:**
- Dashboard → Your project → Monitoring

**Supabase:**
- Dashboard → Your project → Database → Logs

### Frontend Analytics

Netlify provides:
- Traffic analytics
- Build history
- Error logs

### Error Tracking

Consider adding:
- Sentry (error tracking)
- LogRocket (session replay)
- PostHog (analytics)

---

## Troubleshooting

### Deployment Fails

**Backend build fails:**
- Check `backend/requirements.txt` is complete
- Verify Python version (3.8+ required)
- Check build logs for specific errors

**Frontend build fails:**
- Check `frontend/package.json` dependencies
- Verify Node.js version (18+ required)
- Check Netlify build logs

### Connection Issues

**Frontend can't reach backend:**
- Verify `VITE_BACKEND_URL` is set correctly
- Check CORS configuration in backend
- Test backend URL directly: `https://your-backend.com/health`

**WebSocket not connecting:**
- Ensure backend supports WebSocket (Railway/Render do by default)
- Check for proxy/firewall blocking WSS connections
- Verify WebSocket URL format: `wss://your-backend.com/ws/game/{code}`

### Database Issues

**Connection failed:**
- Verify DATABASE_URL is correct
- Check database service is running
- Ensure connection string uses `postgresql+asyncpg://`

**Tables not created:**
- Run migrations: `python -m alembic upgrade head`
- Check if tables exist in database dashboard

### Performance Issues

**Slow responses:**
- Check OpenAI API rate limits
- Monitor database query performance
- Consider upgrading backend plan
- Add Redis caching (advanced)

---

## Scaling Considerations

### Traffic Levels

**0-50 users:**
- Netlify Free + Railway Hobby + Free PostgreSQL
- Cost: $5-10/month

**50-200 users:**
- Netlify Free + Railway Pro + Neon Pro
- Cost: $30-40/month

**200+ users:**
- Consider:
  - Multiple backend instances
  - Load balancer
  - Redis for session storage
  - CDN for static assets
  - Dedicated PostgreSQL

---

## Alternative Deployment Options

### Local Backend + Cloud Frontend (Hybrid)

See [DEPLOYMENT_GUIDE_NGROK_NETLIFY.md](../DEPLOYMENT_GUIDE_NGROK_NETLIFY.md) for:
- ngrok tunnel to local backend
- Netlify for frontend
- Cost: $20/month (ngrok paid plan)
- **Pros:** Full control, easy debugging
- **Cons:** Requires keeping your computer running

### Docker Deployment

Create `Dockerfile` in backend/:

```dockerfile
FROM python:3.11-slim

WORKDIR /app
COPY backend/requirements.txt .
RUN pip install -r requirements.txt

COPY backend/ ./backend/
COPY .env .env

CMD ["uvicorn", "backend.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

Deploy to:
- Fly.io
- Google Cloud Run
- AWS ECS
- DigitalOcean App Platform

---

## Post-Deployment Tasks

### 1. Create Admin User

```bash
# SSH into your backend server or run locally with production DATABASE_URL
python create_admin.py
```

Enter admin credentials when prompted.

### 2. Test All Features

- [ ] User registration and login
- [ ] Create single-human room
- [ ] Create multi-human room with stakes
- [ ] Play complete game
- [ ] Verify gem earning
- [ ] Test wallet and cashout (if MTurk enabled)
- [ ] Test admin panel

### 3. Monitor First Users

Watch logs for:
- Authentication errors
- Database connection issues
- OpenAI API errors
- WebSocket disconnections
- Gem calculation errors

### 4. Set Up Backups

**Database:**
- Neon: Automatic backups included
- Supabase: Automatic backups included
- Self-hosted: Set up daily backups with pg_dump

**Configuration:**
- Keep `.env` file backed up securely
- Document all environment variables
- Store secrets in password manager

---

## Updating Deployed App

### Frontend Updates

```bash
# Make changes locally
git add .
git commit -m "Update frontend"
git push

# Netlify auto-deploys in ~2 minutes
```

### Backend Updates

```bash
# Make changes locally
git add .
git commit -m "Update backend"
git push

# Railway auto-deploys in ~3-5 minutes
```

### Database Migrations

```bash
# Create migration
cd backend
alembic revision --autogenerate -m "Add new column"

# Test locally first
alembic upgrade head

# Commit and push
git add backend/alembic/versions/
git commit -m "Add migration"
git push

# Railway auto-applies migrations on deploy
```

---

## Support & Resources

- **Railway Docs:** https://docs.railway.app
- **Netlify Docs:** https://docs.netlify.com
- **Neon Docs:** https://neon.tech/docs
- **Supabase Docs:** https://supabase.com/docs
- **Project Docs:** [README.md](../README.md), [TUTORIAL.md](../TUTORIAL.md)

---

This deployment approach provides a production-ready setup with automatic deployments, SSL, and scalability for the Human Hunter game.
