# Manual Penetration Testing Procedures

## Overview
This document provides step-by-step procedures for manual security testing of the AI Group Chat application before deployment to 100-120 users.

**Test Environment**: Localhost (backend on port 8001, frontend on port 5173)

---

## Phase 1: Authentication Attack Vectors

### Test 1.1: JWT Token Manipulation

**Objective**: Verify JWT tokens cannot be tampered with

**Steps**:
1. Login as regular user at `http://localhost:5173`
2. Open browser DevTools → Application → Local Storage
3. Copy the JWT token
4. Go to https://jwt.io and decode the token
5. Modify payload (change `sub` to admin user's UUID)
6. Try to use modified token in API request

**Expected Result**: 401 Unauthorized (signature invalid)

**Command**:
```bash
# Use modified token
curl -H "Authorization: Bearer <MODIFIED_TOKEN>" http://localhost:8001/api/auth/me
```

### Test 1.2: Token Reuse After Logout

**Steps**:
1. Login and save token
2. Use token to access `/api/auth/me` (should work)
3. Logout
4. Try to reuse same token

**Expected Result**: 401 Unauthorized (token blacklisted)

**Commands**:
```bash
# Login
TOKEN=$(curl -X POST http://localhost:8001/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"user_id":"test_user","password":"test_password"}' | jq -r '.access_token')

# Use token
curl -H "Authorization: Bearer $TOKEN" http://localhost:8001/api/auth/me

# Logout
curl -X POST -H "Authorization: Bearer $TOKEN" http://localhost:8001/api/auth/logout

# Try reuse (should fail)
curl -H "Authorization: Bearer $TOKEN" http://localhost:8001/api/auth/me
```

### Test 1.3: MTurk Worker ID Spoofing

**Steps**:
1. Capture legitimate MTurk registration request
2. Modify `worker_id` to another worker's ID
3. Attempt registration

**Expected Result**: Should work for different assignment_id, but assignment uniqueness prevents duplicate payouts

**Command**:
```bash
curl -X POST http://localhost:8001/api/auth/mturk-register \
  -H "Content-Type: application/json" \
  -d '{
    "worker_id": "AAAAAAAAAAAA",
    "assignment_id": "3" + random_30_chars,
    "hit_id": "H1234567890"
  }'
```

### Test 1.4: Expired Token Usage

**Steps**:
1. Set `ACCESS_TOKEN_EXPIRE_HOURS = 0.001` in auth.py (very short expiry)
2. Login and get token
3. Wait 10 seconds
4. Try to use token

**Expected Result**: 401 Unauthorized (token expired)

---

## Phase 2: Payment System Attacks

### Test 2.1: Race Condition - Concurrent Cashouts

**Objective**: Verify gems aren't double-spent in concurrent requests

**Steps**:
1. Create user with 5000 gems ($5.00)
2. Open 5 browser tabs, all logged in as same user
3. In all tabs simultaneously, request $3.00 cashout (needs 3000 gems each)
4. Click "Cash Out" in all tabs at same time

**Expected Result**: 
- Only 1 cashout succeeds (first one to acquire DB lock)
- Other 4 fail with "Insufficient gems" or "Pending cashout exists"
- Final gem balance: 2000 gems (5000 - 3000)

**Automated Test**:
```bash
# Run concurrent cashout test
cd backend
pytest tests/test_security_payments.py::TestGemBalanceIntegrity::test_concurrent_cashout_requests_handled_safely -v
```

### Test 2.2: Parameter Tampering - Cashout Amount

**Objective**: Verify cashout amount cannot be manipulated

**Steps**:
1. Initiate cashout for $2.00
2. Intercept request using Browser DevTools → Network tab
3. Right-click request → "Edit and Resend"
4. Change `"amount_usd": 2.00` to `"amount_usd": 1000.00`
5. Send modified request

**Expected Result**: 
- Fails with "Insufficient gems" (user doesn't have 1,000,000 gems)
- OR succeeds but deducts all available gems (atomic transaction)

### Test 2.3: Double Redemption Attack

**Steps**:
1. Create cashout and get redemption code
2. Submit code to MTurk HIT (dev mode: assignment_id="DEV_TEST_123")
3. Save the redemption request
4. Try to submit same code again with different assignment_id

**Expected Result**: Second submission fails with "already redeemed"

**Command**:
```bash
# First redemption
curl -X POST http://localhost:8001/api/cashout/redeem \
  -H "Content-Type: application/json" \
  -d '{
    "redemption_code": "<CODE>",
    "worker_id": "A1234567890ABC",
    "assignment_id": "DEV_TEST_123",
    "hit_id": "H123"
  }'

# Second redemption (should fail)
curl -X POST http://localhost:8001/api/cashout/redeem \
  -H "Content-Type: application/json" \
  -d '{
    "redemption_code": "<SAME_CODE>",
    "worker_id": "A1234567890ABC",
    "assignment_id": "DEV_TEST_456",
    "hit_id": "H123"
  }'
```

### Test 2.4: MTurk Assignment Replay

**Steps**:
1. Register with assignment_id "3123456..."
2. Try to register again with same assignment_id

**Expected Result**: 409 Conflict - assignment already used

---

## Phase 3: Concurrent Session Attacks

### Test 3.1: Multi-Tab Login Conflicts

**Steps**:
1. Open 2 browser tabs
2. Tab 1: Login as `user_a`
3. Tab 2: Login as `user_b` (without logging out in Tab 1)
4. Check localStorage in both tabs

**Expected Result**: 
- Cross-tab synchronization triggers
- Both tabs show same user (last login wins)
- Old token is cleared

**Verification**:
- Open DevTools → Application → Local Storage
- Check `login_event` storage event is triggered

### Test 3.2: Room Overflow Attack

**Steps**:
1. Create room with `max_humans = 2`
2. Have 5 users try to join simultaneously
3. Monitor who gets in

**Expected Result**: Only first 2 users assigned, others rejected

**Commands** (requires 5 terminal windows):
```bash
# Terminal 1-5: Join room simultaneously
for i in {1..5}; do
  curl -X POST http://localhost:8001/api/rooms/join/ROOMCODE \
    -H "Authorization: Bearer <USER_${i}_TOKEN>" \
    -H "Content-Type: application/json" \
    -d '{"player_id":"Player 1"}' &
done
wait
```

### Test 3.3: Reconnection Hijacking

**Steps**:
1. User A joins game as "Player 1"
2. User A disconnects (close tab)
3. User B tries to connect as "Player 1" in same room

**Expected Result**: 
- User B should NOT be able to take User A's slot
- `player_user_map` preserves User A's assignment

---

## Phase 4: Data Leakage Investigation

### Test 4.1: API Response Analysis

**Steps**:
1. Make requests to all endpoints
2. Inspect responses for sensitive data

**Check For**:
- Password hashes
- JWT secret keys
- AWS credentials
- Internal file paths
- Stack traces
- Database table/column names

**Commands**:
```bash
# Test error responses
curl http://localhost:8001/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"user_id":"admin","password":"wrong"}' | jq

# Should return generic error, not "User not found in users table"
```

### Test 4.2: Browser Storage Inspection

**Steps**:
1. Login and play game
2. Open DevTools → Application
3. Inspect Local Storage
4. Inspect Session Storage
5. Inspect Cookies

**Check For**:
- Unencrypted sensitive data
- MTurk worker IDs in cleartext (acceptable if user's own)
- Other users' data
- Admin credentials

### Test 4.3: Network Traffic Analysis

**Steps**:
1. Open DevTools → Network tab
2. Clear network log
3. Play complete game session
4. Inspect all requests/responses

**Check For**:
- Player identity leaks during game
- Other players' user_ids exposed
- Predictable completion keys
- Session tokens sent over HTTP (should be HTTPS in production)

**Specific Checks**:
```
WebSocket messages should show:
✅ "Player 3 says..." (pseudonymized)
❌ "user_abc123 says..." (real identity)
```

---

## Phase 5: Rate Limiting Verification

### Test 5.1: Login Brute-Force Protection

**Steps**:
1. Attempt 10 failed logins rapidly
2. Verify rate limiting triggers

**Command**:
```bash
for i in {1..10}; do
  echo "Attempt $i:"
  curl -X POST http://localhost:8001/api/auth/login \
    -H "Content-Type: application/json" \
    -d "{\"user_id\":\"admin\",\"password\":\"wrong$i\"}"
  echo ""
done
```

**Expected**: Request 6+ should return 429 Too Many Requests

### Test 5.2: Registration Spam Protection

**Command**:
```bash
for i in {1..5}; do
  curl -X POST http://localhost:8001/api/auth/register \
    -H "Content-Type: application/json" \
    -d "{\"user_id\":\"spam_user_$i\",\"password\":\"password\"}"
done
```

**Expected**: Request 4+ should return 429

### Test 5.3: Cashout Spam Protection

**Steps**:
1. Login as user with 20,000 gems
2. Make 6 cashout requests rapidly

**Expected**: Request 6+ should return 429

---

## Phase 6: SQL Injection Tests

### Test 6.1: Login SQL Injection

**Payloads**:
```bash
# Test various SQL injection payloads
curl -X POST http://localhost:8001/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"user_id":"admin'\'' OR '\''1'\''='\''1","password":"any"}'

curl -X POST http://localhost:8001/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"user_id":"admin'\''; DROP TABLE users; --","password":"any"}'
```

**Expected**: 400/401 errors, NOT SQL errors, NOT successful login

### Test 6.2: MTurk Parameter Injection

**Command**:
```bash
curl -X POST http://localhost:8001/api/auth/mturk-register \
  -H "Content-Type: application/json" \
  -d '{
    "worker_id": "A123'\''; DROP TABLE cashout_transactions; --",
    "assignment_id": "31234567890123456789012345678901",
    "hit_id": "H123"
  }'
```

**Expected**: 400 Bad Request (invalid format), NOT SQL error

---

## Phase 7: Authorization Bypass Tests

### Test 7.1: Admin Endpoint Access

**Steps**:
1. Login as regular user
2. Try to access admin endpoints

**Commands**:
```bash
# Get regular user token
TOKEN=$(curl -X POST http://localhost:8001/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"user_id":"regular_user","password":"password"}' | jq -r '.access_token')

# Try admin endpoints
curl -H "Authorization: Bearer $TOKEN" http://localhost:8001/api/admin/sessions
curl -H "Authorization: Bearer $TOKEN" http://localhost:8001/api/admin/users
```

**Expected**: All return 403 Forbidden

### Test 7.2: Other User's Wallet Access

**Steps**:
1. Get User A's token
2. Try to access User B's wallet/cashout data via API manipulation

**Expected**: API should enforce user_id from token, not from request

---

## Phase 8: CORS & CSRF Tests

### Test 8.1: Cross-Origin Request Blocking

**Steps**:
1. Create simple HTML file with fetch request
2. Host on different origin (e.g., `python -m http.server 8080`)
3. Try to call API from that origin

**HTML Test File**:
```html
<script>
fetch('http://localhost:8001/api/health')
  .then(r => r.json())
  .then(console.log)
  .catch(console.error);
</script>
```

**Expected**: CORS error (blocked by browser)

### Test 8.2: HTTPS Enforcement (Production)

**Check**:
```bash
# In production, verify CORS validation
# If HTTP origin in CORS_ALLOWED_ORIGINS in production mode:
# Should fail at startup with ValueError
```

---

## Testing Checklist

### Authentication (8 tests)
- [ ] Expired token rejected
- [ ] Invalid signature detected
- [ ] Token tampering detected
- [ ] Token replay after logout blocked
- [ ] MTurk worker ID validation
- [ ] Assignment ID uniqueness
- [ ] Preview mode handled correctly
- [ ] Rate limiting on registration

### Payment Security (10 tests)
- [ ] Double payment prevented (assignment ID)
- [ ] Redemption code single-use enforced
- [ ] Payment flag prevents duplicate
- [ ] Gem balance validated
- [ ] Minimum cashout enforced
- [ ] Negative amount rejected
- [ ] Expired code rejected
- [ ] Cancelled code rejected
- [ ] Concurrent cashout race condition handled
- [ ] Gems deducted atomically

### Concurrent Sessions (6 tests)
- [ ] Multiple rooms per user allowed
- [ ] Room state isolation verified
- [ ] Unique room codes generated
- [ ] Player ID cannot be hijacked
- [ ] Player-user map enforced
- [ ] Room capacity limits work

### Data Privacy (8 tests)
- [ ] Password hashes not in responses
- [ ] Error messages generic
- [ ] Session data doesn't leak user IDs
- [ ] Users can't access other wallets
- [ ] Users can't see other cashout history
- [ ] Worker IDs not visible to others
- [ ] JWT secret not exposed
- [ ] AWS credentials not exposed

### Rate Limiting (4 tests)
- [ ] Login brute-force prevented
- [ ] Registration spam prevented
- [ ] Cashout spam prevented
- [ ] MTurk registration spam prevented

### Total: 36 manual test cases

---

## High-Priority Attack Scenarios

### Scenario A: Payment Fraud Attempt

**Attack**: Hacker tries to cash out more money than they have

**Steps**:
1. User has 100 gems ($0.10)
2. Intercept cashout request
3. Modify amount to $100.00
4. Submit

**Test**:
```bash
curl -X POST http://localhost:8001/api/wallet/cashout \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"amount_usd": 100.00}'
```

**Expected**: 400 Bad Request - Insufficient gems

### Scenario B: Concurrent Exploitation

**Attack**: User opens multiple tabs to exploit race condition

**Steps**:
1. User has 5000 gems
2. Open 10 tabs
3. Request $3 cashout in all tabs simultaneously
4. Check if more than 5000 gems deducted

**Expected**: Only ONE succeeds, balance = 2000 gems

### Scenario C: Admin Privilege Escalation

**Attack**: Regular user tries to approve their own payment

**Steps**:
1. Complete game session
2. Get session ID
3. Try to call `/api/admin/sessions/{session_id}/approve-payment`

**Expected**: 403 Forbidden

---

## Automated Test Execution

```bash
# Run all security tests
cd backend
pytest tests/test_security_*.py -v

# Run specific test categories
pytest tests/test_security_auth.py -v
pytest tests/test_security_payments.py -v
pytest tests/test_security_concurrency.py -v
pytest tests/test_security_data_privacy.py -v

# Run load tests (marked as slow)
pytest tests/test_security_load.py -v -m slow

# Generate coverage report
pytest tests/test_security_*.py --cov=backend --cov-report=html
```

---

## Documentation

Results should be documented in `SECURITY_TEST_RESULTS.md` with:
- Test name
- Pass/Fail status
- Evidence (screenshots, curl outputs)
- Vulnerabilities found
- Severity rating
- Fix recommendations

