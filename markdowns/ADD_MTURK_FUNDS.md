# How to Add Funds to Your MTurk Account

## The Error You're Seeing

```
ERROR: This Requester has insufficient funds in their account
```

This means your MTurk requester account has $0.00 balance. You need to add funds before creating HITs.

---

## For SANDBOX Testing (Recommended First)

### Option 1: Use the Sandbox Developer Account

The MTurk Sandbox has a special **Developer Sandbox** account that gives you **fake money** for testing:

1. **Go to**: https://requestersandbox.mturk.com/developer

2. **Sign in** with your AWS credentials

3. **Navigate to**: Developer Sandbox → **"Get Started"**

4. MTurk Sandbox automatically provides you with **$10,000 in fake money** for testing

5. No credit card needed!

### Option 2: Manual Sandbox Fund Addition

If the developer account doesn't work, you can add fake funds manually:

1. Go to: https://requestersandbox.mturk.com/prepayments/new
2. "Add Funds" - In sandbox, this adds fake money
3. Add at least **$10.00** (fake money)
4. Confirm

---

## For PRODUCTION (Real Money)

⚠️ **Only do this after testing in sandbox!**

### Add Real Funds to Production Account

1. Go to: https://requester.mturk.com/prepayments/new

2. Choose payment method:
   - Credit/Debit Card
   - Bank Account (ACH)
   
3. Minimum: **$1.00** (but add more for real usage)

4. Recommended starting amount: **$10-20** for initial testing

5. Confirm payment

### What You'll Need

- Valid payment method
- Minimum $1.00 to add
- For cashout testing: At least $10-20 recommended

---

## How Much Money Do You Need?

### For Creating the Standing HIT

- **Base HIT cost**: $0.01 per assignment
- **For standing HIT**: $0.01 × 999,999 assignments = ~$10,000 total

**BUT** you don't pay upfront for all assignments! You only pay when workers complete assignments.

### Initial Funding Needs

For testing the standing HIT:
- **Minimum**: $1.00
- **Recommended**: $10.00 (enough for 1000 test cashouts of $0.01 each)
- **Production**: $50-100+ depending on expected usage

### Per Cashout Transaction

When a player cashes out $5.00:
- You pay exactly $5.00 to that worker
- The standing HIT base is $0.01 (minimal)
- Total cost per cashout ≈ cashout amount

---

## Quick Start Guide

### For Sandbox Testing (Fake Money)

```bash
1. Go to: https://requestersandbox.mturk.com/developer
2. Sign in with AWS credentials
3. The sandbox automatically gives you $10,000 fake money
4. Run the script again:
   cd /home/wschay/ai-group-chat-streamlit/backend
   python create_standing_hit.py
```

### Verify Your Balance

Check your current balance with this command:

```bash
cd /home/wschay/ai-group-chat-streamlit/backend
python -c "
import boto3
import os
from dotenv import load_dotenv

load_dotenv()

env = os.getenv('MTURK_ENVIRONMENT', 'sandbox')
endpoint = 'https://mturk-requester-sandbox.us-east-1.amazonaws.com' if env == 'sandbox' else 'https://mturk-requester.us-east-1.amazonaws.com'

mturk = boto3.client(
    'mturk',
    region_name='us-east-1',
    endpoint_url=endpoint,
    aws_access_key_id=os.getenv('AWS_ACCESS_KEY_ID'),
    aws_secret_access_key=os.getenv('AWS_SECRET_ACCESS_KEY')
)

balance = mturk.get_account_balance()
print(f'Environment: {env.upper()}')
print(f'Available Balance: ${balance[\"AvailableBalance\"]}')
"
```

---

## Troubleshooting

### "I added funds but still getting error"

1. **Wrong environment?**
   - Check your `.env` file: `MTURK_ENVIRONMENT=sandbox` or `production`
   - Funds in sandbox don't transfer to production (and vice versa)
   - They are separate accounts

2. **Wait a moment**
   - Sometimes takes 1-2 minutes for funds to appear
   - Try refreshing or waiting

3. **Check the right account**
   - Sandbox: https://requestersandbox.mturk.com
   - Production: https://requester.mturk.com

### "I don't want to add money yet"

You have two options:

1. **Skip the HIT creation for now**
   - The app will work without cashouts
   - Players can still earn gems
   - Just can't cash out until HIT is created

2. **Use sandbox with fake money**
   - No credit card needed
   - Perfect for testing
   - Switch to production later

### "How much will this cost me?"

**Sandbox**: $0 (all fake money)

**Production ongoing costs**:
- Standing HIT creation: ~$0 (just reserves a spot)
- Per cashout: Exactly what the player cashes out
- Example: Player cashes out $5.00 → You pay $5.00
- Your total cost = Total amount players cash out

---

## Next Steps After Adding Funds

1. **Verify balance** (use command above)

2. **Run the script again**:
   ```bash
   cd /home/wschay/ai-group-chat-streamlit/backend
   python create_standing_hit.py
   ```

3. **Copy the HIT ID** when successful

4. **Add to .env**:
   ```bash
   CASHOUT_HIT_ID=3XXXXXXXXXXXXXXXXXXXXXXXXX
   ```

5. **Restart backend** and test!

---

## Important Notes

- 💰 Sandbox = Fake money (free)
- 💵 Production = Real money (costs money)
- 🧪 Always test in sandbox first
- 📊 Monitor your balance regularly
- 🔒 Funds are per-environment (separate accounts)

---

Need help? Check the error message carefully - it usually tells you exactly what's wrong!

