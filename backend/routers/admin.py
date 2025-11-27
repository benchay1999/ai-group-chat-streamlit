from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from decimal import Decimal
import uuid as uuid_lib

from backend.database import (
    get_async_session, User, UserRole, Session as DBSession, 
    PaymentStatus, AIAgentUsage
)
from backend.auth import require_admin
from backend.global_state import rooms
from backend.pricing import format_cost, format_tokens, calculate_cost
from backend.cashout_cancel_service import garbage_collect_old_hits
from backend.mturk_api import process_payment, get_mturk_client
from backend.config import MTURK_MAX_BONUS, MTURK_BASE_PAY

router = APIRouter()

@router.get("/api/admin/dashboard")
async def admin_dashboard(
    admin_user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_async_session)
):
    """
    Get admin dashboard statistics.
    """
    # Total sessions
    total_sessions = await db.execute(select(DBSession))
    total_count = len(total_sessions.scalars().all())
    
    # Pending payment sessions
    pending_sessions = await db.execute(
        select(DBSession).where(DBSession.payment_status == PaymentStatus.PENDING)
    )
    pending_count = len(pending_sessions.scalars().all())
    
    # Paid sessions
    paid_sessions = await db.execute(
        select(DBSession).where(DBSession.payment_status == PaymentStatus.PAID)
    )
    paid_count = len(paid_sessions.scalars().all())
    
    # Unclaimed sessions
    unclaimed_sessions = await db.execute(
        select(DBSession).where(DBSession.user_id == None)
    )
    unclaimed_count = len(unclaimed_sessions.scalars().all())
    
    return {
        "total_sessions": total_count,
        "pending_payments": pending_count,
        "paid_sessions": paid_count,
        "unclaimed_sessions": unclaimed_count
    }


@router.get("/api/admin/analytics")
async def admin_analytics(
    time_range: str = "all",  # "24h", "7d", "30d", "all"
    admin_user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_async_session)
):
    """
    Get analytics and token usage statistics for admin dashboard.
    """
    from datetime import datetime, timedelta
    
    # Calculate time filter
    now = datetime.utcnow()
    if time_range == "24h":
        time_filter = now - timedelta(hours=24)
    elif time_range == "7d":
        time_filter = now - timedelta(days=7)
    elif time_range == "30d":
        time_filter = now - timedelta(days=30)
    else:
        time_filter = None
    
    # Build base query with time filter
    base_query = select(DBSession)
    if time_filter:
        base_query = base_query.where(DBSession.completed_at >= time_filter)
    
    # Get all sessions for the time range
    result = await db.execute(base_query)
    sessions = result.scalars().all()
    
    # Calculate aggregate statistics
    total_sessions = len(sessions)
    total_input_tokens = sum(s.total_input_tokens for s in sessions)
    total_output_tokens = sum(s.total_output_tokens for s in sessions)
    total_cost = sum(s.total_cost for s in sessions)
    
    # Cost per session statistics
    session_costs = [float(s.total_cost) for s in sessions if s.total_cost > 0]
    avg_cost_per_session = sum(session_costs) / len(session_costs) if session_costs else 0
    median_cost_per_session = sorted(session_costs)[len(session_costs) // 2] if session_costs else 0
    min_cost = min(session_costs) if session_costs else 0
    max_cost = max(session_costs) if session_costs else 0
    
    # Token usage by model
    model_stats = {}
    for session in sessions:
        model = session.model_name or "unknown"
        if model not in model_stats:
            model_stats[model] = {
                "sessions": 0,
                "input_tokens": 0,
                "output_tokens": 0,
                "cost": Decimal(0)
            }
        model_stats[model]["sessions"] += 1
        model_stats[model]["input_tokens"] += session.total_input_tokens
        model_stats[model]["output_tokens"] += session.total_output_tokens
        model_stats[model]["cost"] += session.total_cost
    
    # Cost over time (hourly for 24h, daily for longer periods)
    if time_range == "24h":
        # Hourly breakdown
        time_series = {}
        for session in sessions:
            hour_key = session.completed_at.strftime("%Y-%m-%d %H:00")
            if hour_key not in time_series:
                time_series[hour_key] = {"cost": Decimal(0), "sessions": 0, "tokens": 0}
            time_series[hour_key]["cost"] += session.total_cost
            time_series[hour_key]["sessions"] += 1
            time_series[hour_key]["tokens"] += session.total_input_tokens + session.total_output_tokens
    else:
        # Daily breakdown
        time_series = {}
        for session in sessions:
            day_key = session.completed_at.strftime("%Y-%m-%d")
            if day_key not in time_series:
                time_series[day_key] = {"cost": Decimal(0), "sessions": 0, "tokens": 0}
            time_series[day_key]["cost"] += session.total_cost
            time_series[day_key]["sessions"] += 1
            time_series[day_key]["tokens"] += session.total_input_tokens + session.total_output_tokens
    
    # Convert time series to list format
    time_series_list = [
        {
            "timestamp": key,
            "cost": float(value["cost"]),
            "sessions": value["sessions"],
            "tokens": value["tokens"]
        }
        for key, value in sorted(time_series.items())
    ]
    
    # Recent high-cost sessions
    high_cost_sessions = sorted(sessions, key=lambda s: s.total_cost, reverse=True)[:10]
    high_cost_list = [
        {
            "session_id": str(s.id),
            "room_code": s.room_code,
            "cost": float(s.total_cost),
            "input_tokens": s.total_input_tokens,
            "output_tokens": s.total_output_tokens,
            "model": s.model_name,
            "completed_at": s.completed_at.isoformat()
        }
        for s in high_cost_sessions
    ]
    
    return {
        "time_range": time_range,
        "summary": {
            "total_sessions": total_sessions,
            "total_input_tokens": total_input_tokens,
            "total_output_tokens": total_output_tokens,
            "total_tokens": total_input_tokens + total_output_tokens,
            "total_cost": float(total_cost),
            "avg_cost_per_session": avg_cost_per_session,
            "median_cost_per_session": median_cost_per_session,
            "min_cost": min_cost,
            "max_cost": max_cost,
            # Formatted strings for display
            "total_cost_formatted": format_cost(total_cost),
            "total_tokens_formatted": format_tokens(total_input_tokens + total_output_tokens)
        },
        "by_model": {
            model: {
                "sessions": stats["sessions"],
                "input_tokens": stats["input_tokens"],
                "output_tokens": stats["output_tokens"],
                "total_tokens": stats["input_tokens"] + stats["output_tokens"],
                "cost": float(stats["cost"]),
                "cost_formatted": format_cost(stats["cost"])
            }
            for model, stats in model_stats.items()
        },
        "time_series": time_series_list,
        "high_cost_sessions": high_cost_list
    }


@router.get("/api/admin/room-stats")
async def get_admin_room_stats(
    admin_user: User = Depends(require_admin)
):
    """
    Get statistics about currently operating rooms for admins.
    """
    # Count rooms that are actually operating (in_progress or waiting with players)
    operating_rooms = []
    for room_code, room_data in rooms.items():
        room_status = room_data.get('room_status', '')
        
        # Only count rooms that are truly active
        # in_progress = game is running
        # waiting = game hasn't started but has players
        if room_status == 'in_progress':
            operating_rooms.append({
                'room_code': room_code,
                'max_humans': room_data.get('max_humans'),
                'total_players': room_data.get('total_players'),
                'status': room_status
            })
        elif room_status == 'waiting':
            # Only count waiting rooms that have at least 1 player
            assigned_humans = room_data.get('assigned_humans', [])
            if len(assigned_humans) > 0:
                operating_rooms.append({
                    'room_code': room_code,
                    'max_humans': room_data.get('max_humans'),
                    'total_players': room_data.get('total_players'),
                    'status': room_status
                })
    
    # Count solo-human rooms (max_humans == 1)
    solo_human_count = len([r for r in operating_rooms if r['max_humans'] == 1])
    total_operating = len(operating_rooms)
    
    print(f"📊 Admin room stats: {total_operating} operating ({solo_human_count} solo, {total_operating - solo_human_count} multi)")
    
    return {
        "total_operating": total_operating,
        "solo_human_count": solo_human_count,
        "multi_human_count": total_operating - solo_human_count,
        "rooms": operating_rooms  # For debugging
    }


@router.post("/api/admin/garbage-collect-hits")
async def admin_garbage_collect_hits(
    age_hours: int = 48,
    admin_user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_async_session)
):
    """
    Admin endpoint to garbage collect old, abandoned HITs.
    """
    print(f"\n🗑️  Admin {admin_user.user_id} triggered garbage collection")
    print(f"   Age threshold: {age_hours} hours")
    
    try:
        result = await garbage_collect_old_hits(db=db, age_hours=age_hours)
        return result
    except Exception as e:
        print(f"❌ Error during garbage collection: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Garbage collection failed: {str(e)}")


@router.post("/api/admin/mturk/sessions/{session_id}/approve-payment")
async def approve_mturk_payment(
    session_id: str,
    admin_user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_async_session)
):
    """
    Approve MTurk assignment and send bonus payment.
    """
    # Convert session_id to UUID
    try:
        session_uuid = uuid_lib.UUID(session_id)
    except (ValueError, AttributeError):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid session ID format"
        )
    
    # Get session
    result = await db.execute(
        select(DBSession).where(DBSession.id == session_uuid)
    )
    session = result.scalar_one_or_none()
    
    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Session not found"
        )
    
    # Check if this is an MTurk session
    if not session.mturk_assignment_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="This is not an MTurk session"
        )
    
    # Check if already paid
    if session.mturk_payment_sent:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Payment already sent for this session"
        )
    
    # Check if calculated earnings exist
    if not session.calculated_earnings:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No calculated earnings for this session"
        )
    
    try:
        client = get_mturk_client()
        base_pay = Decimal(str(MTURK_BASE_PAY))
        max_bonus = Decimal(str(MTURK_MAX_BONUS))
        calculated_earnings = Decimal(str(session.calculated_earnings))
        
        # Calculate bonus amount
        raw_bonus = calculated_earnings - base_pay
        bonus_amount = max(Decimal('0'), min(raw_bonus, max_bonus))
        
        # Process payment via MTurk API
        payment_result = process_payment(
            assignment_id=session.mturk_assignment_id,
            worker_id=session.mturk_worker_id,
            calculated_earnings=calculated_earnings,
            max_bonus=max_bonus
        )
        
        # Only update database if payment was successful
        if payment_result['approved']:
            # Update session with payment status
            session.mturk_payment_sent = 1
            session.mturk_bonus_sent = 1 if payment_result.get('bonus_sent', False) else 0
            session.payment_status = PaymentStatus.PAID
            session.payment_amount = session.calculated_earnings
            
            await db.commit()
            await db.refresh(session)
            
            return {
                "success": True,
                "message": "MTurk payment processed successfully",
                "base_pay": float(base_pay),
                "bonus_amount": float(bonus_amount),
                "total_paid": float(base_pay + bonus_amount),
                "payment_result": payment_result,
                "session": {
                    "id": str(session.id),
                    "room_code": session.room_code,
                    "worker_id": session.mturk_worker_id,
                    "assignment_id": session.mturk_assignment_id,
                    "payment_amount": float(session.payment_amount),
                    "payment_status": session.payment_status.value
                }
            }
        else:
            # Payment approval failed, rollback any changes
            await db.rollback()
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="MTurk assignment approval failed. Payment was not processed."
            )
        
    except HTTPException:
        # Re-raise HTTP exceptions
        raise
    except Exception as e:
        # Rollback on any error
        await db.rollback()
        
        # Provide more specific error messages
        error_str = str(e)
        if "InvalidParameterValue" in error_str:
            detail = "Invalid MTurk parameters. Please check worker_id and assignment_id."
        elif "RequestError" in error_str or "credentials" in error_str.lower():
            detail = "MTurk API authentication failed. Please check AWS credentials."
        elif "InsufficientFunds" in error_str:
            detail = "Insufficient funds in MTurk account. Please add funds to continue."
        elif "AssignmentAlreadyApproved" in error_str:
            detail = "This assignment has already been approved in MTurk."
        else:
            detail = f"MTurk API error: {error_str}"
        
        print(f"❌ MTurk payment error: {e}")
        import traceback
        traceback.print_exc()
        
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=detail
        )


