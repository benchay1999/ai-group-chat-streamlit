import time
import time as _time
import asyncio
import random
import numpy as np
from typing import List, Dict
from collections import Counter

from backend.global_state import rooms, room_locks, executor
from backend.langgraph_state import GameState, Phase
from backend.config import DISCUSSION_TIME, VOTING_TIME, SINGLE_HUMAN_BASE_GEMS, MULTI_HUMAN_BASE_GEMS
from backend.services.messaging import broadcast_to_room
from backend.services.stats_service import save_session_stats, calculate_game_rewards
from backend.database import async_session_maker

async def proactive_agent_engagement(room_code: str):
    """
    Periodically check if agents should proactively engage in conversation.
    This prevents long silences and encourages natural conversation flow.
    """
    while room_code in rooms:
        state = rooms[room_code]['state']
        
        # Only during discussion phase
        if state['phase'] != Phase.DISCUSSION:
            break
        
        # Wait for a period before checking (stagger checks to avoid conflicts)
        await asyncio.sleep(random.uniform(1, 2))
        
        if room_code not in rooms:
            break
        
        state = rooms[room_code]['state']
        
        # Check if still in discussion
        if state['phase'] != Phase.DISCUSSION:
            break
        
        # Check if conversation has been quiet (no messages in last 4 seconds)
        last_message_time = state.get('last_message_time', 0)
        time_since_last = time.time() - last_message_time
        
        if time_since_last > 4:
            print(f"💤 Conversation quiet for {time_since_last:.1f}s, triggering proactive engagement")
            asyncio.create_task(trigger_agent_decisions(room_code))

async def run_discussion_phase(room_code: str):
    """
    Run the discussion phase for a room.
    Manages timer and triggers voting phase.
    Also enables proactive agent engagement.
    Broadcasts server time remaining every 5 seconds for synchronization.
    FIX 9.2: Uses monotonic clock to prevent issues with system clock changes.
    """
    # Get room-specific discussion time (fallback to global config)
    discussion_time = rooms[room_code].get('discussion_duration', DISCUSSION_TIME)
    print(f"⏱️ Starting discussion phase for room {room_code}: {discussion_time} seconds")
    
    # FIX 9.2: Store phase start time using monotonic clock (immune to system clock changes)
    phase_start = _time.monotonic()
    rooms[room_code]['phase_start_time'] = phase_start
    
    # Start proactive engagement task
    engagement_task = asyncio.create_task(proactive_agent_engagement(room_code))
    
    # Countdown with periodic broadcasts for synchronization
    # FIX 9.2: Use monotonic clock time to avoid drift from system clock changes
    while True:
        # FIX 9.2: Calculate elapsed time from monotonic clock (immune to NTP adjustments)
        elapsed = _time.monotonic() - phase_start
        remaining = max(0, discussion_time - elapsed)
        
        # Exit if time is up
        if remaining <= 0:
            break
        
        # Broadcast current server time to all clients
        await broadcast_to_room(room_code, {
            "type": "timer_sync",
            "phase": "Discussion",
            "time_remaining": int(remaining)  # Round to int for display
        })
        
        # Sleep for up to 5 seconds (or remaining time if less)
        sleep_duration = min(5.0, remaining)
        await asyncio.sleep(sleep_duration)
        
        # Check if room still exists
        if room_code not in rooms:
            engagement_task.cancel()
            return
    
    print(f"⏱️ Discussion time ({discussion_time}s) elapsed for room {room_code}, transitioning to voting")
    
    # Cancel proactive engagement when discussion ends
    engagement_task.cancel()
    
    if room_code not in rooms:
        return
    
    # Ensure lock exists
    if room_code not in room_locks:
        room_locks[room_code] = asyncio.Lock()
    
    # CRITICAL: Wrap entire phase transition in lock to ensure atomicity
    # This prevents clients from fetching partially-updated state during transition
    async with room_locks[room_code]:
        state = rooms[room_code]['state']
        
        # Check if still in discussion phase
        if state['phase'] != Phase.DISCUSSION:
            return
        
        # ATOMIC STATE UPDATE - All changes happen together
        # STEP 1: Clear votes FIRST (before phase change)
        state['votes'] = {}
        
        # STEP 2: Transition to voting
        state['phase'] = Phase.VOTING
        
        # STEP 3: Clear ALL pending operations to prevent late messages
        state['pending_ai_messages'] = []
        
        # STEP 4: Count human players to determine voting rules
        num_human_players = len([p for p in state['players'] if p['role'] == 'human' and not p['eliminated']])
        
        # STEP 5: Set up AI voting for single-human games
        # AI agents only vote in SINGLE-HUMAN games
        # In multi-human games, only humans vote
        if num_human_players == 1:
            # Single-human game: AI agents participate in voting
            state['pending_ai_votes'] = [
                p['id'] for p in state['players']
                if p['role'] == 'ai' and not p['eliminated']
            ]
            print(f"🤖 Single-human game: {len(state['pending_ai_votes'])} AI agents will vote")
        else:
            # Multi-human game: only humans vote, AI agents don't vote
            state['pending_ai_votes'] = []
            print(f"👥 Multi-human game ({num_human_players} humans): Only humans vote, AI agents will not vote")
        
        # STEP 6: Get voting duration for broadcasts
        voting_duration = rooms[room_code].get('voting_duration', VOTING_TIME)
        
        # STEP 7: Commit all state changes atomically
        rooms[room_code]['state'] = state
        
        print(f"✅ Phase transition complete: DISCUSSION → VOTING in room {room_code} (atomic update)")
    
    # BROADCASTS - Outside lock (async-safe, non-blocking)
    # Stop all typing indicators for any AI that might be typing
    ai_players = [p['id'] for p in state['players'] if p['role'] == 'ai']
    for ai_id in ai_players:
        await broadcast_to_room(room_code, {
            "type": "typing",
            "player": ai_id,
            "status": "stop"
        })
    
    # Broadcast phase change with voting duration and num_human_players
    await broadcast_to_room(room_code, {
        "type": "phase",
        "phase": "Voting",
        "message": "Discussion ended. Time to vote.",
        "voting_duration": voting_duration,
        "num_human_players": num_human_players
    })
    
    # Immediately send timer sync for phase transition
    await broadcast_to_room(room_code, {
        "type": "timer_sync",
        "phase": "Voting",
        "time_remaining": int(voting_duration)
    })
    
    # Start voting phase
    asyncio.create_task(run_voting_phase(room_code))
    
    # Only trigger AI voting for single-human games
    if num_human_players == 1:
        asyncio.create_task(process_ai_votes(room_code))

async def run_voting_phase(room_code: str):
    """
    Run the voting phase for a room.
    Manages timer and triggers elimination.
    Broadcasts server time remaining every 5 seconds for synchronization.
    FIX 9.2: Uses monotonic clock to prevent issues with system clock changes.
    """
    # Get room-specific voting time (fallback to global config)
    voting_time = rooms[room_code].get('voting_duration', VOTING_TIME)
    print(f"🗳️ Starting voting phase for room {room_code}: {voting_time} seconds")
    
    # FIX 1.1: Reset voting completion flag for new voting phase
    rooms[room_code]['voting_completed'] = False
    
    # FIX 9.2: Store phase start time using monotonic clock (immune to system clock changes)
    phase_start = _time.monotonic()
    rooms[room_code]['phase_start_time'] = phase_start
    
    # Countdown with periodic broadcasts for synchronization
    # FIX 9.2: Use monotonic clock time to avoid drift from system clock changes
    while True:
        # FIX 9.2: Calculate elapsed time from monotonic clock (immune to NTP adjustments)
        elapsed = _time.monotonic() - phase_start
        remaining = max(0, voting_time - elapsed)
        
        # Exit if time is up
        if remaining <= 0:
            break
        
        # Broadcast current server time to all clients
        await broadcast_to_room(room_code, {
            "type": "timer_sync",
            "phase": "Voting",
            "time_remaining": int(remaining)  # Round to int for display
        })
        
        # Sleep for up to 5 seconds (or remaining time if less)
        sleep_duration = min(5.0, remaining)
        await asyncio.sleep(sleep_duration)
        
        # Check if room still exists
        if room_code not in rooms:
            return
    
    print(f"🗳️ Voting time ({voting_time}s) elapsed for room {room_code}, completing game")
    
    if room_code not in rooms:
        return
    
    # Ensure lock exists
    if room_code not in room_locks:
        room_locks[room_code] = asyncio.Lock()
    
    # Check phase with lock to prevent race conditions
    async with room_locks[room_code]:
        state = rooms[room_code]['state']
        
        # Check if still in voting phase
        if state['phase'] != Phase.VOTING:
            print(f"⚠️ Phase changed from VOTING to {state['phase']}, skipping completion")
            return
    
    # Force completion of voting (outside lock - complete_voting has its own locking)
    await complete_voting(room_code)

async def process_ai_votes(room_code: str):
    """
    Process AI votes asynchronously.
    """
    if room_code not in rooms:
        return
    
    state = rooms[room_code]['state']
    
    # Ensure lock exists
    if room_code not in room_locks:
        room_locks[room_code] = asyncio.Lock()

    while True:
        # CRITICAL: Use lock for condition check to prevent race conditions
        async with room_locks[room_code]:
            state = rooms[room_code]['state']
            has_pending = state.get('pending_ai_votes') and state['phase'] == Phase.VOTING
            
            if not has_pending:
                break
            
            # Get next AI voter
            ai_id = state['pending_ai_votes'][0]
        
        # DEFENSE: Check if AI has already voted
        if ai_id in state.get('votes', {}):
            print(f"⚠️ AI {ai_id} already voted - skipping duplicate vote")
            async with room_locks[room_code]:
                current_state = rooms[room_code]['state']
                if current_state.get('pending_ai_votes'):
                    current_state['pending_ai_votes'] = [p for p in current_state['pending_ai_votes'] if p != ai_id]
                    rooms[room_code]['state'] = current_state
            continue
        
        # Run single AI vote node in thread pool to avoid blocking
        # Use copy of state to avoid race conditions during generation
        input_state = state.copy()
        loop = asyncio.get_event_loop()
        game_graph = rooms[room_code]['game_graph']
        result = await loop.run_in_executor(
            executor,
            lambda: game_graph.ai_vote_agent_node(input_state, ai_id=ai_id)
        )
        
        should_complete = False
        
        # DEFENSE: Check if room/lock still exists after generation
        if room_code not in rooms or room_code not in room_locks:
            print(f"🛑 AI voting aborted - room {room_code} or lock removed")
            break
        
        # CRITICAL: Update state with LOCK
        async with room_locks[room_code]:
            current_state = rooms[room_code]['state']
            
            # Check phase again
            if current_state['phase'] != Phase.VOTING:
                break
            
            # Update state - merge votes instead of replacing to preserve human votes
            if 'votes' in result:
                print(f"🤖 AI {ai_id} voting. Before: {current_state['votes']}")
                current_state['votes'].update(result['votes'])
                print(f"🤖 AI {ai_id} voted. After: {current_state['votes']}")
            
            if 'pending_ai_votes' in result:
                current_state['pending_ai_votes'] = result['pending_ai_votes']
            
            rooms[room_code]['state'] = current_state
            
            # Check if voting complete (all players who should vote have voted)
            active_players = [p['id'] for p in current_state['players'] if not p['eliminated']]
            required_votes = len(active_players)
            
            if len(current_state['votes']) >= required_votes:
                should_complete = True
        
        # Broadcast vote
        if 'broadcast_queue' in result:
            for msg in result['broadcast_queue']:
                await broadcast_to_room(room_code, msg)
        
        if should_complete:
            await complete_voting(room_code)
            break

async def schedule_correction_message(room_code: str, ai_id: str, correction_text: str, ai_sender: str, messages_before_correction: int):
    """
    Schedule a delayed correction message for a typo.
    Waits 2-8 seconds and sends correction with asterisk prefix.
    """
    # Wait 2-8 seconds before sending correction
    correction_delay = random.uniform(2.0, 8.0)
    print(f"⏱️  Scheduling correction for {ai_id} in {correction_delay:.2f}s")
    await asyncio.sleep(correction_delay)
    
    # Check if room still exists
    if room_code not in rooms:
        print(f"🚫 Correction for {ai_id} cancelled - room deleted")
        return
    
    # Ensure lock exists
    if room_code not in room_locks:
        room_locks[room_code] = asyncio.Lock()
    
    # CRITICAL: Use lock to prevent race conditions when adding correction message
    async with room_locks[room_code]:
        current_state = rooms[room_code]['state']
        
        # Check if still in discussion phase
        if current_state['phase'] != Phase.DISCUSSION:
            print(f"🚫 Correction for {ai_id} cancelled - phase is {current_state['phase'].value}")
            return
        
        # Check if other messages were sent in between (adds realism)
        messages_now = len(current_state.get('chat_history', []))
        messages_between = messages_now - messages_before_correction
        
        print(f"📝 Sending correction for {ai_id}. {messages_between} messages sent in between.")
        
        # Create correction message
        chat_msg = {
            "sender": ai_sender,
            "message": correction_text,
            "timestamp": time.time()
        }
        
        # Add to chat history atomically
        current_state['chat_history'].append(chat_msg)
        current_state['last_message_time'] = time.time()
        rooms[room_code]['state'] = current_state
    
    # Broadcast correction (minimal delay, just thinking time)
    await broadcast_to_room(room_code, {
        "type": "message",
        "sender": ai_sender,
        "message": correction_text,
        "timestamp": chat_msg.get("timestamp", time.time())
    })
    
    print(f"✅ Correction sent for {ai_id}: {correction_text}")

async def process_single_ai_message(room_code: str, ai_id: str):
    """
    Process a single AI agent's message asynchronously.
    Allows multiple AI agents to respond simultaneously.
    Implements LLM-generated chunk-based message sending for human-like typing behavior.
    """
    if room_code not in rooms:
        return
    
    print(f"🤖 Processing message for AI {ai_id} in room {room_code}")
    
    # Ensure lock exists
    if room_code not in room_locks:
        room_locks[room_code] = asyncio.Lock()
    
    try:
        # Lock for initial read
        async with room_locks[room_code]:
            state = rooms[room_code]['state']
            
            # Check if this AI is still in pending messages
            if ai_id not in state.get('pending_ai_messages', []):
                return
            
            # We need a copy of state for the AI generation to work on
            input_state = state.copy()
        
        # Run AI chat node for this specific agent in thread pool to avoid blocking event loop
        # This takes time, so we do it OUTSIDE the lock
        loop = asyncio.get_event_loop()
        game_graph = rooms[room_code]['game_graph']
        result = await loop.run_in_executor(
            executor, 
            lambda: game_graph.ai_chat_agent_node(input_state, ai_id=ai_id)
        )
        
        if not result:
            return
            
        # DEFENSE: Check if room/lock still exists after generation
        if room_code not in rooms or room_code not in room_locks:
            print(f"🛑 AI generation aborted - room {room_code} or lock removed")
            return
        
        # DEFENSE LAYER 1: Check phase BEFORE doing anything (WITH LOCK)
        async with room_locks[room_code]:
            # Refetch state inside lock
            current_state = rooms[room_code]['state']
            if current_state['phase'] != Phase.DISCUSSION:
                print(f"🚫 AI {ai_id} message blocked - phase is {current_state['phase'].value}, not DISCUSSION")
                # Remove from pending without saving message
                if 'pending_ai_messages' in current_state:
                    current_state['pending_ai_messages'] = [p for p in current_state['pending_ai_messages'] if p != ai_id]
                    rooms[room_code]['state'] = current_state
                return
            
            # Update pending messages from result
            if 'pending_ai_messages' in result:
                current_state['pending_ai_messages'] = result['pending_ai_messages']
                rooms[room_code]['state'] = current_state
        
        # Extract message details before updating state
        if 'ai_sender' not in result or 'ai_message_data' not in result:
            return
            
        ai_sender = result['ai_sender']
        message_data = result['ai_message_data']
        
        # Extract chunks and typo information from LLM-generated response
        chunks = message_data.get('chunks', [])
        has_typo = message_data.get('has_typo', False)
        correction = message_data.get('correction', '')
        
        if not chunks:
            print(f"⚠️ No chunks in message_data for {ai_id}")
            return
        
        print(f"📝 AI {ai_id} generated {len(chunks)} chunks: {chunks}")
        if has_typo and correction:
            print(f"🔧 AI {ai_id} has typo, will send correction: {correction}")
        
        # =====================================================================
        # HYBRID DELAY CALCULATION
        # =====================================================================
        
        # Get previous message length for context awareness (cognitive load)
        # Read from input_state (safe copy)
        chat_history = input_state.get('chat_history', [])
        n_char_prev = len(chat_history[-1]['message']) if chat_history else 0
        
        # Calculate total message length from all chunks
        full_message = " ".join(chunks)
        n_char = len(full_message)
        
        # Statistical model parameters
        # 1 + N(0.255, 0.0255)×n_char + N(0.03, 0.003)×n_char_prev + Γ(2.5, 0.25)
        # https://dl.acm.org/doi/full/10.1145/3715275.3732108
        
        # Note: Adjusted for natural conversation pace
        base_delay = 0.8  # Base reaction time
        
        # Typing rate with variance (Normal distribution)
        # Moderate speed: ~4 chars/sec for natural conversation
        typing_rate_per_char = max(0.1, np.random.normal(0.25, 0.03))  # Clamp to avoid negative
        
        # Context factor - cognitive load from processing previous message
        context_rate_per_char = max(0.0, np.random.normal(0.02, 0.003))
        context_delay = context_rate_per_char * n_char_prev
        
        # Thinking time - Gamma distribution (right-skewed, models human thinking)
        # Gamma(shape=2.0, scale=0.2) has mean=0.4s, more realistic thinking
        thinking_time = np.random.gamma(2.0, 0.2)
        
        # Total statistical delay
        total_statistical_delay = base_delay + (typing_rate_per_char * n_char) + context_delay + thinking_time
        
        print(f"📊 Delay calculation for {ai_id}:")
        print(f"   Message length: {n_char} chars, Previous: {n_char_prev} chars")
        print(f"   Base: {base_delay:.2f}s, Typing: {typing_rate_per_char:.3f}s/char × {n_char} = {typing_rate_per_char * n_char:.2f}s")
        print(f"   Context: {context_delay:.2f}s, Thinking: {thinking_time:.2f}s")
        print(f"   Total delay: {total_statistical_delay:.2f}s")
        
        # Note: We already updated pending_ai_messages above inside the lock
        
        # =====================================================================
        # DISTRIBUTE DELAY ACROSS CHUNKS (HYBRID APPROACH)
        # =====================================================================
        
        # Calculate per-chunk delays proportionally
        chunk_delays = []
        total_chunk_chars = sum(len(chunk) for chunk in chunks)
        
        if len(chunks) > 1:
            # Multi-chunk: Distribute delay proportionally by character count
            for chunk in chunks:
                chunk_proportion = len(chunk) / total_chunk_chars if total_chunk_chars > 0 else 1.0 / len(chunks)
                chunk_delay = total_statistical_delay * chunk_proportion
                chunk_delays.append(chunk_delay)
        else:
            # Single chunk: Use entire delay
            chunk_delays = [total_statistical_delay]
        
        print(f"⏱️  Chunk delays: {[f'{d:.2f}s' for d in chunk_delays]}")
        
        # DEFENSE: Check phase before starting (WITH LOCK)
        async with room_locks[room_code]:
            current_state = rooms[room_code]['state']
            if current_state['phase'] != Phase.DISCUSSION:
                print(f"🚫 AI {ai_id} blocked - phase is {current_state['phase'].value}")
                return
            
            # Show typing indicator before sending chunks
            # Update room metadata (persistence source)
            if 'typing_players' not in rooms[room_code]:
                rooms[room_code]['typing_players'] = set()
            rooms[room_code]['typing_players'].add(ai_sender)
        
        await broadcast_to_room(room_code, {
            "type": "typing",
            "player": ai_sender,
            "status": "start"
        })
        
        # Send each chunk with statistically calculated delays
        for chunk_idx, (chunk, chunk_delay) in enumerate(zip(chunks, chunk_delays)):
            # DEFENSE: Check phase before each chunk
            current_state = rooms[room_code]['state']
            if current_state['phase'] != Phase.DISCUSSION:
                print(f"🚫 AI {ai_id} chunk {chunk_idx+1}/{len(chunks)} blocked - phase changed to {current_state['phase'].value}")
                # Stop typing indicator (WITH LOCK)
                async with room_locks[room_code]:
                    if 'typing_players' in rooms[room_code]:
                        rooms[room_code]['typing_players'].discard(ai_sender)
                
                await broadcast_to_room(room_code, {
                    "type": "typing",
                    "player": ai_sender,
                    "status": "stop"
                })
                return
            
            # Split chunk delay into thinking (30%) and typing (70%) for better UX
            thinking_portion = chunk_delay * 0.3
            typing_portion = chunk_delay * 0.7
            
            # Add small variance to thinking time for realism
            thinking_portion = thinking_portion * random.uniform(0.8, 1.2)
            
            print(f"💭 AI {ai_id} chunk {chunk_idx+1}/{len(chunks)}: thinking={thinking_portion:.2f}s, typing={typing_portion:.2f}s")
            
            # Thinking delay
            await asyncio.sleep(thinking_portion)
            
            # DEFENSE: Check room and phase after thinking delay
            if room_code not in rooms:
                print(f"🚫 AI {ai_id} chunk {chunk_idx+1}/{len(chunks)} blocked - room deleted during thinking")
                return
            
            current_state = rooms[room_code]['state']
            if current_state['phase'] != Phase.DISCUSSION:
                print(f"🚫 AI {ai_id} chunk {chunk_idx+1}/{len(chunks)} blocked after thinking - phase changed to {current_state['phase'].value}")
                # Stop typing indicator (WITH LOCK)
                async with room_locks[room_code]:
                    if 'typing_players' in rooms[room_code]:
                        rooms[room_code]['typing_players'].discard(ai_sender)
                
                await broadcast_to_room(room_code, {
                    "type": "typing",
                    "player": ai_sender,
                    "status": "stop"
                })
                return
            
            # Typing delay (simulates actual character-by-character typing)
            await asyncio.sleep(typing_portion)
            
            # DEFENSE: Check room still exists after typing delay
            if room_code not in rooms:
                print(f"🚫 AI {ai_id} chunk {chunk_idx+1}/{len(chunks)} blocked - room deleted during typing")
                return
            
            # CRITICAL: Update state with LOCK
            async with room_locks[room_code]:
                current_state = rooms[room_code]['state']
                # Check phase again
                if current_state['phase'] != Phase.DISCUSSION:
                    print(f"🚫 AI {ai_id} chunk {chunk_idx+1}/{len(chunks)} blocked after typing - phase changed to {current_state['phase'].value}")
                    # Stop typing indicator
                    if 'typing_players' in rooms[room_code]:
                        rooms[room_code]['typing_players'].discard(ai_sender)
                    
                    await broadcast_to_room(room_code, {
                        "type": "typing",
                        "player": ai_sender,
                        "status": "stop"
                    })
                    return
                
                # Create chat message for this chunk
                chat_msg = {
                    "sender": ai_sender,
                    "message": chunk,
                    "timestamp": time.time()
                }
                
                # Add to chat history
                current_state['chat_history'].append(chat_msg)
                current_state['last_message_time'] = time.time()
                rooms[room_code]['state'] = current_state
            
            # Broadcast chunk
            await broadcast_to_room(room_code, {
                "type": "message",
                "sender": ai_sender,
                "message": chunk,
                "timestamp": chat_msg.get("timestamp", time.time())
            })
            
            # Small pause between chunks if not the last chunk
            # Simulates time to press "enter" and start next message
            if chunk_idx < len(chunks) - 1:
                inter_chunk_pause = random.uniform(0.3, 0.5)
                print(f"⏸️  Inter-chunk pause: {inter_chunk_pause:.2f}s")
                await asyncio.sleep(inter_chunk_pause)
                
                # DEFENSE: Check room still exists after inter-chunk sleep
                if room_code not in rooms:
                    print(f"🚫 AI {ai_id} blocked after inter-chunk pause - room deleted")
                    return
        
        # Stop typing indicator after all chunks sent
        # CRITICAL: Use lock to prevent race conditions
        async with room_locks[room_code]:
            if 'typing_players' in rooms[room_code]['state']:
                rooms[room_code]['state']['typing_players'].discard(ai_sender)
            
            # Record current message count for correction scheduling (inside lock for accuracy)
            messages_before_correction = len(rooms[room_code]['state'].get('chat_history', []))
        
        await broadcast_to_room(room_code, {
            "type": "typing",
            "player": ai_sender,
            "status": "stop"
        })
        
        # Schedule correction message if has_typo is true
        # Add 20-60% probability that another AI responds between typo and correction
        if has_typo and correction and correction.strip():
            # Schedule the correction as a background task
            asyncio.create_task(
                schedule_correction_message(room_code, ai_id, correction, ai_sender, messages_before_correction)
            )
        
        # Handle any other broadcasts from result
        if 'broadcast_queue' in result:
            for msg in result['broadcast_queue']:
                await broadcast_to_room(room_code, msg)
        
        # After AI speaks, give other agents a chance to respond
        # Cooldown period to prevent immediate back-and-forth (models natural conversation pacing)
        cooldown = random.uniform(0.8, 1.5)  # More natural than fixed 1.25s
        print(f"⏱️  Post-message cooldown: {cooldown:.2f}s")
        await asyncio.sleep(cooldown)
        
        # DEFENSE: Check room still exists after cooldown
        if room_code not in rooms:
            print(f"🚫 AI {ai_id} blocked after cooldown - room deleted")
            return
        
        # DEFENSE LAYER 4: Check phase before triggering more AI responses
        # CRITICAL: Use lock for phase check to prevent race conditions
        async with room_locks[room_code]:
            current_state = rooms[room_code]['state']
            should_trigger = current_state['phase'] == Phase.DISCUSSION
        
        if should_trigger:
            # Only trigger new responses if still in discussion
            asyncio.create_task(trigger_agent_decisions(room_code, exclude_agents=[ai_id]))
        else:
            async with room_locks[room_code]:
                phase_value = rooms[room_code]['state']['phase'].value
            print(f"🚫 Not triggering new AI responses - phase is {phase_value}")
                
    finally:
        # FIX 2.5: Comprehensive cleanup to prevent ghost typing indicators
        if room_code in rooms:
            # Get AI sender for cleanup
            try:
                async with room_locks[room_code]:
                    state = rooms[room_code].get('state', {})
                    player_id_map = {p['id']: p['id'] for p in state.get('players', []) if p['id'] == ai_id}
                    ai_sender = ai_id if ai_id in player_id_map else None
            except Exception:
                ai_sender = None
            
            # Cleanup typing status to prevent ghost typers on error
            if room_code in room_locks:
                try:
                    async with room_locks[room_code]:
                        if 'typing_players' in rooms[room_code]:
                            rooms[room_code]['typing_players'].discard(ai_id)
                            if ai_sender:
                                rooms[room_code]['typing_players'].discard(ai_sender)
                except Exception:
                    pass
            
            # FIX 2.5: Broadcast typing stop to all clients (critical for cleanup)
            if ai_sender:
                try:
                    await broadcast_to_room(room_code, {
                        "type": "typing",
                        "player": ai_sender,
                        "status": "stop"
                    })
                except Exception as e:
                    print(f"⚠️ Failed to broadcast typing stop for {ai_sender}: {e}")
            
            processing_agents = rooms[room_code].get('ai_processing_agents', set())
            processing_agents.discard(ai_id)
            rooms[room_code]['ai_processing_agents'] = processing_agents
            print(f"✅ AI {ai_id} completed message in room {room_code} (cleanup ensured)")

async def trigger_agent_decisions(room_code: str, exclude_agents: list = None):
    """
    Trigger all agents to actively decide whether to respond to the current conversation.
    This enables agents to respond to each other and engage proactively.
    """
    if room_code not in rooms:
        return
    
    # Ensure lock exists
    if room_code not in room_locks:
        room_locks[room_code] = asyncio.Lock()
    
    # Read state once for decision-making (outside lock - long operation)
    state = rooms[room_code]['state']
    
    # Only trigger during discussion phase
    if state['phase'] != Phase.DISCUSSION:
        return
    
    # Check cooldown (outside lock - quick check)
    if 'last_decision_trigger_time' not in rooms[room_code]:
        rooms[room_code]['last_decision_trigger_time'] = 0
    
    current_time = time.time()
    time_since_last_trigger = current_time - rooms[room_code]['last_decision_trigger_time']
    
    # Cooldown: don't trigger decisions too frequently (minimum 2 seconds between triggers)
    if time_since_last_trigger < 2.0:
        print(f"⏸️ Skipping agent decision trigger (cooldown: {time_since_last_trigger:.1f}s < 2.0s)")
        return
    
    rooms[room_code]['last_decision_trigger_time'] = current_time
    
    # Get all active AIs, excluding specified ones
    active_ais = [
        p["id"] for p in state["players"]
        if p["role"] == "ai" and not p["eliminated"]
    ]
    
    if exclude_agents:
        active_ais = [ai for ai in active_ais if ai not in exclude_agents]
    
    if not active_ais:
        return
    
    # Run decision-making in thread pool to avoid blocking (LONG OPERATION - outside lock)
    loop = asyncio.get_event_loop()
    
    # Let each AI decide if they should respond
    game_graph = rooms[room_code]['game_graph']
    responding_ais = []
    for ai_id in active_ais:
        try:
            should_respond = await loop.run_in_executor(
                executor,
                lambda aid=ai_id: game_graph._should_agent_respond(state, aid)
            )
            if should_respond:
                responding_ais.append(ai_id)
        except Exception as e:
            print(f"⚠️ Error in decision for {ai_id}: {e}")
    
    # CRITICAL: Use lock when updating pending_ai_messages to prevent race conditions
    if responding_ais:
        async with room_locks[room_code]:
            # Re-read current state inside lock
            current_state = rooms[room_code]['state']
            
            # Double-check phase hasn't changed while we were deciding
            if current_state['phase'] != Phase.DISCUSSION:
                print(f"🚫 Agent decisions cancelled - phase changed to {current_state['phase'].value}")
                return
            
            # Merge with existing pending messages to avoid revoking previous decisions
            current_pending = current_state.get('pending_ai_messages', [])
            # Add new ones that aren't already pending (preserve order)
            new_pending = current_pending + [ai for ai in responding_ais if ai not in current_pending]
            
            current_state['pending_ai_messages'] = new_pending
            rooms[room_code]['state'] = current_state
            print(f"🎯 {len(responding_ais)}/{len(active_ais)} agents decided to respond: {responding_ais} (Merged with pending: {current_pending})")
        
        # Trigger the responses (outside lock)
        asyncio.create_task(process_ai_messages(room_code))
    else:
        print(f"🤐 No agents decided to respond this time")

async def process_ai_messages(room_code: str):
    """
    Trigger all pending AI agents to respond simultaneously.
    Each AI agent runs in its own task for realistic concurrent responses.
    Uses a lock to prevent race conditions and duplicate responses.
    """
    if room_code not in rooms:
        return
    
    # Get or create lock for this room
    if room_code not in room_locks:
        room_locks[room_code] = asyncio.Lock()
    
    # Use lock to prevent concurrent calls from creating duplicate tasks
    async with room_locks[room_code]:
        state = rooms[room_code]['state']
        
        # DEFENSE: Only process AI messages during discussion phase
        if state['phase'] != Phase.DISCUSSION:
            print(f"🚫 Not processing AI messages - phase is {state['phase'].value}, not DISCUSSION")
            return
        
        pending_ais = state.get('pending_ai_messages', []).copy()
        processing_agents = rooms[room_code].get('ai_processing_agents', set())
        
        if not pending_ais:
            return
        
        # Filter out AIs that are already processing
        ais_to_process = [ai_id for ai_id in pending_ais if ai_id not in processing_agents]
        
        if not ais_to_process:
            print(f"⏭️  All pending AIs already processing in room {room_code}")
            return
        
        print(f"🤖 Triggering {len(ais_to_process)} AI agents to respond: {ais_to_process}")
        
        # Mark these AIs as processing BEFORE creating tasks
        for ai_id in ais_to_process:
            processing_agents.add(ai_id)
        rooms[room_code]['ai_processing_agents'] = processing_agents
        
        # Create concurrent tasks for each AI agent
        tasks = [
            asyncio.create_task(process_single_ai_message(room_code, ai_id))
            for ai_id in ais_to_process
        ]
    
    # Wait for all AI responses to complete (outside the lock)
    if tasks:
        await asyncio.gather(*tasks, return_exceptions=True)

async def complete_voting(room_code: str):
    """
    Complete the voting phase and process elimination.
    Uses locking to ensure atomic state transitions.
    FIX 1.1: Added voting_completed flag to prevent race condition when called from multiple endpoints.
    """
    print(f"🟢🟢🟢 COMPLETE_VOTING CALLED for room {room_code} 🟢🟢🟢")
    
    if room_code not in rooms:
        print(f"⚠️ Room {room_code} not found in rooms dict, returning")
        return
    
    # Ensure lock exists
    if room_code not in room_locks:
        room_locks[room_code] = asyncio.Lock()
    
    # CRITICAL: Wrap entire state modification in lock for atomicity
    # This prevents clients from fetching partially-updated state during transition
    async with room_locks[room_code]:
        state = rooms[room_code]['state']
        
        # FIX 1.1: Check if voting already completed (prevents duplicate calls)
        if rooms[room_code].get('voting_completed', False):
            print(f"⚠️ Voting already completed for room {room_code}, skipping duplicate call")
            return
        
        # Check phase (double-check pattern for safety)
        if state['phase'] != Phase.VOTING:
            print(f"⚠️ Room {room_code} not in voting phase (current: {state['phase']}), returning")
            return
        
        # FIX 1.1: Set flag immediately to prevent concurrent calls
        rooms[room_code]['voting_completed'] = True
        
        print(f"🏁 Completing voting for room {room_code}")
        print(f"📊 Final votes before processing: {state.get('votes', {})}")
        
        # Determine suspect (player with most votes) and winner directly; no elimination
        # FIXED: Handle both list votes (multi-human) and single votes (backward compatibility)
        vote_counts: Dict[str, int] = {}
        for _, target_list in state.get('votes', {}).items():
            if not target_list:
                continue
            if isinstance(target_list, list):
                # Multi-human game: count each voted player
                for target in target_list:
                    vote_counts[target] = vote_counts.get(target, 0) + 1
            else:
                # Backward compatibility: single vote
                vote_counts[target_list] = vote_counts.get(target_list, 0) + 1
        
        # Determine winner based on game type
        num_humans = len([p for p in state['players'] if p['role'] == 'human' and not p['eliminated']])
        human_ids = [p['id'] for p in state['players'] if p['role'] == 'human' and not p['eliminated']]
        
        # MULTI-HUMAN GAME: Winner is the human player(s) with most votes FROM OTHER HUMANS
        if num_humans > 1:
            print(f"🎭 Multi-human game: Determining winner among {num_humans} humans")
            
            # In multi-human games, only votes FOR human players count
            # AI agents are not candidates for winning
            human_vote_counts = {pid: vote_counts.get(pid, 0) for pid in human_ids}
            
            print(f"   Human vote counts: {human_vote_counts}")
            
            if human_vote_counts and max(human_vote_counts.values()) > 0:
                max_human_votes = max(human_vote_counts.values())
                winners = [pid for pid, cnt in human_vote_counts.items() if cnt == max_human_votes]
                
                if len(winners) > 1:
                    # Multiple humans tied for most votes
                    state['winner'] = 'tie'
                    state['winning_players'] = winners
                    state['selected_suspect'] = winners[0]  # Show one for display
                    state['suspect_role'] = 'human'
                    print(f"   🤝 TIE between {winners} (each with {max_human_votes} votes)")
                else:
                    # Single winner - the human with most votes
                    state['winner'] = winners[0]  # Specific player ID
                    state['winning_players'] = winners
                    state['selected_suspect'] = winners[0]
                    state['suspect_role'] = 'human'
                    print(f"   🏆 WINNER: {winners[0]} with {max_human_votes} votes")
            else:
                # No votes or all zeros - everyone ties
                state['winner'] = 'tie'
                state['winning_players'] = human_ids
                state['selected_suspect'] = human_ids[0] if human_ids else None
                state['suspect_role'] = 'human'
                print(f"   🤝 TIE (no votes cast)")
                
        else:
            # SINGLE-HUMAN GAME: Team-based (human vs AI)
            # Most voted player determines the outcome
            suspect = None
            if vote_counts:
                max_votes = max(vote_counts.values())
                candidates = [pid for pid, cnt in vote_counts.items() if cnt == max_votes]
                suspect = random.choice(candidates) if len(candidates) > 1 else candidates[0]
            # Default fallback if no votes: choose a random AI
            if not suspect:
                ai_ids = [p['id'] for p in state['players'] if p['role'] == 'ai']
                suspect = random.choice(ai_ids) if ai_ids else None
            
            suspect_role = None
            for p in state['players']:
                if p['id'] == suspect:
                    suspect_role = p['role']
                    break
            
            state['selected_suspect'] = suspect
            state['suspect_role'] = suspect_role
            
            # Humans win if suspect is actually a human (most human-like); otherwise AIs win
            winning_team = 'human' if suspect_role == 'human' else 'ai'
            state['winner'] = winning_team
            winning_players = [p['id'] for p in state.get('players', []) if p.get('role') == winning_team]
            state['winning_players'] = winning_players
            print(f"🎮 Single-human game result: {winning_team} team wins (suspect: {suspect})")
        
        # ATOMIC STATE UPDATE
        state['phase'] = Phase.GAME_OVER
        rooms[room_code]['state'] = state
        
        # CRITICAL: Mark room as completed so it doesn't count as "operating"
        rooms[room_code]['room_status'] = 'completed'
        print(f"✅ Room {room_code} marked as COMPLETED (atomic update)")
        
        # Store vote_counts for later use (outside lock)
        # This is safe because vote_counts is a local variable we just calculated
        final_vote_counts = vote_counts.copy()
        suspect = state.get('selected_suspect')
        suspect_role = state.get('suspect_role')
    
    # BROADCASTS - Outside lock (async-safe, non-blocking)
    # Use local variables captured inside the lock
    await broadcast_to_room(room_code, {
        "type": "voting_result",
        "suspect": suspect,
        "role": suspect_role,
        "vote_counts": final_vote_counts
    })
    
    # Broadcast game over
    # Get a copy of state for game_over processing
    async with room_locks[room_code]:
        state_copy = rooms[room_code]['state'].copy()
    
    game_graph = rooms[room_code]['game_graph']
    result = game_graph.game_over_node(state_copy)
    
    # Broadcast any queued messages from game_over_node
    if 'broadcast_queue' in result:
        for msg in result['broadcast_queue']:
            await broadcast_to_room(room_code, msg)
    
    # Update state with game_over results (if any)
    if result:
        async with room_locks[room_code]:
            rooms[room_code]['state'].update(result)
    
    # Save stats at end and get gem rewards
    gem_rewards = {}  # Will store player_id -> gem_amount
    try:
        room_data = rooms.get(room_code, {})
        minimum_stake = room_data.get('minimum_stake', 0)
        
        # Get final state for gem calculations
        async with room_locks[room_code]:
            final_state = rooms[room_code]['state'].copy()
        
        # Calculate rewards first (for frontend display)
        async with async_session_maker() as temp_db:
            rewards = await calculate_game_rewards(room_code, room_data, final_state, temp_db)
            # Extract full breakdown for each player
            # NEW: Stakes are deducted and credited in the same transaction above
            # So total_gems already includes the net result
            for player_id, reward_data in rewards.items():
                stake_gems_credited = reward_data.get('stake_gems', 0)
                base_gems = reward_data.get('base_gems', 0)
                total_gems = reward_data.get('total_gems', 0)
                
                # Calculate for display
                # In multi-human games: total_gems = base + stake_reward
                # Net change = total_gems - minimum_stake (what they risked)
                if minimum_stake > 0:
                    # Multi-human game with stakes
                    stake_display = stake_gems_credited - minimum_stake  # Net stake result
                    net_change = total_gems - minimum_stake  # Net change (base + stakes - deduction)
                else:
                    # Single-human game (no stakes)
                    stake_display = 0
                    net_change = total_gems  # Just the base gems
                
                gem_rewards[player_id] = {
                    'base_gems': base_gems,
                    'stake_gems': stake_display,  # Net stake change (can be negative)
                    'stake_amount': minimum_stake,  # What was at risk
                    'stake_returned': stake_gems_credited,  # What they got back
                    'total_gems': total_gems,  # What's credited (includes deduction already)
                    'net_change': net_change,  # True net profit/loss
                    'is_winner': reward_data.get('is_winner', False)
                }
        
        # Now save the session (which will credit the gems AND deduct stakes atomically)
        await save_session_stats(room_code, final_state, deduct_stakes_first=True)
        
        # Broadcast gem rewards to players with full breakdown
        print(f"💎 Broadcasting gem rewards breakdown: {gem_rewards}")
        await broadcast_to_room(room_code, {
            "type": "gem_rewards",
            "rewards": gem_rewards
        })
        
    except Exception as save_error:
        # Log the error
        print(f"❌❌❌ CRITICAL: save_session_stats failed for room {room_code}")
        print(f"   Error: {save_error}")
        import traceback
        traceback.print_exc()
        
        # Broadcast error to frontend so players can see it
        error_message = f"⚠️ Game completed but failed to award gems. Please contact support if this persists."
        try:
            await broadcast_to_room(room_code, {
                "type": "system_message",
                "message": error_message,
                "severity": "error"
            })
        except Exception as broadcast_err:
            print(f"❌ Also failed to broadcast error: {broadcast_err}")
        
        # DON'T re-raise - game is already complete, gem rewards are secondary
        # Raising here would cause CORS errors and prevent vote response from returning
        print(f"⚠️ Continuing despite gem reward failure - game completion is more important")


