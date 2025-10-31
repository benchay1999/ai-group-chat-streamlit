#!/usr/bin/env python3
"""
Test script to verify the robust environment configuration
"""

import sys

print("=" * 70)
print("  Testing Robust Environment Configuration")
print("=" * 70)

try:
    # This import will trigger all the diagnostic output
    from env_config import (
        get_cashout_hit_id,
        is_cashout_configured,
        get_config_status,
        CASHOUT_HIT_ID,
        ENV_FILE_PATH
    )
    
    print("\n✅ env_config module imported successfully!\n")
    
    # Test 1: Check configuration status
    print("TEST 1: Configuration Status")
    print("-" * 70)
    status = get_config_status()
    for key, value in status.items():
        print(f"   {key}: {value}")
    
    # Test 2: Check if cashout is configured
    print("\nTEST 2: Cashout Configuration Check")
    print("-" * 70)
    if is_cashout_configured():
        print("   ✅ Cashout is configured!")
    else:
        print("   ❌ Cashout is NOT configured!")
    
    # Test 3: Try to get HIT ID
    print("\nTEST 3: Get Cashout HIT ID")
    print("-" * 70)
    try:
        hit_id = get_cashout_hit_id()
        print(f"   ✅ HIT ID retrieved: {hit_id}")
    except ValueError as e:
        print(f"   ❌ Error: {e}")
    
    # Test 4: Direct access to cached value
    print("\nTEST 4: Cached Value Access")
    print("-" * 70)
    if CASHOUT_HIT_ID:
        print(f"   ✅ Cached CASHOUT_HIT_ID: {CASHOUT_HIT_ID}")
    else:
        print(f"   ❌ Cached CASHOUT_HIT_ID is None or empty")
    
    print("\n" + "=" * 70)
    if is_cashout_configured():
        print("✅ ALL TESTS PASSED - Configuration is working correctly!")
        print("=" * 70)
        print("\n✅ You can now start the backend server:")
        print("   cd /home/wschay/ai-group-chat-streamlit")
        print("   uvicorn backend.main:app --host 0.0.0.0 --port 8000 --reload")
        sys.exit(0)
    else:
        print("❌ CONFIGURATION INCOMPLETE - Please fix the issues above")
        print("=" * 70)
        print(f"\n📋 Action Items:")
        print(f"   1. Ensure .env file exists at: {ENV_FILE_PATH}")
        print(f"   2. Add CASHOUT_HIT_ID to .env file")
        print(f"   3. Run: python3 backend/create_standing_hit.py")
        sys.exit(1)
    
except Exception as e:
    print(f"\n❌ ERROR: Failed to import env_config module!")
    print(f"   {type(e).__name__}: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

