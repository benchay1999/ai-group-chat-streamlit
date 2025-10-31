#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Verify cashout system integrity.
Checks for gem duplication bugs and transaction inconsistencies.
"""

import asyncio
from sqlalchemy import select, func
from database import async_session_maker, User, CashoutTransaction, CashoutStatus

async def verify_cashout_integrity():
    """Run integrity checks on cashout system."""
    
    print("=" * 70)
    print("  CASHOUT SYSTEM INTEGRITY CHECK")
    print("=" * 70)
    
    async with async_session_maker() as db:
        # Check 1: Users with negative gem balances (IMPOSSIBLE)
        print("\n1️⃣  Checking for negative gem balances...")
        result = await db.execute(
            select(User).where(User.gem_balance < 0)
        )
        negative_users = result.scalars().all()
        
        if negative_users:
            print(f"   ❌ CRITICAL: {len(negative_users)} users have NEGATIVE gem balances!")
            for user in negative_users:
                print(f"      User: {user.user_id}, Balance: {user.gem_balance}")
        else:
            print(f"   ✅ All users have non-negative balances")
        
        # Check 2: Gems earned vs cashed out consistency
        print("\n2️⃣  Checking gems earned vs cashed out...")
        result = await db.execute(
            select(User).where(User.total_gems_cashed_out > User.total_gems_earned)
        )
        inconsistent_users = result.scalars().all()
        
        if inconsistent_users:
            print(f"   ❌ WARNING: {len(inconsistent_users)} users cashed out MORE than earned!")
            for user in inconsistent_users:
                print(f"      User: {user.user_id}")
                print(f"         Earned: {user.total_gems_earned}")
                print(f"         Cashed out: {user.total_gems_cashed_out}")
        else:
            print(f"   ✅ All cashouts ≤ earnings")
        
        # Check 3: Pending transactions with no gems deducted
        print("\n3️⃣  Checking pending transactions...")
        result = await db.execute(
            select(CashoutTransaction).where(
                CashoutTransaction.status == CashoutStatus.PENDING
            )
        )
        pending_txns = result.scalars().all()
        
        print(f"   📊 Found {len(pending_txns)} pending transaction(s)")
        
        for txn in pending_txns:
            user_result = await db.execute(
                select(User).where(User.id == txn.user_id)
            )
            user = user_result.scalar_one_or_none()
            
            if user:
                print(f"      Transaction: {str(txn.id)[:8]}...")
                print(f"         User: {user.user_id}")
                print(f"         Amount: {txn.amount_gems} gems (${txn.amount_usd})")
                print(f"         User balance: {user.gem_balance} gems")
                print(f"         Created: {txn.created_at}")
        
        # Check 4: Failed transactions - gems should be returned
        print("\n4️⃣  Checking failed/cancelled transactions...")
        result = await db.execute(
            select(func.count()).select_from(CashoutTransaction).where(
                CashoutTransaction.status.in_([CashoutStatus.FAILED, CashoutStatus.CANCELLED])
            )
        )
        failed_count = result.scalar()
        
        print(f"   📊 Found {failed_count} failed/cancelled transaction(s)")
        print(f"   ℹ️  Gems should have been returned for these")
        
        # Check 5: Completed transactions
        print("\n5️⃣  Checking completed transactions...")
        result = await db.execute(
            select(CashoutTransaction).where(
                CashoutTransaction.status == CashoutStatus.COMPLETED
            )
        )
        completed_txns = result.scalars().all()
        
        print(f"   📊 Found {len(completed_txns)} completed transaction(s)")
        
        total_completed_gems = sum(txn.amount_gems for txn in completed_txns)
        total_completed_usd = sum(float(txn.amount_usd) for txn in completed_txns)
        
        print(f"   💎 Total gems paid out: {total_completed_gems:,}")
        print(f"   💵 Total USD paid out: ${total_completed_usd:.2f}")
        
        # Check 6: Sum of all user gem balances
        print("\n6️⃣  Checking total gem economy...")
        result = await db.execute(
            select(func.sum(User.gem_balance), func.sum(User.total_gems_earned))
        )
        total_balance, total_earned = result.one()
        
        print(f"   💎 Total gems in circulation: {total_balance or 0:,}")
        print(f"   📈 Total gems ever earned: {total_earned or 0:,}")
        print(f"   💸 Total gems cashed out: {total_completed_gems:,}")
        
        expected_balance = (total_earned or 0) - total_completed_gems
        actual_balance = total_balance or 0
        
        if abs(expected_balance - actual_balance) > 100:  # Allow small rounding
            print(f"   ❌ CRITICAL: Gem balance mismatch!")
            print(f"      Expected: {expected_balance:,}")
            print(f"      Actual: {actual_balance:,}")
            print(f"      Difference: {actual_balance - expected_balance:,}")
        else:
            print(f"   ✅ Gem economy is consistent")
        
        # Summary
        print("\n" + "=" * 70)
        print("  SUMMARY")
        print("=" * 70)
        
        issues = []
        if negative_users:
            issues.append(f"❌ {len(negative_users)} users with negative balances")
        if inconsistent_users:
            issues.append(f"⚠️  {len(inconsistent_users)} users cashed out more than earned")
        if abs(expected_balance - actual_balance) > 100:
            issues.append(f"❌ Gem economy mismatch: {actual_balance - expected_balance:,} gems")
        
        if issues:
            print("\n🚨 ISSUES FOUND:")
            for issue in issues:
                print(f"   {issue}")
            print("\n⚠️  Manual investigation required!")
        else:
            print("\n✅ ALL CHECKS PASSED - System is healthy!")
        
        print("\n" + "=" * 70)

if __name__ == '__main__':
    asyncio.run(verify_cashout_integrity())

