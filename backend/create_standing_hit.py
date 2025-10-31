#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Create a standing MTurk HIT for the cashout redemption system.
Run this script once to create the HIT, then add the HIT ID to your .env file.
"""

import os
import sys
from dotenv import load_dotenv
import boto3

# Load environment variables
load_dotenv()

def create_standing_hit():
    """Create a standing HIT for cashout redemptions."""
    
    # Get configuration from environment
    environment = os.getenv('MTURK_ENVIRONMENT', 'sandbox')
    aws_access_key = os.getenv('AWS_ACCESS_KEY_ID')
    aws_secret_key = os.getenv('AWS_SECRET_ACCESS_KEY')
    external_url = os.getenv('EXTERNAL_URL', 'http://localhost:5173')
    
    # Determine endpoint based on environment
    endpoints = {
        'sandbox': 'https://mturk-requester-sandbox.us-east-1.amazonaws.com',
        'production': 'https://mturk-requester.us-east-1.amazonaws.com'
    }
    
    if not aws_access_key or not aws_secret_key:
        print("❌ ERROR: AWS credentials not found in .env file!")
        print("   Please set AWS_ACCESS_KEY_ID and AWS_SECRET_ACCESS_KEY")
        return None
    
    # SAFETY CHECK: Warn about production environment
    if environment == 'production':
        print("\n" + "=" * 70)
        print("⚠️  WARNING: PRODUCTION ENVIRONMENT DETECTED!")
        print("=" * 70)
        print("\n   You are about to create a HIT in PRODUCTION mode.")
        print("   This will use REAL MONEY from your MTurk account.")
        print("\n   Are you sure you want to proceed?")
        print("   (Type 'yes' to continue, anything else to switch to sandbox)")
        print("=" * 70)
        
        confirm = input("\nContinue in PRODUCTION? (yes/no): ").strip().lower()
        if confirm != 'yes':
            print("\n❌ Cancelled. Please set MTURK_ENVIRONMENT=sandbox in your .env file")
            print("   and run this script again to create a sandbox HIT first.")
            return None
    else:
        print("\n" + "=" * 70)
        print("✅ SANDBOX MODE - Safe for Testing")
        print("=" * 70)
        print("\n   You are using the MTurk SANDBOX environment.")
        print("   This uses fake money and is safe for testing.")
        print("=" * 70)
    
    print(f"\n🔧 Creating standing HIT in {environment.upper()} environment...")
    print(f"   External URL: {external_url}")
    print(f"   Endpoint: {endpoints[environment]}")
    
    # Initialize MTurk client
    try:
        mturk = boto3.client(
            'mturk',
            region_name='us-east-1',
            endpoint_url=endpoints[environment],
            aws_access_key_id=aws_access_key,
            aws_secret_access_key=aws_secret_key
        )
        
        # Check account balance first
        balance = mturk.get_account_balance()
        print(f"\n💰 Account Balance: ${balance['AvailableBalance']}")
        
    except Exception as e:
        print(f"❌ ERROR: Failed to connect to MTurk: {e}")
        return None
    
    # Determine the cashout URL based on external URL
    base_url = external_url.replace('/lobby', '').rstrip('/')
    cashout_url = f"{base_url}/cashout-confirm"
    
    # Determine max assignments based on environment
    # Sandbox: Lower number to avoid pre-authorization issues
    # Production: Higher number for actual use
    max_assignments = 1000 if environment == 'sandbox' else 99999
    
    print(f"\n📝 HIT Details:")
    print(f"   Title: ChatGame - Redeem Your Earnings (Instant Payment)")
    print(f"   Reward: $0.01 (base)")
    print(f"   Max Assignments: {max_assignments:,}")
    print(f"   Lifetime: 1 year")
    print(f"   Cashout URL: {cashout_url}")
    
    # Warn about pre-authorization
    estimated_hold = max_assignments * 0.01
    print(f"\n💡 MTurk will pre-authorize ~${estimated_hold:.2f} from your account")
    print(f"   Current balance: ${balance['AvailableBalance']}")
    
    # Create the ExternalQuestion XML
    question = f"""
<ExternalQuestion xmlns="http://mechanicalturk.amazonaws.com/AWSMechanicalTurkDataSchemas/2006-07-14/ExternalQuestion.xsd">
  <ExternalURL>{cashout_url}</ExternalURL>
  <FrameHeight>600</FrameHeight>
</ExternalQuestion>
"""
    
    try:
        # Create the HIT
        response = mturk.create_hit(
            Title='ChatGame - Redeem Your Earnings (Instant Payment)',
            Description='Redeem a unique code from the ChatGame to receive your earned payment. Payments are approved instantly. Each code can only be used once.',
            Keywords='games, redemption, instant payment, earnings, bonus',
            Reward='0.01',  # Base reward (actual payment varies per code)
            MaxAssignments=max_assignments,  # Reasonable number for standing HIT
            LifetimeInSeconds=31536000,  # 1 year (365 days)
            AssignmentDurationInSeconds=3600,  # 1 hour to complete
            AutoApprovalDelayInSeconds=3600,  # Auto-approve after 1 hour if not manually approved
            Question=question,
            QualificationRequirements=[]  # No restrictions, all workers can see it
        )
        
        hit_id = response['HIT']['HITId']
        hit_type_id = response['HIT']['HITTypeId']
        
        print(f"\n✅ SUCCESS! Standing HIT created:")
        print(f"\n   HIT ID: {hit_id}")
        print(f"   HIT Type ID: {hit_type_id}")
        
        # Determine worker URL
        worker_urls = {
            'sandbox': f'https://workersandbox.mturk.com/mturk/preview?groupId={hit_type_id}',
            'production': f'https://www.mturk.com/mturk/preview?groupId={hit_type_id}'
        }
        
        print(f"\n🔗 Worker Preview URL:")
        print(f"   {worker_urls[environment]}")
        
        print(f"\n📋 NEXT STEPS:")
        print(f"   1. Add this to your .env file:")
        print(f"      CASHOUT_HIT_ID={hit_id}")
        print(f"   2. Restart your backend server")
        print(f"   3. Test by requesting a cashout in your app")
        print(f"   4. Workers will see this HIT at the preview URL above")
        
        return hit_id
        
    except Exception as e:
        print(f"\n❌ ERROR: Failed to create HIT: {e}")
        return None


def check_existing_hits():
    """Check if there are any existing HITs."""
    
    environment = os.getenv('MTURK_ENVIRONMENT', 'sandbox')
    aws_access_key = os.getenv('AWS_ACCESS_KEY_ID')
    aws_secret_key = os.getenv('AWS_SECRET_ACCESS_KEY')
    
    endpoints = {
        'sandbox': 'https://mturk-requester-sandbox.us-east-1.amazonaws.com',
        'production': 'https://mturk-requester.us-east-1.amazonaws.com'
    }
    
    try:
        mturk = boto3.client(
            'mturk',
            region_name='us-east-1',
            endpoint_url=endpoints[environment],
            aws_access_key_id=aws_access_key,
            aws_secret_access_key=aws_secret_key
        )
        
        hits = mturk.list_hits(MaxResults=10)
        
        if hits['NumResults'] > 0:
            print(f"\n📋 Found {hits['NumResults']} existing HIT(s):")
            for hit in hits['HITs']:
                print(f"\n   HIT ID: {hit['HITId']}")
                print(f"   Title: {hit['Title']}")
                print(f"   Status: {hit['HITStatus']}")
                print(f"   Available: {hit['NumberOfAssignmentsAvailable']}")
                print(f"   Pending: {hit['NumberOfAssignmentsPending']}")
                print(f"   Completed: {hit['NumberOfAssignmentsCompleted']}")
        else:
            print("\n📋 No existing HITs found.")
            
    except Exception as e:
        print(f"❌ ERROR: Failed to list HITs: {e}")


if __name__ == '__main__':
    print("=" * 70)
    print("  MTurk Standing HIT Creator for Cashout System")
    print("=" * 70)
    
    # Check environment and warn user
    environment = os.getenv('MTURK_ENVIRONMENT', 'sandbox')
    
    if environment != 'sandbox':
        print("\n⚠️  WARNING: Your .env file has MTURK_ENVIRONMENT=" + environment)
        print("\n   It's HIGHLY RECOMMENDED to test in sandbox first!")
        print("   Set MTURK_ENVIRONMENT=sandbox in your .env file")
        print("   to create a test HIT with fake money.")
        print("\n   Do you want to continue anyway?")
        
        continue_anyway = input("\nContinue with current environment? (yes/no): ").strip().lower()
        if continue_anyway != 'yes':
            print("\n✅ Good choice! Update your .env file:")
            print("   MTURK_ENVIRONMENT=sandbox")
            print("\nThen run this script again.")
            sys.exit(0)
    else:
        print("\n✅ Sandbox mode detected - safe for testing!")
    
    # Check for existing HITs first
    check_existing_hits()
    
    print("\n" + "=" * 70)
    confirm = input("\nDo you want to create a NEW standing HIT? (yes/no): ").strip().lower()
    
    if confirm in ['yes', 'y']:
        hit_id = create_standing_hit()
        
        if hit_id:
            print("\n" + "=" * 70)
            print("✅ Setup complete! Don't forget to update your .env file.")
            print("=" * 70)
            sys.exit(0)
        else:
            print("\n" + "=" * 70)
            print("❌ Failed to create HIT. Please check the errors above.")
            print("=" * 70)
            sys.exit(1)
    else:
        print("\n❌ Cancelled. No HIT was created.")
        sys.exit(0)

