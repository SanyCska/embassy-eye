"""Initial tables for slot statistics and blocked VPNs

Revision ID: 001
Revises: 
Create Date: 2026-02-07 12:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '001'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create slot_statistics table
    op.create_table(
        'slot_statistics',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('embassy', sa.String(length=100), nullable=False),
        sa.Column('location', sa.String(length=100), nullable=True),
        sa.Column('service', sa.String(length=200), nullable=True),
        sa.Column('detected_at', sa.DateTime(), nullable=False),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_slot_statistics_embassy'), 'slot_statistics', ['embassy'], unique=False)
    op.create_index(op.f('ix_slot_statistics_location'), 'slot_statistics', ['location'], unique=False)
    op.create_index(op.f('ix_slot_statistics_detected_at'), 'slot_statistics', ['detected_at'], unique=False)
    
    # Create blocked_vpns table
    op.create_table(
        'blocked_vpns',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('ip_address', sa.String(length=45), nullable=False),
        sa.Column('country', sa.String(length=100), nullable=True),
        sa.Column('blocked_at', sa.DateTime(), nullable=False),
        sa.Column('embassy', sa.String(length=100), nullable=True),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_blocked_vpns_ip_address'), 'blocked_vpns', ['ip_address'], unique=False)
    op.create_index(op.f('ix_blocked_vpns_country'), 'blocked_vpns', ['country'], unique=False)
    op.create_index(op.f('ix_blocked_vpns_blocked_at'), 'blocked_vpns', ['blocked_at'], unique=False)
    op.create_index(op.f('ix_blocked_vpns_embassy'), 'blocked_vpns', ['embassy'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_blocked_vpns_embassy'), table_name='blocked_vpns')
    op.drop_index(op.f('ix_blocked_vpns_blocked_at'), table_name='blocked_vpns')
    op.drop_index(op.f('ix_blocked_vpns_country'), table_name='blocked_vpns')
    op.drop_index(op.f('ix_blocked_vpns_ip_address'), table_name='blocked_vpns')
    op.drop_table('blocked_vpns')
    
    op.drop_index(op.f('ix_slot_statistics_detected_at'), table_name='slot_statistics')
    op.drop_index(op.f('ix_slot_statistics_location'), table_name='slot_statistics')
    op.drop_index(op.f('ix_slot_statistics_embassy'), table_name='slot_statistics')
    op.drop_table('slot_statistics')
