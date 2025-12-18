# LangGraph Recursion Limit & HTTP Timeout Fixes

## Issues Fixed

### Issue 1: LangGraph Recursion Error ✅
**Error Message:**
```
langgraph.errors.GraphRecursionError: Recursion limit of 25 reached without hitting a stop condition.
```

**Cause:** 
The LangGraph StateGraph was hitting the default recursion limit of 25 iterations when processing multiple AI chat messages and votes in succession.

**Fix Applied:**
1. Added `recursion_limit: 100` config parameter to graph invoke calls in `backend/main.py`
2. Updated graph compilation in `backend/langgraph_game.py`

**Files Modified:**
- `backend/main.py` (line 167)
- `backend/langgraph_game.py` (lines 108-111)

---

### Issue 2: HTTP Timeout Errors ✅
**Error Message:**
```
HTTPConnectionPool(host='localhost', port=8000): Read timed out. (read timeout=5)
```

**Cause:**
The 5-second timeout was too short for:
- AI message generation (can take 5-10 seconds with GPT models)
- Room initialization with multiple AI players
- Vote processing with AI reasoning

**Fix Applied:**
Increased timeout values in `streamlit_app.py`:
- `join_room()`: 5s → 30s (for AI initialization)
- `poll_game_state()`: 5s → 15s (for AI processing)
- `send_message()`: 5s → 20s (for AI response generation)
- `cast_vote()`: 5s → 20s (for AI vote processing)
- `health_check()`: 2s → 5s

**Files Modified:**
- `streamlit_app.py` (lines 44, 60, 76, 90, 361)

---

## Technical Details

### LangGraph Recursion Limit

The recursion limit controls how many times the graph can traverse its nodes before stopping. With the default limit of 25:

**Problem Scenario:**
```
Discussion Phase → AI Agent 1 → AI Agent 2 → AI Agent 3 → AI Agent 4
→ More messages... (repeats) → Hits limit at iteration 25
```

**Solution:**
```python
# In main.py
result = game_graph.graph.invoke(
    {**state, "pending_ai_votes": [ai_id]},
    config={"recursion_limit": 100}  # Increased from default 25
)
```

This allows the graph to:
- Process up to 100 AI messages/votes in a single phase
- Handle multiple rounds without hitting the limit
- Support 8+ AI players with multiple messages each

### HTTP Timeout Configuration

**Timeout Matrix:**

| Operation | Old Timeout | New Timeout | Reason |
|-----------|-------------|-------------|--------|
| Join Room | 5s | 30s | AI initialization can be slow |
| Poll State | 5s | 15s | Reading state is fast but AI might be processing |
| Send Message | 5s | 20s | Triggers AI responses (5-10s per AI) |
| Cast Vote | 5s | 20s | AI vote generation takes time |
| Health Check | 2s | 5s | Simple check but allow for server lag |

**Why these values?**

1. **30s for join_room()**: Creates game, initializes 4+ AI agents, generates personalities
2. **20s for send_message()**: Your message + 1-2 AI responses (each takes 5-10s)
3. **20s for cast_vote()**: Similar to messages, AI needs to reason about votes
4. **15s for poll_game_state()**: Just reading state, but backend might be processing AI

---

## Testing the Fixes

### 1. Test Backend Recursion Fix

```bash
# Start backend
cd backend
uvicorn main:app --reload

# Backend should now handle multiple AI messages without recursion errors
```

### 2. Test Streamlit Timeout Fix

```bash
# Start Streamlit
streamlit run streamlit_app.py

# Try these actions:
# - Join a room (should not timeout during initialization)
# - Send messages (should wait for AI responses)
# - Vote during voting phase (should handle AI votes)
```

### 3. Monitor Backend Logs

Watch for:
- ✅ No more "GraphRecursionError" messages
- ✅ AI messages generating successfully
- ✅ Votes processing without errors

### 4. Monitor Streamlit

Watch for:
- ✅ No more "Read timed out" errors
- ✅ AI responses appearing in chat
- ✅ Game phases transitioning smoothly

---

## Configuration Options

### Adjust Recursion Limit

If you still hit recursion limits with 8+ AI players:

**Edit `backend/main.py` line 167:**
```python
config={"recursion_limit": 150}  # Increase further if needed
```

### Adjust HTTP Timeouts

If AI responses are still timing out:

**Edit `streamlit_app.py`:**
```python
# For slower AI models (GPT-4, etc.)
timeout=30  # Increase for poll_game_state
timeout=40  # Increase for send_message and cast_vote
```

### Monitor Performance

```bash
# Check AI response times
# Backend logs will show timing for each AI message/vote

# Typical times:
# - GPT-4o-mini: 3-8 seconds per message
# - GPT-4: 5-15 seconds per message
# - GPT-3.5-turbo: 2-5 seconds per message
```

---

## Recommendations

### For Development

Use faster models to reduce timeouts:
```bash
export AI_MODEL_NAME=gpt-3.5-turbo
export NUM_AI_PLAYERS=4  # Fewer players = faster
```

### For Production

1. **Use streaming responses** (future enhancement)
2. **Implement caching** for repeated AI queries
3. **Add loading indicators** in Streamlit during long operations
4. **Consider async processing** for non-blocking AI generation

---

## Future Improvements

### 1. Streaming Responses
Instead of waiting for full AI response, stream tokens as they generate.

### 2. Background Processing
Move AI generation to background tasks, poll for results.

### 3. Response Caching
Cache AI responses for similar scenarios to reduce API calls.

### 4. Progress Indicators
Show "AI is thinking..." with progress bar in Streamlit.

### 5. Adaptive Timeouts
Automatically adjust timeouts based on:
- Number of AI players
- Model being used (GPT-3.5 vs GPT-4)
- Current phase (discussion vs voting)

---

## Troubleshooting

### Still Getting Recursion Errors?

**Check:**
1. How many AI players? (More players = more iterations)
2. Is `recursion_limit` config being passed? (line 167 in main.py)
3. Are there infinite loops in graph logic?

**Solution:**
```python
# Increase limit even more
config={"recursion_limit": 200}
```

### Still Getting Timeout Errors?

**Check:**
1. Is backend responding? (`curl http://localhost:8000/health`)
2. Are AI API keys valid?
3. Is OpenAI API rate-limited?

**Solution:**
```python
# Increase timeouts globally in streamlit_app.py
DEFAULT_TIMEOUT = 30  # Add this constant at top
# Use in all requests: timeout=DEFAULT_TIMEOUT
```

### Backend is Slow

**Optimize:**
```bash
# Use faster model
export AI_MODEL_NAME=gpt-3.5-turbo

# Reduce AI players
export NUM_AI_PLAYERS=3

# Reduce message cooldown
# Edit backend/config.py: MESSAGE_COOLDOWN = 0.5
```

---

## Summary

✅ **Fixed LangGraph recursion limit** by increasing from 25 to 100 iterations
✅ **Fixed HTTP timeouts** by increasing from 5s to 15-30s depending on operation
✅ **Backend can now handle** multiple AI messages and votes without crashing
✅ **Streamlit can now wait** for AI responses without timing out

**Both issues are now resolved!** 🎉

The game should now run smoothly with multiple AI players and handle long AI response times gracefully.

