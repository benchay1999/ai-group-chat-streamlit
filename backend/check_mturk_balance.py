#!/usr/bin/env python3
"""
Check your MTurk account balance.
Useful for verifying funds before creating HITs.
"""

import os
from dotenv import load_dotenv
import boto3

# Load environment variables
load_dotenv()

def check_balance():
    """Check MTurk account balance."""
    
    environment = os.getenv('MTURK_ENVIRONMENT', 'sandbox')
    aws_access_key = os.getenv('AWS_ACCESS_KEY_ID')
    aws_secret_key = os.getenv('AWS_SECRET_ACCESS_KEY')
    
    endpoints = {
        'sandbox': 'https://mturk-requester-sandbox.us-east-1.amazonaws.com',
        'production': 'https://mturk-requester.us-east-1.amazonaws.com'
    }
    
    if not aws_access_key or not aws_secret_key:
        print("❌ ERROR: AWS credentials not found in .env file!")
        return
    
    print("=" * 70)
    print(f"  MTurk Account Balance Check - {environment.upper()}")
    print("=" * 70)
    
    try:
        mturk = boto3.client(
            'mturk',
            region_name='us-east-1',
            endpoint_url=endpoints[environment],
            aws_access_key_id=aws_access_key,
            aws_secret_access_key=aws_secret_key
        )
        
        balance = mturk.get_account_balance()
        available = balance['AvailableBalance']
        
        print(f"\n💰 Available Balance: ${available}")
        
        if environment == 'sandbox':
            print("\n📝 Note: This is FAKE MONEY for testing")
            if float(available) < 1.0:
                print("\n⚠️  Your sandbox balance is low!")
                print("   Go to: https://requestersandbox.mturk.com/developer")
                print("   The sandbox provides $10,000 in fake money automatically")
        else:
            print("\n💵 Note: This is REAL MONEY")
            if float(available) < 10.0:
                print("\n⚠️  Your balance is low for production use!")
                print("   Add funds at: https://requester.mturk.com/prepayments/new")
        
        print("\n" + "=" * 70)
        
    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        print("\nCommon issues:")
        print("  - Check AWS credentials in .env file")
        print("  - Verify MTURK_ENVIRONMENT setting")
        print("  - Check internet connection")
        print("=" * 70)


if __name__ == '__main__':
    check_balance()

