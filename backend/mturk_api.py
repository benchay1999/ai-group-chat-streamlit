"""
AWS Mechanical Turk API Integration
Handles HIT creation, assignment approval, and bonus payments for MTurk workers.
"""

import os
from typing import Dict, List, Optional
from decimal import Decimal
import boto3
from botocore.exceptions import ClientError

# Use robust environment configuration
try:
    from . import env_config
except ImportError:
    # Fallback for standalone scripts
    from dotenv import load_dotenv
    load_dotenv(override=True)


class MTurkClient:
    """
    Wrapper for AWS MTurk API operations.
    Supports both sandbox and production environments.
    """
    
    def __init__(self):
        """Initialize MTurk client with credentials from environment."""
        self.environment = os.getenv('MTURK_ENVIRONMENT', 'sandbox')
        
        # MTurk endpoints
        self.endpoints = {
            'sandbox': 'https://mturk-requester-sandbox.us-east-1.amazonaws.com',
            'production': 'https://mturk-requester.us-east-1.amazonaws.com'
        }
        
        # Worker sandbox endpoint (for submit URL)
        self.worker_endpoints = {
            'sandbox': 'https://workersandbox.mturk.com',
            'production': 'https://www.mturk.com'
        }
        
        # Get AWS credentials
        aws_access_key_id = os.getenv('AWS_ACCESS_KEY_ID')
        aws_secret_access_key = os.getenv('AWS_SECRET_ACCESS_KEY')
        
        # Validate credentials exist
        if not aws_access_key_id or not aws_secret_access_key:
            error_msg = "AWS credentials not configured. Please set AWS_ACCESS_KEY_ID and AWS_SECRET_ACCESS_KEY in .env file"
            print(f"❌ MTurkClient initialization failed: {error_msg}")
            raise ValueError(error_msg)
        
        print(f"🔧 Initializing MTurk client...")
        print(f"   Environment: {self.environment}")
        print(f"   Endpoint: {self.endpoints[self.environment]}")
        print(f"   AWS Key ID: {aws_access_key_id[:8]}...{aws_access_key_id[-4:] if len(aws_access_key_id) > 12 else '***'}")
        
        # Initialize boto3 client
        try:
            self.client = boto3.client(
                'mturk',
                endpoint_url=self.endpoints[self.environment],
                region_name='us-east-1',
                aws_access_key_id=aws_access_key_id,
                aws_secret_access_key=aws_secret_access_key
            )
            print(f"✅ MTurk client initialized successfully ({self.environment} environment)")
        except Exception as e:
            print(f"❌ Failed to initialize MTurk boto3 client: {e}")
            raise
        
        # Configuration
        self.base_pay = Decimal(os.getenv('MTURK_BASE_PAY', '0.05'))
        self.external_url = os.getenv('EXTERNAL_URL', 'http://localhost:5173/lobby')
        self.frame_height = int(os.getenv('MTURK_FRAME_HEIGHT', '0'))
        
    def get_account_balance(self) -> Dict:
        """
        Get the current account balance.
        Useful for verifying API credentials and checking available funds.
        
        Returns:
            Dict with AvailableBalance and OnHoldBalance
        """
        try:
            response = self.client.get_account_balance()
            return {
                'available': response['AvailableBalance'],
                'on_hold': response.get('OnHoldBalance', '0.00')
            }
        except ClientError as e:
            print(f"❌ Error getting account balance: {e}")
            raise
    
    def get_hit(self, hit_id: str) -> Dict:
        """
        Get details about a specific HIT.
        
        Args:
            hit_id: The HIT ID
            
        Returns:
            Dict with HIT details
        """
        try:
            response = self.client.get_hit(HITId=hit_id)
            return response['HIT']
        except ClientError as e:
            print(f"❌ Error getting HIT {hit_id}: {e}")
            raise
    
    def get_assignment(self, assignment_id: str) -> Dict:
        """
        Get details about a specific assignment.
        
        Args:
            assignment_id: The assignment ID
            
        Returns:
            Dict with assignment details
        """
        try:
            response = self.client.get_assignment(AssignmentId=assignment_id)
            assignment = response['Assignment']
            
            return {
                'assignment_id': assignment['AssignmentId'],
                'worker_id': assignment['WorkerId'],
                'hit_id': assignment['HITId'],
                'status': assignment['AssignmentStatus'],
                'accept_time': assignment['AcceptTime'],
                'submit_time': assignment.get('SubmitTime'),
                'approval_time': assignment.get('ApprovalTime'),
                'rejection_time': assignment.get('RejectionTime'),
                'answer': assignment.get('Answer')
            }
            
        except ClientError as e:
            print(f"❌ Error getting assignment {assignment_id}: {e}")
            raise
    
    def list_assignments_for_hit(self, hit_id: str) -> List[Dict]:
        """
        List all assignments for a specific HIT.
        
        Args:
            hit_id: The HIT ID
            
        Returns:
            List of assignment dictionaries
        """
        try:
            response = self.client.list_assignments_for_hit(HITId=hit_id)
            assignments = response.get('Assignments', [])
            
            formatted = []
            for assignment in assignments:
                formatted.append({
                    'assignment_id': assignment['AssignmentId'],
                    'worker_id': assignment['WorkerId'],
                    'status': assignment['AssignmentStatus'],
                    'accept_time': assignment['AcceptTime'],
                    'submit_time': assignment.get('SubmitTime')
                })
            
            return formatted
            
        except ClientError as e:
            print(f"❌ Error listing assignments for HIT {hit_id}: {e}")
            raise
    
    def approve_assignment(
        self,
        assignment_id: str,
        requester_feedback: Optional[str] = None,
        override_rejection: bool = False
    ) -> bool:
        """
        Approve an assignment and pay the worker the base reward.
        
        Args:
            assignment_id: The assignment ID to approve
            requester_feedback: Optional feedback message to worker
            override_rejection: If True, can approve a previously rejected assignment
            
        Returns:
            True if successful
        """
        try:
            params = {
                'AssignmentId': assignment_id,
                'OverrideRejection': override_rejection
            }
            
            if requester_feedback:
                params['RequesterFeedback'] = requester_feedback
            
            self.client.approve_assignment(**params)
            print(f"✅ Approved assignment: {assignment_id}")
            return True
            
        except ClientError as e:
            print(f"❌ Error approving assignment {assignment_id}: {e}")
            raise
    
    def reject_assignment(
        self,
        assignment_id: str,
        requester_feedback: str
    ) -> bool:
        """
        Reject an assignment (worker does not get paid).
        
        Args:
            assignment_id: The assignment ID to reject
            requester_feedback: Required feedback explaining rejection
            
        Returns:
            True if successful
        """
        try:
            self.client.reject_assignment(
                AssignmentId=assignment_id,
                RequesterFeedback=requester_feedback
            )
            print(f"⚠️  Rejected assignment: {assignment_id}")
            return True
            
        except ClientError as e:
            print(f"❌ Error rejecting assignment {assignment_id}: {e}")
            raise
    
    def send_bonus(
        self,
        worker_id: str,
        assignment_id: str,
        bonus_amount: Decimal,
        reason: str
    ) -> bool:
        """
        Send a bonus payment to a worker.
        Must be called after the assignment has been approved.
        
        Args:
            worker_id: The worker's ID
            assignment_id: The assignment ID
            bonus_amount: Bonus amount in USD
            reason: Explanation for the bonus (shown to worker)
            
        Returns:
            True if successful
        """
        try:
            # MTurk requires bonus to be at least $0.01
            if bonus_amount < Decimal('0.01'):
                print(f"⚠️  Bonus amount ${bonus_amount} is below minimum $0.01, skipping")
                return False
            
            self.client.send_bonus(
                WorkerId=worker_id,
                AssignmentId=assignment_id,
                BonusAmount=str(bonus_amount),
                Reason=reason
            )
            
            print(f"✅ Sent bonus ${bonus_amount} to worker {worker_id}")
            return True
            
        except ClientError as e:
            print(f"❌ Error sending bonus to {worker_id}: {e}")
            raise
    
    def approve_and_bonus(
        self,
        assignment_id: str,
        worker_id: str,
        bonus_amount: Optional[Decimal] = None,
        bonus_reason: Optional[str] = None,
        requester_feedback: Optional[str] = None
    ) -> Dict[str, bool]:
        """
        Convenience method to approve assignment and send bonus in one call.
        
        Args:
            assignment_id: The assignment ID
            worker_id: The worker's ID
            bonus_amount: Optional bonus amount
            bonus_reason: Reason for bonus (required if bonus_amount provided)
            requester_feedback: Optional feedback for approval
            
        Returns:
            Dict with 'approved' and 'bonus_sent' boolean flags
        """
        result = {
            'approved': False,
            'bonus_sent': False
        }
        
        # Approve assignment first
        try:
            result['approved'] = self.approve_assignment(
                assignment_id,
                requester_feedback=requester_feedback
            )
        except Exception as e:
            print(f"❌ Failed to approve assignment: {e}")
            return result
        
        # Send bonus if specified
        if bonus_amount and bonus_amount > 0:
            if not bonus_reason:
                bonus_reason = "Performance bonus for quality work"
            
            try:
                result['bonus_sent'] = self.send_bonus(
                    worker_id,
                    assignment_id,
                    bonus_amount,
                    bonus_reason
                )
            except Exception as e:
                print(f"❌ Failed to send bonus: {e}")
                # Assignment was approved, so we still return success for that
        
        return result
    
    def delete_hit(self, hit_id: str) -> bool:
        """
        Delete a HIT (only works if no assignments have been submitted).
        
        Args:
            hit_id: The HIT ID to delete
            
        Returns:
            True if successful
        """
        try:
            self.client.delete_hit(HITId=hit_id)
            print(f"✅ Deleted HIT: {hit_id}")
            return True
        except ClientError as e:
            print(f"❌ Error deleting HIT {hit_id}: {e}")
            raise
    
    def expire_hit(self, hit_id: str) -> bool:
        """
        Expire a HIT immediately (makes it unavailable to workers).
        
        Args:
            hit_id: The HIT ID to expire
            
        Returns:
            True if successful
        """
        try:
            self.client.update_expiration_for_hit(
                HITId=hit_id,
                ExpireAt=0  # Expire immediately
            )
            print(f"✅ Expired HIT: {hit_id}")
            return True
        except ClientError as e:
            print(f"❌ Error expiring HIT {hit_id}: {e}")
            raise
    
    def create_worker_qualification(self, worker_id: str, qualification_name: str) -> str:
        """
        Create a unique qualification for a specific worker (for cashout HITs).
        
        Args:
            worker_id: MTurk Worker ID
            qualification_name: Name for the qualification
            
        Returns:
            Qualification ID
        """
        try:
            response = self.client.create_qualification_type(
                Name=qualification_name,
                Description=f"Unique qualification for worker {worker_id} to access their cashout HIT",
                QualificationTypeStatus='Active',
                AutoGranted=False  # We'll manually assign to specific worker
            )
            
            qualification_id = response['QualificationType']['QualificationTypeId']
            print(f"✅ Created qualification: {qualification_id}")
            return qualification_id
            
        except ClientError as e:
            print(f"❌ Error creating qualification: {e}")
            raise
    
    def assign_qualification_to_worker(self, qualification_id: str, worker_id: str, value: int = 1) -> bool:
        """
        Assign a qualification to a specific worker.
        
        Args:
            qualification_id: The qualification type ID
            worker_id: The worker's ID
            value: Qualification value (default: 1)
            
        Returns:
            True if successful
        """
        try:
            self.client.associate_qualification_with_worker(
                QualificationTypeId=qualification_id,
                WorkerId=worker_id,
                IntegerValue=value,
                SendNotification=False
            )
            print(f"✅ Assigned qualification {qualification_id} to worker {worker_id}")
            return True
            
        except ClientError as e:
            print(f"❌ Error assigning qualification: {e}")
            raise
    
    def create_cashout_hit(
        self,
        amount: Decimal,
        qualification_id: str,
        worker_id: str,
        external_url: str,
        duration_seconds: int = 86400,
        auto_approve_seconds: int = 3600
    ) -> Dict:
        """
        Create a cashout HIT that only the specified worker can see and complete.
        
        Args:
            amount: Payment amount in USD
            qualification_id: Unique qualification ID (only assigned to target worker)
            worker_id: MTurk worker ID (for display purposes)
            external_url: URL for the cashout confirmation page
            duration_seconds: How long HIT is available (default: 24 hours)
            auto_approve_seconds: Auto-approval delay (default: 1 hour)
            
        Returns:
            Dict with HIT details including hit_id and hit_url
        """
        # Build ExternalQuestion XML for cashout confirmation page
        # Important: Escape XML special characters in URL (& becomes &amp;)
        import xml.sax.saxutils as saxutils
        escaped_url = saxutils.escape(external_url)
        
        external_question = f"""<?xml version="1.0" encoding="UTF-8"?>
<ExternalQuestion xmlns="http://mechanicalturk.amazonaws.com/AWSMechanicalTurkDataSchemas/2006-07-14/ExternalQuestion.xsd">
  <ExternalURL>{escaped_url}</ExternalURL>
  <FrameHeight>{self.frame_height}</FrameHeight>
</ExternalQuestion>"""
        
        # Qualification requirement: worker must have the unique qualification
        # No ActionsGuarded - just basic requirement check
        # This allows qualified workers to see and accept, non-qualified cannot accept
        qualification_requirements = [
            {
                'QualificationTypeId': qualification_id,
                'Comparator': 'EqualTo',
                'IntegerValues': [1]
            }
        ]
        
        # Format amount properly for MTurk (must be string with 2 decimal places)
        reward_amount = f"{float(amount):.2f}"
        
        print(f"💰 Creating HIT with reward: ${reward_amount} (from amount: {amount}, type: {type(amount)})")
        
        try:
            response = self.client.create_hit(
                Title=f"ChatGame Payout - ${reward_amount}",
                Description=f"Confirm your ${reward_amount} payout from ChatGame. Only you can see this HIT.",
                Keywords="payout, payment, confirmation",
                Reward=reward_amount,
                MaxAssignments=1,
                LifetimeInSeconds=duration_seconds,
                AssignmentDurationInSeconds=1800,  # 30 minutes to complete once accepted
                AutoApprovalDelayInSeconds=auto_approve_seconds,
                Question=external_question,
                QualificationRequirements=qualification_requirements
            )
            
            hit = response['HIT']
            hit_id = hit['HITId']
            
            # Build worker-facing URL
            worker_endpoint = self.worker_endpoints[self.environment]
            hit_url = f"{worker_endpoint}/mturk/preview?groupId={hit['HITGroupId']}"
            
            # Log the actual reward that was set
            actual_reward = hit.get('Reward', 'Unknown')
            print(f"✅ Created cashout HIT: {hit_id}")
            print(f"   💵 Reward set to: ${actual_reward}")
            print(f"   🔗 Worker URL: {hit_url}")
            
            # Verify the reward matches what we requested
            if actual_reward != reward_amount:
                print(f"   ⚠️  WARNING: Reward mismatch! Requested: ${reward_amount}, Got: ${actual_reward}")
            
            return {
                'hit_id': hit_id,
                'hit_type_id': hit['HITTypeId'],
                'hit_group_id': hit['HITGroupId'],
                'hit_url': hit_url,
                'amount': str(amount),
                'expiration': hit['Expiration'].isoformat() if hit.get('Expiration') else None
            }
            
        except ClientError as e:
            print(f"❌ Error creating cashout HIT: {e}")
            raise
    
    def check_hit_status(self, hit_id: str) -> Dict:
        """
        Check the status of a HIT including assignment information.
        
        Args:
            hit_id: The HIT ID
            
        Returns:
            Dict with HIT status and assignment details
        """
        try:
            # Get HIT details
            hit = self.get_hit(hit_id)
            
            # Get assignments
            assignments = self.list_assignments_for_hit(hit_id)
            
            return {
                'hit_status': hit.get('HITStatus'),
                'assignments_available': hit.get('NumberOfAssignmentsAvailable', 0),
                'assignments_pending': hit.get('NumberOfAssignmentsPending', 0),
                'assignments_completed': hit.get('NumberOfAssignmentsCompleted', 0),
                'expiration': hit.get('Expiration'),
                'assignments': assignments
            }
            
        except ClientError as e:
            print(f"❌ Error checking HIT status {hit_id}: {e}")
            raise
    
    def find_and_approve_cashout_assignment(self, hit_id: str) -> Optional[str]:
        """
        Find a submitted assignment for a cashout HIT and approve it.
        
        Args:
            hit_id: The HIT ID
            
        Returns:
            Assignment ID if found and approved, None otherwise
        """
        try:
            assignments = self.list_assignments_for_hit(hit_id)
            
            for assignment in assignments:
                if assignment['status'] == 'Submitted':
                    assignment_id = assignment['assignment_id']
                    
                    # Approve the assignment
                    self.approve_assignment(
                        assignment_id=assignment_id,
                        requester_feedback="Thank you! Your payment has been processed."
                    )
                    
                    print(f"✅ Approved cashout assignment: {assignment_id}")
                    return assignment_id
            
            return None
            
        except ClientError as e:
            print(f"❌ Error approving cashout assignment for HIT {hit_id}: {e}")
            raise
    
    def expire_and_delete_hit(self, hit_id: str) -> bool:
        """
        Expire a HIT immediately and attempt to delete it.
        
        Args:
            hit_id: The HIT ID
            
        Returns:
            True if successful
        """
        try:
            # First, expire the HIT
            self.expire_hit(hit_id)
            
            # Try to delete (only works if no assignments submitted)
            try:
                self.delete_hit(hit_id)
            except ClientError as e:
                # If delete fails (e.g., assignments exist), that's okay
                print(f"⚠️  Could not delete HIT {hit_id} (may have assignments): {e}")
            
            return True
            
        except ClientError as e:
            print(f"❌ Error expiring/deleting HIT {hit_id}: {e}")
            raise


# Global client instance
_mturk_client: Optional[MTurkClient] = None


def get_mturk_client() -> MTurkClient:
    """
    Get or create the global MTurk client instance.
    
    Returns:
        MTurkClient instance
    """
    global _mturk_client
    if _mturk_client is None:
        _mturk_client = MTurkClient()
    return _mturk_client


# Convenience functions for common operations
def process_payment(
    assignment_id: str,
    worker_id: str,
    calculated_earnings: Decimal,
    base_pay: Optional[Decimal] = None,
    max_bonus: Optional[Decimal] = None
) -> Dict[str, bool]:
    """
    Process payment for a completed session: approve assignment + send bonus.
    
    Args:
        assignment_id: MTurk assignment ID
        worker_id: MTurk worker ID
        calculated_earnings: Total earnings calculated by system
        base_pay: Base payment amount (defaults to configured base pay)
        max_bonus: Maximum bonus amount (defaults to base_pay, i.e., 2x total max)
        
    Returns:
        Dict with 'approved' and 'bonus_sent' flags
    """
    client = get_mturk_client()
    
    if base_pay is None:
        base_pay = client.base_pay
    
    # Default max_bonus to base_pay (so total payment = 2x base_pay maximum)
    if max_bonus is None:
        max_bonus = base_pay
    
    # Calculate bonus (total - base), but cap at max_bonus
    raw_bonus = calculated_earnings - base_pay
    bonus_amount = min(raw_bonus, max_bonus)
    
    # Calculate actual total payment
    actual_total = base_pay + bonus_amount
    
    # Prepare bonus reason
    if bonus_amount > 0:
        if raw_bonus > max_bonus:
            bonus_reason = f"Performance bonus: ${bonus_amount:.2f} (capped, earned ${raw_bonus:.2f}) - Total payment: ${actual_total:.2f}"
        else:
            bonus_reason = f"Performance bonus: ${bonus_amount:.2f} for quality participation - Total payment: ${actual_total:.2f}"
    else:
        bonus_reason = None
    
    return client.approve_and_bonus(
        assignment_id=assignment_id,
        worker_id=worker_id,
        bonus_amount=bonus_amount if bonus_amount > 0 else None,
        bonus_reason=bonus_reason,
        requester_feedback="Thank you for participating in our research!"
    )

