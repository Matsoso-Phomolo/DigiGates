"""Shared, ownership-safe self-service account operations."""
from uuid import uuid4
from fastapi import HTTPException
from sqlalchemy import func, select
from sqlalchemy.orm import Session
from .models import User, UserRole
from .security import hash_password

def update_own_profile(db:Session,user:User,data):
    email=str(data.email).lower()
    if db.scalar(select(User.user_id).where(User.email==email,User.user_id!=user.user_id)): raise HTTPException(409,"Email already registered")
    user.full_name=data.full_name; user.email=email
    user.gender=data.gender; user.date_of_birth=data.date_of_birth
    return user

def ensure_super_admin_succession(db:Session,user:User):
    if user.role!=UserRole.SUPER_ADMIN: return
    active=db.scalar(select(func.count()).select_from(User).where(User.role==UserRole.SUPER_ADMIN,User.is_active.is_(True))) or 0
    if active<=1:
        raise HTTPException(409,"The last active Super Admin cannot deactivate or delete their account. Provision and verify a successor first.")

def anonymize_and_revoke(db:Session,user:User):
    ensure_super_admin_succession(db,user)
    marker=f"deleted-{user.user_id}"
    user.full_name="Deleted account"; user.email=f"{marker}@deleted.invalid"
    user.gender=None; user.date_of_birth=None; user.is_active=False
    user.password_hash=hash_password(uuid4().hex+uuid4().hex)
    return user
