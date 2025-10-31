#!/bin/bash
cd /home/wschay/ai-group-chat-streamlit

# Load environment variables from .env
export $(grep -v '^#' .env | xargs)

# Start uvicorn
/nfs_edlab/wschay/anaconda3/envs/group-chat/bin/python3.11 -m uvicorn backend.main:app --host 0.0.0.0 --port 8000 --reload

