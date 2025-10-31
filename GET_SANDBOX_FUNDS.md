# How to Get Sandbox Funds (Step-by-Step)

## The Issue

You're seeing this error:
```
This Requester has insufficient funds in their account
```

This means your **MTurk Sandbox account has $0 balance**. The $10,000 is NOT automatic - you need to manually add it.

---

## Solution: Add Sandbox Funds (3 Methods)

### Method 1: Developer Sandbox (Easiest)

1. **Go to**: https://requestersandbox.mturk.com/developer

2. **Sign in** with your AWS credentials (same ones in your `.env` file)

3. **Look for**: "Developer Sandbox" or "Get Started with Sandbox"

4. **Click**: The button to add sandbox funds

5. You should see your balance increase to **$10,000.00**

---

### Method 2: Direct Prepayment Page

1. **Go to**: https://requestersandbox.mturk.com/prepayments/new

2. **Sign in** with your AWS credentials

3. **Enter amount**: $100.00 (or any amount - it's fake money!)

4. **Submit**: The form (no credit card needed in sandbox)

5. Your balance should update immediately

---

### Method 3: Use the Balance Checker Script

First, check your current balance:

```bash
cd /home/wschay/ai-group-chat-streamlit/backend
bash & conda activate group-chat & python check_mturk_balance.py
```

You'll probably see:
```
💰 Available Balance: $0.00
📝 Note: This is FAKE MONEY for testing
⚠️  Your sandbox balance is low!
```

Then:
1. Go to one of the URLs above
2. Add sandbox funds
3. Run the script again to verify

---

## Verify Your Balance

After adding funds, check again:

```bash
cd /home/wschay/ai-group-chat-streamlit/backend
python check_mturk_balance.py
```

You should see:
```
💰 Available Balance: $10000.00
📝 Note: This is FAKE MONEY for testing
```

---

## Then Create the HIT

Once you have funds, run the HIT creator again:

```bash
cd /home/wschay/ai-group-chat-streamlit/backend
python create_standing_hit.py
```

Now it should work! ✅

---

## Important Notes

### Sandbox vs Production

| Environment | Balance Location | Fund Type | How to Add |
|-------------|-----------------|-----------|------------|
| **Sandbox** | requestersandbox.mturk.com | Fake Money | Developer page or prepayments |
| **Production** | requester.mturk.com | Real Money | Credit card/bank account |

### Common Mistakes

❌ **"I thought sandbox has automatic $10K"**
- Not automatic! You must manually add it once

❌ **"I added funds to production instead of sandbox"**
- They're separate accounts
- Check your `MTURK_ENVIRONMENT` in `.env`
- Make sure you're on the right website

❌ **"I signed in but don't see my balance"**
- Look for "Account Settings" or "Account Balance" link
- Or use the prepayments page directly

---

## Troubleshooting

### "I can't find the developer sandbox page"

Try these direct links:
- https://requestersandbox.mturk.com/developer
- https://requestersandbox.mturk.com/prepayments/new
- https://requestersandbox.mturk.com/account

### "It says I need to verify my account"

For sandbox:
1. You may need to set up your requester account first
2. Go to: https://requestersandbox.mturk.com/
3. Complete any required setup steps
4. Then add funds

### "Still getting insufficient funds error"

1. **Verify environment**:
   ```bash
   grep MTURK_ENVIRONMENT .env
   ```
   Should show: `MTURK_ENVIRONMENT=sandbox`

2. **Check balance again**:
   ```bash
   python check_mturk_balance.py
   ```

3. **Wait a moment**: Sometimes takes 1-2 minutes to update

4. **Try logging out and back in**: On the MTurk sandbox website

---

## Quick Summary

```bash
# 1. Check current balance
cd /home/wschay/ai-group-chat-streamlit/backend
python check_mturk_balance.py

# 2. Go add funds in browser
# https://requestersandbox.mturk.com/prepayments/new

# 3. Verify balance updated
python check_mturk_balance.py

# 4. Create HIT
python create_standing_hit.py
```

---

The key point: **Sandbox funds are NOT automatic**. You must manually add them once, but it's free (fake money). 🎯

