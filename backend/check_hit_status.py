#!/usr/bin/env python3
"""
Check MTurk HIT Status
Shows current assignment availability and details for the cashout HIT
"""

import os
import sys
from dotenv import load_dotenv
import boto3
from decimal import Decimal

# Add backend to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

load_dotenv()

def check_hit_status():
    """Check the status of the cashout HIT."""
    
    print("\n" + "="*70)
    print("MTurk HIT Status Checker")
    print("="*70)
    
    # Get HIT ID from environment
    hit_id = os.getenv('CASHOUT_HIT_ID')
    
    if not hit_id:
        print("\n❌ ERROR: CASHOUT_HIT_ID not found in .env file")
        print("\nPlease set CASHOUT_HIT_ID in your .env file")
        return None
    
    print(f"\n📋 Checking HIT: {hit_id}")
    
    # Get environment settings
    environment = os.getenv('MTURK_ENVIRONMENT', 'sandbox')
    
    endpoints = {
        'sandbox': 'https://mturk-requester-sandbox.us-east-1.amazonaws.com',
        'production': 'https://mturk-requester.us-east-1.amazonaws.com'
    }
    
    worker_endpoints = {
        'sandbox': 'https://workersandbox.mturk.com',
        'production': 'https://www.mturk.com'
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
        return None
    
    try:
        # Get HIT details
        response = mturk.get_hit(HITId=hit_id)
        hit = response['HIT']
        
        print("\n" + "="*70)
        print("HIT DETAILS")
        print("="*70)
        
        print(f"\n📝 Title: {hit['Title']}")
        print(f"💰 Reward: ${hit['Reward']}")
        print(f"📊 Status: {hit['HITStatus']}")
        
        print(f"\n📈 ASSIGNMENTS:")
        print(f"   Max Assignments: {hit['MaxAssignments']:,}")
        print(f"   Available: {hit['NumberOfAssignmentsAvailable']:,}")
        print(f"   Pending: {hit['NumberOfAssignmentsPending']:,}")
        print(f"   Completed: {hit['NumberOfAssignmentsCompleted']:,}")
        
        # Calculate usage
        used = hit['NumberOfAssignmentsCompleted'] + hit['NumberOfAssignmentsPending']
        percentage_used = (used / hit['MaxAssignments']) * 100 if hit['MaxAssignments'] > 0 else 0
        
        print(f"\n📊 USAGE:")
        print(f"   Used: {used:,} / {hit['MaxAssignments']:,}")
        print(f"   Percentage: {percentage_used:.2f}%")
        print(f"   Remaining: {hit['NumberOfAssignmentsAvailable']:,}")
        
        print(f"\n⏰ TIMING:")
        print(f"   Created: {hit['CreationTime']}")
        print(f"   Expiration: {hit['Expiration']}")
        
        print(f"\n🔗 URLS:")
        worker_url = f"{worker_endpoints[environment]}/mturk/preview?groupId={hit['HITGroupId']}"
        print(f"   Worker URL: {worker_url}")
        
        # Diagnosis
        print("\n" + "="*70)
        print("DIAGNOSIS")
        print("="*70)
        
        if hit['NumberOfAssignmentsAvailable'] == 0:
            print("\n❌ PROBLEM FOUND: No assignments available!")
            print(f"   Max Assignments: {hit['MaxAssignments']:,}")
            print(f"   Completed: {hit['NumberOfAssignmentsCompleted']:,}")
            print(f"   Pending: {hit['NumberOfAssignmentsPending']:,}")
            
            if hit['MaxAssignments'] == 1:
                print("\n⚠️  CRITICAL: HIT was created with MaxAssignments=1")
                print("   This means only ONE cashout is possible!")
                print("\n   SOLUTION: You need to either:")
                print("   1. Extend this HIT's assignments (run: python extend_hit_assignments.py)")
                print("   2. Create a NEW standing HIT with higher MaxAssignments")
            else:
                print(f"\n⚠️  All {hit['MaxAssignments']:,} assignments have been used")
                print("\n   SOLUTION: Extend assignments (run: python extend_hit_assignments.py)")
        
        elif hit['NumberOfAssignmentsAvailable'] < 10:
            print(f"\n⚠️  WARNING: Only {hit['NumberOfAssignmentsAvailable']} assignments remaining")
            print("   Consider extending soon to avoid running out")
        else:
            print(f"\n✅ HIT is healthy: {hit['NumberOfAssignmentsAvailable']:,} assignments available")
        
        print("\n" + "="*70)
        
        return hit
        
    except Exception as e:
        print(f"\n❌ ERROR: Failed to get HIT status: {e}")
        import traceback
        traceback.print_exc()
        return None


if __name__ == '__main__':
    check_hit_status()

