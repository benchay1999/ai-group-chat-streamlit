# How to Get MTurk Sandbox Credentials

## The Problem
You're seeing this error:
```
UnrecognizedClientException: The security token included in the request is invalid
```

This happens because your `.env` file has **placeholder credentials** instead of real AWS credentials.

## Quick Fix: 3 Steps

### Step 1: Get AWS Credentials

#### 1.1 Log into AWS Console
- Go to: https://console.aws.amazon.com/iam/
- Sign in with your AWS account (or create one at https://aws.amazon.com/)

#### 1.2 Create IAM User (if you don't have one)
1. Click **"Users"** in left sidebar
2. Click **"Add users"** button
3. **User name**: `mturk-sandbox` (or any name you want)
4. **Select AWS credential type**: Check ✅ **"Access key - Programmatic access"**
5. Click **"Next: Permissions"**

#### 1.3 Grant MTurk Permissions
1. Click **"Attach existing policies directly"**
2. Click **"Create policy"** button (opens new tab)
3. Click **"JSON"** tab
4. Paste this policy:

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "mturk-requester:*"
      ],
      "Resource": "*"
    }
  ]
}
```

5. Click **"Next: Tags"** (skip tags)
6. Click **"Next: Review"**
7. **Name**: `MTurkFullAccess`
8. Click **"Create policy"**
9. Go back to the user creation tab
10. Click the **refresh** button
11. Search for `MTurkFullAccess`
12. Check the box next to it
13. Click **"Next: Tags"** → **"Next: Review"** → **"Create user"**

#### 1.4 Save Your Credentials
**⚠️ CRITICAL: The secret key is only shown ONCE!**

You'll see a screen like this:
```
Access key ID:     AKIAIOSFODNN7EXAMPLE
Secret access key: wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY
```

**Click "Download .csv"** or copy both values immediately.

### Step 2: Update Your .env File

1. Open your `.env` file:
```bash
cd /home/wschay/ai-group-chat-streamlit
nano .env
```

2. Find these lines:
```bash
AWS_ACCESS_KEY_ID=your-aws-access-key-id
AWS_SECRET_ACCESS_KEY=your-aws-secret-access-key
```

3. Replace with your **actual credentials**:
```bash
AWS_ACCESS_KEY_ID=AKIAIOSFODNN7EXAMPLE
AWS_SECRET_ACCESS_KEY=wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY
```

4. Make sure this line is also set:
```bash
MTURK_ENVIRONMENT=sandbox
```

5. Save and exit (Ctrl+O, Enter, Ctrl+X)

### Step 3: Test Your Credentials

Run the test script:
```bash
cd /home/wschay/ai-group-chat-streamlit
python3 test_mturk_credentials.py
```

**Expected output:**
```
✅ SUCCESS! Credentials are valid
   Account Balance: $10000.00
   Environment: SANDBOX
```

Note: Sandbox accounts start with $10,000 in fake money for testing.

## Common Issues

### Issue: "UnrecognizedClientException"
- **Cause**: Invalid credentials
- **Fix**: Double-check you copied the Access Key ID and Secret Key correctly
- **Verify**: Make sure there are no extra spaces or line breaks

### Issue: "AccessDenied"
- **Cause**: IAM user doesn't have MTurk permissions
- **Fix**: Go back to IAM → Users → Your User → Permissions → Add the MTurkFullAccess policy

### Issue: "RequestExpired"
- **Cause**: System clock is out of sync
- **Fix**: Run `sudo ntpdate time.nist.gov` to sync your clock

### Issue: Still seeing placeholder values
- **Cause**: You edited the wrong `.env` file
- **Fix**: Make sure you're editing `/home/wschay/ai-group-chat-streamlit/.env`
- **Verify**: Run `cat /home/wschay/ai-group-chat-streamlit/.env | grep AWS_ACCESS_KEY_ID`

## Security Best Practices

1. **Never commit .env to git**
   - `.env` is already in `.gitignore`
   - Double check: `git status` should NOT show `.env`

2. **Use sandbox for testing**
   - Keep `MTURK_ENVIRONMENT=sandbox` during development
   - Sandbox uses fake money, no real charges

3. **Rotate credentials periodically**
   - Delete old access keys in IAM console
   - Create new ones every few months

4. **Use separate IAM users**
   - Don't use root account credentials
   - Create dedicated IAM user for MTurk only

## MTurk Sandbox vs Production

| Feature | Sandbox | Production |
|---------|---------|------------|
| Money | Fake ($10,000 test balance) | Real (requires adding funds) |
| Workers | Fake (you test yourself) | Real MTurk workers |
| Credentials | Same AWS credentials | Same AWS credentials |
| Endpoint | `mturk-requester-sandbox.us-east-1.amazonaws.com` | `mturk-requester.us-east-1.amazonaws.com` |
| Environment Variable | `MTURK_ENVIRONMENT=sandbox` | `MTURK_ENVIRONMENT=production` |

## Next Steps

After your credentials work:

1. **Create a Standing HIT** (for cashouts):
```bash
cd /home/wschay/ai-group-chat-streamlit
python3 backend/create_standing_hit.py
```

2. **Restart your backend server**:
```bash
# The server needs to reload the new .env values
# Stop the current server (Ctrl+C) and restart it
```

3. **Test cashout flow**:
- Play a game and earn gems
- Try cashing out to verify everything works

## Resources

- **AWS IAM Console**: https://console.aws.amazon.com/iam/
- **MTurk Requester Sandbox**: https://requestersandbox.mturk.com/
- **MTurk API Documentation**: https://docs.aws.amazon.com/AWSMechTurk/latest/AWSMturkAPI/Welcome.html
- **AWS CLI Configuration**: https://docs.aws.amazon.com/cli/latest/userguide/cli-configure-files.html

## Still Having Issues?

If you're still stuck:

1. **Check AWS IAM User**:
   - https://console.aws.amazon.com/iam/home#/users
   - Verify user exists and has MTurk permissions

2. **Verify credentials format**:
   - Access Key ID should start with `AKIA`
   - Secret Key should be exactly 40 characters
   - No quotes, spaces, or special characters

3. **Test with AWS CLI** (if installed):
```bash
aws configure set aws_access_key_id YOUR_KEY_ID
aws configure set aws_secret_access_key YOUR_SECRET_KEY
aws mturk get-account-balance --endpoint-url https://mturk-requester-sandbox.us-east-1.amazonaws.com --region us-east-1
```

4. **Check server logs**:
```bash
# When you start your backend, you should see:
✅ MTurk client initialized successfully (sandbox environment)
   Account Balance: $10000.00
```

Good luck! 🚀

