#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Local backend server startup script.
Run this on your local machine to host the backend.

Usage:
    python run_backend_local.py

Then expose via ngrok:
    ngrok http 8000
"""

import os
import sys
from pathlib import Path

def check_environment():
    """Check if required environment variables are set."""
    required_vars = ['OPENAI_API_KEY']
    missing_vars = [var for var in required_vars if not os.getenv(var)]
    
    if missing_vars:
        print("❌ Missing required environment variables:")
        for var in missing_vars:
            print(f"   - {var}")
        print("\n💡 Set them in your .env file or export them:")
        print(f"   export OPENAI_API_KEY='your-key-here'")
        return False
    
    print("✅ All required environment variables are set")
    return True

def main():
    """Run the backend server."""
    print("=" * 60)
    print("🚀 Starting Local Backend Server")
    print("=" * 60)
    
    # Check environment
    if not check_environment():
        sys.exit(1)
    
    print("\n📡 Backend will be available at: http://localhost:8000")
    print("📊 API docs at: http://localhost:8000/docs")
    print("\n⚠️  Remember to expose this via ngrok:")
    print("   ngrok http 8000")
    print("\n" + "=" * 60 + "\n")
    
    # Import and run uvicorn
    import uvicorn
    from backend.main import app
    
    uvicorn.run(
        app,
        host="0.0.0.0",  # Allow external connections
        port=8000,
        log_level="info",
        reload=False  # Set to True for development
    )

if __name__ == "__main__":
    main()

