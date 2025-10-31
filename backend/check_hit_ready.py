"""
Check if MTurk HIT is ready for a transaction
"""
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from .database import CashoutTransaction, User, CashoutStatus
from .mturk_api import get_mturk_client


async def check_hit_ready(transaction_id: str, user: User, db: AsyncSession) -> dict:
    """
    Check if the HIT is ready for the worker to access.
    
    This verifies:
    1. Transaction exists and belongs to user
    2. HIT was created
    3. Worker has the required qualification
    
    Returns:
        dict with 'ready' boolean and optional 'message'
    """
    
    # Get transaction
    result = await db.execute(
        select(CashoutTransaction)
        .where(CashoutTransaction.id == transaction_id)
    )
    transaction = result.scalar_one_or_none()
    
    if not transaction:
        return {
            "ready": False,
            "message": "Transaction not found"
        }
    
    # Check ownership
    if str(transaction.user_id) != str(user.id):
        return {
            "ready": False,
            "message": "Unauthorized"
        }
    
    # Check if HIT was created
    if not transaction.mturk_hit_id:
        return {
            "ready": False,
            "message": "HIT not created yet"
        }
    
    if transaction.status != CashoutStatus.HIT_CREATED:
        return {
            "ready": False,
            "message": f"Transaction status: {transaction.status}"
        }
    
    # Check if worker has qualification
    try:
        mturk_client = get_mturk_client()
        
        # Get HIT details to find qualification ID
        hit_response = mturk_client.client.get_hit(HITId=transaction.mturk_hit_id)
        hit = hit_response['HIT']
        
        # Get qualification requirements
        qual_reqs = hit.get('QualificationRequirements', [])
        
        if not qual_reqs:
            # No qualification required, HIT is ready
            return {
                "ready": True,
                "message": "HIT is ready (no qualification required)"
            }
        
        # Check if worker has the required qualification
        qualification_id = qual_reqs[0]['QualificationTypeId']
        
        try:
            qual_check = mturk_client.client.get_qualification_score(
                QualificationTypeId=qualification_id,
                WorkerId=user.mturk_worker_id.strip()
            )
            
            qual_value = qual_check['Qualification'].get('IntegerValue', 0)
            
            if qual_value == 1:
                return {
                    "ready": True,
                    "message": "HIT is ready - qualification verified"
                }
            else:
                return {
                    "ready": False,
                    "message": f"Qualification value incorrect: {qual_value}"
                }
                
        except Exception as qual_error:
            # Worker doesn't have qualification yet
            return {
                "ready": False,
                "message": "Qualification not assigned yet, please wait..."
            }
            
    except Exception as e:
        print(f"❌ Error checking HIT readiness: {e}")
        return {
            "ready": False,
            "message": f"Error checking HIT: {str(e)}"
        }

