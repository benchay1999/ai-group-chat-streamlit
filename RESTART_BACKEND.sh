#!/bin/bash
# Restart Backend Server Script

echo "🔄 Restarting Backend Server..."
echo "================================"

# Kill existing uvicorn processes
echo ""
echo "1️⃣  Killing existing backend processes..."
pkill -f uvicorn
sleep 2

# Navigate to backend directory
cd "$(dirname "$0")/backend"

# Activate conda environment and start server
echo ""
echo "2️⃣  Starting backend server..."
bash -c "source $(conda info --base)/etc/profile.d/conda.sh && conda activate group-chat && uvicorn main:app --host 0.0.0.0 --port 8000 --reload" &

echo ""
echo "✅ Backend server starting..."
echo ""
echo "Check logs with:"
echo "   tail -f backend/logs/*.log"
echo ""
echo "Stop with:"
echo "   pkill -f uvicorn"

