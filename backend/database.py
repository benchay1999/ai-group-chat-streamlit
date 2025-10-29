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
DATABASE_URL = os.getenv(
    'DATABASE_URL',
    'sqlite+aiosqlite:///./group_chat.db'
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
    stats_file_path = Column(String(500), nullable=False)
    claimed_at = Column(DateTime, nullable=True)
    
    # Relationship to user
    user = relationship("User", back_populates="sessions")
    
    # Indexes for common queries
    __table_args__ = (
        Index('idx_user_completed', 'user_id', 'completed_at'),
        Index('idx_payment_status', 'payment_status'),
    )
    
    def __repr__(self):
        return f"<Session(id={self.id}, room_code={self.room_code}, user_id={self.user_id})>"


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
    Initialize database tables.
    Should be called on application startup.
    """
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    print("✅ Database tables created successfully")


async def close_db():
    """
    Close database connections.
    Should be called on application shutdown.
    """
    await engine.dispose()
    print("✅ Database connections closed")

