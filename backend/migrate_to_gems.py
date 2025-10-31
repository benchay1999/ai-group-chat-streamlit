"""
One-time migration script to convert existing calculated_earnings to gems.
Run this after deploying the gem economy system to credit existing users.
"""

import asyncio
from decimal import Decimal
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.database import async_session_maker, User, Session as DBSession
from backend.config import GEMS_PER_DOLLAR


async def migrate_earnings_to_gems():
    """
    Convert all existing calculated_earnings from sessions to gems in user wallets.
    """
    print("=" * 60)
    print("GEM ECONOMY MIGRATION")
    print("=" * 60)
    print()
    print("This script will:")
    print("1. Find all sessions with calculated_earnings")
    print("2. Convert earnings to gems (1000 gems = $1.00)")
    print("3. Credit gems to user wallets")
    print()
    
    async with async_session_maker() as db:
        # Get all sessions with calculated_earnings
        query = select(DBSession).where(
            DBSession.calculated_earnings.isnot(None),
            DBSession.calculated_earnings > 0,
            DBSession.user_id.isnot(None)
        )
        result = await db.execute(query)
        sessions = result.scalars().all()
        
        if not sessions:
            print("✅ No sessions found with calculated earnings. Nothing to migrate.")
            return
        
        print(f"📊 Found {len(sessions)} session(s) with calculated earnings")
        print()
        
        # Group sessions by user
        user_earnings = {}
        for session in sessions:
            user_id = session.user_id
            earnings = float(session.calculated_earnings)
            
            if user_id not in user_earnings:
                user_earnings[user_id] = {
                    'total_usd': Decimal('0'),
                    'session_count': 0
                }
            
            user_earnings[user_id]['total_usd'] += Decimal(str(earnings))
            user_earnings[user_id]['session_count'] += 1
        
        print(f"👥 Found {len(user_earnings)} user(s) with earnings to migrate")
        print()
        
        # Get user objects and credit gems
        total_gems_credited = 0
        users_updated = 0
        
        for user_id, data in user_earnings.items():
            # Get user
            user_result = await db.execute(
                select(User).where(User.id == user_id)
            )
            user = user_result.scalar_one_or_none()
            
            if not user:
                print(f"⚠️  User {user_id} not found, skipping")
                continue
            
            # Calculate gems
            total_usd = data['total_usd']
            gems = int(float(total_usd) * GEMS_PER_DOLLAR)
            session_count = data['session_count']
            
            # Credit gems
            user.gem_balance += gems
            user.total_gems_earned += gems
            
            total_gems_credited += gems
            users_updated += 1
            
            print(f"💎 {user.user_id}:")
            print(f"   Sessions: {session_count}")
            print(f"   Total USD: ${total_usd:.2f}")
            print(f"   Gems: {gems}")
            print(f"   New balance: {user.gem_balance} gems")
            print()
        
        # Commit changes
        await db.commit()
        
        print("=" * 60)
        print("MIGRATION COMPLETE!")
        print("=" * 60)
        print()
        print(f"✅ Users updated: {users_updated}")
        print(f"💎 Total gems credited: {total_gems_credited}")
        print(f"💵 Total USD equivalent: ${total_gems_credited / GEMS_PER_DOLLAR:.2f}")
        print()
        print("🎉 All existing earnings have been converted to gems!")


if __name__ == "__main__":
    asyncio.run(migrate_earnings_to_gems())

