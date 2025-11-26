"""Add gems_earned to session_players

Revision ID: 010
Revises: 009
Create Date: 2025-11-26

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '010'
down_revision = '009'
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Add gems_earned column to session_players table."""
    
    # Add gems_earned field to session_players table
    # Nullable to support old records that don't have this data
    op.add_column('session_players',
        sa.Column('gems_earned', sa.Integer, nullable=True)
    )


def downgrade() -> None:
    """Remove gems_earned column from session_players table."""
    
    # Remove gems_earned field
    op.drop_column('session_players', 'gems_earned')

