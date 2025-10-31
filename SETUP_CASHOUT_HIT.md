# Setup MTurk Standing HIT for Cashouts

## Quick Start Guide

Follow these steps to create the standing MTurk HIT needed for the cashout system:

---

## Step 1: Ensure Sandbox Mode (IMPORTANT!)

**Before running the script**, make sure your `.env` file has:

```bash
MTURK_ENVIRONMENT=sandbox
```

This ensures you're using **fake money** for testing. Never test with production first!

## Step 2: Run the Setup Script

I've created a Python script that will create the HIT for you automatically.

```bash
cd /home/wschay/ai-group-chat-streamlit/backend
bash & conda activate group-chat & python create_standing_hit.py
```

The script will:
1. ✅ **Check environment** - Warns if not in sandbox
2. Check your MTurk account balance
3. List any existing HITs
4. Ask if you want to create a new standing HIT
5. Create the HIT and show you the HIT ID

**Safety Features:**
- 🛡️ Automatically detects if you're in production mode
- ⚠️ Shows warning and requires double confirmation for production
- ✅ Encourages sandbox testing first

---

## Step 3: Copy the HIT ID

After the script runs successfully, it will show:

```
✅ SUCCESS! Standing HIT created:

   HIT ID: 3XXXXXXXXXXXXXXXXXXXXXXXXX

📋 NEXT STEPS:
   1. Add this to your .env file:
      CASHOUT_HIT_ID=3XXXXXXXXXXXXXXXXXXXXXXXXX
```

**Copy the HIT ID** (the long string starting with `3`)

---

## Step 4: Update Your .env File

Add the HIT ID to your `.env` file in the backend directory:

```bash
# Open .env file
nano /home/wschay/ai-group-chat-streamlit/backend/.env

# Or if .env is in the root:
nano /home/wschay/ai-group-chat-streamlit/.env
```

Add or update this line:

```bash
CASHOUT_HIT_ID=3XXXXXXXXXXXXXXXXXXXXXXXXX
```

Save and close the file (Ctrl+X, then Y, then Enter in nano).

---

## Step 5: Restart Your Backend

```bash
# Stop your backend (Ctrl+C in the terminal where it's running)
# Then restart:
cd /home/wschay/ai-group-chat-streamlit/backend
bash & conda activate group-chat & uvicorn main:app --reload
```

You should now see:
```
✅ Cashout HIT configured: 3XXXXXXXXXXXXXXXXXXXXXXXXX
```

Instead of the warning!

---

## Verification

### Check if HIT is Active

1. Go to your MTurk Requester dashboard:
   - **Sandbox**: https://requester.sandbox.mturk.com
   - **Production**: https://requester.mturk.com

2. Look for a HIT titled: **"ChatGame - Redeem Your Earnings (Instant Payment)"**

3. It should show:
   - Status: **Active**
   - Assignments Available: **999,999** (or close to it)
   - Assignments Completed: **0** (initially)

### Test the Cashout Flow

1. Login to your game as a test user
2. Go to your profile or wallet
3. Click "Cash Out" (you'll need at least 2000 gems = $2.00)
4. You should see a redemption code
5. The system should show the HIT URL where you can submit the code

---

## Important Notes

### About the Standing HIT

- **One HIT, Many Workers**: This single HIT is used by all players for all cashouts
- **Lifetime**: The HIT lasts 1 year (you can extend it or create a new one)
- **Cost**: $0.01 base per assignment (the actual payment varies per redemption code)
- **Max Assignments**: 999,999 - enough for many cashouts

### Environment

Make sure you're creating the HIT in the correct environment:

```bash
# In your .env file:

# For testing (uses fake money):
MTURK_ENVIRONMENT=sandbox

# For production (uses real money):
MTURK_ENVIRONMENT=production
```

⚠️ **Always test in sandbox first!**

---

## Troubleshooting

### "AWS credentials not found"

Make sure your `.env` file has:
```bash
AWS_ACCESS_KEY_ID=your_access_key_here
AWS_SECRET_ACCESS_KEY=your_secret_key_here
```

### "Failed to connect to MTurk"

1. Check your AWS credentials are correct
2. Make sure your AWS IAM user has MTurk permissions
3. Check your internet connection

### "Insufficient funds"

Your MTurk account needs money to create HITs:
1. Go to your MTurk Requester account
2. Add funds (minimum $1.00 for testing)
3. Try again

### HIT Created But Not Showing

1. Check you're looking at the correct environment (sandbox vs production)
2. Wait a few minutes for MTurk to process
3. Try refreshing the MTurk dashboard

---

## Manual Method (Alternative)

If the script doesn't work, you can create the HIT manually:

1. Go to https://requester.mturk.com (or sandbox URL)
2. Click **"Create" → "New Project" → "Survey Link"**
3. Fill in:
   - **Title**: `ChatGame - Redeem Your Earnings (Instant Payment)`
   - **Description**: `Redeem a code from the ChatGame to receive your earned payment. Instant approval.`
   - **Keywords**: `games, redemption, instant payment`
   - **Reward**: `$0.01`
   - **Workers per assignment**: `999999`
   - **Time per assignment**: `60 minutes`
   - **Auto-approve time**: `1 hour`
   - **Survey Link**: `https://your-domain.com/cashout-confirm`
4. Publish the HIT
5. Copy the HIT ID and add it to your `.env` file

---

## Need Help?

See the full documentation in `REDEMPTION_CODE_SYSTEM.md` for more details about how the cashout system works.

