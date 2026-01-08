# Human Hunter Game Rules and Logistics

## Overview
Human Hunter is a web-based social deduction game inspired by a reverse Turing Test. The game supports two distinct modes:

- **Single-Human Mode**: One human player competes against AI agents who try to identify and vote them out
- **Multi-Human Mode**: Multiple human players compete against each other to prove they are most human-like while identifying other humans

Both modes feature real-time group chat, strategic voting, and a gem-based reward system.

## Game Modes

### Single-Human Mode

**Players:**
- **Total Players:** Configurable (default 5)
  - 1 Human Player (you, the user, labeled as "You")
  - 4 AI Agents (labeled as "Player X", powered by an LLM like GPT)

**Objectives:**
- **AI Agents' Objective:** Identify the human through conversation and vote them out. They must act human-like to avoid being voted out themselves.
- **Human Player's Objective:** Survive configured rounds (default: 1 round) by blending in and avoiding suspicion.

**Rewards:**
- All participants (human + AI): **50 gems**
- No stakes, no risk - pure participation reward

### Multi-Human Mode

**Players:**
- **Total Players:** 2+ human players + configurable AI agents
- All human players compete for most votes
- AI agents participate but don't vote

**Objectives:**
- **Human Players' Objective:** Act most human-like to receive the most votes from other players, while correctly identifying all other human players
- **AI Agents' Role:** Participate in discussion but do not vote (only humans vote in this mode)

**Rewards:**
- **Base Gems:** 100 gems for all participants who vote
- **Stakes System:** Optional gem stakes (0%, 10%, 30%, 50%, or 100% of balance)
  - Minimum 250 gems required to join multi-human games
  - Winners get stake refund + share of loser pool (proportional to voting accuracy)
  - Losers forfeit their stake
- **Voting Penalty:** Must vote to receive base gems and stake refund

**Key Difference:** In multi-human mode, you must vote for **all other humans** (N-1 players, excluding yourself). Voting accuracy determines how much of the loser pool you win.

## Game Flow
The game proceeds through phases until completion. The flow differs slightly by game mode:

### Discussion Phase (Default: 4 minutes, configurable)
- A random conversation topic is presented (e.g., "What's the best topping for pizza?")
- All players chat freely in real-time via a group chat interface
- AI agents respond conversationally, acting natural and analyzing behavior
- Timer counts down; phase automatically transitions to voting when time expires

### Voting Phase (Default: 2 minutes, configurable)
- Chat is disabled
- **Single-Human Mode:**
  - Each player votes for **one** player they think is most human-like
  - AI agents participate in voting
  - Cannot vote for yourself
- **Multi-Human Mode:**
  - Each human votes for **N-1 players** (all humans except yourself)
  - Must identify all other human players
  - AI agents do NOT vote (only humans vote)
  - Voting accuracy affects gem rewards

### Results & Elimination

**Single-Human Mode:**
- Player with most votes is eliminated, role revealed (Human or AI)
- If human eliminated, AIs win
- If AI eliminated, game continues to next round with remaining players
- Game continues until human survives configured rounds (default: 1) or is eliminated

**Multi-Human Mode:**
- No elimination occurs
- Player(s) with most votes WIN
- Gem stakes distributed based on winner/loser status and voting accuracy
- Game ends after first voting round

## Win Conditions

### Single-Human Mode
- **AIs Win:** If the human is eliminated in any round
- **Human Wins:** If the human survives configured rounds (default: 1 round, configurable via ROUNDS_TO_WIN)
- Game ends immediately when a win condition is met

### Multi-Human Mode
- **Winner(s):** Human player(s) with the most votes
- **Tie:** Multiple humans can tie for most votes and share winnings
- Game always ends after first voting round (no elimination/continuation)

## Logistics and Tips
- **Timers:** Discussion defaults to 4 minutes; voting defaults to 2 minutes (configurable). The UI shows a countdown.
- **Chat Interface:** Messages are attributed to senders (e.g., "Player 2: I think pineapple is great!"). Human input is at the bottom; disabled during voting.
- **Player List:** Shows all players, with indicators for voted/elimated status.
- **AI Behavior:** AIs have assigned personalities (e.g., sarcastic, cheerful) and aim to be believable humans. They analyze chats for "human-like" traits.
- **Restarting:** Refresh the page or use the /start endpoint to reset the game.
- **Technical Notes:** Ensure the backend is running with a valid OpenAI API key for AI responses. The game supports both single-player (you vs. AIs) and multiplayer (multiple humans competing) modes.

## Gem Rewards System

### Earning Gems
Gems are the in-game currency that can be converted to real USD via Amazon Mechanical Turk (1000 gems = $1.00).

**Single-Human Games:**
- Simple participation-based rewards
- All players (human + AI): **50 gems**
- No stakes required, no risk

**Multi-Human Games:**
- Performance-based rewards with optional stakes
- **Base Gems:** 100 gems for all participants (requires voting)
- **Stakes System:** Optional risk/reward mechanism
  - Choose stake percentage when creating room: 0%, 10%, 30%, 50%, or 100%
  - Minimum 250 gems required to join multi-human games
  - All players pay the minimum stake (lowest among all players)
  - Winners get: stake refund + (accuracy × share of loser pool)
  - Losers: forfeit their stake entirely
- **Voting Accuracy Matters:** In multi-human games, you must vote for all other humans correctly
  - Accuracy = correct_votes / (num_humans - 1)
  - Higher accuracy = bigger share of loser stakes
  - 100% accuracy = full share; 0% accuracy = only stake refund

### Detailed Examples and Formulas
For complete details on gem calculations, stakes mechanics, and example scenarios, visit the **Gems Info Page** (`/gems-info`) in the application.

### Cashing Out
- View balance in Dashboard or Wallet page
- Minimum cashout: $2.00 (2000 gems)
- Requires MTurk Worker ID (add in Profile)
- Cashouts processed via worker-specific MTurk HITs
- See [MTURK_SETUP.md](../MTURK_SETUP.md) for complete cashout guide

For setup and running the game, refer to [README.md](../README.md).
