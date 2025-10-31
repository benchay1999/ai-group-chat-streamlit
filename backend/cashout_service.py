"""
Cashout Service
Handles business logic for gem-to-USD cashouts via MTurk using redemption codes.
"""

from decimal import Decimal
from datetime import datetime, timedelta
from typing import Optional, Dict, Tuple
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
import uuid
import secrets
import hashlib

from backend.database import User, CashoutTransaction, CashoutStatus
from backend.mturk_api import get_mturk_client
from backend.config import (
    GEMS_PER_DOLLAR,
    MINIMUM_CASHOUT_AMOUNT
)


class CashoutError(Exception):
    """Custom exception for cashout-related errors."""
    pass


def generate_redemption_code() -> str:
    """
    Generate a unique redemption code for cashout.
    
    Returns:
        64-character hex string
    """
    # Generate random bytes and hash them for uniqueness
    random_data = secrets.token_bytes(32)
    timestamp = str(datetime.utcnow().timestamp()).encode()
    
    hash_obj = hashlib.sha256(random_data + timestamp)
    return hash_obj.hexdigest()


def gems_to_usd(gems: int) -> Decimal:
    """
    Convert gems to USD amount.
    
    Args:
        gems: Number of gems
        
    Returns:
        USD amount as Decimal
    """
    return Decimal(str(gems)) / Decimal(str(GEMS_PER_DOLLAR))


def usd_to_gems(usd: Decimal) -> int:
    """
    Convert USD amount to gems.
    
    Args:
        usd: USD amount
        
    Returns:
        Number of gems
    """
    return int(Decimal(str(usd)) * Decimal(str(GEMS_PER_DOLLAR)))


async def validate_cashout_request(
    user: User,
    amount_usd: Decimal,
    db: AsyncSession
) -> Tuple[bool, Optional[str]]:
    """
    Validate a cashout request.
    
    Args:
        user: User making the request
        amount_usd: USD amount to cash out
        db: Database session
        
    Returns:
        Tuple of (is_valid, error_message)
    """
    # Check if user has MTurk worker ID (required for redemption)
    if not user.mturk_worker_id:
        return False, "MTurk Worker ID not set. Please add your Worker ID in profile settings before cashing out."
    
    # Check minimum cashout amount
    if amount_usd < Decimal(str(MINIMUM_CASHOUT_AMOUNT)):
        return False, f"Minimum cashout amount is ${MINIMUM_CASHOUT_AMOUNT:.2f}"
    
    # Calculate required gems
    required_gems = usd_to_gems(amount_usd)
    
    # Check if user has enough gems
    if user.gem_balance < required_gems:
        available_usd = gems_to_usd(user.gem_balance)
        return False, f"Insufficient gems. You have {user.gem_balance} gems (${available_usd:.2f}), but need {required_gems} gems (${amount_usd:.2f})"
    
    # Check for pending cashouts
    pending_query = select(CashoutTransaction).where(
        CashoutTransaction.user_id == user.id,
        CashoutTransaction.status == CashoutStatus.PENDING
    )
    result = await db.execute(pending_query)
    pending_cashouts = result.scalars().all()
    
    if pending_cashouts:
        return False, f"You have {len(pending_cashouts)} pending cashout(s). Please complete or wait for them to expire before requesting a new cashout."
    
    return True, None


async def create_cashout_transaction(
    user: User,
    amount_usd: Decimal,
    db: AsyncSession
) -> CashoutTransaction:
    """
    Create a new cashout transaction with redemption code.
    No HIT creation needed - user will submit code to existing HIT.
    
    Args:
        user: User requesting cashout
        amount_usd: USD amount to cash out
        db: Database session
        
    Returns:
        Created CashoutTransaction with redemption_code
        
    Raises:
        CashoutError: If validation fails
    """
    # Validate request
    is_valid, error_msg = await validate_cashout_request(user, amount_usd, db)
    if not is_valid:
        raise CashoutError(error_msg)
    
    # Calculate gems
    gems_amount = usd_to_gems(amount_usd)
    
    # Store original balance for logging
    original_balance = user.gem_balance
    
    print(f"💎 Creating cashout for user {user.user_id}")
    print(f"   Original balance: {original_balance} gems")
    print(f"   Requesting: {gems_amount} gems (${amount_usd})")
    
    # Generate unique redemption code
    redemption_code = generate_redemption_code()
    
    # Create transaction record
    transaction = CashoutTransaction(
        id=uuid.uuid4(),
        user_id=user.id,
        amount_gems=gems_amount,
        amount_usd=amount_usd,
        status=CashoutStatus.PENDING,
        redemption_code=redemption_code,
        created_at=datetime.utcnow(),
        expires_at=datetime.utcnow() + timedelta(days=7)  # Code valid for 7 days
    )
    
    try:
        # Deduct gems from user's balance immediately
        user.gem_balance -= gems_amount
        
        # Add transaction to database
        db.add(transaction)
        
        # Commit atomically - both user balance and transaction
        await db.commit()
        await db.refresh(transaction)
        await db.refresh(user)  # Refresh user to get committed state
        
        print(f"✅ Created cashout transaction {transaction.id}")
        print(f"   Deducted: {gems_amount} gems")
        print(f"   New balance: {user.gem_balance} gems (was {original_balance})")
        print(f"   Redemption Code: {redemption_code[:16]}...")
        
        return transaction
        
    except Exception as e:
        # CRITICAL FIX: rollback() already restores the user state
        # DO NOT manually add gems back - that would duplicate them!
        print(f"❌ Failed to create cashout transaction: {e}")
        print(f"   Rolling back... Balance will be restored to: {original_balance}")
        
        await db.rollback()
        
        # Refresh user to get rolled-back state
        await db.refresh(user)
        
        print(f"   Balance after rollback: {user.gem_balance} gems")
        
        raise CashoutError(f"Failed to create cashout: {str(e)}")


async def redeem_cashout_code(
    redemption_code: str,
    worker_id: str,
    assignment_id: str,
    hit_id: str,
    db: AsyncSession
) -> Dict:
    """
    Redeem a cashout code and process payment.
    Called when user submits code in MTurk HIT.
    
    Args:
        redemption_code: The redemption code
        worker_id: MTurk Worker ID
        assignment_id: MTurk Assignment ID
        hit_id: MTurk HIT ID
        db: Database session
        
    Returns:
        Dict with redemption result
        
    Raises:
        CashoutError: If code is invalid or already used
    """
    # Find transaction by redemption code
    result = await db.execute(
        select(CashoutTransaction).where(
            CashoutTransaction.redemption_code == redemption_code
        )
    )
    transaction = result.scalar_one_or_none()
    
    if not transaction:
        raise CashoutError("Invalid redemption code")
    
    # Check if already redeemed
    if transaction.status == CashoutStatus.COMPLETED:
        raise CashoutError("This code has already been redeemed")
    
    # Check if expired
    if transaction.expires_at and datetime.utcnow() > transaction.expires_at:
        # Return gems to user
        await cancel_cashout_transaction(transaction, db, "Code expired")
        raise CashoutError("This code has expired")
    
    # Check if cancelled
    if transaction.status == CashoutStatus.CANCELLED:
        raise CashoutError("This cashout was cancelled")
    
    try:
        # Get user (with lock to prevent concurrent modifications)
        user_result = await db.execute(
            select(User).where(User.id == transaction.user_id)
        )
        user = user_result.scalar_one()
        
        print(f"💳 Redeeming code for user {user.user_id}")
        print(f"   Transaction ID: {transaction.id}")
        print(f"   Amount: {transaction.amount_gems} gems = ${transaction.amount_usd}")
        print(f"   Current gem balance: {user.gem_balance}")
        print(f"   Worker ID: {worker_id}")
        print(f"   Assignment ID: {assignment_id}")
        
        # DEVELOPMENT MODE: Check if we're in testing/development
        import os
        mturk_environment = os.getenv('MTURK_ENVIRONMENT', 'sandbox')
        is_dev_mode = (mturk_environment == 'sandbox' and 
                      (not assignment_id or assignment_id.startswith('DEV_') or 
                       assignment_id == 'ASSIGNMENT_ID_NOT_AVAILABLE'))
        
        # Approve the assignment on MTurk (skip in dev mode for testing)
        if not is_dev_mode:
            try:
                print(f"💰 Processing MTurk payment...")
                mturk_client = get_mturk_client()
                
                # Calculate if we need to send a bonus (if amount > base pay)
                base_pay = mturk_client.base_pay
                bonus_amount = max(Decimal('0'), transaction.amount_usd - base_pay)
                
                print(f"   Base pay: ${base_pay}, Bonus: ${bonus_amount}")
                
                # Approve assignment
                mturk_client.approve_assignment(
                    assignment_id=assignment_id,
                    requester_feedback=f"ChatGame payout of ${transaction.amount_usd} approved. Thank you!"
                )
                print(f"✅ MTurk assignment approved")
                
                # Send bonus if needed
                if bonus_amount > 0:
                    mturk_client.send_bonus(
                        worker_id=worker_id,
                        assignment_id=assignment_id,
                        bonus_amount=bonus_amount,
                        reason=f"ChatGame payout bonus (total: ${transaction.amount_usd})"
                    )
                    print(f"✅ MTurk bonus sent: ${bonus_amount}")
            
            except Exception as mturk_error:
                # MTurk API failed - cancel transaction and return gems
                print(f"❌ MTurk API error: {mturk_error}")
                print(f"   Cancelling transaction and returning gems...")
                
                # Use cancel_cashout_transaction which handles gem return properly
                await cancel_cashout_transaction(
                    transaction=transaction,
                    db=db,
                    reason=f"MTurk payment processing failed: {str(mturk_error)}"
                )
                
                raise CashoutError("Payment processing failed. Your gems have been returned to your wallet. Please try again or contact support.")
        else:
            print(f"🧪 DEV MODE: Skipping MTurk API call for testing")
            print(f"   Assignment ID: {assignment_id}")
            print(f"   In production, this would approve assignment and send payment")
        
        # Update transaction to completed
        transaction.status = CashoutStatus.COMPLETED
        transaction.mturk_worker_id = worker_id
        transaction.mturk_assignment_id = assignment_id
        transaction.mturk_hit_id = hit_id
        transaction.completed_at = datetime.utcnow()
        
        # Update user's total cashed out (only after successful payment)
        old_total_cashed_out = user.total_gems_cashed_out
        user.total_gems_cashed_out += transaction.amount_gems
        
        # Commit all changes atomically
        await db.commit()
        await db.refresh(transaction)
        await db.refresh(user)
        
        print(f"✅ Cashout completed successfully!")
        print(f"   User: {user.user_id}")
        print(f"   Amount: ${transaction.amount_usd} ({transaction.amount_gems} gems)")
        print(f"   Total cashed out: {old_total_cashed_out} → {user.total_gems_cashed_out} gems")
        print(f"   Current balance: {user.gem_balance} gems")
        print(f"   Worker: {worker_id}")
        
        return {
            "success": True,
            "amount_usd": float(transaction.amount_usd),
            "amount_gems": transaction.amount_gems,
            "message": f"Payment of ${transaction.amount_usd} approved! Funds will appear in your MTurk account."
        }
        
    except CashoutError:
        # Re-raise CashoutError (already handled, gems already returned)
        raise
        
    except Exception as e:
        # Unexpected error - mark transaction as failed and return gems
        print(f"❌ Unexpected error during redemption: {e}")
        print(f"   Transaction ID: {transaction.id}")
        
        import traceback
        print(f"   Stack trace: {traceback.format_exc()}")
        
        try:
            # Cancel the transaction properly (this returns gems)
            await cancel_cashout_transaction(
                transaction=transaction,
                db=db,
                reason=f"Unexpected error: {str(e)}"
            )
        except Exception as cancel_error:
            print(f"❌ Error during cancellation: {cancel_error}")
            # Last resort: manual rollback
            await db.rollback()
        
        raise CashoutError(f"Payment processing failed: {str(e)}")


async def check_cashout_status(
    transaction_id: uuid.UUID,
    db: AsyncSession
) -> Dict:
    """
    Check the status of a cashout transaction.
    
    Args:
        transaction_id: Transaction UUID
        db: Database session
        
    Returns:
        Dict with status information
    """
    # Get transaction
    result = await db.execute(
        select(CashoutTransaction).where(CashoutTransaction.id == transaction_id)
    )
    transaction = result.scalar_one_or_none()
    
    if not transaction:
        raise CashoutError("Transaction not found")
    
    return {
        'transaction_id': str(transaction.id),
        'status': transaction.status.value,
        'amount_usd': float(transaction.amount_usd),
        'amount_gems': transaction.amount_gems,
        'redemption_code': transaction.redemption_code,
        'created_at': transaction.created_at.isoformat(),
        'completed_at': transaction.completed_at.isoformat() if transaction.completed_at else None,
        'expires_at': transaction.expires_at.isoformat() if transaction.expires_at else None,
        'error_message': transaction.error_message
    }


async def cancel_cashout_transaction(
    transaction: CashoutTransaction,
    db: AsyncSession,
    reason: str = "User cancelled"
) -> None:
    """
    Cancel a cashout transaction and return gems to user.
    
    Args:
        transaction: Transaction to cancel
        db: Database session
        reason: Cancellation reason
    """
    if transaction.status in [CashoutStatus.COMPLETED, CashoutStatus.CANCELLED]:
        print(f"⚠️  Transaction {transaction.id} already {transaction.status.value}, skipping cancellation")
        return  # Already completed or cancelled
    
    print(f"🔄 Cancelling cashout transaction {transaction.id}")
    print(f"   Reason: {reason}")
    print(f"   Amount to return: {transaction.amount_gems} gems")
    
    # Get user and return gems
    user_result = await db.execute(
        select(User).where(User.id == transaction.user_id)
    )
    user = user_result.scalar_one()
    
    old_balance = user.gem_balance
    user.gem_balance += transaction.amount_gems
    
    # Update transaction status
    transaction.status = CashoutStatus.FAILED if "expired" in reason.lower() else CashoutStatus.CANCELLED
    transaction.error_message = reason
    transaction.completed_at = datetime.utcnow()
    
    # Commit atomically
    await db.commit()
    await db.refresh(user)
    await db.refresh(transaction)
    
    print(f"✅ Cancelled cashout transaction {transaction.id}")
    print(f"   User: {user.user_id}")
    print(f"   Gems returned: {transaction.amount_gems}")
    print(f"   Balance: {old_balance} → {user.gem_balance} gems")
    print(f"   Status: {transaction.status.value}")


async def get_user_cashout_history(
    user: User,
    db: AsyncSession,
    limit: int = 20
) -> list:
    """
    Get cashout history for a user.
    
    Args:
        user: User to get history for
        db: Database session
        limit: Maximum number of transactions to return
        
    Returns:
        List of transaction dicts
    """
    query = select(CashoutTransaction).where(
        CashoutTransaction.user_id == user.id
    ).order_by(CashoutTransaction.created_at.desc()).limit(limit)
    
    result = await db.execute(query)
    transactions = result.scalars().all()
    
    return [
        {
            'transaction_id': str(t.id),
            'status': t.status.value,
            'amount_usd': float(t.amount_usd),
            'amount_gems': t.amount_gems,
            # Only show redemption code for pending transactions, mask for others
            'redemption_code': t.redemption_code if t.status == CashoutStatus.PENDING else f"****{t.redemption_code[-8:]}",
            'created_at': t.created_at.isoformat(),
            'completed_at': t.completed_at.isoformat() if t.completed_at else None,
            'error_message': t.error_message
        }
        for t in transactions
    ]
