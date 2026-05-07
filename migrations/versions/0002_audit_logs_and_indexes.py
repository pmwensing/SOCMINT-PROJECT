"""audit logs and rate-limit indexes

Revision ID: 0002_audit_logs_and_indexes
Revises: 0001_initial_schema
Create Date: 2026-05-06
"""
from alembic import op
import sqlalchemy as sa

revision = '0002_audit_logs_and_indexes'
down_revision = '0001_initial_schema'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        'audit_logs',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('actor', sa.String(), nullable=True),
        sa.Column('action', sa.String(), nullable=False),
        sa.Column('target_id', sa.Integer(), sa.ForeignKey('targets.id'), nullable=True),
        sa.Column('target_value', sa.String(), nullable=True),
        sa.Column('ip_address', sa.String(), nullable=True),
        sa.Column('details', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index(
        'ix_rate_limit_action_key_created_at',
        'rate_limit_attempts',
        ['action', 'key', 'created_at'],
    )
    op.create_index('ix_audit_logs_created_at', 'audit_logs', ['created_at'])
    op.create_index('ix_audit_logs_actor_action', 'audit_logs', ['actor', 'action'])


def downgrade():
    op.drop_index('ix_audit_logs_actor_action', table_name='audit_logs')
    op.drop_index('ix_audit_logs_created_at', table_name='audit_logs')
    op.drop_index('ix_rate_limit_action_key_created_at', table_name='rate_limit_attempts')
    op.drop_table('audit_logs')
