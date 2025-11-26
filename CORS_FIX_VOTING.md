# CORS Error Fix - Multi-Human Voting

## Date: November 26, 2025

## Problem

When testing multi-human games with two browsers (admin in Chrome, regular user in Edge):
- First player (regular user) could vote successfully
- Second player (admin) got CORS error when voting:
  ```
  Access to XMLHttpRequest at 'https://ai-groupchat.ngrok.io/api/rooms/QUD09P/vote' 
  from origin 'https://ai-group-chat.netlify.app' has been blocked by CORS policy: 
  No 'Access-Control-Allow-Origin' header is present on the requested resource.
  ```

## Root Cause

The second vote triggered the `complete_voting()` function, which:
1. Processes game completion
2. Calculates and awards gem rewards via `save_session_stats()`
3. If `save_session_stats()` raised an exception, it was re-raised (line 1471)
4. **Uncaught exceptions in FastAPI don't automatically include CORS headers**
5. Browser blocks the response due to missing CORS headers

The first vote succeeded because it didn't trigger completion - only the final vote does.

## Solution

Applied a three-layer fix:

### Fix #1: Global Exception Handler with CORS Headers
**Location:** `backend/main.py` ~line 92

Added a global exception handler that ensures all error responses include proper CORS headers:

```python
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """
    Global exception handler that ensures CORS headers are included in error responses.
    This prevents CORS errors when backend exceptions occur.
    """
    origin = request.headers.get("origin")
    
    response = JSONResponse(
        status_code=500,
        content={
            "success": False,
            "error": "Internal server error",
            "detail": str(exc)[:200]
        }
    )
    
    # Add CORS headers
    if origin and (origin in allowed_origins or "*" in allowed_origins):
        response.headers["Access-Control-Allow-Origin"] = origin
        response.headers["Access-Control-Allow-Credentials"] = "true"
        response.headers["Access-Control-Allow-Methods"] = "*"
        response.headers["Access-Control-Allow-Headers"] = "*"
    
    return response
```

### Fix #2: Better Error Handling in Vote Endpoint
**Location:** `backend/main.py` ~line 6295

Wrapped the vote completion logic in try-catch blocks to provide better error logging:

```python
try:
    await broadcast_to_room(room_code, {
        "type": "voted",
        "player": player_id
    })
    
    if len(state['votes']) >= required_votes:
        try:
            await complete_voting(room_code)
        except Exception as completion_error:
            print(f"❌ Error during vote completion: ...")
            raise
    
    return {"success": True}
    
except Exception as e:
    print(f"❌ Error processing vote: ...")
    raise  # Let global handler deal with it
```

### Fix #3: Remove Exception Re-raising in complete_voting()
**Location:** `backend/main.py` ~line 1508

Changed from re-raising gem reward errors to just logging them:

**BEFORE:**
```python
except Exception as save_error:
    # ... error handling ...
    raise  # This caused CORS errors!
```

**AFTER:**
```python
except Exception as save_error:
    # ... error handling ...
    # DON'T re-raise - game is already complete, gem rewards are secondary
    # Raising here would cause CORS errors and prevent vote response
    print(f"⚠️ Continuing despite gem reward failure - game completion is more important")
```

## Why This Works

1. **Global Exception Handler**: Catches any uncaught exception and ensures CORS headers are always included
2. **Better Logging**: Vote endpoint provides detailed error logging for debugging
3. **Graceful Degradation**: Gem reward failures don't break game completion - game can finish even if rewards fail

## Testing

To verify the fix:

1. **Multi-human game test:**
   - Admin creates room with 2+ humans
   - Players join from different browsers
   - All players chat during discussion
   - All players vote during voting phase
   - ✅ **Expected:** All votes succeed, game completes, no CORS errors

2. **Error resilience test:**
   - Simulate gem reward failure (database error, etc.)
   - ✅ **Expected:** Game still completes, players see error message but no CORS block

## Impact

- ✅ Multi-human voting now works reliably
- ✅ CORS errors eliminated for all endpoints (not just vote)
- ✅ Better error messages and logging
- ✅ Graceful handling of gem reward failures
- ✅ Game completion prioritized over rewards

## Additional Bug Fixed

While fixing the CORS issue, discovered and fixed another bug:

### UnboundLocalError in Multi-Human Games
**Location:** `backend/main.py` ~line 1428

**Problem:** In multi-human games, `suspect` and `suspect_role` were stored in the state dictionary but not as local variables. The voting result broadcast tried to use undefined local variables.

**Fix:** Added code to extract these values from state before broadcasting:

```python
# Get suspect info from state (works for both single and multi-human games)
suspect = state.get('selected_suspect')
suspect_role = state.get('suspect_role')

# Broadcast voting result
await broadcast_to_room(room_code, {
    "type": "voting_result",
    "suspect": suspect,
    "role": suspect_role,
    "vote_counts": vote_counts
})
```

This ensures both single-player and multi-player games work correctly.

## Files Modified

- `backend/main.py`:
  - Added global exception handler (~line 92)
  - Improved vote endpoint error handling (~line 6295)
  - Removed exception re-raising in complete_voting (~line 1508)
  - Fixed UnboundLocalError for multi-human games (~line 1428)

## Notes

- The global exception handler applies to ALL endpoints, preventing future CORS issues
- Gem rewards are treated as "nice to have" - game completion is prioritized
- All errors are still logged for debugging, just not raised to break the response
- CORS headers are added based on request origin, supporting both production and development environments

