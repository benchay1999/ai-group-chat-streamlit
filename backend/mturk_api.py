"""
AWS Mechanical Turk API Integration
Handles HIT creation, assignment approval, and bonus payments for MTurk workers.
"""

import os
from typing import Dict, List, Optional
from decimal import Decimal
import boto3
from botocore.exceptions import ClientError
from dotenv import load_dotenv

load_dotenv()


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
        
        # Initialize boto3 client
        self.client = boto3.client(
            'mturk',
            endpoint_url=self.endpoints[self.environment],
            region_name='us-east-1',
            aws_access_key_id=os.getenv('AWS_ACCESS_KEY_ID'),
            aws_secret_access_key=os.getenv('AWS_SECRET_ACCESS_KEY')
        )
        
        # Configuration
        self.base_pay = Decimal(os.getenv('MTURK_BASE_PAY', '0.05'))
        self.external_url = os.getenv('EXTERNAL_URL', 'http://localhost:5173/lobby')
        self.frame_height = int(os.getenv('MTURK_FRAME_HEIGHT', '0'))
        
        print(f"✅ MTurk client initialized ({self.environment} environment)")
        
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
    
    def create_hit(
        self,
        title: str,
        description: str,
        keywords: str,
        reward: Optional[Decimal] = None,
        max_assignments: int = 1,
        assignment_duration_in_seconds: int = 1800,  # 30 minutes
        lifetime_in_seconds: int = 86400,  # 24 hours
        auto_approval_delay_in_seconds: int = 259200,  # 3 days
        qualification_requirements: Optional[List[Dict]] = None
    ) -> Dict:
        """
        Create a HIT with ExternalQuestion pointing to the game.
        
        Args:
            title: HIT title shown to workers
            description: HIT description
            keywords: Comma-separated keywords for search
            reward: Payment amount (defaults to base_pay)
            max_assignments: Number of workers to complete this HIT
            assignment_duration_in_seconds: Time worker has to complete after accepting
            lifetime_in_seconds: How long HIT is available
            auto_approval_delay_in_seconds: Time before auto-approval
            qualification_requirements: List of qualification requirements
            
        Returns:
            Dict with HIT details including HITId
        """
        if reward is None:
            reward = self.base_pay
            
        # Build ExternalQuestion XML
        external_question = f"""<?xml version="1.0" encoding="UTF-8"?>
<ExternalQuestion xmlns="http://mechanicalturk.amazonaws.com/AWSMechanicalTurkDataSchemas/2006-07-14/ExternalQuestion.xsd">
  <ExternalURL>{self.external_url}</ExternalURL>
  <FrameHeight>{self.frame_height}</FrameHeight>
</ExternalQuestion>"""
        
        try:
            response = self.client.create_hit(
                Title=title,
                Description=description,
                Keywords=keywords,
                Reward=str(reward),
                MaxAssignments=max_assignments,
                LifetimeInSeconds=lifetime_in_seconds,
                AssignmentDurationInSeconds=assignment_duration_in_seconds,
                AutoApprovalDelayInSeconds=auto_approval_delay_in_seconds,
                Question=external_question,
                QualificationRequirements=qualification_requirements or []
            )
            
            hit = response['HIT']
            print(f"✅ Created HIT: {hit['HITId']}")
            
            return {
                'hit_id': hit['HITId'],
                'hit_type_id': hit['HITTypeId'],
                'hit_group_id': hit['HITGroupId'],
                'creation_time': hit['CreationTime'],
                'expiration': hit['Expiration'],
                'max_assignments': hit['MaxAssignments'],
                'reward': hit['Reward'],
                'title': hit['Title']
            }
            
        except ClientError as e:
            print(f"❌ Error creating HIT: {e}")
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
    
    def list_hits(self, max_results: int = 100) -> List[Dict]:
        """
        List all HITs for this requester.
        
        Args:
            max_results: Maximum number of HITs to return
            
        Returns:
            List of HIT dictionaries
        """
        try:
            response = self.client.list_hits(MaxResults=max_results)
            hits = response.get('HITs', [])
            
            # Format for easier consumption
            formatted_hits = []
            for hit in hits:
                formatted_hits.append({
                    'hit_id': hit['HITId'],
                    'title': hit['Title'],
                    'reward': hit['Reward'],
                    'status': hit['HITStatus'],
                    'max_assignments': hit['MaxAssignments'],
                    'available': hit['NumberOfAssignmentsAvailable'],
                    'pending': hit['NumberOfAssignmentsPending'],
                    'completed': hit['NumberOfAssignmentsCompleted'],
                    'creation_time': hit['CreationTime'],
                    'expiration': hit['Expiration']
                })
            
            return formatted_hits
            
        except ClientError as e:
            print(f"❌ Error listing HITs: {e}")
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
def create_game_hit(
    max_workers: int = 1,
    title: str = "Play a group chat game and identify AI players",
    description: str = "Join a 5-minute group chat game, discuss a topic with other players, and vote for who you think is an AI. Fun and engaging!",
    keywords: str = "chat, game, conversation, AI, discussion",
    reward: Optional[Decimal] = None
) -> Dict:
    """
    Create a HIT for the group chat game with sensible defaults.
    
    Args:
        max_workers: Number of workers needed
        title: HIT title
        description: HIT description
        keywords: Search keywords
        reward: Base reward (defaults to configured base pay)
        
    Returns:
        Dict with HIT details
    """
    client = get_mturk_client()
    return client.create_hit(
        title=title,
        description=description,
        keywords=keywords,
        reward=reward,
        max_assignments=max_workers,
        assignment_duration_in_seconds=1800,  # 30 minutes to complete
        lifetime_in_seconds=86400,  # Available for 24 hours
        auto_approval_delay_in_seconds=259200  # Auto-approve after 3 days
    )


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

