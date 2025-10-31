#!/usr/bin/env python3
"""
Verify HIT Actually Exists in MTurk
Checks if the configured HIT ID exists and gets the correct HITGroupId
"""

import os
import sys
from dotenv import load_dotenv
import boto3

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
load_dotenv()

def verify_hit():
    """Verify the HIT exists and get correct URLs."""
    
    print("\n" + "="*70)
    print("HIT EXISTENCE VERIFICATION")
    print("="*70)
    
    # Get configuration
    hit_id = os.getenv('CASHOUT_HIT_ID')
    environment = os.getenv('MTURK_ENVIRONMENT', 'sandbox')
    
    print(f"\n📋 Configuration:")
    print(f"   HIT ID from .env: {hit_id}")
    print(f"   Environment: {environment}")
    
    if not hit_id:
        print("\n❌ CASHOUT_HIT_ID not set in .env file")
        return False
    
    # Setup MTurk client
    endpoints = {
        'sandbox': 'https://mturk-requester-sandbox.us-east-1.amazonaws.com',
        'production': 'https://mturk-requester.us-east-1.amazonaws.com'
    }
    
    worker_endpoints = {
        'sandbox': 'https://workersandbox.mturk.com',
        'production': 'https://www.mturk.com'
    }
    
    try:
        mturk = boto3.client(
            'mturk',
            endpoint_url=endpoints[environment],
            region_name='us-east-1',
            aws_access_key_id=os.getenv('AWS_ACCESS_KEY_ID'),
            aws_secret_access_key=os.getenv('AWS_SECRET_ACCESS_KEY')
        )
        print(f"✅ Connected to MTurk {environment}")
        
        # Try to get the HIT
        print(f"\n🔍 Checking if HIT {hit_id} exists...")
        
        try:
            response = mturk.get_hit(HITId=hit_id)
            hit = response['HIT']
            
            print(f"\n✅ HIT EXISTS!")
            print(f"\n📊 HIT Details:")
            print(f"   HIT ID: {hit['HITId']}")
            print(f"   HIT Type ID: {hit['HITTypeId']}")
            print(f"   HIT Group ID: {hit['HITGroupId']}")
            print(f"   Title: {hit['Title']}")
            print(f"   Status: {hit['HITStatus']}")
            print(f"   Reward: ${hit['Reward']}")
            print(f"   Max Assignments: {hit['MaxAssignments']:,}")
            print(f"   Available: {hit['NumberOfAssignmentsAvailable']:,}")
            print(f"   Completed: {hit['NumberOfAssignmentsCompleted']:,}")
            print(f"   Created: {hit['CreationTime']}")
            print(f"   Expires: {hit['Expiration']}")
            
            # Generate correct URLs
            hit_group_id = hit['HITGroupId']
            worker_preview_url = f"{worker_endpoints[environment]}/mturk/preview?groupId={hit_group_id}"
            
            print(f"\n🔗 CORRECT URLs:")
            print(f"   Worker Preview: {worker_preview_url}")
            
            # Test if the URL is different from what was shown
            shown_url = "https://workersandbox.mturk.com/mturk/preview?groupId=397QAO5SPUQ3VCXECMZ8EIOZW6AEFL"
            if worker_preview_url != shown_url:
                print(f"\n⚠️  WARNING: URL MISMATCH!")
                print(f"   Your app showed: {shown_url}")
                print(f"   Correct URL is:  {worker_preview_url}")
                print(f"\n   This means the backend is generating the wrong URL!")
            
            return True
            
        except mturk.exceptions.RequestError as e:
            if 'does not exist' in str(e).lower():
                print(f"\n❌ HIT DOES NOT EXIST!")
                print(f"   HIT ID {hit_id} was not found in {environment}")
                print(f"\n   This means:")
                print(f"   1. The HIT was deleted")
                print(f"   2. Wrong environment (check MTURK_ENVIRONMENT)")
                print(f"   3. .env has wrong HIT ID")
                
                # List existing HITs
                print(f"\n🔍 Searching for existing HITs in {environment}...")
                try:
                    list_response = mturk.list_hits(MaxResults=100)
                    hits = list_response.get('HITs', [])
                    
                    if not hits:
                        print(f"\n⚠️  NO HITs found in {environment}!")
                        print(f"   You need to create a new standing HIT:")
                        print(f"   python create_standing_hit.py")
                    else:
                        print(f"\n✅ Found {len(hits)} HIT(s) in {environment}:")
                        for idx, h in enumerate(hits, 1):
                            print(f"\n   {idx}. HIT ID: {h['HITId']}")
                            print(f"      Title: {h['Title']}")
                            print(f"      Reward: ${h['Reward']}")
                            print(f"      Assignments: {h['NumberOfAssignmentsAvailable']}/{h['MaxAssignments']}")
                            print(f"      Status: {h['HITStatus']}")
                            
                            if 'ChatGame' in h['Title'] or 'Redeem' in h['Title']:
                                print(f"      ⭐ THIS LOOKS LIKE YOUR CASHOUT HIT!")
                                print(f"      ⭐ Update your .env file:")
                                print(f"      ⭐ CASHOUT_HIT_ID={h['HITId']}")
                except Exception as e2:
                    print(f"   Error listing HITs: {e2}")
                
                return False
            else:
                raise
            
    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == '__main__':
    success = verify_hit()
    sys.exit(0 if success else 1)

