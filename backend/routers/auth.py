from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from backend.database import get_async_session, User, UserRole, Session as DBSession
from backend.auth import (
    hash_password, authenticate_user, create_access_token,
    get_current_user, register_or_login_mturk_worker
)
from backend.schemas import (
    RegisterRequest, LoginRequest, LoginResponse, UserResponse, MTurkRegisterRequest
)
from backend.middleware_utils import (
    login_rate_limiter, register_rate_limiter, mturk_rate_limiter
)
from backend.security_monitor import log_rate_limit_violation, log_failed_login
from backend.config import MTURK_WORKER_ID_PATTERN

router = APIRouter()

@router.post("/api/auth/register")
async def register(
    request: RegisterRequest,
    http_request: Request,
    db: AsyncSession = Depends(get_async_session)
):
    """
    Register a new user.
    """
    # Rate limiting check
    client_ip = http_request.client.host
    if not register_rate_limiter.is_allowed(client_ip):
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many registration attempts. Please wait a minute and try again."
        )
    
    # Check if user already exists
    existing_user = await db.execute(
        select(User).where(User.user_id == request.user_id)
    )
    if existing_user.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User ID already exists"
        )
    
    # Create new user
    hashed_password = hash_password(request.password)
    new_user = User(
        user_id=request.user_id,
        password_hash=hashed_password,
        role=UserRole.USER
    )
    db.add(new_user)
    await db.commit()
    await db.refresh(new_user)
    
    return {
        "success": True,
        "message": "User registered successfully",
        "user_id": new_user.user_id
    }


@router.post("/api/auth/login", response_model=LoginResponse)
async def login(
    request: LoginRequest,
    http_request: Request,
    db: AsyncSession = Depends(get_async_session)
):
    """
    Authenticate user and return JWT token.
    """
    # Rate limiting check (prevent brute-force attacks)
    client_ip = http_request.client.host
    if not login_rate_limiter.is_allowed(client_ip):
        log_rate_limit_violation(client_ip, "/api/auth/login")
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many login attempts. Please wait a minute and try again."
        )
    
    user = await authenticate_user(db, request.user_id, request.password)
    if not user:
        # Log failed login attempt
        log_failed_login(request.user_id, client_ip, "Invalid credentials")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect user ID or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Create access token
    access_token = create_access_token(data={"sub": str(user.id)})
    
    return LoginResponse(
        access_token=access_token,
        token_type="bearer",
        user_id=user.user_id,
        role=user.role.value
    )


@router.get("/api/auth/me", response_model=UserResponse)
async def get_current_user_info(
    current_user: User = Depends(get_current_user)
):
    """
    Get current authenticated user information.
    """
    return UserResponse(
        id=str(current_user.id),
        user_id=current_user.user_id,
        role=current_user.role.value,
        created_at=current_user.created_at.isoformat()
    )


@router.get("/api/profile")
async def get_user_profile(
    current_user: User = Depends(get_current_user)
):
    """
    Get detailed user profile information including wallet and MTurk data.
    """
    from backend.cashout_service import gems_to_usd
    
    return {
        "id": str(current_user.id),
        "user_id": current_user.user_id,
        "role": current_user.role.value,
        "created_at": current_user.created_at.isoformat(),
        "mturk_worker_id": current_user.mturk_worker_id,
        "age": current_user.age,
        "gender": current_user.gender,
        "nationality": current_user.nationality,
        "major": current_user.major,
        "gem_balance": current_user.gem_balance,
        "gem_balance_usd": float(gems_to_usd(current_user.gem_balance)),
        "total_gems_earned": current_user.total_gems_earned,
        "total_gems_cashed_out": current_user.total_gems_cashed_out,
        "total_games": current_user.total_games,
        "total_wins": current_user.total_wins,
        "total_points": current_user.total_points,
        "level": current_user.level,
        "current_streak": current_user.current_streak,
        "longest_streak": current_user.longest_streak,
        "last_played_at": current_user.last_played_at.isoformat() if current_user.last_played_at else None
    }


@router.put("/api/profile/mturk-worker-id")
async def update_mturk_worker_id(
    request: Request,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_session)
):
    """
    Update user's MTurk Worker ID and demographic information.
    """
    import re
    
    body = await request.json()
    worker_id = body.get('worker_id', '').strip()
    age = body.get('age')
    gender = body.get('gender', '').strip().lower()
    nationality = body.get('nationality', '').strip()
    major = body.get('major', '').strip()
    
    # Validate MTurk Worker ID format (typically starts with 'A' and is alphanumeric)
    if worker_id:
        # MTurk Worker IDs are typically 14 characters starting with 'A'
        if not re.match(r'^A[A-Z0-9]{13,}$', worker_id):
            raise HTTPException(
                status_code=400,
                detail="Invalid MTurk Worker ID format. Worker IDs typically start with 'A' followed by alphanumeric characters (e.g., A12TU3EXAMPLE93)"
            )
        
        # Demographic fields are MANDATORY when setting worker ID
        if not age:
            raise HTTPException(
                status_code=400,
                detail="Age is required when setting MTurk Worker ID"
            )
        
        if not gender:
            raise HTTPException(
                status_code=400,
                detail="Gender is required when setting MTurk Worker ID"
            )
        
        if not nationality:
            raise HTTPException(
                status_code=400,
                detail="Nationality is required when setting MTurk Worker ID"
            )
        
        if not major:
            raise HTTPException(
                status_code=400,
                detail="Major/field of study is required when setting MTurk Worker ID"
            )
        
        # Validate age
        try:
            age_int = int(age)
            if age_int < 18 or age_int > 100:
                raise HTTPException(
                    status_code=400,
                    detail="Age must be between 18 and 100"
                )
        except (ValueError, TypeError):
            raise HTTPException(
                status_code=400,
                detail="Age must be a valid number"
            )
        
        # Validate gender
        valid_genders = ['male', 'female', 'wish_not_to_answer']
        if gender not in valid_genders:
            raise HTTPException(
                status_code=400,
                detail=f"Gender must be one of: {', '.join(valid_genders)}"
            )
        
        # Validate nationality and major (non-empty strings)
        if len(nationality) < 2:
            raise HTTPException(
                status_code=400,
                detail="Nationality must be at least 2 characters"
            )
        
        if len(major) < 2:
            raise HTTPException(
                status_code=400,
                detail="Major/field of study must be at least 2 characters"
            )
        
        # Update all fields atomically
        current_user.mturk_worker_id = worker_id
        current_user.age = age_int
        current_user.gender = gender
        current_user.nationality = nationality
        current_user.major = major
    else:
        # If clearing worker ID, clear demographics too
        current_user.mturk_worker_id = None
        current_user.age = None
        current_user.gender = None
        current_user.nationality = None
        current_user.major = None
    
    await db.commit()
    await db.refresh(current_user)
    
    print(f"✅ Updated MTurk Worker ID and demographics for user {current_user.user_id}: {worker_id}")
    
    return {
        "success": True,
        "mturk_worker_id": current_user.mturk_worker_id,
        "age": current_user.age,
        "gender": current_user.gender,
        "nationality": current_user.nationality,
        "major": current_user.major,
        "message": "MTurk Worker ID and demographics updated successfully"
    }


@router.post("/api/auth/mturk-register")
async def mturk_register(
    request: MTurkRegisterRequest,
    http_request: Request,
    db: AsyncSession = Depends(get_async_session)
):
    """
    Auto-register or login an MTurk worker.
    Called by frontend when MTurk URL parameters are detected.
    """
    import re
    
    # Rate limiting check
    client_ip = http_request.client.host
    if not mturk_rate_limiter.is_allowed(client_ip):
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many registration attempts. Please wait a minute and try again."
        )
    
    # Check for preview mode
    if request.assignment_id == "ASSIGNMENT_ID_NOT_AVAILABLE":
        return {
            "success": True,
            "preview_mode": True,
            "message": "Preview mode - accept HIT to participate"
        }
    
    # Validate worker_id format (MTurk worker IDs: A followed by 13 alphanumeric chars)
    worker_id_pattern = re.compile(MTURK_WORKER_ID_PATTERN)
    if not worker_id_pattern.match(request.worker_id):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid MTurk worker ID format. Expected format: A followed by 13 alphanumeric characters."
        )
    
    # Validate assignment_id format (MTurk assignment IDs typically start with '3' and are ~30 chars)
    assignment_id_pattern = re.compile(r'^3[A-Z0-9]{20,40}$')
    if not assignment_id_pattern.match(request.assignment_id):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid MTurk assignment ID format."
        )
    
    # Check if this assignment_id already exists in sessions (prevent duplicate registrations)
    existing_session = await db.execute(
        select(DBSession).where(DBSession.mturk_assignment_id == request.assignment_id)
    )
    if existing_session.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"This assignment has already been registered. Each assignment can only be used once."
        )
    
    # Register or login worker
    user, access_token = await register_or_login_mturk_worker(db, request.worker_id)
    
    # Store MTurk IDs in session context (will be saved with game session)
    return {
        "success": True,
        "access_token": access_token,
        "token_type": "bearer",
        "user_id": user.user_id,
        "role": user.role.value,
        "mturk_context": {
            "worker_id": request.worker_id,
            "assignment_id": request.assignment_id,
            "hit_id": request.hit_id
        }
    }


