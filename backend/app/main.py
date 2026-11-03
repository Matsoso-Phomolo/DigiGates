from datetime import datetime
from decimal import Decimal
from fastapi import Depends, FastAPI, HTTPException, Response, status
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import delete, func, or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
from .config import settings
from .database import get_db
from .models import AdminApproval, ApprovalStatus, Exercise, ExerciseAttempt, Lesson, LogicGate, PrebuiltCircuit, Progress, ProgressStatus, SavedCircuit, User, UserRole
from .schemas import AdminRegistrationPending, ApprovalDecision, ApprovalHistoryOut, AttemptCreate, AttemptOut, ExerciseCreate, ExerciseOut, ExerciseUpdate, GateCreate, GateOut, GateUpdate, LessonCreate, LessonOut, LessonUpdate, Login, ManagedUserCreate, ManagedUserUpdate, PrebuiltCreate, PrebuiltOut, PrebuiltUpdate, ProgressOut, ProgressUpsert, Register, SavedCircuitCreate, SavedCircuitOut, SavedCircuitUpdate, Token, UserOut, UserPage, AccountConfirmation, AccountDeleteConfirmation, PasswordChange, ProfileUpdate
from .account_service import anonymize_and_revoke, ensure_super_admin_succession, update_own_profile
from .security import admin_user, authenticated_account, current_user, hash_password, super_admin_user, token_for, verify_password

app=FastAPI(title="DigiGates API",version="2.0.0")
app.add_middleware(CORSMiddleware,allow_origins=[settings.frontend_origin],allow_credentials=True,allow_methods=["*"],allow_headers=["*"])

def commit(db):
    try: db.commit()
    except IntegrityError as exc:
        db.rollback(); raise HTTPException(409,"Operation conflicts with an existing or referenced record") from exc
def require_learner(user):
    if user.role!=UserRole.LEARNER: raise HTTPException(403,"Learner role required")
def get_or_404(db,model,item_id):
    item=db.get(model,item_id)
    if not item: raise HTTPException(404,"Record not found")
    return item

@app.get("/api/health")
def health(): return {"status":"ok","database":"mysql"}
@app.post("/api/auth/register",response_model=Token|AdminRegistrationPending,status_code=201)
def register(data:Register,db:Session=Depends(get_db)):
    email=str(data.email).lower()
    if db.scalar(select(User).where(User.email==email)): raise HTTPException(409,"Email already registered")
    role=UserRole.ADMIN if data.requested_role=="ADMIN" else UserRole.LEARNER
    approval=ApprovalStatus.PENDING if role==UserRole.ADMIN else ApprovalStatus.ACTIVE
    user=User(full_name=data.full_name,email=email,password_hash=hash_password(data.password),role=role,approval_status=approval)
    db.add(user); commit(db); db.refresh(user)
    if approval==ApprovalStatus.PENDING:
        return AdminRegistrationPending(message="Administrator access requires Super Admin approval.",user=user)
    return Token(access_token=token_for(user),user=user)
@app.post("/api/auth/login",response_model=Token)
def login(data:Login,db:Session=Depends(get_db)):
    user=db.scalar(select(User).where(User.email==str(data.email).lower()))
    if not user or not verify_password(data.password,user.password_hash): raise HTTPException(401,"Incorrect email or password")
    if not user.is_active: raise HTTPException(403,"Account is inactive")
    return Token(access_token=token_for(user),user=user)
@app.get("/api/auth/me",response_model=UserOut)
def me(user=Depends(current_user)): return user

@app.get("/api/profile",response_model=UserOut)
def profile(user=Depends(authenticated_account)):
    return user

@app.put("/api/profile",response_model=UserOut)
def update_profile(data:ProfileUpdate,db:Session=Depends(get_db),user=Depends(authenticated_account)):
    update_own_profile(db,user,data)
    commit(db)
    db.refresh(user)
    return user

@app.put("/api/profile/password",status_code=204)
def change_password(data:PasswordChange,db:Session=Depends(get_db),user=Depends(authenticated_account)):
    if not verify_password(data.current_password,user.password_hash): raise HTTPException(401,"Current password is incorrect")
    if verify_password(data.new_password,user.password_hash): raise HTTPException(400,"New password must be different from current password")
    user.password_hash=hash_password(data.new_password)
    commit(db)
    return Response(status_code=204)

@app.post("/api/profile/deactivate",status_code=204)
def deactivate_account(data:AccountConfirmation,db:Session=Depends(get_db),user=Depends(authenticated_account)):
    if not verify_password(data.current_password,user.password_hash): raise HTTPException(401,"Current password is incorrect")
    ensure_super_admin_succession(db,user)
    user.is_active=False
    commit(db)
    return Response(status_code=204)

@app.delete("/api/profile",status_code=204)
def delete_account(data:AccountDeleteConfirmation,db:Session=Depends(get_db),user=Depends(authenticated_account)):
    if not verify_password(data.current_password,user.password_hash): raise HTTPException(401,"Current password is incorrect")
    anonymize_and_revoke(db,user)
    commit(db)
    return Response(status_code=204)

ADMIN_RESOURCES={
    "logic-gates":(LogicGate,GateCreate,GateUpdate,GateOut,"gate_id"),
    "lessons":(Lesson,LessonCreate,LessonUpdate,LessonOut,"lesson_id"),
    "prebuilt-circuits":(PrebuiltCircuit,PrebuiltCreate,PrebuiltUpdate,PrebuiltOut,"circuit_id"),
    "exercises":(Exercise,ExerciseCreate,ExerciseUpdate,ExerciseOut,"exercise_id"),
}
def resource_spec(name):
    if name not in ADMIN_RESOURCES: raise HTTPException(404,"Unknown resource")
    return ADMIN_RESOURCES[name]
def user_page(db,role,page,page_size,q):
    filters=[User.role==role]
    if q:
        term=f"%{q.strip()}%"; filters.append(or_(User.full_name.like(term),User.email.like(term)))
    total=db.scalar(select(func.count()).select_from(User).where(*filters)) or 0
    items=db.scalars(select(User).where(*filters).order_by(User.full_name).offset((page-1)*page_size).limit(page_size)).all()
    return UserPage(items=items,page=page,page_size=page_size,total=total,pages=max(1,(total+page_size-1)//page_size))
def managed_user(db,item_id,role):
    item=db.scalar(select(User).where(User.user_id==item_id,User.role==role))
    if not item: raise HTTPException(404,"Account not found")
    return item
def apply_user_fields(db,user,data):
    email=str(data.email).lower()
    if db.scalar(select(User).where(User.email==email,User.user_id!=user.user_id)): raise HTTPException(409,"Email already registered")
    for key,value in data.model_dump(exclude={"password"}).items(): setattr(user,key,email if key=="email" else value)

@app.get("/api/admin/learners",response_model=UserPage)
def learners(page:int=1,page_size:int=20,q:str|None=None,db:Session=Depends(get_db),_=Depends(admin_user)):
    if page<1 or not 1<=page_size<=100: raise HTTPException(422,"Invalid pagination")
    return user_page(db,UserRole.LEARNER,page,page_size,q)
@app.get("/api/admin/learners/{item_id}",response_model=UserOut)
def learner(item_id:int,db:Session=Depends(get_db),_=Depends(admin_user)): return managed_user(db,item_id,UserRole.LEARNER)
@app.post("/api/admin/learners",response_model=UserOut,status_code=201)
def create_learner(data:ManagedUserCreate,db:Session=Depends(get_db),_=Depends(admin_user)):
    user=User(full_name=data.full_name,email=str(data.email).lower(),password_hash=hash_password(data.password),gender=data.gender,date_of_birth=data.date_of_birth,role=UserRole.LEARNER,approval_status=ApprovalStatus.ACTIVE)
    db.add(user); commit(db); db.refresh(user); return user
@app.put("/api/admin/learners/{item_id}",response_model=UserOut)
def update_learner(item_id:int,data:ManagedUserUpdate,db:Session=Depends(get_db),_=Depends(admin_user)):
    user=managed_user(db,item_id,UserRole.LEARNER); apply_user_fields(db,user,data); commit(db); db.refresh(user); return user
@app.delete("/api/admin/learners/{item_id}",status_code=204)
def delete_learner(item_id:int,db:Session=Depends(get_db),_=Depends(admin_user)):
    user=managed_user(db,item_id,UserRole.LEARNER); user.is_active=False; commit(db); return Response(status_code=204)

@app.get("/api/super-admin/admins",response_model=UserPage)
def admins(page:int=1,page_size:int=20,q:str|None=None,db:Session=Depends(get_db),_=Depends(super_admin_user)):
    if page<1 or not 1<=page_size<=100: raise HTTPException(422,"Invalid pagination")
    return user_page(db,UserRole.ADMIN,page,page_size,q)
@app.get("/api/super-admin/admins/{item_id}",response_model=UserOut)
def admin_account(item_id:int,db:Session=Depends(get_db),_=Depends(super_admin_user)): return managed_user(db,item_id,UserRole.ADMIN)
@app.post("/api/super-admin/admins",response_model=UserOut,status_code=201)
def create_admin(data:ManagedUserCreate,db:Session=Depends(get_db),_=Depends(super_admin_user)):
    user=User(full_name=data.full_name,email=str(data.email).lower(),password_hash=hash_password(data.password),gender=data.gender,date_of_birth=data.date_of_birth,role=UserRole.ADMIN,approval_status=ApprovalStatus.ACTIVE)
    db.add(user); commit(db); db.refresh(user); return user
@app.put("/api/super-admin/admins/{item_id}",response_model=UserOut)
def update_admin(item_id:int,data:ManagedUserUpdate,db:Session=Depends(get_db),_=Depends(super_admin_user)):
    user=managed_user(db,item_id,UserRole.ADMIN); apply_user_fields(db,user,data); commit(db); db.refresh(user); return user
@app.delete("/api/super-admin/admins/{item_id}",status_code=204)
def delete_admin(item_id:int,db:Session=Depends(get_db),_=Depends(super_admin_user)):
    user=managed_user(db,item_id,UserRole.ADMIN); user.is_active=False; commit(db); return Response(status_code=204)
@app.get("/api/super-admin/admin-requests",response_model=list[UserOut])
def pending_admins(db:Session=Depends(get_db),_=Depends(super_admin_user)):
    return db.scalars(select(User).where(User.role==UserRole.ADMIN,User.approval_status==ApprovalStatus.PENDING).order_by(User.created_at)).all()
@app.post("/api/super-admin/admin-requests/{item_id}/decision",response_model=UserOut)
def decide_admin(item_id:int,data:ApprovalDecision,db:Session=Depends(get_db),super_admin=Depends(super_admin_user)):
    user=db.scalar(select(User).where(User.user_id==item_id,User.role==UserRole.ADMIN).with_for_update())
    if not user: raise HTTPException(404,"Administrator request not found")
    if user.approval_status!=ApprovalStatus.PENDING: raise HTTPException(409,"Administrator request has already been decided")
    result=ApprovalStatus.ACTIVE if data.decision=="APPROVE" else ApprovalStatus.REJECTED
    user.approval_status=result
    db.add(AdminApproval(admin_user_id=user.user_id,status=result,decided_by=super_admin.user_id,decision_note=data.note))
    commit(db); db.refresh(user); return user
@app.get("/api/super-admin/approval-history",response_model=list[ApprovalHistoryOut])
def approval_history(db:Session=Depends(get_db),_=Depends(super_admin_user)):
    return db.scalars(select(AdminApproval).order_by(AdminApproval.decided_at.desc())).all()
@app.get("/api/admin/{resource}")
def admin_list(resource:str,db:Session=Depends(get_db),_=Depends(admin_user)):
    model,*_=resource_spec(resource); return db.scalars(select(model)).all()
@app.get("/api/admin/{resource}/{item_id}")
def admin_view(resource:str,item_id:int,db:Session=Depends(get_db),_=Depends(admin_user)):
    model,*_=resource_spec(resource); return get_or_404(db,model,item_id)
@app.post("/api/admin/{resource}",status_code=201)
def admin_create(resource:str,payload:dict,db:Session=Depends(get_db),admin=Depends(admin_user)):
    model,create_schema,*_=resource_spec(resource); data=create_schema.model_validate(payload).model_dump(mode="json")
    if model is PrebuiltCircuit: data["created_by"]=admin.user_id
    item=model(**data); db.add(item); commit(db); db.refresh(item); return item
@app.put("/api/admin/{resource}/{item_id}")
def admin_update(resource:str,item_id:int,payload:dict,db:Session=Depends(get_db),_=Depends(admin_user)):
    model,_,update_schema,*_=resource_spec(resource); item=get_or_404(db,model,item_id)
    for key,value in update_schema.model_validate(payload).model_dump(mode="json").items(): setattr(item,key,value)
    commit(db); db.refresh(item); return item
@app.delete("/api/admin/{resource}/{item_id}",status_code=204)
def admin_delete(resource:str,item_id:int,db:Session=Depends(get_db),_=Depends(admin_user)):
    model,*_=resource_spec(resource); item=get_or_404(db,model,item_id); db.delete(item); commit(db); return Response(status_code=204)

@app.get("/api/lessons",response_model=list[LessonOut])
def published_lessons(db:Session=Depends(get_db),_=Depends(current_user)):
    return db.scalars(select(Lesson).where(Lesson.is_published.is_(True)).order_by(Lesson.lesson_order)).all()
@app.get("/api/prebuilt-circuits",response_model=list[PrebuiltOut])
def published_circuits(db:Session=Depends(get_db),_=Depends(current_user)):
    return db.scalars(select(PrebuiltCircuit).where(PrebuiltCircuit.is_published.is_(True)).order_by(PrebuiltCircuit.title)).all()

@app.post("/api/saved-circuits",response_model=SavedCircuitOut,status_code=201)
def save_circuit(data:SavedCircuitCreate,db:Session=Depends(get_db),user=Depends(current_user)):
    require_learner(user); item=SavedCircuit(learner_id=user.user_id,**data.model_dump(mode="json")); db.add(item); commit(db); db.refresh(item); return item
@app.get("/api/saved-circuits",response_model=list[SavedCircuitOut])
def list_circuits(db:Session=Depends(get_db),user=Depends(current_user)):
    require_learner(user); return db.scalars(select(SavedCircuit).where(SavedCircuit.learner_id==user.user_id).order_by(SavedCircuit.updated_at.desc())).all()
def own_circuit(db,user,item_id):
    item=db.scalar(select(SavedCircuit).where(SavedCircuit.saved_circuit_id==item_id,SavedCircuit.learner_id==user.user_id))
    if not item: raise HTTPException(404,"Circuit not found")
    return item
@app.get("/api/saved-circuits/{item_id}",response_model=SavedCircuitOut)
def load_circuit(item_id:int,db:Session=Depends(get_db),user=Depends(current_user)):
    require_learner(user); return own_circuit(db,user,item_id)
@app.put("/api/saved-circuits/{item_id}",response_model=SavedCircuitOut)
def update_circuit(item_id:int,data:SavedCircuitUpdate,db:Session=Depends(get_db),user=Depends(current_user)):
    require_learner(user); item=own_circuit(db,user,item_id)
    for k,v in data.model_dump(mode="json").items(): setattr(item,k,v)
    commit(db); db.refresh(item); return item
@app.delete("/api/saved-circuits/{item_id}",status_code=204)
def remove_circuit(item_id:int,db:Session=Depends(get_db),user=Depends(current_user)):
    require_learner(user); db.delete(own_circuit(db,user,item_id)); commit(db); return Response(status_code=204)

@app.put("/api/progress",response_model=ProgressOut)
def upsert_progress(data:ProgressUpsert,db:Session=Depends(get_db),user=Depends(current_user)):
    require_learner(user); get_or_404(db,Lesson,data.lesson_id)
    item=db.scalar(select(Progress).where(Progress.learner_id==user.user_id,Progress.lesson_id==data.lesson_id))
    now=datetime.utcnow()
    if not item: item=Progress(learner_id=user.user_id,lesson_id=data.lesson_id); db.add(item)
    item.status=data.status; item.last_accessed_at=now
    item.completed_at=now if data.status==ProgressStatus.COMPLETED else None
    commit(db); db.refresh(item); return item
@app.get("/api/progress",response_model=list[ProgressOut])
def own_progress(db:Session=Depends(get_db),user=Depends(current_user)):
    require_learner(user); return db.scalars(select(Progress).where(Progress.learner_id==user.user_id)).all()

@app.post("/api/exercise-attempts",response_model=AttemptOut,status_code=201)
def submit_attempt(data:AttemptCreate,db:Session=Depends(get_db),user=Depends(current_user)):
    require_learner(user); exercise=get_or_404(db,Exercise,data.exercise_id)
    if not exercise.is_published: raise HTTPException(404,"Exercise not found")
    correct=data.submitted_answer==exercise.expected_result
    item=ExerciseAttempt(exercise_id=exercise.exercise_id,learner_id=user.user_id,submitted_answer=data.submitted_answer,is_correct=correct,score=Decimal("100") if correct else Decimal("0"))
    db.add(item); commit(db); db.refresh(item); return item
