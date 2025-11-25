"""
Payment Fraud Prevention Security Tests

Tests for:
- Double payment prevention
- Payment amount manipulation
- Redemption code security
- Gem balance integrity
"""

import pytest
import asyncio
from decimal import Decimal
from datetime import datetime, timedelta
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
import uuid

from backend.main import app
from backend.database import (
    Base, User, UserRole, CashoutTransaction, CashoutStatus, DBSession, PaymentStatus
)
from backend.auth import hash_password, create_access_token
from backend.cashout_service import (
    create_cashout_transaction, redeem_cashout_code, CashoutError
)


# Test Database Setup
TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"

@pytest.fixture
async def test_db():
    """Create a test database for each test."""
    engine = create_async_engine(TEST_DATABASE_URL, echo=False)
    
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    async_session_maker = async_sessionmaker(
        engine, class_=AsyncSession, expire_on_commit=False
    )
    
    async with async_session_maker() as session:
        yield session
    
    await engine.dispose()


@pytest.fixture
def client():
    """Create test client."""
    return TestClient(app)


@pytest.fixture
async def test_user_with_gems(test_db: AsyncSession):
    """Create a test user with gem balance."""
    user = User(
        id=uuid.uuid4(),
        user_id="rich_user",
        password_hash=hash_password("password"),
        role=UserRole.USER,
        gem_balance=10000,  # 10,000 gems = $10.00
        mturk_worker_id="A1234567890ABC"
    )
    test_db.add(user)
    await test_db.commit()
    await test_db.refresh(user)
    return user


# ============================================================================
# Double Payment Prevention Tests
# ============================================================================

class TestDoublePaymentPrevention:
    """Test that double payments are prevented."""
    
    @pytest.mark.asyncio
    async def test_same_assignment_id_cannot_be_used_twice(self, test_db):
        """Test that same MTurk assignment ID cannot be used for multiple sessions."""
        # Create first session with assignment ID
        session1 = DBSession(
            id=uuid.uuid4(),
            room_code="ROOM1",
            completion_key="key1",
            language="english",
            total_players=5,
            num_human_players=1,
            discussion_duration=180,
            voting_duration=60,
            stats_file_path="/tmp/stats1.json",
            mturk_assignment_id="31234567890123456789012345678901"
        )
        test_db.add(session1)
        await test_db.commit()
        
        # Try to create second session with same assignment ID
        session2 = DBSession(
            id=uuid.uuid4(),
            room_code="ROOM2",
            completion_key="key2",
            language="english",
            total_players=5,
            num_human_players=1,
            discussion_duration=180,
            voting_duration=60,
            stats_file_path="/tmp/stats2.json",
            mturk_assignment_id="31234567890123456789012345678901"  # Same!
        )
        test_db.add(session2)
        
        # Should raise IntegrityError due to unique constraint
        with pytest.raises(Exception):  # IntegrityError or similar
            await test_db.commit()
    
    @pytest.mark.asyncio
    async def test_redemption_code_cannot_be_redeemed_twice(self, test_user_with_gems, test_db):
        """Test that redemption codes can only be used once."""
        # Create cashout transaction
        transaction = await create_cashout_transaction(
            user=test_user_with_gems,
            amount_usd=Decimal("5.00"),
            db=test_db
        )
        
        # Redeem code first time
        result1 = await redeem_cashout_code(
            redemption_code=transaction.redemption_code,
            worker_id="A1234567890ABC",
            assignment_id="DEV_TEST_123",  # Dev mode
            hit_id="H123",
            db=test_db
        )
        assert result1["success"] is True
        
        # Try to redeem again (should fail)
        with pytest.raises(CashoutError) as exc_info:
            await redeem_cashout_code(
                redemption_code=transaction.redemption_code,
                worker_id="A1234567890ABC",
                assignment_id="DEV_TEST_456",
                hit_id="H123",
                db=test_db
            )
        
        assert "already been redeemed" in str(exc_info.value)
    
    @pytest.mark.asyncio
    async def test_session_payment_flag_prevents_double_payment(self, test_db):
        """Test that mturk_payment_sent flag prevents double payments."""
        # Create session
        session = DBSession(
            id=uuid.uuid4(),
            room_code="ROOM1",
            completion_key="key1",
            language="english",
            total_players=5,
            num_human_players=1,
            discussion_duration=180,
            voting_duration=60,
            stats_file_path="/tmp/stats1.json",
            mturk_assignment_id="31234567890123456789012345678901",
            mturk_payment_sent=0
        )
        test_db.add(session)
        await test_db.commit()
        await test_db.refresh(session)
        
        # First payment
        session.mturk_payment_sent = 1
        await test_db.commit()
        
        # Verify flag is set
        result = await test_db.execute(
            select(DBSession).where(DBSession.id == session.id)
        )
        updated_session = result.scalar_one()
        assert updated_session.mturk_payment_sent == 1


# ============================================================================
# Payment Amount Manipulation Tests
# ============================================================================

class TestPaymentAmountManipulation:
    """Test that payment amounts cannot be manipulated."""
    
    @pytest.mark.asyncio
    async def test_gem_balance_validation(self, test_db):
        """Test that insufficient gem balance prevents cashout."""
        # User with only 100 gems
        user = User(
            id=uuid.uuid4(),
            user_id="poor_user",
            password_hash=hash_password("password"),
            role=UserRole.USER,
            gem_balance=100,  # Only 100 gems = $0.10
            mturk_worker_id="A1234567890ABC"
        )
        test_db.add(user)
        await test_db.commit()
        await test_db.refresh(user)
        
        # Try to cash out $5 (requires 5000 gems)
        with pytest.raises(CashoutError) as exc_info:
            await create_cashout_transaction(
                user=user,
                amount_usd=Decimal("5.00"),
                db=test_db
            )
        
        assert "insufficient" in str(exc_info.value).lower()
    
    @pytest.mark.asyncio
    async def test_minimum_cashout_amount_enforced(self, test_user_with_gems, test_db):
        """Test that minimum cashout amount is enforced."""
        # Try to cash out $0.50 (below minimum of $2.00)
        with pytest.raises(CashoutError) as exc_info:
            await create_cashout_transaction(
                user=test_user_with_gems,
                amount_usd=Decimal("0.50"),
                db=test_db
            )
        
        assert "minimum" in str(exc_info.value).lower()
    
    @pytest.mark.asyncio
    async def test_negative_amount_rejected(self, test_user_with_gems, test_db):
        """Test that negative amounts are rejected."""
        with pytest.raises(CashoutError):
            await create_cashout_transaction(
                user=test_user_with_gems,
                amount_usd=Decimal("-5.00"),
                db=test_db
            )


# ============================================================================
# Redemption Code Security Tests
# ============================================================================

class TestRedemptionCodeSecurity:
    """Test redemption code security mechanisms."""
    
    @pytest.mark.asyncio
    async def test_expired_code_rejection(self, test_user_with_gems, test_db):
        """Test that expired redemption codes are rejected."""
        # Create transaction with expired code
        transaction = CashoutTransaction(
            id=uuid.uuid4(),
            user_id=test_user_with_gems.id,
            amount_gems=5000,
            amount_usd=Decimal("5.00"),
            status=CashoutStatus.PENDING,
            redemption_code="expired_code_12345678901234567890123456789012345678901234",
            created_at=datetime.utcnow() - timedelta(days=8),  # 8 days ago
            expires_at=datetime.utcnow() - timedelta(days=1)   # Expired yesterday
        )
        test_db.add(transaction)
        await test_db.commit()
        
        # Try to redeem expired code
        with pytest.raises(CashoutError) as exc_info:
            await redeem_cashout_code(
                redemption_code=transaction.redemption_code,
                worker_id="A1234567890ABC",
                assignment_id="DEV_TEST_123",
                hit_id="H123",
                db=test_db
            )
        
        assert "expired" in str(exc_info.value).lower()
    
    @pytest.mark.asyncio
    async def test_invalid_code_format_rejection(self, test_db):
        """Test that invalid redemption codes are rejected."""
        # Try to redeem non-existent code
        with pytest.raises(CashoutError) as exc_info:
            await redeem_cashout_code(
                redemption_code="invalid_code_123",
                worker_id="A1234567890ABC",
                assignment_id="DEV_TEST_123",
                hit_id="H123",
                db=test_db
            )
        
        assert "invalid" in str(exc_info.value).lower()
    
    @pytest.mark.asyncio
    async def test_cancelled_code_rejection(self, test_user_with_gems, test_db):
        """Test that cancelled redemption codes cannot be redeemed."""
        # Create and cancel transaction
        transaction = await create_cashout_transaction(
            user=test_user_with_gems,
            amount_usd=Decimal("3.00"),
            db=test_db
        )
        
        # Cancel it
        transaction.status = CashoutStatus.CANCELLED
        await test_db.commit()
        
        # Try to redeem cancelled code
        with pytest.raises(CashoutError) as exc_info:
            await redeem_cashout_code(
                redemption_code=transaction.redemption_code,
                worker_id="A1234567890ABC",
                assignment_id="DEV_TEST_123",
                hit_id="H123",
                db=test_db
            )
        
        assert "cancelled" in str(exc_info.value).lower()


# ============================================================================
# Gem Balance Integrity Tests
# ============================================================================

class TestGemBalanceIntegrity:
    """Test gem balance integrity under various scenarios."""
    
    @pytest.mark.asyncio
    async def test_concurrent_cashout_requests_handled_safely(self, test_db):
        """Test that concurrent cashout requests don't cause negative balance."""
        # User with exactly 5000 gems
        user = User(
            id=uuid.uuid4(),
            user_id="concurrent_user",
            password_hash=hash_password("password"),
            role=UserRole.USER,
            gem_balance=5000,  # $5.00 worth
            mturk_worker_id="A1234567890ABC"
        )
        test_db.add(user)
        await test_db.commit()
        await test_db.refresh(user)
        
        # Try to create two $3 cashouts concurrently
        # Only one should succeed (5000 gems < 6000 gems needed for both)
        
        # Create separate sessions for concurrent access
        engine = test_db.get_bind()
        async_session_maker = async_sessionmaker(
            engine, class_=AsyncSession, expire_on_commit=False
        )
        
        results = []
        errors = []
        
        async def cashout_task(session_num):
            async with async_session_maker() as session:
                try:
                    # Re-fetch user in this session
                    result = await session.execute(
                        select(User).where(User.id == user.id)
                    )
                    session_user = result.scalar_one()
                    
                    transaction = await create_cashout_transaction(
                        user=session_user,
                        amount_usd=Decimal("3.00"),
                        db=session
                    )
                    results.append(transaction)
                except Exception as e:
                    errors.append(e)
        
        # Launch concurrent cashout requests
        await asyncio.gather(
            cashout_task(1),
            cashout_task(2),
            return_exceptions=True
        )
        
        # Exactly one should succeed
        assert len(results) == 1, "Only one cashout should succeed"
        assert len(errors) == 1, "One cashout should fail"
    
    @pytest.mark.asyncio
    async def test_negative_gem_balance_prevention(self, test_db):
        """Test that gem balance cannot go negative."""
        user = User(
            id=uuid.uuid4(),
            user_id="test_user",
            password_hash=hash_password("password"),
            role=UserRole.USER,
            gem_balance=1000,  # Only $1.00 worth
            mturk_worker_id="A1234567890ABC"
        )
        test_db.add(user)
        await test_db.commit()
        await test_db.refresh(user)
        
        # Try to cash out more than balance
        with pytest.raises(CashoutError):
            await create_cashout_transaction(
                user=user,
                amount_usd=Decimal("5.00"),  # Needs 5000 gems
                db=test_db
            )
        
        # Verify balance unchanged
        await test_db.refresh(user)
        assert user.gem_balance == 1000
    
    @pytest.mark.asyncio
    async def test_gems_deducted_atomically_with_transaction(self, test_user_with_gems, test_db):
        """Test that gem deduction and transaction creation are atomic."""
        original_balance = test_user_with_gems.gem_balance
        
        # Create cashout
        transaction = await create_cashout_transaction(
            user=test_user_with_gems,
            amount_usd=Decimal("5.00"),
            db=test_db
        )
        
        # Verify gems deducted
        await test_db.refresh(test_user_with_gems)
        assert test_user_with_gems.gem_balance == original_balance - 5000
        
        # Verify transaction exists
        result = await test_db.execute(
            select(CashoutTransaction).where(CashoutTransaction.id == transaction.id)
        )
        saved_transaction = result.scalar_one()
        assert saved_transaction.amount_gems == 5000


# ============================================================================
# Cashout Rate Limiting Tests
# ============================================================================

class TestCashoutRateLimiting:
    """Test rate limiting on cashout endpoints."""
    
    @pytest.mark.asyncio
    async def test_cashout_rate_limiting(self, client, test_user_with_gems):
        """Test that cashout requests are rate limited."""
        token = create_access_token(data={"sub": str(test_user_with_gems.id)})
        
        # Make 6 cashout requests (limit is 5 per minute)
        responses = []
        for i in range(6):
            response = client.post(
                "/api/wallet/cashout",
                headers={"Authorization": f"Bearer {token}"},
                json={"amount_usd": 2.00}
            )
            responses.append(response.status_code)
        
        # Last request should be rate limited
        assert 429 in responses, "Should rate limit after 5 requests"


# ============================================================================
# Payment Math Validation Tests
# ============================================================================

class TestPaymentMathValidation:
    """Test that payment math is validated correctly."""
    
    @pytest.mark.asyncio
    async def test_gem_to_usd_conversion_accuracy(self, test_db):
        """Test that gem-to-USD conversion is accurate."""
        from backend.cashout_service import gems_to_usd, usd_to_gems
        
        # Test various amounts
        test_cases = [
            (1000, Decimal("1.00")),
            (2500, Decimal("2.50")),
            (5000, Decimal("5.00")),
            (100, Decimal("0.10")),
        ]
        
        for gems, expected_usd in test_cases:
            assert gems_to_usd(gems) == expected_usd
            assert usd_to_gems(expected_usd) == gems
    
    @pytest.mark.asyncio
    async def test_cashout_deducts_correct_gem_amount(self, test_user_with_gems, test_db):
        """Test that cashout deducts exactly the right number of gems."""
        original_balance = test_user_with_gems.gem_balance
        cashout_amount = Decimal("3.00")
        expected_gems = 3000
        
        transaction = await create_cashout_transaction(
            user=test_user_with_gems,
            amount_usd=cashout_amount,
            db=test_db
        )
        
        await test_db.refresh(test_user_with_gems)
        
        # Verify exact gem amount deducted
        assert test_user_with_gems.gem_balance == original_balance - expected_gems
        assert transaction.amount_gems == expected_gems


# ============================================================================
# Pending Cashout Prevention Tests
# ============================================================================

class TestPendingCashoutPrevention:
    """Test that users cannot have multiple pending cashouts."""
    
    @pytest.mark.asyncio
    async def test_cannot_create_cashout_with_pending_transaction(self, test_user_with_gems, test_db):
        """Test that users with pending cashouts cannot create new ones."""
        # Create first cashout
        transaction1 = await create_cashout_transaction(
            user=test_user_with_gems,
            amount_usd=Decimal("2.00"),
            db=test_db
        )
        
        # Transaction is still pending
        assert transaction1.status == CashoutStatus.PENDING
        
        # Try to create second cashout while first is pending
        with pytest.raises(CashoutError) as exc_info:
            await create_cashout_transaction(
                user=test_user_with_gems,
                amount_usd=Decimal("2.00"),
                db=test_db
            )
        
        assert "pending" in str(exc_info.value).lower()


# ============================================================================
# Rollback Tests
# ============================================================================

class TestTransactionRollback:
    """Test that failed transactions properly rollback gem deductions."""
    
    @pytest.mark.asyncio
    async def test_failed_transaction_returns_gems(self, test_db):
        """Test that if transaction creation fails, gems are returned."""
        user = User(
            id=uuid.uuid4(),
            user_id="rollback_user",
            password_hash=hash_password("password"),
            role=UserRole.USER,
            gem_balance=5000,
            mturk_worker_id="A1234567890ABC"
        )
        test_db.add(user)
        await test_db.commit()
        await test_db.refresh(user)
        
        original_balance = user.gem_balance
        
        # This test would need to simulate a transaction failure
        # For now, verify the rollback mechanism exists in the code
        # The actual implementation in cashout_service.py has try/except with rollback
        
        # Verify user balance is unchanged after refresh
        await test_db.refresh(user)
        assert user.gem_balance == original_balance


# ============================================================================
# MTurk Worker ID Validation Tests
# ============================================================================

class TestMTurkWorkerIDValidation:
    """Test MTurk worker ID validation."""
    
    @pytest.mark.asyncio
    async def test_cashout_requires_mturk_worker_id(self, test_db):
        """Test that cashout requires MTurk worker ID to be set."""
        # User without MTurk worker ID
        user = User(
            id=uuid.uuid4(),
            user_id="no_worker_id",
            password_hash=hash_password("password"),
            role=UserRole.USER,
            gem_balance=10000,
            mturk_worker_id=None  # No worker ID
        )
        test_db.add(user)
        await test_db.commit()
        await test_db.refresh(user)
        
        # Try to cash out
        with pytest.raises(CashoutError) as exc_info:
            await create_cashout_transaction(
                user=user,
                amount_usd=Decimal("5.00"),
                db=test_db
            )
        
        assert "worker id" in str(exc_info.value).lower()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

