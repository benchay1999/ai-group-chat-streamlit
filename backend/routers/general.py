from fastapi import APIRouter
from backend.config import NUM_AI_PLAYERS, DISCUSSION_TIME, VOTING_TIME
from backend.global_state import api_key_manager, ONLINE_THRESHOLD_SECONDS
from backend.services.user_activity import get_online_users_count

router = APIRouter()

@router.get("/config")
async def get_config():
    """
    Get current game configuration.
    """
    return {
        "num_ai_players": NUM_AI_PLAYERS,
        "discussion_time": DISCUSSION_TIME,
        "voting_time": VOTING_TIME
    }


@router.get("/health")
async def health_check():
    """
    Health check endpoint with API key manager status.
    """
    health_info = {
        "status": "healthy",
        "api_keys_configured": api_key_manager is not None
    }
    
    if api_key_manager:
        try:
            stats = api_key_manager.get_stats()
            health_info.update({
                "api_key_count": stats["total_keys"],
                "total_rooms_created": stats["total_assigned"],
                "api_system": "operational"
            })
        except Exception as e:
            health_info["api_system"] = f"degraded: {str(e)}"
    else:
        health_info["api_system"] = "unavailable - no API keys configured"
    
    return health_info


@router.get("/api/lobby/online-users")
async def get_online_users():
    """
    Get the count of currently online users.
    Returns count of users who have sent a heartbeat within ONLINE_THRESHOLD_SECONDS.
    """
    online_count = get_online_users_count()
    
    return {
        "total_online": online_count,
        "threshold_seconds": ONLINE_THRESHOLD_SECONDS
    }


