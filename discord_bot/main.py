"""
Main Entry Point for Discord Bot
Launches coordinator bot and all AI agent bots concurrently.
"""

import asyncio
import logging
import sys
from pathlib import Path

# Add parent directory to path for backend imports
parent_dir = Path(__file__).parent.parent
sys.path.insert(0, str(parent_dir))

from config import (
    DISCORD_MAIN_BOT_TOKEN,
    DISCORD_AI_BOT_TOKENS,
    AI_PERSONALITIES,
)
from coordinator_bot import CoordinatorBot
from ai_agent_bot import AIAgentBot
from game_manager import DiscordGameManager

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('discord_bot.log')
    ]
)

logger = logging.getLogger(__name__)


async def main():
    """
    Main function to launch all bots.
    """
    logger.info("=" * 60)
    logger.info("Starting Human Hunter Discord Bot System")
    logger.info("=" * 60)
    
    # Validate configuration
    if not DISCORD_MAIN_BOT_TOKEN:
        logger.error("❌ DISCORD_MAIN_BOT_TOKEN not found in environment")
        sys.exit(1)
    
    if len(DISCORD_AI_BOT_TOKENS) < 4:
        logger.error(f"❌ Need at least 4 AI bot tokens, found {len(DISCORD_AI_BOT_TOKENS)}")
        sys.exit(1)
    
    logger.info(f"✅ Configuration validated")
    logger.info(f"   Main bot token: {'*' * 20}{DISCORD_MAIN_BOT_TOKEN[-8:]}")
    logger.info(f"   AI bot tokens: {len(DISCORD_AI_BOT_TOKENS)}")
    
    # Initialize coordinator bot
    logger.info("Initializing Coordinator Bot...")
    coordinator = CoordinatorBot()
    
    # Initialize AI agent bots
    logger.info(f"Initializing {len(DISCORD_AI_BOT_TOKENS)} AI Agent Bots...")
    ai_bots = []
    
    for i, token in enumerate(DISCORD_AI_BOT_TOKENS):
        agent_id = f"AI_{i+1}"
        personality = AI_PERSONALITIES[i % len(AI_PERSONALITIES)]
        
        bot = AIAgentBot(agent_id, personality)
        ai_bots.append(bot)
        
        logger.info(f"   Created {agent_id} with personality: {personality}")
    
    # Initialize game manager
    logger.info("Initializing Game Manager...")
    game_manager = DiscordGameManager(coordinator, ai_bots)
    
    # Set game manager reference in coordinator
    coordinator.set_game_manager(game_manager)
    
    logger.info("✅ All components initialized")
    logger.info("=" * 60)
    logger.info("Starting bots...")
    logger.info("=" * 60)
    
    # Create tasks for all bots
    tasks = []
    
    # Coordinator bot task
    coordinator_task = asyncio.create_task(
        coordinator.start(DISCORD_MAIN_BOT_TOKEN),
        name="coordinator_bot"
    )
    tasks.append(coordinator_task)
    logger.info("✅ Coordinator bot task created")
    
    # AI bot tasks
    for i, (bot, token) in enumerate(zip(ai_bots, DISCORD_AI_BOT_TOKENS)):
        task = asyncio.create_task(
            bot.start(token),
            name=f"ai_bot_{i+1}"
        )
        tasks.append(task)
    
    logger.info(f"✅ {len(ai_bots)} AI bot tasks created")
    logger.info("=" * 60)
    logger.info("🚀 All bots are starting up...")
    logger.info("=" * 60)
    
    # Run all bots concurrently
    try:
        await asyncio.gather(*tasks)
    except KeyboardInterrupt:
        logger.info("🛑 Received shutdown signal")
    except Exception as e:
        logger.error(f"❌ Error in bot execution: {e}", exc_info=True)
    finally:
        logger.info("Shutting down bots...")
        
        # Close all bots gracefully
        await coordinator.close()
        for bot in ai_bots:
            await bot.close()
        
        logger.info("✅ All bots shut down")
        logger.info("=" * 60)
        logger.info("Human Hunter Discord Bot System Stopped")
        logger.info("=" * 60)


def run():
    """
    Entry point function.
    """
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Shutdown requested by user")
    except Exception as e:
        logger.error(f"Fatal error: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    run()

