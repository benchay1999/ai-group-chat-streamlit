#!/usr/bin/env python3
"""
Per-Transaction HIT Service
============================

Creates a UNIQUE HIT for each cashout transaction.
Each HIT is visible only to the specific worker who requested it.

Benefits:
✅ No MaxAssignments exhaustion (each HIT has MaxAssignments=1)
✅ No URL confusion (each HIT has its own unique URL)
✅ Worker-specific (only the requesting worker can see/complete it)
✅ Clean separation (each transaction = one HIT)
✅ Automatic cleanup (HITs expire after completion)
✅ Scalable (can handle unlimited cashouts)

Flow:
1. User requests cashout → Worker ID verified
2. System creates worker-specific qualification
3. System creates HIT with that qualification requirement
4. Only that worker can see the HIT
5. Worker completes HIT → gets paid
6. HIT expires/gets deleted automatically

No more "No HITs available" errors!
"""

import os
from decimal import Decimal
from datetime import datetime
from typing import Dict, Optional
from sqlalchemy.ext.asyncio import AsyncSession

from .database import User, CashoutTransaction, CashoutStatus
from .config import GEMS_PER_DOLLAR
from .mturk_api import get_mturk_client


async def create_worker_specific_hit(
    user: User,
    transaction: CashoutTransaction,
    db: AsyncSession
) -> Dict:
    """
    Create a HIT that only the specific worker can see and complete.
    
    Uses MTurk's qualification system to restrict HIT visibility.
    
    Args:
        user: User requesting cashout
        transaction: CashoutTransaction object
        db: Database session
    
    Returns:
        Dict with HIT details and worker URL
    """
    
    print(f"\n{'='*70}")
    print(f"🎯 CREATING WORKER-SPECIFIC HIT")
    print(f"{'='*70}")
    print(f"Transaction: {transaction.id}")
    print(f"User: {user.user_id}")
    print(f"Worker ID: {user.mturk_worker_id}")
    print(f"Amount: ${transaction.amount_usd}")
    
    # Validate worker ID exists
    if not user.mturk_worker_id:
        raise ValueError("MTurk Worker ID not set. Please add your Worker ID in your profile settings.")
    
    # STEP 0: Cancel any existing pending HITs for this user
    print(f"\n0️⃣  Checking for existing pending cashouts...")
    from sqlalchemy import select, and_
    from .database import CashoutStatus
    
    existing_result = await db.execute(
        select(CashoutTransaction)
        .where(
            and_(
                CashoutTransaction.user_id == user.id,
                CashoutTransaction.status.in_([CashoutStatus.PENDING, CashoutStatus.HIT_CREATED])
            )
        )
    )
    existing_txs = existing_result.scalars().all()
    
    if existing_txs:
        print(f"   Found {len(existing_txs)} existing pending cashout(s)")
        print(f"   🚫 Auto-cancelling old cashouts...")
        
        from .mturk_api import get_mturk_client
        mturk_client_cancel = get_mturk_client()
        
        for old_tx in existing_txs:
            if old_tx.id == transaction.id:
                continue  # Don't cancel the current transaction
            
            print(f"   Cancelling: {old_tx.id}")
            
            # Delete/expire old HIT
            if old_tx.mturk_hit_id:
                try:
                    mturk_client_cancel.client.delete_hit(HITId=old_tx.mturk_hit_id)
                    print(f"      ✅ Old HIT deleted")
                except:
                    try:
                        from datetime import datetime
                        mturk_client_cancel.client.update_expiration_for_hit(
                            HITId=old_tx.mturk_hit_id,
                            ExpireAt=datetime.utcnow()
                        )
                        print(f"      ✅ Old HIT expired")
                    except:
                        print(f"      ⚠️  Could not clean old HIT")
            
            # Refund gems
            user.gem_balance += old_tx.amount_gems
            if user.total_gems_cashed_out >= old_tx.amount_gems:
                user.total_gems_cashed_out -= old_tx.amount_gems
            
            # Mark as cancelled
            old_tx.status = CashoutStatus.CANCELLED
            old_tx.error_message = "Auto-cancelled: New cashout requested"
            
            print(f"      ✅ {old_tx.amount_gems} gems refunded")
        
        await db.commit()
        print(f"   ✅ Old cashouts cleaned up")
    else:
        print(f"   ✅ No existing pending cashouts")
    
    try:
        mturk_client = get_mturk_client()
        environment = mturk_client.environment
        
        # Step 1: Create worker-specific qualification
        print(f"\n1️⃣  Creating worker-specific qualification...")
        
        qual_name = f"ChatGame_User_{user.user_id}_{transaction.id}"
        qual_description = f"Qualification for ChatGame user {user.user_id} transaction {transaction.id}"
        
        # Create the qualification type
        qualification_id = mturk_client.create_worker_qualification(
            worker_id=user.mturk_worker_id,
            qualification_name=qual_name
        )
        
        print(f"   ✅ Qualification created: {qualification_id}")
        
        # Assign the qualification to the worker
        print(f"   🔄 Assigning qualification to worker {user.mturk_worker_id}...")
        print(f"   📋 DEBUG: Qualification ID: {qualification_id}")
        print(f"   📋 DEBUG: Worker ID: '{user.mturk_worker_id}' (length: {len(user.mturk_worker_id)})")
        print(f"   📋 DEBUG: Worker ID stripped: '{user.mturk_worker_id.strip()}'")
        
        # Use stripped worker ID to avoid whitespace issues
        worker_id_clean = user.mturk_worker_id.strip()
        
        try:
            mturk_client.client.associate_qualification_with_worker(
                QualificationTypeId=qualification_id,
                WorkerId=worker_id_clean,
                IntegerValue=1,
                SendNotification=False
            )
            print(f"   ✅ Qualification assigned to worker: {worker_id_clean}")
        except Exception as assign_error:
            print(f"   ❌ FAILED TO ASSIGN QUALIFICATION!")
            print(f"   ❌ Error: {assign_error}")
            print(f"   ❌ This means the Worker ID is INVALID or doesn't exist in MTurk!")
            raise Exception(f"Cannot assign qualification to worker {worker_id_clean}: {assign_error}")
        
        # Verify the qualification was assigned
        print(f"   🔍 Verifying qualification assignment...")
        
        verification_successful = False
        max_retries = 3
        
        for attempt in range(max_retries):
            try:
                verification = mturk_client.client.get_qualification_score(
                    QualificationTypeId=qualification_id,
                    WorkerId=worker_id_clean
                )
                qual_value = verification.get('Qualification', {}).get('IntegerValue', 'N/A')
                print(f"   ✅ Verification successful (attempt {attempt + 1}) - Worker has qualification with value: {qual_value}")
                verification_successful = True
                break
            except Exception as verify_error:
                print(f"   ⚠️  Verification attempt {attempt + 1} failed: {verify_error}")
                
                if attempt < max_retries - 1:
                    import time
                    wait_time = 2 * (attempt + 1)  # Exponential backoff: 2s, 4s
                    print(f"   ⏳ Waiting {wait_time} seconds before retry...")
                    time.sleep(wait_time)
                else:
                    print(f"   ❌ CRITICAL: Could not verify qualification assignment after {max_retries} attempts!")
                    print(f"   ❌ This means the worker may not be able to access the HIT!")
                    print(f"   ❌ Worker ID used: {user.mturk_worker_id}")
                    print(f"   ❌ Qualification ID: {qualification_id}")
                    
                    # This is critical - raise an error
                    raise Exception(
                        f"Failed to verify qualification assignment for worker {worker_id_clean}. "
                        f"The worker may not be able to access the HIT. "
                        f"Please verify the Worker ID is correct and matches the MTurk account."
                    )
        
        # Step 2: Create HIT with qualification requirement
        print(f"\n2️⃣  Creating HIT with qualification requirement...")
        print(f"   ⏭️  Creating HIT immediately (frontend will wait 5s before allowing access)")
        
        # Generate external URL for the cashout confirmation page
        external_url = os.getenv('EXTERNAL_URL', 'http://localhost:3000')
        base_url = external_url.replace('/lobby', '').rstrip('/')
        cashout_confirm_url = f"{base_url}/cashout-confirm?code={transaction.redemption_code}&tx={transaction.id}"
        
        # Create the HIT
        print(f"\n   🔧 Creating HIT with parameters:")
        print(f"      Amount: ${transaction.amount_usd}")
        print(f"      Qualification ID: {qualification_id}")
        print(f"      Worker ID (for reference): {worker_id_clean}")
        print(f"      External URL: {cashout_confirm_url[:80]}...")
        
        hit_result = mturk_client.create_cashout_hit(
            amount=transaction.amount_usd,
            qualification_id=qualification_id,
            worker_id=worker_id_clean,
            external_url=cashout_confirm_url,
            duration_seconds=86400,  # 24 hours
            auto_approve_seconds=3600  # 1 hour
        )
        
        print(f"   ✅ HIT created: {hit_result['hit_id']}")
        print(f"   ✅ Worker URL: {hit_result['hit_url']}")
        
        # Step 3: Update transaction with HIT details
        print(f"\n3️⃣  Updating transaction record...")
        
        transaction.mturk_hit_id = hit_result['hit_id']
        transaction.status = CashoutStatus.HIT_CREATED
        
        await db.commit()
        
        print(f"   ✅ Transaction updated")
        
        print(f"\n{'='*70}")
        print(f"✅ WORKER-SPECIFIC HIT CREATED SUCCESSFULLY")
        print(f"{'='*70}")
        print(f"\nWorker can access their HIT at:")
        print(f"{hit_result['hit_url']}")
        print(f"\nOnly worker {user.mturk_worker_id} can see this HIT!")
        print(f"{'='*70}\n")
        
        return {
            "success": True,
            "hit_id": hit_result['hit_id'],
            "hit_url": hit_result['hit_url'],
            "qualification_id": qualification_id,
            "amount": float(transaction.amount_usd),
            "expires": hit_result['expiration'],
            "message": f"HIT created! Click the link to complete your ${transaction.amount_usd} cashout."
        }
        
    except Exception as e:
        print(f"\n❌ ERROR creating worker-specific HIT: {e}")
        import traceback
        traceback.print_exc()
        
        # Update transaction status
        transaction.status = CashoutStatus.FAILED
        transaction.error_message = f"Failed to create HIT: {str(e)}"
        
        # Refund gems
        user.gem_balance += transaction.amount_gems
        
        await db.commit()
        
        return {
            "success": False,
            "error": str(e),
            "refunded": True
        }


async def cleanup_completed_hit(
    transaction: CashoutTransaction,
    db: AsyncSession
) -> bool:
    """
    Clean up (delete/expire) a HIT after it's been completed.
    
    This keeps the MTurk account clean and prevents clutter.
    
    Args:
        transaction: Completed CashoutTransaction
        db: Database session
    
    Returns:
        True if cleanup successful
    """
    
    if not transaction.mturk_hit_id:
        return False
    
    try:
        mturk_client = get_mturk_client()
        
        print(f"🧹 Cleaning up HIT: {transaction.mturk_hit_id}")
        
        # Delete the HIT (if no assignments pending)
        try:
            mturk_client.client.delete_hit(HITId=transaction.mturk_hit_id)
            print(f"   ✅ HIT deleted")
            return True
        except Exception as e:
            # If can't delete (has assignments), try to expire it
            print(f"   ⚠️  Could not delete HIT, expiring instead: {e}")
            try:
                mturk_client.client.update_expiration_for_hit(
                    HITId=transaction.mturk_hit_id,
                    ExpireAt=datetime.utcnow()
                )
                print(f"   ✅ HIT expired")
                return True
            except Exception as e2:
                print(f"   ❌ Could not expire HIT: {e2}")
                return False
    
    except Exception as e:
        print(f"❌ Error cleaning up HIT: {e}")
        return False


def get_cashout_instructions() -> Dict:
    """
    Get user-friendly instructions for the new cashout system.
    
    Returns:
        Dict with step-by-step instructions
    """
    
    return {
        "title": "How Cashouts Work (New Simplified System)",
        "steps": [
            {
                "number": 1,
                "title": "Add MTurk Worker ID",
                "description": "Go to your profile and add your MTurk Worker ID (one-time setup)",
                "note": "Find your Worker ID at: https://worker.mturk.com/dashboard"
            },
            {
                "number": 2,
                "title": "Request Cashout",
                "description": "Click 'Cash Out' and choose the amount",
                "note": "System creates a private HIT just for you"
            },
            {
                "number": 3,
                "title": "Complete Your HIT",
                "description": "Click the HIT link provided",
                "note": "Only you can see this HIT - it's private!"
            },
            {
                "number": 4,
                "title": "Get Paid",
                "description": "Submit the HIT and receive payment",
                "note": "Payment is automatically approved within 1 hour"
            }
        ],
        "benefits": [
            "✅ Each cashout gets its own private HIT",
            "✅ No 'No more HITs available' errors",
            "✅ No searching for HITs - direct link provided",
            "✅ Unlimited cashouts over time",
            "✅ Clean and simple process"
        ],
        "faq": [
            {
                "q": "Can I cash out multiple times?",
                "a": "Yes! Each cashout creates a new private HIT. No limits."
            },
            {
                "q": "Will other workers see my HIT?",
                "a": "No! Each HIT is private and only visible to you."
            },
            {
                "q": "What if I don't complete the HIT?",
                "a": "The HIT expires after 24 hours and gems are refunded to your account."
            }
        ]
    }

