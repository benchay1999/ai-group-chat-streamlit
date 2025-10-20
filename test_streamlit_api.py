#!/usr/bin/env python3
"""
Simple test script to verify Streamlit REST API endpoints are working.
Run this after starting the backend to test the new endpoints.
"""

import requests
import json
import time

BACKEND_URL = "http://localhost:8000"
TEST_ROOM = "test-streamlit-room"
TEST_PLAYER = "TestPlayer"


def print_section(title):
    """Print a section header."""
    print(f"\n{'=' * 60}")
    print(f"  {title}")
    print('=' * 60)


def test_health():
    """Test health endpoint."""
    print_section("Testing Health Endpoint")
    try:
        response = requests.get(f"{BACKEND_URL}/health", timeout=5)
        print(f"Status Code: {response.status_code}")
        print(f"Response: {response.json()}")
        return response.status_code == 200
    except Exception as e:
        print(f"❌ Error: {e}")
        return False


def test_join_room():
    """Test joining a room."""
    print_section("Testing Join Room Endpoint")
    try:
        response = requests.post(
            f"{BACKEND_URL}/api/rooms/{TEST_ROOM}/join",
            json={"player_id": TEST_PLAYER},
            timeout=5
        )
        print(f"Status Code: {response.status_code}")
        data = response.json()
        print(f"Response: {json.dumps(data, indent=2)}")
        return response.status_code == 200 and data.get('success')
    except Exception as e:
        print(f"❌ Error: {e}")
        return False


def test_get_state():
    """Test getting room state."""
    print_section("Testing Get Room State Endpoint")
    try:
        response = requests.get(
            f"{BACKEND_URL}/api/rooms/{TEST_ROOM}/state",
            params={"player_id": TEST_PLAYER},
            timeout=5
        )
        print(f"Status Code: {response.status_code}")
        data = response.json()
        
        if data.get('exists'):
            print(f"✅ Room exists: {TEST_ROOM}")
            print(f"Phase: {data.get('phase')}")
            print(f"Round: {data.get('round')}")
            print(f"Topic: {data.get('topic')}")
            print(f"Players: {len(data.get('players', []))}")
            print(f"Chat messages: {len(data.get('chat_history', []))}")
        else:
            print(f"❌ Room does not exist")
            
        return response.status_code == 200 and data.get('exists')
    except Exception as e:
        print(f"❌ Error: {e}")
        return False


def test_send_message():
    """Test sending a message."""
    print_section("Testing Send Message Endpoint")
    try:
        message = "Hello from test script!"
        response = requests.post(
            f"{BACKEND_URL}/api/rooms/{TEST_ROOM}/message",
            json={"player_id": TEST_PLAYER, "message": message},
            timeout=5
        )
        print(f"Status Code: {response.status_code}")
        data = response.json()
        print(f"Response: {json.dumps(data, indent=2)}")
        
        if data.get('success'):
            print(f"✅ Message sent successfully")
        else:
            print(f"⚠️ Message not sent: {data.get('error', 'Unknown error')}")
            
        return response.status_code == 200
    except Exception as e:
        print(f"❌ Error: {e}")
        return False


def test_get_state_with_message():
    """Test getting room state after sending message."""
    print_section("Testing Get Room State (After Message)")
    try:
        # Wait a moment for message to be processed
        time.sleep(1)
        
        response = requests.get(
            f"{BACKEND_URL}/api/rooms/{TEST_ROOM}/state",
            params={"player_id": TEST_PLAYER},
            timeout=5
        )
        data = response.json()
        
        print(f"Status Code: {response.status_code}")
        print(f"Chat messages: {len(data.get('chat_history', []))}")
        
        if data.get('chat_history'):
            print("\nRecent messages:")
            for msg in data['chat_history'][-3:]:  # Show last 3 messages
                print(f"  - {msg['sender']}: {msg['message']}")
        
        return response.status_code == 200
    except Exception as e:
        print(f"❌ Error: {e}")
        return False


def test_typing_status():
    """Test sending typing status."""
    print_section("Testing Typing Status Endpoint")
    try:
        # Start typing
        response = requests.post(
            f"{BACKEND_URL}/api/rooms/{TEST_ROOM}/typing",
            json={"player_id": TEST_PLAYER, "status": "start"},
            timeout=5
        )
        print(f"Start typing - Status Code: {response.status_code}")
        print(f"Response: {response.json()}")
        
        time.sleep(0.5)
        
        # Stop typing
        response = requests.post(
            f"{BACKEND_URL}/api/rooms/{TEST_ROOM}/typing",
            json={"player_id": TEST_PLAYER, "status": "stop"},
            timeout=5
        )
        print(f"Stop typing - Status Code: {response.status_code}")
        print(f"Response: {response.json()}")
        
        return response.status_code == 200
    except Exception as e:
        print(f"❌ Error: {e}")
        return False


def main():
    """Run all tests."""
    print("\n🧪 Testing Streamlit REST API Endpoints")
    print(f"Backend URL: {BACKEND_URL}")
    print(f"Test Room: {TEST_ROOM}")
    print(f"Test Player: {TEST_PLAYER}")
    
    results = []
    
    # Run tests
    results.append(("Health Check", test_health()))
    
    if not results[-1][1]:
        print("\n❌ Backend is not running. Please start it first:")
        print("   cd backend && uvicorn main:app --reload")
        return
    
    results.append(("Join Room", test_join_room()))
    results.append(("Get State", test_get_state()))
    results.append(("Send Message", test_send_message()))
    results.append(("Get State (After Message)", test_get_state_with_message()))
    results.append(("Typing Status", test_typing_status()))
    
    # Print summary
    print_section("Test Summary")
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for test_name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status} - {test_name}")
    
    print(f"\nTotal: {passed}/{total} tests passed")
    
    if passed == total:
        print("\n🎉 All tests passed! The Streamlit API is working correctly.")
        print("\nYou can now run the Streamlit app:")
        print("   streamlit run streamlit_app.py")
    else:
        print(f"\n⚠️ Some tests failed. Please check the backend logs.")


if __name__ == "__main__":
    main()

