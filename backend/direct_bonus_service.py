#!/usr/bin/env python3
"""
Direct MTurk Bonus Payment Service
===================================

Simplified cashout system that sends bonuses directly to workers
without requiring them to accept HITs.

Flow:
1. Worker adds their MTurk Worker ID to profile (one-time)
2. Worker requests cashout
3. System generates unique transaction ID
4. System sends bonus directly to worker via MTurk API
5. Worker receives payment notification from MTurk
6. No HIT acceptance required!

Benefits:
- No HIT exhaustion issues
- No URL generation complexity
- Seamless repeat cashouts
- Workers never see "No more HITs"
- Much simpler implementation
"""

import os
import hashlib
from decimal import Decimal
from datetime import datetime, timedelta
from typing import Optional, Dict
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from .database import User, CashoutTransaction, CashoutStatus
from .config import GEMS_PER_DOLLAR
from .mturk_api import get_mturk_client


async def validate_direct_cashout(
    user: User,
    amount_usd: Decimal,
    db: AsyncSession
) -> tuple[bool, Optional[str]]:
    """
    Validate if user can cash out via direct bonus.
    
    Args:
        user: User requesting cashout
        amount_usd: Amount in USD
        db: Database session
    
    Returns:
        (is_valid, error_message)
    """
    
    # Check if user has MTurk Worker ID
    if not user.mturk_worker_id:
        return False, "Please add your MTurk Worker ID to your profile first"
    
    # Validate Worker ID format (starts with A, followed by alphanumeric)
    if not user.mturk_worker_id.startswith('A') or len(user.mturk_worker_id) < 10:
        return False, "Invalid MTurk Worker ID format"
    
    # Check minimum amount
    from .config import MINIMUM_CASHOUT_AMOUNT
    if amount_usd < MINIMUM_CASHOUT_AMOUNT:
        return False, f"Minimum cashout is ${MINIMUM_CASHOUT_AMOUNT}"
    
    # Check if user has enough gems
    required_gems = int(amount_usd * GEMS_PER_DOLLAR)
    if user.gem_balance < required_gems:
        return False, f"Insufficient gems. You have {user.gem_balance}, need {required_gems}"
    
    # Check for pending cashouts (limit to prevent abuse)
    result = await db.execute(
        select(CashoutTransaction)
        .where(CashoutTransaction.user_id == user.id)
        .where(CashoutTransaction.status == CashoutStatus.PENDING)
    )
    pending = result.scalars().all()
    
    if len(pending) >= 5:
        return False, "You have too many pending cashouts. Please wait for them to complete."
    
    return True, None


async def create_direct_bonus_transaction(
    user: User,
    amount_usd: Decimal,
    db: AsyncSession
) -> CashoutTransaction:
    """
    Create a cashout transaction for direct bonus payment.
    
    Args:
        user: User requesting cashout
        amount_usd: Amount in USD
        db: Database session
    
    Returns:
        CashoutTransaction object
    """
    
    # Calculate gems
    amount_gems = int(amount_usd * GEMS_PER_DOLLAR)
    
    # Generate unique transaction ID for tracking
    transaction_id_str = f"{user.id}{datetime.utcnow().timestamp()}{amount_usd}"
    transaction_hash = hashlib.sha256(transaction_id_str.encode()).hexdigest()[:16]
    
    # Create transaction record
    transaction = CashoutTransaction(
        user_id=user.id,
        amount_gems=amount_gems,
        amount_usd=amount_usd,
        status=CashoutStatus.PENDING,
        redemption_code=transaction_hash,  # Used as transaction reference
        mturk_worker_id=user.mturk_worker_id,
        expires_at=datetime.utcnow() + timedelta(days=7)
    )
    
    # Deduct gems from user's balance immediately
    user.gem_balance -= amount_gems
    
    db.add(transaction)
    await db.commit()
    await db.refresh(transaction)
    
    print(f"💎 Created direct bonus transaction: {transaction.id}")
    print(f"   User: {user.user_id}")
    print(f"   Worker ID: {user.mturk_worker_id}")
    print(f"   Amount: ${amount_usd} ({amount_gems} gems)")
    
    return transaction


async def send_direct_bonus(
    transaction: CashoutTransaction,
    db: AsyncSession
) -> Dict:
    """
    Send bonus payment directly to worker via MTurk API.
    
    Args:
        transaction: CashoutTransaction to process
        db: Database session
    
    Returns:
        Result dictionary with success status
    """
    
    print(f"\n{'='*70}")
    print(f"💰 DIRECT BONUS PAYMENT")
    print(f"{'='*70}")
    print(f"Transaction ID: {transaction.id}")
    print(f"Worker ID: {transaction.mturk_worker_id}")
    print(f"Amount: ${transaction.amount_usd}")
    
    try:
        # Get MTurk client
        mturk_client = get_mturk_client()
        
        # For direct bonus, we need a "dummy assignment" or use a standing registration HIT
        # MTurk requires an assignment ID to send bonus to
        
        # APPROACH 1: Use a standing "registration HIT" (one-time per worker)
        # Workers complete registration HIT once, we store their assignment ID
        # Then we can send bonuses to that assignment indefinitely
        
        # APPROACH 2: Send qualification bonus (simpler but less common)
        # Use MTurk's SendBonus with qualification-based system
        
        # For now, let's implement APPROACH 1 (most reliable)
        
        # Check if user has a registration assignment ID
        if not transaction.mturk_assignment_id:
            return {
                "success": False,
                "error": "Worker must complete registration HIT first",
                "action_required": "complete_registration"
            }
        
        # Send bonus to the registration assignment
        reason = f"ChatGame Cashout #{transaction.redemption_code}: ${transaction.amount_usd}"
        
        mturk_client.send_bonus(
            worker_id=transaction.mturk_worker_id,
            assignment_id=transaction.mturk_assignment_id,
            bonus_amount=transaction.amount_usd,
            reason=reason
        )
        
        print(f"✅ Bonus sent successfully!")
        
        # Update transaction status
        transaction.status = CashoutStatus.COMPLETED
        transaction.completed_at = datetime.utcnow()
        
        # Update user's cashout stats
        user = await db.get(User, transaction.user_id)
        user.total_gems_cashed_out += transaction.amount_gems
        
        await db.commit()
        
        print(f"✅ Transaction completed")
        print(f"{'='*70}\n")
        
        return {
            "success": True,
            "transaction_id": str(transaction.id),
            "amount_usd": float(transaction.amount_usd),
            "worker_id": transaction.mturk_worker_id,
            "message": f"${transaction.amount_usd} sent to your MTurk account"
        }
        
    except Exception as e:
        print(f"❌ Error sending bonus: {e}")
        
        # Update transaction with error
        transaction.status = CashoutStatus.FAILED
        transaction.error_message = str(e)
        
        # Refund gems to user
        user = await db.get(User, transaction.user_id)
        user.gem_balance += transaction.amount_gems
        
        await db.commit()
        
        return {
            "success": False,
            "error": str(e),
            "transaction_id": str(transaction.id),
            "refunded": True
        }


async def get_or_create_registration_assignment(
    user: User,
    db: AsyncSession
) -> Optional[str]:
    """
    Get user's registration assignment ID or prompt them to register.
    
    This is needed because MTurk requires an assignment ID to send bonuses.
    Worker completes a one-time "registration HIT", and we use that
    assignment ID for all future bonus payments.
    
    Args:
        user: User object
        db: Database session
    
    Returns:
        Assignment ID if available, None if needs registration
    """
    
    # Check if user already has a registration assignment
    # We can store this in a separate table or in the user's first cashout transaction
    
    result = await db.execute(
        select(CashoutTransaction)
        .where(CashoutTransaction.user_id == user.id)
        .where(CashoutTransaction.mturk_assignment_id.isnot(None))
        .order_by(CashoutTransaction.created_at)
        .limit(1)
    )
    
    first_transaction = result.scalar_one_or_none()
    
    if first_transaction and first_transaction.mturk_assignment_id:
        return first_transaction.mturk_assignment_id
    
    return None


def generate_registration_hit_url(environment: str = 'sandbox') -> str:
    """
    Generate URL for the one-time registration HIT.
    
    This HIT is simple:
    - Worker enters their User ID from the app
    - System links Worker ID to Assignment ID
    - Assignment ID is used for all future bonuses
    
    Args:
        environment: 'sandbox' or 'production'
    
    Returns:
        Registration HIT URL
    """
    
    # This would be a pre-created standing registration HIT
    # Stored in environment variable: REGISTRATION_HIT_ID
    
    registration_hit_id = os.getenv('REGISTRATION_HIT_ID')
    
    if environment == 'sandbox':
        return f"https://workersandbox.mturk.com/projects/{registration_hit_id}/tasks"
    else:
        return f"https://www.mturk.com/projects/{registration_hit_id}/tasks"

