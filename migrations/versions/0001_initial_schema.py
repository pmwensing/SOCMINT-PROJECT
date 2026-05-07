"""initial schema

Revision ID: 0001_initial_schema
Revises:
Create Date: 2026-05-06
"""
from alembic import op
import sqlalchemy as sa

revision = '0001_initial_schema'
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        'targets',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('type', sa.String()),
        sa.Column('value', sa.String(), unique=True),
        sa.Column('created_at', sa.DateTime(timezone=True)),
    )
    op.create_table(
        'tools',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('name', sa.String(), unique=True),
    )
    op.create_table(
        'users',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('username', sa.String(), unique=True),
        sa.Column('password_hash', sa.String()),
        sa.Column('is_admin', sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column('created_at', sa.DateTime(timezone=True)),
    )
    op.create_table(
        'rate_limit_attempts',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('action', sa.String(), nullable=False),
        sa.Column('key', sa.String(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
    )
    op.create_table(
        'results',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('target_id', sa.Integer(), sa.ForeignKey('targets.id')),
        sa.Column('tool_id', sa.Integer(), sa.ForeignKey('tools.id')),
        sa.Column('data', sa.Text()),
        sa.Column('timestamp', sa.DateTime(timezone=True)),
    )
    op.create_table(
        'profiles',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('target_id', sa.Integer(), sa.ForeignKey('targets.id')),
        sa.Column('source', sa.String()),
        sa.Column('raw', sa.Text()),
        sa.Column('normalized', sa.Text()),
        sa.Column('created_at', sa.DateTime(timezone=True)),
    )
    op.create_table(
        'media',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('target_id', sa.Integer(), sa.ForeignKey('targets.id')),
        sa.Column('profile_id', sa.Integer(), sa.ForeignKey('profiles.id'), nullable=True),
        sa.Column('source_url', sa.String()),
        sa.Column('path', sa.String()),
        sa.Column('checksum', sa.String()),
        sa.Column('content_type', sa.String()),
        sa.Column('created_at', sa.DateTime(timezone=True)),
    )


def downgrade():
    op.drop_table('media')
    op.drop_table('profiles')
    op.drop_table('results')
    op.drop_table('rate_limit_attempts')
    op.drop_table('users')
    op.drop_table('tools')
    op.drop_table('targets')
