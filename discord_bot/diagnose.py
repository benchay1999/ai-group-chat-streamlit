#!/usr/bin/env python3
"""Quick diagnostic script to check Discord bot status."""

import sys
from pathlib import Path

# Add parent directory to path
parent_dir = Path(__file__).parent.parent
sys.path.insert(0, str(parent_dir))

from config import DISCORD_MAIN_BOT_TOKEN, DISCORD_AI_BOT_TOKENS
import discord
from discord.ext import commands
import asyncio


async def diagnose():
    """Run diagnostic checks."""
    print("=" * 60)
    print("Discord Bot Diagnostic Tool")
    print("=" * 60)
    print()
    
    # Check tokens
    print("✓ Main bot token configured:", "Yes" if DISCORD_MAIN_BOT_TOKEN else "No")
    print(f"✓ AI bot tokens configured: {len(DISCORD_AI_BOT_TOKENS)}")
    print()
    
    if not DISCORD_MAIN_BOT_TOKEN:
        print("❌ Main bot token missing!")
        return
    
    # Connect to Discord and check bot status
    print("Connecting to Discord...")
    intents = discord.Intents.default()
    intents.message_content = True
    intents.members = True
    
    bot = commands.Bot(command_prefix="!", intents=intents)
    
    @bot.event
    async def on_ready():
        print(f"\n✅ Bot connected as: {bot.user.name} (ID: {bot.user.id})")
        print(f"\n📊 Bot Status:")
        print(f"   - Guilds (servers): {len(bot.guilds)}")
        
        for guild in bot.guilds:
            print(f"\n   Server: {guild.name} (ID: {guild.id})")
            print(f"   - Members: {guild.member_count}")
            print(f"   - Text Channels: {len(guild.text_channels)}")
            
            # Check bot permissions in each channel
            for channel in guild.text_channels[:5]:  # Show first 5 channels
                perms = channel.permissions_for(guild.me)
                status = "✅" if perms.send_messages and perms.embed_links else "⚠️"
                print(f"      {status} #{channel.name}: "
                      f"Send Messages: {perms.send_messages}, "
                      f"Embed Links: {perms.embed_links}, "
                      f"Use Slash Commands: {perms.use_application_commands}")
        
        print(f"\n📝 Registered Slash Commands:")
        try:
            commands_list = await bot.tree.fetch_commands()
            if commands_list:
                for cmd in commands_list:
                    print(f"   - /{cmd.name}: {cmd.description}")
            else:
                print("   ⚠️ No commands registered yet (may take 5-10 minutes to sync)")
        except Exception as e:
            print(f"   ❌ Error fetching commands: {e}")
        
        print("\n" + "=" * 60)
        print("Diagnosis complete!")
        print("=" * 60)
        print()
        print("🔧 Troubleshooting:")
        print("   1. If no slash commands show: Wait 5-10 minutes for sync")
        print("   2. If permission issues: Re-invite bot with correct URL")
        print("   3. If bot not in server: Invite using OAuth2 URL")
        print()
        print("📚 For more help, see discord_bot/README.md")
        print()
        
        await bot.close()
    
    try:
        await bot.start(DISCORD_MAIN_BOT_TOKEN)
    except discord.LoginFailure:
        print("❌ Invalid bot token!")
    except Exception as e:
        print(f"❌ Error: {e}")


if __name__ == "__main__":
    asyncio.run(diagnose())

