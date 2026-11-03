"""Controlled one-time promotion for an existing verified account.

Run only from a trusted backend shell with production database access:
python -m app.provision_super_admin --email owner@example.com --confirm
"""
import argparse
from sqlalchemy import select
from .database import SessionLocal
from .models import ApprovalStatus, User, UserRole

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("--email",required=True)
    parser.add_argument("--confirm",action="store_true",help="confirm this privileged database change")
    args=parser.parse_args()
    if not args.confirm: raise SystemExit("Refusing promotion without --confirm")
    with SessionLocal() as db:
        user=db.scalar(select(User).where(User.email==args.email.lower()))
        if not user: raise SystemExit("Account not found; register the trusted account first")
        if not user.is_active: raise SystemExit("Account is inactive")
        user.role=UserRole.SUPER_ADMIN; user.approval_status=ApprovalStatus.ACTIVE
        db.commit()
        print(f"Provisioned SUPER_ADMIN for user_id={user.user_id}")
if __name__=="__main__": main()
