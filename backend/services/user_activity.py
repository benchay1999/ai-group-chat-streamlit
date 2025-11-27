import time as _time
from backend.global_state import user_activity, ONLINE_THRESHOLD_SECONDS

def update_user_activity(user_id: str):
    """Update last activity timestamp for a user."""
    user_activity[user_id] = _time.time()


def get_online_users_count() -> int:
    """
    Get count of users active within the online threshold.
    Cleans up stale entries (>5 minutes inactive).
    """
    current_time = _time.time()
    online_count = 0
    stale_users = []
    
    for user_id, last_seen in user_activity.items():
        if current_time - last_seen <= ONLINE_THRESHOLD_SECONDS:
            online_count += 1
        elif current_time - last_seen > 300:  # Remove after 5 minutes of inactivity
            stale_users.append(user_id)
    
    # Cleanup stale entries
    for user_id in stale_users:
        user_activity.pop(user_id, None)
    
    return online_count


