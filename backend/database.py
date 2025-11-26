"""
Database models and connection setup for PostgreSQL.
Uses SQLAlchemy with async support for FastAPI integration.
"""

from sqlalchemy import Column, String, Integer, DateTime, Enum, DECIMAL, ForeignKey, Text, Index
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import declarative_base, relationship
from sqlalchemy.dialects.postgresql import UUID
from datetime import datetime
import uuid
import os
from dotenv import load_dotenv
import enum

load_dotenv()

# Database URL from environment
# Default to SQLite for development (no sudo/installation required)
# For production, use PostgreSQL: postgresql+asyncpg://user:pass@host:port/db

# Get the directory where this file is located (backend/)
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, 'group_chat.db')

DATABASE_URL = os.getenv(
    'DATABASE_URL',
    f'sqlite+aiosqlite:///{DB_PATH}'
)

# Determine if we're using SQLite or PostgreSQL
is_sqlite = 'sqlite' in DATABASE_URL.lower()
is_production = os.getenv('ENVIRONMENT', 'development') == 'production'

# Warn if using SQLite in production
if is_sqlite and is_production:
    print("⚠️  WARNING: Using SQLite in production!")
    print("   SQLite has poor concurrency handling for 100+ users")
    print("   Recommended: Migrate to PostgreSQL for production")
    print("   See: SQLITE_TO_POSTGRESQL.md")

# Create async engine with appropriate settings
if is_sqlite:
    # SQLite configuration (development only)
    engine = create_async_engine(
        DATABASE_URL,
        echo=False if is_production else True,
        future=True
    )
else:
    # PostgreSQL configuration with connection pooling
    engine = create_async_engine(
        DATABASE_URL,
        echo=False if is_production else True,
        future=True,
        pool_size=20,  # Number of connections to maintain
        max_overflow=40,  # Additional connections when pool is full
        pool_pre_ping=True,  # Verify connections before using
        pool_recycle=3600,  # Recycle connections after 1 hour
    )

# Create async session factory
async_session_maker = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False
)

# Base class for models
Base = declarative_base()


# Enums
class UserRole(str, enum.Enum):
    USER = "user"
    ADMIN = "admin"


class PaymentStatus(str, enum.Enum):
    PENDING = "pending"
    PAID = "paid"


class CashoutStatus(str, enum.Enum):
    PENDING = "pending"  # Transaction created, not yet processed
    HIT_CREATED = "hit_created"  # HIT created on MTurk, waiting for worker
    COMPLETED = "completed"  # Worker completed HIT, payment sent
    FAILED = "failed"  # HIT expired or other error
    CANCELLED = "cancelled"  # User cancelled before HIT creation


# Models
class User(Base):
    """User model for authentication."""
    __tablename__ = "users"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(String(255), unique=True, nullable=False, index=True)
    password_hash = Column(String(255), nullable=False)
    role = Column(Enum(UserRole), default=UserRole.USER, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    
    # Gamification fields
    total_games = Column(Integer, default=0, nullable=False)
    total_wins = Column(Integer, default=0, nullable=False)  # Games where user correctly identified AI
    total_points = Column(Integer, default=0, nullable=False)
    current_streak = Column(Integer, default=0, nullable=False)  # Consecutive days played
    longest_streak = Column(Integer, default=0, nullable=False)
    last_played_at = Column(DateTime, nullable=True)
    level = Column(Integer, default=1, nullable=False)
    
    # Gem economy fields (1000 gems = $1.00 USD)
    gem_balance = Column(Integer, default=0, nullable=False)  # Current gem balance
    total_gems_earned = Column(Integer, default=0, nullable=False)  # Lifetime gems earned
    total_gems_cashed_out = Column(Integer, default=0, nullable=False)  # Lifetime gems cashed out
    mturk_worker_id = Column(String(255), nullable=True, index=True)  # MTurk Worker ID for cashouts
    
    # MTurk worker demographics (required when setting worker ID)
    age = Column(Integer, nullable=True)  # Worker age
    gender = Column(String(50), nullable=True)  # Worker gender: male, female, wish_not_to_answer
    nationality = Column(String(255), nullable=True)  # Worker nationality
    major = Column(String(255), nullable=True)  # Worker major/field of study
    
    # Relationships
    sessions = relationship("Session", back_populates="user", cascade="all, delete-orphan")
    cashout_transactions = relationship("CashoutTransaction", back_populates="user", cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"<User(id={self.id}, user_id={self.user_id}, role={self.role})>"


class Session(Base):
    """Session model for tracking game sessions."""
    __tablename__ = "sessions"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    room_code = Column(String(50), nullable=False, index=True)
    completion_key = Column(Text, unique=True, nullable=False, index=True)
    user_id = Column(UUID(as_uuid=True), ForeignKey('users.id', ondelete='CASCADE'), nullable=True, index=True)
    language = Column(String(50), nullable=False)
    total_players = Column(Integer, nullable=False)
    num_human_players = Column(Integer, nullable=False)
    discussion_duration = Column(Integer, nullable=False)  # in seconds
    voting_duration = Column(Integer, nullable=False)  # in seconds
    completed_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    payment_status = Column(Enum(PaymentStatus), default=PaymentStatus.PENDING, nullable=False)
    payment_amount = Column(DECIMAL(10, 2), nullable=True)
    calculated_earnings = Column(DECIMAL(10, 2), nullable=True)  # Performance-based earnings suggestion
    stats_file_path = Column(String(500), nullable=False)
    claimed_at = Column(DateTime, nullable=True)
    
    # MTurk integration fields
    mturk_worker_id = Column(String(255), nullable=True, index=True)  # MTurk worker ID
    mturk_assignment_id = Column(String(255), nullable=True, unique=True, index=True)  # MTurk assignment ID
    mturk_hit_id = Column(String(255), nullable=True, index=True)  # MTurk HIT ID
    mturk_payment_sent = Column(Integer, default=0, nullable=False)  # Boolean: 0=False, 1=True (SQLite compatible)
    mturk_bonus_sent = Column(Integer, default=0, nullable=False)  # Boolean: 0=False, 1=True (SQLite compatible)
    
    # Token usage tracking
    total_input_tokens = Column(Integer, default=0, nullable=False)
    total_output_tokens = Column(Integer, default=0, nullable=False)
    total_cost = Column(DECIMAL(10, 6), default=0, nullable=False)  # Cost in USD
    model_name = Column(String(100), nullable=True)
    
    # Relationships
    user = relationship("User", back_populates="sessions")
    agent_usage = relationship("AIAgentUsage", back_populates="session", cascade="all, delete-orphan")
    
    # Indexes for common queries
    __table_args__ = (
        Index('idx_user_completed', 'user_id', 'completed_at'),
        Index('idx_payment_status', 'payment_status'),
    )
    
    def __repr__(self):
        return f"<Session(id={self.id}, room_code={self.room_code}, user_id={self.user_id})>"


class AIAgentUsage(Base):
    """AI Agent token usage tracking per session."""
    __tablename__ = "ai_agent_usage"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    session_id = Column(UUID(as_uuid=True), ForeignKey('sessions.id', ondelete='CASCADE'), nullable=False, index=True)
    agent_id = Column(String(50), nullable=False)  # e.g., "Player 3", "AI_1"
    input_tokens = Column(Integer, default=0, nullable=False)
    output_tokens = Column(Integer, default=0, nullable=False)
    cost = Column(DECIMAL(10, 6), default=0, nullable=False)  # Cost in USD
    message_count = Column(Integer, default=0, nullable=False)  # Number of LLM calls
    
    # Relationship
    session = relationship("Session", back_populates="agent_usage")
    
    # Index for queries
    __table_args__ = (
        Index('idx_session_agent', 'session_id', 'agent_id'),
    )
    
    def __repr__(self):
        return f"<AIAgentUsage(session_id={self.session_id}, agent_id={self.agent_id}, tokens={self.input_tokens}+{self.output_tokens})>"


class SessionPlayer(Base):
    """Mapping of users to their player IDs in a session."""
    __tablename__ = "session_players"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    session_id = Column(UUID(as_uuid=True), ForeignKey('sessions.id', ondelete='CASCADE'), nullable=False, index=True)
    user_id = Column(UUID(as_uuid=True), ForeignKey('users.id', ondelete='CASCADE'), nullable=True, index=True)
    player_id = Column(String(50), nullable=False)  # e.g., "Player 3", "You"
    role = Column(String(20), nullable=False)  # "human" or "ai"
    
    # Relationships
    session = relationship("Session", backref="players_map")
    user = relationship("User", backref="session_participations")
    
    # Index for queries
    __table_args__ = (
        Index('idx_session_player', 'session_id', 'player_id'),
        Index('idx_user_sessions', 'user_id', 'session_id'),
    )
    
    def __repr__(self):
        return f"<SessionPlayer(session_id={self.session_id}, player_id={self.player_id}, user_id={self.user_id})>"


class CashoutTransaction(Base):
    """Cashout transaction for gem-to-USD conversions via MTurk."""
    __tablename__ = "cashout_transactions"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey('users.id', ondelete='CASCADE'), nullable=False, index=True)
    amount_gems = Column(Integer, nullable=False)  # Gems being cashed out
    amount_usd = Column(DECIMAL(10, 2), nullable=False)  # Equivalent USD amount
    status = Column(Enum(CashoutStatus), default=CashoutStatus.PENDING, nullable=False, index=True)
    
    # Redemption code system (simpler than worker-specific HITs)
    redemption_code = Column(String(64), unique=True, nullable=False, index=True)  # Unique hash for user to submit
    
    # MTurk assignment details (populated when user submits code)
    mturk_worker_id = Column(String(255), nullable=True, index=True)
    mturk_assignment_id = Column(String(255), nullable=True, index=True)
    mturk_hit_id = Column(String(255), nullable=True, index=True)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    completed_at = Column(DateTime, nullable=True)
    expires_at = Column(DateTime, nullable=True)  # Code expiration time (e.g., 7 days)
    
    # Error tracking
    error_message = Column(Text, nullable=True)
    
    # Relationship
    user = relationship("User", back_populates="cashout_transactions")
    
    # Indexes for common queries
    __table_args__ = (
        Index('idx_user_status', 'user_id', 'status'),
        Index('idx_status_created', 'status', 'created_at'),
        Index('idx_redemption_code', 'redemption_code'),
    )
    
    def __repr__(self):
        return f"<CashoutTransaction(id={self.id}, user_id={self.user_id}, amount_usd={self.amount_usd}, status={self.status}, code={self.redemption_code[:8]}...)>"




class RoomStake(Base):
    """Track stakes and gem transactions per room for multi-human games."""
    __tablename__ = "room_stakes"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    room_code = Column(String(50), nullable=False, index=True)
    user_id = Column(UUID(as_uuid=True), ForeignKey('users.id', ondelete='CASCADE'), nullable=False, index=True)
    player_id = Column(String(50), nullable=False)  # e.g., "Player 3", "You"
    stake_percentage = Column(Integer, nullable=False)  # 0, 10, 30, 50, 100
    stake_amount = Column(Integer, nullable=False)  # Actual gems at risk
    deducted = Column(Integer, default=0, nullable=False)  # Boolean: 0=False, 1=True (SQLite compatible)
    returned_amount = Column(Integer, default=0, nullable=False)  # Gems returned (if any)
    won_amount = Column(Integer, default=0, nullable=False)  # Gems won (if any)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    
    # Relationship
    user = relationship("User", backref="room_stakes")
    
    # Indexes for common queries
    __table_args__ = (
        Index('idx_room_user', 'room_code', 'user_id'),
        Index('idx_user_stakes', 'user_id', 'created_at'),
    )
    
    def __repr__(self):
        return f"<RoomStake(room_code={self.room_code}, user_id={self.user_id}, stake_amount={self.stake_amount})>"


class TokenBlacklist(Base):
    """Token blacklist for logout functionality."""
    __tablename__ = "token_blacklist"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    token = Column(Text, unique=True, nullable=False, index=True)  # SHA256 hash of the token
    user_id = Column(UUID(as_uuid=True), ForeignKey('users.id', ondelete='CASCADE'), nullable=True, index=True)
    blacklisted_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    expires_at = Column(DateTime, nullable=False, index=True)  # When the token would have expired
    reason = Column(String(50), default='logout', nullable=False)  # 'logout', 'security', 'admin'
    
    # Relationship
    user = relationship("User", foreign_keys=[user_id])
    
    # Index for cleanup queries
    __table_args__ = (
        Index('idx_expires_blacklisted', 'expires_at', 'blacklisted_at'),
    )
    
    def __repr__(self):
        return f"<TokenBlacklist(id={self.id}, user_id={self.user_id}, reason={self.reason})>"


# Database helper functions
async def get_async_session():
    """
    Dependency for FastAPI to get async database session.
    Use with Depends() in route handlers.
    """
    async with async_session_maker() as session:
        try:
            yield session
        finally:
            await session.close()


async def init_db():
    """
    Initialize database connection.
    Note: Database tables should be created via Alembic migrations:
      cd backend && python -m alembic upgrade head
    
    This function only verifies the database connection.
    """
    try:
        async with engine.begin() as conn:
            # Just verify connection, don't create tables
            # Tables are managed by Alembic migrations
            pass
        print("✅ Database connection established")
    except Exception as e:
        print(f"⚠️  Database connection failed: {e}")
        print("💡 Run migrations first: python -m alembic upgrade head")


async def close_db():
    """
    Close database connections.
    Should be called on application shutdown.
    """
    await engine.dispose()
    print("✅ Database connections closed")

