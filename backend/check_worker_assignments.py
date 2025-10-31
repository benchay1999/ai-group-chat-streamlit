#!/usr/bin/env python3
"""
Check Worker's Assignment Status
Shows if there are pending/active assignments blocking new cashouts
"""

import os
import sys
from dotenv import load_dotenv
import boto3
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
load_dotenv()

def check_worker_assignments(worker_id):
    """Check if worker has pending assignments for the cashout HIT."""
    
    print("\n" + "="*70)
    print("WORKER ASSIGNMENT STATUS CHECKER")
    print("="*70)
    
    # Get HIT ID
    hit_id = os.getenv('CASHOUT_HIT_ID')
    if not hit_id:
        print("\n❌ CASHOUT_HIT_ID not set in .env")
        return False
    
    print(f"\n🎯 Target HIT: {hit_id}")
    print(f"👤 Worker ID: {worker_id}")
    
    # Setup MTurk client
    environment = os.getenv('MTURK_ENVIRONMENT', 'sandbox')
    endpoints = {
        'sandbox': 'https://mturk-requester-sandbox.us-east-1.amazonaws.com',
        'production': 'https://mturk-requester.us-east-1.amazonaws.com'
    }
    
    print(f"🌍 Environment: {environment.upper()}")
    
    try:
        mturk = boto3.client(
            'mturk',
            endpoint_url=endpoints[environment],
            region_name='us-east-1',
            aws_access_key_id=os.getenv('AWS_ACCESS_KEY_ID'),
            aws_secret_access_key=os.getenv('AWS_SECRET_ACCESS_KEY')
        )
        
        # List all assignments for this HIT
        print("\n🔍 Checking assignments for this worker...")
        
        assignments = []
        next_token = None
        
        while True:
            params = {
                'HITId': hit_id,
                'MaxResults': 100
            }
            if next_token:
                params['NextToken'] = next_token
            
            response = mturk.list_assignments_for_hit(**params)
            assignments.extend(response.get('Assignments', []))
            
            next_token = response.get('NextToken')
            if not next_token:
                break
        
        # Filter for this worker
        worker_assignments = [a for a in assignments if a['WorkerId'] == worker_id]
        
        print(f"\n📊 Found {len(worker_assignments)} assignment(s) for this worker")
        
        if not worker_assignments:
            print("\n✅ No assignments found for this worker")
            print("   Worker should be able to accept new assignments")
            return True
        
        # Analyze assignments by status
        print("\n" + "="*70)
        print("ASSIGNMENT DETAILS")
        print("="*70)
        
        submitted = []
        approved = []
        rejected = []
        
        for idx, assignment in enumerate(worker_assignments, 1):
            status = assignment['AssignmentStatus']
            assignment_id = assignment['AssignmentId']
            submit_time = assignment.get('SubmitTime', 'N/A')
            
            print(f"\n{idx}. Assignment: {assignment_id}")
            print(f"   Status: {status}")
            print(f"   Submitted: {submit_time}")
            
            if status == 'Submitted':
                submitted.append(assignment)
                print(f"   ⏳ Waiting for approval")
            elif status == 'Approved':
                approved.append(assignment)
                print(f"   ✅ Approved and paid")
            elif status == 'Rejected':
                rejected.append(assignment)
                print(f"   ❌ Rejected")
        
        # Summary
        print("\n" + "="*70)
        print("SUMMARY")
        print("="*70)
        
        print(f"\n   Total assignments: {len(worker_assignments)}")
        print(f"   ✅ Approved: {len(approved)}")
        print(f"   ⏳ Pending approval: {len(submitted)}")
        print(f"   ❌ Rejected: {len(rejected)}")
        
        # Diagnosis
        print("\n" + "="*70)
        print("DIAGNOSIS")
        print("="*70)
        
        if submitted:
            print(f"\n⏳ You have {len(submitted)} pending assignment(s)")
            print("   These are awaiting approval (should auto-approve within 1 hour)")
            print("\n   ✅ You SHOULD be able to accept new assignments")
            print("   If you can't, wait 5-10 minutes for MTurk to update")
        else:
            print("\n✅ No pending assignments")
            print("   You should be able to accept new assignments")
        
        # Check HIT availability
        print("\n🔍 Checking HIT availability...")
        hit_response = mturk.get_hit(HITId=hit_id)
        hit = hit_response['HIT']
        
        print(f"\n   Max Assignments: {hit['MaxAssignments']:,}")
        print(f"   Available: {hit['NumberOfAssignmentsAvailable']:,}")
        print(f"   Completed: {hit['NumberOfAssignmentsCompleted']:,}")
        print(f"   Pending: {hit['NumberOfAssignmentsPending']:,}")
        
        if hit['NumberOfAssignmentsAvailable'] > 0:
            print("\n✅ HIT has available assignments")
            
            if submitted:
                print("\n💡 LIKELY ISSUE:")
                print("   MTurk may temporarily prevent new assignments while")
                print("   processing your pending submission. This usually")
                print("   resolves within 5-10 minutes.")
                print("\n   SOLUTION: Wait a few minutes, then try again")
            else:
                print("\n💡 HIT is available and you have no pending assignments")
                print("   You should be able to accept new assignments now")
        else:
            print("\n❌ HIT has NO available assignments")
            print("   All assignments have been used/claimed")
            print("\n   SOLUTION: Extend assignments")
            print("   python fix_hit_assignments.py --assignments 10000")
        
        print("\n" + "="*70)
        
        return True
        
    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == '__main__':
    import argparse
    
    parser = argparse.ArgumentParser(description='Check worker assignment status')
    parser.add_argument('worker_id', help='MTurk Worker ID (e.g., A1BCDEFG2HIJK)')
    
    args = parser.parse_args()
    
    check_worker_assignments(args.worker_id)

