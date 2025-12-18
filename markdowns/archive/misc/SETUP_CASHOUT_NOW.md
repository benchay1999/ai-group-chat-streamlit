# Setup Cashout HIT - Quick Guide

## You're Almost There! Just 3 Steps:

### Step 1: Run the Setup Script

Open a new terminal and run:

```bash
cd /home/wschay/ai-group-chat-streamlit/backend
bash & conda activate group-chat & python create_standing_hit.py
```

**What this does:**
- Connects to MTurk Sandbox (safe, fake money)
- Creates a standing HIT for cashouts
- Shows you the HIT ID

### Step 2: Copy the HIT ID

You'll see output like:

```
✅ SUCCESS! Standing HIT created:

   HIT ID: 3XXXXXXXXXXXXXXXXXXXXXXXXX

📋 NEXT STEPS:
   1. Add this to your .env file:
      CASHOUT_HIT_ID=3XXXXXXXXXXXXXXXXXXXXXXXXX
```

**Copy that long HIT ID starting with `3`**

### Step 3: Add to .env File

Open your .env file:

```bash
nano /home/wschay/ai-group-chat-streamlit/.env
```

Add this line at the end:

```bash
CASHOUT_HIT_ID=paste_your_hit_id_here
```

Save and exit (Ctrl+X, Y, Enter)

### Step 4: Restart Backend

Stop your backend server (Ctrl+C) and restart it:

```bash
cd /home/wschay/ai-group-chat-streamlit/backend
bash & conda activate group-chat & uvicorn main:app --reload
```

You should now see:
```
✅ Cashout HIT configured: 3XXXXXXXXXXXXXXXXXXXXXXXXX
```

### Test It!

1. Go to your game
2. Ensure you have at least 2000 gems ($2.00)
3. Click "Cash Out"
4. You should get a redemption code!

---

## Troubleshooting

### "Insufficient funds in MTurk account"

Your MTurk sandbox account needs funds. See: `GET_SANDBOX_FUNDS.md`

### "AWS credentials error"

Your AWS credentials look good! But if you get errors, check they have MTurk permissions.

### "Script not found"

Make sure you're in the right directory:
```bash
ls /home/wschay/ai-group-chat-streamlit/backend/create_standing_hit.py
```

Should show the file exists.

---

## Why This Is Needed

The cashout system uses a **standing HIT** that all players submit their redemption codes to. This is more efficient than creating a new HIT for each cashout.

Think of it like:
- **Old way**: Create a new task for every payment (slow, expensive)
- **New way**: One task, many submissions (fast, efficient)

The HIT stays active for 1 year and can handle 999,999 cashouts!

---

**Status**: Ready to run the setup script! 🚀

