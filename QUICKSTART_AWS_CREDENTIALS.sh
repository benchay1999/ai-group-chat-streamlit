#!/bin/bash
# Quick helper script to guide you through getting AWS credentials

echo ""
echo "═══════════════════════════════════════════════════════════════"
echo "  MTurk Sandbox - AWS Credentials Quick Start"
echo "═══════════════════════════════════════════════════════════════"
echo ""
echo "You need AWS credentials to use MTurk API."
echo ""
echo "OPTION 1: I already have AWS credentials"
echo "  → Skip to Step 2 below"
echo ""
echo "OPTION 2: I need to create AWS credentials"
echo "  → Open this link in your browser:"
echo "     https://console.aws.amazon.com/iam/home#/users"
echo ""
echo "  → Follow these steps:"
echo "     1. Click 'Add users' button"
echo "     2. Username: mturk-sandbox"
echo "     3. Check: ✅ 'Access key - Programmatic access'"
echo "     4. Click 'Next: Permissions'"
echo "     5. Click 'Attach existing policies directly'"
echo "     6. Search: 'AdministratorAccess' (for testing)"
echo "        OR create custom policy with MTurk permissions"
echo "     7. Click through to 'Create user'"
echo "     8. ⚠️  DOWNLOAD the CSV or COPY both:"
echo "         - Access Key ID (starts with AKIA)"
echo "         - Secret Access Key (40 random characters)"
echo ""
echo "═══════════════════════════════════════════════════════════════"
echo "  Step 2: Update Your .env File"
echo "═══════════════════════════════════════════════════════════════"
echo ""
echo "Now that you have credentials, update your .env file:"
echo ""
read -p "Press ENTER to open .env file in nano editor..."
echo ""

# Open .env in nano
nano .env

echo ""
echo "═══════════════════════════════════════════════════════════════"
echo "  Step 3: Test Your Credentials"
echo "═══════════════════════════════════════════════════════════════"
echo ""
read -p "Press ENTER to test your credentials..."
echo ""

# Test credentials
python3 test_mturk_credentials.py

if [ $? -eq 0 ]; then
    echo ""
    echo "═══════════════════════════════════════════════════════════════"
    echo "  ✅ SUCCESS! You're all set!"
    echo "═══════════════════════════════════════════════════════════════"
    echo ""
    echo "Next steps:"
    echo "  1. Create a Standing HIT:"
    echo "     python3 backend/create_standing_hit.py"
    echo ""
    echo "  2. Restart your backend server to load new credentials"
    echo ""
else
    echo ""
    echo "═══════════════════════════════════════════════════════════════"
    echo "  ❌ Credentials test failed"
    echo "═══════════════════════════════════════════════════════════════"
    echo ""
    echo "Troubleshooting:"
    echo "  1. Make sure you copied the credentials exactly"
    echo "  2. No extra spaces or quotes"
    echo "  3. Access Key ID should start with 'AKIA'"
    echo "  4. Secret Key should be exactly 40 characters"
    echo ""
    echo "Try running this script again: ./QUICKSTART_AWS_CREDENTIALS.sh"
    echo ""
fi


