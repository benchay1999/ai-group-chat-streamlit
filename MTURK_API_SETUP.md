# MTurk API Setup Guide

**Complete guide to setting up Amazon Mechanical Turk integration for automated worker payments**

---

## 📋 Table of Contents

1. [Prerequisites](#prerequisites)
2. [AWS Account Setup](#aws-account-setup)
3. [IAM User Creation](#iam-user-creation)
4. [MTurk Sandbox Setup](#mturk-sandbox-setup)
5. [Environment Configuration](#environment-configuration)
6. [Testing the Integration](#testing-the-integration)
7. [Production Deployment](#production-deployment)
8. [Troubleshooting](#troubleshooting)

---

## 🎯 Prerequisites

Before starting, ensure you have:

- ✅ AWS Account (create at https://aws.amazon.com)
- ✅ Credit card for AWS billing (required even for sandbox)
- ✅ Backend and frontend applications running
- ✅ Admin account created in your application
- ✅ Basic understanding of AWS IAM

**Estimated Setup Time:** 30-45 minutes

---

## 🔐 AWS Account Setup

### Step 1: Create AWS Account

1. Go to https://aws.amazon.com
2. Click "Create an AWS Account"
3. Follow the registration process:
   - Enter email and account name
   - Provide payment information
   - Verify identity (phone verification)
   - Select support plan (Basic/Free is fine)

### Step 2: Sign in to AWS Console

1. Go to https://console.aws.amazon.com
2. Sign in with your root account credentials
3. You'll see the AWS Management Console dashboard

---

## 👤 IAM User Creation

**Important:** Never use your root account credentials in applications. Create an IAM user instead.

### Step 1: Navigate to IAM

1. In AWS Console, search for "IAM" in the top search bar
2. Click on "IAM" (Identity and Access Management)

### Step 2: Create New User

1. In the left sidebar, click "Users"
2. Click "Create user" button
3. **User name:** `mturk-api-user` (or your preferred name)
4. Click "Next"

### Step 3: Set Permissions

1. Select "Attach policies directly"
2. Search for "MTurk" in the policy search box
3. Check the box for **`AmazonMechanicalTurkFullAccess`**
   - This policy includes:
     - `mturk:CreateHIT`
     - `mturk:ApproveAssignment`
     - `mturk:SendBonus`
     - `mturk:GetAccountBalance`
     - `mturk:ListHITs`
     - And other MTurk operations
4. Click "Next"
5. Review and click "Create user"

### Step 4: Create Access Keys

1. Click on the newly created user (`mturk-api-user`)
2. Go to the "Security credentials" tab
3. Scroll down to "Access keys" section
4. Click "Create access key"
5. Select use case: **"Application running outside AWS"**
6. Click "Next"
7. (Optional) Add description tag: "Group chat game MTurk integration"
8. Click "Create access key"

### Step 5: Save Credentials

**⚠️ CRITICAL:** You'll see your credentials ONLY ONCE!

```
Access key ID: AKIAIOSFODNN7EXAMPLE
Secret access key: wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY
```

**Save these immediately:**
- Copy to a secure password manager
- Or download the CSV file
- You cannot retrieve the secret key later!

---

## 🧪 MTurk Sandbox Setup

The MTurk Sandbox is a free testing environment that mirrors production.

### Step 1: Register for MTurk

1. Go to https://requester.mturk.com
2. Click "Sign in" and use your AWS credentials
3. Complete the MTurk Requester registration:
   - Agree to terms of service
   - Provide business information (can be personal for testing)
   - Add payment method (required but not charged in sandbox)

### Step 2: Access Sandbox

1. Go to https://requester.mturk.com/developer/sandbox
2. Or use the sandbox URL directly: https://workersandbox.mturk.com

### Step 3: Create Test Worker Account

1. Go to https://workersandbox.mturk.com
2. Click "Create Account" (separate from requester account)
3. Fill in worker information:
   - Email: Use a different email than your requester account
   - Password: Create a strong password
   - Worker ID will be assigned automatically (starts with 'A')
4. Complete worker registration

**Note:** You can create multiple test worker accounts for testing.

---

## ⚙️ Environment Configuration

### Step 1: Update `.env` File

In your project root, edit the `.env` file (or create from `env.example`):

```bash
# MTurk Configuration
AWS_ACCESS_KEY_ID=AKIAIOSFODNN7EXAMPLE
AWS_SECRET_ACCESS_KEY=wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY

# Environment: 'sandbox' for testing, 'production' for real workers
MTURK_ENVIRONMENT=sandbox

# Base payment per completed HIT (in USD)
MTURK_BASE_PAY=0.05

# Maximum bonus per HIT (in USD) - caps performance bonus
# Total max payment = MTURK_BASE_PAY + MTURK_MAX_BONUS
MTURK_MAX_BONUS=0.05

# Public URL where your game is hosted (for MTurk ExternalQuestion)
# Must be HTTPS in production, can be HTTP in sandbox
EXTERNAL_URL=http://localhost:5173/lobby

# Frame height for MTurk iframe (0 = auto-resize)
MTURK_FRAME_HEIGHT=0
```

### Step 2: Verify Configuration

Run the backend and check logs for MTurk initialization:

**Option 1: Using the startup script (recommended)**
```bash
python run_backend_local.py
```

**Option 2: Using uvicorn directly**
```bash
uvicorn backend.main:app --reload --host 0.0.0.0 --port 8000
```

**Option 3: Using Python module**
```bash
python -m uvicorn backend.main:app --reload --host 0.0.0.0 --port 8000
```

Look for these messages in the startup logs:
```
✅ MTurk client initialized (sandbox environment)
💰 Base pay: $0.05, Max bonus: $0.05
🚀 Application started successfully
```

**If you see this instead:**
```
⚠️  MTurk client initialization failed: ...
   MTurk features will not be available until credentials are configured.
```

This means your AWS credentials are not set or are invalid. Check your `.env` file.

---

## 🧪 Testing the Integration

### Test 1: Verify MTurk Connection

```bash
# In backend directory
python -c "from backend.mturk_api import get_account_balance; print(f'Balance: ${get_account_balance()}')"
```

Expected output:
```
Balance: $10000.00  # Sandbox has unlimited balance
```

### Test 2: Create a Test HIT

1. Log in to your app as admin
2. Navigate to Admin Panel
3. (Future feature) Click "Create MTurk HIT"
4. Or use the API directly:

```bash
curl -X POST http://localhost:8000/api/admin/mturk/create-hit \
  -H "Authorization: Bearer YOUR_ADMIN_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "max_workers": 1,
    "title": "Test: Identify AI in Group Chat",
    "description": "Play a game and identify which player is AI",
    "keywords": "game, chat, AI, conversation"
  }'
```

### Test 3: Complete Worker Flow

1. **Create HIT** (as admin)
2. **Find HIT** in sandbox: https://workersandbox.mturk.com
3. **Accept HIT** (as test worker)
4. **Play Game:**
   - Worker is auto-registered
   - Complete the game session
   - Earnings are calculated
5. **Approve Payment** (as admin):
   - Go to Admin Panel
   - Find the session with MTurk worker
   - Click "MTurk Pay $X.XX" button
6. **Verify Payment:**
   - Check worker's MTurk account
   - Should see base pay + bonus

### Test 4: Verify Database

```bash
# Check MTurk fields in database
python -c "
from backend.database import async_session_maker, Session
import asyncio

async def check():
    async with async_session_maker() as db:
        from sqlalchemy import select
        result = await db.execute(select(Session).where(Session.mturk_worker_id != None))
        sessions = result.scalars().all()
        for s in sessions:
            print(f'Worker: {s.mturk_worker_id}, Payment: {s.mturk_payment_sent}, Bonus: {s.mturk_bonus_sent}')

asyncio.run(check())
"
```

---

## 🚀 Production Deployment

### Prerequisites for Production

- ✅ HTTPS domain (required by MTurk)
- ✅ Tested thoroughly in sandbox
- ✅ AWS account with sufficient balance
- ✅ Rate limiting implemented
- ✅ CORS configured for your domain
- ✅ Error monitoring set up

### Step 1: Update Environment

```bash
# .env
MTURK_ENVIRONMENT=production  # ⚠️ Real money!
EXTERNAL_URL=https://yourdomain.com/lobby  # ✅ Must be HTTPS
```

### Step 2: Add Funds to MTurk Account

1. Go to https://requester.mturk.com
2. Click "Account" → "Add Funds"
3. Add initial amount (e.g., $100)
4. **Note:** MTurk charges 20% commission on top of payments

**Cost Calculation:**
```
Per worker: $0.10 (base $0.05 + bonus $0.05)
MTurk fee: 20% = $0.02
Total cost: $0.12 per worker

100 workers = $12.00
1,000 workers = $120.00
```

### Step 3: Create Production HIT

```bash
curl -X POST https://yourdomain.com/api/admin/mturk/create-hit \
  -H "Authorization: Bearer YOUR_ADMIN_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "max_workers": 10,
    "title": "Identify AI in Group Chat Game (5-10 min)",
    "description": "Play a conversation game and try to identify which player is AI. Earn bonus for good performance!",
    "keywords": "game, chat, AI, conversation, research"
  }'
```

### Step 4: Monitor Production

1. **Check Balance Regularly:**
   ```bash
   curl https://yourdomain.com/api/admin/mturk/balance \
     -H "Authorization: Bearer YOUR_ADMIN_TOKEN"
   ```

2. **Review Sessions:**
   - Go to Admin Panel
   - Monitor MTurk sessions
   - Approve payments promptly (within 3 days for auto-approval)

3. **Track Costs:**
   - Set up daily spending alerts
   - Review worker quality
   - Adjust payment caps if needed

---

## 🔧 Troubleshooting

### Issue: "Invalid AWS credentials"

**Symptoms:**
```
botocore.exceptions.NoCredentialsError: Unable to locate credentials
```

**Solutions:**
1. Check `.env` file has correct `AWS_ACCESS_KEY_ID` and `AWS_SECRET_ACCESS_KEY`
2. Verify no extra spaces or quotes in `.env`
3. Restart backend after updating `.env`
4. Check IAM user has MTurk permissions

### Issue: "Insufficient funds"

**Symptoms:**
```
InsufficientFunds: Your account does not have sufficient funds
```

**Solutions:**
1. **Sandbox:** This shouldn't happen (unlimited balance)
2. **Production:** Add funds at https://requester.mturk.com
3. Check account balance: `GET /api/admin/mturk/balance`

### Issue: "ExternalURL must be HTTPS"

**Symptoms:**
```
ExternalURL must use HTTPS protocol
```

**Solutions:**
1. **Sandbox:** HTTP is allowed, check `MTURK_ENVIRONMENT=sandbox`
2. **Production:** Must use HTTPS
3. Set up SSL certificate (Let's Encrypt, Cloudflare, etc.)
4. Update `EXTERNAL_URL` to `https://...`

### Issue: "Assignment already submitted"

**Symptoms:**
```
This assignment has already been submitted
```

**Solutions:**
1. Each assignment can only be submitted once
2. Check `mturk_assignment_id` is unique in database
3. Worker needs to accept a new HIT to play again

### Issue: "Worker not auto-registered"

**Symptoms:**
- Worker lands on lobby but not logged in
- No MTurk badge showing

**Solutions:**
1. Check URL has MTurk parameters: `?workerId=...&assignmentId=...&hitId=...`
2. Verify `MTurkAutoLogin` component is rendered
3. Check browser console for errors
4. Ensure backend `/api/auth/mturk-register` endpoint works

### Issue: "Payment not processing"

**Symptoms:**
- Click "MTurk Pay" but nothing happens
- Error: "Session not found" or "No MTurk data"

**Solutions:**
1. Verify session has `mturk_worker_id` and `mturk_assignment_id`
2. Check `calculated_earnings` is set
3. Ensure assignment hasn't been paid already
4. Check backend logs for detailed error

---

## 📊 Monitoring & Maintenance

### Daily Checks

- [ ] Check MTurk account balance
- [ ] Review pending payments in Admin Panel
- [ ] Approve quality sessions within 24 hours
- [ ] Monitor error logs for MTurk API failures

### Weekly Reviews

- [ ] Analyze worker quality and earnings
- [ ] Review payment caps (adjust if needed)
- [ ] Check for unusual patterns (fraud detection)
- [ ] Update HITs if needed (title, description, pay)

### Monthly Tasks

- [ ] Review total costs vs. budget
- [ ] Analyze data quality from MTurk workers
- [ ] Rotate AWS access keys (security best practice)
- [ ] Update documentation based on learnings

---

## 🆘 Support Resources

### Official Documentation

- **AWS MTurk:** https://docs.aws.amazon.com/mturk/
- **boto3 MTurk:** https://boto3.amazonaws.com/v1/documentation/api/latest/reference/services/mturk.html
- **MTurk Requester:** https://requester.mturk.com/help

### MTurk Sandbox URLs

- **Requester Sandbox:** https://requester.mturk.com/developer/sandbox
- **Worker Sandbox:** https://workersandbox.mturk.com
- **Sandbox API Endpoint:** https://mturk-requester-sandbox.us-east-1.amazonaws.com

### MTurk Production URLs

- **Requester:** https://requester.mturk.com
- **Worker:** https://www.mturk.com
- **Production API Endpoint:** https://mturk-requester.us-east-1.amazonaws.com

### Contact

- **AWS Support:** https://console.aws.amazon.com/support/
- **MTurk Forums:** https://forums.aws.amazon.com/forum.jspa?forumID=11
- **Your Team:** [Add your support contact]

---

## ✅ Setup Checklist

Use this checklist to track your setup progress:

### AWS Setup
- [ ] AWS account created
- [ ] Payment method added
- [ ] IAM user created (`mturk-api-user`)
- [ ] MTurk Full Access policy attached
- [ ] Access keys generated and saved securely

### MTurk Registration
- [ ] Requester account registered
- [ ] Business information provided
- [ ] Sandbox access confirmed
- [ ] Test worker account created

### Application Configuration
- [ ] `.env` file updated with AWS credentials
- [ ] `MTURK_ENVIRONMENT=sandbox` set
- [ ] `EXTERNAL_URL` configured
- [ ] Payment caps configured (`MTURK_BASE_PAY`, `MTURK_MAX_BONUS`)
- [ ] Backend restarted with new config

### Testing
- [ ] MTurk connection verified
- [ ] Test HIT created successfully
- [ ] Worker auto-registration tested
- [ ] Game completion tested
- [ ] Payment approval tested
- [ ] Database fields verified

### Production Readiness
- [ ] HTTPS domain configured
- [ ] CORS restrictions updated
- [ ] Rate limiting implemented
- [ ] Error monitoring set up
- [ ] Daily spending limit configured
- [ ] Funds added to MTurk account
- [ ] Production HIT created
- [ ] End-to-end flow tested in production

---

**Setup Complete!** 🎉

You're now ready to use MTurk for automated worker payments. Remember to:
- Start with sandbox for testing
- Monitor costs closely in production
- Approve payments promptly
- Maintain good worker relationships

For workflow details, see [MTURK_WORKFLOW.md](./MTURK_WORKFLOW.md)

