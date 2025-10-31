#!/usr/bin/env python3
"""
Cancel old HITs for a user to clean up multiple pending cashouts.
"""

import asyncio
import sys
from datetime import datetime
from sqlalchemy import select, desc
from database import async_session_maker, User, CashoutTransaction, CashoutStatus
from mturk_api import get_mturk_client


async def cancel_old_hits(user_id: str, keep_newest: int = 1):
    """
    Cancel old cashout transactions, keeping only the newest N.
    
    Args:
        user_id: User ID
        keep_newest: How many newest transactions to keep (default: 1)
    """
    print("="*70)
    print(f"🧹 CANCELLING OLD CASHOUTS")
    print("="*70)
    
    async with async_session_maker() as db:
        # Find user
        result = await db.execute(
            select(User).where(User.user_id == user_id)
        )
        user = result.scalar_one_or_none()
        
        if not user:
            print(f"\n❌ User not found: {user_id}")
            return
        
        print(f"\n👤 User: {user.user_id}")
        print(f"   Worker ID: {user.mturk_worker_id or 'NOT SET'}")
        print(f"   Current Balance: {user.gem_balance} gems")
        
        # Get active transactions
        result = await db.execute(
            select(CashoutTransaction)
            .where(CashoutTransaction.user_id == user.id)
            .where(CashoutTransaction.status.in_([CashoutStatus.PENDING, CashoutStatus.HIT_CREATED]))
            .order_by(desc(CashoutTransaction.created_at))
        )
        transactions = result.scalars().all()
        
        if not transactions:
            print("\n✅ No active cashouts to cancel")
            return
        
        if len(transactions) <= keep_newest:
            print(f"\n✅ Only {len(transactions)} active cashout(s), nothing to cancel")
            return
        
        # Keep the newest N, cancel the rest
        to_keep = transactions[:keep_newest]
        to_cancel = transactions[keep_newest:]
        
        print(f"\n📊 Found {len(transactions)} active cashout(s)")
        print(f"   Keeping: {len(to_keep)} newest")
        print(f"   Cancelling: {len(to_cancel)} old\n")
        
        for tx in to_keep:
            age = datetime.utcnow() - tx.created_at
            print(f"✅ KEEPING: {tx.id}")
            print(f"   Created: {age.seconds//60}m ago")
            print(f"   HIT ID: {tx.mturk_hit_id}")
            print()
        
        cancelled_count = 0
        refunded_gems = 0
        
        for tx in to_cancel:
            age = datetime.utcnow() - tx.created_at
            print(f"🚫 CANCELLING: {tx.id}")
            print(f"   Created: {age.seconds//60}m ago")
            print(f"   HIT ID: {tx.mturk_hit_id}")
            print(f"   Amount: {tx.amount_gems} gems")
            
            try:
                # Delete/expire HIT
                if tx.mturk_hit_id:
                    mturk_client = get_mturk_client()
                    try:
                        mturk_client.client.delete_hit(HITId=tx.mturk_hit_id)
                        print(f"   ✅ HIT deleted")
                    except:
                        try:
                            mturk_client.client.update_expiration_for_hit(
                                HITId=tx.mturk_hit_id,
                                ExpireAt=datetime.utcnow()
                            )
                            print(f"   ✅ HIT expired")
                        except Exception as e:
                            print(f"   ⚠️  Could not clean HIT: {e}")
                
                # Refund gems
                user.gem_balance += tx.amount_gems
                if user.total_gems_cashed_out >= tx.amount_gems:
                    user.total_gems_cashed_out -= tx.amount_gems
                refunded_gems += tx.amount_gems
                
                # Mark as cancelled
                tx.status = CashoutStatus.CANCELLED
                tx.error_message = "Auto-cancel: Cleaning up old HITs"
                tx.completed_at = datetime.utcnow()
                
                cancelled_count += 1
                print(f"   ✅ Cancelled successfully")
                
            except Exception as e:
                print(f"   ❌ Error: {e}")
            
            print()
        
        # Commit all changes to database
        await db.commit()
        
        # Refresh user to show new balance
        await db.refresh(user)
        
        print("="*70)
        print("✅ CLEANUP COMPLETE")
        print("="*70)
        print(f"   Cancelled: {cancelled_count} transaction(s)")
        print(f"   Gems refunded: {refunded_gems}")
        print(f"   New gem balance: {user.gem_balance}")
        print(f"   Active cashouts remaining: {len(to_keep)}")
        print("="*70)


if __name__ == "__main__":
    if len(sys.argv) > 1:
        keep = int(sys.argv[2]) if len(sys.argv) > 2 else 1
        asyncio.run(cancel_old_hits(user_id=sys.argv[1], keep_newest=keep))
    else:
        print("Usage: python cancel_old_hits.py <user_id> [keep_newest]")
        print("Example: python cancel_old_hits.py benchay 1")

