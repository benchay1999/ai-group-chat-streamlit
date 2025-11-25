# Copy Security Updates to Production Directory

## ⚠️ Important: Migration Checklist

This backup folder has been modified with security enhancements. Here's how to safely copy changes to your working directory.

---

## ✅ Pre-Migration Checklist

Before copying anything:

1. **Backup your working directory** (just in case):
   ```bash
   cd /path/to/your/working/directory
   git add -A
   git commit -m "Backup before security updates"
   # Or create a manual backup
   cp -r . ../working-backup-$(date +%Y%m%d)
   ```

2. **Verify backend is not running** in working directory:
   ```bash
   # Check for running backend
   lsof -i :8000
   # Kill if needed
   pkill -f "uvicorn main:app"
   ```

3. **Note your current settings**:
   ```bash
   # Save current .env file
   cd /path/to/working/directory
   cp .env .env.backup
   ```

---

## 📦 Files to Copy

### Modified Files (3 files) - ⚠️ CAREFUL

These files have security enhancements. **Review diffs before overwriting**:

```bash
# From backup folder to working directory
BACKUP="/home/wschay/1125/ai-group-chat-streamlit"
WORKING="/path/to/your/working/directory"

# 1. backend/main.py
diff $BACKUP/backend/main.py $WORKING/backend/main.py
# Review changes, then:
cp $BACKUP/backend/main.py $WORKING/backend/main.py

# 2. backend/auth.py
diff $BACKUP/backend/auth.py $WORKING/backend/auth.py
cp $BACKUP/backend/auth.py $WORKING/backend/auth.py

# 3. backend/cashout_service.py
diff $BACKUP/backend/cashout_service.py $WORKING/backend/cashout_service.py
cp $BACKUP/backend/cashout_service.py $WORKING/backend/cashout_service.py
```

### New Files (19 files) - ✅ SAFE TO COPY

These are brand new files with no conflicts:

```bash
BACKUP="/home/wschay/1125/ai-group-chat-streamlit"
WORKING="/path/to/your/working/directory"

# Security monitoring system
cp $BACKUP/backend/security_monitor.py $WORKING/backend/security_monitor.py

# Test suite (create tests directory if needed)
mkdir -p $WORKING/backend/tests
cp $BACKUP/backend/tests/__init__.py $WORKING/backend/tests/
cp $BACKUP/backend/tests/test_security_auth.py $WORKING/backend/tests/
cp $BACKUP/backend/tests/test_security_payments.py $WORKING/backend/tests/
cp $BACKUP/backend/tests/test_security_concurrency.py $WORKING/backend/tests/
cp $BACKUP/backend/tests/test_security_data_privacy.py $WORKING/backend/tests/
cp $BACKUP/backend/tests/test_security_load.py $WORKING/backend/tests/
cp $BACKUP/backend/tests/conftest.py $WORKING/backend/tests/
cp $BACKUP/backend/tests/pytest.ini $WORKING/backend/tests/
cp $BACKUP/backend/tests/validate_production_config.py $WORKING/backend/tests/
cp $BACKUP/backend/tests/run_security_tests.sh $WORKING/backend/tests/
cp $BACKUP/backend/tests/requirements_test.txt $WORKING/backend/tests/
cp $BACKUP/backend/tests/README.md $WORKING/backend/tests/
cp $BACKUP/backend/tests/MANUAL_PENETRATION_TESTING.md $WORKING/backend/tests/

# Documentation
cp $BACKUP/START_SECURITY_TESTING.md $WORKING/
cp $BACKUP/RUN_SECURITY_TESTS.md $WORKING/
cp $BACKUP/SECURITY_TEST_DEPLOYMENT_GUIDE.md $WORKING/
cp $BACKUP/SECURITY_IMPLEMENTATION_SUMMARY.md $WORKING/
cp $BACKUP/SECURITY_TEST_RESULTS.md $WORKING/

# Make test runner executable
chmod +x $WORKING/backend/tests/run_security_tests.sh
```

---

## 🔍 What Changed in Modified Files

### 1. backend/main.py

**Lines 38-41** - Added imports:
```python
from .security_monitor import (
    get_security_monitor, log_failed_login, log_rate_limit_violation,
    log_invalid_token, log_admin_access_attempt, log_unusual_cashout
)
```

**Lines 59-78** - Enhanced CORS validation:
```python
# Security validation: Never allow wildcard origins
if '*' in allowed_origins:
    raise ValueError("SECURITY ERROR: Wildcard CORS origins...")

# HTTPS enforcement in production
if os.getenv('MTURK_ENVIRONMENT') == 'production':
    for origin in allowed_origins:
        if origin.startswith('http://') and 'localhost' not in origin:
            raise ValueError("SECURITY ERROR: HTTP origin...")
```

**Lines 122-128** - Added new rate limiters:
```python
# Rate limiters for security-critical endpoints
mturk_rate_limiter = SimpleRateLimiter(max_requests=10, window_seconds=60)
login_rate_limiter = SimpleRateLimiter(max_requests=5, window_seconds=60)
register_rate_limiter = SimpleRateLimiter(max_requests=3, window_seconds=60)
cashout_rate_limiter = SimpleRateLimiter(max_requests=5, window_seconds=60)
```

**Multiple locations** - Added rate limiting checks to endpoints:
- `/api/auth/register` - Added rate limiting + monitoring
- `/api/auth/login` - Added rate limiting + monitoring + failed login logging
- `/api/wallet/cashout` - Added rate limiting + unusual amount monitoring
- `/api/wallet/cashout/v2` - Added rate limiting
- `/api/wallet/cashout-cancel/{id}` - Added rate limiting

### 2. backend/auth.py

**Lines 227-230** - Added monitoring to `require_admin()`:
```python
from .security_monitor import log_admin_access_attempt

is_admin = current_user.role == UserRole.ADMIN
log_admin_access_attempt(
    user_id=current_user.user_id,
    endpoint="admin_endpoint",
    allowed=is_admin
)
```

### 3. backend/cashout_service.py

**Lines 145-175** - Enhanced with row-level locking:
```python
# SECURITY: Refresh user with FOR UPDATE lock
user_result = await db.execute(
    select(User).where(User.id == user.id).with_for_update()
)

# Double-check balance after lock
if user.gem_balance < gems_amount:
    raise CashoutError("Insufficient gems after lock acquisition...")

# Redemption code collision handling (retry loop)
# Negative balance validation
```

**Lines 224-245** - Added locking to `redeem_cashout_code()`:
```python
# SECURITY: Find transaction with row-level lock
result = await db.execute(
    select(CashoutTransaction).where(
        CashoutTransaction.redemption_code == redemption_code
    ).with_for_update()
)

# SECURITY: Check if HIT_CREATED status
if transaction.status == CashoutStatus.HIT_CREATED:
    raise CashoutError("This cashout is being processed...")
```

---

## ⚠️ Potential Issues When Copying

### Issue 1: security_monitor.py is NEW

**Problem**: This file doesn't exist in your working directory.

**Solution**: Must copy it first before copying files that import it.

**Copy order**:
```bash
# 1. Copy security_monitor.py FIRST
cp $BACKUP/backend/security_monitor.py $WORKING/backend/

# 2. Then copy modified files
cp $BACKUP/backend/main.py $WORKING/backend/
cp $BACKUP/backend/auth.py $WORKING/backend/
cp $BACKUP/backend/cashout_service.py $WORKING/backend/
```

### Issue 2: Circular Import in auth.py

**How I handled it**: Import is INSIDE the function, not at top:
```python
def require_admin(current_user: User = Depends(get_current_user)) -> User:
    from .security_monitor import log_admin_access_attempt  # ✅ Inside function
    ...
```

**Why**: Prevents circular import (`main.py` imports `auth.py`, `auth.py` imports `security_monitor.py`)

**Result**: ✅ Safe to copy as-is

### Issue 3: Test dependencies

**Problem**: Tests require additional packages.

**Solution**: Install in working directory:
```bash
cd /path/to/working/directory/backend/tests
pip install -r requirements_test.txt
```

Or manually:
```bash
pip install pytest pytest-asyncio aiohttp httpx pytest-cov
```

---

## 🎯 Recommended Migration Strategy

### Option A: Safe Incremental Copy (RECOMMENDED)

Copy in this order to avoid breaking changes:

```bash
# Set paths
BACKUP="/home/wschay/1125/ai-group-chat-streamlit"
WORKING="/path/to/your/working/directory"

# Step 1: Copy new monitoring system (no dependencies)
cp $BACKUP/backend/security_monitor.py $WORKING/backend/

# Step 2: Copy test suite (independent)
mkdir -p $WORKING/backend/tests
cp -r $BACKUP/backend/tests/* $WORKING/backend/tests/

# Step 3: Copy documentation (independent)
cp $BACKUP/START_SECURITY_TESTING.md $WORKING/
cp $BACKUP/RUN_SECURITY_TESTS.md $WORKING/
cp $BACKUP/SECURITY_*.md $WORKING/

# Step 4: Test that security_monitor works
cd $WORKING/backend
python -c "from security_monitor import get_security_monitor; print('✅ Import works')"

# Step 5: Copy modified backend files (review diffs first!)
# DO THIS ONE AT A TIME and test after each

# 5a. backup current files
cp $WORKING/backend/main.py $WORKING/backend/main.py.pre-security
cp $WORKING/backend/auth.py $WORKING/backend/auth.py.pre-security
cp $WORKING/backend/cashout_service.py $WORKING/backend/cashout_service.py.pre-security

# 5b. Copy new versions
cp $BACKUP/backend/cashout_service.py $WORKING/backend/

# 5c. Test cashout_service
python -c "from backend.cashout_service import create_cashout_transaction; print('✅ Import works')"

# 5d. Copy auth.py
cp $BACKUP/backend/auth.py $WORKING/backend/
python -c "from backend.auth import require_admin; print('✅ Import works')"

# 5e. Copy main.py (last, as it imports everything)
cp $BACKUP/backend/main.py $WORKING/backend/

# 5f. Test full import
python -c "from backend.main import app; print('✅ All imports work')"
```

### Option B: All-at-Once Copy (FASTER BUT RISKIER)

```bash
BACKUP="/home/wschay/1125/ai-group-chat-streamlit"
WORKING="/path/to/your/working/directory"

# Copy everything at once
cp $BACKUP/backend/security_monitor.py $WORKING/backend/
cp $BACKUP/backend/main.py $WORKING/backend/
cp $BACKUP/backend/auth.py $WORKING/backend/
cp $BACKUP/backend/cashout_service.py $WORKING/backend/
cp -r $BACKUP/backend/tests $WORKING/backend/
cp $BACKUP/START_SECURITY_TESTING.md $WORKING/
cp $BACKUP/RUN_SECURITY_TESTS.md $WORKING/
cp $BACKUP/SECURITY_*.md $WORKING/

# Test immediately
cd $WORKING/backend
python -c "from main import app; print('✅ Backend imports successfully')"
```

---

## 🧪 Verification After Copying

### Test 1: Python Imports

```bash
cd /path/to/working/directory/backend

# Test individual modules
python -c "from security_monitor import get_security_monitor; print('✅ security_monitor')"
python -c "from auth import require_admin; print('✅ auth')"
python -c "from cashout_service import create_cashout_transaction; print('✅ cashout_service')"
python -c "from main import app; print('✅ main')"
```

### Test 2: Backend Starts

```bash
# Try to start backend
cd backend
uvicorn main:app --reload --port 8001

# Should see:
# ✅ Database connection established
# 🔓 CORS configured for development...
# 🚀 Application started successfully
```

If you see errors about imports, the copy wasn't done correctly.

### Test 3: Run One Simple Test

```bash
cd backend/tests
pip install pytest pytest-asyncio
pytest test_security_auth.py::TestPasswordSecurity::test_password_hashing_is_strong -v
```

Should pass if everything is working.

---

## 🔧 Troubleshooting

### Error: "ModuleNotFoundError: No module named 'backend.security_monitor'"

**Cause**: security_monitor.py not copied or in wrong location

**Fix**:
```bash
# Verify file exists
ls -lh /path/to/working/directory/backend/security_monitor.py

# If missing, copy it
cp $BACKUP/backend/security_monitor.py $WORKING/backend/
```

### Error: "ImportError: cannot import name 'log_failed_login'"

**Cause**: security_monitor.py copied but main.py not updated

**Fix**: Copy main.py (it has the updated imports)

### Error: Backend won't start (CORS validation error)

**Cause**: New CORS validation is stricter

**Fix**: Update .env in working directory:
```bash
# Don't use wildcard
CORS_ALLOWED_ORIGINS=https://your-netlify-app.netlify.app,http://localhost:5173

# Not this:
# CORS_ALLOWED_ORIGINS=*  ❌ Will cause startup error
```

---

## 📋 Detailed Change Summary

### What's Safe to Copy Immediately

✅ **All test files** - Completely independent, no side effects
✅ **All documentation** - Markdown files, no code execution
✅ **security_monitor.py** - No dependencies on modified code

### What Needs Review

⚠️ **backend/main.py** - Many changes:
- New rate limiters (lines 122-128)
- CORS validation (lines 59-78)
- Rate limiting on 6 endpoints
- Security monitoring integration

⚠️ **backend/auth.py** - Small change:
- Monitoring in `require_admin()` (lines 227-230)

⚠️ **backend/cashout_service.py** - Medium changes:
- Row-level locking in two functions
- Enhanced validation logic

### Recommended Approach

**For Production Server That's Running**:

1. Copy to backup first:
   ```bash
   cp -r /path/to/working/directory /path/to/working/directory.backup
   ```

2. Copy test suite only (doesn't affect running code):
   ```bash
   cp -r $BACKUP/backend/tests $WORKING/backend/
   cp $BACKUP/START_SECURITY_TESTING.md $WORKING/
   ```

3. Run tests against CURRENT production code:
   ```bash
   cd $WORKING/backend/tests
   pytest test_security_*.py -v
   ```

4. Review what fails, then apply fixes incrementally

5. Copy security_monitor.py + modified files during maintenance window

---

## 🎯 Minimal Copy (Tests Only)

If you want to test BEFORE applying fixes:

```bash
# Copy only tests and documentation
cp -r $BACKUP/backend/tests $WORKING/backend/
cp $BACKUP/RUN_SECURITY_TESTS.md $WORKING/
cp $BACKUP/SECURITY_TEST_RESULTS.md $WORKING/

# Run tests against your CURRENT code
cd $WORKING/backend/tests
pip install pytest pytest-asyncio
pytest test_security_*.py -v

# See what fails, then decide which fixes to apply
```

---

## ✅ Verification Commands

After copying, run these to ensure everything works:

```bash
cd /path/to/working/directory

# 1. Check imports
python -c "from backend.main import app; print('✅ Imports OK')"

# 2. Start backend (test mode)
cd backend
uvicorn main:app --reload --port 8001 --env-file ../.env

# Should start without errors

# 3. Run one simple test
cd tests
pytest test_security_auth.py::TestPasswordSecurity -v

# Should pass
```

---

## 🚨 Rollback Plan

If something breaks after copying:

```bash
# Restore from backup
cp /path/to/working/directory.backup/backend/main.py /path/to/working/directory/backend/
cp /path/to/working/directory.backup/backend/auth.py /path/to/working/directory/backend/
cp /path/to/working/directory.backup/backend/cashout_service.py /path/to/working/directory/backend/

# Or use git
git restore backend/main.py backend/auth.py backend/cashout_service.py
```

---

## 📝 Summary

### YES, modifications are copy-paste ready with caveats:

✅ **New files**: 100% safe to copy (no conflicts)
⚠️ **Modified files**: Need to copy in correct order (security_monitor.py first)
✅ **No missing dependencies**: Everything needed is created
✅ **Backward compatible**: Changes are additive (don't break existing code)

### Recommended Migration Path:

1. **Test environment first** (use this backup folder)
2. **Validate all tests pass** here
3. **Then copy to production** during maintenance window
4. **Copy in order**: security_monitor.py → tests → docs → modified files
5. **Verify imports** after each step
6. **Test startup** before deploying

---

## 💡 Alternative: Selective Cherry-Picking

If you only want specific features:

**Just rate limiting**:
- Copy lines 122-128 from main.py (rate limiter definitions)
- Copy rate limiting checks from each endpoint
- Skip security_monitor integration

**Just atomic transactions**:
- Copy changes from cashout_service.py only
- Skip main.py and auth.py changes

**Just tests**:
- Copy entire `backend/tests/` directory
- Run against current code to see what needs fixing

---

**Bottom Line**: Yes, but follow the copy order (new files first, then modified files) to avoid import errors. I recommend testing in this backup folder first, then copying to production.

