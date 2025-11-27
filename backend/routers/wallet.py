from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from decimal import Decimal
import uuid as uuid_module
import traceback

from backend.database import get_async_session, User, CashoutTransaction, CashoutStatus
from backend.auth import get_current_user
from backend.middleware_utils import cashout_rate_limiter
from backend.security_monitor import log_rate_limit_violation, log_unusual_cashout
from backend.cashout_service import (
    create_cashout_transaction, redeem_cashout_code, get_user_cashout_history,
    check_cashout_status, CashoutError, gems_to_usd
)
from backend.cashout_endpoint_v2 import request_cashout_v2
from backend.check_hit_ready import check_hit_ready
from backend.cashout_cancel_service import cancel_cashout_transaction
from backend import env_config
from backend.config import GEMS_PER_DOLLAR, EXTERNAL_URL

router = APIRouter()

@router.get("/api/wallet/balance")
async def get_wallet_balance(
    current_user: User = Depends(get_current_user)
):
    """
    Get user's gem wallet balance and statistics.
    """
    # Check if user has complete MTurk profile (worker ID + demographics)
    has_complete_profile = bool(
        current_user.mturk_worker_id and 
        current_user.age and 
        current_user.gender and 
        current_user.nationality and 
        current_user.major
    )
    
    return {
        "gem_balance": current_user.gem_balance,
        "usd_equivalent": float(gems_to_usd(current_user.gem_balance)),
        "total_gems_earned": current_user.total_gems_earned,
        "total_gems_cashed_out": current_user.total_gems_cashed_out,
        "conversion_rate": {
            "gems_per_dollar": GEMS_PER_DOLLAR,
            "description": f"{GEMS_PER_DOLLAR} gems = $1.00 USD"
        },
        "mturk_worker_id": current_user.mturk_worker_id,
        "has_worker_id": has_complete_profile,  # Now checks for complete profile
        "has_demographics": bool(current_user.age and current_user.gender and current_user.nationality and current_user.major)
    }


@router.post("/api/wallet/cashout")
async def request_cashout(
    request: Request,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_session)
):
    """
    Request a cashout of gems to USD via MTurk redemption code.
    Generates a unique code for user to submit in the standing MTurk HIT.
    """
    # Rate limiting check (per user to prevent cashout spam)
    user_key = f"cashout_{current_user.id}"
    if not cashout_rate_limiter.is_allowed(user_key):
        log_rate_limit_violation(current_user.user_id, "/api/wallet/cashout")
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many cashout requests. Please wait a minute and try again."
        )
    
    body = await request.json()
    amount_usd = Decimal(str(body.get('amount_usd', 0)))
    
    # Log unusual cashout amounts for monitoring
    if amount_usd >= Decimal("50.00"):
        log_unusual_cashout(current_user.user_id, float(amount_usd))
    
    print(f"\n{'='*70}")
    print(f"📥 CASHOUT REQUEST from user: {current_user.user_id}")
    print(f"   Amount: ${amount_usd}")
    print(f"   User balance: {current_user.gem_balance} gems")
    print(f"{'='*70}")
    
    try:
        # Check if cashout system is configured (using cached value)
        print(f"🔍 Step 1: Checking cashout configuration...")
        try:
            mturk_hit_id = env_config.get_cashout_hit_id()
            print(f"   ✅ HIT ID loaded: {mturk_hit_id}")
        except ValueError as e:
            # Detailed error with diagnostic info
            config_status = env_config.get_config_status()
            error_details = {
                "error": "Cashout system not properly configured",
                "env_file_path": config_status['env_file_path'],
                "env_file_exists": config_status['env_file_exists'],
                "solution": "Set CASHOUT_HIT_ID in your .env file and restart the server"
            }
            print(f"   ❌ Configuration error: {error_details}")
            raise HTTPException(
                status_code=503,
                detail=f"Cashout system not configured. Environment file: {config_status['env_file_path']}, Exists: {config_status['env_file_exists']}. Please contact administrator."
            )
        
        # Create cashout transaction with redemption code
        print(f"🔍 Step 2: Creating cashout transaction...")
        transaction = await create_cashout_transaction(
            user=current_user,
            amount_usd=amount_usd,
            db=db
        )
        print(f"   ✅ Transaction created: {transaction.id}")
        
        # Get MTurk environment to provide correct HIT URL
        print(f"🔍 Step 3: Getting MTurk environment...")
        from backend.mturk_api import get_mturk_client
        mturk_client = get_mturk_client()
        environment = mturk_client.environment
        worker_endpoint = mturk_client.worker_endpoints[environment]
        print(f"   ✅ Environment: {environment}")
        print(f"   ✅ Worker endpoint: {worker_endpoint}")
        
        # Generate MTurk HIT URL and testing URL
        
        print(f"🔍 Step 4: Generating redemption URLs...")
        
        # Get HITGroupId from MTurk (needed for worker preview URL)
        # Note: HITId != HITGroupId, must query MTurk to get the group ID
        try:
            hit_response = mturk_client.client.get_hit(HITId=mturk_hit_id)
            hit_group_id = hit_response['HIT']['HITGroupId']
            print(f"   ✅ HITGroupId: {hit_group_id}")
        except Exception as e:
            print(f"   ⚠️ Could not get HITGroupId, using HITId as fallback: {e}")
            hit_group_id = mturk_hit_id  # Fallback (may not work)
        
        # MTurk HIT preview URL (for production use)
        mturk_hit_url = f"{worker_endpoint}/mturk/preview?groupId={hit_group_id}"
        
        # Dev/Testing URL (for testing without accepting HIT)
        # This allows testing the redemption flow without MTurk API calls
        dev_test_url = f"{EXTERNAL_URL.replace('/lobby', '')}/cashout-confirm?dev=true&code={transaction.redemption_code}"
        
        print(f"   ✅ Environment: {environment}")
        print(f"   ✅ MTurk HIT URL: {mturk_hit_url}")
        print(f"   ✅ Dev Test URL: {dev_test_url}")
        
        response_data = {
            "success": True,
            "transaction_id": str(transaction.id),
            "amount_usd": float(transaction.amount_usd),
            "amount_gems": transaction.amount_gems,
            "redemption_code": transaction.redemption_code,
            "status": transaction.status.value,
            "expires_at": transaction.expires_at.isoformat() if transaction.expires_at else None,
            "environment": environment,
            "hit_url": mturk_hit_url,  # MTurk HIT URL (official)
            "dev_test_url": dev_test_url if environment == 'sandbox' else None,  # Testing URL (sandbox only)
            "instructions": {
                "step1": "Copy your redemption code (shown above)",
                "step2": "Choose redemption method below",
                "step3": "MTurk HIT: For real MTurk workers (requires accepting HIT)",
                "step4": "Test Mode: For testing without MTurk (sandbox only)",
                "note": "Your code is valid for 7 days. Payment processes immediately after redemption.",
                "troubleshooting": "If you see 'No HITs available', you may have already accepted one. Return it first from your MTurk dashboard."
            }
        }
        
        print(f"✅ CASHOUT REQUEST SUCCESSFUL")
        print(f"   Transaction ID: {response_data['transaction_id']}")
        print(f"   Redemption Code: {response_data['redemption_code'][:16]}...")
        print(f"{'='*70}\n")
        
        return response_data
        
    except HTTPException:
        # Re-raise HTTP exceptions as-is
        print(f"❌ CASHOUT REQUEST FAILED - HTTP Exception")
        print(f"{'='*70}\n")
        raise
    except CashoutError as e:
        print(f"❌ CASHOUT REQUEST FAILED - Cashout Error: {e}")
        print(f"{'='*70}\n")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        print(f"❌ CASHOUT REQUEST FAILED - Unexpected Error: {e}")
        print(f"   Stack trace:\n{traceback.format_exc()}")
        print(f"{'='*70}\n")
        raise HTTPException(status_code=500, detail=f"Failed to create cashout: {str(e)}")


@router.get("/api/wallet/cashout-history")
async def get_cashout_history(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_session)
):
    """
    Get cashout transaction history for current user.
    """
    try:
        history = await get_user_cashout_history(user=current_user, db=db, limit=50)
        
        return {
            "transactions": history,
            "total_count": len(history)
        }
        
    except Exception as e:
        print(f"❌ Error getting cashout history: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get cashout history: {str(e)}")


# ============================================================================
# NEW: Per-Transaction HIT Cashout System (V2)
# ============================================================================

@router.post("/api/wallet/cashout/v2")
async def cashout_v2(
    request: Request,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_session)
):
    """
    NEW cashout system using per-transaction private HITs.
    """
    # Rate limiting check (per user to prevent cashout spam)
    user_key = f"cashout_{current_user.id}"
    if not cashout_rate_limiter.is_allowed(user_key):
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many cashout requests. Please wait a minute and try again."
        )
    
    return await request_cashout_v2(request, current_user, db)


@router.get("/api/wallet/cashout/{transaction_id}/hit-ready")
async def check_cashout_hit_ready_endpoint(
    transaction_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_session)
):
    """
    Check if MTurk HIT is ready for the worker to access.
    """
    return await check_hit_ready(transaction_id, current_user, db)


@router.get("/api/wallet/cashout-status/{transaction_id}")
async def get_cashout_status_endpoint(
    transaction_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_session)
):
    """
    Get status of a specific cashout transaction.
    """
    try:
        transaction_uuid = uuid_module.UUID(transaction_id)
        status_info = await check_cashout_status(transaction_id=transaction_uuid, db=db)
        
        # Verify transaction belongs to current user
        result = await db.execute(
            select(CashoutTransaction).where(CashoutTransaction.id == transaction_uuid)
        )
        transaction = result.scalar_one_or_none()
        
        if not transaction or transaction.user_id != current_user.id:
            raise HTTPException(status_code=404, detail="Transaction not found")
        
        return status_info
        
    except CashoutError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid transaction ID")
    except Exception as e:
        print(f"❌ Error getting cashout status: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get cashout status: {str(e)}")


@router.post("/api/wallet/cashout-cancel/{transaction_id}")
async def cancel_cashout_request(
    transaction_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_session)
):
    """
    Cancel a pending cashout transaction and return gems to user.
    """
    # Rate limiting check (prevent abuse of cancel/re-request)
    user_key = f"cashout_cancel_{current_user.id}"
    if not cashout_rate_limiter.is_allowed(user_key):
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many requests. Please wait a minute and try again."
        )
    
    try:
        # Parse transaction ID
        try:
            transaction_uuid = uuid_module.UUID(transaction_id)
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid transaction ID format")
        
        # Use the new cancellation service
        result = await cancel_cashout_transaction(
            transaction_id=str(transaction_uuid),
            user=current_user,
            db=db,
            reason="User requested cancellation"
        )
        
        return result
        
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        print(f"❌ Error cancelling cashout: {e}")
        print(f"   Stack trace: {traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=f"Failed to cancel cashout: {str(e)}")


@router.post("/api/wallet/redeem")
async def redeem_cashout(
    request: Request,
    db: AsyncSession = Depends(get_async_session)
):
    """
    Redeem a cashout code (called from MTurk HIT).
    Validates code and processes payment immediately.
    """
    body = await request.json()
    redemption_code = body.get('redemption_code', '').strip()
    worker_id = body.get('worker_id', '').strip()
    assignment_id = body.get('assignment_id', '').strip()
    hit_id = body.get('hit_id', '').strip()
    
    if not all([redemption_code, worker_id, assignment_id, hit_id]):
        raise HTTPException(status_code=400, detail="Missing required fields")
    
    try:
        result = await redeem_cashout_code(
            redemption_code=redemption_code,
            worker_id=worker_id,
            assignment_id=assignment_id,
            hit_id=hit_id,
            db=db
        )
        
        return result
        
    except CashoutError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        print(f"❌ Error redeeming cashout: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to process redemption: {str(e)}")


