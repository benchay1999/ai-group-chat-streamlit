# Environment Variable Reference

This document provides a complete reference for all environment variables used in the Human Hunter project.

## Quick Reference Table

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `OPENAI_API_KEY` | Yes* | - | OpenAI API key for AI players |
| `OPENAI_API_KEYS` | No | - | Multiple API keys for load distribution |
| `NUM_AI_PLAYERS` | No | `4` | Number of AI players per game |
| `DISCUSSION_TIME` | No | `240` | Discussion phase duration (seconds) |
| `VOTING_TIME` | No | `120` | Voting phase duration (seconds) |
| `ROUNDS_TO_WIN` | No | `1` | Rounds human must survive to win |
| `AI_MODEL_NAME` | No | `gpt-4.1-nano` | LLM model to use |
| `AI_MODEL_PROVIDER` | No | `openai` | AI provider (openai/anthropic/groq) |
| `AI_TEMPERATURE` | No | `0.8` | LLM temperature setting |
| `DATABASE_URL` | No | SQLite | Database connection string |
| `JWT_SECRET_KEY` | Prod | `...change-this...` | JWT signing key |
| `JWT_COMPLETION_SECRET` | Prod | `...change-this...` | Completion key signing |
| `ENVIRONMENT` | No | `development` | Environment mode |
| `CORS_ALLOWED_ORIGINS` | No | localhost URLs | Allowed CORS origins |
| `AWS_ACCESS_KEY_ID` | MTurk | - | AWS access key for MTurk |
| `AWS_SECRET_ACCESS_KEY` | MTurk | - | AWS secret key |
| `MTURK_ENVIRONMENT` | No | `sandbox` | MTurk mode (sandbox/production) |
| `CASHOUT_HIT_ID` | MTurk | - | Standing HIT ID for cashouts |

*Required for AI functionality. MTurk variables only required if using payment features.

---

## Required Variables

### `OPENAI_API_KEY`

**Required**: Yes (for AI functionality)  
**Format**: `sk-...`  
**Get it from**: https://platform.openai.com/api-keys

Your OpenAI API key for generating AI player responses.

```env
OPENAI_API_KEY=sk-proj-xxxxxxxxxxxxxxxxxxxx
```

### `OPENAI_API_KEYS`

**Required**: No (recommended for high traffic)  
**Format**: Comma-separated list of API keys  
**Default**: Falls back to `OPENAI_API_KEY`

For deployments with 100+ concurrent users, distribute load across multiple API keys to avoid rate limits. Keys are assigned round-robin to each room.

```env
# Multiple keys for load distribution
OPENAI_API_KEYS=sk-key1...,sk-key2...,sk-key3...
```

**Behavior**:
- Room 1 → Key 1
- Room 2 → Key 2
- Room 3 → Key 3
- Room 4 → Key 1 (cycles back)

**Production Recommendation**: Use 3+ keys for 100+ concurrent users.

---

## Game Configuration

### `NUM_AI_PLAYERS`

**Required**: No  
**Default**: `4`  
**Valid range**: `2` - `10`

Number of AI players in each game room.

```env
NUM_AI_PLAYERS=6
```

### `DISCUSSION_TIME`

**Required**: No  
**Default**: `240` (4 minutes)  
**Unit**: Seconds

Duration of the discussion phase where players chat.

```env
DISCUSSION_TIME=180  # 3 minutes
```

### `VOTING_TIME`

**Required**: No  
**Default**: `120` (2 minutes)  
**Unit**: Seconds

Duration of the voting phase.

```env
VOTING_TIME=60  # 1 minute
```

### `ROUNDS_TO_WIN`

**Required**: No  
**Default**: `1`  
**Valid range**: `1` - `10`

Number of rounds the human must survive to win. Each round eliminates one player.

```env
ROUNDS_TO_WIN=3  # Survive 3 eliminations to win
```

---

## AI Model Configuration

### `AI_MODEL_PROVIDER`

**Required**: No  
**Default**: `openai`  
**Valid values**: `openai`, `anthropic`, `groq`

The AI provider to use for generating responses.

```env
AI_MODEL_PROVIDER=openai
```

**Provider-specific API keys**:
- `openai` → requires `OPENAI_API_KEY`
- `anthropic` → requires `ANTHROPIC_API_KEY`
- `groq` → requires `GROQ_API_KEY`

### `AI_MODEL_NAME`

**Required**: No  
**Default**: `gpt-4.1-nano`

The specific model to use for AI player responses.

**Recommended models by provider**:

| Provider | Model | Cost | Quality |
|----------|-------|------|---------|
| OpenAI | `gpt-4o-mini` | Low | Good |
| OpenAI | `gpt-4o` | High | Excellent |
| OpenAI | `gpt-4.1-nano` | Very Low | Good |
| Anthropic | `claude-3-5-sonnet-20241022` | Medium | Excellent |
| Groq | `llama-3.1-70b-versatile` | Low | Good |

```env
AI_MODEL_NAME=gpt-4o-mini
```

### `AI_TEMPERATURE`

**Required**: No  
**Default**: `0.8`  
**Valid range**: `0.0` - `2.0`

Controls randomness in AI responses. Higher values = more creative/varied responses.

```env
AI_TEMPERATURE=0.8  # Balanced creativity
```

**Guidelines**:
- `0.3` - More consistent, predictable responses
- `0.8` - Balanced (recommended)
- `1.2` - More creative and varied

---

## Database Configuration

### `DATABASE_URL`

**Required**: No  
**Default**: `sqlite+aiosqlite:///./group_chat.db`

Database connection string using SQLAlchemy format.

**SQLite (Development)**:
```env
DATABASE_URL=sqlite+aiosqlite:///./group_chat.db
```

**PostgreSQL (Production)**:
```env
DATABASE_URL=postgresql+asyncpg://user:password@host:5432/database_name
```

**Cloud PostgreSQL Examples**:
```env
# Supabase
DATABASE_URL=postgresql+asyncpg://postgres:password@db.xxxx.supabase.co:5432/postgres

# Neon
DATABASE_URL=postgresql+asyncpg://user:password@ep-xxx.us-east-2.aws.neon.tech/neondb

# Railway
DATABASE_URL=postgresql+asyncpg://postgres:password@containers-xxx.railway.app:5432/railway
```

**Important**: For production with multiple concurrent users, migrate from SQLite to PostgreSQL.

---

## Security Configuration

### `JWT_SECRET_KEY`

**Required**: Yes (in production)  
**Default**: `your-secret-key-change-this-in-production`

Secret key for signing JWT authentication tokens. **Must be changed in production**.

**Generate a secure key**:
```bash
python -c "import secrets; print(secrets.token_urlsafe(32))"
```

```env
JWT_SECRET_KEY=your-generated-secure-key-here
```

**Security**: If using default value in production, the server will refuse to start.

### `JWT_COMPLETION_SECRET`

**Required**: Yes (in production)  
**Default**: `completion-secret-key-change-this`

Secret key for signing completion tokens (proof of game completion).

```env
JWT_COMPLETION_SECRET=another-secure-key-here
```

### `ENVIRONMENT`

**Required**: No  
**Default**: `development`  
**Valid values**: `development`, `production`

Controls security validation and behavior.

```env
ENVIRONMENT=production
```

**Production mode enables**:
- JWT secret validation (fails startup if using defaults)
- HTTPS-only CORS origins (non-localhost)
- API key count warnings
- Enhanced security logging

### `CORS_ALLOWED_ORIGINS`

**Required**: No  
**Default**: `http://localhost:5173,http://localhost:3000,https://ai-group-chat.netlify.app`

Comma-separated list of allowed CORS origins.

```env
# Development
CORS_ALLOWED_ORIGINS=http://localhost:5173,http://localhost:3000

# Production
CORS_ALLOWED_ORIGINS=https://your-app.netlify.app,https://your-custom-domain.com
```

**Security**:
- Wildcard (`*`) is explicitly blocked
- Production mode requires HTTPS origins (except localhost)

---

## MTurk Integration

These variables are only required if using the MTurk payment system.

### `AWS_ACCESS_KEY_ID`

**Required**: For MTurk  
**Get it from**: AWS IAM Console

```env
AWS_ACCESS_KEY_ID=AKIAIOSFODNN7EXAMPLE
```

### `AWS_SECRET_ACCESS_KEY`

**Required**: For MTurk  
**Get it from**: AWS IAM Console

```env
AWS_SECRET_ACCESS_KEY=wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY
```

### `MTURK_ENVIRONMENT`

**Required**: No  
**Default**: `sandbox`  
**Valid values**: `sandbox`, `production`

```env
# Testing (no real money)
MTURK_ENVIRONMENT=sandbox

# Real workers and payments
MTURK_ENVIRONMENT=production
```

**Warning**: Only set to `production` when ready for real payments!

### `MTURK_BASE_PAY`

**Required**: No  
**Default**: `0.05`  
**Unit**: USD

Base payment per completed HIT.

```env
MTURK_BASE_PAY=0.05
```

### `MTURK_MAX_BONUS`

**Required**: No  
**Default**: `0.05`  
**Unit**: USD

Maximum bonus payment per HIT.

```env
MTURK_MAX_BONUS=0.10
```

**Total max payment** = `MTURK_BASE_PAY` + `MTURK_MAX_BONUS`

### `EXTERNAL_URL`

**Required**: For MTurk  
**Default**: `http://localhost:5173/lobby`

Public HTTPS URL where the game is hosted. Used in MTurk ExternalQuestion.

```env
EXTERNAL_URL=https://your-app.netlify.app/lobby
```

### `MTURK_FRAME_HEIGHT`

**Required**: No  
**Default**: `0`  
**Unit**: Pixels

Height of the MTurk iframe. `0` = auto-resize.

```env
MTURK_FRAME_HEIGHT=800
```

### `CASHOUT_HIT_ID`

**Required**: For cashout feature  
**Get it by**: Running `python backend/create_standing_hit.py`

The MTurk HIT ID for the standing cashout HIT.

```env
CASHOUT_HIT_ID=3ABC123DEF456GHI789
```

---

## Gem Economy Configuration

### `GEMS_PER_DOLLAR`

**Hardcoded**: `1000`

Conversion rate: 1000 gems = $1.00 USD. Not configurable via environment.

### `STAKE_PERCENTAGE`

**Required**: No  
**Default**: `0.5` (50%)

Percentage of gem balance used as stake in games.

```env
STAKE_PERCENTAGE=0.5
```

### `SINGLE_HUMAN_BASE_GEMS`

**Required**: No  
**Default**: `50`

Base gem reward for completing a single-human game.

```env
SINGLE_HUMAN_BASE_GEMS=50
```

### `MULTI_HUMAN_BASE_GEMS`

**Required**: No  
**Default**: `100`

Base gem reward for completing a multi-human game.

```env
MULTI_HUMAN_BASE_GEMS=100
```

### `MINIMUM_CASHOUT_AMOUNT`

**Required**: No  
**Default**: `2.00`  
**Unit**: USD

Minimum USD value required to request a cashout.

```env
MINIMUM_CASHOUT_AMOUNT=2.00  # Requires 2000 gems
```

### `CASHOUT_MONITOR_INTERVAL`

**Required**: No  
**Default**: `3600`  
**Unit**: Seconds

How often to check for expired redemption codes.

```env
CASHOUT_MONITOR_INTERVAL=3600  # Every hour
```

---

## Additional API Keys

### `ANTHROPIC_API_KEY`

**Required**: If using `AI_MODEL_PROVIDER=anthropic`

```env
ANTHROPIC_API_KEY=sk-ant-xxxxx
```

### `GEMINI_API_KEY`

**Required**: If using Gemini models

```env
GEMINI_API_KEY=xxxxx
```

---

## Configuration Examples

### Minimal Development Setup

```env
# Only required variable
OPENAI_API_KEY=sk-proj-your-key-here

# Everything else uses defaults:
# - SQLite database
# - 4 AI players
# - 4 min discussion, 2 min voting
# - Development mode (relaxed security)
```

### Standard Development Setup

```env
# API Key
OPENAI_API_KEY=sk-proj-your-key-here

# Game settings
NUM_AI_PLAYERS=4
DISCUSSION_TIME=180
VOTING_TIME=60
ROUNDS_TO_WIN=1

# AI Model
AI_MODEL_NAME=gpt-4o-mini
AI_TEMPERATURE=0.8

# Database (SQLite for development)
DATABASE_URL=sqlite+aiosqlite:///./group_chat.db

# Security (okay for development)
JWT_SECRET_KEY=dev-secret-key-not-for-production
ENVIRONMENT=development
```

### Production Setup

```env
# Multiple API keys for load distribution
OPENAI_API_KEYS=sk-key1...,sk-key2...,sk-key3...

# Game settings
NUM_AI_PLAYERS=5
DISCUSSION_TIME=180
VOTING_TIME=60
ROUNDS_TO_WIN=3

# AI Model
AI_MODEL_NAME=gpt-4o-mini
AI_TEMPERATURE=0.8

# PostgreSQL Database (required for production)
DATABASE_URL=postgresql+asyncpg://user:password@host:5432/human_hunter

# Security (REQUIRED - generate unique keys!)
JWT_SECRET_KEY=your-unique-32-char-secure-key
JWT_COMPLETION_SECRET=another-unique-32-char-key
ENVIRONMENT=production
CORS_ALLOWED_ORIGINS=https://your-app.netlify.app

# MTurk (if using payments)
AWS_ACCESS_KEY_ID=AKIAXXXXX
AWS_SECRET_ACCESS_KEY=xxxxx
MTURK_ENVIRONMENT=production
CASHOUT_HIT_ID=3ABCDEFGHIJK
EXTERNAL_URL=https://your-app.netlify.app/lobby
MINIMUM_CASHOUT_AMOUNT=2.00
```

### High-Traffic Setup (100+ Users)

```env
# 5+ API keys for high concurrency
OPENAI_API_KEYS=sk-key1,sk-key2,sk-key3,sk-key4,sk-key5

# Faster games for higher throughput
DISCUSSION_TIME=120
VOTING_TIME=45
NUM_AI_PLAYERS=4

# Fast, cheap model
AI_MODEL_NAME=gpt-4o-mini
AI_TEMPERATURE=0.7

# PostgreSQL with connection pooling
DATABASE_URL=postgresql+asyncpg://user:pass@pooler.host:6543/db?prepared_statement_cache_size=0

# Production security
ENVIRONMENT=production
JWT_SECRET_KEY=secure-key-here
```

---

## Validation Rules

### Startup Checks

The server performs these validations at startup:

1. **API Key Check**: Warns if no OpenAI API keys configured
2. **Production API Keys**: Warns if only 1 key in production (recommends 3+)
3. **JWT Secrets**: Fails startup in production if using default secrets
4. **CORS Origins**: Blocks wildcard (`*`) origins
5. **HTTPS in Production**: Warns about HTTP origins in production mode

### Error Messages

| Error | Cause | Solution |
|-------|-------|----------|
| `JWT_SECRET_KEY must be set in production!` | Using default JWT secret | Generate and set unique key |
| `SECURITY ERROR: Wildcard CORS origins` | `CORS_ALLOWED_ORIGINS=*` | Set specific origins |
| `HTTP origin not allowed in production` | HTTP origin in prod mode | Use HTTPS origins |
| `No OpenAI API keys configured` | Missing API key | Set `OPENAI_API_KEY` |

---

## Generating Secure Keys

For JWT secrets and other secure values:

```bash
# Generate a 32-character secure random string
python -c "import secrets; print(secrets.token_urlsafe(32))"

# Generate two keys at once
python -c "import secrets; print('JWT_SECRET_KEY=' + secrets.token_urlsafe(32)); print('JWT_COMPLETION_SECRET=' + secrets.token_urlsafe(32))"
```

---

## See Also

- [env.example](env.example) - Template file with all variables
- [TUTORIAL.md](TUTORIAL.md) - Complete project tutorial
- [MTURK_SETUP.md](MTURK_SETUP.md) - MTurk integration guide
- [markdowns/SQLITE_TO_POSTGRESQL.md](markdowns/SQLITE_TO_POSTGRESQL.md) - Database migration

