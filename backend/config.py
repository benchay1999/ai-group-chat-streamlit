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

# Database Configuration
DATABASE_URL = os.getenv(
    'DATABASE_URL',
    'postgresql+asyncpg://postgres:postgres@localhost:5432/group_chat_db'
)

# JWT Configuration
JWT_SECRET_KEY = os.getenv('JWT_SECRET_KEY', 'your-secret-key-change-this-in-production')
JWT_COMPLETION_SECRET = os.getenv('JWT_COMPLETION_SECRET', 'completion-secret-key-change-this')
JWT_ALGORITHM = 'HS256'
ACCESS_TOKEN_EXPIRE_HOURS = 24

# Validate JWT secrets in production
if os.getenv('ENVIRONMENT', 'development') == 'production':
    if JWT_SECRET_KEY == 'your-secret-key-change-this-in-production' or not JWT_SECRET_KEY:
        raise ValueError(
            "JWT_SECRET_KEY must be set in production! "
            "Generate with: python -c 'import secrets; print(secrets.token_urlsafe(32))'"
        )
    if JWT_COMPLETION_SECRET == 'completion-secret-key-change-this' or not JWT_COMPLETION_SECRET:
        raise ValueError(
            "JWT_COMPLETION_SECRET must be set in production! "
            "Generate with: python -c 'import secrets; print(secrets.token_urlsafe(32))'"
        )

# MTurk Worker ID Validation
MTURK_WORKER_ID_PATTERN = r'^A[A-Z0-9]{13,}$'  # Must start with A, followed by 13+ alphanumeric
MTURK_WORKER_ID_MIN_LENGTH = 14

# MTurk Configuration
MTURK_ENVIRONMENT = os.getenv('MTURK_ENVIRONMENT', 'sandbox')  # 'sandbox' or 'production'
MTURK_BASE_PAY = float(os.getenv('MTURK_BASE_PAY', '0.05'))  # Base payment per HIT
MTURK_MAX_BONUS = float(os.getenv('MTURK_MAX_BONUS', '0.05'))  # Maximum bonus per HIT (total = base + bonus)
EXTERNAL_URL = os.getenv('EXTERNAL_URL', 'http://localhost:5173/lobby')  # Public URL for ExternalQuestion
MTURK_FRAME_HEIGHT = int(os.getenv('MTURK_FRAME_HEIGHT', '0'))  # 0 = auto-resize
AWS_ACCESS_KEY_ID = os.getenv('AWS_ACCESS_KEY_ID')  # AWS credentials for MTurk API
AWS_SECRET_ACCESS_KEY = os.getenv('AWS_SECRET_ACCESS_KEY')

# Gem Economy & Cashout Configuration (1000 gems = $1.00 USD)
GEMS_PER_DOLLAR = 1000  # Conversion rate: 1000 gems = $1.00
MINIMUM_CASHOUT_AMOUNT = float(os.getenv('MINIMUM_CASHOUT_AMOUNT', '2.00'))  # Minimum USD to cash out
CASHOUT_MONITOR_INTERVAL = int(os.getenv('CASHOUT_MONITOR_INTERVAL', '3600'))  # Check for expired codes every hour
