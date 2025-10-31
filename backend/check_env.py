#!/usr/bin/env python3
"""
Environment Variable Diagnostic Script
Checks if all required environment variables are loaded correctly
"""

import os
import sys
from pathlib import Path

# Try loading from .env
print("=" * 70)
print("  Environment Variable Diagnostic")
print("=" * 70)

print("\n📂 Current working directory:", os.getcwd())
print("📂 Script directory:", Path(__file__).parent)
print("📂 Project root:", Path(__file__).parent.parent)

# Check if .env file exists
env_file = Path(__file__).parent.parent / ".env"
print(f"\n📄 .env file location: {env_file}")
print(f"📄 .env file exists: {env_file.exists()}")

if env_file.exists():
    print(f"📄 .env file size: {env_file.stat().st_size} bytes")
    print("\n📋 .env file contents (first 10 lines):")
    with open(env_file) as f:
        for i, line in enumerate(f, 1):
            if i <= 10:
                # Mask sensitive values
                if '=' in line and not line.strip().startswith('#'):
                    key, value = line.split('=', 1)
                    if any(word in key.upper() for word in ['KEY', 'SECRET', 'PASSWORD', 'TOKEN']):
                        print(f"   {key}=***MASKED***")
                    else:
                        print(f"   {line.rstrip()}")
                else:
                    print(f"   {line.rstrip()}")
else:
    print("❌ .env file NOT FOUND!")

# Try to load using dotenv
print("\n🔧 Testing dotenv loading...")
try:
    from dotenv import load_dotenv
    
    # Load from parent directory (project root)
    env_path = Path(__file__).parent.parent / ".env"
    loaded = load_dotenv(dotenv_path=env_path, override=True)
    print(f"✅ dotenv.load_dotenv() returned: {loaded}")
except Exception as e:
    print(f"❌ Error loading dotenv: {e}")

# Check specific environment variables
print("\n📊 Environment Variables Status:")
print("=" * 70)

required_vars = [
    'CASHOUT_HIT_ID',
    'MTURK_ENVIRONMENT',
    'AWS_ACCESS_KEY_ID',
    'AWS_SECRET_ACCESS_KEY',
]

for var in required_vars:
    value = os.getenv(var)
    if value:
        # Mask sensitive values
        if any(word in var for word in ['KEY', 'SECRET', 'PASSWORD', 'TOKEN']):
            display_value = '***MASKED***'
        else:
            display_value = value
        print(f"✅ {var:30s} = {display_value}")
    else:
        print(f"❌ {var:30s} = NOT SET")

print("\n" + "=" * 70)

# Final verdict
cashout_hit_id = os.getenv('CASHOUT_HIT_ID')
if cashout_hit_id:
    print("✅ SUCCESS: CASHOUT_HIT_ID is properly configured!")
    print(f"   HIT ID: {cashout_hit_id}")
    print("\n✅ Your backend should work correctly if restarted.")
else:
    print("❌ PROBLEM: CASHOUT_HIT_ID is NOT configured!")
    print("\n🔧 Troubleshooting steps:")
    print("   1. Make sure .env file is in the project root directory")
    print("   2. Make sure the line is: CASHOUT_HIT_ID=your_hit_id")
    print("   3. Make sure there are no spaces around the = sign")
    print("   4. Restart your backend server after making changes")

print("=" * 70)

