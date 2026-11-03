"""remove recently introduced username identity

Revision ID: 20261102_0003
Revises: 20261102_0002
"""
from alembic import op
import sqlalchemy as sa

revision="20261102_0003"
down_revision="20261102_0002"
branch_labels=None
depends_on=None

def upgrade():
    op.drop_index("ix_users_username",table_name="users")
    op.drop_column("users","username")

def downgrade():
    op.add_column("users",sa.Column("username",sa.String(50),nullable=True))
    op.create_index("ix_users_username","users",["username"],unique=True)
