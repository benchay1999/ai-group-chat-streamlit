# Human Hunter - Discord Bot

A Discord bot implementation of the Human Hunter game, where players compete to identify who is human and who is AI in a social deduction game.

## 🎮 Overview

Human Hunter is a Turing Test-inspired game where human players chat with AI agents and vote to eliminate players they suspect. The human wins by surviving multiple rounds, while the AI wins by identifying and eliminating the humans.

### Key Features

- **Dedicated Game Channels**: Each game creates its own private channel that is automatically deleted when the game ends
- **Multiple Concurrent Games**: Support multiple games simultaneously with room codes
- **Multiple AI Bots**: Each AI player is represented by a separate Discord bot with unique personality
- **Private Voting**: Voting happens via DMs to keep votes secret until results
- **Discord Native UI**: Uses embeds, buttons, and select menus for a polished experience
- **Lobby System**: Create and join rooms with customizable settings

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────┐
│           Discord Server                         │
│                                                  │
│  ┌────────────────────────────────────────┐    │
│  │  Coordinator Bot                       │    │
│  │  - Lobby management                    │    │
│  │  - Room creation/joining               │    │
│  │  - Game coordination                   │    │
│  │  - Voting collection                   │    │
│  └────────────────────────────────────────┘    │
│                                                  │
│  ┌────────────────────────────────────────┐    │
│  │  AI Agent Bots (4-8 bots)             │    │
│  │  - Post AI-generated messages          │    │
│  │  - Unique personalities                │    │
│  │  - Join/leave games dynamically        │    │
│  └────────────────────────────────────────┘    │
│                                                  │
└─────────────────────────────────────────────────┘
                     │
                     ├─────────────────┐
                     │                 │
              ┌──────▼─────┐    ┌─────▼──────┐
              │   Game     │    │  LangGraph │
              │  Manager   │───▶│   Engine   │
              └────────────┘    └────────────┘
```

## 📋 Prerequisites

### Required

1. **Python 3.8+**
2. **OpenAI API Key** (for AI agents)
3. **Discord Bot Tokens**:
   - 1 main coordinator bot
   - 4-8 AI agent bots (minimum 4, recommended 4-6)

### Optional

- Discord server with admin permissions
- Development environment (for testing)

## 🚀 Setup Instructions

### Step 1: Discord Application Setup

You need to create multiple Discord applications (bots) in the Discord Developer Portal.

#### 1.1 Create Main Coordinator Bot

1. Go to [Discord Developer Portal](https://discord.com/developers/applications)
2. Click "New Application"
3. Name it "Human Hunter Coordinator" (or any name)
4. Go to "Bot" tab
5. Click "Add Bot"
6. **Enable these Privileged Gateway Intents**:
   - ✅ Server Members Intent
   - ✅ Message Content Intent
7. Click "Reset Token" and copy the token (save for later)
8. Go to "OAuth2" > "URL Generator"
9. Select scopes:
   - ✅ `bot`
   - ✅ `applications.commands`
10. Select bot permissions:
    - ✅ Send Messages
    - ✅ Send Messages in Threads
    - ✅ Embed Links
    - ✅ Attach Files
    - ✅ Read Message History
    - ✅ Add Reactions
    - ✅ Use Slash Commands
    - ✅ Manage Channels (required for creating/deleting game channels)
11. Copy the generated URL and invite the bot to your server

#### 1.2 Create AI Agent Bots

Repeat the above process **4-8 times** (minimum 4) for AI agent bots:

1. Create new application (name: "Human Hunter AI 1", "Human Hunter AI 2", etc.)
2. Add bot
3. Enable the same intents
4. Copy each bot token
5. Invite each bot to your server using the same permissions

**Important**: You need separate tokens for each AI bot!

### Step 2: Project Setup

#### 2.1 Clone and Navigate

```bash
cd /home/wschay/ai-group-chat-streamlit/discord_bot
```

#### 2.2 Install Dependencies

```bash
# Install Discord bot dependencies
pip install -r requirements.txt

# Install backend dependencies (if not already installed)
pip install -r ../backend/requirements.txt
```

#### 2.3 Configure Environment Variables

Create a `.env` file in the project root (parent directory):

```bash
# Navigate to project root
cd /home/wschay/ai-group-chat-streamlit

# Create or edit .env file
nano .env
```

Add the following configuration:

```bash
# Discord Bot Tokens
DISCORD_MAIN_BOT_TOKEN=your_coordinator_bot_token_here
DISCORD_AI_BOT_TOKEN_1=your_ai_bot_1_token_here
DISCORD_AI_BOT_TOKEN_2=your_ai_bot_2_token_here
DISCORD_AI_BOT_TOKEN_3=your_ai_bot_3_token_here
DISCORD_AI_BOT_TOKEN_4=your_ai_bot_4_token_here
# Add more tokens if you created more AI bots (up to 8)
# DISCORD_AI_BOT_TOKEN_5=...
# DISCORD_AI_BOT_TOKEN_6=...

# OpenAI Configuration (required for AI agents)
OPENAI_API_KEY=your_openai_api_key_here

# Game Configuration (optional, defaults shown)
NUM_AI_PLAYERS=4
AI_MODEL_NAME=gpt-4o-mini
AI_TEMPERATURE=0.8
DISCUSSION_TIME=180
VOTING_TIME=60
ROUNDS_TO_WIN=3
```

### Step 3: Run the Bot

```bash
cd /home/wschay/ai-group-chat-streamlit/discord_bot
python main.py
```

You should see output like:

```
============================================================
Starting Human Hunter Discord Bot System
============================================================
✅ Configuration validated
   Main bot token: ********************abcd1234
   AI bot tokens: 4
Initializing Coordinator Bot...
Initializing 4 AI Agent Bots...
   Created AI_1 with personality: slightly sarcastic
   Created AI_2 with personality: very cheerful
   Created AI_3 with personality: inquisitive
   Created AI_4 with personality: quiet and observant
Initializing Game Manager...
✅ All components initialized
============================================================
Starting bots...
============================================================
🎮 Coordinator Bot is online! (Human Hunter Coordinator)
🤖 AI Agent AI_1 is online! (Human Hunter AI 1)
🤖 AI Agent AI_2 is online! (Human Hunter AI 2)
🤖 AI Agent AI_3 is online! (Human Hunter AI 3)
🤖 AI Agent AI_4 is online! (Human Hunter AI 4)
```

## 🎲 How to Play

### In Discord

#### 1. Create a Room

Use the `/create` slash command:
```
/create max_humans:2 total_players:6 room_name:My Game
```

**Parameters:**
- `max_humans`: Number of human players (1-4, default: 2)
- `total_players`: Total players including AI (2-12, default: 6)
- `room_name`: Optional custom name for your room

The bot will create a room and give you a **6-character room code** (e.g., `AB12CD`).

#### 2. Join a Room

Use the `/join` command with the room code:
```
/join AB12CD
```

Replace `AB12CD` with the actual room code provided by the room creator.

#### 3. Wait for Players

- The waiting room embed shows current players
- Game starts automatically when room is full
- You can leave with `/leave` before the game starts
- **When the game starts, a dedicated channel will be created** (e.g., `game-ab12cd`)
- Players will be notified to move to the new channel

#### 4. Discussion Phase

- Chat naturally in the **dedicated game channel**
- AI bots will also participate
- Topic will be displayed at the start
- Try to blend in if you're human!
- Duration: 3 minutes (configurable)

#### 5. Voting Phase

**Two ways to vote:**

**Option 1: Use `/vote` command (Recommended)**
- Type `/vote <player>` in the game channel
- Example: `/vote Player 1` or `/vote Human_1`
- Supports partial matching (e.g., `/vote player 1` works)
- Your vote is private (only you see the confirmation)

**Option 2: Use DM voting**
- Bot will send you a DM with a voting form
- Select a player to eliminate using the dropdown
- Vote confirmation sent in DM

**General:**
- Votes are private and revealed after voting ends
- You can only vote once (cannot change vote)
- Duration: 1 minute (configurable)

#### 6. Results

- Vote counts are revealed
- Player with most votes is eliminated
- Their role (human or AI) is revealed
- Game continues to next round or ends

#### 7. Win Conditions

- **Humans Win**: Survive 1 round (default, configurable up to any number)
- **AI Wins**: Eliminate all humans
- **After the game ends**: The dedicated game channel will be automatically deleted after 30 seconds

### All Commands

- `/create` - Create a new game room
- `/join <code>` - Join a game room by code
- `/leave` - Leave your current room
- `/rooms` - List all active rooms in the channel
- `/vote <player>` - Cast your vote during voting phase (e.g., `/vote Player 1`)

## ⚙️ Configuration

### Game Settings

Edit `backend/config.py` or set environment variables:

| Variable | Description | Default |
|----------|-------------|---------|
| `NUM_AI_PLAYERS` | Number of AI players per game | 4 |
| `AI_MODEL_NAME` | OpenAI model to use | gpt-4o-mini |
| `AI_TEMPERATURE` | AI creativity (0-1) | 0.8 |
| `DISCUSSION_TIME` | Discussion phase duration (seconds) | 180 |
| `VOTING_TIME` | Voting phase duration (seconds) | 60 |
| `ROUNDS_TO_WIN` | Rounds humans must survive | 3 |

### Discord Settings

Edit `discord_bot/config.py`:

| Variable | Description | Default |
|----------|-------------|---------|
| `MIN_HUMANS` | Minimum human players | 1 |
| `MAX_HUMANS` | Maximum human players | 4 |
| `MIN_TOTAL_PLAYERS` | Minimum total players | 2 |
| `MAX_TOTAL_PLAYERS` | Maximum total players | 12 |

### AI Personalities

AI bots are assigned personalities from `backend/config.py`:

- slightly sarcastic
- very cheerful
- inquisitive
- quiet and observant
- enthusiastic
- analytical
- humorous
- philosophical

You can add more personalities to the list!

## 🐛 Troubleshooting

### Bot Not Responding

**Check logs**: Look at console output or `discord_bot.log`

**Common issues**:
1. Bot tokens not set correctly in `.env`
2. Bots not invited to server
3. Missing bot permissions
4. Missing privileged intents in Developer Portal

### Commands Not Showing

1. Wait 5 minutes for Discord to sync commands
2. Check bot has "Use Slash Commands" permission
3. Try kicking and re-inviting the bot
4. Check logs for "Commands synced" message

### Voting Not Working

1. Check bot can send DMs (user must share a server with bot)
2. Verify user has DMs enabled for server members
3. Check logs for DM errors

### AI Bots Not Joining Games

1. Verify all AI bot tokens are valid
2. Check AI bots are invited to the server
3. Check AI bots have "Send Messages" permission
4. Review logs for connection errors

### OpenAI API Errors

1. Verify `OPENAI_API_KEY` is set correctly
2. Check API key has credits
3. Try reducing `NUM_AI_PLAYERS` if rate limited
4. Check OpenAI service status

## 📁 File Structure

```
discord_bot/
├── main.py                 # Entry point, launches all bots
├── coordinator_bot.py      # Main bot for lobby/room management
├── ai_agent_bot.py         # AI agent bot class
├── game_manager.py         # Bridge between Discord and LangGraph
├── ui_components.py        # Discord UI (embeds, views, buttons)
├── config.py               # Bot configuration
├── utils.py                # Helper functions
├── requirements.txt        # Dependencies
├── README.md              # This file
└── discord_bot.log        # Log file (created on run)
```

## 🔧 Development

### Running in Development Mode

```bash
# Set Python path
export PYTHONPATH=/home/wschay/ai-group-chat-streamlit:$PYTHONPATH

# Run with debug logging
python main.py
```

### Testing

1. Create a test Discord server
2. Invite all bots
3. Use `/create max_humans:1 total_players:5` for quick testing
4. Test with multiple accounts or friends for multiplayer

### Adding Features

Key extension points:

- **New AI Personalities**: Edit `backend/config.py` → `AI_PERSONALITIES`
- **New Topics**: Edit `backend/config.py` → `GAME_TOPICS`
- **UI Customization**: Edit `ui_components.py` embed colors and layouts
- **Game Logic**: Edit `backend/langgraph_game.py` for advanced AI behavior

## 🚀 Production Deployment

### Option 1: Local Server

1. Run on a always-on machine
2. Use `screen` or `tmux` to keep running:
   ```bash
   screen -S human-hunter
   cd /home/wschay/ai-group-chat-streamlit/discord_bot
   python main.py
   # Detach with Ctrl+A, D
   ```

### Option 2: Cloud Server

Deploy to any VPS provider:

1. Set up Python 3.8+ on server
2. Clone repository
3. Install dependencies
4. Set environment variables
5. Use systemd or supervisor to keep bot running
6. Set up logging and monitoring

### Option 3: Docker (Advanced)

Create `Dockerfile`:

```dockerfile
FROM python:3.9-slim
WORKDIR /app
COPY . .
RUN pip install -r requirements.txt
RUN pip install -r backend/requirements.txt
CMD ["python", "discord_bot/main.py"]
```

## 📊 Monitoring

### Logs

- Console output: Real-time bot activity
- `discord_bot.log`: Persistent log file
- Log levels: INFO (normal), ERROR (issues), WARNING (potential problems)

### Health Checks

Monitor for these log messages:
- ✅ "Bot is online" - Bot connected successfully
- ❌ "Error in bot execution" - Bot crashed
- ⚠️ "Failed to start game" - Game initialization failed

## 🤝 Contributing

To add features or fix bugs:

1. Create a feature branch
2. Make changes
3. Test thoroughly
4. Submit pull request with description

## 📄 License

This project uses the same license as the parent Human Hunter project.

## 🆘 Support

For issues or questions:

1. Check this README
2. Review logs in `discord_bot.log`
3. Check Discord Developer Portal for bot status
4. Review OpenAI API status

## 🎉 Credits

Built on top of the Human Hunter game:
- Backend: LangGraph multi-agent system
- Original: Streamlit web interface
- Discord Bot: Native Discord implementation

---

**Happy Gaming! May the best human (or AI) win!** 🎮🤖👤

