#!/usr/bin/env python3
"""
Timer Synchronization Test Script

Tests the timer sync fixes to ensure players receive accurate timer updates.

Test Cases:
1. Mid-Phase Join: Player joining mid-phase receives correct remaining time
2. Timer Sync Consistency: Timer sync messages arrive at regular intervals

Usage:
    # Make sure backend is running on localhost:8000
    python test_timer_sync.py
"""

import asyncio
import time
import json
from typing import List, Dict
import websockets
import requests

# Configuration
BACKEND_URL = "http://localhost:8000"
WS_URL = "ws://localhost:8000"

class TimerSyncTester:
    """Test timer synchronization across multiple clients"""
    
    def __init__(self):
        self.room_code = None
        self.player_ids = []
        self.websockets = []
        self.timer_readings = []
        
    async def create_room(self) -> str:
        """Create a new room"""
        print("📝 Creating test room...")
        response = requests.post(
            f"{BACKEND_URL}/api/rooms/create",
            json={
                "max_humans": 1,  # Single player room (no auth required)
                "total_players": 5,  # 1 human + 4 AI
                "discussion_duration": 60,  # Short duration for testing
                "voting_duration": 30,
                "language": "english",
                "stake_percentage": 0
            }
        )
        
        if response.status_code == 200:
            data = response.json()
            if data.get('success'):
                self.room_code = data['room_code']
                print(f"✅ Room created: {self.room_code}")
                return self.room_code
            else:
                print(f"❌ Failed to create room: {data.get('error', 'Unknown error')}")
                return None
        else:
            print(f"❌ Failed to create room: {response.status_code}")
            print(response.text)
            return None
    
    async def connect_player(self, player_id: str) -> websockets.WebSocketClientProtocol:
        """Connect a player to the room via WebSocket"""
        print(f"🔌 Connecting player: {player_id}")
        
        # First join via REST API
        response = requests.post(
            f"{BACKEND_URL}/api/rooms/{self.room_code}/join",
            json={"player_id": player_id}
        )
        
        if response.status_code != 200:
            print(f"❌ Failed to join room: {response.status_code}")
            return None
        
        # Connect WebSocket
        ws_uri = f"{WS_URL}/ws/{self.room_code}/{player_id}"
        ws = await websockets.connect(ws_uri)
        
        self.player_ids.append(player_id)
        self.websockets.append(ws)
        
        print(f"✅ Player {player_id} connected")
        return ws
    
    async def receive_initial_state(self, ws: websockets.WebSocketClientProtocol, player_id: str):
        """Receive and log initial state messages"""
        print(f"📥 Receiving initial state for {player_id}...")
        timer_received = False
        
        timeout = time.time() + 5  # 5 second timeout
        while time.time() < timeout and not timer_received:
            try:
                message = await asyncio.wait_for(ws.recv(), timeout=1.0)
                data = json.loads(message)
                
                if data['type'] == 'timer_sync':
                    print(f"   ⏱️ {player_id} received timer_sync: {data['time_remaining']}s in {data['phase']}")
                    timer_received = True
                    return data['time_remaining']
                elif data['type'] == 'phase':
                    print(f"   📊 {player_id} received phase: {data['phase']}")
                    if 'discussion_duration' in data:
                        print(f"      (discussion_duration: {data['discussion_duration']})")
                    if 'voting_duration' in data:
                        print(f"      (voting_duration: {data['voting_duration']})")
            except asyncio.TimeoutError:
                continue
        
        if not timer_received:
            print(f"   ⚠️ {player_id} did not receive timer_sync within timeout")
        
        return None
    
    async def monitor_timer_sync(self, ws: websockets.WebSocketClientProtocol, player_id: str, duration: int):
        """Monitor timer sync messages for a player"""
        readings = []
        start_time = time.time()
        
        print(f"👀 Monitoring {player_id} for {duration}s...")
        
        while time.time() - start_time < duration:
            try:
                message = await asyncio.wait_for(ws.recv(), timeout=1.0)
                data = json.loads(message)
                
                if data['type'] == 'timer_sync':
                    elapsed = time.time() - start_time
                    print(f"   ⏱️ [{elapsed:.1f}s] {player_id}: {data['time_remaining']}s remaining")
                    readings.append({
                        'player': player_id,
                        'timestamp': time.time(),
                        'elapsed': elapsed,
                        'remaining': data['time_remaining'],
                        'phase': data['phase']
                    })
            except asyncio.TimeoutError:
                continue
        
        return readings
    
    async def test_mid_phase_join(self):
        """Test Case 1: Player joining mid-phase gets correct timer"""
        print("\n" + "="*80)
        print("TEST 1: Player Joining Mid-Phase")
        print("="*80)
        
        # Create room
        await self.create_room()
        if not self.room_code:
            print("❌ Test failed: Could not create room")
            return False
        
        # Connect first player
        ws1 = await self.connect_player("TestPlayer1")
        if not ws1:
            print("❌ Test failed: Could not connect Player 1")
            return False
        
        # Get initial timer
        timer1 = await self.receive_initial_state(ws1, "TestPlayer1")
        print(f"✅ Player 1 initial timer: {timer1}s")
        
        # Wait 10 seconds
        print("\n⏳ Waiting 10 seconds...")
        await asyncio.sleep(10)
        
        # Connect second player mid-phase
        print("\n🔌 Connecting Player 2 mid-phase...")
        ws2 = await self.connect_player("TestPlayer2")
        if not ws2:
            print("❌ Test failed: Could not connect Player 2")
            return False
        
        timer2 = await self.receive_initial_state(ws2, "TestPlayer2")
        
        # Verify timer2 is approximately 10 seconds less than timer1
        expected_timer2 = timer1 - 10
        tolerance = 3  # Allow 3 second tolerance
        
        print(f"\n📊 Test Results:")
        print(f"   Player 1 initial timer: {timer1}s")
        print(f"   Player 2 timer (after 10s): {timer2}s")
        print(f"   Expected Player 2 timer: {expected_timer2}s ± {tolerance}s")
        
        if timer2 is None:
            print("❌ FAIL: Player 2 did not receive timer_sync")
            return False
        elif abs(timer2 - expected_timer2) <= tolerance:
            print(f"✅ PASS: Timer difference within tolerance ({abs(timer2 - expected_timer2)}s)")
            return True
        else:
            print(f"❌ FAIL: Timer difference too large ({abs(timer2 - expected_timer2)}s > {tolerance}s)")
            return False
    
    async def test_multi_player_sync(self):
        """Test Case 2: Single player monitoring timer sync over time"""
        print("\n" + "="*80)
        print("TEST 2: Timer Synchronization Consistency")
        print("="*80)
        
        # Create room
        await self.create_room()
        if not self.room_code:
            print("❌ Test failed: Could not create room")
            return False
        
        # Connect 1 player and monitor over time
        print("🔌 Connecting player...")
        ws1 = await self.connect_player("Player1")
        
        if not ws1:
            print("❌ Test failed: Could not connect player")
            return False
        
        # Get initial timer
        timer1 = await self.receive_initial_state(ws1, "Player1")
        
        print(f"\n📊 Initial Timer Reading:")
        print(f"   Player 1: {timer1}s")
        
        # Monitor player for 20 seconds
        print("\n👀 Monitoring timer sync for 20 seconds...")
        readings = await self.monitor_timer_sync(ws1, "Player1", 20)
        
        # Analyze consistency of server sync messages
        print("\n📊 Timer Sync Analysis:")
        
        if len(readings) == 0:
            print("❌ FAIL: No timer sync messages received")
            return False
        
        print(f"   Received {len(readings)} timer sync messages")
        
        # Check that timer decreases consistently
        # Should receive sync every ~5 seconds
        sync_intervals = []
        for i in range(1, len(readings)):
            interval = readings[i]['elapsed'] - readings[i-1]['elapsed']
            sync_intervals.append(interval)
            print(f"   Sync {i}: {readings[i]['remaining']}s (interval: {interval:.1f}s)")
        
        # Average interval should be around 5 seconds
        if sync_intervals:
            avg_interval = sum(sync_intervals) / len(sync_intervals)
            print(f"\n   Average sync interval: {avg_interval:.1f}s")
            
            # Check if average is close to 5 seconds (±2 seconds tolerance)
            if 3 <= avg_interval <= 7:
                print(f"✅ PASS: Timer sync interval is consistent (~5s)")
                
                # Also check that timer decreases properly
                timer_diffs = []
                for i in range(1, len(readings)):
                    diff = readings[i-1]['remaining'] - readings[i]['remaining']
                    timer_diffs.append(diff)
                
                if timer_diffs:
                    avg_diff = sum(timer_diffs) / len(timer_diffs)
                    print(f"   Average timer decrease: {avg_diff:.1f}s per sync")
                    
                    # Should be approximately equal to sync interval
                    if 3 <= avg_diff <= 7:
                        print(f"✅ PASS: Timer decreases correctly")
                        return True
                    else:
                        print(f"❌ FAIL: Timer decrease inconsistent")
                        return False
                
                return True
            else:
                print(f"❌ FAIL: Sync interval inconsistent ({avg_interval:.1f}s)")
                return False
        else:
            print("❌ FAIL: Not enough sync messages to analyze")
            return False
    
    async def cleanup(self):
        """Close all WebSocket connections"""
        print("\n🧹 Cleaning up...")
        for ws in self.websockets:
            try:
                await ws.close()
            except:
                pass

async def main():
    """Run all timer sync tests"""
    print("🧪 Timer Synchronization Test Suite")
    print("="*80)
    
    tester = TimerSyncTester()
    
    try:
        # Test 1: Mid-phase join
        result1 = await tester.test_mid_phase_join()
        await tester.cleanup()
        
        # Reset for next test
        tester = TimerSyncTester()
        
        # Test 2: Multi-player sync
        result2 = await tester.test_multi_player_sync()
        await tester.cleanup()
        
        # Summary
        print("\n" + "="*80)
        print("TEST SUMMARY")
        print("="*80)
        print(f"Test 1 (Mid-Phase Join): {'✅ PASS' if result1 else '❌ FAIL'}")
        print(f"Test 2 (Timer Sync Consistency): {'✅ PASS' if result2 else '❌ FAIL'}")
        print()
        
        if result1 and result2:
            print("🎉 All tests passed!")
            return 0
        else:
            print("❌ Some tests failed")
            return 1
            
    except Exception as e:
        print(f"\n❌ Test error: {e}")
        import traceback
        traceback.print_exc()
        return 1
    finally:
        await tester.cleanup()

if __name__ == "__main__":
    exit_code = asyncio.run(main())
    exit(exit_code)

