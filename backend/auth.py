"""
Authentication and authorization logic.
Handles password hashing, JWT token generation/verification, and role-based access control.
"""

from datetime import datetime, timedelta
from typing import Optional
from jose import JWTError, jwt
from passlib.context import CryptContext
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
import os
from dotenv import load_dotenv

from .database import User, UserRole, get_async_session

load_dotenv()

# JWT Configuration
JWT_SECRET_KEY = os.getenv('JWT_SECRET_KEY', 'your-secret-key-change-this-in-production')
JWT_ALGORITHM = 'HS256'
ACCESS_TOKEN_EXPIRE_HOURS = 24

# Password hashing configuration using Argon2
# Argon2 is modern, secure, and has NO password length limits (unlike bcrypt's 72 bytes)
pwd_context = CryptContext(
    schemes=["argon2"],
    deprecated="auto",
    argon2__memory_cost=65536,  # 64 MB
    argon2__time_cost=3,  # 3 iterations
    argon2__parallelism=4  # 4 parallel threads
)

# HTTP Bearer token security
security = HTTPBearer()


def hash_password(password: str) -> str:
    """
    Hash a password using Argon2.
    
    Argon2 has NO password length limits and is more secure than bcrypt.
    Winner of the Password Hashing Competition 2015.
    """
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    Verify a password against its Argon2 hash.
    """
    return pwd_context.verify(plain_password, hashed_password)


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """
    Create a JWT access token.
    
    Args:
        data: Dictionary with user data to encode
        expires_delta: Optional expiration time delta
    
    Returns:
        Encoded JWT token
    """
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(hours=ACCESS_TOKEN_EXPIRE_HOURS)
    
    to_encode.update({"exp": expire, "iat": datetime.utcnow()})
    encoded_jwt = jwt.encode(to_encode, JWT_SECRET_KEY, algorithm=JWT_ALGORITHM)
    return encoded_jwt


def decode_access_token(token: str) -> dict:
    """
    Decode and verify a JWT access token.
    
    Args:
        token: JWT token string
    
    Returns:
        Decoded token payload
    
    Raises:
        JWTError: If token is invalid or expired
    """
    try:
        payload = jwt.decode(token, JWT_SECRET_KEY, algorithms=[JWT_ALGORITHM])
        return payload
    except JWTError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Invalid authentication token: {str(e)}",
            headers={"WWW-Authenticate": "Bearer"},
        )


async def get_user_by_user_id(db: AsyncSession, user_id: str) -> Optional[User]:
    """Get user by their user_id."""
    result = await db.execute(select(User).where(User.user_id == user_id))
    return result.scalar_one_or_none()


async def get_user_by_uuid(db: AsyncSession, user_uuid: str) -> Optional[User]:
    """Get user by their UUID."""
    result = await db.execute(select(User).where(User.id == user_uuid))
    return result.scalar_one_or_none()


async def authenticate_user(db: AsyncSession, user_id: str, password: str) -> Optional[User]:
    """
    Authenticate a user with user_id and password.
    
    Args:
        db: Database session
        user_id: User's identifier
        password: Plain text password
    
    Returns:
        User object if authentication successful, None otherwise
    """
    user = await get_user_by_user_id(db, user_id)
    if not user:
        return None
    if not verify_password(password, user.password_hash):
        return None
    return user


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: AsyncSession = Depends(get_async_session)
) -> User:
    """
    Dependency to get the current authenticated user from JWT token.
    
    Args:
        credentials: HTTP Bearer token from request
        db: Database session
    
    Returns:
        Current User object
    
    Raises:
        HTTPException: If token is invalid or user not found
    """
    token = credentials.credentials
    payload = decode_access_token(token)
    
    user_uuid: str = payload.get("sub")
    if user_uuid is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    user = await get_user_by_uuid(db, user_uuid)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    return user


async def get_current_user_optional(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(HTTPBearer(auto_error=False)),
    db: AsyncSession = Depends(get_async_session)
) -> Optional[User]:
    """
    Dependency to get the current user if authenticated, or None if not.
    Does not raise an error if no token is provided.
    
    Args:
        credentials: Optional HTTP Bearer token from request
        db: Database session
    
    Returns:
        Current User object or None
    """
    if credentials is None:
        return None
    
    try:
        token = credentials.credentials
        payload = decode_access_token(token)
        user_uuid: str = payload.get("sub")
        
        if user_uuid is None:
            return None
        
        user = await get_user_by_uuid(db, user_uuid)
        return user
    except HTTPException:
        return None


def require_admin(current_user: User = Depends(get_current_user)) -> User:
    """
    Dependency to ensure current user has admin role.
    
    Args:
        current_user: Current authenticated user
    
    Returns:
        Current user if admin
    
    Raises:
        HTTPException: If user is not an admin
    """
    if current_user.role != UserRole.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required"
        )
    return current_user


# Helper function to create first admin user
async def create_admin_user(db: AsyncSession, user_id: str, password: str) -> User:
    """
    Create an admin user. Use this for initial setup.
    
    Args:
        db: Database session
        user_id: Admin user identifier
        password: Admin password
    
    Returns:
        Created User object
    """
    hashed_password = hash_password(password)
    admin_user = User(
        user_id=user_id,
        password_hash=hashed_password,
        role=UserRole.ADMIN
    )
    db.add(admin_user)
    await db.commit()
    await db.refresh(admin_user)
    return admin_user

