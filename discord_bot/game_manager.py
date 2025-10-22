"""
Game Manager - Bridge between Discord and LangGraph Engine
Coordinates game flow and integrates Discord events with the backend game engine.
"""

import asyncio
import time
import logging
import os
import json
from typing import List, Dict, Optional
from collections import Counter
import random

import discord

from backend.langgraph_game import create_game_for_room, process_human_message, process_human_vote
from backend.langgraph_state import GameState, Phase
from backend.config import DISCUSSION_TIME, VOTING_TIME, ROUNDS_TO_WIN
from utils import DiscordRoom, DiscordPlayer, room_manager
from ui_components import (
    create_game_status_embed,
    create_results_embed,
    create_game_over_embed,
    VoteView
)

logger = logging.getLogger(__name__)


class GameSession:
    """Represents an active game session."""
    
    def __init__(self, room_code: str, room: DiscordRoom, state: GameState):
        self.room_code = room_code
        self.room = room
        self.state = state
        self.votes: Dict[int, str] = {}  # discord_id -> voted_player_id
        self.vote_lock = asyncio.Lock()
        self.discussion_task: Optional[asyncio.Task] = None
        self.voting_task: Optional[asyncio.Task] = None
        self.processing_agents: set = set()  # Track which AIs are currently responding
        self.trigger_lock = asyncio.Lock()  # Prevent concurrent trigger_ai_responses calls
        self.vote_dm_messages: Dict[int, int] = {}  # discord_id -> DM message_id for deletion


class DiscordGameManager:
    """
    Manages all active games and bridges Discord with LangGraph engine.
    """
    
    def __init__(self, coordinator_bot, ai_bots: List):
        """
        Initialize game manager.
        
        Args:
            coordinator_bot: Main coordinator bot instance
            ai_bots: List of AI agent bot instances
        """
        self.coordinator = coordinator_bot
        self.ai_bots = ai_bots
        self.active_games: Dict[str, GameSession] = {}  # room_code -> GameSession
        
        # Set game manager reference in AI bots
        for bot in ai_bots:
            bot.game_manager = self
        
        logger.info(f"Game Manager initialized with {len(ai_bots)} AI bots")
    
    async def initialize_game(self, room_code: str) -> bool:
        """
        Initialize a new game for a room.
        
        Args:
            room_code: Room code to initialize game for
        
        Returns:
            True if game was initialized successfully
        """
        room = room_manager.get_room(room_code)
        if not room:
            logger.error(f"Room {room_code} not found")
            return False
        
        if not room.can_start:
            logger.error(f"Room {room_code} cannot start (not full or not waiting)")
            return False
        
        try:
            # Calculate number of AI players needed
            num_ai = room.num_ai
            
            # Create game state using backend (synchronous function)
            state = create_game_for_room(room_code, num_ai)
            
            # Add human players to game state
            for discord_id, player in room.players.items():
                human_player = {
                    "id": player.game_player_id,
                    "role": "human",
                    "eliminated": False,
                    "personality": None
                }
                state["players"].append(human_player)
            
            # Update room
            room.game_state = state
            room_manager.start_game(room_code)
            
            # Create game session
            session = GameSession(room_code, room, state)
            self.active_games[room_code] = session
            
            # Get game channel (use game_channel_id if available, fallback to lobby channel)
            game_channel_id = room.game_channel_id or room.channel_id
            channel = self.coordinator.get_channel(game_channel_id)
            if not channel:
                logger.error(f"Channel {game_channel_id} not found")
                return False
            
            # Assign and join AI bots to the game channel
            ai_players = [p for p in state["players"] if p["role"] == "ai"]
            for i, ai_player in enumerate(ai_players[:len(self.ai_bots)]):
                bot = self.ai_bots[i]
                await bot.join_game(room_code, channel, ai_player["id"])
            
            # Post game start message in the game channel
            embed = create_game_status_embed(room, state)
            await channel.send("🎮 **Game Starting!**", embed=embed)
            
            # Start discussion phase
            await self.run_discussion_phase(room_code)
            
            logger.info(f"Game {room_code} initialized successfully")
            return True
            
        except Exception as e:
            logger.error(f"Error initializing game {room_code}: {e}", exc_info=True)
            return False
    
    async def handle_human_message(self, room_code: str, discord_id: int, message: str):
        """
        Handle a message from a human player.
        
        Args:
            room_code: Room code
            discord_id: Discord user ID
            message: Message content
        """
        session = self.active_games.get(room_code)
        if not session:
            logger.warning(f"❌ Game session {room_code} not found")
            return
        
        # Check if player is in room
        player = session.room.players.get(discord_id)
        if not player:
            logger.warning(f"❌ Player {discord_id} not in room {room_code}")
            return
        
        # Check if it's discussion phase
        if session.state["phase"] != Phase.DISCUSSION:
            logger.info(f"⏭️ Not discussion phase (current: {session.state['phase']}), ignoring message")
            return
        
        # Check if player is eliminated
        player_obj = next(
            (p for p in session.state["players"] if p["id"] == player.game_player_id),
            None
        )
        if player_obj and player_obj["eliminated"]:
            logger.info(f"💀 Player {player.game_player_id} is eliminated, ignoring message")
            return
        
        try:
            logger.info(f"💬 Processing message from {player.game_player_id}: '{message[:50]}...'")
            
            # Process message through backend (async function)
            updated_state = await process_human_message(
                session.state,
                message,
                player.game_player_id
            )
            session.state = updated_state
            
            logger.info(f"✅ Message processed, chat history length: {len(updated_state.get('chat_history', []))}")
            
            # Trigger AI responses
            logger.info(f"🤖 Triggering AI responses for room {room_code}")
            await self.trigger_ai_responses(room_code)
            
        except Exception as e:
            logger.error(f"❌ Error handling human message: {e}", exc_info=True)
    
    async def trigger_ai_responses(self, room_code: str):
        """
        Trigger AI agents to respond during discussion.
        Uses the same decision-making logic as the original LangGraph implementation.
        Uses lock to prevent concurrent executions causing duplicate responses.
        
        Args:
            room_code: Room code
        """
        session = self.active_games.get(room_code)
        if not session:
            return
        
        # Check if discussion phase
        if session.state["phase"] != Phase.DISCUSSION:
            return
        
        # Use lock to prevent concurrent trigger calls
        if session.trigger_lock.locked():
            logger.info(f"⏸️ Skipping AI trigger (already processing)")
            return
        
        async with session.trigger_lock:
            # Get active AI players
            ai_players = [
                p for p in session.state["players"]
                if p["role"] == "ai" and not p["eliminated"]
            ]
            
            # Filter out AIs that are already processing
            ai_players = [
                p for p in ai_players
                if p["id"] not in session.processing_agents
            ]
            
            if not ai_players:
                logger.info("⏭️ All AIs are already processing responses")
                return
            
            # Use the same decision-making as langgraph_game.py
            # Let each AI actively decide whether to respond
            from backend.langgraph_game import GameGraph
            import asyncio
            from concurrent.futures import ThreadPoolExecutor
            
            graph = GameGraph()
            loop = asyncio.get_event_loop()
            executor = ThreadPoolExecutor(max_workers=1)
            
            responding_ais = []
            for ai_player in ai_players:
                # Call _should_agent_respond to let AI decide
                should_respond = await loop.run_in_executor(
                    executor,
                    graph._should_agent_respond,
                    session.state,
                    ai_player["id"]
                )
                
                if should_respond:
                    responding_ais.append(ai_player)
            
            logger.info(f"💬 {len(responding_ais)}/{len(ai_players)} AIs chose to respond")
            
            # Generate and post AI messages for those who decided to respond
            for ai_player in responding_ais:
                # Mark as processing to prevent duplicates
                session.processing_agents.add(ai_player["id"])
                
                # Find corresponding bot
                bot = next(
                    (b for b in self.ai_bots if b.get_game_player_id(room_code) == ai_player["id"]),
                    None
                )
                
                if bot:
                    try:
                        # Generate AI message using LangGraph
                        ai_message = await self.generate_ai_message(room_code, ai_player["id"])
                        if ai_message:
                            await bot.post_message(room_code, ai_message)
                            
                            # Small delay between AI messages (same as original)
                            await asyncio.sleep(random.uniform(1, 3))
                    finally:
                        # Remove from processing set after completion
                        session.processing_agents.discard(ai_player["id"])
    
    async def generate_ai_message(self, room_code: str, ai_player_id: str) -> Optional[str]:
        """
        Generate an AI message using the backend LangGraph.
        
        Args:
            room_code: Room code
            ai_player_id: AI player ID
        
        Returns:
            Generated message or None
        """
        session = self.active_games.get(room_code)
        if not session:
            return None
        
        try:
            # Import the game graph to access AI generation
            from backend.langgraph_game import GameGraph
            import asyncio
            from concurrent.futures import ThreadPoolExecutor
            
            # Create a temporary graph instance for message generation
            graph = GameGraph()
            
            # Call the AI chat agent node in a thread pool to avoid blocking
            loop = asyncio.get_event_loop()
            executor = ThreadPoolExecutor(max_workers=1)
            result = await loop.run_in_executor(
                executor,
                graph.ai_chat_agent_node,
                session.state,
                ai_player_id
            )
            
            # Extract the generated message
            if result and "ai_message" in result:
                message = result["ai_message"]
                
                # Update chat history in session state
                if "chat_history" in result and result["chat_history"]:
                    session.state["chat_history"].extend(result["chat_history"])
                
                # Update last message time
                if "last_message_time" in result:
                    session.state["last_message_time"] = result["last_message_time"]
                
                return message
            
            return None
            
        except Exception as e:
            logger.error(f"Error generating AI message: {e}", exc_info=True)
            # Fallback to simple message on error
            return "I agree with that!"
    
    async def run_discussion_phase(self, room_code: str):
        """
        Run the discussion phase with timer.
        
        Args:
            room_code: Room code
        """
        session = self.active_games.get(room_code)
        if not session:
            return
        
        logger.info(f"Starting discussion phase for {room_code}")
        
        # Set phase
        session.state["phase"] = Phase.DISCUSSION
        
        # Get game channel (use game_channel_id if available, fallback to lobby channel)
        game_channel_id = session.room.game_channel_id or session.room.channel_id
        channel = self.coordinator.get_channel(game_channel_id)
        if not channel:
            return
        
        # Post phase start message
        embed = create_game_status_embed(session.room, session.state)
        await channel.send(f"💬 **Discussion Phase Started!**\n\n**Topic:** *{session.state['topic']}*", embed=embed)
        
        # Trigger initial AI responses (matches langgraph_game.py behavior)
        await self.trigger_ai_responses(room_code)
        
        # Start AI engagement task
        async def ai_engagement():
            """Periodically trigger AI messages."""
            try:
                for _ in range(int(DISCUSSION_TIME / 20)):  # Every 20 seconds
                    await asyncio.sleep(20)
                    if session.state["phase"] == Phase.DISCUSSION:
                        await self.trigger_ai_responses(room_code)
            except asyncio.CancelledError:
                pass
        
        engagement_task = asyncio.create_task(ai_engagement())
        
        # Wait for discussion time
        await asyncio.sleep(DISCUSSION_TIME)
        
        # Cancel engagement task
        engagement_task.cancel()
        
        # Transition to voting
        await self.run_voting_phase(room_code)
    
    async def run_voting_phase(self, room_code: str):
        """
        Run the voting phase with DM-based voting.
        
        Args:
            room_code: Room code
        """
        session = self.active_games.get(room_code)
        if not session:
            return
        
        logger.info(f"Starting voting phase for {room_code}")
        
        # Set phase
        session.state["phase"] = Phase.VOTING
        session.votes = {}
        
        # Get game channel (use game_channel_id if available, fallback to lobby channel)
        game_channel_id = session.room.game_channel_id or session.room.channel_id
        channel = self.coordinator.get_channel(game_channel_id)
        if not channel:
            return
        
        # Post phase start message with voting instructions
        active_players = [p for p in session.state["players"] if not p["eliminated"]]
        player_list = ", ".join([f"`{p['id']}`" for p in active_players])
        
        await channel.send(
            f"🗳️ **Voting Phase Started!**\n\n"
            f"**How to vote:**\n"
            f"• Use `/vote <player>` command in this channel\n"
            f"• Or check your DMs for the voting menu\n\n"
            f"**Active Players:** {player_list}\n"
            f"⏰ You have {VOTING_TIME} seconds to vote!"
        )
        
        # Send DMs to human players
        for discord_id, player in session.room.players.items():
            await self.send_vote_dm(room_code, discord_id)
        
        # Collect AI votes
        await self.collect_ai_votes(room_code)
        
        # Wait for votes or timeout
        await asyncio.sleep(VOTING_TIME)
        
        # Process votes
        await self.process_votes(room_code)
    
    async def handle_channel_vote(self, room_code: str, discord_id: int, player_id: str) -> tuple:
        """
        Handle a vote cast via /vote command in the channel.
        
        Args:
            room_code: Room code
            discord_id: Discord user ID of voter
            player_id: Player ID being voted for
            
        Returns:
            Tuple of (success: bool, message: str)
        """
        session = self.active_games.get(room_code)
        if not session:
            return False, "Game session not found"
        
        # Check if voting phase
        if session.state["phase"] != Phase.VOTING:
            return False, f"Not in voting phase (current phase: {session.state['phase']})"
        
        # Check if player is in room
        player = session.room.players.get(discord_id)
        if not player:
            return False, "You're not in this game"
        
        # Check if player is eliminated
        player_obj = next(
            (p for p in session.state["players"] if p["id"] == player.game_player_id),
            None
        )
        if player_obj and player_obj["eliminated"]:
            return False, "You've been eliminated and cannot vote"
        
        # Check if already voted
        async with session.vote_lock:
            if discord_id in session.votes:
                return False, "You've already voted! (Vote cannot be changed)"
        
        # Validate target player
        target_player = next(
            (p for p in session.state["players"] 
             if p["id"] == player_id and not p["eliminated"] and p["id"] != player.game_player_id),
            None
        )
        
        if not target_player:
            # Try to find by partial match or display name
            active_players = [
                p for p in session.state["players"]
                if not p["eliminated"] and p["id"] != player.game_player_id
            ]
            
            # Fuzzy match
            player_id_lower = player_id.lower().strip()
            for p in active_players:
                if player_id_lower in p["id"].lower():
                    target_player = p
                    break
            
            if not target_player:
                available = ", ".join([p["id"] for p in active_players])
                return False, f"Invalid player. Available players: {available}"
        
        # Record vote
        async with session.vote_lock:
            session.votes[discord_id] = target_player["id"]
            logger.info(f"✅ {player.game_player_id} voted for {target_player['id']} via /vote command")
        
        # Delete the DM voting message if it exists
        if discord_id in session.vote_dm_messages:
            try:
                user = await self.coordinator.fetch_user(discord_id)
                if user:
                    # Fetch the DM channel
                    dm_channel = await user.create_dm()
                    # Fetch and delete the message
                    try:
                        dm_message = await dm_channel.fetch_message(session.vote_dm_messages[discord_id])
                        await dm_message.delete()
                        logger.info(f"🗑️ Deleted vote DM for {player.game_player_id}")
                    except discord.NotFound:
                        logger.info(f"Vote DM already deleted for {player.game_player_id}")
                    except discord.Forbidden:
                        logger.warning(f"Cannot delete vote DM for {player.game_player_id} (no permission)")
                    
                    # Remove from tracking dict
                    del session.vote_dm_messages[discord_id]
            except Exception as e:
                logger.error(f"Error deleting vote DM: {e}")
        
        return True, f"Vote recorded for {target_player['id']}"
    
    async def send_vote_dm(self, room_code: str, discord_id: int):
        """
        Send voting DM to a player.
        
        Args:
            room_code: Room code
            discord_id: Discord user ID
        """
        session = self.active_games.get(room_code)
        if not session:
            return
        
        player = session.room.players.get(discord_id)
        if not player:
            return
        
        # Get user
        user = await self.coordinator.fetch_user(discord_id)
        if not user:
            logger.error(f"User {discord_id} not found")
            return
        
        # Get active players (excluding voter)
        active_players = [
            p["id"] for p in session.state["players"]
            if not p["eliminated"] and p["id"] != player.game_player_id
        ]
        
        if not active_players:
            return
        
        # Create vote view
        async def vote_callback(voted_player: str):
            async with session.vote_lock:
                session.votes[discord_id] = voted_player
                logger.info(f"Player {discord_id} voted for {voted_player}")
        
        from ui_components import create_vote_embed
        embed = create_vote_embed(session.room, session.state, player.game_player_id)
        view = VoteView(active_players, room_code, vote_callback)
        
        try:
            dm_message = await user.send(embed=embed, view=view)
            # Store the DM message ID so we can delete it later if they use /vote
            session.vote_dm_messages[discord_id] = dm_message.id
            logger.info(f"📬 Sent vote DM to {player.game_player_id} (message ID: {dm_message.id})")
        except Exception as e:
            logger.error(f"Error sending vote DM to {discord_id}: {e}")
    
    async def collect_ai_votes(self, room_code: str):
        """
        Collect votes from AI players.
        
        Args:
            room_code: Room code
        """
        session = self.active_games.get(room_code)
        if not session:
            return
        
        # Get active AI players
        ai_players = [
            p for p in session.state["players"]
            if p["role"] == "ai" and not p["eliminated"]
        ]
        
        # Use the same voting logic as langgraph_game.py
        from backend.langgraph_game import GameGraph
        import asyncio
        from concurrent.futures import ThreadPoolExecutor
        
        graph = GameGraph()
        loop = asyncio.get_event_loop()
        executor = ThreadPoolExecutor(max_workers=1)
        
        # Each AI votes using LangGraph AI generation (same as original)
        for ai_player in ai_players:
            # Call _generate_ai_vote to use intelligent voting
            target = await loop.run_in_executor(
                executor,
                graph._generate_ai_vote,
                session.state,
                ai_player["id"]
            )
            
            if target:
                session.state["votes"][ai_player["id"]] = target
                logger.info(f"AI {ai_player['id']} voted for {target}")
    
    async def process_votes(self, room_code: str):
        """
        Process votes and eliminate a player.
        
        Args:
            room_code: Room code
        """
        session = self.active_games.get(room_code)
        if not session:
            return
        
        logger.info(f"Processing votes for {room_code}")
        
        # Combine human and AI votes
        all_votes = dict(session.state["votes"])  # AI votes
        
        for discord_id, voted_player in session.votes.items():
            player = session.room.players.get(discord_id)
            if player:
                all_votes[player.game_player_id] = voted_player
        
        # Count votes
        vote_counts = Counter(all_votes.values())
        
        if not vote_counts:
            logger.warning(f"No votes cast in {room_code}")
            return
        
        # Determine eliminated player
        eliminated_player_id = vote_counts.most_common(1)[0][0]
        
        # Get player info
        eliminated_player = next(
            (p for p in session.state["players"] if p["id"] == eliminated_player_id),
            None
        )
        
        if not eliminated_player:
            logger.error(f"Eliminated player {eliminated_player_id} not found")
            return
        
        # Mark as eliminated
        eliminated_player["eliminated"] = True
        was_human = eliminated_player["role"] == "human"
        
        # Get game channel (use game_channel_id if available, fallback to lobby channel)
        game_channel_id = session.room.game_channel_id or session.room.channel_id
        channel = self.coordinator.get_channel(game_channel_id)
        if not channel:
            return
        
        # Post results
        embed = create_results_embed(
            session.room,
            session.state,
            eliminated_player_id,
            vote_counts,
            was_human
        )
        await channel.send(embed=embed)
        
        # Mark AI bot as eliminated if applicable
        if not was_human:
            bot = next(
                (b for b in self.ai_bots if b.get_game_player_id(room_code) == eliminated_player_id),
                None
            )
            if bot:
                await bot.mark_eliminated(room_code)
        
        # Check win condition
        await asyncio.sleep(3)
        await self.check_win_condition(room_code)
    
    async def check_win_condition(self, room_code: str):
        """
        Check if game has ended and handle accordingly.
        
        Args:
            room_code: Room code
        """
        session = self.active_games.get(room_code)
        if not session:
            return
        
        # Check if any humans remain
        remaining_humans = [
            p for p in session.state["players"]
            if p["role"] == "human" and not p["eliminated"]
        ]
        
        # Check if humans won (survived required rounds)
        if remaining_humans and session.state["round"] >= ROUNDS_TO_WIN:
            await self.end_game(room_code, "human")
            return
        
        # Check if AI won (no humans remaining)
        if not remaining_humans:
            await self.end_game(room_code, "ai")
            return
        
        # Continue to next round
        session.state["round"] += 1
        await asyncio.sleep(2)
        await self.run_discussion_phase(room_code)
    
    async def end_game(self, room_code: str, winner: str):
        """
        End the game and display results.
        Deletes the dedicated game channel after a delay.
        
        Args:
            room_code: Room code
            winner: 'human' or 'ai'
        """
        session = self.active_games.get(room_code)
        if not session:
            return
        
        logger.info(f"Game {room_code} ended, winner: {winner}")
        
        session.state["winner"] = winner
        session.state["phase"] = Phase.GAME_OVER
        
        # Get game channel (prioritize game_channel_id if available)
        game_channel_id = session.room.game_channel_id or session.room.channel_id
        channel = self.coordinator.get_channel(game_channel_id)
        
        if channel:
            embed = create_game_over_embed(session.state, winner)
            await channel.send(embed=embed)
            
            # If this is a dedicated game channel, notify about deletion
            if session.room.game_channel_id:
                await channel.send(
                    "🔔 This channel will be deleted in 30 seconds.\n"
                    "Thank you for playing Human Hunter!"
                )
        
        # Save session stats
        await self.save_session_stats(room_code, session.state)
        
        # Remove AI bots from game
        for bot in self.ai_bots:
            if bot.is_in_game(room_code):
                await bot.leave_game(room_code)
        
        # Cleanup
        await self.cleanup_game(room_code)
        
        # Delete game channel after delay (if it exists)
        if session.room.game_channel_id and channel:
            try:
                await asyncio.sleep(30)  # 30 second delay to allow reading results
                await channel.delete(reason=f"Game {room_code} ended")
                logger.info(f"Deleted game channel for room {room_code}")
            except discord.NotFound:
                logger.info(f"Game channel for room {room_code} was already deleted")
            except discord.Forbidden:
                logger.error(f"Bot lacks permission to delete channel for room {room_code}")
            except Exception as e:
                logger.error(f"Error deleting game channel: {e}", exc_info=True)
    
    async def save_session_stats(self, room_code: str, state: GameState) -> dict:
        """
        Save session statistics to discord-stats directory.
        Separate from web version for better organization.
        
        Args:
            room_code: Room code
            state: Final game state
        
        Returns:
            Stats payload dictionary
        """
        try:
            # Get project root directory (parent of discord_bot)
            current_dir = os.path.dirname(os.path.abspath(__file__))
            root = os.path.dirname(current_dir)
            out_dir = os.path.join(root, 'discord-stats')
            
            logger.info(f"📁 Creating Discord stats directory: {out_dir}")
            os.makedirs(out_dir, exist_ok=True)
            
            # Count votes
            vote_counts: Dict[str, int] = {}
            for _, target in state.get('votes', {}).items():
                if target:
                    vote_counts[target] = vote_counts.get(target, 0) + 1
            
            # Create payload
            chat_history_len = len(state.get('chat_history', []))
            payload = {
                'room_code': room_code,
                'platform': 'discord',  # Mark as Discord game
                'topic': state.get('topic'),
                'started_at': state.get('round_start_time'),
                'ended_at': time.time(),
                'players': [
                    {'id': p['id'], 'role': p['role'], 'eliminated': p.get('eliminated', False)}
                    for p in state.get('players', [])
                ],
                'chat_history': state.get('chat_history', []),
                'votes': state.get('votes', {}),
                'vote_counts': vote_counts,
                'eliminated_player': state.get('eliminated_player'),
                'winner': state.get('winner'),
                'rounds_played': state.get('round', 1)
            }
            
            # Save to file
            fname = f"{room_code}-{int(time.time())}.json"
            path = os.path.join(out_dir, fname)
            
            with open(path, 'w') as f:
                json.dump(payload, f, ensure_ascii=False, indent=2)
            
            logger.info(f"📊 Session stats saved successfully!")
            logger.info(f"   File: {path}")
            logger.info(f"   Room: {room_code}")
            logger.info(f"   Players: {len(payload['players'])}")
            logger.info(f"   Messages: {chat_history_len}")
            logger.info(f"   Votes: {len(state.get('votes', {}))}")
            logger.info(f"   Winner: {payload['winner']}")
            
            return payload
            
        except Exception as e:
            logger.error(f"❌ Error saving session stats: {e}", exc_info=True)
            return {}
    
    async def cleanup_game(self, room_code: str):
        """
        Clean up a finished game.
        
        Args:
            room_code: Room code
        """
        # Remove from active games
        if room_code in self.active_games:
            del self.active_games[room_code]
        
        # End room in room manager
        room_manager.end_game(room_code)
        
        logger.info(f"Game {room_code} cleaned up")

