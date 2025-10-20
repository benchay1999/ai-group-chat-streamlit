#!/bin/bash
# Quick start script for Streamlit frontend

echo "🎮 Human Hunter - Streamlit Frontend Launcher"
echo "=============================================="
echo ""

# Check if backend is running
echo "📡 Checking backend status..."
if curl -s http://localhost:8000/health > /dev/null 2>&1; then
    echo "✅ Backend is running on port 8000"
else
    echo "❌ Backend is not running!"
    echo ""
    echo "Please start the backend first:"
    echo "  cd backend"
    echo "  export OPENAI_API_KEY='your-api-key-here'"
    echo "  uvicorn main:app --reload"
    echo ""
    exit 1
fi

# Check if streamlit is installed
echo "📦 Checking dependencies..."
if ! python3 -c "import streamlit" 2>/dev/null; then
    echo "⚠️  Streamlit not installed. Installing dependencies..."
    pip install -r streamlit_requirements.txt
    if [ $? -ne 0 ]; then
        echo "❌ Failed to install dependencies"
        exit 1
    fi
    echo "✅ Dependencies installed"
else
    echo "✅ Streamlit is installed"
fi

echo ""
echo "🚀 Starting Streamlit app..."
echo ""

# Try port 8501 first, then 8502, 8503, etc. if occupied
PORT=8501
if lsof -Pi :8501 -sTCP:LISTEN -t >/dev/null 2>&1 ; then
    echo "⚠️  Port 8501 is in use, trying 8502..."
    PORT=8502
    if lsof -Pi :8502 -sTCP:LISTEN -t >/dev/null 2>&1 ; then
        echo "⚠️  Port 8502 is in use, trying 8503..."
        PORT=8503
    fi
fi

echo "   URL: http://localhost:$PORT"
echo ""
echo "Press Ctrl+C to stop"
echo ""

# Run streamlit
streamlit run streamlit_app.py --server.port $PORT

