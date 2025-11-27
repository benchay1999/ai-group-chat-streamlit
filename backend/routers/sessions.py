import os
import json
import time as _time
from typing import Optional, List
from datetime import datetime, timedelta
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc, func, or_, and_
from sqlalchemy.orm import aliased

from backend.database import (
    get_async_session, User, UserRole, Session as DBSession, 
    SessionPlayer, CashoutTransaction, CashoutStatus
)
from backend.auth import get_current_user, get_current_user_optional, require_admin
from backend.global_state import rooms
from backend.services.room_management import get_assigned_humans
from backend.services.user_activity import update_user_activity
from backend.config import GEMS_PER_DOLLAR, DISCUSSION_TIME, VOTING_TIME
from backend.schemas import UserResponse, SessionResponse
from backend.gamification import (
    calculate_level, points_for_next_level, 
    get_next_close_achievements, get_motivational_message,
    ACHIEVEMENTS
)
from backend.cashout_service import gems_to_usd
from backend.earnings import get_earnings_tier
import uuid as uuid_lib

router = APIRouter()

@router.get("/api/sessions")
async def list_sessions(
    participant_name: Optional[str] = None,
    winner_name: Optional[str] = None,
    language: Optional[str] = None,
    discussion_duration: Optional[int] = None,
    voting_duration: Optional[int] = None,
    num_human_players: Optional[int] = None,
    total_players: Optional[int] = None,
    sort_by: Optional[str] = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_session)
):
    """
    List sessions for current user. Admins see all sessions with filtering options.
    """
    if current_user.role == UserRole.ADMIN:
        # Admins see all sessions with optional filters
        query = select(DBSession)
        
        # 1. Participant Filter
        if participant_name:
            p_player = aliased(SessionPlayer)
            p_user = aliased(User)
            query = query.join(p_player, p_player.session_id == DBSession.id)\
                         .join(p_user, p_player.user_id == p_user.id)\
                         .where(p_user.user_id.ilike(f"%{participant_name}%"))
        
        # 2. Winner Filter (User who participated and earned > 0 gems)
        if winner_name:
            w_player = aliased(SessionPlayer)
            w_user = aliased(User)
            query = query.join(w_player, w_player.session_id == DBSession.id)\
                         .join(w_user, w_player.user_id == w_user.id)\
                         .where(w_user.user_id.ilike(f"%{winner_name}%"))\
                         .where(w_player.gems_earned > 0)
        
        # 3. Game Type Filters
        if language:
            query = query.where(DBSession.language == language)
        if discussion_duration is not None:
            query = query.where(DBSession.discussion_duration == discussion_duration)
        if voting_duration is not None:
            query = query.where(DBSession.voting_duration == voting_duration)
        if num_human_players is not None:
            query = query.where(DBSession.num_human_players == num_human_players)
        if total_players is not None:
            query = query.where(DBSession.total_players == total_players)
            
        # 4. Sorting
        if sort_by == 'highest_reward':
            # Sort by max gems earned in the session
            subq = select(func.max(SessionPlayer.gems_earned)).where(SessionPlayer.session_id == DBSession.id).scalar_subquery()
            query = query.order_by(desc(subq))
        else:
            # Default sort: Most recent first
            query = query.order_by(desc(DBSession.completed_at))
            
        result = await db.execute(query.distinct())
        sessions_with_gems = [(s, None) for s in result.scalars().all()]
    else:
        # Regular users see sessions where they're the owner OR where they played
        # Get sessions where user is owner OR participated as a player
        # OPTIMIZATION: Fetch gems_earned directly to avoid N+1 file reads
        result = await db.execute(
            select(DBSession, SessionPlayer.gems_earned)
            .outerjoin(SessionPlayer, and_(
                SessionPlayer.session_id == DBSession.id,
                SessionPlayer.user_id == current_user.id
            ))
            .where(
                or_(
                    DBSession.user_id == current_user.id,
                    SessionPlayer.user_id == current_user.id
                )
            )
            .order_by(desc(DBSession.completed_at))
        )
        sessions_with_gems = result.all()
    
    # Extract sessions for highest reward query
    sessions = [s for s, _ in sessions_with_gems]
    
    # Load gem rewards for each session from JSON files
    session_list = []
    
    # Optimization: Fetch all highest rewards in a single query to avoid N+1
    highest_rewards_map = {}
    if sessions:
        try:
            session_ids = [s.id for s in sessions]
            # Query max gems earned per session for the current batch
            stmt = select(SessionPlayer.session_id, func.max(SessionPlayer.gems_earned))\
                   .where(SessionPlayer.session_id.in_(session_ids))\
                   .group_by(SessionPlayer.session_id)
            
            rewards_result = await db.execute(stmt)
            # Map session_id -> max_gems
            highest_rewards_map = {row[0]: (row[1] or 0) for row in rewards_result.all()}
        except Exception as e:
            print(f"Error fetching highest rewards batch: {e}")
    
    for s, gems_earned_db in sessions_with_gems:
        # Get highest reward for this session from pre-fetched map
        highest_reward = highest_rewards_map.get(s.id, 0)

        session_data = {
            "id": str(s.id),
            "room_code": s.room_code,
            "completion_key": s.completion_key,
            "language": s.language,
            "total_players": s.total_players,
            "num_human_players": s.num_human_players,
            "discussion_duration": s.discussion_duration,
            "voting_duration": s.voting_duration,
            "completed_at": s.completed_at.isoformat(),
            "payment_status": s.payment_status.value,
            "payment_amount": float(s.payment_amount) if s.payment_amount else None,
            "calculated_earnings": float(getattr(s, 'calculated_earnings', None)) if getattr(s, 'calculated_earnings', None) else None,
            "highest_reward": highest_reward,
            "claimed_at": s.claimed_at.isoformat() if s.claimed_at else None,
            "gem_earned": gems_earned_db  # Use DB value!
        }
        
        # Fallback: Load from JSON only if DB value is missing (legacy sessions)
        if session_data["gem_earned"] is None:
            try:
                if s.stats_file_path and os.path.exists(s.stats_file_path):
                    with open(s.stats_file_path, 'r') as f:
                        stats_data = json.load(f)
                        gem_rewards = stats_data.get('gem_rewards', {})
                        
                        # Find which player was this user
                        player_result = await db.execute(
                            select(SessionPlayer).where(
                                SessionPlayer.session_id == s.id,
                                SessionPlayer.user_id == current_user.id
                            )
                        )
                        user_player = player_result.scalar_one_or_none()
                        if user_player and user_player.player_id in gem_rewards:
                            reward_data = gem_rewards[user_player.player_id]
                            if isinstance(reward_data, dict):
                                session_data["gem_earned"] = reward_data.get('net_change', reward_data.get('total_gems', 0))
                            else:
                                session_data["gem_earned"] = reward_data
            except Exception as gem_load_error:
                print(f"⚠️ Could not load gem_earned for session {s.id}: {gem_load_error}")
        
        session_list.append(session_data)
    
    return {
        "sessions": session_list
    }


@router.get("/api/sessions/{session_id}")
async def get_session_detail(
    session_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_session)
):
    """
    Get detailed session information including chat history.
    """
    # Convert session_id to UUID
    try:
        session_uuid = uuid_lib.UUID(session_id)
    except (ValueError, AttributeError):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid session ID format"
        )
    
    # Get session from database
    result = await db.execute(
        select(DBSession).where(DBSession.id == session_uuid)
    )
    session = result.scalar_one_or_none()
    
    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Session not found"
        )
    
    # Check authorization
    if current_user.role != UserRole.ADMIN:
        # Authorized if user is the session owner OR participated as a player
        is_owner = session.user_id == current_user.id
        is_participant = False
        if not is_owner:
            try:
                part_result = await db.execute(
                    select(SessionPlayer).where(
                        SessionPlayer.session_id == session_uuid,
                        SessionPlayer.user_id == current_user.id
                    )
                )
                is_participant = part_result.scalar_one_or_none() is not None
            except Exception as e:
                print(f"⚠️ Authorization check failed: {e}")
        
        if not (is_owner or is_participant):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not authorized to view this session"
            )
    
    # Load chat history from JSON file
    try:
        with open(session.stats_file_path, 'r') as f:
            stats_data = json.load(f)
    except Exception as e:
        print(f"Error loading stats file: {e}")
        stats_data = {}
    
    # Get player identification - which player was the current user?
    current_user_player_id = None
    try:
        print(f"🔍 Looking for player identification: session_id={session_uuid}, user_id={current_user.id}")
        player_result = await db.execute(
            select(SessionPlayer).where(
                SessionPlayer.session_id == session_uuid,
                SessionPlayer.user_id == current_user.id
            )
        )
        user_player = player_result.scalar_one_or_none()
        if user_player:
            current_user_player_id = user_player.player_id
            print(f"✅ Found player identification: {current_user_player_id} for user {current_user.user_id}")
        else:
            print(f"⚠️ No player identification found for user {current_user.user_id} in session {session_uuid}")
    except Exception as e:
        print(f"❌ Error getting player identification: {e}")
        import traceback
        traceback.print_exc()
    
    # Get player-user mappings (for admins)
    player_mappings = []
    if current_user.role == UserRole.ADMIN:
        try:
            players_result = await db.execute(
                select(SessionPlayer).where(SessionPlayer.session_id == session_uuid)
            )
            session_players = players_result.scalars().all()
            
            for sp in session_players:
                mapping = {
                    "player_id": sp.player_id,
                    "role": sp.role,
                    "user_id": None,
                    "user_name": None
                }
                
                if sp.user_id:
                    user_result = await db.execute(
                        select(User).where(User.id == sp.user_id)
                    )
                    player_user = user_result.scalar_one_or_none()
                    if player_user:
                        mapping["user_id"] = str(player_user.id)
                        mapping["user_name"] = player_user.user_id
                
                player_mappings.append(mapping)
        except Exception as e:
            print(f"Error getting player mappings: {e}")
    
    # Get gem earned for this specific user (full breakdown)
    gem_earned = None
    gem_breakdown = None
    if current_user_player_id and stats_data:
        gem_rewards = stats_data.get('gem_rewards', {})
        if current_user_player_id in gem_rewards:
            reward_data = gem_rewards[current_user_player_id]
            # Handle both old format (just number) and new format (breakdown)
            if isinstance(reward_data, dict):
                gem_breakdown = reward_data
                gem_earned = reward_data.get('net_change', reward_data.get('total_gems', 0))  # Use net_change for display
            else:
                gem_earned = reward_data  # Old format (just a number)
            print(f"💎 User {current_user.user_id} net change: {gem_earned} gems as {current_user_player_id}")
    
    return {
        "id": str(session.id),
        "room_code": session.room_code,
        "completion_key": session.completion_key,
        "language": session.language,
        "total_players": session.total_players,
        "num_human_players": session.num_human_players,
        "discussion_duration": session.discussion_duration,
        "voting_duration": session.voting_duration,
        "completed_at": session.completed_at.isoformat(),
        "payment_status": session.payment_status.value,
        "payment_amount": float(session.payment_amount) if session.payment_amount else None,
        "claimed_at": session.claimed_at.isoformat() if session.claimed_at else None,
        "stats": stats_data,
        "current_user_player_id": current_user_player_id,
        "player_mappings": player_mappings,
        # MTurk information
        "mturk_worker_id": session.mturk_worker_id,
        "mturk_assignment_id": session.mturk_assignment_id,
        "mturk_hit_id": session.mturk_hit_id,
        "mturk_payment_sent": bool(session.mturk_payment_sent),
        "mturk_bonus_sent": bool(session.mturk_bonus_sent),
        # Gem economy information
        "calculated_earnings": float(session.calculated_earnings) if session.calculated_earnings else None,
        "gem_earned": gem_earned,  # Actual gems won/lost (can be negative)
        "gem_breakdown": gem_breakdown  # Full breakdown: base_gems, stake_gems, total_gems
    }


@router.get("/api/leaderboard")
async def get_leaderboard(
    db: AsyncSession = Depends(get_async_session),
    limit: int = 10
):
    """
    Get the top users by total gems earned, excluding admins.
    """
    # Query users table, filtering out admins
    result = await db.execute(
        select(User)
        .where(User.role == UserRole.USER)  # Exclude admins
        .order_by(desc(User.total_gems_earned))
        .limit(limit)
    )
    users = result.scalars().all()
    
    # Format leaderboard data
    leaderboard = []
    for rank, user in enumerate(users, start=1):
        # Calculate win rate
        win_rate = 0.0
        if user.total_games > 0:
            win_rate = (user.total_wins / user.total_games) * 100
        
        leaderboard.append({
            "rank": rank,
            "user_id": user.user_id,
            "total_gems_earned": user.total_gems_earned,
            "total_games": user.total_games,
            "total_wins": user.total_wins,
            "win_rate": round(win_rate, 1),  # Round to 1 decimal place
            "level": user.level
        })
    
    return {
        "leaderboard": leaderboard,
        "total_users": len(leaderboard)
    }


@router.get("/api/users/stats")
async def get_user_stats(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_session)
):
    """
    Get detailed user statistics and gamification data.
    """
    # Get user's sessions for win calculation
    result = await db.execute(
        select(DBSession).where(DBSession.user_id == current_user.id)
    )
    # sessions = result.scalars().all() # Not used?
    
    # Calculate win rate
    win_rate = (current_user.total_wins / current_user.total_games * 100) if current_user.total_games > 0 else 0
    
    # Calculate level and progress
    current_level = current_user.level
    points_for_level_up = points_for_next_level(current_level)
    current_level_start = int(100 * (current_level ** 1.5)) if current_level > 1 else 0
    progress_in_level = current_user.total_points - current_level_start
    progress_needed = points_for_level_up - current_level_start
    level_progress_percentage = (progress_in_level / progress_needed * 100) if progress_needed > 0 else 0
    
    # Get next close achievements
    unlocked_ids = []
    for achievement in ACHIEVEMENTS:
        if achievement.requirement_type == "games_played" and current_user.total_games >= achievement.requirement_value:
            unlocked_ids.append(achievement.id)
        elif achievement.requirement_type == "wins" and current_user.total_wins >= achievement.requirement_value:
            unlocked_ids.append(achievement.id)
        elif achievement.requirement_type == "streak" and current_user.current_streak >= achievement.requirement_value:
            unlocked_ids.append(achievement.id)
    
    next_achievements = get_next_close_achievements(
        current_user.total_games,
        current_user.total_wins,
        current_user.current_streak,
        unlocked_ids,
        limit=3
    )
    
    motivational_msg = get_motivational_message(
        current_user.total_games,
        current_user.total_wins,
        current_user.current_streak,
        [ach for ach, _ in next_achievements]
    )
    
    return {
        "user_id": current_user.user_id,
        "level": current_level,
        "total_points": current_user.total_points,
        "points_for_next_level": points_for_level_up,
        "level_progress": {
            "current": progress_in_level,
            "needed": progress_needed,
            "percentage": round(level_progress_percentage, 1)
        },
        "games": {
            "total": current_user.total_games,
            "wins": current_user.total_wins,
            "losses": current_user.total_games - current_user.total_wins,
            "win_rate": round(win_rate, 1)
        },
        "streak": {
            "current": current_user.current_streak,
            "longest": current_user.longest_streak
        },
        "achievements": {
            "unlocked_count": len(unlocked_ids),
            "total_count": len(ACHIEVEMENTS),
            "unlocked_ids": unlocked_ids
        },
        "next_achievements": [
            {
                "id": ach.id,
                "name": ach.name,
                "description": ach.description,
                "icon": ach.icon,
                "points": ach.points,
                "progress_needed": progress
            }
            for ach, progress in next_achievements
        ],
        "motivational_message": motivational_msg,
        "last_played_at": current_user.last_played_at.isoformat() if current_user.last_played_at else None
    }


@router.get("/api/users/earnings")
async def get_user_earnings(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_session)
):
    """
    Get detailed earnings statistics for current user.
    USES GEM ECONOMY SYSTEM - synced with wallet balance.
    """
    print(f"\n{'='*70}")
    print(f"📊 EARNINGS REQUEST for user: {current_user.user_id}")
    print(f"{'='*70}")
    
    # GEM ECONOMY: Use user's gem statistics (SYNCED WITH WALLET)
    total_gems_earned = current_user.total_gems_earned
    current_gem_balance = current_user.gem_balance
    total_gems_cashed_out = current_user.total_gems_cashed_out
    total_games = current_user.total_games
    
    # FALLBACK: If total_games is 0 but user has sessions, sync it from session count
    if total_games == 0:
        result = await db.execute(
            select(func.count(DBSession.id))
            .where(DBSession.user_id == current_user.id)
        )
        session_count = result.scalar() or 0
        if session_count > 0:
            print(f"⚠️ SYNC: User {current_user.user_id} has {session_count} sessions but total_games=0. Syncing...")
            current_user.total_games = session_count
            await db.commit()
            await db.refresh(current_user)
            total_games = session_count
            print(f"✅ SYNCED: total_games updated to {total_games}")
    
    # Convert to USD for display
    current_balance_usd = gems_to_usd(current_gem_balance)
    total_cashed_out_usd = gems_to_usd(total_gems_cashed_out)  # This is the real "lifetime earnings"
    
    print(f"User Stats (GEM ECONOMY - synced with wallet):")
    print(f"   Total games: {total_games}")
    print(f"   Total gems earned: {total_gems_earned} gems")
    print(f"   Current balance: {current_gem_balance} gems = ${current_balance_usd}")
    print(f"   Lifetime earnings (cashed out): {total_gems_cashed_out} gems = ${total_cashed_out_usd}")
    
    # Calculate average per game (IN GEMS, not USD)
    avg_gems_per_game = int((total_gems_earned / total_games) if total_games > 0 else 0)
    
    # Get recent sessions via SessionPlayer table (PROPER USER-SESSION MAPPING)
    result = await db.execute(
        select(DBSession, SessionPlayer.gems_earned)
        .join(SessionPlayer, SessionPlayer.session_id == DBSession.id)
        .where(SessionPlayer.user_id == current_user.id)
        .where(SessionPlayer.role == 'human')  # Only human players, not AI
        .order_by(desc(DBSession.completed_at))
        .limit(10)
    )
    sessions_data = result.all()
    
    print(f"📊 Found {len(sessions_data)} recent sessions for user {current_user.user_id}")
    
    # Calculate last game amount (IN GEMS)
    last_game_gems = 0  # Start with 0, will be updated if we find a recent game
    highest_earning_gems = 0
    recent_sessions = []
    
    for idx, (session, gems_earned) in enumerate(sessions_data):
        # PRIMARY SOURCE: SessionPlayer.gems_earned (database truth)
        actual_gems = gems_earned
        display_amount = gems_earned
        
        # Fallback: JSON file (only if database value is missing - legacy support)
        if actual_gems is None:
            try:
                if session.stats_file_path and os.path.exists(session.stats_file_path):
                    with open(session.stats_file_path, 'r') as f:
                        stats_data = json.load(f)
                        gem_rewards = stats_data.get('gem_rewards', {})
                        
                        # We need to find the player ID again since we don't have it easily here
                        player_result = await db.execute(
                            select(SessionPlayer).where(
                                SessionPlayer.session_id == session.id,
                                SessionPlayer.user_id == current_user.id
                            )
                        )
                        user_player = player_result.scalar_one_or_none()
                        
                        if user_player and user_player.player_id in gem_rewards:
                            reward_data = gem_rewards[user_player.player_id]
                            if isinstance(reward_data, dict):
                                display_amount = reward_data.get('net_change', reward_data.get('total_gems', 0))
                                actual_gems = display_amount
                            else:
                                actual_gems = reward_data
                                display_amount = actual_gems
                            print(f"   Session {idx} (fallback): {display_amount} gems from JSON")
            except Exception as e:
                print(f"   Session {idx}: Error in fallback loading: {e}")

        # Legacy Fallback: calculated_earnings
        if actual_gems is None and hasattr(session, 'calculated_earnings') and session.calculated_earnings:
             actual_gems = int(float(session.calculated_earnings) * GEMS_PER_DOLLAR)
             display_amount = actual_gems
        
        # Final Fallback: Average
        if actual_gems is None:
            actual_gems = avg_gems_per_game
            display_amount = actual_gems
            
        # Ensure we have a value
        if display_amount is None:
            display_amount = 0
            actual_gems = 0

        # Log the value found
        print(f"   Session {idx}: {display_amount} gems (Source: {'DB' if gems_earned is not None else 'Fallback'})")
        
        if idx == 0:  # Most recent game
            last_game_gems = display_amount
            print(f"✅ Last game gems set to: {last_game_gems}")
        
        # Track highest EARNING (not loss)
        if actual_gems > highest_earning_gems:
            highest_earning_gems = actual_gems
        
        # Store sessions with gem amounts for trend chart
        recent_sessions.append({
            "date": session.completed_at.isoformat(),
            "amount": display_amount,
            "status": "completed"
        })
    
    # FALLBACK: If no sessions found but user has gems, use average
    if len(sessions_data) == 0 and total_games > 0:
        last_game_gems = avg_gems_per_game
        print(f"⚠️ No sessions found via SessionPlayer, using average: {last_game_gems} gems")
    
    # Get dates for time-based stats
    now = datetime.utcnow()
    week_ago = now - timedelta(days=7)
    month_ago = now - timedelta(days=30)
    
    # Calculate actual cashouts this week/month (REAL EARNINGS, not estimated)
    result_week = await db.execute(
        select(func.sum(CashoutTransaction.amount_gems))
        .where(CashoutTransaction.user_id == current_user.id)
        .where(CashoutTransaction.status == CashoutStatus.COMPLETED)
        .where(CashoutTransaction.created_at >= week_ago)
    )
    gems_cashed_week = result_week.scalar() or 0
    earnings_this_week_usd = gems_to_usd(gems_cashed_week)
    
    result_month = await db.execute(
        select(func.sum(CashoutTransaction.amount_gems))
        .where(CashoutTransaction.user_id == current_user.id)
        .where(CashoutTransaction.status == CashoutStatus.COMPLETED)
        .where(CashoutTransaction.created_at >= month_ago)
    )
    gems_cashed_month = result_month.scalar() or 0
    earnings_this_month_usd = gems_to_usd(gems_cashed_month)
    
    # Get earnings tier (based on total cashed out, not total earned)
    tier_info = get_earnings_tier(total_cashed_out_usd)
    
    print(f"\nCalculated Stats:")
    print(f"   Avg per game: {avg_gems_per_game} gems")
    print(f"   Last game: {last_game_gems} gems")
    print(f"   Cashed out this week: {gems_cashed_week} gems = ${earnings_this_week_usd}")
    print(f"   Tier: {tier_info['name']} (based on total cashed out)")
    print(f"✅ SYNCED: total_lifetime_earnings (${total_cashed_out_usd}) = wallet.total_gems_cashed_out ({total_gems_cashed_out} gems)")
    print(f"{'='*70}\n")
    
    return {
        # PRIMARY STATS (✅ SYNCED WITH WALLET)
        "total_lifetime_earnings": float(total_cashed_out_usd),  # = wallet.total_gems_cashed_out / 1000
        "current_balance": float(current_balance_usd),  # = wallet.gem_balance / 1000
        "total_cashed_out": float(total_cashed_out_usd),  # = wallet.total_gems_cashed_out / 1000
        
        # PER-GAME STATS (IN GEMS, not USD)
        "average_per_game": avg_gems_per_game,  # Gems per game
        "last_game_gems": last_game_gems,  # Last game in gems
        "highest_single_game": highest_earning_gems,  # Highest in gems
        "total_games": total_games,
        
        # TIME-BASED STATS (Actual cashouts, not estimated)
        "earnings_this_week": float(earnings_this_week_usd),  # USD cashed out this week
        "earnings_this_month": float(earnings_this_month_usd),  # USD cashed out this month
        
        # RECENT HISTORY (now in gems)
        "recent_sessions": recent_sessions,
        
        # TIER INFO (based on total cashed out)
        "tier": {
            "name": tier_info["name"],
            "color": tier_info["color"],
            "current_amount": float(total_cashed_out_usd),
            "next_threshold": float(tier_info["next"]) if tier_info["next"] else None
        },
        
        # GEM ECONOMY DETAILS
        "gem_details": {
            "total_gems_earned": total_gems_earned,
            "current_gem_balance": current_gem_balance,
            "total_gems_cashed_out": total_gems_cashed_out,
            "conversion_rate": GEMS_PER_DOLLAR
        }
    }


@router.get("/api/users/active-session")
async def get_active_session(
    current_user: User = Depends(get_current_user_optional)
):
    """
    Check if the current user has an active game session.
    Returns session info if user is currently in a game (waiting or in_progress).
    """
    if not current_user:
        # Anonymous users - check by player_id in all rooms would require tracking
        # For now, anonymous users rely on client-side localStorage only
        return {
            "has_active_session": False,
            "room_code": None,
            "player_id": None,
            "room_status": None,
            "max_humans": None
        }
    
    user_id = str(current_user.id)
    print(f"🔍 Checking active session for user {current_user.user_id} (ID: {user_id[:8]}...)")
    
    # Search all rooms for this user's active session
    for room_code, room_data in rooms.items():
        room_status = room_data.get('room_status', '')
        
        # Only check rooms that are waiting or in_progress
        if room_status not in ['waiting', 'in_progress']:
            continue
        
        # Check player_user_map for this user
        player_user_map = room_data.get('player_user_map', {})
        
        for player_id, mapped_user_id in player_user_map.items():
            if mapped_user_id == user_id:
                # Found active session for this user
                # Use assigned_humans, never expose connection status
                assigned_humans = get_assigned_humans(room_data)
                max_humans = room_data.get('max_humans', 1)
                
                print(f"✅ Found active session: room={room_code}, player={player_id}, status={room_status}")
                
                return {
                    "has_active_session": True,
                    "room_code": room_code,
                    "player_id": player_id,
                    "room_status": room_status,
                    "max_humans": max_humans,
                    "current_humans_count": len(assigned_humans)
                }
    
    print(f"❌ No active session found for user {current_user.user_id}")
    return {
        "has_active_session": False,
        "room_code": None,
        "player_id": None,
        "room_status": None,
        "max_humans": None
    }


@router.post("/api/users/heartbeat")
async def user_heartbeat(
    current_user: User = Depends(get_current_user_optional)
):
    """
    Receive heartbeat from active users to track online status.
    Works for both authenticated and anonymous users.
    """
    if current_user:
        # Authenticated user - track by user_id
        user_id = str(current_user.id)
        update_user_activity(user_id)
        return {"status": "ok", "user_type": "authenticated", "user_id": current_user.user_id}
    else:
        # Anonymous user - for now we don't track anonymous users
        return {"status": "ok", "user_type": "anonymous"}


