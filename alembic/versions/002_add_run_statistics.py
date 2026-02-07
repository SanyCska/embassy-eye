"""Add run_statistics table for tracking all scraper runs

Revision ID: 002
Revises: 001
Create Date: 2026-02-07 14:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '002'
down_revision: Union[str, None] = '001'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create run_statistics table
    op.create_table(
        'run_statistics',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('embassy', sa.String(length=100), nullable=False),
        sa.Column('location', sa.String(length=100), nullable=True),
        sa.Column('service', sa.String(length=200), nullable=True),
        sa.Column('run_at', sa.DateTime(), nullable=False),
        sa.Column('outcome', sa.String(length=50), nullable=False),
        sa.Column('ip_address', sa.String(length=45), nullable=True),
        sa.Column('country', sa.String(length=100), nullable=True),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_run_statistics_embassy'), 'run_statistics', ['embassy'], unique=False)
    op.create_index(op.f('ix_run_statistics_location'), 'run_statistics', ['location'], unique=False)
    op.create_index(op.f('ix_run_statistics_run_at'), 'run_statistics', ['run_at'], unique=False)
    op.create_index(op.f('ix_run_statistics_outcome'), 'run_statistics', ['outcome'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_run_statistics_outcome'), table_name='run_statistics')
    op.drop_index(op.f('ix_run_statistics_run_at'), table_name='run_statistics')
    op.drop_index(op.f('ix_run_statistics_location'), table_name='run_statistics')
    op.drop_index(op.f('ix_run_statistics_embassy'), table_name='run_statistics')
    op.drop_table('run_statistics')
