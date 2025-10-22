# Discord Bot Game Statistics

This directory contains game statistics and conversation logs from Discord bot games.

## File Format

Each game generates a JSON file with the following naming convention:
```
{ROOM_CODE}-{UNIX_TIMESTAMP}.json
```

Example: `AB12CD-1729485932.json`

## File Contents

Each JSON file contains:

```json
{
  "room_code": "AB12CD",
  "platform": "discord",
  "topic": "What's your favorite movie and why?",
  "started_at": 1729485800.123,
  "ended_at": 1729485932.456,
  "players": [
    {
      "id": "Human_1",
      "role": "human",
      "eliminated": false
    },
    {
      "id": "Player 1",
      "role": "ai",
      "eliminated": true
    }
    // ... more players
  ],
  "chat_history": [
    {
      "player_id": "Human_1",
      "content": "I think AI can be useful...",
      "timestamp": 1729485810.123,
      "role": "human"
    }
    // ... more messages
  ],
  "votes": {
    "Human_1": "Player 1",
    "Player 2": "Human_1"
    // ... more votes
  },
  "vote_counts": {
    "Player 1": 2,
    "Human_1": 1
  },
  "eliminated_player": "Player 1",
  "winner": "human",
  "rounds_played": 1
}
```

## Verification

To verify stats are being saved correctly:

```bash
# Run the verification script
cd discord_bot
python3 verify_stats.py
```

## Analysis

To analyze game data:

```bash
# View latest game
cat discord-stats/*.json | jq . | tail -n 100

# Count total games
ls -1 discord-stats/*.json | wc -l

# Find games where humans won
grep -l '"winner": "human"' discord-stats/*.json

# Extract all chat messages
jq -r '.chat_history[] | "\(.player_id): \(.content)"' discord-stats/*.json
```

## Privacy

Game logs contain:
- Player IDs (Discord usernames are NOT stored, only game IDs like "Human_1")
- Chat messages from the game
- Voting records
- Timestamps

If you need to share logs for debugging, please review them first to ensure no sensitive information is included.

## Storage

- Files are automatically created when games end
- Files are kept indefinitely (manual cleanup required)
- Typical file size: 10-50 KB per game
- No automatic rotation or cleanup

## Cleanup

To clean up old stats:

```bash
# Delete stats older than 30 days
find discord-stats/ -name "*.json" -mtime +30 -delete

# Delete all stats (keep directory)
rm discord-stats/*.json
```

