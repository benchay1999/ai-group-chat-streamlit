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

# Create async engine
engine = create_async_engine(
    DATABASE_URL,
    echo=True,  # Set to False in production
    future=True
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
    
    # Relationship to sessions
    sessions = relationship("Session", back_populates="user", cascade="all, delete-orphan")
    
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

