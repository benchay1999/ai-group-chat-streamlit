# Quick Start Guide - Discord Bot

Get your Human Hunter Discord bot running in 5 minutes!

## ⚡ Speed Run (5 Minutes)

### 1. Get Discord Bot Tokens (3 min)

1. Go to https://discord.com/developers/applications
2. Create **5 applications** (1 coordinator + 4 AI bots)
3. For each application:
   - Click "Bot" tab → "Add Bot"
   - Enable "Server Members Intent" and "Message Content Intent"
   - Click "Reset Token" and copy it
   - Go to OAuth2 → URL Generator
   - Select: `bot` + `applications.commands`
   - Select permissions: Send Messages, Embed Links, Use Slash Commands
   - Copy URL and invite bot to your server

### 2. Configure Environment (1 min)

```bash
cd /home/wschay/ai-group-chat-streamlit
cp discord_bot/env.example .env
nano .env
```

Add your tokens:
```bash
DISCORD_MAIN_BOT_TOKEN=paste_coordinator_token_here
DISCORD_AI_BOT_TOKEN_1=paste_ai_bot_1_token_here
DISCORD_AI_BOT_TOKEN_2=paste_ai_bot_2_token_here
DISCORD_AI_BOT_TOKEN_3=paste_ai_bot_3_token_here
DISCORD_AI_BOT_TOKEN_4=paste_ai_bot_4_token_here
OPENAI_API_KEY=paste_openai_key_here
```

### 3. Install & Run (1 min)

```bash
cd discord_bot
pip install -r requirements.txt
pip install -r ../backend/requirements.txt
python main.py
```

### 4. Play! (Now)

In Discord:
```
/lobby
```

Click "Create Room" → Play!

## 🎮 Commands Reference

| Command | Description | Example |
|---------|-------------|---------|
| `/lobby` | Open game lobby | `/lobby` |
| `/create` | Create new room | `/create max_humans:2 total_players:6 room_name:My Game` |
| `/join` | Join room by code | `/join room_code:ABC123` |
| `/leave` | Leave current room | `/leave` |
| `/rooms` | List active rooms | `/rooms` |

## 🤖 Bot Roles

- **Coordinator Bot**: Manages everything
- **AI Bot 1-4**: Play as AI players

## ⚙️ Quick Settings

Edit `.env` file:

```bash
# Number of AI players
NUM_AI_PLAYERS=4

# Discussion time (seconds)
DISCUSSION_TIME=180

# Voting time (seconds)
VOTING_TIME=60

# Rounds to win
ROUNDS_TO_WIN=3
```

## 🐛 Troubleshooting One-Liners

**Bots offline?**
```bash
# Check tokens in .env file
grep DISCORD .env
```

**Commands not showing?**
```bash
# Wait 5 minutes, then re-invite bots
# Make sure "Use Slash Commands" permission is enabled
```

**Can't vote?**
```bash
# Enable DMs from server members in Discord privacy settings
# User Settings → Privacy & Safety → Allow DMs from server members
```

**Import errors?**
```bash
# Install all dependencies
pip install -r requirements.txt
pip install -r ../backend/requirements.txt
```

## 📁 File Locations

```
discord_bot/
├── main.py              # Run this!
├── .env                 # Configure this! (in parent dir)
├── start.sh             # Or run this!
└── README.md            # Full documentation
```

## ✅ Verification Checklist

- [ ] 5 Discord applications created
- [ ] All bots invited to server
- [ ] All bot tokens in `.env`
- [ ] OpenAI API key in `.env`
- [ ] Dependencies installed
- [ ] `python main.py` runs without errors
- [ ] All bots show as online in Discord
- [ ] `/lobby` command works

## 🎯 Test Game

Fastest test (single player):
```
/create max_humans:1 total_players:5
```

Game starts immediately with 4 AI bots!

## 📞 Need Help?

1. **Full Docs**: See `README.md`
2. **Logs**: Check `discord_bot.log`
3. **Config**: See `env.example`
4. **Summary**: See `../DISCORD_BOT_IMPLEMENTATION_SUMMARY.md`

---

**That's it! Happy gaming!** 🎮

