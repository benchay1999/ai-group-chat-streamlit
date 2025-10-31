"""Add gem economy system

Revision ID: 007
Revises: 006
Create Date: 2025-10-31

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql, sqlite

# revision identifiers, used by Alembic.
revision = '007'
down_revision = '006'
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Add gem economy fields to users table and create cashout_transactions table."""
    
    # Add gem economy fields to users table
    op.add_column('users',
        sa.Column('gem_balance', sa.Integer, nullable=False, server_default='0')
    )
    
    op.add_column('users',
        sa.Column('total_gems_earned', sa.Integer, nullable=False, server_default='0')
    )
    
    op.add_column('users',
        sa.Column('total_gems_cashed_out', sa.Integer, nullable=False, server_default='0')
    )
    
    op.add_column('users',
        sa.Column('mturk_worker_id', sa.String(255), nullable=True)
    )
    op.create_index('ix_users_mturk_worker_id', 'users', ['mturk_worker_id'])
    
    # Create cashout_transactions table
    # Handle UUID differently for PostgreSQL vs SQLite
    bind = op.get_bind()
    is_sqlite = bind.dialect.name == 'sqlite'
    
    if is_sqlite:
        uuid_type = sa.String(36)
    else:
        uuid_type = postgresql.UUID()
    
    op.create_table('cashout_transactions',
        sa.Column('id', uuid_type, primary_key=True),
        sa.Column('user_id', uuid_type, nullable=False),
        sa.Column('amount_gems', sa.Integer, nullable=False),
        sa.Column('amount_usd', sa.DECIMAL(precision=10, scale=2), nullable=False),
        sa.Column('status', sa.String(20), nullable=False, server_default='pending'),
        sa.Column('redemption_code', sa.String(64), nullable=False),
        sa.Column('mturk_worker_id', sa.String(255), nullable=True),
        sa.Column('mturk_assignment_id', sa.String(255), nullable=True),
        sa.Column('mturk_hit_id', sa.String(255), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('completed_at', sa.DateTime(), nullable=True),
        sa.Column('expires_at', sa.DateTime(), nullable=True),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('redemption_code')
    )
    
    # Create indexes for cashout_transactions
    op.create_index('ix_cashout_transactions_user_id', 'cashout_transactions', ['user_id'])
    op.create_index('ix_cashout_transactions_status', 'cashout_transactions', ['status'])
    op.create_index('ix_cashout_transactions_redemption_code', 'cashout_transactions', ['redemption_code'], unique=True)
    op.create_index('ix_cashout_transactions_mturk_worker_id', 'cashout_transactions', ['mturk_worker_id'])
    op.create_index('ix_cashout_transactions_mturk_assignment_id', 'cashout_transactions', ['mturk_assignment_id'])
    op.create_index('ix_cashout_transactions_mturk_hit_id', 'cashout_transactions', ['mturk_hit_id'])
    op.create_index('idx_user_status', 'cashout_transactions', ['user_id', 'status'])
    op.create_index('idx_status_created', 'cashout_transactions', ['status', 'created_at'])


def downgrade() -> None:
    """Remove gem economy fields and cashout_transactions table."""
    
    # Drop cashout_transactions table and its indexes
    op.drop_index('idx_status_created', 'cashout_transactions')
    op.drop_index('idx_user_status', 'cashout_transactions')
    op.drop_index('ix_cashout_transactions_mturk_hit_id', 'cashout_transactions')
    op.drop_index('ix_cashout_transactions_mturk_assignment_id', 'cashout_transactions')
    op.drop_index('ix_cashout_transactions_mturk_worker_id', 'cashout_transactions')
    op.drop_index('ix_cashout_transactions_redemption_code', 'cashout_transactions')
    op.drop_index('ix_cashout_transactions_status', 'cashout_transactions')
    op.drop_index('ix_cashout_transactions_user_id', 'cashout_transactions')
    op.drop_table('cashout_transactions')
    
    # Remove gem economy fields from users table
    op.drop_index('ix_users_mturk_worker_id', 'users')
    op.drop_column('users', 'mturk_worker_id')
    op.drop_column('users', 'total_gems_cashed_out')
    op.drop_column('users', 'total_gems_earned')
    op.drop_column('users', 'gem_balance')

