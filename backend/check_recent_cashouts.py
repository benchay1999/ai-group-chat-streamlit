#!/usr/bin/env python3
"""
Check recent cashout transactions for a user.
Shows which HITs are active and which should be used.
"""

import asyncio
import sys
from datetime import datetime
from sqlalchemy import select, desc
from database import async_session_maker, User, CashoutTransaction, CashoutStatus


async def check_recent_cashouts(user_id: str = None):
    """Check recent cashout transactions."""
    print("="*70)
    print("💰 RECENT CASHOUT TRANSACTIONS")
    print("="*70)
    
    async with async_session_maker() as session:
        # Find user
        if user_id:
            result = await session.execute(
                select(User).where(User.user_id == user_id)
            )
            user = result.scalar_one_or_none()
            
            if not user:
                print(f"\n❌ User not found: {user_id}")
                return
            
            print(f"\n👤 User: {user.user_id}")
            print(f"   Worker ID: {user.mturk_worker_id or 'NOT SET'}")
            print(f"   Current Balance: {user.gem_balance} gems")
            
            # Get recent transactions
            result = await session.execute(
                select(CashoutTransaction)
                .where(CashoutTransaction.user_id == user.id)
                .order_by(desc(CashoutTransaction.created_at))
                .limit(10)
            )
            transactions = result.scalars().all()
        else:
            # Get all recent transactions
            result = await session.execute(
                select(CashoutTransaction)
                .order_by(desc(CashoutTransaction.created_at))
                .limit(20)
            )
            transactions = result.scalars().all()
        
        if not transactions:
            print("\n❌ No cashout transactions found")
            return
        
        print(f"\n📋 Found {len(transactions)} transaction(s)\n")
        
        for i, tx in enumerate(transactions, 1):
            age = datetime.utcnow() - tx.created_at
            age_str = f"{age.days}d {age.seconds//3600}h" if age.days > 0 else f"{age.seconds//3600}h {(age.seconds%3600)//60}m"
            
            # Status indicator
            if tx.status == CashoutStatus.PENDING:
                status_icon = "⏳"
            elif tx.status == CashoutStatus.HIT_CREATED:
                status_icon = "🎯"
            elif tx.status == CashoutStatus.PROCESSING:
                status_icon = "🔄"
            elif tx.status == CashoutStatus.COMPLETED:
                status_icon = "✅"
            elif tx.status == CashoutStatus.CANCELLED:
                status_icon = "🚫"
            elif tx.status == CashoutStatus.FAILED:
                status_icon = "❌"
            else:
                status_icon = "❓"
            
            print(f"{i}. {status_icon} Transaction {tx.id}")
            print(f"   Status: {tx.status.value}")
            print(f"   Amount: ${tx.amount_usd} ({tx.amount_gems} gems)")
            print(f"   Created: {tx.created_at} ({age_str} ago)")
            
            if tx.mturk_hit_id:
                print(f"   HIT ID: {tx.mturk_hit_id}")
                
                # Check if HIT is likely still active
                active_statuses = [CashoutStatus.PENDING, CashoutStatus.HIT_CREATED]
                try:
                    active_statuses.append(CashoutStatus.PROCESSING)
                except AttributeError:
                    pass  # PROCESSING might not exist
                
                if tx.status in active_statuses:
                    if age.total_seconds() < 86400:  # Less than 24 hours
                        print(f"   🟢 THIS HIT SHOULD BE ACTIVE")
                        print(f"   👉 Use this HIT link!")
                    else:
                        print(f"   🟡 HIT is old - might be expired")
                        print(f"   ⚠️  Consider cancelling and creating new cashout")
                else:
                    print(f"   🔴 HIT is not active (status: {tx.status.value})")
                    if tx.status == CashoutStatus.COMPLETED:
                        print(f"   ✅ Already completed - payment processed")
                    elif tx.status == CashoutStatus.CANCELLED:
                        print(f"   🚫 Cancelled - gems refunded")
            else:
                print(f"   ⚠️  No HIT ID (HIT not created yet)")
            
            if tx.error_message:
                print(f"   ⚠️  Error: {tx.error_message}")
            
            print()


if __name__ == "__main__":
    if len(sys.argv) > 1:
        asyncio.run(check_recent_cashouts(user_id=sys.argv[1]))
    else:
        asyncio.run(check_recent_cashouts())

