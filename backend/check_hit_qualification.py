#!/usr/bin/env python3
"""
Check the qualification requirements for a HIT
"""
import sys
from mturk_api import get_mturk_client

def check_hit_qualification(hit_id, worker_id=None):
    """Check qualification requirements for a HIT."""
    print(f"\n🔍 Checking HIT: {hit_id}\n")
    
    mturk = get_mturk_client()
    
    try:
        # Get HIT details
        response = mturk.client.get_hit(HITId=hit_id)
        hit = response['HIT']
        
        print(f"Title: {hit.get('Title')}")
        print(f"Reward: ${hit.get('Reward')}")
        print(f"Status: {hit.get('HITStatus')}")
        print(f"HITGroupId: {hit.get('HITGroupId')}")
        print()
        
        # Check qualification requirements
        qual_reqs = hit.get('QualificationRequirements', [])
        
        if not qual_reqs:
            print("✅ No qualification requirements - HIT is public\n")
        else:
            print(f"🔒 Found {len(qual_reqs)} qualification requirement(s):\n")
            
            for i, qual in enumerate(qual_reqs, 1):
                qual_id = qual.get('QualificationTypeId')
                comparator = qual.get('Comparator')
                values = qual.get('IntegerValues', [])
                
                print(f"Requirement #{i}:")
                print(f"  QualificationTypeId: {qual_id}")
                print(f"  Comparator: {comparator}")
                print(f"  Required Value: {values}")
                
                # Try to get qualification details
                try:
                    qual_info = mturk.client.get_qualification_type(
                        QualificationTypeId=qual_id
                    )
                    qual_type = qual_info['QualificationType']
                    print(f"  Name: {qual_type.get('Name', 'N/A')}")
                    print(f"  Description: {qual_type.get('Description', 'N/A')}")
                except:
                    print(f"  (Could not fetch qualification details)")
                
                # Check if worker has this qualification
                if worker_id:
                    print(f"\n  Checking worker {worker_id}...")
                    try:
                        worker_qual = mturk.client.get_qualification_score(
                            QualificationTypeId=qual_id,
                            WorkerId=worker_id
                        )
                        qual_value = worker_qual['Qualification'].get('IntegerValue', 'N/A')
                        print(f"  ✅ Worker has qualification with value: {qual_value}")
                        
                        if int(qual_value) in values:
                            print(f"  ✅ Worker MEETS requirement")
                        else:
                            print(f"  ❌ Worker DOES NOT meet requirement (has {qual_value}, needs {values})")
                    except Exception as e:
                        print(f"  ❌ Worker DOES NOT have this qualification")
                        print(f"     Error: {e}")
                
                print()
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python check_hit_qualification.py <HITId> [WorkerId]")
        print("Example: python check_hit_qualification.py 3511RHPAEN2DZ8D32XCVXJ5NWPBLRJ A1EWFN76HNDD20")
    else:
        hit_id = sys.argv[1]
        worker_id = sys.argv[2] if len(sys.argv) > 2 else None
        check_hit_qualification(hit_id, worker_id)

