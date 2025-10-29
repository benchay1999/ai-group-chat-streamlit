#!/usr/bin/env python3
"""
Quick database verification script
Checks if the database has the correct schema
"""

import sqlite3
import sys

def verify_database():
    try:
        conn = sqlite3.connect('backend/group_chat.db')
        cursor = conn.cursor()
        
        print("=" * 60)
        print("🔍 Database Schema Verification")
        print("=" * 60)
        print()
        
        # Check tables
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")
        tables = [row[0] for row in cursor.fetchall()]
        
        print("📋 Tables:")
        for table in tables:
            if table != 'alembic_version':
                print(f"   ✅ {table}")
        print()
        
        # Check users table
        cursor.execute('PRAGMA table_info(users)')
        user_cols = [col[1] for col in cursor.fetchall()]
        
        print("👤 Users Table:")
        print(f"   Total columns: {len(user_cols)}")
        
        required_gamification = ['total_games', 'total_wins', 'total_points', 'current_streak', 'longest_streak', 'level']
        missing = []
        
        for col in required_gamification:
            if col in user_cols:
                print(f"   ✅ {col}")
            else:
                print(f"   ❌ {col} (MISSING)")
                missing.append(col)
        print()
        
        # Check sessions table
        cursor.execute('PRAGMA table_info(sessions)')
        session_cols = [col[1] for col in cursor.fetchall()]
        
        print("📊 Sessions Table:")
        print(f"   Total columns: {len(session_cols)}")
        
        required_tracking = ['total_input_tokens', 'total_output_tokens', 'total_cost', 'model_name']
        
        for col in required_tracking:
            if col in session_cols:
                print(f"   ✅ {col}")
            else:
                print(f"   ❌ {col} (MISSING)")
                missing.append(col)
        print()
        
        conn.close()
        
        # Final verdict
        print("=" * 60)
        if missing:
            print("❌ SCHEMA INCOMPLETE")
            print(f"   Missing columns: {', '.join(missing)}")
            print()
            print("🔧 Fix: Run migrations:")
            print("   cd backend")
            print("   rm -f group_chat.db")
            print("   python -m alembic upgrade head")
            print("=" * 60)
            return False
        else:
            print("✅ SCHEMA CORRECT - Database is ready!")
            print()
            print("🚀 You can now:")
            print("   1. Create admin user: cd backend && python create_admin.py")
            print("   2. Start backend: cd backend && python main.py")
            print("   3. Start frontend: cd frontend && npm run dev")
            print("=" * 60)
            return True
            
    except FileNotFoundError:
        print("❌ Database file not found: backend/group_chat.db")
        print()
        print("🔧 Fix: Run migrations:")
        print("   cd backend && python -m alembic upgrade head")
        return False
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

if __name__ == '__main__':
    success = verify_database()
    sys.exit(0 if success else 1)

