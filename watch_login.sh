#!/bin/bash
echo "👀 Monitoring login attempts..."
echo "Please try to login now"
echo "======================================"
tail -f /tmp/backend_final_fix.log | grep --line-buffered -E "(POST /api/auth|login|ERROR|Exception|401|403|Traceback)"

