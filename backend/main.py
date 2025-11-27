"""
FastAPI main application with LangGraph integration.
Maintains WebSocket compatibility with frontend while using graph-based backend.
"""

import asyncio
import os
from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from backend import env_config
from backend.database import init_db, close_db
from backend.middleware_utils import api_rate_limiter, periodic_rate_limiter_cleanup
from backend.services.room_management import periodic_room_cleanup, monitor_room_health

# Import Routers
from backend.routers import auth, wallet, sessions, admin, rooms, websocket, general

app = FastAPI(title="AI Group Chat API", version="2.0.0")

# CORS Configuration - Production-safe
# Get allowed origins from environment variable, default to localhost for development
default_origins = 'http://localhost:5173,http://localhost:3000,https://ai-group-chat.netlify.app'
allowed_origins_str = os.getenv('CORS_ALLOWED_ORIGINS', default_origins)
allowed_origins = [origin.strip() for origin in allowed_origins_str.split(',')]

# Security validation: Never allow wildcard origins
if '*' in allowed_origins:
    raise ValueError(
        "SECURITY ERROR: Wildcard CORS origins ('*') are not allowed. "
        "Please specify explicit origins in CORS_ALLOWED_ORIGINS environment variable."
    )

# In production, MTURK_ENVIRONMENT should be set, and we should restrict CORS
if os.getenv('MTURK_ENVIRONMENT') == 'production':
    # In production, only allow HTTPS origins
    for origin in allowed_origins:
        if origin.startswith('http://') and 'localhost' not in origin:
            raise ValueError(
                f"SECURITY ERROR: HTTP origin '{origin}' not allowed in production. "
                f"All production origins must use HTTPS."
            )
    print(f"🔒 CORS configured for production with origins: {allowed_origins}")
else:
    # In development/sandbox, allow localhost origins
    print(f"🔓 CORS configured for development with origins: {allowed_origins}")

print(f"🌐 CORS allowed origins: {allowed_origins}")

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["*"],  # Allow all headers to be exposed
)


# ============================================================================
# Rate Limiting Middleware
# ============================================================================

@app.middleware("http")
async def rate_limit_middleware(request: Request, call_next):
    """
    Global rate limiting middleware for API endpoints.
    Skips static files and docs.
    """
    path = request.url.path
    
    # Skip rate limiting for:
    # 1. Static files (usually handled by frontend server in prod, but good to safe)
    # 2. Documentation endpoints
    # 3. WebSocket upgrade requests (handled by websocket_connect_rate_limiter)
    if (path.startswith("/static") or 
        path.startswith("/docs") or 
        path.startswith("/openapi.json") or 
        "ws" in request.scope.get("type", "")):
        return await call_next(request)
    
    # Apply global API rate limit
    client_ip = request.client.host
    if not api_rate_limiter.is_allowed(client_ip):
        return JSONResponse(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            content={
                "success": False,
                "error": "Too many requests",
                "detail": "You are sending too many requests. Please wait a moment."
            }
        )
        
    response = await call_next(request)
    return response


# ============================================================================
# Exception Handlers
# ============================================================================

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """
    Global exception handler that ensures CORS headers are included in error responses.
    This prevents CORS errors when backend exceptions occur.
    """
    print(f"❌ Global exception handler caught: {type(exc).__name__}: {str(exc)}")
    import traceback
    traceback.print_exc()
    
    # Determine origin for CORS
    origin = request.headers.get("origin")
    
    # Create error response
    response = JSONResponse(
        status_code=500,
        content={
            "success": False,
            "error": "Internal server error",
            "detail": str(exc)[:200]  # Limit error message length
        }
    )
    
    # Add CORS headers
    if origin and (origin in allowed_origins or "*" in allowed_origins):
        response.headers["Access-Control-Allow-Origin"] = origin
        response.headers["Access-Control-Allow-Credentials"] = "true"
        response.headers["Access-Control-Allow-Methods"] = "*"
        response.headers["Access-Control-Allow-Headers"] = "*"
    
    return response


# ============================================================================
# Include Routers
# ============================================================================

app.include_router(auth.router)
app.include_router(wallet.router)
app.include_router(sessions.router)
app.include_router(admin.router)
app.include_router(rooms.router)
app.include_router(websocket.router)
app.include_router(general.router)


# ============================================================================
# Application Lifecycle Events
# ============================================================================

@app.on_event("startup")
async def startup_event():
    """Initialize database and MTurk client on application startup."""
    await init_db()
    
    # Initialize MTurk client to verify credentials and show configuration
    try:
        from backend.mturk_api import get_mturk_client
        client = get_mturk_client()
        print(f"💰 Base pay: ${client.base_pay}, Max bonus: ${os.getenv('MTURK_MAX_BONUS', '0.05')}")
    except Exception as e:
        print(f"⚠️  MTurk client initialization failed: {e}")
        print("   MTurk features will not be available until credentials are configured.")
    
    # Start cashout monitor background task
    try:
        from backend.cashout_monitor import start_cashout_monitor
        await start_cashout_monitor()
    except Exception as e:
        print(f"⚠️  Cashout monitor initialization failed: {e}")
    
    # Configuration validation already done by env_config module at import time
    # Additional startup validation
    config_status = env_config.get_config_status()
    if not config_status['cashout_hit_id_configured']:
        print("⚠️  CASHOUT SYSTEM NOT CONFIGURED - Cashout requests will fail!")
    
    # Start periodic room cleanup task
    asyncio.create_task(periodic_room_cleanup())
    print("🧹 Started periodic room cleanup task")
    
    # Start room health monitoring task
    asyncio.create_task(monitor_room_health())
    print("🏥 Started room health monitoring task")
    
    # Start periodic rate limiter cleanup task
    asyncio.create_task(periodic_rate_limiter_cleanup())
    print("🧹 Started periodic rate limiter cleanup task")
    
    print("🚀 Application started successfully")


@app.on_event("shutdown")
async def shutdown_event():
    """Close database connections and stop background tasks on application shutdown."""
    # Stop cashout monitor
    try:
        from backend.cashout_monitor import stop_cashout_monitor
        await stop_cashout_monitor()
    except Exception as e:
        print(f"⚠️  Error stopping cashout monitor: {e}")
    
    await close_db()
    print("👋 Application shut down gracefully")
