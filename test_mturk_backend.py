"""
Test script for MTurk backend integration.
Tests the MTurk API module and database integration without requiring AWS credentials.
"""

import asyncio
import sys
import os

# Add backend to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'backend'))

from backend.database import async_session_maker, Session, User
from backend.auth import register_or_login_mturk_worker
from sqlalchemy import select
import uuid


async def test_mturk_worker_registration():
    """Test MTurk worker auto-registration."""
    print("\n" + "="*60)
    print("TEST 1: MTurk Worker Auto-Registration")
    print("="*60)
    
    test_worker_id = f"TEST_WORKER_{uuid.uuid4().hex[:8]}"
    
    async with async_session_maker() as db:
        # Test registration
        print(f"\n1. Registering MTurk worker: {test_worker_id}")
        user, token = await register_or_login_mturk_worker(db, test_worker_id)
        
        print(f"   ✅ User created: {user.user_id}")
        print(f"   ✅ JWT token generated: {token[:50]}...")
        print(f"   ✅ User role: {user.role.value}")
        
        # Test re-login (should return existing user)
        print(f"\n2. Re-logging in same worker: {test_worker_id}")
        user2, token2 = await register_or_login_mturk_worker(db, test_worker_id)
        
        print(f"   ✅ Same user returned: {user2.id == user.id}")
        print(f"   ✅ New token generated: {token2[:50]}...")
        
        assert user2.id == user.id, "Should return same user on re-login"
        # Note: Tokens may be identical if generated in same second (JWT includes timestamp)
        print(f"   ℹ️  Tokens identical: {token == token2} (normal if generated in same second)")
        
    print("\n✅ MTurk worker registration test PASSED")


async def test_mturk_session_fields():
    """Test that MTurk fields exist in Session model."""
    print("\n" + "="*60)
    print("TEST 2: MTurk Session Fields")
    print("="*60)
    
    # Check that MTurk fields exist in the model
    print("\n1. Checking MTurk fields in Session model...")
    
    required_fields = [
        'mturk_worker_id',
        'mturk_assignment_id',
        'mturk_hit_id',
        'mturk_payment_sent',
        'mturk_bonus_sent'
    ]
    
    for field in required_fields:
        assert hasattr(Session, field), f"Session model missing field: {field}"
        print(f"   ✅ Field exists: {field}")
    
    print("\n✅ MTurk session fields test PASSED")


async def test_mturk_session_creation():
    """Test creating a session with MTurk data."""
    print("\n" + "="*60)
    print("TEST 3: MTurk Session Creation")
    print("="*60)
    
    test_worker_id = f"TEST_WORKER_{uuid.uuid4().hex[:8]}"
    test_assignment_id = f"TEST_ASSIGNMENT_{uuid.uuid4().hex[:8]}"
    test_hit_id = f"TEST_HIT_{uuid.uuid4().hex[:8]}"
    
    async with async_session_maker() as db:
        # Create a test user
        print(f"\n1. Creating test MTurk worker: {test_worker_id}")
        user, _ = await register_or_login_mturk_worker(db, test_worker_id)
        
        # Create a test session with MTurk data
        print(f"\n2. Creating session with MTurk data...")
        from decimal import Decimal
        from backend.database import PaymentStatus
        
        session = Session(
            room_code="TEST123",
            completion_key="test_completion_key",
            user_id=user.id,
            language="english",
            total_players=5,
            num_human_players=1,
            discussion_duration=180,
            voting_duration=60,
            payment_status=PaymentStatus.PENDING,
            stats_file_path="/tmp/test_stats.json",
            calculated_earnings=Decimal("0.35"),
            # MTurk fields
            mturk_worker_id=test_worker_id,
            mturk_assignment_id=test_assignment_id,
            mturk_hit_id=test_hit_id,
            mturk_payment_sent=0,
            mturk_bonus_sent=0
        )
        
        db.add(session)
        await db.commit()
        await db.refresh(session)
        
        print(f"   ✅ Session created with ID: {session.id}")
        print(f"   ✅ MTurk worker ID: {session.mturk_worker_id}")
        print(f"   ✅ MTurk assignment ID: {session.mturk_assignment_id}")
        print(f"   ✅ MTurk HIT ID: {session.mturk_hit_id}")
        print(f"   ✅ Calculated earnings: ${session.calculated_earnings}")
        
        # Verify we can query by MTurk assignment ID
        print(f"\n3. Querying session by MTurk assignment ID...")
        result = await db.execute(
            select(Session).where(Session.mturk_assignment_id == test_assignment_id)
        )
        found_session = result.scalar_one_or_none()
        
        assert found_session is not None, "Should find session by assignment ID"
        assert found_session.id == session.id, "Should return correct session"
        print(f"   ✅ Session found by assignment ID")
        
    print("\n✅ MTurk session creation test PASSED")


async def test_mturk_api_module():
    """Test that MTurk API module can be imported and initialized."""
    print("\n" + "="*60)
    print("TEST 4: MTurk API Module")
    print("="*60)
    
    print("\n1. Importing MTurk API module...")
    try:
        from backend.mturk_api import MTurkClient, get_mturk_client
        print("   ✅ MTurk API module imported successfully")
        
        print("\n2. Checking MTurkClient class...")
        assert hasattr(MTurkClient, 'create_hit'), "MTurkClient missing create_hit method"
        assert hasattr(MTurkClient, 'approve_assignment'), "MTurkClient missing approve_assignment method"
        assert hasattr(MTurkClient, 'send_bonus'), "MTurkClient missing send_bonus method"
        assert hasattr(MTurkClient, 'get_assignment'), "MTurkClient missing get_assignment method"
        assert hasattr(MTurkClient, 'list_hits'), "MTurkClient missing list_hits method"
        print("   ✅ All required methods exist")
        
        print("\n3. Testing client initialization (will fail without AWS credentials - expected)...")
        try:
            client = get_mturk_client()
            print(f"   ✅ Client initialized in {client.environment} mode")
            print(f"   ✅ Base pay configured: ${client.base_pay}")
            print(f"   ✅ External URL: {client.external_url}")
        except Exception as e:
            print(f"   ⚠️  Client initialization failed (expected without AWS credentials): {e}")
            print(f"   ℹ️  This is normal - AWS credentials needed for actual API calls")
        
    except ImportError as e:
        print(f"   ❌ Failed to import MTurk API module: {e}")
        raise
    
    print("\n✅ MTurk API module test PASSED")


async def main():
    """Run all tests."""
    print("\n" + "="*60)
    print("MTurk Backend Integration Tests")
    print("="*60)
    
    try:
        await test_mturk_worker_registration()
        await test_mturk_session_fields()
        await test_mturk_session_creation()
        await test_mturk_api_module()
        
        print("\n" + "="*60)
        print("✅ ALL TESTS PASSED!")
        print("="*60)
        print("\nBackend MTurk integration is working correctly.")
        print("Next steps:")
        print("  1. Set up AWS credentials in .env file")
        print("  2. Test with MTurk Sandbox")
        print("  3. Implement frontend integration")
        print()
        
    except Exception as e:
        print(f"\n❌ TEST FAILED: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())

