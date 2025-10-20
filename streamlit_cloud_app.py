#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Streamlit Cloud deployment - Frontend only.
Backend should be running on your local machine and exposed via ngrok.

Setup:
1. Run backend locally: uvicorn backend.main:app --host 0.0.0.0 --port 8000
2. Expose via ngrok: ngrok http 8000
3. Set BACKEND_URL in Streamlit secrets to your ngrok URL
4. Deploy this file to Streamlit Cloud
"""

import streamlit as st
import os

# Check if backend URL is configured
BACKEND_URL = os.getenv('BACKEND_URL', '')

if not BACKEND_URL:
    st.error("⚠️ Backend URL not configured!")
    st.markdown("""
    ### Setup Instructions:
    
    1. **Run backend locally:**
       ```bash
       uvicorn backend.main:app --host 0.0.0.0 --port 8000
       ```
    
    2. **Expose backend via ngrok:**
       ```bash
       ngrok http 8000
       ```
       Copy the public URL (e.g., `https://abc123.ngrok-free.app`)
    
    3. **Add to Streamlit secrets:**
       - Go to your app settings on Streamlit Cloud
       - Add secret: `BACKEND_URL = "https://your-ngrok-url.ngrok-free.app"`
       - Save and reboot app
    """)
    st.stop()

# Set the backend URL for streamlit_app
os.environ['BACKEND_URL'] = BACKEND_URL

# Import and run the main streamlit app
from streamlit_app import main

if __name__ == "__main__":
    main()

