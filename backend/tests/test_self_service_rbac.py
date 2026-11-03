from app.database import SessionLocal
from app.models import ApprovalStatus, User, UserRole
from app.security import hash_password, token_for

def make_user(role,email):
    with SessionLocal() as db:
        user=User(full_name=role.value.title(),email=email,password_hash=hash_password('Secure123!'),role=role,approval_status=ApprovalStatus.ACTIVE)
        db.add(user); db.commit(); db.refresh(user); token=token_for(user); return user.user_id,{"Authorization":"Bearer "+token}

def test_admin_can_read_update_and_delete_own_profile(mysql_client):
    user_id,headers=make_user(UserRole.ADMIN,'self-admin@example.com')
    assert mysql_client.get('/api/profile',headers=headers).status_code==200
    updated=mysql_client.put('/api/profile',headers=headers,json={"full_name":"Updated Admin","email":"self-admin@example.com","gender":"PREFER_NOT_TO_SAY","date_of_birth":"1995-01-01"})
    assert updated.status_code==200 and updated.json()['gender']=='PREFER_NOT_TO_SAY'
    deleted=mysql_client.request('DELETE','/api/profile',headers=headers,json={"current_password":"Secure123!","confirmation":"DELETE"})
    assert deleted.status_code==204
    assert mysql_client.get('/api/profile',headers=headers).status_code==401

def test_last_super_admin_requires_successor(mysql_client):
    with SessionLocal() as db:
        for existing in db.query(User).filter(User.role==UserRole.SUPER_ADMIN).all(): existing.is_active=False
        db.commit()
    _,headers=make_user(UserRole.SUPER_ADMIN,'only-super@example.com')
    blocked=mysql_client.request('DELETE','/api/profile',headers=headers,json={"current_password":"Secure123!","confirmation":"DELETE"})
    assert blocked.status_code==409
    make_user(UserRole.SUPER_ADMIN,'successor-super@example.com')
    assert mysql_client.request('DELETE','/api/profile',headers=headers,json={"current_password":"Secure123!","confirmation":"DELETE"}).status_code==204

def test_pending_admin_has_self_service_but_no_admin_access(mysql_client):
    response=mysql_client.post('/api/auth/register',json={"full_name":"Pending Admin","email":"pending-admin@example.com","password":"Secure123!","requested_role":"ADMIN"})
    assert response.status_code==201 and response.json()['status']=='PENDING'
    login=mysql_client.post('/api/auth/login',json={"email":"pending-admin@example.com","password":"Secure123!"})
    headers={"Authorization":"Bearer "+login.json()['access_token']}
    assert mysql_client.get('/api/profile',headers=headers).status_code==200
    assert mysql_client.get('/api/admin/learners',headers=headers).status_code==403

def test_admin_cannot_manage_admin_through_learner_endpoint(mysql_client):
    admin_id,admin_headers=make_user(UserRole.ADMIN,'manager-admin@example.com')
    target_id,_=make_user(UserRole.ADMIN,'target-admin@example.com')
    assert mysql_client.delete(f'/api/admin/learners/{target_id}',headers=admin_headers).status_code==404

def test_password_change_is_available_to_every_authenticated_role_and_pending_admin(mysql_client):
    cases=[
        (UserRole.LEARNER,ApprovalStatus.ACTIVE,'password-learner@example.com'),
        (UserRole.ADMIN,ApprovalStatus.ACTIVE,'password-admin@example.com'),
        (UserRole.SUPER_ADMIN,ApprovalStatus.ACTIVE,'password-super@example.com'),
        (UserRole.ADMIN,ApprovalStatus.PENDING,'password-pending@example.com'),
        (UserRole.ADMIN,ApprovalStatus.REJECTED,'password-rejected@example.com'),
    ]
    for role,status,email in cases:
        with SessionLocal() as db:
            user=User(full_name='Password Account',email=email,password_hash=hash_password('Secure123!'),role=role,approval_status=status)
            db.add(user);db.commit();db.refresh(user);headers={"Authorization":"Bearer "+token_for(user)}
        changed=mysql_client.put('/api/profile/password',headers=headers,json={"current_password":"Secure123!","new_password":"DifferentSecure123!"})
        assert changed.status_code==204
        assert mysql_client.post('/api/auth/login',json={"email":email,"password":"Secure123!"}).status_code==401
        assert mysql_client.post('/api/auth/login',json={"email":email,"password":"DifferentSecure123!"}).status_code==200
