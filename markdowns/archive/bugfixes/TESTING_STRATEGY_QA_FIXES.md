# Testing Strategy for QA Corner Case Fixes

This document outlines the testing strategy for the 9 high-priority corner case fixes implemented based on the QA analysis.

## Overview

All 9 high-priority fixes have been implemented. This document describes how to test each fix to ensure correctness and prevent regressions.

---

## Fix 1.1: Vote Completion Race Condition

**Issue**: Multiple endpoints (API + WebSocket) could call `complete_voting()` simultaneously.

**Implementation**: Added `voting_completed` atomic flag in room state.

**Files Changed**:
- `backend/services/game_coordinator.py` (lines 866-901, 193-196)

**Testing Strategy**:

### Manual Test
1. Create a multi-human game with 3 players
2. Have all 3 players submit votes simultaneously (within 100ms)
3. Verify only one `complete_voting` execution occurs (check logs for "Voting already completed" message)
4. Confirm gems credited only once per player

### Automated Test
```python
async def test_concurrent_vote_completion():
    """Test that concurrent vote submissions don't duplicate game completion."""
    room_code = create_test_room(max_humans=3)
    
    # Simulate 3 concurrent vote submissions
    tasks = [
        cast_vote_api(room_code, "Player1", ["Player2", "Player3"]),
        cast_vote_api(room_code, "Player2", ["Player1", "Player3"]),
        cast_vote_api(room_code, "Player3", ["Player1", "Player2"]),
    ]
    
    results = await asyncio.gather(*tasks)
    
    # Verify only one completion occurred
    assert sum(1 for r in results if r.get('game_completed')) == 1
    assert room['voting_completed'] == True
```

### Concurrency Test Tool
Use `locust` or `k6` to generate 100+ concurrent votes and verify no duplicate completions.

---

## Fix 2.2: WebSocket Reconnection State Recovery

**Issue**: WebSocket reconnects but doesn't fetch current game state, causing desync.

**Implementation**: Added `onReconnect` callback to `useWebSocket` hook that fetches fresh state.

**Files Changed**:
- `frontend/src/hooks/useWebSocket.js` (lines 12-32, 77)
- `frontend/src/pages/GamePage.jsx` (lines 376-401)

**Testing Strategy**:

### Manual Test
1. Join a game in discussion phase
2. Disconnect WiFi for 10 seconds
3. During disconnect, discussion phase ends → voting starts
4. Reconnect WiFi
5. Verify client state updates to "Voting" phase immediately
6. Verify all missed messages appear in chat

### Automated Test (Playwright/Puppeteer)
```javascript
test('WebSocket reconnection recovers state', async ({ page }) => {
  await page.goto('/game/ABC123');
  
  // Simulate network disconnect
  await page.context().setOffline(true);
  await page.waitForTimeout(15000); // 15s disconnect
  
  // Reconnect
  await page.context().setOffline(false);
  
  // Verify state recovered within 3 seconds
  await page.waitForSelector('[data-phase="Voting"]', { timeout: 3000 });
});
```

### Network Simulation Tool
Use `toxiproxy` to simulate network interruptions:
```bash
toxiproxy-cli toxic add --type latency --toxicName lag --attribute latency=5000 backend
```

---

## Fix 2.5: Ghost Typing Indicators Cleanup

**Issue**: AI typing indicator gets stuck if phase changes mid-generation.

**Implementation**: Enhanced finally block to always broadcast typing stop event.

**Files Changed**:
- `backend/services/game_coordinator.py` (lines 715-747)

**Testing Strategy**:

### Manual Test
1. Start discussion phase with AI agents
2. Wait for AI to start typing (typing indicator appears)
3. Force phase change before message completes (admin tool or timer manipulation)
4. Verify typing indicator disappears within 1 second
5. Confirm no ghost "Player X is typing..." remains

### Automated Test
```python
async def test_typing_indicator_cleanup_on_phase_change():
    """Test typing indicator cleanup when phase changes."""
    room_code = create_test_room()
    
    # Trigger AI response
    send_human_message(room_code, "Player1", "Hello")
    
    # Wait for AI typing to start
    await asyncio.sleep(0.5)
    assert "Player2" in rooms[room_code]['typing_players']
    
    # Force phase change
    async with room_locks[room_code]:
        rooms[room_code]['state']['phase'] = Phase.VOTING
    
    # Wait for cleanup
    await asyncio.sleep(2)
    
    # Verify typing indicator cleared
    assert "Player2" not in rooms[room_code].get('typing_players', set())
```

---

## Fix 4.2: All Players Permanently Left

**Issue**: Room stays alive forever if all players explicitly leave.

**Implementation**: Detect all-left scenario and terminate room immediately.

**Files Changed**:
- `backend/routers/rooms.py` (lines 336-366)

**Testing Strategy**:

### Manual Test
1. Create multi-human room with 3 players
2. Have Player 1 leave (explicit /leave API call)
3. Have Player 2 leave
4. Have Player 3 leave
5. Verify room is deleted immediately after last player leaves
6. Confirm "room_terminated" broadcast sent
7. Check `rooms` dict to confirm room removed

### Automated Test
```python
async def test_all_players_leave_terminates_room():
    """Test room termination when all players leave."""
    room_code = create_test_room(max_humans=3)
    join_player(room_code, "Player1")
    join_player(room_code, "Player2")
    join_player(room_code, "Player3")
    
    # All players leave
    leave_room(room_code, "Player1")
    leave_room(room_code, "Player2")
    leave_room(room_code, "Player3")
    
    # Verify room deleted
    assert room_code not in rooms
    assert room_code not in room_locks
```

---

## Fix 4.6: Concurrent Gem Deductions Database Lock

**Issue**: Two games could deduct gems from same user simultaneously.

**Implementation**: Added `SELECT FOR UPDATE` row-level locking.

**Files Changed**:
- `backend/services/stats_service.py` (line 643)

**Testing Strategy**:

### Manual Test
1. User joins two multi-human games simultaneously
2. Both games complete at nearly the same time
3. Verify gem balance updates atomically (no race condition)
4. Confirm final balance matches expected value

### Automated Test
```python
async def test_concurrent_gem_deductions():
    """Test concurrent gem deductions don't cause race condition."""
    user = create_test_user(gem_balance=1000)
    
    # Create two games with same user
    room1 = create_staked_room(stake=50)
    room2 = create_staked_room(stake=50)
    
    # Complete both games concurrently
    async with async_session_maker() as db:
        task1 = deduct_stakes(room1, db)
        task2 = deduct_stakes(room2, db)
        
        results = await asyncio.gather(task1, task2)
        await db.commit()
    
    # Verify balance
    refreshed_user = await db.get(User, user.id)
    assert refreshed_user.gem_balance == 900  # 1000 - 50 - 50
```

### Load Test
Use `pytest-xdist` to run 100 concurrent gem operations:
```bash
pytest -n 100 test_concurrent_gems.py
```

---

## Fix 6.2: Session Save Retry Logic

**Issue**: Database commit fails → session stats lost forever.

**Implementation**: Added retry mechanism with exponential backoff.

**Files Changed**:
- `backend/services/stats_service.py` (lines 30-77, 918-933)

**Testing Strategy**:

### Manual Test
1. Temporarily make database unavailable (stop PostgreSQL)
2. Complete a game
3. Restart database within 10 seconds
4. Verify session saves successfully on retry
5. Confirm gem rewards credited

### Automated Test
```python
async def test_session_save_retry():
    """Test retry logic for database failures."""
    room_code = create_test_room()
    state = complete_test_game(room_code)
    
    # Mock database to fail first 2 attempts
    with patch('backend.services.stats_service.retry_async_operation') as mock_retry:
        mock_retry.side_effect = [
            OperationalError("DB unavailable"),  # Attempt 1
            OperationalError("DB unavailable"),  # Attempt 2
            None  # Attempt 3 succeeds
        ]
        
        await save_session_stats(room_code, state)
        
        # Verify 3 attempts made
        assert mock_retry.call_count == 3
```

### Database Failure Simulation
Use `toxiproxy` to inject database latency/failures:
```bash
toxiproxy-cli toxic add --type timeout --toxicName db_timeout postgres
```

---

## Fix 7.4: API Key Health Tracking

**Issue**: All API keys saturated → new rooms created but AI never responds.

**Implementation**: Track key health and reject room creation if all keys unhealthy.

**Files Changed**:
- `backend/api_key_manager.py` (entire file enhanced)

**Testing Strategy**:

### Manual Test
1. Configure with 2 API keys
2. Simulate rate limit on both keys (mock or actual)
3. Attempt to create new room
4. Verify error: "All API keys currently unhealthy"
5. Wait 5 minutes (health check interval)
6. Verify keys auto-recover and room creation succeeds

### Automated Test
```python
def test_api_key_health_tracking():
    """Test API key health prevents room creation when all unhealthy."""
    manager = APIKeyManager(["key1", "key2"])
    
    # Report both keys as rate limited
    manager.report_key_failure(0, is_rate_limit=True)
    manager.report_key_failure(1, is_rate_limit=True)
    
    # Verify has_healthy_keys returns False
    assert manager.has_healthy_keys() == False
    
    # Verify get_next_api_key raises error
    with pytest.raises(APIKeyManagerError, match="All API keys are currently unhealthy"):
        manager.get_next_api_key()
    
    # Simulate recovery (5 minutes later)
    with patch('time.time', return_value=time.time() + 301):
        assert manager.has_healthy_keys() == True
```

### Load Test
Use `locust` to create 1000 rooms rapidly and verify:
- Keys distributed evenly
- Unhealthy keys skipped
- Room creation fails gracefully when all keys saturated

---

## Fix 9.2: Timer Using Monotonic Clock

**Issue**: System clock changes affect game timers.

**Implementation**: Replaced `time.time()` with `time.monotonic()`.

**Files Changed**:
- `backend/services/game_coordinator.py` (lines 60-73, 196-212)
- `backend/routers/rooms.py` (line 377)
- `backend/routers/websocket.py` (line 332)

**Testing Strategy**:

### Manual Test
1. Start discussion phase
2. After 30 seconds, manually change system clock forward by 1 hour
3. Verify timer continues counting down normally (not affected)
4. Phase transitions at correct elapsed time (not wall clock time)

### Automated Test
```python
async def test_timer_immune_to_clock_changes():
    """Test timer uses monotonic clock, immune to system time changes."""
    room_code = create_test_room(discussion_duration=60)
    
    # Start discussion
    start_discussion(room_code)
    
    # Simulate system clock jump (mock time.time but not time.monotonic)
    with patch('time.time', return_value=time.time() + 3600):
        # Wait 10 actual seconds
        await asyncio.sleep(10)
        
        # Timer should show ~50s remaining (not affected by time.time jump)
        timer = get_timer(room_code)
        assert 48 <= timer <= 52
```

### System Clock Manipulation Test
```bash
# Requires root/sudo
sudo date -s "+1 hour"
# Run game, verify timer unaffected
sudo ntpdate -s time.nist.gov  # Reset clock
```

---

## Fix 10.2: Stake Economics with Forced Minimum

**Issue**: Wealth disparity in stake amounts leads to unfair economics.

**Implementation**: Percentage-based with forced minimum (250 gems).

**Files Changed**:
- `backend/services/room_management.py` (line 127)
- `backend/routers/rooms.py` (lines 716-732, 778-800)

**Testing Strategy**:

### Manual Test
1. User A (10,000 gems) creates 50% stake room
2. User B (500 gems) tries to join
3. Verify User B blocked (< 250 gems minimum)
4. User C (1,000 gems) joins successfully
5. Verify User A stakes max(5000, 250) = 5000 gems
6. Verify User C stakes max(500, 250) = 500 gems
7. Minimum stake = 500 gems
8. Winner gets base + stake pool

### Automated Test
```python
def test_stake_economics_forced_minimum():
    """Test stake percentage with forced minimum."""
    user_rich = create_user(gems=10000)
    user_poor = create_user(gems=200)
    user_mid = create_user(gems=1000)
    
    room = create_staked_room(stake_percentage=50, min_gems=250)
    
    # Poor user blocked
    result = join_room(room, user_poor)
    assert result['success'] == False
    assert "Insufficient gems" in result['error']
    
    # Rich and mid users join
    join_room(room, user_rich)
    join_room(room, user_mid)
    
    # Verify stakes
    assert room['player_stakes']['PlayerRich'] == 5000  # max(50% of 10000, 250)
    assert room['player_stakes']['PlayerMid'] == 500   # max(50% of 1000, 250)
    assert room['minimum_stake'] == 500
```

---

## Overall Testing Recommendations

### 1. Unit Tests
Create unit tests for each fix in `backend/tests/test_qa_fixes.py`:
```bash
pytest backend/tests/test_qa_fixes.py -v
```

### 2. Integration Tests
Test interactions between fixes in `backend/tests/test_integration_qa.py`:
```bash
pytest backend/tests/test_integration_qa.py -v --cov
```

### 3. End-to-End Tests
Use Playwright for E2E testing:
```bash
npx playwright test tests/e2e/qa-fixes.spec.js
```

### 4. Load Testing
Use Locust to simulate 100+ concurrent users:
```bash
locust -f tests/load/test_concurrent_games.py --headless -u 100 -r 10
```

### 5. Chaos Engineering
Use `toxiproxy` to inject failures:
- Network latency (500-2000ms)
- Connection drops (30% packet loss)
- Database timeouts (5s delay)
- API rate limits (429 errors)

### 6. Monitoring & Alerting
Set up monitoring for:
- Vote completion duplicates (should be 0)
- Ghost typing indicators (count over time)
- Database retry attempts (alert if >10/hour)
- API key health status (alert if all unhealthy)
- Orphaned rooms (all players left but room exists)

### 7. Regression Testing
Run full test suite before each deployment:
```bash
npm run test:all
pytest --cov=backend
npx playwright test
```

---

## Test Coverage Goals

| Fix | Unit Test Coverage | Integration Test | E2E Test | Load Test |
|-----|-------------------|------------------|----------|-----------|
| 1.1 | ✅ 100% | ✅ Required | ⚠️ Optional | ✅ Required |
| 2.2 | ✅ 100% | ✅ Required | ✅ Required | ⚠️ Optional |
| 2.5 | ✅ 100% | ✅ Required | ✅ Required | ⚠️ Optional |
| 4.2 | ✅ 100% | ✅ Required | ⚠️ Optional | ⚠️ Optional |
| 4.6 | ✅ 100% | ✅ Required | ⚠️ Optional | ✅ Required |
| 6.2 | ✅ 100% | ✅ Required | ⚠️ Optional | ⚠️ Optional |
| 7.4 | ✅ 100% | ✅ Required | ⚠️ Optional | ✅ Required |
| 9.2 | ✅ 100% | ✅ Required | ✅ Required | ⚠️ Optional |
| 10.2 | ✅ 100% | ✅ Required | ⚠️ Optional | ⚠️ Optional |

---

## Continuous Integration

Add to CI/CD pipeline (`.github/workflows/test.yml`):

```yaml
name: QA Fixes Tests
on: [push, pull_request]

jobs:
  test-qa-fixes:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - name: Run Unit Tests
        run: pytest backend/tests/test_qa_fixes.py --cov
      - name: Run Integration Tests
        run: pytest backend/tests/test_integration_qa.py
      - name: Run E2E Tests
        run: npx playwright test tests/e2e/qa-fixes.spec.js
      - name: Check Coverage
        run: |
          coverage report --fail-under=90
```

---

## Summary

All 9 high-priority fixes have comprehensive testing strategies covering:
- ✅ Unit tests for logic correctness
- ✅ Integration tests for component interactions
- ✅ E2E tests for user flows
- ✅ Load tests for concurrency issues
- ✅ Chaos engineering for failure scenarios

**Next Steps**:
1. Implement automated tests as outlined above
2. Set up CI/CD pipeline to run tests on each commit
3. Configure monitoring and alerting
4. Schedule regular load testing (weekly)
5. Perform security audit after all tests pass

