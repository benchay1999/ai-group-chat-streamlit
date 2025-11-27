# WebSocket Authentication Policy

**Purpose:** Define authentication policy for WebSocket connections  
**Target Scale:** 100-120 concurrent users  
**Current Status:** Optional authentication (guest play enabled)

---

## Current Implementation

### How It Works Now

WebSocket endpoint: `/ws/{room_code}/{player_id}`

**Query Parameters:**
- `token` (optional): JWT authentication token
- `mturk_context` (optional): MTurk worker information

**Behavior:**
```python
# backend/main.py line 1819
@app.websocket("/ws/{room_code}/{player_id}")
async def websocket_endpoint(websocket: WebSocket, room_code: str, player_id: str):
    token = websocket.query_params.get('token')  # Optional!
    
    if token:
        # Authenticated user - track for gems and MTurk
        user = await get_user_from_token(token)
        rooms[room_code]['player_user_map'][player_id] = str(user.id)
    else:
        # Anonymous user - can still play
        # No tracking, no gems, no MTurk integration
```

**Result:**
- ✅ Authenticated users: Get gems, tracked in database, MTurk integration
- ⚠️ Anonymous users: Can play but no rewards or tracking

---

## Policy Options

### Option 1: Keep Current (Guest Play Allowed)

**Pros:**
- Lower barrier to entry
- More players (anyone can try)
- Good for demos and public access

**Cons:**
- Anonymous users can abuse (spam, inappropriate behavior)
- Can't track all sessions
- Can't reward anonymous players
- Harder to enforce rate limits per user

**Use Case:** Public-facing application with optional registration

**Security Requirements:**
- ✅ Rate limiting by IP address (already implemented)
- ⚠️ WebSocket rate limiting (NEEDS IMPLEMENTATION)
- ✅ Input validation (already implemented)

**Implementation Needed:**
```python
# Add WebSocket rate limiting
websocket_rate_limiter = SimpleRateLimiter(max_requests=10, window_seconds=60)

# In WebSocket endpoint:
client_ip = websocket.client.host
if not websocket_rate_limiter.is_allowed(client_ip):
    await websocket.close(code=1008, reason="Rate limit exceeded")
    return
```

---

### Option 2: Require Authentication (Recommended for MTurk)

**Pros:**
- Full tracking of all users
- Better security (no anonymous spam)
- Required for MTurk integration
- Easier to enforce per-user limits

**Cons:**
- Higher barrier to entry
- All users must register before playing
- Less casual play

**Use Case:** MTurk research study or controlled environment

**Implementation:**
```python
# In WebSocket endpoint:
token = websocket.query_params.get('token')
if not token:
    await websocket.close(code=1008, reason="Authentication required")
    return

user = await get_user_from_token(token)
if not user:
    await websocket.close(code=1008, reason="Invalid token")
    return

# Continue with authenticated user...
```

**Frontend Changes Required:**
```javascript
// frontend/src/services/api.js
export const getWebSocketURL = (roomCode, playerId) => {
  const token = localStorage.getItem('access_token');
  
  if (!token) {
    // Redirect to login instead of allowing connection
    throw new Error('Authentication required');
  }
  
  return `${wsProtocol}://${baseURL}/ws/${roomCode}/${playerId}?token=${token}`;
};
```

---

### Option 3: Hybrid Approach (Limit Guest Features)

**Pros:**
- Balance between access and security
- Guests can try, must register for rewards
- Good for conversion (free trial → registered user)

**Cons:**
- More complex implementation
- Need separate rate limits for guests vs registered
- More testing required

**Implementation:**
```python
# In WebSocket endpoint:
token = websocket.query_params.get('token')
is_guest = not token

if is_guest:
    # Guest restrictions
    - Can join public rooms only
    - No gems earned
    - Stricter rate limits (5 messages/min vs 10/min)
    - Session not saved to database
else:
    # Authenticated user
    - Can join private + public rooms
    - Earn gems
    - Normal rate limits
    - Session saved for tracking
```

---

## Recommendation for 100-120 Users

### If MTurk Research Study: **Option 2 (Require Authentication)**

**Rationale:**
- Need to track all participants
- Need to pay participants (requires authentication)
- Research integrity requires accountability
- Known user population (recruited MTurk workers)

**Action Items:**
1. Update WebSocket endpoint to require authentication
2. Update frontend to enforce login before game
3. Add clear error message: "Please log in to play"
4. Test with MTurk worker registration flow

---

### If Public Application: **Option 1 (Guest Play) + WebSocket Rate Limiting**

**Rationale:**
- Maximize participation
- Good for demos and organic growth
- Can convert guests to registered users

**Action Items:**
1. Implement WebSocket rate limiting by IP
2. Add connection monitoring (max connections per IP)
3. Add abuse detection (spam messages, disconnect/reconnect spam)
4. Encourage registration for rewards

---

## Implementation: WebSocket Rate Limiting (Option 1)

If choosing to keep guest play, implement this:

```python
# In backend/main.py, add to rate limiters section:
websocket_rate_limiter = SimpleRateLimiter(max_requests=20, window_seconds=60)
websocket_connection_limiter = SimpleRateLimiter(max_requests=5, window_seconds=60)

@app.websocket("/ws/{room_code}/{player_id}")
async def websocket_endpoint(websocket: WebSocket, room_code: str, player_id: str):
    client_ip = websocket.client.host
    
    # Check connection rate limit
    if not websocket_connection_limiter.is_allowed(client_ip):
        log_rate_limit_violation(client_ip, "WebSocket connection")
        await websocket.close(code=1008, reason="Too many connections. Please wait.")
        return
    
    await websocket.accept()
    
    # Get authentication status
    token = websocket.query_params.get('token')
    user_id = None
    is_authenticated = False
    
    if token:
        try:
            user = await get_user_from_token(token)
            if user:
                user_id = str(user.id)
                is_authenticated = True
        except:
            pass
    
    # Apply stricter rate limits for anonymous users
    if is_authenticated:
        message_rate_limit = 10  # messages per minute
    else:
        message_rate_limit = 5   # stricter for guests
    
    # ... rest of WebSocket logic
```

---

## Testing Authentication Policy

### Test Case 1: Authenticated User
```bash
# 1. Register user
curl -X POST http://localhost:8000/api/auth/register \
  -H "Content-Type: application/json" \
  -d '{"user_id":"test_user","password":"TestPass1234!"}'

# 2. Login
TOKEN=$(curl -X POST http://localhost:8000/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"user_id":"test_user","password":"TestPass1234!"}' \
  | jq -r '.access_token')

# 3. Connect WebSocket with token
wscat -c "ws://localhost:8000/ws/TEST/You?token=$TOKEN"

# Expected: Connection successful, user tracked
```

### Test Case 2: Anonymous User
```bash
# Connect without token
wscat -c "ws://localhost:8000/ws/TEST/You"

# Expected (Option 1): Connection successful, no tracking
# Expected (Option 2): Connection rejected
```

### Test Case 3: Invalid Token
```bash
# Connect with invalid token
wscat -c "ws://localhost:8000/ws/TEST/You?token=invalid"

# Expected: Connection rejected (invalid token)
```

### Test Case 4: Rate Limiting
```bash
# Connect multiple times rapidly
for i in {1..10}; do
  wscat -c "ws://localhost:8000/ws/TEST/You" &
done

# Expected (Option 1): Connections 6+ rejected (rate limited)
```

---

## Decision Matrix

| Criterion | Guest Play (Option 1) | Required Auth (Option 2) | Hybrid (Option 3) |
|-----------|----------------------|-------------------------|-------------------|
| **Security** | ⚠️ Moderate | ✅ High | ✅ High |
| **MTurk Compatible** | ⚠️ Partially | ✅ Yes | ✅ Yes |
| **User Friction** | ✅ Low | ❌ High | ⚠️ Medium |
| **Tracking Completeness** | ❌ Partial | ✅ Full | ✅ Full |
| **Implementation Effort** | ✅ Low (add rate limit) | ✅ Low (enforce auth) | ❌ High (complex) |
| **Best For** | Public demo | Research study | Commercial app |

---

## Final Recommendation

### For Your Use Case (100-120 concurrent users, potentially MTurk):

**Choose Option 2: Require Authentication**

**Rationale:**
1. You have 100-120 users → manageable registration
2. Need MTurk integration → requires authentication
3. Need to track all sessions → requires authentication
4. Research context → accountability is important

**Implementation Steps:**
1. Update WebSocket endpoint (10 minutes)
2. Update frontend to redirect to login (15 minutes)
3. Add user-friendly error messages (10 minutes)
4. Test authentication flow (20 minutes)
5. **Total: 1 hour implementation**

---

## Implementation Checklist

### If Requiring Authentication (Option 2)
- [ ] Update WebSocket endpoint to check for token
- [ ] Close connection if no token provided
- [ ] Update frontend `getWebSocketURL` to require token
- [ ] Add login redirect in frontend game lobby
- [ ] Update error messages
- [ ] Test with authenticated user
- [ ] Test without token (should reject)
- [ ] Document for users

### If Allowing Guests (Option 1)
- [ ] Implement WebSocket connection rate limiting
- [ ] Implement per-IP connection limits
- [ ] Add monitoring for abuse patterns
- [ ] Test rate limiting under load
- [ ] Add guest user documentation
- [ ] Encourage registration with in-game prompts

---

## Questions to Consider

1. **Will all your users have accounts before playing?**
   - Yes → Require authentication
   - No → Allow guest play with rate limiting

2. **Do you need to track every session?**
   - Yes → Require authentication
   - No → Allow guest play

3. **Is this a research study?**
   - Yes → Require authentication
   - No → Consider allowing guests

4. **Do users need to earn rewards?**
   - Yes → Require authentication (or hybrid)
   - No → Allow guest play

**Make your decision based on these answers.**

---

## Next Steps

1. **Decide:** Choose Option 1 or Option 2 (recommend Option 2)
2. **Implement:** Follow implementation checklist above
3. **Test:** Use test cases provided
4. **Document:** Update user documentation
5. **Monitor:** Track authentication failures and abuse patterns

**Policy should be decided before production deployment!**

