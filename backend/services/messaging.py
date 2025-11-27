from backend.global_state import rooms
from backend.langgraph_state import GameState

async def broadcast_to_room(room_code: str, message: dict, exclude_player: str = None):
    """
    Broadcast a message to all connections in a room.
    Automatically removes stale connections that fail.
    
    Args:
        room_code: Room identifier
        message: Message dictionary to broadcast
        exclude_player: Optional player_id to exclude from broadcast (e.g., message sender)
    """
    if room_code not in rooms:
        return
    
    connections = rooms[room_code]['connections']
    print(f"📡 Broadcasting to {len(connections)} clients: {message.get('type', 'unknown')}")
    
    # Track failed connections to remove after iteration
    failed_connections = []
    
    for player_id, websocket in connections.items():
        if exclude_player and player_id == exclude_player:
            print(f"⏭️  Skipping broadcast to sender: {player_id}")
            continue
        try:
            await websocket.send_json(message)
        except Exception as e:
            print(f"❌ Error broadcasting to {player_id}: {type(e).__name__}: {str(e)}")
            failed_connections.append(player_id)
    
    # Clean up stale connections
    for player_id in failed_connections:
        print(f"🗑️ Removing stale connection: {player_id}")
        rooms[room_code]['connections'].pop(player_id, None)


async def process_broadcast_queue(room_code: str, state: GameState):
    """
    Process and send all messages in the broadcast queue.
    
    Args:
        room_code: Room identifier
        state: Current game state with broadcast_queue
    """
    for message in state.get("broadcast_queue", []):
        await broadcast_to_room(room_code, message)


