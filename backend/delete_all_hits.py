#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Delete All MTurk HITs
Cleans up all HITs in the current environment (sandbox or production)
"""

import os
import sys
from dotenv import load_dotenv
import boto3
from botocore.exceptions import ClientError

load_dotenv()

def delete_all_hits():
    """Delete all HITs in the current MTurk environment."""
    environment = os.getenv('MTURK_ENVIRONMENT', 'sandbox')
    aws_access_key = os.getenv('AWS_ACCESS_KEY_ID')
    aws_secret_key = os.getenv('AWS_SECRET_ACCESS_KEY')

    endpoints = {
        'sandbox': 'https://mturk-requester-sandbox.us-east-1.amazonaws.com',
        'production': 'https://mturk-requester.us-east-1.amazonaws.com'
    }

    if not aws_access_key or not aws_secret_key:
        print("❌ ERROR: AWS credentials not found in .env file!")
        print("   Please set AWS_ACCESS_KEY_ID and AWS_SECRET_ACCESS_KEY")
        return False

    print("=" * 70)
    print("  MTurk HIT Cleanup Tool")
    print("=" * 70)
    print(f"\n⚠️  WARNING: This will DELETE ALL HITs in {environment.upper()} environment!")
    print(f"   Environment: {environment}")
    
    confirm = input("\n⚠️  Are you ABSOLUTELY SURE you want to delete ALL HITs? (type 'DELETE ALL' to confirm): ").strip()
    if confirm != 'DELETE ALL':
        print("❌ Operation cancelled. No HITs were deleted.")
        return False

    print(f"\n🔧 Connecting to MTurk {environment.upper()} environment...")

    try:
        mturk = boto3.client(
            'mturk',
            region_name='us-east-1',
            endpoint_url=endpoints[environment],
            aws_access_key_id=aws_access_key,
            aws_secret_access_key=aws_secret_key
        )

        # Get account balance
        try:
            balance = mturk.get_account_balance()
            print(f"💰 Current Account Balance: ${balance['AvailableBalance']}")
        except:
            pass

        print(f"\n🔍 Finding all HITs...")
        
        # List all HITs
        hits_to_delete = []
        next_token = None
        page = 1
        
        while True:
            try:
                if next_token:
                    response = mturk.list_hits(NextToken=next_token, MaxResults=100)
                else:
                    response = mturk.list_hits(MaxResults=100)
                
                hits = response.get('HITs', [])
                hits_to_delete.extend(hits)
                
                print(f"   Page {page}: Found {len(hits)} HITs")
                page += 1
                
                next_token = response.get('NextToken')
                if not next_token:
                    break
                    
            except ClientError as e:
                if 'RequestError' in str(e):
                    break
                else:
                    raise

        if not hits_to_delete:
            print("\n✅ No HITs found. Environment is already clean!")
            return True

        print(f"\n📋 Total HITs found: {len(hits_to_delete)}")
        print("\n" + "=" * 70)
        print("HITs to be deleted:")
        print("=" * 70)
        
        for idx, hit in enumerate(hits_to_delete, 1):
            hit_id = hit['HITId']
            title = hit.get('Title', 'Unknown')
            status = hit.get('HITStatus', 'Unknown')
            max_assignments = hit.get('MaxAssignments', 0)
            available = hit.get('NumberOfAssignmentsAvailable', 0)
            pending = hit.get('NumberOfAssignmentsPending', 0)
            completed = hit.get('NumberOfAssignmentsCompleted', 0)
            
            print(f"\n{idx}. HIT ID: {hit_id}")
            print(f"   Title: {title}")
            print(f"   Status: {status}")
            print(f"   Assignments: {completed}/{max_assignments} completed, {pending} pending, {available} available")

        print("\n" + "=" * 70)
        final_confirm = input(f"\n⚠️  Proceed with deleting {len(hits_to_delete)} HIT(s)? (yes/no): ").strip().lower()
        if final_confirm != 'yes':
            print("❌ Operation cancelled.")
            return False

        print(f"\n🗑️  Deleting {len(hits_to_delete)} HIT(s)...")
        deleted_count = 0
        error_count = 0

        for idx, hit in enumerate(hits_to_delete, 1):
            hit_id = hit['HITId']
            title = hit.get('Title', 'Unknown')
            
            try:
                # First, try to expire the HIT (required before deletion)
                try:
                    mturk.update_expiration_for_hit(
                        HITId=hit_id,
                        ExpireAt=0  # Expire immediately
                    )
                    print(f"   [{idx}/{len(hits_to_delete)}] Expired HIT: {hit_id[:20]}... ({title})")
                except ClientError as e:
                    if 'HITAlreadyExpired' not in str(e):
                        print(f"   ⚠️  Could not expire HIT {hit_id[:20]}...: {e}")

                # Now delete the HIT
                mturk.delete_hit(HITId=hit_id)
                print(f"   [{idx}/{len(hits_to_delete)}] ✅ Deleted HIT: {hit_id[:20]}... ({title})")
                deleted_count += 1
                
            except ClientError as e:
                error_msg = str(e)
                if 'HITDoesNotExist' in error_msg:
                    print(f"   [{idx}/{len(hits_to_delete)}] ⚠️  HIT already deleted: {hit_id[:20]}...")
                    deleted_count += 1  # Count as successful
                elif 'assignments with status' in error_msg.lower():
                    print(f"   [{idx}/{len(hits_to_delete)}] ⚠️  Cannot delete HIT {hit_id[:20]}...: Has active assignments")
                    print(f"      You may need to manually approve/reject assignments first")
                    error_count += 1
                else:
                    print(f"   [{idx}/{len(hits_to_delete)}] ❌ Failed to delete HIT {hit_id[:20]}...: {e}")
                    error_count += 1
            except Exception as e:
                print(f"   [{idx}/{len(hits_to_delete)}] ❌ Unexpected error deleting HIT {hit_id[:20]}...: {e}")
                error_count += 1

        print("\n" + "=" * 70)
        print("  DELETION SUMMARY")
        print("=" * 70)
        print(f"✅ Successfully deleted: {deleted_count} HIT(s)")
        if error_count > 0:
            print(f"❌ Failed to delete: {error_count} HIT(s)")
            print("\n⚠️  Note: Some HITs may have active assignments and require manual intervention.")
        else:
            print("🎉 All HITs deleted successfully!")

        # Show updated balance
        try:
            balance = mturk.get_account_balance()
            print(f"\n💰 Updated Account Balance: ${balance['AvailableBalance']}")
        except:
            pass

        print("\n" + "=" * 70)
        print("✅ Cleanup complete!")
        print("=" * 70)
        
        return error_count == 0

    except ClientError as e:
        print(f"❌ ERROR: Failed to connect to MTurk: {e}")
        return False
    except Exception as e:
        print(f"❌ An unexpected error occurred: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    print("\n🧹 MTurk HIT Cleanup Tool\n")
    
    success = delete_all_hits()
    
    if success:
        print("\n✅ All done! You can now create a new standing HIT.")
        print("\nNext steps:")
        print("   1. Run: python3 create_standing_hit.py")
        print("   2. Update CASHOUT_HIT_ID in your .env file")
        print("   3. Restart your backend server")
        sys.exit(0)
    else:
        print("\n⚠️  Cleanup completed with errors. Please review the output above.")
        sys.exit(1)

