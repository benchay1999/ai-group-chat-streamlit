#!/bin/bash

# Setup script for Token Tracking & Gamification features
# Run this to initialize the database and install dependencies

set -e  # Exit on error

echo "========================================="
echo "Token Tracking & Gamification Setup"
echo "========================================="
echo ""

# Navigate to backend
cd "$(dirname "$0")/backend"

echo "Step 1: Installing Python dependencies..."
echo "-----------------------------------------"
pip install alembic sqlalchemy aiosqlite python-jose passlib argon2-cffi python-multipart

echo ""
echo "Step 2: Running database migrations..."
echo "-----------------------------------------"
python -m alembic upgrade head

echo ""
echo "Step 3: Verifying database setup..."
echo "-----------------------------------------"
python -c "
import sqlite3
conn = sqlite3.connect('group_chat.db')
cursor = conn.cursor()
cursor.execute('SELECT name FROM sqlite_master WHERE type=\"table\"')
tables = [row[0] for row in cursor.fetchall()]
print('✅ Created tables:', ', '.join(tables))

# Check if token tracking columns exist
cursor.execute('PRAGMA table_info(sessions)')
cols = [col[1] for col in cursor.fetchall()]
if 'total_input_tokens' in cols:
    print('✅ Token tracking columns added to sessions table')
if 'total_points' in cols or 'total_games' in cols:
    # Check users table for gamification
    cursor.execute('PRAGMA table_info(users)')
    user_cols = [col[1] for col in cursor.fetchall()]
    if 'total_points' in user_cols:
        print('✅ Gamification columns added to users table')

conn.close()
"

echo ""
echo "========================================="
echo "✅ Setup Complete!"
echo "========================================="
echo ""
echo "What's now enabled:"
echo "  ✅ Token tracking for all AI LLM calls"
echo "  ✅ Cost calculation and analytics"
echo "  ✅ User gamification (points, levels, achievements)"
echo "  ✅ Daily streak tracking"
echo "  ✅ Player identification in sessions"
echo ""
echo "Next steps:"
echo "  1. Start the backend: cd backend && python main.py"
echo "  2. Start the frontend: cd frontend && npm run dev"
echo "  3. (Optional) Create an admin user: python create_admin.py"
echo "  4. Play a game to test the features!"
echo ""
echo "Admin dashboards:"
echo "  - Analytics: http://localhost:3000/admin/analytics"
echo "  - Sessions: http://localhost:3000/admin"
echo ""
echo "User features:"
echo "  - Dashboard with stats: http://localhost:3000/dashboard"
echo "  - Points and achievements shown after each game"
echo ""

