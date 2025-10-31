#!/bin/bash
echo "👀 Watching backend logs for cashout attempts..."
echo "Please try to cash out now from the UI"
echo "======================================"
tail -f /tmp/backend_cashout.log | grep --line-buffered -E "(CASHOUT|cashout|POST /api/wallet|ERROR|Exception|Failed|Traceback|hit_url|redemption_code)"

