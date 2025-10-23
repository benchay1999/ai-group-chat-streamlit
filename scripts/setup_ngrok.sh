#!/bin/bash
# Setup script for ngrok (no sudo required)

echo "=========================================="
echo "🔧 ngrok Setup (No Sudo Required)"
echo "=========================================="
echo ""

# Check if ngrok binary exists
if [ ! -f ./ngrok ]; then
    echo "📥 Downloading ngrok..."
    curl -Lo ngrok.zip https://bin.equinox.io/c/bNyj1mQVY4c/ngrok-v3-stable-linux-amd64.zip
    unzip ngrok.zip
    rm ngrok.zip
    chmod +x ngrok
    echo "✅ ngrok downloaded"
    echo ""
fi

# Check if already authenticated
if [ -f ~/.config/ngrok/ngrok.yml ]; then
    echo "✅ ngrok is already authenticated"
    echo ""
    echo "To start tunnel, run:"
    echo "  ./ngrok http 8000"
    exit 0
fi

echo "🔑 Authentication Required"
echo ""
echo "To authenticate ngrok:"
echo "  1. Sign up at https://ngrok.com (free)"
echo "  2. Get your auth token from: https://dashboard.ngrok.com/get-started/your-authtoken"
echo "  3. Run: ./ngrok config add-authtoken YOUR_TOKEN"
echo ""
echo "Then start the tunnel:"
echo "  ./ngrok http 8000"
echo ""

