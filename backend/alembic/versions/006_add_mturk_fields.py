"""Add MTurk integration fields to sessions table

Revision ID: 006
Revises: 004
Create Date: 2025-10-30

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '006'
down_revision = '004'
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Add MTurk-related fields to sessions table."""
    # Add MTurk worker ID
    op.add_column('sessions', 
        sa.Column('mturk_worker_id', sa.String(255), nullable=True)
    )
    op.create_index('ix_sessions_mturk_worker_id', 'sessions', ['mturk_worker_id'])
    
    # Add MTurk assignment ID (unique constraint)
    op.add_column('sessions',
        sa.Column('mturk_assignment_id', sa.String(255), nullable=True)
    )
    op.create_index('ix_sessions_mturk_assignment_id', 'sessions', ['mturk_assignment_id'], unique=True)
    
    # Add MTurk HIT ID
    op.add_column('sessions',
        sa.Column('mturk_hit_id', sa.String(255), nullable=True)
    )
    op.create_index('ix_sessions_mturk_hit_id', 'sessions', ['mturk_hit_id'])
    
    # Add payment tracking flags (using Integer for SQLite compatibility)
    op.add_column('sessions',
        sa.Column('mturk_payment_sent', sa.Integer, nullable=False, server_default='0')
    )
    
    op.add_column('sessions',
        sa.Column('mturk_bonus_sent', sa.Integer, nullable=False, server_default='0')
    )


def downgrade() -> None:
    """Remove MTurk-related fields from sessions table."""
    # Drop columns (indexes are dropped automatically with columns)
    op.drop_column('sessions', 'mturk_bonus_sent')
    op.drop_column('sessions', 'mturk_payment_sent')
    op.drop_index('ix_sessions_mturk_hit_id', 'sessions')
    op.drop_column('sessions', 'mturk_hit_id')
    op.drop_index('ix_sessions_mturk_assignment_id', 'sessions')
    op.drop_column('sessions', 'mturk_assignment_id')
    op.drop_index('ix_sessions_mturk_worker_id', 'sessions')
    op.drop_column('sessions', 'mturk_worker_id')

