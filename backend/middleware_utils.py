import time as _time
import asyncio
from collections import defaultdict

class SimpleRateLimiter:
    """Simple in-memory rate limiter for API endpoints."""
    
    def __init__(self, max_requests: int, window_seconds: int):
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self.requests = defaultdict(list)
    
    def is_allowed(self, key: str) -> bool:
        """Check if request is allowed based on rate limit."""
        now = _time.time()
        
        # Clean old requests outside the window
        self.requests[key] = [
            req_time for req_time in self.requests[key]
            if now - req_time < self.window_seconds
        ]
        
        # Check if under limit
        if len(self.requests[key]) >= self.max_requests:
            return False
        
        # Add current request
        self.requests[key].append(now)
        return True
    
    def cleanup_old_entries(self):
        """Periodically cleanup old entries to prevent memory leak."""
        now = _time.time()
        keys_to_delete = []
        
        for key, timestamps in self.requests.items():
            # Remove timestamps outside window
            self.requests[key] = [
                ts for ts in timestamps
                if now - ts < self.window_seconds
            ]
            # Mark empty entries for deletion
            if not self.requests[key]:
                keys_to_delete.append(key)
        
        for key in keys_to_delete:
            del self.requests[key]

# Rate limiters for security-critical endpoints
# NOTE: These limits are per IP address (or per user for cashout)
# 
# For 100-120 concurrent users, limits should allow legitimate traffic
# while still preventing abuse. Adjust based on your deployment:
# - Single public IP (e.g., corporate network): Higher limits needed
# - Distributed users (home networks): Lower limits acceptable
#
# MTurk registration: 20 requests per minute per IP
mturk_rate_limiter = SimpleRateLimiter(max_requests=20, window_seconds=60)
# Login: 30 attempts per minute per IP (allow rapid legitimate logins)
login_rate_limiter = SimpleRateLimiter(max_requests=30, window_seconds=60)
# Registration: 20 per minute per IP (allow concurrent user onboarding)
register_rate_limiter = SimpleRateLimiter(max_requests=20, window_seconds=60)
# Cashout: 10 per minute per user (prevent abuse)
cashout_rate_limiter = SimpleRateLimiter(max_requests=10, window_seconds=60)
# WebSocket connection: 5 per 10 seconds per IP (prevent DOS)
# Allows quick reloads but stops aggressive connection flooding
websocket_connect_rate_limiter = SimpleRateLimiter(max_requests=5, window_seconds=10)
# General API: 100 requests per minute per IP (prevent API flooding)
# Covers polling endpoints (Lobby, Waiting, Dashboard)
api_rate_limiter = SimpleRateLimiter(max_requests=100, window_seconds=60)

async def periodic_rate_limiter_cleanup():
    """
    Background task to clean up old rate limiter entries.
    Runs every 1 hour.
    Prevents memory leaks from indefinite storage of timestamps.
    """
    while True:
        try:
            await asyncio.sleep(3600)  # 1 hour
            
            print("\n🧹 Running rate limiter cleanup...")
            
            # Clean up all global rate limiters
            mturk_rate_limiter.cleanup_old_entries()
            login_rate_limiter.cleanup_old_entries()
            register_rate_limiter.cleanup_old_entries()
            cashout_rate_limiter.cleanup_old_entries()
            websocket_connect_rate_limiter.cleanup_old_entries()
            api_rate_limiter.cleanup_old_entries()
            
            print("✅ Rate limiter cleanup complete")
            
        except Exception as e:
            print(f"❌ Error in rate limiter cleanup: {e}")
            import traceback
            traceback.print_exc()
