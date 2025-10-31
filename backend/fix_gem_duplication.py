#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Fix gem duplication caused by cashout bugs.
Recalculates correct gem balances based on earned vs cashed out.
"""

import asyncio
from sqlalchemy import select, func
from database import async_session_maker, User, CashoutTransaction, CashoutStatus

async def fix_gem_duplication():
    """Fix duplicated gems by recalculating correct balances."""
    
    print("=" * 70)
    print("  GEM DUPLICATION FIX")
    print("=" * 70)
    print("\n⚠️  This will recalculate all user gem balances based on:")
    print("   - Total gems earned (from games)")
    print("   - Total gems cashed out (completed cashouts)")
    print("   - Correct formula: balance = earned - cashed_out")
    print("\n" + "=" * 70)
    
    confirm = input("\nProceed with fix? (type 'YES' to continue): ").strip()
    if confirm != 'YES':
        print("❌ Cancelled")
        return
    
    async with async_session_maker() as db:
        print("\n📊 Analyzing current state...")
        
        # Get all users
        result = await db.execute(select(User))
        users = result.scalars().all()
        
        print(f"   Found {len(users)} user(s)")
        
        # Get all completed cashouts
        result = await db.execute(
            select(CashoutTransaction).where(
                CashoutTransaction.status == CashoutStatus.COMPLETED
            )
        )
        completed_cashouts = result.scalars().all()
        
        print(f"   Found {len(completed_cashouts)} completed cashout(s)")
        
        # Calculate cashouts per user
        cashouts_by_user = {}
        for txn in completed_cashouts:
            user_id = str(txn.user_id)
            cashouts_by_user[user_id] = cashouts_by_user.get(user_id, 0) + txn.amount_gems
        
        print("\n🔧 Fixing gem balances...")
        print("=" * 70)
        
        fixed_count = 0
        total_gems_before = 0
        total_gems_after = 0
        
        for user in users:
            user_id_str = str(user.id)
            
            # Calculate correct balance
            earned = user.total_gems_earned
            cashed_out = cashouts_by_user.get(user_id_str, 0)
            correct_balance = earned - cashed_out
            
            current_balance = user.gem_balance
            
            total_gems_before += current_balance
            total_gems_after += correct_balance
            
            if current_balance != correct_balance:
                diff = correct_balance - current_balance
                
                print(f"\n👤 User: {user.user_id}")
                print(f"   Earned: {earned:,} gems")
                print(f"   Cashed out: {cashed_out:,} gems")
                print(f"   Current balance: {current_balance:,} gems ❌")
                print(f"   Correct balance: {correct_balance:,} gems ✅")
                print(f"   Adjustment: {diff:+,} gems")
                
                # Update balance
                user.gem_balance = correct_balance
                fixed_count += 1
            else:
                print(f"✅ User {user.user_id}: Balance correct ({current_balance:,} gems)")
        
        print("\n" + "=" * 70)
        print("  SUMMARY")
        print("=" * 70)
        print(f"\n📊 Users checked: {len(users)}")
        print(f"🔧 Users fixed: {fixed_count}")
        print(f"✅ Users already correct: {len(users) - fixed_count}")
        print(f"\n💎 Total gems before: {total_gems_before:,}")
        print(f"💎 Total gems after: {total_gems_after:,}")
        print(f"🗑️  Gems removed: {total_gems_before - total_gems_after:,}")
        
        if fixed_count > 0:
            print("\n" + "=" * 70)
            confirm_commit = input("\n💾 Commit these changes to database? (type 'YES'): ").strip()
            
            if confirm_commit == 'YES':
                await db.commit()
                print("\n✅ Changes committed successfully!")
                print("   All gem balances have been corrected.")
            else:
                await db.rollback()
                print("\n❌ Changes rolled back - no changes made to database")
        else:
            print("\n✅ No changes needed - all balances are correct!")
        
        print("\n" + "=" * 70)

if __name__ == '__main__':
    asyncio.run(fix_gem_duplication())

