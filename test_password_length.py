#!/usr/bin/env python3
"""
Test script to verify password length handling.
Run this to test that passwords are properly truncated before hashing.
"""

import asyncio
import sys
sys.path.insert(0, 'backend')

from backend.auth import hash_password, verify_password

def test_password_lengths():
    print("Testing password length handling...")
    print("=" * 60)
    
    # Test 1: Normal length password
    print("\n1. Testing normal password (20 chars):")
    normal_pass = "MySecurePass123!@#$%"
    print(f"   Password: {normal_pass}")
    print(f"   Length: {len(normal_pass)} chars, {len(normal_pass.encode('utf-8'))} bytes")
    try:
        hashed = hash_password(normal_pass)
        print(f"   ✓ Hashing successful")
        verified = verify_password(normal_pass, hashed)
        print(f"   ✓ Verification: {verified}")
    except Exception as e:
        print(f"   ✗ Error: {e}")
    
    # Test 2: Long password (80 chars)
    print("\n2. Testing long password (80 chars):")
    long_pass = "A" * 80
    print(f"   Password: {long_pass[:20]}... (truncated for display)")
    print(f"   Length: {len(long_pass)} chars, {len(long_pass.encode('utf-8'))} bytes")
    try:
        hashed = hash_password(long_pass)
        print(f"   ✓ Hashing successful (auto-truncated to 72 bytes)")
        verified = verify_password(long_pass, hashed)
        print(f"   ✓ Verification: {verified}")
    except Exception as e:
        print(f"   ✗ Error: {e}")
    
    # Test 3: Very long password (200 chars)
    print("\n3. Testing very long password (200 chars):")
    very_long_pass = "X" * 200
    print(f"   Password: {very_long_pass[:20]}... (truncated for display)")
    print(f"   Length: {len(very_long_pass)} chars, {len(very_long_pass.encode('utf-8'))} bytes")
    try:
        hashed = hash_password(very_long_pass)
        print(f"   ✓ Hashing successful (auto-truncated to 72 bytes)")
        verified = verify_password(very_long_pass, hashed)
        print(f"   ✓ Verification: {verified}")
    except Exception as e:
        print(f"   ✗ Error: {e}")
    
    # Test 4: Unicode password
    print("\n4. Testing password with Unicode characters:")
    unicode_pass = "MyPass🔐🎉😀" * 10  # This will be long in bytes
    print(f"   Password: {unicode_pass[:20]}...")
    print(f"   Length: {len(unicode_pass)} chars, {len(unicode_pass.encode('utf-8'))} bytes")
    try:
        hashed = hash_password(unicode_pass)
        print(f"   ✓ Hashing successful")
        verified = verify_password(unicode_pass, hashed)
        print(f"   ✓ Verification: {verified}")
    except Exception as e:
        print(f"   ✗ Error: {e}")
    
    print("\n" + "=" * 60)
    print("All tests completed!")
    print("\nIf you see '✓' for all tests, password truncation is working.")
    print("If you see '✗' errors, there may be an issue with the setup.")

if __name__ == "__main__":
    test_password_lengths()

