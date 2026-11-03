"""Shared, transaction-safe account lifecycle operations."""
from fastapi import HTTPException
from sqlalchemy import delete, func, or_, select
from sqlalchemy.orm import Session
from .models import AdminApproval, ExerciseAttempt, PrebuiltCircuit, Progress, SavedCircuit, User, UserRole

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

def permanently_delete_user(db:Session,user:User):
    """Delete one account and its user-owned records without touching shared content.

    The caller owns the transaction and must commit. Any failure therefore rolls the
    complete operation back through the request-scoped session.
    """
    ensure_super_admin_succession(db,user)
    if db.scalar(select(PrebuiltCircuit.circuit_id).where(PrebuiltCircuit.created_by==user.user_id).limit(1)):
        raise HTTPException(409,"Account owns shared Explore circuits. Reassign or remove those circuits before permanent deletion.")
    db.execute(delete(ExerciseAttempt).where(ExerciseAttempt.learner_id==user.user_id))
    db.execute(delete(Progress).where(Progress.learner_id==user.user_id))
    db.execute(delete(SavedCircuit).where(SavedCircuit.learner_id==user.user_id))
    db.execute(delete(AdminApproval).where(or_(AdminApproval.admin_user_id==user.user_id,AdminApproval.decided_by==user.user_id)))
    db.delete(user)
