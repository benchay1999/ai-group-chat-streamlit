#!/usr/bin/env python3
"""
Delete ALL HITs from MTurk and clean up database.
Use with caution - this is a nuclear option!
"""

import asyncio
from datetime import datetime
from sqlalchemy import select
from database import async_session_maker, CashoutTransaction, CashoutStatus, User
from mturk_api import get_mturk_client


async def delete_all_hits():
    """
    Delete all HITs from MTurk and cancel all pending cashout transactions.
    """
    print("="*70)
    print("🗑️  DELETE ALL HITs - NUCLEAR CLEANUP")
    print("="*70)
    print("\n⚠️  WARNING: This will:")
    print("   - Delete/expire ALL HITs in MTurk")
    print("   - Cancel ALL pending cashout transactions")
    print("   - Refund gems for all cancelled transactions")
    print()
    
    # Step 1: Get MTurk client
    try:
        mturk_client = get_mturk_client()
        print(f"✅ Connected to MTurk ({mturk_client.environment} environment)\n")
    except Exception as e:
        print(f"❌ Failed to connect to MTurk: {e}")
        return
    
    # Step 2: List all HITs from MTurk
    print("📋 Fetching all HITs from MTurk...")
    
    all_hits = []
    next_token = None
    
    try:
        while True:
            if next_token:
                response = mturk_client.client.list_hits(
                    NextToken=next_token,
                    MaxResults=100
                )
            else:
                response = mturk_client.client.list_hits(MaxResults=100)
            
            hits = response.get('HITs', [])
            all_hits.extend(hits)
            
            next_token = response.get('NextToken')
            if not next_token:
                break
        
        print(f"   Found {len(all_hits)} HIT(s) in MTurk\n")
        
    except Exception as e:
        print(f"❌ Error listing HITs: {e}")
        all_hits = []
    
    # Step 3: Delete/expire each HIT
    if all_hits:
        print("🗑️  Deleting HITs from MTurk...\n")
        
        deleted_count = 0
        expired_count = 0
        error_count = 0
        
        for hit in all_hits:
            hit_id = hit['HITId']
            hit_status = hit.get('HITStatus', 'Unknown')
            title = hit.get('Title', 'Untitled')
            
            print(f"   Processing HIT: {hit_id}")
            print(f"      Title: {title}")
            print(f"      Status: {hit_status}")
            
            # Try to delete first
            try:
                mturk_client.client.delete_hit(HITId=hit_id)
                print(f"      ✅ Deleted")
                deleted_count += 1
            except Exception as delete_error:
                # If can't delete, try to expire
                try:
                    mturk_client.client.update_expiration_for_hit(
                        HITId=hit_id,
                        ExpireAt=datetime.utcnow()
                    )
                    print(f"      ✅ Expired")
                    expired_count += 1
                except Exception as expire_error:
                    print(f"      ❌ Could not delete or expire: {expire_error}")
                    error_count += 1
            
            print()
        
        print("─"*70)
        print(f"MTurk Cleanup Summary:")
        print(f"   Deleted: {deleted_count}")
        print(f"   Expired: {expired_count}")
        print(f"   Errors: {error_count}")
        print("─"*70)
        print()
    
    # Step 4: Clean up database
    print("🗄️  Cleaning up database...\n")
    
    async with async_session_maker() as db:
        # Get all pending/hit_created transactions
        result = await db.execute(
            select(CashoutTransaction)
            .where(CashoutTransaction.status.in_([
                CashoutStatus.PENDING,
                CashoutStatus.HIT_CREATED
            ]))
        )
        pending_txs = result.scalars().all()
        
        if not pending_txs:
            print("   ✅ No pending transactions in database")
        else:
            print(f"   Found {len(pending_txs)} pending transaction(s)")
            print(f"   Cancelling and refunding...\n")
            
            total_refunded = 0
            cancelled_count = 0
            
            for tx in pending_txs:
                # Get user
                user_result = await db.execute(
                    select(User).where(User.id == tx.user_id)
                )
                user = user_result.scalar_one_or_none()
                
                if user:
                    print(f"   Transaction: {tx.id}")
                    print(f"      User: {user.user_id}")
                    print(f"      Amount: {tx.amount_gems} gems (${tx.amount_usd})")
                    
                    # Refund gems
                    user.gem_balance += tx.amount_gems
                    if user.total_gems_cashed_out >= tx.amount_gems:
                        user.total_gems_cashed_out -= tx.amount_gems
                    
                    total_refunded += tx.amount_gems
                    print(f"      ✅ Refunded {tx.amount_gems} gems")
                
                # Cancel transaction
                tx.status = CashoutStatus.CANCELLED
                tx.error_message = "Cancelled: Admin deleted all HITs"
                tx.completed_at = datetime.utcnow()
                cancelled_count += 1
                print()
            
            # Commit all changes
            await db.commit()
            
            print("─"*70)
            print(f"Database Cleanup Summary:")
            print(f"   Transactions cancelled: {cancelled_count}")
            print(f"   Total gems refunded: {total_refunded}")
            print("─"*70)
    
    print()
    print("="*70)
    print("✅ CLEANUP COMPLETE - ALL HITs DELETED")
    print("="*70)


async def list_all_hits():
    """Just list all HITs without deleting."""
    print("="*70)
    print("📋 LIST ALL HITs")
    print("="*70)
    
    try:
        mturk_client = get_mturk_client()
        print(f"\n✅ Connected to MTurk ({mturk_client.environment} environment)\n")
    except Exception as e:
        print(f"\n❌ Failed to connect to MTurk: {e}")
        return
    
    all_hits = []
    next_token = None
    
    try:
        while True:
            if next_token:
                response = mturk_client.client.list_hits(
                    NextToken=next_token,
                    MaxResults=100
                )
            else:
                response = mturk_client.client.list_hits(MaxResults=100)
            
            hits = response.get('HITs', [])
            all_hits.extend(hits)
            
            next_token = response.get('NextToken')
            if not next_token:
                break
        
        print(f"Found {len(all_hits)} HIT(s)\n")
        
        if not all_hits:
            print("✅ No HITs found")
            return
        
        for i, hit in enumerate(all_hits, 1):
            hit_id = hit['HITId']
            title = hit.get('Title', 'Untitled')
            status = hit.get('HITStatus', 'Unknown')
            reward = hit.get('Reward', 'Unknown')
            created = hit.get('CreationTime', 'Unknown')
            expiration = hit.get('Expiration', 'Unknown')
            
            print(f"{i}. HIT ID: {hit_id}")
            print(f"   Title: {title}")
            print(f"   Status: {status}")
            print(f"   Reward: {reward}")
            print(f"   Created: {created}")
            print(f"   Expires: {expiration}")
            print()
        
    except Exception as e:
        print(f"❌ Error listing HITs: {e}")


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1 and sys.argv[1] == "--list":
        asyncio.run(list_all_hits())
    else:
        print("\n⚠️  THIS WILL DELETE ALL HITs!")
        print("⚠️  Are you sure? This action cannot be undone.")
        print("\nTo proceed, run:")
        print("   python3 delete_all_hits.py --confirm")
        print("\nTo just list HITs without deleting:")
        print("   python3 delete_all_hits.py --list")
        print()
        
        if len(sys.argv) > 1 and sys.argv[1] == "--confirm":
            asyncio.run(delete_all_hits())
        else:
            print("Aborted. No HITs were deleted.")
