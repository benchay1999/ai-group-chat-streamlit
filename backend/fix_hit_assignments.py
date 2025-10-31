#!/usr/bin/env python3
"""
Fix HIT Assignments
Extends the MaxAssignments for the cashout HIT to allow more cashouts
"""

import os
import sys
from dotenv import load_dotenv
import boto3

# Add backend to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

load_dotenv()

def extend_hit_assignments(additional_assignments=10000):
    """
    Extend the number of assignments for the cashout HIT.
    
    Args:
        additional_assignments: Number of assignments to add (default: 10,000)
    """
    
    print("\n" + "="*70)
    print("MTurk HIT Assignment Extender")
    print("="*70)
    
    # Get HIT ID from environment
    hit_id = os.getenv('CASHOUT_HIT_ID')
    
    if not hit_id:
        print("\n❌ ERROR: CASHOUT_HIT_ID not found in .env file")
        return False
    
    print(f"\n📋 Target HIT: {hit_id}")
    
    # Get environment settings
    environment = os.getenv('MTURK_ENVIRONMENT', 'sandbox')
    
    endpoints = {
        'sandbox': 'https://mturk-requester-sandbox.us-east-1.amazonaws.com',
        'production': 'https://mturk-requester.us-east-1.amazonaws.com'
    }
    
    print(f"🌍 Environment: {environment.upper()}")
    
    # Initialize MTurk client
    try:
        mturk = boto3.client(
            'mturk',
            endpoint_url=endpoints[environment],
            region_name='us-east-1',
            aws_access_key_id=os.getenv('AWS_ACCESS_KEY_ID'),
            aws_secret_access_key=os.getenv('AWS_SECRET_ACCESS_KEY')
        )
        print("✅ Connected to MTurk")
    except Exception as e:
        print(f"\n❌ ERROR: Failed to connect to MTurk: {e}")
        return False
    
    try:
        # Get current HIT status
        print("\n📊 Checking current HIT status...")
        response = mturk.get_hit(HITId=hit_id)
        hit = response['HIT']
        
        current_max = hit['MaxAssignments']
        available = hit['NumberOfAssignmentsAvailable']
        pending = hit['NumberOfAssignmentsPending']
        completed = hit['NumberOfAssignmentsCompleted']
        
        print(f"\n   Current MaxAssignments: {current_max:,}")
        print(f"   Available: {available:,}")
        print(f"   Pending: {pending:,}")
        print(f"   Completed: {completed:,}")
        
        # Calculate new max
        new_max = current_max + additional_assignments
        
        print(f"\n💡 Plan:")
        print(f"   Current Max: {current_max:,}")
        print(f"   Adding: {additional_assignments:,}")
        print(f"   New Max: {new_max:,}")
        
        # Estimate cost
        reward = float(hit['Reward'])
        estimated_cost = additional_assignments * reward
        print(f"\n💰 Estimated pre-authorization: ${estimated_cost:.2f}")
        
        # Confirm
        print("\n" + "="*70)
        print("⚠️  CONFIRMATION REQUIRED")
        print("="*70)
        print(f"\nYou are about to extend the HIT by {additional_assignments:,} assignments")
        print(f"MTurk will pre-authorize an additional ${estimated_cost:.2f}")
        
        if environment == 'production':
            print("\n⚠️  WARNING: This is PRODUCTION environment (real money!)")
        
        response_input = input("\nType 'EXTEND' to continue: ")
        
        if response_input != 'EXTEND':
            print("\n❌ Extension cancelled")
            return False
        
        # Extend the HIT
        print(f"\n🔄 Extending HIT assignments...")
        mturk.create_additional_assignments_for_hit(
            HITId=hit_id,
            NumberOfAdditionalAssignments=additional_assignments
        )
        
        print(f"✅ SUCCESS! HIT extended")
        
        # Verify
        print("\n📊 Verifying new status...")
        response = mturk.get_hit(HITId=hit_id)
        hit = response['HIT']
        
        print(f"\n   New MaxAssignments: {hit['MaxAssignments']:,}")
        print(f"   Available: {hit['NumberOfAssignmentsAvailable']:,}")
        print(f"   Completed: {hit['NumberOfAssignmentsCompleted']:,}")
        
        print("\n" + "="*70)
        print("✅ HIT SUCCESSFULLY EXTENDED")
        print("="*70)
        print(f"\nYour cashout HIT now supports {hit['MaxAssignments']:,} total cashouts!")
        print(f"Workers can now cash out {hit['NumberOfAssignmentsAvailable']:,} more times.")
        
        return True
        
    except Exception as e:
        print(f"\n❌ ERROR: Failed to extend HIT: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == '__main__':
    import argparse
    
    parser = argparse.ArgumentParser(description='Extend MTurk HIT assignments')
    parser.add_argument(
        '--assignments',
        type=int,
        default=10000,
        help='Number of additional assignments to add (default: 10000)'
    )
    
    args = parser.parse_args()
    
    print(f"\nAdding {args.assignments:,} additional assignments...")
    extend_hit_assignments(args.assignments)

