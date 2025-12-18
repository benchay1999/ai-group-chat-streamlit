# Quick Start: Security Testing

## For Immediate Testing

This guide helps you quickly run the security test suite on your local backup environment.

---

## Step 1: Setup (5 minutes)

```bash
cd /home/wschay/1125/ai-group-chat-streamlit

# 1. Create test environment
cp .env .env.test

# 2. Edit .env.test to use sandbox and local settings
#    - MTURK_ENVIRONMENT=sandbox
#    - DATABASE_URL=sqlite+aiosqlite:///./test_group_chat.db
#    - CORS_ALLOWED_ORIGINS=http://localhost:5173

# 3. Initialize test database
cd backend
python -m alembic upgrade head
```

---

## Step 2: Start Test Backend (1 minute)

```bash
# Terminal 1: Start backend on port 8001
cd backend
bash & conda activate group-chat & uvicorn main:app --reload --port 8001 --env-file ../.env.test
```

**Verify**:
```bash
# In Terminal 2:
curl http://localhost:8001/api/health
# Should return: {"status":"healthy"}
```

---

## Step 3: Start Frontend (1 minute)

```bash
# Terminal 3: Start frontend
cd frontend

# Create local env
echo "VITE_API_URL=http://localhost:8001" > .env.local
echo "VITE_WS_URL=ws://localhost:8001" >> .env.local

# Start
npm run dev
# Opens on http://localhost:5173
```

---

## Step 4: Run Automated Tests (10 minutes)

```bash
# Terminal 4: Run security test suite
cd backend/tests

# Install test dependencies
bash & conda activate group-chat & pip install pytest pytest-asyncio aiohttp httpx

# Validate configuration
bash & conda activate group-chat & python validate_production_config.py --env-file ../../.env.test

# Run all tests
bash & conda activate group-chat & pytest test_security_auth.py -v
bash & conda activate group-chat & pytest test_security_payments.py -v
bash & conda activate group-chat & pytest test_security_concurrency.py -v
bash & conda activate group-chat & pytest test_security_data_privacy.py -v
```

---

## Step 5: Create Test Users (2 minutes)

```bash
# Create 20 test users with gems
cd backend
bash & conda activate group-chat & python << 'EOF'
import asyncio
from database import async_session_maker, User, UserRole
from auth import hash_password
import uuid

async def create_users():
    async with async_session_maker() as session:
        for i in range(20):
            user = User(
                id=uuid.uuid4(),
                user_id=f'user_{i:02d}',
                password_hash=hash_password('test123'),
                role=UserRole.USER,
                gem_balance=10000,
                mturk_worker_id=f'A{str(i).zfill(13)}'
            )
            session.add(user)
        await session.commit()
        print(f'✅ Created 20 test users (user_00 to user_19, password: test123)')

asyncio.run(create_users())
EOF
```

---

## Step 6: Manual Penetration Tests (20 minutes)

Open `backend/tests/MANUAL_PENETRATION_TESTING.md` and execute:

### Priority 1: Payment Security

1. **Concurrent Cashout Test**:
   - Login as user_00 at http://localhost:5173
   - Open 5 browser tabs
   - Request $8 cashout in all tabs simultaneously
   - ✅ PASS: Only 1 succeeds
   - ❌ FAIL: Multiple succeed (critical issue!)

2. **Amount Tampering**:
   - Request $2 cashout
   - Intercept in DevTools Network tab
   - Change amount to $1000
   - ✅ PASS: Rejected with "insufficient gems"

### Priority 2: Authentication

3. **Token Tampering**:
   - Login, copy JWT from localStorage
   - Modify payload at jwt.io
   - Try to use modified token
   - ✅ PASS: 401 Unauthorized

4. **Rate Limit Test**:
   ```bash
   # Run 10 login attempts
   for i in {1..10}; do
     curl -X POST http://localhost:8001/api/auth/login \
       -H "Content-Type: application/json" \
       -d '{"user_id":"admin","password":"wrong'$i'"}'
   done
   ```
   - ✅ PASS: Request 6+ gets 429

---

## Step 7: Load Testing (30 minutes)

```bash
# Run load test
cd backend/tests
bash & conda activate group-chat & pytest test_security_load.py -v -m slow
```

**Expected**: Handle 100+ concurrent requests without errors

---

## Step 8: Record Results

Fill in `SECURITY_TEST_RESULTS.md` with:
- ✅ or ❌ for each test
- Screenshots of key tests
- Any vulnerabilities found
- Fix recommendations

---

## Quick Command Reference

```bash
# Start backend
bash & conda activate group-chat & cd backend && uvicorn main:app --reload --port 8001 --env-file ../.env.test

# Start frontend  
bash & conda activate group-chat & cd frontend && npm run dev

# Run tests
bash & conda activate group-chat & cd backend/tests && pytest test_security_*.py -v

# Validate config
bash & conda activate group-chat & cd backend/tests && python validate_production_config.py

# Check backend health
curl http://localhost:8001/api/health

# Login as test user
curl -X POST http://localhost:8001/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"user_id":"user_00","password":"test123"}'
```

---

## Common Issues

### Backend won't start
```bash
# Kill existing process
pkill -f "uvicorn main:app"

# Check port
lsof -i :8001
```

### Tests failing
```bash
# Run single test with details
bash & conda activate group-chat & pytest test_security_auth.py::TestJWTSecurity::test_expired_token_rejection -v -s
```

### Database locked
```bash
# Reset test database
rm backend/test_group_chat.db
cd backend && python -m alembic upgrade head
```

---

## Success Criteria

✅ **Ready for 100-120 user deployment when**:

1. All automated tests pass (37 tests)
2. All manual penetration tests pass (36 tests)
3. Load testing successful (100+ concurrent requests)
4. No critical vulnerabilities found
5. Configuration validator passes
6. Results documented in SECURITY_TEST_RESULTS.md

---

## Timeline Estimate

- **Setup**: 10 minutes
- **Automated tests**: 30 minutes  
- **Manual tests**: 1-2 hours
- **Load testing**: 30 minutes
- **Documentation**: 30 minutes

**Total**: 3-4 hours for comprehensive security validation

---

**Start testing now**: Follow Step 1 above! 🚀

