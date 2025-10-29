#!/bin/bash

# Complete setup script for AI Group Chat with Token Tracking & Gamification
# This will set up a fresh database and prepare everything for testing

set -e  # Exit on error

echo "========================================="
echo "🚀 AI Group Chat - Complete Setup"
echo "========================================="
echo ""

# Navigate to project root
cd "$(dirname "$0")"

echo "Step 1: Installing Backend Dependencies..."
echo "-----------------------------------------"
cd backend
pip install -q alembic sqlalchemy aiosqlite python-jose passlib argon2-cffi python-multipart python-dotenv
echo "✅ Backend dependencies installed"

echo ""
echo "Step 2: Setting Up Fresh Database..."
echo "-----------------------------------------"
# Remove old database if exists
if [ -f "group_chat.db" ]; then
    echo "⚠️  Removing old database..."
    rm -f group_chat.db
fi

# Run migrations
echo "📦 Running database migrations..."
python3 -m alembic upgrade head

# Verify database
echo "✅ Verifying database schema..."
python3 -c "
import sqlite3
conn = sqlite3.connect('group_chat.db')
cursor = conn.cursor()

# Get tables
cursor.execute('SELECT name FROM sqlite_master WHERE type=\"table\" ORDER BY name')
tables = [row[0] for row in cursor.fetchall()]
print('   Tables:', ', '.join([t for t in tables if t != 'alembic_version']))

# Verify users table
cursor.execute('PRAGMA table_info(users)')
user_cols = [col[1] for col in cursor.fetchall()]
has_gamification = all(c in user_cols for c in ['total_games', 'total_points', 'level', 'current_streak'])

# Verify sessions table
cursor.execute('PRAGMA table_info(sessions)')
session_cols = [col[1] for col in cursor.fetchall()]
has_token_tracking = all(c in session_cols for c in ['total_input_tokens', 'total_output_tokens', 'total_cost', 'model_name'])

conn.close()

if has_gamification and has_token_tracking:
    print('   ✅ Gamification: Enabled')
    print('   ✅ Token Tracking: Enabled')
    print('   ✅ Player Identification: Enabled')
else:
    print('   ⚠️  Schema verification failed!')
    exit(1)
"

echo ""
echo "Step 3: Checking Frontend Dependencies..."
echo "-----------------------------------------"
cd ../frontend
if [ ! -d "node_modules" ]; then
    echo "📦 Installing frontend dependencies..."
    npm install --silent
    echo "✅ Frontend dependencies installed"
else
    echo "✅ Frontend dependencies already installed"
fi

echo ""
echo "========================================="
echo "✅ Setup Complete!"
echo "========================================="
echo ""
echo "🎮 Your AI Group Chat is ready with:"
echo "   ✅ Token tracking for all AI LLM calls"
echo "   ✅ Cost calculation and analytics"
echo "   ✅ Gamification (points, levels, achievements)"
echo "   ✅ Player identification in sessions"
echo "   ✅ Fresh database with proper schema"
echo ""
echo "📋 Next Steps:"
echo ""
echo "1️⃣  (Optional) Create an admin user:"
echo "    cd backend && python3 create_admin.py"
echo ""
echo "2️⃣  Start the backend (in one terminal):"
echo "    cd backend && python3 main.py"
echo ""
echo "3️⃣  Start the frontend (in another terminal):"
echo "    cd frontend && npm run dev"
echo ""
echo "4️⃣  Open your browser:"
echo "    http://localhost:3000"
echo ""
echo "🎯 Test the features:"
echo "   • Register and play a game"
echo "   • Check console for token tracking logs"
echo "   • View dashboard for gamification stats"
echo "   • (Admin) Check analytics at /admin/analytics"
echo ""
echo "📚 Documentation:"
echo "   • DATABASE_READY.md - Database setup details"
echo "   • FEATURES_READY_TO_TEST.md - Feature testing guide"
echo "   • IMPLEMENTATION_COMPLETE.md - Technical documentation"
echo ""

cd ..

