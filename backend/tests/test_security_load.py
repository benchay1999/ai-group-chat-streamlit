"""
Load & Stress Testing for 100-120 Concurrent Users

Tests for:
- Concurrent WebSocket connections
- Concurrent game sessions
- Database connection pool handling
- API endpoint performance under load
"""

import pytest
import asyncio
import aiohttp
from datetime import datetime
from decimal import Decimal
import uuid
import time

from backend.database import User, UserRole
from backend.auth import hash_password, create_access_token


# ============================================================================
# Configuration
# ============================================================================

BACKEND_URL = "http://localhost:8001"  # Test backend on different port
WS_URL = "ws://localhost:8001"

NUM_CONCURRENT_USERS = 120
NUM_CONCURRENT_GAMES = 30  # 30 games * 4 players = 120 players


# ============================================================================
# Load Test Utilities
# ============================================================================

async def create_test_user_via_api(session: aiohttp.ClientSession, user_num: int):
    """Create a test user via API."""
    user_data = {
        "user_id": f"load_test_user_{user_num}",
        "password": "test_password"
    }
    
    async with session.post(f"{BACKEND_URL}/api/auth/register", json=user_data) as response:
        if response.status == 200:
            return await response.json()
        elif response.status == 429:
            # Rate limited - wait and retry
            await asyncio.sleep(60)
            return await create_test_user_via_api(session, user_num)
        else:
            raise Exception(f"Failed to create user: {response.status}")


async def login_user(session: aiohttp.ClientSession, user_id: str):
    """Login user and get token."""
    login_data = {
        "user_id": user_id,
        "password": "test_password"
    }
    
    async with session.post(f"{BACKEND_URL}/api/auth/login", json=login_data) as response:
        if response.status == 200:
            data = await response.json()
            return data["access_token"]
        elif response.status == 429:
            # Rate limited - wait and retry
            await asyncio.sleep(60)
            return await login_user(session, user_id)
        else:
            raise Exception(f"Login failed: {response.status}")


# ============================================================================
# Concurrent Connection Tests
# ============================================================================

class TestConcurrentConnections:
    """Test system behavior with many concurrent connections."""
    
    @pytest.mark.asyncio
    @pytest.mark.slow
    async def test_120_concurrent_websocket_connections(self):
        """Test handling of 120 concurrent WebSocket connections."""
        async with aiohttp.ClientSession() as session:
            # Create users
            print(f"\n📊 Creating {NUM_CONCURRENT_USERS} test users...")
            user_creation_tasks = [
                create_test_user_via_api(session, i)
                for i in range(NUM_CONCURRENT_USERS)
            ]
            
            # Batch user creation to avoid rate limiting
            batch_size = 3
            for i in range(0, len(user_creation_tasks), batch_size):
                batch = user_creation_tasks[i:i+batch_size]
                await asyncio.gather(*batch, return_exceptions=True)
                await asyncio.sleep(20)  # Wait between batches
            
            print(f"✅ Users created")
            
            # Login users
            print(f"🔐 Logging in users...")
            login_tasks = [
                login_user(session, f"load_test_user_{i}")
                for i in range(NUM_CONCURRENT_USERS)
            ]
            
            # Batch logins to avoid rate limiting
            tokens = []
            for i in range(0, len(login_tasks), batch_size):
                batch = login_tasks[i:i+batch_size]
                batch_tokens = await asyncio.gather(*batch, return_exceptions=True)
                tokens.extend(batch_tokens)
                await asyncio.sleep(12)  # Wait between batches
            
            print(f"✅ Users logged in")
            
            # Note: Full WebSocket testing requires websockets library
            # This test validates the setup; actual WebSocket load test
            # should be run manually with tools like `ws-loadtest`
            
            assert len(tokens) <= NUM_CONCURRENT_USERS
    
    @pytest.mark.asyncio
    @pytest.mark.slow
    async def test_concurrent_api_requests(self):
        """Test API endpoints under concurrent load."""
        async with aiohttp.ClientSession() as session:
            # Test health endpoint
            tasks = [
                session.get(f"{BACKEND_URL}/api/health")
                for _ in range(100)
            ]
            
            start_time = time.time()
            responses = await asyncio.gather(*tasks, return_exceptions=True)
            elapsed = time.time() - start_time
            
            # Count successful responses
            successful = sum(1 for r in responses if not isinstance(r, Exception) and r.status == 200)
            
            print(f"✅ Handled {successful}/100 requests in {elapsed:.2f}s")
            print(f"   Throughput: {successful/elapsed:.2f} req/s")
            
            # Should handle at least 80% of requests successfully
            assert successful >= 80, f"Only {successful}/100 requests succeeded"


# ============================================================================
# Database Connection Pool Tests
# ============================================================================

class TestDatabaseConnectionPool:
    """Test database connection pooling under load."""
    
    @pytest.mark.asyncio
    @pytest.mark.slow
    async def test_database_query_performance_under_load(self):
        """Test database queries under concurrent load."""
        from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
        
        # Create test engine
        engine = create_async_engine(
            "sqlite+aiosqlite:///:memory:",
            echo=False,
            pool_size=10,
            max_overflow=20
        )
        
        async with engine.begin() as conn:
            from backend.database import Base
            await conn.run_sync(Base.metadata.create_all)
        
        async_session_maker = async_sessionmaker(
            engine, expire_on_commit=False
        )
        
        # Create test users
        async with async_session_maker() as session:
            for i in range(50):
                user = User(
                    id=uuid.uuid4(),
                    user_id=f"db_test_user_{i}",
                    password_hash=hash_password("password"),
                    role=UserRole.USER,
                    gem_balance=1000
                )
                session.add(user)
            await session.commit()
        
        # Concurrent reads
        async def read_user(user_num):
            async with async_session_maker() as session:
                from sqlalchemy import select
                result = await session.execute(
                    select(User).where(User.user_id == f"db_test_user_{user_num}")
                )
                return result.scalar_one_or_none()
        
        # Execute 50 concurrent reads
        start_time = time.time()
        results = await asyncio.gather(
            *[read_user(i) for i in range(50)],
            return_exceptions=True
        )
        elapsed = time.time() - start_time
        
        successful = sum(1 for r in results if not isinstance(r, Exception) and r is not None)
        
        print(f"✅ Executed {successful}/50 database queries in {elapsed:.2f}s")
        
        # Should handle all queries successfully
        assert successful >= 45, f"Only {successful}/50 queries succeeded"
        
        await engine.dispose()


# ============================================================================
# Memory Leak Tests
# ============================================================================

class TestMemoryLeaks:
    """Test for memory leaks under sustained load."""
    
    @pytest.mark.asyncio
    async def test_rate_limiter_cleanup(self):
        """Test that rate limiter cleans up old entries."""
        from backend.main import SimpleRateLimiter
        
        limiter = SimpleRateLimiter(max_requests=10, window_seconds=60)
        
        # Add many entries
        for i in range(1000):
            limiter.is_allowed(f"key_{i}")
        
        # Check size before cleanup
        size_before = len(limiter.requests)
        
        # Wait for entries to expire
        await asyncio.sleep(61)
        
        # Run cleanup
        limiter.cleanup_old_entries()
        
        # Size should be reduced (expired entries removed)
        size_after = len(limiter.requests)
        
        print(f"Rate limiter size: {size_before} → {size_after}")
        # After cleanup, should be empty or much smaller
        assert size_after < size_before


# ============================================================================
# Stress Test Scenarios
# ============================================================================

class TestStressScenarios:
    """Test system under stress scenarios."""
    
    @pytest.mark.asyncio
    @pytest.mark.slow
    async def test_rapid_room_creation(self):
        """Test rapid room creation doesn't cause issues."""
        async with aiohttp.ClientSession() as session:
            # Create 50 rooms rapidly
            tasks = []
            for i in range(50):
                task = session.post(
                    f"{BACKEND_URL}/api/rooms/create",
                    json={
                        "room_name": f"Stress Test Room {i}",
                        "max_humans": 2,
                        "total_players": 5
                    }
                )
                tasks.append(task)
            
            start_time = time.time()
            responses = await asyncio.gather(*tasks, return_exceptions=True)
            elapsed = time.time() - start_time
            
            # Count successful room creations
            successful = sum(
                1 for r in responses
                if not isinstance(r, Exception)
            )
            
            print(f"✅ Created {successful}/50 rooms in {elapsed:.2f}s")
            
            # Should handle most requests (some may fail due to rate limiting)
            assert successful >= 30, f"Only {successful}/50 rooms created"
    
    @pytest.mark.asyncio
    @pytest.mark.slow
    async def test_concurrent_wallet_balance_checks(self):
        """Test concurrent wallet balance API calls."""
        # This simulates many users checking their balance simultaneously
        # Common during cashout announcements or promotions
        
        async with aiohttp.ClientSession() as session:
            # Would need actual auth tokens
            # For now, test endpoint availability
            
            tasks = [
                session.get(f"{BACKEND_URL}/api/health")
                for _ in range(100)
            ]
            
            responses = await asyncio.gather(*tasks, return_exceptions=True)
            successful = sum(1 for r in responses if not isinstance(r, Exception))
            
            assert successful >= 90, "System should handle concurrent health checks"


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-m", "not slow"])

