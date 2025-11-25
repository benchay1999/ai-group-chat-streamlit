# Environment Variables Loading Guide

## ✅ Automatic `.env` Loading

Your backend is **already configured** to automatically load environment variables from the `.env` file. You **do NOT need** to manually export variables!

## How It Works

When you run:
```bash
uvicorn backend.main:app --reload
```

The system automatically:
1. **Loads `env_config.py`** - Finds and loads `.env` from project root
2. **Loads `config.py`** - Also loads `.env` (double protection)
3. **Parses API keys** - Reads `OPENAI_API_KEY` or `OPENAI_API_KEYS`
4. **Initializes API Key Manager** - Sets up round-robin distribution

## Setup Steps

### 1. Create/Update `.env` File

In your project root (`/home/wschay/ai-group-chat-streamlit/`), create or edit `.env`:

```bash
# Single API key (simple setup)
OPENAI_API_KEY=sk-your-actual-key-here

# OR multiple API keys for 100+ users (recommended)
OPENAI_API_KEYS=sk-key1...,sk-key2...,sk-key3...

# Other required variables
DATABASE_URL=sqlite+aiosqlite:///./backend/group_chat.db
JWT_SECRET_KEY=your-secret-key
JWT_COMPLETION_SECRET=your-completion-key
# ... etc
```

### 2. Start Backend

```bash
cd /home/wschay/ai-group-chat-streamlit
uvicorn backend.main:app --reload
```

**That's it!** No manual exports needed.

## Verification

When the backend starts, you should see output like:

```
🔧 Environment Configuration Loading...
   Backend Dir: /home/wschay/ai-group-chat-streamlit/backend
   Project Root: /home/wschay/ai-group-chat-streamlit
   .env Path: /home/wschay/ai-group-chat-streamlit/.env
   .env Exists: True
   ✅ .env loaded: True

✅ Loaded 3 OpenAI API key(s) for round-robin distribution
🔑 APIKeyManager initialized with 3 API key(s)
```

## Troubleshooting

### Issue: "No OpenAI API keys configured"

**Check 1: `.env` file exists**
```bash
ls -la /home/wschay/ai-group-chat-streamlit/.env
```

**Check 2: `.env` has correct variable**
```bash
cat /home/wschay/ai-group-chat-streamlit/.env | grep OPENAI
```

Should show:
```
OPENAI_API_KEY=sk-...
# or
OPENAI_API_KEYS=sk-...,sk-...,sk-...
```

**Check 3: No syntax errors in `.env`**
- No spaces around `=` (use `KEY=value` not `KEY = value`)
- No quotes needed (use `KEY=value` not `KEY="value"`)
- One variable per line

### Issue: "python-dotenv not found"

Install dependencies:
```bash
cd /home/wschay/ai-group-chat-streamlit
pip install -r backend/requirements.txt
```

Or install just python-dotenv:
```bash
pip install python-dotenv
```

### Issue: Environment variables not loading

**Debug Method 1: Check what's being loaded**
```bash
cd /home/wschay/ai-group-chat-streamlit
python3 -c "
from pathlib import Path
from dotenv import load_dotenv
import os

env_path = Path('.env')
print(f'ENV file exists: {env_path.exists()}')
print(f'ENV file path: {env_path.resolve()}')

load_dotenv(dotenv_path=env_path)
print(f'OPENAI_API_KEY set: {bool(os.getenv(\"OPENAI_API_KEY\"))}')
print(f'OPENAI_API_KEYS set: {bool(os.getenv(\"OPENAI_API_KEYS\"))}')
"
```

**Debug Method 2: Check from backend directory**
```bash
cd /home/wschay/ai-group-chat-streamlit/backend
python3 -c "
from pathlib import Path
from dotenv import load_dotenv
import os

project_root = Path(__file__).resolve().parent.parent
env_path = project_root / '.env'
print(f'Project root: {project_root}')
print(f'ENV path: {env_path}')
print(f'ENV exists: {env_path.exists()}')

load_dotenv(dotenv_path=env_path)
print(f'OPENAI_API_KEY: {\"SET\" if os.getenv(\"OPENAI_API_KEY\") else \"NOT SET\"}')
print(f'OPENAI_API_KEYS: {\"SET\" if os.getenv(\"OPENAI_API_KEYS\") else \"NOT SET\"}')
"
```

### Issue: Keys loaded but API calls fail

This means `.env` is loading correctly, but the keys themselves are invalid:

1. **Verify key in OpenAI Dashboard**: https://platform.openai.com/api-keys
2. **Check key has credits**: https://platform.openai.com/account/usage
3. **Test key directly**:
   ```bash
   curl https://api.openai.com/v1/models \
     -H "Authorization: Bearer YOUR_KEY_HERE"
   ```

## Best Practices

### Development
- ✅ Use `.env` file in project root
- ✅ Add `.env` to `.gitignore` (already done)
- ✅ Use `env.example` as template
- ✅ Never commit actual API keys

### Production
- ✅ Set environment variables directly on server
- ✅ Use secrets management (AWS Secrets, etc.)
- ✅ Configure 3+ API keys for load distribution
- ✅ Set `ENVIRONMENT=production` in `.env`

## Environment Variable Precedence

The system loads variables in this order (later overrides earlier):

1. **System environment** (manually exported)
2. **`.env` file** (auto-loaded)
3. **Defaults in code** (fallback values)

So if you DO export manually, it will override the `.env` file.

## Quick Reference

| Command | Description |
|---------|-------------|
| `uvicorn backend.main:app --reload` | Start backend (loads .env automatically) |
| `cat .env \| grep OPENAI` | Check API keys in .env |
| `ls -la .env` | Verify .env file exists |
| `curl localhost:8000/health` | Check API system status |

## Health Check

After starting the backend, verify it's working:

```bash
curl http://localhost:8000/health
```

Expected response:
```json
{
  "status": "healthy",
  "api_keys_configured": true,
  "api_key_count": 3,
  "total_rooms_created": 0,
  "api_system": "operational"
}
```

If `api_keys_configured` is `false` or `api_system` is not `"operational"`, check the troubleshooting steps above.

