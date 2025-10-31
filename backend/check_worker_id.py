#!/usr/bin/env python3
"""
Worker ID Diagnostic Tool
Checks if user's Worker ID is valid and can receive qualifications.
"""

import asyncio
import sys
from sqlalchemy import select
from database import async_session_maker, User
from mturk_api import MTurkClient


async def check_worker_id(user_id: str = None, email: str = None):
    """
    Check if a user's Worker ID is valid in MTurk.
    
    Args:
        user_id: User UUID (optional)
        email: User email (optional)
    """
    print("="*70)
    print("🔍 WORKER ID DIAGNOSTIC TOOL")
    print("="*70)
    
    async with async_session_maker() as session:
        # Find user
        if user_id:
            result = await session.execute(
                select(User).where(User.user_id == user_id)
            )
        elif email:
            result = await session.execute(
                select(User).where(User.email == email)
            )
        else:
            # Get all users with Worker IDs
            result = await session.execute(
                select(User).where(User.mturk_worker_id.isnot(None))
            )
        
        users = result.scalars().all()
        
        if not users:
            print("\n❌ No users found")
            if user_id:
                print(f"   User ID: {user_id}")
            elif email:
                print(f"   Email: {email}")
            else:
                print("   No users have Worker IDs set")
            return
        
        print(f"\n📋 Found {len(users)} user(s)\n")
        
        # Initialize MTurk client
        try:
            mturk_client = MTurkClient()
            print(f"✅ MTurk client initialized ({mturk_client.environment} environment)\n")
        except Exception as e:
            print(f"❌ Failed to initialize MTurk client: {e}\n")
            return
        
        # Check each user
        for user in users:
            print("-"*70)
            print(f"\n👤 User ID: {user.user_id}")
            print(f"   Role: {user.role}")
            print(f"   Worker ID: {user.mturk_worker_id or 'NOT SET'}")
            print(f"   Gem Balance: {user.gem_balance} gems")
            
            if not user.mturk_worker_id:
                print("\n   ⚠️  Worker ID not set - user cannot cash out")
                continue
            
            worker_id = user.mturk_worker_id.strip()
            
            # Check format
            print(f"\n   🔍 Checking Worker ID format...")
            if len(worker_id) < 10:
                print(f"   ❌ Too short (length: {len(worker_id)})")
                print(f"   ❌ Valid Worker IDs are typically 14+ characters")
            elif not worker_id.startswith('A'):
                print(f"   ⚠️  Doesn't start with 'A' (unusual but might be valid)")
            else:
                print(f"   ✅ Format looks correct (length: {len(worker_id)})")
            
            # Check if Worker ID has whitespace
            if worker_id != user.mturk_worker_id:
                print(f"   ⚠️  WARNING: Worker ID has leading/trailing whitespace!")
                print(f"   Original: '{user.mturk_worker_id}'")
                print(f"   Trimmed:  '{worker_id}'")
            
            # Try to create a test qualification
            print(f"\n   🧪 Testing qualification assignment...")
            try:
                # Create a test qualification
                qual_response = mturk_client.client.create_qualification_type(
                    Name=f"Test_Diagnostic_{user.user_id}",
                    Description="Diagnostic test qualification",
                    QualificationTypeStatus='Active',
                    AutoGranted=False
                )
                
                qual_id = qual_response['QualificationType']['QualificationTypeId']
                print(f"   ✅ Test qualification created: {qual_id}")
                
                # Try to assign it to the worker
                try:
                    mturk_client.client.associate_qualification_with_worker(
                        QualificationTypeId=qual_id,
                        WorkerId=worker_id,
                        IntegerValue=1,
                        SendNotification=False
                    )
                    print(f"   ✅ Successfully assigned qualification to worker")
                    
                    # Verify it was assigned
                    try:
                        verification = mturk_client.client.get_qualification_score(
                            QualificationTypeId=qual_id,
                            WorkerId=worker_id
                        )
                        qual_value = verification.get('Qualification', {}).get('IntegerValue', 'N/A')
                        print(f"   ✅ Verification successful - Worker has qualification (value: {qual_value})")
                        print(f"\n   🎉 WORKER ID IS VALID AND WORKING!")
                        
                    except Exception as verify_error:
                        print(f"   ❌ Could not verify qualification: {verify_error}")
                        print(f"   ❌ Worker ID might not exist in MTurk")
                    
                    # Clean up - delete the test qualification
                    try:
                        # First, disassociate from worker
                        mturk_client.client.disassociate_qualification_from_worker(
                            QualificationTypeId=qual_id,
                            WorkerId=worker_id,
                            Reason="Diagnostic test completed"
                        )
                        print(f"   🧹 Cleaned up test qualification")
                    except:
                        pass
                        
                except Exception as assign_error:
                    print(f"   ❌ Failed to assign qualification: {assign_error}")
                    print(f"\n   ❌ WORKER ID IS INVALID OR DOESN'T EXIST IN MTURK")
                    print(f"\n   💡 This is likely the problem!")
                    print(f"   💡 Please verify the Worker ID is correct:")
                    print(f"      1. Go to https://workersandbox.mturk.com")
                    print(f"      2. Click your name → Account")
                    print(f"      3. Copy your Worker ID")
                    print(f"      4. Update it in your profile")
                
            except Exception as e:
                print(f"   ❌ Failed to create test qualification: {e}")
            
            print()


async def list_all_users():
    """List all users and their Worker IDs."""
    print("="*70)
    print("👥 ALL USERS")
    print("="*70)
    
    async with async_session_maker() as session:
        result = await session.execute(select(User))
        users = result.scalars().all()
        
        if not users:
            print("\n❌ No users found in database")
            return
        
        print(f"\nTotal users: {len(users)}\n")
        
        for i, user in enumerate(users, 1):
            print(f"{i}. User ID: {user.user_id}")
            print(f"   Role: {user.role}")
            print(f"   Worker ID: {user.mturk_worker_id or '❌ NOT SET'}")
            print(f"   Gems: {user.gem_balance}")
            print(f"   Total Games: {user.total_games}")
            print()


if __name__ == "__main__":
    if len(sys.argv) > 1:
        if sys.argv[1] == "--list":
            asyncio.run(list_all_users())
        elif sys.argv[1] == "--email":
            if len(sys.argv) > 2:
                asyncio.run(check_worker_id(email=sys.argv[2]))
            else:
                print("Usage: python check_worker_id.py --email user@example.com")
        elif sys.argv[1] == "--user-id":
            if len(sys.argv) > 2:
                asyncio.run(check_worker_id(user_id=sys.argv[2]))
            else:
                print("Usage: python check_worker_id.py --user-id <user-uuid>")
        else:
            print("Usage:")
            print("  python check_worker_id.py --list")
            print("  python check_worker_id.py --email user@example.com")
            print("  python check_worker_id.py --user-id <user-uuid>")
    else:
        # Check all users with Worker IDs
        asyncio.run(check_worker_id())

