# Human Hunter Game Rules and Logistics

## Overview
Human Hunter is a web-based social deduction game inspired by a reverse Turing Test. It pits one human player against four AI agents in a group chat setting. The AIs aim to identify and vote out the human, while the human tries to blend in and survive.

## Players
- **Total Players:** 5
  - 1 Human Player (you, the user, labeled as "You")
  - 4 AI Agents (labeled as "Player X", powered by an LLM like GPT)

Roles are assigned at the start: The human knows they are human, and AIs know they are AIs but must pretend to be human.

## Objectives
- **AI Agents' Objective:** Identify the human through conversation and vote them out. They must act human-like to avoid being voted out themselves.
- **Human Player's Objective:** Survive 3 rounds of voting by blending in and avoiding suspicion.

## Game Flow
The game proceeds in rounds until a win condition is met. Each round consists of:

1. **Discussion Round (3 minutes):**
   - A random conversation topic is presented (e.g., "What's the best topping for pizza?").
   - All players chat freely in real-time via a group chat interface.
   - AIs respond conversationally, analyzing the chat to spot the human while acting natural.

2. **Voting Round (1 minute):**
   - Chat is disabled.
   - Each player votes for one other player they suspect is the human (cannot vote for yourself).
   - Votes are cast by clicking on a player's name in the UI.

3. **Elimination:**
   - The player with the most votes is eliminated, and their role (Human or AI) is revealed.
   - If it's the human, the AIs win.
   - If it's an AI, the game continues to the next round with remaining players.

## Win/Loss Conditions
- **AIs Win:** If the human is eliminated in any round.
- **Human Wins:** If the human survives 3 rounds (i.e., 3 AIs are eliminated first).
- The game ends immediately when a win condition is met.

## Logistics and Tips
- **Timers:** Discussion is strictly 3 minutes; voting is 1 minute. The UI shows a countdown.
- **Chat Interface:** Messages are attributed to senders (e.g., "Player 2: I think pineapple is great!"). Human input is at the bottom; disabled during voting.
- **Player List:** Shows all players, with indicators for voted/elimated status.
- **AI Behavior:** AIs have assigned personalities (e.g., sarcastic, cheerful) and aim to be believable humans. They analyze chats for "human-like" traits.
- **Restarting:** Refresh the page or use the /start endpoint to reset the game.
- **Technical Notes:** Ensure the backend is running with a valid OpenAI API key for AI responses. The game is single-player (you vs. AIs), but the backend manages all state.

For setup and running the game, refer to README.md.
