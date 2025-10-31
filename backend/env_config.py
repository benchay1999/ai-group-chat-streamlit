"""
Robust Environment Configuration Module
Ensures environment variables are loaded correctly with explicit path resolution
"""

import os
from pathlib import Path
from dotenv import load_dotenv

# Get the absolute path to the project root
# This file is in backend/, so parent is the project root
BACKEND_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = BACKEND_DIR.parent
ENV_FILE_PATH = PROJECT_ROOT / ".env"

print(f"🔧 Environment Configuration Loading...")
print(f"   Backend Dir: {BACKEND_DIR}")
print(f"   Project Root: {PROJECT_ROOT}")
print(f"   .env Path: {ENV_FILE_PATH}")
print(f"   .env Exists: {ENV_FILE_PATH.exists()}")

# Load .env file with explicit path
if ENV_FILE_PATH.exists():
    loaded = load_dotenv(dotenv_path=ENV_FILE_PATH, override=True)
    print(f"   ✅ .env loaded: {loaded}")
else:
    print(f"   ⚠️  WARNING: .env file not found at {ENV_FILE_PATH}")
    load_dotenv(override=True)  # Fallback to default behavior

# Cache critical environment variables at module load time
CASHOUT_HIT_ID = os.getenv('CASHOUT_HIT_ID')
MTURK_ENVIRONMENT = os.getenv('MTURK_ENVIRONMENT', 'sandbox')
AWS_ACCESS_KEY_ID = os.getenv('AWS_ACCESS_KEY_ID')
AWS_SECRET_ACCESS_KEY = os.getenv('AWS_SECRET_ACCESS_KEY')

# Diagnostic output
print(f"\n📊 Environment Variables Status:")
print(f"   CASHOUT_HIT_ID: {'✅ SET' if CASHOUT_HIT_ID else '❌ NOT SET'}")
if CASHOUT_HIT_ID:
    print(f"   └─ Value: {CASHOUT_HIT_ID}")
print(f"   MTURK_ENVIRONMENT: {MTURK_ENVIRONMENT}")
print(f"   AWS_ACCESS_KEY_ID: {'✅ SET' if AWS_ACCESS_KEY_ID else '❌ NOT SET'}")
print(f"   AWS_SECRET_ACCESS_KEY: {'✅ SET' if AWS_SECRET_ACCESS_KEY else '❌ NOT SET'}")


def get_cashout_hit_id() -> str:
    """
    Get the cashout HIT ID with robust error handling.
    Returns the cached value loaded at module import time.
    
    Raises:
        ValueError: If CASHOUT_HIT_ID is not configured
    """
    if not CASHOUT_HIT_ID:
        raise ValueError(
            "CASHOUT_HIT_ID not configured. "
            "Please set CASHOUT_HIT_ID in your .env file and restart the server."
        )
    return CASHOUT_HIT_ID


def is_cashout_configured() -> bool:
    """Check if cashout system is properly configured."""
    return CASHOUT_HIT_ID is not None and len(CASHOUT_HIT_ID.strip()) > 0


def get_config_status() -> dict:
    """Get current configuration status for diagnostics."""
    return {
        "env_file_path": str(ENV_FILE_PATH),
        "env_file_exists": ENV_FILE_PATH.exists(),
        "cashout_hit_id_configured": is_cashout_configured(),
        "mturk_environment": MTURK_ENVIRONMENT,
        "aws_credentials_configured": bool(AWS_ACCESS_KEY_ID and AWS_SECRET_ACCESS_KEY)
    }


# Validate critical configuration at import time
if not is_cashout_configured():
    print("\n" + "=" * 70)
    print("⚠️  CRITICAL WARNING: CASHOUT_HIT_ID NOT CONFIGURED!")
    print("=" * 70)
    print(f"Expected .env location: {ENV_FILE_PATH}")
    print(f".env file exists: {ENV_FILE_PATH.exists()}")
    if ENV_FILE_PATH.exists():
        print("\n.env file found but CASHOUT_HIT_ID not set or empty!")
        print("Please add this line to your .env file:")
        print("   CASHOUT_HIT_ID=your_mturk_hit_id_here")
    else:
        print("\n.env file not found!")
        print("Please create .env file at project root with:")
        print("   CASHOUT_HIT_ID=your_mturk_hit_id_here")
    print("\nTo create a HIT, run:")
    print(f"   cd {PROJECT_ROOT}")
    print("   python3 backend/create_standing_hit.py")
    print("=" * 70 + "\n")
else:
    print(f"\n✅ Cashout system configured successfully!")
    print(f"   HIT ID: {CASHOUT_HIT_ID}\n")


