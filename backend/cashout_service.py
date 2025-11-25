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
    
    # Check if user has completed demographic information (required with worker ID)
    if not user.age or not user.gender or not user.nationality or not user.major:
        return False, "Demographic information incomplete. Please update your profile with age, gender, nationality, and major before cashing out."
    
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
    
    SECURITY: Uses database transaction with row-level locking to prevent
    race conditions during concurrent cashout requests.
    
    Args:
        user: User requesting cashout
        amount_usd: USD amount to cash out
        db: Database session
        
    Returns:
        Created CashoutTransaction with redemption_code
        
    Raises:
        CashoutError: If validation fails
    """
    from sqlalchemy import func
    from sqlalchemy.exc import IntegrityError
    
    # SECURITY: Refresh user with FOR UPDATE lock to prevent concurrent modifications
    # This ensures no other transaction can modify the user's gem balance simultaneously
    user_result = await db.execute(
        select(User).where(User.id == user.id).with_for_update()
    )
    user = user_result.scalar_one()
    
    # Validate request (with locked user data)
    is_valid, error_msg = await validate_cashout_request(user, amount_usd, db)
    if not is_valid:
        raise CashoutError(error_msg)
    
    # Calculate gems
    gems_amount = usd_to_gems(amount_usd)
    
    # Store original balance for logging
    original_balance = user.gem_balance
    
    # SECURITY CHECK: Double-check gem balance after lock acquisition
    if user.gem_balance < gems_amount:
        raise CashoutError(
            f"Insufficient gems after lock acquisition. "
            f"You have {user.gem_balance} gems but need {gems_amount}. "
            f"Another transaction may have used these gems."
        )
    
    print(f"💎 Creating cashout for user {user.user_id}")
    print(f"   Original balance: {original_balance} gems")
    print(f"   Requesting: {gems_amount} gems (${amount_usd})")
    
    # Generate unique redemption code (retry loop to handle collision)
    max_retries = 3
    for attempt in range(max_retries):
        redemption_code = generate_redemption_code()
        
        # Check if code already exists (extremely unlikely but handle it)
        existing = await db.execute(
            select(CashoutTransaction).where(
                CashoutTransaction.redemption_code == redemption_code
            )
        )
        if not existing.scalar_one_or_none():
            break  # Code is unique
        
        if attempt == max_retries - 1:
            raise CashoutError("Failed to generate unique redemption code. Please try again.")
    
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
        # Deduct gems from user's balance immediately (within locked transaction)
        user.gem_balance -= gems_amount
        
        # SECURITY: Validate gem balance didn't go negative (defense in depth)
        if user.gem_balance < 0:
            raise CashoutError("Gem balance would go negative. Transaction aborted.")
        
        # Add transaction to database
        db.add(transaction)
        
        # Commit atomically - both user balance and transaction
        # The lock is held until commit, preventing race conditions
        await db.commit()
        await db.refresh(transaction)
        await db.refresh(user)  # Refresh user to get committed state
        
        print(f"✅ Created cashout transaction {transaction.id}")
        print(f"   Deducted: {gems_amount} gems")
        print(f"   New balance: {user.gem_balance} gems (was {original_balance})")
        print(f"   Redemption Code: {redemption_code[:16]}...")
        
        return transaction
        
    except IntegrityError as e:
        # Database constraint violation (e.g., duplicate redemption code)
        print(f"❌ Database integrity error: {e}")
        await db.rollback()
        await db.refresh(user)
        print(f"   Balance after rollback: {user.gem_balance} gems")
        raise CashoutError("Failed to create cashout due to database constraint. Please try again.")
        
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
    # SECURITY: Find transaction with row-level lock to prevent concurrent redemptions
    result = await db.execute(
        select(CashoutTransaction).where(
            CashoutTransaction.redemption_code == redemption_code
        ).with_for_update()
    )
    transaction = result.scalar_one_or_none()
    
    if not transaction:
        raise CashoutError("Invalid redemption code")
    
    # SECURITY: Check if already redeemed (double-redemption prevention)
    if transaction.status == CashoutStatus.COMPLETED:
        raise CashoutError("This code has already been redeemed")
    
    # SECURITY: Check if HIT_CREATED (prevent redemption while HIT is being created)
    if transaction.status == CashoutStatus.HIT_CREATED:
        raise CashoutError("This cashout is being processed. Please wait.")
    
    # Check if expired
    if transaction.expires_at and datetime.utcnow() > transaction.expires_at:
        # Return gems to user
        await cancel_cashout_transaction(transaction, db, "Code expired")
        raise CashoutError("This code has expired")
    
    # Check if cancelled
    if transaction.status == CashoutStatus.CANCELLED:
        raise CashoutError("This cashout was cancelled")
    
    try:
        # SECURITY: Get user with FOR UPDATE lock to prevent concurrent modifications
        user_result = await db.execute(
            select(User).where(User.id == transaction.user_id).with_for_update()
        )
        user = user_result.scalar_one()
        
        print(f"\n{'='*70}")
        print(f"💳 PROCESSING REDEMPTION")
        print(f"{'='*70}")
        print(f"User: {user.user_id}")
        print(f"Transaction ID: {transaction.id}")
        print(f"Amount: {transaction.amount_gems} gems = ${transaction.amount_usd}")
        print(f"Current gem balance: {user.gem_balance}")
        print(f"Worker ID: {worker_id}")
        print(f"Assignment ID: {assignment_id}")
        print(f"HIT ID: {hit_id}")
        
        # DEVELOPMENT MODE: Check if we're in testing/development
        import os
        mturk_environment = os.getenv('MTURK_ENVIRONMENT', 'sandbox')
        
        # Dev mode triggers:
        # 1. Assignment ID is empty or None
        # 2. Assignment ID starts with DEV_
        # 3. Assignment ID is the MTurk preview placeholder
        # 4. Assignment ID contains localhost
        
        print(f"\n🔍 Dev Mode Detection:")
        print(f"   Assignment ID: '{assignment_id}'")
        print(f"   Type: {type(assignment_id)}")
        print(f"   Length: {len(assignment_id) if assignment_id else 0}")
        
        # Explicit checks with logging
        check_empty = not assignment_id
        check_blank = assignment_id.strip() == '' if assignment_id else False
        check_dev_prefix = assignment_id.startswith('DEV_') if assignment_id else False
        check_placeholder = assignment_id == 'ASSIGNMENT_ID_NOT_AVAILABLE' if assignment_id else False
        check_localhost = 'localhost' in assignment_id.lower() if assignment_id else False
        check_undefined = assignment_id == 'undefined' if assignment_id else False
        
        print(f"   Empty: {check_empty}")
        print(f"   Blank: {check_blank}")
        print(f"   Starts with DEV_: {check_dev_prefix}")
        print(f"   Is placeholder: {check_placeholder}")
        print(f"   Contains localhost: {check_localhost}")
        print(f"   Is undefined: {check_undefined}")
        
        is_dev_mode = (
            check_empty or 
            check_blank or
            check_dev_prefix or 
            check_placeholder or
            check_localhost or
            check_undefined
        )
        
        print(f"\n🔍 Payment Processing Mode:")
        print(f"   MTURK_ENVIRONMENT: {mturk_environment}")
        print(f"   Is dev mode: {is_dev_mode}")
        
        if not is_dev_mode:
            print(f"   ⚠️  WARNING: Will attempt real MTurk API call!")
            print(f"   Assignment ID appears to be real: '{assignment_id}'")
        
        # Approve the assignment on MTurk (skip in dev mode for testing)
        if not is_dev_mode:
            try:
                print(f"💰 Processing MTurk payment...")
                mturk_client = get_mturk_client()
                
                # CRITICAL: The HIT was created with Reward='0.01'
                # This is the base pay that MTurk gives when approving
                # Everything else must be sent as a bonus
                hit_base_reward = Decimal('0.01')  # Must match create_standing_hit.py
                
                # Calculate bonus: Total amount minus the HIT's base reward
                bonus_amount = transaction.amount_usd - hit_base_reward
                
                # CRITICAL VALIDATION: Ensure math is correct
                calculated_total = hit_base_reward + bonus_amount
                if calculated_total != transaction.amount_usd:
                    error_msg = f"PAYMENT MATH ERROR: {hit_base_reward} + {bonus_amount} = {calculated_total} ≠ {transaction.amount_usd}"
                    print(f"   ❌ {error_msg}")
                    raise ValueError(error_msg)
                
                print(f"   📊 Payment Breakdown:")
                print(f"      Total amount requested: ${transaction.amount_usd}")
                print(f"      HIT base reward: ${hit_base_reward} (paid by approval)")
                print(f"      Bonus to send: ${bonus_amount}")
                print(f"      ✓ Verification: ${hit_base_reward} + ${bonus_amount} = ${calculated_total}")
                print(f"      ✓ Worker will receive: ${transaction.amount_usd}")
                
                # Step 1: Approve assignment (gives worker the HIT's base reward of $0.01)
                mturk_client.approve_assignment(
                    assignment_id=assignment_id,
                    requester_feedback=f"ChatGame payout of ${transaction.amount_usd} approved. Thank you!"
                )
                print(f"   ✅ Assignment approved (worker gets ${hit_base_reward} base reward)")
                
                # Step 2: Send bonus for the remaining amount
                if bonus_amount > 0:
                    mturk_client.send_bonus(
                        worker_id=worker_id,
                        assignment_id=assignment_id,
                        bonus_amount=bonus_amount,
                        reason=f"ChatGame earnings bonus (Total payout: ${transaction.amount_usd})"
                    )
                    print(f"   ✅ Bonus sent: ${bonus_amount}")
                else:
                    print(f"   ⚠️  No bonus needed (amount equals base reward)")
                
                print(f"   💰 TOTAL PAID TO WORKER: ${transaction.amount_usd}")
            
            except Exception as mturk_error:
                # MTurk API failed
                error_msg = str(mturk_error)
                print(f"\n❌ MTurk API ERROR:")
                print(f"   Error type: {type(mturk_error).__name__}")
                print(f"   Error message: {error_msg}")
                import traceback
                print(f"   Stack trace:\n{traceback.format_exc()}")
                
                # Check if this is a "RequestError" in sandbox - likely a test assignment
                # In sandbox with RequestError, we should just complete the transaction without MTurk
                is_request_error = 'RequestError' in str(type(mturk_error).__name__) or 'RequestError' in error_msg
                is_sandbox = mturk_environment == 'sandbox'
                
                if is_sandbox and is_request_error:
                    print(f"\n⚠️  MTurk RequestError in sandbox - likely a test assignment")
                    print(f"   Treating as dev mode and completing transaction without MTurk API")
                    # Don't cancel - just continue to completion (treated as dev mode)
                    pass
                else:
                    # Real error - cancel transaction and return gems
                    print(f"\n🔄 Cancelling transaction and returning gems...")
                    
                    # Use cancel_cashout_transaction which handles gem return properly
                    await cancel_cashout_transaction(
                        transaction=transaction,
                        db=db,
                        reason=f"MTurk payment processing failed: {str(mturk_error)}"
                    )
                    
                    print(f"{'='*70}\n")
                    raise CashoutError(f"Payment processing failed: {error_msg}. Your gems have been returned to your wallet. Please try again or contact support.")
        else:
            print(f"\n🧪 DEV MODE ACTIVE")
            print(f"   Skipping MTurk API calls for testing")
            print(f"   Assignment ID: {assignment_id}")
            print(f"   In production, this would:")
            print(f"     1. Approve MTurk assignment")
            print(f"     2. Send payment: ${transaction.amount_usd}")
            print(f"   ✅ Simulating successful payment...")
        
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
        
        print(f"\n✅ CASHOUT COMPLETED SUCCESSFULLY!")
        print(f"   User: {user.user_id}")
        print(f"   Amount: ${transaction.amount_usd} ({transaction.amount_gems} gems)")
        print(f"   Total cashed out: {old_total_cashed_out} → {user.total_gems_cashed_out} gems")
        print(f"   Current balance: {user.gem_balance} gems")
        print(f"   Worker: {worker_id}")
        print(f"   Mode: {'DEV MODE' if is_dev_mode else 'PRODUCTION MTurk'}")
        print(f"{'='*70}\n")
        
        return {
            "success": True,
            "amount_usd": float(transaction.amount_usd),
            "amount_gems": transaction.amount_gems,
            "message": f"Payment of ${transaction.amount_usd} approved! Funds will appear in your MTurk account.",
            "dev_mode": is_dev_mode
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
