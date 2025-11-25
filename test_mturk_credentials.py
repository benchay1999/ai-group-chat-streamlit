#!/usr/bin/env python3
"""
Quick test to verify MTurk sandbox credentials
"""
import os
from dotenv import load_dotenv
import boto3
from botocore.exceptions import ClientError

# Load environment
load_dotenv()

aws_key = os.getenv('AWS_ACCESS_KEY_ID')
aws_secret = os.getenv('AWS_SECRET_ACCESS_KEY')
environment = os.getenv('MTURK_ENVIRONMENT', 'sandbox')

print("=" * 60)
print("MTurk Sandbox Credentials Test")
print("=" * 60)
print(f"Environment: {environment}")
print(f"AWS Access Key ID: {aws_key[:8]}...{aws_key[-4:] if aws_key and len(aws_key) > 12 else 'NOT SET'}")
print(f"AWS Secret Key: {'SET (hidden)' if aws_secret else 'NOT SET'}")
print()

if not aws_key or not aws_secret:
    print("❌ ERROR: Credentials not set in .env file")
    print("\nPlease update .env with:")
    print("   AWS_ACCESS_KEY_ID=your-actual-key")
    print("   AWS_SECRET_ACCESS_KEY=your-actual-secret")
    exit(1)

if aws_key == 'your-aws-access-key-id':
    print("❌ ERROR: Using placeholder credentials")
    print("\nPlease replace placeholder values in .env with real AWS credentials")
    exit(1)

# Test connection to MTurk
endpoint = {
    'sandbox': 'https://mturk-requester-sandbox.us-east-1.amazonaws.com',
    'production': 'https://mturk-requester.us-east-1.amazonaws.com'
}[environment]

print(f"Testing connection to: {endpoint}")
print()

try:
    client = boto3.client(
        'mturk',
        endpoint_url=endpoint,
        region_name='us-east-1',
        aws_access_key_id=aws_key,
        aws_secret_access_key=aws_secret
    )
    
    # Test API call
    response = client.get_account_balance()
    balance = response['AvailableBalance']
    
    print("✅ SUCCESS! Credentials are valid")
    print(f"   Account Balance: ${balance}")
    print(f"   Environment: {environment.upper()}")
    print()
    print("You can now use MTurk API in your application!")
    
except ClientError as e:
    error_code = e.response['Error']['Code']
    error_msg = e.response['Error']['Message']
    
    print(f"❌ ERROR: {error_code}")
    print(f"   {error_msg}")
    print()
    
    if 'UnrecognizedClient' in error_code or 'InvalidClientToken' in error_code:
        print("🔍 This means your AWS credentials are invalid.")
        print("\nPossible causes:")
        print("  1. Access Key ID or Secret Key is incorrect")
        print("  2. Credentials are for a different AWS account")
        print("  3. IAM user doesn't have MTurk permissions")
        print("  4. Credentials have been deleted/deactivated")
        print()
        print("Please verify your credentials at:")
        print("  https://console.aws.amazon.com/iam/home#/users")
    
    elif 'RequestExpired' in error_code:
        print("🔍 Your system clock may be out of sync.")
        print("   Run: sudo ntpdate time.nist.gov")
    
    exit(1)

except Exception as e:
    print(f"❌ Unexpected error: {e}")
    exit(1)

print("=" * 60)
