#!/bin/bash

# Human Hunter Discord Bot Launcher
# Quick start script for running the Discord bot

set -e

echo "=================================================="
echo "Human Hunter Discord Bot"
echo "=================================================="
echo ""

# Check if running from correct directory
if [ ! -f "main.py" ]; then
    echo "❌ Error: Please run this script from the discord_bot directory"
    echo "   cd discord_bot && ./start.sh"
    exit 1
fi

# Check if .env exists in parent directory
if [ ! -f "../.env" ]; then
    echo "⚠️  Warning: .env file not found in project root"
    echo ""
    echo "Please create a .env file with your Discord bot tokens:"
    echo "  cp env.example ../.env"
    echo "  nano ../.env"
    echo ""
    exit 1
fi

# Check if required packages are installed
echo "Checking dependencies..."
python3 -c "import discord" 2>/dev/null || {
    echo "❌ discord.py not installed"
    echo "   Install with: pip install -r requirements.txt"
    exit 1
}

python3 -c "import dotenv" 2>/dev/null || {
    echo "❌ python-dotenv not installed"
    echo "   Install with: pip install -r requirements.txt"
    exit 1
}

echo "✅ Dependencies OK"
echo ""

# Check if backend dependencies are available
python3 -c "import sys; sys.path.insert(0, '..'); from backend.langgraph_game import create_game_for_room" 2>/dev/null || {
    echo "❌ Backend dependencies not found"
    echo "   Install with: pip install -r ../backend/requirements.txt"
    exit 1
}

echo "✅ Backend OK"
echo ""

# Run the bot
echo "🚀 Starting Discord bot..."
echo "=================================================="
echo ""

python3 main.py

