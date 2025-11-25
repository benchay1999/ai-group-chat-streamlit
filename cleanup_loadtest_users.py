#!/usr/bin/env python3
"""
Cleanup script to remove load test users from the database.

Usage:
    python cleanup_loadtest_users.py
    python cleanup_loadtest_users.py --dry-run  # Preview what will be deleted
"""

import asyncio
import argparse
from sqlalchemy import select, delete

# Import from backend
from backend.database import async_session_maker, User


async def cleanup_loadtest_users(dry_run=False):
    """Remove all users with user_id starting with 'loadtest_user_'"""
    
    async with async_session_maker() as db:
        # Count users to be deleted
        result = await db.execute(
            select(User).where(User.user_id.like('loadtest_user_%'))
        )
        users_to_delete = result.scalars().all()
        count = len(users_to_delete)
        
        if count == 0:
            print("✅ No load test users found in database")
            return
        
        print(f"\n{'='*60}")
        print(f"  Load Test User Cleanup")
        print(f"{'='*60}")
        print(f"\n📊 Found {count} load test users to delete")
        
        if dry_run:
            print("\n🔍 DRY RUN - Would delete the following users:")
            for i, user in enumerate(users_to_delete[:10], 1):
                print(f"  {i}. {user.user_id}")
            if count > 10:
                print(f"  ... and {count - 10} more")
            print(f"\n💡 Run without --dry-run to actually delete these users")
        else:
            print("\n⚠️  This will permanently delete these users and their data!")
            
            # Ask for confirmation
            response = input("\nContinue? (yes/no): ").strip().lower()
            if response != 'yes':
                print("❌ Cleanup cancelled")
                return
            
            # Delete users
            await db.execute(
                delete(User).where(User.user_id.like('loadtest_user_%'))
            )
            await db.commit()
            
            print(f"\n✅ Successfully deleted {count} load test users")
        
        print(f"{'='*60}\n")


def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(
        description="Clean up load test users from database"
    )
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help="Preview what would be deleted without actually deleting"
    )
    
    args = parser.parse_args()
    
    asyncio.run(cleanup_loadtest_users(dry_run=args.dry_run))


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n⚠️  Cleanup interrupted by user\n")
        exit(130)
