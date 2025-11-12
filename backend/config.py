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
# Each personality has distinct behavioral traits beyond just the label
AI_PERSONALITIES = [
    "slightly sarcastic, tends to use dry humor and subtle jabs",
    "very cheerful, uses exclamation points, positive language, and encouraging words",
    "inquisitive, asks follow-up questions, genuinely curious about others' thoughts",
    "quiet and observant, speaks less frequently but makes thoughtful comments",
    "enthusiastic, gets excited easily, often agrees emphatically with others",
    "analytical, breaks down arguments logically, references facts and reasoning",
    "humorous, makes jokes and finds funny angles in conversations",
    "philosophical, contemplates deeper meanings, references broader concepts"
]

# AI Personalities - Korean
# Each personality has distinct behavioral traits beyond just the label
AI_PERSONALITIES_KO = [
    "약간 냉소적인, 건조한 유머와 은근한 비꼬기를 사용하는 경향이 있음",
    "매우 명랑한, 느낌표를 많이 쓰고, 긍정적인 언어와 격려하는 말을 사용",
    "호기심 많은, 후속 질문을 하고, 다른 사람의 생각에 진심으로 관심이 많음",
    "조용하고 관찰력 있는, 덜 자주 말하지만 신중한 코멘트를 함",
    "열정적인, 쉽게 흥분하고, 다른 사람들과 열렬히 동의하는 경향",
    "분석적인, 논리적으로 주장을 분석하고, 사실과 추론을 언급함",
    "유머러스한, 농담을 하고 대화에서 재미있는 각도를 찾음",
    "철학적인, 더 깊은 의미를 숙고하고, 더 넓은 개념을 참조함"
]

# Personality-Based Imperfection Profiles
# Maps personality types to imperfection characteristics for more realistic behavior
# Note: Netspeak probabilities are intentionally low - should feel natural, not forced
PERSONALITY_IMPERFECTION_LEVELS = {
    # High correctness (10% typo chance, minimal netspeak)
    "analytical": {
        "typo_probability": 0.10,
        "netspeak_probability": 0.05,  # Very rare
        "self_correction_probability": 0.70,
        "correctness_level": "high",
        "behavioral_notes": "Precise language, logical structure, rarely uses slang"
    },
    "quiet and observant": {
        "typo_probability": 0.10,
        "netspeak_probability": 0.03,  # Almost never
        "self_correction_probability": 0.65,
        "correctness_level": "high",
        "behavioral_notes": "Thoughtful, concise, minimal slang usage"
    },
    "분석적인": {
        "typo_probability": 0.10,
        "netspeak_probability": 0.05,
        "self_correction_probability": 0.70,
        "correctness_level": "high",
        "behavioral_notes": "정확한 언어, 논리적 구조, 은어를 거의 사용하지 않음"
    },
    "조용하고 관찰력 있는": {
        "typo_probability": 0.10,
        "netspeak_probability": 0.03,
        "self_correction_probability": 0.65,
        "correctness_level": "high",
        "behavioral_notes": "신중하고 간결하며, 은어 사용이 최소화됨"
    },
    
    # Medium correctness (25% typo chance, occasional netspeak)
    "slightly sarcastic": {
        "typo_probability": 0.25,
        "netspeak_probability": 0.15,  # Occasional
        "self_correction_probability": 0.50,
        "correctness_level": "medium",
        "behavioral_notes": "Dry wit, may use slang sarcastically"
    },
    "philosophical": {
        "typo_probability": 0.25,
        "netspeak_probability": 0.08,  # Rare
        "self_correction_probability": 0.55,
        "correctness_level": "medium",
        "behavioral_notes": "Contemplative, formal language, minimal slang"
    },
    "inquisitive": {
        "typo_probability": 0.25,
        "netspeak_probability": 0.12,  # Sometimes
        "self_correction_probability": 0.50,
        "correctness_level": "medium",
        "behavioral_notes": "Curious, asks questions, moderate slang usage"
    },
    "약간 냉소적인": {
        "typo_probability": 0.25,
        "netspeak_probability": 0.15,
        "self_correction_probability": 0.50,
        "correctness_level": "medium",
        "behavioral_notes": "건조한 재치, 은어를 냉소적으로 사용할 수 있음"
    },
    "철학적인": {
        "typo_probability": 0.25,
        "netspeak_probability": 0.08,
        "self_correction_probability": 0.55,
        "correctness_level": "medium",
        "behavioral_notes": "사색적이고 격식 있는 언어, 은어 최소화"
    },
    "호기심 많은": {
        "typo_probability": 0.25,
        "netspeak_probability": 0.12,
        "self_correction_probability": 0.50,
        "correctness_level": "medium",
        "behavioral_notes": "호기심 있고 질문을 많이 하며, 적당한 은어 사용"
    },
    
    # Low correctness (40% typo chance, more frequent but still natural netspeak)
    "very cheerful": {
        "typo_probability": 0.40,
        "netspeak_probability": 0.25,  # Regular but not overwhelming
        "self_correction_probability": 0.35,
        "correctness_level": "low",
        "behavioral_notes": "Enthusiastic, uses positive slang naturally"
    },
    "enthusiastic": {
        "typo_probability": 0.40,
        "netspeak_probability": 0.22,  # Fairly regular
        "self_correction_probability": 0.40,
        "correctness_level": "low",
        "behavioral_notes": "Excited tone, comfortable with casual language"
    },
    "humorous": {
        "typo_probability": 0.40,
        "netspeak_probability": 0.20,  # Moderate
        "self_correction_probability": 0.38,
        "correctness_level": "low",
        "behavioral_notes": "Playful, uses slang for comedic effect"
    },
    "매우 명랑한": {
        "typo_probability": 0.40,
        "netspeak_probability": 0.25,
        "self_correction_probability": 0.35,
        "correctness_level": "low",
        "behavioral_notes": "열정적이며 긍정적인 은어를 자연스럽게 사용"
    },
    "열정적인": {
        "typo_probability": 0.40,
        "netspeak_probability": 0.22,
        "self_correction_probability": 0.40,
        "correctness_level": "low",
        "behavioral_notes": "흥분한 톤, 캐주얼한 언어에 익숙함"
    },
    "유머러스한": {
        "typo_probability": 0.40,
        "netspeak_probability": 0.20,
        "self_correction_probability": 0.38,
        "correctness_level": "low",
        "behavioral_notes": "재치 있고, 코믹 효과를 위해 은어 사용"
    }
}

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
