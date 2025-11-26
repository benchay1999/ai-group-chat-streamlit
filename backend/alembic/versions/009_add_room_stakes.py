"""Add room stakes table for multi-human game gem economy

Revision ID: 009
Revises: 008
Create Date: 2025-11-26

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql, sqlite

# revision identifiers, used by Alembic.
revision = '009'
down_revision = '008'
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Create room_stakes table for tracking gem stakes in multi-human games."""
    
    # Handle UUID differently for PostgreSQL vs SQLite
    bind = op.get_bind()
    is_sqlite = bind.dialect.name == 'sqlite'
    
    if is_sqlite:
        uuid_type = sa.String(36)
    else:
        uuid_type = postgresql.UUID()
    
    op.create_table('room_stakes',
        sa.Column('id', uuid_type, primary_key=True),
        sa.Column('room_code', sa.String(50), nullable=False),
        sa.Column('user_id', uuid_type, nullable=False),
        sa.Column('player_id', sa.String(50), nullable=False),
        sa.Column('stake_percentage', sa.Integer, nullable=False),
        sa.Column('stake_amount', sa.Integer, nullable=False),
        sa.Column('deducted', sa.Integer, nullable=False, server_default='0'),
        sa.Column('returned_amount', sa.Integer, nullable=False, server_default='0'),
        sa.Column('won_amount', sa.Integer, nullable=False, server_default='0'),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    
    # Create indexes for room_stakes
    op.create_index('ix_room_stakes_room_code', 'room_stakes', ['room_code'])
    op.create_index('ix_room_stakes_user_id', 'room_stakes', ['user_id'])
    op.create_index('idx_room_user', 'room_stakes', ['room_code', 'user_id'])
    op.create_index('idx_user_stakes', 'room_stakes', ['user_id', 'created_at'])


def downgrade() -> None:
    """Remove room_stakes table."""
    
    # Drop indexes
    op.drop_index('idx_user_stakes', 'room_stakes')
    op.drop_index('idx_room_user', 'room_stakes')
    op.drop_index('ix_room_stakes_user_id', 'room_stakes')
    op.drop_index('ix_room_stakes_room_code', 'room_stakes')
    
    # Drop table
    op.drop_table('room_stakes')

