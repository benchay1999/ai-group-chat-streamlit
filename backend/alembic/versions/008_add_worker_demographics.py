"""Add worker demographics

Revision ID: 008
Revises: 007
Create Date: 2025-11-25

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '008'
down_revision = '007'
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Add demographic fields to users table for MTurk workers."""
    
    # Add demographic fields to users table
    op.add_column('users',
        sa.Column('age', sa.Integer, nullable=True)
    )
    
    op.add_column('users',
        sa.Column('gender', sa.String(50), nullable=True)
    )
    
    op.add_column('users',
        sa.Column('nationality', sa.String(255), nullable=True)
    )
    
    op.add_column('users',
        sa.Column('major', sa.String(255), nullable=True)
    )


def downgrade() -> None:
    """Remove demographic fields from users table."""
    
    # Remove demographic fields from users table
    op.drop_column('users', 'major')
    op.drop_column('users', 'nationality')
    op.drop_column('users', 'gender')
    op.drop_column('users', 'age')

