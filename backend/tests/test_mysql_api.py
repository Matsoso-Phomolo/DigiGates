from app.database import SessionLocal
from app.models import Exercise, Lesson, LogicGate, PrebuiltCircuit, User, UserRole
from app.security import hash_password
from app.seed import seed_logic_gates

def auth(client,email="learner@example.com",name="Learner"):
    response=client.post("/api/auth/register",json={"full_name":name,"email":email,"password":"Secure123!"})
    return response,{"Authorization":f"Bearer {response.json()['access_token']}"}
def admin_header():
    with SessionLocal() as db:
        user=User(full_name="Admin",email="admin@example.com",password_hash=hash_password("Secure123!"),role=UserRole.ADMIN); db.add(user); db.commit()
    from app.security import token_for
    return {"Authorization":f"Bearer {token_for(user)}"}
def test_registration_duplicate_and_no_password(mysql_client):
    response,_=auth(mysql_client); assert response.status_code==201; assert "password" not in str(response.json())
    assert mysql_client.post("/api/auth/register",json={"full_name":"Other","email":"learner@example.com","password":"Secure123!"}).status_code==409
def test_seed_idempotent(mysql_client):
    with SessionLocal() as db: seed_logic_gates(db); seed_logic_gates(db); assert db.query(LogicGate).count()==8
def test_admin_crud_and_learner_denied(mysql_client,circuit_json):
    headers=admin_header()
    gate=mysql_client.post("/api/admin/logic-gates",headers=headers,json={"gate_name":"CUSTOM","description":"Custom","input_count":1,"boolean_symbol":"A","expression_pattern":"A"}); assert gate.status_code==201
    lesson=mysql_client.post("/api/admin/lessons",headers=headers,json={"gate_id":gate.json()["gate_id"],"title":"Lesson","theory_content":"Theory","lesson_order":1,"is_published":True}); assert lesson.status_code==201
    circuit=mysql_client.post("/api/admin/prebuilt-circuits",headers=headers,json={"title":"Explore","description":"Demo","difficulty":"BEGINNER","circuit_definition":circuit_json,"expression":"NOT A","is_published":True}); assert circuit.status_code==201
    exercise=mysql_client.post("/api/admin/exercises",headers=headers,json={"lesson_id":lesson.json()["lesson_id"],"circuit_id":None,"title":"Try","instructions":"Answer","exercise_type":"OUTPUT","expected_result":{"Y":1},"is_published":True}); assert exercise.status_code==201
    _,learner_headers=auth(mysql_client,"denied@example.com","Denied")
    assert mysql_client.get("/api/admin/lessons",headers=learner_headers).status_code==403
def test_saved_ownership_progress_and_attempt(mysql_client,circuit_json):
    _,h1=auth(mysql_client,"one@example.com","One"); _,h2=auth(mysql_client,"two@example.com","Two")
    saved=mysql_client.post("/api/saved-circuits",headers=h1,json={"circuit_name":"Mine","circuit_definition":circuit_json,"expression":"NOT A"}); assert saved.status_code==201
    item_id=saved.json()["saved_circuit_id"]; assert mysql_client.get(f"/api/saved-circuits/{item_id}",headers=h1).status_code==200; assert mysql_client.get(f"/api/saved-circuits/{item_id}",headers=h2).status_code==404
    with SessionLocal() as db:
        gate=db.query(LogicGate).first(); lesson=Lesson(gate_id=gate.gate_id,title="Progress",theory_content="Theory",lesson_order=2,is_published=True); db.add(lesson); db.flush(); exercise=Exercise(lesson_id=lesson.lesson_id,title="Output",instructions="Answer",exercise_type="OUTPUT",expected_result={"Y":1},is_published=True); db.add(exercise); db.commit(); lesson_id=lesson.lesson_id; exercise_id=exercise.exercise_id
    assert mysql_client.put("/api/progress",headers=h1,json={"lesson_id":lesson_id,"status":"IN_PROGRESS"}).status_code==200
    assert mysql_client.put("/api/progress",headers=h1,json={"lesson_id":lesson_id,"status":"COMPLETED"}).status_code==200
    assert len(mysql_client.get("/api/progress",headers=h1).json())==1
    attempt=mysql_client.post("/api/exercise-attempts",headers=h1,json={"exercise_id":exercise_id,"submitted_answer":{"Y":1}}); assert attempt.status_code==201; assert attempt.json()["is_correct"] is True
