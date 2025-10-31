"""
New Cashout Endpoint - Per-Transaction HIT System
==================================================

Replaces the standing HIT approach with worker-specific HITs per transaction.

To integrate this, add to main.py:

from .cashout_endpoint_v2 import request_cashout_v2

@app.post("/api/wallet/cashout/v2")
async def cashout_v2(request: Request, current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_async_session)):
    return await request_cashout_v2(request, current_user, db)
"""

from fastapi import HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession
from decimal import Decimal

from .database import User
from .config import GEMS_PER_DOLLAR, MINIMUM_CASHOUT_AMOUNT
from .cashout_service import gems_to_usd, create_cashout_transaction
from .per_transaction_hit_service import create_worker_specific_hit, get_cashout_instructions


async def request_cashout_v2(
    request: Request,
    current_user: User,
    db: AsyncSession
):
    """
    New cashout endpoint using per-transaction HIT system.
    
    No more standing HIT complexity!
    Each cashout creates a private HIT for that specific worker.
    """
    
    print(f"\n{'='*70}")
    print(f"💰 CASHOUT REQUEST V2 (Per-Transaction HIT)")
    print(f"{'='*70}")
    print(f"User: {current_user.user_id}")
    print(f"Worker ID: {current_user.mturk_worker_id}")
    
    try:
        # Parse request body
        body = await request.json()
        amount_usd = Decimal(str(body.get('amount_usd', 0)))
        
        print(f"Requested amount: ${amount_usd}")
        print(f"User balance: {current_user.gem_balance} gems")
        
        # Validation 1: Check Worker ID
        if not current_user.mturk_worker_id:
            raise HTTPException(
                status_code=400,
                detail="Please add your MTurk Worker ID to your profile first. Go to Profile → Add Worker ID."
            )
        
        # Validation 2: Check minimum amount
        if amount_usd < MINIMUM_CASHOUT_AMOUNT:
            raise HTTPException(
                status_code=400,
                detail=f"Minimum cashout is ${MINIMUM_CASHOUT_AMOUNT}"
            )
        
        # Validation 3: Check gem balance
        required_gems = int(amount_usd * GEMS_PER_DOLLAR)
        if current_user.gem_balance < required_gems:
            raise HTTPException(
                status_code=400,
                detail=f"Insufficient gems. You have {current_user.gem_balance}, need {required_gems} ({amount_usd} × 1000)"
            )
        
        # Step 1: Create transaction record and deduct gems
        print(f"\n1️⃣  Creating cashout transaction...")
        transaction = await create_cashout_transaction(
            user=current_user,
            amount_usd=amount_usd,
            db=db
        )
        print(f"   ✅ Transaction created: {transaction.id}")
        print(f"   ✅ {required_gems} gems deducted from balance")
        
        # Step 2: Create worker-specific HIT
        print(f"\n2️⃣  Creating private HIT for worker...")
        hit_result = await create_worker_specific_hit(
            user=current_user,
            transaction=transaction,
            db=db
        )
        
        if not hit_result['success']:
            raise HTTPException(
                status_code=500,
                detail=f"Failed to create HIT: {hit_result.get('error', 'Unknown error')}"
            )
        
        print(f"   ✅ Private HIT created successfully")
        
        # Return response
        response = {
            "success": True,
            "transaction_id": str(transaction.id),
            "amount_usd": float(amount_usd),
            "amount_gems": required_gems,
            "hit_url": hit_result['hit_url'],
            "hit_id": hit_result['hit_id'],
            "redemption_code": transaction.redemption_code,
            "expires_at": hit_result['expires'],
            "instructions": {
                "step1": "Click the HIT link below",
                "step2": "This HIT is private - only you can see it",
                "step3": "Complete the HIT to receive your payment",
                "step4": "Payment will be approved automatically within 1 hour"
            },
            "message": f"✅ Private HIT created! Click the link to cash out ${amount_usd}"
        }
        
        print(f"\n{'='*70}")
        print(f"✅ CASHOUT V2 SUCCESS")
        print(f"{'='*70}")
        print(f"Transaction: {transaction.id}")
        print(f"HIT URL: {hit_result['hit_url']}")
        print(f"{'='*70}\n")
        
        return response
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"\n❌ ERROR in cashout_v2: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(
            status_code=500,
            detail=f"Cashout failed: {str(e)}"
        )


# Add this to your main.py:
"""
# New V2 endpoint (per-transaction HITs)
from .cashout_endpoint_v2 import request_cashout_v2

@app.post("/api/wallet/cashout/v2")
async def cashout_v2(
    request: Request,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_session)
):
    '''
    New cashout system using per-transaction HITs.
    
    Benefits:
    - No MaxAssignments exhaustion
    - Worker-specific HITs (private)
    - Clean separation per transaction
    - Scalable to unlimited cashouts
    '''
    return await request_cashout_v2(request, current_user, db)


# Optional: Migration endpoint to help users transition
@app.get("/api/wallet/cashout/instructions")
async def get_instructions():
    '''Get instructions for the new cashout system.'''
    from .per_transaction_hit_service import get_cashout_instructions
    return get_cashout_instructions()
"""

