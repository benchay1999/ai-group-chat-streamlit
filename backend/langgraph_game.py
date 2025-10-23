"""
LangGraph Multi-Agent Game Implementation.
Defines the StateGraph with all agent nodes and orchestration logic.
"""

import asyncio
import random
import time
import json
from typing import Dict, List, Literal, Optional
from collections import Counter

from langgraph.graph import StateGraph, END
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, SystemMessage

from .langgraph_state import GameState, Phase, ChatMessage, create_initial_state
from .config import (
    AI_MODEL_NAME, 
    AI_TEMPERATURE, 
    GAME_TOPICS, 
    MESSAGE_COOLDOWN,
    ROUNDS_TO_WIN
)


class GameGraph:
    """
    Main game graph orchestrator.
    Manages the LangGraph StateGraph and all agent nodes.
    """
    
    def __init__(self):
        """Initialize the game graph with LangChain models."""
        self.llm = ChatOpenAI(
            model=AI_MODEL_NAME,
            temperature=AI_TEMPERATURE
        )
        self.graph = self._build_graph()
    
    def _build_graph(self) -> StateGraph:
        """
        Build the complete StateGraph with all nodes and edges.
        
        Returns:
            Compiled StateGraph ready for execution
        """
        # Create the graph
        workflow = StateGraph(GameState)
        
        # Add nodes
        workflow.add_node("initialize_game", self.initialize_game_node)
        workflow.add_node("discussion_phase", self.discussion_phase_node)
        workflow.add_node("ai_chat_agent", self.ai_chat_agent_node)
        workflow.add_node("voting_phase", self.voting_phase_node)
        workflow.add_node("ai_vote_agent", self.ai_vote_agent_node)
        workflow.add_node("elimination", self.elimination_node)
        workflow.add_node("check_win_condition", self.check_win_condition_node)
        workflow.add_node("new_round", self.new_round_node)
        workflow.add_node("game_over", self.game_over_node)
        
        # Set entry point
        workflow.set_entry_point("initialize_game")
        
        # Add edges
        workflow.add_edge("initialize_game", "discussion_phase")
        workflow.add_edge("discussion_phase", "ai_chat_agent")
        
        # Conditional routing after AI chat
        workflow.add_conditional_edges(
            "ai_chat_agent",
            self.should_continue_discussion,
            {
                "continue": "ai_chat_agent",
                "voting": "voting_phase"
            }
        )
        
        workflow.add_edge("voting_phase", "ai_vote_agent")
        
        # Conditional routing after AI voting
        workflow.add_conditional_edges(
            "ai_vote_agent",
            self.should_continue_voting,
            {
                "continue": "ai_vote_agent",
                "eliminate": "elimination"
            }
        )
        
        workflow.add_edge("elimination", "check_win_condition")
        
        # Conditional routing after win check
        workflow.add_conditional_edges(
            "check_win_condition",
            self.check_game_status,
            {
                "continue": "new_round",
                "game_over": "game_over"
            }
        )
        
        workflow.add_edge("new_round", "discussion_phase")
        workflow.add_edge("game_over", END)
        
        # Compile with increased recursion limit
        # Default is 25, increase to 100 to handle multiple AI messages and rounds
        return workflow.compile(
            checkpointer=None,
            debug=False
        )
    
    # ============================================================
    # Node Implementations
    # ============================================================
    
    def initialize_game_node(self, state: GameState) -> GameState:
        """
        Initialize the game with starting state.
        Broadcasts initial game info to frontend.
        """
        # Add broadcast messages for initialization
        broadcasts = [
            {"type": "player_list", "players": [p["id"] for p in state["players"]]},
            {"type": "topic", "topic": state["topic"]},
            {"type": "phase", "phase": state["phase"].value, "message": "Discussion started!"}
        ]
        
        return {
            "broadcast_queue": broadcasts
        }
    
    def discussion_phase_node(self, state: GameState) -> GameState:
        """
        Manage the discussion phase.
        Uses active decision-making to determine which AIs should participate.
        """
        # Get active AI players
        active_ais = [
            p["id"] for p in state["players"] 
            if p["role"] == "ai" and not p["eliminated"]
        ]
        
        # Let each AI actively decide whether to respond
        responding_ais = []
        for ai_id in active_ais:
            if self._should_agent_respond(state, ai_id):
                responding_ais.append(ai_id)
        
        print(f"💬 Discussion phase: {len(responding_ais)}/{len(active_ais)} AIs chose to start conversation: {responding_ais}")
        
        return {
            "phase": Phase.DISCUSSION,
            "pending_ai_messages": responding_ais
        }
    
    def ai_chat_agent_node(self, state: GameState, ai_id: str = None) -> GameState:
        """
        AI agent node for generating chat messages.
        Can either process a specific ai_id or take from pending_ai_messages.
        
        Args:
            state: Current game state
            ai_id: Optional specific AI to process (used for concurrent execution)
        """
        if ai_id is None:
            # Fallback: read from pending_ai_messages (for graph execution)
            if not state["pending_ai_messages"]:
                return {}
            ai_id = state["pending_ai_messages"][0]
            remaining_ais = state["pending_ai_messages"][1:]
        else:
            # Explicit ai_id provided (for concurrent execution in main.py)
            remaining_ais = [aid for aid in state.get("pending_ai_messages", []) if aid != ai_id]
        
        # Check message cooldown
        if time.time() - state["last_message_time"] < MESSAGE_COOLDOWN:
            time.sleep(MESSAGE_COOLDOWN - (time.time() - state["last_message_time"]))
        
        # Generate AI message
        message = self._generate_ai_message(state, ai_id)
        
        # Create chat message
        chat_msg: ChatMessage = {
            "sender": ai_id,
            "message": message,
            "timestamp": time.time()
        }
        
        # Return message and metadata (typing indicators handled by async caller)
        return {
            "chat_history": [chat_msg],
            "pending_ai_messages": remaining_ais,
            "last_message_time": time.time(),
            "ai_message": message,
            "ai_sender": ai_id,
            "typing_delay": random.uniform(1, 2)  # Pass delay to async handler
        }
    
    def voting_phase_node(self, state: GameState) -> GameState:
        """
        Transition to voting phase.
        Initialize voting for all active players.
        """
        active_ais = [
            p["id"] for p in state["players"] 
            if p["role"] == "ai" and not p["eliminated"]
        ]
        
        broadcasts = [
            {
                "type": "phase", 
                "phase": "Voting", 
                "message": "Discussion ended. Time to vote."
            }
        ]
        
        return {
            "phase": Phase.VOTING,
            "pending_ai_votes": active_ais,
            "votes": {},
            "broadcast_queue": broadcasts
        }
    
    def ai_vote_agent_node(self, state: GameState, ai_id: Optional[str] = None) -> GameState:
        """
        AI agent node for casting votes.
        Each execution processes one AI agent from pending_ai_votes.
        """
        if not state.get("pending_ai_votes"):
            return {}
        
        # Get next AI to vote (or use provided ai_id)
        if ai_id is None:
            ai_id = state["pending_ai_votes"][0]
            remaining_voters = state["pending_ai_votes"][1:]
        else:
            remaining_voters = [aid for aid in state.get("pending_ai_votes", []) if aid != ai_id]
        
        # Small delay for realism
        time.sleep(random.uniform(0.5, 1.2))
        
        # Generate AI vote
        voted_for = self._generate_ai_vote(state, ai_id)
        
        # Update votes
        new_votes = state["votes"].copy()
        new_votes[ai_id] = voted_for
        
        broadcasts = [
            {"type": "voted", "player": ai_id}
        ]
        
        return {
            "votes": new_votes,
            "pending_ai_votes": remaining_voters,
            "broadcast_queue": broadcasts
        }
    
    def elimination_node(self, state: GameState) -> GameState:
        """
        Process elimination based on votes.
        Determine which player is eliminated and update state.
        """
        # Count votes
        vote_counts = Counter(state["votes"].values())
        
        if not vote_counts:
            # No votes cast - randomly eliminate an AI
            active_players = [
                p["id"] for p in state["players"] 
                if not p["eliminated"] and p["id"] != "You"
            ]
            eliminated = random.choice(active_players) if active_players else None
        else:
            # Get player(s) with most votes
            max_votes = max(vote_counts.values())
            candidates = [
                player for player, count in vote_counts.items() 
                if count == max_votes
            ]
            eliminated = random.choice(candidates) if len(candidates) > 1 else candidates[0]
        
        # Update player elimination status
        updated_players = []
        eliminated_role = None
        for p in state["players"]:
            if p["id"] == eliminated:
                updated_players.append({**p, "eliminated": True})
                eliminated_role = p["role"]
            else:
                updated_players.append(p)
        
        broadcasts = [
            {
                "type": "elimination",
                "eliminated": eliminated,
                "role": eliminated_role
            }
        ]
        
        return {
            "phase": Phase.ELIMINATION,
            "players": updated_players,
            "eliminated_player": eliminated,
            "broadcast_queue": broadcasts
        }
    
    def check_win_condition_node(self, state: GameState) -> GameState:
        """
        Check if the game has a winner.
        """
        # Check if human was eliminated
        human_eliminated = any(
            p["role"] == "human" and p["eliminated"] 
            for p in state["players"]
        )
        
        if human_eliminated:
            return {"winner": "ai"}
        
        # Check if enough AIs eliminated (human wins after ROUNDS_TO_WIN rounds)
        eliminated_ais = sum(
            1 for p in state["players"] 
            if p["role"] == "ai" and p["eliminated"]
        )
        
        if eliminated_ais >= ROUNDS_TO_WIN:
            return {"winner": "human"}
        
        return {"winner": None}
    
    def new_round_node(self, state: GameState) -> GameState:
        """
        Set up a new round after elimination.
        """
        new_round = state["round"] + 1
        new_topic = random.choice(GAME_TOPICS)
        
        broadcasts = [
            {
                "type": "new_round",
                "round": new_round,
                "topic": new_topic
            }
        ]
        
        return {
            "round": new_round,
            "topic": new_topic,
            "phase": Phase.DISCUSSION,
            "votes": {},
            "round_start_time": time.time(),
            "broadcast_queue": broadcasts
        }
    
    def game_over_node(self, state: GameState) -> GameState:
        """
        Handle game over state.
        """
        broadcasts = [
            {
                "type": "game_over",
                "winner": state["winner"]
            }
        ]
        
        return {
            "phase": Phase.GAME_OVER,
            "broadcast_queue": broadcasts
        }
    
    # ============================================================
    # Conditional Edge Functions
    # ============================================================
    
    def should_continue_discussion(self, state: GameState) -> Literal["continue", "voting"]:
        """
        Determine if discussion should continue or move to voting.
        """
        # Check if there are pending AI messages
        if state["pending_ai_messages"]:
            return "continue"
        
        # Check if discussion time has elapsed (simplified check)
        # In production, this would be managed by external timer
        return "voting"
    
    def should_continue_voting(self, state: GameState) -> Literal["continue", "eliminate"]:
        """
        Determine if voting should continue or move to elimination.
        """
        # Check if there are pending AI votes
        if state["pending_ai_votes"]:
            return "continue"
        
        # Check if all active players have voted
        active_players = [p["id"] for p in state["players"] if not p["eliminated"]]
        all_voted = all(player in state["votes"] for player in active_players)
        
        if all_voted:
            return "eliminate"
        
        return "continue"
    
    def check_game_status(self, state: GameState) -> Literal["continue", "game_over"]:
        """
        Determine if game should continue or end.
        """
        if state["winner"] is not None:
            return "game_over"
        return "continue"
    
    # ============================================================
    # Helper Methods for AI Generation
    # ============================================================
    
    def _should_agent_respond(self, state: GameState, ai_id: str) -> bool:
        """
        Determine if an AI agent should respond to the current conversation state.
        Uses LLM to make an active decision based on conversation context.
        
        Args:
            state: Current game state
            ai_id: AI agent identifier
        
        Returns:
            True if agent should respond, False otherwise
        """
        personality = state["ai_personalities"][ai_id]
        # Build visible conversation history using exact names
        def visible_name(real_id: str) -> str:
            return real_id
        
        recent_messages = state["chat_history"][-8:]  # Last 8 messages for context
        visible_history = "\n".join([
            f"{visible_name(msg['sender'])}: {msg['message']}"
            for msg in recent_messages
        ]) if recent_messages else "No messages yet."
        
        # Count how many times this AI has spoken
        ai_message_count = sum(1 for msg in state["chat_history"] if msg["sender"] == ai_id)
        total_messages = len(state["chat_history"])
        
        # Check if this AI was the last speaker
        last_speaker = state["chat_history"][-1]["sender"] if state["chat_history"] else None
        was_last_speaker = last_speaker == ai_id
        
        # Identify who just spoke
        last_speaker_info = ""
        if last_speaker and last_speaker != ai_id:
            last_speaker_info = f" {visible_name(last_speaker)} just spoke."
        elif was_last_speaker:
            last_speaker_info = " You were the last person to speak."
        
        # Determine conversation context
        participation_rate = (ai_message_count / max(1, total_messages)) * 100
        
        # Strategic context
        strategic_context = f"You have sent {ai_message_count} out of {total_messages} total messages ({participation_rate:.0f}% participation).{last_speaker_info}"

        # Timing context: seconds since last message to support quiet-time reasoning
        try:
            time_since_last = time.time() - state.get('last_message_time', time.time())
        except Exception:
            time_since_last = 0.0
        timing_context = f"Time since last message: {time_since_last:.1f}s."
        
        system_prompt = (
            f"You are {ai_id}, an AI agent in a group-chat with personality: {personality}.\n"
            "Your goal is to act like a human user as much as possible and participate naturally in group conversations.\n\n"
            f"Current topic: {state['topic']}\n"
            f"{strategic_context}\n{timing_context}\n\n"
            "Decide conservatively whether you should respond now. Prefer NOT responding unless at least one of these is strongly true:\n"
            "- You can add new, relevant information or a natural follow-up.\n"
            "- You were directly addressed or asked a question.\n"
            "- The chat has been quiet for over ~10 seconds\n"
            "- You can engage/answer to what other players said, without providing too obvious or hoaky answers.\n"
            "- Your participation so far is too low (<10%) and you have a concise point.\n\n"
            "If you did not talk for more than 15 seconds, you MUST talk."
            "Recent conversation:\n"
            f"{visible_history}\n\n"
            "Return ONLY JSON: {\"should_respond\": true/false, \"reason\": \"brief reason\"}"
        )
        
        messages = [HumanMessage(content=system_prompt)]
        
        try:
            response = self.llm.invoke(messages)
            decision_data = json.loads(response.content)
            should_respond = decision_data.get("should_respond", False)
            reason = decision_data.get("reason", "No reason provided")
            print(f"🤔 {ai_id} decision: {should_respond} - {reason}")
            return should_respond
        except (json.JSONDecodeError, KeyError, Exception) as e:
            print(f"⚠️ Error in decision-making for {ai_id}: {e}")
            # Fallback: respond with 30% probability
            return random.random() < 0.3
    
    def _generate_ai_message(self, state: GameState, ai_id: str) -> str:
        """
        Generate a chat message for an AI agent using LangChain.
        Uses visible player names exactly as they appear in the chat (e.g., "You", "Player 1").
        """
        personality = state["ai_personalities"][ai_id]
        
        # Build AI-visible history using exact names
        def visible_name(real_id: str) -> str:
            return real_id
        visible_history = "\n".join([
            f"{visible_name(msg['sender'])}: {msg['message']}"
            for msg in state["chat_history"]
        ])
        
        # Compute recent mentions of topic to decide anchoring strength
        recent_text = " ".join([m["message"] for m in state["chat_history"][-5:]])
        must_anchor_to_topic = state["round"] == 1 and len(state["chat_history"]) < 3 or (state["topic"].split("?")[0].lower() not in recent_text.lower())
        
        topic_clause = (
            f"The current topic is: '{state['topic']}'. Your message must directly address this topic in a natural way. "
            "Do not ask what the topic is."
        ) if must_anchor_to_topic else (
            f"Keep the current topic in mind: '{state['topic']}'."
        )
        
        system_prompt = (
            f"You are {ai_id}. "  # Explicitly state bot's own name
            "You are an AI Agent participating in a group-chat. "
            f"Your personality is {personality}. Your two objectives are:\n"
            "1. Act and chat like a human user as much as possible.\n"
            "2. Keep the conversation engaging and interesting.\n\n"
            + topic_clause + "\n\n"
            "Respond as if in a real-time group chat, building on recent messages. Keep responses concise (1-2 short sentences).\n\n"
            "You may deliberately make typos and mistakes to sound more human. Do not reveal you are an AI."
            "IMPORTANT: Output ONLY the message text. Do not respond with the character name first. e.g., when you are Player 1, DON'T say 'Player 1: hi.' Just output hi."
        )
        
        user_prompt = f"{visible_history}\n\nNow, generate your response message ONLY:"
        
        messages = [
            SystemMessage(content=system_prompt),
            HumanMessage(content=user_prompt)
        ]
        
        try:
            response = self.llm.invoke(messages)
            return response.content
        except Exception as e:
            print(f"Error generating AI message: {e}")
            return "hmm"

    def _generate_ai_vote(self, state: GameState, ai_id: str) -> str:
        """
        Generate a vote for an AI agent using LangChain.
        Returns the REAL player id (e.g., 'You' or 'Player 2').
        """
        # Build chat history using visible names
        def visible_name(real_id: str) -> str:
            return real_id
        
        visible_history = "\n".join([
            f"{visible_name(msg['sender'])}: {msg['message']}"
            for msg in state["chat_history"]
        ])
        
        eligible_targets = [
            p["id"] for p in state["players"]
            if not p["eliminated"] and p["id"] != ai_id
        ]
        eligible_targets_visible = [visible_name(pid) for pid in eligible_targets]
        targets_list = ", ".join(eligible_targets_visible)
        
        prompt = (
            f"You are {ai_id}. "  # Explicitly state bot's own name
            "Based on the chat history, who do you vote for as the AI?\n"
            "Respond ONLY with valid JSON: {\"vote\": \"<exact_name>\", \"reason\": \"Brief reason.\"}.\n"
            f"- The <exact_name> must be one of: {targets_list}.\n"
            f"- Do not vote for yourself ('{ai_id}').\n\n"
            f"History:\n{visible_history}"
        )
        
        for attempt in range(3):
            try:
                messages = [HumanMessage(content=prompt)]
                response = self.llm.invoke(messages)
                vote_data = json.loads(response.content)
                voted_visible = vote_data.get("vote")
                # Map back to real id
                if voted_visible in eligible_targets_visible:
                    index = eligible_targets_visible.index(voted_visible)
                    return eligible_targets[index]
            except (json.JSONDecodeError, KeyError, ValueError) as e:
                print(f"Vote generation attempt {attempt + 1} failed: {e}")
                prompt += "\nPrevious response invalid. Output ONLY valid JSON with 'vote' exactly from the allowed names."
        
        return random.choice(eligible_targets)


# Global graph instance
game_graph = GameGraph()


def create_game_for_room(room_code: str, num_ai_players: int = 4, ai_player_ids: list = None) -> GameState:
    """
    Create initial game state for a room.
    
    Args:
        room_code: Unique room identifier
        num_ai_players: Number of AI players
        ai_player_ids: Optional list of AI player IDs (e.g., ["Player 3", "Player 7"])
    
    Returns:
        Initial GameState
    """
    return create_initial_state(room_code, num_ai_players, ai_player_ids)


async def process_human_message(state: GameState, message: str, player_id: str) -> GameState:
    """
    Process a message from the human player and update state.
    Note: AI decision-making is now handled in main.py via trigger_agent_decisions()
    
    Args:
        state: Current game state
        message: Message text from human
    
    Returns:
        Updated game state
    """
    chat_msg: ChatMessage = {
        "sender": player_id,
        "message": message,
        "timestamp": time.time()
    }
    
    # Update state with new message
    new_state = state.copy()
    new_state["chat_history"] = state["chat_history"] + [chat_msg]
    new_state["last_message_time"] = time.time()
    
    # Don't pre-populate pending_ai_messages here
    # Let trigger_agent_decisions() handle it in main.py for consistency
    new_state["pending_ai_messages"] = []
    
    return new_state


async def process_human_vote(state: GameState, player_id: str, voted_for: str) -> GameState:
    """
    Process a vote from the human player and update state.
    
    Args:
        state: Current game state
        voted_for: ID of player being voted for
    
    Returns:
        Updated game state
    """
    new_votes = state["votes"].copy()
    new_votes[player_id] = voted_for
    
    new_state = state.copy()
    new_state["votes"] = new_votes
    
    return new_state

