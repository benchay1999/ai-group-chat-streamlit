#!/usr/bin/env python3
"""
Find which transaction corresponds to a HIT ID
"""
import sys
import asyncio
from sqlalchemy import select
from database import async_session_maker, CashoutTransaction
from mturk_api import get_mturk_client

async def find_hit_transaction(hit_id):
    """Find transaction for a HIT."""
    print(f"\n🔍 Looking for transaction with HIT ID: {hit_id}\n")
    
    async with async_session_maker() as db:
        # Find transaction with this HIT ID
        result = await db.execute(
            select(CashoutTransaction)
            .where(CashoutTransaction.mturk_hit_id == hit_id)
        )
        tx = result.scalar_one_or_none()
        
        if tx:
            print(f"✅ Found transaction:")
            print(f"   Transaction ID: {tx.id}")
            print(f"   User ID: {tx.user_id}")
            print(f"   Amount: ${tx.amount_usd} ({tx.amount_gems} gems)")
            print(f"   Status: {tx.status}")
            print(f"   Redemption Code: {tx.redemption_code[:20]}...")
            print(f"   Created: {tx.created_at}")
            print(f"   HIT ID: {tx.mturk_hit_id}")
            
            # Get HIT details from MTurk
            print(f"\n📋 Fetching HIT details from MTurk...")
            mturk = get_mturk_client()
            try:
                response = mturk.client.get_hit(HITId=hit_id)
                hit = response['HIT']
                
                print(f"   Title: {hit.get('Title')}")
                print(f"   Reward: ${hit.get('Reward')}")
                print(f"   Status: {hit.get('HITStatus')}")
                print(f"   HITGroupId: {hit.get('HITGroupId')}")
                print(f"\n✅ Correct URL:")
                print(f"   https://workersandbox.mturk.com/mturk/preview?groupId={hit.get('HITGroupId')}")
                
            except Exception as e:
                print(f"   ❌ Error fetching HIT: {e}")
        else:
            print(f"❌ No transaction found with HIT ID: {hit_id}")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python find_hit_transaction.py <HITId>")
    else:
        asyncio.run(find_hit_transaction(sys.argv[1]))

