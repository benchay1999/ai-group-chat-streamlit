"""Add calculated_earnings column to sessions

Revision ID: 004_add_calculated_earnings
Revises: 000_initial_schema
Create Date: 2025-01-29 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID

# revision identifiers, used by Alembic.
revision = '004_add_calculated_earnings'
down_revision = '000_initial_schema'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add calculated_earnings column to sessions table
    op.add_column('sessions', 
        sa.Column('calculated_earnings', sa.DECIMAL(10, 2), nullable=True)
    )


def downgrade() -> None:
    # Remove calculated_earnings column from sessions table
    op.drop_column('sessions', 'calculated_earnings')

