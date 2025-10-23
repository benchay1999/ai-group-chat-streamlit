#!/bin/bash
# Quick test script to verify backend is running and accessible

echo "=========================================="
echo "🧪 Testing Backend Connection"
echo "=========================================="
echo ""

# Test 1: Check if backend is running
echo "Test 1: Checking if backend is running..."
if curl -s http://localhost:8000/health > /dev/null 2>&1; then
    echo "✅ Backend is running on localhost:8000"
else
    echo "❌ Backend is not running"
    echo ""
    echo "Start the backend first:"
    echo "  ./start_local.sh"
    exit 1
fi

# Test 2: Check health endpoint
echo ""
echo "Test 2: Health endpoint response..."
HEALTH=$(curl -s http://localhost:8000/health)
echo "Response: $HEALTH"

if echo "$HEALTH" | grep -q "healthy"; then
    echo "✅ Health check passed"
else
    echo "⚠️  Unexpected health response"
fi

# Test 3: Check API docs
echo ""
echo "Test 3: API documentation..."
if curl -s http://localhost:8000/docs > /dev/null 2>&1; then
    echo "✅ API docs available at http://localhost:8000/docs"
else
    echo "⚠️  Could not access API docs"
fi

# Test 4: Check config endpoint
echo ""
echo "Test 4: Configuration endpoint..."
CONFIG=$(curl -s http://localhost:8000/config)
if [ ! -z "$CONFIG" ]; then
    echo "✅ Config endpoint working"
    echo "Configuration: $CONFIG"
else
    echo "⚠️  Could not get configuration"
fi

echo ""
echo "=========================================="
echo "✅ Backend Tests Complete!"
echo "=========================================="
echo ""
echo "Next steps:"
echo "  1. Choose a tunneling option (see TUNNELING_OPTIONS.md)"
echo "  2. Expose backend to internet"
echo "  3. Set BACKEND_URL in Streamlit Cloud secrets"
echo ""
echo "Quick options:"
echo "  • ngrok (already installed): ./ngrok http 8000"
echo "  • localhost.run (no install): ssh -R 80:localhost:8000 nokey@localhost.run"
echo ""

