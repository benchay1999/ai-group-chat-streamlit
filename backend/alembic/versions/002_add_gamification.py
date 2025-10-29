"""add gamification fields

Revision ID: 002
Revises: 001
Create Date: 2025-10-29 00:01:00.000000

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '002'
down_revision = '001'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add gamification fields to users table
    with op.batch_alter_table('users', schema=None) as batch_op:
        batch_op.add_column(sa.Column('total_games', sa.Integer(), nullable=False, server_default='0'))
        batch_op.add_column(sa.Column('total_wins', sa.Integer(), nullable=False, server_default='0'))
        batch_op.add_column(sa.Column('total_points', sa.Integer(), nullable=False, server_default='0'))
        batch_op.add_column(sa.Column('current_streak', sa.Integer(), nullable=False, server_default='0'))
        batch_op.add_column(sa.Column('longest_streak', sa.Integer(), nullable=False, server_default='0'))
        batch_op.add_column(sa.Column('last_played_at', sa.DateTime(), nullable=True))
        batch_op.add_column(sa.Column('level', sa.Integer(), nullable=False, server_default='1'))


def downgrade() -> None:
    # Remove gamification fields from users table
    with op.batch_alter_table('users', schema=None) as batch_op:
        batch_op.drop_column('level')
        batch_op.drop_column('last_played_at')
        batch_op.drop_column('longest_streak')
        batch_op.drop_column('current_streak')
        batch_op.drop_column('total_points')
        batch_op.drop_column('total_wins')
        batch_op.drop_column('total_games')

