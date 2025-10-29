"""add session players mapping

Revision ID: 003
Revises: 002
Create Date: 2025-10-29 00:02:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import sqlite
import uuid

# revision identifiers, used by Alembic.
revision = '003'
down_revision = '002'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create session_players table
    op.create_table('session_players',
        sa.Column('id', sa.UUID() if not isinstance(op.get_bind().dialect, sqlite.dialect) else sa.String(36), primary_key=True, default=uuid.uuid4),
        sa.Column('session_id', sa.UUID() if not isinstance(op.get_bind().dialect, sqlite.dialect) else sa.String(36), nullable=False),
        sa.Column('user_id', sa.UUID() if not isinstance(op.get_bind().dialect, sqlite.dialect) else sa.String(36), nullable=True),
        sa.Column('player_id', sa.String(length=50), nullable=False),
        sa.Column('role', sa.String(length=20), nullable=False),
        sa.ForeignKeyConstraint(['session_id'], ['sessions.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    
    # Create indexes
    with op.batch_alter_table('session_players', schema=None) as batch_op:
        batch_op.create_index('idx_session_player', ['session_id', 'player_id'], unique=False)
        batch_op.create_index('idx_user_sessions', ['user_id', 'session_id'], unique=False)
        batch_op.create_index(batch_op.f('ix_session_players_session_id'), ['session_id'], unique=False)
        batch_op.create_index(batch_op.f('ix_session_players_user_id'), ['user_id'], unique=False)


def downgrade() -> None:
    # Drop session_players table
    op.drop_table('session_players')

