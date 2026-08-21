from fastapi import FastAPI, Depends, HTTPException, Response
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import select
from sqlalchemy.orm import Session
from .config import settings
from .database import Base, engine, get_db
from .models import User, LogicGate, Lesson, PrebuiltCircuit, SavedCircuit, Progress, Exercise
from .schemas import Register, Login, Token, UserOut, GateIn, LessonIn, CircuitIn, ExerciseIn, SavedCircuitIn, ProgressIn
from .security import hash_password, verify_password, token_for, current_user, admin_user

app = FastAPI(title="DigiGates API", version="1.0.0")
app.add_middleware(CORSMiddleware, allow_origins=[settings.frontend_origin], allow_credentials=True, allow_methods=["*"], allow_headers=["*"])

@app.on_event("startup")
def startup(): Base.metadata.create_all(engine)
@app.get("/api/health")
def health(): return {"status": "ok"}
@app.post("/api/auth/register", response_model=Token, status_code=201)
def register(data: Register, db: Session = Depends(get_db)):
    if db.scalar(select(User).where(User.email == data.email.lower())): raise HTTPException(409, "Email already registered")
    user = User(name=data.name.strip(), email=data.email.lower(), password_hash=hash_password(data.password), role="learner")
    db.add(user); db.commit(); db.refresh(user)
    return Token(access_token=token_for(user), user=user)
@app.post("/api/auth/login", response_model=Token)
def login(data: Login, db: Session = Depends(get_db)):
    user = db.scalar(select(User).where(User.email == data.email.lower()))
    if not user or not verify_password(data.password, user.password_hash): raise HTTPException(401, "Incorrect email or password")
    return Token(access_token=token_for(user), user=user)
@app.get("/api/auth/me", response_model=UserOut)
def me(user=Depends(current_user)): return user

@app.get("/api/content/gates")
def gates(db: Session = Depends(get_db), _=Depends(current_user)): return db.scalars(select(LogicGate).order_by(LogicGate.name)).all()
@app.get("/api/content/lessons")
def lessons(db: Session = Depends(get_db), _=Depends(current_user)): return db.scalars(select(Lesson).order_by(Lesson.order_index)).all()
@app.get("/api/content/circuits")
def circuits(db: Session = Depends(get_db), _=Depends(current_user)): return db.scalars(select(PrebuiltCircuit).order_by(PrebuiltCircuit.title)).all()

@app.get("/api/circuits")
def my_circuits(db: Session = Depends(get_db), user=Depends(current_user)): return db.scalars(select(SavedCircuit).where(SavedCircuit.user_id == user.id)).all()
@app.post("/api/circuits", status_code=201)
def save_circuit(data: SavedCircuitIn, db: Session = Depends(get_db), user=Depends(current_user)):
    item = db.scalar(select(SavedCircuit).where(SavedCircuit.user_id == user.id, SavedCircuit.name == data.name))
    if item: item.definition = data.definition
    else: item = SavedCircuit(user_id=user.id, name=data.name, definition=data.definition); db.add(item)
    db.commit(); db.refresh(item); return item
@app.delete("/api/circuits/{item_id}", status_code=204)
def delete_circuit(item_id: int, db: Session = Depends(get_db), user=Depends(current_user)):
    item = db.get(SavedCircuit, item_id)
    if not item or item.user_id != user.id: raise HTTPException(404, "Circuit not found")
    db.delete(item); db.commit(); return Response(status_code=204)
@app.put("/api/progress")
def save_progress(data: ProgressIn, db: Session = Depends(get_db), user=Depends(current_user)):
    item = db.scalar(select(Progress).where(Progress.user_id == user.id, Progress.mode == data.mode, Progress.item_key == data.item_key))
    if item: item.state = data.state
    else: item = Progress(user_id=user.id, **data.model_dump()); db.add(item)
    db.commit(); return {"saved": True}

RESOURCES = {"gates": (LogicGate, GateIn), "lessons": (Lesson, LessonIn), "circuits": (PrebuiltCircuit, CircuitIn), "exercises": (Exercise, ExerciseIn)}
@app.get("/api/admin/{resource}")
def admin_list(resource: str, db: Session = Depends(get_db), _=Depends(admin_user)):
    if resource == "learners": return db.scalars(select(User).where(User.role == "learner")).all()
    if resource not in RESOURCES: raise HTTPException(404, "Unknown resource")
    return db.scalars(select(RESOURCES[resource][0])).all()
@app.post("/api/admin/{resource}", status_code=201)
def admin_add(resource: str, data: dict, db: Session = Depends(get_db), _=Depends(admin_user)):
    if resource not in RESOURCES: raise HTTPException(404, "Unknown resource")
    model, schema = RESOURCES[resource]; item = model(**schema.model_validate(data).model_dump()); db.add(item); db.commit(); db.refresh(item); return item
@app.put("/api/admin/{resource}/{item_id}")
def admin_edit(resource: str, item_id: int, data: dict, db: Session = Depends(get_db), _=Depends(admin_user)):
    if resource not in RESOURCES: raise HTTPException(404, "Unknown resource")
    model, schema = RESOURCES[resource]; item = db.get(model, item_id)
    if not item: raise HTTPException(404, "Record not found")
    for key, value in schema.model_validate(data).model_dump().items(): setattr(item, key, value)
    db.commit(); db.refresh(item); return item
@app.delete("/api/admin/{resource}/{item_id}", status_code=204)
def admin_delete(resource: str, item_id: int, db: Session = Depends(get_db), _=Depends(admin_user)):
    if resource not in RESOURCES: raise HTTPException(404, "Unknown resource")
    item = db.get(RESOURCES[resource][0], item_id)
    if not item: raise HTTPException(404, "Record not found")
    db.delete(item); db.commit(); return Response(status_code=204)

