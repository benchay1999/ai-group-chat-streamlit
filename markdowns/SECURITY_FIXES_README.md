# Security Fixes - Quick Start Guide

**🎯 Goal:** Prepare application for 100-120 concurrent users  
**⏱️ Time Required:** 2-3 hours  
**📋 Status:** Code fixes complete, user configuration required

---

## What Was Fixed

### ✅ Code Improvements (Already Implemented)

1. **JWT Secret Validation** - Warns on weak/default secrets
2. **Database Connection Pooling** - Supports PostgreSQL with 20-60 connections
3. **MTurk Worker ID Validation** - Standardized pattern
4. **Environment Configuration** - Better documentation and warnings

---

## What You Need To Do (30-minute Quick Start)

### Step 1: Generate JWT Secrets (5 minutes)

```bash
# Generate secrets
python -c "import secrets; print('JWT_SECRET_KEY=' + secrets.token_urlsafe(32))"
python -c "import secrets; print('JWT_COMPLETION_SECRET=' + secrets.token_urlsafe(32))"

# Add to .env file
echo "JWT_SECRET_KEY=<generated-key-1>" >> .env
echo "JWT_COMPLETION_SECRET=<generated-key-2>" >> .env
echo "ENVIRONMENT=production" >> .env
```

### Step 2: Configure CORS (2 minutes)

```bash
# Add your production frontend URL
echo "CORS_ALLOWED_ORIGINS=https://your-production-frontend.com" >> .env
```

### Step 3: Database Setup (Choose One)

**Option A: Keep SQLite for Testing (1 minute)**
```bash
# Already configured - no action needed
# ⚠️ WARNING: Only suitable for <10 concurrent users
```

**Option B: Migrate to PostgreSQL for Production (30 minutes)**
```bash
# 1. Sign up at Supabase.com or Neon.tech (free tier)
# 2. Get connection string
# 3. Update .env:
echo "DATABASE_URL=postgresql+asyncpg://user:pass@host:port/db" >> .env

# 4. Install drivers:
pip install asyncpg psycopg2-binary

# 5. Run migrations:
cd backend && python -m alembic upgrade head
```

### Step 4: Verify MTurk Credentials (5 minutes)

```bash
# Test your AWS credentials
python backend/test_mturk_credentials.py

# Expected output:
# ✅ SUCCESS! Credentials are valid
#    Account Balance: $10000.00
```

### Step 5: Create Cashout HIT (10 minutes)

```bash
# Create standing HIT for cashouts
python backend/create_standing_hit.py

# Follow prompts and copy HIT ID
# Add to .env:
echo "CASHOUT_HIT_ID=<your-hit-id>" >> .env
```

### Step 6: Test Everything (5 minutes)

```bash
# Start backend
cd backend
uvicorn backend.main:app --reload

# In another terminal, run load test:
python load_test.py --users 10 --duration 30

# Expected: >95% success rate, <500ms p95 response time
```

---

## Full Documentation

For detailed instructions, see:

- **`PRODUCTION_DEPLOYMENT_SECURITY_CHECKLIST.md`** - Complete checklist
- **`MONITORING_SETUP_GUIDE.md`** - Set up error tracking
- **`WEBSOCKET_AUTH_POLICY.md`** - Choose authentication policy
- **`SECURITY_AUDIT_SUMMARY.md`** - What was fixed and why

---

## Quick Health Check

After configuration, verify:

```bash
# 1. Start backend
cd backend && uvicorn backend.main:app --reload

# 2. Check logs for:
# ✅ CORS configured for production
# ✅ Sentry initialized (if configured)
# ✅ Database connection established
# ✅ MTurk client initialized

# 3. No warnings about:
# ⚠️ Using default JWT_SECRET_KEY
# ⚠️ JWT_SECRET_KEY is only X characters
# ⚠️ Using SQLite in production (if migrated)
```

---

## Common Issues

### "Using default JWT_SECRET_KEY!"
**Fix:** Generate and add secrets to `.env` (Step 1)

### "Database connection failed"
**Fix:** Verify `DATABASE_URL` is correct, run migrations

### "MTurk credentials invalid"
**Fix:** Check `AWS_ACCESS_KEY_ID` and `AWS_SECRET_ACCESS_KEY` in `.env`

### CORS errors in frontend
**Fix:** Add production frontend URL to `CORS_ALLOWED_ORIGINS`

---

## Production Deployment Checklist

Before deploying to 100-120 users:

- [ ] JWT secrets generated and configured
- [ ] CORS configured with production URL
- [ ] PostgreSQL configured (recommended)
- [ ] MTurk credentials verified
- [ ] Cashout HIT created
- [ ] Load test passed (100 users)
- [ ] Monitoring configured (optional but recommended)
- [ ] Backend restarts without warnings

---

## Need Help?

1. Check backend startup logs for specific errors
2. Read detailed documentation (see "Full Documentation" above)
3. Test with smaller user count first (10-20 users)
4. Review `SECURITY_AUDIT_SUMMARY.md` for complete overview

---

## Files Modified

### Backend Code
- `backend/auth.py` - JWT validation
- `backend/database.py` - Connection pooling
- `backend/main.py` - Input validation
- `backend/config.py` - MTurk pattern

### Configuration
- `env.example` - Documentation updates

### Documentation (New Files)
- `PRODUCTION_DEPLOYMENT_SECURITY_CHECKLIST.md`
- `MONITORING_SETUP_GUIDE.md`
- `WEBSOCKET_AUTH_POLICY.md`
- `SECURITY_AUDIT_SUMMARY.md`
- `SECURITY_FIXES_README.md` (this file)
- `load_test.py`

---

## Summary

**Code:** ✅ Fixed and ready  
**Docs:** ✅ Complete and comprehensive  
**Your Action:** ⚠️ Configuration required (30-60 minutes)

**Follow Step 1-6 above to complete setup. Good luck! 🚀**

