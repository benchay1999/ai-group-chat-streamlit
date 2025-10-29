#!/usr/bin/env python3
"""
Clear old sessions from database that don't have user mappings.
Use this to start fresh for testing authentication.
"""

import sqlite3
import sys

def clear_old_sessions():
    try:
        conn = sqlite3.connect('backend/group_chat.db')
        cursor = conn.cursor()
        
        # Get counts before deletion
        cursor.execute('SELECT COUNT(*) FROM sessions')
        session_count = cursor.fetchone()[0]
        
        cursor.execute('SELECT COUNT(*) FROM session_players')
        player_count = cursor.fetchone()[0]
        
        cursor.execute('SELECT COUNT(*) FROM session_players WHERE user_id IS NOT NULL')
        authenticated_count = cursor.fetchone()[0]
        
        print("=" * 60)
        print("Current Database State")
        print("=" * 60)
        print(f"Total sessions: {session_count}")
        print(f"Total session_players: {player_count}")
        print(f"Authenticated players: {authenticated_count}")
        print(f"Anonymous players: {player_count - authenticated_count}")
        print()
        
        if session_count == 0:
            print("✅ Database is already empty!")
            conn.close()
            return
        
        # Ask for confirmation
        print("⚠️  WARNING: This will delete ALL sessions and start fresh!")
        print()
        response = input("Are you sure you want to continue? (yes/no): ").strip().lower()
        
        if response not in ['yes', 'y']:
            print("❌ Cancelled. No changes made.")
            conn.close()
            return
        
        # Delete all sessions and related data
        cursor.execute('DELETE FROM ai_agent_usage')
        cursor.execute('DELETE FROM session_players')
        cursor.execute('DELETE FROM sessions')
        conn.commit()
        
        print()
        print("=" * 60)
        print("✅ Database Cleared Successfully!")
        print("=" * 60)
        print()
        print("Next steps:")
        print("1. Login to the app FIRST")
        print("2. Then play a game")
        print("3. Check your dashboard - the session should appear!")
        print()
        print("Remember: You must be logged in BEFORE starting the game!")
        
        conn.close()
        
    except Exception as e:
        print(f"❌ Error: {e}")
        sys.exit(1)

if __name__ == '__main__':
    clear_old_sessions()

