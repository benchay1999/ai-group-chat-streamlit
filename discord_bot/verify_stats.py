#!/usr/bin/env python3
"""
Verification script to check if Discord bot game stats are being saved correctly.
"""

import os
import json
import sys
from datetime import datetime
from pathlib import Path

def main():
    # Get stats directory
    current_dir = Path(__file__).parent
    root = current_dir.parent
    stats_dir = root / 'discord-stats'
    
    print("=" * 70)
    print("📊 Discord Bot Stats Verification")
    print("=" * 70)
    print()
    
    # Check if directory exists
    if not stats_dir.exists():
        print("❌ Discord stats directory does not exist!")
        print(f"   Expected location: {stats_dir}")
        print()
        print("This could mean:")
        print("1. No games have been completed yet")
        print("2. There's an issue with the save_session_stats function")
        print()
        print("Try completing a full game and run this script again.")
        return 1
    
    print(f"✅ Discord stats directory found: {stats_dir}")
    print()
    
    # List all JSON files
    json_files = list(stats_dir.glob("*.json"))
    
    if not json_files:
        print("⚠️  No stats files found in directory")
        print()
        print("This means:")
        print("- The directory exists but no games have been saved yet")
        print("- Complete a full game to generate stats files")
        return 0
    
    print(f"✅ Found {len(json_files)} game stats file(s)")
    print()
    
    # Analyze each file
    print("-" * 70)
    print("Game Stats Summary:")
    print("-" * 70)
    
    for i, file_path in enumerate(sorted(json_files, reverse=True), 1):
        try:
            with open(file_path, 'r') as f:
                data = json.load(f)
            
            # Extract timestamp from filename
            filename = file_path.stem
            parts = filename.split('-')
            if len(parts) >= 2:
                timestamp = int(parts[-1])
                dt = datetime.fromtimestamp(timestamp)
                time_str = dt.strftime('%Y-%m-%d %H:%M:%S')
            else:
                time_str = "Unknown"
            
            room_code = data.get('room_code', 'Unknown')
            platform = data.get('platform', 'unknown')
            topic = data.get('topic', 'Unknown')
            players = data.get('players', [])
            chat_history = data.get('chat_history', [])
            votes = data.get('votes', {})
            winner = data.get('winner', 'Unknown')
            rounds = data.get('rounds_played', 0)
            
            print(f"\n{i}. {file_path.name}")
            print(f"   Time: {time_str}")
            print(f"   Room Code: {room_code}")
            print(f"   Platform: {platform}")
            print(f"   Topic: {topic}")
            print(f"   Players: {len(players)} ({sum(1 for p in players if p['role'] == 'human')} human, {sum(1 for p in players if p['role'] == 'ai')} AI)")
            print(f"   Messages: {len(chat_history)}")
            print(f"   Votes Cast: {len(votes)}")
            print(f"   Rounds: {rounds}")
            print(f"   Winner: {winner}")
            
            # Show first few messages
            if chat_history and len(chat_history) > 0:
                print(f"   Sample messages:")
                for msg in chat_history[:3]:
                    content = msg.get('content', '')
                    if len(content) > 50:
                        content = content[:50] + "..."
                    print(f"     - {msg.get('player_id', '???')}: {content}")
            
        except Exception as e:
            print(f"\n{i}. {file_path.name}")
            print(f"   ❌ Error reading file: {e}")
    
    print()
    print("-" * 70)
    print()
    
    # Show latest file in detail
    if json_files:
        latest_file = max(json_files, key=lambda p: p.stat().st_mtime)
        print(f"📄 Latest Game Details: {latest_file.name}")
        print("-" * 70)
        
        try:
            with open(latest_file, 'r') as f:
                data = json.load(f)
            
            print(json.dumps(data, indent=2, ensure_ascii=False)[:2000])
            if len(json.dumps(data, indent=2)) > 2000:
                print("\n... (truncated, see file for full content)")
        except Exception as e:
            print(f"❌ Error reading file: {e}")
        
        print()
        print("-" * 70)
    
    print()
    print("✅ Stats verification complete!")
    print()
    print("To view a specific file:")
    print(f"  cat {stats_dir}/<filename>.json | jq .")
    print()
    print("To monitor new stats files:")
    print(f"  watch -n 2 'ls -lth {stats_dir} | head -n 10'")
    print()
    
    return 0

if __name__ == "__main__":
    sys.exit(main())

