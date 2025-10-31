#!/usr/bin/env python3
"""
Verify what reward amount MTurk HITs actually have.
Check if our code is setting the correct reward.
"""

from mturk_api import get_mturk_client


def check_hit_rewards():
    """Check the actual reward amounts of HITs in MTurk."""
    print("="*70)
    print("🔍 VERIFYING HIT REWARD AMOUNTS")
    print("="*70)
    
    try:
        mturk_client = get_mturk_client()
        print(f"\n✅ Connected to MTurk ({mturk_client.environment} environment)\n")
    except Exception as e:
        print(f"\n❌ Failed to connect to MTurk: {e}")
        return
    
    # List all HITs
    all_hits = []
    next_token = None
    
    try:
        while True:
            if next_token:
                response = mturk_client.client.list_hits(
                    NextToken=next_token,
                    MaxResults=100
                )
            else:
                response = mturk_client.client.list_hits(MaxResults=100)
            
            hits = response.get('HITs', [])
            all_hits.extend(hits)
            
            next_token = response.get('NextToken')
            if not next_token:
                break
        
        print(f"Found {len(all_hits)} HIT(s)\n")
        
        if not all_hits:
            print("✅ No HITs found")
            return
        
        # Check each HIT's reward
        print("HIT Reward Analysis:")
        print("─"*70)
        
        total_rewards = 0.0
        
        for i, hit in enumerate(all_hits, 1):
            hit_id = hit['HITId']
            title = hit.get('Title', 'Untitled')
            reward = hit.get('Reward', '0.00')
            status = hit.get('HITStatus', 'Unknown')
            
            # Parse reward as float
            try:
                reward_float = float(reward)
                total_rewards += reward_float
            except:
                reward_float = 0.0
            
            print(f"\n{i}. {title}")
            print(f"   HIT ID: {hit_id}")
            print(f"   Status: {status}")
            print(f"   💵 Reward: ${reward}")
            
            # Check if reward is wrong
            if 'Payout' in title or 'ChatGame' in title:
                if reward_float < 1.0:
                    print(f"   ⚠️  WARNING: Expected $2.00, got ${reward}")
                    print(f"   ⚠️  This HIT has INCORRECT reward amount!")
                elif reward_float >= 2.0:
                    print(f"   ✅ Correct reward amount")
                else:
                    print(f"   ⚠️  Unexpected reward: ${reward}")
        
        print("\n" + "─"*70)
        print(f"Total rewards across all HITs: ${total_rewards:.2f}")
        print("─"*70)
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    check_hit_rewards()

