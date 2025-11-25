# Security Testing Deployment Guide

## Overview
This guide walks through deploying the application in a test environment to validate security with 10-20 test users before full production deployment.

**Environment**: Local testing (backup folder, isolated from production)

---

## Prerequisites

1. ✅ All security fixes implemented
2. ✅ Automated test suite created
3. ✅ Manual penetration test procedures documented
4. ✅ Production config validator ready

---

## Step 1: Setup Test Environment

### 1.1 Create Test Environment File

```bash
cd /home/wschay/1125/ai-group-chat-streamlit

# Create test environment configuration
cp .env .env.test

# Edit test configuration
nano .env.test
```

**Test Environment Configuration** (.env.test):
```bash
# MTurk - Use SANDBOX for testing
MTURK_ENVIRONMENT=sandbox
AWS_ACCESS_KEY_ID=<your_sandbox_key>
AWS_SECRET_ACCESS_KEY=<your_sandbox_secret>

# Database - Use separate test database
DATABASE_URL=sqlite+aiosqlite:///./test_group_chat.db

# JWT Secrets - Use test secrets (not production)
JWT_SECRET_KEY=test_secret_key_for_security_testing_only_do_not_use_in_prod
JWT_COMPLETION_SECRET=test_completion_secret_for_testing

# URLs - Local testing
EXTERNAL_URL=http://localhost:5173/lobby
CORS_ALLOWED_ORIGINS=http://localhost:5173,http://localhost:3000

# Payment Config - Lower amounts for testing
MTURK_BASE_PAY=0.01
MTURK_MAX_BONUS=0.01
MINIMUM_CASHOUT_AMOUNT=0.10

# Gems - Lower for easier testing
# (Keep default: 1000 gems = $1.00)
```

### 1.2 Initialize Test Database

```bash
cd backend

# Initialize test database with migrations
export DATABASE_URL="sqlite+aiosqlite:///./test_group_chat.db"
python -m alembic upgrade head

# Verify database created
ls -lh test_group_chat.db
```

### 1.3 Create Admin User for Testing

```bash
# Create admin user
python -c "
import asyncio
from database import async_session_maker, User, UserRole
from auth import hash_password
import uuid

async def create_admin():
    async with async_session_maker() as session:
        admin = User(
            id=uuid.uuid4(),
            user_id='test_admin',
            password_hash=hash_password('admin_password_test'),
            role=UserRole.ADMIN
        )
        session.add(admin)
        await session.commit()
        print('✅ Test admin created: test_admin / admin_password_test')

asyncio.run(create_admin())
"
```

---

## Step 2: Start Test Backend

```bash
# Start backend on port 8001 (different from production)
cd backend
uvicorn main:app --reload --port 8001 --env-file ../.env.test

# Verify backend started
curl http://localhost:8001/api/health
```

**Expected Output**:
```json
{"status": "healthy"}
```

---

## Step 3: Start Test Frontend

```bash
# In new terminal
cd frontend

# Create test environment file
cat > .env.local <<EOF
VITE_API_URL=http://localhost:8001
VITE_WS_URL=ws://localhost:8001
EOF

# Install dependencies (if not already done)
npm install

# Start frontend
npm run dev
```

**Expected**: Frontend runs on http://localhost:5173

---

## Step 4: Run Automated Security Tests

```bash
cd backend/tests

# Install test dependencies
pip install -r requirements_test.txt

# Run configuration validation
python validate_production_config.py --env-file ../../.env.test

# Run all security tests
./run_security_tests.sh

# Or run individually:
pytest test_security_auth.py -v
pytest test_security_payments.py -v
pytest test_security_concurrency.py -v
pytest test_security_data_privacy.py -v
pytest test_security_load.py -v -m slow  # This takes longer
```

---

## Step 5: Create 10-20 Test Users

### Option A: Automated User Creation

```bash
cd backend

# Create test user creation script
python -c "
import asyncio
from database import async_session_maker, User, UserRole
from auth import hash_password
import uuid

async def create_test_users(count=20):
    async with async_session_maker() as session:
        for i in range(count):
            user = User(
                id=uuid.uuid4(),
                user_id=f'test_user_{i:02d}',
                password_hash=hash_password('test_password'),
                role=UserRole.USER,
                gem_balance=10000,  # Give each user $10 worth of gems
                mturk_worker_id=f'A{str(i).zfill(13)}'
            )
            session.add(user)
        
        await session.commit()
        print(f'✅ Created {count} test users')
        print(f'   Username format: test_user_00 to test_user_{count-1:02d}')
        print(f'   Password (all): test_password')
        print(f'   Gem balance (each): 10,000 gems ($10.00)')

asyncio.run(create_test_users(20))
"
```

### Option B: Manual Registration via Frontend

1. Go to http://localhost:5173
2. Register users: `test_user_01`, `test_user_02`, ..., `test_user_20`
3. Password: `test_password` (same for all)

---

## Step 6: Execute Manual Penetration Tests

Follow procedures in `MANUAL_PENETRATION_TESTING.md`:

### High-Priority Tests to Run:

1. **JWT Token Tampering** (Test 1.1)
2. **Token Reuse After Logout** (Test 1.2)
3. **Concurrent Cashout Race Condition** (Test 2.1)
4. **Payment Amount Tampering** (Test 2.2)
5. **Multi-Tab Login Conflicts** (Test 3.1)
6. **API Response Data Leakage** (Test 4.1)
7. **Login Brute-Force Protection** (Test 5.1)
8. **SQL Injection Prevention** (Test 6.1)

### Document Results

Create `SECURITY_TEST_RESULTS.md` with findings:
```markdown
# Security Test Results

## Test Date: [DATE]
## Tester: [NAME]
## Environment: Localhost test environment

### Authentication Tests
- [PASS] JWT token tampering detected
- [PASS] Expired tokens rejected
- [FAIL] Token blacklist not working (if applicable)

### Payment Tests
- [PASS] Concurrent cashouts handled correctly
- [PASS] Double redemption prevented

... etc
```

---

## Step 7: Simulate Concurrent Users

### Simulate 20 Concurrent Users

```bash
cd backend/tests

# Run load test
pytest test_security_load.py::TestConcurrentConnections::test_120_concurrent_websocket_connections -v
```

### Manual Simulation (using browser)

1. Open 10 browser windows (use different browsers if needed)
2. Login with different test users in each
3. All users join games simultaneously
4. Monitor for:
   - Database errors
   - Connection failures
   - Payment conflicts
   - Session conflicts

---

## Step 8: Monitor Security Events

### Enable Security Monitoring

Add to backend code temporarily:
```python
# In backend/main.py, add after imports
from backend.security_monitor import get_security_monitor

# Add endpoint to view security events
@app.get("/api/admin/security/events")
async def get_security_events(admin: User = Depends(require_admin)):
    monitor = get_security_monitor()
    return monitor.get_event_summary()
```

### Monitor During Testing

```bash
# View security events in real-time
watch -n 5 'curl -s -H "Authorization: Bearer $ADMIN_TOKEN" http://localhost:8001/api/admin/security/events | jq'
```

---

## Step 9: Validate MTurk Integration (Sandbox)

### Test MTurk Cashout Flow

1. Login as test_user_01 (has 10,000 gems)
2. Request cashout: $5.00
3. Get redemption code
4. Submit to MTurk sandbox HIT
5. Verify payment in MTurk sandbox account

**Commands**:
```bash
# Check MTurk sandbox balance
python backend/check_mturk_balance.py

# Create cashout HIT (if using standing HIT system)
python backend/create_standing_hit.py

# Monitor cashouts
python backend/diagnose_cashout_system.py
```

---

## Step 10: Document Findings

### Create Security Report

**Template**: `SECURITY_TEST_RESULTS.md`

```markdown
# Security Testing Results - Deployment to 100-120 Users

## Executive Summary
- Tests Run: [DATE]
- Environment: Local test (sandbox MTurk)
- Test Users: 20
- Tests Passed: X/Y
- Critical Issues: N
- Status: READY/NOT READY for production

## Critical Findings

### 1. [Issue Title]
- Severity: High/Medium/Low
- Description: [what was found]
- Impact: [who is affected, what's the risk]
- Fix: [how to fix]
- Status: Fixed/Open

## Test Results Summary

### Authentication Security
- ✅ JWT token security: PASSED
- ✅ Rate limiting: PASSED
- ✅ Role-based access: PASSED
- ❌ Issue found: [describe]

### Payment Security
- ✅ Double payment prevention: PASSED
- ✅ Concurrent cashouts: PASSED
- ✅ Amount validation: PASSED

### Concurrency
- ✅ Race conditions: HANDLED
- ✅ 20 concurrent users: STABLE

### Data Privacy
- ✅ No data leakage: VERIFIED
- ✅ Cross-user isolation: VERIFIED

## Recommendations

1. [Recommendation 1]
2. [Recommendation 2]

## Approval

- [ ] All critical issues resolved
- [ ] All high-priority tests passed
- [ ] Manual penetration tests completed
- [ ] Load testing passed (20+ concurrent users)
- [ ] MTurk sandbox integration verified

**Approved for 100-120 user deployment**: YES/NO
**Approved by**: [NAME]
**Date**: [DATE]
```

---

## Troubleshooting

### Backend Won't Start

```bash
# Check port availability
lsof -i :8001

# Kill existing process if needed
kill -9 <PID>

# Check environment variables
python backend/check_env.py
```

### Tests Failing

```bash
# Run single test for debugging
pytest test_security_auth.py::TestJWTSecurity::test_expired_token_rejection -v -s

# Enable full traceback
pytest test_security_auth.py -v --tb=long

# Run with print statements visible
pytest test_security_auth.py -v -s
```

### Database Issues

```bash
# Reset test database
rm backend/test_group_chat.db
cd backend && python -m alembic upgrade head
```

---

## Success Criteria

Before deploying to 100-120 real users:

- [ ] All automated tests passing (0 failures)
- [ ] All manual penetration tests completed
- [ ] No critical vulnerabilities found
- [ ] Load testing passed with 20+ concurrent users
- [ ] Configuration validator passes with 0 errors
- [ ] Security monitoring system operational
- [ ] MTurk sandbox integration working
- [ ] Documentation complete (SECURITY_TEST_RESULTS.md)

---

## Timeline

**Week 1**: Setup & Automated Tests (Steps 1-4)
**Week 2**: Manual Testing & User Simulation (Steps 5-7)
**Week 3**: MTurk Integration & Monitoring (Steps 8-9)
**Week 4**: Documentation & Final Approval (Step 10)

---

## Contact

For security issues found during testing:
- Document in SECURITY_TEST_RESULTS.md
- Mark as critical/high/medium/low
- Create fix plan before production deployment

