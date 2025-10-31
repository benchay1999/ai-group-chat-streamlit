#!/bin/bash
echo "👀 Live monitoring cashout requests..."
echo "======================================"
echo "Please try to cash out NOW from the UI"
echo "======================================"
tail -f /tmp/backend_clean.log | grep --line-buffered -E "(CASHOUT REQUEST V2|Returning response|POST /api/wallet/cashout|ERROR|Exception|Traceback|200 OK|500)" | head -100

