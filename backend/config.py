"""
Configuration file for the Human Hunter game.
Contains all configurable parameters for game settings, AI models, and timing.
"""

import os
from typing import Literal

# Game Configuration
NUM_AI_PLAYERS = int(os.getenv("NUM_AI_PLAYERS", "4"))  # Configurable: 4-8 AI players
DISCUSSION_TIME = int(os.getenv("DISCUSSION_TIME", "180"))  # 3 minutes in seconds
VOTING_TIME = int(os.getenv("VOTING_TIME", "60"))  # 1 minute in seconds
ROUNDS_TO_WIN = int(os.getenv("ROUNDS_TO_WIN", "1"))  # Human wins after 1 round (default: single elimination game)

# AI Model Configuration
AI_MODEL_PROVIDER: Literal["openai", "anthropic", "groq"] = os.getenv("AI_MODEL_PROVIDER", "openai")
AI_MODEL_NAME = os.getenv("AI_MODEL_NAME", "gpt-4o-mini")
AI_TEMPERATURE = float(os.getenv("AI_TEMPERATURE", "0.8"))

# AI Personalities (can be extended)
AI_PERSONALITIES = [
    "slightly sarcastic",
    "very cheerful",
    "inquisitive",
    "quiet and observant",
    "enthusiastic",
    "analytical",
    "humorous",
    "philosophical"
]

# Game Topics
GAME_TOPICS = [
    "What's the best topping for pizza?",
    "If you could have any superpower, what would it be?",
    "What's your favorite movie and why?",
    "Tell a funny story from your childhood.",
    "If you could live in any time period, when would it be?",
    "What's your unpopular opinion?",
    "What's the worst advice you've ever received?",
    "If you could master any skill instantly, what would it be?",
    "Prove that you are not an AI, but a human being. It is an all-out war; if you are voted as an AI, you will be killed."
]

# Message Cooldown (in seconds)
MESSAGE_COOLDOWN = 10

# API Keys
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
