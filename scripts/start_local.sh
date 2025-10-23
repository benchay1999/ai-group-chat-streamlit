#!/bin/bash
# Quick start script for local backend + cloud frontend setup

echo "=========================================="
echo "🎮 AI Group Chat - Local Backend Setup"
echo "=========================================="
echo ""

# Check if .env file exists
if [ ! -f .env ]; then
    echo "⚠️  No .env file found."
    
    # Copy from example if it exists
    if [ -f env.example ]; then
        cp env.example .env
        echo "✅ Created .env from env.example"
    else
        echo "OPENAI_API_KEY=your-api-key-here" > .env
        echo "✅ Created .env file"
    fi
    
    echo ""
    echo "📝 Please edit .env and add your OpenAI API key:"
    echo "   nano .env"
    echo ""
    echo "Then run this script again."
    exit 1
fi

# Load .env
export $(cat .env | grep -v '^#' | xargs)

# Check if OPENAI_API_KEY is set
if [ -z "$OPENAI_API_KEY" ] || [ "$OPENAI_API_KEY" = "your-api-key-here" ]; then
    echo "❌ OPENAI_API_KEY not set in .env file"
    echo ""
    echo "Edit .env and set your API key:"
    echo "  nano .env"
    exit 1
fi

echo "✅ Environment variables loaded"
echo ""

# Check if uvicorn is installed
if ! command -v uvicorn &> /dev/null; then
    echo "⚠️  uvicorn not found. Installing dependencies..."
    pip install -r requirements.txt
    echo ""
fi

echo "🚀 Starting backend server..."
echo ""
echo "📡 Backend will be available at: http://localhost:8000"
echo "📊 API docs at: http://localhost:8000/docs"
echo ""
echo "⚠️  Next steps:"
echo "  1. In another terminal, run: ngrok http 8000"
echo "  2. Copy the ngrok HTTPS URL"
echo "  3. Add it to Streamlit Cloud secrets as BACKEND_URL"
echo ""
echo "=========================================="
echo ""

# Run backend
python run_backend_local.py

