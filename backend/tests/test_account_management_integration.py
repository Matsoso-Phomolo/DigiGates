from app.database import SessionLocal
from app.models import ApprovalStatus, User, UserRole
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
    assert mysql_client.get("/api/super-admin/admin-requests",headers=super_headers).status_code==200
    approved=mysql_client.post(f"/api/super-admin/admin-requests/{pending_id}/decision",headers=super_headers,json={"decision":"APPROVE","note":"Verified"})
    assert approved.status_code==200 and approved.json()["approval_status"]=="ACTIVE"
    assert mysql_client.post(f"/api/super-admin/admin-requests/{pending_id}/decision",headers=super_headers,json={"decision":"APPROVE"}).status_code==409
    login=mysql_client.post("/api/auth/login",json={"email":"pending-approve@example.com","password":"Secure123!"})
    assert login.status_code==200

    rejected=mysql_client.post("/api/auth/register",json={"full_name":"Rejected Admin","email":"pending-reject@example.com","password":"Secure123!","requested_role":"ADMIN"})
    rejected_id=rejected.json()["user"]["user_id"]
    decision=mysql_client.post(f"/api/super-admin/admin-requests/{rejected_id}/decision",headers=super_headers,json={"decision":"REJECT","note":"Not approved"})
    assert decision.status_code==200 and decision.json()["approval_status"]=="REJECTED"
    rejected_login=mysql_client.post("/api/auth/login",json={"email":"pending-reject@example.com","password":"Secure123!"})
    rejected_headers={"Authorization":"Bearer "+rejected_login.json()["access_token"]}
    assert mysql_client.get("/api/profile",headers=rejected_headers).status_code==200
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
    updated=mysql_client.put(f"/api/admin/learners/{learner_id}",headers=admin_headers,json={"full_name":"Updated Learner","email":"managed-learner@example.com","gender":"PREFER_NOT_TO_SAY","date_of_birth":"2001-02-03","is_active":True})
    assert updated.status_code==200 and updated.json()["full_name"]=="Updated Learner"
    assert mysql_client.delete(f"/api/admin/learners/{learner_id}",headers=admin_headers).status_code==204

    super_headers=privileged(UserRole.SUPER_ADMIN,"admin-manager@example.com")
    admin=mysql_client.post("/api/super-admin/admins",headers=super_headers,json={"full_name":"Managed Admin","email":"managed-admin@example.com","password":"Secure123!","gender":None,"date_of_birth":None})
    assert admin.status_code==201 and "username" not in admin.json()
    admin_id=admin.json()["user_id"]
    assert mysql_client.get(f"/api/super-admin/admins/{admin_id}",headers=super_headers).status_code==200
    assert mysql_client.put(f"/api/super-admin/admins/{admin_id}",headers=super_headers,json={"full_name":"Updated Admin","email":"managed-admin@example.com","gender":"NON_BINARY","date_of_birth":"1990-04-05","is_active":True}).status_code==200
    assert mysql_client.delete(f"/api/super-admin/admins/{admin_id}",headers=super_headers).status_code==204
    assert mysql_client.get("/api/super-admin/admins",headers=admin_headers).status_code==403

def test_management_list_serializes_anonymized_self_deleted_account(mysql_client):
    admin_headers=privileged(UserRole.ADMIN,"deleted-list-manager@example.com")
    registration=mysql_client.post("/api/auth/register",json={"full_name":"Disposable Learner","email":"disposable-list@example.com","password":"Secure123!","requested_role":"LEARNER"})
    learner_headers={"Authorization":"Bearer "+registration.json()["access_token"]}
    deleted=mysql_client.request("DELETE","/api/profile",headers=learner_headers,json={"current_password":"Secure123!","confirmation":"DELETE"})
    assert deleted.status_code==204
    listing=mysql_client.get("/api/admin/learners?q=deleted-",headers=admin_headers)
    assert listing.status_code==200
    assert listing.json()["total"]==1
    assert listing.json()["items"][0]["email"].endswith("@deleted.invalid")
