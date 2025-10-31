#!/usr/bin/env python3
"""
Check if a specific HIT exists by HITGroupId
"""
import sys
from mturk_api import get_mturk_client

def check_hit_group(hit_group_id):
    """Check if HIT group exists."""
    print(f"\n🔍 Checking HITGroupId: {hit_group_id}\n")
    
    mturk = get_mturk_client()
    
    try:
        # List all HITs and find ones matching this group
        print("📋 Listing all HITs...")
        response = mturk.client.list_hits(MaxResults=100)
        
        hits = response.get('HITs', [])
        print(f"   Found {len(hits)} total HITs\n")
        
        matching_hits = [hit for hit in hits if hit.get('HITGroupId') == hit_group_id]
        
        if matching_hits:
            print(f"✅ Found {len(matching_hits)} HIT(s) with this HITGroupId:\n")
            for hit in matching_hits:
                print(f"   HIT ID: {hit['HITId']}")
                print(f"   Status: {hit['HITStatus']}")
                print(f"   Title: {hit.get('Title', 'N/A')}")
                print(f"   Reward: ${hit.get('Reward', 'N/A')}")
                print(f"   Expiration: {hit.get('Expiration', 'N/A')}")
                print(f"   Available: {hit.get('NumberOfAssignmentsAvailable', 0)}")
                print()
        else:
            print(f"❌ No HITs found with HITGroupId: {hit_group_id}\n")
            print("This could mean:")
            print("  1. The HIT was deleted")
            print("  2. The HIT has expired")
            print("  3. The HITGroupId is incorrect")
            print("  4. You're in the wrong environment (sandbox vs production)\n")
            
        # Show all available HITs
        if hits:
            print("=" * 70)
            print("All Available HITs:")
            print("=" * 70)
            for hit in hits[:10]:  # Show first 10
                print(f"HITId: {hit['HITId']}")
                print(f"HITGroupId: {hit['HITGroupId']}")
                print(f"Title: {hit.get('Title', 'N/A')}")
                print(f"Reward: ${hit.get('Reward', 'N/A')}")
                print(f"Status: {hit['HITStatus']}")
                print("-" * 70)
                
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python check_hit_group.py <HITGroupId>")
        print("Example: python check_hit_group.py 3PR0UJAG0I5VKOACLDYZEJD4HTHHJ5")
    else:
        check_hit_group(sys.argv[1])

