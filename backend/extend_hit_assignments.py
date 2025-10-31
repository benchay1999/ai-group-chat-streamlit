#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Extend the number of assignments for an existing HIT.
Useful when you've used up all assignments and need more for testing.
"""

import os
import sys
from dotenv import load_dotenv
import boto3

load_dotenv()

def extend_hit_assignments(hit_id, additional_assignments):
    """Add more assignments to an existing HIT."""
    
    environment = os.getenv('MTURK_ENVIRONMENT', 'sandbox')
    aws_access_key = os.getenv('AWS_ACCESS_KEY_ID')
    aws_secret_key = os.getenv('AWS_SECRET_ACCESS_KEY')
    
    endpoints = {
        'sandbox': 'https://mturk-requester-sandbox.us-east-1.amazonaws.com',
        'production': 'https://mturk-requester.us-east-1.amazonaws.com'
    }
    
    if not aws_access_key or not aws_secret_key:
        print("❌ ERROR: AWS credentials not found!")
        return False
    
    print(f"\n🔧 Extending HIT in {environment.upper()} environment...")
    print(f"   HIT ID: {hit_id}")
    print(f"   Adding: {additional_assignments} assignments")
    
    try:
        mturk = boto3.client(
            'mturk',
            region_name='us-east-1',
            endpoint_url=endpoints[environment],
            aws_access_key_id=aws_access_key,
            aws_secret_access_key=aws_secret_key
        )
        
        # Get current HIT info
        hit = mturk.get_hit(HITId=hit_id)
        current_max = hit['HIT']['MaxAssignments']
        
        print(f"\n📊 Current Status:")
        print(f"   Max Assignments: {current_max}")
        print(f"   Number Available: {hit['HIT']['NumberOfAssignmentsAvailable']}")
        print(f"   Number Pending: {hit['HIT']['NumberOfAssignmentsPending']}")
        print(f"   Number Completed: {hit['HIT']['NumberOfAssignmentsCompleted']}")
        
        # Extend assignments
        new_max = current_max + additional_assignments
        
        response = mturk.create_additional_assignments_for_hit(
            HITId=hit_id,
            NumberOfAdditionalAssignments=additional_assignments
        )
        
        print(f"\n✅ SUCCESS! HIT extended:")
        print(f"   Old Max: {current_max}")
        print(f"   New Max: {new_max}")
        print(f"   Added: {additional_assignments} assignments")
        
        # Check balance impact
        balance = mturk.get_account_balance()
        print(f"\n💰 Account Balance: ${balance['AvailableBalance']}")
        print(f"   (Pre-authorization for {additional_assignments} assignments at $0.01 each)")
        
        return True
        
    except Exception as e:
        print(f"\n❌ ERROR: Failed to extend HIT: {e}")
        return False


if __name__ == '__main__':
    print("=" * 70)
    print("  MTurk HIT Assignment Extender")
    print("=" * 70)
    
    # Get HIT ID from environment or command line
    hit_id = os.getenv('CASHOUT_HIT_ID')
    
    if len(sys.argv) > 1:
        hit_id = sys.argv[1]
    
    if not hit_id:
        print("\n❌ ERROR: No HIT ID provided!")
        print("\nUsage:")
        print("  python extend_hit_assignments.py [HIT_ID] [NUMBER]")
        print("\nOr set CASHOUT_HIT_ID in your .env file")
        sys.exit(1)
    
    # Get number of assignments to add
    num_to_add = 100  # Default
    if len(sys.argv) > 2:
        try:
            num_to_add = int(sys.argv[2])
        except ValueError:
            print(f"❌ Invalid number: {sys.argv[2]}")
            sys.exit(1)
    
    print(f"\n📋 Configuration:")
    print(f"   HIT ID: {hit_id}")
    print(f"   Adding: {num_to_add} assignments")
    print(f"   Environment: {os.getenv('MTURK_ENVIRONMENT', 'sandbox')}")
    
    # Confirm
    confirm = input("\nContinue? (yes/no): ").strip().lower()
    if confirm != 'yes':
        print("❌ Cancelled")
        sys.exit(0)
    
    success = extend_hit_assignments(hit_id, num_to_add)
    
    if success:
        print("\n" + "=" * 70)
        print("✅ All done! You can now accept the HIT again.")
        print("=" * 70)
    else:
        sys.exit(1)

