# Dedicated Game Channels Feature

## Overview

Each Human Hunter game now creates its own dedicated Discord channel that is automatically deleted when the game ends. This provides better isolation between games and cleaner server organization.

## What Changed

### 1. Dedicated Channel Creation (coordinator_bot.py)

When a game starts:
- A new text channel is created with the name `game-{room_code}` (e.g., `game-ab12cd`)
- The channel is created in the same category as the lobby channel
- Channel topic includes room code and room name
- Players are mentioned and directed to the new channel
- A welcome message is posted in the game channel

### 2. Automatic Channel Deletion (game_manager.py)

When a game ends:
- Game results are posted in the game channel
- Players receive a 30-second warning before deletion
- Channel is automatically deleted after the delay
- Graceful error handling if channel is already deleted or bot lacks permissions

### 3. Channel Tracking (utils.py)

Added `game_channel_id` field to `DiscordRoom`:
- Stores the ID of the dedicated game channel
- Falls back to lobby channel if not set (backward compatibility)
- Cleared when room is cleaned up

### 4. Updated Game Flow

All game messages now route to the dedicated channel:
- Discussion phase announcements
- Voting phase announcements
- Elimination results
- AI bot messages
- Game over results

## Benefits

1. **Better Organization**: Each game has its own space, reducing clutter in the lobby channel
2. **Concurrent Games**: Multiple games can run simultaneously without interfering with each other
3. **Privacy**: Game conversations are isolated from the lobby
4. **Auto Cleanup**: Channels are automatically removed when games end, keeping the server clean
5. **Easy Navigation**: Players can easily find their active game by channel name

## Required Permissions

The coordinator bot now requires the **Manage Channels** permission to:
- Create text channels when games start
- Delete channels when games end

## User Experience

### Before Game Start
1. Players use `/lobby`, `/create`, `/join` commands in any channel
2. Waiting room messages appear in the lobby channel

### During Game
3. When room is full, bot creates `game-{room_code}` channel
4. Bot mentions players and directs them to the new channel
5. All game activity happens in the dedicated channel
6. AI bots join and post messages in the game channel

### After Game
7. Results are posted in the game channel
8. "Channel will be deleted in 30 seconds" message appears
9. Channel is automatically deleted
10. Room data is cleaned up

## Technical Details

### Channel Creation
```python
game_channel = await guild.create_text_channel(
    name=f"game-{room_code.lower()}",
    category=category,
    topic=f"Human Hunter Game - Room {room_code} - {room.room_name}",
    reason=f"Game channel for room {room_code}"
)
```

### Channel Deletion
```python
await asyncio.sleep(30)  # 30 second delay
await channel.delete(reason=f"Game {room_code} ended")
```

### Channel Routing
All game-related channel lookups now use:
```python
game_channel_id = session.room.game_channel_id or session.room.channel_id
channel = self.coordinator.get_channel(game_channel_id)
```

## Configuration

### Deletion Delay
Default: 30 seconds (hardcoded in `game_manager.py:660`)

To modify, change:
```python
await asyncio.sleep(30)  # Change this value
```

### Channel Naming
Default: `game-{room_code}` (lowercase)

To modify, change the `name` parameter in `coordinator_bot.py:654`:
```python
name=f"game-{room_code.lower()}",  # Customize this format
```

## Error Handling

1. **Missing Permissions**: If bot lacks `Manage Channels` permission, error message is sent to lobby channel
2. **Channel Not Found**: Gracefully handles if channel is deleted manually
3. **Game Initialization Failure**: Automatically cleans up the created channel if game fails to start

## Backward Compatibility

The system maintains backward compatibility:
- If `game_channel_id` is not set (old rooms), falls back to `channel_id` (lobby channel)
- Existing games without dedicated channels continue to work normally

## Testing

To test the feature:
1. Create a room using `/create`
2. Join with enough players to start the game
3. Observe the new channel being created
4. Play the game in the dedicated channel
5. After game ends, watch the channel be deleted after 30 seconds

## Known Limitations

1. **Category Requirement**: Game channels are created in the same category as the lobby channel
2. **Permission Errors**: If bot loses `Manage Channels` permission mid-game, channel won't be deleted (requires manual cleanup)
3. **Fixed Delay**: 30-second deletion delay is hardcoded (could be made configurable)

## Future Enhancements

Possible improvements:
- Configurable deletion delay via `config.py`
- Option to keep channels for a certain time (e.g., 1 hour) for post-game discussion
- Custom channel permissions (e.g., restrict to players only)
- Archived channel option instead of deletion
- Move to dedicated game category instead of using lobby category

