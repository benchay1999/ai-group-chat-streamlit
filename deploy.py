#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Combined deployment script for Streamlit Cloud.
Runs both FastAPI backend and Streamlit frontend in the same process.

Usage on Streamlit Cloud:
1. Set main file path to: deploy.py
2. Add environment variables (OPENAI_API_KEY, etc.) to Streamlit secrets
3. Deploy!
"""

import os
import sys
import threading
import time
import socket
from pathlib import Path

def find_free_port(start_port=8000, max_attempts=10):
    """Find a free port starting from start_port."""
    for port in range(start_port, start_port + max_attempts):
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.bind(('127.0.0.1', port))
            sock.close()
            return port
        except OSError:
            continue
    raise RuntimeError(f"Could not find a free port in range {start_port}-{start_port + max_attempts}")

def run_backend(port=8000):
    """Run the FastAPI backend server in a separate thread."""
    import uvicorn
    from backend.main import app
    
    print(f"🚀 Starting FastAPI backend on port {port}...")
    
    # Run uvicorn server
    config = uvicorn.Config(
        app=app,
        host="127.0.0.1",
        port=port,
        log_level="info",
        access_log=False  # Reduce noise in logs
    )
    server = uvicorn.Server(config)
    server.run()

def wait_for_backend(port=8000, timeout=30):
    """Wait for backend to be ready."""
    import requests
    
    start_time = time.time()
    while time.time() - start_time < timeout:
        try:
            response = requests.get(f"http://127.0.0.1:{port}/health", timeout=1)
            if response.status_code == 200:
                print(f"✅ Backend is ready on port {port}")
                return True
        except:
            pass
        time.sleep(0.5)
    
    print(f"⚠️ Backend did not start within {timeout} seconds")
    return False

def run_streamlit():
    """Run the Streamlit frontend."""
    import streamlit.web.cli as stcli
    
    print("🎨 Starting Streamlit frontend...")
    
    # Set the main script
    streamlit_script = str(Path(__file__).parent / "streamlit_app.py")
    
    sys.argv = [
        "streamlit",
        "run",
        streamlit_script,
        "--server.headless=true",
        "--server.address=0.0.0.0",
        "--server.port=8501"
    ]
    
    sys.exit(stcli.main())

def main():
    """Main entry point."""
    print("=" * 60)
    print("🎮 AI Group Chat - Combined Deployment")
    print("=" * 60)
    
    # Find a free port for backend
    try:
        backend_port = find_free_port(8000)
        print(f"📡 Using port {backend_port} for backend")
    except RuntimeError as e:
        print(f"❌ Error: {e}")
        sys.exit(1)
    
    # Set BACKEND_URL environment variable for streamlit_app.py
    os.environ['BACKEND_URL'] = f"http://127.0.0.1:{backend_port}"
    print(f"🔗 Backend URL set to: {os.environ['BACKEND_URL']}")
    
    # Verify required environment variables
    required_vars = ['OPENAI_API_KEY']
    missing_vars = [var for var in required_vars if not os.getenv(var)]
    if missing_vars:
        print(f"⚠️  Warning: Missing environment variables: {missing_vars}")
        print("⚠️  Make sure to set these in Streamlit Cloud secrets!")
    
    # Start backend in a separate thread
    backend_thread = threading.Thread(
        target=run_backend,
        args=(backend_port,),
        daemon=True,
        name="FastAPI-Backend"
    )
    backend_thread.start()
    print(f"🔄 Backend thread started (daemon)")
    
    # Wait for backend to be ready
    print("⏳ Waiting for backend to initialize...")
    if not wait_for_backend(backend_port, timeout=30):
        print("❌ Failed to start backend. Check logs above for errors.")
        sys.exit(1)
    
    print("=" * 60)
    print("✅ Backend is running!")
    print("🎨 Starting frontend...")
    print("=" * 60)
    
    # Small delay to ensure backend is stable
    time.sleep(1)
    
    # Run Streamlit in the main thread
    # This will block until Streamlit exits
    run_streamlit()

if __name__ == "__main__":
    main()

