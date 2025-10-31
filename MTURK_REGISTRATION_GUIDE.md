# MTurk Requester Registration Guide

**Quick visual guide to link your AWS account to MTurk**

---

## 🎯 What You Need

This error means you haven't linked your AWS account to MTurk yet:

```
MTurk API error: To use the MTurk API, you will need an Amazon Web Services (AWS) Account. 
Your AWS account must be linked to your Amazon Mechanical Turk Account.
```

**Don't worry!** This is a one-time setup that takes ~5 minutes.

---

## 📝 Step-by-Step Registration

### Step 1: Go to MTurk Sandbox Developer Page

**URL:** https://requestersandbox.mturk.com/developer

**Important:** Use the **sandbox** URL (not production)

---

### Step 2: Sign In with AWS Credentials

Click **"Sign in"** and use your AWS account credentials:
- The same account where you created the IAM user
- Your AWS root account email/password
- Or IAM user credentials if you have console access

---

### Step 3: Link Your Account

You'll see a page saying:

```
┌─────────────────────────────────────────────────┐
│  Link your AWS Account to                       │
│  Amazon Mechanical Turk                         │
│                                                 │
│  To use the MTurk API, you need to link        │
│  your AWS account to your MTurk account.       │
│                                                 │
│  [Get Started] or [Link Account]               │
└─────────────────────────────────────────────────┘
```

Click **"Get Started"** or **"Link Account"**

---

### Step 4: Accept Terms of Service

Read and accept the MTurk Participation Agreement:
- ✅ Check "I agree to the terms"
- Click "Accept"

---

### Step 5: Provide Business Information

Fill in the requester information form:

**Required fields:**
- **Name:** Your name or business name
- **Address:** Your address (can be personal)
- **Phone:** Your phone number
- **Email:** Your email (will be verified)

**For testing/research:**
- You can use personal information
- No need for a registered business
- Just be honest about your use case

Click **"Continue"** or **"Next"**

---

### Step 6: Add Payment Method

**⚠️ Required even for sandbox!**

Add a credit card:
- Card number
- Expiration date
- CVV
- Billing address

**Important notes:**
- ✅ Required for both sandbox AND production
- ✅ **You will NOT be charged in sandbox**
- ✅ Sandbox has unlimited balance ($10,000)
- ✅ Only charged when using production

Click **"Add Payment Method"**

---

### Step 7: Verify Email (if prompted)

Check your email for a verification link:
- Subject: "Verify your Amazon Mechanical Turk email"
- Click the verification link
- Return to the MTurk page

---

### Step 8: Confirmation

You should see:

```
✅ Your AWS Account is now linked to Amazon Mechanical Turk!
```

Or you'll be redirected to the MTurk Requester Dashboard.

---

## 🧪 Test Your Registration

### Test 1: Check Account Balance

```bash
curl -X GET https://ai-groupchat.ngrok.io/api/admin/mturk/balance \
  -H "Authorization: Bearer YOUR_ADMIN_TOKEN"
```

**Expected response:**
```json
{
  "available": "10000.00",
  "on_hold": "0.00"
}
```

**Sandbox always shows $10,000** - this is normal!

---

### Test 2: Create a Test HIT

```bash
curl -X POST https://ai-groupchat.ngrok.io/api/admin/mturk/create-hit \
  -H "Authorization: Bearer YOUR_ADMIN_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "max_workers": 1,
    "title": "Test HIT",
    "description": "Test description",
    "keywords": "test"
  }'
```

**Success response:**
```json
{
  "success": true,
  "hit_id": "3EXAMPLE123...",
  "hit_type_id": "3EXAMPLE456...",
  "max_assignments": 1,
  "reward": "0.05",
  "external_url": "http://localhost:5173/lobby"
}
```

**If you still get the error:**
- Wait 5-10 minutes for AWS to propagate changes
- Make sure you used the **sandbox** URL
- Check you're using the correct AWS account
- Verify email if you received a verification email

---

## 🔍 Verify Registration in MTurk Console

### Check Requester Dashboard

1. Go to: https://requestersandbox.mturk.com
2. Sign in with AWS credentials
3. You should see the Requester Dashboard
4. Check "Account" → "Account Settings"
5. Verify your account is active

### Check for Your Test HIT

1. Go to: https://requestersandbox.mturk.com/mturk/manageHITs
2. You should see your test HIT listed
3. Status should be "Assignable"

---

## 🚨 Common Issues

### Issue 1: "I don't see the Link Account page"

**Possible causes:**
- You're already registered (good!)
- You're on the wrong URL (production vs sandbox)
- You're not signed in with the correct AWS account

**Solution:**
- Try creating a HIT to test if you're already registered
- Make sure you're at: https://requestersandbox.mturk.com/developer
- Sign out and sign in again with correct AWS account

---

### Issue 2: "Payment method required"

**This is normal!** MTurk requires a payment method even for sandbox.

**Why?**
- Prevents abuse
- Required by AWS/MTurk policy
- Standard practice

**You won't be charged in sandbox** - the balance is virtual.

---

### Issue 3: "Email verification pending"

**Check your email:**
- Subject: "Verify your Amazon Mechanical Turk email"
- Check spam folder
- Wait a few minutes if not received

**Resend verification:**
- Go to MTurk account settings
- Click "Resend verification email"

---

### Issue 4: "Still getting error after registration"

**Wait a few minutes:**
- AWS needs time to propagate account linking
- Usually takes 1-5 minutes
- Can take up to 15 minutes in rare cases

**Verify your setup:**
```bash
# Check environment
cat .env | grep MTURK_ENVIRONMENT
# Should show: MTURK_ENVIRONMENT=sandbox

# Check AWS credentials
cat .env | grep AWS_ACCESS_KEY_ID
# Should show your access key

# Test connection
python -c "from backend.mturk_api import get_account_balance; print(get_account_balance())"
```

---

## 🎓 Production Registration

**For production (real workers, real money):**

1. Go to: https://requester.mturk.com (no "sandbox")
2. Follow the same steps
3. Add funds to your account
4. Update `.env`: `MTURK_ENVIRONMENT=production`

**Production requirements:**
- ✅ Same registration process
- ✅ Real payment method (will be charged)
- ✅ Add funds before creating HITs
- ✅ MTurk charges 20% commission
- ✅ Minimum $1.00 per HIT

---

## ✅ Registration Complete Checklist

After registration, you should be able to:

- [ ] ✅ Check account balance (shows $10,000 in sandbox)
- [ ] ✅ Create test HITs via API
- [ ] ✅ See HITs in MTurk Requester dashboard
- [ ] ✅ Accept HITs as a test worker
- [ ] ✅ Complete the full payment flow

---

## 📚 Next Steps

Once registered:

1. **Create a test worker account:**
   - Go to: https://workersandbox.mturk.com
   - Create a separate worker account
   - Use different email than requester

2. **Test the full flow:**
   - Create HIT via API
   - Accept HIT as worker
   - Complete game
   - Approve payment as admin

3. **Read the workflow guide:**
   - See `MTURK_WORKFLOW.md`
   - Understand worker journey
   - Learn admin payment process

---

## 🆘 Still Having Issues?

**Check these resources:**
- `MTURK_TROUBLESHOOTING.md` - Common issues
- `MTURK_API_SETUP.md` - Complete setup guide
- AWS MTurk docs: https://docs.aws.amazon.com/mturk/

**Contact AWS Support:**
- If registration fails repeatedly
- If payment method won't accept
- If email verification doesn't work

---

**Registration complete!** 🎉 You can now use the MTurk API!

