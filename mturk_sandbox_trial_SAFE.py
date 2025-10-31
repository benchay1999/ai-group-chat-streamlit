"""
MTurk Sandbox Trial - SECURE VERSION
Tests MTurk API connection using credentials from environment variables.

Usage:
    1. Set AWS credentials in .env file:
       AWS_ACCESS_KEY_ID=your_key
       AWS_SECRET_ACCESS_KEY=your_secret
    
    2. Run: python mturk_sandbox_trial_SAFE.py
"""

import boto3
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Get credentials from environment
aws_access_key_id = os.getenv('AWS_ACCESS_KEY_ID')
aws_secret_access_key = os.getenv('AWS_SECRET_ACCESS_KEY')

if not aws_access_key_id or not aws_secret_access_key:
    print("❌ ERROR: AWS credentials not found!")
    print("Please set AWS_ACCESS_KEY_ID and AWS_SECRET_ACCESS_KEY in your .env file")
    exit(1)

# MTurk sandbox endpoint
endpoint_url = 'https://mturk-requester-sandbox.us-east-1.amazonaws.com'

# Uncomment for production (BE CAREFUL!)
# endpoint_url = 'https://mturk-requester.us-east-1.amazonaws.com'

try:
    client = boto3.client(
        'mturk',
        endpoint_url=endpoint_url,
        region_name='us-east-1',
        aws_access_key_id=aws_access_key_id,
        aws_secret_access_key=aws_secret_access_key,
    )
    
    # Get account balance
    balance_response = client.get_account_balance()
    available_balance = balance_response['AvailableBalance']
    
    print(f"✅ Successfully connected to MTurk Sandbox!")
    print(f"💰 Available Balance: {available_balance}")
    print(f"   (Sandbox always shows $10,000.00)")
    
except Exception as e:
    print(f"❌ Error connecting to MTurk: {e}")
    print("Please check your AWS credentials and try again.")
    exit(1)

