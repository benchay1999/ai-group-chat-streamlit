#!/usr/bin/env python3
"""
Simple Load Testing Script for AI Group Chat Application

Tests concurrent users to verify system can handle 100-120 concurrent users.
Run this before production deployment.

Usage:
    python load_test.py --users 100 --duration 60

Requirements:
    pip install aiohttp asyncio
"""

import asyncio
import aiohttp
import time
import argparse
import statistics
from typing import List, Dict
from dataclasses import dataclass, field


@dataclass
class TestResults:
    """Store test results"""
    total_requests: int = 0
    successful_requests: int = 0
    failed_requests: int = 0
    response_times: List[float] = field(default_factory=list)
    errors: Dict[str, int] = field(default_factory=dict)
    
    @property
    def success_rate(self) -> float:
        if self.total_requests == 0:
            return 0.0
        return (self.successful_requests / self.total_requests) * 100
    
    @property
    def avg_response_time(self) -> float:
        if not self.response_times:
            return 0.0
        return statistics.mean(self.response_times)
    
    @property
    def p95_response_time(self) -> float:
        if not self.response_times:
            return 0.0
        sorted_times = sorted(self.response_times)
        idx = int(len(sorted_times) * 0.95)
        return sorted_times[idx]
    
    @property
    def p99_response_time(self) -> float:
        if not self.response_times:
            return 0.0
        sorted_times = sorted(self.response_times)
        idx = int(len(sorted_times) * 0.99)
        return sorted_times[idx]


class LoadTester:
    """Load testing client"""
    
    def __init__(self, base_url: str, num_users: int, duration: int):
        self.base_url = base_url
        self.num_users = num_users
        self.duration = duration
        self.results = TestResults()
        
    async def test_health_check(self, session: aiohttp.ClientSession) -> bool:
        """Test /health endpoint"""
        start_time = time.time()
        try:
            async with session.get(f"{self.base_url}/health") as response:
                response_time = time.time() - start_time
                self.results.response_times.append(response_time)
                self.results.total_requests += 1
                
                if response.status == 200:
                    self.results.successful_requests += 1
                    return True
                else:
                    self.results.failed_requests += 1
                    self.results.errors[f"HTTP {response.status}"] = self.results.errors.get(f"HTTP {response.status}", 0) + 1
                    return False
        except Exception as e:
            response_time = time.time() - start_time
            self.results.response_times.append(response_time)
            self.results.total_requests += 1
            self.results.failed_requests += 1
            error_type = type(e).__name__
            self.results.errors[error_type] = self.results.errors.get(error_type, 0) + 1
            return False
    
    async def test_register_user(self, session: aiohttp.ClientSession, user_num: int) -> bool:
        """Test user registration endpoint"""
        start_time = time.time()
        try:
            data = {
                "user_id": f"loadtest_user_{user_num}_{int(time.time())}",
                "password": "LoadTest1234!Strong"
            }
            async with session.post(f"{self.base_url}/api/auth/register", json=data) as response:
                response_time = time.time() - start_time
                self.results.response_times.append(response_time)
                self.results.total_requests += 1
                
                if response.status in [200, 201]:
                    self.results.successful_requests += 1
                    return True
                else:
                    self.results.failed_requests += 1
                    self.results.errors[f"HTTP {response.status}"] = self.results.errors.get(f"HTTP {response.status}", 0) + 1
                    return False
        except Exception as e:
            response_time = time.time() - start_time
            self.results.response_times.append(response_time)
            self.results.total_requests += 1
            self.results.failed_requests += 1
            error_type = type(e).__name__
            self.results.errors[error_type] = self.results.errors.get(error_type, 0) + 1
            return False
    
    async def test_api_endpoints(self, session: aiohttp.ClientSession, user_num: int) -> None:
        """Test various API endpoints"""
        # Test health check
        await self.test_health_check(session)
        
        # Test registration
        await self.test_register_user(session, user_num)
    
    async def run_user_simulation(self, user_num: int) -> None:
        """Simulate a single user's activity"""
        async with aiohttp.ClientSession() as session:
            start_time = time.time()
            request_count = 0
            
            while time.time() - start_time < self.duration:
                await self.test_api_endpoints(session, user_num)
                request_count += 1
                
                # Small delay between requests (1 second)
                await asyncio.sleep(1)
    
    async def run(self) -> TestResults:
        """Run load test with multiple concurrent users"""
        print(f"\n{'='*60}")
        print(f"  Load Test Configuration")
        print(f"{'='*60}")
        print(f"  Base URL: {self.base_url}")
        print(f"  Concurrent Users: {self.num_users}")
        print(f"  Test Duration: {self.duration} seconds")
        print(f"{'='*60}\n")
        
        print(f"🚀 Starting load test...")
        start_time = time.time()
        
        # Create tasks for all users
        tasks = [
            self.run_user_simulation(i)
            for i in range(self.num_users)
        ]
        
        # Run all users concurrently
        await asyncio.gather(*tasks)
        
        elapsed_time = time.time() - start_time
        
        # Print results
        self.print_results(elapsed_time)
        
        return self.results
    
    def print_results(self, elapsed_time: float) -> None:
        """Print test results"""
        print(f"\n{'='*60}")
        print(f"  Load Test Results")
        print(f"{'='*60}")
        print(f"\n📊 Request Statistics:")
        print(f"  Total Requests:     {self.results.total_requests:,}")
        print(f"  Successful:         {self.results.successful_requests:,} ({self.results.success_rate:.1f}%)")
        print(f"  Failed:             {self.results.failed_requests:,}")
        print(f"  Requests/Second:    {self.results.total_requests / elapsed_time:.1f}")
        
        print(f"\n⏱️  Response Times:")
        print(f"  Average:            {self.results.avg_response_time*1000:.1f} ms")
        print(f"  95th Percentile:    {self.results.p95_response_time*1000:.1f} ms")
        print(f"  99th Percentile:    {self.results.p99_response_time*1000:.1f} ms")
        
        if self.results.errors:
            print(f"\n❌ Errors:")
            for error_type, count in sorted(self.results.errors.items(), key=lambda x: x[1], reverse=True):
                print(f"  {error_type}: {count}")
        
        print(f"\n⏳ Test Duration: {elapsed_time:.1f} seconds")
        print(f"{'='*60}\n")
        
        # Assessment
        print(f"📋 Assessment:")
        if self.results.success_rate >= 95:
            print(f"  ✅ PASS: Success rate {self.results.success_rate:.1f}% (target: ≥95%)")
        else:
            print(f"  ❌ FAIL: Success rate {self.results.success_rate:.1f}% (target: ≥95%)")
        
        if self.results.p95_response_time < 0.5:
            print(f"  ✅ PASS: p95 response time {self.results.p95_response_time*1000:.0f}ms (target: <500ms)")
        else:
            print(f"  ⚠️  WARN: p95 response time {self.results.p95_response_time*1000:.0f}ms (target: <500ms)")
        
        if self.results.p99_response_time < 1.0:
            print(f"  ✅ PASS: p99 response time {self.results.p99_response_time*1000:.0f}ms (target: <1000ms)")
        else:
            print(f"  ⚠️  WARN: p99 response time {self.results.p99_response_time*1000:.0f}ms (target: <1000ms)")
        
        print()


async def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(description="Load test AI Group Chat application")
    parser.add_argument("--url", default="http://localhost:8000", help="Backend URL")
    parser.add_argument("--users", type=int, default=10, help="Number of concurrent users")
    parser.add_argument("--duration", type=int, default=60, help="Test duration in seconds")
    parser.add_argument("--no-cleanup", action="store_true", help="Don't remind about cleanup after test")
    
    args = parser.parse_args()
    
    # Validate base URL
    base_url = args.url.rstrip('/')
    
    # Run load test
    tester = LoadTester(base_url, args.users, args.duration)
    results = await tester.run()
    
    # Remind about cleanup
    if not args.no_cleanup:
        print("💡 Cleanup Reminder:")
        print("   Load test users remain in the database.")
        print("   To clean them up, run:")
        print("   python3 cleanup_loadtest_users.py --dry-run  # Preview")
        print("   python3 cleanup_loadtest_users.py            # Delete")
        print()
    
    # Exit with appropriate code
    if results.success_rate >= 95:
        print("✅ Load test PASSED\n")
        exit(0)
    else:
        print("❌ Load test FAILED\n")
        exit(1)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n\n⚠️  Load test interrupted by user\n")
        exit(130)

