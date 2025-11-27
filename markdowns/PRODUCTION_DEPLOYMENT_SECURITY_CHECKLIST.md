# Production Deployment Security Checklist

**Date:** November 26, 2025  
**Target Scale:** 100-120 concurrent users  
**Status:** Pre-deployment security audit completed

---

## 🔴 CRITICAL: Must Complete Before Deployment

### 1. JWT Secrets Configuration ✅ IMPLEMENTED

**Status:** Validation added, but secrets must be generated

**Actions Required:**
```bash
# Generate secure JWT secrets
python -c "import secrets; print('JWT_SECRET_KEY=' + secrets.token_urlsafe(32))"
python -c "import secrets; print('JWT_COMPLETION_SECRET=' + secrets.token_urlsafe(32))"

# Add to production .env file (NEVER commit to git!)
# Set ENVIRONMENT=production to enable validation
```

**Validation:**
- [ ] JWT secrets generated and added to `.env`
- [ ] Secrets are at least 32 characters long
- [ ] `ENVIRONMENT=production` set in `.env`
- [ ] Backend starts without JWT warnings
- [ ] Verify secrets are loaded: Check startup logs for warnings

**Code Changes:**
- ✅ Added validation warnings in `backend/auth.py`
- ✅ Updated `env.example` with better documentation

---

### 2. Database Configuration ✅ IMPLEMENTED

**Status:** Connection pooling added, but using SQLite by default

**Actions Required:**

**Option A: PostgreSQL (STRONGLY RECOMMENDED for 100+ users)**
```bash
# 1. Sign up for managed PostgreSQL (no sudo required):
#    - Supabase (https://supabase.com) - Free tier: 500MB
#    - Neon (https://neon.tech) - Free tier: 3GB
#    - Railway (https://railway.app)

# 2. Get connection string and update .env:
DATABASE_URL=postgresql+asyncpg://user:pass@host:port/dbname

# 3. Install PostgreSQL drivers:
pip install asyncpg psycopg2-binary

# 4. Run migrations:
cd backend && python -m alembic upgrade head
```

**Option B: Keep SQLite (NOT recommended for production)**
- ⚠️ Only suitable for <10 concurrent users
- Will experience database locks with 100+ users
- No connection pooling benefits

**Validation:**
- [ ] PostgreSQL database created
- [ ] `DATABASE_URL` updated in `.env`
- [ ] PostgreSQL drivers installed
- [ ] Migrations run successfully
- [ ] Backend starts and connects to PostgreSQL
- [ ] Load test with 100+ concurrent requests (see section below)

**Code Changes:**
- ✅ Added connection pooling for PostgreSQL (pool_size=20, max_overflow=40)
- ✅ Added production warnings for SQLite
- ✅ Auto-detection of SQLite vs PostgreSQL
- ✅ Production mode disables SQL echo logging

---

### 3. CORS Configuration ⚠️ NEEDS REVIEW

**Status:** Default allows localhost only

**Actions Required:**
```bash
# Update .env with your production frontend URL
CORS_ALLOWED_ORIGINS=https://your-production-frontend.com,http://localhost:5173

# IMPORTANT: Must use HTTPS in production (not HTTP)
# Remove localhost URLs from production config
```

**Validation:**
- [ ] Production frontend URL added to `CORS_ALLOWED_ORIGINS`
- [ ] All production URLs use HTTPS
- [ ] No localhost URLs in production config
- [ ] Test API calls from frontend (should not see CORS errors)
- [ ] Check backend logs on startup for CORS configuration

**Code Changes:**
- ✅ CORS validation prevents wildcard origins
- ✅ HTTPS enforcement in production mode
- ✅ Clear error messages for misconfigurations

---

### 4. MTurk Credentials & Cashout System ⚠️ NEEDS CONFIGURATION

**Status:** Requires manual setup

**Actions Required:**

**Step 1: Verify AWS Credentials**
```bash
# Test MTurk credentials
python backend/test_mturk_credentials.py

# Expected output:
# ✅ SUCCESS! Credentials are valid
#    Account Balance: $10000.00 (sandbox) or actual balance (production)
```

**Step 2: Create Standing HIT for Cashouts**
```bash
# Follow the guide in SETUP_CASHOUT_HIT.md
python backend/create_standing_hit.py

# Add the HIT ID to .env:
CASHOUT_HIT_ID=your-hit-id-here
```

**Step 3: Configure MTurk Settings**
```bash
# In .env:
MTURK_ENVIRONMENT=sandbox  # or 'production' when ready
MTURK_BASE_PAY=0.05
MTURK_MAX_BONUS=0.05
MINIMUM_CASHOUT_AMOUNT=2.00
EXTERNAL_URL=https://your-production-frontend.com
```

**Validation:**
- [ ] AWS credentials tested and working
- [ ] MTurk account has sufficient funds
- [ ] Standing HIT created and ID added to `.env`
- [ ] `EXTERNAL_URL` points to production frontend
- [ ] Test cashout flow end-to-end (in sandbox)
- [ ] Verify cashout HIT appears correctly

---

### 5. Input Validation ✅ IMPLEMENTED

**Status:** Implemented for registration endpoint

**Code Changes:**
- ✅ Username validation (3-50 chars, alphanumeric + underscore/hyphen only)
- ✅ Password validation (12+ chars, uppercase, lowercase, number required)
- ✅ SQL injection pattern blocking (defense in depth)

**Validation:**
- [ ] Test registration with weak passwords (should be rejected)
- [ ] Test registration with short usernames (should be rejected)
- [ ] Test registration with SQL injection attempts (should be rejected)
- [ ] Verify error messages are user-friendly

---

### 6. WebSocket Authentication 📋 POLICY DECISION NEEDED

**Current State:**
- WebSocket connections accept optional authentication token
- Anonymous users can join games (guest play enabled)
- Authenticated users tracked for gems and MTurk integration

**Policy Options:**

**Option A: Allow Guest Play (Current)**
- Pros: Lower barrier to entry, more players
- Cons: Can't track anonymous users, potential abuse
- Required: Add rate limiting for anonymous connections

**Option B: Require Authentication**
- Pros: Full tracking, better security, required for MTurk
- Cons: Higher barrier to entry
- Required: Update frontend to enforce login before game

**Recommendation for 100-120 users:**
- If all users are MTurk workers: **Require authentication**
- If mixing MTurk + public users: **Keep guest play** but add rate limiting

**Actions Required:**
- [ ] Decide on authentication policy
- [ ] If allowing guests: Add WebSocket rate limiting
- [ ] If requiring auth: Update frontend to enforce login
- [ ] Document policy in user-facing documentation

---

## 🟡 IMPORTANT: Should Complete Before Production

### 7. Git History Audit ✅ COMPLETED

**Status:** Audit completed

**Findings:**
- ✅ `.env` file never committed to git history
- ✅ No hardcoded AWS access keys found in codebase
- ✅ No hardcoded OpenAI API keys found in codebase
- ✅ Security-related commits are documentation only

**No action required** - Codebase is clean

---

### 8. Rate Limiting 📋 ACCEPTABLE FOR SINGLE-INSTANCE

**Current State:**
- In-memory rate limiting implemented
- State lost on server restart
- Not suitable for multi-instance deployment

**For Single-Instance Deployment (Current):**
- ✅ Acceptable - rate limiting is functional
- ⚠️ Limits reset on restart (minor issue)

**For Multi-Instance Deployment (Future):**
- Needs distributed rate limiting (Redis or database-backed)

**Actions Required:**
- [ ] If deploying single instance: **No action needed**
- [ ] If deploying multiple instances: Implement Redis-based rate limiting
- [ ] Monitor rate limit violations in logs

---

### 9. Session & Token Management 📋 RECOMMENDED IMPROVEMENTS

**Current State:**
- JWT tokens valid for 24 hours
- No token refresh mechanism
- Token blacklist grows indefinitely

**Recommendations:**
```python
# Consider reducing token expiry
ACCESS_TOKEN_EXPIRE_HOURS = 4  # Instead of 24

# Add periodic cleanup job for expired tokens
# (Can be implemented post-launch)
```

**Actions Required:**
- [ ] Decide on token expiry duration (2-24 hours)
- [ ] Update `ACCESS_TOKEN_EXPIRE_HOURS` in config
- [ ] (Optional) Implement token refresh endpoint
- [ ] (Optional) Add periodic cleanup job for token blacklist

---

### 10. Monitoring & Alerting 📋 HIGHLY RECOMMENDED

**Current State:**
- Security monitor logs to console only
- No alerting system

**Recommended Services:**
- **Sentry** (https://sentry.io) - Error tracking, free tier
- **LogDNA/Mezmo** (https://mezmo.com) - Log aggregation
- **UptimeRobot** (https://uptimerobot.com) - Uptime monitoring, free tier

**Actions Required:**
```bash
# 1. Sign up for Sentry (recommended)
pip install sentry-sdk

# 2. Add to backend/main.py:
# import sentry_sdk
# sentry_sdk.init(dsn="your-dsn-here")

# 3. Set up alerts for:
# - Failed login attempts (>10/hour)
# - Rate limit violations (>50/hour)
# - Database connection errors
# - MTurk API errors
```

**Validation:**
- [ ] Error tracking service configured
- [ ] Alerts set up for critical events
- [ ] Test alert delivery (trigger test error)
- [ ] Uptime monitoring configured

---

### 11. Load Testing 📋 CRITICAL BEFORE LAUNCH

**Actions Required:**

**Test 1: Database Performance**
```bash
# Test concurrent database queries
cd backend/tests
pytest test_security_load.py::TestDatabaseConnectionPool -v
```

**Test 2: API Endpoint Performance**
```bash
# Test concurrent API requests (100+ users)
pytest test_security_load.py::TestConcurrentConnections -v
```

**Test 3: WebSocket Connections**
```bash
# Manual test: Open 100+ browser tabs to game lobby
# Monitor: CPU usage, memory usage, database connections
```

**Test 4: End-to-End User Flow**
- [ ] 100+ users register simultaneously
- [ ] 50+ concurrent game sessions
- [ ] Multiple cashout requests simultaneously
- [ ] System remains responsive under load

**Acceptance Criteria:**
- Database response time <100ms (95th percentile)
- API response time <500ms (95th percentile)
- WebSocket connections stable
- No database connection pool exhaustion
- No memory leaks over 1-hour period

---

## 📋 Production Deployment Checklist

### Environment Configuration
- [ ] `JWT_SECRET_KEY` generated and set (32+ chars)
- [ ] `JWT_COMPLETION_SECRET` generated and set (32+ chars)
- [ ] `ENVIRONMENT=production` set
- [ ] `MTURK_ENVIRONMENT` set (sandbox or production)
- [ ] `CORS_ALLOWED_ORIGINS` configured with production frontend URL
- [ ] `DATABASE_URL` pointing to PostgreSQL
- [ ] `AWS_ACCESS_KEY_ID` and `AWS_SECRET_ACCESS_KEY` valid
- [ ] `CASHOUT_HIT_ID` configured
- [ ] `EXTERNAL_URL` pointing to production frontend
- [ ] `MINIMUM_CASHOUT_AMOUNT` set appropriately

### Database
- [ ] PostgreSQL instance created (recommended)
- [ ] Database migrations run (`alembic upgrade head`)
- [ ] Connection pooling configured
- [ ] Automated backups enabled
- [ ] Test database connection from backend

### Security
- [ ] All secrets in `.env` file (not in code)
- [ ] `.env` file in `.gitignore`
- [ ] Git history clean (no leaked secrets)
- [ ] Rate limiting tested under load
- [ ] Input validation tested (passwords, usernames)
- [ ] CORS tested from production frontend
- [ ] SSL/TLS certificates configured for backend

### Testing
- [ ] Load test: 100+ concurrent users
- [ ] Load test: Database queries under stress
- [ ] Load test: WebSocket connections at scale
- [ ] End-to-end test: User registration → game → cashout
- [ ] MTurk worker registration and payment tested
- [ ] Rate limiting verified (login, registration, cashout)

### Monitoring & Operations
- [ ] Error tracking service configured (Sentry)
- [ ] Logging aggregation configured (optional)
- [ ] Uptime monitoring configured (UptimeRobot)
- [ ] Alerts configured for critical events
- [ ] Database connection pool monitoring
- [ ] API response time monitoring

### Documentation
- [ ] Production environment variables documented
- [ ] Deployment procedure documented
- [ ] Rollback procedure documented
- [ ] Incident response plan created
- [ ] User documentation updated

---

## 🚀 Deployment Procedure

### Pre-Deployment (1 hour before)
1. Verify all checklist items completed
2. Run full test suite: `pytest backend/tests/ -v`
3. Load test with 100+ concurrent users
4. Create database backup
5. Verify monitoring/alerting is working

### Deployment (30 minutes)
1. Set `ENVIRONMENT=production` in `.env`
2. Restart backend server
3. Check startup logs for warnings
4. Run health check: `curl https://your-backend.com/health`
5. Test API endpoints from frontend
6. Test WebSocket connections
7. Monitor logs for 5 minutes

### Post-Deployment (1 hour)
1. Monitor error rates (should be <1%)
2. Monitor response times (should be <500ms)
3. Monitor database connection pool (should be <50% utilization)
4. Test end-to-end user flow
5. Be prepared to rollback if issues detected

---

## 🔄 Rollback Procedure

If critical issues detected:

1. **Immediate:**
   - Revert `ENVIRONMENT` to `development`
   - Restart backend server
   - Monitor error rates

2. **Database Issues:**
   - Restore from backup if data corruption
   - Switch back to SQLite if PostgreSQL issues

3. **Authentication Issues:**
   - Verify `.env` file has correct secrets
   - Check JWT token expiry settings
   - Clear token blacklist if needed

4. **Performance Issues:**
   - Reduce max concurrent connections
   - Enable SQL query logging to debug
   - Check database connection pool settings

---

## 📞 Incident Response

### Critical Alerts
- Database connection failures
- Authentication system down
- MTurk payment failures
- High error rate (>5%)

### Response Procedure
1. Check monitoring dashboard
2. Review error logs
3. Identify root cause
4. Implement fix or rollback
5. Post-mortem document created

---

## ✅ Security Improvements Implemented

### Code Changes
1. **JWT Secret Validation**
   - Added startup warnings for default/weak secrets
   - Length validation (minimum 32 characters)
   - Production mode enforcement

2. **Database Configuration**
   - PostgreSQL connection pooling (pool_size=20, max_overflow=40)
   - Auto-detection of database type
   - Production warnings for SQLite
   - SQL echo disabled in production

3. **Input Validation**
   - Username validation (3-50 chars, alphanumeric + underscore/hyphen)
   - Password validation (12+ chars, uppercase, lowercase, number)
   - SQL injection pattern blocking

4. **MTurk Worker ID Validation**
   - Standardized pattern (A + 13 alphanumeric, total 14 chars)
   - Using constant from config.py (no hardcoding)

5. **Documentation**
   - Improved `env.example` with warnings
   - Security checklist created
   - Production deployment guide

---

## 📚 Related Documentation

- `SQLITE_TO_POSTGRESQL.md` - Database migration guide
- `SETUP_CASHOUT_HIT.md` - MTurk cashout system setup
- `SECURITY_IMPLEMENTATION_SUMMARY.md` - Security features overview
- `backend/tests/MANUAL_PENETRATION_TESTING.md` - Security testing guide
- `GET_MTURK_SANDBOX_CREDENTIALS.md` - AWS credentials setup

---

## 🎯 Success Criteria for Production Launch

- [ ] All critical checklist items completed
- [ ] Load testing passed (100+ concurrent users)
- [ ] Zero critical security vulnerabilities
- [ ] Monitoring and alerting configured
- [ ] Rollback procedure tested
- [ ] Team trained on incident response

**Once all items checked:** System is ready for production deployment! 🚀

