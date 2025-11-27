import os
import time as _time
import json
import uuid as uuid_lib
from datetime import datetime
from typing import Dict, Optional, List
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc, func

from backend.global_state import rooms
from backend.langgraph_state import GameState
from backend.config import (
    STAKE_PERCENTAGE, SINGLE_HUMAN_BASE_GEMS, MULTI_HUMAN_BASE_GEMS, 
    DISCUSSION_TIME, VOTING_TIME, GEMS_PER_DOLLAR
)
from backend.database import (
    User, Session as DBSession, UserRole, PaymentStatus, RoomStake,
    SessionPlayer, AIAgentUsage, async_session_maker
)
from backend.pricing import calculate_cost
from backend.gamification import (
    calculate_game_points, check_achievements, update_streak,
    calculate_level, ACHIEVEMENTS
)
from backend.cashout_service import gems_to_usd

async def deduct_stakes(room_code: str, db: AsyncSession) -> bool:
    """
    Deduct stakes from all players (multi-human games only).
    
    IMPORTANT: This function does NOT commit the transaction.
    The caller MUST commit the transaction to finalize deductions.
    This allows atomic deduction + reward crediting in one transaction.
    
    Args:
        room_code: Room identifier
        db: Database session (must be managed by caller)
    
    Returns:
        True if successful, False if any deduction failed
    """
    
    if room_code not in rooms:
        print(f"❌ Room {room_code} not found for stake deduction")
        return False
    
    room_data = rooms[room_code]
    max_humans = room_data.get('max_humans', 1)
    
    # Only deduct stakes in multi-human games
    if max_humans <= 1:
        print(f"ℹ️  Single-human game, no stakes to deduct")
        return True
    
    # Use configured stake percentage (default from config if not in room)
    # Config is 0.5 (float), but room stores 50 (int). Convert to int scale safely.
    stake_percentage = room_data.get('stake_percentage', int(round(STAKE_PERCENTAGE * 100)))
    if stake_percentage == 0:
        print(f"ℹ️  No stakes configured for room {room_code}")
        return True
    
    player_stakes = room_data.get('player_stakes', {})
    player_user_map = room_data.get('player_user_map', {})
    minimum_stake = room_data.get('minimum_stake', 0)
    
    if not player_stakes:
        print(f"⚠️  No player stakes calculated for room {room_code}")
        return True
    
    print(f"💎 Deducting stakes for room {room_code}: {minimum_stake} gems per player")
    
    # Deduct stakes from each player
    deduction_records = []
    try:
        for player_id, stake_amount in player_stakes.items():
            # Get user ID from mapping
            user_id_str = player_user_map.get(player_id)
            if not user_id_str:
                print(f"⚠️  Player {player_id} not authenticated, skipping stake deduction")
                continue
            
            try:
                user_uuid = uuid_lib.UUID(user_id_str)
            except ValueError:
                print(f"❌ Invalid user ID format for player {player_id}: {user_id_str}")
                continue
            
            # Get user from database
            # CRITICAL FIX: Use row-level locking to prevent race conditions
            result = await db.execute(select(User).where(User.id == user_uuid).with_for_update())
            user = result.scalar_one_or_none()
            
            if not user:
                print(f"❌ User not found for player {player_id} (ID: {user_id_str})")
                # Rollback and return failure
                await db.rollback()
                return False
            
            # Validate user has sufficient gems
            if user.gem_balance < minimum_stake:
                print(f"❌ User {user.user_id} has insufficient gems: {user.gem_balance} < {minimum_stake}")
                await db.rollback()
                return False
            
            # Deduct minimum stake (actual winnings calculated at end)
            user.gem_balance -= minimum_stake
            
            # Create RoomStake record
            stake_record = RoomStake(
                id=uuid_lib.uuid4(),
                room_code=room_code,
                user_id=user_uuid,
                player_id=player_id,
                stake_percentage=stake_percentage,
                stake_amount=minimum_stake,
                deducted=1,  # True
                returned_amount=0,
                won_amount=0,
                created_at=datetime.utcnow()
            )
            db.add(stake_record)
            deduction_records.append(stake_record)
            
            print(f"💎 Deducted {minimum_stake} gems from {user.user_id} ({player_id}), new balance: {user.gem_balance}")
        
        # DON'T commit here - let the caller commit atomically with rewards
        # await db.commit()  # REMOVED - caller must commit
        print(f"✅ Stake deductions prepared for {len(deduction_records)} players (not committed yet)")
        
        # Don't broadcast yet - wait until transaction commits
        # The caller will broadcast after successful commit
        
        return True
        
    except Exception as e:
        print(f"❌ Error deducting stakes for room {room_code}: {e}")
        import traceback
        traceback.print_exc()
        await db.rollback()
        return False


async def calculate_game_rewards(
    room_code: str,
    room_data: dict,
    state: GameState,
    db: AsyncSession
) -> dict:
    """
    Calculate and distribute gems for completed game.
    
    Handles both single-human and multi-human games with stake system.
    
    Args:
        room_code: Room identifier
        room_data: Room metadata
        state: Current game state
        db: Database session
    
    Returns:
        Dictionary mapping player_id to reward details
    """
    from collections import Counter
    
    # Get human players
    human_players = [p for p in state['players'] if p['role'] == 'human' and not p['eliminated']]
    num_humans = len(human_players)
    human_player_ids = [p['id'] for p in human_players]
    
    # Get player_user_map to find authenticated users
    player_user_map = room_data.get('player_user_map', {})
    
    # Initialize rewards dict
    rewards = {}
    for player in state['players']:
        if player['role'] == 'human':
            rewards[player['id']] = {
                'base_gems': 0,
                'stake_gems': 0,
                'total_gems': 0,
                'is_winner': False,
                'identification_accuracy': 0.0,
                'votes_received': 0
            }
    
    # Count votes received by each player (for determining most voted)
    vote_counts = Counter()
    for voter_id, voted_for_list in state.get('votes', {}).items():
        if isinstance(voted_for_list, list):
            for voted_player in voted_for_list:
                vote_counts[voted_player] += 1
        else:
            # Backward compatibility for single votes
            vote_counts[voted_for_list] += 1
    
    # Store vote counts in rewards
    for player_id in human_player_ids:
        rewards[player_id]['votes_received'] = vote_counts.get(player_id, 0)
    
    # Identify players who actually cast a vote
    voters = state.get('votes', {})
    voted_player_ids = set(voters.keys())
    print(f"🗳️ Players who voted: {voted_player_ids}")
    
    if num_humans == 1:
        # SINGLE-HUMAN GAME: Participation-based
        # Everyone gets base gems (participation fee)
        # Winner is tracked but doesn't affect rewards
        # No stakes in single-human games
        
        if vote_counts:
            max_votes = max(vote_counts.values())
            winners = [pid for pid, count in vote_counts.items() if count == max_votes and pid in human_player_ids]
        else:
            winners = []
        
        # Everyone gets base gems (participation fee) - IF THEY VOTED
        for player_id in human_player_ids:
            if player_id in voted_player_ids:
                rewards[player_id]['base_gems'] = SINGLE_HUMAN_BASE_GEMS
            else:
                print(f"⚠️ Player {player_id} did not vote - forfeiting base gems")
                rewards[player_id]['base_gems'] = 0
            
            rewards[player_id]['stake_gems'] = 0  # No stakes
            rewards[player_id]['total_gems'] = rewards[player_id]['base_gems']
            rewards[player_id]['is_winner'] = (player_id in winners)  # Track winner for display
        
        print(f"💎 Single-human game rewards (participation-based): {rewards}")
        
    else:
        # MULTI-HUMAN GAME: Complex with partial credit
        # Base reward: 100 gems for all participants
        # Stakes: Calculated based on voting accuracy
        
        # All humans get base gems - IF THEY VOTED
        for player_id in human_player_ids:
            if player_id in voted_player_ids:
                rewards[player_id]['base_gems'] = MULTI_HUMAN_BASE_GEMS
            else:
                print(f"⚠️ Player {player_id} did not vote - forfeiting base gems")
                rewards[player_id]['base_gems'] = 0
        
        # Find player(s) with most votes
        if vote_counts:
            max_votes = max(vote_counts.values())
            top_voted_players = [pid for pid, count in vote_counts.items() if count == max_votes and pid in human_player_ids]
        else:
            top_voted_players = []
        
        # Get stake configuration
        stake_percentage = room_data.get('stake_percentage', 0)
        player_stakes = room_data.get('player_stakes', {})
        
        if stake_percentage > 0 and player_stakes:
            # Calculate minimum stake (what each player risked)
            minimum_stake = room_data.get('minimum_stake', 0)
            
            num_winners = len(top_voted_players)
            num_losers = num_humans - num_winners
            
            if num_winners > 0 and num_losers > 0:
                # NEW LOGIC: Ensures winners never lose gems
                # Step 1: All winners get their stakes back (guaranteed refund)
                # Step 2: Loser stakes are pooled and split equally among winners
                # Step 3: Each winner gets (accuracy%) of their share
                
                loser_stakes_pool = minimum_stake * num_losers
                max_share_per_winner = loser_stakes_pool / num_winners  # Equal division ceiling
                
                print(f"💎 Stake distribution:")
                print(f"   Loser pool: {loser_stakes_pool} gems ({num_losers} losers × {minimum_stake})")
                print(f"   Max per winner: {max_share_per_winner} gems ({num_winners} winners)")
                
                # For each winner, calculate identification accuracy
                total_distributed = 0
                for winner_id in top_voted_players:
                    votes_needed = num_humans - 1
                    winner_votes = state['votes'].get(winner_id, [])
                    if not isinstance(winner_votes, list):
                        winner_votes = [winner_votes] if winner_votes else []
                    
                    # Calculate correct identifications (voted for other humans, not self)
                    correct_identifications = sum(1 for v in winner_votes if v in human_player_ids and v != winner_id)
                    accuracy = correct_identifications / votes_needed if votes_needed > 0 else 0.0
                    
                    # Winner gets:
                    # 1. Their stake back (guaranteed IF THEY VOTED)
                    # 2. (accuracy%) * (their equal share of loser pool)
                    if winner_id in voted_player_ids:
                        stake_refund = minimum_stake
                    else:
                        print(f"   ⚠️ Winner {winner_id} did not vote - forfeiting stake refund")
                        stake_refund = 0
                        
                    stake_winnings = int(accuracy * max_share_per_winner)
                    total_stake_reward = stake_refund + stake_winnings
                    
                    rewards[winner_id]['identification_accuracy'] = accuracy
                    rewards[winner_id]['stake_gems'] = total_stake_reward
                    rewards[winner_id]['is_winner'] = True
                    
                    total_distributed += stake_winnings
                    
                    print(f"   Winner {winner_id}:")
                    print(f"     Accuracy: {correct_identifications}/{votes_needed} = {accuracy*100:.1f}%")
                    print(f"     Refund: {stake_refund} gems (guaranteed if voted)")
                    print(f"     Winnings: {stake_winnings} gems ({accuracy*100:.1f}% of {max_share_per_winner})")
                    print(f"     Total: {total_stake_reward} gems")
                
                # Calculate residual (goes to house)
                residual = loser_stakes_pool - total_distributed
                print(f"   Residual to house: {residual} gems")
                
                # Losers get NOTHING back
                loser_ids = [pid for pid in human_player_ids if pid not in top_voted_players]
                for loser_id in loser_ids:
                    rewards[loser_id]['stake_gems'] = 0  # Get nothing back
                    print(f"   Loser {loser_id}: Lost {minimum_stake} gems, returned 0 gems")
            elif num_winners > 0 and num_losers == 0:
                # Everyone tied - no stakes change hands, refund stakes to everyone
                # Since stakes were deducted at game start, we need to credit them back
                for player_id in top_voted_players:
                    rewards[player_id]['is_winner'] = True
                    if player_id in voted_player_ids:
                        rewards[player_id]['stake_gems'] = minimum_stake  # Refund the deducted stake
                    else:
                        rewards[player_id]['stake_gems'] = 0 # Penalty for not voting
            elif num_winners == 0:
                # No one got any votes - no winners, refund stakes to everyone
                # Since stakes were deducted at game start, we need to credit them back
                for player_id in human_player_ids:
                    if player_id in voted_player_ids:
                        rewards[player_id]['stake_gems'] = minimum_stake  # Refund the deducted stake
                    else:
                        rewards[player_id]['stake_gems'] = 0 # Penalty for not voting
        else:
            # No stakes - just mark winners for display purposes
            # Even without stakes, we want to show who won (got most votes)
            if top_voted_players:
                print(f"💎 No stakes game - marking winners: {top_voted_players}")
                for player_id in top_voted_players:
                     rewards[player_id]['is_winner'] = True
        
        # Calculate total gems
        for player_id in human_player_ids:
            rewards[player_id]['total_gems'] = rewards[player_id]['base_gems'] + rewards[player_id]['stake_gems']
        
        print(f"💎 Multi-human game rewards: {rewards}")
    
    return rewards


async def save_session_stats(room_code: str, state: dict, current_user: Optional[User] = None, deduct_stakes_first: bool = False) -> dict:
    """
    Save session statistics to both group-chat-stats directory and PostgreSQL database.
    Generates a completion key for Mechanical Turk compensation tracking.
    
    Args:
        room_code: Room identifier
        state: Game state dictionary
        current_user: Optional authenticated user (automatically associated with session)
    
    Returns:
        Dictionary with session stats including completion_key
    """
    print(f"🔴🔴🔴 SAVE_SESSION_STATS CALLED for room {room_code} 🔴🔴🔴")
    print(f"   State keys: {list(state.keys())}")
    print(f"   Players: {[p['id'] for p in state.get('players', [])]}")
    print(f"   Votes: {state.get('votes', {})}")
    
    # Need to calculate path relative to project root
    # backend/services/stats_service.py -> backend/services -> backend -> project_root
    current_dir = os.path.dirname(os.path.abspath(__file__))
    backend_dir = os.path.dirname(current_dir)
    root = os.path.dirname(backend_dir)
    
    out_dir = os.path.join(root, 'group-chat-stats')
    os.makedirs(out_dir, exist_ok=True)
    
    # Calculate vote counts
    print(f"📊 Calculating vote counts...")
    vote_counts: Dict[str, int] = {}
    for _, target_list in state.get('votes', {}).items():
        # Skip empty votes
        if not target_list:
            continue
        # Handle both list votes (multi-human) and single votes (backward compatibility)
        if isinstance(target_list, list):
            # Multi-human game: count each voted player
            for target in target_list:
                if target:  # Skip empty strings in the list
                    vote_counts[target] = vote_counts.get(target, 0) + 1
        else:
            # Backward compatibility: single vote (string)
            vote_counts[target_list] = vote_counts.get(target_list, 0) + 1
    print(f"   Vote counts: {vote_counts}")
    
    # Prepare stats payload for JSON file
    print(f"📝 Preparing stats payload...")
    payload = {
        'room_code': room_code,
        'topic': state.get('topic'),
        'started_at': state.get('round_start_time'),
        'ended_at': _time.time(),
        'players': [{'id': p['id'], 'role': p['role']} for p in state.get('players', [])],
        'chat_history': state.get('chat_history', []),
        'votes': state.get('votes', {}),
        'vote_counts': vote_counts,
        'selected_suspect': state.get('selected_suspect'),
        'suspect_role': state.get('suspect_role'),
        'winner': state.get('winner'),
        'winning_players': state.get('winning_players', []),
        'gem_rewards': {}  # Will be populated after calculating rewards
    }
    print(f"✅ Payload prepared successfully")
    
    # Save to JSON file
    print(f"💾 Saving JSON file...")
    fname = f"{room_code}-{int(_time.time())}.json"
    path = os.path.join(out_dir, fname)
    try:
        with open(path, 'w') as f:
            json.dump(payload, f, ensure_ascii=False, indent=2)
        if room_code in rooms:
            rooms[room_code]['last_stats_path'] = path
        print(f"✅ JSON file saved: {path}")
    except Exception as json_error:
        print(f"❌ FAILED to save JSON file: {json_error}")
        import traceback
        traceback.print_exc()
        raise
    
    # Extract session metadata
    room_data = rooms.get(room_code, {})
    language = state.get('language', 'english')
    total_players = room_data.get('total_players', len(state.get('players', [])))
    num_humans = len([p for p in state.get('players', []) if p.get('role') == 'human'])
    discussion_duration = room_data.get('discussion_duration', DISCUSSION_TIME)
    voting_duration = room_data.get('voting_duration', VOTING_TIME)
    completed_at = payload['ended_at']
    
    # Check if debug mode (EARLY CHECK to prevent stake deductions)
    is_debug_mode = (discussion_duration == 60 or voting_duration == 30)
    print(f"🐛 Debug mode check: discussion={discussion_duration}s, voting={voting_duration}s, is_debug={is_debug_mode}")
    if is_debug_mode:
        print(f"🐛 Debug mode detected - will skip all gem distributions and stake deductions")
    
    # Generate session UUID
    session_id = uuid_lib.uuid4()
    
    # Generate a placeholder completion key for backward compatibility with database schema
    # This is no longer used for verification - MTurk uses worker_id/assignment_id instead
    completion_key = f"DEPRECATED_{session_id}"
    
    # Calculate token usage and costs
    total_input_tokens = state.get('total_input_tokens', 0)
    total_output_tokens = state.get('total_output_tokens', 0)
    game_graph = rooms[room_code]['game_graph']
    model_name = game_graph.model_name
    total_cost = calculate_cost(total_input_tokens, total_output_tokens, model_name)
    agent_token_usage = state.get('agent_token_usage', {})
    
    print(f"📊 Total token usage: {total_input_tokens} input, {total_output_tokens} output")
    print(f"💰 Total cost: ${total_cost:.6f} (model: {model_name})")
    
    # Calculate earnings based on performance
    # Will be set if current_user is in the game (for legacy session data compatibility)
    calculated_earnings_value = None
    
    # Save to PostgreSQL
    try:
        async with async_session_maker() as db:
            # IDEMPOTENCY CHECK: Check if this session already exists
            # Use room_code + completion timestamp as unique identifier
            existing_check = await db.execute(
                select(DBSession).where(
                    DBSession.room_code == room_code,
                    DBSession.stats_file_path == path
                )
            )
            existing_session = existing_check.scalar_one_or_none()
            
            if existing_session:
                print(f"⚠️ Session for room {room_code} already exists (ID: {existing_session.id}), skipping duplicate save")
                return {
                    'session_id': str(existing_session.id),
                    'completion_key': existing_session.completion_key,
                    'already_existed': True
                }
            
            # CRITICAL: Deduct stakes FIRST if requested (after voting, before rewards)
            # This makes the entire operation atomic: deduct + credit in ONE transaction
            # SKIP stake deduction in debug mode
            if deduct_stakes_first and not is_debug_mode:
                max_humans = room_data.get('max_humans', 1)
                minimum_stake = room_data.get('minimum_stake', 0)
                
                if max_humans > 1 and minimum_stake > 0:
                    print(f"💎 Deducting stakes in atomic transaction with rewards")
                    stake_success = await deduct_stakes(room_code, db)
                    if not stake_success:
                        print(f"❌ Stake deduction failed - rolling back entire transaction")
                        await db.rollback()
                        raise Exception("Failed to deduct stakes - transaction rolled back")
                    print(f"✅ Stakes deducted (not committed yet - will commit with rewards)")
            elif deduct_stakes_first and is_debug_mode:
                print(f"🐛 Debug mode - skipping stake deduction")
            
            # Calculate and distribute gems using new gem reward system
            player_user_map = room_data.get('player_user_map', {})
            
            # CRITICAL VALIDATION: Check if player_user_map is populated
            print(f"=" * 80)
            print(f"📊 SAVE SESSION STATS - Room {room_code}")
            print(f"=" * 80)
            print(f"💎 Starting gem distribution using calculate_game_rewards for {len(player_user_map)} players")
            print(f"📋 player_user_map contents: {player_user_map}")
            
            if not player_user_map:
                print(f"⚠️ WARNING: player_user_map is EMPTY for room {room_code}!")
                print(f"   Room data keys: {list(room_data.keys())}")
                print(f"   Players in state: {[p['id'] + ' (' + p['role'] + ')' for p in state.get('players', [])]}")
                print(f"   This is expected for anonymous games, but unusual for multi-human games")
            
            # Call the comprehensive reward calculation function
            print(f"🔄 Calling calculate_game_rewards...")
            rewards = await calculate_game_rewards(room_code, room_data, state, db)
            print(f"✅ calculate_game_rewards completed. Rewards calculated for {len(rewards)} players")
            print(f"📊 Rewards breakdown: {rewards}")
            
            # Track successfully credited players for session data
            credited_players = []
            
            # Calculate minimum stake once for net change calculation
            stake_percentage = room_data.get('stake_percentage', 0)
            minimum_stake = room_data.get('minimum_stake', 0) if stake_percentage > 0 else 0
            
            # Process each human player based on calculated rewards
            print(f"👥 Processing {len([p for p in state.get('players', []) if p.get('role') == 'human'])} human players for gem credits...")
            for player in state.get('players', []):
                if player.get('role') != 'human':
                    continue
                
                player_id = player['id']
                mapped_user_id_str = player_user_map.get(player_id)
                
                print(f"  🔹 Player {player_id}: mapped_user_id = {mapped_user_id_str}")
                
                # Skip unauthenticated players
                if not mapped_user_id_str:
                    print(f"     ⚠️ No user mapping found - skipping gem credit (anonymous player)")
                    continue
                
                # Get reward details from calculated rewards
                player_rewards = rewards.get(player_id, {
                    'base_gems': 0,
                    'stake_gems': 0,
                    'total_gems': 0,
                    'is_winner': False,
                    'identification_accuracy': 0.0,
                    'votes_received': 0
                })
                
                total_gems = player_rewards['total_gems']
                base_gems = player_rewards['base_gems']
                stake_gems = player_rewards['stake_gems']
                is_winner = player_rewards.get('is_winner', False)
                
                print(f"     💎 Rewards: total={total_gems}, base={base_gems}, stake={stake_gems}, winner={is_winner}")
                
                # Calculate legacy earnings value for database compatibility
                player_earnings_value = total_gems / 1000.0  # Convert gems to USD equivalent
                
                # Get the user object and credit gems
                try:
                    # CRITICAL FIX: Convert string UUID to UUID object for SQL comparison
                    try:
                        mapped_user_uuid = uuid_lib.UUID(mapped_user_id_str)
                        print(f"     ✅ UUID conversion successful: {mapped_user_uuid}")
                    except (ValueError, AttributeError) as uuid_err:
                        print(f"     ❌ Invalid UUID format: {mapped_user_id_str}, error: {uuid_err}")
                        continue
                    
                    print(f"     🔍 Querying database for user {mapped_user_uuid}...")
                    user_result = await db.execute(
                        select(User).where(User.id == mapped_user_uuid)
                    )
                    db_user = user_result.scalar_one_or_none()
                    
                    if not db_user:
                        print(f"     ❌ User with UUID {mapped_user_uuid} not found in database")
                        continue
                    
                    print(f"     ✅ User found: {db_user.user_id}, current balance: {db_user.gem_balance} gems")
                    
                    # Skip debug mode games
                    if is_debug_mode:
                        print(f"     🐛 Debug mode - skipping gem credit for {player_id}")
                        continue
                    
                    # Use calculated gems from reward system
                    gems_earned = total_gems
                    
                    # VALIDATION: Ensure gems_earned is reasonable (allow negative for stake losses)
                    if gems_earned < -100000:  # Sanity check: max 100,000 gem loss
                        print(f"⚠️ Suspiciously high gem loss ({gems_earned}), capping at -100,000")
                        gems_earned = -100000
                    elif gems_earned > 100000:  # Sanity check: max 100,000 gems per game ($100)
                        print(f"⚠️ Suspiciously high gems ({gems_earned}), capping at 100,000")
                        gems_earned = 100000
                    
                    # Credit/debit gems to user's balance (ATOMIC OPERATION)
                    # NEW: Stakes are deducted in complete_voting() just before this function
                    # So the net operation here is:
                    #   - Deduction happened just before (in complete_voting)
                    #   - Now we credit the total reward
                    #   - Net effect = -stake + reward
                    old_balance = db_user.gem_balance
                    old_total_earned = db_user.total_gems_earned
                    old_total_games = db_user.total_games
                    
                    print(f"     💰 Crediting gems to user...")
                    print(f"        Current balance: {old_balance} gems")
                    print(f"        Adding: {gems_earned} gems")
                    db_user.gem_balance += gems_earned
                    
                    # Only add to total_gems_earned if positive (don't count stake losses)
                    if gems_earned > 0:
                        db_user.total_gems_earned += gems_earned
                    
                    db_user.total_games += 1  # INCREMENT TOTAL GAMES COUNTER
                    
                    print(f"     ✅ Gems credited successfully to user {db_user.user_id}")
                    print(f"        Balance: {old_balance} → {db_user.gem_balance} gems ({gems_earned:+d})")
                    print(f"        Total earned: {old_total_earned} → {db_user.total_gems_earned}")
                    print(f"        Total games: {old_total_games} → {db_user.total_games}")
                    print(f"        Breakdown - Base: {base_gems}, Stakes: {stake_gems}")
                    
                    # Update RoomStake record with final amounts (if exists)
                    stake_result = await db.execute(
                        select(RoomStake).where(
                            RoomStake.room_code == room_code,
                            RoomStake.user_id == mapped_user_uuid
                        )
                    )
                    stake_record = stake_result.scalar_one_or_none()
                    
                    if stake_record:
                        minimum_stake = room_data.get('minimum_stake', 0)
                        
                        if stake_gems > minimum_stake:
                            # Winner: got refund + winnings
                            stake_record.won_amount = stake_gems - minimum_stake
                            stake_record.returned_amount = minimum_stake
                        elif stake_gems == minimum_stake:
                            # Tie or no stakes: got full refund, no winnings
                            stake_record.won_amount = 0
                            stake_record.returned_amount = minimum_stake
                        elif stake_gems > 0:
                            # Loser with partial return
                            stake_record.won_amount = 0
                            stake_record.returned_amount = stake_gems
                        else:
                            # Loser with no return
                            stake_record.won_amount = 0
                            stake_record.returned_amount = 0
                        
                        print(f"   Updated RoomStake record: won={stake_record.won_amount}, returned={stake_record.returned_amount}")
                    
                    # Track for session data (use first authenticated player's earnings for legacy)
                    # Calculate net change (Profit/Loss) for accurate reporting
                    # gems_earned is Gross (credited amount), but user cares about Net
                    net_change = gems_earned - minimum_stake
                    
                    credited_players.append({
                        'player_id': player_id,
                        'user_id': str(mapped_user_uuid),
                        'gems_earned': gems_earned,
                        'earnings_usd': float(player_earnings_value),
                        'base_gems': base_gems,
                        'stake_gems': stake_gems,
                        'net_change': net_change,  # Store net change for accurate SessionPlayer record
                        'is_winner': player_rewards.get('is_winner', False)
                    })
                    
                    # Store for legacy session.calculated_earnings field (use TOTAL gems earned including bonuses)
                    # FIXED: Set for ANY authenticated player, not just current_user
                    # This ensures calculated_earnings is ALWAYS populated for proper last_game_gems display
                    if not calculated_earnings_value and mapped_user_uuid:
                        calculated_earnings_value = gems_to_usd(gems_earned)
                        print(f"📊 Session calculated_earnings set to ${calculated_earnings_value} ({gems_earned} gems total) for player {player_id}")
                        
                except Exception as e:
                    print(f"     ❌ ERROR crediting gems to player {player_id} (user {mapped_user_id_str})")
                    print(f"        Error type: {type(e).__name__}")
                    print(f"        Error message: {e}")
                    print(f"        Stack trace:")
                    print(traceback.format_exc())
                    # Continue to next player - don't let one player's error stop the whole session save
                    continue
            
            print(f"=" * 80)
            print(f"✅ Gem credit phase complete")
            print(f"   Credited players: {len(credited_players)}/{len(player_user_map)}")
            if credited_players:
                print(f"   Successfully credited: {[p['player_id'] for p in credited_players]}")
            print(f"=" * 80)
            
            # Update payload with gem rewards (for JSON file storage) - FULL BREAKDOWN
            payload['gem_rewards'] = {}
            for player_id in [p['id'] for p in state.get('players', []) if p['role'] == 'human']:
                reward = rewards.get(player_id, {})
                stake_returned = reward.get('stake_gems', 0)
                base_gems = reward.get('base_gems', 0)
                total_gems = reward.get('total_gems', 0)
                
                # Calculate display values
                if minimum_stake > 0:
                    stake_display = stake_returned - minimum_stake
                    net_change = total_gems - minimum_stake
                else:
                    stake_display = 0
                    net_change = total_gems
                
                payload['gem_rewards'][player_id] = {
                    'base_gems': base_gems,
                    'stake_gems': stake_display,  # Net stake change (negative for losers)
                    'stake_amount': minimum_stake,  # What was at risk
                    'stake_returned': stake_returned,  # What came back
                    'total_gems': total_gems,  # What's credited (net after deduction)
                    'net_change': net_change,  # True net profit/loss
                    'is_winner': reward.get('is_winner', False)
                }
            payload['credited_players'] = credited_players  # Store detailed credit info
            
            # Build session data dict
            print(f"💾 Building session record...")
            session_data = {
                "id": session_id,
                "room_code": room_code,
                "completion_key": completion_key,
                "user_id": current_user.id if current_user else None,
                "language": language,
                "total_players": total_players,
                "num_human_players": num_humans,
                "discussion_duration": discussion_duration,
                "voting_duration": voting_duration,
                "payment_status": PaymentStatus.PENDING,
                "stats_file_path": path,
                "claimed_at": _time.time() if current_user else None,
                "total_input_tokens": total_input_tokens,
                "total_output_tokens": total_output_tokens,
                "total_cost": total_cost,
                "model_name": model_name
            }
            
            # Only add calculated_earnings if the column exists in the model
            if hasattr(DBSession, 'calculated_earnings'):
                session_data["calculated_earnings"] = calculated_earnings_value
            
            # Add MTurk fields if present in room data
            # MTurk context is stored per-player, so we need to find the authenticated user's context
            mturk_context = None
            if current_user:
                # Find which player_id belongs to this user
                player_user_map = room_data.get('player_user_map', {})
                mturk_contexts = room_data.get('mturk_context', {})
                
                # Find the player_id for this user
                user_id_str = str(current_user.id)
                for player_id, mapped_user_id in player_user_map.items():
                    if mapped_user_id == user_id_str:
                        # Found the player_id for this user, get their MTurk context
                        mturk_context = mturk_contexts.get(player_id)
                        if mturk_context:
                            print(f"💼 Found MTurk context for user {current_user.user_id} (player {player_id})")
                        break
            
            if mturk_context:
                session_data["mturk_worker_id"] = mturk_context.get('worker_id')
                session_data["mturk_assignment_id"] = mturk_context.get('assignment_id')
                session_data["mturk_hit_id"] = mturk_context.get('hit_id')
                print(f"💼 MTurk context saved: worker={mturk_context.get('worker_id')}, assignment={mturk_context.get('assignment_id')}")
            
            print(f"   Session ID: {session_id}")
            print(f"   Room: {room_code}")
            print(f"   Players: {num_humans} human(s), {total_players} total")
            print(f"   Duration: {discussion_duration}s discussion, {voting_duration}s voting")
            
            db_session = DBSession(**session_data)
            db.add(db_session)
            print(f"✅ Session record created and added to transaction")
            
            # Save per-agent token usage
            print(f"💾 Saving AI agent usage records ({len(agent_token_usage)} agents)...")
            for agent_id, usage in agent_token_usage.items():
                agent_cost = calculate_cost(
                    usage.get('input', 0),
                    usage.get('output', 0),
                    model_name
                )
                agent_usage_record = AIAgentUsage(
                    session_id=session_id,
                    agent_id=agent_id,
                    input_tokens=usage.get('input', 0),
                    output_tokens=usage.get('output', 0),
                    cost=agent_cost,
                    message_count=usage.get('calls', 0)
                )
                db.add(agent_usage_record)
            
            print(f"✅ AI agent usage records added")
            
            # Save player-user mappings
            player_user_map = room_data.get('player_user_map', {})
            
            print(f"=" * 80)
            print(f"👥 Creating SessionPlayer records...")
            print(f"   player_user_map: {player_user_map}")
            print(f"   state['players']: {[p['id'] + ' (' + p['role'] + ')' for p in state.get('players', [])]}")
            
            session_players_created = 0
            for player in state.get('players', []):
                player_id = player['id']
                role = player['role']
                mapped_user_id = player_user_map.get(player_id)
                
                print(f"   🔹 Player {player_id} ({role}): mapped_user_id = {mapped_user_id}")
                
                # Convert user_id string to UUID if present
                user_uuid = None
                if mapped_user_id:
                    try:
                        user_uuid = uuid_lib.UUID(mapped_user_id)
                        print(f"      ✅ Mapped to user {user_uuid}")
                    except (ValueError, AttributeError) as e:
                        print(f"      ⚠️ Invalid user_id format: {mapped_user_id}, error: {e}")
                else:
                    print(f"      ℹ️  No user mapping (anonymous or AI)")
                
                # Find gems_earned for this player from credited_players list
                player_gems = None
                for credited_player in credited_players:
                    if credited_player['player_id'] == player_id:
                        # Use net_change (Profit/Loss) for SessionPlayer record so dashboard shows accurate P/L
                        player_gems = credited_player.get('net_change', credited_player['gems_earned'])
                        print(f"      💎 Gems Net Change: {player_gems}")
                        break
                
                session_player = SessionPlayer(
                    session_id=session_id,
                    user_id=user_uuid,
                    player_id=player_id,
                    role=role,
                    gems_earned=player_gems
                )
                db.add(session_player)
                session_players_created += 1
                print(f"      💾 SessionPlayer record added (user_id={user_uuid}, gems_earned={player_gems})")
            
            print(f"✅ {session_players_created} SessionPlayer records created")
            
            # CRITICAL: Commit all changes (Session, AIAgentUsage, SessionPlayer, User gem balances)
            print(f"💾 Committing transaction to database...")
            await db.commit()
            print(f"=" * 80)
            print(f"✅ ✅ ✅ SESSION SAVED SUCCESSFULLY ✅ ✅ ✅")
            print(f"   Session ID: {session_id}")
            print(f"   Room: {room_code}")
            print(f"   Players credited: {len(credited_players)}/{len(player_user_map)}")
            print(f"   File saved: {path}")
            print(f"=" * 80)
    except Exception as e:
        print(f"=" * 80)
        print(f"❌ ❌ ❌ CRITICAL ERROR: Failed to save session to database ❌ ❌ ❌")
        print(f"   Room: {room_code}")
        print(f"   Error: {e}")
        print(f"=" * 80)
        import traceback
        traceback.print_exc()
        
        # Try to rollback the failed transaction
        try:
            await db.rollback()
            print(f"✅ Transaction rolled back successfully")
        except Exception as rollback_error:
            print(f"❌ Failed to rollback transaction: {rollback_error}")
        
        # RE-RAISE THE EXCEPTION to surface the actual error
        # This will help us identify what's breaking
        print(f"🔄 Re-raising exception to surface the error...")
        raise
    
    # Add completion key to payload
    payload['completion_key'] = completion_key
    payload['session_id'] = str(session_id)
    
    # =========================================================================
    # Gamification: Award points and check achievements
    # =========================================================================
    if current_user:
        try:
            # Determine if user won (correctly identified AI)
            user_won = False
            suspect_role = state.get('suspect_role')
            if suspect_role == 'ai':
                user_won = True
            
            # Count user messages
            user_messages = [
                msg for msg in state.get('chat_history', [])
                if any(p['id'] == msg.get('sender') and p['role'] == 'human' 
                       for p in state.get('players', []))
            ]
            num_user_messages = len(user_messages)
            
            # Check if user voted
            user_voted = any(
                p['id'] in state.get('votes', {}) and p['role'] == 'human'
                for p in state.get('players', [])
            )
            
            # Calculate points earned
            points_earned, points_breakdown = calculate_game_points(
                game_completed=True,
                won_game=user_won,
                discussion_duration=discussion_duration,
                num_messages=num_user_messages,
                voted=user_voted
            )
            
            print(f"🎮 User earned {points_earned} points! Breakdown: {points_breakdown}")
            
            # Update user stats in database
            async with async_session_maker() as db:
                # Refresh user from database
                result = await db.execute(
                    select(User).where(User.id == current_user.id)
                )
                user = result.scalar_one_or_none()
                
                if user:
                    # Get unlocked achievements before update (for checking new ones)
                    old_achievements = []
                    for achievement in ACHIEVEMENTS:
                        if achievement.requirement_type == "games_played" and user.total_games >= achievement.requirement_value:
                            old_achievements.append(achievement.id)
                        elif achievement.requirement_type == "wins" and user.total_wins >= achievement.requirement_value:
                            old_achievements.append(achievement.id)
                        elif achievement.requirement_type == "streak" and user.current_streak >= achievement.requirement_value:
                            old_achievements.append(achievement.id)
                    
                    # Update streak
                    new_current_streak, new_longest_streak = update_streak(
                        user.last_played_at,
                        user.current_streak,
                        user.longest_streak
                    )
                    
                    # Update user stats
                    user.total_games += 1
                    if user_won:
                        user.total_wins += 1
                    user.total_points += points_earned
                    user.current_streak = new_current_streak
                    user.longest_streak = new_longest_streak
                    user.last_played_at = datetime.utcnow()
                    
                    # Recalculate level
                    user.level = calculate_level(user.total_points)
                    
                    await db.commit()
                    
                    # Check for new achievements
                    new_achievements = check_achievements(
                        user.total_games,
                        user.total_wins,
                        user.current_streak,
                        user.total_points,
                        old_achievements
                    )
                    
                    # Add gamification data to payload for frontend
                    payload['gamification'] = {
                        'points_earned': points_earned,
                        'points_breakdown': points_breakdown,
                        'new_achievements': [
                            {
                                'id': ach.id,
                                'name': ach.name,
                                'description': ach.description,
                                'icon': ach.icon,
                                'points': ach.points
                            }
                            for ach in new_achievements
                        ],
                        'user_stats': {
                            'level': user.level,
                            'total_points': user.total_points,
                            'total_games': user.total_games,
                            'total_wins': user.total_wins,
                            'current_streak': user.current_streak,
                            'longest_streak': user.longest_streak
                        },
                        'won_game': user_won
                    }
                    
                    if new_achievements:
                        print(f"🏆 User unlocked {len(new_achievements)} new achievements!")
                        for ach in new_achievements:
                            print(f"   - {ach.icon} {ach.name}: {ach.description}")
                
        except Exception as e:
            print(f"⚠️  Error updating gamification stats: {e}")
            import traceback
            traceback.print_exc()
            # Don't fail the game completion if gamification fails
    
    return payload


