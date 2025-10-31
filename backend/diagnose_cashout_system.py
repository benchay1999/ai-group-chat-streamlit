#!/usr/bin/env python3
"""
Diagnose Cashout System Configuration
Checks all components to identify why cashouts aren't working
"""

import os
import sys
from dotenv import load_dotenv
import boto3
from pathlib import Path

# Add backend to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def diagnose_system():
    """Run comprehensive diagnosis of cashout system."""
    
    print("\n" + "="*70)
    print("CASHOUT SYSTEM DIAGNOSTIC")
    print("="*70)
    
    issues_found = []
    
    # Check 1: .env file exists and is readable
    print("\n1️⃣  Checking .env file...")
    
    project_root = Path(__file__).parent.parent
    env_file = project_root / '.env'
    
    if not env_file.exists():
        print(f"   ❌ .env file not found at: {env_file}")
        issues_found.append(".env file missing")
    else:
        print(f"   ✅ .env file found at: {env_file}")
        
        # Load environment variables
        load_dotenv(env_file)
        
        # Check 2: CASHOUT_HIT_ID is set
        print("\n2️⃣  Checking CASHOUT_HIT_ID...")
        hit_id = os.getenv('CASHOUT_HIT_ID')
        
        if not hit_id:
            print(f"   ❌ CASHOUT_HIT_ID not set in .env file")
            issues_found.append("CASHOUT_HIT_ID missing")
        else:
            print(f"   ✅ CASHOUT_HIT_ID found: {hit_id}")
            
            # Check 3: MTurk credentials
            print("\n3️⃣  Checking MTurk credentials...")
            aws_key = os.getenv('AWS_ACCESS_KEY_ID')
            aws_secret = os.getenv('AWS_SECRET_ACCESS_KEY')
            
            if not aws_key or not aws_secret:
                print(f"   ❌ AWS credentials missing")
                issues_found.append("AWS credentials missing")
            else:
                print(f"   ✅ AWS credentials found")
                
                # Check 4: MTurk environment
                print("\n4️⃣  Checking MTurk environment...")
                environment = os.getenv('MTURK_ENVIRONMENT', 'sandbox')
                print(f"   ℹ️  Environment: {environment.upper()}")
                
                endpoints = {
                    'sandbox': 'https://mturk-requester-sandbox.us-east-1.amazonaws.com',
                    'production': 'https://mturk-requester.us-east-1.amazonaws.com'
                }
                
                worker_endpoints = {
                    'sandbox': 'https://workersandbox.mturk.com',
                    'production': 'https://www.mturk.com'
                }
                
                # Check 5: Connect to MTurk and verify HIT
                print("\n5️⃣  Connecting to MTurk...")
                try:
                    mturk = boto3.client(
                        'mturk',
                        endpoint_url=endpoints[environment],
                        region_name='us-east-1',
                        aws_access_key_id=aws_key,
                        aws_secret_access_key=aws_secret
                    )
                    print(f"   ✅ Connected to MTurk ({environment})")
                    
                    # Check 6: Verify HIT exists
                    print("\n6️⃣  Verifying HIT...")
                    try:
                        response = mturk.get_hit(HITId=hit_id)
                        hit = response['HIT']
                        
                        print(f"   ✅ HIT exists: {hit_id}")
                        print(f"\n   📊 HIT Details:")
                        print(f"      Title: {hit['Title']}")
                        print(f"      Status: {hit['HITStatus']}")
                        print(f"      Max Assignments: {hit['MaxAssignments']:,}")
                        print(f"      Available: {hit['NumberOfAssignmentsAvailable']:,}")
                        print(f"      Completed: {hit['NumberOfAssignmentsCompleted']:,}")
                        print(f"      Pending: {hit['NumberOfAssignmentsPending']:,}")
                        
                        # Check if assignments are available
                        if hit['NumberOfAssignmentsAvailable'] == 0:
                            print(f"\n   ❌ PROBLEM: No assignments available!")
                            print(f"      All {hit['MaxAssignments']:,} assignments are used")
                            issues_found.append("No assignments available")
                        else:
                            print(f"\n   ✅ {hit['NumberOfAssignmentsAvailable']:,} assignments available")
                        
                        # Check 7: Generate worker URL
                        print("\n7️⃣  Generating worker URL...")
                        worker_url = f"{worker_endpoints[environment]}/mturk/preview?groupId={hit['HITGroupId']}"
                        print(f"   ✅ Worker URL:")
                        print(f"      {worker_url}")
                        
                        # Check 8: Compare with what backend would generate
                        print("\n8️⃣  Checking backend URL generation...")
                        print(f"   ℹ️  Backend should generate this URL:")
                        print(f"      {worker_url}")
                        
                        # Check 9: Verify cashout page
                        print("\n9️⃣  Checking cashout page URL...")
                        external_url = os.getenv('EXTERNAL_URL', 'http://localhost:3000')
                        cashout_page = f"{external_url.rstrip('/')}/cashout-confirm"
                        print(f"   ℹ️  Cashout confirmation page:")
                        print(f"      {cashout_page}")
                        
                    except Exception as e:
                        print(f"   ❌ HIT not found or error: {e}")
                        issues_found.append(f"HIT not found: {hit_id}")
                        
                        # Check if HIT exists in environment
                        print(f"\n   🔍 Searching for HITs in {environment}...")
                        try:
                            list_response = mturk.list_hits(MaxResults=100)
                            hits = list_response.get('HITs', [])
                            
                            if not hits:
                                print(f"   ⚠️  No HITs found in {environment} environment")
                                print(f"      You may need to create a new standing HIT")
                            else:
                                print(f"   ℹ️  Found {len(hits)} HIT(s) in {environment}:")
                                for h in hits[:5]:  # Show first 5
                                    print(f"      - {h['HITId']}: {h['Title'][:50]}")
                                    print(f"        Assignments: {h['NumberOfAssignmentsAvailable']}/{h['MaxAssignments']}")
                        except Exception as e2:
                            print(f"   ❌ Error listing HITs: {e2}")
                        
                except Exception as e:
                    print(f"   ❌ Failed to connect to MTurk: {e}")
                    issues_found.append("MTurk connection failed")
    
    # Summary
    print("\n" + "="*70)
    print("DIAGNOSIS SUMMARY")
    print("="*70)
    
    if issues_found:
        print(f"\n❌ {len(issues_found)} issue(s) found:\n")
        for i, issue in enumerate(issues_found, 1):
            print(f"   {i}. {issue}")
        
        print("\n" + "="*70)
        print("RECOMMENDED ACTIONS")
        print("="*70)
        
        if "CASHOUT_HIT_ID missing" in issues_found or any("HIT not found" in i for i in issues_found):
            print("\n🔧 Action Required: Update HIT ID")
            print("\n1. Create a new standing HIT:")
            print("   python create_standing_hit.py")
            print("\n2. Copy the HIT ID from the output")
            print("\n3. Update your .env file:")
            print("   CASHOUT_HIT_ID=<paste_hit_id_here>")
            print("\n4. Restart your backend server:")
            print("   pkill -f uvicorn")
            print("   uvicorn main:app --host 0.0.0.0 --port 8000 --reload")
        
        if "No assignments available" in issues_found:
            print("\n🔧 Action Required: Extend assignments")
            print("\n   python fix_hit_assignments.py --assignments 10000")
        
    else:
        print("\n✅ All checks passed!")
        print("\nYour cashout system appears to be configured correctly.")
        print("\nIf you're still having issues, please check:")
        print("   1. Backend server is running")
        print("   2. Backend has been restarted after .env changes")
        print("   3. You're clicking the correct HIT URL from the app")
    
    print("\n" + "="*70)
    
    return len(issues_found) == 0


if __name__ == '__main__':
    success = diagnose_system()
    sys.exit(0 if success else 1)

