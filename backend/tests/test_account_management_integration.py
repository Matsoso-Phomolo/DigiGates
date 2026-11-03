from app.database import SessionLocal
from decimal import Decimal
from app.models import ApprovalStatus, Exercise, ExerciseAttempt, Lesson, LogicGate, PrebuiltCircuit, Progress, SavedCircuit, User, UserRole
from app.security import hash_password, token_for

def privileged(role,email):
    with SessionLocal() as db:
        user=User(full_name=role.value.title(),email=email,password_hash=hash_password("Secure123!"),role=role,approval_status=ApprovalStatus.ACTIVE)
        db.add(user); db.commit(); db.refresh(user)
        return {"Authorization":"Bearer "+token_for(user)}

def test_super_admin_approval_and_rejection(mysql_client):
    super_headers=privileged(UserRole.SUPER_ADMIN,"approval-super@example.com")
    pending=mysql_client.post("/api/auth/register",json={"full_name":"Pending Admin","email":"pending-approve@example.com","password":"Secure123!","requested_role":"ADMIN"})
    assert pending.status_code==201 and pending.json()["status"]=="PENDING"
    pending_id=pending.json()["user"]["user_id"]
    assert "access_token" not in pending.json()
    assert mysql_client.post("/api/auth/login",json={"email":"pending-approve@example.com","password":"Secure123!"}).status_code==403
    assert mysql_client.get("/api/super-admin/admin-requests",headers=super_headers).status_code==200
    approved=mysql_client.post(f"/api/super-admin/admin-requests/{pending_id}/decision",headers=super_headers,json={"decision":"APPROVE","note":"Verified"})
    assert approved.status_code==200 and approved.json()["approval_status"]=="ACTIVE"
    assert mysql_client.post(f"/api/super-admin/admin-requests/{pending_id}/decision",headers=super_headers,json={"decision":"APPROVE"}).status_code==409
    login=mysql_client.post("/api/auth/login",json={"email":"pending-approve@example.com","password":"Secure123!"})
    assert login.status_code==200

    rejected=mysql_client.post("/api/auth/register",json={"full_name":"Rejected Admin","email":"pending-reject@example.com","password":"Secure123!","requested_role":"ADMIN"})
    rejected_id=rejected.json()["user"]["user_id"]
    with SessionLocal() as db:
        rejected_user=db.get(User,rejected_id)
        rejected_headers={"Authorization":"Bearer "+token_for(rejected_user)}
    decision=mysql_client.post(f"/api/super-admin/admin-requests/{rejected_id}/decision",headers=super_headers,json={"decision":"REJECT","note":"Not approved"})
    assert decision.status_code==200 and decision.json()["approval_status"]=="REJECTED"
    rejected_login=mysql_client.post("/api/auth/login",json={"email":"pending-reject@example.com","password":"Secure123!"})
    assert rejected_login.status_code==403
    assert mysql_client.get("/api/profile",headers=rejected_headers).status_code==403
    assert mysql_client.get("/api/admin/learners",headers=rejected_headers).status_code==403
    history=mysql_client.get("/api/super-admin/approval-history",headers=super_headers)
    assert history.status_code==200 and len(history.json())>=2

def test_role_scoped_account_crud_and_profile_persistence(mysql_client):
    admin_headers=privileged(UserRole.ADMIN,"learner-manager@example.com")
    created=mysql_client.post("/api/admin/learners",headers=admin_headers,json={"full_name":"Managed Learner","email":"managed-learner@example.com","password":"Secure123!","gender":"FEMALE","date_of_birth":"2001-02-03"})
    assert created.status_code==201
    learner=created.json(); learner_id=learner["user_id"]
    assert "username" not in learner and learner["gender"]=="FEMALE" and learner["date_of_birth"]=="2001-02-03"
    listing=mysql_client.get("/api/admin/learners?q=managed-learner@example.com",headers=admin_headers)
    assert listing.status_code==200 and listing.json()["total"]==1
    updated=mysql_client.put(f"/api/admin/learners/{learner_id}",headers=admin_headers,json={"full_name":"Updated Learner","email":"managed-learner@example.com","gender":"PREFER_NOT_TO_SAY","date_of_birth":"2001-02-03"})
    assert updated.status_code==200 and updated.json()["full_name"]=="Updated Learner"
    learner_token=mysql_client.post("/api/auth/login",json={"email":"managed-learner@example.com","password":"Secure123!"}).json()["access_token"]
    learner_headers={"Authorization":"Bearer "+learner_token}
    assert mysql_client.post(f"/api/admin/learners/{learner_id}/deactivate",headers=admin_headers).status_code==204
    assert mysql_client.post("/api/auth/login",json={"email":"managed-learner@example.com","password":"Secure123!"}).status_code==403
    assert mysql_client.get("/api/profile",headers=learner_headers).status_code==401
    inactive_edit=mysql_client.put(f"/api/admin/learners/{learner_id}",headers=admin_headers,json={"full_name":"Edited While Inactive","email":"managed-learner@example.com","gender":"PREFER_NOT_TO_SAY","date_of_birth":"2001-02-03"})
    assert inactive_edit.status_code==200 and inactive_edit.json()["is_active"] is False
    assert mysql_client.post(f"/api/admin/learners/{learner_id}/reactivate",headers=admin_headers).status_code==204
    assert mysql_client.post("/api/auth/login",json={"email":"managed-learner@example.com","password":"Secure123!"}).status_code==200
    assert mysql_client.delete(f"/api/admin/learners/{learner_id}",headers=admin_headers).status_code==204
    with SessionLocal() as db: assert db.get(User,learner_id) is None

    super_headers=privileged(UserRole.SUPER_ADMIN,"admin-manager@example.com")
    admin=mysql_client.post("/api/super-admin/admins",headers=super_headers,json={"full_name":"Managed Admin","email":"managed-admin@example.com","password":"Secure123!","gender":None,"date_of_birth":None})
    assert admin.status_code==201 and "username" not in admin.json()
    admin_id=admin.json()["user_id"]
    assert mysql_client.get(f"/api/super-admin/admins/{admin_id}",headers=super_headers).status_code==200
    assert mysql_client.put(f"/api/super-admin/admins/{admin_id}",headers=super_headers,json={"full_name":"Updated Admin","email":"managed-admin@example.com","gender":"NON_BINARY","date_of_birth":"1990-04-05"}).status_code==200
    assert mysql_client.post(f"/api/super-admin/admins/{admin_id}/deactivate",headers=super_headers).status_code==204
    assert mysql_client.post(f"/api/super-admin/admins/{admin_id}/reactivate",headers=super_headers).status_code==204
    assert mysql_client.delete(f"/api/super-admin/admins/{admin_id}",headers=super_headers).status_code==204
    assert mysql_client.get("/api/super-admin/admins",headers=admin_headers).status_code==403
    assert mysql_client.post(f"/api/super-admin/admins/{admin_id}/reactivate",headers=admin_headers).status_code==403

def test_permanent_delete_removes_user_owned_records_without_placeholder(mysql_client,circuit_json):
    admin_headers=privileged(UserRole.ADMIN,"delete-manager@example.com")
    created=mysql_client.post("/api/admin/learners",headers=admin_headers,json={"full_name":"Owned Data Learner","email":"owned-data@example.com","password":"Secure123!"})
    learner_id=created.json()["user_id"]
    with SessionLocal() as db:
        gate=LogicGate(gate_name="DELETE_TEST_GATE",description="test",input_count=1,boolean_symbol="A",expression_pattern="{A}")
        db.add(gate); db.flush()
        lesson=Lesson(gate_id=gate.gate_id,title="Deletion test",theory_content="test",lesson_order=999,is_published=False)
        db.add(lesson); db.flush()
        exercise=Exercise(lesson_id=lesson.lesson_id,title="Deletion exercise",instructions="test",exercise_type="test",expected_result={"Y":1},is_published=False)
        db.add(exercise); db.flush()
        gate_id,lesson_id,exercise_id=gate.gate_id,lesson.lesson_id,exercise.exercise_id
        db.add_all([
            SavedCircuit(learner_id=learner_id,circuit_name="Owned circuit",circuit_definition=circuit_json,expression="Y = NOT A"),
            Progress(learner_id=learner_id,lesson_id=lesson.lesson_id),
            ExerciseAttempt(exercise_id=exercise.exercise_id,learner_id=learner_id,submitted_answer={"Y":1},is_correct=True,score=Decimal("100")),
        ])
        db.commit()
    assert mysql_client.delete(f"/api/admin/learners/{learner_id}",headers=admin_headers).status_code==204
    with SessionLocal() as db:
        assert db.get(User,learner_id) is None
        assert db.query(SavedCircuit).filter_by(learner_id=learner_id).count()==0
        assert db.query(Progress).filter_by(learner_id=learner_id).count()==0
        assert db.query(ExerciseAttempt).filter_by(learner_id=learner_id).count()==0
        assert db.query(User).filter(User.email.like("deleted-%@deleted.invalid")).count()==0
        db.delete(db.get(Exercise,exercise_id)); db.delete(db.get(Lesson,lesson_id)); db.delete(db.get(LogicGate,gate_id)); db.commit()

def test_shared_content_blocks_delete_and_rolls_back_owned_data(mysql_client,circuit_json):
    admin_headers=privileged(UserRole.ADMIN,"rollback-manager@example.com")
    created=mysql_client.post("/api/admin/learners",headers=admin_headers,json={"full_name":"Content Owner","email":"content-owner@example.com","password":"Secure123!"})
    learner_id=created.json()["user_id"]
    with SessionLocal() as db:
        db.add(SavedCircuit(learner_id=learner_id,circuit_name="Keep on failure",circuit_definition=circuit_json,expression="Y = NOT A"))
        db.add(PrebuiltCircuit(title="Shared content",description="shared",difficulty="BEGINNER",circuit_definition=circuit_json,expression="Y = NOT A",created_by=learner_id,is_published=True))
        db.commit()
    blocked=mysql_client.delete(f"/api/admin/learners/{learner_id}",headers=admin_headers)
    assert blocked.status_code==409
    with SessionLocal() as db:
        assert db.get(User,learner_id) is not None
        assert db.query(SavedCircuit).filter_by(learner_id=learner_id).count()==1
        assert db.query(PrebuiltCircuit).filter_by(created_by=learner_id).count()==1
