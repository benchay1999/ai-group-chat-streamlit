#!/usr/bin/env python3
"""
Test cashout creation to see detailed error messages.
"""

import asyncio
from decimal import Decimal
from sqlalchemy import select
from database import async_session_maker, User
from per_transaction_hit_service import create_worker_specific_hit
from cashout_service import create_cashout_transaction


async def test_cashout(user_id: str, amount: float):
    """Test creating a cashout."""
    print("="*70)
    print("🧪 TESTING CASHOUT CREATION")
    print("="*70)
    print(f"User ID: {user_id}")
    print(f"Amount: ${amount}\n")
    
    async with async_session_maker() as db:
        # Get user
        result = await db.execute(
            select(User).where(User.user_id == user_id)
        )
        user = result.scalar_one_or_none()
        
        if not user:
            print(f"❌ User not found: {user_id}")
            return
        
        print(f"✅ Found user: {user.user_id}")
        print(f"   Worker ID: {user.mturk_worker_id}")
        print(f"   Gem balance: {user.gem_balance}")
        print()
        
        # Check if user has Worker ID
        if not user.mturk_worker_id:
            print("❌ ERROR: User has no MTurk Worker ID set!")
            print("   Solution: Add Worker ID in profile settings")
            return
        
        # Check if user has enough gems
        gems_needed = int(amount * 1000)
        if user.gem_balance < gems_needed:
            print(f"❌ ERROR: Insufficient gems!")
            print(f"   Need: {gems_needed} gems")
            print(f"   Have: {user.gem_balance} gems")
            return
        
        print("✅ Validation passed")
        print()
        
        # Try to create transaction
        print("📝 Creating transaction...")
        try:
            transaction = await create_cashout_transaction(
                user=user,
                amount_usd=Decimal(str(amount)),
                db=db
            )
            print(f"✅ Transaction created: {transaction.id}")
            print(f"   Amount USD: ${transaction.amount_usd}")
            print(f"   Amount gems: {transaction.amount_gems}")
            print(f"   Redemption code: {transaction.redemption_code}")
            print()
            
        except Exception as e:
            print(f"❌ Failed to create transaction: {e}")
            import traceback
            traceback.print_exc()
            return
        
        # Try to create HIT
        print("🎯 Creating worker-specific HIT...")
        try:
            result = await create_worker_specific_hit(
                user=user,
                transaction=transaction,
                db=db
            )
            
            if result.get('success'):
                print("✅ HIT created successfully!")
                print(f"   HIT ID: {result.get('hit_id')}")
                print(f"   HIT URL: {result.get('hit_url')}")
            else:
                print(f"❌ HIT creation failed: {result.get('error')}")
                
        except Exception as e:
            print(f"❌ Exception during HIT creation: {e}")
            import traceback
            traceback.print_exc()


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) < 2:
        print("Usage: python test_cashout_creation.py <user_id> [amount]")
        print("Example: python test_cashout_creation.py benchay 2.00")
    else:
        user_id = sys.argv[1]
        amount = float(sys.argv[2]) if len(sys.argv) > 2 else 2.00
        asyncio.run(test_cashout(user_id, amount))

