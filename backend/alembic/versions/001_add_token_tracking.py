"""add token tracking

Revision ID: 001
Revises: 
Create Date: 2025-10-29 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import sqlite
import uuid

# revision identifiers, used by Alembic.
revision = '001'
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add token tracking columns to sessions table
    with op.batch_alter_table('sessions', schema=None) as batch_op:
        batch_op.add_column(sa.Column('total_input_tokens', sa.Integer(), nullable=False, server_default='0'))
        batch_op.add_column(sa.Column('total_output_tokens', sa.Integer(), nullable=False, server_default='0'))
        batch_op.add_column(sa.Column('total_cost', sa.DECIMAL(precision=10, scale=6), nullable=False, server_default='0'))
        batch_op.add_column(sa.Column('model_name', sa.String(length=100), nullable=True))

    # Create ai_agent_usage table
    op.create_table('ai_agent_usage',
        sa.Column('id', sa.UUID() if not isinstance(op.get_bind().dialect, sqlite.dialect) else sa.String(36), primary_key=True, default=uuid.uuid4),
        sa.Column('session_id', sa.UUID() if not isinstance(op.get_bind().dialect, sqlite.dialect) else sa.String(36), nullable=False),
        sa.Column('agent_id', sa.String(length=50), nullable=False),
        sa.Column('input_tokens', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('output_tokens', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('cost', sa.DECIMAL(precision=10, scale=6), nullable=False, server_default='0'),
        sa.Column('message_count', sa.Integer(), nullable=False, server_default='0'),
        sa.ForeignKeyConstraint(['session_id'], ['sessions.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    
    # Create indexes
    with op.batch_alter_table('ai_agent_usage', schema=None) as batch_op:
        batch_op.create_index('idx_session_agent', ['session_id', 'agent_id'], unique=False)
        batch_op.create_index(batch_op.f('ix_ai_agent_usage_session_id'), ['session_id'], unique=False)


def downgrade() -> None:
    # Drop ai_agent_usage table
    op.drop_table('ai_agent_usage')
    
    # Remove token tracking columns from sessions table
    with op.batch_alter_table('sessions', schema=None) as batch_op:
        batch_op.drop_column('model_name')
        batch_op.drop_column('total_cost')
        batch_op.drop_column('total_output_tokens')
        batch_op.drop_column('total_input_tokens')

