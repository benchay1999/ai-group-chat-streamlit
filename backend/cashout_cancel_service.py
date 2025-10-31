"""
Cashout Cancellation and HIT Cleanup Service
===========================================

Handles cancellation of pending cashouts and garbage collection of HITs.
"""

from datetime import datetime, timedelta
from decimal import Decimal
from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession

from .database import CashoutTransaction, CashoutStatus, User
from .mturk_api import MTurkClient, get_mturk_client


async def cancel_cashout_transaction(
    transaction_id: str,
    user: User,
    db: AsyncSession,
    reason: str = "User requested cancellation"
) -> dict:
    """
    Cancel a pending cashout transaction.
    
    This will:
    1. Verify transaction belongs to user
    2. Check if transaction can be cancelled
    3. Delete/expire the MTurk HIT
    4. Refund gems (ONCE, with duplication protection)
    5. Update transaction status
    
    Args:
        transaction_id: Transaction UUID
        user: User requesting cancellation
        db: Database session
        reason: Reason for cancellation
        
    Returns:
        Dict with cancellation result
        
    Raises:
        ValueError: If transaction cannot be cancelled
    """
    
    print(f"\n{'='*70}")
    print(f"🚫 CANCELLING CASHOUT TRANSACTION")
    print(f"{'='*70}")
    print(f"Transaction ID: {transaction_id}")
    print(f"User: {user.user_id}")
    print(f"Reason: {reason}")
    
    # Get transaction with lock to prevent race conditions
    result = await db.execute(
        select(CashoutTransaction)
        .where(
            and_(
                CashoutTransaction.id == transaction_id,
                CashoutTransaction.user_id == user.id
            )
        )
        .with_for_update()  # Lock the row
    )
    
    transaction = result.scalar_one_or_none()
    
    if not transaction:
        raise ValueError("Transaction not found or does not belong to you")
    
    print(f"\n📊 Transaction Status: {transaction.status}")
    print(f"   Amount: ${transaction.amount_usd} ({transaction.amount_gems} gems)")
    print(f"   Created: {transaction.created_at}")
    print(f"   HIT ID: {transaction.mturk_hit_id or 'N/A'}")
    
    # Check if transaction can be cancelled
    cancellable_statuses = [
        CashoutStatus.PENDING,
        CashoutStatus.HIT_CREATED,
        CashoutStatus.PROCESSING
    ]
    
    if transaction.status not in cancellable_statuses:
        if transaction.status == CashoutStatus.COMPLETED:
            raise ValueError("Cannot cancel completed transaction")
        elif transaction.status == CashoutStatus.CANCELLED:
            raise ValueError("Transaction is already cancelled")
        elif transaction.status == CashoutStatus.FAILED:
            # Failed transactions might have already been refunded
            print(f"⚠️  Transaction already failed. Checking if refund needed...")
            # Check if gems were already refunded
            # If status is FAILED, gems should already be refunded
            return {
                "success": True,
                "message": "Transaction was already failed",
                "refunded": False,
                "gems_returned": 0
            }
        else:
            raise ValueError(f"Cannot cancel transaction with status: {transaction.status}")
    
    # Step 1: Delete/expire the MTurk HIT (if exists)
    hit_deleted = False
    if transaction.mturk_hit_id:
        print(f"\n1️⃣  Cleaning up MTurk HIT...")
        try:
            mturk_client = get_mturk_client()
            
            # Try to delete the HIT first
            try:
                mturk_client.client.delete_hit(HITId=transaction.mturk_hit_id)
                print(f"   ✅ HIT deleted: {transaction.mturk_hit_id}")
                hit_deleted = True
            except Exception as delete_error:
                print(f"   ⚠️  Could not delete HIT (might have assignments): {delete_error}")
                
                # If can't delete, try to expire it
                try:
                    mturk_client.client.update_expiration_for_hit(
                        HITId=transaction.mturk_hit_id,
                        ExpireAt=datetime.utcnow()
                    )
                    print(f"   ✅ HIT expired: {transaction.mturk_hit_id}")
                    hit_deleted = True
                except Exception as expire_error:
                    print(f"   ❌ Could not expire HIT: {expire_error}")
                    print(f"   ⚠️  HIT may still be active in MTurk")
                    # Continue anyway - we'll mark transaction as cancelled
        
        except Exception as e:
            print(f"   ❌ Error cleaning up HIT: {e}")
            # Continue anyway - transaction will be cancelled
    else:
        print(f"\n1️⃣  No HIT to clean up (HIT ID not set)")
    
    # Step 2: Refund gems (with duplication protection)
    print(f"\n2️⃣  Processing gem refund...")
    
    # Get current user balance for verification
    original_balance = user.gem_balance
    gems_to_refund = transaction.amount_gems
    
    print(f"   Current balance: {original_balance} gems")
    print(f"   Gems to refund: {gems_to_refund} gems")
    
    # CRITICAL: Only refund if transaction status indicates gems were deducted
    # When cashout is created, gems are deducted immediately
    # So for PENDING, HIT_CREATED, PROCESSING - gems need to be refunded
    refund_applied = False
    
    if transaction.status in [CashoutStatus.PENDING, CashoutStatus.HIT_CREATED, CashoutStatus.PROCESSING]:
        # Refund the gems
        user.gem_balance += gems_to_refund
        
        # Also update total cashed out counter (reverse the cashout)
        if user.total_gems_cashed_out >= gems_to_refund:
            user.total_gems_cashed_out -= gems_to_refund
        else:
            # This shouldn't happen, but handle gracefully
            print(f"   ⚠️  Warning: total_gems_cashed_out ({user.total_gems_cashed_out}) < gems_to_refund ({gems_to_refund})")
            user.total_gems_cashed_out = 0
        
        refund_applied = True
        new_balance = user.gem_balance
        
        print(f"   ✅ Gems refunded: {gems_to_refund}")
        print(f"   New balance: {new_balance} gems (was: {original_balance})")
    else:
        print(f"   ⏭️  No refund needed (status: {transaction.status})")
    
    # Step 3: Update transaction status
    print(f"\n3️⃣  Updating transaction status...")
    
    transaction.status = CashoutStatus.CANCELLED
    transaction.error_message = f"Cancelled by user: {reason}"
    transaction.completed_at = datetime.utcnow()
    
    print(f"   ✅ Status updated to: CANCELLED")
    
    # Commit all changes atomically
    await db.commit()
    
    print(f"\n{'='*70}")
    print(f"✅ CASHOUT CANCELLED SUCCESSFULLY")
    print(f"{'='*70}")
    print(f"   HIT cleaned up: {hit_deleted}")
    print(f"   Gems refunded: {gems_to_refund if refund_applied else 0}")
    print(f"   New balance: {user.gem_balance} gems")
    print(f"{'='*70}\n")
    
    return {
        "success": True,
        "message": "Cashout cancelled successfully",
        "hit_deleted": hit_deleted,
        "refunded": refund_applied,
        "gems_returned": gems_to_refund if refund_applied else 0,
        "new_balance": user.gem_balance,
        "transaction_id": str(transaction.id)
    }


async def garbage_collect_old_hits(
    db: AsyncSession,
    age_hours: int = 48
) -> dict:
    """
    Garbage collect old, abandoned HITs.
    
    Finds transactions with HITs that are:
    - Status: PENDING, HIT_CREATED, or PROCESSING
    - Older than specified hours
    - No completion
    
    For each, it will:
    - Delete/expire the HIT
    - Cancel the transaction
    - Refund gems
    
    Args:
        db: Database session
        age_hours: How old (in hours) before considering abandoned
        
    Returns:
        Dict with cleanup statistics
    """
    
    print(f"\n{'='*70}")
    print(f"🗑️  GARBAGE COLLECTION: Old HITs")
    print(f"{'='*70}")
    print(f"Looking for transactions older than {age_hours} hours...")
    
    cutoff_time = datetime.utcnow() - timedelta(hours=age_hours)
    
    # Find abandoned transactions
    result = await db.execute(
        select(CashoutTransaction)
        .where(
            and_(
                CashoutTransaction.status.in_([
                    CashoutStatus.PENDING,
                    CashoutStatus.HIT_CREATED,
                    CashoutStatus.PROCESSING
                ]),
                CashoutTransaction.created_at < cutoff_time,
                CashoutTransaction.completed_at.is_(None)
            )
        )
    )
    
    abandoned_transactions = result.scalars().all()
    
    print(f"Found {len(abandoned_transactions)} abandoned transactions\n")
    
    if not abandoned_transactions:
        print("✅ No garbage to collect")
        return {
            "success": True,
            "transactions_cleaned": 0,
            "hits_deleted": 0,
            "gems_refunded": 0
        }
    
    stats = {
        "transactions_cleaned": 0,
        "hits_deleted": 0,
        "gems_refunded": 0,
        "errors": 0
    }
    
    mturk_client = None
    try:
        mturk_client = get_mturk_client()
    except Exception as e:
        print(f"⚠️  Could not initialize MTurk client: {e}")
        print(f"⚠️  Will cancel transactions but cannot clean HITs")
    
    for transaction in abandoned_transactions:
        print(f"\n{'─'*70}")
        print(f"Processing transaction {transaction.id}")
        print(f"   User: {transaction.user_id}")
        print(f"   Amount: ${transaction.amount_usd} ({transaction.amount_gems} gems)")
        print(f"   Created: {transaction.created_at}")
        print(f"   Age: {datetime.utcnow() - transaction.created_at}")
        
        try:
            # Delete/expire HIT if exists
            if transaction.mturk_hit_id and mturk_client:
                try:
                    mturk_client.client.delete_hit(HITId=transaction.mturk_hit_id)
                    print(f"   ✅ HIT deleted")
                    stats["hits_deleted"] += 1
                except Exception as delete_error:
                    try:
                        mturk_client.client.update_expiration_for_hit(
                            HITId=transaction.mturk_hit_id,
                            ExpireAt=datetime.utcnow()
                        )
                        print(f"   ✅ HIT expired")
                        stats["hits_deleted"] += 1
                    except Exception as expire_error:
                        print(f"   ⚠️  Could not clean HIT: {expire_error}")
            
            # Get user and refund gems
            user_result = await db.execute(
                select(User).where(User.id == transaction.user_id)
            )
            user = user_result.scalar_one_or_none()
            
            if user:
                user.gem_balance += transaction.amount_gems
                if user.total_gems_cashed_out >= transaction.amount_gems:
                    user.total_gems_cashed_out -= transaction.amount_gems
                
                print(f"   ✅ Refunded {transaction.amount_gems} gems to user")
                stats["gems_refunded"] += transaction.amount_gems
            else:
                print(f"   ⚠️  User not found, cannot refund gems")
            
            # Mark transaction as cancelled
            transaction.status = CashoutStatus.CANCELLED
            transaction.error_message = f"Auto-cancelled: Abandoned for {age_hours}+ hours"
            transaction.completed_at = datetime.utcnow()
            
            stats["transactions_cleaned"] += 1
            print(f"   ✅ Transaction cancelled")
            
        except Exception as e:
            print(f"   ❌ Error processing transaction: {e}")
            stats["errors"] += 1
    
    # Commit all changes
    await db.commit()
    
    print(f"\n{'='*70}")
    print(f"✅ GARBAGE COLLECTION COMPLETE")
    print(f"{'='*70}")
    print(f"   Transactions cleaned: {stats['transactions_cleaned']}")
    print(f"   HITs deleted/expired: {stats['hits_deleted']}")
    print(f"   Gems refunded: {stats['gems_refunded']}")
    print(f"   Errors: {stats['errors']}")
    print(f"{'='*70}\n")
    
    return {
        "success": True,
        **stats
    }

