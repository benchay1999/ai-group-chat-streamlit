#!/usr/bin/env python3
"""
Check what assignments a worker has completed and their payments.
"""

import sys
from mturk_api import get_mturk_client


def check_worker_assignments(worker_id):
    """Check all assignments for a specific worker."""
    print("="*70)
    print(f"🔍 CHECKING ASSIGNMENTS FOR WORKER")
    print("="*70)
    print(f"Worker ID: {worker_id}\n")
    
    try:
        mturk_client = get_mturk_client()
        print(f"✅ Connected to MTurk ({mturk_client.environment} environment)\n")
    except Exception as e:
        print(f"❌ Failed to connect to MTurk: {e}")
        return
    
    # List all HITs first
    print("📋 Getting all HITs...\n")
    
    all_hits = []
    next_token = None
    
    try:
        while True:
            if next_token:
                response = mturk_client.client.list_hits(NextToken=next_token, MaxResults=100)
            else:
                response = mturk_client.client.list_hits(MaxResults=100)
            
            hits = response.get('HITs', [])
            all_hits.extend(hits)
            
            next_token = response.get('NextToken')
            if not next_token:
                break
        
        print(f"Found {len(all_hits)} total HIT(s)\n")
        
        # For each HIT, check if worker has assignments
        worker_assignments = []
        
        for hit in all_hits:
            hit_id = hit['HITId']
            
            try:
                assignments_response = mturk_client.client.list_assignments_for_hit(
                    HITId=hit_id,
                    MaxResults=100
                )
                
                assignments = assignments_response.get('Assignments', [])
                
                # Filter for this worker
                for assignment in assignments:
                    if assignment.get('WorkerId') == worker_id:
                        worker_assignments.append({
                            'hit': hit,
                            'assignment': assignment
                        })
            except Exception as e:
                pass  # Skip HITs we can't access
        
        if not worker_assignments:
            print(f"❌ No assignments found for worker {worker_id}")
            return
        
        print(f"✅ Found {len(worker_assignments)} assignment(s) for this worker\n")
        print("="*70)
        print("ASSIGNMENTS:")
        print("="*70)
        
        total_paid = 0.0
        
        for i, item in enumerate(worker_assignments, 1):
            hit = item['hit']
            assignment = item['assignment']
            
            hit_id = hit['HITId']
            title = hit.get('Title', 'Untitled')
            reward = hit.get('Reward', '0.00')
            
            assignment_id = assignment.get('AssignmentId', 'N/A')
            status = assignment.get('AssignmentStatus', 'Unknown')
            submit_time = assignment.get('SubmitTime', 'Unknown')
            approval_time = assignment.get('ApprovalTime', 'Unknown')
            
            try:
                reward_float = float(reward)
                if status == 'Approved':
                    total_paid += reward_float
            except:
                reward_float = 0.0
            
            print(f"\n{i}. HIT: {title}")
            print(f"   HIT ID: {hit_id}")
            print(f"   💵 Reward: ${reward}")
            print(f"   Assignment ID: {assignment_id}")
            print(f"   Status: {status}")
            print(f"   Submitted: {submit_time}")
            print(f"   Approved: {approval_time}")
            
            if reward_float < 1.0 and 'Payout' in title:
                print(f"   ⚠️  WARNING: This HIT has INCORRECT reward (expected $2.00+)")
        
        print("\n" + "="*70)
        print(f"TOTAL PAYMENT TO WORKER: ${total_paid:.2f}")
        print("="*70)
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    if len(sys.argv) > 1:
        check_worker_assignments(sys.argv[1])
    else:
        print("Usage: python check_worker_assignments.py <worker_id>")
        print("Example: python check_worker_assignments.py A1EWFN76HNDD20")
