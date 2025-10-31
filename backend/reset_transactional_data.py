#!/usr/bin/env python3
"""
Database Reset Script - Clear Transactional Data
=================================================

This script clears all game-related transactional data while preserving user accounts.

What gets DELETED:
- All game sessions
- All session player mappings
- All AI agent usage records
- All cashout transactions

What gets RESET to 0:
- User gem balances
- User total gems earned
- User total gems cashed out
- User total games played
- User total wins
- User total points
- User streaks
- User level

What gets PRESERVED:
- User accounts (user_id, passwords)
- User roles (admin/user)
- MTurk Worker IDs
- User creation dates

IMPORTANT: This cannot be undone! Make a backup first if needed.
"""

import asyncio
import sys
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession
from database import async_session_maker, User, Session, SessionPlayer, AIAgentUsage, CashoutTransaction
from sqlalchemy import select, delete


async def confirm_reset():
    """Ask user to confirm the reset operation."""
    print("\n" + "="*70)
    print("⚠️  DATABASE RESET - TRANSACTIONAL DATA")
    print("="*70)
    print("\nThis will DELETE:")
    print("  ❌ All game sessions")
    print("  ❌ All session player mappings")
    print("  ❌ All AI agent usage records")
    print("  ❌ All cashout transactions")
    print("\nThis will RESET:")
    print("  🔄 User gem balances → 0")
    print("  🔄 User total gems earned → 0")
    print("  🔄 User total gems cashed out → 0")
    print("  🔄 User game stats → 0")
    print("\nThis will PRESERVE:")
    print("  ✅ User accounts (user_id, passwords)")
    print("  ✅ User roles (admin/user)")
    print("  ✅ MTurk Worker IDs")
    print("  ✅ User creation dates")
    print("\n" + "="*70)
    
    response = input("\n⚠️  Are you ABSOLUTELY SURE? Type 'RESET' to continue: ")
    return response == "RESET"


async def get_table_counts(db: AsyncSession):
    """Get counts of records in all tables."""
    counts = {}
    
    # Count sessions
    result = await db.execute(select(Session))
    counts['sessions'] = len(result.scalars().all())
    
    # Count session players
    result = await db.execute(select(SessionPlayer))
    counts['session_players'] = len(result.scalars().all())
    
    # Count AI agent usage
    result = await db.execute(select(AIAgentUsage))
    counts['ai_agent_usage'] = len(result.scalars().all())
    
    # Count cashout transactions
    result = await db.execute(select(CashoutTransaction))
    counts['cashout_transactions'] = len(result.scalars().all())
    
    # Count users
    result = await db.execute(select(User))
    counts['users'] = len(result.scalars().all())
    
    return counts


async def reset_transactional_data():
    """Reset all transactional data while preserving user accounts."""
    
    async with async_session_maker() as db:
        try:
            print("\n📊 Collecting current database statistics...")
            before_counts = await get_table_counts(db)
            
            print("\nCurrent database state:")
            print(f"  Users: {before_counts['users']}")
            print(f"  Sessions: {before_counts['sessions']}")
            print(f"  Session Players: {before_counts['session_players']}")
            print(f"  AI Agent Usage: {before_counts['ai_agent_usage']}")
            print(f"  Cashout Transactions: {before_counts['cashout_transactions']}")
            
            if not await confirm_reset():
                print("\n❌ Reset cancelled by user.")
                return False
            
            print("\n🔄 Starting reset process...\n")
            
            # Step 1: Delete cashout transactions
            print("1️⃣  Deleting cashout transactions...")
            result = await db.execute(delete(CashoutTransaction))
            print(f"   ✅ Deleted {before_counts['cashout_transactions']} cashout transaction(s)")
            
            # Step 2: Delete AI agent usage records
            print("\n2️⃣  Deleting AI agent usage records...")
            result = await db.execute(delete(AIAgentUsage))
            print(f"   ✅ Deleted {before_counts['ai_agent_usage']} AI agent usage record(s)")
            
            # Step 3: Delete session players
            print("\n3️⃣  Deleting session player mappings...")
            result = await db.execute(delete(SessionPlayer))
            print(f"   ✅ Deleted {before_counts['session_players']} session player mapping(s)")
            
            # Step 4: Delete sessions
            print("\n4️⃣  Deleting game sessions...")
            result = await db.execute(delete(Session))
            print(f"   ✅ Deleted {before_counts['sessions']} game session(s)")
            
            # Step 5: Reset user stats
            print("\n5️⃣  Resetting user statistics...")
            result = await db.execute(select(User))
            users = result.scalars().all()
            
            reset_count = 0
            for user in users:
                # Reset gem economy fields
                user.gem_balance = 0
                user.total_gems_earned = 0
                user.total_gems_cashed_out = 0
                
                # Reset game stats
                user.total_games = 0
                user.total_wins = 0
                user.total_points = 0
                user.current_streak = 0
                user.longest_streak = 0
                user.level = 1
                user.last_played_at = None
                
                reset_count += 1
                print(f"   🔄 Reset stats for user: {user.user_id}")
            
            print(f"\n   ✅ Reset {reset_count} user account(s)")
            
            # Commit all changes
            await db.commit()
            
            print("\n" + "="*70)
            print("✅ RESET COMPLETE")
            print("="*70)
            
            # Verify final state
            print("\n📊 Verifying final database state...")
            after_counts = await get_table_counts(db)
            
            print("\nFinal database state:")
            print(f"  Users: {after_counts['users']} (preserved)")
            print(f"  Sessions: {after_counts['sessions']} (should be 0)")
            print(f"  Session Players: {after_counts['session_players']} (should be 0)")
            print(f"  AI Agent Usage: {after_counts['ai_agent_usage']} (should be 0)")
            print(f"  Cashout Transactions: {after_counts['cashout_transactions']} (should be 0)")
            
            # Verification
            if (after_counts['sessions'] == 0 and 
                after_counts['session_players'] == 0 and 
                after_counts['ai_agent_usage'] == 0 and 
                after_counts['cashout_transactions'] == 0):
                print("\n✅ Verification passed! All transactional data cleared.")
            else:
                print("\n⚠️  Warning: Some data may not have been cleared properly.")
            
            print("\n🎉 Database reset successful!")
            print("\nUser accounts preserved:")
            for user in users:
                print(f"  ✅ {user.user_id} (Role: {user.role.value}, MTurk: {user.mturk_worker_id or 'Not set'})")
            
            return True
            
        except Exception as e:
            print(f"\n❌ Error during reset: {e}")
            import traceback
            traceback.print_exc()
            await db.rollback()
            return False


async def main():
    """Main entry point."""
    print("\n🔧 Database Reset Tool")
    print("="*70)
    
    try:
        success = await reset_transactional_data()
        
        if success:
            print("\n✅ All done! The database has been reset.")
            print("   User accounts are preserved and ready for a fresh start.")
            sys.exit(0)
        else:
            print("\n❌ Reset failed or was cancelled.")
            sys.exit(1)
            
    except KeyboardInterrupt:
        print("\n\n⚠️  Reset interrupted by user (Ctrl+C)")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    print("\n" + "="*70)
    print("DATABASE RESET SCRIPT")
    print("="*70)
    print("\n⚠️  This script will clear all game data but keep user accounts.")
    print("Make sure you understand what this does before proceeding!\n")
    
    # Run the async main function
    asyncio.run(main())

