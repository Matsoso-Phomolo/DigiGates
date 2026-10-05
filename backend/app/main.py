from datetime import datetime
from decimal import Decimal
from fastapi import Depends, FastAPI, HTTPException, Response, status
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import delete, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
from .config import settings
from .database import get_db
from .models import Exercise, ExerciseAttempt, Lesson, LogicGate, PrebuiltCircuit, Progress, ProgressStatus, SavedCircuit, User, UserRole
from .schemas import AttemptCreate, AttemptOut, ExerciseCreate, ExerciseOut, ExerciseUpdate, GateCreate, GateOut, GateUpdate, LessonCreate, LessonOut, LessonUpdate, Login, PrebuiltCreate, PrebuiltOut, PrebuiltUpdate, ProgressOut, ProgressUpsert, Register, SavedCircuitCreate, SavedCircuitOut, SavedCircuitUpdate, Token, UserOut, AccountConfirmation, AccountDeleteConfirmation, PasswordChange, ProfileUpdate
from .security import admin_user, current_user, hash_password, token_for, verify_password

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
@app.post("/api/auth/register",response_model=Token,status_code=201)
def register(data:Register,db:Session=Depends(get_db)):
    email=str(data.email).lower()
    if db.scalar(select(User).where(User.email==email)): raise HTTPException(409,"Email already registered")
    user=User(full_name=data.full_name,email=email,password_hash=hash_password(data.password),role=UserRole.LEARNER)
    db.add(user); commit(db); db.refresh(user)
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
def profile(user=Depends(current_user)):
    return user

@app.put("/api/profile",response_model=UserOut)
def update_profile(data:ProfileUpdate,db:Session=Depends(get_db),user=Depends(current_user)):
    email=str(data.email).lower()
    existing=db.scalar(select(User).where(User.email==email,User.user_id!=user.user_id))
    if existing: raise HTTPException(409,"Email already registered")
    user.full_name=data.full_name
    user.email=email
    commit(db)
    db.refresh(user)
    return user

@app.put("/api/profile/password",status_code=204)
def change_password(data:PasswordChange,db:Session=Depends(get_db),user=Depends(current_user)):
    if not verify_password(data.current_password,user.password_hash): raise HTTPException(401,"Current password is incorrect")
    if verify_password(data.new_password,user.password_hash): raise HTTPException(400,"New password must be different from current password")
    user.password_hash=hash_password(data.new_password)
    commit(db)
    return Response(status_code=204)

@app.post("/api/profile/deactivate",status_code=204)
def deactivate_account(data:AccountConfirmation,db:Session=Depends(get_db),user=Depends(current_user)):
    if user.role!=UserRole.LEARNER: raise HTTPException(403,"Learner account required")
    if not verify_password(data.current_password,user.password_hash): raise HTTPException(401,"Current password is incorrect")
    user.is_active=False
    commit(db)
    return Response(status_code=204)

@app.delete("/api/profile",status_code=204)
def delete_account(data:AccountDeleteConfirmation,db:Session=Depends(get_db),user=Depends(current_user)):
    if user.role!=UserRole.LEARNER: raise HTTPException(403,"Learner account required")
    if not verify_password(data.current_password,user.password_hash): raise HTTPException(401,"Current password is incorrect")
    db.execute(delete(ExerciseAttempt).where(ExerciseAttempt.learner_id==user.user_id))
    db.execute(delete(Progress).where(Progress.learner_id==user.user_id))
    db.execute(delete(SavedCircuit).where(SavedCircuit.learner_id==user.user_id))
    db.delete(user)
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
