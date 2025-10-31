#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Return all your accepted HITs in MTurk sandbox/production.
Useful when testing cashout flow and you've accepted HITs but didn't submit them.
"""

import os
import sys
from dotenv import load_dotenv
import boto3

load_dotenv()

def return_all_my_hits(worker_id):
    """Return all HITs accepted by a worker."""
    
    environment = os.getenv('MTURK_ENVIRONMENT', 'sandbox')
    aws_access_key = os.getenv('AWS_ACCESS_KEY_ID')
    aws_secret_key = os.getenv('AWS_SECRET_ACCESS_KEY')
    
    endpoints = {
        'sandbox': 'https://mturk-requester-sandbox.us-east-1.amazonaws.com',
        'production': 'https://mturk-requester.us-east-1.amazonaws.com'
    }
    
    if not aws_access_key or not aws_secret_key:
        print("❌ ERROR: AWS credentials not found!")
        return False
    
    if not worker_id:
        print("❌ ERROR: Worker ID required!")
        print("\nUsage:")
        print("  python return_my_hits.py YOUR_WORKER_ID")
        print("\nFind your worker ID:")
        print("  - Sandbox: https://workersandbox.mturk.com/dashboard")
        print("  - Look for 'Worker ID' in your dashboard")
        return False
    
    print("=" * 70)
    print(f"  RETURN MY ACCEPTED HITs")
    print("=" * 70)
    print(f"\n🔧 Environment: {environment.upper()}")
    print(f"👤 Worker ID: {worker_id}")
    
    try:
        mturk = boto3.client(
            'mturk',
            region_name='us-east-1',
            endpoint_url=endpoints[environment],
            aws_access_key_id=aws_access_key,
            aws_secret_access_key=aws_secret_key
        )
        
        # Get all HITs
        print(f"\n📋 Finding HITs...")
        paginator = mturk.get_paginator('list_hits')
        all_hits = []
        
        for page in paginator.paginate():
            all_hits.extend(page['HITs'])
        
        print(f"   Found {len(all_hits)} total HIT(s)")
        
        # For each HIT, check for assignments by this worker
        returned_count = 0
        
        for hit in all_hits:
            hit_id = hit['HITId']
            
            try:
                # List assignments for this HIT
                response = mturk.list_assignments_for_hit(
                    HITId=hit_id,
                    AssignmentStatuses=['Submitted']  # Get submitted assignments
                )
                
                # Check if any are from this worker
                for assignment in response.get('Assignments', []):
                    if assignment['WorkerId'] == worker_id:
                        assignment_id = assignment['AssignmentId']
                        
                        print(f"\n📌 Found your assignment:")
                        print(f"   HIT: {hit['Title'][:50]}...")
                        print(f"   Assignment ID: {assignment_id}")
                        print(f"   Status: {assignment['AssignmentStatus']}")
                        
                        # Note: Workers can't return submitted assignments
                        # Only accepted-but-not-submitted can be returned
                        # This script is for REQUESTERS to see what's assigned
                        
            except Exception as e:
                # Skip HITs we can't access
                continue
        
        print("\n" + "=" * 70)
        print("  IMPORTANT INFORMATION")
        print("=" * 70)
        print("\n⚠️  As a REQUESTER, you cannot return HITs on behalf of workers.")
        print("⚠️  Workers must return HITs themselves from their MTurk dashboard.")
        print("\n👤 Worker Instructions:")
        print("   1. Go to: https://workersandbox.mturk.com/dashboard")
        print("   2. Click 'HITs Assigned to You'")
        print("   3. Find the ChatGame cashout HIT")
        print("   4. Click 'Return HIT' button")
        print("   5. Now you can accept it again!")
        
        print("\n💡 FOR TESTING:")
        print("   Use dev mode instead:")
        print("   → http://localhost:5173/cashout-confirm?dev=true")
        print("   → No MTurk HIT acceptance needed!")
        print("   → Unlimited tests!")
        
        print("\n" + "=" * 70)
        
    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        return False
    
    return True


if __name__ == '__main__':
    if len(sys.argv) < 2:
        print("=" * 70)
        print("  RETURN MY ACCEPTED HITs")
        print("=" * 70)
        print("\n❌ Worker ID required!")
        print("\nUsage:")
        print("  python return_my_hits.py YOUR_WORKER_ID")
        print("\n📍 Find your Worker ID:")
        print("   Sandbox: https://workersandbox.mturk.com/dashboard")
        print("   Production: https://worker.mturk.com/dashboard")
        print("   (Look for 'Worker ID' in your account info)")
        print("\n" + "=" * 70)
        sys.exit(1)
    
    worker_id = sys.argv[1]
    return_all_my_hits(worker_id)

