#!/usr/bin/env python3
"""
Approve all submitted assignments.
"""

from mturk_api import get_mturk_client


def approve_all_assignments():
    """Approve all submitted assignments."""
    print("="*70)
    print("✅ APPROVING ALL SUBMITTED ASSIGNMENTS")
    print("="*70)
    
    try:
        mturk_client = get_mturk_client()
        print(f"\n✅ Connected to MTurk ({mturk_client.environment} environment)\n")
    except Exception as e:
        print(f"\n❌ Failed to connect to MTurk: {e}")
        return
    
    # Get all HITs
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
        
        print(f"Found {len(all_hits)} HIT(s)\n")
        
        # Check each HIT for submitted assignments
        total_approved = 0
        total_amount = 0.0
        
        for hit in all_hits:
            hit_id = hit['HITId']
            title = hit.get('Title', 'Untitled')
            reward = hit.get('Reward', '0.00')
            
            try:
                reward_float = float(reward)
            except:
                reward_float = 0.0
            
            try:
                # Get assignments for this HIT
                assignments_response = mturk_client.client.list_assignments_for_hit(
                    HITId=hit_id,
                    AssignmentStatuses=['Submitted'],
                    MaxResults=100
                )
                
                assignments = assignments_response.get('Assignments', [])
                
                if assignments:
                    print(f"HIT: {title}")
                    print(f"   HIT ID: {hit_id}")
                    print(f"   Reward: ${reward}")
                    print(f"   Submitted assignments: {len(assignments)}\n")
                    
                    for assignment in assignments:
                        assignment_id = assignment.get('AssignmentId')
                        worker_id = assignment.get('WorkerId')
                        
                        print(f"   Approving assignment {assignment_id}")
                        print(f"      Worker: {worker_id}")
                        
                        try:
                            mturk_client.client.approve_assignment(
                                AssignmentId=assignment_id,
                                RequesterFeedback="Thank you for completing this HIT!",
                                OverrideRejection=False
                            )
                            print(f"      ✅ Approved - Worker will receive ${reward}")
                            total_approved += 1
                            total_amount += reward_float
                        except Exception as approve_error:
                            print(f"      ❌ Error: {approve_error}")
                    
                    print()
                    
            except Exception as e:
                pass  # Skip HITs we can't access
        
        print("="*70)
        print(f"APPROVAL SUMMARY:")
        print(f"   Total assignments approved: {total_approved}")
        print(f"   Total amount paid: ${total_amount:.2f}")
        print("="*70)
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    approve_all_assignments()

