"""
Authentication & Authorization Security Tests

Tests for:
- JWT token security (expiration, tampering, replay)
- MTurk worker registration security
- Role-based access control
- Rate limiting on auth endpoints
"""

import pytest
import time
from datetime import datetime, timedelta
from jose import jwt
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
import uuid

from backend.main import app
from backend.database import Base, User, UserRole, TokenBlacklist
from backend.auth import (
    hash_password, create_access_token, decode_access_token,
    JWT_SECRET_KEY, JWT_ALGORITHM
)


# Test Database Setup
TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"

@pytest.fixture
async def test_db():
    """Create a test database for each test."""
    engine = create_async_engine(TEST_DATABASE_URL, echo=False)
    
    # Create tables
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    # Create session maker
    async_session_maker = async_sessionmaker(
        engine, class_=AsyncSession, expire_on_commit=False
    )
    
    async with async_session_maker() as session:
        yield session
    
    # Cleanup
    await engine.dispose()


@pytest.fixture
def client():
    """Create test client."""
    return TestClient(app)


@pytest.fixture
async def test_user(test_db: AsyncSession):
    """Create a test user."""
    user = User(
        id=uuid.uuid4(),
        user_id="test_user",
        password_hash=hash_password("test_password"),
        role=UserRole.USER
    )
    test_db.add(user)
    await test_db.commit()
    await test_db.refresh(user)
    return user


@pytest.fixture
async def test_admin(test_db: AsyncSession):
    """Create a test admin user."""
    admin = User(
        id=uuid.uuid4(),
        user_id="test_admin",
        password_hash=hash_password("admin_password"),
        role=UserRole.ADMIN
    )
    test_db.add(admin)
    await test_db.commit()
    await test_db.refresh(admin)
    return admin


# ============================================================================
# JWT Token Security Tests
# ============================================================================

class TestJWTSecurity:
    """Test JWT token security mechanisms."""
    
    def test_expired_token_rejection(self, client):
        """Test that expired tokens are rejected."""
        # Create an expired token
        expired_token = create_access_token(
            data={"sub": str(uuid.uuid4())},
            expires_delta=timedelta(seconds=-1)  # Expired 1 second ago
        )
        
        # Try to use expired token
        response = client.get(
            "/api/auth/me",
            headers={"Authorization": f"Bearer {expired_token}"}
        )
        
        assert response.status_code == 401
        assert "expired" in response.json()["detail"].lower() or "invalid" in response.json()["detail"].lower()
    
    def test_invalid_signature_detection(self, client):
        """Test that tokens with invalid signatures are rejected."""
        # Create token with wrong secret key
        fake_token = jwt.encode(
            {"sub": str(uuid.uuid4()), "exp": datetime.utcnow() + timedelta(hours=1)},
            "wrong-secret-key",
            algorithm=JWT_ALGORITHM
        )
        
        # Try to use fake token
        response = client.get(
            "/api/auth/me",
            headers={"Authorization": f"Bearer {fake_token}"}
        )
        
        assert response.status_code == 401
        assert "invalid" in response.json()["detail"].lower()
    
    def test_token_tampering_detection(self, client):
        """Test that tampered tokens are detected."""
        # Create valid token
        valid_token = create_access_token(data={"sub": str(uuid.uuid4())})
        
        # Tamper with token (flip a bit in the middle)
        tampered_token = valid_token[:-10] + "0" * 10
        
        # Try to use tampered token
        response = client.get(
            "/api/auth/me",
            headers={"Authorization": f"Bearer {tampered_token}"}
        )
        
        assert response.status_code == 401
    
    @pytest.mark.asyncio
    async def test_token_replay_after_logout(self, client, test_user, test_db):
        """Test that tokens cannot be reused after logout."""
        # Login
        login_response = client.post(
            "/api/auth/login",
            json={"user_id": "test_user", "password": "test_password"}
        )
        assert login_response.status_code == 200
        token = login_response.json()["access_token"]
        
        # Use token (should work)
        response = client.get(
            "/api/auth/me",
            headers={"Authorization": f"Bearer {token}"}
        )
        assert response.status_code == 200
        
        # Logout (blacklist token)
        logout_response = client.post(
            "/api/auth/logout",
            headers={"Authorization": f"Bearer {token}"}
        )
        assert logout_response.status_code == 200
        
        # Try to reuse token after logout (should fail)
        response = client.get(
            "/api/auth/me",
            headers={"Authorization": f"Bearer {token}"}
        )
        assert response.status_code == 401


# ============================================================================
# MTurk Worker Registration Security Tests
# ============================================================================

class TestMTurkRegistrationSecurity:
    """Test MTurk worker registration security."""
    
    def test_duplicate_worker_id_prevention(self, client):
        """Test that duplicate worker IDs cannot be registered for same assignment."""
        worker_data = {
            "worker_id": "A1234567890ABC",
            "assignment_id": "31234567890123456789012345678901",
            "hit_id": "H1234567890"
        }
        
        # First registration (should succeed)
        response1 = client.post("/api/auth/mturk-register", json=worker_data)
        # May succeed or fail depending on validation, but should be consistent
        
        # Second registration with same assignment_id (should fail)
        response2 = client.post("/api/auth/mturk-register", json=worker_data)
        
        # Either both fail validation, or second fails with duplicate error
        if response1.status_code == 200:
            assert response2.status_code == 409  # Conflict - duplicate assignment
        else:
            # Both should fail with same validation error
            assert response1.status_code == response2.status_code
    
    def test_invalid_worker_id_format_rejection(self, client):
        """Test that invalid worker ID formats are rejected."""
        invalid_worker_ids = [
            "INVALID",  # Too short
            "B1234567890ABC",  # Doesn't start with 'A'
            "a1234567890abc",  # Lowercase
            "A123",  # Too short
            "A12345678901234567890",  # Too long
            "",  # Empty
            "A123456789@ABC",  # Special characters
        ]
        
        for invalid_id in invalid_worker_ids:
            response = client.post(
                "/api/auth/mturk-register",
                json={
                    "worker_id": invalid_id,
                    "assignment_id": "31234567890123456789012345678901",
                    "hit_id": "H1234567890"
                }
            )
            assert response.status_code == 400, f"Should reject invalid worker_id: {invalid_id}"
    
    def test_invalid_assignment_id_format_rejection(self, client):
        """Test that invalid assignment ID formats are rejected."""
        invalid_assignment_ids = [
            "INVALID",  # Doesn't start with '3'
            "2123456789",  # Wrong first digit
            "3",  # Too short
            "",  # Empty
            "31234",  # Too short
        ]
        
        for invalid_id in invalid_assignment_ids:
            response = client.post(
                "/api/auth/mturk-register",
                json={
                    "worker_id": "A1234567890ABC",
                    "assignment_id": invalid_id,
                    "hit_id": "H1234567890"
                }
            )
            assert response.status_code == 400, f"Should reject invalid assignment_id: {invalid_id}"
    
    def test_preview_mode_handling(self, client):
        """Test that preview mode doesn't create accounts."""
        response = client.post(
            "/api/auth/mturk-register",
            json={
                "worker_id": "A1234567890ABC",
                "assignment_id": "ASSIGNMENT_ID_NOT_AVAILABLE",
                "hit_id": "H1234567890"
            }
        )
        
        assert response.status_code == 200
        assert response.json()["preview_mode"] is True
        assert "access_token" not in response.json()
    
    def test_rate_limiting_on_mturk_register(self, client):
        """Test rate limiting prevents registration spam."""
        # Valid worker data
        worker_data_template = {
            "worker_id": "A1234567890ABC",
            "hit_id": "H1234567890"
        }
        
        # Make 11 requests (limit is 10 per minute)
        responses = []
        for i in range(11):
            worker_data = worker_data_template.copy()
            # Use unique assignment IDs
            worker_data["assignment_id"] = f"3{str(i).zfill(30)}"
            
            response = client.post("/api/auth/mturk-register", json=worker_data)
            responses.append(response.status_code)
        
        # At least one should be rate limited (429)
        assert 429 in responses, "Rate limiting should trigger after 10 requests"


# ============================================================================
# Role-Based Access Control Tests
# ============================================================================

class TestRoleBasedAccessControl:
    """Test that role-based access control is properly enforced."""
    
    @pytest.mark.asyncio
    async def test_non_admin_cannot_access_admin_endpoints(self, client, test_user):
        """Test that regular users cannot access admin endpoints."""
        # Create token for regular user
        token = create_access_token(data={"sub": str(test_user.id)})
        
        # Try to access admin endpoint
        admin_endpoints = [
            "/api/admin/sessions",
            "/api/admin/users",
        ]
        
        for endpoint in admin_endpoints:
            response = client.get(
                endpoint,
                headers={"Authorization": f"Bearer {token}"}
            )
            assert response.status_code == 403, f"Non-admin should not access {endpoint}"
    
    @pytest.mark.asyncio
    async def test_admin_can_access_admin_endpoints(self, client, test_admin):
        """Test that admin users can access admin endpoints."""
        # Create token for admin
        token = create_access_token(data={"sub": str(test_admin.id)})
        
        # Access admin endpoint
        response = client.get(
            "/api/admin/sessions",
            headers={"Authorization": f"Bearer {token}"}
        )
        # Should succeed (200) or have different error (not 403)
        assert response.status_code != 403
    
    @pytest.mark.asyncio
    async def test_user_cannot_access_other_user_wallet(self, client, test_user, test_db):
        """Test that users cannot access other users' wallet data."""
        # Create second user
        other_user = User(
            id=uuid.uuid4(),
            user_id="other_user",
            password_hash=hash_password("password"),
            role=UserRole.USER,
            gem_balance=1000
        )
        test_db.add(other_user)
        await test_db.commit()
        
        # Create token for test_user
        token = create_access_token(data={"sub": str(test_user.id)})
        
        # Try to access wallet (should get test_user's wallet, not other_user's)
        response = client.get(
            "/api/wallet/balance",
            headers={"Authorization": f"Bearer {token}"}
        )
        
        assert response.status_code == 200
        # Verify it's test_user's wallet (gem_balance should be 0, not 1000)
        assert response.json()["gem_balance"] != 1000


# ============================================================================
# Login Rate Limiting Tests
# ============================================================================

class TestLoginRateLimiting:
    """Test rate limiting on login endpoint."""
    
    def test_login_rate_limiting_prevents_brute_force(self, client):
        """Test that login attempts are rate limited to prevent brute-force."""
        # Attempt 6 logins (limit is 5 per minute)
        responses = []
        for i in range(6):
            response = client.post(
                "/api/auth/login",
                json={
                    "user_id": "nonexistent_user",
                    "password": f"wrong_password_{i}"
                }
            )
            responses.append(response.status_code)
        
        # Last request should be rate limited
        assert responses[-1] == 429, "6th login attempt should be rate limited"
    
    def test_registration_rate_limiting(self, client):
        """Test that registration attempts are rate limited."""
        # Attempt 4 registrations (limit is 3 per minute)
        responses = []
        for i in range(4):
            response = client.post(
                "/api/auth/register",
                json={
                    "user_id": f"test_user_{i}",
                    "password": "password123"
                }
            )
            responses.append(response.status_code)
        
        # Last request should be rate limited
        assert responses[-1] == 429, "4th registration attempt should be rate limited"


# ============================================================================
# Token Blacklist Tests
# ============================================================================

class TestTokenBlacklist:
    """Test token blacklisting functionality."""
    
    @pytest.mark.asyncio
    async def test_blacklisted_token_is_rejected(self, client, test_user, test_db):
        """Test that blacklisted tokens cannot be used."""
        # Create token
        token = create_access_token(data={"sub": str(test_user.id)})
        
        # Blacklist it
        from backend.auth import decode_access_token
        import hashlib
        
        payload = decode_access_token(token)
        token_hash = hashlib.sha256(token.encode()).hexdigest()
        
        blacklist_entry = TokenBlacklist(
            id=uuid.uuid4(),
            token=token_hash,
            user_id=test_user.id,
            blacklisted_at=datetime.utcnow(),
            expires_at=payload["exp"],
            reason="test"
        )
        test_db.add(blacklist_entry)
        await test_db.commit()
        
        # Try to use blacklisted token
        response = client.get(
            "/api/auth/me",
            headers={"Authorization": f"Bearer {token}"}
        )
        
        assert response.status_code == 401


# ============================================================================
# Password Security Tests
# ============================================================================

class TestPasswordSecurity:
    """Test password hashing and verification."""
    
    def test_password_hashing_is_strong(self):
        """Test that passwords are hashed with Argon2."""
        password = "test_password_123"
        hashed = hash_password(password)
        
        # Argon2 hashes start with $argon2
        assert hashed.startswith("$argon2"), "Should use Argon2 hashing"
        
        # Hash should be different each time (salted)
        hashed2 = hash_password(password)
        assert hashed != hashed2, "Hashes should be salted (different each time)"
    
    def test_long_password_support(self):
        """Test that long passwords are supported (Argon2 has no length limit)."""
        # bcrypt has 72-byte limit, Argon2 doesn't
        long_password = "a" * 200
        hashed = hash_password(long_password)
        
        from backend.auth import verify_password
        assert verify_password(long_password, hashed)
    
    def test_password_verification_fails_for_wrong_password(self):
        """Test that password verification correctly rejects wrong passwords."""
        password = "correct_password"
        hashed = hash_password(password)
        
        from backend.auth import verify_password
        assert not verify_password("wrong_password", hashed)


# ============================================================================
# Cross-User Security Tests
# ============================================================================

class TestCrossUserSecurity:
    """Test that users cannot access each other's resources."""
    
    @pytest.mark.asyncio
    async def test_user_cannot_use_another_users_token(self, client, test_user, test_db):
        """Test that User A's token cannot access User B's resources."""
        # Create User B
        user_b = User(
            id=uuid.uuid4(),
            user_id="user_b",
            password_hash=hash_password("password"),
            role=UserRole.USER
        )
        test_db.add(user_b)
        await test_db.commit()
        
        # Create token for User A
        token_a = create_access_token(data={"sub": str(test_user.id)})
        
        # Try to access user info (should return User A, not User B)
        response = client.get(
            "/api/auth/me",
            headers={"Authorization": f"Bearer {token_a}"}
        )
        
        assert response.status_code == 200
        assert response.json()["user_id"] == "test_user", "Should return User A's info"
        assert response.json()["user_id"] != "user_b", "Should not return User B's info"


# ============================================================================
# SQL Injection Tests
# ============================================================================

class TestSQLInjectionPrevention:
    """Test that SQL injection attempts are prevented."""
    
    def test_sql_injection_in_login(self, client):
        """Test SQL injection attempts in login endpoint."""
        # Common SQL injection payloads
        injection_attempts = [
            "admin' OR '1'='1",
            "admin'; DROP TABLE users; --",
            "' OR 1=1 --",
            "admin'--",
        ]
        
        for payload in injection_attempts:
            response = client.post(
                "/api/auth/login",
                json={
                    "user_id": payload,
                    "password": "any_password"
                }
            )
            
            # Should get authentication error, not SQL error
            # Status could be 401 (auth failed) or 429 (rate limited)
            assert response.status_code in [401, 429]
            assert "sql" not in response.json()["detail"].lower()
    
    def test_sql_injection_in_mturk_worker_id(self, client):
        """Test SQL injection in MTurk worker ID."""
        response = client.post(
            "/api/auth/mturk-register",
            json={
                "worker_id": "A1234'; DROP TABLE users; --",
                "assignment_id": "31234567890123456789012345678901",
                "hit_id": "H1234567890"
            }
        )
        
        # Should fail validation, not cause SQL error
        assert response.status_code == 400
        assert "invalid" in response.json()["detail"].lower()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

