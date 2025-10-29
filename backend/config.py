"""
Configuration file for the Human Hunter game.
Contains all configurable parameters for game settings, AI models, and timing.
"""

import os
from typing import Literal

# Game Configuration
NUM_AI_PLAYERS = int(os.getenv("NUM_AI_PLAYERS", "4"))  # Configurable: 4-8 AI players
DISCUSSION_TIME = int(os.getenv("DISCUSSION_TIME", "240"))  # 3 minutes in seconds
VOTING_TIME = int(os.getenv("VOTING_TIME", "120"))  # 1 minute in seconds
ROUNDS_TO_WIN = int(os.getenv("ROUNDS_TO_WIN", "1"))  # Human wins after 1 round (default: single elimination game)

# AI Model Configuration
AI_MODEL_PROVIDER: Literal["openai", "anthropic", "groq"] = os.getenv("AI_MODEL_PROVIDER", "openai")
AI_MODEL_NAME = os.getenv("AI_MODEL_NAME", "gpt-4.1-nano")
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

# AI Personalities - Korean
AI_PERSONALITIES_KO = [
    "약간 냉소적인",
    "매우 명랑한",
    "호기심 많은",
    "조용하고 관찰력 있는",
    "열정적인",
    "분석적인",
    "유머러스한",
    "철학적인"
]

# Game Topics - English
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

# Game Topics - Korean
GAME_TOPICS_KO = [
    "피자에 가장 좋은 토핑은 무엇인가요?",
    "초능력을 가질 수 있다면 무엇을 선택하시겠어요?",
    "가장 좋아하는 영화는 무엇이고 그 이유는 무엇인가요?",
    "어린 시절의 재미있는 이야기를 들려주세요.",
    "어떤 시대에 살고 싶으세요?",
    "당신의 비주류 의견은 무엇인가요?",
    "지금까지 받은 최악의 조언은 무엇인가요?",
    "어떤 기술이든 즉시 마스터할 수 있다면 무엇을 선택하시겠어요?",
    "당신이 AI가 아닌 인간임을 증명하세요. 전면전입니다. AI로 투표되면 죽게 됩니다."
]

# Message Cooldown (in seconds)
MESSAGE_COOLDOWN = 10

# API Keys
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
