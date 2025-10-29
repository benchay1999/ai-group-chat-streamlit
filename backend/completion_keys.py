"""
Completion key management for Mechanical Turk compensation tracking.
Uses JWT tokens to encode session metadata in a verifiable, tamper-proof format.
"""

from datetime import datetime
from typing import Dict, Optional
from jose import JWTError, jwt
from fastapi import HTTPException, status
import os
from dotenv import load_dotenv

load_dotenv()

# Separate secret for completion keys (never expires, different from auth tokens)
JWT_COMPLETION_SECRET = os.getenv('JWT_COMPLETION_SECRET', 'completion-secret-key-change-this')
JWT_ALGORITHM = 'HS256'


def generate_completion_key(
    session_id: str,
    room_code: str,
    language: str,
    total_players: int,
    num_humans: int,
    discussion_duration: int,
    voting_duration: int,
    completed_at: float
) -> str:
    """
    Generate a JWT completion key encoding session metadata.
    
    Args:
        session_id: UUID of the session in database
        room_code: Original room code
        language: Session language (english/korean)
        total_players: Total number of players
        num_humans: Number of human players
        discussion_duration: Discussion phase duration in seconds
        voting_duration: Voting phase duration in seconds
        completed_at: Unix timestamp of completion
    
    Returns:
        JWT token encoding all session metadata
    """
    payload = {
        "session_id": str(session_id),
        "room_code": room_code,
        "language": language,
        "total_players": total_players,
        "num_humans": num_humans,
        "discussion_duration": discussion_duration,
        "voting_duration": voting_duration,
        "completed_at": completed_at,
        "iat": datetime.utcnow().timestamp()
    }
    
    # No expiration for completion keys - they should remain valid indefinitely
    token = jwt.encode(payload, JWT_COMPLETION_SECRET, algorithm=JWT_ALGORITHM)
    return token


def decode_completion_key(token: str) -> Dict:
    """
    Decode and verify a completion key.
    
    Args:
        token: JWT completion key
    
    Returns:
        Decoded payload dictionary
    
    Raises:
        HTTPException: If token is invalid or tampered with
    """
    try:
        payload = jwt.decode(token, JWT_COMPLETION_SECRET, algorithms=[JWT_ALGORITHM])
        
        # Validate required fields
        required_fields = [
            "session_id", "room_code", "language", "total_players",
            "num_humans", "discussion_duration", "voting_duration", "completed_at"
        ]
        
        for field in required_fields:
            if field not in payload:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Invalid completion key: missing field '{field}'"
                )
        
        return payload
    
    except JWTError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid completion key: {str(e)}"
        )


def extract_session_info(token: str) -> Dict:
    """
    Extract human-readable session information from completion key.
    Convenience wrapper around decode_completion_key.
    
    Args:
        token: JWT completion key
    
    Returns:
        Dictionary with session information
    """
    payload = decode_completion_key(token)
    
    return {
        "session_id": payload["session_id"],
        "room_code": payload["room_code"],
        "language": payload["language"],
        "total_players": payload["total_players"],
        "num_humans": payload["num_humans"],
        "discussion_duration": payload["discussion_duration"],
        "voting_duration": payload["voting_duration"],
        "completed_at": datetime.fromtimestamp(payload["completed_at"]).isoformat(),
        "issued_at": datetime.fromtimestamp(payload["iat"]).isoformat() if "iat" in payload else None
    }


def verify_completion_key(token: str) -> bool:
    """
    Quick verification that a completion key is valid.
    
    Args:
        token: JWT completion key
    
    Returns:
        True if valid, False otherwise
    """
    try:
        decode_completion_key(token)
        return True
    except HTTPException:
        return False

