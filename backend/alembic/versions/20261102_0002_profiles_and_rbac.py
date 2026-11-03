"""student profiles and three-role approval workflow

Revision ID: 20261102_0002
Revises: 20260823_0001
"""
from alembic import op
import sqlalchemy as sa

revision="20261102_0002"
down_revision="20260823_0001"
branch_labels=None
depends_on=None

def upgrade():
    op.execute("ALTER TABLE users MODIFY role ENUM('LEARNER','ADMIN','SUPER_ADMIN') NOT NULL")
    op.add_column("users",sa.Column("username",sa.String(50),nullable=True))
    op.add_column("users",sa.Column("approval_status",sa.Enum("ACTIVE","PENDING","REJECTED",name="approvalstatus"),server_default="ACTIVE",nullable=False))
    op.add_column("users",sa.Column("gender",sa.Enum("MALE","FEMALE","NON_BINARY","PREFER_NOT_TO_SAY",name="gender"),nullable=True))
    op.add_column("users",sa.Column("date_of_birth",sa.Date(),nullable=True))
    op.create_index("ix_users_username","users",["username"],unique=True)
    op.create_table(
        "admin_approvals",
        sa.Column("approval_id",sa.Integer(),primary_key=True),
        sa.Column("admin_user_id",sa.Integer(),sa.ForeignKey("users.user_id",ondelete="RESTRICT"),nullable=False),
        sa.Column("status",sa.Enum("ACTIVE","PENDING","REJECTED",name="approvalstatus"),nullable=False),
        sa.Column("decided_by",sa.Integer(),sa.ForeignKey("users.user_id",ondelete="RESTRICT"),nullable=False),
        sa.Column("decision_note",sa.String(500),nullable=True),
        sa.Column("decided_at",sa.DateTime(),server_default=sa.func.now(),nullable=False),
    )
    op.create_index("ix_admin_approvals_admin_user_id","admin_approvals",["admin_user_id"])
    op.create_index("ix_admin_approvals_decided_by","admin_approvals",["decided_by"])

def downgrade():
    op.drop_table("admin_approvals")
    op.drop_index("ix_users_username",table_name="users")
    op.drop_column("users","date_of_birth")
    op.drop_column("users","gender")
    op.drop_column("users","approval_status")
    op.drop_column("users","username")
    op.execute("UPDATE users SET role='ADMIN' WHERE role='SUPER_ADMIN'")
    op.execute("ALTER TABLE users MODIFY role ENUM('LEARNER','ADMIN') NOT NULL")
