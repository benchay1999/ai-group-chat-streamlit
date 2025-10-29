"""initial schema

Revision ID: 000
Revises: 
Create Date: 2025-10-29 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import sqlite
import uuid

# revision identifiers, used by Alembic.
revision = '000'
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create users table with all fields
    op.create_table('users',
        sa.Column('id', sa.String(36) if isinstance(op.get_bind().dialect, sqlite.dialect) else sa.UUID(), primary_key=True),
        sa.Column('user_id', sa.String(length=255), nullable=False),
        sa.Column('password_hash', sa.String(length=255), nullable=False),
        sa.Column('role', sa.String(20), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('total_games', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('total_wins', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('total_points', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('current_streak', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('longest_streak', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('last_played_at', sa.DateTime(), nullable=True),
        sa.Column('level', sa.Integer(), nullable=False, server_default='1'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('user_id')
    )
    op.create_index(op.f('ix_users_user_id'), 'users', ['user_id'], unique=True)
    
    # Create sessions table with all fields
    op.create_table('sessions',
        sa.Column('id', sa.String(36) if isinstance(op.get_bind().dialect, sqlite.dialect) else sa.UUID(), primary_key=True),
        sa.Column('room_code', sa.String(length=50), nullable=False),
        sa.Column('completion_key', sa.Text(), nullable=False),
        sa.Column('user_id', sa.String(36) if isinstance(op.get_bind().dialect, sqlite.dialect) else sa.UUID(), nullable=True),
        sa.Column('language', sa.String(length=50), nullable=False),
        sa.Column('total_players', sa.Integer(), nullable=False),
        sa.Column('num_human_players', sa.Integer(), nullable=False),
        sa.Column('discussion_duration', sa.Integer(), nullable=False),
        sa.Column('voting_duration', sa.Integer(), nullable=False),
        sa.Column('completed_at', sa.DateTime(), nullable=False),
        sa.Column('payment_status', sa.String(20), nullable=False),
        sa.Column('payment_amount', sa.DECIMAL(precision=10, scale=2), nullable=True),
        sa.Column('stats_file_path', sa.String(length=500), nullable=False),
        sa.Column('claimed_at', sa.DateTime(), nullable=True),
        sa.Column('total_input_tokens', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('total_output_tokens', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('total_cost', sa.DECIMAL(precision=10, scale=6), nullable=False, server_default='0'),
        sa.Column('model_name', sa.String(length=100), nullable=True),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('completion_key')
    )
    op.create_index(op.f('ix_sessions_completed_at'), 'sessions', ['completed_at'], unique=False)
    op.create_index(op.f('ix_sessions_completion_key'), 'sessions', ['completion_key'], unique=True)
    op.create_index(op.f('ix_sessions_room_code'), 'sessions', ['room_code'], unique=False)
    op.create_index(op.f('ix_sessions_user_id'), 'sessions', ['user_id'], unique=False)
    op.create_index('idx_user_completed', 'sessions', ['user_id', 'completed_at'], unique=False)
    op.create_index('idx_payment_status', 'sessions', ['payment_status'], unique=False)
    
    # Create ai_agent_usage table
    op.create_table('ai_agent_usage',
        sa.Column('id', sa.String(36) if isinstance(op.get_bind().dialect, sqlite.dialect) else sa.UUID(), primary_key=True),
        sa.Column('session_id', sa.String(36) if isinstance(op.get_bind().dialect, sqlite.dialect) else sa.UUID(), nullable=False),
        sa.Column('agent_id', sa.String(length=50), nullable=False),
        sa.Column('input_tokens', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('output_tokens', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('cost', sa.DECIMAL(precision=10, scale=6), nullable=False, server_default='0'),
        sa.Column('message_count', sa.Integer(), nullable=False, server_default='0'),
        sa.ForeignKeyConstraint(['session_id'], ['sessions.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('idx_session_agent', 'ai_agent_usage', ['session_id', 'agent_id'], unique=False)
    op.create_index(op.f('ix_ai_agent_usage_session_id'), 'ai_agent_usage', ['session_id'], unique=False)
    
    # Create session_players table
    op.create_table('session_players',
        sa.Column('id', sa.String(36) if isinstance(op.get_bind().dialect, sqlite.dialect) else sa.UUID(), primary_key=True),
        sa.Column('session_id', sa.String(36) if isinstance(op.get_bind().dialect, sqlite.dialect) else sa.UUID(), nullable=False),
        sa.Column('user_id', sa.String(36) if isinstance(op.get_bind().dialect, sqlite.dialect) else sa.UUID(), nullable=True),
        sa.Column('player_id', sa.String(length=50), nullable=False),
        sa.Column('role', sa.String(length=20), nullable=False),
        sa.ForeignKeyConstraint(['session_id'], ['sessions.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('idx_session_player', 'session_players', ['session_id', 'player_id'], unique=False)
    op.create_index('idx_user_sessions', 'session_players', ['user_id', 'session_id'], unique=False)
    op.create_index(op.f('ix_session_players_session_id'), 'session_players', ['session_id'], unique=False)
    op.create_index(op.f('ix_session_players_user_id'), 'session_players', ['user_id'], unique=False)


def downgrade() -> None:
    op.drop_table('session_players')
    op.drop_table('ai_agent_usage')
    op.drop_table('sessions')
    op.drop_table('users')

