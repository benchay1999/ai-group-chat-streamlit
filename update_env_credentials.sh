#!/bin/bash
# Helper script to update .env with your AWS credentials

echo ""
echo "═══════════════════════════════════════════════════════════════"
echo "  Update AWS Credentials in .env"
echo "═══════════════════════════════════════════════════════════════"
echo ""
echo "You need to provide your ACTUAL AWS credentials."
echo ""
echo "⚠️  IMPORTANT:"
echo "   - Access Key ID starts with 'AKIA' (20 characters)"
echo "   - Secret Access Key is 40 random characters"
echo "   - These are SECRET - don't share them!"
echo ""
echo "Where to find them:"
echo "   - Downloaded CSV from AWS IAM"
echo "   - AWS Console → IAM → Users → Security Credentials"
echo "   - Email from AWS when you created IAM user"
echo ""
echo "Don't have credentials? See: GET_MTURK_SANDBOX_CREDENTIALS.md"
echo ""
echo "═══════════════════════════════════════════════════════════════"
echo ""

# Get credentials from user
read -p "Enter your AWS Access Key ID (starts with AKIA): " access_key
read -s -p "Enter your AWS Secret Access Key (40 chars, hidden): " secret_key
echo ""
echo ""

# Validate format
if [[ ! $access_key =~ ^AKIA[A-Z0-9]{16}$ ]]; then
    echo "❌ ERROR: Access Key ID format looks wrong"
    echo "   Expected: Starts with AKIA, total 20 characters"
    echo "   Got: $access_key (${#access_key} characters)"
    echo ""
    echo "Double-check your credentials and try again."
    exit 1
fi

if [[ ${#secret_key} -ne 40 ]]; then
    echo "❌ ERROR: Secret Access Key length is wrong"
    echo "   Expected: 40 characters"
    echo "   Got: ${#secret_key} characters"
    echo ""
    echo "Double-check your credentials and try again."
    exit 1
fi

# Backup .env
cp .env .env.backup
echo "📋 Backed up .env to .env.backup"

# Update .env file
sed -i "s|AWS_ACCESS_KEY_ID=.*|AWS_ACCESS_KEY_ID=$access_key|" .env
sed -i "s|AWS_SECRET_ACCESS_KEY=.*|AWS_SECRET_ACCESS_KEY=$secret_key|" .env

echo "✅ Updated .env file"
echo ""
echo "Testing credentials..."
echo ""

# Test credentials
python3 test_mturk_credentials.py

if [ $? -eq 0 ]; then
    echo ""
    echo "═══════════════════════════════════════════════════════════════"
    echo "  🎉 SUCCESS! Your credentials work!"
    echo "═══════════════════════════════════════════════════════════════"
    echo ""
    rm .env.backup
else
    echo ""
    echo "═══════════════════════════════════════════════════════════════"
    echo "  ❌ Credentials don't work"
    echo "═══════════════════════════════════════════════════════════════"
    echo ""
    echo "Restoring backup..."
    mv .env.backup .env
    echo ""
    echo "Possible issues:"
    echo "  1. Access Key ID or Secret Key is incorrect"
    echo "  2. IAM user doesn't have MTurk permissions"
    echo "  3. Credentials were deactivated"
    echo ""
    echo "Verify your credentials in AWS IAM console:"
    echo "  https://console.aws.amazon.com/iam/home#/users"
    exit 1
fi


